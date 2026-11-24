"""W1.1 验收：意图注册表、角色白名单、取数口径与导出物（计划 W1.1）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))

from ai_demo_dataset import (  # noqa: E402
    CUSTOMER_ID,
    CUSTOMER_ZERO_LIMIT,
    EXPECTED,
    INVOICE_CANCELLED,
    INVOICE_DRAFT,
    INVOICE_PAID,
    INVOICE_PARTIAL,
    KIT_SOURCE_REF,
    KIT_UNKNOWN_SOURCE_REF,
    MATERIAL_RAW,
    MISSING_CUSTOMER,
    NCR_CLOSED,
    SO_LATE_FINISH,
    SO_NO_PRODUCTION,
    SO_ON_TIME,
    SO_OUTSIDE_WINDOW,
    SO_SHIPPED,
    seed_ai_demo_dataset,
)

from backend.common.database.base import Base  # noqa: E402
from backend.services.ai.catalog import get_catalog  # noqa: E402
from backend.services.ai.intent import BoundIntent  # noqa: E402
from backend.services.ai.intents import INTENT_REGISTRY  # noqa: E402
from backend.services.ai.intents import credit as credit_intent  # noqa: E402
from backend.services.ai.intents import inventory as inventory_intent  # noqa: E402
from backend.services.ai.intents import kitting as kitting_intent  # noqa: E402
from backend.services.ai.intents import orders as orders_intent  # noqa: E402
from backend.services.ai.intents import planning_exceptions as mrp_intent  # noqa: E402
from backend.services.ai.intents import quality as quality_intent  # noqa: E402
from backend.services.ai.intents import receivables as receivables_intent  # noqa: E402

_MODULES = (
    kitting_intent, inventory_intent, orders_intent, mrp_intent,
    credit_intent, receivables_intent, quality_intent,
)

EXPECTED_CODES = {
    "kitting_shortage", "material_below_safety", "order_delay_risk",
    "open_mrp_exceptions", "customer_credit_status", "ar_overdue",
    "open_nonconformance",
}

EXPECTED_DOWNLINKS = {
    "kitting_shortage": "/pp/kitting",
    "order_delay_risk": "/sd/sales-orders",
    "material_below_safety": "/mm/materials",
    "open_mrp_exceptions": None,
    "customer_credit_status": "/sd/customers",
    "ar_overdue": "/sd/invoices",
    "open_nonconformance": "/qms/ncrs",
}


@pytest.fixture()
def dataset(db):
    seed_ai_demo_dataset(db)
    db.commit()
    return db


def test_registry_has_exactly_seven_codes():
    assert set(INTENT_REGISTRY) == EXPECTED_CODES


def test_each_spec_declares_complete_contract():
    catalog = get_catalog()
    for code, spec in INTENT_REGISTRY.items():
        assert issubclass(spec.params_model, BoundIntent), code
        assert spec.params_model.model_config.get("extra") == "forbid", code
        assert spec.read_only is True, code
        assert spec.primary_entity in spec.entities, code
        assert spec.primary_entity in catalog.entities, code
        table = catalog.entities[spec.primary_entity].table
        columns = {c.name for c in Base.metadata.tables[table].columns}
        for key in spec.record_key:
            assert key in columns, f"{code}: record_key {key} 不是 {table} 的真实列"
        assert spec.downlink == EXPECTED_DOWNLINKS[code], code
        assert spec.allowed_roles, code
        assert spec.output_fields, code
        assert spec.shacl_coverage in {"full", "partial", "none"}, code


def test_shacl_coverage_distribution_is_truthful():
    coverage = [spec.shacl_coverage for spec in INTENT_REGISTRY.values()]
    assert coverage.count("full") == 3
    assert coverage.count("partial") == 2
    assert coverage.count("none") == 2


def test_handlers_use_orm_only_and_force_limit():
    for module in _MODULES:
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "db.execute(" not in source, module.__name__
        assert "text(" not in source, module.__name__
        assert 'f"SELECT' not in source and 'f"select' not in source, module.__name__
        assert ".limit(" in source, module.__name__


def test_kitting_shortage_caliber(dataset):
    result = kitting_intent.run(
        dataset, kitting_intent.KittingShortageParams(), "PLANNER"
    )
    assert len(result.rows) == EXPECTED["kitting_rows"]
    assert all(row["kit_status"] == "SHORT" for row in result.rows)
    raw = next(row for row in result.rows if row["material_code"] == MATERIAL_RAW)
    assert raw["shortage_qty"] == EXPECTED["kitting_shortage"]
    assert len(result.sources) == len(result.rows)

    filtered = kitting_intent.run(
        dataset, kitting_intent.KittingShortageParams(source_ref=KIT_SOURCE_REF), "PLANNER"
    )
    assert [row["result_number"] for row in filtered.rows] == ["KIT-20261101-0001"]

    empty = kitting_intent.run(
        dataset,
        kitting_intent.KittingShortageParams(source_ref=KIT_UNKNOWN_SOURCE_REF),
        "PLANNER",
    )
    assert empty.rows == [] and empty.sources == []


def test_order_delay_risk_caliber(dataset):
    result = orders_intent.run(
        dataset, orders_intent.OrderDelayRiskParams(), "SALES"
    )
    numbers = [row["order_number"] for row in result.rows]
    assert len(result.rows) == EXPECTED["order_delay_rows"]
    assert SO_SHIPPED not in numbers
    assert SO_ON_TIME not in numbers
    assert SO_OUTSIDE_WINDOW not in numbers
    reasons = {row["order_number"]: row["risk_reason"] for row in result.rows}
    assert reasons[SO_LATE_FINISH] == "计划完工晚于交付日"
    assert reasons[SO_NO_PRODUCTION] == "无生产订单"
    assert all("amount" not in row and "unit_price" not in row for row in result.rows)

    empty = orders_intent.run(
        dataset, orders_intent.OrderDelayRiskParams(customer_id="CUST404"), "SALES"
    )
    assert empty.rows == []


def test_material_below_safety_caliber(dataset):
    result = inventory_intent.run(
        dataset, inventory_intent.MaterialBelowSafetyParams(), "WAREHOUSE"
    )
    assert len(result.rows) == EXPECTED["material_rows"]
    raw = next(row for row in result.rows if row["material_code"] == MATERIAL_RAW)
    assert raw["shortage"] == 40.0        # 50 - 10
    assert raw["current_stock"] < raw["safety_stock"]

    raw_only = inventory_intent.run(
        dataset, inventory_intent.MaterialBelowSafetyParams(material_type="RAW"), "WAREHOUSE"
    )
    assert [row["material_code"] for row in raw_only.rows] == [MATERIAL_RAW]

    empty = inventory_intent.run(
        dataset,
        inventory_intent.MaterialBelowSafetyParams(material_type="PACKAGING"),
        "WAREHOUSE",
    )
    assert empty.rows == []


def test_open_mrp_exceptions_caliber(dataset):
    result = mrp_intent.run(
        dataset, mrp_intent.OpenMrpExceptionsParams(), "PLANNER"
    )
    assert len(result.rows) == 3
    assert all(row["resolution_status"] == "OPEN" for row in result.rows)
    assert all(row["shortage_qty"] != 999 for row in result.rows)   # RESOLVED 被排除

    critical = mrp_intent.run(
        dataset, mrp_intent.OpenMrpExceptionsParams(severity="CRITICAL"), "PLANNER"
    )
    assert len(critical.rows) == EXPECTED["mrp_critical_open_rows"]
    # run_number 可为空，溯源必须回落到主键 id
    nullable = [row for row in critical.rows if row["run_number"] is None]
    assert nullable and all(row["id"] for row in nullable)

    empty = mrp_intent.run(
        dataset, mrp_intent.OpenMrpExceptionsParams(severity="INFO"), "PLANNER"
    )
    assert empty.rows == []


def test_customer_credit_status_caliber(dataset):
    result = credit_intent.run(
        dataset, credit_intent.CustomerCreditStatusParams(customer_id=CUSTOMER_ID), "FINANCE"
    )
    assert len(result.rows) == 1
    row = result.rows[0]
    expected = EXPECTED["credit"]
    assert row["credit_limit"] == pytest.approx(expected["credit_limit"])
    assert row["ar_balance"] == pytest.approx(expected["ar_balance"])
    assert row["open_order_amount"] == pytest.approx(expected["open_order_amount"])
    assert row["open_order_count"] == expected["open_order_count"]
    assert row["credit_usage_ratio"] == pytest.approx(expected["credit_usage_ratio"])

    zero = credit_intent.run(
        dataset,
        credit_intent.CustomerCreditStatusParams(customer_id=CUSTOMER_ZERO_LIMIT),
        "FINANCE",
    )
    assert zero.rows[0]["credit_usage_ratio"] is None

    missing = credit_intent.run(
        dataset,
        credit_intent.CustomerCreditStatusParams(customer_id=MISSING_CUSTOMER),
        "FINANCE",
    )
    assert missing.rows == [] and missing.reason == "customer_not_found"


def test_ar_overdue_caliber(dataset):
    result = receivables_intent.run(
        dataset, receivables_intent.ArOverdueParams(), "FINANCE"
    )
    assert len(result.rows) == EXPECTED["overdue_rows"]
    assert sum(row["outstanding"] for row in result.rows) == pytest.approx(
        EXPECTED["overdue_outstanding_total"]
    )
    numbers = {row["invoice_number"] for row in result.rows}
    assert numbers == {INVOICE_PARTIAL, "INV-20261001-0002"}
    assert not numbers & {INVOICE_DRAFT, INVOICE_PAID, INVOICE_CANCELLED}
    assert all(row["days_overdue"] > 30 for row in result.rows)

    single = receivables_intent.run(
        dataset, receivables_intent.ArOverdueParams(invoice_number=INVOICE_PARTIAL), "FINANCE"
    )
    assert len(single.rows) == 1

    empty = receivables_intent.run(
        dataset,
        receivables_intent.ArOverdueParams(customer_id=CUSTOMER_ZERO_LIMIT),
        "FINANCE",
    )
    assert empty.rows == []


def test_open_nonconformance_caliber(dataset):
    result = quality_intent.run(
        dataset, quality_intent.OpenNonConformanceParams(), "ENGINEER"
    )
    assert len(result.rows) == EXPECTED["ncr_open_rows"]
    assert NCR_CLOSED not in {row["ncr_number"] for row in result.rows}

    critical = quality_intent.run(
        dataset, quality_intent.OpenNonConformanceParams(severity="CRITICAL"), "ENGINEER"
    )
    assert len(critical.rows) == EXPECTED["ncr_critical_rows"]

    empty = quality_intent.run(
        dataset, quality_intent.OpenNonConformanceParams(severity="MINOR"), "ENGINEER"
    )
    assert empty.rows == []


def test_money_columns_trimmed_for_non_finance_roles():
    for code in ("customer_credit_status", "ar_overdue"):
        spec = INTENT_REGISTRY[code]
        default_fields = set(spec.output_fields["*"])
        assert not default_fields & {
            "credit_limit", "ar_balance", "open_order_amount",
            "amount", "received_amount", "outstanding", "credit_usage_ratio",
        }, code
        finance_fields = set(spec.output_fields["FINANCE"])
        assert finance_fields - default_fields, code


def test_export_artifact_matches_registry():
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "backend" / "scripts" / "export_ai_intent_meta.py"), "--check"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    document = json.loads(
        (PROJECT_ROOT / "frontend" / "src" / "mock" / "ai-intents.json").read_text(encoding="utf-8")
    )
    items = {item["code"]: item for item in document["intents"]}
    assert set(items) == EXPECTED_CODES
    for code, spec in INTENT_REGISTRY.items():
        item = items[code]
        assert set(item["roles"]) == set(spec.allowed_roles), code
        assert item["record_key"] == list(spec.record_key), code
        assert item["downlink"] == spec.downlink, code
