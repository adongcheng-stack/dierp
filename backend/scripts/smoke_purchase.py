"""N3 采购闭环冒烟：列表 → 整单收货（回冲库存）→ 部分收货 → 超量拒绝 → 关闭。

Run: python backend/scripts/smoke_purchase.py
（TestClient 驱动，不要求后端进程已重启；收尾由外层门禁统一 reset_demo 恢复基线）
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

import json  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.common.models.mm import Material  # noqa: E402

client = TestClient(app)


def call(method: str, path: str, token: str | None = None, body: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    resp = client.request(method, path, json=body, headers=headers)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {}


def _material_stock(code: str) -> float:
    db = SessionLocal()
    try:
        row = db.query(Material).filter(Material.material_code == code).first()
        return float(row.current_stock or 0) if row else 0.0
    finally:
        db.close()


def main() -> int:
    # 幂等起点：先复位演示基线（收货/关闭残留会让后续断言失效）
    import subprocess
    subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        check=True,
        capture_output=True,
    )
    print("[0] reset_demo 幂等起点 OK")
    st, data = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"}).json(), None
    token = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"}).json()["access_token"]
    print("[1] 登录 OK；GET 采购单列表")
    st, data = call("GET", "/api/purchase/purchase-orders", token)
    assert st == 200 and data["total"] >= 2, f"列表异常: {st} {str(data)[:150]}"
    by_material = {}
    for po in data["items"]:
        for line in po["lines"]:
            by_material[line["material_code"]] = (po["purchase_order_number"], line["line_number"], line["outstanding_quantity"])
    assert "RM-FR4-150" in by_material, "缺 RM-FR4-150 采购行"
    print(f"    采购单 {data['total']} 张，行物料 {sorted(by_material)}")

    print("[2] 整单收货（单 1，不传行=全收）")
    po1 = by_material["RM-FR4-150"][0]
    st, received = call("POST", f"/api/purchase/purchase-orders/{po1}/receive", token, {"received_by": "smoke"})
    assert st == 200 and received["status"] == "RECEIVED", f"{st} {str(received)[:200]}"
    print(f"    {po1} → RECEIVED")

    print("[3] 库存回冲校验")
    stock = _material_stock("RM-FR4-150")
    assert stock >= 100, f"RM-FR4-150 库存未回冲: {stock}"
    print(f"    RM-FR4-150 库存 = {stock}（含 +100 到货）")

    print("[4] 部分收货（单 2 第 1 行收 50/200）")
    po2 = by_material["RM-PP1080"][0]
    st, partial = call("POST", f"/api/purchase/purchase-orders/{po2}/receive", token,
                       {"lines": [{"line_number": 1, "quantity": 50}], "received_by": "smoke"})
    assert st == 200 and partial["status"] == "PARTIALLY_RECEIVED", f"{st} {str(partial)[:200]}"
    line1 = next(l for l in partial["lines"] if l["line_number"] == 1)
    assert abs(line1["outstanding_quantity"] - 150) < 1e-6
    print(f"    {po2} → PARTIALLY_RECEIVED，行1 余量 150")

    print("[5] 超量收货拒绝")
    st, err = call("POST", f"/api/purchase/purchase-orders/{po2}/receive", token,
                   {"lines": [{"line_number": 1, "quantity": 999}]})
    assert st == 400 and "超量" in err.get("detail", ""), f"{st} {str(err)[:200]}"
    print("    400 超量拦截 OK")

    print("[6] 收满 → RECEIVED；关闭后再收 → 400")
    st, full = call("POST", f"/api/purchase/purchase-orders/{po2}/receive", token,
                    {"lines": [{"line_number": 1, "quantity": 150}, {"line_number": 2, "quantity": 50}]})
    assert st == 200 and full["status"] == "RECEIVED"
    st, closed = call("POST", f"/api/purchase/purchase-orders/{po1}/close", token)
    assert st == 200 and closed["status"] == "CLOSED"
    st, again = call("POST", f"/api/purchase/purchase-orders/{po1}/receive", token, {})
    assert st == 400, f"关闭后收货未被拒绝: {st}"
    print("    RECEIVED / CLOSED / 拒绝收货 全部符合预期")

    # 自清理：复位演示基线（收货/关闭残留会污染 parity 与后续演示）
    import subprocess
    subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        check=True,
        capture_output=True,
    )
    print("[7] reset_demo 恢复基线 OK")

    print("\n采购闭环冒烟通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
