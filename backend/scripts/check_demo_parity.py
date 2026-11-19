"""演示数据一致性校验：mock snapshot.json ↔ 真实数据库种子。

对比两侧「应当一致的关键事实」（忽略动态编号的日期部分），
不一致即退出码 1，供 CI / 发布前门禁使用。

Run: python backend/scripts/check_demo_parity.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.common.models.mm import Material  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    EquipmentFailure,
    InspectionOrder,
    NonConformanceReport,
)
from backend.common.models.pp import LotCard, OperationReport, ProductionOrder  # noqa: E402
from backend.common.models.sd import SalesOrder  # noqa: E402

SNAPSHOT_PATH = project_root / "frontend" / "src" / "mock" / "snapshot.json"

errors: list[str] = []
checks = 0


def check(name: str, db_value, mock_value):
    global checks
    checks += 1
    if db_value != mock_value:
        errors.append(f"[{name}] DB={db_value!r} != MOCK={mock_value!r}")


def main() -> int:
    db = SessionLocal()
    try:
        with io.open(SNAPSHOT_PATH, encoding="utf-8") as f:
            mock = json.load(f)

        def live(model):
            return db.query(model).filter(model.is_deleted == False).all()  # noqa: E712

        # ── 1) APS 工单的销售关联（本次踩过坑的字段） ─────────────────────
        db_aps = {
            o.order_number: o.sales_order_number
            for o in live(ProductionOrder)
            if o.order_number.startswith("PO-APS-")
        }
        mock_aps = {
            o["order_number"]: o.get("sales_order_number")
            for o in mock["productionOrders"]
            if o["order_number"].startswith("PO-APS-")
        }
        check("APS工单销售关联", db_aps, mock_aps)

        # ── 2) 批次卡集合 ────────────────────────────────────────────────
        check("批次卡集合", sorted(l.lot_number for l in live(LotCard)),
              sorted(l["lot_number"] for l in mock["lotCards"]))

        # ── 3) 生产订单主键与物料映射 ─────────────────────────────────────
        check("生产订单物料映射",
              sorted((o.order_number, o.material_code) for o in live(ProductionOrder)),
              sorted((o["order_number"], o["material_code"]) for o in mock["productionOrders"]))

        # ── 4) 销售订单 → 客户 ───────────────────────────────────────────
        check("销售订单客户关联",
              sorted((s.order_number, s.customer_id) for s in live(SalesOrder)),
              sorted((s["order_number"], s["customer_id"]) for s in mock["salesOrders"]))

        # ── 5) 物料主数据集合 ────────────────────────────────────────────
        check("物料编码集合", sorted(m.material_code for m in live(Material)),
              sorted(m["material_code"] for m in mock["materials"]))

        # ── 6) 检验单关键事实（忽略动态单号） ─────────────────────────────
        db_insp = sorted(
            (i.inspection_type.value, i.material_code, i.lot_number, i.result.value if i.result else None)
            for i in live(InspectionOrder)
        )
        mock_insp = sorted(
            (i["inspection_type"], i["material_code"], i.get("lot_number"), i.get("result"))
            for i in mock["inspectionOrders"]
        )
        check("检验单事实(环节/物料/批次/结论)", db_insp, mock_insp)

        # ── 7) NCR 关键事实（忽略动态单号） ───────────────────────────────
        db_ncr = sorted(
            (n.source_type.value, n.material_code, n.lot_number,
             bool(n.equipment_cause), n.failure_number is not None, n.status.value)
            for n in live(NonConformanceReport)
        )
        mock_ncr = sorted(
            (n["source_type"], n["material_code"], n.get("lot_number"),
             bool(n.get("equipment_cause")), n.get("failure_number") is not None, n["status"])
            for n in mock["nonConformanceReports"]
        )
        check("NCR事实(来源/物料/批次/设备原因/联动/状态)", db_ncr, mock_ncr)

        # ── 8) 设备故障（资源维度） ───────────────────────────────────────
        check("设备故障资源集合",
              sorted((f.resource_id, f.status.value) for f in live(EquipmentFailure)),
              sorted((f["resource_id"], f["status"]) for f in mock["equipmentFailures"]))

        # ── 9) QMS 演示报废报工单 ────────────────────────────────────────
        key = "OR-QMS-2026-REPORT-0001"
        db_rep = next((r for r in live(OperationReport) if r.report_number == key), None)
        mock_rep = next((r for r in mock["operationReports"] if r.get("report_number") == key), None)
        check("QMS报废报工存在", db_rep is not None, mock_rep is not None)
        if db_rep and mock_rep:
            check("QMS报废报工事实",
                  (db_rep.production_order_number, float(db_rep.scrap_quantity or 0), db_rep.lot_number),
                  (mock_rep["production_order_number"], float(mock_rep.get("scrap_quantity") or 0), mock_rep.get("lot_number")))

        # ── 9.5) 采购演示单据（N3 闭环；忽略动态单号） ────────────────────
        from backend.common.models.planning import PurchaseOrder, PurchaseOrderLine  # noqa: E402

        db_pos = live(PurchaseOrder)
        db_lines = {
            po.purchase_order_number: sorted(
                (l.material_code, float(l.quantity), float(l.received_quantity or 0))
                for l in live(PurchaseOrderLine)
                if l.purchase_order_number == po.purchase_order_number
            )
            for po in db_pos
        }
        db_purchase = sorted(
            (po.supplier_name, po.status.value, tuple(db_lines[po.purchase_order_number]))
            for po in db_pos
        )
        mock_pos = mock.get("purchaseOrders", [])
        mock_lines_map = {}
        for line in mock.get("purchaseOrderLines", []):
            mock_lines_map.setdefault(line["purchase_order_number"], []).append(
                (line["material_code"], float(line["quantity"]), float(line.get("received_quantity") or 0))
            )
        mock_purchase = sorted(
            (po["supplier_name"], po["status"], tuple(sorted(mock_lines_map.get(po["purchase_order_number"], []))))
            for po in mock_pos
        )
        check("采购演示单据(供应商/状态/行)", db_purchase, mock_purchase)

        # ── 9.6) 供应商主数据（采购域闭环） ────────────────────────────────
        from backend.common.models.planning import Supplier as ParitySupplier  # noqa: E402

        db_suppliers = sorted(
            (s.supplier_code, s.supplier_name, s.status)
            for s in live(ParitySupplier)
        )
        mock_suppliers = sorted(
            (s["supplier_code"], s["supplier_name"], s.get("status") or "ACTIVE")
            for s in mock.get("suppliers", [])
        )
        check("供应商主数据(编码/名称/状态)", db_suppliers, mock_suppliers)

        # ── 9.7) 采购申请（PR；忽略动态单号） ─────────────────────────────
        from backend.common.models.planning import (  # noqa: E402
            PurchaseRequest as ParityPR,
            PurchaseRequestLine as ParityPRLine,
        )

        db_prs = live(ParityPR)
        db_pr_lines = {
            pr.purchase_request_number: sorted(
                (l.material_code, float(l.quantity))
                for l in live(ParityPRLine)
                if l.purchase_request_number == pr.purchase_request_number
            )
            for pr in db_prs
        }
        db_pr_facts = sorted(
            (pr.supplier_name or "", pr.status.value, tuple(db_pr_lines[pr.purchase_request_number]))
            for pr in db_prs
        )
        mock_pr_lines_map: dict = {}
        for line in mock.get("purchaseRequestLines", []):
            mock_pr_lines_map.setdefault(line["purchase_request_number"], []).append(
                (line["material_code"], float(line["quantity"]))
            )
        mock_pr_facts = sorted(
            (pr.get("supplier_name") or "", pr["status"],
             tuple(sorted(mock_pr_lines_map.get(pr["purchase_request_number"], []))))
            for pr in mock.get("purchaseRequests", [])
        )
        check("采购申请(供应商/状态/行)", db_pr_facts, mock_pr_facts)

        # ── 10) 快照版本与结构 ───────────────────────────────────────────
        for collection in ["inspectionOrders", "nonConformanceReports", "operationReports",
                           "lotCards", "productionOrders", "salesOrders", "customers", "materials",
                           "suppliers", "purchaseRequests", "purchaseRequestLines",
                           "materialTransactions"]:
            check(f"快照含集合 {collection}", collection in mock, True)

        print(f"共 {checks} 项事实对比")
        if errors:
            print(f"\n❌ 不一致 {len(errors)} 项：")
            for e in errors:
                print("  ", e)
            return 1
        print("✅ mock 快照与数据库种子关键事实一致")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
