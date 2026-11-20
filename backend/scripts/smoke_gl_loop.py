"""总账全链路冒烟（P2）：业务动作 → 自动分录 → 余额表试算平衡。

Run: python backend/scripts/smoke_gl_loop.py
（TestClient 驱动；起点+终点双 reset，失败也复位）
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
    PurchaseOrder,
    PurchaseOrderLine,
    StandardCost,
)

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []

MATERIAL = "HF1004ENIGAB01"


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail if not cond else ''}")


def _reset() -> int:
    return subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).returncode


def main() -> int:
    if _reset() != 0:
        print("起点 reset 失败，中止")
        return 1
    try:
        return _run()
    finally:
        rc = _reset()
        print(f"reset_demo EXIT={rc}")
        db = SessionLocal()
        try:
            entries_after = db.query(planning.JournalEntry).count()
        finally:
            db.close()
        check("12.reset 复位（凭证清空+科目保留）",
              rc == 0 and entries_after == 0, f"reset={rc} entries={entries_after}")
        passed = sum(1 for _, ok, _ in CHECKS if ok)
        print(f"\n===== 总账全链路冒烟：{passed}/{len(CHECKS)} 通过 =====")
        sys.exit(0 if passed == len(CHECKS) and len(CHECKS) >= 10 else 1)


def _run() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        po = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.is_deleted.is_(False),
                    PurchaseOrder.status == planning.PurchaseOrderStatus.RELEASED)
            .order_by(PurchaseOrder.id)
            .first()
        )
        cust = db.query(sd.Customer).order_by(sd.Customer.id).first()
        assert po is not None and cust is not None, "前置数据缺失"
        po_number, supplier_id, customer_id = po.purchase_order_number, po.supplier_id, cust.customer_id
        std = (
            db.query(StandardCost)
            .filter(StandardCost.material_code == MATERIAL)
            .order_by(StandardCost.id.desc())
            .first()
        )
        std_cost = float(std.material_cost or 0) if std else 0.0
    finally:
        db.close()

    # 前置：采购收货 + 销售发货
    r = client.get(f"/api/purchase/purchase-orders/{po_number}")
    lines = [{"line_number": ln["line_number"], "quantity": ln["outstanding_quantity"]}
             for ln in r.json()["lines"] if ln["outstanding_quantity"] > 0]
    client.post(f"/api/purchase/purchase-orders/{po_number}/receive", json={"lines": lines}, headers=H)
    db = SessionLocal()
    try:
        po_lines = db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.purchase_order_number == po_number).all()
        cap = sum(float(l.received_quantity or 0) * float(l.unit_price or 0) for l in po_lines)
    finally:
        db.close()
    r = client.post("/api/sd/sales-orders", headers=H,
                    json={"customer_id": customer_id, "product_number": "PN-GL-01",
                          "quantity": 10, "unit_price": 25.5,
                          "delivery_date": "2026-02-10T00:00:00",
                          "material_code": MATERIAL, "sales_unit": "PCS",
                          "remarks": "总账冒烟订单（reset 清理）"})
    so = r.json()["order_number"]
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": so, "quantity": 10})
    dk = r.json()["delivery_number"]
    client.post(f"/api/sd/deliveries/{dk}/ship", headers=H)

    # 1. 科目种子 8 个
    r = client.get("/api/finance/accounts")
    check("1.科目表 9 个一级科目（含本年利润 3131）", r.status_code == 200 and r.json()["total"] == 9,
          f"{r.status_code} total={r.json().get('total')}")

    # 2. 采购发票确认 → 自动分录 SUPPLIER_INVOICE_CONFIRMED
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po_number, "amount": round(cap * 0.8, 2)})
    pi1 = r.json()["invoice_number"]
    r = client.post(f"/api/purchase/supplier-invoices/{pi1}/confirm", headers=H)
    r = client.get("/api/finance/journal-entries", params={"source_type": "SUPPLIER_INVOICE_CONFIRMED"})
    entry = next((e for e in r.json().get("items", []) if e["source_ref"] == pi1), None)
    check("2.采购发票确认→分录 POSTED",
          r.status_code == 200 and entry is not None and entry["status"] == "POSTED",
          f"{r.status_code} entry={entry is not None}")

    # 3. 分录行 1405 借 / 2202 贷，金额=发票额
    if entry:
        detail = client.get(f"/api/finance/journal-entries/{entry['entry_number']}").json()
        l_debit = next((l for l in detail["lines"] if l["account_code"] == "1405"), None)
        l_credit = next((l for l in detail["lines"] if l["account_code"] == "2202"), None)
        check("3.分录科目与金额勾稽(1405/2202)",
              l_debit is not None and l_credit is not None
              and abs(l_debit["debit"] - round(cap * 0.8, 2)) < 0.01
              and abs(l_credit["credit"] - round(cap * 0.8, 2)) < 0.01,
              detail)
    else:
        check("3.分录科目与金额勾稽(1405/2202)", False, "no entry")

    # 4. 销售开票 issue → 分录 SALES_INVOICE_ISSUED（1122/6001）
    r = client.post("/api/sd/invoices", headers=H,
                    json={"sales_order_number": so, "delivery_number": dk, "amount": 255})
    inv1 = r.json()["invoice_number"]
    r = client.post(f"/api/sd/invoices/{inv1}/issue", headers=H)
    r = client.get("/api/finance/journal-entries", params={"source_type": "SALES_INVOICE_ISSUED"})
    entry = next((e for e in r.json().get("items", []) if e["source_ref"] == inv1), None)
    check("4.开票→分录 SALES_INVOICE_ISSUED",
          r.status_code == 200 and entry is not None,
          f"{r.status_code} entry={entry is not None}")

    # 5. 发货 → 分录 SALES_DELIVERY_SHIPPED（6401/1405，数量×标准成本）
    r = client.get("/api/finance/journal-entries", params={"source_type": "SALES_DELIVERY_SHIPPED"})
    entry = next((e for e in r.json().get("items", []) if e["source_ref"] == dk), None)
    check("5.发货→分录 SALES_DELIVERY_SHIPPED(标准成本)",
          std_cost > 0 and entry is not None,
          f"std={std_cost} entry={entry is not None}")

    # 6. 付款核销 → 分录 SUPPLIER_PAYMENT_PAID
    r = client.post("/api/purchase/payments", headers=H,
                    json={"supplier_id": supplier_id, "amount": 300})
    pay1 = r.json()["payment_number"]
    client.post(f"/api/purchase/payments/{pay1}/pay", headers=H,
                json={"allocations": [{"invoice_number": pi1, "allocated_amount": 300}]})
    r = client.get("/api/finance/journal-entries", params={"source_type": "SUPPLIER_PAYMENT_PAID"})
    entry = next((e for e in r.json().get("items", []) if e["source_ref"] == pay1), None)
    check("6.付款→分录 SUPPLIER_PAYMENT_PAID", entry is not None)

    # 7. 收款核销 → 分录 RECEIPT_PAID
    r = client.post("/api/sd/receipts", headers=H, json={"customer_id": customer_id, "amount": 255})
    rc1 = r.json()["receipt_number"]
    client.post(f"/api/sd/receipts/{rc1}/pay", headers=H,
                json={"allocations": [{"invoice_number": inv1, "allocated_amount": 255}]})
    r = client.get("/api/finance/journal-entries", params={"source_type": "RECEIPT_PAID"})
    entry = next((e for e in r.json().get("items", []) if e["source_ref"] == rc1), None)
    check("7.收款→分录 RECEIPT_PAID", entry is not None)

    # 8. 余额表：Σ借 = Σ贷 铁律
    r = client.get("/api/finance/trial-balance")
    tb = r.json()
    check("8.试算平衡 Σ借=Σ贷", r.status_code == 200 and tb["balanced"] is True
          and tb["total_debit"] == tb["total_credit"] and tb["total_debit"] > 0,
          f"debit={tb.get('total_debit')} credit={tb.get('total_credit')}")

    # 9. 余额表科目发生额：6001 贷 255、6401 借 10×标准成本
    row_6001 = next((x for x in tb["items"] if x["account_code"] == "6001"), None)
    row_6401 = next((x for x in tb["items"] if x["account_code"] == "6401"), None)
    check("9.科目发生额勾稽(6001/6401)",
          row_6001 is not None and abs(row_6001["credit_total"] - 255) < 0.01
          and row_6401 is not None and abs(row_6401["debit_total"] - round(10 * std_cost, 2)) < 0.01,
          f"6001={row_6001} 6401={row_6401}")

    # 10. 会计期间当月 OPEN
    r = client.get("/api/finance/periods")
    import datetime as _dt
    current = _dt.datetime.now().strftime("%Y-%m")
    row = next((x for x in r.json().get("items", []) if x["period_code"] == current), None)
    check("10.当月期间 OPEN", r.status_code == 200 and row is not None and row["status"] == "OPEN",
          f"period={row}")

    # 11. 领料 → MATERIAL_ISSUE 分录（数量×标准成本）
    db = SessionLocal()
    try:
        prod_order = (
            db.query(pp.ProductionOrder)
            .filter(pp.ProductionOrder.is_deleted.is_(False),
                    pp.ProductionOrder.status == pp.ProductionOrderStatus.IN_PRODUCTION)
            .order_by(pp.ProductionOrder.id)
            .first()
        )
        issue_order = prod_order.order_number if prod_order else None
        issue_material = prod_order.material_code if prod_order else None
        mat = db.query(mm.Material).filter(mm.Material.material_code == issue_material).first()
        issue_unit = mat.unit if mat else "PCS"
    finally:
        db.close()
    if issue_order:
        r = client.post("/api/mm/material-issues", headers=H,
                        json={"production_order_number": issue_order, "material_code": issue_material,
                              "quantity": 1, "unit": issue_unit, "remarks": "GL冒烟领料"})
        entries = client.get("/api/finance/journal-entries",
                             params={"source_type": "MATERIAL_ISSUE"}).json().get("items", [])
        check("11.领料→分录 MATERIAL_ISSUE", r.status_code == 201
              and any(e["source_ref"] == r.json().get("issue_number") for e in entries),
              f"{r.status_code} {r.text[:150]}")
    else:
        check("11.领料→分录 MATERIAL_ISSUE", False, "无 IN_PRODUCTION 工单")

    # 12. 盘点审批 → STOCK_ADJUST 分录
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": 9999})  # 大额盘盈，后续不审批业务姿势无所谓
    stk = r.json().get("stocktake_number")
    client.post(f"/api/mm/stocktakes/{stk}/approve", headers=H)
    entries = client.get("/api/finance/journal-entries",
                         params={"source_type": "STOCK_ADJUST"}).json().get("items", [])
    check("12.盘点→分录 STOCK_ADJUST", any(e["source_ref"] == stk for e in entries),
          f"entries={len(entries)}")

    # 13. 完工 → PRODUCTION_COMPLETE 分录
    r = client.post(f"/api/pp/production-orders/{issue_order}/complete", headers=H)
    entries = client.get("/api/finance/journal-entries",
                         params={"source_type": "PRODUCTION_COMPLETE"}).json().get("items", [])
    check("13.完工→分录 PRODUCTION_COMPLETE", r.status_code == 200
          and any(e["source_ref"] == issue_order for e in entries),
          f"{r.status_code} {r.text[:150]}")

    # 14. 三钩子入账后试算仍平衡
    tb2 = client.get("/api/finance/trial-balance").json()
    check("14.新增分录后试算平衡 Σ借=Σ贷",
          tb2["balanced"] is True and tb2["total_debit"] > tb["total_debit"],
          f"before={tb['total_debit']} after={tb2['total_debit']}")

    # 15. 凭证 source_ref 过滤（溯源跳转后端契约）
    seeded = client.get("/api/finance/journal-entries",
                        params={"source_type": "SALES_INVOICE_ISSUED"}).json().get("items", [])
    if seeded:
        ref = seeded[0]["source_ref"]
        hit = client.get("/api/finance/journal-entries", params={"source_ref": ref}).json()
        check("15.凭证 source_ref 过滤", hit.get("total", 0) >= 1
              and all(e["source_ref"] == ref for e in hit.get("items", [])),
              f"ref={ref} total={hit.get('total')}")
    else:
        check("15.凭证 source_ref 过滤", False, "无 SALES_INVOICE_ISSUED 凭证")

    # 16. 单据号过滤（溯源跳转落地契约）：种子发票 INV-20251231-0001
    hit = client.get("/api/sd/invoices", params={"invoice_number": "INV-20251231-0001"}).json()
    check("16.发票单号过滤", hit.get("total") == 1
          and hit["items"][0]["invoice_number"] == "INV-20251231-0001",
          f"total={hit.get('total')}")

    # 17-19. 月结流程：预览 → 结账（含损益结转分录）→ 反结账
    preview = client.get("/api/finance/month-end/preview",
                         params={"period_code": current}).json()
    check("17.月结预览试算平衡", preview["balanced"] is True
          and preview["period_status"] == "OPEN", str(preview)[:150])
    closed = client.post(f"/api/finance/periods/{current}/close", headers=H)
    tb3 = client.get("/api/finance/trial-balance").json()
    check("18.月结 CLOSED+结转后试算平衡",
          closed.status_code == 200 and closed.json().get("period_status") == "CLOSED"
          and tb3["balanced"] is True,
          f"{closed.status_code} {str(closed.json())[:120]}")
    reopened = client.post(f"/api/finance/periods/{current}/reopen", headers=H)
    check("19.反结账恢复 OPEN", reopened.status_code == 200
          and reopened.json().get("status") == "OPEN", f"{reopened.status_code} {reopened.text[:150]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
