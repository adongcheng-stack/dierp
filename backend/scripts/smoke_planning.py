"""计划引擎冒烟脚本：生成 MPS -> 下达 -> 运行 MRP -> 输出结果摘要。

用法：python backend/scripts/smoke_planning.py [--rollback]
"""
from __future__ import annotations

import argparse
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
    KittingResult,
    MrpException,
    MrpRequirement,
    PlannedOrder,
)
from backend.services.planning import MpsEngine, MrpEngine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollback", action="store_true", help="只验证不落库")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = today + timedelta(days=1)
        end = today + timedelta(days=56)

        print("1) 生成 MPS ...")
        mps = MpsEngine.generate(
            db,
            horizon_start=start,
            horizon_end=end,
            plan_name="演示 MPS · 未来 8 周",
            demand_source="MIXED",
            include_forecast=True,
            include_safety_stock=True,
            created_by="smoke",
        )
        db.flush()
        print(
            f"   {mps.mps_number} 需求合计={mps.total_gross} 计划接收={mps.total_planned}"
        )

        print("2) 下达 MPS ...")
        MpsEngine.release(db, mps.mps_number, released_by="smoke")

        print("3) 运行 MRP ...")
        run = MrpEngine.run(
            db,
            horizon_start=start,
            horizon_end=end,
            run_type="REGENERATIVE",
            demand_source="MPS",
            mps_number=mps.mps_number,
            include_forecast=True,
            include_safety_stock=True,
            run_by="smoke",
        )
        db.flush()

        req_count = (
            db.query(MrpRequirement).filter(MrpRequirement.run_number == run.run_number).count()
        )
        plan_count = (
            db.query(PlannedOrder).filter(PlannedOrder.run_number == run.run_number).count()
        )
        exc_count = (
            db.query(MrpException).filter(MrpException.run_number == run.run_number).count()
        )
        kit_count = db.query(KittingResult).count()
        print(
            f"   {run.run_number} 需求行={req_count} 计划订单={plan_count} "
            f"异常={exc_count} 齐套结果={kit_count}"
        )

        print("   计划订单示例:")
        for plan in (
            db.query(PlannedOrder)
            .filter(PlannedOrder.run_number == run.run_number)
            .order_by(PlannedOrder.id)
            .limit(8)
            .all()
        ):
            print(
                f"   - {plan.planned_order_number} {plan.order_type} "
                f"{plan.material_code} x {plan.quantity} {plan.start_date:%m-%d}~{plan.due_date:%m-%d}"
            )

        print("   关键异常示例:")
        for exc in (
            db.query(MrpException)
            .filter(MrpException.run_number == run.run_number)
            .order_by(MrpException.severity.desc())
            .limit(6)
            .all()
        ):
            print(
                f"   - [{exc.severity}] {exc.exception_type} {exc.material_code}: "
                f"{(exc.suggestion or '')[:60]}"
            )

        if args.rollback:
            db.rollback()
            print("已回滚（未落库）")
        else:
            db.commit()
            print("已提交")
    except Exception as exc:
        db.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
