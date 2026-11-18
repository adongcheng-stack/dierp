"""
PP模块数据模型 - 生产计划与控制
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum
from backend.common.models.base import BaseModel
from datetime import datetime


class WorkCenterType(str, Enum):
    """工作中心类型"""
    MACHINE = "MACHINE"  # 单台机器
    MACHINE_GROUP = "MACHINE_GROUP"  # 机组
    LABOR = "LABOR"  # 人工工位
    PRODUCTION_LINE = "PRODUCTION_LINE"  # 产线


class WorkCenterStatus(str, Enum):
    """工作中心状态"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    IN_MAINTENANCE = "IN_MAINTENANCE"


class ProductionOrderStatus(str, Enum):
    """生产订单状态"""
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class OperationReportStatus(str, Enum):
    """工序报工状态"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class WorkCenter(BaseModel):
    """工作中心表"""
    __tablename__ = "work_centers"
    __table_args__ = (
        # 为work_center_id添加唯一约束，用于自引用外键
        {'extend_existing': True}
    )
    
    work_center_id = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200), nullable=False)
    work_center_type = Column(String(50), nullable=False)  # MACHINE, MACHINE_GROUP, LABOR, PRODUCTION_LINE
    plant_id = Column(String(50), nullable=False)
    status = Column(SQLEnum(WorkCenterStatus), default=WorkCenterStatus.ACTIVE)
    # 自引用外键 - 使用work_center_id作为引用（需要唯一约束）
    parent_work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id", use_alter=True, name="fk_work_center_parent"))
    hierarchy_level = Column(Integer, default=1)
    
    # 基础与调度数据
    work_center_category = Column(String(50))  # 工作中心类别
    usage = Column(String(50))  # 用途：PP01, PM01, QM01
    standard_value_key = Column(String(50))  # 标准值码
    control_key = Column(String(50))  # 控制码
    queue_time = Column(Numeric(10, 2), default=0)  # 排队时间（小时）
    wait_time = Column(Numeric(10, 2), default=0)  # 等待时间（小时）
    move_time = Column(Numeric(10, 2), default=0)  # 传送时间（小时）
    
    # 产能数据
    capacity_category = Column(String(50))  # 能力类别
    factory_calendar_id = Column(String(50))  # 工厂日历ID
    shift_start_time = Column(String(10))  # 班次开始时间
    shift_finish_time = Column(String(10))  # 班次结束时间
    break_time = Column(Numeric(10, 2), default=0)  # 休息时间（小时）
    capacity_utilization = Column(Numeric(5, 2), default=100)  # 产能利用率（%）
    number_of_capacities = Column(Integer, default=1)  # 能力数量
    capacity_formula_setup = Column(String(50))
    capacity_formula_processing = Column(String(50))
    capacity_formula_teardown = Column(String(50))
    
    # 成本核算数据
    cost_center_id = Column(String(50))  # 成本中心代码
    activity_types = Column(Text)  # JSON 数组
    
    # PCB行业特定数据
    process_category = Column(String(50))  # 工艺类别：DRILLING, PLATING, ETCHING等
    technical_attributes = Column(Text)  # 技术属性（JSON格式）
    
    # 关联
    parent = relationship("WorkCenter", remote_side=[work_center_id])
    operations = relationship("RoutingOperation", back_populates="work_center")
    operation_reports = relationship("OperationReport", back_populates="work_center")


class ProductionOrder(BaseModel):
    """生产订单表"""
    __tablename__ = "production_orders"
    
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    sales_order_number = Column(String(50), ForeignKey("sales_orders.order_number"), nullable=False)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    production_version_id = Column(String(50), ForeignKey("production_versions.production_version_id"))
    quantity = Column(Numeric(15, 2), nullable=False)  # 生产数量
    unit = Column(String(20), nullable=False)  # 生产单位
    planned_start_date = Column(DateTime)
    planned_finish_date = Column(DateTime)
    actual_start_date = Column(DateTime)
    actual_finish_date = Column(DateTime)
    status = Column(SQLEnum(ProductionOrderStatus), default=ProductionOrderStatus.DRAFT)
    lot_number = Column(String(50))  # LOT卡号
    remarks = Column(Text)
    
    # 新增字段：关联的销售订单数量和单位转换
    sales_quantity = Column(Numeric(15, 2))  # 关联的销售订单数量
    sales_unit = Column(String(20))  # 关联的销售订单单位
    conversion_factor = Column(Numeric(15, 4))  # 单位转换系数
    
    # 关联（延迟导入避免循环依赖）
    # sales_order = relationship("SalesOrder", back_populates="production_orders")
    # material = relationship("Material")
    # production_version = relationship("ProductionVersion")
    # material_issues = relationship("MaterialIssue", back_populates="production_order")
    operation_reports = relationship("OperationReport", back_populates="production_order")


class OperationReport(BaseModel):
    """工序报工表"""
    __tablename__ = "operation_reports"
    
    report_number = Column(String(50), unique=True, nullable=False, index=True)
    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), nullable=False)
    lot_number = Column(String(50))  # LOT卡号
    routing_operation_id = Column(Integer, ForeignKey("routing_operations.id"))
    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), nullable=False)
    operation_no = Column(String(20), nullable=False)
    operation_name = Column(String(200))
    
    # 报工数量
    reported_quantity = Column(Numeric(15, 2), nullable=False)
    good_quantity = Column(Numeric(15, 2))  # 良品数量
    scrap_quantity = Column(Numeric(15, 2), default=0)  # 报废数量
    
    # 报工时间
    setup_time = Column(Numeric(10, 2), default=0)  # 实际调机时间（分钟）
    machine_time = Column(Numeric(10, 2), default=0)  # 实际机器时间（分钟）
    labor_time = Column(Numeric(10, 2), default=0)  # 实际人工时间（分钟）
    
    # 报工信息
    reported_by = Column(String(50), nullable=False)  # 报工人
    reported_at = Column(DateTime, nullable=False)
    status = Column(SQLEnum(OperationReportStatus), default=OperationReportStatus.PENDING)
    remarks = Column(Text)
    
    # 关联
    production_order = relationship("ProductionOrder", back_populates="operation_reports")
    work_center = relationship("WorkCenter", back_populates="operation_reports")
    routing_operation = relationship("RoutingOperation")


class ProductionProgress(BaseModel):
    """生产进度表（用于看板）"""
    __tablename__ = "production_progress"
    
    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), nullable=False)
    operation_no = Column(String(20), nullable=False)
    operation_name = Column(String(200))
    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"))
    planned_quantity = Column(Numeric(15, 2), nullable=False)
    completed_quantity = Column(Numeric(15, 2), default=0)
    in_progress_quantity = Column(Numeric(15, 2), default=0)
    completion_rate = Column(Numeric(5, 2), default=0)  # 完成率（%）
    planned_start_time = Column(DateTime)
    planned_finish_time = Column(DateTime)
    actual_start_time = Column(DateTime)
    actual_finish_time = Column(DateTime)
    status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED
    
    # 关联
    production_order = relationship("ProductionOrder")
    work_center = relationship("WorkCenter")


class LotCard(BaseModel):
    """LOT卡表"""
    __tablename__ = "lot_cards"
    __table_args__ = (
        # 确保production_order_number唯一，保证1:1关系
        {'extend_existing': True}
    )
    
    lot_number = Column(String(50), unique=True, nullable=False, index=True)
    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), nullable=False, unique=True)  # 唯一约束保证1:1关系
    mi_number = Column(String(50), ForeignKey("mis.mi_number"), nullable=False)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    quantity = Column(Numeric(15, 2), nullable=False)  # 数量
    unit = Column(String(20), nullable=False)  # 单位
    status = Column(String(50), default="ACTIVE")  # ACTIVE, COMPLETED, CANCELLED
    # 移除mi_content字段，改为使用lot_card_instructions表存储指令项
    completed_at = Column(DateTime)
    remarks = Column(Text)
    
    # 关联
    production_order = relationship("ProductionOrder", uselist=False)  # 一对一关系
    instructions = relationship("LotCardInstruction", back_populates="lot_card", cascade="all, delete-orphan", order_by="LotCardInstruction.sequence")
    # mi = relationship("MI")  # 延迟导入避免循环依赖


class LotCardInstruction(BaseModel):
    """LOT卡指令项表"""
    __tablename__ = "lot_card_instructions"
    
    lot_number = Column(String(50), ForeignKey("lot_cards.lot_number"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)  # 序号（指令的执行顺序）
    operation_code = Column(String(50))  # 工序代码（参考工艺路线工序）
    operation_name = Column(String(200))  # 工序名称（参考工艺路线工序）
    instruction_type = Column(String(100))  # 指令类型，如：开料、钻孔、电镀、线路、阻焊、表面处理、成型等
    instruction_content = Column(Text)  # 指令内容，详细的工序内容描述
    description = Column(String(500))  # 说明，对指令的补充说明
    
    # 关联
    lot_card = relationship("LotCard", back_populates="instructions")
    
    # 唯一约束：同一LOT卡下序号唯一
    __table_args__ = (
        UniqueConstraint('lot_number', 'sequence', name='uq_lot_card_instruction_lot_sequence'),
        {'extend_existing': True}
    )

