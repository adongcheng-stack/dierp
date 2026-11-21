"""
GENERATED FILE - DO NOT EDIT BY HAND.
Source: ontology/model/admin.yaml (version 1.0.0)
Ontology: https://dierp.local/ontology/erp/v1#
Regenerate: python backend/ontology/generate_models.py
"""

from sqlalchemy import Column, ForeignKey, Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from enum import Enum
from backend.common.models.base import BaseModel


# ======================================================================
# 枚举（来自 ontology/src/mappings.json，唯一事实源）
# ======================================================================

class UserRole(str, Enum):
    """UserRole"""
    SALES = "SALES"
    SALES_MANAGER = "SALES_MANAGER"
    ENGINEER = "ENGINEER"
    PLANNER = "PLANNER"
    PRODUCTION = "PRODUCTION"
    WAREHOUSE = "WAREHOUSE"
    FINANCE = "FINANCE"
    GENERAL_MANAGER = "GENERAL_MANAGER"
    ADMIN = "ADMIN"

class DepartmentStatus(str, Enum):
    """DepartmentStatus"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class DepartmentType(str, Enum):
    """DepartmentType"""
    COMPANY = "COMPANY"
    DIVISION = "DIVISION"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    WORKSHOP = "WORKSHOP"

class MenuType(str, Enum):
    """MenuType"""
    DIRECTORY = "DIRECTORY"
    MENU = "MENU"
    BUTTON = "BUTTON"

class MenuStatus(str, Enum):
    """MenuStatus"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ParamType(str, Enum):
    """ParamType"""
    STRING = "STRING"
    INT = "INT"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"

class LoginStatus(str, Enum):
    """LoginStatus"""
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class Department(BaseModel):
    """部门（组织架构树节点）"""
    __tablename__ = "departments"

    code = Column(String(50), nullable=False, unique=True, index=True, comment="部门编码")

    name = Column(String(100), nullable=False, comment="部门名称")

    parent_id = Column(Integer, ForeignKey("departments.id"), index=True, comment="上级部门 ID（自引用）")

    level = Column(Integer, default=1, comment="层级（根为 1）")

    department_type = Column(SQLEnum(DepartmentType), default=DepartmentType.DEPARTMENT, comment="部门类型")

    manager = Column(String(100), comment="部门负责人")

    contact_phone = Column(String(30), comment="联系电话")

    sort_order = Column(Integer, default=0, comment="排序号")

    status = Column(SQLEnum(DepartmentStatus), index=True, default=DepartmentStatus.ACTIVE, comment="状态")

    established_date = Column(Date, comment="成立日期")

    remark = Column(Text)



class Menu(BaseModel):
    """系统菜单（路由与按钮权限声明）"""
    __tablename__ = "menus"

    code = Column(String(80), nullable=False, unique=True, index=True, comment="菜单编码")

    name = Column(String(100), nullable=False, comment="菜单名称")

    parent_id = Column(Integer, ForeignKey("menus.id"), index=True, comment="上级菜单 ID（自引用）")

    path = Column(String(200), comment="路由地址")

    component = Column(String(200), comment="组件路径")

    icon = Column(String(100), comment="图标名")

    menu_type = Column(SQLEnum(MenuType), default=MenuType.MENU, comment="菜单类型")

    permission = Column(String(120), comment="权限标识（如 sd:customer:list）")

    sort_order = Column(Integer, default=0, comment="排序号")

    visible = Column(Boolean, default=True, comment="是否可见")

    status = Column(SQLEnum(MenuStatus), index=True, default=MenuStatus.ACTIVE, comment="状态")



class RoleMenu(BaseModel):
    """角色-菜单授权"""
    __tablename__ = "role_menus"

    role_code = Column(SQLEnum(UserRole), nullable=False, index=True, comment="角色编码（UserRole 枚举）")

    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False, index=True, comment="菜单 ID")



class SystemParameter(BaseModel):
    """系统参数"""
    __tablename__ = "system_parameters"

    param_key = Column(String(100), nullable=False, unique=True, index=True, comment="参数键")

    param_name = Column(String(100), nullable=False, comment="参数名称")

    param_value = Column(Text, comment="参数值")

    param_type = Column(SQLEnum(ParamType), default=ParamType.STRING, comment="参数类型")

    param_desc = Column(String(300), comment="参数说明")

    is_system = Column(Boolean, default=False, comment="是否系统内置（内置不可删）")

    remark = Column(Text)



class LoginLog(BaseModel):
    """登录日志"""
    __tablename__ = "login_logs"

    username = Column(String(50), nullable=False, index=True, comment="登录账号")

    role = Column(String(50), comment="登录角色")

    login_status = Column(SQLEnum(LoginStatus), nullable=False, index=True, comment="登录结果")

    message = Column(String(300), comment="结果说明")

    ip_address = Column(String(64), comment="来源 IP")

    user_agent = Column(String(500), comment="浏览器标识")

    login_time = Column(DateTime, nullable=False, index=True, comment="登录时间")

