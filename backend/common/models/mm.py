"""
MM模块数据模型 - 物料管理
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.common.models.base import BaseModel


class Material(BaseModel):
    """物料表"""
    __tablename__ = "materials"
    
    material_code = Column(String(50), unique=True, nullable=False, index=True)
    material_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)  # 物料分类
    specification = Column(String(500))  # 规格型号
    unit = Column(String(20), nullable=False)  # 计量单位
    brand = Column(String(100))  # 品牌/厂家
    min_package = Column(String(100))  # 最小包装
    current_stock = Column(Numeric(15, 2), default=0)  # 当前库存
    safety_stock = Column(Numeric(15, 2), default=0)  # 安全库存
    description = Column(Text)
    # 扩展字段
    material_type = Column(String(20))  # FG/RAW/SEMI
    status = Column(String(20))  # ACTIVE/OBSOLETE/DRAFT
    version = Column(String(50))
    base_unit = Column(String(20))
    production_unit = Column(String(20))
    conversion_factor = Column(Numeric(15, 4))  # 1 production_unit = ? base_unit
    # PCB工程属性
    layer_count = Column(Integer)
    board_thickness = Column(Numeric(10, 3))
    thickness_tolerance = Column(String(50))
    copper_weight = Column(String(50))
    material_grade = Column(String(100))
    surface_finish = Column(String(50))
    solder_mask_color = Column(String(50))
    silkscreen_color = Column(String(50))
    impedance_control = Column(Boolean, default=False)
    min_line_space = Column(Numeric(10, 3))
    min_hole_size = Column(Numeric(10, 3))
    unit_length = Column(Numeric(10, 3))
    unit_width = Column(Numeric(10, 3))
    panel_length = Column(Numeric(10, 3))
    panel_width = Column(Numeric(10, 3))
    units_per_panel = Column(Integer)
    # 供应链计划
    procurement_type = Column(String(20))  # MAKE/BUY/SUB
    mrp_controller = Column(String(50))
    lead_time_days = Column(Integer)
    max_lot_size = Column(Integer)
    min_order_quantity = Column(Integer)
    order_multiple = Column(Integer)
    abc_class = Column(String(10))
    # 库存管理
    shelf_life_days = Column(Integer)
    default_location = Column(String(100))
    storage_condition = Column(String(100))
    batch_tracking = Column(Boolean, default=False)
    # 成本
    valuation_method = Column(String(50))
    standard_price = Column(Numeric(15, 2))
    currency = Column(String(10))
    last_cost_update = Column(DateTime)
    
    # 关联（延迟导入避免循环依赖）
    # bom_items = relationship("BOMItem", back_populates="material", foreign_keys="BOMItem.material_code")
    material_issues = relationship("MaterialIssue", back_populates="material")


class MaterialIssue(BaseModel):
    """生产领料表"""
    __tablename__ = "material_issues"
    
    issue_number = Column(String(50), unique=True, nullable=False, index=True)
    production_order_number = Column(String(50), nullable=False)  # 延迟外键，避免循环依赖
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    quantity = Column(Numeric(15, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    issued_by = Column(String(50), nullable=False)  # 领料人
    issued_at = Column(DateTime, nullable=False)
    warehouse = Column(String(50))  # 仓库
    remarks = Column(Text)
    
    # 关联（延迟导入避免循环依赖）
    # production_order = relationship("ProductionOrder", back_populates="material_issues")
    material = relationship("Material", back_populates="material_issues")


class MaterialTransaction(BaseModel):
    """物料事务表（库存变动记录）"""
    __tablename__ = "material_transactions"
    
    transaction_number = Column(String(50), unique=True, nullable=False, index=True)
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    transaction_type = Column(String(50), nullable=False)  # ISSUE, RECEIPT, ADJUSTMENT
    quantity = Column(Numeric(15, 2), nullable=False)  # 正数表示入库，负数表示出库
    unit = Column(String(20), nullable=False)
    reference_number = Column(String(50))  # 关联单据号（如领料单号）
    reference_type = Column(String(50))  # 关联单据类型
    warehouse = Column(String(50))
    transaction_date = Column(DateTime, nullable=False)
    operator = Column(String(50), nullable=False)
    remarks = Column(Text)
    
    # 关联
    material = relationship("Material")

