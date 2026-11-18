"""
统一异常处理模块
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class BusinessException(HTTPException):
    """业务异常基类"""
    
    def __init__(
        self,
        error_code: str,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        业务异常
        
        Args:
            error_code: 错误代码（如：CUSTOMER_NOT_FOUND）
            detail: 错误详情信息
            status_code: HTTP状态码
            extra_data: 额外的错误数据
        """
        self.error_code = error_code
        self.extra_data = extra_data or {}
        
        error_detail = {
            "error_code": error_code,
            "message": detail,
            **self.extra_data
        }
        
        super().__init__(status_code=status_code, detail=error_detail)


class ValidationException(BusinessException):
    """验证异常"""
    
    def __init__(
        self,
        error_code: str,
        detail: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        验证异常
        
        Args:
            error_code: 错误代码
            detail: 错误详情
            field: 验证失败的字段名
            value: 验证失败的值
            extra_data: 额外的错误数据
        """
        validation_data = {}
        if field is not None:
            validation_data["field"] = field
        if value is not None:
            validation_data["value"] = str(value)
        
        if extra_data:
            validation_data.update(extra_data)
        
        super().__init__(
            error_code=error_code,
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            extra_data=validation_data
        )


class NotFoundException(BusinessException):
    """资源不存在异常"""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        detail: Optional[str] = None
    ):
        """
        资源不存在异常
        
        Args:
            resource_type: 资源类型（如：Customer, SalesOrder）
            resource_id: 资源ID
            detail: 可选的详细错误信息
        """
        if not detail:
            detail = f"{resource_type}不存在: {resource_id}"
        
        super().__init__(
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            extra_data={"resource_type": resource_type, "resource_id": resource_id}
        )


class ConflictException(BusinessException):
    """资源冲突异常（如重复创建）"""
    
    def __init__(
        self,
        error_code: str,
        detail: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        资源冲突异常
        
        Args:
            error_code: 错误代码
            detail: 错误详情
            resource_type: 资源类型
            resource_id: 资源ID
            extra_data: 额外的错误数据
        """
        conflict_data = {}
        if resource_type:
            conflict_data["resource_type"] = resource_type
        if resource_id:
            conflict_data["resource_id"] = resource_id
        if extra_data:
            conflict_data.update(extra_data)
        
        super().__init__(
            error_code=error_code,
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
            extra_data=conflict_data
        )


class UnauthorizedException(BusinessException):
    """未授权异常"""
    
    def __init__(self, detail: str = "未授权访问"):
        super().__init__(
            error_code="UNAUTHORIZED",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(BusinessException):
    """禁止访问异常"""
    
    def __init__(self, detail: str = "禁止访问"):
        super().__init__(
            error_code="FORBIDDEN",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


# 错误代码定义
class ErrorCodes:
    """错误代码常量"""
    
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # 客户相关
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    CUSTOMER_ALREADY_EXISTS = "CUSTOMER_ALREADY_EXISTS"
    
    # 报价单相关
    QUOTATION_NOT_FOUND = "QUOTATION_NOT_FOUND"
    QUOTATION_STATUS_INVALID = "QUOTATION_STATUS_INVALID"
    
    # 销售订单相关
    SALES_ORDER_NOT_FOUND = "SALES_ORDER_NOT_FOUND"
    SALES_ORDER_STATUS_INVALID = "SALES_ORDER_STATUS_INVALID"
    MATERIAL_CODE_REQUIRED = "MATERIAL_CODE_REQUIRED"
    MAPPING_NOT_FOUND = "MAPPING_NOT_FOUND"
    MATERIAL_NOT_ACTIVE = "MATERIAL_NOT_ACTIVE"
    PRODUCTION_VERSION_INVALID = "PRODUCTION_VERSION_INVALID"
    
    # 本厂编号映射相关
    FACTORY_PRODUCT_MAPPING_NOT_FOUND = "FACTORY_PRODUCT_MAPPING_NOT_FOUND"
    FACTORY_PRODUCT_MAPPING_EXISTS = "FACTORY_PRODUCT_MAPPING_EXISTS"
    FACTORY_PRODUCT_MAPPING_CONFLICT = "FACTORY_PRODUCT_MAPPING_CONFLICT"
    
    # 生产订单相关
    PRODUCTION_ORDER_NOT_FOUND = "PRODUCTION_ORDER_NOT_FOUND"
    PRODUCTION_ORDER_STATUS_INVALID = "PRODUCTION_ORDER_STATUS_INVALID"
    PRODUCTION_VERSION_NOT_FOUND = "PRODUCTION_VERSION_NOT_FOUND"
    PRODUCTION_VERSION_STATUS_INVALID = "PRODUCTION_VERSION_STATUS_INVALID"
    MATERIAL_CODE_MISMATCH = "MATERIAL_CODE_MISMATCH"
    
    # BOM相关
    BOM_NOT_FOUND = "BOM_NOT_FOUND"
    BOM_ALREADY_EXISTS = "BOM_ALREADY_EXISTS"
    BOM_VALIDATION_FAILED = "BOM_VALIDATION_FAILED"
    BOM_ITEM_EMPTY = "BOM_ITEM_EMPTY"
    BOM_CIRCULAR_REFERENCE = "BOM_CIRCULAR_REFERENCE"
    
    # Routing相关
    ROUTING_NOT_FOUND = "ROUTING_NOT_FOUND"
    ROUTING_ALREADY_EXISTS = "ROUTING_ALREADY_EXISTS"
    ROUTING_VALIDATION_FAILED = "ROUTING_VALIDATION_FAILED"
    ROUTING_OPERATION_EMPTY = "ROUTING_OPERATION_EMPTY"
    WORK_CENTER_NOT_FOUND = "WORK_CENTER_NOT_FOUND"
    
    # 物料相关
    MATERIAL_NOT_FOUND = "MATERIAL_NOT_FOUND"
    
    # MI相关
    MI_NOT_FOUND = "MI_NOT_FOUND"
    MI_STATUS_INVALID = "MI_STATUS_INVALID"
    MI_INSTRUCTIONS_EMPTY = "MI_INSTRUCTIONS_EMPTY"
    
    # LOT卡相关
    LOT_CARD_NOT_FOUND = "LOT_CARD_NOT_FOUND"
    
    # 业务规则相关
    CUSTOMER_CREDIT_EXCEEDED = "CUSTOMER_CREDIT_EXCEEDED"
    MATERIAL_STOCK_INSUFFICIENT = "MATERIAL_STOCK_INSUFFICIENT"
    WORK_CENTER_CAPACITY_INSUFFICIENT = "WORK_CENTER_CAPACITY_INSUFFICIENT"
    
    # 状态流转相关
    STATUS_TRANSITION_INVALID = "STATUS_TRANSITION_INVALID"

