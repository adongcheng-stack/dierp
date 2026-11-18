"""演示数据一键清理与重建。

用途：演示前把「运行时产生的」数据清空，并重建一套可直接展示的演示数据，
避免多轮演练后排程批次/异常/故障记录堆积、口径漂移。

设计原则：
- **不动核心主数据**：客户、报价、销售订单、BOM、工艺路线、生产订单、
  物料、成本费率等 MVP 基础数据保持原样。
- **清空运行时数据**：排程批次/工序/异常、插单场景/影响明细、
  维护工单/故障记录、维护计划（计划本身由种子重建）、检验单/不合格品记录、QMS 带报废报工单。
- **重建演示数据**：调用 upgrade_planning 的幂等种子 + APS 引擎，
  生成一个已发布排程批次与一个插单模拟场景。

可重复执行：每次执行都会得到同一套种子数据（编号会变化，内容一致）。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from backend.common.models.planning import (
    EquipmentFailure,
    InspectionOrder,
    MaintenanceOrder,
    MaintenancePlan,
    NonConformanceReport,
    Resource,
    ResourceStatus,
    ScenarioImpact,
    ScenarioSimulation,
    ScheduleException,
    ScheduledOperation,
    ScheduleRun,
)
from backend.common.models.pp import OperationReport
from backend.services.planning.aps_engine import ApsEngine


def _clear(db: Session) -> dict[str, int]:
    """按外键依赖顺序清空运行时数据。"""
    cleared: dict[str, int] = {}
    # 子表在前，父表在后
    models = [
        ("scenario_impacts", ScenarioImpact),
        ("scenarios", ScenarioSimulation),
        ("schedule_exceptions", ScheduleException),
        ("scheduled_operations", ScheduledOperation),
        ("schedule_runs", ScheduleRun),
        ("maintenance_orders", MaintenanceOrder),
        ("equipment_failures", EquipmentFailure),
        ("maintenance_plans", MaintenancePlan),
        ("non_conformance_reports", NonConformanceReport),
        ("inspection_orders", InspectionOrder),
    ]
    for key, model in models:
        cleared[key] = db.query(model).delete(synchronize_session=False)
    # 清掉 QMS 演示专用的带报废报工单（不影响基础演示报工）
    qms_report = (
        db.query(OperationReport)
        .filter(OperationReport.report_number == "OR-QMS-2026-REPORT-0001")
        .first()
    )
    if qms_report is not None:
        db.delete(qms_report)
        cleared["operation_reports"] = 1
    db.flush()
    return cleared


def _reset_resources(db: Session) -> int:
    """资源状态复位：默认 ACTIVE，DRILL-B 置 MAINTENANCE 以演示 RESOURCE_DOWN。"""
    changed = 0
    for resource in db.query(Resource).all():
        target = (
            ResourceStatus.MAINTENANCE
            if resource.resource_id == "RES-DRILL-B-01"
            else ResourceStatus.ACTIVE
        )
        if resource.status != target:
            resource.status = target
            changed += 1
    db.flush()
    return changed


def _rebuild_master_seed(db: Session) -> None:
    """确保 APS/EAM/QMS 依赖的主数据存在（幂等）。"""
    # 延迟导入，避免脚本模块在 API 启动时被提前加载
    from backend.upgrade_planning import (
        seed_aps_master_data,
        seed_eam_demo_data,
        seed_operation_report_routing,
        seed_qms_demo_data,
    )

    seed_aps_master_data(db)
    seed_eam_demo_data(db)
    seed_operation_report_routing(db)
    seed_qms_demo_data(db)


def _build_demo_run(
    db: Session,
    *,
    created_by: str,
    with_scenario: bool,
) -> dict:
    """生成一个已发布的排程批次（可选再生成一个插单模拟场景）。"""
    now = datetime.now()
    horizon_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    run = ApsEngine.run(
        db,
        run_name="演示 APS · 一键重置",
        horizon_start=horizon_start,
        horizon_end=horizon_start + timedelta(days=28),
        algorithm="FORWARD",
        source_type="PRODUCTION_ORDER",
        created_by=created_by,
    )
    ApsEngine.publish(db, run.run_number, published_by=created_by)

    operation_count = (
        db.query(ScheduledOperation)
        .filter(ScheduledOperation.run_number == run.run_number)
        .count()
    )
    exception_count = (
        db.query(ScheduleException)
        .filter(ScheduleException.run_number == run.run_number)
        .count()
    )
    scenario_id: Optional[str] = None
    if with_scenario:
        scenario = ApsEngine.simulate(
            db,
            run_number=run.run_number,
            scenario_type="INSERT_ORDER",
            description="一键重置演示：紧急插单 200 PCS",
            created_by=created_by,
        )
        scenario_id = scenario.scenario_id

    return {
        "run_number": run.run_number,
        "operations": operation_count,
        "exceptions": exception_count,
        "scenario_id": scenario_id,
    }


def reset_planning_demo(
    db: Session,
    *,
    created_by: str = "system",
    rebuild_run: bool = True,
    with_scenario: bool = True,
) -> dict:
    """一键重置计划/执行/EAM 演示数据。

    返回：{"cleared": {...}, "resources_reset": n, "seeded": {...}}
    """
    cleared = _clear(db)
    resources_reset = _reset_resources(db)
    _rebuild_master_seed(db)

    seeded: dict = {
        "maintenance_plans": db.query(MaintenancePlan).count(),
        "maintenance_orders": db.query(MaintenanceOrder).count(),
        "equipment_failures": db.query(EquipmentFailure).count(),
        "inspections": db.query(InspectionOrder).count(),
        "ncrs": db.query(NonConformanceReport).count(),
    }
    if rebuild_run:
        seeded.update(_build_demo_run(db, created_by=created_by, with_scenario=with_scenario))

    db.flush()
    return {
        "cleared": cleared,
        "resources_reset": resources_reset,
        "seeded": seeded,
        "reset_at": datetime.now().isoformat(timespec="seconds"),
        "reset_by": created_by,
    }
