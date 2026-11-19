"""
MM模块路由 - 物料管理
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from backend.common.database.base import get_db
from backend.common.models.user import User
from backend.api.routers.auth import get_current_user
from backend.common.models.mm import Material, MaterialIssue, MaterialTransaction
from backend.common.models.planning import (
    Stocktake,
    StocktakeStatus,
    StockTransfer,
    StockTransferStatus,
    Warehouse,
)
from backend.common.utils.number_generator import NumberGenerator

router = APIRouter()


# Pydantic模型
class MaterialCreate(BaseModel):
    material_code: str
    material_name: str
    category: str
    specification: Optional[str] = None
    unit: str
    brand: Optional[str] = None
    min_package: Optional[str] = None
    current_stock: float = 0
    safety_stock: float = 0
    description: Optional[str] = None
    material_type: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None
    base_unit: Optional[str] = None
    production_unit: Optional[str] = None
    conversion_factor: Optional[float] = None
    layer_count: Optional[int] = None
    board_thickness: Optional[float] = None
    thickness_tolerance: Optional[str] = None
    copper_weight: Optional[str] = None
    material_grade: Optional[str] = None
    surface_finish: Optional[str] = None
    solder_mask_color: Optional[str] = None
    silkscreen_color: Optional[str] = None
    impedance_control: Optional[bool] = None
    min_line_space: Optional[float] = None
    min_hole_size: Optional[float] = None
    unit_length: Optional[float] = None
    unit_width: Optional[float] = None
    panel_length: Optional[float] = None
    panel_width: Optional[float] = None
    units_per_panel: Optional[int] = None
    procurement_type: Optional[str] = None
    mrp_controller: Optional[str] = None
    lead_time_days: Optional[int] = None
    max_lot_size: Optional[int] = None
    min_order_quantity: Optional[int] = None
    order_multiple: Optional[int] = None
    abc_class: Optional[str] = None
    shelf_life_days: Optional[int] = None
    default_location: Optional[str] = None
    storage_condition: Optional[str] = None
    batch_tracking: Optional[bool] = None
    valuation_method: Optional[str] = None
    standard_price: Optional[float] = None
    currency: Optional[str] = None
    last_cost_update: Optional[datetime] = None


class MaterialUpdate(MaterialCreate):
    pass


class MaterialResponse(BaseModel):
    id: int
    material_code: str
    material_name: str
    category: str
    specification: Optional[str] = None
    unit: str
    brand: Optional[str] = None
    min_package: Optional[str] = None
    current_stock: float
    safety_stock: float
    description: Optional[str] = None
    material_type: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None
    base_unit: Optional[str] = None
    production_unit: Optional[str] = None
    conversion_factor: Optional[float] = None
    layer_count: Optional[int] = None
    board_thickness: Optional[float] = None
    thickness_tolerance: Optional[str] = None
    copper_weight: Optional[str] = None
    material_grade: Optional[str] = None
    surface_finish: Optional[str] = None
    solder_mask_color: Optional[str] = None
    silkscreen_color: Optional[str] = None
    impedance_control: Optional[bool] = None
    min_line_space: Optional[float] = None
    min_hole_size: Optional[float] = None
    unit_length: Optional[float] = None
    unit_width: Optional[float] = None
    panel_length: Optional[float] = None
    panel_width: Optional[float] = None
    units_per_panel: Optional[int] = None
    procurement_type: Optional[str] = None
    mrp_controller: Optional[str] = None
    lead_time_days: Optional[int] = None
    max_lot_size: Optional[int] = None
    min_order_quantity: Optional[int] = None
    order_multiple: Optional[int] = None
    abc_class: Optional[str] = None
    shelf_life_days: Optional[int] = None
    default_location: Optional[str] = None
    storage_condition: Optional[str] = None
    batch_tracking: Optional[bool] = None
    valuation_method: Optional[str] = None
    standard_price: Optional[float] = None
    currency: Optional[str] = None
    last_cost_update: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MaterialIssueCreate(BaseModel):
    production_order_number: str
    material_code: str
    quantity: float
    unit: str
    warehouse: Optional[str] = None
    remarks: Optional[str] = None


class MaterialIssueResponse(BaseModel):
    id: int
    issue_number: str
    production_order_number: str
    material_code: str
    quantity: float
    issued_by: str
    
    class Config:
        from_attributes = True


# 物料主数据管理
@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    material: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建物料"""
    # 检查物料编码是否已存在
    existing = db.query(Material).filter(Material.material_code == material.material_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"物料编码已存在: {material.material_code}"
        )
    
    db_material = Material(
        material_code=material.material_code,
        material_name=material.material_name,
        category=material.category,
        specification=material.specification,
        unit=material.unit,
        brand=material.brand,
        min_package=material.min_package,
        current_stock=material.current_stock,
        safety_stock=material.safety_stock,
        description=material.description,
        material_type=material.material_type,
        status=material.status,
        version=material.version,
        base_unit=material.base_unit,
        production_unit=material.production_unit,
        conversion_factor=material.conversion_factor,
        layer_count=material.layer_count,
        board_thickness=material.board_thickness,
        thickness_tolerance=material.thickness_tolerance,
        copper_weight=material.copper_weight,
        material_grade=material.material_grade,
        surface_finish=material.surface_finish,
        solder_mask_color=material.solder_mask_color,
        silkscreen_color=material.silkscreen_color,
        impedance_control=material.impedance_control,
        min_line_space=material.min_line_space,
        min_hole_size=material.min_hole_size,
        unit_length=material.unit_length,
        unit_width=material.unit_width,
        panel_length=material.panel_length,
        panel_width=material.panel_width,
        units_per_panel=material.units_per_panel,
        procurement_type=material.procurement_type,
        mrp_controller=material.mrp_controller,
        lead_time_days=material.lead_time_days,
        max_lot_size=material.max_lot_size,
        min_order_quantity=material.min_order_quantity,
        order_multiple=material.order_multiple,
        abc_class=material.abc_class,
        shelf_life_days=material.shelf_life_days,
        default_location=material.default_location,
        storage_condition=material.storage_condition,
        batch_tracking=material.batch_tracking,
        valuation_method=material.valuation_method,
        standard_price=material.standard_price,
        currency=material.currency,
        last_cost_update=material.last_cost_update,
        created_by=current_user.username
    )
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material


@router.get("/materials", response_model=List[MaterialResponse])
async def list_materials(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    material_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取物料列表（优化：只加载必要字段，不加载关联数据）"""
    
    query = db.query(Material).filter(Material.is_deleted == False)
    if category:
        query = query.filter(Material.category == category)
    if material_code:
        query = query.filter(Material.material_code.like(f"%{material_code}%"))
    if status:
        query = query.filter(Material.status == status)
    
    # 列表查询不需要加载关联数据，手动构建响应避免Pydantic序列化时触发延迟加载
    # Material模型没有定义关系，但为了安全起见，我们手动构建响应
    materials = query.order_by(Material.material_code).offset(skip).limit(limit).all()
    
    # 手动构建响应，确保字段正确序列化
    result = []
    for material in materials:
        material_dict = {
            "id": material.id,
            "material_code": material.material_code,
            "material_name": material.material_name,
            "category": material.category,
            "specification": material.specification,
            "unit": material.unit,
            "brand": material.brand,
            "min_package": material.min_package,
            "current_stock": float(material.current_stock) if material.current_stock else 0.0,
            "safety_stock": float(material.safety_stock) if material.safety_stock else 0.0,
            "description": material.description,
            "material_type": material.material_type,
            "status": material.status if material.status else "ACTIVE",
            "version": material.version,
            "base_unit": material.base_unit,
            "production_unit": material.production_unit,
            "created_at": material.created_at,
            "updated_at": material.updated_at,
            "created_by": material.created_by,
            "updated_by": material.updated_by
        }
        result.append(material_dict)
    
    return result


@router.get("/materials/{material_code}", response_model=MaterialResponse)
async def get_material(
    material_code: str,
    db: Session = Depends(get_db)
):
    """获取物料详情"""
    material = db.query(Material).filter(
        Material.material_code == material_code,
        Material.is_deleted == False
    ).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"物料不存在: {material_code}"
        )
    return material


@router.put("/materials/{material_code}", response_model=MaterialResponse)
async def update_material(
    material_code: str,
    material: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新物料"""
    db_material = db.query(Material).filter(
        Material.material_code == material_code,
        Material.is_deleted == False
    ).first()
    if not db_material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"物料不存在: {material_code}"
        )
    # 更新字段
    for field in material.dict(exclude_unset=True):
        setattr(db_material, field, material.dict()[field])
    db_material.updated_by = current_user.username
    db.commit()
    db.refresh(db_material)
    return db_material


# 生产领料
@router.post("/material-issues", response_model=MaterialIssueResponse, status_code=status.HTTP_201_CREATED)
async def create_material_issue(
    issue: MaterialIssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建生产领料单"""
    try:
        # 检查物料是否存在
        material = db.query(Material).filter(Material.material_code == issue.material_code).first()
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"物料不存在: {issue.material_code}"
            )
        
        # 验证单位是否与物料单位一致
        if issue.unit != material.unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"单位不匹配: 物料的单位为 {material.unit}，但领料单的单位为 {issue.unit}。领料单应使用物料的单位。"
            )
        
        # 检查库存是否充足（确保类型一致）
        issue_quantity_decimal = Decimal(str(issue.quantity))
        if material.current_stock < issue_quantity_decimal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"库存不足: 当前库存 {material.current_stock} {material.unit}, 需要 {issue.quantity} {material.unit}"
            )
        
        # 检查生产订单是否存在
        from backend.common.models.pp import ProductionOrder, ProductionOrderStatus
        production_order = db.query(ProductionOrder).filter(
            ProductionOrder.order_number == issue.production_order_number
        ).first()
        if not production_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"生产订单不存在: {issue.production_order_number}"
            )
        
        # 验证生产订单状态：不能是已完成或已关闭状态
        if production_order.status in [ProductionOrderStatus.COMPLETED, ProductionOrderStatus.CLOSED]:
            from backend.common.exceptions import ValidationException, ErrorCodes
            raise ValidationException(
                error_code=ErrorCodes.PRODUCTION_ORDER_STATUS_INVALID,
                detail=f"生产订单状态不允许领料: 当前状态为 {production_order.status}，已完成或已关闭的订单不能创建领料单",
                field="production_order_status",
                value=production_order.status
            )
        
        # 验证物料编码是否与生产订单匹配（可选，但建议验证）
        if production_order.material_code != issue.material_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"物料编码不匹配: 生产订单的物料编码为 {production_order.material_code}，但领料单的物料编码为 {issue.material_code}"
            )
        
        # 生成领料单号（确保唯一性）
        order_suffix = issue.production_order_number[-4:] if len(issue.production_order_number) >= 4 else issue.production_order_number
        issue_number_base = f"MI-{datetime.now().strftime('%Y%m%d')}-{order_suffix}"
        issue_number = issue_number_base
        
        # 检查领料单号是否已存在，如果存在则添加序号
        counter = 0
        while db.query(MaterialIssue).filter(MaterialIssue.issue_number == issue_number).first():
            counter += 1
            issue_number = f"{issue_number_base}-{counter}"
            if counter > 100:  # 防止无限循环
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="无法生成唯一的领料单号"
                )
        
        db_issue = MaterialIssue(
            issue_number=issue_number,
            production_order_number=issue.production_order_number,
            material_code=issue.material_code,
            quantity=issue.quantity,
            unit=issue.unit,
            issued_by=current_user.username,
            issued_at=datetime.utcnow(),
            warehouse=issue.warehouse,
            remarks=issue.remarks,
            created_by=current_user.username
        )
        db.add(db_issue)
        
        # 扣减库存（确保类型一致，使用 Decimal）
        material.current_stock -= issue_quantity_decimal
        material.updated_by = current_user.username
        
        # 记录库存事务
        transaction_number_base = f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        transaction_number = transaction_number_base
        counter = 0
        while db.query(MaterialTransaction).filter(MaterialTransaction.transaction_number == transaction_number).first():
            counter += 1
            transaction_number = f"{transaction_number_base}-{counter}"
            if counter > 100:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="无法生成唯一的事务编号"
                )
        
        # 记录库存事务
        try:
            transaction = MaterialTransaction(
                transaction_number=transaction_number,
                material_code=issue.material_code,
                transaction_type="ISSUE",
                quantity=-issue_quantity_decimal,  # 使用 Decimal 类型，负数表示出库
                unit=issue.unit,
                reference_number=issue_number,
                reference_type="MATERIAL_ISSUE",
                warehouse=issue.warehouse if issue.warehouse else None,  # 确保 None 而不是空字符串
                transaction_date=datetime.utcnow(),
                operator=current_user.username,
                remarks=f"生产领料: {issue.production_order_number}" if issue.production_order_number else None,
                created_by=current_user.username  # 添加创建人
            )
            db.add(transaction)
            db.flush()  # 先 flush 以检查是否有错误
        except Exception as trans_e:
            print(f"创建库存事务记录错误: {type(trans_e).__name__}: {trans_e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建库存事务记录失败: {str(trans_e)}。请检查后端控制台日志获取详细信息。"
            )
        
        try:
            db.commit()
            db.refresh(db_issue)
            return db_issue
        except Exception as commit_e:
            print(f"提交事务错误: {type(commit_e).__name__}: {commit_e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"提交事务失败: {str(commit_e)}"
            )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"创建生产领料单错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建生产领料单失败: {str(e)}"
        )


@router.get("/material-issues", response_model=List[MaterialIssueResponse])
async def list_material_issues(
    skip: int = 0,
    limit: int = 100,
    production_order_number: Optional[str] = None,
    material_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取生产领料列表（已优化：预加载关联数据）"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(MaterialIssue)
    if production_order_number:
        query = query.filter(MaterialIssue.production_order_number == production_order_number)
    if material_code:
        query = query.filter(MaterialIssue.material_code == material_code)
    
    # 预加载关联数据，避免N+1查询
    # 注意：MaterialIssue.production_order 关系被注释掉了，所以只加载 material
    query = query.options(
        joinedload(MaterialIssue.material)
    )
    
    issues = query.offset(skip).limit(limit).all()
    return issues


# 库存查询
@router.get("/inventory")
async def get_inventory(
    material_code: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取库存信息（含可用量口径）。

    - 在途量 on_order_qty：RELEASED / PARTIALLY_RECEIVED 采购单的未收余量（按物料汇总）；
    - 已分配量 allocated_qty：开放工单（RELEASED / IN_PRODUCTION）按 BOM 展开的组件需求
      减去该工单已领料量（复用齐套引擎 KittingService 的展开口径）；
    - 可用量 available_qty = 当前库存 + 在途量 - 已分配量（负数即缺口）。
    """
    from sqlalchemy import func
    from datetime import datetime as _datetime

    from backend.common.models.pp import ProductionOrder, ProductionOrderStatus
    from backend.common.models.planning import (
        PurchaseOrder,
        PurchaseOrderLine,
        PurchaseOrderStatus,
    )
    from backend.services.planning.kitting_service import KittingService

    query = db.query(Material).filter(Material.is_deleted == False)
    if material_code:
        query = query.filter(Material.material_code.like(f"%{material_code}%"))
    if category:
        query = query.filter(Material.category == category)

    materials = query.all()

    # ── 在途：开放采购单行余量按物料汇总（单次聚合） ──
    on_order_rows = (
        db.query(
            PurchaseOrderLine.material_code,
            func.coalesce(
                func.sum(PurchaseOrderLine.quantity - PurchaseOrderLine.received_quantity), 0
            ),
        )
        .join(
            PurchaseOrder,
            PurchaseOrder.purchase_order_number == PurchaseOrderLine.purchase_order_number,
        )
        .filter(
            PurchaseOrderLine.is_deleted == False,  # noqa: E712
            PurchaseOrder.is_deleted == False,  # noqa: E712
            PurchaseOrder.status.in_(
                [PurchaseOrderStatus.RELEASED, PurchaseOrderStatus.PARTIALLY_RECEIVED]
            ),
        )
        .group_by(PurchaseOrderLine.material_code)
        .all()
    )
    on_order_map = {code: float(total or 0) for code, total in on_order_rows}

    # ── 已分配：开放工单 BOM 组件需求 − 该工单已领料（按工单+物料） ──
    issued_rows = (
        db.query(
            MaterialIssue.production_order_number,
            MaterialIssue.material_code,
            func.coalesce(func.sum(MaterialIssue.quantity), 0),
        )
        .group_by(MaterialIssue.production_order_number, MaterialIssue.material_code)
        .all()
    )
    issued_map = {
        (order_number, code): float(total or 0)
        for order_number, code, total in issued_rows
    }

    open_orders = (
        db.query(ProductionOrder)
        .filter(
            ProductionOrder.is_deleted == False,  # noqa: E712
            ProductionOrder.status.in_(
                [ProductionOrderStatus.RELEASED, ProductionOrderStatus.IN_PRODUCTION]
            ),
        )
        .all()
    )
    allocated_map: dict[str, float] = {}
    for order in open_orders:
        due = order.planned_start_date or order.created_at or _datetime.now()
        try:
            components = KittingService._component_requirements(
                db, order.material_code, order.quantity or 0, due
            )
        except Exception:
            components = []
        for row in components:
            code = row["material_code"]
            required = float(row.get("required_qty") or 0)
            already_issued = issued_map.get((order.order_number, code), 0.0)
            net = max(required - already_issued, 0.0)
            allocated_map[code] = allocated_map.get(code, 0.0) + net

    return [
        {
            "material_code": m.material_code,
            "material_name": m.material_name,
            "category": m.category,
            "unit": m.unit,
            "current_stock": float(m.current_stock),
            "safety_stock": float(m.safety_stock),
            "on_order_qty": round(on_order_map.get(m.material_code, 0.0), 2),
            "allocated_qty": round(allocated_map.get(m.material_code, 0.0), 2),
            "available_qty": round(
                float(m.current_stock) + on_order_map.get(m.material_code, 0.0)
                - allocated_map.get(m.material_code, 0.0),
                2,
            ),
            "stock_status": "充足" if m.current_stock >= m.safety_stock else "不足"
        }
        for m in materials
    ]


# 库存事务流水
@router.get("/transactions")
async def list_material_transactions(
    skip: int = 0,
    limit: int = 100,
    material_code: Optional[str] = None,
    transaction_type: Optional[str] = None,
    reference_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """库存事务流水（账本）：领料/到货/退货/调整的每笔库存变动。

    - quantity 正数入库、负数出库；
    - reference_number/reference_type 指向来源单据（领料单/采购单/退货单）。
    """
    from sqlalchemy.orm import joinedload

    query = db.query(MaterialTransaction).options(joinedload(MaterialTransaction.material))
    if material_code:
        query = query.filter(MaterialTransaction.material_code.like(f"%{material_code}%"))
    if transaction_type:
        query = query.filter(MaterialTransaction.transaction_type == transaction_type)
    if reference_type:
        query = query.filter(MaterialTransaction.reference_type == reference_type)
    if start_date:
        query = query.filter(MaterialTransaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(MaterialTransaction.transaction_date <= end_date)

    total = query.count()
    rows = (
        query.order_by(MaterialTransaction.transaction_date.desc(), MaterialTransaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "transaction_number": t.transaction_number,
                "material_code": t.material_code,
                "material_name": t.material.material_name if t.material else None,
                "transaction_type": t.transaction_type,
                "quantity": float(t.quantity),
                "unit": t.unit,
                "reference_number": t.reference_number,
                "reference_type": t.reference_type,
                "warehouse": t.warehouse,
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                "operator": t.operator,
                "remarks": t.remarks,
            }
            for t in rows
        ],
    }


# ── 库存补强（P3）：仓库主数据 / 盘点 / 调拨 ──────────────────────────
class WarehouseCreate(BaseModel):
    warehouse_code: str
    warehouse_name: str
    location: Optional[str] = None
    remarks: Optional[str] = None


class StocktakeCreate(BaseModel):
    material_code: str
    counted_qty: float = Field(..., ge=0)
    warehouse: Optional[str] = None
    remarks: Optional[str] = None


class StockTransferCreate(BaseModel):
    from_warehouse_code: str
    to_warehouse_code: str
    material_code: str
    quantity: float = Field(..., gt=0)
    remarks: Optional[str] = None


def _warehouse_dict(w: Warehouse) -> dict:
    return {
        "warehouse_code": w.warehouse_code,
        "warehouse_name": w.warehouse_name,
        "location": w.location,
        "is_active": bool(w.is_active),
        "remarks": w.remarks,
    }


def _stocktake_dict(s: Stocktake) -> dict:
    return {
        "stocktake_number": s.stocktake_number,
        "material_code": s.material_code,
        "warehouse": s.warehouse,
        "book_qty": float(s.book_qty or 0),
        "counted_qty": float(s.counted_qty or 0),
        "diff": float(s.diff or 0),
        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
        "stocktake_date": s.stocktake_date.isoformat() if s.stocktake_date else None,
        "remarks": s.remarks,
    }


def _transfer_dict(t: StockTransfer) -> dict:
    return {
        "transfer_number": t.transfer_number,
        "from_warehouse_code": t.from_warehouse_code,
        "to_warehouse_code": t.to_warehouse_code,
        "material_code": t.material_code,
        "quantity": float(t.quantity or 0),
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "transfer_date": t.transfer_date.isoformat() if t.transfer_date else None,
        "remarks": t.remarks,
    }


@router.get("/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    rows = db.query(Warehouse).filter(Warehouse.is_deleted.is_(False)).all()
    return {"total": len(rows), "items": [_warehouse_dict(w) for w in rows]}


@router.post("/warehouses", status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Warehouse).filter(Warehouse.warehouse_code == payload.warehouse_code).first():
        raise HTTPException(status_code=400, detail=f"仓库编码已存在: {payload.warehouse_code}")
    w = Warehouse(
        warehouse_code=payload.warehouse_code,
        warehouse_name=payload.warehouse_name,
        location=payload.location,
        is_active=True,
        remarks=payload.remarks,
        created_by=current_user.username,
    )
    db.add(w)
    db.commit()
    return _warehouse_dict(w)


@router.get("/stocktakes")
def list_stocktakes(
    stocktake_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Stocktake).filter(Stocktake.is_deleted.is_(False))
    if stocktake_status:
        query = query.filter(Stocktake.status == StocktakeStatus(stocktake_status))
    total = query.count()
    rows = query.order_by(Stocktake.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_stocktake_dict(s) for s in rows]}


@router.get("/stocktakes/{stocktake_number}")
def get_stocktake(stocktake_number: str, db: Session = Depends(get_db)):
    s = (
        db.query(Stocktake)
        .filter(Stocktake.stocktake_number == stocktake_number, Stocktake.is_deleted.is_(False))
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail=f"盘点单不存在: {stocktake_number}")
    return _stocktake_dict(s)


@router.post("/stocktakes", status_code=status.HTTP_201_CREATED)
def create_stocktake(
    payload: StocktakeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建盘点单（DRAFT）：book_qty 取创建时现存量快照，diff = 实盘 − 账面。"""
    material = db.query(Material).filter(Material.material_code == payload.material_code).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"物料不存在: {payload.material_code}")
    book_qty = float(material.current_stock or 0)
    diff = round(payload.counted_qty - book_qty, 2)
    number = NumberGenerator.generate_document_number(db, Stocktake, "stocktake_number", "STK", 4)
    s = Stocktake(
        stocktake_number=number,
        material_code=material.material_code,
        warehouse=payload.warehouse,
        book_qty=book_qty,
        counted_qty=payload.counted_qty,
        diff=diff,
        status=StocktakeStatus.DRAFT,
        stocktake_date=datetime.now(),
        remarks=payload.remarks,
        created_by=current_user.username,
    )
    db.add(s)
    db.flush()  # 坑2
    db.commit()
    return _stocktake_dict(s)


@router.post("/stocktakes/{stocktake_number}/approve")
def approve_stocktake(
    stocktake_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批盘点：写 ADJUSTMENT 流水并校正现存量；调整后库存 ≥0。"""
    s = (
        db.query(Stocktake)
        .filter(Stocktake.stocktake_number == stocktake_number, Stocktake.is_deleted.is_(False))
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail=f"盘点单不存在: {stocktake_number}")
    if s.status != StocktakeStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"盘点单状态为 {s.status.value}，不允许审批")
    material = db.query(Material).filter(Material.material_code == s.material_code).first()
    if not material:
        raise HTTPException(status_code=400, detail=f"物料不存在: {s.material_code}")
    diff = float(s.diff or 0)
    if float(material.current_stock or 0) + diff < 0:
        raise HTTPException(
            status_code=400,
            detail=f"调整后库存为负：当前 {float(material.current_stock or 0)}，差异 {diff}",
        )
    if abs(diff) > 1e-9:
        material.current_stock = float(material.current_stock or 0) + diff
        db.add(MaterialTransaction(
            transaction_number=NumberGenerator.generate_document_number(
                db, MaterialTransaction, "transaction_number", "TXN", 6),
            material_code=s.material_code,
            transaction_type="ADJUSTMENT",
            quantity=diff,
            unit=material.unit or "PCS",
            reference_number=s.stocktake_number,
            reference_type="STOCKTAKE",
            warehouse=s.warehouse,
            transaction_date=datetime.now(),
            operator=current_user.username,
            remarks=f"盘点调整 {s.stocktake_number}",
            created_by=current_user.username,
        ))
    s.status = StocktakeStatus.APPROVED
    s.updated_by = current_user.username
    s.updated_at = datetime.now()
    db.commit()
    return _stocktake_dict(s)


@router.post("/stocktakes/{stocktake_number}/cancel")
def cancel_stocktake(
    stocktake_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = (
        db.query(Stocktake)
        .filter(Stocktake.stocktake_number == stocktake_number, Stocktake.is_deleted.is_(False))
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail=f"盘点单不存在: {stocktake_number}")
    if s.status != StocktakeStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"盘点单状态为 {s.status.value}，不允许作废")
    s.status = StocktakeStatus.CANCELLED
    s.updated_by = current_user.username
    s.updated_at = datetime.now()
    db.commit()
    return _stocktake_dict(s)


@router.get("/stock-transfers")
def list_stock_transfers(
    transfer_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(StockTransfer).filter(StockTransfer.is_deleted.is_(False))
    if transfer_status:
        query = query.filter(StockTransfer.status == StockTransferStatus(transfer_status))
    total = query.count()
    rows = query.order_by(StockTransfer.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_transfer_dict(t) for t in rows]}


@router.get("/stock-transfers/{transfer_number}")
def get_stock_transfer(transfer_number: str, db: Session = Depends(get_db)):
    t = (
        db.query(StockTransfer)
        .filter(StockTransfer.transfer_number == transfer_number, StockTransfer.is_deleted.is_(False))
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail=f"调拨单不存在: {transfer_number}")
    return _transfer_dict(t)


@router.post("/stock-transfers", status_code=status.HTTP_201_CREATED)
def create_stock_transfer(
    payload: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建调拨单（DRAFT）：from≠to、仓库须存在、数量>0。"""
    if payload.from_warehouse_code == payload.to_warehouse_code:
        raise HTTPException(status_code=400, detail="调出与调入仓库不能相同")
    material = db.query(Material).filter(Material.material_code == payload.material_code).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"物料不存在: {payload.material_code}")
    for code in (payload.from_warehouse_code, payload.to_warehouse_code):
        if not db.query(Warehouse).filter(Warehouse.warehouse_code == code).first():
            raise HTTPException(status_code=404, detail=f"仓库不存在: {code}")
    number = NumberGenerator.generate_document_number(db, StockTransfer, "transfer_number", "TRF", 4)
    t = StockTransfer(
        transfer_number=number,
        from_warehouse_code=payload.from_warehouse_code,
        to_warehouse_code=payload.to_warehouse_code,
        material_code=material.material_code,
        quantity=payload.quantity,
        status=StockTransferStatus.DRAFT,
        transfer_date=datetime.now(),
        remarks=payload.remarks,
        created_by=current_user.username,
    )
    db.add(t)
    db.flush()
    db.commit()
    return _transfer_dict(t)


@router.post("/stock-transfers/{transfer_number}/confirm")
def confirm_stock_transfer(
    transfer_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认调拨：记调出/调入两笔流水（总量不变，不动 current_stock）。"""
    t = (
        db.query(StockTransfer)
        .filter(StockTransfer.transfer_number == transfer_number, StockTransfer.is_deleted.is_(False))
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail=f"调拨单不存在: {transfer_number}")
    if t.status != StockTransferStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"调拨单状态为 {t.status.value}，不允许确认")
    for warehouse_code, qty, txn_type, ref_type in (
        (t.from_warehouse_code, -float(t.quantity or 0), "TRANSFER_OUT", "STOCK_TRANSFER_OUT"),
        (t.to_warehouse_code, float(t.quantity or 0), "TRANSFER_IN", "STOCK_TRANSFER_IN"),
    ):
        db.add(MaterialTransaction(
            transaction_number=NumberGenerator.generate_document_number(
                db, MaterialTransaction, "transaction_number", "TXN", 6),
            material_code=t.material_code,
            transaction_type=txn_type,
            quantity=qty,
            unit="PCS",
            reference_number=t.transfer_number,
            reference_type=ref_type,
            warehouse=warehouse_code,
            transaction_date=datetime.now(),
            operator=current_user.username,
            remarks=f"调拨 {t.transfer_number} {'调出' if qty < 0 else '调入'} {warehouse_code}",
            created_by=current_user.username,
        ))
        db.flush()  # 坑2：同事务连续生成单号
    t.status = StockTransferStatus.CONFIRMED
    t.updated_by = current_user.username
    t.updated_at = datetime.now()
    db.commit()
    return _transfer_dict(t)


@router.post("/stock-transfers/{transfer_number}/cancel")
def cancel_stock_transfer(
    transfer_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = (
        db.query(StockTransfer)
        .filter(StockTransfer.transfer_number == transfer_number, StockTransfer.is_deleted.is_(False))
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail=f"调拨单不存在: {transfer_number}")
    if t.status != StockTransferStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"调拨单状态为 {t.status.value}，不允许作废")
    t.status = StockTransferStatus.CANCELLED
    t.updated_by = current_user.username
    t.updated_at = datetime.now()
    db.commit()
    return _transfer_dict(t)





@router.get("/batch-tracking")
def batch_tracking(db: Session = Depends(get_db)):
    """批次/效期纯读视图（P3）：按物料聚合 ACTIVE LOT 卡 + shelf_life_days 临期预警。

    口径：LotCard 无效期字段（纯读不加表），到期日=最近完成时间 + 物料 shelf_life_days（估算）；
    days_to_expiry ≤ 30 或已过期 → warning。
    """
    from backend.common.models.pp import LotCard

    now = datetime.now()
    lots = db.query(LotCard).filter(LotCard.is_deleted.is_(False), LotCard.status == "ACTIVE").all()
    materials = {
        m.material_code: m
        for m in db.query(Material).filter(Material.is_deleted.is_(False)).all()
    }
    by_material: dict[str, dict] = {}
    for lot in lots:
        material = materials.get(lot.material_code)
        if material is None:
            continue
        row = by_material.setdefault(
            lot.material_code,
            {
                "material_code": lot.material_code,
                "material_name": material.material_name,
                "shelf_life_days": material.shelf_life_days,
                "lot_count": 0,
                "lot_qty": 0.0,
                "last_completed_at": None,
                "estimated_expiry": None,
                "days_to_expiry": None,
                "warning": False,
            },
        )
        row["lot_count"] += 1
        row["lot_qty"] += float(lot.quantity or 0)
        completed = lot.completed_at
        if completed is not None:
            if row["last_completed_at"] is None or completed > row["last_completed_at"]:
                row["last_completed_at"] = completed
    items = []
    for row in by_material.values():
        row["lot_qty"] = round(row["lot_qty"], 2)
        row["last_completed_at"] = (
            row["last_completed_at"].isoformat() if row["last_completed_at"] else None
        )
        shelf = row.get("shelf_life_days")
        if shelf and row["last_completed_at"]:
            base = datetime.fromisoformat(row["last_completed_at"])
            expiry = base + __import__("datetime").timedelta(days=int(shelf))
            days = (expiry - now).days
            row["estimated_expiry"] = expiry.date().isoformat()
            row["days_to_expiry"] = days
            row["warning"] = days <= 30
        row["estimate_pending"] = row["estimated_expiry"] is None  # 在制批无完成时间，无法估算
        items.append(row)
    items.sort(key=lambda x: (
        not x["warning"],
        x["days_to_expiry"] if x["days_to_expiry"] is not None else 9e9,
    ))
    return {"total": len(items), "items": items, "generated_at": now.isoformat()}
