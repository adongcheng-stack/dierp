"""销售域三线打通冒烟：发货单 → 出库/流水/订单联动 → 签收 → 开票 → 应收。

Run: python backend/scripts/smoke_sd_delivery.py
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
from backend.common.models.mm import Material, MaterialTransaction  # noqa: E402
from backend.common.models.planning import ReceivableEntry, SalesDelivery, SalesInvoice  # noqa: E402
from backend.common.models.sd import SalesOrder  # noqa: E402

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []

MATERIAL = "HF1004ENIGAB01"


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail if not cond else ''}")


def _stock(code: str) -> float:
    db = SessionLocal()
    try:
        row = db.query(Material).filter(Material.material_code == code).first()
        return float(row.current_stock or 0) if row else 0.0
    finally:
        db.close()


def _order_status(order_number: str) -> str | None:
    db = SessionLocal()
    try:
        row = db.query(SalesOrder).filter(SalesOrder.order_number == order_number).first()
        return row.status.value if row and row.status else None
    finally:
        db.close()


def _txn(type_: str, ref: str) -> MaterialTransaction | None:
    db = SessionLocal()
    try:
        return (
            db.query(MaterialTransaction)
            .filter(
                MaterialTransaction.transaction_type == type_,
                MaterialTransaction.reference_number == ref,
            )
            .first()
        )
    finally:
        db.close()


def _counts() -> tuple[int, int, int]:
    db = SessionLocal()
    try:
        return (
            db.query(SalesDelivery).count(),
            db.query(SalesInvoice).count(),
            db.query(ReceivableEntry).count(),
        )
    finally:
        db.close()


def _reset() -> int:
    reset = subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return reset.returncode


def main() -> int:
    # 起点先复位：上次崩溃的残留不影响本次断言
    if _reset() != 0:
        print("起点 reset 失败，中止")
        return 1
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

    # 前置：自建可全量发货的订单（不依赖种子数据），并记录基线计数
    r = client.post(
        "/api/sd/sales-orders",
        headers=H,
        json={
            "customer_id": customer_id,
            "product_number": "PN-SMOKE-SD01",
            "quantity": 50,
            "unit_price": 25.5,
            "delivery_date": "2026-02-10T00:00:00",
            "material_code": MATERIAL,
            "sales_unit": "PCS",
            "remarks": "销售域冒烟专用订单（备注标记，reset 清理）",
        },
    )
    assert r.status_code == 201, f"冒烟前置：创建销售订单失败 {r.status_code} {r.text[:200]}"
    order_number = r.json()["order_number"]
    stock0 = _stock(MATERIAL)
    base_counts = _counts()  # reset 后应为种子基线 (2, 1, 1)

    try:
        return _run(H, order_number, stock0, base_counts, customer_id)
    finally:
        # 无论成败都复位，避免污染后续门禁
        rc = _reset()
        print(f"reset_demo EXIT={rc}")


def _run(H: dict, order_number: str, stock0: float, base_counts: tuple, customer_id: str) -> int:

    # 1. 创建发货单 DRAFT（DK 前缀）
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order_number, "quantity": 20, "remarks": "冒烟-首张"})
    check("1.创建发货单 201/DRAFT/DK 前缀",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["delivery_number"].startswith("DK-"),
          f"{r.status_code} {r.text[:200]}")
    dk1 = r.json()["delivery_number"]

    # 2. 超发 400（20+20+20=60 > 50）
    client.post("/api/sd/deliveries", headers=H,
                json={"sales_order_number": order_number, "quantity": 20})
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order_number, "quantity": 20})
    check("2.超发校验 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

    # 3. ship 扣库存
    r = client.post(f"/api/sd/deliveries/{dk1}/ship", headers=H)
    check("3.ship 扣库存", r.status_code == 200 and abs(stock0 - _stock(MATERIAL) - 20) < 1e-6,
          f"{r.status_code} stock {stock0}->{_stock(MATERIAL)}")

    # 4. SALES_ISSUE 流水（数量 -20）
    t = _txn("SALES_ISSUE", dk1)
    check("4.SALES_ISSUE 流水", t is not None and float(t.quantity) == -20,
          "no txn" if t is None else f"qty={t.quantity}")

    # 5. 补一张 10 凑满 50 → 全量 ship → 订单 SHIPPED
    client.post("/api/sd/deliveries", headers=H,
                json={"sales_order_number": order_number, "quantity": 10})
    list_r = client.get("/api/sd/deliveries", params={"order_number": order_number}, headers=H).json()
    others = [i["delivery_number"] for i in list_r["items"] if i["delivery_number"] != dk1]
    for n in others:
        client.post(f"/api/sd/deliveries/{n}/ship", headers=H)
    check("5.全量发货→订单 SHIPPED", _order_status(order_number) == "SHIPPED",
          _order_status(order_number))

    # 6. 签收 DELIVERED
    r = client.post(f"/api/sd/deliveries/{dk1}/deliver", headers=H)
    check("6.签收 DELIVERED", r.status_code == 200 and r.json()["status"] == "DELIVERED",
          f"{r.status_code} {r.text[:200]}")

    # 7. 全量签收 → 订单 DELIVERED
    for n in others:
        client.post(f"/api/sd/deliveries/{n}/deliver", headers=H)
    check("7.全量签收→订单 DELIVERED", _order_status(order_number) == "DELIVERED",
          _order_status(order_number))

    # 8. 开票创建 201/INV（挂 dk1，金额 ≤ 上限 50×25.5=1275）
    r = client.post("/api/sd/invoices", headers=H,
                    json={"sales_order_number": order_number, "delivery_number": dk1,
                          "amount": 1000, "remarks": "冒烟-发票"})
    check("8.创建发票 201/DRAFT/INV 前缀",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["invoice_number"].startswith("INV-"),
          f"{r.status_code} {r.text[:200]}")
    inv1 = r.json()["invoice_number"]

    # 9. 超开 400（已开 1000 + 400 = 1400 > 1275）
    r = client.post("/api/sd/invoices", headers=H,
                    json={"sales_order_number": order_number, "amount": 400})
    check("9.超开校验 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

    # 10. issue → ISSUED + AR 流水（INVOICE 1000）
    r = client.post(f"/api/sd/invoices/{inv1}/issue", headers=H)
    db = SessionLocal()
    try:
        ar = db.query(ReceivableEntry).filter(ReceivableEntry.invoice_number == inv1).first()
    finally:
        db.close()
    check("10.issue→ISSUED+AR 流水",
          r.status_code == 200 and r.json()["status"] == "ISSUED"
          and ar is not None and float(ar.amount) == 1000
          and ar.entry_number.startswith("AR-"),
          f"{r.status_code} ar={'None' if ar is None else float(ar.amount)}")

    # 11. receivables 应收出现（该客户 outstanding ≥ 1000）
    r = client.get("/api/sd/receivables", headers=H)
    row = next((x for x in r.json().get("items", []) if x["customer_id"] == customer_id), None)
    check("11.应收台账出现该客户", r.status_code == 200 and row is not None
          and row["outstanding_amount"] >= 1000,
          f"{r.status_code} row={'None' if row is None else row.get('outstanding_amount')}")

    # 12. 非法流转：DRAFT 直接 deliver → 400（用第二张订单，订单 1 已全量发货）
    r = client.post(
        "/api/sd/sales-orders",
        headers=H,
        json={
            "customer_id": customer_id,
            "product_number": "PN-SMOKE-SD02",
            "quantity": 10,
            "unit_price": 25.5,
            "delivery_date": "2026-02-10T00:00:00",
            "material_code": MATERIAL,
            "sales_unit": "PCS",
            "remarks": "销售域冒烟专用订单2（备注标记，reset 清理）",
        },
    )
    assert r.status_code == 201, f"冒烟前置2：创建订单失败 {r.text[:200]}"
    order2 = r.json()["order_number"]
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order2, "quantity": 5})
    dk3 = r.json()["delivery_number"]
    r = client.post(f"/api/sd/deliveries/{dk3}/deliver", headers=H)
    check("12.非法流转 DRAFT→deliver 400", r.status_code == 400, f"{r.status_code}")

    # 13. 红字冲回：ship 后 cancel → 库存回补 + REVERSE 流水
    r = client.post(f"/api/sd/deliveries/{dk3}/ship", headers=H)
    stock_before = _stock(MATERIAL)
    r = client.post(f"/api/sd/deliveries/{dk3}/cancel", headers=H)
    t3 = _txn("SALES_ISSUE_REVERSE", dk3)
    check("13.作废红字冲回",
          r.status_code == 200 and r.json()["status"] == "CANCELLED"
          and abs(_stock(MATERIAL) - stock_before - 5) < 1e-6
          and t3 is not None and float(t3.quantity) == 5,
          f"{r.status_code} stock {_stock(MATERIAL)}")

    # 14. reset 复位：回到种子基线 (2, 1, 1)
    reset = subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    after = _counts()
    check("14.reset 复位基线 (2,1,1)",
          reset.returncode == 0 and after == (2, 1, 1) == base_counts,
          f"reset={reset.returncode} counts={after} base={base_counts}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 销售域冒烟：{passed}/{len(CHECKS)} 通过 =====")
    return 0 if passed == len(CHECKS) and len(CHECKS) >= 12 and reset.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
