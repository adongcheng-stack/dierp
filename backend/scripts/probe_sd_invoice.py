"""一次性行为探针：销售发票 + 应收台账（T105）。

6 断言：创建 DRAFT（挂已发货单）→ 超开 400 → 挂未 SHIPPED 发货单 400
→ issue（ISSUED + AR 流水金额勾稽）→ 重复 issue 400 → receivables 聚合。

Run: python backend/scripts/probe_sd_invoice.py
（TestClient 驱动；结束后自动 reset_demo 恢复基线）
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
from backend.common.models import eng, mm, sd, planning  # noqa: E402,F401
from backend.common.models.planning import ReceivableEntry  # noqa: E402

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []

MATERIAL = "HF1004ENIGAB01"


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail if not cond else ''}")


def _ar_entry(invoice_number: str) -> ReceivableEntry | None:
    db = SessionLocal()
    try:
        return (
            db.query(ReceivableEntry)
            .filter(
                ReceivableEntry.invoice_number == invoice_number,
                ReceivableEntry.entry_type == planning.ReceivableEntryType.INVOICE,
            )
            .first()
        )
    finally:
        db.close()


def main() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        cust = db.query(sd.Customer).order_by(sd.Customer.id).first()
        customer_id = cust.customer_id if cust else "CUST-HF001"
    finally:
        db.close()

    # 前置：订单1（20×25.5=510 可开票上限）+ 发货单已 SHIPPED；订单2 仅 DRAFT 发货单
    def _make_order(product: str, qty: float) -> str:
        r = client.post(
            "/api/sd/sales-orders",
            headers=H,
            json={
                "customer_id": customer_id,
                "product_number": product,
                "quantity": qty,
                "unit_price": 25.5,
                "delivery_date": "2026-02-10T00:00:00",
                "material_code": MATERIAL,
                "sales_unit": "PCS",
                "remarks": "发票探针专用订单（reset 清理）",
            },
        )
        assert r.status_code == 201, f"探针前置：创建订单失败 {r.status_code} {r.text[:200]}"
        return r.json()["order_number"]

    order1 = _make_order("PN-PROBE-INV1", 20)
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order1, "quantity": 20})
    dk1 = r.json()["delivery_number"]
    r = client.post(f"/api/sd/deliveries/{dk1}/ship", headers=H)
    assert r.status_code == 200, f"探针前置：ship 失败 {r.text[:200]}"

    # 1. 创建发票 DRAFT（INV 前缀，挂已 SHIPPED 发货单）
    r = client.post(
        "/api/sd/invoices",
        headers=H,
        json={"sales_order_number": order1, "delivery_number": dk1,
              "amount": 300, "remarks": "发票探针-首张"},
    )
    check("1.创建发票 201/DRAFT/INV 前缀",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["invoice_number"].startswith("INV-"),
          f"{r.status_code} {r.text[:200]}")
    inv1 = r.json()["invoice_number"]

    # 2. 超开 400（已开 300 + 300 = 600 > 上限 510）
    r = client.post("/api/sd/invoices", headers=H,
                    json={"sales_order_number": order1, "amount": 300})
    check("2.超开校验 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

    # 3. 挂未 SHIPPED 发货单 400（订单2 的 DRAFT 发货单）
    order2 = _make_order("PN-PROBE-INV2", 10)
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order2, "quantity": 10})
    dk2 = r.json()["delivery_number"]
    r = client.post("/api/sd/invoices", headers=H,
                    json={"sales_order_number": order2, "delivery_number": dk2, "amount": 100})
    check("3.未发货开票 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

    # 4. issue → ISSUED + AR 流水（INVOICE 正金额 300，ref=INV1）
    r = client.post(f"/api/sd/invoices/{inv1}/issue", headers=H)
    ar = _ar_entry(inv1)
    check("4.issue→ISSUED+AR 流水",
          r.status_code == 200 and r.json()["status"] == "ISSUED"
          and ar is not None and float(ar.amount) == 300
          and ar.entry_number.startswith("AR-"),
          f"{r.status_code} ar={'None' if ar is None else float(ar.amount)}")

    # 5. 重复 issue 400
    r = client.post(f"/api/sd/invoices/{inv1}/issue", headers=H)
    check("5.重复 issue 400", r.status_code == 400, f"{r.status_code}")

    # 6. receivables 聚合：该客户 invoiced/outstanding ≥ 300 且含账龄结构
    r = client.get("/api/sd/receivables", headers=H)
    rows = {x["customer_id"]: x for x in r.json()["items"]}
    row = rows.get(customer_id)
    check("6.receivables 聚合",
          r.status_code == 200 and row is not None
          and row["invoiced_amount"] >= 300 and row["outstanding_amount"] >= 300
          and "aging" in row,
          f"{r.status_code} row={'None' if row is None else row.get('invoiced_amount')}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 发票应收探针：{passed}/{len(CHECKS)} 通过 =====")
    reset = subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(f"reset_demo EXIT={reset.returncode}")
    return 0 if passed == len(CHECKS) == 6 and reset.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
