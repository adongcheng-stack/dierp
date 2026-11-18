"""MRP engine: multi-level BOM explosion, netting, lot sizing and pegging.

The engine is deliberately explicit rather than magic:
  1. independent demand (MPS / sales / forecast / safety stock)
  2. firm supply (on hand, production orders, purchase orders, firmed plans)
  3. low-level-code driven netting
  4. planned production/purchase orders + dependent requirements
  5. pegging, exceptions and kitting hand-off
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common.models.mm import Material
from backend.common.models.planning import (
    DemandType,
    ExceptionSeverity,
    Forecast,
    KittingResult,
    MpsEntry,
    MpsPlan,
    MrpException,
    MrpExceptionType,
    MrpRequirement,
    MrpRun,
    MrpRunStatus,
    MrpRunType,
    PeggingLink,
    PlannedOrder,
    PlannedOrderStatus,
    PlannedOrderType,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    ResolutionStatus,
    SupplyType,
)
from backend.common.models.pp import OperationReport, ProductionOrder, ProductionOrderStatus
from backend.common.models.sd import SalesOrder, SalesOrderStatus
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import (
    ZERO,
    add_days,
    as_str,
    bom_components,
    dec,
    get_bom,
    get_material,
    get_policy,
    lead_time_days,
    lot_size,
    low_level_codes,
    material_unit,
    procurement_type,
    safety_time_days,
)

OPEN_SALES_STATUSES = [SalesOrderStatus.APPROVED, SalesOrderStatus.IN_PRODUCTION]
FIRM_PRODUCTION_STATUSES = [ProductionOrderStatus.RELEASED, ProductionOrderStatus.IN_PRODUCTION]


@dataclass
class Demand:
    material_code: str
    quantity: Decimal
    due_date: datetime
    demand_type: str
    demand_ref: str
    level: int = 0
    parent_planned_order: Optional[str] = None


@dataclass
class Supply:
    material_code: str
    quantity: Decimal
    available_date: datetime
    supply_type: str
    supply_ref: str
    remaining: Decimal = field(init=False)

    def __post_init__(self) -> None:
        self.remaining = self.quantity


class SupplyPool:
    def __init__(self) -> None:
        self.items: list[Supply] = []

    def add(self, supply: Supply) -> None:
        self.items.append(supply)

    def consume(self, due_date: datetime, quantity: Decimal) -> tuple[list[tuple[Supply, Decimal]], Decimal]:
        remaining = quantity
        allocations: list[tuple[Supply, Decimal]] = []
        for supply in sorted(self.items, key=lambda item: item.available_date):
            if remaining <= ZERO:
                break
            if supply.remaining <= ZERO:
                continue
            if supply.available_date > due_date:
                continue
            take = min(supply.remaining, remaining)
            if take <= ZERO:
                continue
            supply.remaining -= take
            remaining -= take
            allocations.append((supply, take))
        return allocations, remaining

    def on_hand_remaining(self) -> Decimal:
        return sum(
            (item.remaining for item in self.items if item.supply_type == SupplyType.ON_HAND.value),
            ZERO,
        )


class MrpEngine:
    """Stateless MRP service. All persistence goes through the caller's session."""

    @staticmethod
    def run(
        db: Session,
        *,
        horizon_start: datetime,
        horizon_end: datetime,
        run_type: str = "REGENERATIVE",
        demand_source: str = "AUTO",
        mps_number: Optional[str] = None,
        plant_id: Optional[str] = None,
        include_forecast: bool = True,
        include_safety_stock: bool = True,
        run_by: Optional[str] = None,
    ) -> MrpRun:
        if horizon_end < horizon_start:
            raise ValueError("MRP 计划结束日期不能早于开始日期")

        run_number = NumberGenerator.generate_document_number(db, MrpRun, "run_number", "MRP", 3)
        run = MrpRun(
            run_number=run_number,
            run_type=run_type,
            status=MrpRunStatus.RUNNING,
            horizon_start=horizon_start,
            horizon_end=horizon_end,
            demand_source=demand_source,
            mps_number=mps_number,
            plant_id=plant_id,
            started_at=datetime.now(),
            run_by=run_by,
            created_by=run_by,
        )
        db.add(run)
        db.flush()

        # A regenerative run supersedes previous unfirm suggestions.
        if run_type == MrpRunType.REGENERATIVE.value:
            query = db.query(PlannedOrder).filter(
                PlannedOrder.status == PlannedOrderStatus.PLANNED,
                PlannedOrder.is_deleted == False,
            )
            if plant_id:
                query = query.filter(PlannedOrder.material_code.in_(
                    db.query(Material.material_code).filter(Material.is_deleted == False)
                ))
            query.update(
                {PlannedOrder.status: PlannedOrderStatus.CANCELLED, PlannedOrder.updated_by: run_by},
                synchronize_session=False,
            )
            db.flush()

        low_level: dict[str, int] = {}
        pools: dict[str, SupplyPool] = defaultdict(SupplyPool)
        demands_by_level: dict[int, list[Demand]] = defaultdict(list)
        independent_count = 0
        exception_keys: set[tuple[str, str, str]] = set()

        def add_exception(
            exception_type: MrpExceptionType,
            severity: ExceptionSeverity,
            material_code: Optional[str],
            *,
            shortage_qty: Decimal = ZERO,
            shortage_date: Optional[datetime] = None,
            suggestion: Optional[str] = None,
            requirement_ref: Optional[str] = None,
            planned_order_number: Optional[str] = None,
        ) -> None:
            key = (exception_type.value, material_code or "", requirement_ref or "")
            if key in exception_keys:
                return
            exception_keys.add(key)
            db.add(MrpException(
                run_number=run_number,
                exception_type=exception_type,
                severity=severity,
                material_code=material_code,
                requirement_ref=requirement_ref,
                planned_order_number=planned_order_number,
                shortage_qty=shortage_qty,
                shortage_date=shortage_date,
                suggestion=suggestion,
                resolution_status=ResolutionStatus.OPEN,
                created_by=run_by,
            ))

        # ── 1. Build independent demand ──────────────────────────────────
        selected_mps: Optional[MpsPlan] = None
        if demand_source in ("AUTO", "MPS"):
            query = db.query(MpsPlan).filter(
                MpsPlan.status == "RELEASED",
                MpsPlan.is_deleted == False,
                MpsPlan.horizon_end >= horizon_start,
                MpsPlan.horizon_start <= horizon_end,
            )
            if mps_number:
                query = query.filter(MpsPlan.mps_number == mps_number)
            selected_mps = query.order_by(MpsPlan.horizon_start.desc(), MpsPlan.id.desc()).first()

        roots: set[str] = set()
        if selected_mps is not None:
            run.mps_number = selected_mps.mps_number
            entries = (
                db.query(MpsEntry)
                .filter(MpsEntry.mps_number == selected_mps.mps_number, MpsEntry.is_deleted == False)
                .all()
            )
            for entry in entries:
                if dec(entry.planned_receipt) <= ZERO:
                    continue
                demands_by_level[0].append(Demand(
                    material_code=entry.material_code,
                    quantity=dec(entry.planned_receipt),
                    due_date=entry.bucket_date,
                    demand_type=DemandType.MPS.value,
                    demand_ref=selected_mps.mps_number,
                ))
                roots.add(entry.material_code)
                independent_count += 1
        else:
            # Sales demand
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
            sales_by_week: dict[tuple[str, datetime], Decimal] = defaultdict(lambda: ZERO)
            for order in sales_orders:
                if not order.material_code:
                    continue
                material = get_material(db, order.material_code)
                if material is None:
                    continue
                qty = dec(order.production_quantity or order.quantity)
                if qty <= ZERO:
                    continue
                demands_by_level[0].append(Demand(
                    material_code=order.material_code,
                    quantity=qty,
                    due_date=order.delivery_date,
                    demand_type=DemandType.SALES_ORDER.value,
                    demand_ref=order.order_number,
                ))
                roots.add(order.material_code)
                independent_count += 1
                week = order.delivery_date - timedelta(days=order.delivery_date.weekday())
                week = week.replace(hour=0, minute=0, second=0, microsecond=0)
                sales_by_week[(order.material_code, week)] += qty

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
                    remaining = dec(forecast.quantity) - dec(forecast.consumed_quantity)
                    if remaining <= ZERO:
                        continue
                    week = forecast.due_date - timedelta(days=forecast.due_date.weekday())
                    week = week.replace(hour=0, minute=0, second=0, microsecond=0)
                    consumed = sales_by_week.get((forecast.material_code, week), ZERO)
                    residual = max(ZERO, remaining - consumed)
                    if residual <= ZERO:
                        continue
                    demands_by_level[0].append(Demand(
                        material_code=forecast.material_code,
                        quantity=residual,
                        due_date=forecast.due_date,
                        demand_type=DemandType.FORECAST.value,
                        demand_ref=forecast.forecast_number,
                    ))
                    roots.add(forecast.material_code)
                    independent_count += 1

        # Safety stock is a standing requirement at the start of the horizon.
        if include_safety_stock:
            for material in db.query(Material).filter(Material.is_deleted == False).all():
                if dec(material.safety_stock) <= ZERO:
                    continue
                policy = get_policy(db, material.material_code)
                if policy is not None and as_str(policy.mrp_type) == "NONE":
                    continue
                demands_by_level[0].append(Demand(
                    material_code=material.material_code,
                    quantity=dec(policy.safety_stock) if policy and policy.safety_stock else dec(material.safety_stock),
                    due_date=horizon_start,
                    demand_type=DemandType.SAFETY_STOCK.value,
                    demand_ref=f"SAFETY-{material.material_code}",
                ))
                roots.add(material.material_code)
                independent_count += 1

        # ── 2. Firm supply and firm-order dependent demand ───────────────
        materials = {
            material.material_code: material
            for material in db.query(Material).filter(Material.is_deleted == False).all()
        }
        for material in materials.values():
            pools[material.material_code].add(Supply(
                material_code=material.material_code,
                quantity=dec(material.current_stock),
                available_date=datetime(1970, 1, 1),
                supply_type=SupplyType.ON_HAND.value,
                supply_ref="ON_HAND",
            ))

        def reported_qty(order_number: str) -> Decimal:
            value = (
                db.query(func.coalesce(func.sum(OperationReport.good_quantity), 0))
                .filter(
                    OperationReport.production_order_number == order_number,
                    OperationReport.is_deleted == False,
                )
                .scalar()
            )
            return dec(value)

        firm_orders = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.status.in_(FIRM_PRODUCTION_STATUSES),
                ProductionOrder.is_deleted == False,
            )
            .all()
        )
        for order in firm_orders:
            remaining = max(ZERO, dec(order.quantity) - reported_qty(order.order_number))
            if remaining <= ZERO:
                continue
            due = order.planned_finish_date or order.planned_start_date
            start = order.planned_start_date or datetime.now()
            # Ignore stale orders that are far behind the horizon: they are either
            # already physically complete or belong to a previous planning cycle.
            if due and due < horizon_start - timedelta(days=7):
                continue
            if due and due <= horizon_end:
                pools[order.material_code].add(Supply(
                    material_code=order.material_code,
                    quantity=remaining,
                    available_date=due,
                    supply_type=SupplyType.PRODUCTION_ORDER.value,
                    supply_ref=order.order_number,
                ))
            if start <= horizon_end:
                # A firm order is also a demand for its components.
                MrpEngine._explode(
                    db,
                    material_code=order.material_code,
                    quantity=remaining,
                    due_date=start,
                    demand_type=DemandType.DEPENDENT.value,
                    demand_ref=order.order_number,
                    parent_ref=order.order_number,
                    level=0,
                    low_level=low_level,
                    demands_by_level=demands_by_level,
                    add_exception=add_exception,
                    run_by=run_by,
                )

        po_rows = (
            db.query(PurchaseOrderLine, PurchaseOrder)
            .join(PurchaseOrder, PurchaseOrder.purchase_order_number == PurchaseOrderLine.purchase_order_number)
            .filter(
                PurchaseOrder.status.in_([
                    PurchaseOrderStatus.RELEASED,
                    PurchaseOrderStatus.PARTIALLY_RECEIVED,
                ]),
                PurchaseOrderLine.is_deleted == False,
            )
            .all()
        )
        for line, po in po_rows:
            remaining = max(ZERO, dec(line.quantity) - dec(line.received_quantity))
            if remaining <= ZERO:
                continue
            due = line.expected_date or po.expected_date
            if not due or due > horizon_end:
                continue
            pools[line.material_code].add(Supply(
                material_code=line.material_code,
                quantity=remaining,
                available_date=due,
                supply_type=SupplyType.PURCHASE_ORDER.value,
                supply_ref=po.purchase_order_number,
            ))

        firmed_plans = (
            db.query(PlannedOrder)
            .filter(
                PlannedOrder.status.in_([PlannedOrderStatus.FIRMED, PlannedOrderStatus.RELEASED]),
                PlannedOrder.is_deleted == False,
                PlannedOrder.due_date <= horizon_end,
            )
            .all()
        )
        for plan in firmed_plans:
            pools[plan.material_code].add(Supply(
                material_code=plan.material_code,
                quantity=dec(plan.quantity),
                available_date=plan.due_date,
                supply_type=SupplyType.PLANNED_ORDER.value,
                supply_ref=plan.planned_order_number,
            ))

        # ── 3. Low-level codes and level buckets ────────────────────────
        all_roots = set(roots) | {order.material_code for order in firm_orders} | set(materials)
        low_level.update(low_level_codes(db, all_roots))
        for level in list(demands_by_level.keys()):
            for demand in demands_by_level[level]:
                demand.level = max(level, low_level.get(demand.material_code, level))
        # Re-bucket after assigning final levels.
        rebucketed: dict[int, list[Demand]] = defaultdict(list)
        for demands in demands_by_level.values():
            for demand in demands:
                rebucketed[demand.level].append(demand)
        demands_by_level = rebucketed

        requirement_count = 0
        planned_production = 0
        planned_purchase = 0
        shortage_count = 0

        # ── 4. Level-by-level netting ───────────────────────────────────
        while demands_by_level:
            level = min(demands_by_level.keys())
            level_demands = demands_by_level.pop(level)
            by_material: dict[str, list[Demand]] = defaultdict(list)
            for demand in level_demands:
                by_material[demand.material_code].append(demand)

            for material_code, mat_demands in by_material.items():
                material = materials.get(material_code) or get_material(db, material_code)
                policy = get_policy(db, material_code)
                pool = pools[material_code]

                for demand in sorted(mat_demands, key=lambda item: item.due_date):
                    if demand.quantity <= ZERO:
                        continue
                    allocations, shortage = pool.consume(demand.due_date, demand.quantity)
                    covered = demand.quantity - shortage

                    requirement_count += 1
                    req_row = MrpRequirement(
                        run_number=run_number,
                        line_number=requirement_count,
                        material_code=material_code,
                        requirement_level=demand.level,
                        demand_type=demand.demand_type,
                        demand_ref=demand.demand_ref,
                        parent_planned_order=demand.parent_planned_order,
                        quantity=demand.quantity,
                        covered_qty=covered,
                        shortage_qty=shortage,
                        due_date=demand.due_date,
                        status="COVERED" if shortage <= ZERO else "SHORTAGE",
                        created_by=run_by,
                    )
                    db.add(req_row)
                    db.flush()

                    for supply, qty in allocations:
                        db.add(PeggingLink(
                            run_number=run_number,
                            planned_order_number=None,
                            demand_type=demand.demand_type,
                            demand_ref=demand.demand_ref,
                            supply_type=supply.supply_type,
                            supply_ref=supply.supply_ref,
                            pegged_qty=qty,
                            pegged_at=datetime.now(),
                            created_by=run_by,
                        ))

                    if shortage <= ZERO:
                        continue

                    shortage_count += 1
                    severity = (
                        ExceptionSeverity.CRITICAL
                        if demand.due_date <= add_days(datetime.now(), 3) or shortage >= demand.quantity / Decimal("2")
                        else ExceptionSeverity.WARNING
                    )
                    add_exception(
                        MrpExceptionType.SHORTAGE,
                        severity,
                        material_code,
                        shortage_qty=shortage,
                        shortage_date=demand.due_date,
                        suggestion=(
                            f"需求 {demand.demand_ref} 短缺 {shortage:.2f}，"
                            f"已生成计划订单；请确认提前期与供应商产能"
                        ),
                        requirement_ref=demand.demand_ref,
                    )

                    if policy is None:
                        add_exception(
                            MrpExceptionType.NO_POLICY,
                            ExceptionSeverity.WARNING,
                            material_code,
                            suggestion="未配置计划参数，已按物料主数据默认值推算；建议补齐批量规则与提前期",
                            requirement_ref=demand.demand_ref,
                        )

                    proc = procurement_type(policy, material)
                    order_type = (
                        PlannedOrderType.PURCHASE
                        if proc == "BUY"
                        else PlannedOrderType.PRODUCTION
                    )
                    lead_days = lead_time_days(policy, material) + safety_time_days(policy)
                    due_date = demand.due_date
                    start_date = due_date - timedelta(days=lead_days)
                    unit = material_unit(material)

                    if start_date < datetime.now():
                        add_exception(
                            MrpExceptionType.LEAD_TIME_VIOLATION,
                            ExceptionSeverity.WARNING,
                            material_code,
                            shortage_qty=shortage,
                            shortage_date=due_date,
                            suggestion="计划开始日期早于当前日期，存在压缩提前期或延期交付风险",
                            requirement_ref=demand.demand_ref,
                        )

                    for lot_qty in MrpEngine._split_lot(policy, shortage):
                        planned_number = NumberGenerator.generate_document_number(
                            db, PlannedOrder, "planned_order_number", "PLO", 4
                        )
                        planned = PlannedOrder(
                            planned_order_number=planned_number,
                            run_number=run_number,
                            order_type=order_type,
                            material_code=material_code,
                            quantity=lot_qty,
                            unit=unit,
                            start_date=start_date,
                            due_date=due_date,
                            status=PlannedOrderStatus.PLANNED,
                            procurement_type=proc,
                            lot_sizing_rule=as_str(getattr(policy, "lot_sizing_rule", None)),
                            lead_time_days=lead_days,
                            demand_type=demand.demand_type,
                            demand_ref=demand.demand_ref,
                            parent_planned_order=demand.parent_planned_order,
                            created_by=run_by,
                        )
                        db.add(planned)
                        db.flush()

                        if order_type == PlannedOrderType.PURCHASE:
                            planned_purchase += 1
                        else:
                            planned_production += 1

                        db.add(PeggingLink(
                            run_number=run_number,
                            planned_order_number=planned_number,
                            demand_type=demand.demand_type,
                            demand_ref=demand.demand_ref,
                            supply_type=SupplyType.PLANNED_ORDER.value,
                            supply_ref=planned_number,
                            pegged_qty=min(lot_qty, shortage),
                            pegged_at=datetime.now(),
                            created_by=run_by,
                        ))
                        pool.add(Supply(
                            material_code=material_code,
                            quantity=lot_qty,
                            available_date=due_date,
                            supply_type=SupplyType.PLANNED_ORDER.value,
                            supply_ref=planned_number,
                        ))

                        if order_type == PlannedOrderType.PRODUCTION:
                            MrpEngine._explode(
                                db,
                                material_code=material_code,
                                quantity=lot_qty,
                                due_date=start_date,
                                demand_type=DemandType.DEPENDENT.value,
                                demand_ref=planned_number,
                                parent_ref=planned_number,
                                level=demand.level,
                                low_level=low_level,
                                demands_by_level=demands_by_level,
                                add_exception=add_exception,
                                run_by=run_by,
                            )

        # ── 5. Excess detection ─────────────────────────────────────────
        for material_code, pool in pools.items():
            on_hand = pool.on_hand_remaining()
            material = materials.get(material_code)
            safety = dec(material.safety_stock) if material else ZERO
            if on_hand > ZERO and on_hand > max(safety * 3, Decimal("100")):
                add_exception(
                    MrpExceptionType.EXCESS,
                    ExceptionSeverity.INFO,
                    material_code,
                    shortage_qty=ZERO,
                    suggestion=f"期末预计库存 {on_hand} 高于安全库存 {safety} 的 3 倍，建议推迟采购或调拨",
                    requirement_ref=f"EXCESS-{material_code}",
                )

        # ── 6. Kitting snapshot for firm and new planned production orders ──
        MrpEngine._build_kitting_snapshot(db, run_number, run_by)

        # ── 7. Finish run ───────────────────────────────────────────────
        exception_count = db.query(func.count(MrpException.id)).filter(
            MrpException.run_number == run_number
        ).scalar() or 0
        run.status = MrpRunStatus.COMPLETED
        run.finished_at = datetime.now()
        run.total_demands = independent_count
        run.total_requirements = requirement_count
        run.planned_production_count = planned_production
        run.planned_purchase_count = planned_purchase
        run.exception_count = int(exception_count)
        run.shortage_count = shortage_count
        run.log_text = (
            f"独立需求 {independent_count} 条；需求行 {requirement_count} 条；"
            f"计划生产 {planned_production} 张；计划采购 {planned_purchase} 张；"
            f"异常 {exception_count} 条，其中短缺 {shortage_count} 条。"
        )
        db.flush()
        return run

    # ── helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _split_lot(policy, quantity: Decimal) -> list[Decimal]:
        """Apply lot sizing and split by max order quantity if configured."""
        if quantity <= ZERO:
            return []
        max_qty = dec(getattr(policy, "max_order_qty", 0))
        lots: list[Decimal] = []
        remaining = quantity
        guard = 0
        while remaining > ZERO and guard < 200:
            guard += 1
            chunk = min(remaining, max_qty) if max_qty > ZERO else remaining
            lot = lot_size(policy, chunk)
            if max_qty > ZERO:
                lot = min(lot, max_qty)
            if lot <= ZERO:
                break
            lots.append(lot)
            remaining -= lot
        return lots or [quantity]

    @staticmethod
    def _explode(
        db: Session,
        *,
        material_code: str,
        quantity: Decimal,
        due_date: datetime,
        demand_type: str,
        demand_ref: str,
        parent_ref: str,
        level: int,
        low_level: dict[str, int],
        demands_by_level: dict[int, list[Demand]],
        add_exception,
        run_by: Optional[str],
    ) -> None:
        bom = get_bom(db, material_code, due_date)
        if bom is None:
            add_exception(
                MrpExceptionType.NO_BOM,
                ExceptionSeverity.CRITICAL,
                material_code,
                shortage_qty=quantity,
                shortage_date=due_date,
                suggestion="自制物料缺少已发布 BOM，无法展开组件需求",
                requirement_ref=demand_ref,
            )
            return
        base_quantity = dec(bom.base_quantity) or Decimal("1")
        for item in bom_components(db, bom):
            child_qty = (
                quantity / base_quantity
                * dec(item.quantity)
                * (Decimal("1") + dec(item.scrap_rate) / Decimal("100"))
            )
            if child_qty <= ZERO:
                continue
            child_level = max(level + 1, low_level.get(item.material_code, level + 1))
            low_level[item.material_code] = max(low_level.get(item.material_code, 0), child_level)
            demands_by_level[child_level].append(Demand(
                material_code=item.material_code,
                quantity=child_qty.quantize(Decimal("0.01")),
                due_date=due_date,
                demand_type=demand_type,
                demand_ref=demand_ref,
                level=child_level,
                parent_planned_order=parent_ref,
            ))

    @staticmethod
    def _build_kitting_snapshot(db: Session, run_number: str, run_by: Optional[str]) -> None:
        """Create a kitting result for firm and newly planned production orders."""
        from backend.services.planning.kitting_service import KittingService

        orders = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.status.in_(FIRM_PRODUCTION_STATUSES),
                ProductionOrder.is_deleted == False,
            )
            .all()
        )
        planned = (
            db.query(PlannedOrder)
            .filter(
                PlannedOrder.run_number == run_number,
                PlannedOrder.order_type == PlannedOrderType.PRODUCTION,
                PlannedOrder.status == PlannedOrderStatus.PLANNED,
                PlannedOrder.is_deleted == False,
            )
            .all()
        )
        for order in orders:
            KittingService.analyze_production_order(db, order.order_number, persist=True, checked_by=run_by)
        for plan in planned:
            KittingService.analyze_planned_order(db, plan.planned_order_number, persist=True, checked_by=run_by)
