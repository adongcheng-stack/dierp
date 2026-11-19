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
from backend.common.models.mm import Material, MaterialTransaction
from backend.common.models.planning import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    PurchaseRequest,
    PurchaseRequestLine,
    PurchaseRequestStatus,
    PurchaseReturn,
    PurchaseReturnLine,
    ReturnType,
    ReturnStatus,
    Supplier,
)
from backend.common.utils.number_generator import NumberGenerator

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
    """到货请求：不传 quantity 时按「未收余量」整行收货。

    auto_iqc=True 时为每个收货行自动生成 INCOMING 来料检验单（DRAFT）。
    """

    lines: list[ReceiveItem] = Field(default_factory=list)
    remarks: Optional[str] = None
    received_by: Optional[str] = None
    auto_iqc: bool = False


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

    # 到货自动来料检验（IQC）：每个收货行生成一张 DRAFT 检验单，与收货同事务提交
    auto_iqc_numbers: list[str] = []
    if payload.auto_iqc:
        from backend.common.models.planning import InspectionType
        from backend.services.planning.qms_engine import QmsEngine

        for line, quantity in planned:
            row = QmsEngine.create_inspection(
                db,
                inspection_type=InspectionType.INCOMING,
                material_code=line.material_code,
                purchase_order_number=purchase_order_number,
                quantity_inspected=quantity,
                inspector=payload.received_by or "system",
                remarks=f"收货自动生成: {purchase_order_number}#{line.line_number}",
                created_by=payload.received_by or "web",
            )
            auto_iqc_numbers.append(row.inspection_number)

    db.commit()
    order, lines = _load_order(db, purchase_order_number)
    result = _order_dict(order, lines)
    if auto_iqc_numbers:
        result["auto_iqc_inspections"] = auto_iqc_numbers
    return result


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
    """应付账款：按供应商汇总「净到货金额 - 已结金额 = 应付」。

    - 到货金额 = 各采购行 received_quantity × unit_price 之和；
    - 已整单关闭（CLOSED）视为结清（演示口径）；
    - 审批通过的退货（RETURN）冲减净到货与应付；
    - 应付 = 净到货金额 - 已结金额。
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
                "returned_amount": 0.0,
                "closed_amount": 0.0,
                "payable_amount": 0.0,
            },
        )
        received_qty = _f(line.received_quantity)
        received_amount = received_qty * _f(line.unit_price)
        bucket["received_amount"] += received_amount
        if order.status == PurchaseOrderStatus.CLOSED:
            bucket["closed_amount"] += received_amount

    # 审批通过的退货（RETURN）冲减净到货与应付；来源采购单已关闭的，同冲减已结金额
    approved_returns = (
        db.query(PurchaseReturn)
        .filter(
            PurchaseReturn.is_deleted == False,  # noqa: E712
            PurchaseReturn.return_type == ReturnType.RETURN,
            PurchaseReturn.status.in_([ReturnStatus.APPROVED, ReturnStatus.CLOSED]),
        )
        .all()
    )
    for ret in approved_returns:
        sid = ret.supplier_id or "未指定"
        if supplier_id and sid != supplier_id:
            continue
        bucket = by_supplier.get(sid)
        if bucket is None:
            order = orders.get(ret.purchase_order_number)
            bucket = by_supplier.setdefault(
                sid,
                {
                    "supplier_id": sid,
                    "supplier_name": (order.supplier_name if order else None) or sid,
                    "received_amount": 0.0,
                    "returned_amount": 0.0,
                    "closed_amount": 0.0,
                    "payable_amount": 0.0,
                },
            )
        amount = _f(ret.total_amount)
        bucket["returned_amount"] += amount
        bucket["received_amount"] -= amount
        bucket["closed_amount"] -= amount

    for bucket in by_supplier.values():
        bucket["received_amount"] = round(bucket["received_amount"], 2)
        bucket["returned_amount"] = round(bucket.get("returned_amount", 0.0), 2)
        bucket["closed_amount"] = round(max(bucket["closed_amount"], 0.0), 2)
        bucket["payable_amount"] = round(
            bucket["received_amount"] - bucket["closed_amount"], 2
        )

    items = sorted(by_supplier.values(), key=lambda x: -x["payable_amount"])
    total_payable = round(sum(x["payable_amount"] for x in items), 2)
    return {
        "total_payable": total_payable,
        "total_received": round(sum(x["received_amount"] for x in items), 2),
        "items": items,
    }


# ── 采购申请（PR）───────────────────────────────────────────────────────
def _pr_line_dict(line: PurchaseRequestLine) -> dict:
    return {
        "line_number": line.line_number,
        "material_code": line.material_code,
        "quantity": _f(line.quantity),
        "unit": line.unit,
        "unit_price": _f(line.unit_price),
        "expected_date": line.expected_date.isoformat() if line.expected_date else None,
        "status": _s(line.status),
        "remarks": line.remarks,
    }


def _pr_dict(pr: PurchaseRequest, lines: list[PurchaseRequestLine]) -> dict:
    return {
        "purchase_request_number": pr.purchase_request_number,
        "supplier_id": pr.supplier_id,
        "supplier_name": pr.supplier_name,
        "status": _s(pr.status),
        "request_date": pr.request_date.isoformat() if pr.request_date else None,
        "expected_date": pr.expected_date.isoformat() if pr.expected_date else None,
        "currency": pr.currency,
        "total_amount": _f(pr.total_amount),
        "source_planned_order": pr.source_planned_order,
        "requested_by": pr.requested_by,
        "converted_po_number": pr.converted_po_number,
        "remarks": pr.remarks,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "lines": [_pr_line_dict(line) for line in lines],
    }


def _load_pr(db: Session, number: str) -> tuple[PurchaseRequest, list[PurchaseRequestLine]]:
    pr = (
        db.query(PurchaseRequest)
        .filter(
            PurchaseRequest.purchase_request_number == number,
            PurchaseRequest.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if pr is None:
        raise HTTPException(status_code=404, detail=f"采购申请不存在: {number}")
    lines = (
        db.query(PurchaseRequestLine)
        .filter(
            PurchaseRequestLine.purchase_request_number == number,
            PurchaseRequestLine.is_deleted == False,  # noqa: E712
        )
        .order_by(PurchaseRequestLine.line_number)
        .all()
    )
    return pr, lines


class PRLineItem(BaseModel):
    material_code: str
    quantity: float = Field(gt=0)
    unit: Optional[str] = None
    unit_price: float = 0
    expected_date: Optional[datetime] = None
    remarks: Optional[str] = None


class PRCreatePayload(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    expected_date: Optional[datetime] = None
    source_planned_order: Optional[str] = None
    requested_by: Optional[str] = None
    remarks: Optional[str] = None
    lines: list[PRLineItem] = Field(min_length=1)


@router.get("/purchase-requests")
def list_purchase_requests(
    skip: int = 0,
    limit: int = 200,
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier_id: Optional[str] = None,
    material_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """采购申请列表（含行）。"""
    query = db.query(PurchaseRequest).filter(PurchaseRequest.is_deleted == False)  # noqa: E712
    if status_filter:
        query = query.filter(PurchaseRequest.status == status_filter)
    if supplier_id:
        query = query.filter(PurchaseRequest.supplier_id == supplier_id)
    prs = query.order_by(PurchaseRequest.id.desc()).all()
    if material_code:
        hit_numbers = {
            line.purchase_request_number
            for line in db.query(PurchaseRequestLine)
            .filter(
                PurchaseRequestLine.material_code == material_code,
                PurchaseRequestLine.is_deleted == False,  # noqa: E712
            )
            .all()
        }
        prs = [p for p in prs if p.purchase_request_number in hit_numbers]

    total = len(prs)
    page = prs[skip : skip + limit]
    all_lines = (
        db.query(PurchaseRequestLine)
        .filter(PurchaseRequestLine.is_deleted == False)  # noqa: E712
        .all()
    )
    lines_by_pr: dict[str, list[PurchaseRequestLine]] = {}
    for line in all_lines:
        lines_by_pr.setdefault(line.purchase_request_number, []).append(line)
    return {
        "total": total,
        "items": [_pr_dict(p, lines_by_pr.get(p.purchase_request_number, [])) for p in page],
    }


@router.get("/purchase-requests/{purchase_request_number}")
def get_purchase_request(purchase_request_number: str, db: Session = Depends(get_db)):
    pr, lines = _load_pr(db, purchase_request_number)
    return _pr_dict(pr, lines)


@router.post("/purchase-requests", status_code=status.HTTP_201_CREATED)
def create_purchase_request(payload: PRCreatePayload, db: Session = Depends(get_db)):
    """创建采购申请（DRAFT）：两阶段——先全量校验物料与单位，再统一落库。"""
    # ── 第一阶段：全量校验并解析行（任一失败整单不落库） ──
    planned: list[dict] = []
    material_codes = [item.material_code for item in payload.lines]
    materials = {
        m.material_code: m
        for m in db.query(Material)
        .filter(
            Material.material_code.in_(material_codes),
            Material.is_deleted == False,  # noqa: E712
        )
        .all()
    }
    for index, item in enumerate(payload.lines, start=1):
        material = materials.get(item.material_code)
        if material is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"物料不存在: {item.material_code}",
            )
        planned.append(
            {
                "line_number": index,
                "material_code": item.material_code,
                "quantity": _f(item.quantity),
                "unit": item.unit or material.unit,
                "unit_price": _f(item.unit_price),
                "expected_date": item.expected_date or payload.expected_date,
                "remarks": item.remarks,
            }
        )

    # ── 第二阶段：落库 ──
    number = NumberGenerator.generate_document_number(
        db, PurchaseRequest, "purchase_request_number", "PRQ", 4
    )
    pr = PurchaseRequest(
        purchase_request_number=number,
        supplier_id=payload.supplier_id,
        supplier_name=payload.supplier_name,
        status=PurchaseRequestStatus.DRAFT,
        request_date=datetime.now(),
        expected_date=payload.expected_date,
        currency="CNY",
        total_amount=round(sum(row["quantity"] * row["unit_price"] for row in planned), 2),
        source_planned_order=payload.source_planned_order,
        requested_by=payload.requested_by,
        remarks=payload.remarks,
        created_by="web",
    )
    db.add(pr)
    db.flush()
    for row in planned:
        db.add(PurchaseRequestLine(purchase_request_number=number, **row, created_by="web"))
    db.commit()
    pr, lines = _load_pr(db, number)
    return _pr_dict(pr, lines)


def _pr_transition(db: Session, number: str, allowed, target, action: str) -> dict:
    pr, lines = _load_pr(db, number)
    if pr.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购申请状态为 {_s(pr.status)}，不允许{action}",
        )
    pr.status = target
    pr.updated_at = datetime.now()
    db.commit()
    pr, lines = _load_pr(db, number)
    return _pr_dict(pr, lines)


@router.post("/purchase-requests/{purchase_request_number}/release")
def release_purchase_request(purchase_request_number: str, db: Session = Depends(get_db)):
    """下达采购申请（DRAFT → RELEASED），下达后才允许转采购单。"""
    return _pr_transition(
        db,
        purchase_request_number,
        {PurchaseRequestStatus.DRAFT},
        PurchaseRequestStatus.RELEASED,
        "下达",
    )


@router.post("/purchase-requests/{purchase_request_number}/cancel")
def cancel_purchase_request(purchase_request_number: str, db: Session = Depends(get_db)):
    """作废采购申请（DRAFT/RELEASED → CANCELLED）。"""
    return _pr_transition(
        db,
        purchase_request_number,
        {PurchaseRequestStatus.DRAFT, PurchaseRequestStatus.RELEASED},
        PurchaseRequestStatus.CANCELLED,
        "作废",
    )


@router.post("/purchase-requests/{purchase_request_number}/convert")
def convert_purchase_request(purchase_request_number: str, db: Session = Depends(get_db)):
    """整单转采购单（RELEASED → CONVERTED）：

    - 生成 RELEASED 状态的采购单（行原样拷贝）；
    - 供应商/期望日期/币种继承申请单；
    - 回写 converted_po_number，行状态置 CONVERTED；
    - PO.source_planned_order 继承申请单的来源计划订单（保持计划追溯链）。
    """
    pr, lines = _load_pr(db, purchase_request_number)
    if pr.status != PurchaseRequestStatus.RELEASED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购申请状态为 {_s(pr.status)}，仅已下达(RELEASED)申请可转采购单",
        )
    open_lines = [line for line in lines if _s(line.status) == "OPEN"]
    if not open_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购申请无可转换行: {purchase_request_number}",
        )

    po_number = NumberGenerator.generate_document_number(
        db, PurchaseOrder, "purchase_order_number", "PUR", 4
    )
    order = PurchaseOrder(
        purchase_order_number=po_number,
        supplier_id=pr.supplier_id,
        supplier_name=pr.supplier_name,
        status=PurchaseOrderStatus.RELEASED,
        order_date=datetime.now(),
        expected_date=pr.expected_date,
        currency=pr.currency or "CNY",
        total_amount=round(sum(_f(l.quantity) * _f(l.unit_price) for l in open_lines), 2),
        source_planned_order=pr.source_planned_order,
        remarks=f"来源采购申请: {pr.purchase_request_number}",
        created_by="web",
    )
    db.add(order)
    db.flush()
    for line in open_lines:
        db.add(
            PurchaseOrderLine(
                purchase_order_number=po_number,
                line_number=line.line_number,
                material_code=line.material_code,
                quantity=line.quantity,
                received_quantity=0,
                unit=line.unit,
                unit_price=line.unit_price,
                expected_date=line.expected_date or pr.expected_date,
                status="OPEN",
                created_by="web",
            )
        )
        line.status = "CONVERTED"
    pr.status = PurchaseRequestStatus.CONVERTED
    pr.converted_po_number = po_number
    pr.updated_at = datetime.now()
    db.commit()
    pr, lines = _load_pr(db, purchase_request_number)
    return _pr_dict(pr, lines)


# ── 采购退货 / 索赔 ─────────────────────────────────────────────────────
def _return_line_dict(line: PurchaseReturnLine) -> dict:
    return {
        "line_number": line.line_number,
        "purchase_order_line_number": line.purchase_order_line_number,
        "material_code": line.material_code,
        "quantity": _f(line.quantity),
        "unit": line.unit,
        "unit_price": _f(line.unit_price),
        "remarks": line.remarks,
    }


def _return_dict(ret: PurchaseReturn, lines: list[PurchaseReturnLine]) -> dict:
    return {
        "return_number": ret.return_number,
        "purchase_order_number": ret.purchase_order_number,
        "supplier_id": ret.supplier_id,
        "supplier_name": ret.supplier_name,
        "return_type": _s(ret.return_type),
        "status": _s(ret.status),
        "return_date": ret.return_date.isoformat() if ret.return_date else None,
        "total_amount": _f(ret.total_amount),
        "reason": ret.reason,
        "remarks": ret.remarks,
        "created_at": ret.created_at.isoformat() if ret.created_at else None,
        "lines": [_return_line_dict(line) for line in lines],
    }


def _load_return(db: Session, number: str) -> tuple[PurchaseReturn, list[PurchaseReturnLine]]:
    ret = (
        db.query(PurchaseReturn)
        .filter(
            PurchaseReturn.return_number == number,
            PurchaseReturn.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if ret is None:
        raise HTTPException(status_code=404, detail=f"退货索赔单不存在: {number}")
    lines = (
        db.query(PurchaseReturnLine)
        .filter(
            PurchaseReturnLine.return_number == number,
            PurchaseReturnLine.is_deleted == False,  # noqa: E712
        )
        .order_by(PurchaseReturnLine.line_number)
        .all()
    )
    return ret, lines


def _returned_quantity_by_line(db: Session, po_number: str) -> dict[int, float]:
    """按采购行号汇总「已占用退货量」：RETURN 类型且单据非 REJECTED（DRAFT 占用、APPROVED/CLOSED 已退）。"""
    rows = (
        db.query(PurchaseReturnLine, PurchaseReturn)
        .join(
            PurchaseReturn,
            PurchaseReturn.return_number == PurchaseReturnLine.return_number,
        )
        .filter(
            PurchaseReturn.purchase_order_number == po_number,
            PurchaseReturn.return_type == ReturnType.RETURN,
            PurchaseReturn.status != ReturnStatus.REJECTED,
            PurchaseReturnLine.is_deleted == False,  # noqa: E712
            PurchaseReturn.is_deleted == False,  # noqa: E712
        )
        .all()
    )
    totals: dict[int, float] = {}
    for line, _header in rows:
        key = int(line.purchase_order_line_number or 0)
        totals[key] = totals.get(key, 0.0) + _f(line.quantity)
    return totals


class ReturnLineItem(BaseModel):
    purchase_order_line_number: int = Field(ge=1)
    quantity: float = Field(gt=0)
    unit_price: Optional[float] = None  # 不传则取采购行单价
    remarks: Optional[str] = None


class ReturnCreatePayload(BaseModel):
    purchase_order_number: str
    return_type: str = "RETURN"  # RETURN=退货（扣库存） / CLAIM=索赔（只记金额）
    reason: Optional[str] = None
    remarks: Optional[str] = None
    lines: list[ReturnLineItem] = Field(min_length=1)


@router.get("/purchase-returns")
def list_purchase_returns(
    skip: int = 0,
    limit: int = 200,
    status_filter: Optional[str] = Query(None, alias="status"),
    return_type: Optional[str] = None,
    purchase_order_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """退货/索赔单列表（含行）。"""
    query = db.query(PurchaseReturn).filter(PurchaseReturn.is_deleted == False)  # noqa: E712
    if status_filter:
        query = query.filter(PurchaseReturn.status == status_filter)
    if return_type:
        query = query.filter(PurchaseReturn.return_type == return_type)
    if purchase_order_number:
        query = query.filter(PurchaseReturn.purchase_order_number == purchase_order_number)
    rets = query.order_by(PurchaseReturn.id.desc()).all()
    total = len(rets)
    page = rets[skip : skip + limit]
    all_lines = (
        db.query(PurchaseReturnLine)
        .filter(PurchaseReturnLine.is_deleted == False)  # noqa: E712
        .all()
    )
    lines_by_return: dict[str, list[PurchaseReturnLine]] = {}
    for line in all_lines:
        lines_by_return.setdefault(line.return_number, []).append(line)
    return {
        "total": total,
        "items": [_return_dict(r, lines_by_return.get(r.return_number, [])) for r in page],
    }


@router.get("/purchase-returns/{return_number}")
def get_purchase_return(return_number: str, db: Session = Depends(get_db)):
    ret, lines = _load_return(db, return_number)
    return _return_dict(ret, lines)


@router.post("/purchase-returns", status_code=status.HTTP_201_CREATED)
def create_purchase_return(payload: ReturnCreatePayload, db: Session = Depends(get_db)):
    """创建退货/索赔单（DRAFT）：先全量校验可退余量，再统一落库。

    - RETURN（退货）：可退量 = 行已收量 − 已占用退货量（非 REJECTED 的 RETURN 单）；
    - CLAIM（索赔）：只登记金额，不占用/不扣减任何数量；
    - 审批通过（APPROVED）时 RETURN 才真正扣减库存并记库存事务。
    """
    if payload.return_type not in (ReturnType.RETURN.value, ReturnType.CLAIM.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"return_type 必须为 RETURN/CLAIM，收到: {payload.return_type}",
        )
    order, po_lines = _load_order(db, payload.purchase_order_number)
    if order.status not in (
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
        PurchaseOrderStatus.RECEIVED,
        PurchaseOrderStatus.CLOSED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"采购单状态为 {_s(order.status)}，无已到货数量可退/可索赔",
        )
    line_map = {line.line_number: line for line in po_lines}
    returned_totals = (
        _returned_quantity_by_line(db, payload.purchase_order_number)
        if payload.return_type == ReturnType.RETURN.value
        else {}
    )

    # ── 第一阶段：全量校验并解析行 ──
    planned: list[dict] = []
    for index, item in enumerate(payload.lines, start=1):
        po_line = line_map.get(item.purchase_order_line_number)
        if po_line is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"采购行不存在: {payload.purchase_order_number}#{item.purchase_order_line_number}",
            )
        received = _f(po_line.received_quantity)
        if payload.return_type == ReturnType.RETURN.value:
            available = received - returned_totals.get(item.purchase_order_line_number, 0.0)
            if _f(item.quantity) > available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"行 {item.purchase_order_line_number} 退货超量："
                        f"已收 {received}，已占用退货 {returned_totals.get(item.purchase_order_line_number, 0.0)}，"
                        f"可退 {round(available, 2)}，请求 {_f(item.quantity)}"
                    ),
                )
        planned.append(
            {
                "line_number": index,
                "purchase_order_line_number": item.purchase_order_line_number,
                "material_code": po_line.material_code,
                "quantity": _f(item.quantity),
                "unit": po_line.unit,
                "unit_price": _f(item.unit_price) if item.unit_price is not None else _f(po_line.unit_price),
                "remarks": item.remarks,
            }
        )

    # ── 第二阶段：落库 ──
    number = NumberGenerator.generate_document_number(
        db, PurchaseReturn, "return_number", "RTN", 4
    )
    ret = PurchaseReturn(
        return_number=number,
        purchase_order_number=payload.purchase_order_number,
        supplier_id=order.supplier_id,
        supplier_name=order.supplier_name,
        return_type=ReturnType(payload.return_type),
        status=ReturnStatus.DRAFT,
        return_date=datetime.now(),
        total_amount=round(sum(row["quantity"] * row["unit_price"] for row in planned), 2),
        reason=payload.reason,
        remarks=payload.remarks,
        created_by="web",
    )
    db.add(ret)
    db.flush()
    for row in planned:
        db.add(PurchaseReturnLine(return_number=number, **row, created_by="web"))
    db.commit()
    ret, lines = _load_return(db, number)
    return _return_dict(ret, lines)


@router.post("/purchase-returns/{return_number}/approve")
def approve_purchase_return(return_number: str, db: Session = Depends(get_db)):
    """审批通过（DRAFT → APPROVED）。

    RETURN 类型：扣减物料库存（两阶段：先校验库存充足，再扣减 + 记 RETURN 库存事务）；
    CLAIM 类型：只确认索赔金额，不动库存。
    """
    ret, lines = _load_return(db, return_number)
    if ret.status != ReturnStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"退货索赔单状态为 {_s(ret.status)}，仅草稿(DRAFT)可审批",
        )

    if ret.return_type == ReturnType.RETURN:
        # ── 第一阶段：库存充足性校验 ──
        stock_map: dict[str, Material] = {}
        for line in lines:
            material = (
                db.query(Material)
                .filter(
                    Material.material_code == line.material_code,
                    Material.is_deleted == False,  # noqa: E712
                )
                .first()
            )
            stock_map[line.material_code] = material
            need = sum(_f(l.quantity) for l in lines if l.material_code == line.material_code)
            have = _f(material.current_stock) if material is not None else 0.0
            if have < need:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"库存不足，无法退货: {line.material_code} 当前 {have}，需退 {need}",
                )
        # ── 第二阶段：扣库存 + 记库存事务 ──
        for line in lines:
            material = stock_map[line.material_code]
            if material is not None:
                material.current_stock = _f(material.current_stock) - _f(line.quantity)
                material.updated_at = datetime.now()
            transaction_number = NumberGenerator.generate_document_number(
                db, MaterialTransaction, "transaction_number", "TR", 4
            )
            db.add(
                MaterialTransaction(
                    transaction_number=transaction_number,
                    material_code=line.material_code,
                    transaction_type="RETURN",
                    quantity=-_f(line.quantity),
                    unit=line.unit,
                    reference_number=return_number,
                    reference_type="PURCHASE_RETURN",
                    transaction_date=datetime.now(),
                    operator="web",
                    remarks=f"采购退货: {ret.purchase_order_number}",
                    created_by="web",
                )
            )

    ret.status = ReturnStatus.APPROVED
    ret.updated_at = datetime.now()
    db.commit()
    ret, lines = _load_return(db, return_number)
    return _return_dict(ret, lines)


@router.post("/purchase-returns/{return_number}/reject")
def reject_purchase_return(return_number: str, db: Session = Depends(get_db)):
    """驳回（DRAFT → REJECTED）：RETURN 占用的可退量随即释放。"""
    ret, _ = _load_return(db, return_number)
    if ret.status != ReturnStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"退货索赔单状态为 {_s(ret.status)}，仅草稿(DRAFT)可驳回",
        )
    ret.status = ReturnStatus.REJECTED
    ret.updated_at = datetime.now()
    db.commit()
    ret, lines = _load_return(db, return_number)
    return _return_dict(ret, lines)


@router.post("/purchase-returns/{return_number}/close")
def close_purchase_return(return_number: str, db: Session = Depends(get_db)):
    """关闭（APPROVED → CLOSED）：单据归档，保持已生效的数量/金额口径。"""
    ret, _ = _load_return(db, return_number)
    if ret.status != ReturnStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"退货索赔单状态为 {_s(ret.status)}，仅已审批(APPROVED)可关闭",
        )
    ret.status = ReturnStatus.CLOSED
    ret.updated_at = datetime.now()
    db.commit()
    ret, lines = _load_return(db, return_number)
    return _return_dict(ret, lines)
