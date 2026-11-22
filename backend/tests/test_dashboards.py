"""驾驶舱接口与本体预警规则测试（SQLite 内存库隔离）。"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.common.database.base import get_db
from backend.services.dashboard.alerts import build_alerts, seed_dashboard_rules
from backend.common.models.dashboard import AlertLevel, AlertOperator, DashboardRule, DashboardScope
from backend.services.finance.finance_seed import seed_finance_demo

PATHS = [
    "/api/dashboard/home",
    "/api/dashboard/production",
    "/api/dashboard/production-progress",
    "/api/dashboard/finance",
    "/api/dashboard/sales",
]


@pytest.fixture()
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    seed = Session()
    seed_dashboard_rules(seed)
    seed.commit()
    seed.close()

    def _override():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize("path", PATHS)
def test_dashboard_endpoints_anonymous_ok(client, path):
    """dashboard 域本体声明匿名可读，所有驾驶舱 GET 应返回 200。"""
    resp = client.get(path)
    assert resp.status_code == 200, (path, resp.text[:200])
    assert "generated_at" in resp.json()


def test_home_contains_cockpit_catalog(client):
    data = client.get("/api/dashboard/home").json()
    assert len(data["cockpits"]) == 5
    assert len(data["workbenches"]) == 5
    assert any(c["key"] == "progress" for c in data["cockpits"])
    assert "summary" in data


def test_window_param_is_echoed(client):
    resp = client.get("/api/dashboard/production?window=LAST90")
    assert resp.status_code == 200
    assert resp.json()["window"] == "LAST90"


def test_production_progress_shape(client):
    data = client.get("/api/dashboard/production-progress").json()
    assert "summary" in data and "rows" in data
    assert "operations" in data["summary"]


def test_alert_rule_evaluation(client):
    """本体阈值规则触发：OEE 0.5 < 0.7 应产生 WARNING。"""
    Session = sessionmaker(bind=next(client.app.dependency_overrides[get_db]()).get_bind())
    db = Session()
    try:
        db.add(DashboardRule(
            code="R-TEST-OEE", name="测试OEE", scope=DashboardScope.PRODUCTION,
            metric="equipment.oee", operator=AlertOperator.LT,
            threshold=0.7, level=AlertLevel.WARNING,
            message="OEE {value:.0%} 偏低", default_window="ALL", enabled=True,
        ))
        db.commit()
        alerts = build_alerts(db, "PRODUCTION", {"equipment": {"oee": 0.5}})
        codes = [a["code"] for a in alerts]
        assert "R-TEST-OEE" in codes
        assert "R-HOME-OEE" in codes  # HOME 规则始终生效
        alert = next(a for a in alerts if a["code"] == "R-TEST-OEE")
        assert alert["level"] == "WARNING"
        assert "偏低" in alert["message"]
    finally:
        db.close()


def test_finance_seed_builds_cross_month_vouchers(db):
    """财务种子：发票/收付款/核销/跨月凭证一次成型，且重复调用幂等。"""
    from datetime import datetime

    from backend.api.routers.dashboard import _finance_kpi
    from backend.common.models.planning import (
        Account,
        JournalEntry,
        PurchaseOrder,
        Receipt,
        SalesInvoice,
        SupplierInvoice,
        SupplierPayment,
    )
    from backend.common.models.sd import SalesOrder
    from backend.services.finance.gl_rules import GL_ACCOUNTS

    for code, name, account_type in GL_ACCOUNTS:
        db.add(Account(account_code=code, account_name=name, account_type=account_type, is_leaf=True))
    order_customers = [
        ("SO-20251231-0001", "FJ002"),
        ("SO-20251230-0001", "FJ002"),
        ("SO-20251216-0001", "FJ001"),
        ("SO-20251218-0001", "FJ001"),
        ("SO-20251230-0002", "FJ002"),
    ]
    for number, customer_id in order_customers:
        db.add(SalesOrder(
            order_number=number, customer_id=customer_id, product_number="P",
            quantity=1, unit_price=1, total_amount=1, delivery_date=datetime.now(),
        ))
    for index in range(2):
        db.add(PurchaseOrder(
            purchase_order_number=f"PUR-TEST-{index + 1}",
            supplier_id="SUP-TEST", supplier_name="测试供应商", total_amount=20000,
        ))
    db.flush()

    assert seed_finance_demo(db) > 0
    db.flush()

    assert db.query(SalesInvoice).count() == 6
    assert db.query(Receipt).count() == 5
    assert db.query(SupplierInvoice).count() == 2
    assert db.query(SupplierPayment).count() == 2
    entries = db.query(JournalEntry).all()
    assert len(entries) == 15
    assert len({entry.period_code for entry in entries}) >= 5

    finance = _finance_kpi(db)
    assert finance["collection_rate"] > 0
    assert finance["receivable_outstanding"] > 0
    assert finance["payable_open"] > 0
    assert finance["cash_balance"] > 0

    # 幂等：再次调用不重复入账
    assert seed_finance_demo(db) == 0
    assert db.query(JournalEntry).count() == 15
