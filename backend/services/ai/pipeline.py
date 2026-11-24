"""受控查询管道：``ask()`` 把自然语言问题收敛为"意图 + 参数 + 手写只读 ORM 查询"。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §7.3。12 步链路：
开关 → 限流 → 归一化 → 前置分类 → 解析意图 → 模式闸 → SHACL 闸 → 权限闸
→ 执行（超时/行数）→ 溯源 → 回答模板 → 审计（成功与所有拒绝路径都落库）。
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from rdflib import URIRef

from backend.services.ai.answer import allowed_numbers, build_answer, numbers_subset
from backend.services.ai.audit import write_ai_query_log
from backend.services.ai.catalog import get_catalog
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.executor import execute_intent
from backend.services.ai.gates import bind_params, shacl_check, shacl_check_shape
from backend.services.ai.intents import INTENT_REGISTRY
from backend.services.ai.llm import (
    LLMClient,
    build_narration_payload,
    call_narration,
    get_llm_client,
)
from backend.services.ai.ontology_service import NS, get_ontology_service
from backend.services.ai.proposer import (
    LLMProposer,
    ProposedIntent,
    RuleBasedProposer,
    normalize,
    preclassify,
)
from backend.services.ai.ratelimit import get_rate_limiter

_STATUS_BY_CODE = {
    "AI_PERMISSION_DENIED": "REJECTED_PERMISSION",
    "AI_EXECUTION_TIMEOUT": "REJECTED_TIMEOUT",
    "AI_RATE_LIMITED": "REJECTED_RATE_LIMIT",
    "AI_QUERY_TOO_BROAD": "REJECTED_TOO_BROAD",
}


def _audit_status(exc: AIException) -> str:
    if exc.code == "AI_INTENT_UNKNOWN":
        return "REJECTED_SCHEMA" if exc.reject_reason == "SCHEMA_REJECTED" else "REJECTED_INTENT"
    if exc.code == "AI_PARAM_INVALID":
        return "REJECTED_SHACL" if exc.reject_reason == "SHACL" else "REJECTED_PARAM"
    return _STATUS_BY_CODE.get(exc.code, "FAILED")


def _role_name(user: Any) -> str:
    role = getattr(user, "role", None)
    value = getattr(role, "value", role)
    return str(value) if value else "ANONYMOUS"


def _prepare_intent(spec: Any, raw_params: dict[str, Any], role: str) -> tuple[Any, dict[str, Any], str]:
    """绑定参数 → SHACL 闸 → 权限闸；REST 与 MCP 共用同一套校验，避免旁路。"""
    params = bind_params(spec.params_model, raw_params)
    bound = params.model_dump()

    ontology = get_ontology_service()
    ontology.ensure_loaded()
    if spec.shacl_shape:
        # 外部数据源：显式绑定本体的 MES 形状；约束只在 shapes.ttl
        violations, shacl_status = shacl_check_shape(
            URIRef(NS + spec.shacl_shape), spec.shacl_params, bound, ontology.shapes
        )
    else:
        primary = get_catalog().entities[spec.primary_entity]
        violations, shacl_status = shacl_check(primary, bound, ontology.shapes)
    if violations:
        detail = "; ".join(f"{v['path']}:{v['component']}" for v in violations)
        error = AIException(
            "AI_PARAM_INVALID", f"SHACL 校验失败: {detail}", reject_reason="SHACL"
        )
        # 供调用方审计时如实记录 shacl 状态（否则失败分支会丢失 failed/warn）
        error.shacl_status = shacl_status
        raise error

    if role not in spec.allowed_roles:
        raise AIException(
            "AI_PERMISSION_DENIED",
            f"角色 {role} 无权执行意图 {spec.code}",
        )
    return params, bound, shacl_status


def _provenance(spec: Any, outcome: Any) -> list[dict[str, str]]:
    return [
        {
            "table": source.table,
            "record_ref": "|".join(str(row.get(key)) for key in spec.record_key),
            "ontology_class": source.ontology_iri,
            # 外部系统来源显式标记（ERP/MES），前端据此展示来源标签
            "source_system": spec.source_system,
        }
        for row, source in zip(outcome.result.rows, outcome.result.sources)
    ]


def ask(
    question: str,
    user: Any,
    db: Any,
    request_id: str | None = None,
    *,
    proposer: Any | None = None,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    trace_id = uuid.uuid4().hex
    started = time.monotonic()
    username = getattr(user, "username", None) or "unknown"
    role = _role_name(user)
    raw_question = question or ""

    intent_code: str | None = None
    intent_params: dict[str, Any] | None = None
    shacl_status: str | None = None
    row_count = 0
    model_name = "deterministic-v1"

    def _audit(status: str, exc: AIException | None = None, provenance: Any = None) -> None:
        write_ai_query_log(
            trace_id=trace_id,
            status=status,
            request_id=request_id,
            username=username,
            role=role,
            question=raw_question,
            intent_code=intent_code,
            intent_json=intent_params,
            error_code=exc.code if exc is not None else None,
            shacl_status=shacl_status,
            reject_reason=exc.reject_reason if exc is not None else None,
            model_name=model_name,
            latency_ms=int((time.monotonic() - started) * 1000),
            row_count=row_count,
            provenance_json=provenance,
        )

    try:
        if not settings.ai_enabled:
            raise AIException("AI_DISABLED")
        if not settings.ai_chatbi_enabled:
            raise AIException("AI_CHATBI_DISABLED")

        get_rate_limiter().check(username)

        text = normalize(raw_question, settings.ai_max_question_chars)
        preclassify(text)

        client = llm_client if llm_client is not None else get_llm_client()
        if proposer is not None:
            proposal: ProposedIntent = proposer.propose(text)
        else:
            try:
                proposal = RuleBasedProposer(db).propose(text)
            except AIException as exc:
                # 确定性解析未命中时才有 LLM 兜底；其余拒绝原因（限流/写操作等）原样上抛
                if exc.code != "AI_INTENT_UNKNOWN" or client is None:
                    raise
                proposal = LLMProposer(client).propose(text)
        intent_code = proposal.intent
        intent_params = dict(proposal.params)
        if proposal.source == "llm":
            # 如实记录本次提议实际使用的模型（显式 proposer 由测试/演示注入时以其客户端为准）
            source_client = getattr(proposer, "client", None) or client
            model_name = getattr(source_client, "last_model", None) or settings.ai_llm_model or "llm"

        spec = INTENT_REGISTRY.get(proposal.intent)
        if spec is None:
            raise AIException(
                "AI_INTENT_UNKNOWN",
                reject_reason="SCHEMA_REJECTED" if proposal.source == "llm" else None,
            )

        params, bound, shacl_status = _prepare_intent(
            spec, {**spec.defaults, **proposal.params}, role
        )
        intent_params = bound

        outcome = execute_intent(db, spec, params, role=role, settings=settings)
        row_count = outcome.row_count
        answer_result = build_answer(spec, outcome.result, role, outcome.truncated)

        if client is not None and settings.ai_llm_narration_enabled:
            payload = build_narration_payload(
                outcome.result,
                answer_result.columns,
                allow_external_data=settings.ai_llm_allow_external_data,
            )
            try:
                narration = call_narration(client, payload)
                allow = allowed_numbers(answer_result.rows, {float(row_count)})
                if numbers_subset(narration, allow):
                    answer_result.text = narration
                    model_name = getattr(client, "last_model", None) or settings.ai_llm_model or "llm"
            except Exception:  # noqa: BLE001 - 叙述失败退回确定性模板
                pass

        provenance = _provenance(spec, outcome)

        _audit("OK", provenance=provenance)
        return {
            "trace_id": trace_id,
            "request_id": request_id,
            "intent": {"code": spec.code, "label": spec.label, "params": bound},
            "answer": answer_result.text,
            "data": {
                "columns": answer_result.columns,
                "rows": answer_result.rows,
                "row_count": row_count,
                # 区分"工单不存在"与"工单存在但无工序/报工"等业务空态
                "reason": outcome.result.reason,
            },
            "provenance": provenance,
            "limits": {
                "row_count": row_count,
                "truncated": outcome.truncated,
                "shacl": shacl_status,
                "coverage": spec.shacl_coverage,
                "timeout_seconds": settings.ai_query_timeout_seconds,
                "max_rows": settings.ai_max_rows,
                "elapsed_ms": outcome.elapsed_ms,
            },
            "model": model_name,
        }

    except AIException as exc:
        if exc.trace_id is None:
            exc.trace_id = trace_id
        if shacl_status is None and getattr(exc, "shacl_status", None):
            shacl_status = exc.shacl_status
        _audit(_audit_status(exc), exc=exc)
        raise
    except Exception as exc:  # noqa: BLE001 - 未预期异常也要落审计
        error = AIException("AI_EXECUTION_FAILED", f"内部错误: {type(exc).__name__}")
        error.trace_id = trace_id
        _audit("FAILED", exc=error)
        raise error from exc


def run_intent(
    intent_code: str,
    params: dict[str, Any],
    user: Any,
    db: Any,
    request_id: str | None = None,
) -> dict[str, Any]:
    """结构化意图执行入口（MCP 等外部工具用），与 ``ask`` 共用同一套闸与审计。

    不接受自由文本、不做 LLM 提议；只允许注册表中的只读意图。
    """
    settings = get_settings()
    trace_id = uuid.uuid4().hex
    started = time.monotonic()
    username = getattr(user, "username", None) or "unknown"
    role = _role_name(user)
    question = f"mcp:{intent_code}"

    intent_params: dict[str, Any] | None = None
    shacl_status: str | None = None
    row_count = 0

    def _audit(status: str, exc: AIException | None = None, provenance: Any = None) -> None:
        write_ai_query_log(
            trace_id=trace_id,
            status=status,
            request_id=request_id,
            username=username,
            role=role,
            question=question,
            intent_code=intent_code,
            intent_json=intent_params,
            error_code=exc.code if exc is not None else None,
            shacl_status=shacl_status,
            reject_reason=exc.reject_reason if exc is not None else None,
            model_name="deterministic-v1",
            latency_ms=int((time.monotonic() - started) * 1000),
            row_count=row_count,
            provenance_json=provenance,
        )

    try:
        if not settings.ai_enabled:
            raise AIException("AI_DISABLED")
        if not settings.ai_chatbi_enabled:
            raise AIException("AI_CHATBI_DISABLED")

        get_rate_limiter().check(username)

        spec = INTENT_REGISTRY.get(intent_code)
        if spec is None:
            raise AIException("AI_INTENT_UNKNOWN", reject_reason="SCHEMA_REJECTED")

        bound_params, bound, shacl_status = _prepare_intent(
            spec, {**spec.defaults, **params}, role
        )
        intent_params = bound

        outcome = execute_intent(db, spec, bound_params, role=role, settings=settings)
        row_count = outcome.row_count
        answer_result = build_answer(spec, outcome.result, role, outcome.truncated)
        provenance = _provenance(spec, outcome)

        _audit("OK", provenance=provenance)
        return {
            "trace_id": trace_id,
            "request_id": request_id,
            "tool": spec.code,
            "intent": {"code": spec.code, "label": spec.label, "params": bound},
            "answer": answer_result.text,
            "data": {
                "columns": answer_result.columns,
                "rows": answer_result.rows,
                "row_count": row_count,
                "reason": outcome.result.reason,
            },
            "provenance": provenance,
            "limits": {
                "row_count": row_count,
                "truncated": outcome.truncated,
                "shacl": shacl_status,
                "coverage": spec.shacl_coverage,
                "timeout_seconds": settings.ai_query_timeout_seconds,
                "max_rows": settings.ai_max_rows,
                "elapsed_ms": outcome.elapsed_ms,
            },
            "model": "deterministic-v1",
        }
    except AIException as exc:
        if exc.trace_id is None:
            exc.trace_id = trace_id
        if shacl_status is None and getattr(exc, "shacl_status", None):
            shacl_status = exc.shacl_status
        _audit(_audit_status(exc), exc=exc)
        raise
    except Exception as exc:  # noqa: BLE001 - 未预期异常也要落审计
        error = AIException("AI_EXECUTION_FAILED", f"内部错误: {type(exc).__name__}")
        error.trace_id = trace_id
        _audit("FAILED", exc=error)
        raise error from exc
