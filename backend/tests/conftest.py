"""pytest 共享夹具：SQLite 内存库 + 全量模型建表。

模型均为方言无关类型（已探测无 JSONB/ARRAY 等），
可在内存 SQLite 上跑引擎级单元测试，不依赖真实 PostgreSQL。
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.common.database.base import Base  # noqa: E402

# 先导入全部模型模块，避免 mapper 关系解析失败（RoutingOperation 等）
from backend.common.models import eng, mm, pp, sd, planning, audit, admin  # noqa: E402,F401


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
