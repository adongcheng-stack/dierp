"""一次性行为探针：库存补强（T503）——仓库/盘点/调拨。

8 断言。Run: python backend/scripts/probe_mm_stock.py
（起点+终点双 reset）
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
from backend.common.models.mm import Material, MaterialTransaction  # noqa: E402

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


def _stock(code: str) -> float:
    db = SessionLocal()
    try:
        row = db.query(Material).filter(Material.material_code == code).first()
        return float(row.current_stock or 0) if row else 0.0
    finally:
        db.close()


def _txn(type_: str, ref: str) -> MaterialTransaction | None:
    db = SessionLocal()
    try:
        return (
            db.query(MaterialTransaction)
            .filter(MaterialTransaction.transaction_type == type_,
                    MaterialTransaction.reference_number == ref)
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
        rc = _reset()
        print(f"reset_demo EXIT={rc}")


def _run() -> int:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    stock0 = _stock(MATERIAL)

    # 1. 仓库创建（幂等：201 或已存在 400 皆可，最终 GET 必须在册；探针标记供 reset 清理）
    client.post("/api/mm/warehouses", headers=H,
                json={"warehouse_code": "WH-PD01", "warehouse_name": "成品一仓",
                      "location": "A栋1层", "remarks": "仓库探针"})
    client.post("/api/mm/warehouses", headers=H,
                json={"warehouse_code": "WH-PD02", "warehouse_name": "成品二仓",
                      "remarks": "仓库探针"})
    wh_list = client.get("/api/mm/warehouses").json()
    codes = {w["warehouse_code"] for w in wh_list.get("items", [])}
    check("1.仓库在册 WH-PD01/WH-PD02", {"WH-PD01", "WH-PD02"} <= codes,
          f"codes={sorted(codes)}")

    # 2. 盘点创建：book_qty=快照、diff=counted−book
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": stock0 + 5,
                          "warehouse": "WH-PD01", "remarks": "盘盈探针"})
    check("2.盘点创建 book 快照+diff 计算",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and abs(r.json()["book_qty"] - stock0) < 1e-6
          and abs(r.json()["diff"] - 5) < 1e-6
          and r.json()["stocktake_number"].startswith("STK-"),
          f"{r.status_code} {r.text[:200]}")
    stk1 = r.json()["stocktake_number"]

    # 3. 盘盈审批 → 库存 +5 + ADJUSTMENT 流水
    r = client.post(f"/api/mm/stocktakes/{stk1}/approve", headers=H)
    t = _txn("ADJUSTMENT", stk1)
    check("3.盘盈审批→库存校正+ADJUSTMENT 流水",
          r.status_code == 200 and r.json()["status"] == "APPROVED"
          and abs(_stock(MATERIAL) - (stock0 + 5)) < 1e-6
          and t is not None and float(t.quantity) == 5,
          f"{r.status_code} stock={_stock(MATERIAL)} txn={'None' if t is None else t.quantity}")

    # 4. 盘亏至负 → 400（模拟并发：先批一张 −30，再批此前创建的 −80 → 50−80 < 0）
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": 0})
    stk2 = r.json()["stocktake_number"]  # diff = −80（基于 80 的快照）
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": 50})
    stk3 = r.json()["stocktake_number"]  # diff = −30
    client.post(f"/api/mm/stocktakes/{stk3}/approve", headers=H)  # 库存 80→50
    r = client.post(f"/api/mm/stocktakes/{stk2}/approve", headers=H)  # 50−80 < 0 → 400
    check("4.盘亏至负 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 5. 调拨创建 201/TRF
    r = client.post("/api/mm/stock-transfers", headers=H,
                    json={"from_warehouse_code": "WH-PD01", "to_warehouse_code": "WH-PD02",
                          "material_code": MATERIAL, "quantity": 10})
    check("5.调拨创建 201/TRF/DRAFT",
          r.status_code == 201 and r.json()["status"] == "DRAFT"
          and r.json()["transfer_number"].startswith("TRF-"),
          f"{r.status_code} {r.text[:200]}")
    trf1 = r.json()["transfer_number"]

    # 6. from==to 400
    r = client.post("/api/mm/stock-transfers", headers=H,
                    json={"from_warehouse_code": "WH-PD01", "to_warehouse_code": "WH-PD01",
                          "material_code": MATERIAL, "quantity": 10})
    check("6.from=to 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 7. 调拨确认 → 两笔流水（OUT −10 / IN +10），总量不变
    stock_before = _stock(MATERIAL)
    r = client.post(f"/api/mm/stock-transfers/{trf1}/confirm", headers=H)
    t_out = _txn("TRANSFER_OUT", trf1)
    t_in = _txn("TRANSFER_IN", trf1)
    check("7.调拨确认→两笔流水+总量不变",
          r.status_code == 200 and r.json()["status"] == "CONFIRMED"
          and t_out is not None and float(t_out.quantity) == -10
          and t_in is not None and float(t_in.quantity) == 10
          and abs(_stock(MATERIAL) - stock_before) < 1e-6,
          f"{r.status_code} out={'None' if t_out is None else t_out.quantity}")

    # 8. 重复确认 400
    r = client.post(f"/api/mm/stock-transfers/{trf1}/confirm", headers=H)
    check("8.重复确认 400", r.status_code == 400, f"{r.status_code}")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n===== 库存补强探针：{passed}/{len(CHECKS)} 通过 =====")
    return 0 if passed == len(CHECKS) == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
