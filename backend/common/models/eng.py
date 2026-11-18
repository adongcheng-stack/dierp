"""
ENG模块数据模型 - 工程管理
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum
from backend.common.models.base import BaseModel


class BOMStatus(str, Enum):
    """BOM状态"""
    NEW = "NEW"
    REVIEWING = "REVIEWING"
    RELEASED = "RELEASED"
    PRODUCING = "PRODUCING"
    OBSOLETE = "OBSOLETE"


class RoutingStatus(str, Enum):
    """工艺路线状态"""
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    OBSOLETE = "OBSOLETE"


class MIStatus(str, Enum):
    """MI状态"""
    DRAFT = "DRAFT"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    RELEASED = "RELEASED"
    OBSOLETE = "OBSOLETE"


class BOM(BaseModel):
    """BOM表"""
    __tablename__ = "boms"
    
    bom_number = Column(String(50), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    parent_material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    plant_id = Column(String(50))  # 工厂/生产地点
    bom_type = Column(String(20), default="PRODUCTION")  # 生产/工程/成本
    base_quantity = Column(Numeric(15, 4), default=1)
    base_uom = Column(String(20), default="PNL")
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime)
    status = Column(SQLEnum(BOMStatus), default=BOMStatus.NEW)
    description = Column(Text)
    
    # 关联
    parent_material = relationship("Material", foreign_keys=[parent_material_code])
    items = relationship("BOMItem", back_populates="bom", cascade="all, delete-orphan")
    production_versions = relationship("ProductionVersion", back_populates="bom")


class BOMItem(BaseModel):
    """BOM明细表"""
    __tablename__ = "bom_items"
    
    bom_number = Column(String(50), ForeignKey("boms.bom_number"), nullable=False)
    line_number = Column(Integer, nullable=False)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    item_category = Column(String(50))  # STOCK_ITEM / SUB_ASSEMBLY / CONSUMABLE 等
    quantity = Column(Numeric(15, 4), nullable=False)  # 单机用量
    unit = Column(String(20), nullable=False)
    scrap_rate = Column(Numeric(10, 2))  # 损耗率%
    calculation_formula = Column(String(100))  # 计算公式标识
    layer_code = Column(String(50))  # PCB层码/位置
    material_type = Column(String(50))  # COPPER_FOIL / PREPREG / CORE / ... 或工序步骤
    process_step = Column(String(50))  # 后工序步骤如 SOLDER_MASK
    remarks = Column(String(500))
    
    # 关联
    bom = relationship("BOM", back_populates="items")
    # material = relationship("Material", back_populates="bom_items", foreign_keys=[material_code])  # 暂时注释，避免循环依赖


class Routing(BaseModel):
    """工艺路线表"""
    __tablename__ = "routings"
    
    routing_id = Column(String(50), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    description = Column(String(500))
    plant_id = Column(String(50), nullable=False)
    base_unit = Column(String(20), default="PNL")
    base_quantity = Column(Numeric(15, 2), default=1)
    units_per_panel = Column(Integer, default=1)
    panel_size = Column(String(50))
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime)
    status = Column(SQLEnum(RoutingStatus), default=RoutingStatus.DRAFT)
    change_request_no = Column(String(50))  # 工程变更单号（审计追踪）
    
    # 关联
    material = relationship("Material")
    operations = relationship("RoutingOperation", back_populates="routing", cascade="all, delete-orphan", order_by="RoutingOperation.operation_no")
    production_versions = relationship("ProductionVersion", back_populates="routing")


class RoutingOperation(BaseModel):
    """工艺路线工序表"""
    __tablename__ = "routing_operations"
    
    routing_id = Column(String(50), ForeignKey("routings.routing_id"), nullable=False)
    operation_no = Column(String(20), nullable=False)
    operation_code = Column(String(50), nullable=False)
    operation_name = Column(String(200), nullable=False)
    operation_type = Column(String(50), nullable=False)  # internal, external, quality
    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), nullable=False)
    sop_link = Column(String(255))  # 作业指导书链接
    
    # 时间参数（单位：分钟）
    setup_time = Column(Numeric(10, 2), default=0)  # 调机时间
    machine_time = Column(Numeric(10, 2), default=0)  # 机器时间
    labor_time = Column(Numeric(10, 2), default=0)  # 人工时间
    queue_time = Column(Numeric(10, 2), default=0)  # 排队缓冲
    
    # 控制逻辑
    cost_relevant = Column(Boolean, default=True)
    scheduling_relevant = Column(Boolean, default=True)
    needs_reporting = Column(Boolean, default=True)  # 需报工 / confirmationRequired
    auto_deduct_material = Column(Boolean, default=False)  # 自动倒扣料 / allowAutoBackflush
    trigger_quality_check = Column(Boolean, default=False)  # 触发质检 / qualityInspection
    
    # 外协参数
    service_code = Column(String(50))  # 服务代码
    planned_delivery_days = Column(Numeric(10, 2))  # 计划交期（天）
    estimated_unit_price = Column(Numeric(15, 2))  # 预估单价
    estimated_currency = Column(String(10))  # 预估货币
    suggested_supplier = Column(String(100))  # 建议供应商
    generate_purchase_req = Column(Boolean, default=False)  # 自动生成采购申请

    # 质检参数
    inspection_plan_id = Column(String(100))  # 检验计划
    sampling_rate = Column(Numeric(10, 2))  # 抽检率%
    verification_logic = Column(String(50))  # BLOCK_ON_FAIL 等
    
    # 质检参数
    inspection_plan = Column(String(50))  # 检验计划
    sampling_rate = Column(Numeric(5, 2))  # 抽样率（%）
    inspection_type = Column(String(50))  # 检验类型：full, sample, skip
    
    sop_url = Column(String(500))  # SOP文档链接
    remarks = Column(Text)
    
    # 关联
    routing = relationship("Routing", back_populates="operations")
    work_center = relationship("WorkCenter")


class MI(BaseModel):
    """MI表（制造指令）"""
    __tablename__ = "mis"
    
    mi_number = Column(String(50), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    description = Column(String(500))
    status = Column(SQLEnum(MIStatus), default=MIStatus.DRAFT)
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime)
    # 移除content字段，改为使用mi_instructions表存储指令项
    
    # 关联
    material = relationship("Material")
    production_versions = relationship("ProductionVersion", back_populates="mi")
    instructions = relationship("MIInstruction", back_populates="mi", cascade="all, delete-orphan", order_by="MIInstruction.sequence")


class MIInstruction(BaseModel):
    """MI指令项表"""
    __tablename__ = "mi_instructions"
    
    mi_number = Column(String(50), ForeignKey("mis.mi_number"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)  # 序号（指令的执行顺序）
    operation_code = Column(String(50))  # 工序代码（参考工艺路线工序）
    operation_name = Column(String(200))  # 工序名称（参考工艺路线工序）
    instruction_type = Column(String(100))  # 指令类型，如：开料、钻孔、电镀、线路、阻焊、表面处理、成型等
    instruction_content = Column(Text)  # 指令内容，详细的工序内容描述
    description = Column(String(500))  # 说明，对指令的补充说明
    
    # 关联
    mi = relationship("MI", back_populates="instructions")
    
    # 唯一约束：同一MI下序号唯一
    __table_args__ = (
        UniqueConstraint('mi_number', 'sequence', name='uq_mi_instruction_mi_sequence'),
        {'extend_existing': True}
    )


class ProductionVersion(BaseModel):
    """生产版本表（BOM+工艺路线+MI组合）"""
    __tablename__ = "production_versions"
    
    production_version_id = Column(String(50), unique=True, nullable=False, index=True)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    bom_number = Column(String(50), ForeignKey("boms.bom_number"), nullable=False)
    routing_id = Column(String(50), ForeignKey("routings.routing_id"), nullable=False)
    mi_number = Column(String(50), ForeignKey("mis.mi_number"), nullable=True)  # MI可选
    version = Column(String(20), nullable=False)
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime)
    status = Column(String(50), default="ACTIVE")
    description = Column(Text)
    
    # 关联
    material = relationship("Material")
    bom = relationship("BOM", back_populates="production_versions")
    routing = relationship("Routing", back_populates="production_versions")
    mi = relationship("MI", back_populates="production_versions")

