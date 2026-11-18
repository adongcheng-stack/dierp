"""
基础数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from backend.common.database.base import Base


class BaseModel(Base):
    """基础模型类"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(50))
    updated_by = Column(String(50))
    is_deleted = Column(Boolean, default=False, nullable=False)

