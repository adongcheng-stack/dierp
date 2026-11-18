"""
业务规则验证模块
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal

from backend.common.exceptions import ValidationException, ErrorCodes
from backend.common.models.mm import Material
from backend.common.models.pp import WorkCenter, ProductionOrder
from backend.common.models.sd import Customer, SalesOrder
from backend.common.models.eng import ProductionVersion, Routing, RoutingOperation


class BusinessRulesValidator:
    """业务规则验证器"""
    
    @staticmethod
    def validate_customer_credit(
        customer_id: str,
        order_amount: Decimal,
        db: Session
    ) -> bool:
        """
        验证客户信用额度
        
        Args:
            customer_id: 客户ID
            order_amount: 订单金额
            db: 数据库会话
            
        Returns:
            bool: 是否通过验证
            
        Raises:
            ValidationException: 信用额度不足时抛出
        """
        customer = db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        
        if not customer:
            return True  # 客户不存在由其他验证处理
        
        # 如果未设置信用额度，跳过验证
        if not customer.credit_limit:
            return True
        
        # 计算当前未完成订单总额
        # TODO: 实现未完成订单总额计算
        # current_unpaid_amount = ...
        
        # 验证信用额度
        credit_limit = Decimal(str(customer.credit_limit))
        if order_amount > credit_limit:
            raise ValidationException(
                error_code="CUSTOMER_CREDIT_EXCEEDED",
                detail=f"订单金额 {order_amount} 超过客户信用额度 {credit_limit}",
                field="order_amount",
                value=float(order_amount)
            )
        
        return True
    
    @staticmethod
    def validate_material_stock(
        material_code: str,
        required_quantity: Decimal,
        db: Session
    ) -> bool:
        """
        验证物料库存是否充足
        
        Args:
            material_code: 物料编码
            required_quantity: 所需数量
            db: 数据库会话
            
        Returns:
            bool: 是否通过验证
            
        Raises:
            ValidationException: 库存不足时抛出
        """
        material = db.query(Material).filter(
            Material.material_code == material_code
        ).first()
        
        if not material:
            return True  # 物料不存在由其他验证处理
        
        current_stock = Decimal(str(material.current_stock or 0))
        safety_stock = Decimal(str(material.safety_stock or 0))
        
        # 检查可用库存（当前库存 - 安全库存）
        available_stock = current_stock - safety_stock
        
        if required_quantity > available_stock:
            raise ValidationException(
                error_code="MATERIAL_STOCK_INSUFFICIENT",
                detail=f"物料 {material_code} 库存不足：需要 {required_quantity}，可用 {available_stock}（当前库存：{current_stock}，安全库存：{safety_stock}）",
                field="required_quantity",
                value=float(required_quantity)
            )
        
        return True
    
    @staticmethod
    def validate_work_center_capacity(
        work_center_id: str,
        required_time: Decimal,
        planned_date: Optional[Any],
        db: Session
    ) -> bool:
        """
        验证工作中心产能是否充足
        
        Args:
            work_center_id: 工作中心ID
            required_time: 所需时间（分钟）
            planned_date: 计划日期
            db: 数据库会话
            
        Returns:
            bool: 是否通过验证
            
        Raises:
            ValidationException: 产能不足时抛出
        """
        work_center = db.query(WorkCenter).filter(
            WorkCenter.work_center_id == work_center_id
        ).first()
        
        if not work_center:
            return True  # 工作中心不存在由其他验证处理
        
        # TODO: 实现产能计算逻辑
        # 需要计算：
        # 1. 工作中心的日产能
        # 2. 计划日期当天的已占用产能
        # 3. 验证是否有足够产能
        
        # 暂时返回True，待实现具体逻辑
        return True
    
    @staticmethod
    def validate_production_order_capacity(
        production_order_data: Dict[str, Any],
        db: Session
    ) -> bool:
        """
        验证生产订单的产能需求
        
        Args:
            production_order_data: 生产订单数据
            db: 数据库会话
            
        Returns:
            bool: 是否通过验证
        """
        production_version_id = production_order_data.get("production_version_id")
        if not production_version_id:
            return True
        
        # 获取生产版本
        pv = db.query(ProductionVersion).filter(
            ProductionVersion.production_version_id == production_version_id
        ).first()
        
        if not pv or not pv.routing_id:
            return True
        
        # 获取工艺路线
        routing = db.query(Routing).filter(
            Routing.routing_id == pv.routing_id
        ).first()
        
        if not routing:
            return True
        
        # 获取所有工序
        operations = db.query(RoutingOperation).filter(
            RoutingOperation.routing_id == routing.routing_id
        ).all()
        
        # 验证每个工序的工作中心产能
        for op in operations:
            if op.work_center_id and op.scheduling_relevant:
                # 计算所需时间
                quantity = Decimal(str(production_order_data.get("quantity", 1)))
                setup_time = Decimal(str(op.setup_time or 0))
                machine_time = Decimal(str(op.machine_time or 0))
                required_time = setup_time + (machine_time * quantity)
                
                # 验证产能
                BusinessRulesValidator.validate_work_center_capacity(
                    work_center_id=op.work_center_id,
                    required_time=required_time,
                    planned_date=production_order_data.get("planned_start_date"),
                    db=db
                )
        
        return True
    
    @staticmethod
    def validate_production_order_materials(
        production_order_data: Dict[str, Any],
        db: Session
    ) -> bool:
        """
        验证生产订单的物料需求
        
        Args:
            production_order_data: 生产订单数据
            db: 数据库会话
            
        Returns:
            bool: 是否通过验证
        """
        production_version_id = production_order_data.get("production_version_id")
        if not production_version_id:
            return True
        
        # 获取生产版本
        pv = db.query(ProductionVersion).filter(
            ProductionVersion.production_version_id == production_version_id
        ).first()
        
        if not pv or not pv.bom_number:
            return True
        
        # TODO: 实现BOM展开和物料需求计算
        # 需要：
        # 1. 展开BOM（考虑多层级）
        # 2. 计算每种物料的需求量（考虑损耗率）
        # 3. 验证每种物料的库存
        
        # 暂时返回True，待实现具体逻辑
        return True

