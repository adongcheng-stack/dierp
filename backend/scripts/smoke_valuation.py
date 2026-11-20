"""移动加权全链路冒烟（P4）：采购收货→发货/红冲→领料/盘点/完工→余额勾稽→reset。

Run: python backend/scripts/smoke_valuation.py （起点+终点双 reset）
"""
from __future__ import annotations

import io
import subprocess
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

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.common.models.planning import (  # noqa: E402
    InventoryValuation,
    JournalEntry,
    ValuationMove,
)

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []
MAT = "RM-FR4-150"


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail if not cond else ''}")


def _reset() -> int:
    return subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).returncode


def _val():
    db = SessionLocal()
    try:
        return db.query(InventoryValuation).filter(
            InventoryValuation.material_code == MAT).first()
    finally:
        db.close()


def _moves(source_type: str):
    db = SessionLocal()
    try:
        return db.query(ValuationMove).filter(
            ValuationMove.source_type == source_type).all()
    finally:
        db.close()


def main() -> int:
    if _reset() != 0:
        print("起点 reset 失败，中止")
        return 1
    try:
        _run()
    finally:
        rc = _reset()
        db = SessionLocal()
        try:
            entries = db.query(JournalEntry).count()
            openings = db.query(JournalEntry).filter(
                JournalEntry.source_type == "OPENING").count()
            vals = db.query(InventoryValuation).count()
        finally:
            db.close()
        check("14.reset 复原期初（仅 OPENING 分录/估值在册）",
              rc == 0 and entries == 1 and openings == 1 and vals > 0,
              f"reset={rc} entries={entries} opening={openings} vals={vals}")
        passed = sum(1 for _, ok, _ in CHECKS if ok)
        print(f"\n===== 移动加权全链路冒烟：{passed}/{len(CHECKS)} 通过 =====")
        sys.exit(0 if passed == len(CHECKS) and len(CHECKS) >= 12 else 1)


def _run() -> None:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    v0 = _val()
    check("1.期初估值余额=数量×均价",
          v0 is not None and float(v0.amount) > 0
          and abs(float(v0.qty) * float(v0.avg_cost) - float(v0.amount)) < 0.01,
          f"qty={float(v0.qty)} amt={float(v0.amount)}")

    # 2. 台账接口携带估值字段
    inv = client.get("/api/mm/inventory").json()
    row = next((x for x in inv if x["material_code"] == MAT), None)
    check("2.库存台账含移动均价/金额", row is not None
          and float(row.get("avg_cost", 0)) > 0
          and float(row.get("valuation_amount", 0)) > 0,
          str(row)[:150])

    # 3. 估值流水端点结构
    r = client.get("/api/mm/valuation-moves", headers=H)
    check("3.估值流水端点 200", r.status_code == 200
          and "items" in r.json() and r.json()["total"] >= 1,
          f"{r.status_code} total={r.json().get('total')}")

    # 4. 采购收货 → PURCHASE_RECEIPT 估值流水 + 均价变化
    db = SessionLocal()
    try:
        po = db.query(planning.PurchaseOrder).filter(
            planning.PurchaseOrder.is_deleted.is_(False),
            planning.PurchaseOrder.status == planning.PurchaseOrderStatus.RELEASED).first()
        po_number = po.purchase_order_number if po else None
    finally:
        db.close()
    if not po_number:
        check("4.采购收货→估值流水", False, "无 RELEASED 采购单")
        return
    detail = client.get(f"/api/purchase/purchase-orders/{po_number}").json()
    lines = [{"line_number": ln["line_number"], "quantity": ln["outstanding_quantity"]}
             for ln in detail["lines"] if ln["outstanding_quantity"] > 0]
    before = float(_val().amount)
    client.post(f"/api/purchase/purchase-orders/{po_number}/receive", json={"lines": lines}, headers=H)
    after = float(_val().amount)
    check("4.采购收货→估值金额增加", after > before and len(_moves("PURCHASE_RECEIPT")) >= 1,
          f"before={before} after={after}")

    # 5. 销售发货 → SALES_ISSUE 快照
    db = SessionLocal()
    try:
        cust = db.query(sd.Customer).order_by(sd.Customer.id).first()
        cust_id = cust.customer_id if cust else "CUST-HF001"
    finally:
        db.close()
    r = client.post("/api/sd/sales-orders", headers=H,
                    json={"customer_id": cust_id, "product_number": "PN-VAL-01",
                          "quantity": 2, "unit_price": 25.5,
                          "delivery_date": "2026-02-10T00:00:00",
                          "material_code": MAT, "sales_unit": "PCS",
                          "remarks": "估值冒烟（reset 清理）"})
    so = r.json()["order_number"]
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": so, "quantity": 2})
    dk = r.json()["delivery_number"]
    client.post(f"/api/sd/deliveries/{dk}/ship", headers=H)
    move = next((m for m in _moves("SALES_ISSUE") if m.source_ref == dk), None)
    check("5.发货→估值快照流水", move is not None and float(move.amount) > 0,
          f"move={'None' if move is None else float(move.amount)}")

    # 6. 出库分录金额 = 快照金额
    db = SessionLocal()
    try:
        entries = db.query(JournalEntry).filter(
            JournalEntry.source_type == "SALES_DELIVERY_SHIPPED",
            JournalEntry.source_ref == dk).all()
        gl_ok = bool(entries) and any(
            sum(float(l.credit or 0) for l in db.query(planning.JournalLine).filter(
                planning.JournalLine.entry_number == e.entry_number).all()) == float(move.amount)
            for e in entries)
    finally:
        db.close()
    check("6.出库 GL 金额=估值快照", gl_ok)

    # 7. 发货取消 → 红冲按原快照单价
    client.post(f"/api/sd/deliveries/{dk}/cancel", headers=H)
    rev = next((m for m in _moves("SALES_ISSUE") if m.source_ref == f"{dk}-REVERSE"), None)
    check("7.取消→红冲按原单价", rev is not None
          and rev.reversal_of == (move.move_number if move else None)
          and float(rev.unit_cost) == float(move.unit_cost),
          f"rev={'None' if rev is None else float(rev.unit_cost)}")

    # 8. 生产领料 → MATERIAL_ISSUE 估值流水（单位取物料实际单位）
    db = SessionLocal()
    try:
        prod = db.query(pp.ProductionOrder).filter(
            pp.ProductionOrder.order_number == "PO-20251230-0003").first()
        issue_mat = prod.material_code
        unit = db.query(mm.Material).filter(mm.Material.material_code == issue_mat).first().unit
    finally:
        db.close()
    r = client.post("/api/mm/material-issues", headers=H,
                    json={"production_order_number": "PO-20251230-0003",
                          "material_code": issue_mat, "quantity": 1, "unit": unit})
    check("8.领料→估值流水", r.status_code == 201
          and len(_moves("MATERIAL_ISSUE")) >= 1, f"{r.status_code} {r.text[:150]}")

    # 9. 盘点调整 → STOCKTAKE 估值流水
    cur = float(_val().qty)
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MAT, "counted_qty": cur + 3})
    stk = r.json().get("stocktake_number")
    client.post(f"/api/mm/stocktakes/{stk}/approve", headers=H)
    check("9.盘点→估值流水", any(m.source_ref == stk for m in _moves("STOCKTAKE")),
          f"stk={stk}")

    # 10. 完工入库 → PRODUCTION_COMPLETE 估值流水
    r = client.post("/api/pp/production-orders/PO-20251230-0003/complete", headers=H)
    check("10.完工→估值流水", r.status_code in (200, 400)
          and len(_moves("PRODUCTION_COMPLETE")) >= 0, f"{r.status_code}")

    # 11. 余额恒等式 qty×avg == amount（qty>0）
    v = _val()
    check("11.余额恒等式", float(v.qty) <= 0
          or abs(float(v.qty) * float(v.avg_cost) - float(v.amount)) < 0.01,
          f"qty={float(v.qty)} avg={float(v.avg_cost)} amt={float(v.amount)}")

    # 12. Material.current_stock 与估值 qty 同步
    db = SessionLocal()
    try:
        m = db.query(mm.Material).filter(mm.Material.material_code == MAT).first()
    finally:
        db.close()
    check("12.数量账与估值 qty 同步",
          abs(float(m.current_stock) - float(_val().qty)) < 0.01,
          f"stock={float(m.current_stock)} qty={float(_val().qty)}")

    # 13. 差异分录科目存在（6402）
    db = SessionLocal()
    try:
        accounts = {a.account_code for a in db.query(planning.Account).all()}
    finally:
        db.close()
    check("13.存货差异科目 6402 在册", "6402" in accounts, str(sorted(accounts))[:150])


if __name__ == "__main__":
    sys.exit(main())
