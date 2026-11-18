"""
ENG模块路由 - 工程管理
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from backend.common.database.base import get_db
from backend.common.models.user import User
from backend.api.routers.auth import get_current_user
from backend.common.models.eng import (
    BOM, BOMItem, Routing, RoutingOperation, MI, MIInstruction, ProductionVersion,
    BOMStatus, RoutingStatus, MIStatus
)
from backend.common.models.mm import Material
from backend.common.models.sd import FactoryProductMapping
from backend.common.utils.validators import BOMValidator, RoutingValidator
from backend.common.exceptions import BusinessException, ConflictException, NotFoundException, ErrorCodes

router = APIRouter()


# Pydantic模型
class BOMItemCreate(BaseModel):
    line_number: Optional[int] = None  # 序号（如10, 20, 30），如果未提供则自动生成
    material_code: str
    item_category: Optional[str] = None
    quantity: float
    unit: str
    scrap_rate: Optional[float] = None
    calculation_formula: Optional[str] = None
    layer_code: Optional[str] = None
    material_type: Optional[str] = None
    process_step: Optional[str] = None
    remarks: Optional[str] = None


class BOMCreate(BaseModel):
    bom_number: Optional[str] = None
    parent_material_code: str
    version: str = "V1.0"
    plant_id: Optional[str] = None
    bom_type: Optional[str] = "PRODUCTION"
    base_quantity: float = 1
    base_uom: str = "PNL"
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[str] = None
    items: List[BOMItemCreate]


class BOMItemResponse(BOMItemCreate):
    id: int
    line_number: int

    class Config:
        from_attributes = True


class BOMResponse(BaseModel):
    id: int
    bom_number: str
    version: str
    parent_material_code: str
    plant_id: Optional[str] = None
    bom_type: Optional[str] = None
    base_quantity: float
    base_uom: str
    status: str
    description: Optional[str] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    items: List[BOMItemResponse] = []
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RoutingOperationCreate(BaseModel):
    operation_no: str
    operation_code: str
    operation_name: str
    operation_type: str  # INTERNAL, EXTERNAL, QUALITY
    work_center_id: str
    sop_link: Optional[str] = None

    setup_time: float = 0
    machine_time: float = 0
    labor_time: float = 0
    queue_time: float = 0

    cost_relevant: bool = True
    scheduling_relevant: bool = True
    needs_reporting: bool = Field(default=True, description="confirmationRequired")
    auto_deduct_material: bool = Field(default=False, description="allowAutoBackflush")
    trigger_quality_check: bool = Field(default=False, description="qualityInspection")

    # external params
    service_code: Optional[str] = None
    planned_delivery_days: Optional[float] = None
    estimated_unit_price: Optional[float] = None
    estimated_currency: Optional[str] = None
    suggested_supplier: Optional[str] = None
    generate_purchase_req: bool = Field(default=False, description="generatePurchaseReq")

    # quality params
    inspection_plan_id: Optional[str] = None
    sampling_rate: Optional[float] = None
    verification_logic: Optional[str] = None

    remarks: Optional[str] = None


class RoutingCreate(BaseModel):
    routing_id: Optional[str] = None
    material_code: str
    version: str = "A01"
    description: Optional[str] = None
    plant_id: str
    base_unit: str = "PNL"
    base_quantity: float = 1
    units_per_panel: int = 1
    panel_size: Optional[str] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    change_request_no: Optional[str] = None  # 工程变更单号
    operations: List[RoutingOperationCreate]


class RoutingUpdate(BaseModel):
    material_code: str
    version: str = "A01"
    description: Optional[str] = None
    plant_id: str
    base_unit: str = "PNL"
    base_quantity: float = 1
    units_per_panel: int = 1
    panel_size: Optional[str] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    change_request_no: Optional[str] = None  # 工程变更单号
    operations: List[RoutingOperationCreate]


class RoutingResponse(BaseModel):
    id: int
    routing_id: str
    version: str
    material_code: str
    description: Optional[str] = None
    plant_id: str
    base_unit: str
    base_quantity: float
    units_per_panel: int
    panel_size: Optional[str] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    status: str
    change_request_no: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MIInstructionCreate(BaseModel):
    """MI指令项创建模型"""
    sequence: int
    operation_code: Optional[str] = None  # 工序代码（参考工艺路线工序）
    operation_name: Optional[str] = None  # 工序名称（参考工艺路线工序）
    instruction_type: str
    instruction_content: str
    description: Optional[str] = None


class MICreate(BaseModel):
    mi_number: Optional[str] = None
    material_code: str
    version: str = "V1.0"
    description: Optional[str] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    content: Optional[str] = None  # 保留用于向后兼容
    instructions: Optional[List[MIInstructionCreate]] = None  # 指令项列表


class MIInstructionResponse(BaseModel):
    """MI指令项响应模型"""
    id: int
    mi_number: str
    sequence: int
    operation_code: Optional[str] = None  # 工序代码（参考工艺路线工序）
    operation_name: Optional[str] = None  # 工序名称（参考工艺路线工序）
    instruction_type: Optional[str] = None
    instruction_content: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class MIResponse(BaseModel):
    id: int
    mi_number: str
    version: str
    material_code: str
    description: Optional[str] = None
    status: str
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    content: Optional[str] = None  # 保留用于向后兼容
    created_at: datetime
    created_by: Optional[str] = None
    instructions: List[MIInstructionResponse] = []  # 指令项列表
    
    class Config:
        from_attributes = True


#
# 产品主数据（以本厂编号为核心字段）- MVP：复用原 SD 的 FactoryProductMapping 表
# 迁移到 ENG 模块暴露接口，作为连接设计/生产/销售的关键纽带
#
class ProductMappingCreate(BaseModel):
    customer_id: str
    product_number: str = Field(..., alias="factory_product_number")
    material_code: str
    production_version_id: Optional[str] = None
    is_default: bool = True
    effective_date: datetime
    expiry_date: Optional[datetime] = None


class ProductMappingUpdate(BaseModel):
    customer_id: Optional[str] = None
    product_number: Optional[str] = Field(None, alias="factory_product_number")
    material_code: Optional[str] = None
    production_version_id: Optional[str] = None
    is_default: Optional[bool] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class ProductMappingResponse(BaseModel):
    id: int
    customer_id: str
    product_number: str = Field(..., alias="factory_product_number")
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
        populate_by_name = True


@router.post("/product-mappings", response_model=ProductMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_product_mapping(
    mapping: ProductMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建产品主数据映射（本厂编号 ↔ 物料/生产版本），ENG模块统一管理入口"""
    from backend.services.mapping_service import MappingService

    mapping_data = {
        "customer_id": mapping.customer_id,
        "factory_product_number": mapping.product_number,
        "material_code": mapping.material_code,
        "production_version_id": mapping.production_version_id,
        "is_default": mapping.is_default,
        "effective_date": mapping.effective_date,
        "expiry_date": mapping.expiry_date,
    }
    return MappingService.create_factory_product_mapping(
        mapping_data=mapping_data,
        current_user=current_user.username,
        db=db
    )


@router.get("/product-mappings", response_model=List[ProductMappingResponse])
async def list_product_mappings(
    customer_id: Optional[str] = None,
    product_number: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取产品主数据映射列表"""
    query = db.query(FactoryProductMapping).filter(FactoryProductMapping.is_deleted == False)
    if customer_id:
        query = query.filter(FactoryProductMapping.customer_id == customer_id)
    if product_number:
        query = query.filter(FactoryProductMapping.factory_product_number == product_number)
    return query.offset(skip).limit(limit).all()


@router.get("/product-mappings/by-id/{mapping_id}", response_model=ProductMappingResponse)
async def get_product_mapping_by_id(
    mapping_id: int,
    db: Session = Depends(get_db)
):
    """根据ID获取产品主数据映射"""
    mapping = db.query(FactoryProductMapping).filter(
        FactoryProductMapping.id == mapping_id,
        FactoryProductMapping.is_deleted == False
    ).first()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")
    return mapping


@router.get("/product-mappings/{customer_id}/{product_number}", response_model=ProductMappingResponse)
async def resolve_product_mapping(
    customer_id: str,
    product_number: str,
    db: Session = Depends(get_db)
):
    """解析产品主数据：按客户+本厂编号返回当前有效默认映射（销售/生产/工程统一入口）"""
    from backend.services.mapping_service import MappingService

    mapping = MappingService.find_mapping(
        customer_id=customer_id,
        factory_product_number=product_number,
        db=db
    )
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到产品主数据映射")
    return mapping


@router.put("/product-mappings/{mapping_id}", response_model=ProductMappingResponse)
async def update_product_mapping(
    mapping_id: int,
    mapping: ProductMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新产品主数据映射"""
    from backend.services.mapping_service import MappingService

    mapping_data = {}
    if mapping.customer_id is not None:
        mapping_data["customer_id"] = mapping.customer_id
    if mapping.product_number is not None:
        mapping_data["factory_product_number"] = mapping.product_number
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

    return MappingService.update_factory_product_mapping(
        mapping_id=mapping_id,
        mapping_data=mapping_data,
        current_user=current_user.username,
        db=db
    )


@router.delete("/product-mappings/{mapping_id}")
async def delete_product_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除产品主数据映射（软删除）"""
    db_mapping = db.query(FactoryProductMapping).filter(FactoryProductMapping.id == mapping_id).first()
    if not db_mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")
    db_mapping.is_deleted = True
    db_mapping.updated_by = current_user.username
    db.commit()
    return {"message": "映射已删除"}

class ProductionVersionCreate(BaseModel):
    material_code: str
    bom_number: str
    routing_id: str
    mi_number: Optional[str] = None  # MI可选
    version: str
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    description: Optional[str] = None


# BOM管理
@router.post("/boms", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def create_bom(
    bom: BOMCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建BOM"""
    try:
        # 生成BOM编号
        if not bom.bom_number:
            bom_number = f"BOM-{bom.parent_material_code}-{bom.version}"
        else:
            bom_number = bom.bom_number
        
        # 检查BOM编号是否已存在
        existing = db.query(BOM).filter(BOM.bom_number == bom_number).first()
        if existing:
            raise ConflictException(
                error_code=ErrorCodes.BOM_ALREADY_EXISTS,
                detail=f"BOM编号已存在: {bom_number}",
                resource_type="BOM",
                resource_id=bom_number
            )
        
        # 准备BOM数据用于验证
        bom_data = {
            "parent_material_code": bom.parent_material_code,
            "base_quantity": bom.base_quantity,
            "items": [
                {
                    "line_number": item.line_number,
                    "material_code": item.material_code,
                    "quantity": item.quantity,
                    "scrap_rate": item.scrap_rate,
                }
                for item in bom.items
            ]
        }
        
        # 使用验证服务进行完整验证
        BOMValidator.validate_bom(bom_data, db)
        
        # 创建BOM
        db_bom = BOM(
            bom_number=bom_number,
            version=bom.version,
            parent_material_code=bom.parent_material_code,
            plant_id=bom.plant_id,
            bom_type=bom.bom_type,
            base_quantity=bom.base_quantity,
            base_uom=bom.base_uom,
            effective_date=bom.effective_date,
            expiry_date=bom.expiry_date,
            status=BOMStatus(bom.status) if bom.status else BOMStatus.NEW,
            description=bom.description,
            created_by=current_user.username
        )
        db.add(db_bom)
        
        # 创建BOM明细
        for idx, item in enumerate(bom.items, start=1):
            # 使用前端传入的line_number，如果没有则使用默认序号（10的倍数）
            line_number = item.line_number if item.line_number is not None else idx * 10
            
            bom_item = BOMItem(
                bom_number=bom_number,
                line_number=line_number,
                material_code=item.material_code,
                item_category=item.item_category,
                quantity=item.quantity,
                unit=item.unit,
                scrap_rate=item.scrap_rate,
                calculation_formula=item.calculation_formula,
                layer_code=item.layer_code,
                material_type=item.material_type,
                process_step=item.process_step,
                remarks=item.remarks,
                created_by=current_user.username
            )
            db.add(bom_item)
        
        db.commit()
        db.refresh(db_bom)
        return db_bom
    
    except BusinessException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise BusinessException(
            error_code=ErrorCodes.INTERNAL_ERROR,
            detail=f"创建BOM失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/boms", response_model=List[BOMResponse])
async def list_boms(
    skip: int = 0,
    limit: int = 100,
    parent_material_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取BOM列表（优化：只加载必要字段，不加载关联数据）"""
    from backend.common.models.eng import BOMStatus
    from sqlalchemy.orm import noload
    
    query = db.query(BOM)
    if parent_material_code:
        query = query.filter(BOM.parent_material_code == parent_material_code)
    if status:
        try:
            status_enum = BOMStatus(status)
            query = query.filter(BOM.status == status_enum)
        except ValueError:
            query = query.filter(BOM.status == status)
    
    # 列表查询不需要加载关联数据（items, parent_material等），只返回基本信息
    # 使用noload()明确禁止加载关系，避免Pydantic序列化时触发延迟加载
    query = query.options(
        noload(BOM.items),
        noload(BOM.parent_material),
        noload(BOM.production_versions)
    )
    
    boms = query.order_by(BOM.bom_number).offset(skip).limit(limit).all()
    
    # 手动构建响应，确保状态字段正确序列化，避免访问关系属性
    result = []
    for bom in boms:
        bom_dict = {
            "id": bom.id,
            "bom_number": bom.bom_number,
            "version": bom.version,
            "parent_material_code": bom.parent_material_code,
            "plant_id": bom.plant_id,
            "bom_type": bom.bom_type,
            "base_quantity": float(bom.base_quantity) if bom.base_quantity else 0.0,
            "base_uom": bom.base_uom,
            "status": bom.status.value if hasattr(bom.status, 'value') else str(bom.status),
            "description": bom.description,
            "effective_date": bom.effective_date,
            "expiry_date": bom.expiry_date,
            "items": [],  # 列表查询不返回items，减少数据量
            "created_at": bom.created_at,
            "updated_by": bom.updated_by,
            "updated_at": bom.updated_at
        }
        result.append(bom_dict)
    
    return result


@router.get("/boms/{bom_number}", response_model=BOMResponse)
async def get_bom(
    bom_number: str,
    db: Session = Depends(get_db)
):
    """获取BOM详情（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload, selectinload
    
    bom = db.query(BOM).filter(BOM.bom_number == bom_number).options(
        joinedload(BOM.parent_material),
        selectinload(BOM.items)
    ).first()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOM不存在: {bom_number}"
        )
    # 手动加载明细
    bom.items  # trigger lazy load
    return bom


@router.put("/boms/{bom_number}", response_model=BOMResponse)
async def update_bom(
    bom_number: str,
    bom: BOMCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新BOM"""
    db_bom = db.query(BOM).filter(BOM.bom_number == bom_number).first()
    if not db_bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOM不存在: {bom_number}"
        )
    
    # 检查父项物料是否存在
    parent_material = db.query(Material).filter(
        Material.material_code == bom.parent_material_code
    ).first()
    if not parent_material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"物料不存在: {bom.parent_material_code}"
        )
    
    # 检查是否有BOM明细
    if not bom.items or len(bom.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BOM必须至少包含一个物料明细"
        )
    
    try:
        # 更新基本信息
        db_bom.version = bom.version
        db_bom.parent_material_code = bom.parent_material_code
        db_bom.plant_id = bom.plant_id
        db_bom.bom_type = bom.bom_type
        db_bom.base_quantity = bom.base_quantity
        db_bom.base_uom = bom.base_uom
        db_bom.effective_date = bom.effective_date
        db_bom.expiry_date = bom.expiry_date
        db_bom.status = BOMStatus(bom.status) if bom.status else db_bom.status
        db_bom.description = bom.description
        db_bom.updated_by = current_user.username
        
        # 删除旧明细
        db.query(BOMItem).filter(BOMItem.bom_number == bom_number).delete()
        
        # 创建新明细
        for idx, item in enumerate(bom.items, start=1):
            # 检查物料是否存在
            material = db.query(Material).filter(Material.material_code == item.material_code).first()
            if not material:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"物料不存在: {item.material_code}"
                )
            
            # 使用前端传入的line_number，如果没有则使用默认序号（10的倍数）
            line_number = item.line_number if item.line_number is not None else idx * 10
            
            bom_item = BOMItem(
                bom_number=bom_number,
                line_number=line_number,
                material_code=item.material_code,
                item_category=item.item_category,
                quantity=item.quantity,
                unit=item.unit,
                scrap_rate=item.scrap_rate,
                calculation_formula=item.calculation_formula,
                layer_code=item.layer_code,
                material_type=item.material_type,
                process_step=item.process_step,
                remarks=item.remarks,
                created_by=current_user.username
            )
            db.add(bom_item)
        
        db.commit()
        db.refresh(db_bom)
        return db_bom
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"更新BOM错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新BOM失败: {str(e)}"
        )


# 工艺路线管理
@router.post("/routings", response_model=RoutingResponse, status_code=status.HTTP_201_CREATED)
async def create_routing(
    routing: RoutingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建工艺路线"""
    try:
        # 生成工艺路线ID
        if not routing.routing_id:
            routing_id = f"RT-{routing.material_code}-{routing.version}"
        else:
            routing_id = routing.routing_id
        
        # 检查工艺路线ID是否已存在
        existing = db.query(Routing).filter(Routing.routing_id == routing_id).first()
        if existing:
            raise ConflictException(
                error_code=ErrorCodes.ROUTING_ALREADY_EXISTS,
                detail=f"工艺路线ID已存在: {routing_id}",
                resource_type="Routing",
                resource_id=routing_id
            )
        
        # 准备Routing数据用于验证
        routing_data = {
            "material_code": routing.material_code,
            "operations": [
                {
                    "operation_no": op.operation_no,
                    "operation_code": op.operation_code,
                    "operation_name": op.operation_name,
                    "operation_type": op.operation_type,
                    "work_center_id": op.work_center_id,
                    "setup_time": op.setup_time or 0,
                    "machine_time": op.machine_time or 0,
                    "labor_time": op.labor_time or 0,
                }
                for op in routing.operations
            ]
        }
        
        # 使用验证服务进行完整验证
        RoutingValidator.validate_routing(routing_data, db)
        
        # 创建Routing
        db_routing = Routing(
            routing_id=routing_id,
            version=routing.version,
            material_code=routing.material_code,
            description=routing.description,
            plant_id=routing.plant_id,
            base_unit=routing.base_unit,
            base_quantity=routing.base_quantity,
            units_per_panel=routing.units_per_panel,
            panel_size=routing.panel_size,
            effective_date=routing.effective_date,
            expiry_date=routing.expiry_date,
            status=RoutingStatus.DRAFT,
            change_request_no=routing.change_request_no,
            created_by=current_user.username
        )
        db.add(db_routing)
        
        # 创建工序
        for op in routing.operations:
            routing_operation = RoutingOperation(
                routing_id=routing_id,
                operation_no=op.operation_no,
                operation_code=op.operation_code,
                operation_name=op.operation_name,
                operation_type=op.operation_type,
                work_center_id=op.work_center_id,
                sop_link=op.sop_link,
                setup_time=op.setup_time or 0,
                machine_time=op.machine_time or 0,
                labor_time=op.labor_time or 0,
                queue_time=op.queue_time or 0,
                cost_relevant=op.cost_relevant if op.cost_relevant is not None else True,
                scheduling_relevant=op.scheduling_relevant if op.scheduling_relevant is not None else True,
                needs_reporting=op.needs_reporting if op.needs_reporting is not None else True,
                auto_deduct_material=op.auto_deduct_material if op.auto_deduct_material is not None else False,
                trigger_quality_check=op.trigger_quality_check if op.trigger_quality_check is not None else False,
                service_code=op.service_code,
                planned_delivery_days=op.planned_delivery_days,
                estimated_unit_price=op.estimated_unit_price,
                estimated_currency=op.estimated_currency,
                suggested_supplier=op.suggested_supplier,
                inspection_plan_id=op.inspection_plan_id,
                sampling_rate=op.sampling_rate,
                verification_logic=op.verification_logic,
                remarks=op.remarks,
                created_by=current_user.username
            )
            db.add(routing_operation)
        
        db.commit()
        db.refresh(db_routing)
        return db_routing
    
    except BusinessException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise BusinessException(
            error_code=ErrorCodes.INTERNAL_ERROR,
            detail=f"创建工艺路线失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/routings", response_model=List[RoutingResponse])
async def list_routings(
    skip: int = 0,
    limit: int = 100,
    material_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取工艺路线列表（优化：只加载必要字段，不加载关联数据）"""
    from backend.common.models.eng import RoutingStatus
    
    query = db.query(Routing)
    if material_code:
        query = query.filter(Routing.material_code == material_code)
    if status:
        # 如果status是字符串，转换为枚举进行比较
        try:
            status_enum = RoutingStatus(status)
            query = query.filter(Routing.status == status_enum)
        except ValueError:
            # 如果不是有效的枚举值，使用字符串比较
            query = query.filter(Routing.status == status)
    
    # 列表查询不需要加载关联数据（operations, material等），只返回基本信息
    # 这样可以大大提高查询性能，避免N+1查询和序列化问题
    # 使用noload()明确禁止加载关系，避免Pydantic序列化时触发延迟加载
    from sqlalchemy.orm import noload
    query = query.options(
        noload(Routing.operations),
        noload(Routing.material),
        noload(Routing.production_versions)
    )
    
    routings = query.order_by(Routing.routing_id).offset(skip).limit(limit).all()
    
    # 确保状态字段是字符串，而不是枚举对象
    result = []
    for routing in routings:
        routing_dict = {
            "id": routing.id,
            "routing_id": routing.routing_id,
            "version": routing.version,
            "material_code": routing.material_code,
            "description": routing.description,
            "plant_id": routing.plant_id,
            "base_unit": routing.base_unit,
            "base_quantity": float(routing.base_quantity) if routing.base_quantity else 0.0,
            "units_per_panel": routing.units_per_panel,
            "panel_size": routing.panel_size,
            "effective_date": routing.effective_date,
            "expiry_date": routing.expiry_date,
            "status": routing.status.value if hasattr(routing.status, 'value') else str(routing.status),
            "change_request_no": routing.change_request_no,
            "created_by": routing.created_by,
            "created_at": routing.created_at,
            "updated_by": routing.updated_by,
            "updated_at": routing.updated_at
        }
        result.append(routing_dict)
    
    return result


@router.get("/routings/{routing_id}", response_model=RoutingResponse)
async def get_routing(
    routing_id: str,
    db: Session = Depends(get_db)
):
    """获取工艺路线详情（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload, selectinload
    
    routing = db.query(Routing).filter(
        Routing.routing_id == routing_id
    ).options(
        joinedload(Routing.material),
        selectinload(Routing.operations).joinedload(RoutingOperation.work_center)
    ).first()
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工艺路线不存在: {routing_id}"
        )
    return routing


@router.get("/routings/{routing_id}/operations")
async def get_routing_operations(
    routing_id: str,
    db: Session = Depends(get_db)
):
    """获取工艺路线的工序列表"""
    # 检查工艺路线是否存在
    routing = db.query(Routing).filter(
        Routing.routing_id == routing_id
    ).first()
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工艺路线不存在: {routing_id}"
        )
    
    # 获取该工艺路线的所有工序
    operations = db.query(RoutingOperation).filter(
        RoutingOperation.routing_id == routing_id
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
            "sop_link": op.sop_link,
            "setup_time": float(op.setup_time) if op.setup_time else 0,
            "machine_time": float(op.machine_time) if op.machine_time else 0,
            "labor_time": float(op.labor_time) if op.labor_time else 0,
            "queue_time": float(op.queue_time) if op.queue_time else 0,
            "cost_relevant": op.cost_relevant,
            "scheduling_relevant": op.scheduling_relevant,
            "needs_reporting": op.needs_reporting,
            "auto_deduct_material": op.auto_deduct_material,
            "trigger_quality_check": op.trigger_quality_check,
            "service_code": op.service_code,
            "planned_delivery_days": float(op.planned_delivery_days) if op.planned_delivery_days else None,
            "estimated_unit_price": float(op.estimated_unit_price) if op.estimated_unit_price else None,
            "estimated_currency": op.estimated_currency,
            "suggested_supplier": op.suggested_supplier,
            "inspection_plan_id": op.inspection_plan_id,
            "sampling_rate": float(op.sampling_rate) if op.sampling_rate else None,
            "verification_logic": op.verification_logic,
            "remarks": op.remarks
        })
    
    return result


@router.put("/routings/{routing_id}", response_model=RoutingResponse)
async def update_routing(
    routing_id: str,
    routing: RoutingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新工艺路线"""
    db_routing = db.query(Routing).filter(
        Routing.routing_id == routing_id
    ).first()
    
    if not db_routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工艺路线不存在: {routing_id}"
        )
    
    # 检查物料是否存在
    material = db.query(Material).filter(Material.material_code == routing.material_code).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"物料不存在: {routing.material_code}"
        )
    
    # 检查是否有工序
    if not routing.operations or len(routing.operations) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="工艺路线必须至少包含一个工序"
        )
    
    try:
        # 更新基本信息
        db_routing.material_code = routing.material_code
        db_routing.version = routing.version
        db_routing.description = routing.description
        db_routing.plant_id = routing.plant_id
        db_routing.base_unit = routing.base_unit
        db_routing.base_quantity = routing.base_quantity
        db_routing.units_per_panel = routing.units_per_panel
        db_routing.panel_size = routing.panel_size
        db_routing.effective_date = routing.effective_date
        db_routing.expiry_date = routing.expiry_date
        db_routing.change_request_no = routing.change_request_no
        db_routing.updated_by = current_user.username
        
        # 删除旧工序
        db.query(RoutingOperation).filter(
            RoutingOperation.routing_id == routing_id
        ).delete()
        
        # 创建新工序
        for op in routing.operations:
            routing_operation = RoutingOperation(
                routing_id=routing_id,
                operation_no=op.operation_no,
                operation_code=op.operation_code,
                operation_name=op.operation_name,
                operation_type=op.operation_type,
                work_center_id=op.work_center_id,
                sop_link=op.sop_link,
                setup_time=op.setup_time or 0,
                machine_time=op.machine_time or 0,
                labor_time=op.labor_time or 0,
                queue_time=op.queue_time or 0,
                cost_relevant=op.cost_relevant if op.cost_relevant is not None else True,
                scheduling_relevant=op.scheduling_relevant if op.scheduling_relevant is not None else True,
                needs_reporting=op.needs_reporting if op.needs_reporting is not None else True,
                auto_deduct_material=op.auto_deduct_material if op.auto_deduct_material is not None else False,
                trigger_quality_check=op.trigger_quality_check if op.trigger_quality_check is not None else False,
                service_code=op.service_code,
                planned_delivery_days=op.planned_delivery_days,
                estimated_unit_price=op.estimated_unit_price,
                estimated_currency=op.estimated_currency,
                suggested_supplier=op.suggested_supplier,
                generate_purchase_req=op.generate_purchase_req if op.generate_purchase_req is not None else False,
                inspection_plan_id=op.inspection_plan_id,
                sampling_rate=op.sampling_rate,
                verification_logic=op.verification_logic,
                remarks=op.remarks,
                created_by=current_user.username
            )
            db.add(routing_operation)
        
        db.commit()
        db.refresh(db_routing)
        return db_routing
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"更新工艺路线错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新工艺路线失败: {str(e)}"
        )


# 工艺路线审核相关接口
class ApprovalRequest(BaseModel):
    comment: Optional[str] = None


@router.post("/routings/{routing_id}/submit")
async def submit_routing(
    routing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交工艺路线审核（草稿 -> 已发布）"""
    from backend.common.models.eng import RoutingStatus
    from backend.common.utils.status_validator import RoutingStatusValidator
    
    try:
        routing = db.query(Routing).filter(
            Routing.routing_id == routing_id
        ).first()
        
        if not routing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工艺路线不存在: {routing_id}"
            )
        
        # 只有草稿状态可以提交审核
        if routing.status != RoutingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工艺路线状态不允许提交: {routing.status}"
            )
        
        # 验证状态流转
        RoutingStatusValidator.validate_routing_status_transition(
            current_status=routing.status,
            new_status=RoutingStatus.RELEASED
        )
        
        # 更新状态为已发布
        routing.status = RoutingStatus.RELEASED
        routing.updated_by = current_user.username
        
        db.commit()
        db.refresh(routing)
        
        return {"message": "工艺路线已提交审核并发布", "status": routing.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"提交工艺路线错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交工艺路线失败: {str(e)}"
        )


@router.post("/routings/{routing_id}/reject")
async def reject_routing(
    routing_id: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """拒绝工艺路线（草稿 -> 已废弃）"""
    from backend.common.models.eng import RoutingStatus
    from backend.common.utils.status_validator import RoutingStatusValidator
    
    try:
        routing = db.query(Routing).filter(
            Routing.routing_id == routing_id
        ).first()
        
        if not routing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工艺路线不存在: {routing_id}"
            )
        
        # 只有草稿状态可以拒绝
        if routing.status != RoutingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工艺路线状态不允许拒绝: {routing.status}"
            )
        
        # 验证状态流转
        RoutingStatusValidator.validate_routing_status_transition(
            current_status=routing.status,
            new_status=RoutingStatus.OBSOLETE
        )
        
        # 更新状态为已废弃
        routing.status = RoutingStatus.OBSOLETE
        routing.updated_by = current_user.username
        
        db.commit()
        db.refresh(routing)
        
        return {"message": "工艺路线已拒绝", "status": routing.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"拒绝工艺路线错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"拒绝工艺路线失败: {str(e)}"
        )


@router.post("/routings/{routing_id}/obsolete")
async def obsolete_routing(
    routing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """废弃工艺路线（已发布 -> 已废弃）"""
    from backend.common.models.eng import RoutingStatus
    from backend.common.utils.status_validator import RoutingStatusValidator
    
    try:
        routing = db.query(Routing).filter(
            Routing.routing_id == routing_id
        ).first()
        
        if not routing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工艺路线不存在: {routing_id}"
            )
        
        # 只有已发布状态可以废弃
        if routing.status != RoutingStatus.RELEASED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工艺路线状态不允许废弃: {routing.status}"
            )
        
        # 验证状态流转
        RoutingStatusValidator.validate_routing_status_transition(
            current_status=routing.status,
            new_status=RoutingStatus.OBSOLETE
        )
        
        # 更新状态为已废弃
        routing.status = RoutingStatus.OBSOLETE
        routing.updated_by = current_user.username
        
        db.commit()
        db.refresh(routing)
        
        return {"message": "工艺路线已废弃", "status": routing.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"废弃工艺路线错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"废弃工艺路线失败: {str(e)}"
        )


# MI管理
@router.post("/mis", response_model=MIResponse, status_code=status.HTTP_201_CREATED)
async def create_mi(
    mi: MICreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建MI（制造指令）"""
    # 检查物料是否存在
    material = db.query(Material).filter(Material.material_code == mi.material_code).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"物料不存在: {mi.material_code}"
        )
    
    # 生成MI编号
    if not mi.mi_number:
        mi_number = f"MI-{mi.material_code}-{mi.version}"
    else:
        mi_number = mi.mi_number
    
    # 检查MI编号是否已存在
    existing = db.query(MI).filter(MI.mi_number == mi_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MI编号已存在: {mi_number}"
        )
    
    # 验证指令项序号唯一性
    if mi.instructions:
        sequences = [inst.sequence for inst in mi.instructions]
        if len(sequences) != len(set(sequences)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指令项序号不能重复"
        )
    
    db_mi = MI(
        mi_number=mi_number,
        version=mi.version,
        material_code=mi.material_code,
        description=mi.description,
        effective_date=mi.effective_date,
        expiry_date=mi.expiry_date,
        status=MIStatus.DRAFT,
        created_by=current_user.username
    )
    db.add(db_mi)
    db.flush()  # 先flush，确保MI有ID
    
    # 创建指令项
    if mi.instructions:
        for inst_data in mi.instructions:
            db_inst = MIInstruction(
                mi_number=mi_number,
                sequence=inst_data.sequence,
                operation_code=inst_data.operation_code,
                operation_name=inst_data.operation_name,
                instruction_type=inst_data.instruction_type,
                instruction_content=inst_data.instruction_content,
                description=inst_data.description,
                created_by=current_user.username
            )
            db.add(db_inst)
    
    db.commit()
    db.refresh(db_mi)
    
    # 加载指令项
    instructions = db.query(MIInstruction).filter(
        MIInstruction.mi_number == mi_number,
        MIInstruction.is_deleted == False
    ).order_by(MIInstruction.sequence).all()
    
    # 构建响应
    response = MIResponse(
        id=db_mi.id,
        mi_number=db_mi.mi_number,
        version=db_mi.version,
        material_code=db_mi.material_code,
        description=db_mi.description,
        status=db_mi.status.value if hasattr(db_mi.status, 'value') else str(db_mi.status),
        effective_date=db_mi.effective_date,
        expiry_date=db_mi.expiry_date,
        created_at=db_mi.created_at,
        created_by=db_mi.created_by,
        instructions=[MIInstructionResponse(
            id=inst.id,
            mi_number=inst.mi_number,
            sequence=inst.sequence,
            operation_code=inst.operation_code,
            operation_name=inst.operation_name,
            instruction_type=inst.instruction_type,
            instruction_content=inst.instruction_content,
            description=inst.description
        ) for inst in instructions]
    )
    
    return response


@router.get("/mis", response_model=List[MIResponse])
async def list_mis(
    skip: int = 0,
    limit: int = 100,
    material_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取MI列表（包含指令项）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(MI)
    if material_code:
        query = query.filter(MI.material_code == material_code)
    if status:
        query = query.filter(MI.status == status)
    
    # 预加载关联数据，避免N+1查询
    query = query.options(
        joinedload(MI.material)
    )
    
    mis = query.order_by(MI.created_at.desc()).offset(skip).limit(limit).all()
    
    # 构建响应列表，包含每个MI的指令项
    result = []
    for mi in mis:
        # 加载指令项
        instructions = db.query(MIInstruction).filter(
            MIInstruction.mi_number == mi.mi_number,
            MIInstruction.is_deleted == False
        ).order_by(MIInstruction.sequence).all()
        
        # 构建响应对象
        response = MIResponse(
            id=mi.id,
            mi_number=mi.mi_number,
            version=mi.version,
            material_code=mi.material_code,
            description=mi.description,
            status=mi.status.value if hasattr(mi.status, 'value') else str(mi.status),
            effective_date=mi.effective_date,
            expiry_date=mi.expiry_date,
            created_at=mi.created_at,
            created_by=mi.created_by,
            instructions=[MIInstructionResponse(
                id=inst.id,
                mi_number=inst.mi_number,
                sequence=inst.sequence,
                instruction_type=inst.instruction_type,
                instruction_content=inst.instruction_content,
                description=inst.description
            ) for inst in instructions]
        )
        result.append(response)
    
    return result


@router.get("/mis/{mi_number}", response_model=MIResponse)
async def get_mi(
    mi_number: str,
    db: Session = Depends(get_db)
):
    """获取MI详情（包含指令项）"""
    from sqlalchemy.orm import joinedload
    
    mi = db.query(MI).filter(MI.mi_number == mi_number).options(
        joinedload(MI.material)
    ).first()
    if not mi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MI不存在: {mi_number}"
        )
    
    # 加载指令项
    instructions = db.query(MIInstruction).filter(
        MIInstruction.mi_number == mi_number,
        MIInstruction.is_deleted == False
    ).order_by(MIInstruction.sequence).all()
    
    # 构建响应
    response = MIResponse(
        id=mi.id,
        mi_number=mi.mi_number,
        version=mi.version,
        material_code=mi.material_code,
        description=mi.description,
        status=mi.status.value if hasattr(mi.status, 'value') else str(mi.status),
        effective_date=mi.effective_date,
        expiry_date=mi.expiry_date,
        created_at=mi.created_at,
        created_by=mi.created_by,
        instructions=[MIInstructionResponse(
            id=inst.id,
            mi_number=inst.mi_number,
            sequence=inst.sequence,
            operation_code=inst.operation_code,
            operation_name=inst.operation_name,
            instruction_type=inst.instruction_type,
            instruction_content=inst.instruction_content,
            description=inst.description
        ) for inst in instructions]
    )
    
    return response


class MIUpdate(BaseModel):
    material_code: str
    version: str
    description: Optional[str] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    content: Optional[str] = None  # 保留用于向后兼容
    instructions: Optional[List[MIInstructionCreate]] = None  # 指令项列表


@router.put("/mis/{mi_number}", response_model=MIResponse)
async def update_mi(
    mi_number: str,
    mi: MIUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新MI（包含指令项）"""
    db_mi = db.query(MI).filter(MI.mi_number == mi_number).first()
    if not db_mi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MI不存在: {mi_number}"
        )
    
    # 检查物料是否存在
    material = db.query(Material).filter(Material.material_code == mi.material_code).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"物料不存在: {mi.material_code}"
        )
    
    # 只有草稿状态的MI可以更新
    if db_mi.status != MIStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有草稿状态的MI可以更新，当前状态: {db_mi.status}"
        )
    
    # 验证指令项序号唯一性
    if mi.instructions:
        sequences = [inst.sequence for inst in mi.instructions]
        if len(sequences) != len(set(sequences)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指令项序号不能重复"
        )
    
    db_mi.material_code = mi.material_code
    db_mi.version = mi.version
    db_mi.description = mi.description
    db_mi.effective_date = mi.effective_date
    db_mi.expiry_date = mi.expiry_date
    db_mi.updated_by = current_user.username
    
    # 更新指令项
    if mi.instructions is not None:
        # 删除现有指令项（软删除）
        existing_instructions = db.query(MIInstruction).filter(
            MIInstruction.mi_number == mi_number,
            MIInstruction.is_deleted == False
        ).all()
        
        for inst in existing_instructions:
            inst.is_deleted = True
            inst.updated_by = current_user.username
            # updated_at 由 SQLAlchemy 自动更新
        
        # 创建新的指令项
        for inst_data in mi.instructions:
            # 检查序号是否重复
            existing = db.query(MIInstruction).filter(
                MIInstruction.mi_number == mi_number,
                MIInstruction.sequence == inst_data.sequence,
                MIInstruction.is_deleted == False
            ).first()
            
            if existing:
                # 更新现有指令项
                existing.instruction_type = inst_data.instruction_type
                existing.instruction_content = inst_data.instruction_content
                existing.description = inst_data.description
                existing.updated_by = current_user.username
                existing.is_deleted = False
                # updated_at 由 SQLAlchemy 自动更新
            else:
                # 创建新指令项
                new_inst = MIInstruction(
                    mi_number=mi_number,
                    sequence=inst_data.sequence,
                    instruction_type=inst_data.instruction_type,
                    instruction_content=inst_data.instruction_content,
                    description=inst_data.description,
                    created_by=current_user.username
                )
                db.add(new_inst)
    
    db.commit()
    db.refresh(db_mi)
    
    # 重新加载指令项
    instructions = db.query(MIInstruction).filter(
        MIInstruction.mi_number == mi_number,
        MIInstruction.is_deleted == False
    ).order_by(MIInstruction.sequence).all()
    
    # 构建响应
    response = MIResponse(
        id=db_mi.id,
        mi_number=db_mi.mi_number,
        version=db_mi.version,
        material_code=db_mi.material_code,
        description=db_mi.description,
        status=db_mi.status.value if hasattr(db_mi.status, 'value') else str(db_mi.status),
        effective_date=db_mi.effective_date,
        expiry_date=db_mi.expiry_date,
        created_at=db_mi.created_at,
        created_by=db_mi.created_by,
        instructions=[MIInstructionResponse(
            id=inst.id,
            mi_number=inst.mi_number,
            sequence=inst.sequence,
            operation_code=inst.operation_code,
            operation_name=inst.operation_name,
            instruction_type=inst.instruction_type,
            instruction_content=inst.instruction_content,
            description=inst.description
        ) for inst in instructions]
    )
    
    return response


@router.post("/mis/{mi_number}/submit")
async def submit_mi(
    mi_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交MI审核"""
    mi = db.query(MI).filter(MI.mi_number == mi_number).first()
    if not mi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MI不存在: {mi_number}"
        )
    
    if mi.status != MIStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有草稿状态的MI可以提交审核，当前状态: {mi.status}"
        )
    
    mi.status = MIStatus.REVIEWING
    mi.updated_by = current_user.username
    db.commit()
    db.refresh(mi)
    
    return {
        "message": "MI已提交审核",
        "status": mi.status
    }


@router.post("/mis/{mi_number}/approve")
async def approve_mi(
    mi_number: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """审核通过MI"""
    mi = db.query(MI).filter(MI.mi_number == mi_number).first()
    if not mi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MI不存在: {mi_number}"
        )
    
    if mi.status != MIStatus.REVIEWING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有待审核状态的MI可以审核，当前状态: {mi.status}"
        )

    # 规则：不能自己审核自己（创建人不能审核自己创建的MI）
    if mi.created_by and mi.created_by == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能自己审核自己，请由其他人员审核"
        )
    
    mi.status = MIStatus.APPROVED
    mi.updated_by = current_user.username
    db.commit()
    db.refresh(mi)
    
    return {
        "message": "MI审核通过",
        "status": mi.status
    }


@router.post("/mis/{mi_number}/reject")
async def reject_mi(
    mi_number: str,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """驳回MI"""
    mi = db.query(MI).filter(MI.mi_number == mi_number).first()
    if not mi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MI不存在: {mi_number}"
        )
    
    if mi.status != MIStatus.REVIEWING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有待审核状态的MI可以驳回，当前状态: {mi.status}"
        )

    # 规则：不能自己审核自己（创建人不能驳回自己创建的MI）
    if mi.created_by and mi.created_by == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能自己审核自己，请由其他人员审核"
        )
    
    mi.status = MIStatus.DRAFT  # 驳回后回到草稿状态
    mi.updated_by = current_user.username
    db.commit()
    db.refresh(mi)
    
    return {
        "message": "MI已驳回",
        "status": mi.status
    }


# 生产版本管理
@router.post("/production-versions", status_code=status.HTTP_201_CREATED)
async def create_production_version(
    pv: ProductionVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建生产版本（BOM+工艺路线+MI组合）"""
    # 检查BOM、工艺路线、MI是否存在
    bom = db.query(BOM).filter(BOM.bom_number == pv.bom_number).first()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOM不存在: {pv.bom_number}"
        )
    
    routing = db.query(Routing).filter(Routing.routing_id == pv.routing_id).first()
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工艺路线不存在: {pv.routing_id}"
        )
    
    # MI可选，但如果提供了则验证存在
    if pv.mi_number:
        mi = db.query(MI).filter(MI.mi_number == pv.mi_number).first()
        if not mi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MI不存在: {pv.mi_number}"
            )
    
    # 生成生产版本ID
    production_version_id = f"PV-{pv.material_code}-{pv.version}"
    
    # 检查生产版本ID是否已存在
    existing = db.query(ProductionVersion).filter(
        ProductionVersion.production_version_id == production_version_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"生产版本ID已存在: {production_version_id}"
        )
    
    db_pv = ProductionVersion(
        production_version_id=production_version_id,
        material_code=pv.material_code,
        bom_number=pv.bom_number,
        routing_id=pv.routing_id,
        mi_number=pv.mi_number,  # 可以为None
        version=pv.version,
        effective_date=pv.effective_date,
        expiry_date=pv.expiry_date,
        description=pv.description,
        status="DRAFT",  # 初始状态为草稿
        created_by=current_user.username
    )
    db.add(db_pv)
    db.commit()
    db.refresh(db_pv)
    return db_pv


@router.post("/production-versions/{production_version_id}/release")
async def release_production_version(
    production_version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发布生产版本（发布时MI必选）"""
    db_pv = db.query(ProductionVersion).filter(
        ProductionVersion.production_version_id == production_version_id
    ).first()
    if not db_pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产版本不存在: {production_version_id}"
        )
    
    # 发布时MI必选
    if not db_pv.mi_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="发布生产版本时MI必选，请先关联MI"
        )
    
    # 检查MI是否存在且已批准
    mi = db.query(MI).filter(MI.mi_number == db_pv.mi_number).first()
    if not mi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MI不存在: {db_pv.mi_number}"
        )
    
    if mi.status != MIStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MI必须已批准才能发布，当前MI状态: {mi.status}"
        )
    
    # 更新状态为已发布
    db_pv.status = "RELEASED"
    db_pv.updated_by = current_user.username
    db.commit()
    db.refresh(db_pv)
    
    return {
        "message": "生产版本发布成功",
        "production_version_id": db_pv.production_version_id,
        "status": db_pv.status
    }


@router.get("/production-versions")
async def list_production_versions(
    skip: int = 0,
    limit: int = 100,
    material_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取生产版本列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(ProductionVersion)
    if material_code:
        query = query.filter(ProductionVersion.material_code == material_code)
    if status:
        query = query.filter(ProductionVersion.status == status)
    
    # 预加载关联数据，避免N+1查询
    query = query.options(
        joinedload(ProductionVersion.material),
        joinedload(ProductionVersion.bom),
        joinedload(ProductionVersion.routing),
        joinedload(ProductionVersion.mi)
    )
    
    pvs = query.order_by(ProductionVersion.created_at.desc()).offset(skip).limit(limit).all()
    return pvs


@router.get("/production-versions/{production_version_id}")
async def get_production_version(
    production_version_id: str,
    db: Session = Depends(get_db)
):
    """获取生产版本详情（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    pv = db.query(ProductionVersion).filter(
        ProductionVersion.production_version_id == production_version_id
    ).options(
        joinedload(ProductionVersion.material),
        joinedload(ProductionVersion.bom),
        joinedload(ProductionVersion.routing),
        joinedload(ProductionVersion.mi)
    ).first()
    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产版本不存在: {production_version_id}"
        )
    return pv


class ProductionVersionUpdate(BaseModel):
    material_code: str
    bom_number: str
    routing_id: str
    mi_number: Optional[str] = None  # MI可选
    version: str
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    description: Optional[str] = None


@router.put("/production-versions/{production_version_id}")
async def update_production_version(
    production_version_id: str,
    pv: ProductionVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新生产版本"""
    db_pv = db.query(ProductionVersion).filter(
        ProductionVersion.production_version_id == production_version_id
    ).first()
    if not db_pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生产版本不存在: {production_version_id}"
        )
    
    # 检查BOM、工艺路线、MI是否存在
    bom = db.query(BOM).filter(BOM.bom_number == pv.bom_number).first()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOM不存在: {pv.bom_number}"
        )
    
    routing = db.query(Routing).filter(Routing.routing_id == pv.routing_id).first()
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工艺路线不存在: {pv.routing_id}"
        )
    
    # MI可选，但如果提供了则验证存在
    if pv.mi_number:
        mi = db.query(MI).filter(MI.mi_number == pv.mi_number).first()
        if not mi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MI不存在: {pv.mi_number}"
            )
    
    db_pv.material_code = pv.material_code
    db_pv.bom_number = pv.bom_number
    db_pv.routing_id = pv.routing_id
    db_pv.mi_number = pv.mi_number
    db_pv.version = pv.version
    db_pv.effective_date = pv.effective_date
    db_pv.expiry_date = pv.expiry_date
    db_pv.description = pv.description
    db_pv.updated_by = current_user.username
    
    db.commit()
    db.refresh(db_pv)
    return db_pv

