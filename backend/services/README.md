# 服务层说明

## 概述

服务层（Services Layer）是业务逻辑的集中处理层，负责将API路由与数据模型分离，提高代码的可维护性和可复用性。

## 目录结构

```
backend/services/
├── __init__.py
├── mapping_service.py          # 本厂编号映射服务
├── sales_order_service.py      # 销售订单服务
└── production_order_service.py # 生产订单服务
```

## 设计原则

1. **单一职责**：每个服务类只负责一个业务领域
2. **静态方法**：服务方法使用 `@staticmethod` 装饰器，便于调用
3. **异常处理**：服务层抛出统一的业务异常（`BusinessException`）
4. **数据验证**：服务层负责业务规则验证

## 服务说明

### MappingService（映射服务）

负责本厂编号到物料编码和生产版本的映射逻辑。

**主要方法：**
- `find_mapping()`: 查找本厂编号映射
- `resolve_material_code()`: 解析本厂编号到物料编码和生产版本
- `calculate_unit_conversion()`: 计算单位转换
- `calculate_production_quantity()`: 计算生产数量

### SalesOrderService（销售订单服务）

负责销售订单的创建和业务逻辑处理。

**主要方法：**
- `validate_customer()`: 验证客户是否存在
- `validate_quotation()`: 验证报价单
- `resolve_material_info()`: 解析物料信息
- `create_sales_order()`: 创建销售订单（内部使用 MappingService 进行单位转换）

### ProductionOrderService（生产订单服务）

负责生产订单的创建和业务逻辑处理。

**主要方法：**
- `validate_sales_order()`: 验证销售订单
- `validate_production_version()`: 验证生产版本
- `resolve_material_code()`: 解析物料编码
- `create_production_order()`: 创建生产订单（内部使用 MappingService 进行单位转换）

## 使用示例

### 在API路由中使用服务

```python
from backend.services.sales_order_service import SalesOrderService
from backend.common.exceptions import BusinessException

@router.post("/sales-orders")
async def create_sales_order(order: SalesOrderCreate, db: Session, current_user: User):
    try:
        order_data = {
            "customer_id": order.customer_id,
            "product_number": order.product_number,
            # ... 其他字段
        }
        
        db_order = SalesOrderService.create_sales_order(
            order_data=order_data,
            current_user=current_user.username,
            db=db
        )
        
        return db_order
    
    except BusinessException:
        raise  # 业务异常直接抛出
    except Exception as e:
        db.rollback()
        raise BusinessException(
            error_code="INTERNAL_ERROR",
            detail=f"创建失败: {str(e)}"
        )
```

## 错误处理

服务层使用统一的异常类：

- `BusinessException`: 业务异常基类
- `ValidationException`: 验证异常
- `NotFoundException`: 资源不存在异常
- `ConflictException`: 资源冲突异常

所有异常都会被全局异常处理器捕获并返回统一的错误响应格式。

## 未来扩展

- 添加更多服务（如BOM服务、Routing服务等）
- 实现服务层的依赖注入
- 添加服务层的单元测试
- 实现服务层的缓存机制

