"""Planning router: MPS, MRP, planned orders, exceptions, kitting and policies."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.api.routers.auth import get_current_user
from backend.common.database.base import get_db
from backend.common.models.eng import ProductionVersion
from backend.common.models.mm import Material
from backend.common.models.planning import (
    ChangeoverMatrix,
    CostRate,
    CostRateType,
    CostSettlement,
    CostStatus,
    CostVariance,
    EquipmentFailure,
    ExceptionSeverity,
    FailureSeverity,
    FailureStatus,
    Forecast,
    KittingResult,
    KitStatus,
    MaintenanceOrder,
    MaintenancePlan,
    MaintenanceStatus,
    MaintenanceType,
    MpsEntry,
    MpsPlan,
    MrpException,
    MrpRequirement,
    MrpRun,
    MrpRunType,
    PeggingLink,
    PlannedOrder,
    PlannedOrderStatus,
    PlannedOrderType,
    PlanningPolicy,
    ProductionCost,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    ResolutionStatus,
    Resource,
    ResourceStatus,
    ScenarioImpact,
    ScenarioSimulation,
    ScheduleAlgorithm,
    ScheduleException,
    ScheduleExceptionType,
    ScheduleOpStatus,
    ScheduleRun,
    ScheduleRunStatus,
    ScheduledOperation,
    SkillMatrix,
    StandardCost,
    VarianceType,
    WorkCalendar,
)
from backend.common.models.pp import OperationReport, ProductionOrder, ProductionOrderStatus, WorkCenter
from backend.common.models.sd import SalesOrder, SalesOrderStatus
from backend.common.models.user import User, UserRole
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import dec
from backend.services.planning.aps_engine import ApsEngine
from backend.services.planning.cost_engine import CostEngine
from backend.services.planning.demo_reset import reset_planning_demo
from backend.services.planning.eam_engine import EamEngine
from backend.services.planning.kitting_service import KittingService
from backend.services.planning.mps_engine import MpsEngine
from backend.services.planning.mrp_engine import MrpEngine

router = APIRouter()

OPEN_SALES_STATUSES = [SalesOrderStatus.APPROVED, SalesOrderStatus.IN_PRODUCTION]


# ── helpers ────────────────────────────────────────────────────────────
def _f(value) -> float:
    return float(value) if value is not None else 0.0


def _s(value) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _dt(value) -> Optional[str]:
    return value.isoformat() if value else None


def _get_or_404(db: Session, model, *criteria, label: str):
    row = db.query(model).filter(*criteria).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label}不存在")
    return row


# ── schemas ────────────────────────────────────────────────────────────
class MpsGenerateRequest(BaseModel):
    horizon_start: datetime
    horizon_end: datetime
    plan_name: Optional[str] = None
    plant_id: Optional[str] = None
    demand_source: str = "MIXED"
    include_forecast: bool = True
    include_safety_stock: bool = True


class MrpRunRequest(BaseModel):
    horizon_start: datetime
    horizon_end: datetime
    run_type: str = "REGENERATIVE"
    demand_source: str = "AUTO"
    mps_number: Optional[str] = None
    plant_id: Optional[str] = None
    include_forecast: bool = True
    include_safety_stock: bool = True


class PlannedOrderReleaseRequest(BaseModel):
    sales_order_number: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    unit_price: Optional[float] = None
    auto_confirm: bool = True


class ExceptionResolveRequest(BaseModel):
    resolution_status: str = "RESOLVED"
    remarks: Optional[str] = None


class KittingAnalyzeRequest(BaseModel):
    checked_by: Optional[str] = None


class PlanningPolicyPayload(BaseModel):
    material_code: str
    mrp_type: str = "MRP"
    procurement_type: str = "MAKE"
    lot_sizing_rule: str = "LOT_FOR_LOT"
    fixed_lot_size: float = 0
    min_order_qty: float = 0
    max_order_qty: Optional[float] = None
    order_multiple: float = 1
    eoq: Optional[float] = None
    lead_time_days: int = 0
    safety_time_days: int = 0
    safety_stock: float = 0
    reorder_point: float = 0
    planner_code: Optional[str] = None
    abc_class: Optional[str] = None
    is_active: bool = True
    remarks: Optional[str] = None


# ── serializers ────────────────────────────────────────────────────────
def _mps_summary(plan: MpsPlan) -> dict:
    return {
        "id": plan.id,
        "mps_number": plan.mps_number,
        "version": plan.version,
        "plan_name": plan.plan_name,
        "plant_id": plan.plant_id,
        "horizon_start": _dt(plan.horizon_start),
        "horizon_end": _dt(plan.horizon_end),
        "bucket_type": plan.bucket_type,
        "status": _s(plan.status),
        "demand_source": plan.demand_source,
        "total_gross": _f(plan.total_gross),
        "total_planned": _f(plan.total_planned),
        "generated_by": plan.generated_by,
        "generated_at": _dt(plan.generated_at),
        "created_at": _dt(plan.created_at),
    }


def _mps_entry(entry: MpsEntry) -> dict:
    return {
        "id": entry.id,
        "mps_number": entry.mps_number,
        "line_number": entry.line_number,
        "material_code": entry.material_code,
        "bucket_date": _dt(entry.bucket_date),
        "opening_stock": _f(entry.opening_stock),
        "gross_requirement": _f(entry.gross_requirement),
        "sales_demand": _f(entry.sales_demand),
        "forecast_demand": _f(entry.forecast_demand),
        "scheduled_receipt": _f(entry.scheduled_receipt),
        "projected_available": _f(entry.projected_available),
        "net_requirement": _f(entry.net_requirement),
        "planned_receipt": _f(entry.planned_receipt),
        "planner_action": _s(entry.planner_action),
    }


def _run_summary(run: MrpRun) -> dict:
    return {
        "id": run.id,
        "run_number": run.run_number,
        "run_type": _s(run.run_type),
        "status": _s(run.status),
        "horizon_start": _dt(run.horizon_start),
        "horizon_end": _dt(run.horizon_end),
        "demand_source": run.demand_source,
        "mps_number": run.mps_number,
        "plant_id": run.plant_id,
        "total_demands": run.total_demands,
        "total_requirements": run.total_requirements,
        "planned_production_count": run.planned_production_count,
        "planned_purchase_count": run.planned_purchase_count,
        "exception_count": run.exception_count,
        "shortage_count": run.shortage_count,
        "started_at": _dt(run.started_at),
        "finished_at": _dt(run.finished_at),
        "run_by": run.run_by,
        "log_text": run.log_text,
    }


def _requirement(row: MrpRequirement) -> dict:
    return {
        "id": row.id,
        "run_number": row.run_number,
        "line_number": row.line_number,
        "material_code": row.material_code,
        "requirement_level": row.requirement_level,
        "demand_type": _s(row.demand_type),
        "demand_ref": row.demand_ref,
        "parent_planned_order": row.parent_planned_order,
        "quantity": _f(row.quantity),
        "covered_qty": _f(row.covered_qty),
        "shortage_qty": _f(row.shortage_qty),
        "due_date": _dt(row.due_date),
        "status": row.status,
    }


def _planned_order(plan: PlannedOrder) -> dict:
    return {
        "id": plan.id,
        "planned_order_number": plan.planned_order_number,
        "run_number": plan.run_number,
        "order_type": _s(plan.order_type),
        "material_code": plan.material_code,
        "quantity": _f(plan.quantity),
        "unit": plan.unit,
        "start_date": _dt(plan.start_date),
        "due_date": _dt(plan.due_date),
        "status": _s(plan.status),
        "procurement_type": plan.procurement_type,
        "supplier_id": plan.supplier_id,
        "lot_sizing_rule": plan.lot_sizing_rule,
        "lead_time_days": plan.lead_time_days,
        "demand_type": plan.demand_type,
        "demand_ref": plan.demand_ref,
        "parent_planned_order": plan.parent_planned_order,
        "conversion_order_number": plan.conversion_order_number,
        "confirmed_by": plan.confirmed_by,
        "confirmed_at": _dt(plan.confirmed_at),
        "created_at": _dt(plan.created_at),
    }


def _exception(row: MrpException) -> dict:
    return {
        "id": row.id,
        "run_number": row.run_number,
        "exception_type": _s(row.exception_type),
        "severity": _s(row.severity),
        "material_code": row.material_code,
        "requirement_ref": row.requirement_ref,
        "planned_order_number": row.planned_order_number,
        "shortage_qty": _f(row.shortage_qty),
        "shortage_date": _dt(row.shortage_date),
        "suggestion": row.suggestion,
        "resolution_status": _s(row.resolution_status),
        "resolved_by": row.resolved_by,
        "resolved_at": _dt(row.resolved_at),
        "created_at": _dt(row.created_at),
    }


def _kitting(row: KittingResult) -> dict:
    import json

    details = []
    if row.shortage_details:
        try:
            details = json.loads(row.shortage_details)
        except (TypeError, ValueError):
            details = []
    return {
        "id": row.id,
        "result_number": row.result_number,
        "source_type": row.source_type,
        "source_ref": row.source_ref,
        "material_code": row.material_code,
        "kit_status": _s(row.kit_status),
        "required_qty": _f(row.required_qty),
        "available_qty": _f(row.available_qty),
        "shortage_qty": _f(row.shortage_qty),
        "shortage_details": details,
        "checked_at": _dt(row.checked_at),
        "remarks": row.remarks,
    }


def _policy(row: PlanningPolicy) -> dict:
    return {
        "id": row.id,
        "policy_id": row.policy_id,
        "material_code": row.material_code,
        "mrp_type": _s(row.mrp_type),
        "procurement_type": _s(row.procurement_type),
        "lot_sizing_rule": _s(row.lot_sizing_rule),
        "fixed_lot_size": _f(row.fixed_lot_size),
        "min_order_qty": _f(row.min_order_qty),
        "max_order_qty": _f(row.max_order_qty) if row.max_order_qty is not None else None,
        "order_multiple": _f(row.order_multiple) or 1,
        "eoq": _f(row.eoq) if row.eoq is not None else None,
        "lead_time_days": row.lead_time_days or 0,
        "safety_time_days": row.safety_time_days or 0,
        "safety_stock": _f(row.safety_stock),
        "reorder_point": _f(row.reorder_point),
        "planner_code": row.planner_code,
        "abc_class": row.abc_class,
        "is_active": bool(row.is_active),
        "remarks": row.remarks,
    }


# ── MPS ────────────────────────────────────────────────────────────────
@router.post("/mps/generate", status_code=status.HTTP_201_CREATED)
def generate_mps(
    payload: MpsGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        plan = MpsEngine.generate(
            db,
            horizon_start=payload.horizon_start,
            horizon_end=payload.horizon_end,
            plan_name=payload.plan_name,
            plant_id=payload.plant_id,
            demand_source=payload.demand_source,
            include_forecast=payload.include_forecast,
            include_safety_stock=payload.include_safety_stock,
            created_by=current_user.username,
        )
        db.commit()
        return _mps_summary(plan)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MPS 生成失败: {exc}",
        )


@router.get("/mps")
def list_mps(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(MpsPlan).filter(MpsPlan.is_deleted == False)
    if status_filter:
        query = query.filter(MpsPlan.status == status_filter)
    total = query.count()
    rows = (
        query.order_by(MpsPlan.horizon_start.desc(), MpsPlan.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": [_mps_summary(row) for row in rows]}


@router.get("/mps/{mps_number}")
def get_mps(mps_number: str, db: Session = Depends(get_db)):
    plan = _get_or_404(
        db, MpsPlan, MpsPlan.mps_number == mps_number, label=f"MPS 计划 {mps_number} "
    )
    entries = (
        db.query(MpsEntry)
        .filter(MpsEntry.mps_number == mps_number, MpsEntry.is_deleted == False)
        .order_by(MpsEntry.material_code, MpsEntry.bucket_date)
        .all()
    )
    result = _mps_summary(plan)
    result["entries"] = [_mps_entry(row) for row in entries]
    return result


@router.post("/mps/{mps_number}/release")
def release_mps(
    mps_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        plan = MpsEngine.release(db, mps_number, released_by=current_user.username)
        db.commit()
        return _mps_summary(plan)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/mps/{mps_number}/close")
def close_mps(
    mps_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_or_404(db, MpsPlan, MpsPlan.mps_number == mps_number, label="MPS 计划 ")
    plan.status = "CLOSED"
    plan.updated_by = current_user.username
    db.commit()
    return _mps_summary(plan)


# ── MRP ────────────────────────────────────────────────────────────────
@router.post("/mrp/run", status_code=status.HTTP_201_CREATED)
def run_mrp(
    payload: MrpRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        run = MrpEngine.run(
            db,
            horizon_start=payload.horizon_start,
            horizon_end=payload.horizon_end,
            run_type=payload.run_type,
            demand_source=payload.demand_source,
            mps_number=payload.mps_number,
            plant_id=payload.plant_id,
            include_forecast=payload.include_forecast,
            include_safety_stock=payload.include_safety_stock,
            run_by=current_user.username,
        )
        db.commit()
        return _run_summary(run)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MRP 运算失败: {exc}",
        )


@router.get("/mrp/runs")
def list_mrp_runs(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(MrpRun).filter(MrpRun.is_deleted == False)
    if status_filter:
        query = query.filter(MrpRun.status == status_filter)
    total = query.count()
    rows = query.order_by(MrpRun.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_run_summary(row) for row in rows]}


@router.get("/mrp/runs/{run_number}")
def get_mrp_run(run_number: str, db: Session = Depends(get_db)):
    run = _get_or_404(
        db, MrpRun, MrpRun.run_number == run_number, label=f"MRP 批次 {run_number} "
    )
    requirements = (
        db.query(MrpRequirement)
        .filter(MrpRequirement.run_number == run_number, MrpRequirement.is_deleted == False)
        .order_by(MrpRequirement.requirement_level, MrpRequirement.line_number)
        .all()
    )
    planned = (
        db.query(PlannedOrder)
        .filter(PlannedOrder.run_number == run_number, PlannedOrder.is_deleted == False)
        .order_by(PlannedOrder.order_type, PlannedOrder.material_code)
        .all()
    )
    exceptions = (
        db.query(MrpException)
        .filter(MrpException.run_number == run_number, MrpException.is_deleted == False)
        .order_by(MrpException.severity, MrpException.id)
        .all()
    )
    result = _run_summary(run)
    result["requirements"] = [_requirement(row) for row in requirements]
    result["planned_orders"] = [_planned_order(row) for row in planned]
    result["exceptions"] = [_exception(row) for row in exceptions]
    return result


@router.get("/mrp/runs/{run_number}/pegging")
def get_mrp_pegging(run_number: str, db: Session = Depends(get_db)):
    rows = (
        db.query(PeggingLink)
        .filter(PeggingLink.run_number == run_number, PeggingLink.is_deleted == False)
        .order_by(PeggingLink.id)
        .all()
    )
    return [
        {
            "id": row.id,
            "planned_order_number": row.planned_order_number,
            "demand_type": _s(row.demand_type),
            "demand_ref": row.demand_ref,
            "supply_type": _s(row.supply_type),
            "supply_ref": row.supply_ref,
            "pegged_qty": _f(row.pegged_qty),
        }
        for row in rows
    ]


# ── Planned orders ────────────────────────────────────────────────────
@router.get("/planned-orders")
def list_planned_orders(
    skip: int = 0,
    limit: int = 200,
    run_number: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    order_type: Optional[str] = None,
    material_code: Optional[str] = None,
    include_cancelled: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(PlannedOrder).filter(PlannedOrder.is_deleted == False)
    if run_number:
        query = query.filter(PlannedOrder.run_number == run_number)
    if status_filter:
        query = query.filter(PlannedOrder.status == status_filter)
    elif not include_cancelled:
        query = query.filter(PlannedOrder.status != PlannedOrderStatus.CANCELLED)
    if order_type:
        query = query.filter(PlannedOrder.order_type == order_type)
    if material_code:
        query = query.filter(PlannedOrder.material_code == material_code)
    total = query.count()
    rows = (
        query.order_by(PlannedOrder.due_date, PlannedOrder.planned_order_number)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": [_planned_order(row) for row in rows]}


@router.get("/planned-orders/{planned_order_number}")
def get_planned_order(planned_order_number: str, db: Session = Depends(get_db)):
    plan = _get_or_404(
        db,
        PlannedOrder,
        PlannedOrder.planned_order_number == planned_order_number,
        label=f"计划订单 {planned_order_number} ",
    )
    result = _planned_order(plan)
    result["pegging"] = [
        {
            "demand_type": _s(row.demand_type),
            "demand_ref": row.demand_ref,
            "supply_type": _s(row.supply_type),
            "supply_ref": row.supply_ref,
            "pegged_qty": _f(row.pegged_qty),
        }
        for row in db.query(PeggingLink)
        .filter(
            PeggingLink.planned_order_number == planned_order_number,
            PeggingLink.is_deleted == False,
        )
        .all()
    ]
    return result


@router.post("/planned-orders/{planned_order_number}/confirm")
def confirm_planned_order(
    planned_order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_or_404(
        db,
        PlannedOrder,
        PlannedOrder.planned_order_number == planned_order_number,
        label="计划订单 ",
    )
    if _s(plan.status) not in (PlannedOrderStatus.PLANNED.value, PlannedOrderStatus.FIRMED.value):
        raise HTTPException(status_code=400, detail=f"当前状态不允许确认: {_s(plan.status)}")
    plan.status = PlannedOrderStatus.FIRMED
    plan.confirmed_by = current_user.username
    plan.confirmed_at = datetime.now()
    plan.updated_by = current_user.username
    db.commit()
    return _planned_order(plan)


def _resolve_sales_order_number(db: Session, plan: PlannedOrder) -> Optional[str]:
    """Walk the pegging chain to find the originating sales order."""
    if plan.demand_ref and plan.demand_ref.startswith("SO-"):
        exists = (
            db.query(SalesOrder.order_number)
            .filter(SalesOrder.order_number == plan.demand_ref)
            .scalar()
        )
        if exists:
            return exists

    current = plan
    seen: set[str] = set()
    while current is not None and current.parent_planned_order:
        parent_number = current.parent_planned_order
        if parent_number in seen:
            break
        seen.add(parent_number)
        current = (
            db.query(PlannedOrder)
            .filter(PlannedOrder.planned_order_number == parent_number)
            .first()
        )
        if current is None:
            break
        if current.demand_ref and current.demand_ref.startswith("SO-"):
            exists = (
                db.query(SalesOrder.order_number)
                .filter(SalesOrder.order_number == current.demand_ref)
                .scalar()
            )
            if exists:
                return exists

    fallback = (
        db.query(SalesOrder.order_number)
        .filter(
            SalesOrder.status.in_(OPEN_SALES_STATUSES),
            SalesOrder.is_deleted == False,
        )
        .order_by(SalesOrder.delivery_date)
        .first()
    )
    return fallback[0] if fallback else None


def _resolve_production_version(db: Session, material_code: str) -> Optional[ProductionVersion]:
    return (
        db.query(ProductionVersion)
        .filter(
            ProductionVersion.material_code == material_code,
            ProductionVersion.is_deleted == False,
            ProductionVersion.status.in_(["ACTIVE", "RELEASED"]),
        )
        .order_by(ProductionVersion.effective_date.desc())
        .first()
    )


@router.post("/planned-orders/{planned_order_number}/release")
def release_planned_order(
    planned_order_number: str,
    payload: PlannedOrderReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = _get_or_404(
        db,
        PlannedOrder,
        PlannedOrder.planned_order_number == planned_order_number,
        label="计划订单 ",
    )
    if _s(plan.status) not in (
        PlannedOrderStatus.PLANNED.value,
        PlannedOrderStatus.FIRMED.value,
    ):
        raise HTTPException(status_code=400, detail=f"当前状态不允许下达: {_s(plan.status)}")

    try:
        order_type = _s(plan.order_type)
        if order_type == PlannedOrderType.PRODUCTION.value:
            sales_order_number = payload.sales_order_number or _resolve_sales_order_number(db, plan)
            if not sales_order_number:
                raise HTTPException(
                    status_code=400,
                    detail="无法关联销售订单，请手工指定 sales_order_number 后再下达",
                )
            sales_order = (
                db.query(SalesOrder)
                .filter(SalesOrder.order_number == sales_order_number)
                .first()
            )
            if sales_order is None:
                raise HTTPException(status_code=404, detail=f"销售订单不存在: {sales_order_number}")

            production_version = _resolve_production_version(db, plan.material_code)
            order_number = NumberGenerator.generate_production_order_number(db)
            order = ProductionOrder(
                order_number=order_number,
                sales_order_number=sales_order_number,
                material_code=plan.material_code,
                production_version_id=(
                    production_version.production_version_id if production_version else None
                ),
                quantity=plan.quantity,
                unit=plan.unit,
                planned_start_date=plan.start_date,
                planned_finish_date=plan.due_date,
                status=ProductionOrderStatus.DRAFT,
                remarks=f"由计划订单 {plan.planned_order_number} 自动转换（MRP {plan.run_number}）",
                created_by=current_user.username,
            )
            db.add(order)
            conversion_number = order_number
        else:
            material = (
                db.query(Material)
                .filter(Material.material_code == plan.material_code)
                .first()
            )
            unit_price = (
                Decimal(str(payload.unit_price))
                if payload.unit_price is not None
                else dec(material.standard_price if material else 0)
            )
            po_number = NumberGenerator.generate_document_number(
                db, PurchaseOrder, "purchase_order_number", "PUR", 4
            )
            po = PurchaseOrder(
                purchase_order_number=po_number,
                supplier_id=payload.supplier_id,
                supplier_name=payload.supplier_name,
                status=PurchaseOrderStatus.RELEASED,
                order_date=datetime.now(),
                expected_date=plan.due_date,
                total_amount=dec(plan.quantity) * unit_price,
                source_planned_order=plan.planned_order_number,
                remarks=f"由计划订单 {plan.planned_order_number} 自动转换（MRP {plan.run_number}）",
                created_by=current_user.username,
            )
            db.add(po)
            db.flush()
            db.add(
                PurchaseOrderLine(
                    purchase_order_number=po_number,
                    line_number=1,
                    material_code=plan.material_code,
                    quantity=plan.quantity,
                    received_quantity=0,
                    unit=plan.unit,
                    unit_price=unit_price,
                    expected_date=plan.due_date,
                    status="OPEN",
                    created_by=current_user.username,
                )
            )
            conversion_number = po_number

        if payload.auto_confirm:
            plan.status = PlannedOrderStatus.RELEASED
        else:
            plan.status = PlannedOrderStatus.FIRMED
        plan.conversion_order_number = conversion_number
        plan.confirmed_by = current_user.username
        plan.confirmed_at = datetime.now()
        plan.updated_by = current_user.username
        db.commit()

        result = _planned_order(plan)
        result["created_order_number"] = conversion_number
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"计划订单下达失败: {exc}",
        )


# ── MRP exceptions ────────────────────────────────────────────────────
@router.get("/exceptions")
def list_exceptions(
    skip: int = 0,
    limit: int = 200,
    run_number: Optional[str] = None,
    severity: Optional[str] = None,
    exception_type: Optional[str] = None,
    resolution_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(MrpException).filter(MrpException.is_deleted == False)
    if run_number:
        query = query.filter(MrpException.run_number == run_number)
    if severity:
        query = query.filter(MrpException.severity == severity)
    if exception_type:
        query = query.filter(MrpException.exception_type == exception_type)
    if resolution_status:
        query = query.filter(MrpException.resolution_status == resolution_status)
    total = query.count()
    rows = (
        query.order_by(MrpException.severity.desc(), MrpException.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": [_exception(row) for row in rows]}


@router.post("/exceptions/{exception_id}/resolve")
def resolve_exception(
    exception_id: int,
    payload: ExceptionResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_or_404(db, MrpException, MrpException.id == exception_id, label="MRP 异常 ")
    try:
        resolution = ResolutionStatus(payload.resolution_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的处理状态: {payload.resolution_status}")
    row.resolution_status = resolution
    row.resolved_by = current_user.username
    row.resolved_at = datetime.now()
    if payload.remarks:
        row.remarks = payload.remarks
    row.updated_by = current_user.username
    db.commit()
    return _exception(row)


# ── Kitting ───────────────────────────────────────────────────────────
@router.get("/kitting")
def list_kitting(
    skip: int = 0,
    limit: int = 200,
    source_type: Optional[str] = None,
    kit_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(KittingResult).filter(KittingResult.is_deleted == False)
    if source_type:
        query = query.filter(KittingResult.source_type == source_type)
    if kit_status:
        query = query.filter(KittingResult.kit_status == kit_status)
    total = query.count()
    rows = query.order_by(KittingResult.checked_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_kitting(row) for row in rows]}


@router.get("/kitting/{result_number}")
def get_kitting(result_number: str, db: Session = Depends(get_db)):
    row = _get_or_404(
        db, KittingResult, KittingResult.result_number == result_number, label="齐套分析结果 "
    )
    return _kitting(row)


@router.get("/kitting/by-source/{source_type}/{source_ref}")
def get_kitting_by_source(source_type: str, source_ref: str, db: Session = Depends(get_db)):
    row = _get_or_404(
        db,
        KittingResult,
        KittingResult.source_type == source_type,
        KittingResult.source_ref == source_ref,
        KittingResult.is_deleted == False,
        label="齐套分析结果 ",
    )
    return _kitting(row)


@router.post("/kitting/production-orders/{order_number}")
def analyze_production_order_kitting(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = KittingService.analyze_production_order(
            db, order_number, persist=True, checked_by=current_user.username
        )
        db.commit()
        return _kitting(result)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/kitting/planned-orders/{planned_order_number}")
def analyze_planned_order_kitting(
    planned_order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = KittingService.analyze_planned_order(
            db, planned_order_number, persist=True, checked_by=current_user.username
        )
        db.commit()
        return _kitting(result)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


# ── Planning policies ─────────────────────────────────────────────────
@router.get("/policies")
def list_policies(
    skip: int = 0,
    limit: int = 200,
    material_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PlanningPolicy).filter(PlanningPolicy.is_deleted == False)
    if material_code:
        query = query.filter(PlanningPolicy.material_code == material_code)
    if is_active is not None:
        query = query.filter(PlanningPolicy.is_active == is_active)
    total = query.count()
    rows = query.order_by(PlanningPolicy.material_code).offset(skip).limit(limit).all()
    return {"total": total, "items": [_policy(row) for row in rows]}


@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PlanningPolicyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    material = (
        db.query(Material)
        .filter(Material.material_code == payload.material_code)
        .first()
    )
    if material is None:
        raise HTTPException(status_code=404, detail=f"物料不存在: {payload.material_code}")
    existing = (
        db.query(PlanningPolicy)
        .filter(
            PlanningPolicy.material_code == payload.material_code,
            PlanningPolicy.is_deleted == False,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该物料已存在计划参数，请使用更新接口")

    row = PlanningPolicy(
        policy_id=NumberGenerator.generate_document_number(
            db, PlanningPolicy, "policy_id", "PLP", 4
        ),
        material_code=payload.material_code,
        created_by=current_user.username,
    )
    _apply_policy_payload(row, payload)
    row.updated_by = current_user.username
    db.add(row)
    db.commit()
    return _policy(row)


@router.put("/policies/{policy_id}")
def update_policy(
    policy_id: str,
    payload: PlanningPolicyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_or_404(
        db,
        PlanningPolicy,
        PlanningPolicy.policy_id == policy_id,
        PlanningPolicy.is_deleted == False,
        label="计划参数 ",
    )
    if payload.material_code != row.material_code:
        raise HTTPException(status_code=400, detail="不允许修改物料编码，请新建策略")
    _apply_policy_payload(row, payload)
    row.updated_by = current_user.username
    db.commit()
    return _policy(row)


@router.delete("/policies/{policy_id}")
def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_or_404(
        db,
        PlanningPolicy,
        PlanningPolicy.policy_id == policy_id,
        PlanningPolicy.is_deleted == False,
        label="计划参数 ",
    )
    row.is_deleted = True
    row.is_active = False
    row.updated_by = current_user.username
    db.commit()
    return {"message": "计划参数已删除"}


def _apply_policy_payload(row: PlanningPolicy, payload: PlanningPolicyPayload) -> None:
    row.mrp_type = payload.mrp_type
    row.procurement_type = payload.procurement_type
    row.lot_sizing_rule = payload.lot_sizing_rule
    row.fixed_lot_size = payload.fixed_lot_size
    row.min_order_qty = payload.min_order_qty
    row.max_order_qty = payload.max_order_qty
    row.order_multiple = payload.order_multiple
    row.eoq = payload.eoq
    row.lead_time_days = payload.lead_time_days
    row.safety_time_days = payload.safety_time_days
    row.safety_stock = payload.safety_stock
    row.reorder_point = payload.reorder_point
    row.planner_code = payload.planner_code
    row.abc_class = payload.abc_class
    row.is_active = payload.is_active
    row.remarks = payload.remarks


# ── Overview for the planning cockpit ─────────────────────────────────
@router.get("/overview")
def planning_overview(db: Session = Depends(get_db)):
    latest_run = (
        db.query(MrpRun)
        .filter(MrpRun.is_deleted == False)
        .order_by(MrpRun.id.desc())
        .first()
    )
    open_exceptions = (
        db.query(func.count(MrpException.id))
        .filter(
            MrpException.is_deleted == False,
            MrpException.resolution_status == ResolutionStatus.OPEN,
        )
        .scalar()
        or 0
    )
    critical_exceptions = (
        db.query(func.count(MrpException.id))
        .filter(
            MrpException.is_deleted == False,
            MrpException.resolution_status == ResolutionStatus.OPEN,
            MrpException.severity == ExceptionSeverity.CRITICAL,
        )
        .scalar()
        or 0
    )
    short_kits = (
        db.query(func.count(KittingResult.id))
        .filter(
            KittingResult.is_deleted == False,
            KittingResult.kit_status.in_([KitStatus.SHORT, KitStatus.PARTIAL]),
        )
        .scalar()
        or 0
    )
    planned_open = (
        db.query(func.count(PlannedOrder.id))
        .filter(
            PlannedOrder.is_deleted == False,
            PlannedOrder.status.in_(
                [PlannedOrderStatus.PLANNED, PlannedOrderStatus.FIRMED]
            ),
        )
        .scalar()
        or 0
    )
    return {
        "latest_run": _run_summary(latest_run) if latest_run else None,
        "mps_draft": db.query(func.count(MpsPlan.id))
        .filter(MpsPlan.is_deleted == False, MpsPlan.status == "DRAFT")
        .scalar()
        or 0,
        "mps_released": db.query(func.count(MpsPlan.id))
        .filter(MpsPlan.is_deleted == False, MpsPlan.status == "RELEASED")
        .scalar()
        or 0,
        "open_exceptions": int(open_exceptions),
        "critical_exceptions": int(critical_exceptions),
        "short_kits": int(short_kits),
        "planned_orders_open": int(planned_open),
        "forecasts": db.query(func.count(Forecast.id))
        .filter(Forecast.is_deleted == False)
        .scalar()
        or 0,
        "policies": db.query(func.count(PlanningPolicy.id))
        .filter(PlanningPolicy.is_deleted == False, PlanningPolicy.is_active == True)
        .scalar()
        or 0,
    }


# ═══════════════════════════════════════════════════════════════════════
# 成本引擎（P1）：标准成本 / 工单实际成本 / 差异 / 结算 / 费率
# ═══════════════════════════════════════════════════════════════════════

class RatePayload(BaseModel):
    work_center_id: str
    rate_type: str
    rate_per_hour: float
    currency: str = "CNY"
    effective_from: Optional[datetime] = None
    status: str = "ACTIVE"
    remarks: Optional[str] = None


def _cost_rate(row: CostRate) -> dict:
    return {
        "id": row.id,
        "rate_id": row.rate_id,
        "work_center_id": row.work_center_id,
        "rate_type": _s(row.rate_type),
        "rate_per_hour": _f(row.rate_per_hour),
        "currency": row.currency,
        "effective_from": _dt(row.effective_from),
        "effective_to": _dt(row.effective_to),
        "status": row.status,
        "remarks": row.remarks,
    }


def _standard_cost(row: StandardCost) -> dict:
    return {
        "id": row.id,
        "cost_id": row.cost_id,
        "material_code": row.material_code,
        "version": row.version,
        "cost_date": _dt(row.cost_date),
        "material_cost": _f(row.material_cost),
        "labor_cost": _f(row.labor_cost),
        "overhead_cost": _f(row.overhead_cost),
        "total_cost": _f(row.total_cost),
        "unit_cost": _f(row.unit_cost),
        "currency": row.currency,
        "status": row.status,
        "rolled_up_at": _dt(row.rolled_up_at),
        "cost_method": row.cost_method,
        "remarks": row.remarks,
    }


def _production_cost(row: ProductionCost) -> dict:
    return {
        "id": row.id,
        "cost_id": row.cost_id,
        "production_order_number": row.production_order_number,
        "material_code": row.material_code,
        "quantity": _f(row.quantity),
        "material_cost_actual": _f(row.material_cost_actual),
        "labor_cost_actual": _f(row.labor_cost_actual),
        "overhead_actual": _f(row.overhead_actual),
        "total_actual": _f(row.total_actual),
        "standard_cost": _f(row.standard_cost),
        "wip_value": _f(row.wip_value),
        "status": _s(row.status),
        "collected_at": _dt(row.collected_at),
        "settled_at": _dt(row.settled_at),
        "remarks": row.remarks,
    }


def _variance(row: CostVariance) -> dict:
    return {
        "id": row.id,
        "variance_number": row.variance_number,
        "production_order_number": row.production_order_number,
        "variance_type": _s(row.variance_type),
        "standard_amount": _f(row.standard_amount),
        "actual_amount": _f(row.actual_amount),
        "variance_amount": _f(row.variance_amount),
        "variance_pct": _f(row.variance_pct),
        "analyzed_at": _dt(row.analyzed_at),
        "remarks": row.remarks,
    }


def _settlement(row: CostSettlement) -> dict:
    return {
        "id": row.id,
        "settlement_number": row.settlement_number,
        "production_order_number": row.production_order_number,
        "total_cost": _f(row.total_cost),
        "wip_value": _f(row.wip_value),
        "settlement_status": _s(row.settlement_status),
        "settled_at": _dt(row.settled_at),
        "remarks": row.remarks,
    }


# ── 成本概览 ───────────────────────────────────────────────────────────
@router.get("/cost/overview")
def cost_overview(db: Session = Depends(get_db)):
    def count(model):
        return db.query(func.count(model.id)).filter(model.is_deleted == False).scalar() or 0

    return {
        "standard_costs": count(StandardCost),
        "production_costs": count(ProductionCost),
        "open_costs": db.query(func.count(ProductionCost.id))
        .filter(ProductionCost.status.in_([CostStatus.OPEN, CostStatus.COLLECTED]))
        .scalar()
        or 0,
        "settled_costs": db.query(func.count(ProductionCost.id))
        .filter(ProductionCost.status == CostStatus.SETTLED)
        .scalar()
        or 0,
        "variances": count(CostVariance),
        "adverse_variances": db.query(func.count(CostVariance.id))
        .filter(CostVariance.variance_amount > 0, CostVariance.is_deleted == False)
        .scalar()
        or 0,
        "settlements": count(CostSettlement),
        "rates": db.query(func.count(CostRate.id))
        .filter(CostRate.status == "ACTIVE", CostRate.is_deleted == False)
        .scalar()
        or 0,
        "cost_centers": db.query(func.count(WorkCenter.id))
        .filter(WorkCenter.is_deleted == False)
        .scalar()
        or 0,
    }


# ── 费率 ───────────────────────────────────────────────────────────────
@router.get("/cost/rates")
def list_rates(
    skip: int = 0,
    limit: int = 200,
    work_center_id: Optional[str] = None,
    rate_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CostRate).filter(CostRate.is_deleted == False)
    if work_center_id:
        query = query.filter(CostRate.work_center_id == work_center_id)
    if rate_type:
        query = query.filter(CostRate.rate_type == rate_type)
    total = query.count()
    rows = query.order_by(CostRate.work_center_id, CostRate.id).offset(skip).limit(limit).all()
    return {"total": total, "items": [_cost_rate(row) for row in rows]}


@router.put("/cost/rates/{rate_id}")
def update_rate(
    rate_id: str,
    payload: RatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_or_404(
        db, CostRate, CostRate.rate_id == rate_id, CostRate.is_deleted == False,
        label="成本费率 ",
    )
    row.rate_per_hour = payload.rate_per_hour
    row.currency = payload.currency
    row.status = payload.status
    row.remarks = payload.remarks
    row.updated_by = current_user.username
    db.commit()
    return _cost_rate(row)


# ── 标准成本 ───────────────────────────────────────────────────────────
@router.post("/cost/standard/rollup")
def rollup_standard(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    material_codes = payload.get("material_codes") or []
    version = payload.get("version", "1")
    roll_deep = payload.get("roll_deep", False)
    if not material_codes:
        raise HTTPException(status_code=400, detail="material_codes 不能为空")
    done = 0
    for code in material_codes:
        CostEngine.rollup_standard_cost(
            db, code, version=version, roll_deep=roll_deep, created_by=current_user.username
        )
        done += 1
    db.commit()
    return {"rolled_up": done, "material_codes": material_codes}


@router.get("/cost/standard")
def list_standard(
    skip: int = 0,
    limit: int = 200,
    material_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(StandardCost).filter(StandardCost.is_deleted == False)
    if material_code:
        query = query.filter(StandardCost.material_code == material_code)
    total = query.count()
    rows = (
        query.order_by(StandardCost.material_code, StandardCost.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": [_standard_cost(row) for row in rows]}


@router.get("/cost/standard/{material_code}")
def get_standard(
    material_code: str,
    db: Session = Depends(get_db),
):
    row = _get_or_404(
        db, StandardCost, StandardCost.material_code == material_code,
        StandardCost.is_deleted == False, label="标准成本 ",
    )
    return _standard_cost(row)


# ── 工单实际成本 ───────────────────────────────────────────────────────
@router.get("/cost/production")
def list_production(
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ProductionCost).filter(ProductionCost.is_deleted == False)
    if status:
        query = query.filter(ProductionCost.status == status)
    total = query.count()
    rows = query.order_by(ProductionCost.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_production_cost(row) for row in rows]}


@router.post("/cost/production/collect")
def collect_production(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_number = payload.get("production_order_number")
    if not order_number:
        raise HTTPException(status_code=400, detail="production_order_number 不能为空")
    try:
        row = CostEngine.collect_production_cost(db, order_number, created_by=current_user.username)
        db.commit()
        return _production_cost(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cost/production/{order_number}")
def get_production_cost(
    order_number: str,
    db: Session = Depends(get_db),
):
    row = _get_or_404(
        db, ProductionCost,
        ProductionCost.production_order_number == order_number,
        ProductionCost.is_deleted == False, label="工单成本 ",
    )
    return _production_cost(row)


# ── 差异分析 ───────────────────────────────────────────────────────────
@router.post("/cost/variances/analyze")
def analyze_variances(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_number = payload.get("production_order_number")
    if not order_number:
        raise HTTPException(status_code=400, detail="production_order_number 不能为空")
    try:
        rows = CostEngine.analyze_variances(db, order_number, created_by=current_user.username)
        db.commit()
        return {"items": [_variance(row) for row in rows]}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cost/variances")
def list_variances(
    skip: int = 0,
    limit: int = 200,
    production_order_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CostVariance).filter(CostVariance.is_deleted == False)
    if production_order_number:
        query = query.filter(CostVariance.production_order_number == production_order_number)
    total = query.count()
    rows = query.order_by(CostVariance.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_variance(row) for row in rows]}


# ── 结算 ───────────────────────────────────────────────────────────────
@router.post("/cost/settlement/settle")
def settle_cost(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_number = payload.get("production_order_number")
    if not order_number:
        raise HTTPException(status_code=400, detail="production_order_number 不能为空")
    try:
        row = CostEngine.settle(db, order_number, created_by=current_user.username)
        db.commit()
        return _settlement(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cost/settlements")
def list_settlements(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(CostSettlement).filter(CostSettlement.is_deleted == False)
    total = query.count()
    rows = query.order_by(CostSettlement.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_settlement(row) for row in rows]}


# ══════════════════════════════════════════════════════════════════════
# P1 高级排程 APS
# ══════════════════════════════════════════════════════════════════════


def _aps_run(row: ScheduleRun) -> dict:
    return {
        "run_number": row.run_number,
        "run_name": row.run_name,
        "algorithm": row.algorithm.value if row.algorithm else None,
        "status": row.status.value if row.status else None,
        "horizon_start": _dt(row.horizon_start),
        "horizon_end": _dt(row.horizon_end),
        "source_type": row.source_type,
        "generated_by": row.generated_by,
        "generated_at": _dt(row.generated_at),
        "published_at": _dt(row.published_at),
        "operation_count": row.operation_count or 0,
        "exception_count": row.exception_count or 0,
        "notes": row.notes,
    }


def _aps_operation(row: ScheduledOperation) -> dict:
    return {
        "op_id": row.op_id,
        "run_number": row.run_number,
        "production_order_number": row.production_order_number,
        "planned_order_number": row.planned_order_number,
        "material_code": row.material_code,
        "operation_no": row.operation_no,
        "operation_name": row.operation_name,
        "work_center_id": row.work_center_id,
        "resource_id": row.resource_id,
        "sequence": row.sequence or 0,
        "planned_qty": _f(row.planned_qty),
        "setup_minutes": _f(row.setup_minutes),
        "run_minutes": _f(row.run_minutes),
        "planned_start": _dt(row.planned_start),
        "planned_end": _dt(row.planned_end),
        "status": row.status.value if row.status else None,
    }


def _aps_exception(row: ScheduleException) -> dict:
    return {
        "exception_id": row.exception_id,
        "run_number": row.run_number,
        "exception_type": row.exception_type.value if row.exception_type else None,
        "production_order_number": row.production_order_number,
        "work_center_id": row.work_center_id,
        "resource_id": row.resource_id,
        "severity": row.severity,
        "message": row.message,
        "suggested_action": row.suggested_action,
        "created_at": _dt(row.created_at),
    }


def _aps_scenario(row: ScenarioSimulation) -> dict:
    return {
        "scenario_id": row.scenario_id,
        "run_number": row.run_number,
        "scenario_type": row.scenario_type.value if row.scenario_type else None,
        "description": row.description,
        "reference_ref": row.reference_ref,
        "created_by": row.created_by,
        "created_at": _dt(row.created_at),
        "impact_summary": row.impact_summary,
        "status": row.status,
    }


def _aps_impact(row: ScenarioImpact) -> dict:
    return {
        "impact_id": row.impact_id,
        "scenario_id": row.scenario_id,
        "production_order_number": row.production_order_number,
        "material_code": row.material_code,
        "affected_days": _f(row.affected_days),
        "original_due_date": _dt(row.original_due_date),
        "new_due_date": _dt(row.new_due_date),
        "delay_days": _f(row.delay_days),
        "impact_level": row.impact_level,
    }


@router.get("/aps/overview")
def aps_overview(db: Session = Depends(get_db)):
    def count(model):
        return db.query(func.count(model.id)).filter(model.is_deleted == False).scalar() or 0

    latest = (
        db.query(ScheduleRun)
        .filter(ScheduleRun.is_deleted == False)
        .order_by(ScheduleRun.id.desc())
        .first()
    )
    return {
        "runs": count(ScheduleRun),
        "published_runs": db.query(func.count(ScheduleRun.id))
        .filter(ScheduleRun.status == ScheduleRunStatus.PUBLISHED, ScheduleRun.is_deleted == False)
        .scalar()
        or 0,
        "operations": count(ScheduledOperation),
        "exceptions": count(ScheduleException),
        "critical_exceptions": db.query(func.count(ScheduleException.id))
        .filter(ScheduleException.severity == "CRITICAL", ScheduleException.is_deleted == False)
        .scalar()
        or 0,
        "scenarios": count(ScenarioSimulation),
        "resources": count(Resource),
        "active_resources": db.query(func.count(Resource.id))
        .filter(Resource.status == ResourceStatus.ACTIVE, Resource.is_deleted == False)
        .scalar()
        or 0,
        "skills": count(SkillMatrix),
        "changeovers": count(ChangeoverMatrix),
        "work_centers": db.query(func.count(WorkCenter.id))
        .filter(WorkCenter.is_deleted == False)
        .scalar()
        or 0,
        "latest_run": _aps_run(latest) if latest else None,
    }


@router.post("/aps/run", status_code=status.HTTP_201_CREATED)
def aps_run(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    horizon_start = payload.get("horizon_start")
    horizon_end = payload.get("horizon_end")
    start = (
        datetime.fromisoformat(str(horizon_start))
        if horizon_start
        else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    )
    end = datetime.fromisoformat(str(horizon_end)) if horizon_end else start + timedelta(days=28)
    try:
        row = ApsEngine.run(
            db,
            run_name=payload.get("run_name"),
            horizon_start=start,
            horizon_end=end,
            algorithm=payload.get("algorithm") or "FORWARD",
            source_type=payload.get("source_type") or "PRODUCTION_ORDER",
            created_by=current_user.username,
        )
        db.commit()
        return _aps_run(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/aps/runs")
def aps_runs(
    skip: int = 0,
    limit: int = 200,
    status_filter: Optional[str] = Query(None, alias="status"),
    source_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ScheduleRun).filter(ScheduleRun.is_deleted == False)
    if status_filter:
        query = query.filter(ScheduleRun.status == status_filter)
    if source_type:
        query = query.filter(ScheduleRun.source_type == source_type)
    total = query.count()
    rows = query.order_by(ScheduleRun.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_aps_run(row) for row in rows]}


@router.get("/aps/runs/{run_number}")
def aps_run_detail(run_number: str, db: Session = Depends(get_db)):
    row = (
        db.query(ScheduleRun)
        .filter(ScheduleRun.run_number == run_number, ScheduleRun.is_deleted == False)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"排程批次不存在: {run_number}")
    ops = (
        db.query(ScheduledOperation)
        .filter(ScheduledOperation.run_number == run_number, ScheduledOperation.is_deleted == False)
        .order_by(ScheduledOperation.planned_start)
        .all()
    )
    exceptions = (
        db.query(ScheduleException)
        .filter(ScheduleException.run_number == run_number, ScheduleException.is_deleted == False)
        .order_by(ScheduleException.id.desc())
        .all()
    )
    return {**_aps_run(row), "operations": [_aps_operation(op) for op in ops], "exceptions": [_aps_exception(ex) for ex in exceptions]}


@router.get("/aps/runs/{run_number}/gantt")
def aps_gantt(run_number: str, db: Session = Depends(get_db)):
    row = (
        db.query(ScheduleRun)
        .filter(ScheduleRun.run_number == run_number, ScheduleRun.is_deleted == False)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"排程批次不存在: {run_number}")
    ops = (
        db.query(ScheduledOperation)
        .filter(ScheduledOperation.run_number == run_number, ScheduledOperation.is_deleted == False)
        .order_by(ScheduledOperation.planned_start)
        .all()
    )
    centers = (
        db.query(WorkCenter)
        .filter(WorkCenter.is_deleted == False)
        .order_by(WorkCenter.work_center_id)
        .all()
    )
    gantt = []
    for wc in centers:
        items = [op for op in ops if op.work_center_id == wc.work_center_id]
        if not items:
            continue
        gantt.append(
            {
                "work_center_id": wc.work_center_id,
                "description": wc.description,
                "capacity": wc.number_of_capacities or 1,
                "operations": [
                    {**_aps_operation(op), "title": f"{op.production_order_number} · {op.operation_name}"}
                    for op in items
                ],
            }
        )
    return {
        "run": _aps_run(row),
        "gantt": gantt,
        "range": {"start": _dt(row.horizon_start), "end": _dt(row.horizon_end)},
    }


@router.post("/aps/runs/{run_number}/publish")
def aps_publish(
    run_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = ApsEngine.publish(db, run_number, published_by=current_user.username)
        db.commit()
        return _aps_run(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/aps/exceptions")
def aps_exceptions(
    skip: int = 0,
    limit: int = 200,
    run_number: Optional[str] = None,
    exception_type: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ScheduleException).filter(ScheduleException.is_deleted == False)
    if run_number:
        query = query.filter(ScheduleException.run_number == run_number)
    if exception_type:
        query = query.filter(ScheduleException.exception_type == exception_type)
    if severity:
        query = query.filter(ScheduleException.severity == severity)
    total = query.count()
    rows = query.order_by(ScheduleException.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_aps_exception(row) for row in rows]}


@router.post("/aps/simulate", status_code=status.HTTP_201_CREATED)
def aps_simulate(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run_number = payload.get("run_number")
    if not run_number:
        raise HTTPException(status_code=400, detail="run_number 不能为空")
    try:
        row = ApsEngine.simulate(
            db,
            run_number=run_number,
            scenario_type=payload.get("scenario_type") or "INSERT_ORDER",
            description=payload.get("description"),
            reference_ref=payload.get("reference_ref"),
            created_by=current_user.username,
        )
        db.commit()
        impacts = (
            db.query(ScenarioImpact)
            .filter(ScenarioImpact.scenario_id == row.scenario_id, ScenarioImpact.is_deleted == False)
            .all()
        )
        return {**_aps_scenario(row), "impacts": [_aps_impact(i) for i in impacts]}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/aps/scenarios")
def aps_scenarios(
    skip: int = 0,
    limit: int = 200,
    run_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ScenarioSimulation).filter(ScenarioSimulation.is_deleted == False)
    if run_number:
        query = query.filter(ScenarioSimulation.run_number == run_number)
    total = query.count()
    rows = query.order_by(ScenarioSimulation.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_aps_scenario(row) for row in rows]}


@router.get("/aps/scenarios/{scenario_id}")
def aps_scenario_detail(scenario_id: str, db: Session = Depends(get_db)):
    row = (
        db.query(ScenarioSimulation)
        .filter(ScenarioSimulation.scenario_id == scenario_id, ScenarioSimulation.is_deleted == False)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"模拟场景不存在: {scenario_id}")
    impacts = (
        db.query(ScenarioImpact)
        .filter(ScenarioImpact.scenario_id == scenario_id, ScenarioImpact.is_deleted == False)
        .order_by(ScenarioImpact.id)
        .all()
    )
    return {**_aps_scenario(row), "impacts": [_aps_impact(i) for i in impacts]}


@router.get("/aps/resources")
def aps_resources(
    skip: int = 0,
    limit: int = 200,
    work_center_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Resource).filter(Resource.is_deleted == False)
    if work_center_id:
        query = query.filter(Resource.work_center_id == work_center_id)
    total = query.count()
    rows = query.order_by(Resource.work_center_id, Resource.resource_id).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "resource_id": row.resource_id,
                "resource_name": row.resource_name,
                "work_center_id": row.work_center_id,
                "resource_type": row.resource_type,
                "capacity_per_shift": _f(row.capacity_per_shift),
                "shift_start": row.shift_start,
                "shift_end": row.shift_end,
                "workdays": row.workdays,
                "status": row.status.value if row.status else None,
                "skill_tags": row.skill_tags,
                "notes": row.notes,
            }
            for row in rows
        ],
    }


@router.get("/aps/skills")
def aps_skills(
    skip: int = 0,
    limit: int = 200,
    resource_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(SkillMatrix).filter(SkillMatrix.is_deleted == False)
    if resource_id:
        query = query.filter(SkillMatrix.resource_id == resource_id)
    total = query.count()
    rows = query.order_by(SkillMatrix.resource_id, SkillMatrix.skill_code).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "skill_id": row.skill_id,
                "resource_id": row.resource_id,
                "skill_code": row.skill_code,
                "skill_name": row.skill_name,
                "proficiency": _f(row.proficiency),
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/aps/changeovers")
def aps_changeovers(
    skip: int = 0,
    limit: int = 200,
    work_center_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ChangeoverMatrix).filter(ChangeoverMatrix.is_deleted == False)
    if work_center_id:
        query = query.filter(ChangeoverMatrix.work_center_id == work_center_id)
    total = query.count()
    rows = query.order_by(ChangeoverMatrix.work_center_id, ChangeoverMatrix.changeover_id).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "changeover_id": row.changeover_id,
                "work_center_id": row.work_center_id,
                "from_operation": row.from_operation,
                "to_operation": row.to_operation,
                "changeover_minutes": _f(row.changeover_minutes),
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/aps/calendars")
def aps_calendars(db: Session = Depends(get_db)):
    rows = db.query(WorkCalendar).filter(WorkCalendar.is_deleted == False).order_by(WorkCalendar.work_center_id).all()
    return {
        "total": len(rows),
        "items": [
            {
                "calendar_id": row.calendar_id,
                "work_center_id": row.work_center_id,
                "shift_start": row.shift_start,
                "shift_end": row.shift_end,
                "break_hours": _f(row.break_hours),
                "capacity_hours": _f(row.capacity_hours),
                "utilization": _f(row.utilization),
                "workdays": row.workdays,
                "status": row.status,
            }
            for row in rows
        ],
    }


# ══════════════════════════════════════════════════════════════════════
# P1 轻量 EAM 设备管理
# ══════════════════════════════════════════════════════════════════════


def _eam_plan(row: MaintenancePlan) -> dict:
    return {
        "plan_id": row.plan_id,
        "resource_id": row.resource_id,
        "maintenance_type": row.maintenance_type.value if row.maintenance_type else None,
        "cycle_days": row.cycle_days or 0,
        "last_executed_at": _dt(row.last_executed_at),
        "next_due_at": _dt(row.next_due_at),
        "responsible": row.responsible,
        "status": row.status.value if row.status else None,
        "notes": row.notes,
    }


def _eam_order(row: MaintenanceOrder) -> dict:
    return {
        "order_number": row.order_number,
        "resource_id": row.resource_id,
        "plan_id": row.plan_id,
        "maintenance_type": row.maintenance_type.value if row.maintenance_type else None,
        "planned_date": _dt(row.planned_date),
        "completed_at": _dt(row.completed_at),
        "downtime_hours": _f(row.downtime_hours),
        "executed_by": row.executed_by,
        "result_note": row.result_note,
        "status": row.status.value if row.status else None,
    }


def _eam_failure(row: EquipmentFailure) -> dict:
    return {
        "failure_number": row.failure_number,
        "resource_id": row.resource_id,
        "work_center_id": row.work_center_id,
        "occurred_at": _dt(row.occurred_at),
        "resolved_at": _dt(row.resolved_at),
        "severity": row.severity.value if row.severity else None,
        "description": row.description,
        "root_cause": row.root_cause,
        "action_taken": row.action_taken,
        "downtime_hours": _f(row.downtime_hours),
        "status": row.status.value if row.status else None,
        "reported_by": row.reported_by,
    }


@router.get("/eam/overview")
def eam_overview(db: Session = Depends(get_db)):
    data = EamEngine.overview(db)
    # 追加最近的到期计划与未关闭故障，供工作台直接渲染
    as_of = datetime.now()
    due_plans = (
        db.query(MaintenancePlan)
        .filter(
            MaintenancePlan.is_deleted == False,
            MaintenancePlan.status == MaintenanceStatus.PLANNED,
            MaintenancePlan.next_due_at.isnot(None),
            MaintenancePlan.next_due_at <= as_of,
        )
        .order_by(MaintenancePlan.next_due_at)
        .limit(20)
        .all()
    )
    open_failures = (
        db.query(EquipmentFailure)
        .filter(
            EquipmentFailure.is_deleted == False,
            EquipmentFailure.status != FailureStatus.CLOSED,
        )
        .order_by(EquipmentFailure.occurred_at.desc())
        .limit(20)
        .all()
    )
    data["due_plan_items"] = [_eam_plan(row) for row in due_plans]
    data["open_failure_items"] = [_eam_failure(row) for row in open_failures]
    return data


@router.get("/eam/plans")
def eam_plans(
    skip: int = 0,
    limit: int = 200,
    resource_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    maintenance_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(MaintenancePlan).filter(MaintenancePlan.is_deleted == False)
    if resource_id:
        query = query.filter(MaintenancePlan.resource_id == resource_id)
    if status_filter:
        query = query.filter(MaintenancePlan.status == status_filter)
    if maintenance_type:
        query = query.filter(MaintenancePlan.maintenance_type == maintenance_type)
    total = query.count()
    rows = query.order_by(MaintenancePlan.next_due_at, MaintenancePlan.plan_id).offset(skip).limit(limit).all()
    return {"total": total, "items": [_eam_plan(row) for row in rows]}


@router.post("/eam/plans", status_code=status.HTTP_201_CREATED)
def create_eam_plan(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource_id = payload.get("resource_id")
    if not resource_id:
        raise HTTPException(status_code=400, detail="resource_id 不能为空")
    resource = (
        db.query(Resource)
        .filter(Resource.resource_id == resource_id, Resource.is_deleted == False)
        .first()
    )
    if resource is None:
        raise HTTPException(status_code=404, detail=f"设备资源不存在: {resource_id}")
    next_due = payload.get("next_due_at")
    row = MaintenancePlan(
        plan_id=NumberGenerator.generate_document_number(db, MaintenancePlan, "plan_id", "MP", 4),
        resource_id=resource_id,
        maintenance_type=payload.get("maintenance_type") or MaintenanceType.INSPECTION,
        cycle_days=int(payload.get("cycle_days") or 30),
        last_executed_at=None,
        next_due_at=datetime.fromisoformat(str(next_due)) if next_due else datetime.now(),
        responsible=payload.get("responsible"),
        status=payload.get("status") or MaintenanceStatus.PLANNED,
        notes=payload.get("notes"),
        created_by=current_user.username,
    )
    db.add(row)
    db.commit()
    return _eam_plan(row)


@router.put("/eam/plans/{plan_id}")
def update_eam_plan(
    plan_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_or_404(
        db, MaintenancePlan, MaintenancePlan.plan_id == plan_id,
        MaintenancePlan.is_deleted == False, label="维护计划 ",
    )
    if "maintenance_type" in payload and payload["maintenance_type"]:
        row.maintenance_type = payload["maintenance_type"]
    if "cycle_days" in payload and payload["cycle_days"] is not None:
        row.cycle_days = int(payload["cycle_days"])
    if "next_due_at" in payload:
        row.next_due_at = (
            datetime.fromisoformat(str(payload["next_due_at"])) if payload["next_due_at"] else row.next_due_at
        )
    if "responsible" in payload:
        row.responsible = payload["responsible"]
    if "status" in payload and payload["status"]:
        row.status = payload["status"]
    if "notes" in payload:
        row.notes = payload["notes"]
    row.updated_by = current_user.username
    db.commit()
    return _eam_plan(row)


@router.get("/eam/orders")
def eam_orders(
    skip: int = 0,
    limit: int = 200,
    resource_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    plan_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(MaintenanceOrder).filter(MaintenanceOrder.is_deleted == False)
    if resource_id:
        query = query.filter(MaintenanceOrder.resource_id == resource_id)
    if status_filter:
        query = query.filter(MaintenanceOrder.status == status_filter)
    if plan_id:
        query = query.filter(MaintenanceOrder.plan_id == plan_id)
    total = query.count()
    rows = query.order_by(MaintenanceOrder.planned_date.desc(), MaintenanceOrder.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_eam_order(row) for row in rows]}


@router.post("/eam/orders/{order_number}/complete")
def complete_eam_order(
    order_number: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = EamEngine.complete_order(
            db,
            order_number,
            executed_by=payload.get("executed_by") or current_user.username,
            downtime_hours=payload.get("downtime_hours"),
            result_note=payload.get("result_note"),
        )
        db.commit()
        return _eam_order(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/eam/failures")
def eam_failures(
    skip: int = 0,
    limit: int = 200,
    resource_id: Optional[str] = None,
    work_center_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(EquipmentFailure).filter(EquipmentFailure.is_deleted == False)
    if resource_id:
        query = query.filter(EquipmentFailure.resource_id == resource_id)
    if work_center_id:
        query = query.filter(EquipmentFailure.work_center_id == work_center_id)
    if status_filter:
        query = query.filter(EquipmentFailure.status == status_filter)
    if severity:
        query = query.filter(EquipmentFailure.severity == severity)
    total = query.count()
    rows = query.order_by(EquipmentFailure.occurred_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_eam_failure(row) for row in rows]}


@router.post("/eam/failures", status_code=status.HTTP_201_CREATED)
def report_eam_failure(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource_id = payload.get("resource_id")
    if not resource_id:
        raise HTTPException(status_code=400, detail="resource_id 不能为空")
    occurred_at = payload.get("occurred_at")
    try:
        row = EamEngine.record_failure(
            db,
            resource_id=resource_id,
            occurred_at=datetime.fromisoformat(str(occurred_at)) if occurred_at else None,
            severity=payload.get("severity") or "MEDIUM",
            description=payload.get("description"),
            reported_by=current_user.username,
            downtime_hours=payload.get("downtime_hours"),
        )
        db.commit()
        return _eam_failure(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/eam/failures/{failure_number}/resolve")
def resolve_eam_failure(
    failure_number: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = EamEngine.resolve_failure(
            db,
            failure_number,
            root_cause=payload.get("root_cause"),
            action_taken=payload.get("action_taken"),
            downtime_hours=payload.get("downtime_hours"),
            resolved_by=current_user.username,
        )
        db.commit()
        return _eam_failure(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/eam/oee")
def eam_oee(work_center_id: Optional[str] = None, db: Session = Depends(get_db)):
    return EamEngine.oee_snapshot(db, work_center_id=work_center_id)


@router.post("/eam/generate-due-orders")
def eam_generate_due_orders(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    as_of = payload.get("as_of")
    try:
        rows = EamEngine.generate_due_orders(
            db,
            as_of=datetime.fromisoformat(str(as_of)) if as_of else None,
            created_by=current_user.username,
        )
        db.commit()
        return {"generated": len(rows), "items": [_eam_order(row) for row in rows]}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


# ── 演示数据一键重置 ────────────────────────────────────────────────
@router.post("/demo/reset")
def demo_reset(
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空运行时演示数据并重建一套可展示的演示场景（仅管理员）。

    清空范围：排程批次/工序/异常、插单场景/影响、维护计划/工单、故障记录。
    保留范围：客户、订单、BOM、工艺路线、生产订单、物料、成本费率等主数据。
    """
    role = getattr(current_user.role, "value", current_user.role)
    if str(role).upper() != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以重置演示数据",
        )
    payload = payload or {}
    try:
        result = reset_planning_demo(
            db,
            created_by=current_user.username,
            rebuild_run=bool(payload.get("rebuild_run", True)),
            with_scenario=bool(payload.get("with_scenario", True)),
        )
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - 重置失败需回滚并保留原始错误
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重置演示数据失败: {exc}")

