"""财务演示闭环种子：发票 → 收付款 → 核销 → 总账凭证。

与 seed_sales_delivery_demo 等基础种子不同，本模块补齐「资金域 + 总账」
的跨月演示数据，让财务驾驶舱的应收/应付/回款率/现金流四卡与凭证趋势图
都有真实口径的数据可展示。

设计约定：
- 幂等：以固定单据号判重，重复调用不会重复入账（GlEngine.post 自身也幂等）。
- 跨月：凭证按业务日期入账（GlEngine.post 的 entry_date），自动补建会计期间。
- 口径：发票状态/已收金额与核销明细同步，保证 receivable/collection_rate 自洽。
- 由 reset_planning_demo 在清空运行时数据后调用，不触碰核心主数据。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.common.models.planning import (
    InvoiceStatus,
    PaymentAllocation,
    PaymentMethod,
    Receipt,
    ReceiptAllocation,
    ReceivableEntry,
    ReceivableEntryType,
    SalesInvoice,
    SupplierInvoice,
    SupplierInvoiceStatus,
    SupplierPayment,
)
from backend.common.models.sd import SalesOrder


# 销售发票：(单号, 业务日期, 金额, 客户ID, 来源销售订单, 状态, 已收金额)
SALES_INVOICES: list[tuple[str, str, str, str, str, InvoiceStatus, str]] = [
    ("INV-DEMO-202606-0001", "2026-06-15", "18000", "FJ002", "SO-20251231-0001", InvoiceStatus.PAID, "18000"),
    ("INV-DEMO-202607-0001", "2026-07-12", "24500", "FJ002", "SO-20251230-0001", InvoiceStatus.PARTIALLY_PAID, "20000"),
    ("INV-DEMO-202608-0001", "2026-08-18", "12600", "FJ001", "SO-20251216-0001", InvoiceStatus.PAID, "12600"),
    ("INV-DEMO-202609-0001", "2026-09-20", "30000", "FJ002", "SO-20251231-0001", InvoiceStatus.PARTIALLY_PAID, "25000"),
    ("INV-DEMO-202610-0001", "2026-10-16", "16800", "FJ001", "SO-20251218-0001", InvoiceStatus.PAID, "16800"),
    ("INV-DEMO-202611-0001", "2026-11-10", "21000", "FJ002", "SO-20251230-0002", InvoiceStatus.ISSUED, "0"),
]

# 收款单：(单号, 业务日期, 金额, 客户ID, 核销的发票号, 核销金额)
RECEIPTS: list[tuple[str, str, str, str, str, str]] = [
    ("RC-DEMO-202607-0001", "2026-07-20", "18000", "FJ002", "INV-DEMO-202606-0001", "18000"),
    ("RC-DEMO-202608-0001", "2026-08-25", "20000", "FJ002", "INV-DEMO-202607-0001", "20000"),
    ("RC-DEMO-202609-0001", "2026-09-28", "12600", "FJ001", "INV-DEMO-202608-0001", "12600"),
    ("RC-DEMO-202610-0001", "2026-10-22", "25000", "FJ002", "INV-DEMO-202609-0001", "25000"),
    ("RC-DEMO-202611-0001", "2026-11-15", "16800", "FJ001", "INV-DEMO-202610-0001", "16800"),
]

# 供应商发票：(单号, 业务日期, 金额, 付款单核销金额) —— 采购订单运行时动态取
SUPPLIER_INVOICES: list[tuple[str, str, str, str]] = [
    ("PI-DEMO-202608-0001", "2026-08-20", "3850", "3850"),
    ("PI-DEMO-202609-0001", "2026-09-25", "6700", "4000"),
]

# 付款单：(单号, 业务日期, 金额, 核销的供应商发票号, 核销金额)
SUPPLIER_PAYMENTS: list[tuple[str, str, str, str, str]] = [
    ("PAY-DEMO-202609-0001", "2026-09-30", "3850", "PI-DEMO-202608-0001", "3850"),
    ("PAY-DEMO-202611-0001", "2026-11-18", "4000", "PI-DEMO-202609-0001", "4000"),
]


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seed_finance_demo(db: Session) -> int:
    """重建跨月财务闭环数据；已存在则跳过（幂等）。"""
    from backend.services.finance.gl_engine import post as gl_post

    if db.query(SalesInvoice).filter(
        SalesInvoice.invoice_number == SALES_INVOICES[0][0]
    ).first() is not None:
        return 0

    created = 0
    customer_names: dict[str, str] = {}

    # ── 1) 销售发票 + 应收流水 + 凭证 ──────────────────────────────
    for number, date_str, amount, customer_id, order_number, status, received in SALES_INVOICES:
        order = db.query(SalesOrder).filter(SalesOrder.order_number == order_number).first()
        customer_name = customer_names.get(customer_id)
        if customer_name is None and order is not None and order.customer is not None:
            customer_name = order.customer.legal_name
            customer_names[customer_id] = customer_name
        invoice_date = _dt(date_str)
        db.add(SalesInvoice(
            invoice_number=number,
            sales_order_number=order_number,
            customer_id=customer_id,
            customer_name=customer_name,
            amount=Decimal(amount),
            currency="CNY",
            status=status,
            invoice_date=invoice_date,
            due_date=invoice_date,
            received_amount=Decimal(received),
            remarks="财务演示种子：跨月销售发票",
            created_by="system",
        ))
        db.flush()
        db.add(ReceivableEntry(
            entry_number=number.replace("INV", "AR"),
            invoice_number=number,
            customer_id=customer_id,
            entry_type=ReceivableEntryType.INVOICE,
            amount=Decimal(amount),
            entry_date=invoice_date,
            reference_number=number,
            remarks="财务演示种子：开票应收",
            created_by="system",
        ))
        gl_post(
            db, "SALES_INVOICE_ISSUED", number,
            amount=float(amount), summary=f"演示开票 {number}",
            operator="system", entry_date=invoice_date,
        )
        created += 1

    # ── 2) 收款单 + 核销 + 应收流水 + 凭证 ─────────────────────────
    for number, date_str, amount, customer_id, invoice_number, allocated in RECEIPTS:
        receipt_date = _dt(date_str)
        db.add(Receipt(
            receipt_number=number,
            customer_id=customer_id,
            customer_name=customer_names.get(customer_id),
            amount=Decimal(amount),
            receipt_date=receipt_date,
            method=PaymentMethod.TRANSFER,
            status="PAID",
            remarks="财务演示种子：客户回款",
            created_by="system",
        ))
        db.flush()
        db.add(ReceiptAllocation(
            receipt_number=number,
            invoice_number=invoice_number,
            allocated_amount=Decimal(allocated),
            remarks="财务演示种子：回款核销",
        ))
        db.add(ReceivableEntry(
            entry_number=number.replace("RC", "AR-R"),
            invoice_number=invoice_number,
            customer_id=customer_id,
            entry_type=ReceivableEntryType.RECEIPT,
            amount=Decimal(allocated),
            entry_date=receipt_date,
            reference_number=number,
            remarks="财务演示种子：收款核销",
            created_by="system",
        ))
        gl_post(
            db, "RECEIPT_PAID", number,
            amount=float(allocated), summary=f"演示回款 {number}",
            operator="system", entry_date=receipt_date,
        )
        created += 1

    # ── 3) 供应商发票 + 凭证（采购订单动态取，避免硬编码动态单号） ──
    from backend.common.models.planning import PurchaseOrder

    purchase_orders = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.is_deleted.is_(False))
        .order_by(PurchaseOrder.purchase_order_number)
        .all()
    )
    for index, (number, date_str, amount, _paid) in enumerate(SUPPLIER_INVOICES):
        if index >= len(purchase_orders):
            break
        order_row = purchase_orders[index]
        invoice_date = _dt(date_str)
        db.add(SupplierInvoice(
            invoice_number=number,
            purchase_order_number=order_row.purchase_order_number,
            supplier_id=order_row.supplier_id,
            supplier_name=order_row.supplier_name,
            amount=Decimal(amount),
            tax_amount=Decimal("0"),
            status=SupplierInvoiceStatus.CONFIRMED,
            invoice_date=invoice_date,
            remarks="财务演示种子：供应商发票",
            created_by="system",
        ))
        gl_post(
            db, "SUPPLIER_INVOICE_CONFIRMED", number,
            amount=float(amount), summary=f"演示采购发票 {number}",
            operator="system", entry_date=invoice_date,
        )
        created += 1

    # ── 4) 付款单 + 核销 + 凭证 ────────────────────────────────────
    supplier_names = {row.invoice_number: row.supplier_name for row in db.query(SupplierInvoice).all()}
    supplier_ids = {row.invoice_number: row.supplier_id for row in db.query(SupplierInvoice).all()}
    for number, date_str, amount, invoice_number, allocated in SUPPLIER_PAYMENTS:
        payment_date = _dt(date_str)
        db.add(SupplierPayment(
            payment_number=number,
            supplier_id=supplier_ids.get(invoice_number),
            supplier_name=supplier_names.get(invoice_number),
            amount=Decimal(amount),
            payment_date=payment_date,
            method=PaymentMethod.TRANSFER,
            status="PAID",
            remarks="财务演示种子：供应商付款",
            created_by="system",
        ))
        db.flush()
        db.add(PaymentAllocation(
            payment_number=number,
            invoice_number=invoice_number,
            allocated_amount=Decimal(allocated),
            remarks="财务演示种子：付款核销",
        ))
        gl_post(
            db, "SUPPLIER_PAYMENT_PAID", number,
            amount=float(allocated), summary=f"演示付款 {number}",
            operator="system", entry_date=payment_date,
        )
        created += 1

    db.flush()
    return created
