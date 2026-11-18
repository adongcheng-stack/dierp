"""
PP模块路由 - 生产计划与控制
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime
from backend.common.database.base import get_db
from backend.common.models.user import User
from backend.api.routers.auth import get_current_user
from backend.common.models.pp import (
    WorkCenter, ProductionOrder, OperationReport, ProductionProgress, LotCard, LotCardInstruction,
    WorkCenterType, WorkCenterStatus, ProductionOrderStatus, OperationReportStatus
)
from backend.common.utils.number_generator import NumberGenerator
from backend.services.production_order_service import ProductionOrderService
from backend.common.exceptions import BusinessException
from backend.common.models.sd import SalesOrderStatus

router = APIRouter()


def sync_sales_order_status(sales_order_number: str, db: Session):
    """根据生产订单状态同步更新销售订单状态"""
    from backend.common.models.sd import SalesOrder, SalesOrderStatus
    
    # 获取销售订单
    sales_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == sales_order_number
    ).first()
    
    if not sales_order:
        return
    
    # 获取该销售订单的所有生产订单
    production_orders = db.query(ProductionOrder).filter(
        ProductionOrder.sales_order_number == sales_order_number
    ).all()
    
    if not production_orders:
        return
    
    # 统计生产订单状态
    status_counts = {}
    for po in production_orders:
        # 处理枚举类型的状态
        if isinstance(po.status, ProductionOrderStatus):
            status = po.status.value
        elif hasattr(po.status, 'value'):
            status = po.status.value
        else:
            status = str(po.status)
        status_counts[status] = status_counts.get(status, 0) + 1
    
    total_orders = len(production_orders)
    completed_count = status_counts.get(ProductionOrderStatus.COMPLETED.value, 0)
    in_production_count = status_counts.get(ProductionOrderStatus.IN_PRODUCTION.value, 0)
    released_count = status_counts.get(ProductionOrderStatus.RELEASED.value, 0)
    closed_count = status_counts.get(ProductionOrderStatus.CLOSED.value, 0)
    cancelled_count = status_counts.get(ProductionOrderStatus.CANCELLED.value, 0)
    
    # 状态同步逻辑
    # 处理枚举类型的状态
    if isinstance(sales_order.status, SalesOrderStatus):
        current_status = sales_order.status.value
    elif hasattr(sales_order.status, 'value'):
        current_status = sales_order.status.value
    else:
        current_status = str(sales_order.status)
    
    try:
        # 如果所有生产订单都已完成或已关闭，销售订单状态更新为已完成
        if (completed_count + closed_count) == total_orders and total_orders > 0:
            if current_status != SalesOrderStatus.COMPLETED.value:
                sales_order.status = SalesOrderStatus.COMPLETED
                if hasattr(sales_order, 'updated_by'):
                    sales_order.updated_by = "system"  # 系统自动更新
                db.commit()
                print(f"销售订单 {sales_order_number} 状态已自动更新为 COMPLETED（所有生产订单已完成或已关闭）")
        # 如果有生产订单在生产中，且销售订单状态是已批准，则更新为生产中
        elif in_production_count > 0:
            if current_status == SalesOrderStatus.APPROVED.value:
                sales_order.status = SalesOrderStatus.IN_PRODUCTION
                if hasattr(sales_order, 'updated_by'):
                    sales_order.updated_by = "system"  # 系统自动更新
                db.commit()
                print(f"销售订单 {sales_order_number} 状态已自动更新为 IN_PRODUCTION（有生产订单开始生产）")
        # 如果有生产订单已下达但还未开始生产，且销售订单状态是已批准，保持已批准状态
        elif released_count > 0 and in_production_count == 0:
            # 如果销售订单状态是已批准，保持不变
            pass
    except Exception as e:
        db.rollback()
        print(f"同步销售订单状态时发生错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # 不重新抛出异常，避免影响主流程


# Pydantic模型
class ActivityTypePayload(BaseModel):
    activity_type_id: Optional[str] = None
    description: Optional[str] = None
    standard_rate: Optional[float] = None
    unit_of_measure: Optional[str] = None


class TechnicalAttributePayload(BaseModel):
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    unit: Optional[str] = None


class WorkCenterCreate(BaseModel):
    work_center_id: str
    description: str
    work_center_type: str
    plant_id: str
    status: str = "ACTIVE"
    parent_work_center_id: Optional[str] = None
    hierarchy_level: int = 1
    work_center_category: Optional[str] = None
    usage: Optional[str] = None
    standard_value_key: Optional[str] = None
    control_key: Optional[str] = None
    queue_time: Optional[float] = None
    wait_time: Optional[float] = None
    move_time: Optional[float] = None
    capacity_category: Optional[str] = None
    factory_calendar_id: Optional[str] = None
    shift_start_time: Optional[str] = None
    shift_finish_time: Optional[str] = None
    break_time: Optional[float] = None
    capacity_utilization: Optional[float] = None
    number_of_capacities: Optional[int] = None
    capacity_formula_setup: Optional[str] = None
    capacity_formula_processing: Optional[str] = None
    capacity_formula_teardown: Optional[str] = None
    cost_center_id: Optional[str] = None
    process_category: Optional[str] = None
    activity_types: Optional[List[ActivityTypePayload]] = None
    technical_attributes: Optional[List[TechnicalAttributePayload]] = None


class WorkCenterUpdate(WorkCenterCreate):
    pass


class WorkCenterResponse(BaseModel):
    id: int
    work_center_id: str
    description: str
    work_center_type: str
    status: str
    plant_id: str
    parent_work_center_id: Optional[str] = None
    hierarchy_level: int
    work_center_category: Optional[str] = None
    usage: Optional[str] = None
    standard_value_key: Optional[str] = None
    control_key: Optional[str] = None
    queue_time: Optional[float] = None
    wait_time: Optional[float] = None
    move_time: Optional[float] = None
    capacity_category: Optional[str] = None
    factory_calendar_id: Optional[str] = None
    shift_start_time: Optional[str] = None
    shift_finish_time: Optional[str] = None
    break_time: Optional[float] = None
    capacity_utilization: Optional[float] = None
    number_of_capacities: Optional[int] = None
    capacity_formula_setup: Optional[str] = None
    capacity_formula_processing: Optional[str] = None
    capacity_formula_teardown: Optional[str] = None
    cost_center_id: Optional[str] = None
    process_category: Optional[str] = None
    activity_types: Optional[List[ActivityTypePayload]] = None
    technical_attributes: Optional[List[TechnicalAttributePayload]] = None
    
    class Config:
        from_attributes = True


class ProductionOrderCreate(BaseModel):
    sales_order_number: str
    production_version_id: str  # 改为必填
    material_code: Optional[str] = None  # 改为可选，通过生产版本自动填充
    quantity: float
    unit: str = "PNL"
    planned_start_date: Optional[datetime] = None
    planned_finish_date: Optional[datetime] = None
    lot_number: Optional[str] = None
    remarks: Optional[str] = None


class ProductionOrderUpdate(BaseModel):
    sales_order_number: str
    production_version_id: str  # 改为必填
    material_code: Optional[str] = None  # 改为可选，通过生产版本自动填充
    quantity: float
    unit: str = "PNL"
    planned_start_date: Optional[datetime] = None
    planned_finish_date: Optional[datetime] = None
    lot_number: Optional[str] = None
    remarks: Optional[str] = None


class ProductionOrderResponse(BaseModel):
    id: int
    order_number: str
    sales_order_number: str
    material_code: str
    production_version_id: Optional[str] = None
    quantity: float
    unit: str
    planned_start_date: Optional[datetime] = None
    planned_finish_date: Optional[datetime] = None
    lot_number: Optional[str] = None
    status: str
    remarks: Optional[str] = None
    # 新增字段：关联的销售订单数量和单位转换
    sales_quantity: Optional[float] = None
    sales_unit: Optional[str] = None
    conversion_factor: Optional[float] = None
    
    class Config:
        from_attributes = True


# LOT卡相关Pydantic模型
class LotCardInstructionResponse(BaseModel):
    """LOT卡指令项响应模型"""
    id: int
    lot_number: str
    sequence: int
    operation_code: Optional[str] = None  # 工序代码（参考工艺路线工序）
    operation_name: Optional[str] = None  # 工序名称（参考工艺路线工序）
    instruction_type: Optional[str] = None
    instruction_content: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class LotCardResponse(BaseModel):
    id: int
    lot_number: str
    production_order_number: str
    mi_number: str
    material_code: str
    quantity: float
    unit: str
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None
    instructions: List[LotCardInstructionResponse] = []  # 指令项列表
    
    class Config:
        from_attributes = True


class OperationReportCreate(BaseModel):
    production_order_number: str
    lot_number: Optional[str] = None
    routing_operation_id: Optional[int] = None
    work_center_id: str
    operation_no: str
    operation_name: Optional[str] = None
    reported_quantity: float
    good_quantity: Optional[float] = None
    scrap_quantity: float = 0
    setup_time: float = 0
    machine_time: float = 0
    labor_time: float = 0
    remarks: Optional[str] = None


class OperationReportResponse(BaseModel):
    id: int
    report_number: str
    production_order_number: str
    work_center_id: str
    operation_no: str
    reported_quantity: float
    status: str
    
    class Config:
        from_attributes = True


# 工作中心管理
@router.post("/work-centers", response_model=WorkCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_work_center(
    work_center: WorkCenterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建工作中心"""
    try:
        # 检查工作中心ID是否已存在
        existing = db.query(WorkCenter).filter(
            WorkCenter.work_center_id == work_center.work_center_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工作中心ID已存在: {work_center.work_center_id}"
            )
        
        # 处理状态枚举
        work_center_status = WorkCenterStatus.ACTIVE
        if work_center.status:
            try:
                work_center_status = WorkCenterStatus[work_center.status]
            except KeyError:
                # 如果状态值不在枚举中，尝试使用字符串值
                work_center_status = WorkCenterStatus(work_center.status)
        
        # 处理 activity_types 和 technical_attributes
        activity_types_json = None
        if work_center.activity_types and len(work_center.activity_types) > 0:
            try:
                # Pydantic模型对象需要转换为字典
                activity_types_list = []
                for a in work_center.activity_types:
                    if isinstance(a, dict):
                        activity_types_list.append(a)
                    elif hasattr(a, 'dict'):
                        activity_types_list.append(a.dict())
                    elif hasattr(a, 'model_dump'):  # Pydantic v2
                        activity_types_list.append(a.model_dump())
                    else:
                        activity_types_list.append(a)
                activity_types_json = json.dumps(activity_types_list)
            except Exception as e:
                print(f"序列化 activity_types 失败: {e}")
                import traceback
                traceback.print_exc()
                activity_types_json = None
        
        technical_attributes_json = None
        if work_center.technical_attributes and len(work_center.technical_attributes) > 0:
            try:
                # Pydantic模型对象需要转换为字典
                technical_attributes_list = []
                for t in work_center.technical_attributes:
                    if isinstance(t, dict):
                        technical_attributes_list.append(t)
                    elif hasattr(t, 'dict'):
                        technical_attributes_list.append(t.dict())
                    elif hasattr(t, 'model_dump'):  # Pydantic v2
                        technical_attributes_list.append(t.model_dump())
                    else:
                        technical_attributes_list.append(t)
                technical_attributes_json = json.dumps(technical_attributes_list)
            except Exception as e:
                print(f"序列化 technical_attributes 失败: {e}")
                import traceback
                traceback.print_exc()
                technical_attributes_json = None
        
        db_work_center = WorkCenter(
            work_center_id=work_center.work_center_id,
            description=work_center.description,
            work_center_type=work_center.work_center_type,
            plant_id=work_center.plant_id,
            status=work_center_status,
            parent_work_center_id=work_center.parent_work_center_id,
            hierarchy_level=work_center.hierarchy_level,
            work_center_category=work_center.work_center_category,
            usage=work_center.usage,
            standard_value_key=work_center.standard_value_key,
            control_key=work_center.control_key,
            queue_time=work_center.queue_time,
            wait_time=work_center.wait_time,
            move_time=work_center.move_time,
            capacity_category=work_center.capacity_category,
            factory_calendar_id=work_center.factory_calendar_id,
            shift_start_time=work_center.shift_start_time,
            shift_finish_time=work_center.shift_finish_time,
            break_time=work_center.break_time,
            capacity_utilization=work_center.capacity_utilization,
            number_of_capacities=work_center.number_of_capacities,
            capacity_formula_setup=work_center.capacity_formula_setup,
            capacity_formula_processing=work_center.capacity_formula_processing,
            capacity_formula_teardown=work_center.capacity_formula_teardown,
            cost_center_id=work_center.cost_center_id,
            process_category=work_center.process_category,
            activity_types=activity_types_json,
            technical_attributes=technical_attributes_json,
            created_by=current_user.username
        )
        db.add(db_work_center)
        db.flush()  # 先flush以持久化对象
        db.refresh(db_work_center)
        db.commit()
        
        # 将 JSON 字符串反序列化为列表，以符合响应模型
        if db_work_center.activity_types:
            try:
                db_work_center.activity_types = json.loads(db_work_center.activity_types)
            except Exception:
                db_work_center.activity_types = None
        if db_work_center.technical_attributes:
            try:
                db_work_center.technical_attributes = json.loads(db_work_center.technical_attributes)
            except Exception:
                db_work_center.technical_attributes = None
        
        return db_work_center
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"创建工作中心错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工作中心失败: {str(e)}"
        )


@router.get("/work-centers", response_model=List[WorkCenterResponse])
async def list_work_centers(
    skip: int = 0,
    limit: int = 100,
    plant_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取工作中心列表"""
    query = db.query(WorkCenter)
    if plant_id:
        query = query.filter(WorkCenter.plant_id == plant_id)
    if status:
        query = query.filter(WorkCenter.status == status)
    work_centers = query.offset(skip).limit(limit).all()
    # 反序列化 JSON 字段
    for wc in work_centers:
        if wc.activity_types:
            try:
                wc.activity_types = json.loads(wc.activity_types)
            except Exception:
                wc.activity_types = None
        if wc.technical_attributes:
            try:
                wc.technical_attributes = json.loads(wc.technical_attributes)
            except Exception:
                wc.technical_attributes = None
    return work_centers


@router.get("/work-centers/{work_center_id}", response_model=WorkCenterResponse)
async def get_work_center(
    work_center_id: str,
    db: Session = Depends(get_db)
):
    """获取工作中心详情"""
    work_center = db.query(WorkCenter).filter(
        WorkCenter.work_center_id == work_center_id
    ).first()
    if not work_center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作中心不存在: {work_center_id}"
        )
    # 反序列化 JSON 字段
    if work_center.activity_types:
        try:
            work_center.activity_types = json.loads(work_center.activity_types)
        except Exception:
            work_center.activity_types = None
    if work_center.technical_attributes:
        try:
            work_center.technical_attributes = json.loads(work_center.technical_attributes)
        except Exception:
            work_center.technical_attributes = None
    return work_center


# 生产订单管理
@router.post("/production-orders", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_production_order(
    order: ProductionOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建生产订单"""
    try:
        # 检查销售订单状态（必须在服务层之前验证，因为服务层假设销售订单存在）
        from backend.common.models.sd import SalesOrder
        sales_order = db.query(SalesOrder).filter(
            SalesOrder.order_number == order.sales_order_number
        ).first()
        if not sales_order:
            from backend.common.exceptions import NotFoundException
            raise NotFoundException(
                resource_type="SalesOrder",
                resource_id=order.sales_order_number
            )
        
        if sales_order.status != SalesOrderStatus.APPROVED:
            from backend.common.exceptions import ValidationException, ErrorCodes
            raise ValidationException(
                error_code=ErrorCodes.SALES_ORDER_STATUS_INVALID,
                detail="销售订单必须已审批才能创建生产订单",
                field="sales_order_status",
                value=sales_order.status
            )
        
        # 优先使用销售订单中的生产版本（如果存在）
        production_version_id = sales_order.production_version_id or order.production_version_id
        if not production_version_id:
            from backend.common.exceptions import ValidationException, ErrorCodes
            raise ValidationException(
                error_code=ErrorCodes.PRODUCTION_VERSION_NOT_FOUND,
                detail="销售订单缺少生产版本，请先完善销售订单信息",
                field="production_version_id",
                value=None
            )
        
        # 使用服务层创建生产订单
        order_data = {
            "sales_order_number": order.sales_order_number,
            "production_version_id": production_version_id,
            "material_code": order.material_code,
            "quantity": order.quantity,
            "unit": order.unit,
            "planned_start_date": order.planned_start_date,
            "planned_finish_date": order.planned_finish_date,
            "lot_number": order.lot_number,
            "remarks": order.remarks,
        }
        
        db_order = ProductionOrderService.create_production_order(
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
            detail=f"创建生产订单失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/production-orders", response_model=List[ProductionOrderResponse])
async def list_production_orders(
    skip: int = 0,
    limit: int = 100,
    sales_order_number: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取生产订单列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(ProductionOrder)
    if sales_order_number:
        query = query.filter(ProductionOrder.sales_order_number == sales_order_number)
    if status:
        query = query.filter(ProductionOrder.status == status)
    
    # 预加载关联数据，避免N+1查询
    # 注意：由于模型中的关系被注释，这里使用显式join或延迟加载
    # 如果响应模型需要这些数据，可以考虑使用joinedload
    # query = query.options(
    #     joinedload(ProductionOrder.sales_order),
    #     joinedload(ProductionOrder.material),
    #     joinedload(ProductionOrder.production_version)
    # )
    
    orders = query.offset(skip).limit(limit).all()
    return orders


@router.get("/production-orders/{order_number}", response_model=ProductionOrderResponse)
async def get_production_order(
    order_number: str,
    db: Session = Depends(get_db)
):
    """获取生产订单详情"""
    # 注意：响应模型不包含关联对象，因此不需要预加载
    # 如果需要关联数据，可以使用单独的端点或修改响应模型
    order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    return order


@router.get("/production-orders/{order_number}/operations")
async def get_production_order_operations(
    order_number: str,
    db: Session = Depends(get_db)
):
    """获取生产订单的工艺路线工序列表"""
    # 获取生产订单
    order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    
    # 通过物料编码查找工艺路线
    from backend.common.models.eng import Routing, RoutingOperation
    routing = db.query(Routing).filter(
        Routing.material_code == order.material_code,
        Routing.status == "RELEASED"  # 只获取已发布的工艺路线
    ).order_by(Routing.effective_date.desc()).first()
    
    if not routing:
        # 如果没有已发布的工艺路线，尝试获取草稿状态的
        routing = db.query(Routing).filter(
            Routing.material_code == order.material_code
        ).order_by(Routing.effective_date.desc()).first()
    
    if not routing:
        return []
    
    # 获取该工艺路线的所有工序
    operations = db.query(RoutingOperation).filter(
        RoutingOperation.routing_id == routing.routing_id
    ).order_by(RoutingOperation.operation_no).all()
    
    # 转换为响应格式
    result = []
    for op in operations:
        result.append({
            "id": op.id,
            "routing_id": op.routing_id,
            "operation_no": op.operation_no,
            "operation_code": op.operation_code,
            "operation_name": op.operation_name,
            "operation_type": op.operation_type,
            "work_center_id": op.work_center_id,
            "setup_time": float(op.setup_time) if op.setup_time else 0,
            "machine_time": float(op.machine_time) if op.machine_time else 0,
            "labor_time": float(op.labor_time) if op.labor_time else 0,
            "queue_time": float(op.queue_time) if op.queue_time else 0,
            "cost_relevant": op.cost_relevant,
            "scheduling_relevant": op.scheduling_relevant,
            "remarks": op.remarks
        })
    
    return result


@router.put("/production-orders/{order_number}", response_model=ProductionOrderResponse)
async def update_production_order(
    order_number: str,
    order: ProductionOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新生产订单"""
    db_order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    
    # 检查销售订单是否存在
    from backend.common.models.sd import SalesOrder
    sales_order = db.query(SalesOrder).filter(
        SalesOrder.order_number == order.sales_order_number
    ).first()
    if not sales_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"销售订单不存在: {order.sales_order_number}"
        )
    
    # 检查生产版本是否存在并获取物料编码
    from backend.common.models.eng import ProductionVersion
    production_version = db.query(ProductionVersion).filter(
        ProductionVersion.production_version_id == order.production_version_id
    ).first()
    if not production_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产版本不存在: {order.production_version_id}"
        )
    
    # 使用生产版本中的物料编码（如果用户提供了物料编码，验证是否一致）
    material_code = production_version.material_code
    if order.material_code and order.material_code != material_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"物料编码不匹配：生产版本的物料编码为 {material_code}，但提供的物料编码为 {order.material_code}"
        )
    
    # 从销售订单获取单位转换信息（如果存在）
    from backend.common.models.mm import Material
    material = db.query(Material).filter(
        Material.material_code == material_code
    ).first()
    
    # 更新字段
    db_order.sales_order_number = order.sales_order_number
    db_order.material_code = material_code  # 使用生产版本的物料编码
    db_order.production_version_id = order.production_version_id
    db_order.quantity = order.quantity
    db_order.unit = order.unit
    db_order.planned_start_date = order.planned_start_date
    db_order.planned_finish_date = order.planned_finish_date
    db_order.lot_number = order.lot_number
    db_order.remarks = order.remarks
    
    # 更新单位转换信息（如果销售订单有）
    if sales_order:
        if sales_order.production_quantity:
            db_order.sales_quantity = sales_order.quantity
            db_order.sales_unit = sales_order.sales_unit or (material.base_unit if material else "PCS")
            db_order.conversion_factor = sales_order.conversion_factor or (float(material.conversion_factor) if material and material.conversion_factor else 1.0)
    
    db_order.updated_by = current_user.username
    
    db.commit()
    db.refresh(db_order)
    return db_order


@router.post("/production-orders/{order_number}/release")
async def release_production_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下达生产订单"""
    order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    
    # 检查状态：支持枚举和字符串比较
    current_status_value = order.status.value if isinstance(order.status, ProductionOrderStatus) else str(order.status)
    if current_status_value != ProductionOrderStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"生产订单状态不允许下达: {current_status_value}，当前状态必须是 DRAFT"
        )
    
    try:
        # 添加状态流转验证
        from backend.common.utils.status_validator import ProductionOrderStatusValidator
        # 将枚举值转换为字符串
        current_status_str = order.status.value if isinstance(order.status, ProductionOrderStatus) else str(order.status)
        new_status_str = ProductionOrderStatus.RELEASED.value
        ProductionOrderStatusValidator.validate_production_order_status_transition(
            current_status=current_status_str,
            new_status=new_status_str
        )
        
        # 更新状态
        order.status = ProductionOrderStatus.RELEASED
        order.updated_by = current_user.username
        
        try:
            db.commit()
            db.refresh(order)  # 刷新对象以获取最新状态
        except Exception as db_error:
            db.rollback()
            print(f"数据库提交失败: {type(db_error).__name__}: {db_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"数据库操作失败: {str(db_error)}"
            )
        
        # 同步销售订单状态
        try:
            sync_sales_order_status(order.sales_order_number, db)
        except Exception as e:
            print(f"同步销售订单状态失败: {e}")
            import traceback
            traceback.print_exc()
            # 不抛出异常，避免影响生产订单状态更新
        
        # 将枚举值转换为字符串以便序列化
        status_value = order.status.value if isinstance(order.status, ProductionOrderStatus) else str(order.status)
        return {"message": "生产订单已下达", "status": status_value}
    except HTTPException:
        # 重新抛出 HTTPException，不进行额外处理
        raise
    except Exception as e:
        db.rollback()
        print(f"下达生产订单失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下达生产订单失败: {str(e)}"
        )


@router.post("/production-orders/{order_number}/close")
async def close_production_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """关闭生产订单"""
    order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    
    # 需求规定：当所有工序完成后关闭生产订单（COMPLETED -> CLOSED）
    current_status_str = order.status.value if isinstance(order.status, ProductionOrderStatus) else str(order.status)
    if order.status != ProductionOrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"生产订单仅在「已完成」状态下允许关闭，当前状态: {current_status_str}"
        )
    
    # 添加状态流转验证
    from backend.common.utils.status_validator import ProductionOrderStatusValidator
    new_status_str = ProductionOrderStatus.CLOSED.value
    ProductionOrderStatusValidator.validate_production_order_status_transition(
        current_status=current_status_str,
        new_status=new_status_str
    )
    order.status = ProductionOrderStatus.CLOSED
    order.actual_finish_date = datetime.utcnow()
    order.updated_by = current_user.username
    db.commit()
    
    # 同步销售订单状态（关闭时也检查是否所有订单都完成）
    try:
        sync_sales_order_status(order.sales_order_number, db)
    except Exception as e:
        print(f"同步销售订单状态失败: {e}")
        # 不抛出异常，避免影响生产订单状态更新
    
    return {"message": "生产订单已关闭", "status": order.status}


@router.post("/production-orders/{order_number}/start")
async def start_production_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """开始生产（从已下达转为生产中）"""
    order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    
    # 添加状态流转验证
    from backend.common.utils.status_validator import ProductionOrderStatusValidator
    # 将枚举值转换为字符串
    current_status_str = order.status.value if isinstance(order.status, ProductionOrderStatus) else str(order.status)
    new_status_str = ProductionOrderStatus.IN_PRODUCTION.value
    ProductionOrderStatusValidator.validate_production_order_status_transition(
        current_status=current_status_str,
        new_status=new_status_str
    )
    
    order.status = ProductionOrderStatus.IN_PRODUCTION
    order.actual_start_date = datetime.utcnow()
    order.updated_by = current_user.username
    db.commit()
    
    # 同步销售订单状态
    try:
        sync_sales_order_status(order.sales_order_number, db)
    except Exception as e:
        print(f"同步销售订单状态失败: {e}")
        # 不抛出异常，避免影响生产订单状态更新
    
    return {"message": "生产订单已开始生产", "status": order.status}


@router.post("/production-orders/{order_number}/complete")
async def complete_production_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """完成生产订单"""
    order = db.query(ProductionOrder).filter(
        ProductionOrder.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单不存在: {order_number}"
        )
    
    # 添加状态流转验证
    from backend.common.utils.status_validator import ProductionOrderStatusValidator
    # 将枚举值转换为字符串
    current_status_str = order.status.value if isinstance(order.status, ProductionOrderStatus) else str(order.status)
    new_status_str = ProductionOrderStatus.COMPLETED.value
    ProductionOrderStatusValidator.validate_production_order_status_transition(
        current_status=current_status_str,
        new_status=new_status_str
    )
    
    order.status = ProductionOrderStatus.COMPLETED
    order.actual_finish_date = datetime.utcnow()
    order.updated_by = current_user.username
    db.commit()
    
    # 同步销售订单状态
    try:
        sync_sales_order_status(order.sales_order_number, db)
    except Exception as e:
        print(f"同步销售订单状态失败: {e}")
        # 不抛出异常，避免影响生产订单状态更新
    
    return {"message": "生产订单已完成", "status": order.status}


# 工序报工
@router.post("/operation-reports", response_model=OperationReportResponse, status_code=status.HTTP_201_CREATED)
async def create_operation_report(
    report: OperationReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建工序报工"""
    try:
        # 检查生产订单是否存在
        production_order = db.query(ProductionOrder).filter(
            ProductionOrder.order_number == report.production_order_number
        ).first()
        if not production_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"生产订单不存在: {report.production_order_number}"
            )
        
        # 从生产订单关联的LOT卡读取lot_number
        lot_card = db.query(LotCard).filter(
            LotCard.production_order_number == report.production_order_number
        ).first()
        
        if not lot_card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"生产订单 {report.production_order_number} 没有关联的LOT卡，无法进行报工"
            )
        
        # 使用LOT卡的lot_number
        lot_number = lot_card.lot_number
        
        # 验证生产订单状态：只有生产中的状态才能报工
        production_order_status_value = production_order.status.value if isinstance(production_order.status, ProductionOrderStatus) else str(production_order.status)
        if production_order_status_value != ProductionOrderStatus.IN_PRODUCTION.value:
            from backend.common.exceptions import ValidationException, ErrorCodes
            raise ValidationException(
                error_code=ErrorCodes.PRODUCTION_ORDER_STATUS_INVALID,
                detail=f"生产订单状态不允许报工: 当前状态为 {production_order_status_value}，只有生产中的订单（IN_PRODUCTION）才能进行工序报工",
                field="production_order_status",
                value=production_order_status_value
            )
        
        # 检查工作中心是否存在
        work_center = db.query(WorkCenter).filter(
            WorkCenter.work_center_id == report.work_center_id
        ).first()
        if not work_center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工作中心不存在: {report.work_center_id}"
            )
        
        # 生成报工单号（确保订单号长度足够）
        order_suffix = report.production_order_number[-4:] if len(report.production_order_number) >= 4 else report.production_order_number
        report_number = f"OR-{datetime.now().strftime('%Y%m%d')}-{order_suffix}"
        
        # 检查报工单号是否已存在
        existing = db.query(OperationReport).filter(OperationReport.report_number == report_number).first()
        if existing:
            # 如果已存在，添加序号
            import random
            report_number = f"OR-{datetime.now().strftime('%Y%m%d')}-{order_suffix}-{random.randint(1000, 9999)}"
        
        good_quantity = report.good_quantity if report.good_quantity is not None else report.reported_quantity
        
        db_report = OperationReport(
            report_number=report_number,
            production_order_number=report.production_order_number,
            lot_number=lot_number,  # 使用从LOT卡读取的lot_number
            routing_operation_id=report.routing_operation_id,
            work_center_id=report.work_center_id,
            operation_no=report.operation_no,
            operation_name=report.operation_name,
            reported_quantity=report.reported_quantity,
            good_quantity=good_quantity,
            scrap_quantity=report.scrap_quantity or 0,
            setup_time=report.setup_time or 0,
            machine_time=report.machine_time or 0,
            labor_time=report.labor_time or 0,
            status=OperationReportStatus.PENDING,
            reported_by=current_user.username,
            reported_at=datetime.utcnow(),
            remarks=report.remarks,
            created_by=current_user.username
        )
        db.add(db_report)
        
        # 更新生产进度
        try:
            progress = db.query(ProductionProgress).filter(
                ProductionProgress.production_order_number == report.production_order_number,
                ProductionProgress.operation_no == report.operation_no
            ).first()
            
            if not progress:
                progress = ProductionProgress(
                    production_order_number=report.production_order_number,
                    operation_no=report.operation_no,
                    operation_name=report.operation_name,
                    work_center_id=report.work_center_id,
                    planned_quantity=production_order.quantity,
                    completed_quantity=0,
                    in_progress_quantity=0,
                    status="PENDING",
                    created_by=current_user.username
                )
                db.add(progress)
            
            progress.completed_quantity += good_quantity
            progress.completion_rate = (progress.completed_quantity / progress.planned_quantity * 100) if progress.planned_quantity > 0 else 0
            if progress.completed_quantity >= progress.planned_quantity:
                progress.status = "COMPLETED"
                progress.actual_finish_time = datetime.utcnow()
        except Exception as e:
            # 如果更新进度失败，记录错误但不影响报工
            print(f"更新生产进度失败: {e}")
            import traceback
            traceback.print_exc()
        
        db.commit()
        db.refresh(db_report)
        return db_report
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"创建工序报工错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工序报工失败: {str(e)}"
        )


@router.get("/operation-reports", response_model=List[OperationReportResponse])
async def list_operation_reports(
    skip: int = 0,
    limit: int = 100,
    production_order_number: Optional[str] = None,
    work_center_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取工序报工列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(OperationReport)
    if production_order_number:
        query = query.filter(OperationReport.production_order_number == production_order_number)
    if work_center_id:
        query = query.filter(OperationReport.work_center_id == work_center_id)
    
    # 预加载关联数据，避免N+1查询
    query = query.options(
        joinedload(OperationReport.production_order),
        joinedload(OperationReport.work_center),
        joinedload(OperationReport.routing_operation)
    )
    
    reports = query.offset(skip).limit(limit).all()
    return reports


# 生产进度看板
@router.get("/production-progress")
async def get_production_progress(
    production_order_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取生产进度看板数据"""
    query = db.query(ProductionProgress)
    if production_order_number:
        query = query.filter(ProductionProgress.production_order_number == production_order_number)
    progress_list = query.order_by(ProductionProgress.operation_no).all()
    
    return [
        {
            "production_order_number": p.production_order_number,
            "operation_no": p.operation_no,
            "operation_name": p.operation_name,
            "work_center_id": p.work_center_id,
            "planned_quantity": float(p.planned_quantity),
            "completed_quantity": float(p.completed_quantity),
            "in_progress_quantity": float(p.in_progress_quantity),
            "completion_rate": float(p.completion_rate),
            "status": p.status,
            "planned_start_time": p.planned_start_time.isoformat() if p.planned_start_time else None,
            "planned_finish_time": p.planned_finish_time.isoformat() if p.planned_finish_time else None,
            "actual_start_time": p.actual_start_time.isoformat() if p.actual_start_time else None,
            "actual_finish_time": p.actual_finish_time.isoformat() if p.actual_finish_time else None,
        }
        for p in progress_list
    ]


# LOT卡相关接口
@router.get("/lot-cards/{production_order_number}", response_model=LotCardResponse)
async def get_lot_card_by_production_order(
    production_order_number: str,
    db: Session = Depends(get_db)
):
    """根据生产订单号获取LOT卡（包含指令项）"""
    lot_card = db.query(LotCard).filter(
        LotCard.production_order_number == production_order_number,
        LotCard.is_deleted == False
    ).first()
    
    if not lot_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产订单 {production_order_number} 没有关联的LOT卡"
        )
    
    # 加载指令项
    instructions = db.query(LotCardInstruction).filter(
        LotCardInstruction.lot_number == lot_card.lot_number,
        LotCardInstruction.is_deleted == False
    ).order_by(LotCardInstruction.sequence).all()
    
    # 构建响应
    response = LotCardResponse(
        id=lot_card.id,
        lot_number=lot_card.lot_number,
        production_order_number=lot_card.production_order_number,
        mi_number=lot_card.mi_number,
        material_code=lot_card.material_code,
        quantity=float(lot_card.quantity),
        unit=lot_card.unit,
        status=lot_card.status,
        created_at=lot_card.created_at,
        completed_at=lot_card.completed_at,
        remarks=lot_card.remarks,
        instructions=[LotCardInstructionResponse(
            id=inst.id,
            lot_number=inst.lot_number,
            sequence=inst.sequence,
            instruction_type=inst.instruction_type,
            instruction_content=inst.instruction_content,
            description=inst.description
        ) for inst in instructions]
    )
    
    return response


@router.get("/lot-cards", response_model=List[LotCardResponse])
async def list_lot_cards(
    production_order_number: Optional[str] = None,
    mi_number: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取LOT卡列表（包含指令项）"""
    query = db.query(LotCard).filter(LotCard.is_deleted == False)
    
    if production_order_number:
        query = query.filter(LotCard.production_order_number == production_order_number)
    if mi_number:
        query = query.filter(LotCard.mi_number == mi_number)
    if status:
        query = query.filter(LotCard.status == status)
    
    lot_cards = query.order_by(LotCard.created_at.desc()).offset(skip).limit(limit).all()
    
    # 构建响应列表，包含每个LOT卡的指令项
    result = []
    for lot_card in lot_cards:
        # 加载指令项
        instructions = db.query(LotCardInstruction).filter(
            LotCardInstruction.lot_number == lot_card.lot_number,
            LotCardInstruction.is_deleted == False
        ).order_by(LotCardInstruction.sequence).all()
        
        # 构建响应对象
        response = LotCardResponse(
            id=lot_card.id,
            lot_number=lot_card.lot_number,
            production_order_number=lot_card.production_order_number,
            mi_number=lot_card.mi_number,
            material_code=lot_card.material_code,
            quantity=float(lot_card.quantity),
            unit=lot_card.unit,
            status=lot_card.status,
            created_at=lot_card.created_at,
            completed_at=lot_card.completed_at,
            remarks=lot_card.remarks,
            instructions=[LotCardInstructionResponse(
                id=inst.id,
                lot_number=inst.lot_number,
                sequence=inst.sequence,
                operation_code=inst.operation_code,
                operation_name=inst.operation_name,
                instruction_type=inst.instruction_type,
                instruction_content=inst.instruction_content,
                description=inst.description
            ) for inst in instructions]
        )
        result.append(response)
    
    return result


@router.get("/lot-cards/by-lot-number/{lot_number}", response_model=LotCardResponse)
async def get_lot_card_by_lot_number(
    lot_number: str,
    db: Session = Depends(get_db)
):
    """根据LOT卡号获取LOT卡（包含指令项）"""
    lot_card = db.query(LotCard).filter(
        LotCard.lot_number == lot_number,
        LotCard.is_deleted == False
    ).first()
    
    if not lot_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LOT卡不存在: {lot_number}"
        )
    
    # 加载指令项
    instructions = db.query(LotCardInstruction).filter(
        LotCardInstruction.lot_number == lot_number,
        LotCardInstruction.is_deleted == False
    ).order_by(LotCardInstruction.sequence).all()
    
    # 构建响应
    response = LotCardResponse(
        id=lot_card.id,
        lot_number=lot_card.lot_number,
        production_order_number=lot_card.production_order_number,
        mi_number=lot_card.mi_number,
        material_code=lot_card.material_code,
        quantity=float(lot_card.quantity),
        unit=lot_card.unit,
        status=lot_card.status,
        created_at=lot_card.created_at,
        completed_at=lot_card.completed_at,
        remarks=lot_card.remarks,
        instructions=[LotCardInstructionResponse(
            id=inst.id,
            lot_number=inst.lot_number,
            sequence=inst.sequence,
            instruction_type=inst.instruction_type,
            instruction_content=inst.instruction_content,
            description=inst.description
        ) for inst in instructions]
    )
    
    return response


class LotCardInstructionUpdate(BaseModel):
    """LOT卡指令项更新请求模型"""
    sequence: int
    instruction_type: Optional[str] = None
    instruction_content: Optional[str] = None
    description: Optional[str] = None


class LotCardUpdate(BaseModel):
    """LOT卡更新请求模型"""
    remarks: Optional[str] = None
    instructions: Optional[List[LotCardInstructionUpdate]] = None  # 指令项列表


@router.put("/lot-cards/{lot_number}", response_model=LotCardResponse)
async def update_lot_card(
    lot_number: str,
    update_data: LotCardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新LOT卡信息（备注和指令项）"""
    lot_card = db.query(LotCard).filter(
        LotCard.lot_number == lot_number,
        LotCard.is_deleted == False
    ).first()
    
    if not lot_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LOT卡不存在: {lot_number}"
        )
    
    # 更新备注
    if update_data.remarks is not None:
        lot_card.remarks = update_data.remarks
    
    # 更新指令项
    if update_data.instructions is not None:
        # 删除现有指令项（软删除）
        existing_instructions = db.query(LotCardInstruction).filter(
            LotCardInstruction.lot_number == lot_number,
            LotCardInstruction.is_deleted == False
        ).all()
        
        for inst in existing_instructions:
            inst.is_deleted = True
            inst.updated_by = current_user.username
            inst.updated_at = datetime.now()
        
        # 创建新的指令项
        for inst_data in update_data.instructions:
            # 检查序号是否重复
            existing = db.query(LotCardInstruction).filter(
                LotCardInstruction.lot_number == lot_number,
                LotCardInstruction.sequence == inst_data.sequence,
                LotCardInstruction.is_deleted == False
            ).first()
            
            if existing:
                # 更新现有指令项
                existing.operation_code = inst_data.operation_code
                existing.operation_name = inst_data.operation_name
                existing.instruction_type = inst_data.instruction_type
                existing.instruction_content = inst_data.instruction_content
                existing.description = inst_data.description
                existing.updated_by = current_user.username
                existing.updated_at = datetime.now()
                existing.is_deleted = False
            else:
                # 创建新指令项
                new_inst = LotCardInstruction(
                    lot_number=lot_number,
                    sequence=inst_data.sequence,
                    operation_code=inst_data.operation_code,
                    operation_name=inst_data.operation_name,
                    instruction_type=inst_data.instruction_type,
                    instruction_content=inst_data.instruction_content,
                    description=inst_data.description,
                    created_by=current_user.username
                )
                db.add(new_inst)
    
    # 更新修改人和修改时间
    lot_card.updated_by = current_user.username
    lot_card.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(lot_card)
        
        # 重新加载指令项
        instructions = db.query(LotCardInstruction).filter(
            LotCardInstruction.lot_number == lot_number,
            LotCardInstruction.is_deleted == False
        ).order_by(LotCardInstruction.sequence).all()
        
        # 构建响应
        response = LotCardResponse(
            id=lot_card.id,
            lot_number=lot_card.lot_number,
            production_order_number=lot_card.production_order_number,
            mi_number=lot_card.mi_number,
            material_code=lot_card.material_code,
            quantity=float(lot_card.quantity),
            unit=lot_card.unit,
            status=lot_card.status,
            created_at=lot_card.created_at,
            completed_at=lot_card.completed_at,
            remarks=lot_card.remarks,
            instructions=[LotCardInstructionResponse(
                id=inst.id,
                lot_number=inst.lot_number,
                sequence=inst.sequence,
                operation_code=inst.operation_code,
                operation_name=inst.operation_name,
                instruction_type=inst.instruction_type,
                instruction_content=inst.instruction_content,
                description=inst.description
            ) for inst in instructions]
        )
        
        return response
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新LOT卡失败: {str(e)}"
        )

