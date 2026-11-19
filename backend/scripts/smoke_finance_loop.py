"""资金域全链路冒烟（P1）：三单匹配 → 付款核销 → AP 递减；收款核销 → 应收递减 → 账龄变化。

Run: python backend/scripts/smoke_finance_loop.py
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
    ReceivableEntry,
    SalesDelivery,
    SalesInvoice,
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


def _ap_supplier(supplier_id: str) -> dict | None:
    r = client.get("/api/purchase/ap-view")
    return next((x for x in r.json().get("items", []) if x["supplier_id"] == supplier_id), None)


def main() -> int:
    if _reset() != 0:
        print("起点 reset 失败，中止")
        return 1
    try:
        return _run()
    finally:
        print(f"reset_demo EXIT={_reset()}")


def _run() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    # ── 采购侧前置：RELEASED PO 整单收货 ──
    db = SessionLocal()
    try:
        po = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.is_deleted.is_(False),
                    PurchaseOrder.status == planning.PurchaseOrderStatus.RELEASED)
            .order_by(PurchaseOrder.id)
            .first()
        )
        assert po is not None, "前置：无 RELEASED 采购单"
        po_number, supplier_id = po.purchase_order_number, po.supplier_id
    finally:
        db.close()
    r = client.get(f"/api/purchase/purchase-orders/{po_number}")
    lines = [{"line_number": ln["line_number"], "quantity": ln["outstanding_quantity"]}
             for ln in r.json()["lines"] if ln["outstanding_quantity"] > 0]
    r = client.post(f"/api/purchase/purchase-orders/{po_number}/receive", json={"lines": lines}, headers=H)
    assert r.status_code == 200, f"前置收货失败 {r.text[:150]}"
    db = SessionLocal()
    try:
        po_lines = db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.purchase_order_number == po_number).all()
        cap = sum(float(l.received_quantity or 0) * float(l.unit_price or 0) for l in po_lines)
    finally:
        db.close()

    # ── 销售侧前置：订单→发货→开票→issue ──
    db = SessionLocal()
    try:
        cust = db.query(sd.Customer).order_by(sd.Customer.id).first()
        customer_id = cust.customer_id if cust else "CUST-HF001"
    finally:
        db.close()
    r = client.post("/api/sd/sales-orders", headers=H,
                    json={"customer_id": customer_id, "product_number": "PN-FIN-SMOKE",
                          "quantity": 20, "unit_price": 25.5,
                          "delivery_date": "2026-02-10T00:00:00",
                          "material_code": MATERIAL, "sales_unit": "PCS",
                          "remarks": "资金冒烟订单（reset 清理）"})
    assert r.status_code == 201, "前置销售订单失败"
    so = r.json()["order_number"]
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": so, "quantity": 20})
    dk = r.json()["delivery_number"]
    client.post(f"/api/sd/deliveries/{dk}/ship", headers=H)
    r = client.post("/api/sd/invoices", headers=H,
                    json={"sales_order_number": so, "delivery_number": dk, "amount": 510})
    assert r.status_code == 201, "前置销售发票失败"
    inv1 = r.json()["invoice_number"]
    client.post(f"/api/sd/invoices/{inv1}/issue", headers=H)

    # 1. 采购发票创建 201/PI/DRAFT
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po_number, "amount": round(cap * 0.8, 2)})
    check("1.采购发票创建 201/DRAFT/PI 前缀",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["invoice_number"].startswith("PI-"),
          f"{r.status_code} {r.text[:200]}")
    pi1 = r.json()["invoice_number"]

    # 2. 三单匹配：超匹配 400
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po_number, "amount": round(cap * 1.5, 2)})
    check("2.三单匹配(超匹配) 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 3. confirm → CONFIRMED；AP 视图出现已确认发票
    r = client.post(f"/api/purchase/supplier-invoices/{pi1}/confirm", headers=H)
    ap_after_confirm = _ap_supplier(supplier_id)
    check("3.confirm→CONFIRMED+AP 已确认口径",
          r.status_code == 200 and r.json()["status"] == "CONFIRMED"
          and ap_after_confirm is not None
          and ap_after_confirm["confirmed_invoice_amount"] == round(cap * 0.8, 2),
          f"{r.status_code} ap={ap_after_confirm}")

    # 4. 付款创建 201/PAY/DRAFT
    r = client.post("/api/purchase/payments", headers=H,
                    json={"supplier_id": supplier_id, "amount": 400, "method": "TRANSFER"})
    check("4.付款创建 201/PAY/DRAFT",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["payment_number"].startswith("PAY-"),
          f"{r.status_code} {r.text[:200]}")
    pay1 = r.json()["payment_number"]

    # 5. 付款核销 → PAID + AP 递减（open = 0.8cap − 300）
    r = client.post(f"/api/purchase/payments/{pay1}/pay", headers=H,
                    json={"allocations": [{"invoice_number": pi1, "allocated_amount": 300}]})
    ap_after_pay = _ap_supplier(supplier_id)
    check("5.付款核销→PAID+AP 递减",
          r.status_code == 200 and r.json()["status"] == "PAID"
          and ap_after_pay is not None
          and ap_after_pay["paid_amount"] == 300
          and ap_after_pay["open_invoice_amount"] == round(cap * 0.8, 2) - 300,
          f"{r.status_code} ap={ap_after_pay}")

    # 6. 核销超发票额 400
    r = client.post("/api/purchase/payments", headers=H, json={"supplier_id": supplier_id, "amount": 5000})
    pay2 = r.json()["payment_number"]
    r = client.post(f"/api/purchase/payments/{pay2}/allocate", headers=H,
                    json={"invoice_number": pi1, "allocated_amount": 99999})
    check("6.核销超发票额 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 7. 重复 confirm 400（状态机）
    r = client.post(f"/api/purchase/supplier-invoices/{pi1}/confirm", headers=H)
    check("7.重复 confirm 400", r.status_code == 400, f"{r.status_code}")

    # 8. 收款创建 201/RC/DRAFT
    r = client.post("/api/sd/receipts", headers=H,
                    json={"customer_id": customer_id, "amount": 510, "method": "TRANSFER"})
    check("8.收款创建 201/RC/DRAFT",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["receipt_number"].startswith("RC-"),
          f"{r.status_code} {r.text[:200]}")
    rc1 = r.json()["receipt_number"]

    # 9. 部分核销 → 发票 PARTIALLY_PAID + AR RECEIPT 负流水
    r = client.post(f"/api/sd/receipts/{rc1}/pay", headers=H,
                    json={"allocations": [{"invoice_number": inv1, "allocated_amount": 300}]})
    db = SessionLocal()
    try:
        inv_row = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == inv1).first()
        ar = db.query(ReceivableEntry).filter(
            ReceivableEntry.reference_number == rc1,
            ReceivableEntry.entry_type == planning.ReceivableEntryType.RECEIPT).first()
    finally:
        db.close()
    check("9.收款部分核销→PARTIALLY_PAID+AR 流水",
          r.status_code == 200 and inv_row is not None and inv_row.status.value == "PARTIALLY_PAID"
          and float(inv_row.received_amount or 0) == 300
          and ar is not None and float(ar.amount) == -300,
          f"{r.status_code} inv={'None' if inv_row is None else inv_row.status.value}")

    # 10. 超收核销 400
    r = client.post("/api/sd/receipts", headers=H, json={"customer_id": customer_id, "amount": 500})
    rc2 = r.json()["receipt_number"]
    r = client.post(f"/api/sd/receipts/{rc2}/pay", headers=H,
                    json={"allocations": [{"invoice_number": inv1, "allocated_amount": 999}]})
    check("10.超收核销 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 11. 账龄变化：部分核销后未收余额所在桶递减（此处均为 d90p：到期日 2026-02-10 已过 90+ 天）
    r = client.get("/api/sd/receivables")
    row = next((x for x in r.json().get("items", []) if x["customer_id"] == customer_id), None)
    check("11.应收台账反映核销",
          r.status_code == 200 and row is not None
          and row["received_amount"] >= 300 and row["outstanding_amount"] < row["invoiced_amount"],
          f"{r.status_code} row={row}")

    # 12. 补足核销 → 发票 PAID
    r = client.post(f"/api/sd/receipts/{rc2}/pay", headers=H,
                    json={"allocations": [{"invoice_number": inv1, "allocated_amount": 210}]})
    db = SessionLocal()
    try:
        inv_row = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == inv1).first()
    finally:
        db.close()
    check("12.补足核销→发票 PAID",
          r.status_code == 200 and inv_row is not None and inv_row.status.value == "PAID",
          f"{r.status_code} inv={'None' if inv_row is None else inv_row.status.value}")

    # 13. 账龄变化：发票全额核销后，其未收余额从账龄桶移除（d90p 桶不含有该发票的 510）
    r = client.get("/api/sd/receivables")
    row2 = next((x for x in r.json().get("items", []) if x["customer_id"] == customer_id), None)
    aged_out = row2 is not None and abs(
        (row2["aging"]["d90p"] + row2["aging"]["d90"] + row2["aging"]["d60"]
         + row2["aging"]["d30"] + row2["aging"]["current"]) - row2["outstanding_amount"]
    ) < 0.01
    check("13.账龄分桶与未收余额勾稽", aged_out and row2 is not None
          and row2["outstanding_amount"] < row["outstanding_amount"],
          f"before={row and row['outstanding_amount']} after={row2 and row2['outstanding_amount']}")

    # 14. 重复支付付款单 400（状态机）
    r = client.post(f"/api/purchase/payments/{pay1}/pay", headers=H,
                    json={"allocations": []})
    check("14.重复支付付款单 400", r.status_code == 400, f"{r.status_code}")

    # 15. reset 复位：资金域种子基线（无 P1 种子 → 5 新表清空，销售域回到 2/1/1）
    after_reset = _reset()
    db = SessionLocal()
    try:
        counts = (
            db.query(planning.SupplierInvoice).count(),
            db.query(planning.SupplierPayment).count(),
            db.query(planning.PaymentAllocation).count(),
            db.query(planning.Receipt).count(),
            db.query(planning.ReceiptAllocation).count(),
            db.query(SalesDelivery).count(),
        )
    finally:
        db.close()
    check("15.reset 复位（资金表清空+销售域基线）",
          after_reset == 0 and counts[:5] == (0, 0, 0, 0, 0) and counts[5] == 2,
          f"reset={after_reset} counts={counts}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 资金域全链路冒烟：{passed}/{len(CHECKS)} 通过 =====")
    return 0 if passed == len(CHECKS) and len(CHECKS) >= 14 else 1


if __name__ == "__main__":
    sys.exit(main())
