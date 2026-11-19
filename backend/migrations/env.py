"""Alembic 迁移环境：复用后端数据库配置与模型元数据。

- 目标库 URL 取自 backend.common.database.base（DATABASE_URL 环境变量约定一致）；
- target_metadata 挂全量模型（需先 import 全部模型模块，避免 mapper 解析失败）；
- include_object 白名单：只管理 Base.metadata 中登记的表，
  历史遗留表（如 workflows）不纳入迁移，避免 autogenerate 产生误删。
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 让 alembic 能 import backend.*
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.common.database.base import Base, engine  # noqa: E402
from backend.common.models import eng, mm, pp, sd, user, planning  # noqa: E402,F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """白名单：只管理应用元数据里的表/对象。"""
    if type_ == "table":
        return name in Base.metadata.tables
    return True


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本，不连库。"""
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        # MVP 时代手写表存在历史漂移（索引/注释/遗留列），关闭类型比对以降噪；
        # autogenerate 产物必须人工审查后再 upgrade（详见 docs 升级方案 N4 节）。
        compare_type=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接连库执行。"""
    connectable = engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
