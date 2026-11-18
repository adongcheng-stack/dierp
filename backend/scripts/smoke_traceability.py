"""双向追溯引擎冒烟测试（只读派生查询，不产生数据）。

Run: python backend/scripts/smoke_traceability.py
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


def node_keys(result):
    return {n["key"] for n in result["nodes"]}


def count_by_prefix(result, prefix):
    return sum(1 for k in node_keys(result) if k.startswith(prefix))


def main() -> int:
    db = SessionLocal()
    try:
        print("[1] 正向追溯 LOT-20251230-0003（质量+设备全链路）")
        result = TraceEngine.trace_lot(db, "LOT-20251230-0003")
        keys = node_keys(result)
        assert result["direction"] == "FORWARD"
        # 静态单据编号（演示主数据，不随日期变化）
        expected = [
            "LOT:LOT-20251230-0003",
            "PRODUCTION_ORDER:PO-20251230-0003",
            "SALES_ORDER:SO-20251230-0002",
            "CUSTOMER:FJ002",
        ]
        missing = [k for k in expected if k not in keys]
        assert not missing, f"正向链缺节点: {missing}"
        # 动态编号（种子按当天日期生成，断言用前缀计数）
        ipqc = [n for n in result["nodes"] if n["type"] == "INSPECTION" and n["meta"].get("result") == "FAIL"]
        assert ipqc, "正向链缺 FAIL 检验"
        assert count_by_prefix(result, "NCR:") >= 2, "正向链缺 NCR"
        assert count_by_prefix(result, "EQUIPMENT_FAILURE:") >= 1, "正向链缺设备故障"
        print(
            f"    节点 {len(keys)} 个 / 边 {len(result['edges'])} 条，"
            f"FAIL 检验 + NCR×{count_by_prefix(result, 'NCR:')} + 故障×{count_by_prefix(result, 'EQUIPMENT_FAILURE:')} 全入链"
        )

        print("[2] 正向追溯 LOT-20251230-0002（报废报工链）")
        result = TraceEngine.trace_lot(db, "LOT-20251230-0002")
        keys = node_keys(result)
        assert "OPERATION_REPORT:OR-QMS-2026-REPORT-0001" in keys, "报废报工未入链"
        assert "SALES_ORDER:SO-20251230-0001" in keys, "销售订单未入链"
        scrap_node = next(n for n in result["nodes"] if n["key"] == "OPERATION_REPORT:OR-QMS-2026-REPORT-0001")
        assert scrap_node["meta"]["scrap_quantity"] == 12.0
        print(f"    节点 {len(keys)} 个，含报废报工 12 PCS")

        print("[3] 反向追溯物料 HF1004ENIGAB02（领料→工单→批次→销售→客户）")
        result = TraceEngine.trace_material(db, "HF1004ENIGAB02")
        keys = node_keys(result)
        assert result["direction"] == "BACKWARD"
        for key in [
            "MATERIAL:HF1004ENIGAB02",
            "MATERIAL_ISSUE:MI-20251218-0001",
            "PRODUCTION_ORDER:PO-20251218-0001",
            "LOT:LOT-20251218-0001",
            "SALES_ORDER:SO-20251218-0001",
            "CUSTOMER:FJ001",
        ]:
            assert key in keys, f"反向链缺节点: {key}"
        print(f"    节点 {len(keys)} 个 / 边 {len(result['edges'])} 条，反向链完整")

        print("[4] 从销售订单 SO-20251231-0001 出发（1 单 4 工）")
        result = TraceEngine.trace_order(db, "SO-20251231-0001")
        keys = node_keys(result)
        for po in ["PO-APS-01", "PO-APS-02", "PO-APS-03", "PO-APS-04"]:
            assert f"PRODUCTION_ORDER:{po}" in keys, f"缺生产订单 {po}"
        assert "CUSTOMER:FJ002" in keys
        print(f"    节点 {len(keys)} 个，覆盖 4 张 APS 工单")

        print("[5] 从生产订单 PO-20251230-0003 出发（自动识别）")
        result = TraceEngine.trace_order(db, "PO-20251230-0003")
        keys = node_keys(result)
        assert "LOT:LOT-20251230-0003" in keys
        assert count_by_prefix(result, "NCR:") >= 2, "生产订单展开缺 NCR"
        print(f"    节点 {len(keys)} 个")

        print("[6] 根节点搜索")
        hits = TraceEngine.search(db, "LOT-2025")
        assert any(h["type"] == "LOT" for h in hits), "LOT 搜索无结果"
        hits = TraceEngine.search(db, "NCR-")
        ncr_hits = [h for h in hits if h["type"] == "NCR"]
        assert ncr_hits and all(h["meta"].get("trace_lot") or h["meta"].get("trace_material") for h in ncr_hits), "NCR 搜索缺追溯跳转"
        print(f"    LOT 命中 + NCR 命中 {len(ncr_hits)} 条（可跳转）")

        print("[7] 概览")
        overview = TraceEngine.overview(db)
        assert overview["lots"] >= 4 and overview["ncrs"] >= 2
        print(f"    {overview}")

        print("\n双向追溯引擎冒烟通过")
        return 0
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
