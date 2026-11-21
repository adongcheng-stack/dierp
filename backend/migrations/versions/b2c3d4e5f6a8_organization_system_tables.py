"""create organization & system management tables (admin overlay)

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]


def upgrade() -> None:
    # 部门树（自引用）
    op.create_table(
        "departments",
        *_base_columns(),
        sa.Column("code", sa.String(length=50), nullable=False, comment="部门编码"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="部门名称"),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("department_type", sa.Enum("COMPANY", "DIVISION", "DEPARTMENT", "TEAM", "WORKSHOP", name="departmenttype"), nullable=True),
        sa.Column("manager", sa.String(length=100), nullable=True),
        sa.Column("contact_phone", sa.String(length=30), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "INACTIVE", name="departmentstatus"), nullable=True),
        sa.Column("established_date", sa.Date(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("id", "code", "parent_id", "status"):
        op.create_index(f"ix_departments_{name}", "departments", [name], unique=(name == "code"))

    # 菜单树（自引用）
    op.create_table(
        "menus",
        *_base_columns(),
        sa.Column("code", sa.String(length=80), nullable=False, comment="菜单编码"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="菜单名称"),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("menus.id"), nullable=True),
        sa.Column("path", sa.String(length=200), nullable=True),
        sa.Column("component", sa.String(length=200), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("menu_type", sa.Enum("DIRECTORY", "MENU", "BUTTON", name="menutype"), nullable=True),
        sa.Column("permission", sa.String(length=120), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("visible", sa.Boolean(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "INACTIVE", name="menustatus"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("id", "code", "parent_id", "status"):
        op.create_index(f"ix_menus_{name}", "menus", [name], unique=(name == "code"))

    # 角色-菜单授权
    op.create_table(
        "role_menus",
        *_base_columns(),
        sa.Column("role_code", postgresql.ENUM("SALES", "SALES_MANAGER", "ENGINEER", "PLANNER", "PRODUCTION", "WAREHOUSE", "FINANCE", "GENERAL_MANAGER", "ADMIN", name="userrole", create_type=False), nullable=False),
        sa.Column("menu_id", sa.Integer(), sa.ForeignKey("menus.id"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_menus_id", "role_menus", ["id"])
    op.create_index("ix_role_menus_role_code", "role_menus", ["role_code"])
    op.create_index("ix_role_menus_menu_id", "role_menus", ["menu_id"])
    op.create_unique_constraint("uq_role_menu", "role_menus", ["role_code", "menu_id"])

    # 系统参数
    op.create_table(
        "system_parameters",
        *_base_columns(),
        sa.Column("param_key", sa.String(length=100), nullable=False),
        sa.Column("param_name", sa.String(length=100), nullable=False),
        sa.Column("param_value", sa.Text(), nullable=True),
        sa.Column("param_type", sa.Enum("STRING", "INT", "BOOLEAN", "JSON", name="paramtype"), nullable=True),
        sa.Column("param_desc", sa.String(length=300), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("id", "param_key"):
        op.create_index(f"ix_system_parameters_{name}", "system_parameters", [name], unique=(name == "param_key"))

    # 登录日志
    op.create_table(
        "login_logs",
        *_base_columns(),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("login_status", sa.Enum("SUCCESS", "FAIL", name="loginstatus"), nullable=False),
        sa.Column("message", sa.String(length=300), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("login_time", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("id", "username", "login_status", "login_time"):
        op.create_index(f"ix_login_logs_{name}", "login_logs", [name])


def downgrade() -> None:
    for table in ("login_logs", "system_parameters", "role_menus", "menus", "departments"):
        op.drop_table(table)
    for enum_name in ("loginstatus", "paramtype", "userrole", "menustatus", "menutype", "departmentstatus", "departmenttype"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
