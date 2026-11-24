"""意图 2：订单延期风险（设计 §7.2 #2、§7.2.1 #2）。"""
from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import Field
from sqlalchemy.orm import Session

from backend.common.models.pp import ProductionOrder
from backend.common.models.sd import SalesOrder, SalesOrderStatus
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "order_delay_risk"

ALLOWED_ROLES = frozenset({"SALES", "SALES_MANAGER", "PLANNER", "GENERAL_MANAGER", "ADMIN"})

ALL_COLUMNS = [
    "order_number", "customer_id", "material_code", "quantity",
    "delivery_date", "order_status", "risk_reason",
]

_RISK_STATUSES = (SalesOrderStatus.APPROVED, SalesOrderStatus.IN_PRODUCTION)
_ROW_CAP = 200


class OrderDelayRiskParams(BoundIntent):
    within_days: int = Field(default=7, ge=1, le=90)
    customer_id: str | None = None


def _value(enum_value: object) -> str:
    return enum_value.value if hasattr(enum_value, "value") else str(enum_value)


def run(db: Session, p: OrderDelayRiskParams, role: str) -> QueryResult:
    now = datetime.now()
    deadline = now + timedelta(days=p.within_days)
    query = db.query(SalesOrder).filter(
        # SHIPPED 已发货，不属于延期风险
        SalesOrder.status.in_(list(_RISK_STATUSES)),
        SalesOrder.delivery_date <= deadline,
        SalesOrder.delivery_date >= now,
    )
    if p.customer_id:
        query = query.filter(SalesOrder.customer_id == p.customer_id)
    orders = query.order_by(SalesOrder.delivery_date.asc()).limit(_ROW_CAP).all()

    numbers = [o.order_number for o in orders]
    unfinished: dict[str, list[ProductionOrder]] = {}
    if numbers:
        for po in (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.sales_order_number.in_(numbers),
                ProductionOrder.actual_finish_date.is_(None),
            )
            .all()
        ):
            unfinished.setdefault(po.sales_order_number, []).append(po)

    data = []
    sources = []
    for order in orders:
        pos = unfinished.get(order.order_number, [])
        if not pos:
            reason = "无生产订单"
        elif any(
            po.planned_finish_date is None or po.planned_finish_date > order.delivery_date
            for po in pos
        ):
            reason = "计划完工晚于交付日"
        else:
            continue
        data.append({
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "material_code": order.material_code,
            "quantity": float(order.quantity or 0),
            "delivery_date": order.delivery_date.isoformat(),
            "order_status": _value(order.status),
            "risk_reason": reason,
        })
        sources.append(Provenance(
            table="sales_orders", record_key=order.order_number,
            ontology_iri=NS + "SalesOrder",
        ))
    return QueryResult(columns=list(ALL_COLUMNS), rows=data, sources=sources)


SPEC = IntentSpec(
    code=CODE,
    label="订单延期风险",
    description="列出交付窗口内未完工、且计划完工晚于交付日或无生产订单的销售订单。",
    entities=["SalesOrder", "ProductionOrder"],
    primary_entity="SalesOrder",
    params_model=OrderDelayRiskParams,
    defaults={"within_days": 7},
    domains=["sd", "pp"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={"*": list(ALL_COLUMNS)},
    output_enums={"order_status": "SalesOrderStatus"},
    record_key=["order_number"],
    downlink="/sd/sales-orders",
    shacl_coverage="none",
    provenance_kind="document",
    formula="sales_orders.status IN (APPROVED, IN_PRODUCTION)；delivery_date ∈ [now, now+within_days]；"
            "风险 = 无未完工生产订单，或存在 planned_finish_date 为空/晚于交付日的生产订单；不含金额列",
    handler=run,
)
