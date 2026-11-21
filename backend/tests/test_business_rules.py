"""业务规则 TODO 落地后的单元测试（信用额度 / 产能 / BOM 展开）。"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from backend.common.exceptions import ValidationException
from backend.common.models.eng import BOM, BOMItem, ProductionVersion
from backend.common.models.mm import Material
from backend.common.models.planning import ScheduleRun, ScheduledOperation, WorkCalendar
from backend.common.models.pp import WorkCenter
from backend.common.models.sd import Customer, SalesOrder, SalesOrderStatus
from backend.common.utils.business_rules import BusinessRulesValidator


def _material(db, code, stock=0, safety=0):
    db.add(Material(material_code=code, material_name=code, category="RAW",
                    unit="PCS", current_stock=stock, safety_stock=safety,
                    status="ACTIVE"))
    db.flush()


def _bom(db, number, parent, items):
    db.add(BOM(bom_number=number, version="A.0", parent_material_code=parent,
               effective_date=datetime(2026, 1, 1), base_quantity=1,
               status="NEW"))
    db.flush()
    for line, (code, qty, scrap) in enumerate(items, start=1):
        db.add(BOMItem(bom_number=number, line_number=line, material_code=code,
                       quantity=qty, unit="PCS", scrap_rate=scrap))
    db.flush()


# ── 1. 客户未完成订单总额 ────────────────────────────────────────────────

def test_outstanding_amount_counts_only_open_statuses(db):
    db.add(Customer(customer_id="C1", legal_name="客户一", credit_limit=1200))
    for no, amount, status in [
        ("SO-1", 200, SalesOrderStatus.APPROVED),
        ("SO-2", 300, SalesOrderStatus.IN_PRODUCTION),
        ("SO-3", 400, SalesOrderStatus.DELIVERED),
        ("SO-4", 500, SalesOrderStatus.CLOSED),
        ("SO-5", 600, SalesOrderStatus.CANCELLED),
    ]:
        db.add(SalesOrder(order_number=no, customer_id="C1", product_number="P",
                          quantity=1, unit_price=amount, total_amount=amount,
                          delivery_date=datetime(2026, 12, 1), status=status))
    db.flush()

    total = BusinessRulesValidator.calculate_outstanding_orders_amount("C1", db)
    assert total == Decimal("900")  # 200 + 300 + 400

    BusinessRulesValidator.validate_customer_credit("C1", Decimal("150"), db)  # 1050 <= 1200
    with pytest.raises(ValidationException) as exc:
        BusinessRulesValidator.validate_customer_credit("C1", Decimal("400"), db)  # 1300 > 1200
    assert exc.value.detail["error_code"] == "CUSTOMER_CREDIT_EXCEEDED"
    assert "未完成订单" in exc.value.detail["message"]


def test_credit_skipped_when_no_limit(db):
    db.add(Customer(customer_id="C2", legal_name="客户二"))
    db.flush()
    assert BusinessRulesValidator.validate_customer_credit("C2", Decimal("999999"), db) is True


# ── 2. 工作中心产能 ──────────────────────────────────────────────────────

def _work_center(db, code, with_calendar=True):
    db.add(WorkCenter(work_center_id=code, description=code,
                      work_center_type="MACHINE", plant_id="1000",
                      number_of_capacities=1))
    db.flush()
    if with_calendar:
        db.add(WorkCalendar(calendar_id=f"CAL-{code}", work_center_id=code,
                            shift_start="08:00", shift_end="18:00",
                            break_hours=1, utilization=100))
        db.flush()


def test_capacity_uses_calendar_and_scheduled_operations(db):
    _work_center(db, "W1")
    day = datetime(2026, 11, 21, 8, 0)
    db.add(ScheduleRun(run_number="RUN-1", horizon_start=day,
                       horizon_end=day + timedelta(days=1)))
    db.flush()
    db.add(ScheduledOperation(op_id="OP-1", run_number="RUN-1",
                              work_center_id="W1", planned_start=day,
                              planned_end=day + timedelta(hours=4),
                              setup_minutes=40, run_minutes=160,
                              status="PLANNED"))
    db.flush()

    # 日产能 = (10h - 1h) * 60 = 540 分钟；已占用 200 分钟
    assert BusinessRulesValidator.calculate_daily_capacity_minutes("W1", db) == Decimal("540")
    assert BusinessRulesValidator.calculate_occupied_capacity_minutes("W1", day, db) == Decimal("200")

    BusinessRulesValidator.validate_work_center_capacity("W1", Decimal("300"), day, db)  # 500 <= 540
    with pytest.raises(ValidationException) as exc:
        BusinessRulesValidator.validate_work_center_capacity("W1", Decimal("400"), day, db)  # 600 > 540
    assert exc.value.detail["error_code"] == "WC_CAPACITY_INSUFFICIENT"


def test_capacity_skipped_without_calendar(db):
    _work_center(db, "W2", with_calendar=False)
    assert BusinessRulesValidator.validate_work_center_capacity(
        "W2", Decimal("99999"), datetime(2026, 11, 21), db) is True


# ── 3. 多层级 BOM 展开与物料需求 ────────────────────────────────────────

def test_bom_explosion_applies_scrap_rate_and_validates_stock(db):
    for code, stock in [("FG", 0), ("A", 100), ("B", 5)]:
        _material(db, code, stock=stock)
    _bom(db, "BOM-FG", "FG", [("A", Decimal("2"), Decimal("10"))])
    _bom(db, "BOM-A", "A", [("B", Decimal("3"), Decimal("0"))])
    db.flush()

    req = BusinessRulesValidator.explode_bom_requirements("FG", Decimal("10"), db)
    assert req["A"] == Decimal("22.00")   # 2 * 1.1 * 10
    assert req["B"] == Decimal("66.00")   # 3 * 22

    # B 库存 5、安全库存 0，需求 66 → 校验失败
    with pytest.raises(ValidationException) as exc:
        BusinessRulesValidator.validate_production_order_materials(
            {"material_code": "FG", "quantity": 10}, db)
    assert exc.value.detail["error_code"] == "MATERIAL_STOCK_INSUFFICIENT"

    # 补足库存后展开校验应通过
    db.query(Material).filter(Material.material_code == "B").one().current_stock = 100
    db.flush()
    assert BusinessRulesValidator.validate_production_order_materials(
        {"material_code": "FG", "quantity": 10}, db) is True
