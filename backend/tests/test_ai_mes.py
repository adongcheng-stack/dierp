"""MES 只读链路验收：开关、只读事务、表白名单、参数化、溯源与行结构。

全部用桩替换 pymysql 连接，不依赖真实数据库；真实库只在人工连通性验证时使用。
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.services.ai import mes_client
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.executor import _validate_provenance, execute_intent
from backend.services.ai.intent import Provenance, QueryResult
from backend.services.ai.intents import mes as mes_intent
from backend.services.ai.mes_shapes import validate_mes_result
from backend.services.ai.ontology_service import NS
from backend.services.ai.pipeline import _prepare_intent

WORK_ORDER_NO = "GD-20260914-00001"


class _FakeCursor:
    def __init__(self, rows_by_table: dict[str, list[dict]]):
        self.rows_by_table = rows_by_table
        self.executed: list[tuple[str, tuple | None]] = []
        self._last: list[dict] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))
        normalized = " ".join(sql.split()).upper()
        for table, rows in self.rows_by_table.items():
            if f"FROM {table.upper()}" in normalized:
                self._last = rows
                return
        self._last = []

    def fetchall(self) -> list[dict]:
        return list(self._last)


class _FakeConnection:
    def __init__(self, rows_by_table: dict[str, list[dict]]):
        self.cursor_obj = _FakeCursor(rows_by_table)
        self.rolled_back = False
        self.closed = False

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def _order_row() -> dict:
    return {
        "id": 1,
        "work_order_no": WORK_ORDER_NO,
        "product_name": "测试产品",
        "quantity": Decimal("100.00"),
        "completed_quantity": Decimal("60.00"),
        "qualified_quantity": Decimal("58.00"),
        "scrapped_quantity": Decimal("2.00"),
        "status": "IN_PRODUCTION",
        "planned_start_date": dt.datetime(2026, 9, 14, 8, 0),
        "planned_end_date": dt.datetime(2026, 9, 15, 18, 0),
        "actual_start_date": dt.datetime(2026, 9, 14, 9, 0),
        "actual_end_date": None,
    }


def _tasks() -> list[dict]:
    return [
        {
            "id": 11, "work_order_id": 1, "process_id": 101, "process_name": "SMT",
            "sequence": 1, "status": "COMPLETED", "equipment_id": 5,
            "planned_start_date": dt.datetime(2026, 9, 14, 8, 0),
            "planned_end_date": dt.datetime(2026, 9, 14, 12, 0),
            "actual_start_date": dt.datetime(2026, 9, 14, 9, 0),
            "actual_end_date": dt.datetime(2026, 9, 14, 11, 0),
            "completed_quantity": Decimal("40.00"),
            "qualified_quantity": Decimal("39.00"),
            "scrapped_quantity": Decimal("1.00"),
        },
        {
            "id": 12, "work_order_id": 1, "process_id": 102, "process_name": "组装",
            "sequence": 2, "status": "PENDING", "equipment_id": None,
            "planned_start_date": dt.datetime(2026, 9, 14, 13, 0),
            "planned_end_date": dt.datetime(2026, 9, 15, 18, 0),
            "actual_start_date": None, "actual_end_date": None,
            "completed_quantity": Decimal("0.00"),
            "qualified_quantity": Decimal("0.00"),
            "scrapped_quantity": Decimal("0.00"),
        },
    ]


def _reports() -> list[dict]:
    return [
        {
            "id": 111, "process_task_id": 11, "process_id": 101, "process_name": "SMT",
            "report_time": dt.datetime(2026, 9, 14, 11, 30),
            "completed_quantity": Decimal("40.00"),
            "qualified_quantity": Decimal("39.00"),
            "scrapped_quantity": Decimal("1.00"),
            "defect_reason": "虚焊",
            "actual_hours": Decimal("2.50"),
        },
    ]


@pytest.fixture(autouse=True)
def _mes_settings(monkeypatch):
    monkeypatch.setenv("MES_QUERY_ENABLED", "true")
    monkeypatch.setenv("MES_DB_USER", "ut-mes")
    monkeypatch.setenv("MES_DB_PASSWORD", "ut-mes-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _install(monkeypatch, rows_by_table: dict[str, list[dict]]) -> tuple[_FakeConnection, dict]:
    conn = _FakeConnection(rows_by_table)
    seen: dict = {}

    def _connect(**kwargs):
        seen.update(kwargs)
        return conn

    monkeypatch.setattr(mes_client.pymysql, "connect", _connect)
    return conn, seen


def test_fetch_forces_read_only_transaction_and_parameterized_select(monkeypatch):
    conn, seen = _install(monkeypatch, {
        "prd_work_order": [_order_row()],
        "prd_process_task": _tasks(),
        "prd_process_report": _reports(),
    })

    result = mes_client.fetch_work_order_progress(WORK_ORDER_NO, limit=50)

    statements = conn.cursor_obj.executed
    assert " ".join(statements[0][0].split()).upper() == "SET SESSION TRANSACTION READ ONLY"
    assert " ".join(statements[1][0].split()).upper() == "START TRANSACTION READ ONLY"
    for sql, _ in statements[2:]:
        assert " ".join(sql.split()).upper().startswith("SELECT ")
        assert WORK_ORDER_NO not in sql  # 参数化，不拼接字面量

    assert seen["autocommit"] is False
    assert seen["password"] == "ut-mes-secret"
    assert conn.rolled_back is True and conn.closed is True

    # 一条报工行 + 一条无报工的工序行
    assert len(result.rows) == 2
    assert len(result.sources) == len(result.rows)
    report_row = next(row for row in result.rows if row["report_id"] == 111)
    assert report_row["work_order_no"] == WORK_ORDER_NO
    assert report_row["process_task_id"] == 11
    assert report_row["report_qualified_quantity"] == 39.0
    assert report_row["row_key"] == "report:111"
    task_row = next(row for row in result.rows if row["process_task_id"] == 12)
    assert task_row["report_id"] is None
    assert task_row["row_key"] == "task:12"
    assert {source.table for source in result.sources} == {
        "prd_process_report", "prd_process_task",
    }


def test_fetch_returns_order_row_when_no_tasks(monkeypatch):
    _install(monkeypatch, {
        "prd_work_order": [_order_row()],
        "prd_process_task": [],
        "prd_process_report": [],
    })
    result = mes_client.fetch_work_order_progress(WORK_ORDER_NO)
    assert len(result.rows) == 1
    assert result.rows[0]["row_key"] == "work_order:1"
    assert result.rows[0]["order_status"] == "IN_PRODUCTION"
    assert result.sources[0].table == "prd_work_order"


def test_fetch_reports_unknown_work_order(monkeypatch):
    _install(monkeypatch, {"prd_work_order": []})
    result = mes_client.fetch_work_order_progress(WORK_ORDER_NO)
    assert result.rows == [] and result.sources == []
    assert result.reason == "work_order_not_found"


def test_disabled_switch_never_connects(monkeypatch):
    monkeypatch.setenv("MES_QUERY_ENABLED", "false")
    get_settings.cache_clear()

    def _boom(**kwargs):  # pragma: no cover - 不应被调用
        raise AssertionError("MES 未启用时不得建立连接")

    monkeypatch.setattr(mes_client.pymysql, "connect", _boom)
    with pytest.raises(AIException) as exc:
        mes_client.fetch_work_order_progress(WORK_ORDER_NO)
    assert exc.value.code == "AI_MES_UNAVAILABLE"
    assert "ut-mes-secret" not in exc.value.message


def test_table_whitelist_and_select_only():
    with pytest.raises(AIException):
        mes_client._assert_read_only_sql("SELECT * FROM mysql.user")
    with pytest.raises(AIException):
        mes_client._assert_read_only_sql("DELETE FROM prd_work_order")
    with pytest.raises(AIException):
        mes_client._assert_read_only_sql("SELECT * FROM prd_work_order; DROP TABLE prd_work_order")
    mes_client._assert_read_only_sql(mes_client._PROCESS_TASK_SQL)


def test_params_model_forbids_extra_and_requires_order_number():
    with pytest.raises(ValidationError):
        mes_intent.MesWorkOrderProgressParams()
    with pytest.raises(ValidationError):
        mes_intent.MesWorkOrderProgressParams(work_order_no="x", sql="DROP TABLE t")


def test_executor_provenance_accepts_only_whitelisted_mes_tables():
    spec = mes_intent.SPEC
    good = QueryResult(
        columns=["row_key"], rows=[{"row_key": "report:1"}],
        sources=[Provenance(
            table="prd_process_report", record_key="1",
            ontology_iri="https://dierp.local/ontology/erp/v1#ScheduledOperation",
        )],
    )
    _validate_provenance(spec, good)

    bad = QueryResult(
        columns=["row_key"], rows=[{"row_key": "report:1"}],
        sources=[Provenance(
            table="mysql_user", record_key="1",
            ontology_iri="https://dierp.local/ontology/erp/v1#ScheduledOperation",
        )],
    )
    with pytest.raises(AIException) as exc:
        _validate_provenance(spec, bad)
    assert exc.value.code == "AI_PROVENANCE_INCOMPLETE"


def test_client_sql_constants_are_select_only():
    for sql in (
        mes_client._WORK_ORDER_SQL,
        mes_client._PROCESS_TASK_SQL,
        mes_client._PROCESS_REPORT_SQL,
    ):
        normalized = " ".join(sql.split())
        assert normalized.upper().startswith("SELECT ")
        assert ";" not in normalized
        assert not re.search(
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
            normalized,
            flags=re.IGNORECASE,
        )


# ── 本体形状：参数闸与结果行校验（形状唯一事实源在 ontology/src） ──


def _fetched_rows(monkeypatch) -> list[dict]:
    _install(monkeypatch, {
        "prd_work_order": [_order_row()],
        "prd_process_task": _tasks(),
        "prd_process_report": _reports(),
    })
    return [dict(row) for row in mes_client.fetch_work_order_progress(WORK_ORDER_NO).rows]


def test_realistic_fetch_rows_satisfy_mes_shapes(monkeypatch):
    rows = _fetched_rows(monkeypatch)
    assert len(rows) == 2  # 报工行 + 无报工的工序行
    assert validate_mes_result(rows) == []


def test_shape_rejects_missing_report_time_and_quantity(monkeypatch):
    rows = _fetched_rows(monkeypatch)
    report_row = next(row for row in rows if row["report_id"] == 111)
    report_row["report_time"] = None
    report_row["report_qualified_quantity"] = None
    paths = {item["path"] for item in validate_mes_result(rows)}
    assert {"mesReportTime", "mesReportQualifiedQuantity"} <= paths


def test_shape_rejects_unknown_status_and_bad_order_number(monkeypatch):
    rows = _fetched_rows(monkeypatch)
    rows[0]["task_status"] = "RUNNING"
    rows[0]["work_order_no"] = "WO-1"
    violations = validate_mes_result(rows)
    paths = {item["path"] for item in violations}
    assert {"mesTaskStatus", "mesWorkOrderNo"} <= paths
    assert all(item["component"] for item in violations)


def test_param_gate_uses_ontology_pattern_for_work_order_no():
    _, bound, status = _prepare_intent(
        mes_intent.SPEC, {"work_order_no": WORK_ORDER_NO}, "PLANNER"
    )
    assert bound["work_order_no"] == WORK_ORDER_NO
    assert status == "passed"

    with pytest.raises(AIException) as exc:
        _prepare_intent(mes_intent.SPEC, {"work_order_no": "GD-2026-1"}, "PLANNER")
    assert exc.value.code == "AI_PARAM_INVALID"
    assert exc.value.reject_reason == "SHACL"


def test_executor_rejects_rows_violating_mes_shapes(db, monkeypatch):
    bad_row = {column: None for column in mes_client.COLUMNS}
    bad_row.update({"work_order_no": WORK_ORDER_NO, "row_key": "work_order:1"})
    result = QueryResult(
        columns=list(mes_client.COLUMNS),
        rows=[bad_row],
        sources=[Provenance(
            table="prd_work_order", record_key="1",
            ontology_iri=NS + "ProductionOrder",
        )],
    )
    monkeypatch.setattr(mes_intent, "fetch_work_order_progress", lambda *a, **k: result)

    with pytest.raises(AIException) as exc:
        execute_intent(
            db, mes_intent.SPEC,
            mes_intent.MesWorkOrderProgressParams(work_order_no=WORK_ORDER_NO),
            role="PLANNER",
        )
    assert exc.value.code == "AI_EXECUTION_FAILED"
    assert exc.value.reject_reason == "SHACL"
