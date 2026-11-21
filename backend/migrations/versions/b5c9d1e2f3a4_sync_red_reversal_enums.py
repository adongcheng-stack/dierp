"""sync red-reversal enums (receipt/GL) and entry_type comment

Revision ID: b5c9d1e2f3a4
Revises: 4f768566fd42
Create Date: 2026-11-20 17:50:00
"""
from alembic import op
import sqlalchemy as sa

revision = "b5c9d1e2f3a4"
down_revision = "4f768566fd42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL 枚举类型需显式追加值，否则写入 RECEIPT_REVERSE 会报非法枚举值
    op.execute("ALTER TYPE receivableentrytype ADD VALUE IF NOT EXISTS 'RECEIPT_REVERSE'")
    op.execute("ALTER TYPE glsourcetype ADD VALUE IF NOT EXISTS 'RECEIPT_PAID_REVERSE'")
    # 与本体 planning.yaml 的列注释保持一致（alembic check 依赖此项）
    op.alter_column(
        "receivable_entries",
        "entry_type",
        existing_type=sa.Enum(
            "INVOICE", "RECEIPT", "ADJUST", "RECEIPT_REVERSE",
            name="receivableentrytype",
        ),
        existing_nullable=True,
        comment="流水类型(INVOICE/RECEIPT/ADJUST/RECEIPT_REVERSE)",
    )


def downgrade() -> None:
    # 枚举值无法安全删除（可能已被数据引用），仅还原注释
    op.alter_column(
        "receivable_entries",
        "entry_type",
        existing_type=sa.Enum(
            "INVOICE", "RECEIPT", "ADJUST", "RECEIPT_REVERSE",
            name="receivableentrytype",
        ),
        existing_nullable=True,
        comment="流水类型(INVOICE/RECEIPT/ADJUST)",
    )
