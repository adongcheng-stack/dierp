"""
GENERATED FILE - DO NOT EDIT BY HAND.
Source: ontology/model/dashboard.yaml (version 1.0.0)
Ontology: https://dierp.local/ontology/erp/v1#
Regenerate: python backend/ontology/generate_models.py
"""

from sqlalchemy import Column, ForeignKey, Boolean, Numeric, String
from sqlalchemy import Enum as SQLEnum
from enum import Enum
from backend.common.models.base import BaseModel


# ======================================================================
# 枚举（来自 ontology/src/mappings.json，唯一事实源）
# ======================================================================

class DashboardScope(str, Enum):
    """DashboardScope"""
    HOME = "HOME"
    MANAGEMENT = "MANAGEMENT"
    PRODUCTION = "PRODUCTION"
    PROGRESS = "PROGRESS"
    FINANCE = "FINANCE"
    SALES = "SALES"

class AlertOperator(str, Enum):
    """AlertOperator"""
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"

class AlertLevel(str, Enum):
    """AlertLevel"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class TimeWindow(str, Enum):
    """TimeWindow"""
    ALL = "ALL"
    LAST30 = "LAST30"
    LAST90 = "LAST90"
    LAST365 = "LAST365"


class DashboardRule(BaseModel):
    """驾驶舱指标预警规则"""
    __tablename__ = "dashboard_rules"

    code = Column(String(80), nullable=False, unique=True, index=True, comment="规则编码")

    name = Column(String(100), nullable=False, comment="规则名称")

    scope = Column(SQLEnum(DashboardScope), nullable=False, index=True, comment="适用驾驶舱")

    metric = Column(String(120), nullable=False, comment="KPI 路径（如 equipment.oee）")

    operator = Column(SQLEnum(AlertOperator), default=AlertOperator.LT, comment="比较运算符")

    threshold = Column(Numeric(15, 4), nullable=False, comment="阈值")

    level = Column(SQLEnum(AlertLevel), default=AlertLevel.WARNING, comment="预警级别")

    message = Column(String(300), comment="预警话术模板")

    default_window = Column(SQLEnum(TimeWindow), default=TimeWindow.ALL, comment="默认时间窗口")

    enabled = Column(Boolean, default=True, comment="是否启用")

