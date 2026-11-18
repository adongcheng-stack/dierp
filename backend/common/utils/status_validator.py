"""
状态流转验证器
"""
from typing import Dict, List, Optional
from backend.common.exceptions import ValidationException, ErrorCodes
from backend.common.models.sd import SalesOrderStatus, QuotationStatus, CustomerStatus
from backend.common.models.pp import ProductionOrderStatus, OperationReportStatus
from backend.common.models.eng import BOMStatus, RoutingStatus, MIStatus
# 注意：ProductionVersion 没有状态枚举，使用字符串状态


class StatusTransitionValidator:
    """状态流转验证器基类"""
    
    @staticmethod
    def validate_transition(
        current_status: str,
        new_status: str,
        allowed_transitions: Dict[str, List[str]],
        resource_type: str = "Resource"
    ) -> bool:
        """
        验证状态流转是否合法
        
        Args:
            current_status: 当前状态（字符串或枚举值）
            new_status: 新状态（字符串或枚举值）
            allowed_transitions: 允许的状态流转规则字典
            resource_type: 资源类型（用于错误信息）
            
        Returns:
            bool: 如果流转合法返回True
            
        Raises:
            ValidationException: 如果流转不合法
        """
        # 确保状态值是字符串（处理枚举值）
        # 如果传入的是枚举对象，使用 .value 获取字符串值
        if hasattr(current_status, 'value'):
            current_status_str = current_status.value
        else:
            current_status_str = str(current_status) if current_status else ""
        
        if hasattr(new_status, 'value'):
            new_status_str = new_status.value
        else:
            new_status_str = str(new_status) if new_status else ""
        
        # 如果状态相同，允许（幂等操作）
        if current_status_str == new_status_str:
            return True
        
        # 获取当前状态允许的流转目标
        # 首先尝试直接使用字符串作为键
        allowed_targets_raw = allowed_transitions.get(current_status_str, [])
        
        # 如果没找到，尝试查找枚举值作为键
        if not allowed_targets_raw:
            for key, value in allowed_transitions.items():
                # 如果键是枚举对象，比较其值
                if hasattr(key, 'value'):
                    if key.value == current_status_str:
                        allowed_targets_raw = value
                        break
                # 如果键是字符串，直接比较
                elif str(key) == current_status_str:
                    allowed_targets_raw = value
                    break
        
        # 将允许的目标转换为字符串列表
        # 如果目标是枚举对象，使用 .value；否则转换为字符串
        allowed_targets = []
        for target in allowed_targets_raw:
            if hasattr(target, 'value'):
                allowed_targets.append(target.value)
            else:
                allowed_targets.append(str(target))
        
        if new_status_str not in allowed_targets:
            allowed_str = ", ".join(allowed_targets) if allowed_targets else "无"
            raise ValidationException(
                error_code=ErrorCodes.STATUS_TRANSITION_INVALID,
                detail=f"{resource_type}状态流转不合法：{current_status_str} -> {new_status_str}，允许的流转：{allowed_str}",
                field="status",
                value=new_status_str,
                extra_data={
                    "current_status": current_status_str,
                    "new_status": new_status_str,
                    "allowed_transitions": allowed_targets
                }
            )
        
        return True


class SalesOrderStatusValidator(StatusTransitionValidator):
    """销售订单状态流转验证器"""
    
    # 销售订单状态流转规则
    ALLOWED_TRANSITIONS = {
        SalesOrderStatus.DRAFT: [
            SalesOrderStatus.PENDING_REVIEW,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.PENDING_REVIEW: [
            SalesOrderStatus.REVIEWING,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.REVIEWING: [
            SalesOrderStatus.APPROVED,
            SalesOrderStatus.REJECTED,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.APPROVED: [
            SalesOrderStatus.IN_PRODUCTION,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.REJECTED: [
            SalesOrderStatus.DRAFT,  # 可以修改后重新提交
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.IN_PRODUCTION: [
            SalesOrderStatus.COMPLETED,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.COMPLETED: [
            SalesOrderStatus.SHIPPED,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.SHIPPED: [
            SalesOrderStatus.DELIVERED,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.DELIVERED: [
            SalesOrderStatus.RECONCILED,
            SalesOrderStatus.CANCELLED
        ],
        SalesOrderStatus.RECONCILED: [
            SalesOrderStatus.CLOSED
        ],
        SalesOrderStatus.CLOSED: [],  # 终态，不允许再流转
        SalesOrderStatus.CANCELLED: []  # 终态，不允许再流转
    }
    
    @staticmethod
    def validate_sales_order_status_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        验证销售订单状态流转
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            
        Returns:
            bool: 如果流转合法返回True
            
        Raises:
            ValidationException: 如果流转不合法
        """
        return StatusTransitionValidator.validate_transition(
            current_status=current_status,
            new_status=new_status,
            allowed_transitions=SalesOrderStatusValidator.ALLOWED_TRANSITIONS,
            resource_type="销售订单"
        )


class QuotationStatusValidator(StatusTransitionValidator):
    """报价单状态流转验证器"""
    
    # 报价单状态流转规则
    ALLOWED_TRANSITIONS = {
        QuotationStatus.DRAFT: [
            QuotationStatus.PENDING_SALES,
            QuotationStatus.CANCELLED
        ],
        QuotationStatus.PENDING_SALES: [
            QuotationStatus.PENDING_GENERAL_MANAGER,  # 市场总监审核通过，进入总经理审核
            QuotationStatus.REJECTED,  # 市场总监审核拒绝
            QuotationStatus.CANCELLED
        ],
        QuotationStatus.PENDING_GENERAL_MANAGER: [
            QuotationStatus.APPROVED,  # 总经办审核通过
            QuotationStatus.REJECTED,  # 总经办审核拒绝
            QuotationStatus.CANCELLED
        ],
        QuotationStatus.APPROVED: [
            QuotationStatus.CUSTOMER_CONFIRMED,
            QuotationStatus.LINKED,  # 关联到销售订单
            QuotationStatus.CANCELLED
        ],
        QuotationStatus.REJECTED: [
            QuotationStatus.DRAFT,  # 可以修改后重新提交
            QuotationStatus.CANCELLED
        ],
        QuotationStatus.CUSTOMER_CONFIRMED: [
            QuotationStatus.LINKED,
            QuotationStatus.CANCELLED
        ],
        QuotationStatus.LINKED: [
            QuotationStatus.CANCELLED  # 已关联的报价单只能取消
        ],
        QuotationStatus.CANCELLED: []  # 终态，不允许再流转
    }
    
    @staticmethod
    def validate_quotation_status_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        验证报价单状态流转
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            
        Returns:
            bool: 如果流转合法返回True
            
        Raises:
            ValidationException: 如果流转不合法
        """
        return StatusTransitionValidator.validate_transition(
            current_status=current_status,
            new_status=new_status,
            allowed_transitions=QuotationStatusValidator.ALLOWED_TRANSITIONS,
            resource_type="报价单"
        )


class ProductionOrderStatusValidator(StatusTransitionValidator):
    """生产订单状态流转验证器"""
    
    # 生产订单状态流转规则（使用字符串值作为键）
    ALLOWED_TRANSITIONS = {
        ProductionOrderStatus.DRAFT.value: [
            ProductionOrderStatus.RELEASED.value,
            ProductionOrderStatus.CANCELLED.value
        ],
        ProductionOrderStatus.RELEASED.value: [
            ProductionOrderStatus.IN_PRODUCTION.value,
            ProductionOrderStatus.CANCELLED.value
        ],
        ProductionOrderStatus.IN_PRODUCTION.value: [
            ProductionOrderStatus.COMPLETED.value,
            ProductionOrderStatus.CANCELLED.value
        ],
        ProductionOrderStatus.COMPLETED.value: [
            ProductionOrderStatus.CLOSED.value
        ],
        ProductionOrderStatus.CLOSED.value: [],  # 终态，不允许再流转
        ProductionOrderStatus.CANCELLED.value: []  # 终态，不允许再流转
    }
    
    @staticmethod
    def validate_production_order_status_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        验证生产订单状态流转
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            
        Returns:
            bool: 如果流转合法返回True
            
        Raises:
            ValidationException: 如果流转不合法
        """
        return StatusTransitionValidator.validate_transition(
            current_status=current_status,
            new_status=new_status,
            allowed_transitions=ProductionOrderStatusValidator.ALLOWED_TRANSITIONS,
            resource_type="生产订单"
        )


class CustomerStatusValidator(StatusTransitionValidator):
    """客户状态流转验证器"""
    
    # 客户状态流转规则（根据HF-SD-P010-ZP01流程）
    ALLOWED_TRANSITIONS = {
        CustomerStatus.DRAFT: [
            CustomerStatus.PENDING_SALES_MANAGER,  # 提交审批
            CustomerStatus.INACTIVE
        ],
        CustomerStatus.PENDING_SALES_MANAGER: [
            CustomerStatus.PENDING_GENERAL_MANAGER,  # 销售经理审批通过，直接到总经理（跳过财务）
            CustomerStatus.INACTIVE  # 销售经理拒绝
        ],
        CustomerStatus.PENDING_GENERAL_MANAGER: [
            CustomerStatus.FROZEN,  # 总经理审批通过，进入冻结状态
            CustomerStatus.INACTIVE  # 总经理拒绝
        ],
        CustomerStatus.FROZEN: [
            CustomerStatus.ACTIVE  # 财务激活
        ],
        CustomerStatus.ACTIVE: [
            CustomerStatus.BLOCKED,
            CustomerStatus.INACTIVE
        ],
        CustomerStatus.BLOCKED: [
            CustomerStatus.ACTIVE,
            CustomerStatus.INACTIVE
        ],
        CustomerStatus.INACTIVE: [
            CustomerStatus.PENDING_SALES_MANAGER,  # 可以重新提交审批
            CustomerStatus.DRAFT  # 可以重新编辑为草稿
        ],
        # 兼容旧状态
        CustomerStatus.PENDING_APPROVAL: [
            CustomerStatus.PENDING_SALES_MANAGER,  # 迁移到新流程
            CustomerStatus.ACTIVE,
            CustomerStatus.BLOCKED,
            CustomerStatus.INACTIVE
        ]
    }
    
    @staticmethod
    def validate_customer_status_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        验证客户状态流转
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            
        Returns:
            bool: 如果流转合法返回True
            
        Raises:
            ValidationException: 如果流转不合法
        """
        return StatusTransitionValidator.validate_transition(
            current_status=current_status,
            new_status=new_status,
            allowed_transitions=CustomerStatusValidator.ALLOWED_TRANSITIONS,
            resource_type="客户"
        )


class RoutingStatusValidator(StatusTransitionValidator):
    """工艺路线状态流转验证器"""
    
    # 工艺路线状态流转规则（使用字符串值作为键）
    ALLOWED_TRANSITIONS = {
        RoutingStatus.DRAFT.value: [
            RoutingStatus.RELEASED.value,  # 草稿 -> 已发布（审核通过）
            RoutingStatus.OBSOLETE.value  # 草稿 -> 已废弃（拒绝）
        ],
        RoutingStatus.RELEASED.value: [
            RoutingStatus.OBSOLETE.value  # 已发布 -> 已废弃（废弃）
        ],
        RoutingStatus.OBSOLETE.value: [
            RoutingStatus.DRAFT.value  # 已废弃 -> 草稿（重新编辑）
        ]
    }
    
    @staticmethod
    def validate_routing_status_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        验证工艺路线状态流转
        
        Args:
            current_status: 当前状态
            new_status: 新状态
            
        Returns:
            bool: 如果流转合法返回True
            
        Raises:
            ValidationException: 如果流转不合法
        """
        return StatusTransitionValidator.validate_transition(
            current_status=current_status,
            new_status=new_status,
            allowed_transitions=RoutingStatusValidator.ALLOWED_TRANSITIONS,
            resource_type="工艺路线"
        )

