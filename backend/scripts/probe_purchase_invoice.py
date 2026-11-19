"""一次性行为探针：采购发票三单匹配（T203）。

6 断言：收货前置 → 创建 201/PI/DRAFT → 超匹配 400 → confirm CONFIRMED
→ 重复 confirm 400 → 未收货 PO 创建 400。

Run: python backend/scripts/probe_purchase_invoice.py
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
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.common.models.planning import (  # noqa: E402
    PurchaseOrder,
    PurchaseOrderLine,
)

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail if not cond else ''}")


def _pick_po(db) -> PurchaseOrder | None:
    return (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.is_deleted.is_(False), PurchaseOrder.status == planning.PurchaseOrderStatus.RELEASED)
        .order_by(PurchaseOrder.id)
        .first()
    )


def _received_value(po_number: str) -> float:
    db = SessionLocal()
    try:
        lines = db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.purchase_order_number == po_number
        ).all()
        return sum(float(l.received_quantity or 0) * float(l.unit_price or 0) for l in lines)
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
    try:
        return _run()
    finally:
        rc = _reset()
        print(f"reset_demo EXIT={rc}")


def _run() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    # 前置：取 RELEASED 采购单并整单收货（三单匹配上限=已收货价值）
    db = SessionLocal()
    try:
        po = _pick_po(db)
        assert po is not None, "探针前置：无 RELEASED 采购单"
        po_number = po.purchase_order_number
    finally:
        db.close()
    r = client.get(f"/api/purchase/purchase-orders/{po_number}")
    lines = [
        {"line_number": ln["line_number"], "quantity": ln["outstanding_quantity"]}
        for ln in r.json()["lines"]
        if ln["outstanding_quantity"] > 0
    ]
    assert lines, "探针前置：采购单无可收货行"
    r = client.post(
        f"/api/purchase/purchase-orders/{po_number}/receive", json={"lines": lines}, headers=H
    )
    assert r.status_code == 200, f"探针前置：收货失败 {r.status_code} {r.text[:200]}"
    cap = _received_value(po_number)
    assert cap > 0, f"探针前置：收货后上限仍为 0"

    # 1. 创建采购发票 201/PI/DRAFT（金额=上限的 80%）
    r = client.post(
        "/api/purchase/supplier-invoices",
        headers=H,
        json={"purchase_order_number": po_number, "amount": round(cap * 0.8, 2),
              "remarks": "发票探针"},
    )
    check("1.创建发票 201/DRAFT/PI 前缀",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["invoice_number"].startswith("PI-"),
          f"{r.status_code} {r.text[:200]}")
    pi1 = r.json()["invoice_number"]

    # 2. 超匹配 400（再开 1.5 倍上限）
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po_number, "amount": round(cap * 1.5, 2)})
    check("2.三单匹配(超匹配) 400", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

    # 3. confirm → CONFIRMED
    r = client.post(f"/api/purchase/supplier-invoices/{pi1}/confirm", headers=H)
    check("3.confirm→CONFIRMED", r.status_code == 200 and r.json()["status"] == "CONFIRMED",
          f"{r.status_code} {r.text[:200]}")

    # 4. 重复 confirm 400
    r = client.post(f"/api/purchase/supplier-invoices/{pi1}/confirm", headers=H)
    check("4.重复 confirm 400", r.status_code == 400, f"{r.status_code}")

    # 5. cancel 流程：新建后作废
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po_number, "amount": round(cap * 0.1, 2)})
    pi2 = r.json()["invoice_number"]
    r = client.post(f"/api/purchase/supplier-invoices/{pi2}/cancel", headers=H)
    check("5.cancel→CANCELLED", r.status_code == 200 and r.json()["status"] == "CANCELLED",
          f"{r.status_code} {r.text[:200]}")

    # 6. 未收货 PO 创建 400（上限=0）
    db = SessionLocal()
    try:
        po2 = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.is_deleted.is_(False),
                    PurchaseOrder.status == planning.PurchaseOrderStatus.RELEASED,
                    PurchaseOrder.purchase_order_number != po_number)
            .order_by(PurchaseOrder.id)
            .first()
        )
        po2_number = po2.purchase_order_number if po2 else po_number
    finally:
        db.close()
    if po2_number == po_number:
        po2_number = "PUR-NO-RECEIPT-PROBE"  # 无第二张单时用不存在单号也应 404/400
    r = client.post("/api/purchase/supplier-invoices", headers=H,
                    json={"purchase_order_number": po2_number, "amount": 100})
    check("6.未收货 PO 开票 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 采购发票探针：{passed}/{len(CHECKS)} 通过 =====")
    return 0 if passed == len(CHECKS) == 6 else 1


if __name__ == "__main__":
    sys.exit(main())
