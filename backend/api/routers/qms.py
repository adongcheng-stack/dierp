"""QMS router: 来料/过程/终检检验单 + 不合格品（NCR）闭环，与报工 & EAM 联动。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.routers.auth import get_current_user
from backend.common.database.base import get_db
from backend.common.models.mm import Material
from backend.common.models.planning import (
    InspectionOrder,
    InspectionResult,
    InspectionStatus,
    InspectionType,
    NcrDisposition,
    NcrSeverity,
    NcrSourceType,
    NcrStatus,
    NonConformanceReport,
)
from backend.common.models.pp import OperationReport, ProductionOrder
from backend.common.models.user import User
from backend.services.planning.qms_engine import QmsEngine

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────
def _f(value) -> float:
    return float(value) if value is not None else 0.0


def _s(value) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _dt(value) -> Optional[str]:
    return value.isoformat() if value else None


def _inspection(row: InspectionOrder) -> dict:
    return {
        "inspection_number": row.inspection_number,
        "inspection_type": _s(row.inspection_type),
        "material_code": row.material_code,
        "lot_number": row.lot_number,
        "purchase_order_number": row.purchase_order_number,
        "report_number": row.report_number,
        "quantity_inspected": _f(row.quantity_inspected),
        "quantity_ok": _f(row.quantity_ok),
        "quantity_rejected": _f(row.quantity_rejected),
        "inspector": row.inspector,
        "inspected_at": _dt(row.inspected_at),
        "result": _s(row.result),
        "status": _s(row.status),
        "remarks": row.remarks,
    }


def _ncr(row: NonConformanceReport) -> dict:
    return {
        "ncr_number": row.ncr_number,
        "source_type": _s(row.source_type),
        "source_ref": row.source_ref,
        "inspection_number": row.inspection_number,
        "report_number": row.report_number,
        "lot_number": row.lot_number,
        "material_code": row.material_code,
        "quantity": _f(row.quantity),
        "defect_code": row.defect_code,
        "defect_desc": row.defect_desc,
        "severity": _s(row.severity),
        "disposition": _s(row.disposition),
        "disposition_note": row.disposition_note,
        "root_cause": row.root_cause,
        "equipment_cause": bool(row.equipment_cause),
        "failure_number": row.failure_number,
        "status": _s(row.status),
        "reviewed_by": row.reviewed_by,
        "reviewed_at": _dt(row.reviewed_at),
        "closed_by": row.closed_by,
        "closed_at": _dt(row.closed_at),
    }


# ── 概览 ───────────────────────────────────────────────────────────────
@router.get("/overview")
def qms_overview(db: Session = Depends(get_db)):
    data = QmsEngine.overview(db)
    # 追加最近的不合格检验单与未关闭 NCR，供工作台直接渲染
    recent_fail = (
        db.query(InspectionOrder)
        .filter(
            InspectionOrder.is_deleted == False,
            InspectionOrder.result == InspectionResult.FAIL,
        )
        .order_by(InspectionOrder.inspected_at.desc())
        .limit(20)
        .all()
    )
    open_ncrs = (
        db.query(NonConformanceReport)
        .filter(
            NonConformanceReport.is_deleted == False,
            NonConformanceReport.status.in_([NcrStatus.OPEN, NcrStatus.UNDER_REVIEW]),
        )
        .order_by(NonConformanceReport.id.desc())
        .limit(20)
        .all()
    )
    data["recent_fail_inspections"] = [_inspection(row) for row in recent_fail]
    data["open_ncr_items"] = [_ncr(row) for row in open_ncrs]
    return data


# ── 检验单 ─────────────────────────────────────────────────────────────
@router.get("/inspections")
def list_inspections(
    inspection_type: Optional[str] = Query(None, alias="type"),
    result: Optional[str] = None,
    material_code: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(InspectionOrder).filter(InspectionOrder.is_deleted == False)
    if inspection_type:
        query = query.filter(InspectionOrder.inspection_type == InspectionType(inspection_type))
    if result:
        query = query.filter(InspectionOrder.result == InspectionResult(result))
    if material_code:
        query = query.filter(InspectionOrder.material_code == material_code)
    if status:
        query = query.filter(InspectionOrder.status == InspectionStatus(status))
    total = query.count()
    rows = query.order_by(InspectionOrder.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_inspection(row) for row in rows]}


@router.get("/inspections/{inspection_number}")
def get_inspection(inspection_number: str, db: Session = Depends(get_db)):
    """检验单详情（单条）。"""
    row = (
        db.query(InspectionOrder)
        .filter(
            InspectionOrder.inspection_number == inspection_number,
            InspectionOrder.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"检验单不存在: {inspection_number}")
    return _inspection(row)


@router.post("/inspections", status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection_type = payload.get("inspection_type")
    material_code = payload.get("material_code")
    if not inspection_type or not material_code:
        raise HTTPException(status_code=400, detail="inspection_type 与 material_code 不能为空")
    inspected_at = payload.get("inspected_at")
    try:
        row = QmsEngine.create_inspection(
            db,
            inspection_type=inspection_type,
            material_code=material_code,
            lot_number=payload.get("lot_number"),
            purchase_order_number=payload.get("purchase_order_number"),
            report_number=payload.get("report_number"),
            quantity_inspected=payload.get("quantity_inspected"),
            inspector=payload.get("inspector") or current_user.username,
            inspected_at=datetime.fromisoformat(str(inspected_at)) if inspected_at else None,
            remarks=payload.get("remarks"),
            created_by=current_user.username,
        )
        db.commit()
        return _inspection(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/inspections/{inspection_number}/complete")
def complete_inspection(
    inspection_number: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = QmsEngine.complete_inspection(
            db,
            inspection_number,
            quantity_ok=payload.get("quantity_ok"),
            quantity_rejected=payload.get("quantity_rejected"),
            inspector=payload.get("inspector"),
            result=payload.get("result"),
            remarks=payload.get("remarks"),
            auto_create_ncr=bool(payload.get("auto_create_ncr", True)),
            updated_by=current_user.username,
        )
        db.commit()
        return _inspection(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


# ── 不合格品闭环 ───────────────────────────────────────────────────────
@router.get("/ncrs")
def list_ncrs(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    material_code: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(NonConformanceReport).filter(NonConformanceReport.is_deleted == False)
    if status:
        query = query.filter(NonConformanceReport.status == NcrStatus(status))
    if source_type:
        query = query.filter(NonConformanceReport.source_type == NcrSourceType(source_type))
    if material_code:
        query = query.filter(NonConformanceReport.material_code == material_code)
    if severity:
        query = query.filter(NonConformanceReport.severity == NcrSeverity(severity))
    total = query.count()
    rows = query.order_by(NonConformanceReport.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_ncr(row) for row in rows]}


@router.post("/ncrs", status_code=status.HTTP_201_CREATED)
def create_ncr(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = QmsEngine.create_ncr(
            db,
            source_type=payload.get("source_type") or "INSPECTION",
            source_ref=payload.get("source_ref"),
            inspection_number=payload.get("inspection_number"),
            report_number=payload.get("report_number"),
            lot_number=payload.get("lot_number"),
            material_code=payload.get("material_code"),
            quantity=payload.get("quantity"),
            defect_code=payload.get("defect_code"),
            defect_desc=payload.get("defect_desc"),
            severity=payload.get("severity") or "MAJOR",
            created_by=current_user.username,
        )
        db.commit()
        return _ncr(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ncrs/{ncr_number}/review")
def review_ncr(
    ncr_number: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = QmsEngine.review_ncr(
            db,
            ncr_number,
            severity=payload.get("severity"),
            root_cause=payload.get("root_cause"),
            equipment_cause=payload.get("equipment_cause"),
            resource_id=payload.get("resource_id"),
            failure_desc=payload.get("failure_desc"),
            reviewed_by=current_user.username,
        )
        db.commit()
        return _ncr(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ncrs/{ncr_number}/disposition")
def disposition_ncr(
    ncr_number: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    disposition = payload.get("disposition")
    if not disposition:
        raise HTTPException(status_code=400, detail="disposition 不能为空")
    try:
        row = QmsEngine.disposition_ncr(
            db,
            ncr_number,
            disposition=disposition,
            disposition_note=payload.get("disposition_note"),
            equipment_cause=payload.get("equipment_cause"),
            resource_id=payload.get("resource_id"),
            failure_desc=payload.get("failure_desc"),
            dispositioned_by=current_user.username,
        )
        db.commit()
        return _ncr(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ncrs/{ncr_number}/close")
def close_ncr(
    ncr_number: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = QmsEngine.close_ncr(
            db,
            ncr_number,
            disposition=payload.get("disposition"),
            disposition_note=payload.get("disposition_note"),
            closed_by=current_user.username,
        )
        db.commit()
        return _ncr(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


# ── 联动辅助：可生成 NCR 的报工单（scrap>0） ──────────────────────────
@router.get("/operation-reports/scrap")
def list_scrap_reports(
    production_order_number: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """返回 scrap_quantity > 0 的报工单，供前端「由报工生成 NCR」下拉选择。"""
    query = db.query(OperationReport).filter(
        OperationReport.is_deleted == False,
        OperationReport.scrap_quantity > 0,
    )
    if production_order_number:
        query = query.filter(OperationReport.production_order_number == production_order_number)
    rows = query.order_by(OperationReport.id.desc()).limit(limit).all()
    order_numbers = {row.production_order_number for row in rows if row.production_order_number}
    material_by_order = {
        order.order_number: order.material_code
        for order in (
            db.query(ProductionOrder)
            .filter(ProductionOrder.order_number.in_(order_numbers))
            .all()
            if order_numbers
            else []
        )
    }
    return {
        "items": [
            {
                "report_number": row.report_number,
                "production_order_number": row.production_order_number,
                "lot_number": row.lot_number,
                "material_code": material_by_order.get(row.production_order_number),
                "work_center_id": row.work_center_id,
                "operation_no": row.operation_no,
                "reported_quantity": _f(row.reported_quantity),
                "scrap_quantity": _f(row.scrap_quantity),
            }
            for row in rows
        ]
    }