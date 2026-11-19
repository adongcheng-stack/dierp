"""N4 完工入库冒烟：complete 端点回冲成品库存 + 幂等拒绝 + reset 复位。

Run: python backend/scripts/smoke_receipt.py
（TestClient 驱动；结束后自动 reset_demo 恢复基线）
"""
from __future__ import annotations

import io
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

import subprocess  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.common.models.mm import Material  # noqa: E402
from backend.common.models.pp import ProductionOrder  # noqa: E402

client = TestClient(app)


def _stock(code: str) -> float:
    db = SessionLocal()
    try:
        row = db.query(Material).filter(Material.material_code == code).first()
        return float(row.current_stock or 0) if row else 0.0
    finally:
        db.close()


def _order(number: str):
    db = SessionLocal()
    try:
        return db.query(ProductionOrder).filter(ProductionOrder.order_number == number).first()
    finally:
        db.close()


def main() -> int:
    token = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    order_number = "PO-APS-02"  # RELEASED，含报废报工单（良品 100）
    order = _order(order_number)
    assert order is not None and order.status.value == "RELEASED", "前置状态异常，请先 reset_demo"
    material_before = _stock(order.material_code)
    print(f"[1] 前置：{order_number} RELEASED，物料 {order.material_code} 库存 {material_before}")

    # 状态机：RELEASED → IN_PRODUCTION → COMPLETED
    resp = client.post(f"/api/pp/production-orders/{order_number}/start", headers=headers)
    assert resp.status_code == 200, resp.text[:200]

    resp = client.post(f"/api/pp/production-orders/{order_number}/complete", headers=headers)
    assert resp.status_code == 200, resp.text[:200]
    material_after = _stock(order.material_code)
    delta = material_after - material_before
    assert abs(delta - 100.0) < 1e-6, f"完工入库未回冲良品 100：Δ={delta}"
    assert _order(order_number).status.value == "COMPLETED"
    print(f"[2] 完工入库 OK：库存 {material_before} → {material_after}（+良品 100），状态 COMPLETED")

    resp = client.post(f"/api/pp/production-orders/{order_number}/complete", headers=headers)
    assert resp.status_code in (400, 422), f"重复完工未被拒绝: {resp.status_code}"
    print("[3] 重复完工拒绝 OK")

    print("[4] reset_demo 恢复基线")
    subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        check=True,
        capture_output=True,
    )
    order = _order(order_number)
    assert order.status.value == "RELEASED" and order.actual_finish_date is None
    assert abs(_stock(order.material_code) - material_before) < 1e-6
    print("    状态与库存均已复位，演示可重复")

    print("\n完工入库冒烟通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
