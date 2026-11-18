"""APS finite-capacity scheduling engine.

Turns released production orders into an operation-level schedule that respects
work-center capacity, work calendars, changeover and skill constraints. It is
deliberately a *bounded* scheduler (no industrial-grade optimizer): it performs
forward / backward / mixed scheduling at work-center granularity and writes the
result to `ScheduleRun` / `ScheduledOperation` / `ScheduleException`. Scenario
simulation (insert order / equipment down / material delay) reports the impact on
existing operations without mutating the published schedule.

Constraints modelled:
  - work-center capacity (calendar hours x utilization x number of machines)
  - operation time (setup + machine + labor, in minutes)
  - operation sequence inside an order
  - skill matrix (optional, per resource)
  - changeover minutes between consecutive operations on the same center (optional)
  - material readiness (kitting status)

Output entities match the ontology: ScheduleRun / ScheduledOperation /
ScheduleException / ScenarioSimulation / ScenarioImpact.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.common.models.eng import Routing, RoutingOperation
from backend.common.models.mm import Material
from backend.common.models.planning import (
    ChangeoverMatrix,
    Resource,
    ResourceStatus,
    ScheduleAlgorithm,
    ScheduleException,
    ScheduleExceptionType,
    ScheduleOpStatus,
    ScheduleRun,
    ScheduleRunStatus,
    ScheduledOperation,
    ScenarioImpact,
    ScenarioSimulation,
    ScenarioType,
    SkillMatrix,
    WorkCalendar,
)
from backend.common.models.pp import ProductionOrder, WorkCenter
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import ZERO, dec, get_material, get_routing, routing_operations

MIN_PER_HOUR = Decimal("60")


def _m(value) -> Decimal:
    return dec(value)


def _dt(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    return value


class WorkCenterCalendar:
    """A per-work-center time window over the horizon, derived from WorkCalendar."""

    def __init__(
        self,
        work_center: WorkCenter,
        calendar: Optional[WorkCalendar],
        start: datetime,
        end: datetime,
    ):
        self.work_center_id = work_center.work_center_id
        self.machines = int(work_center.number_of_capacities or 1)
        cal = calendar or WorkCalendar()
        self.shift_start = int((cal.shift_start or "08:00").split(":")[0])
        self.shift_end = int((cal.shift_end or "20:00").split(":")[0])
        self.break_hours = _m(cal.break_hours or 1)
        self.utilization = _m(cal.utilization or 100)
        self.workdays = set(
            int(x) for x in str(cal.workdays or "1,2,3,4,5,6").split(",") if str(x).strip().isdigit()
        )
        self.start = start
        self.end = end
        # busy intervals per machine: list[(start, end)]
        self.busy: list[list[list[tuple[datetime, datetime]]]] = [
            [] for _ in range(self.machines)
        ]
        self.hours_per_day = Decimal(max(0, self.shift_end - self.shift_start)) - self.break_hours

    def is_workday(self, day: datetime) -> bool:
        # python weekday(): Monday=0 .. Sunday=6 ; our workdays use 1..7 for Mon..Sun
        return (day.weekday() + 1) in self.workdays

    def day_open(self, day: datetime) -> datetime:
        return day.replace(hour=self.shift_start, minute=0, second=0, microsecond=0)

    def day_close(self, day: datetime) -> datetime:
        return day.replace(hour=self.shift_end, minute=0, second=0, microsecond=0)

    def effective_hours(self, minutes: Decimal) -> Decimal:
        """Real machine minutes after utilization for the requested work minutes."""
        if self.utilization <= ZERO:
            return Decimal("1e9")
        return (minutes * Decimal("100") / self.utilization)

    def find_slot(
        self,
        duration_minutes: Decimal,
        earliest: datetime,
    ) -> Optional[tuple[int, datetime, datetime]]:
        """Find the earliest slot on a machine >= earliest for the given work duration.

        Returns (machine_index, start, end). Handles shift boundaries and weekends.
        """
        need_minutes = self.effective_hours(duration_minutes)
        cursor = earliest
        for machine_index in range(self.machines):
            cursor = earliest
            while cursor < self.end:
                if not self.is_workday(cursor):
                    cursor = self.day_open(cursor + timedelta(days=1))
                    continue
                open_at = self.day_open(cursor)
                close_at = self.day_close(cursor)
                if cursor < open_at:
                    cursor = open_at
                if cursor >= close_at:
                    cursor = self.day_open(cursor + timedelta(days=1))
                    continue
                # available window on this day
                window_end = close_at
                free = self._available_intervals(machine_index, cursor, window_end)
                for (s, e) in free:
                    usable_min = (e - s).total_seconds() / 60.0
                    if Decimal(usable_min) >= need_minutes:
                        start = s
                        end = start + timedelta(minutes=float(need_minutes))
                        return (machine_index, start, end)
                # not enough contiguous time today; move to next day
                cursor = self.day_open(cursor + timedelta(days=1))
        return None

    def _available_intervals(
        self, machine_index: int, start: datetime, end: datetime
    ) -> list[tuple[datetime, datetime]]:
        busy = sorted(
            (s, e) for (s, e) in self.busy[machine_index] if e > start and s < end
        )
        free: list[tuple[datetime, datetime]] = []
        cursor = start
        for (s, e) in busy:
            if s > cursor:
                free.append((cursor, min(s, end)))
            cursor = max(cursor, e)
        if cursor < end:
            free.append((cursor, end))
        return free

    def occupy(self, machine_index: int, start: datetime, end: datetime) -> None:
        self.busy[machine_index].append((start, end))

    def load_hours(self) -> Decimal:
        total = ZERO
        for machine in self.busy:
            for (s, e) in machine:
                total += Decimal((e - s).total_seconds()) / 3600
        return total


class ApsEngine:
    """Factory-style static scheduler over the four scheduling entities."""

    @staticmethod
    def run(
        db: Session,
        *,
        run_name: Optional[str] = None,
        horizon_start: Optional[datetime] = None,
        horizon_end: Optional[datetime] = None,
        algorithm: str = "FORWARD",
        source_type: str = "PRODUCTION_ORDER",
        created_by: Optional[str] = None,
    ) -> ScheduleRun:
        now = datetime.now()
        horizon_start = horizon_start or now.replace(hour=0, minute=0, second=0, microsecond=0)
        horizon_end = horizon_end or horizon_start + timedelta(days=56)

        # clean previous run of the same scope (re-run replaces a DRAFT run)
        run = (
            db.query(ScheduleRun)
            .filter(
                ScheduleRun.source_type == source_type,
                ScheduleRun.status.in_([ScheduleRunStatus.DRAFT, ScheduleRunStatus.RUNNING]),
                ScheduleRun.is_deleted == False,
            )
            .order_by(ScheduleRun.id.desc())
            .first()
        )
        if run is None:
            run = ScheduleRun(
                run_number=NumberGenerator.generate_document_number(
                    db, ScheduleRun, "run_number", "APS", 4
                ),
                run_name=run_name or f"APS 有限产能排程",
                algorithm=algorithm,
                horizon_start=horizon_start,
                horizon_end=horizon_end,
                source_type=source_type,
                status=ScheduleRunStatus.RUNNING,
                generated_by=created_by,
                created_by=created_by,
            )
            db.add(run)
            db.flush()
        else:
            run.run_name = run_name or run.run_name
            run.algorithm = algorithm
            run.horizon_start = horizon_start
            run.horizon_end = horizon_end
            run.status = ScheduleRunStatus.RUNNING

        # drop previous operations / exceptions of this run
        db.query(ScheduledOperation).filter(
            ScheduledOperation.run_number == run.run_number
        ).delete(synchronize_session=False)
        db.query(ScheduleException).filter(
            ScheduleException.run_number == run.run_number
        ).delete(synchronize_session=False)
        db.flush()

        orders = ApsEngine._orders_for_source(db, source_type, horizon_start, horizon_end, now)

        calendars = ApsEngine._calendars(db, horizon_start, horizon_end)
        schedules: dict[str, WorkCenterCalendar] = calendars

        # 资源状态 / 技能 / 换产约束
        resource_state = ApsEngine._resource_state(db)
        changeovers = ApsEngine._changeover_map(db)

        op_count = 0
        exception_count = 0
        for order in orders:
            sequence = 0
            planned_at = order["planned_start_date"] or horizon_start
            if algorithm in ("BACKWARD", "MIXED"):
                planned_at = order["planned_finish_date"] or order["planned_start_date"] or horizon_end
            # 排程窗口钳制：历史工单不得排到窗口之前
            if planned_at < horizon_start:
                planned_at = horizon_start
            routing = get_routing(db, order["material_code"], now)
            if routing is None:
                db.add(
                    ScheduleException(
                        exception_id=ApsEngine._eid(db),
                        run_number=run.run_number,
                        exception_type=ScheduleExceptionType.CAPACITY_OVERLOAD,
                        production_order_number=order["order_number"],
                        severity="WARNING",
                        message=f"工单 {order['order_number']} 缺少已发布工艺路线，无法排程",
                        suggested_action="维护并发布工艺路线后重新排程",
                        created_by=created_by,
                    )
                )
                exception_count += 1
                continue
            ops = [op for op in routing_operations(db, routing) if op.scheduling_relevant]
            kit_status = ApsEngine._kitting_status(db, order["order_number"])
            previous_op: Optional[RoutingOperation] = None
            for op in ops:
                sequence += 1
                duration = _m(op.setup_time) + _m(op.machine_time) + _m(op.labor_time)
                if duration <= ZERO:
                    duration = Decimal("30")  # default 30 min per op for demo

                # ── 资源停机约束 ───────────────────────────────────────
                down_resources = resource_state["down"].get(op.work_center_id, [])
                if down_resources:
                    db.add(
                        ScheduleException(
                            exception_id=ApsEngine._eid(db),
                            run_number=run.run_number,
                            exception_type=ScheduleExceptionType.RESOURCE_DOWN,
                            production_order_number=order["order_number"],
                            work_center_id=op.work_center_id,
                            resource_id=down_resources[0],
                            severity="CRITICAL" if resource_state["all_down"].get(op.work_center_id) else "WARNING",
                            message=(
                                f"工作中心 {op.work_center_id} 资源 "
                                f"{', '.join(down_resources)} 处于停机/保养状态"
                            ),
                            suggested_action="确认设备恢复计划，或将工序转至备用资源/工作中心",
                            created_by=created_by,
                        )
                    )
                    exception_count += 1
                    if resource_state["all_down"].get(op.work_center_id):
                        planned_at = planned_at + timedelta(minutes=float(duration))
                        continue

                # ── 技能匹配约束 ───────────────────────────────────────
                required_skill = ApsEngine._required_skill(op)
                if required_skill and not ApsEngine._skill_match(
                    resource_state, op.work_center_id, required_skill
                ):
                    db.add(
                        ScheduleException(
                            exception_id=ApsEngine._eid(db),
                            run_number=run.run_number,
                            exception_type=ScheduleExceptionType.SKILL_MISMATCH,
                            production_order_number=order["order_number"],
                            work_center_id=op.work_center_id,
                            severity="WARNING",
                            message=(
                                f"工作中心 {op.work_center_id} 无具备 {required_skill} 能力的可用资源"
                            ),
                            suggested_action="补充技能矩阵或指派具备相应技能的作业人员",
                            created_by=created_by,
                        )
                    )
                    exception_count += 1

                # ── 换产约束（同一工作中心相邻两道工序） ─────────────────
                if previous_op is not None and previous_op.work_center_id == op.work_center_id:
                    changeover_minutes = changeovers.get(
                        (op.work_center_id, previous_op.operation_no, op.operation_no), ZERO
                    )
                    if changeover_minutes > ZERO:
                        duration = duration + changeover_minutes
                        if changeover_minutes > Decimal("30"):
                            db.add(
                                ScheduleException(
                                    exception_id=ApsEngine._eid(db),
                                    run_number=run.run_number,
                                    exception_type=ScheduleExceptionType.CHANGEOVER_LIMIT,
                                    production_order_number=order["order_number"],
                                    work_center_id=op.work_center_id,
                                    severity="WARNING",
                                    message=(
                                        f"工单 {order['order_number']} 在 {op.work_center_id} 的换产时间 "
                                        f"{changeover_minutes} 分钟超出 30 分钟阈值"
                                    ),
                                    suggested_action="评估 SMED 改善或调整工序顺序以减少换产",
                                    created_by=created_by,
                                )
                            )
                            exception_count += 1

                calendar = schedules.get(op.work_center_id)
                slot = None
                if calendar is not None:
                    earliest = planned_at
                    if algorithm in ("BACKWARD", "MIXED"):
                        earliest = ApsEngine._backward_earliest(
                            calendar, op.work_center_id, duration, planned_at
                        )
                        if earliest is None:
                            earliest = planned_at
                    slot = calendar.find_slot(duration, earliest)
                if slot is None:
                    db.add(
                        ScheduleException(
                            exception_id=ApsEngine._eid(db),
                            run_number=run.run_number,
                            exception_type=ScheduleExceptionType.CAPACITY_OVERLOAD,
                            production_order_number=order["order_number"],
                            work_center_id=op.work_center_id,
                            severity="WARNING",
                            message=f"工单 {order['order_number']} 工序 {op.operation_no} 在 {op.work_center_id} 找不到可用产能",
                            suggested_action="调整班次/利用率或增加资源后重新排程",
                            created_by=created_by,
                        )
                    )
                    exception_count += 1
                    planned_at = planned_at + timedelta(minutes=float(duration))
                    continue
                machine_index, start, end = slot
                if calendar is not None:
                    calendar.occupy(machine_index, start, end)
                if algorithm in ("BACKWARD", "MIXED"):
                    planned_at = start
                else:
                    planned_at = end
                db.add(
                    ScheduledOperation(
                        op_id=ApsEngine._eid(db),
                        run_number=run.run_number,
                        production_order_number=order["order_number"],
                        material_code=order["material_code"],
                        operation_no=op.operation_no,
                        operation_name=op.operation_name,
                        work_center_id=op.work_center_id,
                        sequence=sequence,
                        planned_qty=dec(order["quantity"]),
                        setup_minutes=dec(op.setup_time),
                        run_minutes=dec(op.machine_time) + dec(op.labor_time),
                        planned_start=start,
                        planned_end=end,
                        status=ScheduleOpStatus.PLANNED,
                        created_by=created_by,
                    )
                )
                op_count += 1
                previous_op = op
            # order-level due date risk / material shortage
            db.flush()  # autoflush=False: ensure just-added ops are visible to the due-date query
            if ApsEngine._finish_exceeds_due(db, run.run_number, order["order_number"], order["planned_finish_date"]):
                db.add(
                    ScheduleException(
                        exception_id=ApsEngine._eid(db),
                        run_number=run.run_number,
                        exception_type=ScheduleExceptionType.DUE_DATE_RISK,
                        production_order_number=order["order_number"],
                        severity="WARNING",
                        message=f"工单 {order['order_number']} 排程可能无法满足交期",
                        suggested_action="评估提前开始 / 加班 / 委外",
                        created_by=created_by,
                    )
                )
                exception_count += 1
            if kit_status in ("SHORT", "PARTIAL"):
                critical = kit_status == "SHORT"
                db.add(
                    ScheduleException(
                        exception_id=ApsEngine._eid(db),
                        run_number=run.run_number,
                        exception_type=ScheduleExceptionType.MATERIAL_SHORTAGE,
                        production_order_number=order["order_number"],
                        severity="CRITICAL" if critical else "WARNING",
                        message=(
                            f"工单 {order['order_number']} "
                            + ("物料缺料，不宜下达排程" if critical else "物料部分缺料，排程存在风险")
                        ),
                        suggested_action="补料齐套后再排程" if critical else "确认缺料补货计划，必要时调整排程顺序",
                        created_by=created_by,
                    )
                )
                exception_count += 1

        run.operation_count = op_count
        run.exception_count = exception_count
        run.status = ScheduleRunStatus.COMPLETED
        run.finished_at = datetime.now()
        db.flush()
        return run

    @staticmethod
    def _calendars(
        db: Session, start: datetime, end: datetime
    ) -> dict[str, WorkCenterCalendar]:
        result: dict[str, WorkCenterCalendar] = {}
        work_centers = (
            db.query(WorkCenter).filter(WorkCenter.is_deleted == False).all()
        )
        cal_rows = {
            row.work_center_id: row
            for row in db.query(WorkCalendar).filter(WorkCalendar.is_deleted == False).all()
        }
        for wc in work_centers:
            result[wc.work_center_id] = WorkCenterCalendar(
                wc, cal_rows.get(wc.work_center_id), start, end
            )
        return result

    @staticmethod
    def _required_skill(op: RoutingOperation) -> Optional[str]:
        """Derive the capability required by an operation from its operation code.

        `DRL-001` -> `DRL`, which is matched against the resource skill tags
        (`DRILLING`, `ETCHING`, ...).  Returns None when no skill can be inferred.
        """
        code = str(op.operation_code or "").strip().upper()
        if not code:
            return None
        prefix = code.split("-")[0][:3]
        return prefix or None

    @staticmethod
    def _resource_state(db: Session) -> dict:
        """Load resource availability / skill coverage per work center."""
        resources = (
            db.query(Resource)
            .filter(Resource.is_deleted == False)
            .order_by(Resource.work_center_id, Resource.resource_id)
            .all()
        )
        down: dict[str, list[str]] = {}
        active_by_center: dict[str, list[Resource]] = {}
        machine_by_center: dict[str, list[Resource]] = {}
        for row in resources:
            center = row.work_center_id
            if row.status != ResourceStatus.ACTIVE:
                down.setdefault(center, []).append(row.resource_id)
                continue
            active_by_center.setdefault(center, []).append(row)
            if str(row.resource_type or "MACHINE").upper() == "MACHINE":
                machine_by_center.setdefault(center, []).append(row)

        all_down: dict[str, bool] = {}
        for center in set(list(down.keys()) + list(machine_by_center.keys())):
            machines = machine_by_center.get(center, [])
            all_down[center] = bool(machines) and not machines

        # skill coverage: a center is "skill ok" when at least one active resource
        # carries a capability tag (or when the center has no resource master data).
        skills_by_resource: dict[str, set[str]] = {}
        for row in resources:
            tags = {
                tag.strip().upper()
                for tag in str(row.skill_tags or "").split(",")
                if tag.strip()
            }
            skills_by_resource[row.resource_id] = tags

        skill_ok: dict[str, bool] = {}
        for center in active_by_center:
            skill_ok[center] = True
        return {
            "down": down,
            "all_down": all_down,
            "active": active_by_center,
            "skills": skills_by_resource,
            "skill_ok": skill_ok,
        }

    @staticmethod
    def _skill_match(state: dict, work_center_id: str, required: Optional[str]) -> bool:
        """True when some active resource of the center covers the required skill."""
        if not required:
            return True
        rows = state["active"].get(work_center_id, [])
        if not rows:
            # no resource master data -> cannot verify, do not raise a mismatch
            return True
        for row in rows:
            for tag in state["skills"].get(row.resource_id, set()):
                if tag == required or tag.startswith(required) or required.startswith(tag):
                    return True
        return False

    @staticmethod
    def _changeover_map(db: Session) -> dict:
        """(work_center_id, from_operation_no, to_operation_no) -> minutes."""
        rows = (
            db.query(ChangeoverMatrix)
            .filter(ChangeoverMatrix.is_deleted == False)
            .all()
        )
        result: dict[tuple[str, str, str], Decimal] = {}
        for row in rows:
            key = (row.work_center_id, str(row.from_operation or ""), str(row.to_operation or ""))
            result[key] = _m(row.changeover_minutes)
        return result

    @staticmethod
    def _orders_for_source(
        db: Session,
        source_type: str,
        horizon_start: datetime,
        horizon_end: datetime,
        now: datetime,
    ) -> list[dict]:
        """Return a uniform list of scheduling jobs.

        Each entry: {
          order_number, material_code, quantity,
          planned_start_date, planned_finish_date
        }
        Supports PRODUCTION_ORDER and PLANNED_ORDER (PRODUCTION) sources.
        """
        if source_type == "PLANNED_ORDER":
            from backend.common.models.planning import PlannedOrder, PlannedOrderType

            rows = (
                db.query(PlannedOrder)
                .filter(
                    PlannedOrder.is_deleted == False,
                    PlannedOrder.order_type == PlannedOrderType.PRODUCTION,
                    PlannedOrder.status.in_(["PLANNED", "FIRMED", "RELEASED"]),
                )
                .order_by(PlannedOrder.due_date, PlannedOrder.planned_order_number)
                .all()
            )
            return [
                {
                    "order_number": row.planned_order_number,
                    "material_code": row.material_code,
                    "quantity": dec(row.quantity),
                    "planned_start_date": row.start_date or row.due_date or horizon_start,
                    "planned_finish_date": row.due_date or horizon_end,
                }
                for row in rows
            ]

        rows = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.is_deleted == False,
                ProductionOrder.status.in_(["RELEASED", "IN_PRODUCTION"]),
            )
            .order_by(ProductionOrder.planned_start_date, ProductionOrder.order_number)
            .all()
        )
        return [
            {
                "order_number": row.order_number,
                "material_code": row.material_code,
                "quantity": dec(row.quantity),
                "planned_start_date": row.planned_start_date or horizon_start,
                "planned_finish_date": row.planned_finish_date or horizon_end,
            }
            for row in rows
        ]

    @staticmethod
    def _backward_earliest(
        calendar: WorkCenterCalendar,
        work_center_id: str,
        duration: Decimal,
        due: datetime,
    ) -> Optional[datetime]:
        """For backward scheduling, return a plausible start (due - duration) clipped to horizon."""
        need_minutes = calendar.effective_hours(duration)
        candidate = due - timedelta(minutes=float(need_minutes))
        return max(candidate, calendar.start)

    @staticmethod
    def _eid(db: Session) -> str:
        return f"OP-{datetime.now():%Y%m%d%H%M%S}-{str(uuid.uuid4())[:6]}"

    @staticmethod
    def _kitting_status(db: Session, order_number: str) -> Optional[str]:
        from backend.common.models.planning import KittingResult

        row = (
            db.query(KittingResult)
            .filter(
                KittingResult.source_type == "PRODUCTION_ORDER",
                KittingResult.source_ref == order_number,
                KittingResult.is_deleted == False,
            )
            .order_by(KittingResult.id.desc())
            .first()
        )
        return row.kit_status.value if row and row.kit_status else None

    @staticmethod
    def _finish_exceeds_due(
        db: Session, run_number: str, order_number: str, due: Optional[datetime]
    ) -> bool:
        last = (
            db.query(ScheduledOperation)
            .filter(
                ScheduledOperation.run_number == run_number,
                ScheduledOperation.production_order_number == order_number,
            )
            .order_by(ScheduledOperation.planned_end.desc())
            .first()
        )
        if last is None or due is None:
            return False
        return last.planned_end and last.planned_end > due

    @staticmethod
    def publish(db: Session, run_number: str, published_by: Optional[str] = None) -> ScheduleRun:
        run = ApsEngine._get_run(db, run_number)
        db.query(ScheduledOperation).filter(
            ScheduledOperation.run_number == run.run_number
        ).update({"status": ScheduleOpStatus.PUBLISHED}, synchronize_session=False)
        run.status = ScheduleRunStatus.PUBLISHED
        run.published_at = datetime.now()
        run.updated_by = published_by
        db.flush()
        return run

    @staticmethod
    def _get_run(db: Session, run_number: str) -> ScheduleRun:
        run = (
            db.query(ScheduleRun)
            .filter(ScheduleRun.run_number == run_number, ScheduleRun.is_deleted == False)
            .first()
        )
        if run is None:
            raise ValueError(f"排程批次不存在: {run_number}")
        return run

    # ── Scenario simulation ─────────────────────────────────────────────
    @staticmethod
    def simulate(
        db: Session,
        *,
        run_number: str,
        scenario_type: str,
        description: Optional[str] = None,
        reference_ref: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> ScenarioSimulation:
        run = ApsEngine._get_run(db, run_number)
        scenario = ScenarioSimulation(
            scenario_id=ApsEngine._eid(db),
            run_number=run_number,
            scenario_type=scenario_type,
            description=description or "插单/扰动模拟",
            reference_ref=reference_ref,
            created_by=created_by,
            status="DRAFT",
        )
        db.add(scenario)
        db.flush()

        operations = (
            db.query(ScheduledOperation)
            .filter(ScheduledOperation.run_number == run_number)
            .order_by(ScheduledOperation.planned_start)
            .all()
        )
        impacts: list[ScenarioImpact] = []
        # estimate delay: for INSERT_ORDER, all ops after the reference shift back
        # by a fixed insertion burden; for EQUIPMENT_DOWN, ops on that center shift
        if scenario_type == ScenarioType.INSERT_ORDER.value:
            burden_days = Decimal("2")
            for op in operations:
                if reference_ref and op.production_order_number == reference_ref:
                    continue
                impact = ScenarioImpact(
                    impact_id=ApsEngine._eid(db),
                    scenario_id=scenario.scenario_id,
                    production_order_number=op.production_order_number,
                    material_code=op.material_code,
                    affected_days=burden_days,
                    original_due_date=op.planned_end,
                    new_due_date=op.planned_end + timedelta(days=float(burden_days)),
                    delay_days=burden_days,
                    impact_level="MEDIUM",
                    created_by=created_by,
                )
                db.add(impact)
                impacts.append(impact)
        elif scenario_type == ScenarioType.EQUIPMENT_DOWN.value:
            affected = 0
            for op in operations:
                if op.work_center_id == reference_ref:
                    impact = ScenarioImpact(
                        impact_id=ApsEngine._eid(db),
                        scenario_id=scenario.scenario_id,
                        production_order_number=op.production_order_number,
                        material_code=op.material_code,
                        affected_days=Decimal("1"),
                        original_due_date=op.planned_end,
                        new_due_date=op.planned_end + timedelta(days=1),
                        delay_days=Decimal("1"),
                        impact_level="HIGH",
                        created_by=created_by,
                    )
                    db.add(impact)
                    impacts.append(impact)
                    affected += 1
            scenario.impact_summary = f"设备 {reference_ref} 停机影响 {affected} 道工序"
        elif scenario_type == ScenarioType.MATERIAL_DELAY.value:
            for op in operations:
                impact = ScenarioImpact(
                    impact_id=ApsEngine._eid(db),
                    scenario_id=scenario.scenario_id,
                    production_order_number=op.production_order_number,
                    material_code=op.material_code,
                    affected_days=Decimal("1.5"),
                    original_due_date=op.planned_end,
                    new_due_date=op.planned_end + timedelta(days=1, hours=12),
                    delay_days=Decimal("1.5"),
                    impact_level="MEDIUM",
                    created_by=created_by,
                )
                db.add(impact)
                impacts.append(impact)

        scenario.impact_summary = (
            scenario.impact_summary
            or f"{len(impacts)} 道工序受影响，平均延期 "
            f"{sum(i.delay_days for i in impacts) / max(1, len(impacts)):.1f} 天"
        )
        scenario.status = "COMPLETED"
        db.flush()
        return scenario