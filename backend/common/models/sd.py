"""
SD模块数据模型 - 销售与分销
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from enum import Enum
from backend.common.models.base import BaseModel


class CustomerStatus(str, Enum):
    """客户状态"""
    DRAFT = "DRAFT"
    PENDING_SALES_MANAGER = "PENDING_SALES_MANAGER"  # 待销售总监/销售经理审批
    PENDING_FINANCE = "PENDING_FINANCE"  # 待财务总监/应收会计审批
    PENDING_GENERAL_MANAGER = "PENDING_GENERAL_MANAGER"  # 待总经理审批
    PENDING_APPROVAL = "PENDING_APPROVAL"  # 兼容老值，不再使用
    FROZEN = "FROZEN"  # 已建档（冻结），等待激活
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    INACTIVE = "INACTIVE"


class QuotationStatus(str, Enum):
    """报价单状态"""
    DRAFT = "DRAFT"
    PENDING_SALES = "PENDING_SALES"  # 待销售审核
    PENDING_FINANCE = "PENDING_FINANCE"  # 待财务审核
    PENDING_GENERAL_MANAGER = "PENDING_GENERAL_MANAGER"  # 待总经办审核
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CUSTOMER_CONFIRMED = "CUSTOMER_CONFIRMED"  # 客户已确认
    LINKED = "LINKED"  # 已关联（已关联到销售订单）
    CANCELLED = "CANCELLED"


class SalesOrderStatus(str, Enum):
    """销售订单状态"""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"  # 待订单评审
    REVIEWING = "REVIEWING"  # 评审中
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    RECONCILED = "RECONCILED"  # 已对账
    CLOSED = "CLOSED"  # 已关闭
    CANCELLED = "CANCELLED"


class Customer(BaseModel):
    """客户表"""
    __tablename__ = "customers"
    
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    legal_name = Column(String(200), nullable=False)
    trade_name = Column(String(200))
    tax_id = Column(String(50))
    customer_industry = Column(String(50))
    customer_website = Column(String(200))
    customer_status = Column(SQLEnum(CustomerStatus), default=CustomerStatus.DRAFT)
    credit_limit = Column(Numeric(15, 2))
    
    # 关联
    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    contacts = relationship("CustomerContact", back_populates="customer", cascade="all, delete-orphan")
    partner_functions = relationship("CustomerPartnerFunction", back_populates="customer", cascade="all, delete-orphan")
    sales_data = relationship("CustomerSalesData", back_populates="customer", cascade="all, delete-orphan")
    quotations = relationship("Quotation", back_populates="customer")
    sales_orders = relationship("SalesOrder", back_populates="customer")


class CustomerAddress(BaseModel):
    """客户地址表"""
    __tablename__ = "customer_addresses"
    
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    address_type = Column(String(50), nullable=False)  # HEADQUARTERS, PLANT, WAREHOUSE, BILLING
    detail_address = Column(String(500), nullable=False)
    location = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(50), default="中国")
    province = Column(String(50))
    city = Column(String(50))
    district = Column(String(50))
    is_default_shipping = Column(Boolean, default=False)
    is_default_billing = Column(Boolean, default=False)
    
    # 关联
    customer = relationship("Customer", back_populates="addresses")


class CustomerContact(BaseModel):
    """客户联系人表"""
    __tablename__ = "customer_contacts"
    
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    is_primary_contact = Column(Boolean, default=False)
    contact_name = Column(String(100), nullable=False)
    contact_role = Column(String(100))
    contact_department = Column(String(100))
    contact_phone = Column(String(20))
    contact_email = Column(String(100))
    
    # 关联
    customer = relationship("Customer", back_populates="contacts")


class CustomerPartnerFunction(BaseModel):
    """客户合作属性/角色表"""
    __tablename__ = "customer_partner_functions"
    
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    partner_role = Column(String(50), nullable=False)  # SOLD_TO, SHIP_TO, BILL_TO, PAYER
    partner_id = Column(String(50))
    partner_name = Column(String(200))
    partnership_description = Column(String(500))
    
    # 关联
    customer = relationship("Customer", back_populates="partner_functions")


class CustomerSalesData(BaseModel):
    """客户销售数据表"""
    __tablename__ = "customer_sales_data"
    
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    sales_organization = Column(String(50))
    account_manager_name = Column(String(100))
    sales_assistant_name = Column(String(100))
    trading_currency = Column(String(10), default="CNY")
    primary_trade_country = Column(String(50))
    incoterms = Column(String(50))
    shipping_conditions = Column(String(100))
    
    # 关联
    customer = relationship("Customer", back_populates="sales_data")


class FactoryProductMapping(BaseModel):
    """本厂编号映射表"""
    __tablename__ = "factory_product_mappings"
    
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    factory_product_number = Column(String(50), nullable=False)  # 本厂编号
    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False)
    production_version_id = Column(String(50), ForeignKey("production_versions.production_version_id"))
    is_default = Column(Boolean, default=True)  # 是否为默认映射
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime)
    
    # 关联（延迟导入避免循环依赖）
    customer = relationship("Customer")
    # material = relationship("Material")
    # production_version = relationship("ProductionVersion")
    
    __table_args__ = (
        UniqueConstraint('customer_id', 'factory_product_number', 'effective_date', name='uq_factory_product'),
    )


class Quotation(BaseModel):
    """报价单表"""
    __tablename__ = "quotations"
    
    quotation_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product_number = Column(String(50), nullable=False)  # 14位编号，如HS1004ENIGAB01
    product_series = Column(String(50))  # 产品系列
    layers = Column(Integer)  # 层数
    quantity = Column(Numeric(15, 2), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="CNY")
    
    # 价格明细（可选字段，兼容旧数据）
    engineering_fee = Column(Numeric(15, 2), nullable=True)  # 工程费
    board_material_fee_amount = Column(Numeric(15, 2), nullable=True)  # 板材费（金额）
    via_fee = Column(Numeric(15, 2), nullable=True)  # 过孔费
    estimated_total_price = Column(Numeric(15, 2), nullable=True)  # 预估总价
    valid_until = Column(DateTime)
    status = Column(SQLEnum(QuotationStatus), default=QuotationStatus.DRAFT)
    customer_confirmed = Column(Boolean, default=False)
    customer_confirmed_at = Column(DateTime)
    remarks = Column(Text)
    
    # 审核信息
    sales_approver = Column(String(50))
    sales_approved_at = Column(DateTime)
    finance_approver = Column(String(50))
    finance_approved_at = Column(DateTime)
    general_manager_approver = Column(String(50))
    general_manager_approved_at = Column(DateTime)
    
    # ========== 产品配置信息 ==========
    # 基本信息
    product_category = Column(String(50))  # 产品类别：FR-4, 罗杰斯高频板, CEM-1等
    hdi_type = Column(String(50))  # HDI盲埋孔：无, 1阶, 2阶, 3阶
    
    # 板材信息
    board_material_brand = Column(String(100))  # 板材品牌：建滔KB (A级)
    board_material_model = Column(String(100))  # 板材型号：KB6164
    board_material_tg = Column(String(50))  # TG值：TG135
    board_material_flame_retardant = Column(String(50))  # 阻燃性：94V-0
    board_material_fee = Column(String(200))  # 指定板材费：不加价/起步价等
    
    # 拼版和出货
    panelization_count = Column(Integer, default=1)  # 拼版款数
    output_format = Column(String(50))  # 出货形式：单片出货, 连片(按文件), 连片(华秋代拼)
    single_piece_length = Column(Numeric(10, 2))  # 单片长度(cm)
    single_piece_width = Column(Numeric(10, 2))  # 单片宽度(cm)
    single_piece_quantity = Column(Numeric(15, 2))  # 单片数量
    single_piece_unit = Column(String(20), default="Pcs")  # 单片数量单位
    process_border_type = Column(String(50))  # 工艺边框类型：无
    process_border_size = Column(Numeric(10, 2))  # 工艺边框尺寸(mm)
    
    # ========== 工艺信息 ==========
    board_thickness = Column(String(20))  # 板子厚度：1.6mm
    outer_copper_thickness = Column(String(20))  # 外层铜厚：1oz
    inner_copper_thickness = Column(String(20))  # 内层铜厚：0.5oz
    min_line_width_spacing = Column(String(20))  # 最小线宽线距：6/6
    line_width_spacing_unit = Column(String(20), default="mil")  # 线宽线距单位
    min_hole_diameter = Column(String(20))  # 最小孔径：0.3
    hole_diameter_unit = Column(String(20), default="mm")  # 孔径单位
    solder_mask_color = Column(String(50))  # 阻焊颜色：绿色
    character_color = Column(String(50))  # 字符颜色：白色
    solder_mask_coverage = Column(String(100))  # 阻焊覆盖：过孔盖油
    holes_in_pads = Column(String(50))  # 盘中孔：无
    surface_finish = Column(String(100))  # 表面处理：有铅喷锡
    lamination_order = Column(String(100))  # 层压顺序：文件中有提供
    impedance = Column(String(50))  # 阻抗：无
    stackup_structure = Column(String(200))  # 叠层结构：无需求
    finger_bevel = Column(String(50))  # 手指斜边：无需
    half_hole = Column(String(50))  # 半孔：无需
    edge_plating = Column(String(50))  # 包边：无需
    press_fit_hole = Column(String(50))  # 压接孔：无需
    test_method = Column(String(100))  # 测试方式：样品免费
    
    # ========== 个性化服务（JSON存储详细配置）==========
    personalized_services = Column(JSON)  # 个性化服务配置JSON
    
    # ========== 地址快递信息 ==========
    shipping_notification = Column(String(50))  # 发货通知：无需/需要
    delivery_note = Column(String(50))  # 送货单：电子版/纸质版
    shipping_address = Column(Text)  # 收货地址
    express_company = Column(String(100))  # 快递公司
    
    # ========== 发票支付信息 ==========
    invoice_type = Column(String(100))  # 开票类型：增值税(普通)发票/数电增值税(专用)发票
    payment_method = Column(String(100))  # 订单支付方式：自动扣款并确认/手动确认支付
    
    # ========== SMT贴片信息 ==========
    smt_patch_required = Column(Boolean, default=False)  # 是否需要华秋SMT贴片
    
    # ========== 报价明细 - 板规格参数 ==========
    utilization_rate = Column(Numeric(10, 4))  # 利用率 (%)
    delivery_length = Column(Numeric(10, 2))  # 出货长 (mm)
    delivery_width = Column(Numeric(10, 2))  # 出货宽 (mm)
    set_per_unit = Column(Integer, default=1)  # SET=U
    material_type = Column(String(50))  # 板材类型
    tg_value = Column(String(50))  # TG值
    finished_board_thickness = Column(String(50))  # 完成板厚
    large_material_spec = Column(String(50))  # 大料规格
    large_material_pnl_count = Column(Integer)  # 大料开PNL数
    pnl_set_count = Column(Integer)  # PNL含SET数
    pnl_length_mm = Column(Numeric(10, 2))  # PNL尺寸MM - 长度
    pnl_width_mm = Column(Numeric(10, 2))  # PNL尺寸MM - 宽度
    core_board_count = Column(Integer)  # 芯板张数
    core_board_spec = Column(String(200))  # 芯板规格
    inner_layer_thickening = Column(Boolean, default=False)  # 内层加厚
    outer_line_width_spacing_limit = Column(Boolean, default=False)  # 外层线宽/距<=3.5mil 完成-基铜>=35
    solder_mask_color_detail = Column(String(50))  # 阻焊颜色（明细用）
    times = Column(Integer, default=1)  # 次数
    specify_sun = Column(Boolean, default=False)  # 指定太阳
    board_thickness_tolerance = Column(Boolean, default=False)  # 板厚公差<+/-10%
    via_plugging = Column(String(50))  # 过孔塞孔
    character_color_detail = Column(String(50))  # 字符颜色（明细用）
    min_drill_bit = Column(String(50))  # 最小钻咀
    set_hole_count = Column(Integer)  # SET孔数
    pcs_conversion = Column(Numeric(10, 2))  # PCS换算
    pnl_conversion = Column(Numeric(10, 2))  # PNL换算
    acceptance_standard = Column(String(50))  # 验收标准
    routing_process = Column(Numeric(10, 2))  # 锣程 (MM)
    v_score_process = Column(Numeric(10, 2))  # V程 (MM/SET)
    hard_gold = Column(Boolean, default=False)  # 硬金(金手指)
    no_positioning_hole_routing = Column(Boolean, default=False)  # 无定位孔锣
    test_points = Column(Integer, default=0)  # 测试点数
    
    # ========== 报价明细 - 加价选项 ==========
    # 常规加价（JSON存储，便于扩展）
    regular_surcharges = Column(JSON)  # 常规加价选项：碳油、蓝胶、高温胶、阻抗要求等
    # 特殊加价
    special_surcharges = Column(JSON)  # 特殊加价选项：跳刀V、沉头孔、额外PP张数等
    # 其他加价
    additional_surcharge_per_m2 = Column(Numeric(15, 2))  # 额外加价/M2
    customer_provides_hf_board = Column(Boolean, default=False)  # 客户提供高频板
    min_customer_consumption = Column(Numeric(15, 2))  # 收客户最低消费
    market_quote_remarks = Column(String(500))  # 市场报价备注
    
    # ========== 报价明细 - 计算结果 ==========
    actual_p_input = Column(Integer)  # 实际投P
    delivery_area = Column(Numeric(15, 4))  # 交货面积 (m²)
    cost_per_pcs = Column(Numeric(15, 4))  # 成本PCS
    cost_per_m2 = Column(Numeric(15, 4))  # 成本平米
    quote_price_per_pcs = Column(Numeric(15, 4))  # 报价pcs价
    quote_price_per_m2 = Column(Numeric(15, 4))  # 报价平米价
    test_fixture = Column(Numeric(15, 2))  # 测试架
    other_costs = Column(Numeric(15, 2))  # 其他费用
    final_total_price = Column(Numeric(15, 2))  # 最终总价
    
    # 关联
    customer = relationship("Customer", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    detail_items = relationship("QuotationDetailItem", back_populates="quotation", cascade="all, delete-orphan")


class QuotationItem(BaseModel):
    """报价单明细表"""
    __tablename__ = "quotation_items"
    
    quotation_number = Column(String(50), ForeignKey("quotations.quotation_number"), nullable=False)
    line_number = Column(Integer, nullable=False)
    material_code = Column(String(50))
    material_name = Column(String(200))
    quantity = Column(Numeric(15, 2))
    unit_price = Column(Numeric(15, 2))
    total_price = Column(Numeric(15, 2))
    remarks = Column(String(500))
    
    # 关联
    quotation = relationship("Quotation", back_populates="items")


class QuotationDetailItem(BaseModel):
    """报价明细工序表 - 存储工序成本明细"""
    __tablename__ = "quotation_detail_items"
    
    quotation_number = Column(String(50), ForeignKey("quotations.quotation_number"), nullable=False)
    process_name = Column(String(200), nullable=False)  # 工序名称
    process_order = Column(Integer, nullable=False)  # 工序顺序
    p_cost_calculation_info = Column(Text)  # P成本计算信息
    p_price = Column(Numeric(15, 4))  # P价格
    delivery_area = Column(Numeric(15, 4))  # 出货面积 (m²)
    process_cost_share = Column(Numeric(10, 4))  # 工序成本占 (%)
    remarks = Column(String(500))
    
    # 关联
    quotation = relationship("Quotation", back_populates="detail_items")


class SalesOrder(BaseModel):
    """销售订单表"""
    __tablename__ = "sales_orders"
    
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    quotation_number = Column(String(50), ForeignKey("quotations.quotation_number"))  # 关联报价单
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product_number = Column(String(50), nullable=False)  # 本厂编号
    quantity = Column(Numeric(15, 2), nullable=False)  # 销售数量
    unit_price = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="CNY")
    delivery_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(SalesOrderStatus), default=SalesOrderStatus.DRAFT)
    is_return_order = Column(Boolean, default=False)  # 是否返单
    remarks = Column(Text)
    
    # 新增字段：物料和生产版本关联
    material_code = Column(String(50), ForeignKey("materials.material_code"))
    production_version_id = Column(String(50), ForeignKey("production_versions.production_version_id"))
    sales_unit = Column(String(20))  # 销售单位
    production_quantity = Column(Numeric(15, 2))  # 生产数量
    production_unit = Column(String(20))  # 生产单位
    conversion_factor = Column(Numeric(15, 4))  # 单位转换系数
    
    # 订单评审信息
    review_status = Column(String(50))  # PENDING, REVIEWING, APPROVED, REJECTED
    sales_reviewed = Column(Boolean, default=False)
    engineering_reviewed = Column(Boolean, default=False)
    material_reviewed = Column(Boolean, default=False)
    finance_reviewed = Column(Boolean, default=False)
    
    # 关联
    customer = relationship("Customer", back_populates="sales_orders")
    quotation = relationship("Quotation")
    # production_orders = relationship("ProductionOrder", back_populates="sales_order")  # 暂时注释，避免循环依赖


class ContractReview(BaseModel):
    """订单评审表"""
    __tablename__ = "contract_reviews"
    
    sales_order_number = Column(String(50), ForeignKey("sales_orders.order_number"), nullable=False)
    reviewer_role = Column(String(50), nullable=False)  # SALES, ENGINEER, MATERIAL, FINANCE
    reviewer = Column(String(50), nullable=False)
    review_result = Column(String(50), nullable=False)  # APPROVED, REJECTED
    review_comment = Column(Text)
    reviewed_at = Column(DateTime, nullable=False)
    
    # 关联
    sales_order = relationship("SalesOrder")

