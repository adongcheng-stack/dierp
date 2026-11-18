"""经营看板引擎：六域 KPI 汇总（销售/生产/质量/设备/成本/交期）。

与追溯引擎同为只读派生查询：所有 KPI 由既有单据实时推导，
不落库、不新增实体。口径与 mock/handlers.ts 的 /dashboard/management 同构。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.common.models.pp import OperationReport, ProductionOrder
from backend.common.models.sd import SalesOrder
from backend.common.models.planning import (
    CostSettlement,
    CostVariance,
    EquipmentFailure,
    InspectionOrder,
    MaintenancePlan,
    NonConformanceReport,
)
from backend.services.planning.eam_engine import EamEngine

# 视为「未完结」的销售/生产状态（其余视为已交货/已关闭）
SALES_OPEN_VALUES = {"PENDING_APPROVAL", "APPROVED", "IN_PRODUCTION", "PARTIALLY_SHIPPED"}
PRODUCTION_OPEN_VALUES = {"PLANNED", "RELEASED", "IN_PRODUCTION"}
NCR_OPEN_VALUES = {"OPEN", "UNDER_REVIEW"}


def _f(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _v(value: Any) -> str:
    return value.value if value is not None else ""


class ManagementDashboard:
    """经营看板：一次调用返回六域 KPI。"""

    @staticmethod
    def overview(db: Session) -> Dict[str, Any]:
        today = datetime.now().date()

        # ── 1) 销售 ────────────────────────────────────────────────────
        sales_orders = (
            db.query(SalesOrder).filter(SalesOrder.is_deleted == False).all()  # noqa: E712
        )
        sales_open = [s for s in sales_orders if _v(s.status) in SALES_OPEN_VALUES]
        sales = {
            "orders": len(sales_orders),
            "open_orders": len(sales_open),
            "amount_total": round(sum(_f(s.total_amount) for s in sales_orders), 2),
            "amount_open": round(sum(_f(s.total_amount) for s in sales_open), 2),
        }

        # ── 2) 生产 ────────────────────────────────────────────────────
        production_orders = (
            db.query(ProductionOrder).filter(ProductionOrder.is_deleted == False).all()  # noqa: E712
        )
        by_status: Dict[str, int] = {}
        for order in production_orders:
            by_status[_v(order.status)] = by_status.get(_v(order.status), 0) + 1
        production_open = [o for o in production_orders if _v(o.status) in PRODUCTION_OPEN_VALUES]
        production_delayed = [
            o
            for o in production_open
            if o.planned_finish_date is not None and o.planned_finish_date.date() < today
        ]
        finished = [o for o in production_orders if _v(o.status) in {"COMPLETED", "CLOSED"}]
        production = {
            "orders": len(production_orders),
            "open_orders": len(production_open),
            "by_status": by_status,
            "completion_rate": round(len(finished) / len(production_orders), 4) if production_orders else 0.0,
            "delayed_orders": len(production_delayed),
        }

        # ── 3) 质量 ────────────────────────────────────────────────────
        inspections = (
            db.query(InspectionOrder).filter(InspectionOrder.is_deleted == False).all()  # noqa: E712
        )
        completed = [i for i in inspections if i.result is not None]
        inspected_qty = sum(_f(i.quantity_inspected) for i in completed)
        rejected_qty = sum(_f(i.quantity_rejected) for i in completed)
        first_pass_rate = round(1 - rejected_qty / inspected_qty, 4) if inspected_qty > 0 else 1.0
        ncrs = (
            db.query(NonConformanceReport).filter(NonConformanceReport.is_deleted == False).all()  # noqa: E712
        )
        quality = {
            "inspections": len(inspections),
            "fail_inspections": sum(1 for i in completed if _v(i.result) == "FAIL"),
            "first_pass_rate": first_pass_rate,
            "ncrs": len(ncrs),
            "ncrs_open": sum(1 for n in ncrs if _v(n.status) in NCR_OPEN_VALUES),
            "ncrs_equipment": sum(1 for n in ncrs if n.equipment_cause),
        }

        # ── 4) 设备（复用 EamEngine.oee_snapshot 口径） ─────────────────
        oee = EamEngine.oee_snapshot(db)
        failures = (
            db.query(EquipmentFailure).filter(EquipmentFailure.is_deleted == False).all()  # noqa: E712
        )
        equipment = {
            "oee": _f(oee["summary"]["oee"]),
            "availability": _f(oee["summary"]["availability"]),
            "performance": _f(oee["summary"]["performance"]),
            "quality": _f(oee["summary"]["quality"]),
            "open_failures": sum(1 for f in failures if _v(f.status) == "OPEN"),
            "downtime_hours": round(sum(_f(f.downtime_hours) for f in failures), 2),
            "work_centers": [
                {
                    "work_center_id": wc["work_center_id"],
                    "oee": _f(wc["oee"]),
                    "downtime_hours": _f(wc["downtime_hours"]),
                }
                for wc in oee["work_centers"]
            ],
        }

        # ── 5) 成本 ────────────────────────────────────────────────────
        variances = (
            db.query(CostVariance).filter(CostVariance.is_deleted == False).all()  # noqa: E712
        )
        variance_by_type: Dict[str, float] = {}
        for variance in variances:
            key = _v(variance.variance_type) or "UNKNOWN"
            variance_by_type[key] = round(variance_by_type.get(key, 0.0) + _f(variance.variance_amount), 2)
        settlements = (
            db.query(CostSettlement).filter(CostSettlement.is_deleted == False).count()  # noqa: E712
        )
        cost = {
            "variance_total": round(sum(_f(v.variance_amount) for v in variances), 2),
            "variance_by_type": variance_by_type,
            "settlements": settlements,
        }

        # ── 6) 交期 ────────────────────────────────────────────────────
        sales_delayed = [
            s
            for s in sales_open
            if s.delivery_date is not None and s.delivery_date.date() < today
        ]
        due_plans = (
            db.query(MaintenancePlan)
            .filter(
                MaintenancePlan.is_deleted == False,  # noqa: E712
                MaintenancePlan.next_due_at.isnot(None),
            )
            .all()
        )
        due_maintenance = sum(1 for p in due_plans if p.next_due_at.date() <= today)
        delivery = {
            "delayed_sales_orders": len(sales_delayed),
            "delayed_production_orders": len(production_delayed),
            "due_maintenance_plans": due_maintenance,
        }

        return {
            "sales": sales,
            "production": production,
            "quality": quality,
            "equipment": equipment,
            "cost": cost,
            "delivery": delivery,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def insights(data: Dict[str, Any]) -> List[str]:
        """基于 KPI 的自动点评（演示话术），纯规则推导。"""
        out: List[str] = []
        equipment = data.get("equipment", {})
        if equipment.get("oee", 1.0) < 0.7:
            worst = min(
                equipment.get("work_centers", []),
                key=lambda wc: wc.get("oee", 1.0),
                default=None,
            )
            if worst:
                out.append(
                    f"设备综合 OEE {equipment['oee']:.0%} 低于 70%，{worst['work_center_id']} 仅 "
                    f"{worst['oee']:.0%}（停机 {worst['downtime_hours']}h），建议优先排维"
                )
        quality = data.get("quality", {})
        if quality.get("ncrs_open", 0) > 0:
            out.append(f"未关闭不合格品 {quality['ncrs_open']} 张，其中设备原因 {quality['ncrs_equipment']} 张待追溯")
        production = data.get("production", {})
        if production.get("delayed_orders", 0) > 0:
            out.append(f"{production['delayed_orders']} 张在制工单已过计划完工日，需要重排或插单评估")
        delivery = data.get("delivery", {})
        if delivery.get("delayed_sales_orders", 0) > 0:
            out.append(f"{delivery['delayed_sales_orders']} 张销售订单已过承诺交期，交付风险需跟进")
        cost = data.get("cost", {})
        if cost.get("variance_total", 0) != 0:
            out.append(f"成本差异合计 {cost['variance_total']:,.2f} 元，{max(cost.get('variance_by_type', {}), key=lambda k: abs(cost['variance_by_type'][k]), default='-')} 贡献最大")
        if not out:
            out.append("各项经营指标均在正常区间")
        return out
