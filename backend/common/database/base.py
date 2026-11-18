"""
数据库基础配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库连接配置
# 使用参数方式解析，避免URL编码问题
import urllib.parse

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:123456@localhost:5432/hserp_mvp"
)

# 解析连接字符串为参数
try:
    parsed = urllib.parse.urlparse(DATABASE_URL)
    user = parsed.username or "postgres"
    password = parsed.password or "123456"
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    database = parsed.path.lstrip('/') or "hserp_mvp"
    
    # 使用URL编码的密码重新构建连接字符串，确保特殊字符正确处理
    safe_password = urllib.parse.quote(password, safe='')
    safe_url = f"postgresql://{user}:{safe_password}@{host}:{port}/{database}"
    
    engine = create_engine(
        safe_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"client_encoding": "utf8"}
    )
except Exception as e:
    # 如果解析失败，使用默认值
    print(f"Warning: Could not parse DATABASE_URL: {e}")
    print("Using default connection settings")
    engine = create_engine(
        "postgresql://postgres:123456@localhost:5432/hserp_mvp",
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"client_encoding": "utf8"}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

