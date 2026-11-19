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

# MVP 时代由手写 SQL / 一次性脚本创建的表：结构在库里，模型只是「够用」的映射，
# 双方在注释、索引、可空性上长期不一致。这些表由手写脚本自己管理，
# 不纳入 Alembic 比对，否则 `alembic check` 永远红、autogenerate 会生成
# 删除注释/删除约束一类破坏性脚本。
# 若将来要改这些表的结构，先做一次「收养迁移」（把它们对齐后从本集合移除）。
LEGACY_UNMANAGED_TABLES = {
    "factory_product_mappings",
    "lot_card_instructions",
    "lot_cards",
    "mi_instructions",
}


def _managed(table_name: str) -> bool:
    return table_name in Base.metadata.tables and table_name not in LEGACY_UNMANAGED_TABLES


def include_object(obj, name, type_, reflected, compare_to):
    """白名单：只管理应用元数据里、且未被标记为遗留的表/对象。

    - 表：必须在 Base.metadata 中登记且不在遗留集合；
    - 索引 / 约束 / 列：MVP 手写脚本创建、元数据中没有的对象
      （reflected=True 且 compare_to=None）一律忽略，避免
      `drop_index idx_sales_order_production_version` 这类破坏性操作。
    """
    if type_ == "table":
        return _managed(name)
    if reflected and compare_to is None:
        return False
    table = getattr(obj, "table", None)
    if table is not None:
        return _managed(table.name)
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
