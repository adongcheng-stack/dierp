"""收款单红字冲回单元测试（PAID → REVERSED）。"""
from datetime import datetime
from decimal import Decimal

from backend.api.routers.sd import reverse_receipt
from backend.common.models.planning import (
    Account,
    AccountType,
    InvoiceStatus,
    JournalEntry,
    ReceivableEntry,
    ReceivableEntryType,
    Receipt,
    ReceiptAllocation,
    SalesInvoice,
)
from backend.common.models.sd import Customer, SalesOrder
from backend.common.models.user import User, UserRole


def _setup_paid_receipt(db):
    db.add(Customer(customer_id="C-RV", legal_name="红冲测试客户"))
    db.add(SalesOrder(order_number="SO-RV-1", customer_id="C-RV", product_number="P",
                      quantity=1, unit_price=1000, total_amount=1000,
                      delivery_date=datetime(2026, 12, 1)))
    db.flush()
    db.add(SalesInvoice(invoice_number="INV-RV-1", sales_order_number="SO-RV-1",
                        customer_id="C-RV", amount=1000,
                        status=InvoiceStatus.PAID, received_amount=1000,
                        invoice_date=datetime.now()))
    db.add(Receipt(receipt_number="RC-RV-1", customer_id="C-RV", customer_name="红冲测试客户",
                   amount=1000, receipt_date=datetime.now(), status="PAID"))
    db.flush()
    db.add(ReceiptAllocation(receipt_number="RC-RV-1", invoice_number="INV-RV-1",
                             allocated_amount=1000))
    for code, name in [("1122", "应收账款"), ("1002", "银行存款")]:
        db.add(Account(account_code=code, account_name=name, account_type=AccountType.ASSET))
    db.flush()
    user = User(username="admin", email="a@b.c", password_hash="x", role=UserRole.ADMIN)
    db.add(user)
    db.flush()
    return user


def test_reverse_paid_receipt(db):
    user = _setup_paid_receipt(db)

    result = reverse_receipt("RC-RV-1", db, user)

    assert result["status"] == "REVERSED"
    assert result["reversed_amount"] == 1000.0
    invoice = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == "INV-RV-1").one()
    assert float(invoice.received_amount) == 0.0
    assert invoice.status == InvoiceStatus.ISSUED
    receipt = db.query(Receipt).filter(Receipt.receipt_number == "RC-RV-1").one()
    assert receipt.status == "REVERSED"

    reverses = (
        db.query(ReceivableEntry)
        .filter(ReceivableEntry.entry_type == ReceivableEntryType.RECEIPT_REVERSE)
        .all()
    )
    assert len(reverses) == 1
    assert float(reverses[0].amount) == 1000.0
    assert reverses[0].reference_number == "RC-RV-1-REVERSE"

    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.source_type == "RECEIPT_PAID_REVERSE")
        .all()
    )
    assert len(entries) == 1


def test_reverse_requires_paid_status(db):
    user = _setup_paid_receipt(db)
    receipt = db.query(Receipt).filter(Receipt.receipt_number == "RC-RV-1").one()
    receipt.status = "DRAFT"
    db.flush()

    try:
        reverse_receipt("RC-RV-1", db, user)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("DRAFT 收款单不应允许红冲")


def _setup_issued_invoice(db):
    db.add(Customer(customer_id="C-IVRV", legal_name="发票红冲测试客户"))
    db.add(SalesOrder(order_number="SO-IVRV-1", customer_id="C-IVRV", product_number="P",
                      quantity=1, unit_price=500, total_amount=500,
                      delivery_date=datetime(2026, 12, 1)))
    db.flush()
    db.add(SalesInvoice(invoice_number="INV-IVRV-1", sales_order_number="SO-IVRV-1",
                        customer_id="C-IVRV", amount=500,
                        status=InvoiceStatus.ISSUED, received_amount=0,
                        invoice_date=datetime.now()))
    for code, name, kind in [("1122", "应收账款", AccountType.ASSET),
                             ("6001", "主营业务收入", AccountType.REVENUE)]:
        db.add(Account(account_code=code, account_name=name, account_type=kind))
    db.flush()
    user = User(username="admin", email="a@b2.c", password_hash="x", role=UserRole.ADMIN)
    db.add(user)
    db.flush()
    return user


def test_reverse_issued_invoice(db):
    """发票侧红字冲回（ISSUED → CANCELLED，负向应收流水 + 红字凭证）。"""
    from backend.api.routers.sd import reverse_invoice

    user = _setup_issued_invoice(db)
    result = reverse_invoice("INV-IVRV-1", db, user)

    assert result["status"] == "CANCELLED"
    assert result["reversed_amount"] == 500.0

    entry = (
        db.query(ReceivableEntry)
        .filter(ReceivableEntry.reference_number == "INV-IVRV-1-INV-REVERSE")
        .one()
    )
    assert entry.entry_type == ReceivableEntryType.INVOICE_REVERSE
    assert float(entry.amount) == -500.0

    invoice = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == "INV-IVRV-1").one()
    assert invoice.status == InvoiceStatus.CANCELLED

    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.source_type == "SALES_INVOICE_REVERSED")
        .all()
    )
    assert len(entries) == 1


def test_reverse_invoice_rejects_paid(db):
    from backend.api.routers.sd import reverse_invoice
    from fastapi import HTTPException

    user = _setup_issued_invoice(db)
    invoice = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == "INV-IVRV-1").one()
    invoice.received_amount = 500
    invoice.status = InvoiceStatus.PARTIALLY_PAID
    db.flush()
    try:
        reverse_invoice("INV-IVRV-1", db, user)
        assert False, "已收款发票应拒绝红冲"
    except HTTPException as exc:
        assert exc.status_code == 400
