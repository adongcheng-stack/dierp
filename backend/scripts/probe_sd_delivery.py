"""一次性行为探针：发货单域（T104）。

8 断言：创建 DRAFT → 超发 400 → ship（库存扣+SALES_ISSUE 流水+订单联动 SHIPPED）
→ deliver（签收+订单 DELIVERED）→ ship+cancel 红字冲回 → 非法流转 400。

Run: python backend/scripts/probe_sd_delivery.py
（TestClient 驱动；结束后自动 reset_demo 恢复基线）
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
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
from backend.common.models.sd import SalesOrder  # noqa: E402
from backend.common.models.planning import SalesDelivery  # noqa: E402

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []

MATERIAL = "HF1004ENIGAB01"
ORDER_QTY = 50.0


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


def main() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    # 前置：探针自建销售订单（可全量发货），客户取库内任一客户
    db = SessionLocal()
    try:
        cust = db.query(sd.Customer).order_by(sd.Customer.id).first()
        customer_id = cust.customer_id if cust else "CUST-HF001"
    finally:
        db.close()
    r = client.post(
        "/api/sd/sales-orders",
        headers=H,
        json={
            "customer_id": customer_id,
            "product_number": "PN-PROBE-SD01",
            "quantity": ORDER_QTY,
            "unit_price": 25.5,
            "delivery_date": "2026-02-10T00:00:00",
            "material_code": MATERIAL,
            "sales_unit": "PCS",
            "remarks": "探针专用订单（备注标记，reset 清理）",
        },
    )
    assert r.status_code == 201, f"探针前置：创建销售订单失败 {r.status_code} {r.text}"
    order_number = r.json()["order_number"]
    stock0 = _stock(MATERIAL)

    # 1. 创建发货单 DRAFT（DK 前缀）
    r = client.post(
        "/api/sd/deliveries",
        headers=H,
        json={"sales_order_number": order_number, "quantity": 20, "remarks": "探针-首张"},
    )
    check("1.创建发货单 201/DRAFT/DK 前缀",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["delivery_number"].startswith("DK-"),
          f"{r.status_code} {r.text[:200]}")
    dk1 = r.json()["delivery_number"]

    # 2. 超发 400（20+20=40，再发 20 → Σ60 > 50）
    client.post("/api/sd/deliveries", headers=H,
                json={"sales_order_number": order_number, "quantity": 20})
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order_number, "quantity": 20})
    check("2.超发校验 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

    # 3. ship 扣库存（DK1：20 → 库存差 = 20）
    r = client.post(f"/api/sd/deliveries/{dk1}/ship", headers=H)
    stock1 = _stock(MATERIAL)
    check("3.ship 扣库存", r.status_code == 200 and abs(stock0 - stock1 - 20) < 1e-6,
          f"{r.status_code} stock {stock0}->{stock1}")

    # 4. SALES_ISSUE 流水（ref=DK1，数量 -20）
    t = _txn("SALES_ISSUE", dk1)
    check("4.SALES_ISSUE 流水", t is not None and float(t.quantity) == -20,
          "no txn" if t is None else f"qty={t.quantity}")

    # 5. 全量发货联动：补一张 10（Σ=50 达到订单量）→ 全部 ship → 订单 SHIPPED
    client.post("/api/sd/deliveries", headers=H,
                json={"sales_order_number": order_number, "quantity": 10})
    list_r = client.get("/api/sd/deliveries", params={"order_number": order_number}, headers=H).json()
    others = [i["delivery_number"] for i in list_r["items"] if i["delivery_number"] != dk1]
    for n in others:
        client.post(f"/api/sd/deliveries/{n}/ship", headers=H)
    check("5.全量发货→订单 SHIPPED", _order_status(order_number) == "SHIPPED",
          _order_status(order_number))

    # 6. 全部签收 → 订单 DELIVERED（单据签收含在内）
    r = client.post(f"/api/sd/deliveries/{dk1}/deliver", headers=H)
    delivered_self = r.status_code == 200 and r.json()["status"] == "DELIVERED"
    for n in others:
        client.post(f"/api/sd/deliveries/{n}/deliver", headers=H)
    check("6.全量签收→订单 DELIVERED", delivered_self and _order_status(order_number) == "DELIVERED",
          _order_status(order_number))

    # 7. 红字冲回：新订单+发货+作废 → 库存回补 + REVERSE 流水
    r = client.post(
        "/api/sd/sales-orders",
        headers=H,
        json={
            "customer_id": customer_id,
            "product_number": "PN-PROBE-SD02",
            "quantity": 10,
            "unit_price": 25.5,
            "delivery_date": "2026-02-10T00:00:00",
            "material_code": MATERIAL,
            "sales_unit": "PCS",
            "remarks": "探针专用订单2（备注标记，reset 清理）",
        },
    )
    assert r.status_code == 201, f"探针前置2：创建订单失败 {r.text[:200]}"
    order2 = r.json()["order_number"]
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order2, "quantity": 10})
    dk2 = r.json()["delivery_number"]
    client.post(f"/api/sd/deliveries/{dk2}/ship", headers=H)
    stock_before_cancel = _stock(MATERIAL)
    r = client.post(f"/api/sd/deliveries/{dk2}/cancel", headers=H)
    t2 = _txn("SALES_ISSUE_REVERSE", dk2)
    check("7.作废红字冲回",
          r.status_code == 200 and r.json()["status"] == "CANCELLED"
          and abs(_stock(MATERIAL) - stock_before_cancel - 10) < 1e-6
          and t2 is not None and float(t2.quantity) == 10,
          f"{r.status_code} stock {_stock(MATERIAL)}")

    # 8. 非法流转：DRAFT 直接 deliver → 400
    r = client.post("/api/sd/deliveries", headers=H,
                    json={"sales_order_number": order2, "quantity": 5})
    dk3 = r.json()["delivery_number"]
    r = client.post(f"/api/sd/deliveries/{dk3}/deliver", headers=H)
    check("8.非法流转 DRAFT→deliver 400", r.status_code == 400, f"{r.status_code}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 发货单探针：{passed}/{len(CHECKS)} 通过 =====")
    reset = subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(f"reset_demo EXIT={reset.returncode}")
    return 0 if passed == len(CHECKS) == 8 and reset.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
