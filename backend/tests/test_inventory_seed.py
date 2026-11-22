"""库存演示种子回归：盘点/调拨/估值流水与凭证一次成型。"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.common.models.mm import Material  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    Account,
    JournalEntry,
    Stocktake,
    StockTransfer,
    ValuationMove,
    Warehouse,
)
from backend.services.finance.gl_rules import GL_ACCOUNTS  # noqa: E402
from backend.services.inventory.inventory_seed import seed_inventory_demo  # noqa: E402
from backend.services.inventory.valuation import InventoryValuationService  # noqa: E402


BASELINE = {
    "RM-FR4-150": 20,
    "RM-PP1080": 15,
    "RM-CU-FOIL": 30,
    "RM-DRY-FILM": 18,
    "HF1004ENIGAB02": 100,
}


def test_inventory_seed_builds_stock_documents(db):
    """库存种子：仓库/盘点/调拨/估值流水齐全，重复调用幂等。"""
    for code, name, account_type in GL_ACCOUNTS:
        db.add(Account(account_code=code, account_name=name, account_type=account_type, is_leaf=True))
    for code, qty in BASELINE.items():
        db.add(Material(
            material_code=code, material_name=code, category="RAW", unit="PCS",
            current_stock=qty, standard_price=10,
        ))
    db.flush()
    # 建移动加权期初（不导入 upgrade_planning：其模块级 stdout 重配置会破坏 pytest 捕获）
    for code, qty in BASELINE.items():
        InventoryValuationService.post(
            db, material_code=code, qty_delta=qty, unit_cost=10,
            source_type="OPENING", source_ref=f"OPENING-TEST-{code}", operator="system",
        )

    assert seed_inventory_demo(db) > 0
    db.flush()

    assert db.query(Warehouse).count() == 2
    assert db.query(Stocktake).count() == 3
    assert db.query(StockTransfer).count() == 3
    assert db.query(ValuationMove).count() >= 10  # 5 期初 + 2 盘点 + 3 领料
    assert db.query(JournalEntry).count() >= 5

    # 重复调用不重复入账
    assert seed_inventory_demo(db) == 0
    assert db.query(Stocktake).count() == 3
