"""受控执行器：只调用意图自带的只读 handler，并强制超时/行数/溯源（设计 §7.3）。

- 超时：PG 用 ``SET LOCAL statement_timeout``（字面量毫秒，唯一允许的 ``text()``）；
  SQLite 用 ``set_progress_handler``；两者都叠加 Python 预算，避免驱动侧遗漏；
- 行数：按 ``AI_MAX_ROWS`` 二次截断；
- 溯源：每行 ``record_key`` 必须非空、``sources`` 必须覆盖行，否则整体拒绝。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.common.database.base import Base
from backend.services.ai.config import AISettings, get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.intent import IntentSpec, QueryResult
from backend.services.ai.mes_shapes import validate_mes_result

# 外部系统只读来源白名单：仅允许语义映射已登记、且链路真实使用的 MES 表。
# 未列入此处的表仍按"未知来源表"拒绝，避免溯源校验被整体放松。
EXTERNAL_SOURCE_TABLES: Final[frozenset[str]] = frozenset({
    "prd_work_order",
    "prd_process_task",
    "prd_process_report",
})


@dataclass
class ExecutionOutcome:
    result: QueryResult
    row_count: int
    truncated: bool
    elapsed_ms: int
    timeout_mode: str


def _apply_timeout(
    db: Session, seconds: int, clock
) -> tuple[str, Any]:
    try:
        bind = db.get_bind()
    except Exception:  # noqa: BLE001 - 拿不到绑定信息时退回纯 Python 预算
        return "python_budget", None

    dialect = getattr(bind, "dialect", None)
    name = getattr(dialect, "name", "")

    if name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {int(seconds * 1000)}"))
        return "statement_timeout", None

    if name == "sqlite":
        try:
            connection = db.connection()
            fairy = getattr(connection, "connection", connection)
            raw = getattr(fairy, "driver_connection", fairy)
            deadline = clock() + seconds

            def _handler() -> int:
                return 1 if clock() >= deadline else 0

            raw.set_progress_handler(_handler, 1000)
            return "progress_handler", raw
        except Exception:  # noqa: BLE001
            return "python_budget", None

    return "python_budget", None


def _clear_timeout(raw: Any) -> None:
    if raw is None:
        return
    try:
        raw.set_progress_handler(None, 0)
    except Exception:  # noqa: BLE001
        pass


def _validate_provenance(spec: IntentSpec, result: QueryResult) -> None:
    if not result.rows:
        return
    if len(result.sources) < len(result.rows):
        raise AIException(
            "AI_PROVENANCE_INCOMPLETE",
            f"溯源条数 {len(result.sources)} 少于结果行数 {len(result.rows)}",
        )
    for row in result.rows:
        missing = [
            key for key in spec.record_key
            if row.get(key) is None or str(row.get(key)).strip() == ""
        ]
        if missing:
            raise AIException(
                "AI_PROVENANCE_INCOMPLETE",
                f"记录键缺失: {', '.join(missing)}",
            )
    for source in result.sources:
        if (
            source.table not in Base.metadata.tables
            and source.table not in EXTERNAL_SOURCE_TABLES
        ):
            raise AIException("AI_PROVENANCE_INCOMPLETE", f"未知来源表: {source.table}")
        if not source.record_key:
            raise AIException("AI_PROVENANCE_INCOMPLETE", "来源记录键为空")


def execute_intent(
    db: Session,
    spec: IntentSpec,
    params: Any,
    *,
    role: str,
    settings: AISettings | None = None,
    clock=time.monotonic,
) -> ExecutionOutcome:
    settings = settings or get_settings()
    timeout = settings.ai_query_timeout_seconds
    mode, raw = _apply_timeout(db, timeout, clock)
    started = clock()
    try:
        result = spec.handler(db, params, role)
    except AIException:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一转成受控错误码
        elapsed = clock() - started
        if elapsed >= timeout:
            raise AIException("AI_EXECUTION_TIMEOUT", reject_reason="TIMEOUT") from exc
        raise AIException("AI_EXECUTION_FAILED", f"执行失败: {type(exc).__name__}") from exc
    finally:
        _clear_timeout(raw)

    elapsed = clock() - started
    if elapsed > timeout:
        raise AIException("AI_EXECUTION_TIMEOUT", reject_reason="TIMEOUT")

    _validate_provenance(spec, result)

    rows = result.rows[: settings.ai_max_rows]
    sources = result.sources[: len(rows)]
    truncated = len(rows) < len(result.rows)

    # 外部数据源：结果行必须满足本体形状；违规即拒绝，避免把脏数据当成已校验结果
    if spec.source_system == "MES" and rows:
        violations = validate_mes_result(rows)
        if violations:
            detail = "; ".join(
                f"{item['row_key']}:{item['path']}:{item['component']}"
                for item in violations[:5]
            )
            raise AIException(
                "AI_EXECUTION_FAILED",
                f"MES 数据未通过本体形状校验: {len(violations)} 条（{detail}）",
                reject_reason="SHACL",
            )

    return ExecutionOutcome(
        result=QueryResult(
            columns=list(result.columns),
            rows=rows,
            sources=sources,
            reason=result.reason,
        ),
        row_count=len(rows),
        truncated=truncated,
        elapsed_ms=int(elapsed * 1000),
        timeout_mode=mode,
    )
