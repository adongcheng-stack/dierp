"""驾驶舱取数：资金 KPI 与工序进度（从 dashboard 路由抽出供解读层复用）。

口径与 ``GET /api/dashboard/finance-kpi`` / ``/api/dashboard/production-progress``
完全一致；仅移动位置，不改变任何计算与返回结构。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

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
from backend.common.models.pp import ProductionProgress

WINDOW_DAYS = {"ALL": None, "LAST30": 30, "LAST90": 90, "LAST365": 365}


def window_start(window: str) -> datetime | None:
    days = WINDOW_DAYS.get(window)
    return datetime.now() - timedelta(days=days) if days else None


def in_window(value: Any, start: datetime | None) -> bool:
    if start is None:
        return True
    if value is None:
        return False
    if isinstance(value, datetime):
        return value >= start
    if hasattr(value, "date"):
        return value.date() >= start.date()
    return True


def finance_kpi(db: Session) -> dict[str, Any]:
    """资金维度 KPI（与 /finance-kpi 同口径，供驾驶舱复用）。"""
    sales_invoices = (
        db.query(SalesInvoice)
        .filter(SalesInvoice.is_deleted.is_(False), SalesInvoice.status != InvoiceStatus.CANCELLED)
        .all()
    )
    receivable = round(sum(
        float(i.amount or 0) - float(i.received_amount or 0) for i in sales_invoices
    ), 2)
    invoiced = round(sum(
        float(i.amount or 0) for i in sales_invoices if i.status != InvoiceStatus.DRAFT
    ), 2)
    collected = round(sum(float(a.allocated_amount or 0) for a in db.query(ReceiptAllocation).all()), 2)
    rate = round(collected / invoiced, 4) if invoiced > 0 else 0.0
    confirmed = round(sum(
        float(i.amount or 0)
        for i in db.query(SupplierInvoice)
        .filter(
            SupplierInvoice.is_deleted.is_(False),
            SupplierInvoice.status == SupplierInvoiceStatus.CONFIRMED,
        ).all()
    ), 2)
    paid = round(sum(float(a.allocated_amount or 0) for a in db.query(PaymentAllocation).all()), 2)
    debit = credit = 0.0
    for line, _entry in (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_number == JournalEntry.entry_number)
        .filter(
            JournalEntry.is_deleted.is_(False),
            JournalEntry.status == JournalStatus.POSTED,
            JournalLine.account_code == "1002",
        ).all()
    ):
        debit += float(line.debit or 0)
        credit += float(line.credit or 0)
    return {
        "receivable_outstanding": receivable,
        "payable_open": round(confirmed - paid, 2),
        "collection_rate": rate,
        "cash_balance": round(debit - credit, 2),
        "invoiced_total": invoiced,
        "collected_total": collected,
        "supplier_confirmed_total": confirmed,
        "supplier_paid_total": paid,
    }


def progress_rows(db: Session, window: str, order: str | None) -> list[dict[str, Any]]:
    start = window_start(window)
    query = db.query(ProductionProgress)
    if order:
        query = query.filter(ProductionProgress.production_order_number == order)
    rows = query.order_by(ProductionProgress.production_order_number, ProductionProgress.operation_no).all()
    rows = [row for row in rows if in_window(row.planned_start_time or row.actual_start_time, start)]
    result = []
    for row in rows:
        planned = float(row.planned_quantity or 0)
        completed = float(row.completed_quantity or 0)
        rate = float(row.completion_rate or 0)
        if rate <= 0 and planned > 0:
            rate = round(min(completed / planned, 1.0), 4)
        status = str(row.status.value if hasattr(row.status, "value") else row.status)
        # 演示种子只写了 PENDING 但未回写完成量，按完成率推导真实状态，避免 100% 仍显示待开始
        if status == "PENDING":
            if rate >= 1:
                status = "COMPLETED"
            elif rate > 0:
                status = "IN_PROGRESS"
        result.append({
            "production_order_number": row.production_order_number,
            "operation_no": row.operation_no,
            "operation_name": row.operation_name,
            "work_center_id": row.work_center_id,
            "planned_quantity": planned,
            "completed_quantity": completed,
            "completion_rate": rate,
            "status": status,
            "planned_start_time": row.planned_start_time.isoformat() if row.planned_start_time else None,
            "planned_finish_time": row.planned_finish_time.isoformat() if row.planned_finish_time else None,
            "actual_start_time": row.actual_start_time.isoformat() if row.actual_start_time else None,
            "actual_finish_time": row.actual_finish_time.isoformat() if row.actual_finish_time else None,
        })
    return result
