"""财务管理 router（P2）：科目表 / 凭证查询 / 余额表（试算平衡）/ 会计期间。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.api.routers.auth import get_current_user
from backend.common.models.user import User
from backend.common.models.planning import (
    Account,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    JournalStatus,
    PeriodStatus,
)
from backend.services.finance.gl_engine import GlEngineError
from backend.services.finance.gl_engine import post as gl_post

router = APIRouter()


def _entry_dict(entry: JournalEntry, lines: List[JournalLine]) -> dict:
    return {
        "entry_number": entry.entry_number,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        "period_code": entry.period_code,
        "status": entry.status.value if hasattr(entry.status, "value") else str(entry.status),
        "source_type": entry.source_type.value if hasattr(entry.source_type, "value") else str(entry.source_type),
        "source_ref": entry.source_ref,
        "remarks": entry.remarks,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "lines": [
            {
                "line_number": l.line_number,
                "account_code": l.account_code,
                "debit": float(l.debit or 0),
                "credit": float(l.credit or 0),
                "summary": l.summary,
            }
            for l in sorted(lines, key=lambda x: x.line_number)
        ],
    }


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    rows = (
        db.query(Account)
        .filter(Account.is_deleted.is_(False))
        .order_by(Account.account_code)
        .all()
    )
    return {
        "total": len(rows),
        "items": [
            {
                "account_code": a.account_code,
                "account_name": a.account_name,
                "account_type": a.account_type.value if hasattr(a.account_type, "value") else str(a.account_type),
                "parent_code": a.parent_code,
                "is_leaf": bool(a.is_leaf),
            }
            for a in rows
        ],
    }


@router.get("/periods")
def list_periods(db: Session = Depends(get_db)):
    rows = db.query(FiscalPeriod).order_by(FiscalPeriod.period_code.desc()).all()
    return {
        "total": len(rows),
        "items": [
            {
                "period_code": p.period_code,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            }
            for p in rows
        ],
    }


@router.get("/trial-balance")
def trial_balance(
    period_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """科目余额表：按科目聚合 POSTED 凭证借/贷发生额；Σ借=Σ贷 铁律。"""
    query = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_number == JournalEntry.entry_number)
        .filter(JournalEntry.is_deleted.is_(False),
                JournalEntry.status == JournalStatus.POSTED)
    )
    if period_code:
        query = query.filter(JournalEntry.period_code == period_code)
    accounts = {
        a.account_code: a
        for a in db.query(Account).filter(Account.is_deleted.is_(False)).all()
    }
    by_account: dict[str, dict] = {}
    total_debit = 0.0
    total_credit = 0.0
    for line, _entry in query.all():
        row = by_account.setdefault(
            line.account_code,
            {
                "account_code": line.account_code,
                "account_name": accounts[line.account_code].account_name if line.account_code in accounts else line.account_code,
                "account_type": accounts[line.account_code].account_type.value if line.account_code in accounts and hasattr(accounts[line.account_code].account_type, "value") else "",
                "debit_total": 0.0,
                "credit_total": 0.0,
            },
        )
        row["debit_total"] += float(line.debit or 0)
        row["credit_total"] += float(line.credit or 0)
        total_debit += float(line.debit or 0)
        total_credit += float(line.credit or 0)
    items = sorted(by_account.values(), key=lambda x: x["account_code"])
    for item in items:
        item["debit_total"] = round(item["debit_total"], 2)
        item["credit_total"] = round(item["credit_total"], 2)
        item["balance"] = round(item["debit_total"] - item["credit_total"], 2)
    return {
        "period_code": period_code,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "balanced": abs(total_debit - total_credit) < 0.01,
        "items": items,
    }


@router.get("/journal-entries")
def list_journal_entries(
    source_type: Optional[str] = None,
    source_ref: Optional[str] = None,
    period_code: Optional[str] = None,
    entry_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(JournalEntry).filter(JournalEntry.is_deleted.is_(False))
    if source_type:
        query = query.filter(JournalEntry.source_type == source_type)
    if source_ref:
        query = query.filter(JournalEntry.source_ref == source_ref)
    if period_code:
        query = query.filter(JournalEntry.period_code == period_code)
    if entry_status:
        query = query.filter(JournalEntry.status == JournalStatus(entry_status))
    total = query.count()
    rows = query.order_by(JournalEntry.id.desc()).offset(offset).limit(limit).all()
    numbers = [r.entry_number for r in rows]
    lines = (
        db.query(JournalLine).filter(JournalLine.entry_number.in_(numbers)).all()
        if numbers
        else []
    )
    lines_by_entry: dict[str, list[JournalLine]] = {}
    for line in lines:
        lines_by_entry.setdefault(line.entry_number, []).append(line)
    return {
        "total": total,
        "items": [_entry_dict(r, lines_by_entry.get(r.entry_number, [])) for r in rows],
    }


@router.get("/journal-entries/{entry_number}")
def get_journal_entry(entry_number: str, db: Session = Depends(get_db)):
    entry = (
        db.query(JournalEntry)
        .filter(JournalEntry.entry_number == entry_number, JournalEntry.is_deleted.is_(False))
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail=f"凭证不存在: {entry_number}")
    lines = db.query(JournalLine).filter(JournalLine.entry_number == entry_number).all()
    return _entry_dict(entry, lines)


# ── 月结流程（P3 长期债）：试算平衡门禁 → 损益结转 → 期间 CLOSE ────────
def _month_end_lines(db: Session, period_code: str) -> dict:
    """期间发生额与损益科目明细（只读，preview 与 close 共用）。"""
    rows = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_number == JournalEntry.entry_number)
        .filter(
            JournalEntry.is_deleted.is_(False),
            JournalEntry.status == JournalStatus.POSTED,
            JournalEntry.period_code == period_code,
        )
        .all()
    )
    by_account: dict[str, dict[str, float]] = {}
    for line, _entry in rows:
        bucket = by_account.setdefault(line.account_code, {"debit": 0.0, "credit": 0.0})
        bucket["debit"] += float(line.debit or 0)
        bucket["credit"] += float(line.credit or 0)
    def net(code: str) -> float:
        b = by_account.get(code, {"debit": 0.0, "credit": 0.0})
        return round(b["debit"] - b["credit"], 2)
    total_debit = round(sum(b["debit"] for b in by_account.values()), 2)
    total_credit = round(sum(b["credit"] for b in by_account.values()), 2)
    revenue = max(-net("6001"), 0.0)                  # 收入类贷方余额
    cost_5001 = max(net("5001"), 0.0)                 # 生产成本借方余额
    cost_6401 = max(net("6401"), 0.0)                 # 主营业务成本借方余额
    expense = round(cost_5001 + cost_6401, 2)
    return {
        "period_code": period_code,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balanced": abs(total_debit - total_credit) < 0.01,
        "revenue": revenue,
        "expense": expense,
        "cost_5001": cost_5001,
        "cost_6401": cost_6401,
        "variance": round(revenue - expense, 2),
        "entry_count": len(rows),
    }


def _period_or_404(db: Session, period_code: str) -> FiscalPeriod:
    period = db.query(FiscalPeriod).filter(FiscalPeriod.period_code == period_code).first()
    if not period:
        raise HTTPException(status_code=404, detail=f"会计期间不存在: {period_code}")
    return period


@router.get("/month-end/preview")
def month_end_preview(period_code: str, db: Session = Depends(get_db)):
    """月结预览：期间借贷发生额、收入/成本/差额与试算平衡状态。"""
    period = _period_or_404(db, period_code)
    data = _month_end_lines(db, period_code)
    data["period_status"] = period.status.value
    return data


@router.post("/periods/{period_code}/close")
def close_period(
    period_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """月结：试算平衡校验 → 损益结转分录（收入成本匹配）→ 期间置 CLOSED。"""
    period = _period_or_404(db, period_code)
    if period.status == PeriodStatus.CLOSED:
        raise HTTPException(status_code=400, detail=f"期间 {period_code} 已结账，无需重复月结")
    data = _month_end_lines(db, period_code)
    if not data["balanced"]:
        raise HTTPException(
            status_code=400,
            detail=f"试算不平衡（借 {data['total_debit']} / 贷 {data['total_credit']}），禁止月结",
        )

    revenue, expense = data["revenue"], data["expense"]
    if max(revenue, expense) > 0:
        lines = [
            ("6001", revenue, 0, f"月结结转收入 {period_code}"),
            ("5001", 0, data["cost_5001"], f"月结结转生产成本 {period_code}"),
            ("6401", 0, data["cost_6401"], f"月结结转主营业务成本 {period_code}"),
            ("3131", max(expense - revenue, 0.0), max(revenue - expense, 0.0),
             f"损益结转差额 {period_code}"),
        ]
        lines = [line for line in lines if line[1] > 0 or line[2] > 0]
        try:
            gl_post(
                db, "PERIOD_CLOSE", period_code,
                amount=max(revenue, expense), lines=lines,
                summary=f"月结损益结转 {period_code}", operator=current_user.username,
            )
            db.commit()
        except GlEngineError as exc:
            raise HTTPException(status_code=400, detail=f"结转分录失败: {exc}")

    period.status = PeriodStatus.CLOSED
    period.updated_by = current_user.username
    period.updated_at = datetime.now()
    db.commit()
    result = _month_end_lines(db, period_code)
    result["period_status"] = PeriodStatus.CLOSED.value
    return result


@router.post("/periods/{period_code}/reopen")
def reopen_period(
    period_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """反结账：CLOSED → OPEN（不删除已过账凭证）。"""
    period = _period_or_404(db, period_code)
    if period.status != PeriodStatus.CLOSED:
        raise HTTPException(status_code=400, detail=f"期间状态为 {period.status.value}，无需反结账")
    period.status = PeriodStatus.OPEN
    period.updated_by = current_user.username
    period.updated_at = datetime.now()
    db.commit()
    return {"period_code": period_code, "status": PeriodStatus.OPEN.value}
