"""AI 助手路由（P0 只有只读接口）。

权限模型（设计 §6.2）：``ai`` 域 ``anonymousRead=false``，路由级强制登录，
再按 ``READ_ROLE_POLICY["ai"]`` 收窄角色。**不挂** ``_gates``：``ai`` 是只读域，
若走通用写门会因 ``WRITE_ROLE_POLICY["ai"]`` 为空把合法请求判成 403。
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.api.routers.auth import get_current_user
from backend.common.database.base import get_db
from backend.common.models.ai import AiQueryLog
from backend.common.models.user import User, UserRole
from backend.common.utils.security_policy import READ_ROLE_POLICY
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.insights import build_dashboard_insights
from backend.services.ai.ontology_service import (
    OntologySourceError,
    get_ontology_service,
)
from backend.services.ai.pipeline import ask as ask_pipeline

router = APIRouter()
# MCP 工具层使用独立 Bearer token（不依赖登录会话），因此单独挂载、不继承 ai 域的登录依赖
mcp_router = APIRouter()


def _role_of(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


async def require_ai_access(current_user: User = Depends(get_current_user)) -> User:
    """登录之上的 AI 域读角色闸；未声明策略时 fail-closed。"""
    role = _role_of(current_user)
    if role == UserRole.ADMIN.value:
        return current_user
    allowed = READ_ROLE_POLICY.get("ai")
    if allowed is None or role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前角色无权使用 AI 助手",
        )
    return current_user


def _raise_http(exc: AIException) -> None:
    raise HTTPException(status_code=exc.http_status, detail=exc.to_payload())


def _ensure_enabled() -> None:
    """``AI_ENABLED=false`` 时整个 ``/api/ai/*`` 关闭（503）。"""
    if not get_settings().ai_enabled:
        _raise_http(AIException("AI_DISABLED"))


def _ensure_chatbi() -> None:
    """``AI_CHATBI_ENABLED=false`` 只关闭问答与洞察，本体检索仍可用。"""
    _ensure_enabled()
    if not get_settings().ai_chatbi_enabled:
        _raise_http(AIException("AI_CHATBI_DISABLED"))


def _log_item(log: AiQueryLog) -> dict:
    return {
        "trace_id": log.trace_id,
        "request_id": log.request_id,
        "username": log.username,
        "role": log.role,
        "question": log.question,
        "intent_code": log.intent_code,
        "intent": log.intent_json,
        "status": log.status,
        "error_code": log.error_code,
        "shacl_status": log.shacl_status,
        "row_count": log.row_count,
        "latency_ms": log.latency_ms,
        "model": log.model,
        "provenance": log.provenance_json,
        "feedback_score": log.feedback_score,
        "feedback_comment": log.feedback_comment,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("/ping")
async def ping() -> dict[str, object]:
    """连通性与开关探针（不触达本体，避免把加载失败误报成鉴权失败）。"""
    _ensure_enabled()
    settings = get_settings()
    return {
        "ok": True,
        "ai_enabled": settings.ai_enabled,
        "chatbi_enabled": settings.ai_chatbi_enabled,
        "mes_query_enabled": settings.mes_ready,
    }


@router.post("/chat")
async def chat(
    request: Request,
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """受控问答：意图白名单 + 只读执行 + 溯源；本接口不写任何业务表。"""
    _ensure_chatbi()
    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        _raise_http(AIException("AI_PARAM_INVALID", "question 不能为空"))
    try:
        return ask_pipeline(
            question.strip(),
            current_user,
            db,
            request_id=getattr(request.state, "request_id", None),
        )
    except AIException as exc:
        _raise_http(exc)


@router.get("/queries")
async def list_queries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """审计列表：普通用户仅本人记录，ADMIN 可看全部。"""
    _ensure_enabled()
    query = db.query(AiQueryLog).filter(AiQueryLog.is_deleted.is_(False))
    if _role_of(current_user) != UserRole.ADMIN.value:
        query = query.filter(AiQueryLog.username == getattr(current_user, "username", None))
    total = query.count()
    rows = (
        query.order_by(AiQueryLog.created_at.desc(), AiQueryLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_log_item(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/queries/{trace_id}/feedback")
async def submit_feedback(
    trace_id: str,
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """反馈只允许改本人记录；ADMIN 例外。"""
    _ensure_enabled()
    score = payload.get("score") if isinstance(payload, dict) else None
    if isinstance(score, bool) or not isinstance(score, int) or score not in (-1, 0, 1):
        _raise_http(AIException("AI_PARAM_INVALID", "score 必须为 -1 / 0 / 1"))
    comment = payload.get("comment")
    if comment is not None and (not isinstance(comment, str) or len(comment) > 500):
        _raise_http(AIException("AI_PARAM_INVALID", "comment 必须是 500 字以内的字符串"))

    log = (
        db.query(AiQueryLog)
        .filter(AiQueryLog.trace_id == trace_id, AiQueryLog.is_deleted.is_(False))
        .first()
    )
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"问答记录不存在: {trace_id}", "trace_id": trace_id},
        )
    if _role_of(current_user) != UserRole.ADMIN.value and log.username != getattr(
        current_user, "username", None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AI_PERMISSION_DENIED",
                "message": "只能反馈本人的问答记录",
                "trace_id": trace_id,
            },
        )
    log.feedback_score = score
    log.feedback_comment = comment
    db.commit()
    return {
        "trace_id": trace_id,
        "feedback_score": score,
        "feedback_comment": comment,
    }


@router.get("/insights/dashboard")
async def dashboard_insights(
    window: str = Query("7d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """A4 异常解读：汇总六域 KPI 告警与 MRP 异常，只读且按角色裁剪金额。"""
    _ensure_chatbi()
    if window not in {"7d", "30d"}:
        _raise_http(AIException("AI_PARAM_INVALID", "window 仅支持 7d / 30d"))
    return build_dashboard_insights(db, window, _role_of(current_user))



@router.get("/ontology/entities")
async def list_entities() -> dict:
    _ensure_enabled()
    from backend.services.ai import catalog

    return catalog.get_catalog().summary()


@router.get("/ontology/entities/{name}")
async def describe_entity(name: str) -> dict:
    _ensure_enabled()
    try:
        return get_ontology_service().describe(name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AI_INTENT_UNKNOWN", "message": f"未知实体: {name}", "trace_id": None},
        )
    except OntologySourceError as exc:
        _raise_http(AIException("AI_EXECUTION_FAILED", str(exc)))


@router.get("/ontology/search")
async def search_ontology(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=50),
) -> dict:
    _ensure_enabled()
    try:
        items = get_ontology_service().search(q, limit=limit)
    except OntologySourceError as exc:
        _raise_http(AIException("AI_EXECUTION_FAILED", str(exc)))
    return {"query": q, "items": items, "count": len(items)}


@router.get("/ontology/rules")
async def list_rules() -> dict:
    _ensure_enabled()
    try:
        return {"rules": get_ontology_service().rules()}
    except OntologySourceError as exc:
        _raise_http(AIException("AI_EXECUTION_FAILED", str(exc)))


@router.post("/ontology/sparql")
async def run_sparql(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    _ensure_enabled()
    if _role_of(current_user) != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只读 SPARQL 仅管理员可用",
        )
    if not get_settings().ai_sparql_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI_SPARQL_ENABLED 未开启",
        )
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        _raise_http(AIException("AI_PARAM_INVALID", "query 不能为空"))
    limit = payload.get("limit", 200)
    if not isinstance(limit, int):
        _raise_http(AIException("AI_PARAM_INVALID", "limit 必须是整数"))
    try:
        rows = get_ontology_service().sparql(query, limit=limit)
    except ValueError as exc:
        _raise_http(AIException("AI_PARAM_INVALID", str(exc)))
    except OntologySourceError as exc:
        _raise_http(AIException("AI_EXECUTION_FAILED", str(exc)))
    return {"rows": rows, "row_count": len(rows)}


@router.get("/semantics/mes")
def mes_semantics(current_user: User = Depends(get_current_user)) -> dict:
    """ERP↔MES 语义映射 v1：只读目录，锚点与枚举来自本体。"""
    _ensure_enabled()
    from backend.services.ai.semantics import SemanticsSourceError, build_mes_mapping

    try:
        report = build_mes_mapping()
    except SemanticsSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AI_SEMANTICS_UNAVAILABLE", "message": str(exc)},
        )
    if report["problems"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AI_SEMANTICS_INVALID", "problems": report["problems"]},
        )
    return report


@mcp_router.post("/mcp")
async def mcp_endpoint(
    request: Request,
    payload: dict = Body(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """MCP JSON-RPC 子集：只暴露只读意图，Bearer token 鉴权，写操作默认不开放。"""
    _ensure_enabled()
    from backend.services.ai.mcp.server import MCPAuthError, authenticate, handle

    try:
        username, role = authenticate(authorization)
    except MCPAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return handle(payload, username, role, db, request_id=request.headers.get("x-request-id"))
