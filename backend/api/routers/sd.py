"""
SD模块路由 - 销售与分销
"""
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from backend.common.database.base import get_db
from backend.common.models.user import User, UserRole
from backend.api.routers.auth import get_current_user
from backend.common.utils.permissions import require_role
from backend.common.models.sd import (
    Customer, CustomerAddress, CustomerContact, CustomerPartnerFunction,
    CustomerSalesData, FactoryProductMapping, Quotation, QuotationItem, 
    SalesOrder, ContractReview, CustomerStatus, QuotationStatus, SalesOrderStatus
)
from backend.common.models.mm import Material, MaterialTransaction
from backend.common.models.planning import (
    SalesDelivery,
    DeliveryStatus,
    SalesInvoice,
    InvoiceStatus,
    ReceivableEntry,
    ReceivableEntryType,
    Receipt,
    ReceiptAllocation,
)
from backend.common.models.eng import ProductionVersion
from sqlalchemy import or_
from backend.common.utils.number_generator import NumberGenerator
from backend.common.utils.workflow import WorkflowEngine, WorkflowStatus
from backend.services.sales_order_service import SalesOrderService
from backend.common.exceptions import BusinessException

router = APIRouter()


# Pydantic模型
class CustomerPartnerFunctionPayload(BaseModel):
    partner_role: str
    partner_id: Optional[str] = None
    partner_name: Optional[str] = None
    partnership_description: Optional[str] = None


class CustomerAddressPayload(BaseModel):
    address_type: str
    detail_address: str
    location: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = Field(default="中国")
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    is_default_shipping: Optional[bool] = False
    is_default_billing: Optional[bool] = False


class CustomerContactPayload(BaseModel):
    is_primary_contact: Optional[bool] = False
    contact_name: str
    contact_role: Optional[str] = None
    contact_department: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class CustomerSalesDataPayload(BaseModel):
    sales_organization: Optional[str] = None
    account_manager_name: Optional[str] = None
    sales_assistant_name: Optional[str] = None
    trading_currency: Optional[str] = "CNY"
    primary_trade_country: Optional[str] = None
    incoterms: Optional[str] = None
    shipping_conditions: Optional[str] = None


class CustomerCreate(BaseModel):
    customer_id: str
    legal_name: str
    trade_name: Optional[str] = None
    tax_id: Optional[str] = None
    customer_industry: Optional[str] = None
    customer_website: Optional[str] = None
    credit_limit: Optional[float] = None
    customer_status: Optional[str] = None
    partner_functions: Optional[List[CustomerPartnerFunctionPayload]] = []
    customer_addresses: Optional[List[CustomerAddressPayload]] = []
    customer_contacts: Optional[List[CustomerContactPayload]] = []
    sales_data: Optional[List[CustomerSalesDataPayload]] = []


class CustomerUpdate(CustomerCreate):
    pass


class CustomerPartnerFunctionResponse(CustomerPartnerFunctionPayload):
    id: int

    class Config:
        from_attributes = True


class CustomerAddressResponse(CustomerAddressPayload):
    id: int

    class Config:
        from_attributes = True


class CustomerContactResponse(CustomerContactPayload):
    id: int

    class Config:
        from_attributes = True


class CustomerSalesDataResponse(CustomerSalesDataPayload):
    id: int

    class Config:
        from_attributes = True


class CustomerResponse(BaseModel):
    id: int
    customer_id: str
    legal_name: str
    trade_name: Optional[str]
    tax_id: Optional[str] = None
    customer_industry: Optional[str] = None
    customer_website: Optional[str] = None
    credit_limit: Optional[float] = None
    customer_status: str
    partner_functions: List[CustomerPartnerFunctionResponse] = []
    addresses: List[CustomerAddressResponse] = []
    contacts: List[CustomerContactResponse] = []
    sales_data: List[CustomerSalesDataResponse] = []

    class Config:
        from_attributes = True


class QuotationCreate(BaseModel):
    customer_id: str
    product_number: str
    product_series: Optional[str] = None
    layers: Optional[int] = None
    quantity: float
    unit_price: float
    currency: str = "CNY"
    valid_until: Optional[datetime] = None
    remarks: Optional[str] = None
    
    # 价格明细
    engineering_fee: Optional[float] = None  # 工程费
    board_material_fee_amount: Optional[float] = None  # 板材费（金额）
    via_fee: Optional[float] = None  # 过孔费
    estimated_total_price: Optional[float] = None  # 预估总价
    
    # 产品配置信息
    product_category: Optional[str] = None  # 产品类别
    hdi_type: Optional[str] = None  # HDI盲埋孔
    board_material_brand: Optional[str] = None  # 板材品牌
    board_material_model: Optional[str] = None  # 板材型号
    board_material_tg: Optional[str] = None  # TG值
    board_material_flame_retardant: Optional[str] = None  # 阻燃性
    board_material_fee: Optional[str] = None  # 指定板材费
    panelization_count: Optional[int] = 1  # 拼版款数
    output_format: Optional[str] = None  # 出货形式
    single_piece_length: Optional[float] = None  # 单片长度
    single_piece_width: Optional[float] = None  # 单片宽度
    single_piece_quantity: Optional[float] = None  # 单片数量
    single_piece_unit: Optional[str] = "Pcs"  # 单片数量单位
    process_border_type: Optional[str] = None  # 工艺边框类型
    process_border_size: Optional[float] = None  # 工艺边框尺寸
    
    # 工艺信息
    board_thickness: Optional[str] = None  # 板子厚度
    outer_copper_thickness: Optional[str] = None  # 外层铜厚
    inner_copper_thickness: Optional[str] = None  # 内层铜厚
    min_line_width_spacing: Optional[str] = None  # 最小线宽线距
    line_width_spacing_unit: Optional[str] = "mil"  # 线宽线距单位
    min_hole_diameter: Optional[str] = None  # 最小孔径
    hole_diameter_unit: Optional[str] = "mm"  # 孔径单位
    solder_mask_color: Optional[str] = None  # 阻焊颜色
    character_color: Optional[str] = None  # 字符颜色
    solder_mask_coverage: Optional[str] = None  # 阻焊覆盖
    holes_in_pads: Optional[str] = None  # 盘中孔
    surface_finish: Optional[str] = None  # 表面处理
    lamination_order: Optional[str] = None  # 层压顺序
    impedance: Optional[str] = None  # 阻抗
    stackup_structure: Optional[str] = None  # 叠层结构
    finger_bevel: Optional[str] = None  # 手指斜边
    half_hole: Optional[str] = None  # 半孔
    edge_plating: Optional[str] = None  # 包边
    press_fit_hole: Optional[str] = None  # 压接孔
    test_method: Optional[str] = None  # 测试方式
    
    # 个性化服务（JSON格式）
    personalized_services: Optional[dict] = None
    
    # 地址快递信息
    shipping_notification: Optional[str] = None  # 发货通知
    delivery_note: Optional[str] = None  # 送货单
    shipping_address: Optional[str] = None  # 收货地址
    express_company: Optional[str] = None  # 快递公司
    
    # 发票支付信息
    invoice_type: Optional[str] = None  # 开票类型
    payment_method: Optional[str] = None  # 订单支付方式
    
    # SMT贴片信息
    smt_patch_required: Optional[bool] = False  # 是否需要华秋SMT贴片
    
    # ========== 报价明细 - 板规格参数 ==========
    utilization_rate: Optional[float] = None  # 利用率 (%)
    delivery_length: Optional[float] = None  # 出货长 (mm)
    delivery_width: Optional[float] = None  # 出货宽 (mm)
    set_per_unit: Optional[int] = 1  # SET=U
    material_type: Optional[str] = None  # 板材类型
    tg_value: Optional[str] = None  # TG值
    finished_board_thickness: Optional[str] = None  # 完成板厚
    large_material_spec: Optional[str] = None  # 大料规格
    large_material_pnl_count: Optional[int] = None  # 大料开PNL数
    pnl_set_count: Optional[int] = None  # PNL含SET数
    pnl_length_mm: Optional[float] = None  # PNL尺寸MM - 长度
    pnl_width_mm: Optional[float] = None  # PNL尺寸MM - 宽度
    core_board_count: Optional[int] = None  # 芯板张数
    core_board_spec: Optional[str] = None  # 芯板规格
    inner_layer_thickening: Optional[bool] = False  # 内层加厚
    outer_line_width_spacing_limit: Optional[bool] = False  # 外层线宽/距<=3.5mil
    solder_mask_color_detail: Optional[str] = None  # 阻焊颜色（明细用）
    times: Optional[int] = 1  # 次数
    specify_sun: Optional[bool] = False  # 指定太阳
    board_thickness_tolerance: Optional[bool] = False  # 板厚公差<+/-10%
    via_plugging: Optional[str] = None  # 过孔塞孔
    character_color_detail: Optional[str] = None  # 字符颜色（明细用）
    min_drill_bit: Optional[str] = None  # 最小钻咀
    set_hole_count: Optional[int] = None  # SET孔数
    pcs_conversion: Optional[float] = None  # PCS换算
    pnl_conversion: Optional[float] = None  # PNL换算
    acceptance_standard: Optional[str] = None  # 验收标准
    routing_process: Optional[float] = None  # 锣程 (MM)
    v_score_process: Optional[float] = None  # V程 (MM/SET)
    hard_gold: Optional[bool] = False  # 硬金(金手指)
    no_positioning_hole_routing: Optional[bool] = False  # 无定位孔锣
    test_points: Optional[int] = 0  # 测试点数
    
    # ========== 报价明细 - 加价选项 ==========
    regular_surcharges: Optional[dict] = None  # 常规加价选项（JSON）
    special_surcharges: Optional[dict] = None  # 特殊加价选项（JSON）
    additional_surcharge_per_m2: Optional[float] = None  # 额外加价/M2
    customer_provides_hf_board: Optional[bool] = False  # 客户提供高频板
    min_customer_consumption: Optional[float] = None  # 收客户最低消费
    market_quote_remarks: Optional[str] = None  # 市场报价备注


class QuotationUpdate(QuotationCreate):
    """报价单更新模型（继承QuotationCreate的所有字段）"""
    pass


class QuotationResponse(BaseModel):
    id: int
    quotation_number: str
    customer_id: str
    product_number: str
    product_series: Optional[str] = None
    layers: Optional[int] = None
    quantity: float
    unit_price: float
    total_amount: float
    currency: str
    valid_until: Optional[datetime] = None
    status: str
    remarks: Optional[str] = None
    
    # 价格明细
    engineering_fee: Optional[float] = None  # 工程费
    board_material_fee_amount: Optional[float] = None  # 板材费（金额）
    via_fee: Optional[float] = None  # 过孔费
    estimated_total_price: Optional[float] = None  # 预估总价
    
    # 产品配置信息
    product_category: Optional[str] = None
    hdi_type: Optional[str] = None
    board_material_brand: Optional[str] = None
    board_material_model: Optional[str] = None
    board_material_tg: Optional[str] = None
    board_material_flame_retardant: Optional[str] = None
    board_material_fee: Optional[str] = None
    panelization_count: Optional[int] = None
    output_format: Optional[str] = None
    single_piece_length: Optional[float] = None
    single_piece_width: Optional[float] = None
    single_piece_quantity: Optional[float] = None
    single_piece_unit: Optional[str] = None
    process_border_type: Optional[str] = None
    process_border_size: Optional[float] = None
    
    # 工艺信息
    board_thickness: Optional[str] = None
    outer_copper_thickness: Optional[str] = None
    inner_copper_thickness: Optional[str] = None
    min_line_width_spacing: Optional[str] = None
    line_width_spacing_unit: Optional[str] = None
    min_hole_diameter: Optional[str] = None
    hole_diameter_unit: Optional[str] = None
    solder_mask_color: Optional[str] = None
    character_color: Optional[str] = None
    solder_mask_coverage: Optional[str] = None
    holes_in_pads: Optional[str] = None
    surface_finish: Optional[str] = None
    lamination_order: Optional[str] = None
    impedance: Optional[str] = None
    stackup_structure: Optional[str] = None
    finger_bevel: Optional[str] = None
    half_hole: Optional[str] = None
    edge_plating: Optional[str] = None
    press_fit_hole: Optional[str] = None
    test_method: Optional[str] = None
    
    # 个性化服务
    personalized_services: Optional[dict] = None
    
    # 地址快递信息
    shipping_notification: Optional[str] = None
    delivery_note: Optional[str] = None
    shipping_address: Optional[str] = None
    express_company: Optional[str] = None
    
    # 发票支付信息
    invoice_type: Optional[str] = None
    payment_method: Optional[str] = None
    
    # SMT贴片信息
    smt_patch_required: Optional[bool] = None
    
    class Config:
        from_attributes = True


class SalesOrderCreate(BaseModel):
    quotation_number: Optional[str] = None
    customer_id: str
    product_number: str
    quantity: float
    unit_price: float
    delivery_date: datetime
    is_return_order: bool = False
    remarks: Optional[str] = None
    # 新增字段（可选，如果提供则直接使用，否则自动查找映射）
    material_code: Optional[str] = None
    production_version_id: Optional[str] = None
    sales_unit: Optional[str] = None
    production_quantity: Optional[float] = None
    production_unit: Optional[str] = None
    conversion_factor: Optional[float] = None


class SalesOrderUpdate(BaseModel):
    quotation_number: Optional[str] = None
    customer_id: str
    product_number: str
    quantity: float
    unit_price: float
    delivery_date: datetime
    is_return_order: bool = False
    remarks: Optional[str] = None


class SalesOrderResponse(BaseModel):
    id: int
    order_number: str
    quotation_number: Optional[str] = None
    customer_id: str
    product_number: str
    quantity: float
    unit_price: float
    total_amount: float
    currency: str
    delivery_date: datetime
    # SQLAlchemy 模型里 status 是 SalesOrderStatus 枚举；用枚举类型可避免序列化成 "SalesOrderStatus.APPROVED"
    status: SalesOrderStatus
    is_return_order: bool = False
    remarks: Optional[str] = None
    # 新增字段
    material_code: Optional[str] = None
    production_version_id: Optional[str] = None
    sales_unit: Optional[str] = None
    production_quantity: Optional[float] = None
    production_unit: Optional[str] = None
    conversion_factor: Optional[float] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True


# 本厂编号映射Pydantic模型
class FactoryProductMappingCreate(BaseModel):
    customer_id: str
    factory_product_number: str
    material_code: str
    production_version_id: Optional[str] = None
    is_default: Optional[bool] = True
    effective_date: datetime
    expiry_date: Optional[datetime] = None


class FactoryProductMappingUpdate(BaseModel):
    material_code: Optional[str] = None
    production_version_id: Optional[str] = None
    is_default: Optional[bool] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class FactoryProductMappingResponse(BaseModel):
    id: int
    customer_id: str
    factory_product_number: str
    material_code: str
    production_version_id: Optional[str] = None
    is_default: bool
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# 客户管理
from backend.common.models.user import UserRole


@router.post("/customers", response_model=CustomerResponse, status_code=http_status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建客户"""
    # 检查客户ID是否已存在
    existing = db.query(Customer).filter(Customer.customer_id == customer.customer_id).first()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"客户ID已存在: {customer.customer_id}"
        )
    
    # 新建客户时，状态自动设置为DRAFT，不允许前端指定
    db_customer = Customer(
        customer_id=customer.customer_id,
        legal_name=customer.legal_name,
        trade_name=customer.trade_name,
        tax_id=customer.tax_id,
        customer_industry=customer.customer_industry,
        customer_website=customer.customer_website,
        credit_limit=customer.credit_limit,
        customer_status=CustomerStatus.DRAFT,  # 系统自动设置为DRAFT
        created_by=current_user.username
    )
    db.add(db_customer)
    db.flush()

    # 合作属性/角色
    for pf in customer.partner_functions or []:
        db.add(CustomerPartnerFunction(
            customer_id=db_customer.customer_id,
            partner_role=pf.partner_role,
            partner_id=pf.partner_id,
            partner_name=pf.partner_name,
            partnership_description=pf.partnership_description,
            created_by=current_user.username
        ))

    # 地址
    for addr in customer.customer_addresses or []:
        db.add(CustomerAddress(
            customer_id=db_customer.customer_id,
            address_type=addr.address_type,
            detail_address=addr.detail_address,
            location=addr.location,
            postal_code=addr.postal_code,
            country=addr.country,
            province=addr.province,
            city=addr.city,
            district=addr.district,
            is_default_shipping=addr.is_default_shipping or False,
            is_default_billing=addr.is_default_billing or False,
            created_by=current_user.username
        ))

    # 联系人
    for ct in customer.customer_contacts or []:
        db.add(CustomerContact(
            customer_id=db_customer.customer_id,
            is_primary_contact=ct.is_primary_contact or False,
            contact_name=ct.contact_name,
            contact_role=ct.contact_role,
            contact_department=ct.contact_department,
            contact_phone=ct.contact_phone,
            contact_email=ct.contact_email,
            created_by=current_user.username
        ))

    # 销售数据（允许多组，通常一组）
    for sd in customer.sales_data or []:
        db.add(CustomerSalesData(
            customer_id=db_customer.customer_id,
            sales_organization=sd.sales_organization,
            account_manager_name=sd.account_manager_name,
            sales_assistant_name=sd.sales_assistant_name,
            trading_currency=sd.trading_currency,
            primary_trade_country=sd.primary_trade_country,
            incoterms=sd.incoterms,
            shipping_conditions=sd.shipping_conditions,
            created_by=current_user.username
        ))

    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.post("/customers/{customer_id}/submit")
async def submit_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交客户建档审批，进入销售总监/销售经理节点"""
    from backend.common.utils.status_validator import CustomerStatusValidator
    from backend.common.exceptions import ValidationException
    
    try:
        db_customer = db.query(Customer).filter(
            Customer.customer_id == customer_id,
            Customer.is_deleted == False
        ).first()
        
        if not db_customer:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="客户不存在")
        
        # 检查当前状态是否允许提交
        # 确保状态值是字符串（可能是枚举对象）
        current_status_raw = db_customer.customer_status
        if isinstance(current_status_raw, CustomerStatus):
            current_status = current_status_raw.value
        else:
            current_status = str(current_status_raw) if current_status_raw else CustomerStatus.DRAFT.value
        
        new_status_str = CustomerStatus.PENDING_SALES_MANAGER.value
        
        # 允许的状态：DRAFT, INACTIVE, PENDING_APPROVAL
        allowed_statuses = [CustomerStatus.DRAFT.value, CustomerStatus.INACTIVE.value, CustomerStatus.PENDING_APPROVAL.value]
        if current_status not in allowed_statuses:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"当前状态不允许提交审批: {current_status}，允许的状态: {', '.join(allowed_statuses)}"
            )
        
        # 验证状态流转
        try:
            CustomerStatusValidator.validate_customer_status_transition(
                current_status=current_status,
                new_status=new_status_str
            )
        except ValidationException as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"状态流转不合法: {str(e)}"
            )
        except Exception as e:
            print(f"状态验证错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"状态验证失败: {str(e)}"
            )
        
        db_customer.customer_status = CustomerStatus.PENDING_SALES_MANAGER
        db_customer.updated_by = current_user.username
        db.commit()
        db.refresh(db_customer)
        return {"message": "客户已提交审核", "status": db_customer.customer_status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"提交客户审批错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交客户审批失败: {str(e)}"
        )


@router.post("/customers/{customer_id}/approve")
async def approve_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """按顺序审批客户：销售经理 -> 总经理（财务不参与审批，只负责激活）"""
    from backend.common.utils.status_validator import CustomerStatusValidator
    
    db_customer = db.query(Customer).filter(
        Customer.customer_id == customer_id,
        Customer.is_deleted == False
    ).first()
    
    if not db_customer:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="客户不存在")
    
    # 确保状态值是字符串（可能是枚举对象）
    current_status_raw = db_customer.customer_status
    if isinstance(current_status_raw, CustomerStatus):
        current_status = current_status_raw.value
    else:
        current_status = str(current_status_raw) if current_status_raw else ""
    
    # 审批流程：销售经理 -> 总经理（跳过财务审批）
    if current_status == CustomerStatus.PENDING_SALES_MANAGER.value:
        required_role = UserRole.SALES_MANAGER
        new_status = CustomerStatus.PENDING_GENERAL_MANAGER.value
    elif current_status == CustomerStatus.PENDING_GENERAL_MANAGER.value:
        required_role = UserRole.GENERAL_MANAGER
        new_status = CustomerStatus.FROZEN.value
    else:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"当前状态不允许审批: {current_status}")
    
    # 检查权限：ADMIN角色可以绕过所有限制
    require_role(
        current_user, 
        required_role, 
        f"当前状态需要角色 {required_role.value} 审批"
    )
    
    # 验证状态流转
    try:
        CustomerStatusValidator.validate_customer_status_transition(
            current_status=current_status,
            new_status=new_status
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"状态流转不合法: {str(e)}"
        )
    
    # 设置新状态（使用枚举对象）
    if new_status == CustomerStatus.PENDING_GENERAL_MANAGER.value:
        db_customer.customer_status = CustomerStatus.PENDING_GENERAL_MANAGER
    elif new_status == CustomerStatus.FROZEN.value:
        db_customer.customer_status = CustomerStatus.FROZEN
    
    db_customer.updated_by = current_user.username
    
    try:
        db.commit()
        db.refresh(db_customer)
        return {"message": "客户已审批通过", "status": db_customer.customer_status}
    except Exception as e:
        db.rollback()
        print(f"审批客户错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审批客户失败: {str(e)}"
        )


@router.post("/customers/{customer_id}/reject")
async def reject_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """拒绝客户建档（任一审批节点，财务不参与审批）"""
    from backend.common.utils.status_validator import CustomerStatusValidator
    
    db_customer = db.query(Customer).filter(
        Customer.customer_id == customer_id,
        Customer.is_deleted == False
    ).first()
    
    if not db_customer:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="客户不存在")
    
    # 确保状态值是字符串（可能是枚举对象）
    current_status_raw = db_customer.customer_status
    if isinstance(current_status_raw, CustomerStatus):
        current_status = current_status_raw.value
    else:
        current_status = str(current_status_raw) if current_status_raw else ""
    
    # 拒绝流程：销售经理或总经理可以拒绝（财务不参与审批）
    if current_status == CustomerStatus.PENDING_SALES_MANAGER.value:
        required_role = UserRole.SALES_MANAGER
    elif current_status == CustomerStatus.PENDING_GENERAL_MANAGER.value:
        required_role = UserRole.GENERAL_MANAGER
    else:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"当前状态不允许拒绝: {current_status}")
    
    # 检查权限：ADMIN角色可以绕过所有限制
    require_role(
        current_user, 
        required_role, 
        f"当前状态需要角色 {required_role.value} 审批"
    )
    
    # 验证状态流转
    try:
        CustomerStatusValidator.validate_customer_status_transition(
            current_status=current_status,
            new_status=CustomerStatus.INACTIVE.value
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"状态流转不合法: {str(e)}"
        )
    
    db_customer.customer_status = CustomerStatus.INACTIVE
    db_customer.updated_by = current_user.username
    db.commit()
    db.refresh(db_customer)
    return {"message": "客户建档已拒绝", "status": db_customer.customer_status}


@router.post("/customers/{customer_id}/activate")
async def activate_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """应收会计激活客户（从冻结状态激活）"""
    from backend.common.utils.status_validator import CustomerStatusValidator
    from backend.common.exceptions import ValidationException
    
    try:
        db_customer = db.query(Customer).filter(
            Customer.customer_id == customer_id,
            Customer.is_deleted == False
        ).first()
        
        if not db_customer:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="客户不存在")
        
        # 确保状态值是字符串（可能是枚举对象）
        current_status_raw = db_customer.customer_status
        if isinstance(current_status_raw, CustomerStatus):
            current_status = current_status_raw.value
        else:
            current_status = str(current_status_raw) if current_status_raw else CustomerStatus.FROZEN.value
        
        if current_status != CustomerStatus.FROZEN.value:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"当前状态不允许激活: {current_status}，只有已建档(冻结)状态可以激活")
        
        # 检查权限：ADMIN角色可以绕过所有限制
        require_role(current_user, UserRole.FINANCE, "需要财务角色激活客户")
        
        # 验证状态流转
        try:
            CustomerStatusValidator.validate_customer_status_transition(
                current_status=current_status,
                new_status=CustomerStatus.ACTIVE.value
            )
        except ValidationException as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"状态流转不合法: {str(e)}"
            )
        except Exception as e:
            print(f"状态验证错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"状态验证失败: {str(e)}"
            )
        
        db_customer.customer_status = CustomerStatus.ACTIVE
        db_customer.updated_by = current_user.username
        db.commit()
        db.refresh(db_customer)
        return {"message": "客户已激活", "status": db_customer.customer_status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"激活客户错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"激活客户失败: {str(e)}"
        )


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取客户列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import selectinload
    
    query = db.query(Customer).filter(Customer.is_deleted == False)
    if status:
        query = query.filter(Customer.customer_status == status)
    
    # 预加载关联数据，避免N+1查询（如果响应模型需要这些数据）
    # 注意：如果响应模型不需要这些数据，可以注释掉以提升性能
    query = query.options(
        selectinload(Customer.addresses),
        selectinload(Customer.contacts),
        selectinload(Customer.partner_functions),
        selectinload(Customer.sales_data)
    )
    
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.get("/customers/pending-approval", response_model=List[CustomerResponse])
async def list_pending_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户需要审批的客户列表（财务不参与审批，只负责激活）"""
    if current_user.role == UserRole.SALES_MANAGER:
        target_status = CustomerStatus.PENDING_SALES_MANAGER
    elif current_user.role == UserRole.FINANCE:
        # 财务不参与审批，只负责激活冻结状态的客户
        target_status = CustomerStatus.FROZEN
    elif current_user.role == UserRole.GENERAL_MANAGER:
        target_status = CustomerStatus.PENDING_GENERAL_MANAGER
    else:
        return []
    
    customers = db.query(Customer).filter(
        Customer.customer_status == target_status,
        Customer.is_deleted == False
    ).order_by(Customer.created_at.desc()).all()
    return customers


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """获取客户详情（已优化：预加载关联数据）"""
    from sqlalchemy.orm import selectinload
    
    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id,
        Customer.is_deleted == False
    ).options(
        selectinload(Customer.addresses),
        selectinload(Customer.contacts),
        selectinload(Customer.partner_functions),
        selectinload(Customer.sales_data)
    ).first()
    if not customer:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {customer_id}"
        )
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新客户（包含地址、联系人、合作角色、销售数据）"""
    db_customer = db.query(Customer).filter(
        Customer.customer_id == customer_id,
        Customer.is_deleted == False
    ).first()
    if not db_customer:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {customer_id}"
        )

    # 基本信息（客户状态由系统自动管理，不允许前端修改）
    db_customer.legal_name = customer.legal_name
    db_customer.trade_name = customer.trade_name
    db_customer.tax_id = customer.tax_id
    db_customer.customer_industry = customer.customer_industry
    db_customer.customer_website = customer.customer_website
    db_customer.credit_limit = customer.credit_limit
    # 客户状态由系统通过审批流程自动管理，不允许在编辑时修改
    # 状态只能通过 submit/approve/reject/activate 等API变更
    db_customer.updated_by = current_user.username

    # 先清空关联再重建
    db.query(CustomerPartnerFunction).filter(CustomerPartnerFunction.customer_id == customer_id).delete()
    db.query(CustomerAddress).filter(CustomerAddress.customer_id == customer_id).delete()
    db.query(CustomerContact).filter(CustomerContact.customer_id == customer_id).delete()
    db.query(CustomerSalesData).filter(CustomerSalesData.customer_id == customer_id).delete()
    db.flush()

    for pf in customer.partner_functions or []:
        db.add(CustomerPartnerFunction(
            customer_id=db_customer.customer_id,
            partner_role=pf.partner_role,
            partner_id=pf.partner_id,
            partner_name=pf.partner_name,
            partnership_description=pf.partnership_description,
            created_by=current_user.username
        ))

    for addr in customer.customer_addresses or []:
        db.add(CustomerAddress(
            customer_id=db_customer.customer_id,
            address_type=addr.address_type,
            detail_address=addr.detail_address,
            location=addr.location,
            postal_code=addr.postal_code,
            country=addr.country,
            province=addr.province,
            city=addr.city,
            district=addr.district,
            is_default_shipping=addr.is_default_shipping or False,
            is_default_billing=addr.is_default_billing or False,
            created_by=current_user.username
        ))

    for ct in customer.customer_contacts or []:
        db.add(CustomerContact(
            customer_id=db_customer.customer_id,
            is_primary_contact=ct.is_primary_contact or False,
            contact_name=ct.contact_name,
            contact_role=ct.contact_role,
            contact_department=ct.contact_department,
            contact_phone=ct.contact_phone,
            contact_email=ct.contact_email,
            created_by=current_user.username
        ))

    for sd in customer.sales_data or []:
        db.add(CustomerSalesData(
            customer_id=db_customer.customer_id,
            sales_organization=sd.sales_organization,
            account_manager_name=sd.account_manager_name,
            sales_assistant_name=sd.sales_assistant_name,
            trading_currency=sd.trading_currency,
            primary_trade_country=sd.primary_trade_country,
            incoterms=sd.incoterms,
            shipping_conditions=sd.shipping_conditions,
            created_by=current_user.username
        ))

    db.commit()
    db.refresh(db_customer)
    return db_customer


# 报价单管理
@router.post("/quotations", response_model=QuotationResponse, status_code=http_status.HTTP_201_CREATED)
async def create_quotation(
    quotation: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建报价单"""
    from sqlalchemy import inspect
    
    try:
        # 检查客户是否存在
        customer = db.query(Customer).filter(Customer.customer_id == quotation.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"客户不存在: {quotation.customer_id}"
            )
        
        # 生成报价单号
        quotation_number = NumberGenerator.generate_quotation_number(db, quotation.customer_id)
        
        total_amount = quotation.quantity * quotation.unit_price
        
        # 检查数据库表是否有新字段
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('quotations')]
        has_price_fields = all(col in columns for col in ['engineering_fee', 'board_material_fee_amount', 'via_fee', 'estimated_total_price'])
        
        # 构建报价单对象
        quotation_data = {
            'quotation_number': quotation_number,
            'customer_id': quotation.customer_id,
            'product_number': quotation.product_number,
            'product_series': quotation.product_series,
            'layers': quotation.layers,
            'quantity': quotation.quantity,
            'unit_price': quotation.unit_price,
            'total_amount': total_amount,
            'currency': quotation.currency,
            'valid_until': quotation.valid_until,
            'status': QuotationStatus.DRAFT,
            'remarks': quotation.remarks,
            # 产品配置信息
            'product_category': quotation.product_category,
            'hdi_type': quotation.hdi_type,
            'board_material_brand': quotation.board_material_brand,
            'board_material_model': quotation.board_material_model,
            'board_material_tg': quotation.board_material_tg,
            'board_material_flame_retardant': quotation.board_material_flame_retardant,
            'board_material_fee': quotation.board_material_fee,
            'panelization_count': quotation.panelization_count or 1,
            'output_format': quotation.output_format,
            'single_piece_length': quotation.single_piece_length,
            'single_piece_width': quotation.single_piece_width,
            'single_piece_quantity': quotation.single_piece_quantity,
            'single_piece_unit': quotation.single_piece_unit or "Pcs",
            'process_border_type': quotation.process_border_type,
            'process_border_size': quotation.process_border_size,
            # 工艺信息
            'board_thickness': quotation.board_thickness,
            'outer_copper_thickness': quotation.outer_copper_thickness,
            'inner_copper_thickness': quotation.inner_copper_thickness,
            'min_line_width_spacing': quotation.min_line_width_spacing,
            'line_width_spacing_unit': quotation.line_width_spacing_unit or "mil",
            'min_hole_diameter': quotation.min_hole_diameter,
            'hole_diameter_unit': quotation.hole_diameter_unit or "mm",
            'solder_mask_color': quotation.solder_mask_color,
            'character_color': quotation.character_color,
            'solder_mask_coverage': quotation.solder_mask_coverage,
            'holes_in_pads': quotation.holes_in_pads,
            'surface_finish': quotation.surface_finish,
            'lamination_order': quotation.lamination_order,
            'impedance': quotation.impedance,
            'stackup_structure': quotation.stackup_structure,
            'finger_bevel': quotation.finger_bevel,
            'half_hole': quotation.half_hole,
            'edge_plating': quotation.edge_plating,
            'press_fit_hole': quotation.press_fit_hole,
            'test_method': quotation.test_method,
            # 个性化服务
            'personalized_services': quotation.personalized_services,
            # 地址快递信息
            'shipping_notification': quotation.shipping_notification,
            'delivery_note': quotation.delivery_note,
            'shipping_address': quotation.shipping_address,
            'express_company': quotation.express_company,
            # 发票支付信息
            'invoice_type': quotation.invoice_type,
            'payment_method': quotation.payment_method,
            # SMT贴片信息
            'smt_patch_required': quotation.smt_patch_required or False,
            'created_by': current_user.username
        }
        
        # 只有在数据库表有这些字段时才添加价格明细
        if has_price_fields:
            quotation_data['engineering_fee'] = quotation.engineering_fee
            quotation_data['board_material_fee_amount'] = quotation.board_material_fee_amount
            quotation_data['via_fee'] = quotation.via_fee
            quotation_data['estimated_total_price'] = quotation.estimated_total_price
        
        db_quotation = Quotation(**quotation_data)
        db.add(db_quotation)
        db.commit()
        db.refresh(db_quotation)
        
        # 如果数据库表中没有新字段，在返回前设置默认值
        if not has_price_fields:
            db_quotation.engineering_fee = quotation.engineering_fee
            db_quotation.board_material_fee_amount = quotation.board_material_fee_amount
            db_quotation.via_fee = quotation.via_fee
            db_quotation.estimated_total_price = quotation.estimated_total_price
        
        return db_quotation
    except Exception as e:
        db.rollback()
        print(f"创建报价单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建报价单失败: {str(e)}"
        )


@router.get("/quotations", response_model=List[QuotationResponse])
async def list_quotations(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    is_return_order: Optional[bool] = None,  # 是否返单：True=返单（只显示已关联），False=新单（只显示已批准）
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报价单列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload, selectinload
    from sqlalchemy import inspect
    
    try:
        # 检查数据库表是否有新字段
        inspector = inspect(db.bind)
        try:
            columns = [col['name'] for col in inspector.get_columns('quotations')]
        except Exception as e:
            print(f"检查数据库表字段时出错: {e}")
            db.rollback()
            columns = []
        has_price_fields = all(col in columns for col in ['engineering_fee', 'board_material_fee_amount', 'via_fee', 'estimated_total_price'])
        
        # 构建查询
        query = db.query(Quotation)
        if customer_id:
            query = query.filter(Quotation.customer_id == customer_id)
        if status:
            query = query.filter(Quotation.status == status)
        
        # 根据返单/新单过滤报价单
        if is_return_order is not None:
            if is_return_order:
                # 返单：只显示已关联的报价单
                query = query.filter(Quotation.status == QuotationStatus.LINKED)
            else:
                # 新单：只显示已批准的报价单（不包括已关联的）
                query = query.filter(Quotation.status == QuotationStatus.APPROVED)
        
        # 预加载关联数据，避免N+1查询
        query = query.options(
            joinedload(Quotation.customer),
            selectinload(Quotation.items)
        )
        
        # 按创建时间倒序排列，限制返回数量
        # 使用try-except包装查询，避免因数据库表结构不匹配导致错误
        try:
            quotations = query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()
        except Exception as query_error:
            # 如果查询失败，回滚事务并重新开始
            print(f"查询报价单时出错: {query_error}")
            db.rollback()
            # 重新构建查询，只查询基本字段
            query = db.query(Quotation)
            if customer_id:
                query = query.filter(Quotation.customer_id == customer_id)
            if status:
                query = query.filter(Quotation.status == status)
            if is_return_order is not None:
                if is_return_order:
                    query = query.filter(Quotation.status == QuotationStatus.LINKED)
                else:
                    query = query.filter(Quotation.status == QuotationStatus.APPROVED)
            query = query.options(joinedload(Quotation.customer))
            try:
                quotations = query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()
            except Exception as retry_error:
                # 如果重试也失败，再次回滚并抛出异常
                db.rollback()
                print(f"重试查询报价单时也出错: {retry_error}")
                raise
        
        # 安全地处理字段，避免访问不存在的字段
        for q in quotations:
            # 价格明细字段
            if not has_price_fields:
                q.engineering_fee = None
                q.board_material_fee_amount = None
                q.via_fee = None
                q.estimated_total_price = getattr(q, 'unit_price', None)
            else:
                # 确保价格明细字段存在（兼容旧数据）
                if not hasattr(q, 'engineering_fee') or q.engineering_fee is None:
                    q.engineering_fee = None
                if not hasattr(q, 'board_material_fee_amount') or q.board_material_fee_amount is None:
                    q.board_material_fee_amount = None
                if not hasattr(q, 'via_fee') or q.via_fee is None:
                    q.via_fee = None
                if not hasattr(q, 'estimated_total_price') or q.estimated_total_price is None:
                    q.estimated_total_price = getattr(q, 'unit_price', None)
            
            # 安全地访问可能不存在的新字段
            try:
                # 报价明细字段（如果不存在则设为None）
                if not hasattr(q, 'utilization_rate'):
                    q.utilization_rate = None
                if not hasattr(q, 'delivery_length'):
                    q.delivery_length = None
                if not hasattr(q, 'delivery_width'):
                    q.delivery_width = None
                if not hasattr(q, 'material_type'):
                    q.material_type = None
                if not hasattr(q, 'tg_value'):
                    q.tg_value = None
                if not hasattr(q, 'finished_board_thickness'):
                    q.finished_board_thickness = None
                if not hasattr(q, 'solder_mask_color_detail'):
                    q.solder_mask_color_detail = None
                if not hasattr(q, 'character_color_detail'):
                    q.character_color_detail = None
            except Exception:
                # 如果字段不存在，忽略错误
                pass
        
        return quotations
    except Exception as e:
        # 确保在异常时回滚事务
        try:
            db.rollback()
        except Exception:
            pass
        print(f"获取报价单列表错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取报价单列表失败: {str(e)}"
        )


# 注意：更具体的路由（/submit）应该放在参数路由之前
@router.post("/quotations/{quotation_number}/submit")
async def submit_quotation(
    quotation_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交报价单审核（两级：市场总监 → 总经理，无财务环节）"""
    from backend.common.models.user import UserRole
    from backend.common.utils.status_validator import QuotationStatusValidator
    
    try:
        quotation = db.query(Quotation).filter(
            Quotation.quotation_number == quotation_number
        ).first()
        
        if not quotation:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"报价单不存在: {quotation_number}"
            )
        
        # 允许 DRAFT 和 REJECTED 状态的报价单提交审核
        if quotation.status not in [QuotationStatus.DRAFT, QuotationStatus.REJECTED]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"报价单状态不允许提交: {quotation.status}"
            )
        
        # 如果是被拒绝的报价单，只有业务员（SALES）才能重新提交
        if quotation.status == QuotationStatus.REJECTED and current_user.role != UserRole.SALES:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="只有业务员才能重新提交被拒绝的报价单"
            )
        
        # 清除之前的审核人信息
        quotation.sales_approver = None
        quotation.sales_approved_at = None
        quotation.finance_approver = None
        quotation.finance_approved_at = None
        quotation.general_manager_approver = None
        quotation.general_manager_approved_at = None
        
        # 流转到市场总监待审
        QuotationStatusValidator.validate_quotation_status_transition(
            current_status=quotation.status,
            new_status=QuotationStatus.PENDING_SALES
        )
        quotation.status = QuotationStatus.PENDING_SALES
        quotation.updated_by = current_user.username
        
        db.commit()
        db.refresh(quotation)
        
        return {"message": "报价单已提交审核", "status": quotation.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"提交报价单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交报价单失败: {str(e)}"
        )


# 审核相关接口
class ApprovalRequest(BaseModel):
    comment: Optional[str] = None


@router.post("/quotations/{quotation_number}/approve")
async def approve_quotation(
    quotation_number: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """审核通过报价单（两级：市场总监 → 总经理）"""
    from backend.common.models.user import UserRole
    from backend.common.utils.status_validator import QuotationStatusValidator
    
    quotation = db.query(Quotation).filter(
        Quotation.quotation_number == quotation_number
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"报价单不存在: {quotation_number}"
        )
    
    # 根据当前状态决定所需角色与目标状态
    if quotation.status == QuotationStatus.PENDING_SALES:
        required_role = UserRole.SALES_MANAGER
        new_status = QuotationStatus.PENDING_GENERAL_MANAGER
        quotation.sales_approver = current_user.username
        quotation.sales_approved_at = datetime.utcnow()
    elif quotation.status == QuotationStatus.PENDING_GENERAL_MANAGER:
        required_role = UserRole.GENERAL_MANAGER
        new_status = QuotationStatus.APPROVED
        quotation.general_manager_approver = current_user.username
        quotation.general_manager_approved_at = datetime.utcnow()
    else:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态不允许审核通过: {quotation.status}"
        )
    
    # 检查权限：ADMIN角色可以绕过所有限制
    require_role(
        current_user, 
        required_role, 
        f"当前状态需要角色 {required_role.value} 审批"
    )
    
    QuotationStatusValidator.validate_quotation_status_transition(
        current_status=quotation.status,
        new_status=new_status
    )
    quotation.status = new_status
    quotation.updated_by = current_user.username
    db.commit()
    
    return {"message": "报价单审核通过", "status": quotation.status}


@router.post("/quotations/{quotation_number}/reject")
async def reject_quotation(
    quotation_number: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """拒绝报价单"""
    from backend.common.models.user import UserRole
    from backend.common.utils.status_validator import QuotationStatusValidator
    
    if not request.comment:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="拒绝审核必须填写拒绝原因"
        )
    
    quotation = db.query(Quotation).filter(
        Quotation.quotation_number == quotation_number
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"报价单不存在: {quotation_number}"
        )
    
    # 根据当前状态决定所需角色
    if quotation.status == QuotationStatus.PENDING_SALES:
        required_role = UserRole.SALES_MANAGER
    elif quotation.status == QuotationStatus.PENDING_GENERAL_MANAGER:
        required_role = UserRole.GENERAL_MANAGER
    else:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态不允许拒绝: {quotation.status}"
        )
    
    # 检查权限：ADMIN角色可以绕过所有限制
    require_role(
        current_user, 
        required_role, 
        f"当前状态需要角色 {required_role.value} 审批"
    )
    
    QuotationStatusValidator.validate_quotation_status_transition(
        current_status=quotation.status,
        new_status=QuotationStatus.REJECTED
    )
    quotation.status = QuotationStatus.REJECTED
    quotation.updated_by = current_user.username
    db.commit()
    
    return {"message": "报价单已拒绝", "status": quotation.status}


@router.get("/quotations/pending-approval")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的待审核报价单列表（按状态和角色简单筛选）"""
    from backend.common.models.user import UserRole
    
    if current_user.role == UserRole.SALES_MANAGER:
        target_status = QuotationStatus.PENDING_SALES
    elif current_user.role == UserRole.GENERAL_MANAGER:
        target_status = QuotationStatus.PENDING_GENERAL_MANAGER
    else:
        return []
    
    quotations = db.query(Quotation).filter(
        Quotation.status == target_status
    ).order_by(Quotation.created_at.desc()).all()
    
    return quotations


@router.get("/quotations/{quotation_number}/approval-status")
async def get_quotation_approval_status(
    quotation_number: str,
    db: Session = Depends(get_db)
):
    """获取报价单的审核状态"""
    quotation = db.query(Quotation).filter(
        Quotation.quotation_number == quotation_number
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"报价单不存在: {quotation_number}"
        )
    
    # 查找工作流实例
    from backend.common.utils.workflow import WorkflowInstance
    instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.business_id == quotation_number,
        WorkflowInstance.business_type == "QUOTATION"
    ).order_by(WorkflowInstance.created_at.desc()).first()
    
    if not instance:
        return {
            "quotation_number": quotation_number,
            "status": quotation.status,
            "workflow_enabled": False,
            "approval_history": []
        }
    
    # 获取审核历史
    try:
        workflow_engine = WorkflowEngine(db)
        workflow_status = workflow_engine.get_instance_status(instance.instance_id)
        
        if not workflow_status:
            return {
                "quotation_number": quotation_number,
                "status": quotation.status,
                "workflow_enabled": True,
                "workflow_status": None,
                "approval_history": []
            }
        
        return {
            "quotation_number": quotation_number,
            "status": quotation.status,
            "workflow_enabled": True,
            "workflow_status": workflow_status,
            "approval_history": [
                {
                    "node_name": node.get("node_name", ""),
                    "status": node.get("status", ""),
                    "approver": node.get("approver"),
                    "approved_at": node.get("approved_at"),
                    "comment": node.get("comment")
                }
                for node in workflow_status.get("nodes", [])
            ]
        }
    except Exception as e:
        print(f"获取审核状态错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核状态失败: {str(e)}"
        )


@router.get("/quotations/{quotation_number}", response_model=QuotationResponse)
async def get_quotation(
    quotation_number: str,
    db: Session = Depends(get_db)
):
    """获取报价单详情（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload, selectinload
    
    quotation = db.query(Quotation).filter(
        Quotation.quotation_number == quotation_number
    ).options(
        joinedload(Quotation.customer),
        selectinload(Quotation.items)
    ).first()
    if not quotation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"报价单不存在: {quotation_number}"
        )
    
    # 确保价格明细字段存在（兼容旧数据）
    try:
        if not hasattr(quotation, 'engineering_fee'):
            quotation.engineering_fee = None
        if not hasattr(quotation, 'board_material_fee_amount'):
            quotation.board_material_fee_amount = None
        if not hasattr(quotation, 'via_fee'):
            quotation.via_fee = None
        if not hasattr(quotation, 'estimated_total_price'):
            quotation.estimated_total_price = getattr(quotation, 'unit_price', None)
    except Exception as e:
        print(f"警告: 处理报价单 {quotation_number} 的价格明细字段时出错: {e}")
    
    return quotation


@router.put("/quotations/{quotation_number}", response_model=QuotationResponse)
async def update_quotation(
    quotation_number: str,
    quotation: QuotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新报价单"""
    db_quotation = db.query(Quotation).filter(
        Quotation.quotation_number == quotation_number
    ).first()
    
    if not db_quotation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"报价单不存在: {quotation_number}"
        )
    
    # 允许更新 DRAFT 和 REJECTED 状态的报价单
    if db_quotation.status not in [QuotationStatus.DRAFT, QuotationStatus.REJECTED]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"报价单状态不允许编辑: {db_quotation.status}"
        )
    
    # 如果是被拒绝的报价单，只有业务员（SALES）才能编辑，ADMIN角色可以绕过此限制
    if db_quotation.status == QuotationStatus.REJECTED:
        require_role(current_user, UserRole.SALES, "只有业务员才能编辑被拒绝的报价单")
    
    # 检查客户是否存在
    customer = db.query(Customer).filter(Customer.customer_id == quotation.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {quotation.customer_id}"
        )
    
    # 如果是从 REJECTED 状态更新，清除之前的审核信息
    if db_quotation.status == QuotationStatus.REJECTED:
        db_quotation.sales_approver = None
        db_quotation.sales_approved_at = None
        db_quotation.finance_approver = None
        db_quotation.finance_approved_at = None
        db_quotation.general_manager_approver = None
        db_quotation.general_manager_approved_at = None
        # 更新后状态改为 DRAFT，允许重新提交（添加状态流转验证）
        from backend.common.utils.status_validator import QuotationStatusValidator
        QuotationStatusValidator.validate_quotation_status_transition(
            current_status=db_quotation.status,
            new_status=QuotationStatus.DRAFT
        )
        db_quotation.status = QuotationStatus.DRAFT
    
    # 更新字段
    db_quotation.customer_id = quotation.customer_id
    db_quotation.product_number = quotation.product_number
    db_quotation.product_series = quotation.product_series
    db_quotation.layers = quotation.layers
    db_quotation.quantity = quotation.quantity
    db_quotation.unit_price = quotation.unit_price
    db_quotation.total_amount = quotation.quantity * quotation.unit_price
    db_quotation.currency = quotation.currency
    db_quotation.valid_until = quotation.valid_until
    db_quotation.remarks = quotation.remarks
    # 产品配置信息
    if quotation.product_category is not None:
        db_quotation.product_category = quotation.product_category
    if quotation.hdi_type is not None:
        db_quotation.hdi_type = quotation.hdi_type
    if quotation.board_material_brand is not None:
        db_quotation.board_material_brand = quotation.board_material_brand
    if quotation.board_material_model is not None:
        db_quotation.board_material_model = quotation.board_material_model
    if quotation.board_material_tg is not None:
        db_quotation.board_material_tg = quotation.board_material_tg
    if quotation.board_material_flame_retardant is not None:
        db_quotation.board_material_flame_retardant = quotation.board_material_flame_retardant
    if quotation.board_material_fee is not None:
        db_quotation.board_material_fee = quotation.board_material_fee
    if quotation.panelization_count is not None:
        db_quotation.panelization_count = quotation.panelization_count
    if quotation.output_format is not None:
        db_quotation.output_format = quotation.output_format
    if quotation.single_piece_length is not None:
        db_quotation.single_piece_length = quotation.single_piece_length
    if quotation.single_piece_width is not None:
        db_quotation.single_piece_width = quotation.single_piece_width
    if quotation.single_piece_quantity is not None:
        db_quotation.single_piece_quantity = quotation.single_piece_quantity
    if quotation.single_piece_unit is not None:
        db_quotation.single_piece_unit = quotation.single_piece_unit
    if quotation.process_border_type is not None:
        db_quotation.process_border_type = quotation.process_border_type
    if quotation.process_border_size is not None:
        db_quotation.process_border_size = quotation.process_border_size
    # 工艺信息
    if quotation.board_thickness is not None:
        db_quotation.board_thickness = quotation.board_thickness
    if quotation.outer_copper_thickness is not None:
        db_quotation.outer_copper_thickness = quotation.outer_copper_thickness
    if quotation.inner_copper_thickness is not None:
        db_quotation.inner_copper_thickness = quotation.inner_copper_thickness
    if quotation.min_line_width_spacing is not None:
        db_quotation.min_line_width_spacing = quotation.min_line_width_spacing
    if quotation.line_width_spacing_unit is not None:
        db_quotation.line_width_spacing_unit = quotation.line_width_spacing_unit
    if quotation.min_hole_diameter is not None:
        db_quotation.min_hole_diameter = quotation.min_hole_diameter
    if quotation.hole_diameter_unit is not None:
        db_quotation.hole_diameter_unit = quotation.hole_diameter_unit
    if quotation.solder_mask_color is not None:
        db_quotation.solder_mask_color = quotation.solder_mask_color
    if quotation.character_color is not None:
        db_quotation.character_color = quotation.character_color
    if quotation.solder_mask_coverage is not None:
        db_quotation.solder_mask_coverage = quotation.solder_mask_coverage
    if quotation.holes_in_pads is not None:
        db_quotation.holes_in_pads = quotation.holes_in_pads
    if quotation.surface_finish is not None:
        db_quotation.surface_finish = quotation.surface_finish
    if quotation.lamination_order is not None:
        db_quotation.lamination_order = quotation.lamination_order
    if quotation.impedance is not None:
        db_quotation.impedance = quotation.impedance
    if quotation.stackup_structure is not None:
        db_quotation.stackup_structure = quotation.stackup_structure
    if quotation.finger_bevel is not None:
        db_quotation.finger_bevel = quotation.finger_bevel
    if quotation.half_hole is not None:
        db_quotation.half_hole = quotation.half_hole
    if quotation.edge_plating is not None:
        db_quotation.edge_plating = quotation.edge_plating
    if quotation.press_fit_hole is not None:
        db_quotation.press_fit_hole = quotation.press_fit_hole
    if quotation.test_method is not None:
        db_quotation.test_method = quotation.test_method
    # 个性化服务
    if quotation.personalized_services is not None:
        db_quotation.personalized_services = quotation.personalized_services
    # 地址快递信息
    if quotation.shipping_notification is not None:
        db_quotation.shipping_notification = quotation.shipping_notification
    if quotation.delivery_note is not None:
        db_quotation.delivery_note = quotation.delivery_note
    if quotation.shipping_address is not None:
        db_quotation.shipping_address = quotation.shipping_address
    if quotation.express_company is not None:
        db_quotation.express_company = quotation.express_company
    # 发票支付信息
    if quotation.invoice_type is not None:
        db_quotation.invoice_type = quotation.invoice_type
    if quotation.payment_method is not None:
        db_quotation.payment_method = quotation.payment_method
    # SMT贴片信息
    if quotation.smt_patch_required is not None:
        db_quotation.smt_patch_required = quotation.smt_patch_required
    
    # 价格明细（检查数据库表是否有这些字段）
    has_price_fields = True
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('quotations')]
        has_price_fields = all(col in columns for col in ['engineering_fee', 'board_material_fee_amount', 'via_fee', 'estimated_total_price'])
        
        if has_price_fields:
            if quotation.engineering_fee is not None:
                db_quotation.engineering_fee = quotation.engineering_fee
            if quotation.board_material_fee_amount is not None:
                db_quotation.board_material_fee_amount = quotation.board_material_fee_amount
            if quotation.via_fee is not None:
                db_quotation.via_fee = quotation.via_fee
            if quotation.estimated_total_price is not None:
                db_quotation.estimated_total_price = quotation.estimated_total_price
    except Exception as e:
        print(f"警告: 更新报价单价格明细字段时出错: {e}")
        has_price_fields = False
    
    db_quotation.updated_by = current_user.username
    
    try:
        db.commit()
        db.refresh(db_quotation)
        
        # 如果数据库表中没有新字段，在返回前设置默认值
        if not has_price_fields:
            db_quotation.engineering_fee = quotation.engineering_fee
            db_quotation.board_material_fee_amount = quotation.board_material_fee_amount
            db_quotation.via_fee = quotation.via_fee
            db_quotation.estimated_total_price = quotation.estimated_total_price
    except Exception as e:
        db.rollback()
        print(f"更新报价单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新报价单失败: {str(e)}"
        )
    return db_quotation


# 报价明细成本计算
class QuotationDetailCalculationRequest(BaseModel):
    """报价明细成本计算请求"""
    # 板规格参数
    utilization_rate: Optional[float] = None
    delivery_length: Optional[float] = None
    delivery_width: Optional[float] = None
    set_per_unit: Optional[int] = 1
    material_type: Optional[str] = None
    tg_value: Optional[str] = None
    finished_board_thickness: Optional[str] = None
    large_material_spec: Optional[str] = None
    large_material_pnl_count: Optional[int] = None
    pnl_set_count: Optional[int] = None
    pnl_length_mm: Optional[float] = None
    pnl_width_mm: Optional[float] = None
    core_board_count: Optional[int] = None
    core_board_spec: Optional[str] = None
    inner_layer_thickening: Optional[bool] = False
    outer_line_width_spacing_limit: Optional[bool] = False
    solder_mask_color_detail: Optional[str] = None
    times: Optional[int] = 1
    specify_sun: Optional[bool] = False
    board_thickness_tolerance: Optional[bool] = False
    via_plugging: Optional[str] = None
    character_color_detail: Optional[str] = None
    min_drill_bit: Optional[str] = None
    set_hole_count: Optional[int] = None
    pcs_conversion: Optional[float] = None
    pnl_conversion: Optional[float] = None
    acceptance_standard: Optional[str] = None
    routing_process: Optional[float] = None
    v_score_process: Optional[float] = None
    hard_gold: Optional[bool] = False
    no_positioning_hole_routing: Optional[bool] = False
    test_points: Optional[int] = 0
    # 加价选项
    regular_surcharges: Optional[dict] = None
    special_surcharges: Optional[dict] = None
    additional_surcharge_per_m2: Optional[float] = None
    customer_provides_hf_board: Optional[bool] = False
    min_customer_consumption: Optional[float] = None
    market_quote_remarks: Optional[str] = None
    # 订单数量
    order_quantity: Optional[float] = 1


class QuotationDetailCalculationResponse(BaseModel):
    """报价明细成本计算结果"""
    # 计算结果
    order_quantity: float  # 订单数量
    actual_p_input: int  # 实际投P
    delivery_area: float  # 交货面积 (m²)
    cost_per_pcs: float  # 成本PCS
    cost_per_m2: float  # 成本平米
    quote_price_per_pcs: float  # 报价pcs价
    quote_price_per_m2: float  # 报价平米价
    engineering_fee: float  # 工程费
    board_material_fee: float  # 板材费
    test_fixture: float  # 测试架
    other_costs: float  # 其他费用
    final_total_price: float  # 最终总价
    # 工序明细
    process_details: List[dict]  # 工序明细列表


@router.post("/quotations/calculate-details", response_model=QuotationDetailCalculationResponse)
async def calculate_quotation_details_temp(
    calculation_data: QuotationDetailCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """计算报价明细成本（临时计算，不需要报价单编号）"""
    return await _calculate_quotation_details_logic(calculation_data, db, None)


@router.post("/quotations/{quotation_number}/calculate-details", response_model=QuotationDetailCalculationResponse)
async def calculate_quotation_details(
    quotation_number: str,
    calculation_data: QuotationDetailCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """计算报价明细成本"""
    # 获取报价单
    db_quotation = db.query(Quotation).filter(
        Quotation.quotation_number == quotation_number
    ).first()
    
    if not db_quotation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"报价单不存在: {quotation_number}"
        )
    
    return await _calculate_quotation_details_logic(calculation_data, db, db_quotation)


async def _calculate_quotation_details_logic(
    calculation_data: QuotationDetailCalculationRequest,
    db: Session,
    db_quotation: Optional[Quotation]
):
    """报价明细成本计算逻辑（内部函数）"""
    
    # 简化的成本计算逻辑（实际业务逻辑会更复杂）
    order_quantity = calculation_data.order_quantity or 1
    delivery_length = calculation_data.delivery_length or 0
    delivery_width = calculation_data.delivery_width or 0
    
    # 计算交货面积（mm²转m²）
    delivery_area_mm2 = delivery_length * delivery_width * order_quantity
    delivery_area = delivery_area_mm2 / 1000000  # 转换为m²
    
    # 计算实际投P（简化逻辑：根据订单数量计算）
    actual_p_input = max(1, int(order_quantity))
    
    # 基础成本计算（简化版）
    base_cost_per_m2 = 1000.0  # 基础成本/平米（示例值）
    
    # 根据层数调整成本（从报价单或计算数据中获取）
    layers = 1
    if db_quotation and db_quotation.layers:
        layers = db_quotation.layers
    layer_multiplier = 1.0 + (layers - 1) * 0.15
    cost_per_m2 = base_cost_per_m2 * layer_multiplier
    
    # 加价计算
    surcharge_per_m2 = 0.0
    if calculation_data.additional_surcharge_per_m2:
        surcharge_per_m2 += calculation_data.additional_surcharge_per_m2
    
    # 常规加价
    if calculation_data.regular_surcharges:
        for key, value in calculation_data.regular_surcharges.items():
            if value:  # 如果选项被选中
                surcharge_per_m2 += 50.0  # 每个常规加价项增加50元/平米（示例）
    
    # 特殊加价
    if calculation_data.special_surcharges:
        for key, value in calculation_data.special_surcharges.items():
            if isinstance(value, bool) and value:
                surcharge_per_m2 += 100.0  # 每个特殊加价项增加100元/平米（示例）
            elif isinstance(value, (int, float)) and value > 0:
                surcharge_per_m2 += value * 10.0  # 根据数量计算（示例）
    
    cost_per_m2 += surcharge_per_m2
    
    # 计算成本PCS
    cost_per_pcs = cost_per_m2 * (delivery_length * delivery_width / 1000000) if delivery_area > 0 else 0
    
    # 报价价格（成本基础上加30%利润）
    quote_price_per_m2 = cost_per_m2 * 1.3
    quote_price_per_pcs = cost_per_pcs * 1.3
    
    # 工程费（根据层数和复杂度）
    engineering_fee = 150.0
    if layers > 4:
        engineering_fee = 200.0
    if layers > 6:
        engineering_fee = 250.0
    
    # 板材费（根据面积和成本计算）
    board_material_fee = cost_per_m2 * delivery_area if delivery_area > 0 else 0.0
    
    # 测试架费用
    test_fixture = 0.0
    if calculation_data.test_points and calculation_data.test_points > 0:
        test_fixture = 500.0  # 示例值
    
    # 其他费用
    other_costs = 0.0
    if calculation_data.min_customer_consumption:
        other_costs = calculation_data.min_customer_consumption
    
    # 最终总价（工程费 + 板材费 + 其他费用）
    final_total_price = (
        engineering_fee +
        board_material_fee +
        test_fixture +
        other_costs
    )
    
    # 生成工序明细（示例数据）
    process_details = [
        {
            "process_order": 1,
            "process_name": "开料",
            "p_cost_calculation_info": f"基础开料成本",
            "p_price": cost_per_m2 * 0.1,
            "delivery_area": delivery_area,
            "process_cost_share": 10.0
        },
        {
            "process_order": 2,
            "process_name": "钻孔",
            "p_cost_calculation_info": f"SET孔数: {calculation_data.set_hole_count or 0}",
            "p_price": cost_per_m2 * 0.15,
            "delivery_area": delivery_area,
            "process_cost_share": 15.0
        },
        {
            "process_order": 3,
            "process_name": "电镀",
            "p_cost_calculation_info": f"层数: {layers}",
            "p_price": cost_per_m2 * 0.2,
            "delivery_area": delivery_area,
            "process_cost_share": 20.0
        },
        {
            "process_order": 4,
            "process_name": "线路",
            "p_cost_calculation_info": f"线宽线距: {db_quotation.min_line_width_spacing if db_quotation else 'N/A'}",
            "p_price": cost_per_m2 * 0.25,
            "delivery_area": delivery_area,
            "process_cost_share": 25.0
        },
        {
            "process_order": 5,
            "process_name": "阻焊",
            "p_cost_calculation_info": f"阻焊颜色: {calculation_data.solder_mask_color_detail or 'N/A'}",
            "p_price": cost_per_m2 * 0.15,
            "delivery_area": delivery_area,
            "process_cost_share": 15.0
        },
        {
            "process_order": 6,
            "process_name": "表面处理",
            "p_cost_calculation_info": f"表面处理: {db_quotation.surface_finish if db_quotation else 'N/A'}",
            "p_price": cost_per_m2 * 0.1,
            "delivery_area": delivery_area,
            "process_cost_share": 10.0
        },
        {
            "process_order": 7,
            "process_name": "成型",
            "p_cost_calculation_info": f"锣程: {calculation_data.routing_process or 0}MM",
            "p_price": cost_per_m2 * 0.05,
            "delivery_area": delivery_area,
            "process_cost_share": 5.0
        }
    ]
    
    # 构建返回结果，添加板材费字段
    result_data = {
        "order_quantity": order_quantity,
        "actual_p_input": actual_p_input,
        "delivery_area": round(delivery_area, 4),
        "cost_per_pcs": round(cost_per_pcs, 4),
        "cost_per_m2": round(cost_per_m2, 4),
        "quote_price_per_pcs": round(quote_price_per_pcs, 4),
        "quote_price_per_m2": round(quote_price_per_m2, 4),
        "engineering_fee": round(engineering_fee, 2),
        "board_material_fee": round(board_material_fee, 2),
        "test_fixture": round(test_fixture, 2),
        "other_costs": round(other_costs, 2),
        "final_total_price": round(final_total_price, 2),
        "process_details": process_details
    }
    
    return QuotationDetailCalculationResponse(**result_data)


# 销售订单管理
@router.post("/sales-orders", response_model=SalesOrderResponse, status_code=http_status.HTTP_201_CREATED)
async def create_sales_order(
    order: SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建销售订单（可从报价单转单或直接创建返单）"""
    try:
        # 使用服务层创建销售订单
        order_data = {
            "customer_id": order.customer_id,
            "quotation_number": order.quotation_number,
            "product_number": order.product_number,
            "material_code": order.material_code,
            "production_version_id": order.production_version_id,
            "quantity": order.quantity,
            "unit_price": order.unit_price,
            "delivery_date": order.delivery_date,
            "is_return_order": order.is_return_order,
            "sales_unit": order.sales_unit,
            "production_unit": order.production_unit,
            "conversion_factor": order.conversion_factor,
            "production_quantity": order.production_quantity,
            "remarks": order.remarks,
        }
        
        db_order = SalesOrderService.create_sales_order(
            order_data=order_data,
            current_user=current_user.username,
            db=db
        )
        
        return db_order
    
    except BusinessException:
        # 业务异常直接抛出（事务装饰器会自动回滚）
        raise
    except Exception as e:
        # 其他异常转换为业务异常（事务装饰器会自动回滚）
        raise BusinessException(
            error_code="INTERNAL_ERROR",
            detail=f"创建销售订单失败: {str(e)}",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/sales-orders", response_model=List[SalesOrderResponse])
async def list_sales_orders(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取销售订单列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(SalesOrder)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if status:
        query = query.filter(SalesOrder.status == status)
    
    # 预加载关联数据，避免N+1查询
    query = query.options(
        joinedload(SalesOrder.customer),
        joinedload(SalesOrder.quotation)
    )
    
    orders = query.offset(skip).limit(limit).all()
    return orders


@router.get("/sales-orders/{order_number}", response_model=SalesOrderResponse)
async def get_sales_order(
    order_number: str,
    db: Session = Depends(get_db)
):
    """获取销售订单详情（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).options(
        joinedload(SalesOrder.customer),
        joinedload(SalesOrder.quotation)
        # 注意：SalesOrder.contract_reviews 关系未定义，所以不加载
    ).first()
    if not order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    return order


@router.get("/sales-orders/{order_number}/review-status")
async def get_sales_order_review_status(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取销售订单评审状态（多部门评审流程）"""
    from backend.common.utils.workflow import WorkflowInstance, WorkflowNode
    
    # 查找工作流实例（使用更宽松的查询条件）
    workflow_instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.business_id == order_number,
        WorkflowInstance.business_type == "SALES_ORDER"
    ).order_by(WorkflowInstance.created_at.desc()).first()
    
    # 如果没找到，尝试查找所有相关的工作流实例（用于调试）
    if not workflow_instance:
        all_instances = db.query(WorkflowInstance).filter(
            WorkflowInstance.business_id == order_number
        ).all()
        print(f"[DEBUG] 订单 {order_number} 的所有工作流实例: {[i.instance_id for i in all_instances]}")
        
        # 尝试查找 SALES_ORDER 类型的所有实例
        sales_order_instances = db.query(WorkflowInstance).filter(
            WorkflowInstance.business_type == "SALES_ORDER"
        ).limit(10).all()
        print(f"[DEBUG] 最近10个 SALES_ORDER 类型的工作流实例: {[(i.business_id, i.instance_id) for i in sales_order_instances]}")
    
    if not workflow_instance:
        # 检查订单状态，提供更详细的提示信息
        db_order = db.query(SalesOrder).filter(
            SalesOrder.order_number == order_number
        ).first()
        
        if db_order:
            if db_order.status == SalesOrderStatus.DRAFT:
                message = "该订单尚未提交审核，请先提交审核以启动评审流程"
            elif db_order.status in [SalesOrderStatus.APPROVED, SalesOrderStatus.IN_PRODUCTION, SalesOrderStatus.COMPLETED]:
                message = "该订单已完成评审或已进入生产流程"
            elif db_order.status == SalesOrderStatus.PENDING_REVIEW:
                # 订单状态是待评审，但工作流实例不存在，尝试自动修复
                message = "订单状态为待评审，但未找到工作流实例。系统将尝试自动修复..."
                try:
                    workflow_engine = WorkflowEngine(db)
                    
                    # 首先检查工作流定义是否存在，如果不存在则创建
                    from backend.common.utils.workflow import Workflow
                    workflow_def = db.query(Workflow).filter(
                        Workflow.workflow_id == "SALES_ORDER_REVIEW"
                    ).first()
                    
                    if not workflow_def:
                        print("[INFO] 工作流定义不存在，正在创建...")
                        # 创建工作流定义
                        workflow_engine.create_workflow(
                            workflow_id="SALES_ORDER_REVIEW",
                            workflow_name="销售订单多部门评审流程",
                            description="销售订单需要经过销售、工程、物料、财务四个部门顺序评审",
                            module="SD",
                            nodes=[
                                {
                                    "node_id": "SALES_REVIEW",
                                    "node_name": "销售部门评审",
                                    "node_type": "APPROVAL",
                                    "approver_role": "SALES_MANAGER",
                                    "config": {"required": True}
                                },
                                {
                                    "node_id": "ENGINEERING_REVIEW",
                                    "node_name": "工程部门评审",
                                    "node_type": "APPROVAL",
                                    "approver_role": "ENGINEER",
                                    "config": {"required": True}
                                },
                                {
                                    "node_id": "MATERIAL_REVIEW",
                                    "node_name": "物料部门评审",
                                    "node_type": "APPROVAL",
                                    "approver_role": "WAREHOUSE",
                                    "config": {"required": True}
                                },
                                {
                                    "node_id": "FINANCE_REVIEW",
                                    "node_name": "财务部门评审",
                                    "node_type": "APPROVAL",
                                    "approver_role": "FINANCE",
                                    "config": {"required": True}
                                }
                            ]
                        )
                        print("[OK] 工作流定义创建成功")
                    
                    # 尝试重新创建工作流实例
                    instance = workflow_engine.start_workflow(
                        workflow_id="SALES_ORDER_REVIEW",
                        business_id=order_number,
                        business_type="SALES_ORDER",
                        created_by=current_user.username
                    )
                    db.commit()
                    # 重新查询工作流实例
                    workflow_instance = db.query(WorkflowInstance).filter(
                        WorkflowInstance.instance_id == instance.instance_id
                    ).first()
                    if workflow_instance:
                        message = "已自动创建工作流定义和实例"
                        print(f"[OK] 已为订单 {order_number} 创建工作流实例: {instance.instance_id}")
                except Exception as e:
                    print(f"[ERROR] 自动创建工作流实例失败: {e}")
                    import traceback
                    traceback.print_exc()
                    message = f"未找到评审工作流实例，且自动修复失败: {str(e)}"
            else:
                message = "未找到评审工作流实例，订单状态可能异常"
        else:
            message = "未找到评审工作流实例"
        
        # 如果自动修复成功，继续处理；否则返回错误
        if not workflow_instance:
            return {
                "has_workflow": False,
                "message": message,
                "order_status": db_order.status.value if db_order else None
            }
    
    # 获取工作流状态
    workflow_engine = WorkflowEngine(db)
    status_data = workflow_engine.get_instance_status(workflow_instance.instance_id)
    
    # 检查当前用户是否可以审批当前节点
    can_approve = False
    debug_info = {
        "current_user_role": current_user.role.value,
        "current_node_id": None,
        "node_approver_role": None,
        "can_approve": False,
        "status_data_exists": status_data is not None,
        "has_current_node": status_data.get('current_node') if status_data else False
    }
    
    # 确保 status_data 存在且有 current_node
    if not status_data:
        print(f"[WARNING] status_data 为空，无法进行权限检查")
        debug_info["error"] = "status_data为空"
    elif not status_data.get('current_node'):
        print(f"[WARNING] status_data 中没有 current_node，无法进行权限检查")
        debug_info["error"] = "status_data中没有current_node"
        debug_info["status_data_keys"] = list(status_data.keys()) if isinstance(status_data, dict) else None
        # 尝试从 workflow_instance 获取 current_node_id
        if workflow_instance and workflow_instance.current_node_id:
            print(f"[INFO] 从 workflow_instance 获取 current_node_id: {workflow_instance.current_node_id}")
            current_node_id = workflow_instance.current_node_id
            debug_info["current_node_id_from_instance"] = current_node_id
            
            current_node = db.query(WorkflowNode).filter(
                WorkflowNode.node_id == current_node_id
            ).first()
            
            if current_node:
                node_approver_role = str(current_node.approver_role) if current_node.approver_role else None
                user_role = str(current_user.role.value)
                
                debug_info["node_approver_role"] = node_approver_role
                debug_info["user_role_str"] = user_role
                
                if node_approver_role:
                    if node_approver_role == "SALES_MANAGER":
                        can_approve = user_role in ["SALES", "SALES_MANAGER", "ADMIN"]
                    else:
                        can_approve = user_role == node_approver_role or user_role == "ADMIN"
                    
                    debug_info["can_approve"] = can_approve
                    debug_info["role_match"] = user_role == node_approver_role
    elif status_data and status_data.get('current_node'):
        current_node_id = status_data['current_node']
        debug_info["current_node_id"] = current_node_id
        
        current_node = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == current_node_id
        ).first()
        
        if current_node:
            # 确保 approver_role 是字符串类型
            node_approver_role = str(current_node.approver_role) if current_node.approver_role else None
            debug_info["node_approver_role"] = node_approver_role
            
            if node_approver_role:
                # 确保用户角色也是字符串类型
                user_role = str(current_user.role.value)
                
                # 检查用户角色是否匹配
                # 对于销售部门评审，允许 SALES 和 SALES_MANAGER 角色
                if node_approver_role == "SALES_MANAGER":
                    can_approve = user_role in ["SALES", "SALES_MANAGER", "ADMIN"]
                else:
                    can_approve = user_role == node_approver_role or user_role == "ADMIN"
                
                debug_info["can_approve"] = can_approve
                debug_info["user_role_str"] = user_role
                debug_info["node_role_str"] = node_approver_role
                debug_info["role_match"] = user_role == node_approver_role
    
    # 打印详细的调试信息（便于排查问题）
    print(f"[评审权限检查] 订单: {order_number}")
    print(f"  用户: {current_user.username}")
    print(f"  用户角色(原始): {current_user.role}")
    print(f"  用户角色(值): {current_user.role.value}")
    print(f"  用户角色(类型): {type(current_user.role.value)}")
    if status_data and status_data.get('current_node'):
        current_node_id = status_data['current_node']
        current_node = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == current_node_id
        ).first()
        if current_node:
            print(f"  节点ID: {current_node.node_id}")
            print(f"  节点名称: {current_node.node_name}")
            print(f"  节点要求角色(原始): {current_node.approver_role}")
            print(f"  节点要求角色(类型): {type(current_node.approver_role)}")
            print(f"  节点要求角色(字符串): {str(current_node.approver_role) if current_node.approver_role else None}")
    print(f"  调试信息: {debug_info}")
    print(f"  最终can_approve: {can_approve}")
    
    # 获取评审历史
    reviews = db.query(ContractReview).filter(
        ContractReview.sales_order_number == order_number
    ).order_by(ContractReview.reviewed_at.desc()).all()
    
    review_history = [
        {
            "reviewer_role": r.reviewer_role,
            "reviewer": r.reviewer,
            "review_result": r.review_result,
            "review_comment": r.review_comment,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None
        }
        for r in reviews
    ]
    
    return {
        "has_workflow": True,
        "workflow_status": status_data,
        "review_history": review_history,
        "can_approve": can_approve,
        "current_user_role": current_user.role.value,
        "debug_info": debug_info  # 添加调试信息
    }


@router.put("/sales-orders/{order_number}", response_model=SalesOrderResponse)
async def update_sales_order(
    order_number: str,
    order: SalesOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新销售订单"""
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查客户是否存在
    customer = db.query(Customer).filter(Customer.customer_id == order.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"客户不存在: {order.customer_id}"
        )
    
    # 如果从报价单转单，检查报价单是否存在且状态正确
    if order.quotation_number:
        quotation = db.query(Quotation).filter(
            Quotation.quotation_number == order.quotation_number
        ).first()
        if not quotation:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"报价单不存在: {order.quotation_number}"
            )
        # 根据返单/新单判断允许的报价单状态
        if order.is_return_order:
            # 返单：只允许使用已关联的报价单
            if quotation.status != QuotationStatus.LINKED:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"返单只能使用已关联的报价单，当前报价单状态: {quotation.status}"
                )
        else:
            # 新单：只允许使用已批准的报价单
            if quotation.status != QuotationStatus.APPROVED:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"新单只能使用已批准的报价单，当前报价单状态: {quotation.status}"
                )
    
    # 更新字段
    db_order.quotation_number = order.quotation_number
    db_order.customer_id = order.customer_id
    db_order.product_number = order.product_number
    db_order.quantity = order.quantity
    db_order.unit_price = order.unit_price
    db_order.total_amount = order.quantity * order.unit_price
    db_order.delivery_date = order.delivery_date
    db_order.is_return_order = order.is_return_order
    db_order.remarks = order.remarks
    db_order.updated_by = current_user.username
    
    db.commit()
    db.refresh(db_order)
    return db_order


@router.post("/sales-orders/{order_number}/submit")
async def submit_sales_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交销售订单审核 - 启动多部门评审流程"""
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有草稿状态的订单可以提交审核
    if db_order.status != SalesOrderStatus.DRAFT:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许提交审核，当前状态: {db_order.status}"
        )
    
    try:
        # 检查是否已经存在工作流实例（防止重复提交）
        from backend.common.utils.workflow import WorkflowInstance
        existing_instance = db.query(WorkflowInstance).filter(
            WorkflowInstance.business_id == order_number,
            WorkflowInstance.business_type == "SALES_ORDER"
        ).first()
        
        if existing_instance:
            # 如果已存在工作流实例，直接返回
            from backend.common.utils.status_validator import SalesOrderStatusValidator
            SalesOrderStatusValidator.validate_sales_order_status_transition(
                current_status=db_order.status,
                new_status=SalesOrderStatus.PENDING_REVIEW
            )
            db_order.status = SalesOrderStatus.PENDING_REVIEW
            db_order.review_status = "PENDING"
            db_order.updated_by = current_user.username
            db.commit()
            return {
                "message": "销售订单已提交审核，等待销售部门评审",
                "status": db_order.status,
                "workflow_instance_id": existing_instance.instance_id
            }
        
        # 启动订单评审工作流
        workflow_engine = WorkflowEngine(db)
        instance = workflow_engine.start_workflow(
            workflow_id="SALES_ORDER_REVIEW",
            business_id=order_number,
            business_type="SALES_ORDER",
            created_by=current_user.username
        )
        
        # 验证工作流实例是否创建成功
        if not instance or not instance.instance_id:
            raise ValueError("工作流实例创建失败")
        
        # 添加状态流转验证
        from backend.common.utils.status_validator import SalesOrderStatusValidator
        SalesOrderStatusValidator.validate_sales_order_status_transition(
            current_status=db_order.status,
            new_status=SalesOrderStatus.PENDING_REVIEW
        )
        
        # 更新订单状态为待订单评审
        db_order.status = SalesOrderStatus.PENDING_REVIEW
        db_order.review_status = "PENDING"
        db_order.updated_by = current_user.username
        
        # 提交事务
        db.commit()
        
        # 验证工作流实例是否已保存到数据库
        db.refresh(instance)
        saved_instance = db.query(WorkflowInstance).filter(
            WorkflowInstance.instance_id == instance.instance_id
        ).first()
        
        if not saved_instance:
            raise ValueError(f"工作流实例保存失败: {instance.instance_id}")
        
        return {
            "message": "销售订单已提交审核，等待销售部门评审",
            "status": db_order.status,
            "workflow_instance_id": instance.instance_id
        }
    except Exception as e:
        db.rollback()
        print(f"提交销售订单审核错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交审核失败: {str(e)}"
        )


@router.post("/sales-orders/{order_number}/approve", response_model=SalesOrderResponse)
async def approve_sales_order(
    order_number: str,
    request: Optional[ApprovalRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """审批通过销售订单 - 多部门评审流程"""
    from backend.common.utils.workflow import WorkflowInstance, WorkflowNode
    
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有待订单评审或评审中的订单可以审批
    if db_order.status not in [SalesOrderStatus.PENDING_REVIEW, SalesOrderStatus.REVIEWING]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许审批，当前状态: {db_order.status}"
        )
    
    try:
        # 查找工作流实例
        workflow_instance = db.query(WorkflowInstance).filter(
            WorkflowInstance.business_id == order_number,
            WorkflowInstance.business_type == "SALES_ORDER"
        ).order_by(WorkflowInstance.created_at.desc()).first()
        
        if not workflow_instance:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="未找到订单评审工作流实例"
            )
        
        # 检查当前用户是否有权限审批当前节点
        current_node = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == workflow_instance.current_node_id
        ).first()
        
        if not current_node:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="未找到当前评审节点"
            )
        
        # 检查用户角色是否匹配
        # 确保角色比较时使用字符串类型
        node_approver_role = str(current_node.approver_role) if current_node.approver_role else None
        user_role = str(current_user.role.value)
        
        if node_approver_role:
            # 对于销售部门评审，允许 SALES 和 SALES_MANAGER 角色
            if node_approver_role == "SALES_MANAGER":
                # 销售部门评审允许 SALES 和 SALES_MANAGER
                if user_role not in ["SALES", "SALES_MANAGER", "ADMIN"]:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail=f"当前节点需要销售部门角色（SALES 或 SALES_MANAGER）审批，您的角色是 {user_role}"
                    )
            elif user_role != node_approver_role and user_role != "ADMIN":
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail=f"当前节点需要 {node_approver_role} 角色审批，您的角色是 {user_role}"
                )
        
        # 使用工作流引擎审批
        workflow_engine = WorkflowEngine(db)
        comment = request.comment if request else None
        updated_instance = workflow_engine.approve(
            instance_id=workflow_instance.instance_id,
            approver=current_user.username,
            comment=comment
        )
        
        # 记录评审历史
        review = ContractReview(
            sales_order_number=order_number,
            reviewer_role=current_user.role.value,
            reviewer=current_user.username,
            review_result="APPROVED",
            review_comment=comment,
            reviewed_at=datetime.utcnow()
        )
        db.add(review)
        
        # 更新订单评审状态（添加状态流转验证）
        from backend.common.utils.status_validator import SalesOrderStatusValidator, QuotationStatusValidator
        
        if updated_instance.status == WorkflowStatus.COMPLETED:
            # 所有部门都评审通过
            #
            # 兼容：如果订单仍停留在 PENDING_REVIEW（历史数据/并发/异常回滚导致），先落到 REVIEWING 再批准，
            # 避免直接 PENDING_REVIEW -> APPROVED 触发状态流转校验失败。
            if db_order.status == SalesOrderStatus.PENDING_REVIEW:
                SalesOrderStatusValidator.validate_sales_order_status_transition(
                    current_status=db_order.status,
                    new_status=SalesOrderStatus.REVIEWING
                )
                db_order.status = SalesOrderStatus.REVIEWING

            SalesOrderStatusValidator.validate_sales_order_status_transition(
                current_status=db_order.status,
                new_status=SalesOrderStatus.APPROVED
            )
            db_order.status = SalesOrderStatus.APPROVED
            db_order.review_status = "APPROVED"
            
            # 如果订单关联了报价单，将报价单状态更新为已关联
            if db_order.quotation_number:
                quotation = db.query(Quotation).filter(
                    Quotation.quotation_number == db_order.quotation_number
                ).first()
                if quotation:
                    QuotationStatusValidator.validate_quotation_status_transition(
                        current_status=quotation.status,
                        new_status=QuotationStatus.LINKED
                    )
                    quotation.status = QuotationStatus.LINKED
                    quotation.updated_by = current_user.username
        else:
            # 还有部门未评审
            SalesOrderStatusValidator.validate_sales_order_status_transition(
                current_status=db_order.status,
                new_status=SalesOrderStatus.REVIEWING
            )
            db_order.status = SalesOrderStatus.REVIEWING
            db_order.review_status = "REVIEWING"
        
        db_order.updated_by = current_user.username
        db.commit()
        db.refresh(db_order)
        
        return db_order
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"审批销售订单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审批失败: {str(e)}"
        )


@router.post("/sales-orders/{order_number}/reject", response_model=SalesOrderResponse)
async def reject_sales_order(
    order_number: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """拒绝销售订单 - 多部门评审流程"""
    from backend.common.utils.workflow import WorkflowInstance
    
    if not request.comment:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="拒绝审核必须填写拒绝原因"
        )
    
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有待订单评审或评审中的订单可以拒绝
    if db_order.status not in [SalesOrderStatus.PENDING_REVIEW, SalesOrderStatus.REVIEWING]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许拒绝，当前状态: {db_order.status}"
        )
    
    try:
        # 查找工作流实例
        workflow_instance = db.query(WorkflowInstance).filter(
            WorkflowInstance.business_id == order_number,
            WorkflowInstance.business_type == "SALES_ORDER"
        ).order_by(WorkflowInstance.created_at.desc()).first()
        
        if workflow_instance:
            # 检查当前用户是否有权限审批当前节点
            from backend.common.utils.workflow import WorkflowNode
            current_node = db.query(WorkflowNode).filter(
                WorkflowNode.node_id == workflow_instance.current_node_id
            ).first()
            
            if current_node and current_node.approver_role:
                # 检查用户角色是否匹配
                # 确保角色比较时使用字符串类型
                node_approver_role = str(current_node.approver_role) if current_node.approver_role else None
                user_role = str(current_user.role.value)
                
                # 对于销售部门评审，允许 SALES 和 SALES_MANAGER 角色
                if node_approver_role == "SALES_MANAGER":
                    # 销售部门评审允许 SALES 和 SALES_MANAGER
                    if user_role not in ["SALES", "SALES_MANAGER", "ADMIN"]:
                        raise HTTPException(
                            status_code=http_status.HTTP_403_FORBIDDEN,
                            detail=f"当前节点需要销售部门角色（SALES 或 SALES_MANAGER）审批，您的角色是 {user_role}"
                        )
                elif user_role != node_approver_role and user_role != "ADMIN":
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail=f"当前节点需要 {node_approver_role} 角色审批，您的角色是 {user_role}"
                    )
            
            # 使用工作流引擎拒绝
            workflow_engine = WorkflowEngine(db)
            workflow_engine.reject(
                instance_id=workflow_instance.instance_id,
                approver=current_user.username,
                comment=request.comment
            )
        
        # 记录评审历史
        review = ContractReview(
            sales_order_number=order_number,
            reviewer_role=current_user.role.value,
            reviewer=current_user.username,
            review_result="REJECTED",
            review_comment=request.comment,
            reviewed_at=datetime.utcnow()
        )
        db.add(review)
        
        # 更新订单状态为已拒绝
        # 添加状态流转验证
        from backend.common.utils.status_validator import SalesOrderStatusValidator
        SalesOrderStatusValidator.validate_sales_order_status_transition(
            current_status=db_order.status,
            new_status=SalesOrderStatus.REJECTED
        )
        db_order.status = SalesOrderStatus.REJECTED
        db_order.review_status = "REJECTED"
        db_order.updated_by = current_user.username
        db.commit()
        db.refresh(db_order)
        
        return db_order
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"拒绝销售订单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"拒绝失败: {str(e)}"
        )


@router.post("/sales-orders/{order_number}/ship", response_model=SalesOrderResponse)
async def ship_sales_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """销售发货 - 将订单状态改为已发货"""
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有已完成或生产中的订单可以发货
    if db_order.status not in [SalesOrderStatus.COMPLETED, SalesOrderStatus.IN_PRODUCTION]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许发货，当前状态: {db_order.status}"
        )
    
    try:
        # 更新订单状态为已发货
        # 添加状态流转验证
        from backend.common.utils.status_validator import SalesOrderStatusValidator
        SalesOrderStatusValidator.validate_sales_order_status_transition(
            current_status=db_order.status,
            new_status=SalesOrderStatus.SHIPPED
        )
        db_order.status = SalesOrderStatus.SHIPPED
        db_order.updated_by = current_user.username
        db.commit()
        db.refresh(db_order)
        
        return db_order
    except Exception as e:
        db.rollback()
        print(f"销售发货错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发货失败: {str(e)}"
        )


@router.post("/sales-orders/{order_number}/deliver", response_model=SalesOrderResponse)
async def deliver_sales_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """销售签收 - 将订单状态改为已签收"""
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有已发货的订单可以签收
    if db_order.status != SalesOrderStatus.SHIPPED:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许签收，当前状态: {db_order.status}，需要状态: SHIPPED"
        )
    
    try:
        # 更新订单状态为已签收
        # 添加状态流转验证
        from backend.common.utils.status_validator import SalesOrderStatusValidator
        SalesOrderStatusValidator.validate_sales_order_status_transition(
            current_status=db_order.status,
            new_status=SalesOrderStatus.DELIVERED
        )
        db_order.status = SalesOrderStatus.DELIVERED
        db_order.updated_by = current_user.username
        db.commit()
        db.refresh(db_order)
        
        return db_order
    except Exception as e:
        db.rollback()
        print(f"销售签收错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"签收失败: {str(e)}"
        )


@router.post("/sales-orders/{order_number}/reconcile", response_model=SalesOrderResponse)
async def reconcile_sales_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """销售对账 - 将订单状态改为已对账"""
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有已签收的订单可以对账
    if db_order.status != SalesOrderStatus.DELIVERED:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许对账，当前状态: {db_order.status}，需要状态: DELIVERED"
        )
    
    try:
        # 更新订单状态为已对账
        # 添加状态流转验证
        from backend.common.utils.status_validator import SalesOrderStatusValidator
        SalesOrderStatusValidator.validate_sales_order_status_transition(
            current_status=db_order.status,
            new_status=SalesOrderStatus.RECONCILED
        )
        db_order.status = SalesOrderStatus.RECONCILED
        db_order.updated_by = current_user.username
        db.commit()
        db.refresh(db_order)
        
        return db_order
    except Exception as e:
        db.rollback()
        print(f"销售对账错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对账失败: {str(e)}"
        )


@router.post("/sales-orders/{order_number}/close", response_model=SalesOrderResponse)
async def close_sales_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """关闭销售订单 - 关闭销售订单及所有关联的生产订单"""
    db_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order_number}"
        )
    
    # 检查订单状态，只有已对账的订单可以关闭
    if db_order.status != SalesOrderStatus.RECONCILED:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许关闭，当前状态: {db_order.status}，需要状态: RECONCILED"
        )
    
    try:
        from backend.common.models.pp import ProductionOrder, ProductionOrderStatus
        from datetime import datetime
        
        # 查找所有关联的生产订单
        production_orders = db.query(ProductionOrder).filter(
            ProductionOrder.sales_order_number == order_number
        ).all()
        
        # 关闭所有未关闭的生产订单
        closed_count = 0
        for po in production_orders:
            if po.status not in [ProductionOrderStatus.CLOSED, ProductionOrderStatus.CANCELLED]:
                po.status = ProductionOrderStatus.CLOSED
                if not po.actual_finish_date:
                    po.actual_finish_date = datetime.utcnow()
                po.updated_by = current_user.username
                closed_count += 1
        
        # 更新销售订单状态为已关闭
        # 添加状态流转验证
        from backend.common.utils.status_validator import SalesOrderStatusValidator
        SalesOrderStatusValidator.validate_sales_order_status_transition(
            current_status=db_order.status,
            new_status=SalesOrderStatus.CLOSED
        )
        db_order.status = SalesOrderStatus.CLOSED
        db_order.updated_by = current_user.username
        db.commit()
        db.refresh(db_order)
        
        # 记录关闭的生产订单数量（可以通过日志或消息返回）
        print(f"销售订单 {order_number} 已关闭，已关闭 {closed_count} 个关联的生产订单")
        
        return db_order
    except Exception as e:
        db.rollback()
        print(f"关闭销售订单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"关闭失败: {str(e)}"
        )


# 本厂编号映射管理
@router.post("/factory-product-mappings", response_model=FactoryProductMappingResponse, status_code=http_status.HTTP_201_CREATED)
async def create_factory_product_mapping(
    mapping: FactoryProductMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建本厂编号映射（带冲突检测）"""
    from backend.services.mapping_service import MappingService
    from backend.common.exceptions import BusinessException
    
    try:
        mapping_data = {
            "customer_id": mapping.customer_id,
            "factory_product_number": mapping.factory_product_number,
            "material_code": mapping.material_code,
            "production_version_id": mapping.production_version_id,
            "is_default": mapping.is_default,
            "effective_date": mapping.effective_date,
            "expiry_date": mapping.expiry_date,
        }
        
        db_mapping = MappingService.create_factory_product_mapping(
            mapping_data=mapping_data,
            current_user=current_user.username,
            db=db
        )
        
        return db_mapping
    
    except BusinessException:
        # 业务异常直接抛出（事务装饰器会自动回滚）
        raise
    except Exception as e:
        # 其他异常：事务装饰器会自动回滚，这里只做日志记录
        raise BusinessException(
            error_code="INTERNAL_ERROR",
            detail=f"创建本厂编号映射失败: {str(e)}",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/factory-product-mappings", response_model=List[FactoryProductMappingResponse])
async def list_factory_product_mappings(
    customer_id: Optional[str] = None,
    factory_product_number: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取本厂编号映射列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(FactoryProductMapping)
    
    if customer_id:
        query = query.filter(FactoryProductMapping.customer_id == customer_id)
    if factory_product_number:
        query = query.filter(FactoryProductMapping.factory_product_number == factory_product_number)
    
    # 预加载关联数据，避免N+1查询
    # 注意：material 和 production_version 关系在模型中未定义，因此只预加载 customer
    query = query.options(
        joinedload(FactoryProductMapping.customer)
    )
    
    mappings = query.offset(skip).limit(limit).all()
    return mappings


# 注意：更具体的路由必须放在更通用的路由之前，避免路由冲突
@router.get("/factory-product-mappings/by-id/{mapping_id}", response_model=FactoryProductMappingResponse)
async def get_factory_product_mapping_by_id(
    mapping_id: int,
    db: Session = Depends(get_db)
):
    """根据ID获取本厂编号映射"""
    from backend.common.exceptions import NotFoundException
    
    mapping = db.query(FactoryProductMapping).filter(
        FactoryProductMapping.id == mapping_id,
        FactoryProductMapping.is_deleted == False
    ).first()
    
    if not mapping:
        raise NotFoundException(
            resource_type="FactoryProductMapping",
            resource_id=str(mapping_id)
        )
    
    return mapping


@router.get("/factory-product-mappings/{customer_id}/{product_number}/history")
async def get_factory_product_mapping_history(
    customer_id: str,
    product_number: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """获取本厂编号映射历史（指定时间段内的所有映射）"""
    from backend.services.mapping_service import MappingService
    from datetime import datetime, timedelta
    
    # 如果没有指定日期，默认查询最近一年的历史
    if not start_date:
        start_date = datetime.now() - timedelta(days=365)
    
    mappings = MappingService.find_mappings_in_period(
        customer_id=customer_id,
        factory_product_number=product_number,
        start_date=start_date,
        end_date=end_date,
        db=db
    )
    
    return mappings


@router.get("/factory-product-mappings/{customer_id}/{product_number}")
async def get_factory_product_mapping(
    customer_id: str,
    product_number: str,
    db: Session = Depends(get_db)
):
    """获取本厂编号映射（查找当前有效的默认映射）"""
    from backend.services.mapping_service import MappingService
    from backend.common.exceptions import NotFoundException
    
    mapping = MappingService.find_mapping(
        customer_id=customer_id,
        factory_product_number=product_number,
        db=db
    )
    
    if not mapping:
        raise NotFoundException(
            resource_type="FactoryProductMapping",
            resource_id=f"{customer_id}/{product_number}",
            detail=f"未找到本厂编号映射: {product_number}（客户: {customer_id}）"
        )
    
    return mapping


@router.put("/factory-product-mappings/{mapping_id}", response_model=FactoryProductMappingResponse)
async def update_factory_product_mapping(
    mapping_id: int,
    mapping: FactoryProductMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新本厂编号映射（带冲突检测）"""
    from backend.services.mapping_service import MappingService
    from backend.common.exceptions import BusinessException
    
    try:
        mapping_data = {}
        if mapping.customer_id is not None:
            mapping_data["customer_id"] = mapping.customer_id
        if mapping.factory_product_number is not None:
            mapping_data["factory_product_number"] = mapping.factory_product_number
        if mapping.material_code is not None:
            mapping_data["material_code"] = mapping.material_code
        if mapping.production_version_id is not None:
            mapping_data["production_version_id"] = mapping.production_version_id
        if mapping.is_default is not None:
            mapping_data["is_default"] = mapping.is_default
        if mapping.effective_date is not None:
            mapping_data["effective_date"] = mapping.effective_date
        if mapping.expiry_date is not None:
            mapping_data["expiry_date"] = mapping.expiry_date
        
        db_mapping = MappingService.update_factory_product_mapping(
            mapping_id=mapping_id,
            mapping_data=mapping_data,
            current_user=current_user.username,
            db=db
        )
        
        return db_mapping
    
    except BusinessException:
        # 业务异常直接抛出（事务装饰器会自动回滚）
        raise
    except Exception as e:
        # 其他异常：事务装饰器会自动回滚
        raise BusinessException(
            error_code="INTERNAL_ERROR",
            detail=f"更新本厂编号映射失败: {str(e)}",
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/factory-product-mappings/{mapping_id}")
async def delete_factory_product_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除本厂编号映射（软删除）"""
    db_mapping = db.query(FactoryProductMapping).filter(
        FactoryProductMapping.id == mapping_id
    ).first()
    
    if not db_mapping:
        raise HTTPException(status_code=404, detail="映射不存在")
    
    db_mapping.is_deleted = True
    db_mapping.updated_by = current_user.username
    db.commit()
    return {"message": "映射已删除"}


# ── 发货单（销售出库：DRAFT --ship--> SHIPPED --deliver--> DELIVERED） ──
class DeliveryCreate(BaseModel):
    sales_order_number: str = Field(..., description="来源销售订单号")
    quantity: float = Field(..., gt=0, description="发货数量")
    unit_price: Optional[float] = Field(None, description="销售单价（默认取订单单价）")
    remarks: Optional[str] = None


def _delivery_dict(d: SalesDelivery) -> dict:
    return {
        "delivery_number": d.delivery_number,
        "sales_order_number": d.sales_order_number,
        "customer_id": d.customer_id,
        "customer_name": d.customer_name,
        "material_code": d.material_code,
        "quantity": float(d.quantity or 0),
        "unit": d.unit,
        "unit_price": float(d.unit_price or 0),
        "status": d.status.value if hasattr(d.status, "value") else str(d.status),
        "ship_date": d.ship_date.isoformat() if d.ship_date else None,
        "delivery_date": d.delivery_date.isoformat() if d.delivery_date else None,
        "remarks": d.remarks,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _shipped_qty(db: Session, order_number: str) -> float:
    """订单有效发货量（非 CANCELLED 的 Σquantity）。"""
    rows = (
        db.query(SalesDelivery)
        .filter(
            SalesDelivery.sales_order_number == order_number,
            SalesDelivery.is_deleted.is_(False),
            SalesDelivery.status != DeliveryStatus.CANCELLED,
        )
        .all()
    )
    return float(sum((r.quantity or 0) for r in rows))


def _sync_order_ship_status(db: Session, order_number: str) -> None:
    """联动销售订单状态：全量发货→SHIPPED；全部签收→DELIVERED。"""
    order = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_number == order_number, SalesOrder.is_deleted.is_(False))
        .first()
    )
    if not order:
        return
    deliveries = (
        db.query(SalesDelivery)
        .filter(
            SalesDelivery.sales_order_number == order_number,
            SalesDelivery.is_deleted.is_(False),
            SalesDelivery.status != DeliveryStatus.CANCELLED,
        )
        .all()
    )
    if not deliveries:
        return
    total = float(sum((d.quantity or 0) for d in deliveries))
    shipped_qty = float(sum((d.quantity or 0) for d in deliveries if d.status in (
        DeliveryStatus.SHIPPED, DeliveryStatus.DELIVERED)))
    delivered_qty = float(sum((d.quantity or 0) for d in deliveries if d.status == DeliveryStatus.DELIVERED))
    if delivered_qty >= float(order.quantity or 0) and delivered_qty >= total:
        order.status = SalesOrderStatus.DELIVERED
    elif shipped_qty >= float(order.quantity or 0) and shipped_qty >= total:
        order.status = SalesOrderStatus.SHIPPED
    order.updated_at = datetime.now()


@router.get("/deliveries")
def list_deliveries(
    customer_id: Optional[str] = None,
    order_number: Optional[str] = None,
    delivery_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(SalesDelivery).filter(SalesDelivery.is_deleted.is_(False))
    if customer_id:
        query = query.filter(SalesDelivery.customer_id == customer_id)
    if order_number:
        query = query.filter(SalesDelivery.sales_order_number == order_number)
    if delivery_status:
        query = query.filter(SalesDelivery.status == DeliveryStatus(delivery_status))
    total = query.count()
    rows = query.order_by(SalesDelivery.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_delivery_dict(d) for d in rows]}


@router.get("/deliveries/{delivery_number}")
def get_delivery(delivery_number: str, db: Session = Depends(get_db)):
    d = (
        db.query(SalesDelivery)
        .filter(SalesDelivery.delivery_number == delivery_number, SalesDelivery.is_deleted.is_(False))
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail=f"发货单不存在: {delivery_number}")
    return _delivery_dict(d)


@router.post("/deliveries", status_code=http_status.HTTP_201_CREATED)
def create_delivery(
    payload: DeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建发货单（DRAFT）。两阶段校验：订单存在 → 可发余量。"""
    order = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.order_number == payload.sales_order_number,
            SalesOrder.is_deleted.is_(False),
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"销售订单不存在: {payload.sales_order_number}")
    if not order.material_code:
        raise HTTPException(status_code=400, detail="销售订单缺少物料编码，无法发货")
    already = _shipped_qty(db, order.order_number)
    if already + payload.quantity > float(order.quantity or 0) + 1e-9:
        raise HTTPException(
            status_code=400,
            detail=f"超发：订单 {order.order_number} 数量 {float(order.quantity)}，"
                   f"已发 {already}，本次 {payload.quantity}",
        )
    number = NumberGenerator.generate_document_number(db, SalesDelivery, "delivery_number", "DK", 4)
    customer = db.query(Customer).filter(Customer.customer_id == order.customer_id).first()
    d = SalesDelivery(
        delivery_number=number,
        sales_order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=(customer.trade_name or customer.legal_name) if customer else None,
        material_code=order.material_code,
        quantity=payload.quantity,
        unit=order.sales_unit or "PCS",
        unit_price=payload.unit_price if payload.unit_price is not None else float(order.unit_price or 0),
        status=DeliveryStatus.DRAFT,
        remarks=payload.remarks,
        created_by=current_user.username,
    )
    db.add(d)
    db.flush()  # 坑2：同事务生成下一张单号前先落库
    db.commit()
    return _delivery_dict(d)


def _load_delivery(db: Session, delivery_number: str) -> SalesDelivery:
    d = (
        db.query(SalesDelivery)
        .filter(SalesDelivery.delivery_number == delivery_number, SalesDelivery.is_deleted.is_(False))
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail=f"发货单不存在: {delivery_number}")
    return d


@router.post("/deliveries/{delivery_number}/ship")
def ship_delivery(
    delivery_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发货出库：扣成品库存 + 记 SALES_ISSUE 流水 + 订单状态联动。"""
    d = _load_delivery(db, delivery_number)
    if d.status != DeliveryStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"发货单状态为 {d.status.value}，不允许发货")
    material = db.query(Material).filter(Material.material_code == d.material_code).first()
    if not material:
        raise HTTPException(status_code=400, detail=f"物料不存在: {d.material_code}")
    if float(material.current_stock or 0) < float(d.quantity or 0):
        raise HTTPException(
            status_code=400,
            detail=f"库存不足：当前 {float(material.current_stock or 0)}，需 {float(d.quantity)}",
        )
    material.current_stock = float(material.current_stock or 0) - float(d.quantity or 0)
    db.add(MaterialTransaction(
        transaction_number=NumberGenerator.generate_document_number(
            db, MaterialTransaction, "transaction_number", "TXN", 6),
        material_code=d.material_code,
        transaction_type="SALES_ISSUE",
        quantity=-float(d.quantity or 0),
        unit=d.unit,
        reference_number=d.delivery_number,
        reference_type="SALES_DELIVERY",
        transaction_date=datetime.now(),
        operator=current_user.username,
        remarks=f"发货出库 {d.delivery_number}",
        created_by=current_user.username,
    ))
    d.status = DeliveryStatus.SHIPPED
    d.ship_date = datetime.now()
    d.updated_by = current_user.username
    d.updated_at = datetime.now()
    db.flush()
    _sync_order_ship_status(db, d.sales_order_number)
    db.commit()
    return _delivery_dict(d)


@router.post("/deliveries/{delivery_number}/deliver")
def deliver_delivery(
    delivery_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """客户签收：SHIPPED → DELIVERED。"""
    d = _load_delivery(db, delivery_number)
    if d.status != DeliveryStatus.SHIPPED:
        raise HTTPException(status_code=400, detail=f"发货单状态为 {d.status.value}，不允许签收")
    d.status = DeliveryStatus.DELIVERED
    d.delivery_date = datetime.now()
    d.updated_by = current_user.username
    d.updated_at = datetime.now()
    db.flush()
    _sync_order_ship_status(db, d.sales_order_number)
    db.commit()
    return _delivery_dict(d)


@router.post("/deliveries/{delivery_number}/cancel")
def cancel_delivery(
    delivery_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """作废：DRAFT 直接作废；SHIPPED 需红字冲回出库；DELIVERED 禁止作废。"""
    d = _load_delivery(db, delivery_number)
    if d.status == DeliveryStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="发货单已作废")
    if d.status == DeliveryStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="已签收的发货单不允许作废，请走退货流程")
    if d.status == DeliveryStatus.SHIPPED:
        # 红字冲回：库存回补 + 正向流水
        material = db.query(Material).filter(Material.material_code == d.material_code).first()
        if material:
            material.current_stock = float(material.current_stock or 0) + float(d.quantity or 0)
        db.add(MaterialTransaction(
            transaction_number=NumberGenerator.generate_document_number(
                db, MaterialTransaction, "transaction_number", "TXN", 6),
            material_code=d.material_code,
            transaction_type="SALES_ISSUE_REVERSE",
            quantity=float(d.quantity or 0),
            unit=d.unit,
            reference_number=d.delivery_number,
            reference_type="SALES_DELIVERY",
            transaction_date=datetime.now(),
            operator=current_user.username,
            remarks=f"作废冲回 {d.delivery_number}",
            created_by=current_user.username,
        ))
    d.status = DeliveryStatus.CANCELLED
    d.updated_by = current_user.username
    d.updated_at = datetime.now()
    db.flush()
    _sync_order_ship_status(db, d.sales_order_number)
    db.commit()
    return _delivery_dict(d)


# ── 销售发票 + 应收台账（开票生成应收流水；核销 P1） ──────────────────
class InvoiceCreate(BaseModel):
    sales_order_number: str = Field(..., description="来源销售订单号")
    delivery_number: Optional[str] = Field(None, description="关联发货单（可空）")
    amount: float = Field(..., gt=0, description="开票金额")
    due_date: Optional[datetime] = Field(None, description="到期日（默认取订单交付期）")
    remarks: Optional[str] = None


def _invoice_dict(i: SalesInvoice) -> dict:
    return {
        "invoice_number": i.invoice_number,
        "sales_order_number": i.sales_order_number,
        "delivery_number": i.delivery_number,
        "customer_id": i.customer_id,
        "customer_name": i.customer_name,
        "amount": float(i.amount or 0),
        "currency": i.currency,
        "status": i.status.value if hasattr(i.status, "value") else str(i.status),
        "invoice_date": i.invoice_date.isoformat() if i.invoice_date else None,
        "due_date": i.due_date.isoformat() if i.due_date else None,
        "received_amount": float(i.received_amount or 0),
        "remarks": i.remarks,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _shipped_value(db: Session, order_number: str) -> float:
    """订单已发货量（SHIPPED+DELIVERED）× 单价 的可开票上限。"""
    rows = (
        db.query(SalesDelivery)
        .filter(
            SalesDelivery.sales_order_number == order_number,
            SalesDelivery.is_deleted.is_(False),
            SalesDelivery.status.in_([DeliveryStatus.SHIPPED, DeliveryStatus.DELIVERED]),
        )
        .all()
    )
    return float(sum(float(d.quantity or 0) * float(d.unit_price or 0) for d in rows))


def _invoiced_amount(db: Session, order_number: str) -> float:
    rows = (
        db.query(SalesInvoice)
        .filter(
            SalesInvoice.sales_order_number == order_number,
            SalesInvoice.is_deleted.is_(False),
            SalesInvoice.status != InvoiceStatus.CANCELLED,
        )
        .all()
    )
    return float(sum(float(i.amount or 0) for i in rows))


def _check_invoice_cap(
    db: Session, order_number: str, amount: float, exclude_invoice_number: Optional[str] = None
) -> None:
    order = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_number == order_number, SalesOrder.is_deleted.is_(False))
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"销售订单不存在: {order_number}")
    cap = _shipped_value(db, order_number)
    already = _invoiced_amount(db, order_number)
    if exclude_invoice_number:
        # issue 复查时排除自身（自身金额已含在 already 中）
        self_row = (
            db.query(SalesInvoice)
            .filter(SalesInvoice.invoice_number == exclude_invoice_number)
            .first()
        )
        if self_row:
            already -= float(self_row.amount or 0)
    if already + amount > cap + 1e-6:
        raise HTTPException(
            status_code=400,
            detail=f"超开：已发货可开票上限 {cap:.2f}，已开 {already:.2f}，本次 {amount:.2f}",
        )


@router.get("/invoices")
def list_invoices(
    customer_id: Optional[str] = None,
    order_number: Optional[str] = None,
    invoice_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(SalesInvoice).filter(SalesInvoice.is_deleted.is_(False))
    if customer_id:
        query = query.filter(SalesInvoice.customer_id == customer_id)
    if order_number:
        query = query.filter(SalesInvoice.sales_order_number == order_number)
    if invoice_status:
        query = query.filter(SalesInvoice.status == InvoiceStatus(invoice_status))
    total = query.count()
    rows = query.order_by(SalesInvoice.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_invoice_dict(i) for i in rows]}


@router.get("/receivables")
def receivables_summary(
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """应收台账：按客户聚合 发票额/已收/未收/账龄分段（核销 P1）。"""
    query = db.query(SalesInvoice).filter(SalesInvoice.is_deleted.is_(False))
    if customer_id:
        query = query.filter(SalesInvoice.customer_id == customer_id)
    invoices = query.all()
    by_customer: dict[str, dict] = {}
    now = datetime.now()
    for i in invoices:
        if i.status == InvoiceStatus.CANCELLED:
            continue
        row = by_customer.setdefault(
            i.customer_id,
            {
                "customer_id": i.customer_id,
                "customer_name": i.customer_name,
                "invoiced_amount": 0.0,
                "received_amount": 0.0,
                "outstanding_amount": 0.0,
                "aging": {"current": 0.0, "d30": 0.0, "d60": 0.0, "d90": 0.0, "d90p": 0.0},
                "invoice_count": 0,
            },
        )
        amount = float(i.amount or 0)
        outstanding = amount - float(i.received_amount or 0)
        row["invoiced_amount"] += amount
        row["received_amount"] += float(i.received_amount or 0)
        row["outstanding_amount"] += outstanding
        row["invoice_count"] += 1
        bucket = "current"
        if i.due_date and outstanding > 0:
            overdue_days = (now - i.due_date).days
            if overdue_days > 90:
                bucket = "d90p"
            elif overdue_days > 60:
                bucket = "d90"
            elif overdue_days > 30:
                bucket = "d60"
            elif overdue_days > 0:
                bucket = "d30"
        row["aging"][bucket] += outstanding
    items = sorted(by_customer.values(), key=lambda r: r["outstanding_amount"], reverse=True)
    return {
        "total": len(items),
        "items": items,
        "totals": {
            "invoiced_amount": round(sum(r["invoiced_amount"] for r in items), 2),
            "received_amount": round(sum(r["received_amount"] for r in items), 2),
            "outstanding_amount": round(sum(r["outstanding_amount"] for r in items), 2),
        },
    }


@router.get("/invoices/{invoice_number}")
def get_invoice(invoice_number: str, db: Session = Depends(get_db)):
    i = (
        db.query(SalesInvoice)
        .filter(SalesInvoice.invoice_number == invoice_number, SalesInvoice.is_deleted.is_(False))
        .first()
    )
    if not i:
        raise HTTPException(status_code=404, detail=f"发票不存在: {invoice_number}")
    return _invoice_dict(i)


@router.post("/invoices", status_code=http_status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建销售发票（DRAFT）：挂单校验 + 超开校验。"""
    order = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.order_number == payload.sales_order_number,
            SalesOrder.is_deleted.is_(False),
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"销售订单不存在: {payload.sales_order_number}")
    if payload.delivery_number:
        d = (
            db.query(SalesDelivery)
            .filter(
                SalesDelivery.delivery_number == payload.delivery_number,
                SalesDelivery.is_deleted.is_(False),
            )
            .first()
        )
        if not d:
            raise HTTPException(status_code=404, detail=f"发货单不存在: {payload.delivery_number}")
        if d.status not in (DeliveryStatus.SHIPPED, DeliveryStatus.DELIVERED):
            raise HTTPException(
                status_code=400,
                detail=f"发货单 {payload.delivery_number} 状态为 {d.status.value}，未发货不得开票",
            )
    _check_invoice_cap(db, order.order_number, payload.amount)
    customer = db.query(Customer).filter(Customer.customer_id == order.customer_id).first()
    number = NumberGenerator.generate_document_number(db, SalesInvoice, "invoice_number", "INV", 4)
    due = payload.due_date or order.delivery_date or datetime.now()
    i = SalesInvoice(
        invoice_number=number,
        sales_order_number=order.order_number,
        delivery_number=payload.delivery_number,
        customer_id=order.customer_id,
        customer_name=(customer.trade_name or customer.legal_name) if customer else None,
        amount=payload.amount,
        currency=order.currency or "CNY",
        status=InvoiceStatus.DRAFT,
        invoice_date=datetime.now(),
        due_date=due,
        received_amount=0,
        remarks=payload.remarks,
        created_by=current_user.username,
    )
    db.add(i)
    db.flush()  # 坑2：同事务生成流水号前先落库
    db.commit()
    return _invoice_dict(i)


@router.post("/invoices/{invoice_number}/issue")
def issue_invoice(
    invoice_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认开票：DRAFT → ISSUED，生成应收流水（INVOICE，正金额）。"""
    i = (
        db.query(SalesInvoice)
        .filter(SalesInvoice.invoice_number == invoice_number, SalesInvoice.is_deleted.is_(False))
        .first()
    )
    if not i:
        raise HTTPException(status_code=404, detail=f"发票不存在: {invoice_number}")
    if i.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"发票状态为 {i.status.value}，不允许开票")
    _check_invoice_cap(db, i.sales_order_number, float(i.amount or 0), exclude_invoice_number=i.invoice_number)
    i.status = InvoiceStatus.ISSUED
    i.updated_by = current_user.username
    i.updated_at = datetime.now()
    db.flush()
    db.add(ReceivableEntry(
        entry_number=NumberGenerator.generate_document_number(
            db, ReceivableEntry, "entry_number", "AR", 4),
        invoice_number=i.invoice_number,
        customer_id=i.customer_id,
        entry_type=ReceivableEntryType.INVOICE,
        amount=float(i.amount or 0),
        entry_date=datetime.now(),
        reference_number=i.invoice_number,
        remarks=f"开票应收 {i.invoice_number}",
        created_by=current_user.username,
    ))
    db.commit()
    return _invoice_dict(i)


# ── 收款单 + 核销（PAID 冲减发票 received_amount；台账流水记 RECEIPT） ──
class ReceiptAllocationItem(BaseModel):
    invoice_number: str
    allocated_amount: float = Field(..., gt=0)


class ReceiptCreate(BaseModel):
    customer_id: str = Field(..., description="客户编码")
    amount: float = Field(..., gt=0, description="收款金额")
    method: str = Field("TRANSFER", description="收款方式 TRANSFER/CASH/BILL")
    remarks: Optional[str] = None


class ReceiptPayPayload(BaseModel):
    allocations: list[ReceiptAllocationItem] = Field(default_factory=list)


def _receipt_dict(r: Receipt, allocations: Optional[list[ReceiptAllocation]] = None) -> dict:
    data = {
        "receipt_number": r.receipt_number,
        "customer_id": r.customer_id,
        "customer_name": r.customer_name,
        "amount": float(r.amount or 0),
        "receipt_date": r.receipt_date.isoformat() if r.receipt_date else None,
        "method": r.method.value if hasattr(r.method, "value") else str(r.method),
        "status": r.status,
        "remarks": r.remarks,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "allocated_amount": 0.0,
        "allocations": [],
    }
    if allocations is not None:
        data["allocated_amount"] = round(sum(float(a.allocated_amount or 0) for a in allocations), 2)
        data["allocations"] = [
            {"invoice_number": a.invoice_number, "allocated_amount": float(a.allocated_amount or 0)}
            for a in allocations
        ]
    return data


def _load_receipt(db: Session, number: str) -> Receipt:
    r = (
        db.query(Receipt)
        .filter(Receipt.receipt_number == number, Receipt.is_deleted.is_(False))
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail=f"收款单不存在: {number}")
    return r


def _receipt_allocations(db: Session, number: str) -> list[ReceiptAllocation]:
    return db.query(ReceiptAllocation).filter(ReceiptAllocation.receipt_number == number).all()


@router.get("/receipts")
def list_receipts(
    customer_id: Optional[str] = None,
    receipt_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Receipt).filter(Receipt.is_deleted.is_(False))
    if customer_id:
        query = query.filter(Receipt.customer_id == customer_id)
    if receipt_status:
        query = query.filter(Receipt.status == receipt_status)
    total = query.count()
    rows = query.order_by(Receipt.id.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [_receipt_dict(r, _receipt_allocations(db, r.receipt_number)) for r in rows],
    }


@router.get("/receipts/{receipt_number}")
def get_receipt(receipt_number: str, db: Session = Depends(get_db)):
    r = _load_receipt(db, receipt_number)
    return _receipt_dict(r, _receipt_allocations(db, receipt_number))


@router.post("/receipts", status_code=http_status.HTTP_201_CREATED)
def create_receipt(
    payload: ReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建收款单（DRAFT）。核销在 pay 时进行。"""
    if payload.method not in ("TRANSFER", "CASH", "BILL"):
        raise HTTPException(status_code=400, detail=f"收款方式非法: {payload.method}")
    customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    number = NumberGenerator.generate_document_number(db, Receipt, "receipt_number", "RC", 4)
    r = Receipt(
        receipt_number=number,
        customer_id=payload.customer_id,
        customer_name=(customer.trade_name or customer.legal_name) if customer else None,
        amount=payload.amount,
        receipt_date=datetime.now(),
        method=payload.method,
        status="DRAFT",
        remarks=payload.remarks,
        created_by=current_user.username,
    )
    db.add(r)
    db.flush()
    db.commit()
    return _receipt_dict(r)


@router.post("/receipts/{receipt_number}/pay")
def pay_receipt(
    receipt_number: str,
    payload: ReceiptPayPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """收款核销（DRAFT → PAID）：冲减发票 received_amount + 联动状态 + AR 流水 RECEIPT（负金额）。"""
    r = _load_receipt(db, receipt_number)
    if r.status != "DRAFT":
        raise HTTPException(status_code=400, detail=f"收款单状态为 {r.status}，不允许核销")
    if not payload.allocations:
        raise HTTPException(status_code=400, detail="核销至少需要一张发票明细")
    used = 0.0
    for item in payload.allocations:
        invoice = (
            db.query(SalesInvoice)
            .filter(
                SalesInvoice.invoice_number == item.invoice_number,
                SalesInvoice.is_deleted.is_(False),
            )
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail=f"发票不存在: {item.invoice_number}")
        if invoice.status not in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID):
            raise HTTPException(
                status_code=400,
                detail=f"发票 {item.invoice_number} 状态为 {invoice.status.value}，不可核销",
            )
        outstanding = float(invoice.amount or 0) - float(invoice.received_amount or 0)
        if item.allocated_amount > outstanding + 1e-6:
            raise HTTPException(
                status_code=400,
                detail=f"超收核销：发票 {item.invoice_number} 未收余额 {outstanding:.2f}，本次 {item.allocated_amount:.2f}",
            )
        used += item.allocated_amount
    if used > float(r.amount or 0) + 1e-6:
        raise HTTPException(
            status_code=400,
            detail=f"核销超收款额：收款 {float(r.amount):.2f}，本次合计 {used:.2f}",
        )
    for item in payload.allocations:
        invoice = (
            db.query(SalesInvoice)
            .filter(SalesInvoice.invoice_number == item.invoice_number)
            .first()
        )
        invoice.received_amount = float(invoice.received_amount or 0) + item.allocated_amount
        if invoice.received_amount >= float(invoice.amount or 0) - 1e-6:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        invoice.updated_by = current_user.username
        invoice.updated_at = datetime.now()
        db.add(ReceiptAllocation(
            receipt_number=r.receipt_number,
            invoice_number=item.invoice_number,
            allocated_amount=item.allocated_amount,
            created_by=current_user.username,
        ))
        db.flush()  # 坑2：流水号生成前先落库
        db.add(ReceivableEntry(
            entry_number=NumberGenerator.generate_document_number(
                db, ReceivableEntry, "entry_number", "AR", 4),
            invoice_number=item.invoice_number,
            customer_id=r.customer_id,
            entry_type=ReceivableEntryType.RECEIPT,
            amount=-item.allocated_amount,
            entry_date=datetime.now(),
            reference_number=r.receipt_number,
            remarks=f"收款核销 {r.receipt_number}",
            created_by=current_user.username,
        ))
    r.status = "PAID"
    r.updated_by = current_user.username
    r.updated_at = datetime.now()
    db.commit()
    return _receipt_dict(r, _receipt_allocations(db, receipt_number))


@router.post("/receipts/{receipt_number}/cancel")
def cancel_receipt(
    receipt_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """作废收款单：仅 DRAFT；PAID 单已冲减发票，需红字流程（未在 P1 范围）。"""
    r = _load_receipt(db, receipt_number)
    if r.status != "DRAFT":
        raise HTTPException(status_code=400, detail=f"收款单状态为 {r.status}，不允许作废")
    r.status = "CANCELLED"
    r.updated_by = current_user.username
    r.updated_at = datetime.now()
    db.commit()
    return _receipt_dict(r)

