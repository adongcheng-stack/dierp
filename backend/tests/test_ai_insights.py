"""W1.5 A4 异常解读验收：结构、证据、权限裁剪、只读与 LLM 降级。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.api.routers.auth import pwd_context
from backend.common.database.base import get_db
from backend.common.models.ai import AiQueryLog
from backend.common.models.mm import Material
from backend.common.models.planning import (
    ExceptionSeverity,
    KittingResult,
    MrpException,
    MrpExceptionType,
    NonConformanceReport,
    ResolutionStatus,
    SalesInvoice,
)
from backend.common.models.sd import SalesOrder, SalesOrderStatus
from backend.common.models.user import User, UserRole
from backend.services.ai import insights as insights_mod
from backend.services.ai.config import get_settings
from backend.services.ai.insights import build_dashboard_insights
from backend.services.ai.llm import LLMError
from backend.services.dashboard.alerts import seed_dashboard_rules

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from ai_demo_dataset import seed_ai_demo_dataset  # noqa: E402

PASSWORD = "admin123"

BUSINESS_TABLES = (
    KittingResult, Material, SalesOrder, SalesInvoice, MrpException, NonConformanceReport,
)


@pytest.fixture(autouse=True)
def _fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(session_factory, monkeypatch):
    Session = session_factory
    seed = Session()
    password_hash = pwd_context.hash(PASSWORD)
    for role in UserRole:
        seed.add(
            User(
                username=f"ai_{role.value.lower()}",
                email=f"ai_{role.value.lower()}@ut.local",
                full_name=role.value,
                password_hash=password_hash,
                role=role,
                department="UT",
                is_active=True,
            )
        )
    seed.commit()
    seed.close()

    def _override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def ai_dataset(session_factory):
    session = session_factory()
    try:
        seed_ai_demo_dataset(session)
        session.commit()
    finally:
        session.close()


def _login(client: TestClient, username: str) -> str:
    resp = client.post("/api/auth/login", data={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text[:200]
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── 结构与证据 ─────────────────────────────────────────────


def test_empty_database_returns_no_alerts(client):
    token = _login(client, "ai_planner")
    resp = client.get("/api/ai/insights/dashboard", headers=_auth(token))
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["window"] == "7d"
    assert body["alerts"] == []
    assert "placeholder" not in body
    assert "未发现" in body["narrative"]
    assert body["narration_source"] == "template"
    assert body["model"] == "deterministic-v1"


def test_alerts_have_metric_threshold_and_evidence(client, ai_dataset):
    token = _login(client, "ai_planner")
    resp = client.get("/api/ai/insights/dashboard?window=7d", headers=_auth(token))
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()

    assert body["alerts"], body
    for alert in body["alerts"]:
        assert alert["metric"]
        assert alert["threshold"] is not None
        assert alert["evidence"], alert["code"]
        assert alert["drilldown"]
        for item in alert["evidence"]:
            assert item["table"] and item["record_ref"]
        assert alert["evidence_total"] >= len(alert["evidence"])
    assert body["summary"]["total"] == len(body["alerts"])
    # 演示数据有 3 条 OPEN MRP 异常
    assert any(item["scope"] == "PLANNING" for item in body["alerts"])


def test_mrp_alerts_follow_intent_role_whitelist(client, ai_dataset):
    planner = client.get(
        "/api/ai/insights/dashboard", headers=_auth(_login(client, "ai_planner"))
    ).json()
    sales = client.get(
        "/api/ai/insights/dashboard", headers=_auth(_login(client, "ai_sales_manager"))
    ).json()
    assert any(item["scope"] == "PLANNING" for item in planner["alerts"])
    assert not any(item["scope"] == "PLANNING" for item in sales["alerts"])


# ── 金额裁剪 ───────────────────────────────────────────────


def _seed_small_open_order(db):
    seed_dashboard_rules(db)
    db.add(
        SalesOrder(
            order_number="SO-LOW-AMOUNT",
            customer_id="CUST001",
            product_number="M-RAW-001",
            material_code="M-RAW-001",
            quantity=1,
            unit_price=500,
            total_amount=500,
            currency="CNY",
            delivery_date=datetime.now() + timedelta(days=3),
            status=SalesOrderStatus.APPROVED,
        )
    )
    db.commit()


def test_amount_fields_are_masked_for_non_finance_roles(db):
    _seed_small_open_order(db)

    masked = build_dashboard_insights(db, "7d", "SALES_MANAGER")
    amount_alert = next(
        item for item in masked["alerts"] if item["metric"] == "sales.amount_open"
    )
    assert amount_alert["amount_masked"] is True
    assert amount_alert["current_value"] is None
    assert amount_alert["threshold"] is None
    assert amount_alert["deviation"] is None
    assert "500" not in amount_alert["suggestion"]

    visible = build_dashboard_insights(db, "7d", "FINANCE")
    visible_alert = next(
        item for item in visible["alerts"] if item["metric"] == "sales.amount_open"
    )
    assert visible_alert["amount_masked"] is False
    assert visible_alert["current_value"] == 500.0
    assert visible_alert["threshold"] == 1000.0


# ── 窗口与错误映射 ─────────────────────────────────────────


def test_window_filters_mrp_exceptions(db):
    old = MrpException(
        run_number="MRP-WINDOW-0001",
        exception_type=MrpExceptionType.SHORTAGE,
        severity=ExceptionSeverity.WARNING,
        material_code="M-RAW-001",
        shortage_qty=5,
        shortage_date=datetime.now() - timedelta(days=20),
        resolution_status=ResolutionStatus.OPEN,
    )
    db.add(old)
    db.commit()
    code = f"MRP-{old.id}"

    short = build_dashboard_insights(db, "7d", "PLANNER")
    long = build_dashboard_insights(db, "30d", "PLANNER")
    assert code not in {item["code"] for item in short["alerts"]}
    assert code in {item["code"] for item in long["alerts"]}


def test_invalid_window_and_chatbi_disabled(client, monkeypatch):
    token = _login(client, "ai_planner")
    invalid = client.get(
        "/api/ai/insights/dashboard?window=1d", headers=_auth(token)
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "AI_PARAM_INVALID"

    monkeypatch.setenv("AI_CHATBI_ENABLED", "false")
    get_settings.cache_clear()
    disabled = client.get("/api/ai/insights/dashboard", headers=_auth(token))
    assert disabled.status_code == 503
    assert disabled.json()["detail"]["code"] == "AI_CHATBI_DISABLED"


def test_insights_is_read_only(client, ai_dataset, session_factory):
    token = _login(client, "ai_planner")
    session = session_factory()
    try:
        before = {
            model.__tablename__: session.query(model).count() for model in BUSINESS_TABLES
        }
        logs_before = session.query(AiQueryLog).count()
    finally:
        session.close()

    resp = client.get("/api/ai/insights/dashboard", headers=_auth(token))
    assert resp.status_code == 200, resp.text[:300]

    session = session_factory()
    try:
        after = {
            model.__tablename__: session.query(model).count() for model in BUSINESS_TABLES
        }
        logs_after = session.query(AiQueryLog).count()
    finally:
        session.close()
    assert after == before
    assert logs_after == logs_before


def test_narrative_uses_ontology_enum_labels(client, ai_dataset):
    """枚举码不得进入叙述与告警文案；标签必须来自本体 labels。"""
    token = _login(client, "ai_planner")
    resp = client.get("/api/ai/insights/dashboard", headers=_auth(token))
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()

    mrp = [alert for alert in body["alerts"] if alert["scope"] == "PLANNING"]
    assert mrp
    type_codes = (
        "SHORTAGE", "EXCESS", "LATE", "EARLY",
        "NO_BOM", "NO_POLICY", "LEAD_TIME_VIOLATION", "CAPACITY_OVERLOAD",
    )
    for alert in mrp:
        for code in type_codes:
            assert code not in alert["title"]
            assert code not in (alert["attribution"] or "")

    narrative = body["narrative"]
    for code in type_codes + ("CRITICAL", "WARNING", "INFO"):
        assert code not in narrative
    labels = ("物料短缺", "物料过剩", "交期延迟", "交期提前", "缺少物料清单",
              "缺少计划策略", "提前期违约", "产能超载")
    assert any(label in narrative for label in labels)


# ── LLM 润色与降级 ─────────────────────────────────────────


class StubClient:
    last_model = "stub-model"

    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[dict] = []

    def complete(self, payload: dict, *, response_format: str | None = None) -> str:
        self.calls.append(payload)
        if self.error is not None:
            raise self.error
        return self.text or ""


def _enable_llm(monkeypatch, stub: StubClient) -> None:
    monkeypatch.setenv("AI_LLM_ENABLED", "true")
    monkeypatch.setenv("AI_LLM_NARRATION_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(insights_mod, "get_llm_client", lambda: stub)


def _dataset(db):
    seed_ai_demo_dataset(db)
    db.commit()


def test_llm_narration_is_used_only_when_numbers_match(db, monkeypatch):
    _dataset(db)
    stub = StubClient(text="近 7 天共发现异常，建议优先处理严重项。")
    _enable_llm(monkeypatch, stub)

    result = build_dashboard_insights(db, "7d", "PLANNER")
    assert result["narration_source"] == "llm"
    assert result["model"] == "stub-model"
    assert result["narrative"].startswith("近 7 天")

    payload = stub.calls[0]
    assert payload["task"] == "insight_narration"
    assert "draft" not in payload
    assert all(item["attribution"] is None for item in payload["alerts"])
    assert "M-RAW-001" not in json.dumps(payload, ensure_ascii=False)


def test_llm_invented_number_falls_back_to_template(db, monkeypatch):
    _dataset(db)
    _enable_llm(monkeypatch, StubClient(text="共 424242 项异常，请立即处理。"))

    result = build_dashboard_insights(db, "7d", "PLANNER")
    assert result["narration_source"] == "template"
    assert "424242" not in result["narrative"]
    assert result["narrative"]


def test_llm_failure_degrades_to_template(db, monkeypatch):
    _dataset(db)
    _enable_llm(monkeypatch, StubClient(error=LLMError("429 quota exhausted")))

    result = build_dashboard_insights(db, "7d", "PLANNER")
    assert result["narration_source"] == "template"
    assert result["model"] == "deterministic-v1"
    assert result["alerts"]
