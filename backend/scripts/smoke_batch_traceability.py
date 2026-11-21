"""原料批次追溯冒烟：领料 → 原料批次 → 采购单 → 供应商。

Run: python backend/scripts/smoke_batch_traceability.py
依赖 upgrade_planning.seed_material_batches 已回填演示批次（demo_reset 亦会调用）。
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
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.services.planning.traceability_engine import TraceEngine  # noqa: E402


def main() -> int:
    db = SessionLocal()
    passed = 0
    checks = 5
    try:
        # 1. 演示领料单已回填批次与来源采购单
        issue = (
            db.query(mm.MaterialIssue)
            .filter(
                mm.MaterialIssue.is_deleted == False,  # noqa: E712
                mm.MaterialIssue.batch_number.isnot(None),
            )
            .first()
        )
        assert issue is not None, "演示领料单未回填批次号（请先运行 upgrade_planning.py）"
        assert issue.purchase_order_number, "演示领料单未回填来源采购单"
        print(f"[PASS] 1.领料单 {issue.issue_number} 含批次 {issue.batch_number} / 采购单 {issue.purchase_order_number}")
        passed += 1

        # 2. 物料反向追溯含原料批次节点
        result = TraceEngine.trace_material(db, issue.material_code)
        batches = [n for n in result["nodes"] if n["type"] == "MATERIAL_BATCH"]
        assert batches, "物料追溯缺 MATERIAL_BATCH 节点"
        passed += 1
        print(f"[PASS] 2.物料 {issue.material_code} 反向追溯含 {len(batches)} 个原料批次节点")

        # 3. 批次节点带供应商元数据
        supplier_batches = [n for n in batches if n["meta"].get("supplier")]
        assert supplier_batches, "批次节点未带供应商"
        print(f"[PASS] 3.批次节点携带供应商 {supplier_batches[0]['meta']['supplier']}")
        passed += 1

        # 4. 领料 → 批次 → 采购单 的边齐备
        batch_key = f"MATERIAL_BATCH:{supplier_batches[0]['id']}"
        labels = [(e["from"], e["to"], e["label"]) for e in result["edges"]]
        assert any(b[0].startswith("MATERIAL_ISSUE:") and b[1] == batch_key for b in labels), "缺领料→批次边"
        assert any(b[0] == batch_key and b[1].startswith("PURCHASE_ORDER:") for b in labels), "缺批次→采购单边"
        print("[PASS] 4.领料→原料批次→采购单边齐备")
        passed += 1

        # 5. 正向工单追溯同样带出批次
        order_result = TraceEngine.trace_order(db, issue.production_order_number)
        order_batches = [n for n in order_result["nodes"] if n["type"] == "MATERIAL_BATCH"]
        assert order_batches, "工单正向追溯缺原料批次节点"
        print(f"[PASS] 5.工单 {issue.production_order_number} 正向追溯含 {len(order_batches)} 个批次节点")
        passed += 1
    finally:
        db.close()

    print(f"\n===== 原料批次追溯冒烟：{passed}/{checks} 通过 =====")
    return 0 if passed == checks else 1


if __name__ == "__main__":
    sys.exit(main())
