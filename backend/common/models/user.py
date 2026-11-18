"""
用户模型
"""
from sqlalchemy import Column, String, Integer, Boolean, Enum as SQLEnum
from enum import Enum
from backend.common.models.base import BaseModel


class UserRole(str, Enum):
    """用户角色"""
    SALES = "SALES"  # 销售
    SALES_MANAGER = "SALES_MANAGER"  # 销售经理
    ENGINEER = "ENGINEER"  # 工程
    PLANNER = "PLANNER"  # 计划
    PRODUCTION = "PRODUCTION"  # 生产
    WAREHOUSE = "WAREHOUSE"  # 仓库
    FINANCE = "FINANCE"  # 财务
    GENERAL_MANAGER = "GENERAL_MANAGER"  # 总经理
    ADMIN = "ADMIN"  # 系统管理员


class User(BaseModel):
    """用户表"""
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(SQLEnum(UserRole), nullable=False)
    department = Column(String(50))
    is_active = Column(Boolean, default=True, nullable=False)
    phone = Column(String(20))

