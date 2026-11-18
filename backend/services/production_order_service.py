"""
生产订单服务
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from backend.common.models.pp import ProductionOrder, ProductionOrderStatus, LotCard, LotCardInstruction
from backend.common.models.sd import SalesOrder
from backend.common.models.eng import ProductionVersion, MI, MIInstruction, MIStatus
from backend.common.models.mm import Material
from backend.common.exceptions import NotFoundException, ValidationException, ErrorCodes
from backend.common.utils.number_generator import NumberGenerator
from backend.common.utils.validators import ProductionVersionValidator
from backend.common.utils.logger import log_info, log_error
from backend.common.utils.business_rules import BusinessRulesValidator
from backend.common.utils.transaction import transactional
from backend.services.mapping_service import MappingService
from datetime import datetime


class ProductionOrderService:
    """生产订单服务"""
    
    @staticmethod
    def validate_sales_order(sales_order_number: str, db: Session) -> SalesOrder:
        """
        验证销售订单是否存在
        
        Args:
            sales_order_number: 销售订单号
            db: 数据库会话
            
        Returns:
            SalesOrder: 销售订单对象
            
        Raises:
            NotFoundException: 销售订单不存在
        """
        sales_order = db.query(SalesOrder).filter(
            SalesOrder.order_number == sales_order_number
        ).first()
        
        if not sales_order:
            raise NotFoundException(
                resource_type="SalesOrder",
                resource_id=sales_order_number
            )
        
        return sales_order
    
    @staticmethod
    def validate_production_version(
        production_version_id: str,
        material_code: Optional[str],
        db: Session
    ) -> ProductionVersion:
        """
        验证生产版本
        
        Args:
            production_version_id: 生产版本ID
            material_code: 物料编码（可选，用于验证一致性）
            db: 数据库会话
            
        Returns:
            ProductionVersion: 生产版本对象
            
        Raises:
            NotFoundException: 生产版本不存在
            ValidationException: 生产版本状态无效或物料编码不一致
        """
        # 验证生产版本存在且状态可用
        pv = ProductionVersionValidator.validate_production_version_status(
            production_version_id=production_version_id,
            db=db,
            allowed_statuses=["RELEASED", "ACTIVE"]
        )
        
        # 如果提供了物料编码，验证一致性
        if material_code and pv.material_code != material_code:
            raise ValidationException(
                error_code=ErrorCodes.MATERIAL_CODE_MISMATCH,
                detail=f"物料编码不匹配：生产版本的物料编码为 {pv.material_code}，但提供的物料编码为 {material_code}",
                field="material_code",
                value=material_code
            )
        
        return pv
    
    @staticmethod
    def resolve_material_code(
        sales_order: SalesOrder,
        production_version: ProductionVersion,
        provided_material_code: Optional[str]
    ) -> str:
        """
        解析物料编码（优先使用生产版本的物料编码）
        
        Args:
            sales_order: 销售订单对象
            production_version: 生产版本对象
            provided_material_code: 提供的物料编码（可选）
            
        Returns:
            str: 物料编码
            
        Raises:
            ValidationException: 物料编码不一致
        """
        # 优先使用生产版本的物料编码
        material_code = production_version.material_code
        
        # 如果提供了物料编码，验证一致性
        if provided_material_code and provided_material_code != material_code:
            raise ValidationException(
                error_code=ErrorCodes.MATERIAL_CODE_MISMATCH,
                detail=f"物料编码不匹配：生产版本的物料编码为 {material_code}，但提供的物料编码为 {provided_material_code}",
                field="material_code",
                value=provided_material_code
            )
        
        return material_code
    
    
    
    @staticmethod
    @transactional
    def create_production_order(
        order_data: dict,
        current_user: str,
        db: Session
    ) -> ProductionOrder:
        """
        创建生产订单
        
        Args:
            order_data: 订单数据字典，包含：
                - sales_order_number: 销售订单号
                - production_version_id: 生产版本ID（必填）
                - material_code: 物料编码（可选，通过生产版本自动填充）
                - quantity: 生产数量
                - unit: 生产单位
                - planned_start_date: 计划开始日期（可选）
                - planned_finish_date: 计划完成日期（可选）
                - lot_number: LOT卡号（可选）
                - remarks: 备注（可选）
            current_user: 当前用户名
            db: 数据库会话
            
        Returns:
            ProductionOrder: 创建的生产订单对象
        """
        log_info("开始创建生产订单", 
                sales_order_number=order_data["sales_order_number"],
                production_version_id=order_data["production_version_id"],
                user=current_user)
        
        # 验证销售订单
        sales_order = ProductionOrderService.validate_sales_order(
            sales_order_number=order_data["sales_order_number"],
            db=db
        )
        
        # 验证生产版本
        production_version = ProductionOrderService.validate_production_version(
            production_version_id=order_data["production_version_id"],
            material_code=order_data.get("material_code"),
            db=db
        )
        
        # 解析物料编码
        material_code = ProductionOrderService.resolve_material_code(
            sales_order=sales_order,
            production_version=production_version,
            provided_material_code=order_data.get("material_code")
        )
        
        # 获取销售订单的单位信息（统一使用 MappingService）
        sales_quantity = float(sales_order.quantity)
        sales_unit = sales_order.sales_unit or "PCS"
        conversion_factor = float(sales_order.conversion_factor) if sales_order.conversion_factor else 1.0
        
        # 计算生产数量
        # 优先使用销售订单中的生产数量信息
        if sales_order.production_quantity:
            production_quantity = float(sales_order.production_quantity)
            production_unit = sales_order.production_unit or order_data.get("unit", "PNL")
        else:
            # 如果提供了生产数量，使用提供的；否则根据单位转换计算
            if order_data.get("quantity") and order_data.get("unit"):
                production_quantity = order_data["quantity"]
                production_unit = order_data["unit"]
            else:
                # 使用 MappingService 计算生产数量
                production_unit = sales_order.production_unit or order_data.get("unit", "PNL")
                production_quantity = MappingService.calculate_production_quantity(
                    sales_quantity=sales_quantity,
                    sales_unit=sales_unit,
                    production_unit=production_unit,
                    conversion_factor=conversion_factor
                )
        
        # 验证业务规则
        try:
            # 验证产能
            BusinessRulesValidator.validate_production_order_capacity(
                production_order_data=order_data,
                db=db
            )
            
            # 验证物料库存
            BusinessRulesValidator.validate_production_order_materials(
                production_order_data=order_data,
                db=db
            )
        except ValidationException as e:
            log_error("生产订单业务规则验证失败", error=e, 
                     sales_order_number=order_data["sales_order_number"])
            raise
        
        # 生成生产订单号
        order_number = NumberGenerator.generate_production_order_number(db)
        
        # 创建生产订单
        db_order = ProductionOrder(
            order_number=order_number,
            sales_order_number=order_data["sales_order_number"],
            material_code=material_code,
            production_version_id=order_data["production_version_id"],
            quantity=production_quantity,
            unit=production_unit,
            sales_quantity=sales_quantity,
            sales_unit=sales_unit,
            conversion_factor=conversion_factor,
            planned_start_date=order_data.get("planned_start_date"),
            planned_finish_date=order_data.get("planned_finish_date"),
            lot_number=order_data.get("lot_number"),
            status=ProductionOrderStatus.DRAFT,
            remarks=order_data.get("remarks"),
            created_by=current_user
        )
        
        db.add(db_order)
        db.flush()  # 先flush，确保生产订单有ID
        
        # 根据MI自动生成LOT卡
        lot_card = ProductionOrderService.create_lot_card_from_mi(
            production_order=db_order,
            production_version=production_version,
            db=db
        )
        
        # 更新生产订单的lot_number
        db_order.lot_number = lot_card.lot_number
        db.flush()
        db.refresh(db_order)
        
        log_info("生产订单创建成功", order_number=db_order.order_number, 
                sales_order_number=order_data["sales_order_number"],
                lot_number=lot_card.lot_number)
        
        return db_order
    
    @staticmethod
    def create_lot_card_from_mi(
        production_order: ProductionOrder,
        production_version: ProductionVersion,
        db: Session
    ) -> LotCard:
        """
        根据MI自动生成LOT卡，并复制MI指令项到LOT卡指令项
        
        Args:
            production_order: 生产订单对象
            production_version: 生产版本对象
            db: 数据库会话
            
        Returns:
            LotCard: 创建的LOT卡对象
            
        Raises:
            NotFoundException: MI不存在
            ValidationException: MI状态无效或缺少指令项
        """
        # 获取MI
        if not production_version.mi_number:
            raise ValidationException(
                error_code=ErrorCodes.MI_NOT_FOUND,
                detail="生产版本缺少MI，无法生成LOT卡",
                field="mi_number",
                value=None
            )
        
        mi = db.query(MI).filter(
            MI.mi_number == production_version.mi_number
        ).first()
        
        if not mi:
            raise NotFoundException(
                resource_type="MI",
                resource_id=production_version.mi_number
            )
        
        # 验证MI状态
        if mi.status != MIStatus.RELEASED:
            raise ValidationException(
                error_code=ErrorCodes.MI_STATUS_INVALID,
                detail=f"MI状态无效，当前状态为 {mi.status}，需要状态为 RELEASED",
                field="mi_status",
                value=mi.status
            )
        
        # 获取MI指令项
        mi_instructions = db.query(MIInstruction).filter(
            MIInstruction.mi_number == mi.mi_number,
            MIInstruction.is_deleted == False
        ).order_by(MIInstruction.sequence).all()
        
        if not mi_instructions:
            raise ValidationException(
                error_code=ErrorCodes.MI_INSTRUCTIONS_EMPTY,
                detail="MI没有指令项，无法生成LOT卡",
                field="mi_instructions",
                value=None
            )
        
        # 生成LOT卡号
        lot_number = NumberGenerator.generate_lot_number(db)
        
        # 创建LOT卡
        lot_card = LotCard(
            lot_number=lot_number,
            production_order_number=production_order.order_number,
            mi_number=mi.mi_number,
            material_code=production_order.material_code,
            quantity=production_order.quantity,
            unit=production_order.unit,
            status="ACTIVE",
            created_by=production_order.created_by
        )
        
        db.add(lot_card)
        db.flush()  # 先flush，确保LOT卡有ID
        
        # 复制MI指令项到LOT卡指令项
        for mi_inst in mi_instructions:
            lot_card_inst = LotCardInstruction(
                lot_number=lot_number,
                sequence=mi_inst.sequence,
                operation_code=mi_inst.operation_code,
                operation_name=mi_inst.operation_name,
                instruction_type=mi_inst.instruction_type,
                instruction_content=mi_inst.instruction_content,
                description=mi_inst.description,
                created_by=production_order.created_by
            )
            db.add(lot_card_inst)
        
        db.flush()
        db.refresh(lot_card)
        
        log_info("LOT卡创建成功", lot_number=lot_number,
                production_order_number=production_order.order_number,
                mi_number=mi.mi_number,
                instructions_count=len(mi_instructions))
        
        return lot_card

