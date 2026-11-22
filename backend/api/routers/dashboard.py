"""驾驶舱/看板路由：只读派生 KPI + 本体规则预警。

所有接口均为 GET，挂在 dashboard 域（本体 :anonymousRead true），
与既有「管理驾驶舱」保持一致的只读契约。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.services.planning.management_dashboard import ManagementDashboard
from backend.services.dashboard.alerts import build_alerts
from backend.common.models.planning import (
    FiscalPeriod,
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
from backend.common.models.sd import Quotation

router = APIRouter()

WINDOW_DAYS = {"ALL": None, "LAST30": 30, "LAST90": 90, "LAST365": 365}


def _window_start(window: str) -> datetime | None:
    days = WINDOW_DAYS.get(window)
    return datetime.now() - timedelta(days=days) if days else None


def _in_window(value: Any, start: datetime | None) -> bool:
    if start is None:
        return True
    if value is None:
        return False
    if isinstance(value, datetime):
        return value >= start
    if hasattr(value, "date"):
        return value.date() >= start.date()
    return True


def _finance_kpi(db: Session) -> dict[str, Any]:
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


def _progress_rows(db: Session, window: str, order: str | None) -> list[dict[str, Any]]:
    start = _window_start(window)
    query = db.query(ProductionProgress)
    if order:
        query = query.filter(ProductionProgress.production_order_number == order)
    rows = query.order_by(ProductionProgress.production_order_number, ProductionProgress.operation_no).all()
    rows = [row for row in rows if _in_window(row.planned_start_time or row.actual_start_time, start)]
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


@router.get("/management")
def management_overview(db: Session = Depends(get_db)):
    """销售/生产/质量/设备/成本/交期 六域 KPI + 自动点评。"""
    data = ManagementDashboard.overview(db)
    data["insights"] = ManagementDashboard.insights(data)
    return data


@router.get("/finance-kpi")
def finance_kpi(db: Session = Depends(get_db)):
    """资金维度四卡：应收余额 / 应付余额 / 回款率 / 现金流水。"""
    return _finance_kpi(db)


COCKPITS = [
    {"key": "management", "title": "管理驾驶舱", "path": "/dashboard/management", "description": "六域 KPI + 资金四卡 + 自动点评", "icon": "Gauge"},
    {"key": "production", "title": "生产驾驶舱", "path": "/dashboard/production", "description": "工单完成率 / OEE / 不良 / 交期风险", "icon": "Factory"},
    {"key": "progress", "title": "生产进度看板", "path": "/dashboard/production-progress", "description": "工序级进度甘特与异常", "icon": "ClipboardCheck"},
    {"key": "finance", "title": "财务驾驶舱", "path": "/dashboard/finance", "description": "应收应付 / 回款率 / 现金流 / 月结", "icon": "Wallet"},
    {"key": "sales", "title": "销售驾驶舱", "path": "/dashboard/sales", "description": "订单额 / 未交 / 报价转化 / 账龄", "icon": "ShoppingCart"},
]

WORKBENCHES = [
    {"title": "计划工作台", "path": "/pp/planning", "domain": "计划与控制"},
    {"title": "APS 工作台", "path": "/aps/workbench", "domain": "高级排程"},
    {"title": "成本工作台", "path": "/cost/workbench", "domain": "成本管理"},
    {"title": "质量工作台", "path": "/qms/workbench", "domain": "质量管理"},
    {"title": "设备工作台", "path": "/eam/workbench", "domain": "设备管理"},
]


@router.get("/home")
def dashboard_home(db: Session = Depends(get_db)):
    """驾驶舱中心：入口目录 + 全局摘要 + HOME 规则预警。"""
    overview = ManagementDashboard.overview(db)
    finance = _finance_kpi(db)
    data = {**overview, "finance": finance}
    return {
        "cockpits": COCKPITS,
        "workbenches": WORKBENCHES,
        "summary": {
            "sales_amount": overview["sales"]["amount_total"],
            "production_completion": overview["production"]["completion_rate"],
            "oee": overview["equipment"]["oee"],
            "collection_rate": finance["collection_rate"],
            "cash_balance": finance["cash_balance"],
        },
        "alerts": build_alerts(db, "HOME", data),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/production")
def production_dashboard(window: str = "ALL", db: Session = Depends(get_db)):
    """生产驾驶舱：工单/OEE/质量 + 工序进度 + 预警。"""
    overview = ManagementDashboard.overview(db)
    rows = _progress_rows(db, window, None)
    avg_rate = round(sum(row["completion_rate"] for row in rows) / len(rows), 4) if rows else 0.0
    progress = {
        "operations": len(rows),
        "avg_completion_rate": avg_rate,
        "delayed": sum(1 for row in rows if row["status"] == "DELAYED"),
        "rows": rows[:30],
    }
    data = {**overview, "progress": progress}
    return {
        **data,
        "window": window,
        "alerts": build_alerts(db, "PRODUCTION", data),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/production-progress")
def production_progress_board(
    window: str = "ALL",
    order: str | None = Query(None, description="工单号筛选"),
    db: Session = Depends(get_db),
):
    """生产进度看板：工序甘特数据源（接既有 ProductionProgress）。"""
    rows = _progress_rows(db, window, order)
    summary = {
        "operations": len(rows),
        "orders": len({row["production_order_number"] for row in rows}),
        "avg_completion_rate": round(sum(r["completion_rate"] for r in rows) / len(rows), 4) if rows else 0.0,
        "by_status": {},
    }
    for row in rows:
        summary["by_status"][row["status"]] = summary["by_status"].get(row["status"], 0) + 1
    data = {"progress": summary}
    return {
        "summary": summary,
        "rows": rows,
        "window": window,
        "alerts": build_alerts(db, "PROGRESS", data),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/finance")
def finance_dashboard(window: str = "ALL", db: Session = Depends(get_db)):
    """财务驾驶舱：资金四卡 + 凭证趋势 + 期间状态 + 预警。"""
    finance = _finance_kpi(db)
    start = _window_start(window)
    entries = db.query(JournalEntry).filter(JournalEntry.is_deleted.is_(False)).all()
    entries = [entry for entry in entries if _in_window(entry.entry_date, start)]
    trend_map: dict[str, float] = {}
    for entry in entries:
        key = (entry.entry_date or datetime.now()).strftime("%Y-%m")
        trend_map[key] = trend_map.get(key, 0.0) + 1
    trend = [{"month": key, "entries": value} for key, value in sorted(trend_map.items())]
    periods = []
    for period in db.query(FiscalPeriod).filter(FiscalPeriod.is_deleted.is_(False)).all():
        periods.append({
            "period_code": period.period_code,
            "status": str(period.status.value if hasattr(period.status, "value") else period.status),
        })
    data = {"finance": finance}
    return {
        "finance": finance,
        "trend": trend,
        "periods": periods,
        "window": window,
        "alerts": build_alerts(db, "FINANCE", data),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/sales")
def sales_dashboard(window: str = "ALL", db: Session = Depends(get_db)):
    """销售驾驶舱：订单/报价转化/客户账龄 + 预警。"""
    overview = ManagementDashboard.overview(db)
    start = _window_start(window)
    quotations = db.query(Quotation).filter(Quotation.is_deleted.is_(False)).all()
    quotations = [q for q in quotations if _in_window(getattr(q, "created_at", None), start)]
    approved = sum(
        1 for q in quotations
        if str(q.status.value if hasattr(q.status, "value") else q.status)
        in {"APPROVED", "CONFIRMED", "RELEASED", "COMPLETED"}
    )
    quotation_stat = {
        "total": len(quotations),
        "approved": approved,
        "conversion_rate": round(approved / len(quotations), 4) if quotations else 0.0,
    }
    aging: dict[str, float] = {}
    for invoice in db.query(SalesInvoice).filter(
        SalesInvoice.is_deleted.is_(False), SalesInvoice.status != InvoiceStatus.CANCELLED
    ).all():
        outstanding = float(invoice.amount or 0) - float(invoice.received_amount or 0)
        if outstanding > 0:
            key = invoice.customer_name or invoice.customer_id or "-"
            aging[key] = round(aging.get(key, 0.0) + outstanding, 2)
    customers = [
        {"customer": key, "outstanding": value}
        for key, value in sorted(aging.items(), key=lambda item: -item[1])[:10]
    ]
    data = {"sales": overview["sales"], "quotation": quotation_stat}
    return {
        "sales": overview["sales"],
        "quotation": quotation_stat,
        "customers": customers,
        "window": window,
        "alerts": build_alerts(db, "SALES", data),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
