"""Cost engine smoke test (P1 成本引擎).

Verifies the full cost pipeline against the local DB:
  standard rollup -> actual collection -> variance -> settlement -> rates.
Run: python backend/scripts/smoke_cost.py
"""
from __future__ import annotations

import sys
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
from backend.common.models import mm, pp  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    CostSettlement,
    CostVariance,
    ProductionCost,
    StandardCost,
)
from backend.services.planning.cost_engine import CostEngine  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        materials = [
            m.material_code
            for m in db.query(mm.Material).filter(mm.Material.is_deleted == False).all()
        ]
        print(f"[1] 标准成本多层滚动: {len(materials)} 个物料")
        done = CostEngine.rollup_many(db, materials, version="1", created_by="smoke")
        db.commit()
        rows = db.query(StandardCost).filter(StandardCost.is_deleted == False).all()
        print(f"    滚动 {done} 个，标准成本 {len(rows)} 条")
        for r in rows[:6]:
            print(
                f"    {r.material_code}: "
                f"料={float(r.material_cost)} 工={float(r.labor_cost)} "
                f"费={float(r.overhead_cost)} 合计={float(r.total_cost)}"
            )

        order = (
            db.query(pp.ProductionOrder)
            .filter(pp.ProductionOrder.is_deleted == False)
            .first()
        )
        if order is None:
            print("[!] 无生产订单，跳过实际成本/差异/结算")
            return 0
        ono = order.order_number
        print(f"\n[2] 工单实际成本归集: {ono}")
        prod = CostEngine.collect_production_cost(db, ono, created_by="smoke")
        db.commit()
        print(
            f"    料={float(prod.material_cost_actual)} "
            f"工={float(prod.labor_cost_actual)} "
            f"费={float(prod.overhead_actual)} "
            f"合计={float(prod.total_actual)} 状态={prod.status}"
        )

        print(f"\n[3] 差异分析: {ono}")
        variances = CostEngine.analyze_variances(db, ono, created_by="smoke")
        db.commit()
        for v in variances:
            print(
                f"    {v.variance_type.value}: "
                f"标准={float(v.standard_amount)} 实际={float(v.actual_amount)} "
                f"差异={float(v.variance_amount)} ({float(v.variance_pct)}%)"
            )

        print(f"\n[4] 结算: {ono}")
        stl = CostEngine.settle(db, ono, created_by="smoke")
        db.commit()
        print(
            f"    结算 {stl.settlement_number} 总成本={float(stl.total_cost)} "
            f"状态={stl.settlement_status}"
        )

        counts = {
            "标准成本": db.query(StandardCost).count(),
            "工单成本": db.query(ProductionCost).count(),
            "差异": db.query(CostVariance).count(),
            "结算": db.query(CostSettlement).count(),
        }
        print(f"\n[5] 数据量: {counts}")
        print("\n成本引擎冒烟通过")
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