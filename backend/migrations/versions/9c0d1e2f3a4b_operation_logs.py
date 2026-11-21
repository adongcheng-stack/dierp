"""create operation log table (audit trail, axiom A19)

Revision ID: 9c0d1e2f3a4b
Revises: b5c9d1e2f3a4
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "9c0d1e2f3a4b"
down_revision = "b5c9d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False, comment="请求 ID，串联一次 HTTP 调用"),
        sa.Column("username", sa.String(length=50), nullable=True, comment="操作人；匿名请求为 null"),
        sa.Column("role", sa.String(length=50), nullable=True, comment="操作角色"),
        sa.Column("method", sa.String(length=10), nullable=False, comment="HTTP 方法"),
        sa.Column("path", sa.String(length=500), nullable=False, comment="请求路径（不含查询串）"),
        sa.Column("status_code", sa.Integer(), nullable=False, comment="响应状态码"),
        sa.Column("client_ip", sa.String(length=64), nullable=True, comment="客户端 IP"),
        sa.Column("detail", sa.Text(), nullable=True, comment="可选补充信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operation_logs_id"), "operation_logs", ["id"], unique=False)
    op.create_index(op.f("ix_operation_logs_request_id"), "operation_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_operation_logs_username"), "operation_logs", ["username"], unique=False)
    op.create_index(op.f("ix_operation_logs_created_at"), "operation_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operation_logs_created_at"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_username"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_request_id"), table_name="operation_logs")
    op.drop_index(op.f("ix_operation_logs_id"), table_name="operation_logs")
    op.drop_table("operation_logs")
