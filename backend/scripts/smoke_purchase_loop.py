"""采购域全链路冒烟：采购申请 → 采购单 → 到货 → 退货/索赔 → 应付。

Run: python backend/scripts/smoke_purchase_loop.py
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
from backend.common.models.mm import Material  # noqa: E402

client = TestClient(app)
CHECKS: list[tuple[str, bool, object]] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))


def _stock(code: str) -> float:
    db = SessionLocal()
    try:
        row = db.query(Material).filter(Material.material_code == code).first()
        return float(row.current_stock or 0) if row else 0.0
    finally:
        db.close()


def main() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    # ── [1] 种子申请可见 ──
    r = client.get("/api/purchase/purchase-requests")
    check("PR 列表匿名可读", r.status_code == 200)
    seeded = r.json().get("items", [])
    check("种子 PR ≥ 2", len(seeded) >= 2, len(seeded))
    check("种子含 DRAFT 与 RELEASED",
          {"DRAFT", "RELEASED"}.issubset({p["status"] for p in seeded}))

    # ── [2] 创建申请（DRAFT）──
    r = client.post(
        "/api/purchase/purchase-requests",
        json={
            "supplier_id": "SUP-HQ",
            "supplier_name": "华强覆铜板贸易",
            "requested_by": "smoke",
            "lines": [
                {"material_code": "RM-FR4-150", "quantity": 3, "unit_price": 38.5},
                {"material_code": "RM-CU-FOIL", "quantity": 2, "unit_price": 86.0},
            ],
        },
        headers=H,
    )
    check("创建 PR → 201 DRAFT", r.status_code == 201 and r.json()["status"] == "DRAFT",
          r.text[:120] if r.status_code != 201 else r.json()["purchase_request_number"])
    pr_number = r.json()["purchase_request_number"]
    check("PR 号符合 PRQ-YYYYMMDD-XXXX", pr_number.startswith("PRQ-"), pr_number)
    check("PR 总金额 = 3×38.5 + 2×86", abs(r.json()["total_amount"] - 287.5) < 1e-6,
          r.json()["total_amount"])

    # ── [3] 状态机：DRAFT 不能直接转换 ──
    r = client.post(f"/api/purchase/purchase-requests/{pr_number}/convert", headers=H)
    check("DRAFT 转换被拒绝", r.status_code == 400, r.status_code)

    # ── [4] 下达 → 转换 ──
    r = client.post(f"/api/purchase/purchase-requests/{pr_number}/release", headers=H)
    check("下达 → RELEASED", r.status_code == 200 and r.json()["status"] == "RELEASED")
    r = client.post(f"/api/purchase/purchase-requests/{pr_number}/convert", headers=H)
    check("转换 → CONVERTED", r.status_code == 200 and r.json()["status"] == "CONVERTED")
    po_number = r.json().get("converted_po_number")
    check("回写 converted_po_number", bool(po_number), po_number)

    # ── [5] 生成的采购单可用并整单收货 ──
    r = client.get(f"/api/purchase/purchase-orders/{po_number}")
    check("转换生成的 PO 可读", r.status_code == 200 and r.json()["status"] == "RELEASED")
    lines = [{"line_number": ln["line_number"], "quantity": ln["outstanding_quantity"]}
             for ln in r.json()["lines"] if ln["outstanding_quantity"] > 0]
    stock_before = _stock("RM-FR4-150")
    r = client.post(f"/api/purchase/purchase-orders/{po_number}/receive",
                    json={"lines": lines}, headers=H)
    check("整单收货 → RECEIVED", r.status_code == 200 and r.json()["status"] == "RECEIVED")
    check("收货回冲库存", abs(_stock("RM-FR4-150") - stock_before - 3.0) < 1e-6,
          f"{stock_before} -> {_stock('RM-FR4-150')}")

    # ── [6] 退货：超量拒绝 + 正常退货 ──
    r = client.post(
        "/api/purchase/purchase-returns",
        json={"purchase_order_number": po_number, "return_type": "RETURN",
              "reason": "冒烟超量",
              "lines": [{"purchase_order_line_number": 1, "quantity": 999}]},
        headers=H,
    )
    check("退货超量被拒绝", r.status_code == 400, r.status_code)

    r = client.post(
        "/api/purchase/purchase-returns",
        json={"purchase_order_number": po_number, "return_type": "RETURN",
              "reason": "冒烟退货",
              "lines": [{"purchase_order_line_number": 1, "quantity": 1}]},
        headers=H,
    )
    check("创建退货单 → 201 DRAFT", r.status_code == 201 and r.json()["status"] == "DRAFT",
          r.text[:120] if r.status_code != 201 else "")
    rtn_number = r.json()["return_number"] if r.status_code == 201 else None
    check("退货号符合 RTN-YYYYMMDD-XXXX", bool(rtn_number and rtn_number.startswith("RTN-")), rtn_number)

    stock_at_return = _stock("RM-FR4-150")
    r = client.post(f"/api/purchase/purchase-returns/{rtn_number}/approve", headers=H)
    check("退货审批 → APPROVED", r.status_code == 200 and r.json()["status"] == "APPROVED")
    check("审批后库存扣减 1", abs(_stock("RM-FR4-150") - (stock_at_return - 1.0)) < 1e-6,
          f"{stock_at_return} -> {_stock('RM-FR4-150')}")

    # ── [7] 已占用退货量：再退 3 张应被拒（已收 3，已占用 1）──
    r = client.post(
        "/api/purchase/purchase-returns",
        json={"purchase_order_number": po_number, "return_type": "RETURN",
              "lines": [{"purchase_order_line_number": 1, "quantity": 3}]},
        headers=H,
    )
    check("已占用可退量拦截（可退 2 请求 3）", r.status_code == 400, r.status_code)

    # ── [8] 驳回释放占用 ──
    r = client.post(
        "/api/purchase/purchase-returns",
        json={"purchase_order_number": po_number, "return_type": "RETURN",
              "lines": [{"purchase_order_line_number": 1, "quantity": 2}]},
        headers=H,
    )
    rtn2 = r.json()["return_number"] if r.status_code == 201 else None
    r = client.post(f"/api/purchase/purchase-returns/{rtn2}/reject", headers=H)
    check("驳回 → REJECTED", r.status_code == 200 and r.json()["status"] == "REJECTED")
    check("驳回后库存不变", abs(_stock("RM-FR4-150") - (stock_at_return - 1.0)) < 1e-6)

    # ── [9] 索赔：不动库存，只记金额 ──
    r = client.post(
        "/api/purchase/purchase-returns",
        json={"purchase_order_number": po_number, "return_type": "CLAIM",
              "reason": "冒烟索赔",
              "lines": [{"purchase_order_line_number": 2, "quantity": 2}]},
        headers=H,
    )
    claim_number = r.json()["return_number"] if r.status_code == 201 else None
    check("创建索赔单 → 201", r.status_code == 201, r.status_code)
    check("索赔金额 = 2×86", abs(r.json().get("total_amount", 0) - 172.0) < 1e-6,
          r.json().get("total_amount"))
    stock_at_claim = _stock("RM-CU-FOIL")
    r = client.post(f"/api/purchase/purchase-returns/{claim_number}/approve", headers=H)
    check("索赔审批 → APPROVED", r.status_code == 200)
    check("索赔不动库存", abs(_stock("RM-CU-FOIL") - stock_at_claim) < 1e-6)

    # ── [10] 关闭已审批退货 ──
    r = client.post(f"/api/purchase/purchase-returns/{rtn_number}/close", headers=H)
    check("退货关闭 → CLOSED", r.status_code == 200 and r.json()["status"] == "CLOSED")

    # ── [11] 应付账款：净到货冲减退货 ──
    r = client.get("/api/purchase/ap-view")
    check("AP 视图可读", r.status_code == 200)
    sup_hq = next((x for x in r.json().get("items", []) if x["supplier_id"] == "SUP-HQ"), None)
    check("AP 含 SUP-HQ", sup_hq is not None)
    if sup_hq:
        check("AP returned_amount > 0（退货冲减）", sup_hq.get("returned_amount", 0) > 0,
              sup_hq.get("returned_amount"))
        check("应付 = 净到货 - 已结",
              abs(sup_hq["payable_amount"] - (sup_hq["received_amount"] - sup_hq["closed_amount"])) < 0.01,
              sup_hq)

    # ── [12] reset 恢复基线 ──
    subprocess.run([sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
                   check=True, capture_output=True)
    r = client.get("/api/purchase/purchase-requests")
    check("reset 后 PR 回到种子 2 张", r.json().get("total") == 2, r.json().get("total"))
    check("reset 后库存复位", abs(_stock("RM-FR4-150") - stock_before) < 1e-6,
          f"{_stock('RM-FR4-150')} vs {stock_before}")

    failed = [(n, d) for n, ok, d in CHECKS if not ok]
    for name, ok, detail in CHECKS:
        print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f": {detail}" if not ok and detail != "" else ""))
    print("\n采购域全链路冒烟通过" if not failed else f"\n存在 {len(failed)} 处偏差")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
