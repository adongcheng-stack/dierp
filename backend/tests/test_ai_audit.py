"""AI 审计（W0.6）：独立 session 持久化、拒绝态落库、原文关闭、JSON 往返。"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy.orm import sessionmaker

from backend.common.database.base import Base
from backend.common.models.ai import AiQueryLog
from backend.services.ai import audit as audit_mod
from backend.services.ai.audit import AI_QUERY_LOG_RETENTION_DAYS, write_ai_query_log
from backend.services.ai.config import AISettings, get_settings


@pytest.fixture()
def sessions(engine, monkeypatch):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(audit_mod, "SessionLocal", Session)
    return Session


def test_table_is_managed():
    assert "ai_query_logs" in Base.metadata.tables
    env_source = (PROJECT_ROOT / "backend/migrations/env.py").read_text(encoding="utf-8")
    legacy_block = env_source.split("LEGACY_UNMANAGED_TABLES", 1)[1].split("}", 1)[0]
    assert "ai_query_logs" not in legacy_block


def test_persists_in_independent_session(sessions):
    write_ai_query_log(
        trace_id="trace-persist-1",
        status="OK",
        request_id="req-1",
        username="planner",
        role="PLANNER",
        question="哪些销售订单延期？",
        intent_code="delayed_sales_orders",
        intent_json={"limit": 10},
        shacl_status="passed",
        latency_ms=12,
        row_count=3,
        provenance_json=[{"table": "sales_orders", "record_key": "SO-1"}],
    )
    with sessions() as fresh:
        row = fresh.query(AiQueryLog).filter_by(trace_id="trace-persist-1").one()
        assert row.status == "OK"
        assert row.username == "planner"
        assert row.question == "哪些销售订单延期？"
        assert row.question_sha256 == hashlib.sha256("哪些销售订单延期？".encode()).hexdigest()
        assert row.intent_json == {"limit": 10}
        assert row.provenance_json == [{"table": "sales_orders", "record_key": "SO-1"}]
        assert row.is_deleted is False


def test_rejections_are_persisted(sessions):
    cases = [
        ("trace-403", "REJECTED_PERMISSION", "AI_PERMISSION_DENIED"),
        ("trace-422", "REJECTED_PARAM", "AI_PARAM_INVALID"),
        ("trace-504", "REJECTED_TIMEOUT", "AI_EXECUTION_TIMEOUT"),
    ]
    for trace_id, status, code in cases:
        write_ai_query_log(
            trace_id=trace_id, status=status, error_code=code,
            reject_reason="x" * 400, question="q",
        )
    with sessions() as fresh:
        assert fresh.query(AiQueryLog).count() == 3
        timeout = fresh.query(AiQueryLog).filter_by(trace_id="trace-504").one()
        assert timeout.error_code == "AI_EXECUTION_TIMEOUT"
        assert len(timeout.reject_reason) == 300


def test_question_can_be_disabled(sessions, monkeypatch):
    monkeypatch.setenv("AI_LOG_QUESTION", "false")
    get_settings.cache_clear()
    try:
        write_ai_query_log(trace_id="trace-no-question", status="OK", question="毛利是多少")
    finally:
        get_settings.cache_clear()

    with sessions() as fresh:
        row = fresh.query(AiQueryLog).filter_by(trace_id="trace-no-question").one()
        assert row.question is None
        assert row.question_sha256 == hashlib.sha256("毛利是多少".encode()).hexdigest()


def test_retention_is_code_constant():
    assert AI_QUERY_LOG_RETENTION_DAYS == 90
    assert "ai_query_log_retention_days" not in AISettings.model_fields


def test_invalid_status_is_rejected():
    with pytest.raises(ValueError):
        write_ai_query_log(trace_id="trace-bad", status="NOT_A_STATUS")
