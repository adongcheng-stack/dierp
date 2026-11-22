"""把数据库中的财务闭环演示数据导出到前端 mock 快照。

配合 finance_seed.seed_finance_demo 使用：先 reset_demo，再运行本脚本，
即可保证离线演示包与后端真实种子同构（check_demo_parity 会校验关键事实）。

Run: python backend/scripts/export_finance_snapshot.py
"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime
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
from backend.common.models.mm import MaterialTransaction  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    FiscalPeriod,
    InventoryValuation,
    JournalEntry,
    JournalLine,
    PaymentAllocation,
    Receipt,
    ReceiptAllocation,
    ReceivableEntry,
    SalesInvoice,
    Stocktake,
    StockTransfer,
    SupplierInvoice,
    SupplierPayment,
    ValuationMove,
    Warehouse,
)

SNAPSHOT = project_root / "frontend" / "src" / "mock" / "snapshot.json"


def _value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _dump(rows, columns, id_base):
    out = []
    for index, row in enumerate(rows, start=1):
        item = {"id": id_base + index, "is_deleted": bool(getattr(row, "is_deleted", False))}
        for column in columns:
            item[column] = _value(getattr(row, column, None))
        out.append(item)
    return out


def main() -> int:
    db = SessionLocal()
    try:
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

        collections = [
            ("salesInvoices", SalesInvoice, [
                "invoice_number", "sales_order_number", "delivery_number", "customer_id",
                "customer_name", "amount", "currency", "status", "invoice_date", "due_date",
                "received_amount", "remarks", "created_by", "created_at", "updated_by", "updated_at",
            ], 920000),
            ("receivableEntries", ReceivableEntry, [
                "entry_number", "invoice_number", "customer_id", "entry_type", "amount",
                "entry_date", "reference_number", "remarks", "created_by", "created_at",
            ], 930000),
            ("receipts", Receipt, [
                "receipt_number", "customer_id", "customer_name", "amount", "receipt_date",
                "method", "status", "remarks", "created_by", "created_at",
            ], 931000),
            ("receiptAllocations", ReceiptAllocation, [
                "receipt_number", "invoice_number", "allocated_amount", "remarks",
            ], 932000),
            ("supplierInvoices", SupplierInvoice, [
                "invoice_number", "purchase_order_number", "supplier_id", "supplier_name",
                "amount", "tax_amount", "status", "invoice_date", "remarks", "created_by", "created_at",
            ], 933000),
            ("supplierPayments", SupplierPayment, [
                "payment_number", "supplier_id", "supplier_name", "amount", "payment_date",
                "method", "status", "remarks", "created_by", "created_at",
            ], 934000),
            ("paymentAllocations", PaymentAllocation, [
                "payment_number", "invoice_number", "allocated_amount", "remarks",
            ], 935000),
            ("glJournalEntries", JournalEntry, [
                "entry_number", "entry_date", "period_code", "status", "source_type",
                "source_ref", "remarks", "created_by", "created_at",
            ], 941000),
            ("glJournalLines", JournalLine, [
                "entry_number", "line_number", "account_code", "debit", "credit", "summary",
            ], 942000),
            ("glFiscalPeriods", FiscalPeriod, [
                "period_code", "start_date", "end_date", "status", "created_at",
            ], 943000),
            # 库存域：仓库 / 盘点 / 调拨 / 估值流水 / 库存流水
            ("warehouses", Warehouse, [
                "warehouse_code", "warehouse_name", "location", "is_active",
                "remarks", "created_by", "created_at",
            ], 950000),
            ("stocktakes", Stocktake, [
                "stocktake_number", "material_code", "warehouse", "book_qty",
                "counted_qty", "diff", "status", "stocktake_date", "remarks",
                "created_by", "created_at", "updated_by", "updated_at",
            ], 951000),
            ("stockTransfers", StockTransfer, [
                "transfer_number", "from_warehouse_code", "to_warehouse_code",
                "material_code", "quantity", "status", "transfer_date", "remarks",
                "created_by", "created_at", "updated_by", "updated_at",
            ], 952000),
            ("valuationMoves", ValuationMove, [
                "move_number", "material_code", "direction", "qty", "unit_cost",
                "amount", "balance_qty", "balance_amount", "source_type",
                "source_ref", "reversal_of", "created_by", "created_at",
            ], 953000),
            ("inventoryValuations", InventoryValuation, [
                "material_code", "qty", "amount", "avg_cost", "last_cost",
                "updated_by", "updated_at",
            ], 954000),
            ("materialTransactions", MaterialTransaction, [
                "transaction_number", "material_code", "transaction_type", "quantity",
                "unit", "reference_number", "reference_type", "warehouse",
                "transaction_date", "operator", "remarks", "created_by", "created_at",
            ], 955000),
        ]
        for name, model, columns, id_base in collections:
            rows = db.query(model).order_by(model.id).all()
            data[name] = _dump(rows, columns, id_base)
            print(f"[OK] {name}: {len(rows)} 条")

        data["version"] = int(data.get("version", 0)) + 1
        data["generatedAt"] = datetime.now().isoformat(timespec="seconds")
        SNAPSHOT.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[OK] snapshot 已更新，version={data['version']}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
