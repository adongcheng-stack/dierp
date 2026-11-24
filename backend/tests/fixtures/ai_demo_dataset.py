"""P1 最小演示数据集（计划 W1.6、设计附录 A）。

一次性写入 7 个意图各 ≥3 条正例，并显式包含边界样本：
1 个已关闭 NCR、1 个已解决 MRP 异常、1 个已收款发票、1 张无生产订单的销售订单。

所有单号/客户号以模块常量导出，测试不得硬编码示意值（评审 S12）。
``seed_ai_demo_dataset`` 只做插入，调用方负责 commit；同一引擎重复建库结果一致。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.common.models.mm import Material
from backend.common.models.planning import (
    ExceptionSeverity,
    InvoiceStatus,
    KitStatus,
    KittingResult,
    MrpException,
    MrpExceptionType,
    NcrSeverity,
    NcrStatus,
    NonConformanceReport,
    ReceivableEntry,
    ReceivableEntryType,
    ResolutionStatus,
    SalesInvoice,
)
from backend.common.models.pp import ProductionOrder
from backend.common.models.sd import Customer, SalesOrder, SalesOrderStatus

# ── 固定单号（测试唯一来源）────────────────────────────────
CUSTOMER_ID = "CUST001"
CUSTOMER_ZERO_LIMIT = "CUST002"
CUSTOMER_NO_ORDERS = "CUST003"
MISSING_CUSTOMER = "CUST404"

KIT_SOURCE_REF = "PO-20261101-0001"
KIT_UNKNOWN_SOURCE_REF = "PO-20990000-9999"

SO_LATE_FINISH = "SO-20261101-0001"
SO_NO_PRODUCTION = "SO-20261101-0002"
SO_SHIPPED = "SO-20261101-0003"
SO_OUTSIDE_WINDOW = "SO-20261101-0004"
SO_ON_TIME = "SO-20261101-0005"

INVOICE_PARTIAL = "INV-20261001-0001"
INVOICE_PARTIAL_SMALL = "INV-20261001-0002"
INVOICE_DRAFT = "INV-20261001-0003"
INVOICE_PAID = "INV-20261001-0004"
INVOICE_CANCELLED = "INV-20261001-0005"
INVOICE_NOT_DUE = "INV-20261001-0006"

MATERIAL_RAW = "M-RAW-001"
MATERIAL_SEMI = "M-SEMI-001"
MATERIAL_FG = "M-FG-001"

NCR_OPEN = "NCR-20261101-0001"
NCR_REVIEW = "NCR-20261101-0002"
NCR_DISPOSITIONED = "NCR-20261101-0003"
NCR_CLOSED = "NCR-20261101-0004"

# ── 期望值（取数口径的精确断言基准）──────────────────────
EXPECTED: dict[str, Any] = {
    "kitting_shortage": 12.0,          # KIT-20261101-0001 的 shortage_qty
    "kitting_rows": 3,
    "order_delay_rows": 2,             # 计划完工晚于交付日 + 无生产订单
    "material_rows": 3,
    "mrp_critical_open_rows": 2,
    "credit": {
        "credit_limit": 100000.0,
        "ar_balance": 600.0,           # 1000 - 400 + 50 - 50 + 0
        "open_order_amount": 3500.0,   # 1000 + 500 + 2000（SHIPPED 不计）
        "open_order_count": 3,
        "credit_usage_ratio": 0.041,
    },
    "overdue_rows": 2,
    "overdue_outstanding_total": 1000.0,   # 600 + 400
    "ncr_open_rows": 3,
    "ncr_critical_rows": 2,
}


def _material(code: str, name: str, material_type: str, stock: float, safety: float) -> Material:
    return Material(
        material_code=code, material_name=name, material_type=material_type,
        category="DEMO", unit="PCS", current_stock=stock, safety_stock=safety,
        status="ACTIVE",
    )


def _order(
    number: str, customer_id: str, material_code: str, quantity: float,
    unit_price: float, delivery: datetime, status: SalesOrderStatus,
) -> SalesOrder:
    return SalesOrder(
        order_number=number, customer_id=customer_id, product_number=material_code,
        material_code=material_code, quantity=quantity, unit_price=unit_price,
        total_amount=quantity * unit_price, currency="CNY", delivery_date=delivery,
        status=status,
    )


def seed_ai_demo_dataset(db: Session, now: datetime | None = None) -> dict[str, Any]:
    """写入演示数据集（不 commit，由调用方决定事务边界）。"""
    now = now or datetime.now()

    # 1) 客户
    db.add_all([
        Customer(customer_id=CUSTOMER_ID, legal_name="示例客户一", credit_limit=100000,
                 customer_status="ACTIVE"),
        Customer(customer_id=CUSTOMER_ZERO_LIMIT, legal_name="示例客户二", credit_limit=0,
                 customer_status="ACTIVE"),
        Customer(customer_id=CUSTOMER_NO_ORDERS, legal_name="示例客户三", credit_limit=50000,
                 customer_status="ACTIVE"),
    ])

    # 2) 物料（3 条低于安全库存 + 1 条正常）
    db.add_all([
        _material(MATERIAL_RAW, "示例原材料", "RAW", 10, 50),
        _material(MATERIAL_SEMI, "示例半成品", "SEMI", 0, 25),
        _material(MATERIAL_FG, "示例成品", "FG", 5, 15),
        _material("M-RAW-002", "库存充足原材料", "RAW", 30, 20),
    ])

    # 3) 齐套结果（3 条 SHORT + 1 条 FULL）
    db.add_all([
        KittingResult(
            result_number="KIT-20261101-0001", source_ref=KIT_SOURCE_REF,
            material_code=MATERIAL_RAW, kit_status=KitStatus.SHORT,
            required_qty=40, available_qty=0, shortage_qty=12,
            checked_at=now - timedelta(hours=1),
        ),
        KittingResult(
            result_number="KIT-20261101-0002", source_ref="PO-20261101-0002",
            material_code=MATERIAL_SEMI, kit_status=KitStatus.SHORT,
            required_qty=20, available_qty=15, shortage_qty=5,
            checked_at=now - timedelta(hours=2),
        ),
        KittingResult(
            result_number="KIT-20261101-0003", source_ref="PO-20261101-0003",
            material_code=MATERIAL_FG, kit_status=KitStatus.SHORT,
            required_qty=10, available_qty=7, shortage_qty=3,
            checked_at=now - timedelta(hours=3),
        ),
        KittingResult(
            result_number="KIT-20261101-0004", source_ref="PO-20261101-0004",
            material_code=MATERIAL_RAW, kit_status=KitStatus.FULL,
            required_qty=10, available_qty=10, shortage_qty=0,
            checked_at=now - timedelta(hours=4),
        ),
    ])

    # 4) 销售订单 + 生产订单
    db.add_all([
        _order(SO_LATE_FINISH, CUSTOMER_ID, MATERIAL_RAW, 10, 100,
               now + timedelta(days=3), SalesOrderStatus.APPROVED),
        _order(SO_NO_PRODUCTION, CUSTOMER_ID, MATERIAL_SEMI, 5, 100,
               now + timedelta(days=5), SalesOrderStatus.APPROVED),
        _order(SO_SHIPPED, CUSTOMER_ID, MATERIAL_FG, 3, 100,
               now + timedelta(days=2), SalesOrderStatus.SHIPPED),
        _order(SO_OUTSIDE_WINDOW, CUSTOMER_ID, MATERIAL_RAW, 20, 100,
               now + timedelta(days=20), SalesOrderStatus.APPROVED),
        _order(SO_ON_TIME, CUSTOMER_ZERO_LIMIT, MATERIAL_RAW, 7, 100,
               now + timedelta(days=4), SalesOrderStatus.APPROVED),
    ])
    db.add_all([
        ProductionOrder(
            order_number="PO-20261101-0010", sales_order_number=SO_LATE_FINISH,
            material_code=MATERIAL_RAW, quantity=10, unit="PCS",
            planned_start_date=now, planned_finish_date=now + timedelta(days=10),
            status="IN_PRODUCTION",
        ),
        ProductionOrder(
            order_number="PO-20261101-0011", sales_order_number=SO_ON_TIME,
            material_code=MATERIAL_RAW, quantity=7, unit="PCS",
            planned_start_date=now, planned_finish_date=now + timedelta(days=1),
            status="IN_PRODUCTION",
        ),
    ])

    # 5) 销售发票（2 条超期未收足 + DRAFT/PAID/CANCELLED/未到期 各 1 条）
    db.add_all([
        SalesInvoice(
            invoice_number=INVOICE_PARTIAL, sales_order_number=SO_LATE_FINISH,
            customer_id=CUSTOMER_ID, customer_name="示例客户一",
            amount=1000, status=InvoiceStatus.ISSUED,
            invoice_date=now - timedelta(days=60), due_date=now - timedelta(days=40),
            received_amount=400,
        ),
        SalesInvoice(
            invoice_number=INVOICE_PARTIAL_SMALL, sales_order_number=SO_LATE_FINISH,
            customer_id=CUSTOMER_ID, customer_name="示例客户一",
            amount=500, status=InvoiceStatus.PARTIALLY_PAID,
            invoice_date=now - timedelta(days=50), due_date=now - timedelta(days=35),
            received_amount=100,
        ),
        SalesInvoice(
            invoice_number=INVOICE_DRAFT, sales_order_number=SO_LATE_FINISH,
            customer_id=CUSTOMER_ID, amount=800, status=InvoiceStatus.DRAFT,
            due_date=now - timedelta(days=40), received_amount=0,
        ),
        SalesInvoice(
            invoice_number=INVOICE_PAID, sales_order_number=SO_LATE_FINISH,
            customer_id=CUSTOMER_ID, amount=300, status=InvoiceStatus.PAID,
            due_date=now - timedelta(days=40), received_amount=300,
        ),
        SalesInvoice(
            invoice_number=INVOICE_CANCELLED, sales_order_number=SO_LATE_FINISH,
            customer_id=CUSTOMER_ID, amount=200, status=InvoiceStatus.CANCELLED,
            due_date=now - timedelta(days=40), received_amount=0,
        ),
        SalesInvoice(
            invoice_number=INVOICE_NOT_DUE, sales_order_number=SO_LATE_FINISH,
            customer_id=CUSTOMER_ID, amount=700, status=InvoiceStatus.ISSUED,
            due_date=now - timedelta(days=5), received_amount=0,
        ),
    ])

    # 6) 应收流水（覆盖 5 个枚举值，带符号金额之和 = 600）
    db.add_all([
        ReceivableEntry(
            entry_number="AR-20261001-0001", invoice_number=INVOICE_PARTIAL,
            customer_id=CUSTOMER_ID, entry_type=ReceivableEntryType.INVOICE,
            amount=1000, entry_date=now - timedelta(days=60),
        ),
        ReceivableEntry(
            entry_number="AR-20261001-0002", invoice_number=INVOICE_PARTIAL,
            customer_id=CUSTOMER_ID, entry_type=ReceivableEntryType.RECEIPT,
            amount=-400, entry_date=now - timedelta(days=30),
        ),
        ReceivableEntry(
            entry_number="AR-20261001-0003", invoice_number=INVOICE_PARTIAL,
            customer_id=CUSTOMER_ID, entry_type=ReceivableEntryType.RECEIPT_REVERSE,
            amount=50, entry_date=now - timedelta(days=20),
        ),
        ReceivableEntry(
            entry_number="AR-20261001-0004", invoice_number=INVOICE_PARTIAL,
            customer_id=CUSTOMER_ID, entry_type=ReceivableEntryType.INVOICE_REVERSE,
            amount=-50, entry_date=now - timedelta(days=10),
        ),
        ReceivableEntry(
            entry_number="AR-20261001-0005", invoice_number=INVOICE_PARTIAL,
            customer_id=CUSTOMER_ID, entry_type=ReceivableEntryType.ADJUST,
            amount=0, entry_date=now - timedelta(days=5),
        ),
    ])

    # 7) MRP 异常（3 条 OPEN + 1 条 RESOLVED）
    db.add_all([
        MrpException(
            run_number="MRP-20261101-0001", exception_type=MrpExceptionType.SHORTAGE,
            severity=ExceptionSeverity.CRITICAL, material_code=MATERIAL_RAW,
            shortage_qty=100, resolution_status=ResolutionStatus.OPEN,
        ),
        MrpException(
            run_number=None, exception_type=MrpExceptionType.LATE,
            severity=ExceptionSeverity.CRITICAL, material_code=MATERIAL_SEMI,
            shortage_qty=50, resolution_status=ResolutionStatus.OPEN,
        ),
        MrpException(
            run_number="MRP-20261101-0001", exception_type=MrpExceptionType.SHORTAGE,
            severity=ExceptionSeverity.WARNING, material_code=MATERIAL_FG,
            shortage_qty=10, resolution_status=ResolutionStatus.OPEN,
        ),
        MrpException(
            run_number="MRP-20261101-0001", exception_type=MrpExceptionType.SHORTAGE,
            severity=ExceptionSeverity.CRITICAL, material_code=MATERIAL_RAW,
            shortage_qty=999, resolution_status=ResolutionStatus.RESOLVED,
        ),
    ])

    # 8) NCR（3 条未关闭 + 1 条 CLOSED）
    db.add_all([
        NonConformanceReport(
            ncr_number=NCR_OPEN, material_code=MATERIAL_RAW, quantity=2,
            severity=NcrSeverity.CRITICAL, status=NcrStatus.OPEN,
            source_type="INSPECTION",
        ),
        NonConformanceReport(
            ncr_number=NCR_REVIEW, material_code=MATERIAL_SEMI, quantity=1,
            severity=NcrSeverity.CRITICAL, status=NcrStatus.UNDER_REVIEW,
            source_type="INSPECTION",
        ),
        NonConformanceReport(
            ncr_number=NCR_DISPOSITIONED, material_code=MATERIAL_FG, quantity=3,
            severity=NcrSeverity.MAJOR, status=NcrStatus.DISPOSITIONED,
            source_type="INSPECTION",
        ),
        NonConformanceReport(
            ncr_number=NCR_CLOSED, material_code=MATERIAL_RAW, quantity=9,
            severity=NcrSeverity.CRITICAL, status=NcrStatus.CLOSED,
            source_type="INSPECTION",
        ),
    ])

    return EXPECTED
