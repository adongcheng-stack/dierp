"""轻量 EAM 设备管理引擎（P1）。

覆盖设备台账（复用 APS 的 Resource 主数据）、周期性维护计划、维护工单与
设备故障记录，并与 APS 排程联动：

- 资源处于 MAINTENANCE / DOWN 时，APS 排程会产生 RESOURCE_DOWN 异常；
- 故障停机时长进入 OEE 可用率估算（简化口径）；
- 维护计划到期后自动生成维护工单（幂等），形成「计划 → 到期 → 工单 → 完成回写」闭环。

所有写入均为幂等或可重复执行，供升级种子脚本与冒烟测试直接调用。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common.models.planning import (
    EquipmentFailure,
    FailureSeverity,
    FailureStatus,
    MaintenanceOrder,
    MaintenancePlan,
    MaintenanceStatus,
    MaintenanceType,
    Resource,
    ResourceStatus,
    WorkCalendar,
)
from backend.common.models.pp import OperationReport, WorkCenter
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import ZERO, dec

# 默认班次时长（小时）：与 WorkCalendar.capacity_hours 缺省保持一致
DEFAULT_SHIFT_HOURS = Decimal("10")


def _as_enum_value(value) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


class EamEngine:
    """设备管理静态方法集合：到期保养生成 / 故障闭环 / OEE 快照。"""

    # ── 维护计划 → 到期维护工单 ────────────────────────────────────────
    @staticmethod
    def generate_due_orders(
        db: Session,
        *,
        as_of: Optional[datetime] = None,
        created_by: Optional[str] = None,
    ) -> list[MaintenanceOrder]:
        """扫描维护计划，为 next_due_at <= as_of 的计划生成维护工单。

        幂等规则：同一 plan 在同一 planned_date 上已有未删除工单时跳过；
        生成后回写 next_due_at = 本次到期时间 + cycle_days，避免重复触发。
        """
        as_of = as_of or datetime.now()
        created: list[MaintenanceOrder] = []
        plans = (
            db.query(MaintenancePlan)
            .filter(
                MaintenancePlan.is_deleted == False,
                MaintenancePlan.status == MaintenanceStatus.PLANNED,
                MaintenancePlan.next_due_at.isnot(None),
                MaintenancePlan.next_due_at <= as_of,
            )
            .order_by(MaintenancePlan.next_due_at)
            .all()
        )
        for plan in plans:
            planned_date = plan.next_due_at
            exists = (
                db.query(MaintenanceOrder)
                .filter(
                    MaintenanceOrder.plan_id == plan.plan_id,
                    MaintenanceOrder.planned_date == planned_date,
                    MaintenanceOrder.is_deleted == False,
                )
                .first()
            )
            if exists is not None:
                # 已有工单则只推进计划，保证重复执行幂等
                plan.next_due_at = planned_date + timedelta(days=int(plan.cycle_days or 30))
                continue
            order = MaintenanceOrder(
                order_number=NumberGenerator.generate_document_number(
                    db, MaintenanceOrder, "order_number", "MO", 4
                ),
                resource_id=plan.resource_id,
                plan_id=plan.plan_id,
                maintenance_type=plan.maintenance_type,
                planned_date=planned_date,
                downtime_hours=ZERO,
                status=MaintenanceStatus.PLANNED,
                created_by=created_by,
            )
            db.add(order)
            db.flush()
            # 回写计划：下次到期 = 本次到期 + 周期
            plan.next_due_at = planned_date + timedelta(days=int(plan.cycle_days or 30))
            created.append(order)
        db.flush()
        return created

    @staticmethod
    def complete_order(
        db: Session,
        order_number: str,
        *,
        executed_by: Optional[str] = None,
        downtime_hours=None,
        result_note: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> MaintenanceOrder:
        """完成维护工单，并回写来源维护计划的执行时间与下次到期时间。"""
        order = (
            db.query(MaintenanceOrder)
            .filter(MaintenanceOrder.order_number == order_number, MaintenanceOrder.is_deleted == False)
            .first()
        )
        if order is None:
            raise ValueError(f"维护工单不存在: {order_number}")
        if order.status == MaintenanceStatus.DONE:
            raise ValueError(f"维护工单已完成，不能重复完成: {order_number}")
        completed_at = completed_at or datetime.now()
        order.status = MaintenanceStatus.DONE
        order.completed_at = completed_at
        order.executed_by = executed_by or order.executed_by
        if downtime_hours is not None:
            order.downtime_hours = dec(downtime_hours)
        order.result_note = result_note or order.result_note

        plan = None
        if order.plan_id:
            plan = (
                db.query(MaintenancePlan)
                .filter(MaintenancePlan.plan_id == order.plan_id, MaintenancePlan.is_deleted == False)
                .first()
            )
        if plan is not None:
            plan.last_executed_at = completed_at
            plan.next_due_at = completed_at + timedelta(days=int(plan.cycle_days or 30))
        db.flush()
        return order

    # ── 故障记录 ──────────────────────────────────────────────────────
    @staticmethod
    def record_failure(
        db: Session,
        *,
        resource_id: str,
        occurred_at: Optional[datetime] = None,
        severity: str = "MEDIUM",
        description: Optional[str] = None,
        reported_by: Optional[str] = None,
        downtime_hours=None,
    ) -> EquipmentFailure:
        """上报设备故障；工作中心从资源主数据冗余，便于按中心汇总 OEE。"""
        resource = (
            db.query(Resource)
            .filter(Resource.resource_id == resource_id, Resource.is_deleted == False)
            .first()
        )
        if resource is None:
            raise ValueError(f"设备资源不存在: {resource_id}")
        failure = EquipmentFailure(
            failure_number=NumberGenerator.generate_document_number(
                db, EquipmentFailure, "failure_number", "EF", 4
            ),
            resource_id=resource_id,
            work_center_id=resource.work_center_id,
            occurred_at=occurred_at or datetime.now(),
            severity=FailureSeverity(severity),
            description=description,
            downtime_hours=dec(downtime_hours) if downtime_hours is not None else ZERO,
            status=FailureStatus.OPEN,
            reported_by=reported_by,
            created_by=reported_by,
        )
        db.add(failure)
        db.flush()
        return failure

    @staticmethod
    def resolve_failure(
        db: Session,
        failure_number: str,
        *,
        root_cause: Optional[str] = None,
        action_taken: Optional[str] = None,
        downtime_hours=None,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ) -> EquipmentFailure:
        """解决故障：写根因/处置/停机时长，状态置 CLOSED。"""
        failure = (
            db.query(EquipmentFailure)
            .filter(EquipmentFailure.failure_number == failure_number, EquipmentFailure.is_deleted == False)
            .first()
        )
        if failure is None:
            raise ValueError(f"设备故障不存在: {failure_number}")
        if failure.status == FailureStatus.CLOSED:
            raise ValueError(f"设备故障已关闭: {failure_number}")
        failure.status = FailureStatus.CLOSED
        failure.resolved_at = resolved_at or datetime.now()
        failure.root_cause = root_cause or failure.root_cause
        failure.action_taken = action_taken or failure.action_taken
        if downtime_hours is not None:
            failure.downtime_hours = dec(downtime_hours)
        if resolved_by:
            failure.updated_by = resolved_by
        db.flush()
        return failure

    # ── OEE 快照（简化口径） ─────────────────────────────────────────
    @staticmethod
    def oee_snapshot(db: Session, work_center_id: Optional[str] = None) -> dict:
        """按工作中心估算 OEE = 可用率 × 性能率 × 良品率。

        简化口径：
        - 可用率 = 1 - 故障停机时长 / 班次时长（班次取 WorkCalendar.capacity_hours）；
        - 性能率 = 报工标准工时 / 实际工时（标准工时按工艺路线工序时间 × 数量占比估算，
          无工艺路线的报工不参与性能率，避免失真）；
        - 良品率 = 报工良品数 / 报工总数。
        """
        now = datetime.now()

        centers = (
            db.query(WorkCenter).filter(WorkCenter.is_deleted == False).all()
        )
        if work_center_id:
            centers = [wc for wc in centers if wc.work_center_id == work_center_id]

        calendars = {
            row.work_center_id: row
            for row in db.query(WorkCalendar).filter(WorkCalendar.is_deleted == False).all()
        }
        resources = (
            db.query(Resource).filter(Resource.is_deleted == False).all()
        )
        resources_by_center: dict[str, list[Resource]] = {}
        for row in resources:
            resources_by_center.setdefault(row.work_center_id, []).append(row)

        # 故障停机时长（含未关闭故障的已登记停机）
        failure_rows = (
            db.query(
                EquipmentFailure.work_center_id,
                func.coalesce(func.sum(EquipmentFailure.downtime_hours), 0),
            )
            .filter(EquipmentFailure.is_deleted == False)
            .group_by(EquipmentFailure.work_center_id)
            .all()
        )
        downtime_by_center = {row[0]: dec(row[1]) for row in failure_rows}

        # 报工聚合：数量 + 实际工时（分钟）
        report_query = (
            db.query(
                OperationReport.work_center_id,
                func.count(OperationReport.id),
                func.coalesce(func.sum(OperationReport.reported_quantity), 0),
                func.coalesce(func.sum(OperationReport.good_quantity), 0),
                func.coalesce(func.sum(OperationReport.machine_time), 0),
                func.coalesce(func.sum(OperationReport.labor_time), 0),
            )
            .filter(OperationReport.is_deleted == False)
            .group_by(OperationReport.work_center_id)
        )
        if work_center_id:
            report_query = report_query.filter(OperationReport.work_center_id == work_center_id)
        report_rows = report_query.all()

        rows = []
        overall = {"availability": [], "performance": [], "quality": []}
        for wc in centers:
            center_id = wc.work_center_id
            calendar = calendars.get(center_id)
            shift_hours = (
                dec(calendar.capacity_hours) if calendar and calendar.capacity_hours else DEFAULT_SHIFT_HOURS
            )
            if shift_hours <= ZERO:
                shift_hours = DEFAULT_SHIFT_HOURS
            downtime = downtime_by_center.get(center_id, ZERO)
            availability = Decimal("1") - downtime / shift_hours
            availability = max(ZERO, min(Decimal("1"), availability))

            stats = next((r for r in report_rows if r[0] == center_id), None)
            quality = Decimal("1")
            performance = Decimal("1")
            report_count = 0
            reported_qty = ZERO
            good_qty = ZERO
            actual_minutes = ZERO
            if stats is not None:
                _, report_count, reported_qty, good_qty, machine_minutes, labor_minutes = stats
                reported_qty = dec(reported_qty)
                good_qty = dec(good_qty)
                actual_minutes = dec(machine_minutes) + dec(labor_minutes)
                if reported_qty > ZERO:
                    quality = good_qty / reported_qty
                # 性能率：标准工时 / 实际工时
                standard_minutes = EamEngine._standard_minutes(db, center_id)
                if standard_minutes > ZERO and actual_minutes > ZERO:
                    performance = standard_minutes / actual_minutes
                    performance = min(Decimal("1"), max(ZERO, performance))
            overall["availability"].append(availability)
            overall["performance"].append(performance)
            overall["quality"].append(quality)
            oee = availability * performance * quality
            # 资源健康摘要
            center_resources = resources_by_center.get(center_id, [])
            rows.append(
                {
                    "work_center_id": center_id,
                    "description": wc.description,
                    "shift_hours": float(shift_hours),
                    "downtime_hours": float(downtime),
                    "availability": round(float(availability), 4),
                    "performance": round(float(performance), 4),
                    "quality": round(float(quality), 4),
                    "oee": round(float(oee), 4),
                    "report_count": report_count,
                    "reported_qty": float(reported_qty),
                    "good_qty": float(good_qty),
                    "resource_count": len(center_resources),
                    "down_resources": [
                        r.resource_id
                        for r in center_resources
                        if _as_enum_value(r.status) != "ACTIVE"
                    ],
                }
            )

        def _avg(values):
            return round(sum(values) / len(values), 4) if values else 0.0

        summary = {
            "availability": _avg(overall["availability"]),
            "performance": _avg(overall["performance"]),
            "quality": _avg(overall["quality"]),
        }
        summary["oee"] = round(
            summary["availability"] * summary["performance"] * summary["quality"], 4
        )
        return {"generated_at": now.isoformat(), "summary": summary, "work_centers": rows}

    @staticmethod
    def _standard_minutes(db: Session, work_center_id: str) -> Decimal:
        """该工作中心全部报工对应的标准工时估算（分钟）。

        对每条报工：标准分钟 = 工艺路线工序(调机+机加+人工) × (报工数 / 工单计划数)。
        缺工艺路线 / 工序 / 工单的报工按 0 计（不参与性能率放大）。
        """
        from backend.common.models.eng import RoutingOperation
        from backend.common.models.pp import ProductionOrder

        reports = (
            db.query(OperationReport)
            .filter(
                OperationReport.work_center_id == work_center_id,
                OperationReport.is_deleted == False,
            )
            .all()
        )
        if not reports:
            return ZERO
        total = ZERO
        matched = 0
        for report in reports:
            if not report.routing_operation_id:
                continue
            op = (
                db.query(RoutingOperation)
                .filter(RoutingOperation.id == report.routing_operation_id)
                .first()
            )
            if op is None:
                continue
            order = (
                db.query(ProductionOrder)
                .filter(ProductionOrder.order_number == report.production_order_number)
                .first()
            )
            if order is None or not order.quantity:
                continue
            qty_ratio = float(report.reported_quantity or 0) / float(order.quantity)
            standard = dec(op.setup_time) + dec(op.machine_time) + dec(op.labor_time)
            total += standard * Decimal(str(min(qty_ratio, 1.0)))
            matched += 1
        return total if matched else ZERO

    # ── 概览 ──────────────────────────────────────────────────────────
    @staticmethod
    def overview(db: Session, *, as_of: Optional[datetime] = None) -> dict:
        """EAM 工作台概览统计。"""
        as_of = as_of or datetime.now()
        plans = db.query(MaintenancePlan).filter(MaintenancePlan.is_deleted == False)
        orders = db.query(MaintenanceOrder).filter(MaintenanceOrder.is_deleted == False)
        failures = db.query(EquipmentFailure).filter(EquipmentFailure.is_deleted == False)
        resources = db.query(Resource).filter(Resource.is_deleted == False)

        open_failures = failures.filter(EquipmentFailure.status == FailureStatus.OPEN)
        return {
            "plans": plans.count(),
            "due_plans": plans.filter(
                MaintenancePlan.next_due_at.isnot(None),
                MaintenancePlan.next_due_at <= as_of,
            ).count(),
            "orders": orders.count(),
            "orders_planned": orders.filter(MaintenanceOrder.status == MaintenanceStatus.PLANNED).count(),
            "orders_done": orders.filter(MaintenanceOrder.status == MaintenanceStatus.DONE).count(),
            "failures": failures.count(),
            "open_failures": open_failures.count(),
            "critical_failures": open_failures
            .filter(EquipmentFailure.severity == FailureSeverity.CRITICAL)
            .count(),
            "resources": resources.count(),
            "resources_down": resources.filter(Resource.status != ResourceStatus.ACTIVE).count(),
        }
