"""
数据迁移脚本：补齐指令表缺失的工序字段

背景
----
MIInstruction / LotCardInstruction 两个模型在开发过程中增加了
`operation_code`（工序代码）与 `operation_name`（工序名称）两列，
但数据库 `mi_instructions` / `lot_card_instructions` 表没有同步新增，
导致：

  - GET  /api/eng/mis            500 Internal Server Error
  - GET  /api/pp/lot-cards/*     500 Internal Server Error

（psycopg2.errors.UndefinedColumn: 列 mi_instructions.operation_code 不存在）

本脚本
----
1. 幂等检查两列是否已存在
2. 不存在则 ALTER TABLE ADD COLUMN（均为可空字段，不影响存量数据）
3. 打印执行结果

使用方法
----
    cd D:\\project\\erp\\backend
    $env:PYTHONPATH = "D:\\project\\erp"
    python DBScript\\migration_add_instruction_operation_fields.py
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.common.database.base import DATABASE_URL  # noqa: E402


# (表名, [(列名, 类型), ...])
TARGETS = [
    ("mis", [("content", "VARCHAR(500)")]),
    ("lot_cards", [("mi_content", "TEXT")]),
    ("mi_instructions", [
        ("operation_code", "VARCHAR(50)"),
        ("operation_name", "VARCHAR(200)"),
    ]),
    ("lot_card_instructions", [
        ("operation_code", "VARCHAR(50)"),
        ("operation_name", "VARCHAR(200)"),
    ]),
]


def main() -> int:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    added, skipped = [], []
    with engine.begin() as conn:
        for table, columns in TARGETS:
            if table not in inspector.get_table_names():
                skipped.append(f"{table}: 表不存在，跳过")
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, coltype in columns:
                if name in existing:
                    skipped.append(f"{table}.{name}: 已存在")
                    continue
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {coltype}'))
                added.append(f"{table}.{name}")

    print("=== 指令表字段迁移完成 ===")
    print(f"新增列: {added if added else '无'}")
    print(f"跳过项: {skipped if skipped else '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())