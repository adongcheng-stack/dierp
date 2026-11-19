"""baseline: 既有库结构基线（create_all 时代的表全部视作已存在）

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-11-19

空迁移 + alembic stamp head：为既有库打上版本标记。
此后所有结构变更一律通过 `alembic revision --autogenerate` 生成、
`alembic upgrade head` 应用；env.py 的 include_object 白名单保证
历史遗留表（workflows 等）不会被误删。
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
