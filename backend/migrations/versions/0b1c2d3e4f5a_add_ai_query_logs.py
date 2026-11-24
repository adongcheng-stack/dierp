"""create ai_query_logs table (AI 问答审计)

Revision ID: 0b1c2d3e4f5a
Revises: c3d4e5f6a8b9
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0b1c2d3e4f5a"
down_revision = "c3d4e5f6a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_query_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False, comment="本次问答链路 ID"),
        sa.Column("request_id", sa.String(length=36), nullable=True, comment="关联 operation_logs.request_id"),
        sa.Column("username", sa.String(length=50), nullable=True),
        sa.Column("role", sa.String(length=30), nullable=True),
        sa.Column("question", sa.Text(), nullable=True, comment="AI_LOG_QUESTION=false 时为 NULL"),
        sa.Column("question_sha256", sa.String(length=64), nullable=True, comment="关闭原文时用于去重与趋势"),
        sa.Column("intent_code", sa.String(length=50), nullable=True),
        sa.Column("intent_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, comment="OK / REJECTED_* / FAILED"),
        sa.Column("error_code", sa.String(length=50), nullable=True, comment="与设计 §7.5 的错误码一一对应"),
        sa.Column("shacl_status", sa.String(length=20), nullable=True, comment="passed / partial / skipped / failed"),
        sa.Column("reject_reason", sa.String(length=300), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True, comment="只存表名/单号/IRI，不存整行数据"),
        sa.Column("feedback_score", sa.Integer(), nullable=True, comment="-1 / 0 / 1"),
        sa.Column("feedback_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_query_logs_id"), "ai_query_logs", ["id"], unique=False)
    op.create_index(op.f("ix_ai_query_logs_trace_id"), "ai_query_logs", ["trace_id"], unique=True)
    op.create_index(op.f("ix_ai_query_logs_request_id"), "ai_query_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_ai_query_logs_username"), "ai_query_logs", ["username"], unique=False)
    op.create_index(op.f("ix_ai_query_logs_intent_code"), "ai_query_logs", ["intent_code"], unique=False)
    op.create_index(op.f("ix_ai_query_logs_status"), "ai_query_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_query_logs_status"), table_name="ai_query_logs")
    op.drop_index(op.f("ix_ai_query_logs_intent_code"), table_name="ai_query_logs")
    op.drop_index(op.f("ix_ai_query_logs_username"), table_name="ai_query_logs")
    op.drop_index(op.f("ix_ai_query_logs_request_id"), table_name="ai_query_logs")
    op.drop_index(op.f("ix_ai_query_logs_trace_id"), table_name="ai_query_logs")
    op.drop_index(op.f("ix_ai_query_logs_id"), table_name="ai_query_logs")
    op.drop_table("ai_query_logs")
