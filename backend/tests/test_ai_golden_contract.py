"""契约快照校验：18 条验收问题与前端 mock 共用同一份 golden 文件。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy.orm import sessionmaker

from backend.services.ai import audit as audit_mod
from backend.services.ai import pipeline as pipeline_mod
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.intent import Provenance, QueryResult
from backend.services.ai.intents import mes as mes_mod
from backend.services.ai.mes_client import COLUMNS
from backend.services.ai.ontology_service import NS
from backend.services.ai.ratelimit import get_rate_limiter

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from ai_demo_dataset import seed_ai_demo_dataset  # noqa: E402

GOLDEN_FILE = PROJECT_ROOT / "frontend" / "mock-tests" / "ai-golden.json"

ROLES = {
    "PLANNER": SimpleNamespace(username="golden_planner", role="PLANNER"),
    "SALES_MANAGER": SimpleNamespace(username="golden_sales", role="SALES_MANAGER"),
    "WAREHOUSE": SimpleNamespace(username="golden_warehouse", role="WAREHOUSE"),
    "FINANCE": SimpleNamespace(username="golden_finance", role="FINANCE"),
    "ENGINEER": SimpleNamespace(username="golden_engineer", role="ENGINEER"),
    "ADMIN": SimpleNamespace(username="golden_admin", role="ADMIN"),
}


@pytest.fixture(autouse=True)
def _fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_limiter():
    get_rate_limiter().reset()
    yield
    get_rate_limiter().reset()


@pytest.fixture()
def sessions(engine, monkeypatch):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(audit_mod, "SessionLocal", Session)
    return Session


@pytest.fixture()
def dataset(db):
    seed_ai_demo_dataset(db)
    db.commit()
    return db


def _mes_row(**overrides):
    row = {column: None for column in COLUMNS}
    row.update(overrides)
    return row


def _stub_mes_progress(work_order_no, *, limit=None, settings=None):
    """golden 用桩：不触达真实 MES，只验证意图/参数/列/状态契约。"""
    settings = settings or get_settings()
    if not settings.mes_ready:
        raise AIException("AI_MES_UNAVAILABLE")
    if work_order_no != "GD-20260914-00001":
        return QueryResult(
            columns=list(COLUMNS), rows=[], sources=[], reason="work_order_not_found",
        )
    rows = [
        _mes_row(
            work_order_no=work_order_no, product_name="测试产品",
            order_status="IN_PRODUCTION", order_quantity=100.0,
            order_completed_quantity=40.0, order_qualified_quantity=40.0,
            order_scrapped_quantity=0.0,
            planned_start_date="2026-09-14 08:00:00",
            planned_end_date="2026-09-20 18:00:00",
            process_task_id=11,
            process_name="SMT", task_sequence=1, task_status="COMPLETED",
            task_completed_quantity=40.0, task_qualified_quantity=40.0,
            task_scrapped_quantity=0.0,
            report_id=111, report_time="2026-09-14 11:30:00",
            report_completed_quantity=40.0, report_qualified_quantity=40.0,
            report_scrapped_quantity=0.0,
            row_key="report:111",
        ),
        _mes_row(
            work_order_no=work_order_no, product_name="测试产品",
            order_status="IN_PRODUCTION", order_quantity=100.0,
            order_completed_quantity=40.0, order_qualified_quantity=40.0,
            order_scrapped_quantity=0.0,
            planned_start_date="2026-09-14 08:00:00",
            planned_end_date="2026-09-20 18:00:00",
            process_task_id=12,
            process_name="组装", task_sequence=2, task_status="PENDING",
            task_completed_quantity=0.0, task_qualified_quantity=0.0,
            task_scrapped_quantity=0.0,
            row_key="task:12",
        ),
    ]
    sources = [
        Provenance(
            table="prd_process_report", record_key="111",
            ontology_iri=NS + "ScheduledOperation",
        ),
        Provenance(
            table="prd_process_task", record_key="12",
            ontology_iri=NS + "ScheduledOperation",
        ),
    ]
    return QueryResult(columns=list(COLUMNS), rows=rows, sources=sources)


def _apply_mes_switch(case: dict, monkeypatch) -> None:
    if case.get("mes_enabled"):
        monkeypatch.setenv("MES_QUERY_ENABLED", "true")
        monkeypatch.setenv("MES_DB_USER", "golden-mes")
        monkeypatch.setenv("MES_DB_PASSWORD", "golden-mes-secret")
        monkeypatch.setattr(mes_mod, "fetch_work_order_progress", _stub_mes_progress)
    else:
        monkeypatch.delenv("MES_QUERY_ENABLED", raising=False)
        monkeypatch.delenv("MES_DB_USER", raising=False)
        monkeypatch.delenv("MES_DB_PASSWORD", raising=False)
    get_settings.cache_clear()


def test_golden_contract_case_ids_are_complete():
    cases = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))["cases"]
    assert [case["id"] for case in cases] == [f"A{index}" for index in range(1, 19)]


def test_backend_matches_shared_golden_contract(dataset, sessions, monkeypatch):
    cases = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        _apply_mes_switch(case, monkeypatch)
        user = ROLES[case["role"]]
        try:
            response = pipeline_mod.ask(case["question"], user, dataset)
            actual = {
                "intent": response["intent"]["code"],
                "params": response["intent"]["params"],
                "columns": response["data"]["columns"],
                "status": 200,
            }
        except AIException as exc:
            actual = {"intent": None, "params": {}, "columns": [], "status": exc.http_status}
        assert actual == case["expected"], f"{case['id']} 契约漂移: {actual}"
