"""库存估值服务（移动加权实际成本）。

唯一库存写入口：数量（Material.current_stock）与金额（InventoryValuation）同事务维护，
每次变动落一条 ValuationMove 成本快照；红字冲回按原流水单价，不用当前均价。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from backend.common.models.mm import Material
from backend.common.models.planning import (
    CostSourceType,
    InventoryValuation,
    ValuationDirection,
    ValuationMove,
)
from backend.common.utils.number_generator import NumberGenerator

Q6 = Decimal("0.000001")
Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")


class ValuationError(Exception):
    """估值业务错误（数量不足/金额守护失败）。"""


def _dec(value) -> Decimal:
    return Decimal(str(value or 0))


def _q(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def get_or_create_valuation(db: Session, material_code: str) -> InventoryValuation:
    row = db.query(InventoryValuation).filter(
        InventoryValuation.material_code == material_code
    ).first()
    if row is None:
        row = InventoryValuation(
            material_code=material_code,
            qty=Decimal("0"), amount=Decimal("0"),
            avg_cost=Decimal("0"), last_cost=Decimal("0"),
            created_by="system",
        )
        db.add(row)
        db.flush()
    return row


def get_cost(db: Session, material_code: str) -> Decimal:
    """当前计价单价（供 GL 分录金额使用）。"""
    row = get_or_create_valuation(db, material_code)
    cost = _dec(row.avg_cost)
    if cost <= 0:
        cost = _dec(row.last_cost)
    return cost


class InventoryValuationService:
    """移动加权库存估值：唯一的库存数量+金额写入口。"""

    @staticmethod
    def post(
        db: Session,
        *,
        material_code: str,
        qty_delta,
        unit_cost=None,
        source_type: str,
        source_ref: str,
        reversal_of: Optional[str] = None,
        operator: str = "system",
        allow_negative: bool = False,
    ) -> ValuationMove:
        """记一次库存变动，返回估值流水（含成本快照）。

        - qty_delta>0 入库：金额 += qty × unit_cost，均价重算，last_cost 更新
        - qty_delta<0 出库：成本取原流水快照（有 reversal_of）或当前均价（qty=0 回退 last_cost）
        - 出账后金额为负 → 钳制 0 + 告警日志（由调用方按需补成本差异科目）
        - source_type+source_ref 幂等：重复调用直接返回既有流水
        """
        delta = _dec(qty_delta)
        if delta == 0:
            raise ValuationError("库存变动数量不能为 0")
        existing = (
            db.query(ValuationMove)
            .filter(ValuationMove.source_type == source_type,
                    ValuationMove.source_ref == source_ref,
                    ValuationMove.qty == abs(delta))
            .first()
        )
        if existing is not None:
            return existing

        material = db.query(Material).filter(Material.material_code == material_code).first()
        if material is None:
            raise ValuationError(f"物料不存在: {material_code}")

        valuation = get_or_create_valuation(db, material_code)
        qty_before = _dec(valuation.qty)
        amount_before = _dec(valuation.amount)

        direction = ValuationDirection.IN if delta > 0 else ValuationDirection.OUT
        if direction == ValuationDirection.IN:
            if reversal_of:
                original = db.query(ValuationMove).filter(
                    ValuationMove.move_number == reversal_of).first()
                if original is None:
                    print(f"[VALUATION] 红冲原流水不存在 {reversal_of}，回退本次 unit_cost")
                else:
                    unit_cost = original.unit_cost
            cost = _dec(unit_cost)
            if cost <= 0:
                cost = _dec(valuation.last_cost)
            qty_after = qty_before + abs(delta)
            amount_after = amount_before + abs(delta) * cost
            valuation.last_cost = _q(cost, Q6)
        else:
            qty_out = abs(delta)
            if qty_before < qty_out and not allow_negative:
                raise ValuationError(
                    f"库存不足：{material_code} 现存 {qty_before}，需出 {qty_out}"
                )
            if reversal_of:
                original = db.query(ValuationMove).filter(
                    ValuationMove.move_number == reversal_of).first()
                if original is None:
                    print(f"[VALUATION] 红冲原流水不存在 {reversal_of}，回退当前均价")
                    cost = get_cost(db, material_code)
                else:
                    cost = _dec(original.unit_cost)
            else:
                cost = _dec(valuation.avg_cost)
                if cost <= 0:
                    cost = _dec(valuation.last_cost)
            qty_after = qty_before - qty_out
            amount_after = amount_before - qty_out * cost
            if amount_after < 0:
                variance = abs(amount_after)
                print(
                    f"[VALUATION] 负金额钳制：{material_code} 余额 {amount_after}，"
                    f"原余额 {amount_before}，出账 {qty_out}×{cost}，差额 {variance} 入存货差异"
                )
                amount_after = Decimal("0")
                # 差异归属：借 6402 存货差异 / 贷 1405 库存商品（gl_post 自带幂等）
                try:
                    from backend.services.finance.gl_engine import post as gl_post
                    gl_post(
                        db, "COST_VARIANCE", f"VAR-{source_ref}",
                        amount=variance,
                        lines=[
                            ("6402", variance, 0, f"存货差异 {source_ref}"),
                            ("1405", 0, variance, f"存货差异 {source_ref}"),
                        ],
                        summary=f"存货差异 {material_code}", operator=operator,
                    )
                except Exception as exc:
                    print(f"[VALUATION] 差异分录失败 {source_ref}: {exc}")

        avg_after = _dec(amount_after) / qty_after if qty_after > 0 else Decimal("0")
        valuation.qty = _q(qty_after, Q2)
        valuation.amount = _q(amount_after, Q4)
        valuation.avg_cost = _q(avg_after, Q6)
        valuation.updated_by = operator
        valuation.updated_at = datetime.now()

        # 数量账与金额账保持单一真相
        material.current_stock = _q(qty_after, Q2)
        material.updated_by = operator

        move = ValuationMove(
            move_number=NumberGenerator.generate_document_number(
                db, ValuationMove, "move_number", "VM", 4),
            material_code=material_code,
            direction=direction,
            qty=_q(abs(delta), Q2),
            unit_cost=_q(cost, Q6),
            amount=_q(abs(delta) * cost, Q4),
            balance_qty=_q(qty_after, Q2),
            balance_amount=_q(amount_after, Q4),
            source_type=source_type,
            source_ref=source_ref,
            reversal_of=reversal_of,
            created_by=operator,
        )
        db.add(move)
        db.flush()
        return move
