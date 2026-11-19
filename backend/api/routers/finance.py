"""财务管理 router（P2）：科目表 / 凭证查询 / 余额表（试算平衡）/ 会计期间。"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.common.models.planning import (
    Account,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    JournalStatus,
)

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
