"""移动加权估值探针（T802）：入库/出库/红冲快照/负金额守护/除零回退/幂等/数量同步。

Run: python backend/scripts/probe_valuation.py （起点+终点双 reset）
"""
from __future__ import annotations

import io
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.common.models.planning import InventoryValuation, ValuationMove  # noqa: E402
from backend.services.inventory.valuation import (  # noqa: E402
    InventoryValuationService,
    ValuationError,
    get_cost,
)

CHECKS: list[tuple[str, bool, object]] = []
MAT = "RM-FR4-150"


def check(name: str, cond: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name} {detail if not cond else ''}")


def _reset() -> int:
    return subprocess.run(
        [sys.executable, str(project_root / "backend" / "scripts" / "reset_demo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).returncode


def _state(db):
    row = db.query(InventoryValuation).filter(InventoryValuation.material_code == MAT).first()
    mat = db.query(mm.Material).filter(mm.Material.material_code == MAT).first()
    return row, mat


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
        print(f"\n===== 移动加权探针：{passed}/{len(CHECKS)} 通过 =====")
        sys.exit(0 if passed == len(CHECKS) and len(CHECKS) >= 8 else 1)


def _run() -> None:
    db = SessionLocal()
    try:
        row, mat = _state(db)
        check("1.期初建账存在且金额=数量×均价",
              row is not None and float(row.amount) > 0
              and abs(float(row.qty) * float(row.avg_cost) - float(row.amount)) < 0.01,
              f"qty={float(row.qty)} amount={float(row.amount)} avg={float(row.avg_cost)}")
        qty0, amount0 = float(row.qty), float(row.amount)

        # 2. 入库 10@120 → 加权均价重算
        m_in = InventoryValuationService.post(
            db, material_code=MAT, qty_delta=10, unit_cost=120,
            source_type="PURCHASE_RECEIPT", source_ref="PROBE-IN-1", operator="probe")
        db.commit()
        db.refresh(row)
        expected_avg = (amount0 + 1200) / (qty0 + 10)
        check("2.入库加权均价正确",
              abs(float(row.avg_cost) - expected_avg) < 0.0001
              and abs(float(row.amount) - (amount0 + 1200)) < 0.01
              and float(m_in.unit_cost) == 120,
              f"avg={float(row.avg_cost)} expected={expected_avg:.6f}")
        avg_after_in = float(row.avg_cost)

        # 3. 出库 5 → 按当前均价、余额快照正确
        m_out = InventoryValuationService.post(
            db, material_code=MAT, qty_delta=-5,
            source_type="SALES_ISSUE", source_ref="PROBE-OUT-1", operator="probe")
        db.commit()
        db.refresh(row)
        check("3.出库按均价+余额快照",
              abs(float(m_out.unit_cost) - avg_after_in) < 0.0001
              and abs(float(m_out.balance_qty) - (qty0 + 10 - 5)) < 0.01
              and abs(float(row.amount) - (amount0 + 1200 - 5 * avg_after_in)) < 0.01,
              f"cost={float(m_out.unit_cost)} balQty={float(m_out.balance_qty)}")

        # 4. 价格变动后红冲：按原出库快照价（非当前均价）
        InventoryValuationService.post(
            db, material_code=MAT, qty_delta=8, unit_cost=200,
            source_type="PURCHASE_RECEIPT", source_ref="PROBE-IN-2", operator="probe")
        db.commit()
        db.refresh(row)
        current_avg = float(row.avg_cost)
        rev = InventoryValuationService.post(
            db, material_code=MAT, qty_delta=5,
            source_type="SALES_ISSUE", source_ref="PROBE-OUT-1-REVERSE",
            reversal_of=m_out.move_number, operator="probe")
        db.commit()
        check("4.红冲按原快照单价(非当前均价)",
              abs(float(rev.unit_cost) - avg_after_in) < 0.0001
              and abs(float(rev.unit_cost) - current_avg) > 0.001,
              f"rev={float(rev.unit_cost)} old={avg_after_in:.6f} current={current_avg:.6f}")

        # 5. 幂等：同 source_type+ref+数量 重复调用返回同一流水
        again = InventoryValuationService.post(
            db, material_code=MAT, qty_delta=10, unit_cost=120,
            source_type="PURCHASE_RECEIPT", source_ref="PROBE-IN-1", operator="probe")
        check("5.幂等重复调用不改账", again.move_number == m_in.move_number,
              f"{again.move_number} vs {m_in.move_number}")

        # 6. 数量账与金额账同步
        db.refresh(row)
        db.refresh(mat)
        check("6.Material.current_stock 与估值 qty 同步",
              abs(float(mat.current_stock) - float(row.qty)) < 0.01,
              f"stock={float(mat.current_stock)} qty={float(row.qty)}")

        # 7. 出库数量 > 现存 → 拒绝
        try:
            InventoryValuationService.post(
                db, material_code=MAT, qty_delta=-999999,
                source_type="SALES_ISSUE", source_ref="PROBE-OVER", operator="probe")
            rejected = False
        except ValuationError:
            rejected = True
        check("7.超量出库被拒", rejected)

        # 8. 负金额守护：人为制造金额异常 + 按高价原快照红冲 → 金额钳制 0
        val = db.query(InventoryValuation).filter(
            InventoryValuation.material_code == MAT).first()
        original_high = db.query(ValuationMove).filter(
            ValuationMove.source_ref == "PROBE-IN-2").first()
        val.amount = Decimal("1.0000")  # 模拟金额账异常（低于真实价值）
        db.commit()
        InventoryValuationService.post(
            db, material_code=MAT, qty_delta=-1,
            source_type="MATERIAL_ISSUE", source_ref="PROBE-NEG",
            reversal_of=original_high.move_number, allow_negative=True, operator="probe")
        db.commit()
        db.refresh(val)
        check("8.负金额钳制为0+告警", float(val.amount) == 0,
              f"amount={float(val.amount)}")

        # 9. 清空库存 → avg=0、last_cost 保留，get_cost 有回退
        qty_left = float(val.qty)
        if qty_left > 0:
            InventoryValuationService.post(
                db, material_code=MAT, qty_delta=-qty_left,
                source_type="MATERIAL_ISSUE", source_ref="PROBE-DRAIN", operator="probe")
            db.commit()
            db.refresh(val)
        check("9.零库存均价归零+成本回退",
              float(val.qty) == 0 and float(val.avg_cost) == 0
              and get_cost(db, MAT) > 0,
              f"qty={float(val.qty)} avg={float(val.avg_cost)} fallback={get_cost(db, MAT)}")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
