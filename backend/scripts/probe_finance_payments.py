"""一次性行为探针：付款/收款核销 + AP/AR 视图口径（T204）。

8 断言：付款创建 → 核销 PAID → 超发票额 400 → 收款创建 → 收款核销（发票 PARTIALLY_PAID+AR RECEIPT 负流水）
→ 超收核销 400 → 补足核销→发票 PAID → ap-view 新口径 + receivables 递减。

Run: python backend/scripts/probe_finance_payments.py
（TestClient 驱动；起点+终点双 reset）
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
    PaymentAllocation,
    PurchaseOrder,
    PurchaseOrderLine,
    ReceivableEntry,
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


def _ar(entry_type: str, ref: str) -> ReceivableEntry | None:
    db = SessionLocal()
    try:
        return (
            db.query(ReceivableEntry)
            .filter(ReceivableEntry.entry_type == getattr(planning.ReceivableEntryType, entry_type),
                    ReceivableEntry.reference_number == ref)
            .first()
        )
    finally:
        db.close()


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

    # ── 采购侧前置：收货 + 采购发票确认 ──
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
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po_number, "amount": round(cap * 0.8, 2)})
    assert r.status_code == 201, f"前置采购发票失败 {r.text[:150]}"
    pi1 = r.json()["invoice_number"]
    r = client.post(f"/api/purchase/supplier-invoices/{pi1}/confirm", headers=H)
    assert r.status_code == 200, "前置确认失败"

    # ── 销售侧前置：订单→发货→开票→issue ──
    db = SessionLocal()
    try:
        cust = db.query(sd.Customer).order_by(sd.Customer.id).first()
        customer_id = cust.customer_id if cust else "CUST-HF001"
    finally:
        db.close()
    r = client.post("/api/sd/sales-orders", headers=H,
                    json={"customer_id": customer_id, "product_number": "PN-FIN-01",
                          "quantity": 20, "unit_price": 25.5,
                          "delivery_date": "2026-02-10T00:00:00",
                          "material_code": MATERIAL, "sales_unit": "PCS",
                          "remarks": "资金探针订单（reset 清理）"})
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

    # 1. 付款单创建 201/PAY/DRAFT
    r = client.post("/api/purchase/payments", headers=H,
                    json={"supplier_id": supplier_id, "amount": 400, "method": "TRANSFER",
                          "remarks": "资金探针"})
    check("1.付款单创建 201/PAY/DRAFT",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["payment_number"].startswith("PAY-"),
          f"{r.status_code} {r.text[:200]}")
    pay1 = r.json()["payment_number"]

    # 2. 核销支付 → PAID + 核销明细
    r = client.post(f"/api/purchase/payments/{pay1}/pay", headers=H,
                    json={"allocations": [{"invoice_number": pi1, "allocated_amount": 300}]})
    detail = client.get(f"/api/purchase/payments/{pay1}").json()
    check("2.付款核销→PAID+明细",
          r.status_code == 200 and r.json()["status"] == "PAID"
          and detail.get("allocated_amount") == 300
          and any(a["invoice_number"] == pi1 for a in detail.get("allocations", [])),
          f"{r.status_code} {r.text[:200]}")

    # 3. 核销超发票额 400
    r = client.post("/api/purchase/payments", headers=H,
                    json={"supplier_id": supplier_id, "amount": 5000})
    pay2 = r.json()["payment_number"]
    r = client.post(f"/api/purchase/payments/{pay2}/allocate", headers=H,
                    json={"invoice_number": pi1, "allocated_amount": 99999})
    check("3.核销超发票额 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 4. 收款单创建 201/RC/DRAFT
    r = client.post("/api/sd/receipts", headers=H,
                    json={"customer_id": customer_id, "amount": 510, "method": "TRANSFER",
                          "remarks": "资金探针"})
    check("4.收款单创建 201/RC/DRAFT",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["receipt_number"].startswith("RC-"),
          f"{r.status_code} {r.text[:200]}")
    rc1 = r.json()["receipt_number"]

    # 5. 收款核销 → 发票 PARTIALLY_PAID + AR RECEIPT 负流水
    r = client.post(f"/api/sd/receipts/{rc1}/pay", headers=H,
                    json={"allocations": [{"invoice_number": inv1, "allocated_amount": 300}]})
    db = SessionLocal()
    try:
        inv_row = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == inv1).first()
        ar = _ar("RECEIPT", rc1)
    finally:
        db.close()
    check("5.收款核销→发票PARTIALLY_PAID+AR流水",
          r.status_code == 200 and r.json()["status"] == "PAID"
          and inv_row is not None and inv_row.status.value == "PARTIALLY_PAID"
          and float(inv_row.received_amount or 0) == 300
          and ar is not None and float(ar.amount) == -300,
          f"{r.status_code} inv={'None' if inv_row is None else inv_row.status.value}")

    # 6. 超收核销 400
    r = client.post("/api/sd/receipts", headers=H, json={"customer_id": customer_id, "amount": 500})
    rc2 = r.json()["receipt_number"]
    r = client.post(f"/api/sd/receipts/{rc2}/pay", headers=H,
                    json={"allocations": [{"invoice_number": inv1, "allocated_amount": 999}]})
    check("6.超收核销 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 7. 补足核销 → 发票 PAID
    r = client.post(f"/api/sd/receipts/{rc2}/pay", headers=H,
                    json={"allocations": [{"invoice_number": inv1, "allocated_amount": 210}]})
    db = SessionLocal()
    try:
        inv_row = db.query(SalesInvoice).filter(SalesInvoice.invoice_number == inv1).first()
    finally:
        db.close()
    check("7.补足核销→发票PAID",
          r.status_code == 200 and inv_row is not None and inv_row.status.value == "PAID",
          f"{r.status_code} inv={'None' if inv_row is None else inv_row.status.value}")

    # 8. ap-view 新口径 + receivables 递减
    r = client.get("/api/purchase/ap-view", headers=H)
    ap_row = next((x for x in r.json().get("items", []) if x["supplier_id"] == supplier_id), None)
    recv = client.get("/api/sd/receivables", headers=H).json()
    ar_row = next((x for x in recv.get("items", []) if x["customer_id"] == customer_id), None)
    check("8.AP新口径+应收递减",
          r.status_code == 200 and ap_row is not None
          and ap_row["confirmed_invoice_amount"] == round(cap * 0.8, 2)
          and ap_row["paid_amount"] == 300
          and ap_row["open_invoice_amount"] == round(cap * 0.8, 2) - 300
          and ar_row is not None and ar_row["received_amount"] >= 510,
          f"ap={JSON(ap_row)} ar={JSON(ar_row)}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 资金核销探针：{passed}/{len(CHECKS)} 通过 =====")
    return 0 if passed == len(CHECKS) == 8 else 1


def JSON(x) -> str:
    import json
    return json.dumps(x, ensure_ascii=False)[:200]


if __name__ == "__main__":
    sys.exit(main())
