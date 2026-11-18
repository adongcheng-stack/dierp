"""EAM 设备管理引擎冒烟测试（P1 轻量 EAM）。

Run: python backend/scripts/smoke_eam.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    import io

    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    EquipmentFailure,
    FailureStatus,
    MaintenanceOrder,
    MaintenancePlan,
    MaintenanceStatus,
    Resource,
    ResourceStatus,
)
from backend.services.planning.eam_engine import EamEngine  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        print("[1] 到期保养自动生成（generate_due_orders）")
        created = EamEngine.generate_due_orders(db, as_of=today, created_by="smoke")
        db.commit()
        print(f"    本次生成 {len(created)} 张维护工单")
        for order in created:
            print(f"    {order.order_number} {order.resource_id} {order.maintenance_type.value} @ {order.planned_date:%m-%d}")
        again = EamEngine.generate_due_orders(db, as_of=today, created_by="smoke")
        db.commit()
        assert len(again) == 0, f"generate_due_orders 不幂等：重复执行又生成 {len(again)} 张"
        print(f"    幂等校验通过（重复执行生成 {len(again)} 张）")

        print("\n[2] 维护工单完成并回写计划（complete_order）")
        target = (
            db.query(MaintenanceOrder)
            .filter(
                MaintenanceOrder.is_deleted == False,
                MaintenanceOrder.status == MaintenanceStatus.PLANNED,
            )
            .order_by(MaintenanceOrder.id.desc())
            .first()
        )
        if target is None:
            # 保证脚本可重复运行：把一条计划拨到过去再生成一张工单（避开历史工单日期，绕过幂等）
            plan = (
                db.query(MaintenancePlan)
                .filter(MaintenancePlan.is_deleted == False, MaintenancePlan.status == MaintenanceStatus.PLANNED)
                .order_by(MaintenancePlan.id)
                .first()
            )
            assert plan is not None, "没有可用的维护计划（先运行 backend/upgrade_planning.py）"
            taken = {
                row.planned_date
                for row in db.query(MaintenanceOrder)
                .filter(
                    MaintenanceOrder.plan_id == plan.plan_id,
                    MaintenanceOrder.is_deleted == False,
                )
                .all()
            }
            due = today - timedelta(days=1)
            while due in taken:
                due -= timedelta(days=1)
            plan.next_due_at = due
            db.flush()
            generated = EamEngine.generate_due_orders(db, as_of=today, created_by="smoke")
            assert generated, "拨动计划后仍未生成维护工单"
            target = generated[0]
            print(f"    无既有 PLANNED 工单，已拨动计划 {plan.plan_id} 至 {due:%m-%d} 并生成 {target.order_number}")
        plan_before = (
            db.query(MaintenancePlan).filter(MaintenancePlan.plan_id == target.plan_id).first()
            if target.plan_id
            else None
        )
        completed = EamEngine.complete_order(
            db,
            target.order_number,
            executed_by="smoke",
            downtime_hours="1.5",
            result_note="冒烟测试：点检完成",
        )
        db.commit()
        print(f"    工单 {completed.order_number} 状态={completed.status.value}")
        if plan_before is not None:
            print(
                f"    计划回写 last_executed_at={plan_before.last_executed_at:%m-%d %H:%M} "
                f"next_due_at={plan_before.next_due_at:%m-%d}"
            )
            assert plan_before.last_executed_at is not None, "计划 last_executed_at 未回写"

        print("\n[3] 故障上报与解决（record_failure / resolve_failure）")
        failure = EamEngine.record_failure(
            db,
            resource_id="RES-DRILL-A-01",
            severity="LOW",
            description="冒烟测试：主轴冷却液液位偏低",
            reported_by="smoke",
            downtime_hours="0.5",
        )
        db.commit()
        print(f"    上报 {failure.failure_number} @ {failure.work_center_id} 状态={failure.status.value}")
        resolved = EamEngine.resolve_failure(
            db,
            failure.failure_number,
            root_cause="冷却液自然蒸发",
            action_taken="补充冷却液至标准液位",
            downtime_hours="0.5",
            resolved_by="smoke",
        )
        db.commit()
        print(f"    解决 {resolved.failure_number} 状态={resolved.status.value}")
        assert resolved.status == FailureStatus.CLOSED

        print("\n[4] OEE 快照（oee_snapshot）")
        snapshot = EamEngine.oee_snapshot(db)
        summary = snapshot["summary"]
        print(
            f"    全厂: 可用率={summary['availability']} 性能率={summary['performance']} "
            f"良品率={summary['quality']} OEE={summary['oee']}"
        )
        for row in snapshot["work_centers"]:
            print(
                f"    {row['work_center_id']}: A={row['availability']} P={row['performance']} "
                f"Q={row['quality']} OEE={row['oee']} 停机={row['downtime_hours']}h "
                f"停机资源={row['down_resources'] or '-'}"
            )
        drill_b = next((r for r in snapshot["work_centers"] if r["work_center_id"] == "DRILL-B"), None)
        assert drill_b is not None, "OEE 快照缺少 DRILL-B 工作中心"
        assert drill_b["downtime_hours"] > 0, "DRILL-B 应计入故障停机时长"
        assert drill_b["down_resources"] == ["RES-DRILL-B-01"], "RES-DRILL-B-01 应为非 ACTIVE 状态"

        counts = {
            "维护计划": db.query(MaintenancePlan).filter(MaintenancePlan.is_deleted == False).count(),
            "维护工单": db.query(MaintenanceOrder).filter(MaintenanceOrder.is_deleted == False).count(),
            "故障记录": db.query(EquipmentFailure).filter(EquipmentFailure.is_deleted == False).count(),
            "保养中资源": db.query(Resource)
            .filter(Resource.status == ResourceStatus.MAINTENANCE, Resource.is_deleted == False)
            .count(),
        }
        print(f"\n[5] 数据量: {counts}")
        print("\nEAM 设备管理冒烟通过")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
