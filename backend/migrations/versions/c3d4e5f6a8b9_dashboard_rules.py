"""create dashboard_rules table (cockpit alert rules)

Revision ID: c3d4e5f6a8b9
Revises: b2c3d4e5f6a8
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a8b9"
down_revision = "b2c3d4e5f6a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.Enum("HOME", "MANAGEMENT", "PRODUCTION", "PROGRESS", "FINANCE", "SALES", name="dashboardscope"), nullable=False),
        sa.Column("metric", sa.String(length=120), nullable=False),
        sa.Column("operator", sa.Enum("LT", "LTE", "GT", "GTE", name="alertoperator"), nullable=False),
        sa.Column("threshold", sa.Numeric(15, 4), nullable=False),
        sa.Column("level", sa.Enum("INFO", "WARNING", "CRITICAL", name="alertlevel"), nullable=False),
        sa.Column("message", sa.String(length=300), nullable=True),
        sa.Column("default_window", sa.Enum("ALL", "LAST30", "LAST90", "LAST365", name="timewindow"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, unique in (("id", False), ("code", True), ("scope", False)):
        op.create_index(f"ix_dashboard_rules_{name}", "dashboard_rules", [name], unique=unique)


def downgrade() -> None:
    op.drop_table("dashboard_rules")
    for enum_name in ("timewindow", "alertlevel", "alertoperator", "dashboardscope"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
