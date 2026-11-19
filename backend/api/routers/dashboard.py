"""经营看板 router：六域 KPI 只读汇总（ADR-20261118-01 同类派生查询）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.services.planning.management_dashboard import ManagementDashboard
from backend.common.models.planning import (
    InvoiceStatus,
    JournalEntry,
    JournalLine,
    JournalStatus,
    PaymentAllocation,
    ReceiptAllocation,
    SalesInvoice,
    SupplierInvoice,
    SupplierInvoiceStatus,
)

router = APIRouter()


@router.get("/management")
def management_overview(db: Session = Depends(get_db)):
    """销售/生产/质量/设备/成本/交期 六域 KPI + 自动点评。"""
    data = ManagementDashboard.overview(db)
    data["insights"] = ManagementDashboard.insights(data)
    return data


@router.get("/finance-kpi")
def finance_kpi(db: Session = Depends(get_db)):
    """资金维度四卡（P3，纯读）：应收余额 / 应付余额 / 回款率 / 现金流水。"""
    # 应收余额：未作废销售发票的 未收合计
    sales_invoices = (
        db.query(SalesInvoice)
        .filter(SalesInvoice.is_deleted.is_(False),
                SalesInvoice.status != InvoiceStatus.CANCELLED)
        .all()
    )
    receivable_outstanding = round(sum(
        float(i.amount or 0) - float(i.received_amount or 0) for i in sales_invoices
    ), 2)
    invoiced_total = round(sum(float(i.amount or 0) for i in sales_invoices
                               if i.status != InvoiceStatus.DRAFT), 2)

    # 回款率：收款核销合计 ÷ 已开票合计（分母 0 → 0）
    collected_total = round(sum(
        float(a.allocated_amount or 0) for a in db.query(ReceiptAllocation).all()
    ), 2)
    collection_rate = round(collected_total / invoiced_total, 4) if invoiced_total > 0 else 0.0

    # 应付余额：已确认采购发票 − 付款核销
    confirmed_total = round(sum(
        float(i.amount or 0)
        for i in db.query(SupplierInvoice)
        .filter(SupplierInvoice.is_deleted.is_(False),
                SupplierInvoice.status == SupplierInvoiceStatus.CONFIRMED)
        .all()
    ), 2)
    paid_total = round(sum(
        float(a.allocated_amount or 0) for a in db.query(PaymentAllocation).all()
    ), 2)
    payable_open = round(confirmed_total - paid_total, 2)

    # 现金流水：GL 1002 银行存款 余额（Σ借 − Σ贷，POSTED）
    cash_debit = cash_credit = 0.0
    rows = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_number == JournalEntry.entry_number)
        .filter(JournalEntry.is_deleted.is_(False),
                JournalEntry.status == JournalStatus.POSTED,
                JournalLine.account_code == "1002")
        .all()
    )
    for line, _entry in rows:
        cash_debit += float(line.debit or 0)
        cash_credit += float(line.credit or 0)
    cash_balance = round(cash_debit - cash_credit, 2)

    return {
        "receivable_outstanding": receivable_outstanding,
        "payable_open": payable_open,
        "collection_rate": collection_rate,
        "cash_balance": cash_balance,
        "invoiced_total": invoiced_total,
        "collected_total": collected_total,
        "supplier_confirmed_total": confirmed_total,
        "supplier_paid_total": paid_total,
    }
