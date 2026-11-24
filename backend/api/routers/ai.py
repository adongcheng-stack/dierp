"""AI 助手路由（P0 只有只读接口）。

权限模型（设计 §6.2）：``ai`` 域 ``anonymousRead=false``，路由级强制登录，
再按 ``READ_ROLE_POLICY["ai"]`` 收窄角色。**不挂** ``_gates``：``ai`` 是只读域，
若走通用写门会因 ``WRITE_ROLE_POLICY["ai"]`` 为空把合法请求判成 403。
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from backend.api.routers.auth import get_current_user
from backend.common.models.user import User, UserRole
from backend.common.utils.security_policy import READ_ROLE_POLICY
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.ontology_service import (
    OntologySourceError,
    get_ontology_service,
)

router = APIRouter()


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


@router.get("/ping")
async def ping() -> dict[str, bool]:
    """连通性与开关探针（不触达本体，避免把加载失败误报成鉴权失败）。"""
    settings = get_settings()
    return {
        "ok": True,
        "ai_enabled": settings.ai_enabled,
        "chatbi_enabled": settings.ai_chatbi_enabled,
    }


@router.get("/ontology/entities")
async def list_entities() -> dict:
    from backend.services.ai import catalog

    return catalog.get_catalog().summary()


@router.get("/ontology/entities/{name}")
async def describe_entity(name: str) -> dict:
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
    try:
        items = get_ontology_service().search(q, limit=limit)
    except OntologySourceError as exc:
        _raise_http(AIException("AI_EXECUTION_FAILED", str(exc)))
    return {"query": q, "items": items, "count": len(items)}


@router.get("/ontology/rules")
async def list_rules() -> dict:
    try:
        return {"rules": get_ontology_service().rules()}
    except OntologySourceError as exc:
        _raise_http(AIException("AI_EXECUTION_FAILED", str(exc)))


@router.post("/ontology/sparql")
async def run_sparql(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict:
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
