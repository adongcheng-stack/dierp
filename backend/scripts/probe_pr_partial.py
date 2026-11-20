"""PR 行级部分转换探针（T902）：部分数量→多次转换→状态联动→边界拒绝。

Run: python backend/scripts/probe_pr_partial.py （起点+终点双 reset）
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
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []


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
        _run()
    finally:
        rc = _reset()
        print(f"reset_demo EXIT={rc}")
        passed = sum(1 for _, ok, _ in CHECKS if ok)
        print(f"\n===== PR 部分转换探针：{passed}/{len(CHECKS)} 通过 =====")
        sys.exit(0 if passed == len(CHECKS) and len(CHECKS) >= 10 else 1)


def _run() -> None:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    mat = "RM-FR4-150"
    unit = next((m["unit"] for m in client.get("/api/mm/materials").json()
                 if m["material_code"] == mat), "PCS")

    # 1. 建 3 行申请单
    r = client.post("/api/purchase/purchase-requests", headers=H, json={
        "supplier_id": "SUP-RY", "supplier_name": "苏州瑞银电子材料",
        "expected_date": "2026-12-20T00:00:00", "requested_by": "probe",
        "remarks": "部分转换探针",
        "lines": [
            {"material_code": mat, "quantity": 100, "unit": unit, "unit_price": 10},
            {"material_code": mat, "quantity": 50, "unit": unit, "unit_price": 10},
            {"material_code": mat, "quantity": 20, "unit": unit, "unit_price": 10},
        ],
    })
    check("1.创建 3 行申请单", r.status_code == 201 and len(r.json()["lines"]) == 3,
          f"{r.status_code} {r.text[:150]}")
    pr = r.json()["purchase_request_number"]

    # 2. 下达
    r = client.post(f"/api/purchase/purchase-requests/{pr}/release", headers=H)
    check("2.下达 RELEASED", r.status_code == 200 and r.json()["status"] == "RELEASED",
          f"{r.status_code} {r.text[:150]}")

    # 3. 行 1 部分转 30
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert-lines", headers=H,
                    json={"lines": [{"line_number": 1, "quantity": 30}]})
    data = r.json()
    line1 = next((l for l in data["lines"] if l["line_number"] == 1), {})
    check("3.部分转换→PR PARTIALLY_CONVERTED",
          r.status_code == 200 and data.get("status") == "PARTIALLY_CONVERTED"
          and line1.get("status") == "OPEN"
          and abs(line1.get("converted_quantity", 0) - 30) < 1e-6
          and abs(line1.get("remaining_quantity", 0) - 70) < 1e-6,
          f"{r.status_code} status={data.get('status')} line1={line1}")
    po1 = data.get("new_po_number")

    # 4. 生成的 PO 数量/金额正确
    po = client.get(f"/api/purchase/purchase-orders/{po1}").json()
    check("4.PO 数量=本次转换量", po.get("status") == "RELEASED"
          and any(float(l["quantity"]) == 30 for l in po.get("lines", [])),
          str(po)[:180])

    # 5. 同一行再转剩余 70 → 行置 CONVERTED，PR 仍部分
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert-lines", headers=H,
                    json={"lines": [{"line_number": 1, "quantity": 70}]})
    data = r.json()
    line1 = next((l for l in data["lines"] if l["line_number"] == 1), {})
    check("5.行转满→CONVERTED（申请仍部分）",
          r.status_code == 200 and line1.get("status") == "CONVERTED"
          and data.get("status") == "PARTIALLY_CONVERTED",
          f"line1={line1.get('status')} pr={data.get('status')}")

    # 6. 重复行选择 400
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert-lines", headers=H,
                    json={"lines": [{"line_number": 2, "quantity": 1},
                                    {"line_number": 2, "quantity": 2}]})
    check("6.重复行选择 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 7. 超余量 400
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert-lines", headers=H,
                    json={"lines": [{"line_number": 2, "quantity": 999}]})
    check("7.超余量 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 8. 已转满的行再转 400
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert-lines", headers=H,
                    json={"lines": [{"line_number": 1, "quantity": 1}]})
    check("8.已转满行再转 400", r.status_code == 400, f"{r.status_code}")

    # 9. 剩余两行一次转完 → PR CONVERTED
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert-lines", headers=H,
                    json={"lines": [{"line_number": 2}, {"line_number": 3}]})
    data = r.json()
    check("9.全部行转完→PR CONVERTED",
          r.status_code == 200 and data.get("status") == "CONVERTED",
          f"{r.status_code} status={data.get('status')}")

    # 10. converted_po_numbers 累计 3 张
    numbers = [n for n in (data.get("converted_po_numbers") or "").split(",") if n]
    check("10.多张 PO 单号累计", len(numbers) == 3 and len(set(numbers)) == 3, str(numbers))

    # 11. 整单转换对已转换申请 400
    r = client.post(f"/api/purchase/purchase-requests/{pr}/convert", headers=H)
    check("11.已转换申请整单转换 400", r.status_code == 400, f"{r.status_code}")

    # 12. 整单转换（未转过）仍可用且新字段就位
    r = client.get("/api/purchase/purchase-requests", params={"status": "RELEASED"}, headers=H)
    open_pr = next((p for p in r.json().get("items", []) if p["purchase_request_number"] != pr), None)
    if open_pr:
        r = client.post(f"/api/purchase/purchase-requests/{open_pr['purchase_request_number']}/convert", headers=H)
        check("12.整单转换兼容+新字段", r.status_code == 200
              and r.json().get("converted_po_numbers")
              and all(abs(l.get("converted_quantity", 0) - l["quantity"]) < 1e-6
                      for l in r.json()["lines"] if l["status"] == "CONVERTED"),
              f"{r.status_code} {r.text[:150]}")
    else:
        check("12.整单转换兼容+新字段", False, "无其他 RELEASED 申请")


if __name__ == "__main__":
    sys.exit(main())
