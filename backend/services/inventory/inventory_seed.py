"""库存演示闭环种子：仓库 / 盘点 / 调拨 / 移动加权估值流水。

补齐库存域空表，与财务种子一样由 reset_planning_demo 在清空运行时数据后调用。
盘点单（含差异）按业务日期审批，自动产生 STOCKTAKE 估值流水与 STOCK_ADJUST 凭证；
调拨单确认产生调出/调入流水；再补几笔 MATERIAL_ISSUE 估值流水，
让「估值流水」页有跨月、有 IN/OUT 两个方向的完整台账。

幂等：以固定单据号判重，重复调用不重复入账。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.common.models.mm import MaterialTransaction
from backend.common.models.planning import (
    Stocktake,
    StocktakeStatus,
    StockTransfer,
    StockTransferStatus,
    Warehouse,
)


WAREHOUSES = [
    ("WH-PD01", "成品一库", "A区1排"),
    ("WH-PD02", "成品二库", "B区1排"),
]

# 盘点单：(单号, 业务日期, 物料, 仓库, 账面, 实物, 状态)
STOCKTAKES = [
    ("STK-DEMO-202609-0001", "2026-09-25", "RM-FR4-150", "WH-PD01", "20", "19.5", StocktakeStatus.APPROVED),
    ("STK-DEMO-202610-0001", "2026-10-28", "RM-PP1080", "WH-PD02", "15", "15.3", StocktakeStatus.APPROVED),
    ("STK-DEMO-202611-0001", "2026-11-18", "HF1004ENIGAB02", "WH-PD01", "100", "100", StocktakeStatus.DRAFT),
]

# 调拨单：(单号, 业务日期, 物料, 源仓, 目的仓, 数量, 状态)
TRANSFERS = [
    ("TRF-DEMO-202608-0001", "2026-08-22", "RM-CU-FOIL", "WH-PD01", "WH-PD02", "5", StockTransferStatus.CONFIRMED),
    ("TRF-DEMO-202610-0001", "2026-10-15", "RM-DRY-FILM", "WH-PD02", "WH-PD01", "3", StockTransferStatus.CONFIRMED),
    ("TRF-DEMO-202611-0001", "2026-11-12", "RM-SOLDER-MASK", "WH-PD01", "WH-PD02", "4", StockTransferStatus.DRAFT),
]

# 额外领料出库估值流水：(来源单号, 业务日期, 物料, 数量)
ISSUE_MOVES = [
    ("MI-DEMO-202607-0001", "2026-07-24", "RM-FR4-150", "3"),
    ("MI-DEMO-202608-0001", "2026-08-26", "RM-PP1080", "2"),
    ("MI-DEMO-202609-0001", "2026-09-22", "RM-CU-FOIL", "4"),
]


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seed_inventory_demo(db: Session) -> int:
    """重建库存演示数据；已存在则跳过（幂等）。"""
    from backend.services.finance.gl_engine import post as gl_post
    from backend.services.inventory.valuation import InventoryValuationService, get_cost

    if db.query(Stocktake).filter(
        Stocktake.stocktake_number == STOCKTAKES[0][0]
    ).first() is not None:
        return 0

    created = 0

    # ── 1) 仓库（后端此前无仓库种子，mock 快照沿用同编码） ──────────
    for code, name, location in WAREHOUSES:
        if db.query(Warehouse).filter(Warehouse.warehouse_code == code).first() is None:
            db.add(Warehouse(
                warehouse_code=code, warehouse_name=name, location=location,
                is_active=True, remarks="库存演示种子", created_by="system",
            ))
            created += 1

    # ── 2) 盘点单 + 审批（差异产生估值流水 + 调整凭证） ─────────────
    for number, date_str, material_code, warehouse, book, counted, status in STOCKTAKES:
        biz_date = _dt(date_str)
        diff = Decimal(counted) - Decimal(book)
        db.add(Stocktake(
            stocktake_number=number,
            material_code=material_code,
            warehouse=warehouse,
            book_qty=Decimal(book),
            counted_qty=Decimal(counted),
            diff=diff,
            status=status,
            stocktake_date=biz_date,
            remarks="库存演示种子：跨月盘点",
            created_by="system",
        ))
        db.flush()
        if status == StocktakeStatus.APPROVED and diff != 0:
            move = InventoryValuationService.post(
                db, material_code=material_code, qty_delta=diff,
                unit_cost=get_cost(db, material_code),
                source_type="STOCKTAKE", source_ref=number, operator="system",
            )
            db.add(MaterialTransaction(
                transaction_number=f"TXN-{number}",
                material_code=material_code,
                transaction_type="ADJUSTMENT",
                quantity=diff,
                unit="PCS",
                reference_number=number,
                reference_type="STOCKTAKE",
                warehouse=warehouse,
                transaction_date=biz_date,
                operator="system",
                remarks=f"盘点调整 {number}",
                created_by="system",
            ))
            if move is not None and float(move.amount or 0) > 0:
                amount = float(move.amount)
                lines = None
                if diff > 0:
                    lines = [
                        ("1405", amount, 0, f"盘盈调整 {number}"),
                        ("5001", 0, amount, f"盘盈调整 {number}"),
                    ]
                gl_post(
                    db, "STOCK_ADJUST", number, amount=amount, lines=lines,
                    summary=f"盘点调整 {number}", operator="system", entry_date=biz_date,
                )
        created += 1

    # ── 3) 调拨单 + 确认（调出/调入两笔流水，总量不变） ─────────────
    for number, date_str, material_code, from_wh, to_wh, qty, status in TRANSFERS:
        biz_date = _dt(date_str)
        db.add(StockTransfer(
            transfer_number=number,
            from_warehouse_code=from_wh,
            to_warehouse_code=to_wh,
            material_code=material_code,
            quantity=Decimal(qty),
            status=status,
            transfer_date=biz_date,
            remarks="库存演示种子：跨月调拨",
            created_by="system",
        ))
        db.flush()
        if status == StockTransferStatus.CONFIRMED:
            for warehouse_code, delta, txn_type, ref_type in (
                (from_wh, -Decimal(qty), "TRANSFER_OUT", "STOCK_TRANSFER_OUT"),
                (to_wh, Decimal(qty), "TRANSFER_IN", "STOCK_TRANSFER_IN"),
            ):
                db.add(MaterialTransaction(
                    transaction_number=f"TXN-{number}-{txn_type}",
                    material_code=material_code,
                    transaction_type=txn_type,
                    quantity=delta,
                    unit="PCS",
                    reference_number=number,
                    reference_type=ref_type,
                    warehouse=warehouse_code,
                    transaction_date=biz_date,
                    operator="system",
                    remarks=f"调拨 {number} {'调出' if delta < 0 else '调入'} {warehouse_code}",
                    created_by="system",
                ))
        created += 1

    # ── 4) 领料出库估值流水（跨月、OUT 方向） ───────────────────────
    for source_ref, date_str, material_code, qty in ISSUE_MOVES:
        move = InventoryValuationService.post(
            db, material_code=material_code, qty_delta=-Decimal(qty),
            source_type="MATERIAL_ISSUE", source_ref=source_ref, operator="system",
        )
        gl_post(
            db, "MATERIAL_ISSUE", source_ref, amount=float(move.amount),
            summary=f"演示领料 {source_ref}", operator="system", entry_date=_dt(date_str),
        )
        created += 1

    db.flush()
    return created
