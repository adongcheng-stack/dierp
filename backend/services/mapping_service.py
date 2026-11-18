"""
本厂编号映射服务
"""
from typing import Optional, Tuple, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.common.models.sd import FactoryProductMapping
from backend.common.models.mm import Material
from backend.common.models.eng import ProductionVersion
from backend.common.exceptions import NotFoundException, ValidationException, ConflictException, ErrorCodes
from backend.common.utils.logger import log_info, log_warning
from backend.common.utils.transaction import transactional


class MappingService:
    """本厂编号映射服务"""
    
    @staticmethod
    def find_mapping(
        customer_id: str,
        factory_product_number: str,
        db: Session
    ) -> Optional[FactoryProductMapping]:
        """
        查找本厂编号映射
        
        Args:
            customer_id: 客户ID
            factory_product_number: 本厂编号
            db: 数据库会话
            
        Returns:
            FactoryProductMapping: 映射对象，如果不存在则返回None
        """
        mapping = db.query(FactoryProductMapping).filter(
            FactoryProductMapping.customer_id == customer_id,
            FactoryProductMapping.factory_product_number == factory_product_number,
            FactoryProductMapping.effective_date <= datetime.now(),
            or_(
                FactoryProductMapping.expiry_date.is_(None),
                FactoryProductMapping.expiry_date >= datetime.now()
            ),
            FactoryProductMapping.is_default == True,
            FactoryProductMapping.is_deleted == False
        ).first()
        
        return mapping
    
    @staticmethod
    def resolve_material_code(
        customer_id: str,
        factory_product_number: str,
        db: Session
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        解析本厂编号到物料编码和生产版本
        
        Args:
            customer_id: 客户ID
            factory_product_number: 本厂编号
            db: 数据库会话
            
        Returns:
            tuple: (material_code, production_version_id)
            
        Raises:
            NotFoundException: 映射不存在时抛出
            ValidationException: 物料不存在或状态无效时抛出
        """
        mapping = MappingService.find_mapping(customer_id, factory_product_number, db)
        
        if not mapping:
            raise NotFoundException(
                resource_type="FactoryProductMapping",
                resource_id=f"{customer_id}/{factory_product_number}",
                detail=f"未找到本厂编号映射: {factory_product_number}（客户: {customer_id}）"
            )
        
        material_code = mapping.material_code
        production_version_id = mapping.production_version_id
        
        # 验证物料存在且状态有效
        material = db.query(Material).filter(
            Material.material_code == material_code
        ).first()
        
        if not material:
            raise NotFoundException(
                resource_type="Material",
                resource_id=material_code,
                detail=f"映射的物料不存在: {material_code}"
            )
        
        if material.status != "ACTIVE":
            raise ValidationException(
                error_code=ErrorCodes.MATERIAL_NOT_ACTIVE,
                detail=f"物料状态非激活: {material_code}，当前状态: {material.status}",
                field="material_status",
                value=material.status
            )
        
        # 验证生产版本（如果存在）
        if production_version_id:
            pv = db.query(ProductionVersion).filter(
                ProductionVersion.production_version_id == production_version_id
            ).first()
            
            if not pv:
                raise NotFoundException(
                    resource_type="ProductionVersion",
                    resource_id=production_version_id,
                    detail=f"映射的生产版本不存在: {production_version_id}"
                )
            
            if pv.status not in ["RELEASED", "ACTIVE"]:
                raise ValidationException(
                    error_code=ErrorCodes.PRODUCTION_VERSION_STATUS_INVALID,
                    detail=f"生产版本状态不可用: {production_version_id}，当前状态: {pv.status}",
                    field="production_version_status",
                    value=pv.status
                )
            
            # 验证物料编码一致性
            if pv.material_code != material_code:
                raise ValidationException(
                    error_code=ErrorCodes.MATERIAL_CODE_MISMATCH,
                    detail=f"生产版本的物料编码与映射不一致: 生产版本物料={pv.material_code}，映射物料={material_code}",
                    field="material_code",
                    value=material_code
                )
        
        return material_code, production_version_id
    
    @staticmethod
    def calculate_unit_conversion(
        material_code: str,
        sales_unit: Optional[str],
        production_unit: Optional[str],
        db: Session
    ) -> Tuple[str, str, float]:
        """
        计算单位转换
        
        Args:
            material_code: 物料编码
            sales_unit: 销售单位（可选）
            production_unit: 生产单位（可选）
            db: 数据库会话
            
        Returns:
            tuple: (sales_unit, production_unit, conversion_factor)
        """
        material = db.query(Material).filter(
            Material.material_code == material_code
        ).first()
        
        if not material:
            raise NotFoundException(
                resource_type="Material",
                resource_id=material_code
            )
        
        # 使用物料默认单位
        if not sales_unit:
            sales_unit = material.base_unit or "PCS"
        if not production_unit:
            production_unit = material.production_unit or material.base_unit or "PNL"
        
        # 计算转换系数
        if sales_unit == production_unit:
            conversion_factor = 1.0
        elif material.conversion_factor:
            conversion_factor = float(material.conversion_factor)
        else:
            conversion_factor = 1.0
        
        return sales_unit, production_unit, conversion_factor
    
    @staticmethod
    def calculate_production_quantity(
        sales_quantity: float,
        sales_unit: str,
        production_unit: str,
        conversion_factor: float
    ) -> float:
        """
        计算生产数量
        
        Args:
            sales_quantity: 销售数量
            sales_unit: 销售单位
            production_unit: 生产单位
            conversion_factor: 转换系数
            
        Returns:
            float: 生产数量
        """
        if sales_unit == production_unit:
            return sales_quantity
        else:
            return sales_quantity / conversion_factor
    
    @staticmethod
    def check_mapping_conflicts(
        customer_id: str,
        factory_product_number: str,
        effective_date: datetime,
        expiry_date: Optional[datetime],
        exclude_mapping_id: Optional[int] = None,
        db: Session = None
    ) -> List[FactoryProductMapping]:
        """
        检查同一时间段内的映射冲突
        
        Args:
            customer_id: 客户ID
            factory_product_number: 本厂编号
            effective_date: 生效日期
            expiry_date: 失效日期（可选）
            exclude_mapping_id: 排除的映射ID（用于更新时排除自身）
            db: 数据库会话
            
        Returns:
            List[FactoryProductMapping]: 冲突的映射列表
            
        Raises:
            ConflictException: 如果存在冲突的映射
        """
        if db is None:
            raise ValueError("db参数不能为空")
        
        # 构建查询条件：查找同一客户、同一本厂编号、时间段有重叠的映射
        query = db.query(FactoryProductMapping).filter(
            FactoryProductMapping.customer_id == customer_id,
            FactoryProductMapping.factory_product_number == factory_product_number,
            FactoryProductMapping.is_deleted == False
        )
        
        # 排除自身（用于更新时）
        if exclude_mapping_id:
            query = query.filter(FactoryProductMapping.id != exclude_mapping_id)
        
        # 查找时间段有重叠的映射
        # 时间段重叠的条件：
        # 1. 新映射的生效日期在现有映射的有效期内
        # 2. 新映射的失效日期在现有映射的有效期内
        # 3. 新映射完全包含现有映射
        # 4. 现有映射完全包含新映射
        
        conflicting_mappings = []
        all_mappings = query.all()
        
        for existing_mapping in all_mappings:
            existing_effective = existing_mapping.effective_date
            existing_expiry = existing_mapping.expiry_date
            
            # 检查时间段是否重叠
            # 时间段重叠：新映射的开始时间 <= 现有映射的结束时间 且 新映射的结束时间 >= 现有映射的开始时间
            new_start = effective_date
            new_end = expiry_date if expiry_date else datetime.max
            
            existing_start = existing_effective
            existing_end = existing_expiry if existing_expiry else datetime.max
            
            # 检查是否重叠
            if new_start <= existing_end and new_end >= existing_start:
                conflicting_mappings.append(existing_mapping)
        
        return conflicting_mappings
    
    @staticmethod
    def validate_mapping_no_conflicts(
        customer_id: str,
        factory_product_number: str,
        effective_date: datetime,
        expiry_date: Optional[datetime],
        exclude_mapping_id: Optional[int] = None,
        db: Session = None
    ) -> bool:
        """
        验证映射是否存在冲突（同一时间段内的映射冲突）
        
        Args:
            customer_id: 客户ID
            factory_product_number: 本厂编号
            effective_date: 生效日期
            expiry_date: 失效日期（可选）
            exclude_mapping_id: 排除的映射ID（用于更新时排除自身）
            db: 数据库会话
            
        Returns:
            bool: 如果无冲突返回True
            
        Raises:
            ConflictException: 如果存在冲突的映射
        """
        conflicting_mappings = MappingService.check_mapping_conflicts(
            customer_id=customer_id,
            factory_product_number=factory_product_number,
            effective_date=effective_date,
            expiry_date=expiry_date,
            exclude_mapping_id=exclude_mapping_id,
            db=db
        )
        
        if conflicting_mappings:
            # 构建冲突详情
            conflict_details = []
            for mapping in conflicting_mappings:
                conflict_details.append({
                    "mapping_id": mapping.id,
                    "material_code": mapping.material_code,
                    "production_version_id": mapping.production_version_id,
                    "effective_date": mapping.effective_date.isoformat() if mapping.effective_date else None,
                    "expiry_date": mapping.expiry_date.isoformat() if mapping.expiry_date else None,
                    "is_default": mapping.is_default
                })
            
            raise ConflictException(
                error_code=ErrorCodes.FACTORY_PRODUCT_MAPPING_CONFLICT,
                detail=f"本厂编号映射存在时间段冲突：{factory_product_number}（客户: {customer_id}）",
                resource_type="FactoryProductMapping",
                resource_id=f"{customer_id}/{factory_product_number}",
                extra_data={
                    "conflicts": conflict_details,
                    "new_effective_date": effective_date.isoformat() if effective_date else None,
                    "new_expiry_date": expiry_date.isoformat() if expiry_date else None
                }
            )
        
        return True
    
    @staticmethod
    def find_mappings_in_period(
        customer_id: str,
        factory_product_number: str,
        start_date: datetime,
        end_date: Optional[datetime],
        db: Session
    ) -> List[FactoryProductMapping]:
        """
        查找指定时间段内的所有映射（包括历史映射）
        
        Args:
            customer_id: 客户ID
            factory_product_number: 本厂编号
            start_date: 开始日期
            end_date: 结束日期（可选）
            db: 数据库会话
            
        Returns:
            List[FactoryProductMapping]: 映射列表
        """
        query = db.query(FactoryProductMapping).filter(
            FactoryProductMapping.customer_id == customer_id,
            FactoryProductMapping.factory_product_number == factory_product_number,
            FactoryProductMapping.is_deleted == False
        )
        
        # 查找时间段有重叠的映射
        if end_date:
            query = query.filter(
                or_(
                    # 映射的生效日期在查询时间段内
                    and_(
                        FactoryProductMapping.effective_date >= start_date,
                        FactoryProductMapping.effective_date <= end_date
                    ),
                    # 映射的失效日期在查询时间段内
                    and_(
                        FactoryProductMapping.expiry_date.isnot(None),
                        FactoryProductMapping.expiry_date >= start_date,
                        FactoryProductMapping.expiry_date <= end_date
                    ),
                    # 映射完全包含查询时间段
                    and_(
                        FactoryProductMapping.effective_date <= start_date,
                        or_(
                            FactoryProductMapping.expiry_date.is_(None),
                            FactoryProductMapping.expiry_date >= end_date
                        )
                    )
                )
            )
        else:
            # 如果没有结束日期，查找生效日期在开始日期之后的映射
            query = query.filter(FactoryProductMapping.effective_date >= start_date)
        
        return query.order_by(FactoryProductMapping.effective_date).all()
    
    @staticmethod
    @transactional
    def create_factory_product_mapping(
        mapping_data: dict,
        current_user: str,
        db: Session
    ) -> FactoryProductMapping:
        """
        创建本厂编号映射（带冲突检测）
        
        Args:
            mapping_data: 映射数据字典，包含：
                - customer_id: 客户ID
                - factory_product_number: 本厂编号
                - material_code: 物料编码
                - production_version_id: 生产版本ID（可选）
                - is_default: 是否默认映射
                - effective_date: 生效日期
                - expiry_date: 失效日期（可选）
            current_user: 当前用户名
            db: 数据库会话
            
        Returns:
            FactoryProductMapping: 创建的映射对象
            
        Raises:
            NotFoundException: 客户、物料或生产版本不存在
            ValidationException: 物料或生产版本状态无效
            ConflictException: 存在时间段冲突
        """
        from backend.common.models.sd import Customer
        
        log_info("开始创建本厂编号映射", 
                customer_id=mapping_data["customer_id"],
                factory_product_number=mapping_data["factory_product_number"],
                user=current_user)
        
        # 验证客户存在
        customer = db.query(Customer).filter(
            Customer.customer_id == mapping_data["customer_id"]
        ).first()
        if not customer:
            raise NotFoundException(
                resource_type="Customer",
                resource_id=mapping_data["customer_id"]
            )
        
        # 验证物料存在且激活
        material = db.query(Material).filter(
            Material.material_code == mapping_data["material_code"]
        ).first()
        if not material:
            raise NotFoundException(
                resource_type="Material",
                resource_id=mapping_data["material_code"]
            )
        if material.status != "ACTIVE":
            raise ValidationException(
                error_code=ErrorCodes.MATERIAL_NOT_ACTIVE,
                detail=f"物料状态非激活: {mapping_data['material_code']}，当前状态: {material.status}",
                field="material_status",
                value=material.status
            )
        
        # 验证生产版本（如果提供）
        if mapping_data.get("production_version_id"):
            pv = db.query(ProductionVersion).filter(
                ProductionVersion.production_version_id == mapping_data["production_version_id"]
            ).first()
            if not pv:
                raise NotFoundException(
                    resource_type="ProductionVersion",
                    resource_id=mapping_data["production_version_id"]
                )
            if pv.status not in ["RELEASED", "ACTIVE"]:
                raise ValidationException(
                    error_code=ErrorCodes.PRODUCTION_VERSION_STATUS_INVALID,
                    detail=f"生产版本状态不可用: {mapping_data['production_version_id']}，当前状态: {pv.status}",
                    field="production_version_status",
                    value=pv.status
                )
            if pv.material_code != mapping_data["material_code"]:
                raise ValidationException(
                    error_code=ErrorCodes.MATERIAL_CODE_MISMATCH,
                    detail=f"生产版本的物料编码与映射不一致: 生产版本物料={pv.material_code}，映射物料={mapping_data['material_code']}",
                    field="material_code",
                    value=mapping_data["material_code"]
                )
        
        # 检查时间段冲突
        MappingService.validate_mapping_no_conflicts(
            customer_id=mapping_data["customer_id"],
            factory_product_number=mapping_data["factory_product_number"],
            effective_date=mapping_data["effective_date"],
            expiry_date=mapping_data.get("expiry_date"),
            db=db
        )
        
        # 如果设置为默认，取消其他默认映射
        if mapping_data.get("is_default", False):
            db.query(FactoryProductMapping).filter(
                FactoryProductMapping.customer_id == mapping_data["customer_id"],
                FactoryProductMapping.factory_product_number == mapping_data["factory_product_number"],
                FactoryProductMapping.is_default == True,
                FactoryProductMapping.is_deleted == False
            ).update({"is_default": False})
        
        # 创建映射
        db_mapping = FactoryProductMapping(
            customer_id=mapping_data["customer_id"],
            factory_product_number=mapping_data["factory_product_number"],
            material_code=mapping_data["material_code"],
            production_version_id=mapping_data.get("production_version_id"),
            is_default=mapping_data.get("is_default", False),
            effective_date=mapping_data["effective_date"],
            expiry_date=mapping_data.get("expiry_date"),
            created_by=current_user
        )
        
        db.add(db_mapping)
        # 先flush以持久化对象，否则refresh会报未持久化错误
        db.flush()
        # 事务由 @transactional 装饰器自动提交
        db.refresh(db_mapping)
        
        log_info("本厂编号映射创建成功", 
                mapping_id=db_mapping.id,
                customer_id=mapping_data["customer_id"],
                factory_product_number=mapping_data["factory_product_number"])
        
        return db_mapping
    
    @staticmethod
    @transactional
    def update_factory_product_mapping(
        mapping_id: int,
        mapping_data: dict,
        current_user: str,
        db: Session
    ) -> FactoryProductMapping:
        """
        更新本厂编号映射（带冲突检测）
        
        Args:
            mapping_id: 映射ID
            mapping_data: 映射数据字典（部分更新）
            current_user: 当前用户名
            db: 数据库会话
            
        Returns:
            FactoryProductMapping: 更新后的映射对象
            
        Raises:
            NotFoundException: 映射、客户、物料或生产版本不存在
            ValidationException: 物料或生产版本状态无效
            ConflictException: 存在时间段冲突
        """
        from backend.common.models.sd import Customer
        
        # 获取现有映射
        db_mapping = db.query(FactoryProductMapping).filter(
            FactoryProductMapping.id == mapping_id,
            FactoryProductMapping.is_deleted == False
        ).first()
        
        if not db_mapping:
            raise NotFoundException(
                resource_type="FactoryProductMapping",
                resource_id=str(mapping_id)
            )
        
        log_info("开始更新本厂编号映射", 
                mapping_id=mapping_id,
                customer_id=db_mapping.customer_id,
                factory_product_number=db_mapping.factory_product_number,
                user=current_user)
        
        # 确定要使用的值（更新值优先，否则使用现有值）
        customer_id = mapping_data.get("customer_id") or db_mapping.customer_id
        factory_product_number = mapping_data.get("factory_product_number") or db_mapping.factory_product_number
        material_code = mapping_data.get("material_code") or db_mapping.material_code
        production_version_id = mapping_data.get("production_version_id")
        if production_version_id is None:
            production_version_id = db_mapping.production_version_id
        
        effective_date = mapping_data.get("effective_date")
        if effective_date is None:
            effective_date = db_mapping.effective_date
        
        expiry_date = mapping_data.get("expiry_date")
        if expiry_date is None:
            expiry_date = db_mapping.expiry_date
        
        # 验证客户（如果更新）
        if mapping_data.get("customer_id"):
            customer = db.query(Customer).filter(
                Customer.customer_id == mapping_data["customer_id"]
            ).first()
            if not customer:
                raise NotFoundException(
                    resource_type="Customer",
                    resource_id=mapping_data["customer_id"]
                )
        
        # 验证物料（如果更新）
        if mapping_data.get("material_code"):
            material = db.query(Material).filter(
                Material.material_code == mapping_data["material_code"]
            ).first()
            if not material:
                raise NotFoundException(
                    resource_type="Material",
                    resource_id=mapping_data["material_code"]
                )
            if material.status != "ACTIVE":
                raise ValidationException(
                    error_code=ErrorCodes.MATERIAL_NOT_ACTIVE,
                    detail=f"物料状态非激活: {mapping_data['material_code']}，当前状态: {material.status}",
                    field="material_status",
                    value=material.status
                )
        
        # 验证生产版本（如果更新）
        if mapping_data.get("production_version_id") is not None:
            if mapping_data["production_version_id"]:
                pv = db.query(ProductionVersion).filter(
                    ProductionVersion.production_version_id == mapping_data["production_version_id"]
                ).first()
                if not pv:
                    raise NotFoundException(
                        resource_type="ProductionVersion",
                        resource_id=mapping_data["production_version_id"]
                    )
                if pv.status not in ["RELEASED", "ACTIVE"]:
                    raise ValidationException(
                        error_code=ErrorCodes.PRODUCTION_VERSION_STATUS_INVALID,
                        detail=f"生产版本状态不可用: {mapping_data['production_version_id']}，当前状态: {pv.status}",
                        field="production_version_status",
                        value=pv.status
                    )
                final_material_code = mapping_data.get("material_code") or db_mapping.material_code
                if pv.material_code != final_material_code:
                    raise ValidationException(
                        error_code=ErrorCodes.MATERIAL_CODE_MISMATCH,
                        detail=f"生产版本的物料编码与映射不一致: 生产版本物料={pv.material_code}，映射物料={final_material_code}",
                        field="material_code",
                        value=final_material_code
                    )
        
        # 检查时间段冲突（排除自身）
        if mapping_data.get("effective_date") is not None or mapping_data.get("expiry_date") is not None:
            MappingService.validate_mapping_no_conflicts(
                customer_id=customer_id,
                factory_product_number=factory_product_number,
                effective_date=effective_date,
                expiry_date=expiry_date,
                exclude_mapping_id=mapping_id,
                db=db
            )
        
        # 如果设置为默认，取消其他默认映射
        if mapping_data.get("is_default") is True:
            db.query(FactoryProductMapping).filter(
                FactoryProductMapping.customer_id == customer_id,
                FactoryProductMapping.factory_product_number == factory_product_number,
                FactoryProductMapping.id != mapping_id,
                FactoryProductMapping.is_default == True,
                FactoryProductMapping.is_deleted == False
            ).update({"is_default": False})
        
        # 更新字段
        if mapping_data.get("customer_id") is not None:
            db_mapping.customer_id = mapping_data["customer_id"]
        if mapping_data.get("factory_product_number") is not None:
            db_mapping.factory_product_number = mapping_data["factory_product_number"]
        if mapping_data.get("material_code") is not None:
            db_mapping.material_code = mapping_data["material_code"]
        if mapping_data.get("production_version_id") is not None:
            db_mapping.production_version_id = mapping_data["production_version_id"]
        if mapping_data.get("is_default") is not None:
            db_mapping.is_default = mapping_data["is_default"]
        if mapping_data.get("effective_date") is not None:
            db_mapping.effective_date = mapping_data["effective_date"]
        if mapping_data.get("expiry_date") is not None:
            db_mapping.expiry_date = mapping_data["expiry_date"]
        
        db_mapping.updated_by = current_user
        # 事务由 @transactional 装饰器自动提交
        db.refresh(db_mapping)
        
        log_info("本厂编号映射更新成功", 
                mapping_id=mapping_id,
                customer_id=customer_id,
                factory_product_number=factory_product_number)
        
        return db_mapping

