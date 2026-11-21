"""add INVOICE_REVERSE / SALES_INVOICE_REVERSED enums

Revision ID: a1b2c3d4e5f7
Revises: 9c0d1e2f3a4b
"""
from __future__ import annotations

from alembic import op

revision = "a1b2c3d4e5f7"
down_revision = "9c0d1e2f3a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE receivableentrytype ADD VALUE IF NOT EXISTS 'INVOICE_REVERSE'"
    )
    op.execute(
        "ALTER TYPE glsourcetype ADD VALUE IF NOT EXISTS 'SALES_INVOICE_REVERSED'"
    )


def downgrade() -> None:
    # PostgreSQL 不支持安全删除枚举值，保留新增值以免历史数据失效
    pass
