"""双向追溯 router：LOT / 物料 / 订单 全链路只读派生查询（ADR-20261118-01）。"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.services.planning.traceability_engine import TraceEngine

router = APIRouter()


@router.get("/overview")
def trace_overview(db: Session = Depends(get_db)):
    """可追溯对象概览（各单据数量）。"""
    return TraceEngine.overview(db)


@router.get("/search")
def trace_search(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """根节点搜索：批次/工单/销售订单/物料/NCR。"""
    return {"items": TraceEngine.search(db, q, limit)}


@router.get("/lots/{lot_number}")
def trace_lot(lot_number: str, db: Session = Depends(get_db)):
    """正向追溯：批次 → 工单 → 销售/客户 + 领料/报工/检验/NCR/设备故障。"""
    try:
        return TraceEngine.trace_lot(db, lot_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/materials/{material_code}")
def trace_material(material_code: str, db: Session = Depends(get_db)):
    """反向追溯：物料 → 领料/工单/批次/销售/客户 + 检验/NCR/故障/采购。"""
    try:
        return TraceEngine.trace_material(db, material_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/orders/{order_number}")
def trace_order(order_number: str, db: Session = Depends(get_db)):
    """从订单出发（自动识别生产/销售订单）。"""
    try:
        return TraceEngine.trace_order(db, order_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
