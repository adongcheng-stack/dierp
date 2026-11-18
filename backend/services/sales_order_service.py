"""
销售订单服务
"""
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from backend.common.models.sd import Customer, Quotation, SalesOrder, QuotationStatus, SalesOrderStatus
from backend.common.models.eng import ProductionVersion
from backend.common.exceptions import NotFoundException, ValidationException, ErrorCodes
from backend.common.utils.number_generator import NumberGenerator
from backend.common.utils.logger import log_info, log_error
from backend.common.utils.business_rules import BusinessRulesValidator
from backend.common.utils.transaction import transactional
from backend.services.mapping_service import MappingService


class SalesOrderService:
    """销售订单服务"""
    
    @staticmethod
    def validate_customer(customer_id: str, db: Session) -> Customer:
        """
        验证客户是否存在
        
        Args:
            customer_id: 客户ID
            db: 数据库会话
            
        Returns:
            Customer: 客户对象
            
        Raises:
            NotFoundException: 客户不存在
        """
        customer = db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        
        if not customer:
            raise NotFoundException(
                resource_type="Customer",
                resource_id=customer_id
            )
        
        return customer
    
    @staticmethod
    def validate_quotation(
        quotation_number: Optional[str],
        is_return_order: bool,
        db: Session
    ) -> Optional[Quotation]:
        """
        验证报价单（如果提供）
        
        Args:
            quotation_number: 报价单号
            is_return_order: 是否为返单
            db: 数据库会话
            
        Returns:
            Quotation: 报价单对象，如果未提供则返回None
            
        Raises:
            NotFoundException: 报价单不存在
            ValidationException: 报价单状态不正确
        """
        if not quotation_number:
            return None
        
        quotation = db.query(Quotation).filter(
            Quotation.quotation_number == quotation_number
        ).first()
        
        if not quotation:
            raise NotFoundException(
                resource_type="Quotation",
                resource_id=quotation_number
            )
        
        # 根据返单/新单判断允许的报价单状态
        if is_return_order:
            # 返单：只允许使用已关联的报价单
            if quotation.status != QuotationStatus.LINKED:
                raise ValidationException(
                    error_code=ErrorCodes.QUOTATION_STATUS_INVALID,
                    detail=f"返单只能使用已关联的报价单，当前报价单状态: {quotation.status}",
                    field="quotation_status",
                    value=quotation.status
                )
        else:
            # 新单：只允许使用已批准的报价单
            if quotation.status != QuotationStatus.APPROVED:
                raise ValidationException(
                    error_code=ErrorCodes.QUOTATION_STATUS_INVALID,
                    detail=f"新单只能使用已批准的报价单，当前报价单状态: {quotation.status}",
                    field="quotation_status",
                    value=quotation.status
                )
        
        return quotation
    
    @staticmethod
    def resolve_material_info(
        customer_id: str,
        product_number: str,
        material_code: Optional[str],
        production_version_id: Optional[str],
        db: Session
    ) -> Tuple[str, Optional[str]]:
        """
        解析物料信息（物料编码和生产版本）
        
        Args:
            customer_id: 客户ID
            product_number: 本厂编号
            material_code: 物料编码（可选，如果提供则直接使用）
            production_version_id: 生产版本ID（可选）
            db: 数据库会话
            
        Returns:
            tuple: (material_code, production_version_id)
            
        Raises:
            ValidationException: 如果未提供material_code且映射不存在
        """
        # 如果已提供物料编码，直接使用
        if material_code:
            # 验证物料存在
            from backend.common.models.mm import Material
            material = db.query(Material).filter(
                Material.material_code == material_code
            ).first()
            if not material:
                raise NotFoundException(
                    resource_type="Material",
                    resource_id=material_code
                )
            
            # 验证生产版本（如果提供）
            if production_version_id:
                pv = db.query(ProductionVersion).filter(
                    ProductionVersion.production_version_id == production_version_id
                ).first()
                if not pv:
                    raise NotFoundException(
                        resource_type="ProductionVersion",
                        resource_id=production_version_id
                    )
                
                if pv.status not in ["RELEASED", "ACTIVE"]:
                    raise ValidationException(
                        error_code=ErrorCodes.PRODUCTION_VERSION_STATUS_INVALID,
                        detail=f"生产版本状态不可用: {pv.status}",
                        field="production_version_status",
                        value=pv.status
                    )
            
            return material_code, production_version_id
        
        # 如果未提供物料编码，尝试从映射中查找
        try:
            resolved_material_code, resolved_production_version_id = MappingService.resolve_material_code(
                customer_id=customer_id,
                factory_product_number=product_number,
                db=db
            )
            
            # 使用解析出的生产版本（如果未提供）
            final_production_version_id = production_version_id or resolved_production_version_id
            
            return resolved_material_code, final_production_version_id
        
        except NotFoundException:
            raise ValidationException(
                error_code=ErrorCodes.MATERIAL_CODE_REQUIRED,
                detail="物料编码不能为空，请先创建本厂编号映射或手动选择物料",
                field="material_code",
                value=None
            )
    
    
    @staticmethod
    @transactional
    def create_sales_order(
        order_data: dict,
        current_user: str,
        db: Session
    ) -> SalesOrder:
        """
        创建销售订单
        
        Args:
            order_data: 订单数据字典，包含：
                - customer_id: 客户ID
                - quotation_number: 报价单号（可选）
                - product_number: 本厂编号
                - material_code: 物料编码（可选）
                - production_version_id: 生产版本ID（可选）
                - quantity: 销售数量
                - unit_price: 单价
                - delivery_date: 交货日期
                - is_return_order: 是否返单
                - sales_unit: 销售单位（可选）
                - production_unit: 生产单位（可选）
                - conversion_factor: 转换系数（可选）
                - production_quantity: 生产数量（可选）
                - remarks: 备注（可选）
            current_user: 当前用户名
            db: 数据库会话
            
        Returns:
            SalesOrder: 创建的销售订单对象
        """
        log_info("开始创建销售订单", customer_id=order_data["customer_id"], user=current_user)
        
        # 验证客户
        SalesOrderService.validate_customer(order_data["customer_id"], db)
        
        # 验证报价单（如果提供）
        SalesOrderService.validate_quotation(
            quotation_number=order_data.get("quotation_number"),
            is_return_order=order_data.get("is_return_order", False),
            db=db
        )
        
        # 解析物料信息
        material_code, production_version_id = SalesOrderService.resolve_material_info(
            customer_id=order_data["customer_id"],
            product_number=order_data["product_number"],
            material_code=order_data.get("material_code"),
            production_version_id=order_data.get("production_version_id"),
            db=db
        )
        
        # 计算单位转换信息（统一使用 MappingService）
        # 1. 计算单位转换
        sales_unit, production_unit, conversion_factor = MappingService.calculate_unit_conversion(
            material_code=material_code,
            sales_unit=order_data.get("sales_unit"),
            production_unit=order_data.get("production_unit"),
            db=db
        )
        
        # 2. 使用提供的转换系数（如果提供）
        if order_data.get("conversion_factor") is not None:
            conversion_factor = order_data["conversion_factor"]
        
        # 3. 计算生产数量（如果未提供）
        if order_data.get("production_quantity") is not None:
            production_quantity = order_data["production_quantity"]
        else:
            production_quantity = MappingService.calculate_production_quantity(
                sales_quantity=order_data["quantity"],
                sales_unit=sales_unit,
                production_unit=production_unit,
                conversion_factor=conversion_factor
            )
        
        # 生成销售订单号
        order_number = NumberGenerator.generate_sales_order_number(db)
        
        # 计算总金额
        total_amount = order_data["quantity"] * order_data["unit_price"]
        
        # 验证客户信用额度
        from decimal import Decimal
        try:
            BusinessRulesValidator.validate_customer_credit(
                customer_id=order_data["customer_id"],
                order_amount=Decimal(str(total_amount)),
                db=db
            )
        except ValidationException as e:
            log_error("客户信用额度验证失败", error=e, customer_id=order_data["customer_id"], amount=total_amount)
            raise
        
        # 确定初始状态
        initial_status = (
            SalesOrderStatus.DRAFT 
            if not order_data.get("is_return_order", False) 
            else SalesOrderStatus.PENDING_REVIEW
        )
        
        # 创建销售订单
        db_order = SalesOrder(
            order_number=order_number,
            quotation_number=order_data.get("quotation_number"),
            customer_id=order_data["customer_id"],
            product_number=order_data["product_number"],
            quantity=order_data["quantity"],
            unit_price=order_data["unit_price"],
            total_amount=total_amount,
            delivery_date=order_data["delivery_date"],
            status=initial_status,
            is_return_order=order_data.get("is_return_order", False),
            remarks=order_data.get("remarks"),
            material_code=material_code,
            production_version_id=production_version_id,
            sales_unit=sales_unit,
            production_quantity=production_quantity,
            production_unit=production_unit,
            conversion_factor=conversion_factor,
            created_by=current_user
        )
        
        db.add(db_order)
        # 先flush以持久化对象，否则refresh会报未持久化错误
        db.flush()
        # 事务由 @transactional 装饰器自动提交
        db.refresh(db_order)
        
        log_info("销售订单创建成功", order_number=db_order.order_number, customer_id=order_data["customer_id"])
        
        return db_order

