"""MPS engine: sales orders + forecast + safety stock -> time-phased master schedule."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.common.models.mm import Material
from backend.common.models.planning import (
    Forecast,
    MpsEntry,
    MpsPlan,
    PlannedOrder,
    PlannedOrderStatus,
    PlannedOrderType,
    PlannerAction,
)
from backend.common.models.pp import OperationReport, ProductionOrder as PpProductionOrder, ProductionOrderStatus
from backend.common.models.sd import SalesOrder, SalesOrderStatus
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import (
    ZERO,
    add_days,
    as_str,
    dec,
    get_material,
    get_policy,
    iter_week_buckets,
    lead_time_days,
    lot_size,
    material_unit,
    week_start,
)


OPEN_SALES_STATUSES = [
    SalesOrderStatus.APPROVED,
    SalesOrderStatus.IN_PRODUCTION,
]

FIRM_PRODUCTION_STATUSES = [
    ProductionOrderStatus.RELEASED,
    ProductionOrderStatus.IN_PRODUCTION,
]


class MpsEngine:
    """Generate a time-phased MPS from independent demand and firm supply."""

    @staticmethod
    def generate(
        db: Session,
        *,
        horizon_start: datetime,
        horizon_end: datetime,
        plan_name: Optional[str] = None,
        plant_id: Optional[str] = None,
        demand_source: str = "MIXED",
        include_forecast: bool = True,
        include_safety_stock: bool = True,
        created_by: Optional[str] = None,
    ) -> MpsPlan:
        if horizon_end < horizon_start:
            raise ValueError("MPS 计划结束日期不能早于开始日期")

        buckets = iter_week_buckets(horizon_start, horizon_end)
        if not buckets:
            raise ValueError("MPS 计划区间为空")

        # 1) Collect independent demand by material and bucket.
        sales_by_material: dict[str, dict[datetime, Decimal]] = {}
        forecast_by_material: dict[str, dict[datetime, Decimal]] = {}
        units: dict[str, str] = {}
        materials: dict[str, Material] = {}

        sales_orders = (
            db.query(SalesOrder)
            .filter(
                SalesOrder.status.in_(OPEN_SALES_STATUSES),
                SalesOrder.delivery_date >= horizon_start,
                SalesOrder.delivery_date <= horizon_end,
                SalesOrder.is_deleted == False,
            )
            .all()
        )
        for order in sales_orders:
            material_code = order.material_code
            if not material_code:
                continue
            material = get_material(db, material_code)
            if material is None:
                continue
            if as_str(material.material_type) not in ("FG", "SEMI"):
                continue
            qty = dec(order.production_quantity or order.quantity)
            if qty <= ZERO:
                continue
            bucket = week_start(order.delivery_date)
            sales_by_material.setdefault(material_code, {}).setdefault(bucket, ZERO)
            sales_by_material[material_code][bucket] += qty
            materials[material_code] = material
            units[material_code] = material_unit(material)

        if include_forecast:
            forecasts = (
                db.query(Forecast)
                .filter(
                    Forecast.status.in_(["RELEASED", "ACTIVE", "CONFIRMED"]),
                    Forecast.due_date >= horizon_start,
                    Forecast.due_date <= horizon_end,
                    Forecast.is_deleted == False,
                )
                .all()
            )
            for forecast in forecasts:
                material = get_material(db, forecast.material_code)
                if material is None:
                    continue
                if as_str(material.material_type) not in ("FG", "SEMI"):
                    continue
                remaining = dec(forecast.quantity) - dec(forecast.consumed_quantity)
                if remaining <= ZERO:
                    continue
                bucket = week_start(forecast.due_date)
                forecast_by_material.setdefault(forecast.material_code, {}).setdefault(bucket, ZERO)
                forecast_by_material[forecast.material_code][bucket] += remaining
                materials[forecast.material_code] = material
                units[forecast.material_code] = material_unit(material)

        if include_safety_stock:
            for material in db.query(Material).filter(Material.is_deleted == False).all():
                if as_str(material.material_type) not in ("FG", "SEMI"):
                    continue
                if dec(material.safety_stock) > ZERO:
                    materials[material.material_code] = material
                    units[material.material_code] = material_unit(material)

        if not materials:
            raise ValueError("MPS 区间内没有可计划的销售订单、预测或安全库存")

        # 2) Firm supply: on-hand + firm production orders + open purchase orders + firmed planned orders.
        scheduled_receipts: dict[str, dict[datetime, Decimal]] = {}
        for material_code in materials:
            scheduled_receipts[material_code] = {}

        firm_orders = (
            db.query(PpProductionOrder)
            .filter(
                PpProductionOrder.status.in_(FIRM_PRODUCTION_STATUSES),
                PpProductionOrder.material_code.in_(list(materials.keys())),
                PpProductionOrder.is_deleted == False,
            )
            .all()
        )
        for order in firm_orders:
            due = order.planned_finish_date or order.planned_start_date
            if not due or due > horizon_end:
                continue
            reported = (
                db.query(func.coalesce(func.sum(OperationReport.good_quantity), 0))
                .filter(
                    OperationReport.production_order_number == order.order_number,
                    OperationReport.is_deleted == False,
                )
                .scalar()
            )
            remaining = max(ZERO, dec(order.quantity) - dec(reported))
            if remaining <= ZERO:
                continue
            bucket = week_start(due)
            scheduled_receipts[order.material_code].setdefault(bucket, ZERO)
            scheduled_receipts[order.material_code][bucket] += remaining

        from backend.common.models.planning import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus

        po_rows = (
            db.query(PurchaseOrderLine, PurchaseOrder)
            .join(PurchaseOrder, PurchaseOrder.purchase_order_number == PurchaseOrderLine.purchase_order_number)
            .filter(
                PurchaseOrder.status.in_([
                    PurchaseOrderStatus.RELEASED,
                    PurchaseOrderStatus.PARTIALLY_RECEIVED,
                ]),
                PurchaseOrderLine.material_code.in_(list(materials.keys())),
                PurchaseOrderLine.is_deleted == False,
            )
            .all()
        )
        for line, po in po_rows:
            due = line.expected_date or po.expected_date
            if not due or due > horizon_end:
                continue
            remaining = max(ZERO, dec(line.quantity) - dec(line.received_quantity))
            if remaining <= ZERO:
                continue
            bucket = week_start(due)
            scheduled_receipts[line.material_code].setdefault(bucket, ZERO)
            scheduled_receipts[line.material_code][bucket] += remaining

        firmed_plans = (
            db.query(PlannedOrder)
            .filter(
                PlannedOrder.status.in_([PlannedOrderStatus.FIRMED, PlannedOrderStatus.RELEASED]),
                PlannedOrder.order_type != PlannedOrderType.PURCHASE,
                PlannedOrder.material_code.in_(list(materials.keys())),
                PlannedOrder.is_deleted == False,
            )
            .all()
        )
        for plan in firmed_plans:
            if plan.due_date > horizon_end:
                continue
            bucket = week_start(plan.due_date)
            scheduled_receipts[plan.material_code].setdefault(bucket, ZERO)
            scheduled_receipts[plan.material_code][bucket] += dec(plan.quantity)

        # 3) Create the MPS header.
        mps_number = NumberGenerator.generate_document_number(db, MpsPlan, "mps_number", "MPS", 3)
        plan = MpsPlan(
            mps_number=mps_number,
            version="1",
            plan_name=plan_name or f"MPS {horizon_start:%Y-%m-%d} ~ {horizon_end:%Y-%m-%d}",
            plant_id=plant_id,
            horizon_start=horizon_start,
            horizon_end=horizon_end,
            bucket_type="WEEK",
            status="DRAFT",
            demand_source=demand_source,
            generated_by=created_by,
            generated_at=datetime.now(),
            created_by=created_by,
        )
        db.add(plan)
        db.flush()

        total_gross = ZERO
        total_planned = ZERO
        line_number = 0

        for material_code in sorted(materials.keys()):
            material = materials[material_code]
            policy = get_policy(db, material_code)
            sales = sales_by_material.get(material_code, {})
            forecasts = forecast_by_material.get(material_code, {})
            receipts = scheduled_receipts.get(material_code, {})
            available = dec(material.current_stock)
            safety_stock = dec(material.safety_stock)
            if policy is not None and policy.safety_stock is not None:
                safety_stock = max(safety_stock, dec(policy.safety_stock))
            lead_days = lead_time_days(policy, material)

            for bucket in buckets:
                sales_qty = dec(sales.get(bucket, ZERO))
                forecast_qty = dec(forecasts.get(bucket, ZERO))
                # Forecast consumption: sales in the bucket consumes forecast.
                forecast_residual = max(ZERO, forecast_qty - sales_qty)
                if demand_source == "SALES":
                    forecast_residual = ZERO
                elif demand_source == "FORECAST":
                    sales_qty = ZERO

                gross = sales_qty + forecast_residual
                receipt = dec(receipts.get(bucket, ZERO))
                opening = available
                projected = opening + receipt - gross
                net_requirement = max(ZERO, safety_stock - projected)
                planned_receipt = lot_size(policy, net_requirement) if net_requirement > ZERO else ZERO
                projected += planned_receipt

                if net_requirement > ZERO:
                    if bucket <= add_days(datetime.now(), lead_days):
                        action = PlannerAction.EXPEDITE
                    else:
                        action = PlannerAction.RELEASE
                elif gross == ZERO and projected > safety_stock * 2:
                    action = PlannerAction.DELAY
                else:
                    action = PlannerAction.NONE

                line_number += 1
                entry = MpsEntry(
                    mps_number=mps_number,
                    line_number=line_number,
                    material_code=material_code,
                    bucket_date=bucket,
                    opening_stock=opening,
                    gross_requirement=gross,
                    sales_demand=sales_qty,
                    forecast_demand=forecast_residual,
                    scheduled_receipt=receipt,
                    projected_available=projected,
                    net_requirement=net_requirement,
                    planned_receipt=planned_receipt,
                    planner_action=action,
                    created_by=created_by,
                )
                db.add(entry)
                total_gross += gross
                total_planned += planned_receipt
                available = projected

        plan.total_gross = total_gross
        plan.total_planned = total_planned
        db.flush()
        return plan

    @staticmethod
    def release(db: Session, mps_number: str, released_by: Optional[str] = None) -> MpsPlan:
        plan = db.query(MpsPlan).filter(MpsPlan.mps_number == mps_number).first()
        if not plan:
            raise ValueError(f"MPS 计划不存在: {mps_number}")
        if as_str(plan.status) == "RELEASED":
            return plan
        if as_str(plan.status) == "CLOSED":
            raise ValueError("已关闭的 MPS 不能下达")
        plan.status = "RELEASED"
        plan.updated_by = released_by
        db.flush()
        return plan
