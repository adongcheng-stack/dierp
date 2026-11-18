"""APS scheduling engine smoke test (P1 有限产能排程).

Run: python backend/scripts/smoke_aps.py
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
    ScheduleException,
    ScheduleRun,
    ScheduledOperation,
    ScenarioImpact,
    ScenarioSimulation,
)
from backend.services.planning.aps_engine import ApsEngine  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = today
        end = today + timedelta(days=42)

        print("[1] 正排（FORWARD）")
        run = ApsEngine.run(
            db,
            run_name="演示 APS · 正排",
            horizon_start=start,
            horizon_end=end,
            algorithm="FORWARD",
            created_by="smoke",
        )
        db.commit()
        ops = (
            db.query(ScheduledOperation)
            .filter(ScheduledOperation.run_number == run.run_number)
            .order_by(ScheduledOperation.planned_start)
            .all()
        )
        print(f"    批次 {run.run_number} 工序={len(ops)} 异常={run.exception_count}")
        for op in ops[:8]:
            print(
                f"    {op.production_order_number} {op.operation_no} {op.operation_name} "
                f"@ {op.work_center_id} {op.planned_start:%m-%d %H:%M}~{op.planned_end:%H:%M}"
            )

        print("\n[2] 插单模拟（INSERT_ORDER）")
        scenario = ApsEngine.simulate(
            db,
            run_number=run.run_number,
            scenario_type="INSERT_ORDER",
            description="临时插单 300 PCS",
            created_by="smoke",
        )
        db.commit()
        impacts = (
            db.query(ScenarioImpact)
            .filter(ScenarioImpact.scenario_id == scenario.scenario_id)
            .all()
        )
        print(f"    场景 {scenario.scenario_id} 影响工序 {len(impacts)} 道")
        print(f"    摘要: {scenario.impact_summary}")

        print("\n[3] 发布")
        ApsEngine.publish(db, run.run_number, published_by="smoke")
        db.commit()
        run = db.query(ScheduleRun).filter(ScheduleRun.run_number == run.run_number).first()
        print(f"    状态={run.status.value}")

        counts = {
            "排程批次": db.query(ScheduleRun).count(),
            "排程工序": db.query(ScheduledOperation).count(),
            "排程异常": db.query(ScheduleException).count(),
            "模拟场景": db.query(ScenarioSimulation).count(),
            "影响明细": db.query(ScenarioImpact).count(),
        }
        print(f"\n[4] 数据量: {counts}")
        print("\nAPS 排程冒烟通过")
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