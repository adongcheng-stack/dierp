"""Kitting (material readiness) analysis.

A kitting result answers one question: *for this order, which components are
short, how many, and when do we need them?*  It is intentionally a one-level
BOM check: multi-level availability is MRP's job, kitting is the shop-floor
gate before releasing an order.
"""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common.models.planning import (
    KittingResult,
    KitStatus,
    PlannedOrder,
    PlannedOrderStatus,
    PlannedOrderType,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)
from backend.common.models.pp import ProductionOrder
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import (
    ZERO,
    bom_components,
    dec,
    get_bom,
    get_material,
)

OPEN_PO_STATUSES = [
    PurchaseOrderStatus.RELEASED,
    PurchaseOrderStatus.PARTIALLY_RECEIVED,
]


class KittingService:
    """Compute and persist material readiness snapshots."""

    # ── public API ─────────────────────────────────────────────────────
    @staticmethod
    def analyze_production_order(
        db: Session,
        order_number: str,
        *,
        persist: bool = True,
        checked_by: Optional[str] = None,
    ) -> KittingResult:
        order = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.order_number == order_number,
                ProductionOrder.is_deleted == False,
            )
            .first()
        )
        if order is None:
            raise ValueError(f"生产订单不存在: {order_number}")
        due = order.planned_start_date or order.planned_finish_date or datetime.now()
        return KittingService._analyze(
            db,
            source_type="PRODUCTION_ORDER",
            source_ref=order.order_number,
            material_code=order.material_code,
            quantity=dec(order.quantity),
            due_date=due,
            persist=persist,
            checked_by=checked_by,
        )

    @staticmethod
    def analyze_planned_order(
        db: Session,
        planned_order_number: str,
        *,
        persist: bool = True,
        checked_by: Optional[str] = None,
    ) -> KittingResult:
        plan = (
            db.query(PlannedOrder)
            .filter(
                PlannedOrder.planned_order_number == planned_order_number,
                PlannedOrder.is_deleted == False,
            )
            .first()
        )
        if plan is None:
            raise ValueError(f"计划订单不存在: {planned_order_number}")
        if plan.order_type != PlannedOrderType.PRODUCTION:
            raise ValueError("只有自制类计划订单需要齐套分析")
        return KittingService._analyze(
            db,
            source_type="PLANNED_ORDER",
            source_ref=plan.planned_order_number,
            material_code=plan.material_code,
            quantity=dec(plan.quantity),
            due_date=plan.start_date or plan.due_date,
            persist=persist,
            checked_by=checked_by,
        )

    # ── internals ──────────────────────────────────────────────────────
    @staticmethod
    def _analyze(
        db: Session,
        *,
        source_type: str,
        source_ref: str,
        material_code: str,
        quantity: Decimal,
        due_date: datetime,
        persist: bool,
        checked_by: Optional[str],
    ) -> KittingResult:
        components = KittingService._component_requirements(
            db, material_code, quantity, due_date
        )

        required_total = sum((row["required_qty"] for row in components), ZERO)
        available_total = sum((row["available_qty"] for row in components), ZERO)
        shortage_total = sum((row["shortage_qty"] for row in components), ZERO)

        if not components:
            kit_status = KitStatus.SHORT
            remarks = "缺少已发布 BOM 或 BOM 无组件，无法齐套"
        elif shortage_total <= ZERO:
            kit_status = KitStatus.FULL
            remarks = f"{len(components)} 项组件齐套"
        elif available_total <= ZERO:
            kit_status = KitStatus.SHORT
            remarks = f"{len([row for row in components if row['shortage_qty'] > ZERO])} 项组件缺料"
        else:
            kit_status = KitStatus.PARTIAL
            remarks = f"{len([row for row in components if row['shortage_qty'] > ZERO])} 项组件部分缺料"

        result = (
            db.query(KittingResult)
            .filter(
                KittingResult.source_type == source_type,
                KittingResult.source_ref == source_ref,
                KittingResult.is_deleted == False,
            )
            .first()
        )
        if result is None:
            result = KittingResult(
                result_number=NumberGenerator.generate_document_number(
                    db, KittingResult, "result_number", "KIT", 4
                ),
                source_type=source_type,
                source_ref=source_ref,
                created_by=checked_by,
            )
            db.add(result)

        result.material_code = material_code
        result.kit_status = kit_status
        result.required_qty = required_total
        result.available_qty = available_total
        result.shortage_qty = shortage_total
        result.shortage_details = json.dumps(
            [
                {
                    **row,
                    "required_qty": float(row["required_qty"]),
                    "available_qty": float(row["available_qty"]),
                    "shortage_qty": float(row["shortage_qty"]),
                }
                for row in components
                if row["shortage_qty"] > ZERO
            ],
            ensure_ascii=False,
        )
        result.checked_at = datetime.now()
        result.updated_by = checked_by
        result.remarks = remarks
        if persist:
            db.flush()
        return result

    @staticmethod
    def _component_requirements(
        db: Session,
        material_code: str,
        quantity: Decimal,
        due_date: datetime,
    ) -> list[dict]:
        # Stale orders may predate the current released BOM; analyse them against
        # today's effective engineering data instead of reporting "no BOM".
        bom_date = due_date if due_date and due_date >= datetime.now() else datetime.now()
        bom = get_bom(db, material_code, bom_date)
        if bom is None:
            return []

        base_quantity = dec(bom.base_quantity) or Decimal("1")
        rows: list[dict] = []
        for item in bom_components(db, bom):
            required = (
                quantity
                / base_quantity
                * dec(item.quantity)
                * (Decimal("1") + dec(item.scrap_rate) / Decimal("100"))
            )
            if required <= ZERO:
                continue
            required = required.quantize(Decimal("0.01"))
            available = KittingService._available_qty(db, item.material_code, due_date)
            shortage = max(ZERO, required - available)
            material = get_material(db, item.material_code)
            rows.append(
                {
                    "material_code": item.material_code,
                    "material_name": material.material_name if material else None,
                    "unit": item.unit or (material.unit if material else "PCS"),
                    "required_qty": required,
                    "available_qty": available,
                    "shortage_qty": shortage,
                    "needed_date": due_date.date().isoformat() if due_date else None,
                }
            )
        return rows

    @staticmethod
    def _available_qty(db: Session, material_code: str, due_date: datetime) -> Decimal:
        """On-hand plus open purchase orders that arrive before the order start."""
        material = get_material(db, material_code)
        available = dec(material.current_stock) if material else ZERO

        incoming = (
            db.query(func.coalesce(func.sum(PurchaseOrderLine.quantity - PurchaseOrderLine.received_quantity), 0))
            .join(
                PurchaseOrder,
                PurchaseOrder.purchase_order_number == PurchaseOrderLine.purchase_order_number,
            )
            .filter(
                PurchaseOrderLine.material_code == material_code,
                PurchaseOrderLine.is_deleted == False,
                PurchaseOrder.status.in_(OPEN_PO_STATUSES),
                PurchaseOrder.is_deleted == False,
            )
            .scalar()
        )
        available += dec(incoming)
        return max(ZERO, available)
