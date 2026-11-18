"""演示环境一键清理与重建（命令行入口）。

用法：
    python backend/scripts/reset_demo.py                # 清理 + 重建排程/场景/EAM 种子
    python backend/scripts/reset_demo.py --keep-run     # 只清理，不重建排程批次
    python backend/scripts/reset_demo.py --no-scenario  # 重建排程但不生成插单场景
    python backend/scripts/reset_demo.py --json         # 输出机器可读结果

清空范围：排程批次/工序/异常、插单场景/影响、维护计划/工单、故障记录。
保留范围：客户、销售订单、BOM、工艺路线、生产订单、物料、成本费率等主数据。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.common.database.base import SessionLocal  # noqa: E402
from backend.services.planning.demo_reset import reset_planning_demo  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理并重建 ERP 演示数据")
    parser.add_argument("--keep-run", action="store_true", help="只清理，不重建 APS 排程批次")
    parser.add_argument("--no-scenario", action="store_true", help="重建排程但不生成插单场景")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    parser.add_argument("--by", default="system", help="操作人（写入 reset_by）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.json:
        print("=" * 56)
        print("ERP 演示数据一键重置")
        print("=" * 56)

    db = SessionLocal()
    try:
        result = reset_planning_demo(
            db,
            created_by=args.by,
            rebuild_run=not args.keep_run,
            with_scenario=not args.no_scenario,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return

    cleared = result["cleared"]
    seeded = result["seeded"]
    print("[1] 清理运行时数据")
    for key, count in cleared.items():
        print(f"    {key:<22}{count:>6}")
    print(f"[2] 资源状态复位 {result['resources_reset']} 条（DRILL-B 保持保养中）")
    print("[3] 重建演示数据")
    print(f"    维护计划               {seeded.get('maintenance_plans', 0):>6}")
    print(f"    维护工单               {seeded.get('maintenance_orders', 0):>6}")
    print(f"    故障记录               {seeded.get('equipment_failures', 0):>6}")
    if "run_number" in seeded:
        print(f"    排程批次               {seeded['run_number']}")
        print(f"    排程工序               {seeded.get('operations', 0):>6}")
        print(f"    排程异常               {seeded.get('exceptions', 0):>6}")
        if seeded.get("scenario_id"):
            print(f"    插单场景               {seeded['scenario_id']}")
    print("-" * 56)
    print(f"重置完成 · {result['reset_at']} · by {result['reset_by']}")


if __name__ == "__main__":
    main()
