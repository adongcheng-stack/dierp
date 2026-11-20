"""轻量总账分录引擎（P2 demo 口径）。

GlEngine.post(db, source_type, source_ref, amount=..., lines=...)：
  - 幂等：同一 (source_type, source_ref) 只入账一次，重复调用返回既有凭证；
  - 平衡铁律：Σdebit == Σcredit，否则拒绝（应用层校验，SHACL 无法表达跨行）；
  - 期间检查：会计期间存在且 CLOSED 时拒绝过账（期间缺失则自动补当期 OPEN）。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from backend.common.models.planning import (
    Account,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    JournalStatus,
    PeriodStatus,
)
from backend.common.utils.number_generator import NumberGenerator
from backend.services.finance.gl_rules import GL_RULES


class GlEngineError(Exception):
    """分录引擎业务错误（平衡/期间/规则缺失）。"""


def _ensure_period(db: Session, entry_date: datetime) -> str:
    """期间存在且 OPEN 才可过账；缺失则自动补建当期 OPEN（demo 口径）。"""
    period_code = entry_date.strftime("%Y-%m")
    period = db.query(FiscalPeriod).filter(FiscalPeriod.period_code == period_code).first()
    if period is None:
        if entry_date.month == 12:
            start = entry_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1, month=1)
        else:
            start = entry_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(month=start.month + 1)
        period = FiscalPeriod(
            period_code=period_code, start_date=start, end_date=end, status=PeriodStatus.OPEN
        )
        db.add(period)
        db.flush()
    elif period.status == PeriodStatus.CLOSED:
        raise GlEngineError(f"会计期间 {period_code} 已结账，不允许过账")
    return period_code


def post(
    db: Session,
    source_type: str,
    source_ref: str,
    amount: Optional[float] = None,
    lines: Optional[list[tuple[str, Decimal, Decimal, str]]] = None,
    summary: str = "",
    operator: str = "system",
) -> JournalEntry:
    """按业务事件入账：lines 为 (科目, 借, 贷, 摘要)；不传 lines 时按 GL_RULES 单行借贷。

    幂等：同一 (source_type, source_ref) 重复调用直接返回既有凭证（不重复入账）。
    """
    existing = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.source_type == source_type,
            JournalEntry.source_ref == source_ref,
            JournalEntry.is_deleted.is_(False),
        )
        .first()
    )
    if existing is not None:
        return existing

    if source_type not in GL_RULES and lines is None:
        raise GlEngineError(f"业务事件 {source_type} 无分录映射，且未提供 lines")

    if lines is None:
        debit_account, credit_account = GL_RULES[source_type]
        if not amount or amount <= 0:
            raise GlEngineError(f"分录金额必须大于 0：{source_type} {source_ref} amount={amount}")
        lines = [
            (debit_account, Decimal(str(amount)), Decimal("0"), summary or f"{source_type} {source_ref}"),
            (credit_account, Decimal("0"), Decimal(str(amount)), summary or f"{source_type} {source_ref}"),
        ]

    # 科目必须已存在（种子维护）
    for account_code, _debit, _credit, _summary in lines:
        account = db.query(Account).filter(Account.account_code == account_code).first()
        if account is None:
            raise GlEngineError(f"科目不存在: {account_code}（请先执行科目种子）")

    def _cent(value) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_debit = sum((_cent(l[1]) for l in lines), Decimal("0"))
    total_credit = sum((_cent(l[2]) for l in lines), Decimal("0"))
    if total_debit <= 0 or total_debit != total_credit:
        raise GlEngineError(
            f"分录借贷不平衡：Σ借 {total_debit} != Σ贷 {total_credit}（{source_type} {source_ref}）"
        )

    now = datetime.now()
    period_code = _ensure_period(db, now)
    entry = JournalEntry(
        entry_number=NumberGenerator.generate_document_number(db, JournalEntry, "entry_number", "JE", 4),
        entry_date=now,
        period_code=period_code,
        status=JournalStatus.POSTED,
        source_type=source_type,
        source_ref=source_ref,
        remarks=summary or None,
        created_by=operator,
    )
    db.add(entry)
    db.flush()  # 坑2：行号与 FK 依赖凭证落库
    for index, (account_code, debit, credit, line_summary) in enumerate(lines, start=1):
        db.add(JournalLine(
            entry_number=entry.entry_number,
            line_number=index,
            account_code=account_code,
            debit=_cent(debit),
            credit=_cent(credit),
            summary=line_summary,
        ))
    db.flush()
    return entry
