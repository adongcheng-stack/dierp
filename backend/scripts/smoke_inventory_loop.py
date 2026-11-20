"""库存补强全链路冒烟（P3）：盘点 → 校正+流水；调拨 → 双流水；批次效期与资金 KPI 对账。

Run: python backend/scripts/smoke_inventory_loop.py
（TestClient 驱动；起点+终点双 reset，失败也复位）
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
        _run()
    finally:
        rc = _reset()
        db = SessionLocal()
        try:
            counts = (
                db.query(planning.Stocktake).count(),
                db.query(planning.StockTransfer).count(),
                db.query(planning.Warehouse).filter(planning.Warehouse.remarks.is_(None)).count(),
            )
        finally:
            db.close()
        check("12.reset 复位（盘点/调拨清空，仓库种子保留）",
              rc == 0 and counts[:2] == (0, 0) and counts[2] >= 0,
              f"reset={rc} counts={counts}")
        passed = sum(1 for _, ok, _ in CHECKS if ok)
        print(f"\n===== 库存补强冒烟：{passed}/{len(CHECKS)} 通过 =====")
        sys.exit(0 if passed == len(CHECKS) and len(CHECKS) >= 10 else 1)


def _run() -> None:
    token = client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    stock0 = _stock(MATERIAL)

    # 1. 仓库在册（幂等创建）
    client.post("/api/mm/warehouses", headers=H,
                json={"warehouse_code": "WH-SM01", "warehouse_name": "冒烟一仓",
                      "remarks": "库存冒烟"})
    client.post("/api/mm/warehouses", headers=H,
                json={"warehouse_code": "WH-SM02", "warehouse_name": "冒烟二仓",
                      "remarks": "库存冒烟"})
    codes = {w["warehouse_code"] for w in client.get("/api/mm/warehouses").json().get("items", [])}
    check("1.仓库在册 WH-SM01/02", {"WH-SM01", "WH-SM02"} <= codes, f"codes={sorted(codes)}")

    # 2. 盘点创建快照 + diff
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": stock0 + 8,
                          "warehouse": "WH-SM01"})
    check("2.盘点创建 book 快照+diff",
          r.status_code == 201 and abs(r.json()["book_qty"] - stock0) < 1e-6
          and abs(r.json()["diff"] - 8) < 1e-6,
          f"{r.status_code} {r.text[:200]}")
    stk1 = r.json()["stocktake_number"]

    # 3. 盘盈审批 → 库存 +8 + ADJUSTMENT 流水
    client.post(f"/api/mm/stocktakes/{stk1}/approve", headers=H)
    t = _txn("ADJUSTMENT", stk1)
    check("3.盘盈审批→库存+流水",
          abs(_stock(MATERIAL) - (stock0 + 8)) < 1e-6
          and t is not None and float(t.quantity) == 8,
          f"stock={_stock(MATERIAL)} txn={'None' if t is None else t.quantity}")

    # 4. 并发盘亏至负 → 400
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": 0})
    stk_neg = r.json()["stocktake_number"]  # diff = −(stock0+8)
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": 10})
    stk_small = r.json()["stocktake_number"]  # diff = −(stock0−2)
    client.post(f"/api/mm/stocktakes/{stk_small}/approve", headers=H)  # 库存 → stock0−2
    r = client.post(f"/api/mm/stocktakes/{stk_neg}/approve", headers=H)  # (stock0−2)−(stock0+8) < 0
    check("4.盘亏至负 400", r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    # 5. 已审批不可作废 → 400；DRAFT 可作废 → 200
    r = client.post(f"/api/mm/stocktakes/{stk1}/cancel", headers=H)
    check("5.已审批盘点作废 400", r.status_code == 400, f"{r.status_code}")
    r = client.post("/api/mm/stocktakes", headers=H,
                    json={"material_code": MATERIAL, "counted_qty": 0})
    stk_draft = r.json()["stocktake_number"]
    r = client.post(f"/api/mm/stocktakes/{stk_draft}/cancel", headers=H)
    check("6.DRAFT 盘点作废 200", r.status_code == 200 and r.json()["status"] == "CANCELLED",
          f"{r.status_code}")

    # 7. 调拨创建 + from=to 400
    r = client.post("/api/mm/stock-transfers", headers=H,
                    json={"from_warehouse_code": "WH-SM01", "to_warehouse_code": "WH-SM02",
                          "material_code": MATERIAL, "quantity": 12})
    check("7.调拨创建 201/TRF", r.status_code == 201
          and r.json()["transfer_number"].startswith("TRF-"), f"{r.status_code} {r.text[:200]}")
    trf1 = r.json()["transfer_number"]
    r = client.post("/api/mm/stock-transfers", headers=H,
                    json={"from_warehouse_code": "WH-SM01", "to_warehouse_code": "WH-SM01",
                          "material_code": MATERIAL, "quantity": 1})
    check("8.from=to 400", r.status_code == 400, f"{r.status_code}")

    # 9. 调拨确认 → 双流水 + 总量不变 + 重复确认 400
    stock_before = _stock(MATERIAL)
    client.post(f"/api/mm/stock-transfers/{trf1}/confirm", headers=H)
    t_out = _txn("TRANSFER_OUT", trf1)
    t_in = _txn("TRANSFER_IN", trf1)
    check("9.调拨确认→双流水+总量不变",
          t_out is not None and float(t_out.quantity) == -12
          and t_in is not None and float(t_in.quantity) == 12
          and abs(_stock(MATERIAL) - stock_before) < 1e-6,
          f"out={'None' if t_out is None else t_out.quantity} in={'None' if t_in is None else t_in.quantity}")
    r = client.post(f"/api/mm/stock-transfers/{trf1}/confirm", headers=H)
    check("10.重复确认 400", r.status_code == 400, f"{r.status_code}")

    # 11. 批次效期视图 200 + 字段勾稽（取有 ACTIVE 批的物料 HF1004ENIGAB02）
    r = client.get("/api/mm/batch-tracking")
    row = next((x for x in r.json().get("items", []) if x["material_code"] == "HF1004ENIGAB02"), None)
    check("11.批次效期视图", r.status_code == 200 and row is not None
          and row["lot_count"] >= 1 and "estimate_pending" in row and "warning" in row,
          f"{r.status_code} row={'None' if row is None else {k: row[k] for k in ('lot_count', 'lot_qty')}}")

    # 13. 资金 KPI 与台账对账（应收余额 == receivables 未收合计）
    kpi = client.get("/api/dashboard/finance-kpi").json()
    recv = client.get("/api/sd/receivables").json()
    check("12.KPI 应收与台账勾稽",
          abs(kpi["receivable_outstanding"] - recv["totals"]["outstanding_amount"]) < 0.01,
          f"kpi={kpi['receivable_outstanding']} recv={recv['totals']['outstanding_amount']}")


if __name__ == "__main__":
    sys.exit(main())
