"""Shared planning utilities: dates, lot sizing, BOM/routing access."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Iterable, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.common.models.eng import BOM, BOMItem, BOMStatus, Routing, RoutingOperation, RoutingStatus
from backend.common.models.mm import Material
from backend.common.models.planning import LotSizingRule, PlanningPolicy


ZERO = Decimal("0")
ONE = Decimal("1")


def dec(value, default: Decimal = ZERO) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def as_str(value) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def day_start(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def day_end(value: datetime) -> datetime:
    return value.replace(hour=23, minute=59, second=59, microsecond=999999)


def add_days(value: datetime, days: int) -> datetime:
    return value + timedelta(days=days)


def week_start(value: datetime) -> datetime:
    value = day_start(value)
    return value - timedelta(days=value.weekday())


def iter_week_buckets(start: datetime, end: datetime) -> list[datetime]:
    cursor = week_start(start)
    last = day_start(end)
    buckets: list[datetime] = []
    while cursor <= last:
        buckets.append(cursor)
        cursor += timedelta(days=7)
    return buckets


def lot_size(policy: Optional[PlanningPolicy], net_qty: Decimal) -> Decimal:
    """Apply lot-sizing rule, MOQ, order multiple and max lot size."""
    if net_qty <= ZERO:
        return ZERO
    qty = net_qty
    rule = as_str(getattr(policy, "lot_sizing_rule", None)) or LotSizingRule.LOT_FOR_LOT.value

    if rule == LotSizingRule.FIXED_LOT.value:
        fixed = dec(getattr(policy, "fixed_lot_size", 0))
        if fixed > ZERO:
            qty = max(fixed, net_qty)
    elif rule == LotSizingRule.MIN_MAX.value:
        minimum = dec(getattr(policy, "min_order_qty", 0))
        if minimum > ZERO:
            qty = max(qty, minimum)
    elif rule == LotSizingRule.EOQ.value:
        eoq = dec(getattr(policy, "eoq", 0))
        if eoq > ZERO:
            qty = max(eoq, net_qty)

    moq = dec(getattr(policy, "min_order_qty", 0))
    if moq > ZERO:
        qty = max(qty, moq)

    multiple = dec(getattr(policy, "order_multiple", 1), ONE)
    if multiple > ZERO:
        qty = (qty / multiple).to_integral_value(rounding=ROUND_CEILING) * multiple

    maximum = dec(getattr(policy, "max_order_qty", 0))
    if maximum > ZERO and qty > maximum:
        # Split into multiple planned orders at the service layer; here cap one lot.
        qty = maximum
    return qty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def lead_time_days(policy: Optional[PlanningPolicy], material: Optional[Material] = None) -> int:
    if policy is not None and getattr(policy, "lead_time_days", None) is not None:
        return int(policy.lead_time_days)
    if material is not None and material.lead_time_days is not None:
        return int(material.lead_time_days)
    return 0


def safety_time_days(policy: Optional[PlanningPolicy]) -> int:
    if policy is not None and getattr(policy, "safety_time_days", None) is not None:
        return int(policy.safety_time_days)
    return 0


def material_unit(material: Optional[Material]) -> str:
    if material is None:
        return "PCS"
    return material.production_unit or material.base_unit or material.unit or "PCS"


def get_material(db: Session, material_code: str) -> Optional[Material]:
    return db.query(Material).filter(Material.material_code == material_code).first()


def get_policy(db: Session, material_code: str) -> Optional[PlanningPolicy]:
    return (
        db.query(PlanningPolicy)
        .filter(PlanningPolicy.material_code == material_code, PlanningPolicy.is_active == True)
        .first()
    )


def procurement_type(policy: Optional[PlanningPolicy], material: Optional[Material]) -> str:
    raw = as_str(getattr(policy, "procurement_type", None))
    if raw:
        return raw
    if material is not None:
        raw = as_str(getattr(material, "procurement_type", None))
        if raw:
            return raw
        if as_str(getattr(material, "material_type", None)) in ("RAW", "PACKAGING"):
            return "BUY"
    return "MAKE"


def get_bom(db: Session, material_code: str, on_date: datetime) -> Optional[BOM]:
    """Return the released BOM effective on the given date."""
    query = db.query(BOM).filter(
        BOM.parent_material_code == material_code,
        BOM.status == BOMStatus.RELEASED,
        BOM.is_deleted == False,
        BOM.effective_date <= on_date,
    ).filter(or_(BOM.expiry_date == None, BOM.expiry_date >= on_date))
    # Prefer the newest effective version.
    return query.order_by(BOM.effective_date.desc(), BOM.id.desc()).first()


def bom_components(db: Session, bom: BOM) -> list[BOMItem]:
    return (
        db.query(BOMItem)
        .filter(BOMItem.bom_number == bom.bom_number, BOMItem.is_deleted == False)
        .order_by(BOMItem.line_number)
        .all()
    )


def get_routing(db: Session, material_code: str, on_date: datetime) -> Optional[Routing]:
    query = db.query(Routing).filter(
        Routing.material_code == material_code,
        Routing.status == RoutingStatus.RELEASED,
        Routing.is_deleted == False,
        Routing.effective_date <= on_date,
    ).filter(or_(Routing.expiry_date == None, Routing.expiry_date >= on_date))
    return query.order_by(Routing.effective_date.desc(), Routing.id.desc()).first()


def routing_operations(db: Session, routing: Routing) -> list[RoutingOperation]:
    return (
        db.query(RoutingOperation)
        .filter(RoutingOperation.routing_id == routing.routing_id, RoutingOperation.is_deleted == False)
        .order_by(RoutingOperation.operation_no)
        .all()
    )


def low_level_codes(db: Session, root_materials: Iterable[str]) -> dict[str, int]:
    """Compute low-level codes from released BOMs using a bounded DFS.

    Level 0 = finished goods / independent demand. A component that appears at
    multiple levels gets the deepest level so it is netted only after every
    parent requirement has been generated.
    """
    codes: dict[str, int] = {}

    def walk(material_code: str, level: int, path: set[str]) -> None:
        if level > 20 or material_code in path:
            return
        codes[material_code] = max(codes.get(material_code, 0), level)
        bom = get_bom(db, material_code, datetime.now())
        if not bom:
            return
        for item in bom_components(db, bom):
            walk(item.material_code, level + 1, path | {material_code})

    for root in root_materials:
        walk(root, 0, set())
    return codes


def production_capacity_minutes(db: Session, material_code: str, quantity: Decimal) -> Decimal:
    """Rough routing load in minutes, used for lead-time and exception hints."""
    routing = get_routing(db, material_code, datetime.now())
    if not routing:
        return ZERO
    total = ZERO
    for op in routing_operations(db, routing):
        total += dec(op.setup_time) + dec(op.machine_time) + dec(op.labor_time) + dec(op.queue_time)
    return total
