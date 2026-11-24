"""AI 审计写入（设计 §9.3）。

要点：
- 使用**独立 session**（``SessionLocal()``）并显式 ``commit()``；不复用 ``get_db()``
  （后者只 close 不 commit），否则请求结束后审计行会丢失；
- 审计失败不改变 HTTP 响应，但必须记 error 日志；失败后重开一次会话写 ``FAILED`` 兜底标记；
- ``AI_LOG_QUESTION=false`` 时不落原文，只存 SHA-256。
"""
from __future__ import annotations

import hashlib
from typing import Any

from backend.common.database.base import SessionLocal
from backend.common.models.ai import AiQueryLog
from backend.common.utils.logger import log_error
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AUDIT_STATUSES

# 保留期是代码常量（不占 17 个环境变量口径）；清理任务在 P2
AI_QUERY_LOG_RETENTION_DAYS = 90
_MAX_REJECT_REASON = 300


def _persist(payload: dict[str, Any]) -> bool:
    db = SessionLocal()
    try:
        db.add(AiQueryLog(**payload))
        db.commit()
        return True
    except Exception as exc:  # 审计失败不影响主流程
        db.rollback()
        log_error("AI 审计写入失败", exc, trace_id=payload.get("trace_id"))
        return False
    finally:
        db.close()


def write_ai_query_log(
    *,
    trace_id: str,
    status: str,
    request_id: str | None = None,
    username: str | None = None,
    role: str | None = None,
    question: str | None = None,
    intent_code: str | None = None,
    intent_json: dict[str, Any] | None = None,
    error_code: str | None = None,
    shacl_status: str | None = None,
    reject_reason: str | None = None,
    model_name: str | None = None,
    latency_ms: int | None = None,
    row_count: int = 0,
    provenance_json: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> None:
    if status not in AUDIT_STATUSES:
        raise ValueError(f"非法审计状态: {status}")

    settings = get_settings()
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest() if question else None
    stored_question = question[: settings.ai_max_question_chars] if (
        question and settings.ai_log_question
    ) else None

    payload: dict[str, Any] = {
        "trace_id": trace_id,
        "request_id": request_id,
        "username": username,
        "role": role,
        "question": stored_question,
        "question_sha256": digest,
        "intent_code": intent_code,
        "intent_json": intent_json,
        "status": status,
        "error_code": error_code,
        "shacl_status": shacl_status,
        "reject_reason": reject_reason[:_MAX_REJECT_REASON] if reject_reason else None,
        "model": model_name,
        "latency_ms": latency_ms,
        "row_count": row_count,
        "provenance_json": provenance_json,
    }
    if _persist(payload):
        return

    fallback = {
        "trace_id": f"{trace_id}-audit-failed"[:36],
        "request_id": request_id,
        "username": username,
        "role": role,
        "question_sha256": digest,
        "status": "FAILED",
        "error_code": "AUDIT_WRITE_FAILED",
        "reject_reason": "审计写入失败（已记录 error 日志）",
        "row_count": 0,
    }
    if not _persist(fallback):
        log_error("AI 审计兜底写入仍失败", trace_id=trace_id)
