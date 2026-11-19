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
    Supplier,
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

    # ── 第一阶段：全量校验并生成收货计划（任一失败整单不落库） ──
    planned: list[tuple[PurchaseOrderLine, float]] = []
    if payload.lines:
        wanted: dict[int, float | None] = {}
        for item in payload.lines:
            line = line_map.get(item.line_number)
            if line is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"采购行不存在: {purchase_order_number}#{item.line_number}",
                )
            if item.quantity is None:
                wanted[item.line_number] = None  # 整行余量，优先级最高
                continue
            if wanted.get(item.line_number, 0.0) is None:
                continue  # 已被「整行余量」覆盖，忽略后续显式数量
            wanted[item.line_number] = wanted.get(item.line_number, 0.0) + _f(item.quantity)

        for line_number, quantity in wanted.items():
            line = line_map[line_number]
            outstanding = _f(line.quantity) - _f(line.received_quantity)
            target = outstanding if quantity is None else quantity
            if target <= 0:
                continue
            if target > outstanding:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"行 {line_number} 收货超量：余量 {outstanding}，请求 {_f(target)}",
                )
            planned.append((line, target))
    else:
        for line in lines:
            outstanding = _f(line.quantity) - _f(line.received_quantity)
            if outstanding > 0:
                planned.append((line, outstanding))

    if not planned:
        # 没有可收数量：保持单据原状（幂等），不产生任何写入
        return _order_dict(order, lines)

    # ── 第二阶段：落库（此时已无校验失败可能） ──
    for line, quantity in planned:
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
            material.current_stock = _f(material.current_stock) + quantity

        line.received_quantity = _f(line.received_quantity) + quantity
        line.status = "RECEIVED" if _f(line.received_quantity) >= _f(line.quantity) else "PARTIAL"
        if payload.remarks:
            line.remarks = payload.remarks

    lines_full = all(_f(l.received_quantity) >= _f(l.quantity) for l in lines)
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


# ── 供应商主数据 ────────────────────────────────────────────────────────
def _supplier_dict(supplier) -> dict:
    return {
        "supplier_code": supplier.supplier_code,
        "supplier_name": supplier.supplier_name,
        "short_name": supplier.short_name,
        "supplier_type": supplier.supplier_type,
        "status": supplier.status,
        "contact_person": supplier.contact_person,
        "contact_phone": supplier.contact_phone,
        "email": supplier.email,
        "address": supplier.address,
        "tax_number": supplier.tax_number,
        "bank_account": supplier.bank_account,
        "payment_terms": supplier.payment_terms,
        "lead_time_days": supplier.lead_time_days,
        "default_currency": supplier.default_currency,
        "rating": supplier.rating,
        "remarks": supplier.remarks,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
    }


def _load_supplier(db: Session, code: str):
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.supplier_code == code,
            Supplier.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if supplier is None:
        raise HTTPException(status_code=404, detail=f"供应商不存在: {code}")
    return supplier


class SupplierPayload(BaseModel):
    supplier_name: str
    short_name: Optional[str] = None
    supplier_type: str = "MATERIAL"
    status: str = "ACTIVE"
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_number: Optional[str] = None
    bank_account: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: int = 0
    default_currency: str = "CNY"
    rating: int = 3
    remarks: Optional[str] = None


@router.get("/suppliers")
def list_suppliers(
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    supplier_type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """供应商列表：可按状态/类型/关键字过滤。"""
    query = db.query(Supplier).filter(Supplier.is_deleted == False)  # noqa: E712
    if status:
        query = query.filter(Supplier.status == status)
    if supplier_type:
        query = query.filter(Supplier.supplier_type == supplier_type)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Supplier.supplier_code.like(like)) | (Supplier.supplier_name.like(like))
        )
    total = query.count()
    rows = query.order_by(Supplier.supplier_code).offset(skip).limit(limit).all()
    return {"total": total, "items": [_supplier_dict(r) for r in rows]}


@router.get("/suppliers/refs")
def list_supplier_refs(db: Session = Depends(get_db)):
    """下拉引用：仅返回编码 + 名称（供采购单/PR 表单选择）。"""
    rows = (
        db.query(Supplier)
        .filter(
            Supplier.is_deleted == False,  # noqa: E712
            Supplier.status == "ACTIVE",
        )
        .order_by(Supplier.supplier_code)
        .all()
    )
    return [
        {"supplier_code": r.supplier_code, "supplier_name": r.supplier_name} for r in rows
    ]


@router.get("/suppliers/{supplier_code}")
def get_supplier(supplier_code: str, db: Session = Depends(get_db)):
    supplier = _load_supplier(db, supplier_code)
    return _supplier_dict(supplier)


@router.post("/suppliers", status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierPayload, db: Session = Depends(get_db)):
    # 供应商编码自动生成（演示口径 SUP-xxxx，按序号递增）
    last = db.query(Supplier).order_by(Supplier.id.desc()).first()
    seq = (last.id + 1) if last else 1
    supplier_code = f"SUP-{seq:04d}"
    row = Supplier(
        supplier_code=supplier_code,
        supplier_name=payload.supplier_name,
        short_name=payload.short_name,
        supplier_type=payload.supplier_type,
        status=payload.status,
        contact_person=payload.contact_person,
        contact_phone=payload.contact_phone,
        email=payload.email,
        address=payload.address,
        tax_number=payload.tax_number,
        bank_account=payload.bank_account,
        payment_terms=payload.payment_terms,
        lead_time_days=payload.lead_time_days,
        default_currency=payload.default_currency,
        rating=payload.rating,
        remarks=payload.remarks,
        created_by="web",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _supplier_dict(row)


@router.put("/suppliers/{supplier_code}")
def update_supplier(
    supplier_code: str, payload: SupplierPayload, db: Session = Depends(get_db)
):
    row = _load_supplier(db, supplier_code)
    for field in payload.dict(exclude_unset=True):
        setattr(row, field, payload.dict()[field])
    row.updated_by = "web"
    db.commit()
    db.refresh(row)
    return _supplier_dict(row)


@router.post("/suppliers/{supplier_code}/toggle")
def toggle_supplier(supplier_code: str, db: Session = Depends(get_db)):
    """停用 / 启用：切换 status = ACTIVE ↔ INACTIVE。"""
    row = _load_supplier(db, supplier_code)
    row.status = "INACTIVE" if row.status == "ACTIVE" else "ACTIVE"
    row.updated_by = "web"
    db.commit()
    db.refresh(row)
    return _supplier_dict(row)


# ── 应付账款视图 ────────────────────────────────────────────────────────
@router.get("/ap-view")
def ap_view(
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """应付账款：按供应商汇总「已到货金额 - 已收货款 = 应付」。

    - 到货金额 = 各采购行 received_quantity × unit_price 之和；
    - 已收货款按整单 CLOSED 视为结清（演示口径），否则记 0；
    - 应收 = 到货金额 - 已收货款。
    """
    lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.is_deleted == False)  # noqa: E712
        .all()
    )
    orders = {
        o.purchase_order_number: o
        for o in db.query(PurchaseOrder)
        .filter(PurchaseOrder.is_deleted == False)  # noqa: E712
        .all()
    }

    by_supplier: dict[str, dict] = {}
    for line in lines:
        order = orders.get(line.purchase_order_number)
        if order is None:
            continue
        sid = order.supplier_id or "未指定"
        sname = order.supplier_name or sid
        if supplier_id and sid != supplier_id:
            continue
        bucket = by_supplier.setdefault(
            sid,
            {
                "supplier_id": sid,
                "supplier_name": sname,
                "received_amount": 0.0,
                "closed_amount": 0.0,
                "payable_amount": 0.0,
            },
        )
        received_qty = _f(line.received_quantity)
        received_amount = received_qty * _f(line.unit_price)
        bucket["received_amount"] += received_amount
        if order.status == PurchaseOrderStatus.CLOSED:
            bucket["closed_amount"] += received_amount
        bucket["payable_amount"] += received_amount

    for bucket in by_supplier.values():
        bucket["payable_amount"] = round(bucket["payable_amount"] - bucket["closed_amount"], 2)
        bucket["received_amount"] = round(bucket["received_amount"], 2)
        bucket["closed_amount"] = round(bucket["closed_amount"], 2)

    items = sorted(by_supplier.values(), key=lambda x: -x["payable_amount"])
    total_payable = round(sum(x["payable_amount"] for x in items), 2)
    return {
        "total_payable": total_payable,
        "total_received": round(sum(x["received_amount"] for x in items), 2),
        "items": items,
    }
