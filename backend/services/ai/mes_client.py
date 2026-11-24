"""MES 跨库只读客户端（默认关闭）。

安全边界（与用户约束一一对应）：
- 连接建立后立即 ``SET SESSION TRANSACTION READ ONLY`` + ``START TRANSACTION READ ONLY``；
- 只执行本模块硬编码的 SELECT，表名必须命中 ``ALLOWED_TABLES``，参数一律 ``%s`` 绑定；
- 仅暴露 ``fetch_work_order_progress``，模块内不存在 INSERT/UPDATE/DELETE/DDL 路径；
- 凭据只来自 ``AISettings``（进程环境变量），异常信息不含账号、密码或连接串；
- 连接/读超时与行数上限都取自配置，避免跨库查询拖垮 ERP 请求。

本模块直连 MySQL 而非复用 ERP SQLAlchemy 会话：MES 与 ERP 是两个数据库，
跨库无法共享事务；用独立连接才能把"只读事务"约束施加到 MES 会话上。
"""
from __future__ import annotations

import re
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from backend.services.ai.config import AISettings, get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.intent import Provenance, QueryResult
from backend.services.ai.ontology_service import NS

# 白名单：仅本次语义映射涉及、且最小链路真实使用的表
ALLOWED_TABLES: frozenset[str] = frozenset({
    "prd_work_order",
    "prd_process_task",
    "prd_process_report",
})

COLUMNS: tuple[str, ...] = (
    "work_order_no", "product_name", "order_status", "order_quantity",
    "order_completed_quantity", "order_qualified_quantity", "order_scrapped_quantity",
    "planned_start_date", "planned_end_date",
    "process_task_id", "process_name", "task_sequence", "task_status", "equipment_id",
    "task_completed_quantity", "task_qualified_quantity", "task_scrapped_quantity",
    "report_id", "report_time", "report_completed_quantity",
    "report_qualified_quantity", "report_scrapped_quantity", "defect_reason",
    "actual_hours", "row_key",
)

_WORK_ORDER_SQL = """
SELECT id, work_order_no, product_name, quantity,
       completed_quantity, qualified_quantity, scrapped_quantity, status,
       planned_start_date, planned_end_date, actual_start_date, actual_end_date
FROM prd_work_order
WHERE work_order_no = %s
LIMIT 1
"""

_PROCESS_TASK_SQL = """
SELECT id, work_order_id, process_id, process_name, `sequence`, status,
       equipment_id, planned_start_date, planned_end_date,
       actual_start_date, actual_end_date,
       completed_quantity, qualified_quantity, scrapped_quantity
FROM prd_process_task
WHERE work_order_id = %s
ORDER BY `sequence`, id
LIMIT %s
"""

_PROCESS_REPORT_SQL = """
SELECT id, process_task_id, process_id, process_name, report_time,
       completed_quantity, qualified_quantity, scrapped_quantity,
       defect_reason, actual_hours
FROM prd_process_report
WHERE work_order_id = %s
ORDER BY report_time, id
LIMIT %s
"""

_TABLE_REF_RE = re.compile(r"\b(?:FROM|JOIN)\s+`?([A-Za-z0-9_]+)`?", re.IGNORECASE)


def _assert_read_only_sql(sql: str) -> None:
    """代码层兜底：只允许单条 SELECT，且表名必须在白名单内。"""
    normalized = " ".join(sql.split())
    if not normalized.upper().startswith("SELECT "):
        raise AIException("AI_MES_UNAVAILABLE", "MES 查询仅允许 SELECT")
    if ";" in normalized:
        raise AIException("AI_MES_UNAVAILABLE", "MES 查询不允许多语句")
    tables = {match.group(1).lower() for match in _TABLE_REF_RE.finditer(normalized)}
    unknown = tables - ALLOWED_TABLES
    if unknown:
        raise AIException("AI_MES_UNAVAILABLE", f"MES 查询涉及未授权表: {sorted(unknown)}")


def _number(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _datetime(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ") if hasattr(value, "hour") else value.isoformat()
    return str(value)


def _connect(settings: AISettings) -> Any:
    """建立 MES 连接；失败时只抛受控错误，不回显连接串与凭据。"""
    try:
        return pymysql.connect(
            host=settings.mes_db_host,
            port=settings.mes_db_port,
            user=settings.mes_db_user,
            password=settings.mes_db_password.get_secret_value(),
            database=settings.mes_db_name,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=settings.mes_query_timeout_seconds,
            read_timeout=settings.mes_query_timeout_seconds,
            write_timeout=settings.mes_query_timeout_seconds,
        )
    except Exception:  # noqa: BLE001 - 驱动异常可能含连接串，统一收敛
        raise AIException("AI_MES_UNAVAILABLE", "MES 数据库连接失败") from None


def _fetch_all(cursor: Any, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    _assert_read_only_sql(sql)
    cursor.execute(sql, params)
    return list(cursor.fetchall())


def _order_row(order: dict[str, Any], row_key: str) -> dict[str, Any]:
    return {
        "work_order_no": order.get("work_order_no"),
        "product_name": order.get("product_name"),
        "order_status": order.get("status"),
        "order_quantity": _number(order.get("quantity")),
        "order_completed_quantity": _number(order.get("completed_quantity")),
        "order_qualified_quantity": _number(order.get("qualified_quantity")),
        "order_scrapped_quantity": _number(order.get("scrapped_quantity")),
        "planned_start_date": _datetime(order.get("planned_start_date")),
        "planned_end_date": _datetime(order.get("planned_end_date")),
        "process_task_id": None,
        "process_name": None,
        "task_sequence": None,
        "task_status": None,
        "equipment_id": None,
        "task_completed_quantity": None,
        "task_qualified_quantity": None,
        "task_scrapped_quantity": None,
        "report_id": None,
        "report_time": None,
        "report_completed_quantity": None,
        "report_qualified_quantity": None,
        "report_scrapped_quantity": None,
        "defect_reason": None,
        "actual_hours": None,
        "row_key": row_key,
    }


def _with_task(row: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    row.update({
        "process_task_id": task.get("id"),
        "process_name": task.get("process_name"),
        "task_sequence": task.get("sequence"),
        "task_status": task.get("status"),
        "equipment_id": task.get("equipment_id"),
        "task_completed_quantity": _number(task.get("completed_quantity")),
        "task_qualified_quantity": _number(task.get("qualified_quantity")),
        "task_scrapped_quantity": _number(task.get("scrapped_quantity")),
    })
    return row


def _with_report(row: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    row.update({
        "report_id": report.get("id"),
        "report_time": _datetime(report.get("report_time")),
        "report_completed_quantity": _number(report.get("completed_quantity")),
        "report_qualified_quantity": _number(report.get("qualified_quantity")),
        "report_scrapped_quantity": _number(report.get("scrapped_quantity")),
        "defect_reason": report.get("defect_reason"),
        "actual_hours": _number(report.get("actual_hours")),
    })
    return row


def fetch_work_order_progress(
    work_order_no: str,
    *,
    limit: int | None = None,
    settings: AISettings | None = None,
) -> QueryResult:
    """给定 MES 工单号，返回该工单的工序任务与报工记录（只读）。"""
    settings = settings or get_settings()
    if not settings.mes_ready:
        raise AIException("AI_MES_UNAVAILABLE")

    order_no = (work_order_no or "").strip()
    if not order_no:
        raise AIException("AI_PARAM_INVALID", "工单号不能为空")

    cap = max(1, min(limit or settings.mes_query_max_rows, settings.mes_query_max_rows))

    connection = _connect(settings)
    try:
        with connection.cursor() as cursor:
            # 会话层强制只读：即使凭据是 root，也无法在本连接内写入
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("START TRANSACTION READ ONLY")

            orders = _fetch_all(cursor, _WORK_ORDER_SQL, (order_no,))
            if not orders:
                return QueryResult(
                    columns=list(COLUMNS), rows=[], sources=[], reason="work_order_not_found"
                )
            order = orders[0]

            tasks = _fetch_all(cursor, _PROCESS_TASK_SQL, (order["id"], cap))
            reports = _fetch_all(cursor, _PROCESS_REPORT_SQL, (order["id"], cap))
    except AIException:
        raise
    except Exception:  # noqa: BLE001 - 驱动异常可能含 SQL/连接细节，统一收敛
        raise AIException("AI_MES_UNAVAILABLE", "MES 只读查询失败") from None
    finally:
        try:
            connection.rollback()
        except Exception:  # noqa: BLE001 - 连接已断开时 rollback 可能失败
            pass
        try:
            connection.close()
        except Exception:  # noqa: BLE001 - 关闭失败不影响只读查询结果
            pass

    if not tasks:
        row = _order_row(order, f"work_order:{order['id']}")
        return QueryResult(
            columns=list(COLUMNS),
            rows=[row],
            sources=[Provenance(
                table="prd_work_order", record_key=str(order["id"]),
                ontology_iri=NS + "ProductionOrder",
            )],
            reason="work_order_no_tasks",
        )

    reports_by_task: dict[Any, list[dict[str, Any]]] = {}
    for report in reports:
        reports_by_task.setdefault(report.get("process_task_id"), []).append(report)

    rows: list[dict[str, Any]] = []
    sources: list[Provenance] = []
    for task in tasks:
        if len(rows) >= cap:
            break
        task_reports = reports_by_task.get(task.get("id"), [])
        if not task_reports:
            rows.append(_with_task(_order_row(order, f"task:{task['id']}"), task))
            sources.append(Provenance(
                table="prd_process_task", record_key=str(task["id"]),
                ontology_iri=NS + "ScheduledOperation",
            ))
            continue
        for report in task_reports:
            if len(rows) >= cap:
                break
            rows.append(_with_report(
                _with_task(_order_row(order, f"report:{report['id']}"), task), report
            ))
            sources.append(Provenance(
                table="prd_process_report", record_key=str(report["id"]),
                ontology_iri=NS + "ScheduledOperation",
            ))

    return QueryResult(columns=list(COLUMNS), rows=rows, sources=sources)
