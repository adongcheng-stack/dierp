"""采购订单 router：列表 / 详情 / 到货（回冲原料库存）/ 关闭。

闭环补全：MRP 计划订单 release 时自动生成 PUR 采购单（见 planning.py），
本路由让采购单「可见、可收货、可关闭」，到货即回冲物料库存（N3 采购闭环）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.common.models.mm import Material
from backend.common.models.planning import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)

router = APIRouter()

RECEIVABLE_STATUSES = {PurchaseOrderStatus.RELEASED, PurchaseOrderStatus.PARTIALLY_RECEIVED}


# ── helpers ────────────────────────────────────────────────────────────
def _s(value) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def _line_dict(line: PurchaseOrderLine) -> dict:
    return {
        "line_number": line.line_number,
        "material_code": line.material_code,
        "quantity": _f(line.quantity),
        "received_quantity": _f(line.received_quantity),
        "outstanding_quantity": _f(line.quantity) - _f(line.received_quantity),
        "unit": line.unit,
        "unit_price": _f(line.unit_price),
        "expected_date": line.expected_date.isoformat() if line.expected_date else None,
        "status": _s(line.status),
        "remarks": line.remarks,
    }


def _order_dict(order: PurchaseOrder, lines: list[PurchaseOrderLine]) -> dict:
    return {
        "purchase_order_number": order.purchase_order_number,
        "supplier_id": order.supplier_id,
        "supplier_name": order.supplier_name,
        "status": _s(order.status),
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "expected_date": order.expected_date.isoformat() if order.expected_date else None,
        "currency": order.currency,
        "total_amount": _f(order.total_amount),
        "source_planned_order": order.source_planned_order,
        "remarks": order.remarks,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "lines": [_line_dict(line) for line in lines],
    }


def _load_order(db: Session, number: str) -> tuple[PurchaseOrder, list[PurchaseOrderLine]]:
    order = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.purchase_order_number == number,
            PurchaseOrder.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail=f"采购单不存在: {number}")
    lines = (
        db.query(PurchaseOrderLine)
        .filter(
            PurchaseOrderLine.purchase_order_number == number,
            PurchaseOrderLine.is_deleted == False,  # noqa: E712
        )
        .order_by(PurchaseOrderLine.line_number)
        .all()
    )
    return order, lines


class ReceiveItem(BaseModel):
    line_number: int = Field(ge=1)
    quantity: Optional[float] = Field(default=None, gt=0)


class ReceivePayload(BaseModel):
    """到货请求：不传 quantity 时按「未收余量」整行收货。"""

    lines: list[ReceiveItem] = Field(default_factory=list)
    remarks: Optional[str] = None
    received_by: Optional[str] = None


# ── 端点 ───────────────────────────────────────────────────────────────
@router.get("/purchase-orders")
def list_purchase_orders(
    skip: int = 0,
    limit: int = 200,
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier_id: Optional[str] = None,
    material_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseOrder).filter(PurchaseOrder.is_deleted == False)  # noqa: E712
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    orders = query.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.id.desc()).all()
    if material_code:
        hit_numbers = {
            line.purchase_order_number
            for line in db.query(PurchaseOrderLine)
            .filter(
                PurchaseOrderLine.material_code == material_code,
                PurchaseOrderLine.is_deleted == False,  # noqa: E712
            )
            .all()
        }
        orders = [o for o in orders if o.purchase_order_number in hit_numbers]

    total = len(orders)
    page = orders[skip : skip + limit]
    all_lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.is_deleted == False)  # noqa: E712
        .all()
    )
    lines_by_order: dict[str, list[PurchaseOrderLine]] = {}
    for line in all_lines:
        lines_by_order.setdefault(line.purchase_order_number, []).append(line)
    return {
        "total": total,
        "items": [_order_dict(o, lines_by_order.get(o.purchase_order_number, [])) for o in page],
    }


@router.get("/purchase-orders/{purchase_order_number}")
def get_purchase_order(purchase_order_number: str, db: Session = Depends(get_db)):
    order, lines = _load_order(db, purchase_order_number)
    return _order_dict(order, lines)


@router.post("/purchase-orders/{purchase_order_number}/receive")
def receive_purchase_order(
    purchase_order_number: str,
    payload: ReceivePayload,
    db: Session = Depends(get_db),
):
    """到货收货：行累计 received_quantity，物料库存实时回冲。

    - 单状态限 RELEASED / PARTIALLY_RECEIVED（RECEIVED/CLOSED 拒绝）；
    - 超量收货拒绝（累计不得超过行数量）；
    - 全部行收满 → 单据 RECEIVED，否则 PARTIALLY_RECEIVED；
    - 幂等保护：余量不足时给出明确错误而不是静默多收。
    """
    order, lines = _load_order(db, purchase_order_number)
    if order.status not in RECEIVABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购单状态为 {_s(order.status)}，不允许收货",
        )

    line_map = {line.line_number: line for line in lines}
    targets = payload.lines or [
        ReceiveItem(line_number=line.line_number, quantity=None) for line in lines
    ]
    if not targets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="收货行为空")

    received_any = False
    for item in targets:
        line = line_map.get(item.line_number)
        if line is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"采购行不存在: {purchase_order_number}#{item.line_number}",
            )
        outstanding = _f(line.quantity) - _f(line.received_quantity)
        if item.quantity is not None:
            if _f(item.quantity) > outstanding:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"行 {item.line_number} 收货超量：余量 {outstanding}，请求 {_f(item.quantity)}",
                )
            quantity = _f(item.quantity)
        else:
            quantity = outstanding
        if quantity <= 0:
            continue

        # 库存回冲（原料入库）
        material = (
            db.query(Material)
            .filter(
                Material.material_code == line.material_code,
                Material.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if material is not None:
            material.current_stock = (_f(material.current_stock) + quantity)

        line.received_quantity = _f(line.received_quantity) + quantity
        line.status = "RECEIVED" if _f(line.received_quantity) >= _f(line.quantity) else "PARTIAL"
        if payload.remarks:
            line.remarks = payload.remarks
        received_any = True

    if received_any:
        lines_full = all(
            _f(l.received_quantity) >= _f(l.quantity) for l in lines
        )
        order.status = (
            PurchaseOrderStatus.RECEIVED if lines_full else PurchaseOrderStatus.PARTIALLY_RECEIVED
        )
        if payload.remarks:
            order.remarks = payload.remarks
        order.updated_at = datetime.now()

    db.commit()
    order, lines = _load_order(db, purchase_order_number)
    return _order_dict(order, lines)


@router.post("/purchase-orders/{purchase_order_number}/close")
def close_purchase_order(purchase_order_number: str, db: Session = Depends(get_db)):
    order, _ = _load_order(db, purchase_order_number)
    if order.status == PurchaseOrderStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购单已关闭: {purchase_order_number}",
        )
    if order.status == PurchaseOrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购单已作废: {purchase_order_number}",
        )
    order.status = PurchaseOrderStatus.CLOSED
    order.updated_at = datetime.now()
    db.commit()
    order, lines = _load_order(db, purchase_order_number)
    return _order_dict(order, lines)
