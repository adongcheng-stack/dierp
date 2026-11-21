"""
统一验证服务模块
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from dataclasses import dataclass
from decimal import Decimal

from backend.common.exceptions import ValidationException, NotFoundException, ErrorCodes
from backend.common.models.mm import Material
from backend.common.models.eng import BOM, BOMItem, Routing, RoutingOperation, ProductionVersion
from backend.common.models.pp import WorkCenter


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BOMValidator:
    """BOM验证器"""
    
    @staticmethod
    def validate_bom_structure(bom_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        验证BOM结构完整性
        
        Args:
            bom_data: BOM数据字典，包含 parent_material_code, items 等字段
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 验证父物料是否存在
        if not bom_data.get("parent_material_code"):
            errors.append("BOM必须指定父物料编码")
        else:
            parent_material = db.query(Material).filter(
                Material.material_code == bom_data["parent_material_code"]
            ).first()
            if not parent_material:
                errors.append(f"父物料不存在: {bom_data['parent_material_code']}")
            elif parent_material.status != "ACTIVE":
                warnings.append(f"父物料状态非激活: {parent_material.status}")
        
        # 验证BOM明细不能为空
        items = bom_data.get("items", [])
        if not items or len(items) == 0:
            errors.append("BOM必须至少包含一个物料明细")
        
        # 验证行号唯一性
        if items:
            line_numbers = [item.get("line_number") for item in items if item.get("line_number")]
            if len(line_numbers) != len(set(line_numbers)):
                errors.append("BOM明细行号不能重复")
        
        # 验证物料编码存在性
        for idx, item in enumerate(items, start=1):
            material_code = item.get("material_code")
            if not material_code:
                errors.append(f"第{idx}行明细缺少物料编码")
            else:
                material = db.query(Material).filter(
                    Material.material_code == material_code
                ).first()
                if not material:
                    errors.append(f"第{idx}行明细的物料不存在: {material_code}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_bom_quantities(bom_data: Dict[str, Any]) -> ValidationResult:
        """
        验证BOM数量合理性
        
        Args:
            bom_data: BOM数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 验证基数
        base_quantity = bom_data.get("base_quantity", 1)
        if base_quantity <= 0:
            errors.append("BOM基数必须大于0")
        
        # 验证明细数量
        items = bom_data.get("items", [])
        for idx, item in enumerate(items, start=1):
            quantity = item.get("quantity")
            if quantity is None:
                errors.append(f"第{idx}行明细缺少数量")
            elif quantity <= 0:
                errors.append(f"第{idx}行明细数量必须大于0")
            
            # 验证损耗率
            scrap_rate = item.get("scrap_rate")
            if scrap_rate is not None:
                if scrap_rate < 0 or scrap_rate > 100:
                    errors.append(f"第{idx}行明细损耗率必须在0-100%之间")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_bom_hierarchy(bom_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        验证BOM层级关系（防止循环引用）
        
        Args:
            bom_data: BOM数据字典
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        parent_material_code = bom_data.get("parent_material_code")
        if not parent_material_code:
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        items = bom_data.get("items", [])
        
        # 检查是否有子物料与父物料相同（直接循环引用）
        for item in items:
            material_code = item.get("material_code")
            if material_code == parent_material_code:
                errors.append(f"不能将父物料 {parent_material_code} 作为子物料，避免循环引用")
        
        # 深层循环引用：递归检查每个子物料的下级 BOM 是否会回到父物料
        def descendants_of(material_code: str, visited: set) -> bool:
            """从 material_code 出发，其任意下级 BOM 是否包含 parent_material_code。"""
            if material_code in visited:
                return False
            next_visited = visited | {material_code}
            boms = db.query(BOM).filter(
                BOM.parent_material_code == material_code
            ).all()
            for bom in boms:
                for item in bom.items:
                    child_code = item.material_code
                    if not child_code:
                        continue
                    if child_code == parent_material_code:
                        return True
                    if descendants_of(child_code, next_visited):
                        return True
            return False

        for item in items:
            material_code = item.get("material_code")
            if not material_code or material_code == parent_material_code:
                continue
            if descendants_of(material_code, {parent_material_code}):
                errors.append(
                    f"检测到循环引用：{parent_material_code} → {material_code} → … → {parent_material_code}"
                )
                break

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_bom(bom_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        完整的BOM验证
        
        Args:
            bom_data: BOM数据字典
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
            
        Raises:
            ValidationException: 验证失败时抛出
        """
        # 合并所有验证结果
        structure_result = BOMValidator.validate_bom_structure(bom_data, db)
        quantities_result = BOMValidator.validate_bom_quantities(bom_data)
        hierarchy_result = BOMValidator.validate_bom_hierarchy(bom_data, db)
        
        all_errors = structure_result.errors + quantities_result.errors + hierarchy_result.errors
        all_warnings = structure_result.warnings + quantities_result.warnings + hierarchy_result.warnings
        
        is_valid = len(all_errors) == 0
        
        if not is_valid:
            raise ValidationException(
                error_code=ErrorCodes.BOM_VALIDATION_FAILED,
                detail="BOM验证失败",
                extra_data={
                    "errors": all_errors,
                    "warnings": all_warnings
                }
            )
        
        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=all_warnings
        )


class RoutingValidator:
    """Routing验证器"""
    
    @staticmethod
    def validate_routing_structure(routing_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        验证Routing结构完整性
        
        Args:
            routing_data: Routing数据字典
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 验证物料是否存在
        material_code = routing_data.get("material_code")
        if not material_code:
            errors.append("工艺路线必须指定物料编码")
        else:
            material = db.query(Material).filter(
                Material.material_code == material_code
            ).first()
            if not material:
                errors.append(f"物料不存在: {material_code}")
            elif material.status != "ACTIVE":
                warnings.append(f"物料状态非激活: {material.status}")
        
        # 验证工序不能为空
        operations = routing_data.get("operations", [])
        if not operations or len(operations) == 0:
            errors.append("工艺路线必须至少包含一个工序")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_routing_operations(routing_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        验证Routing工序顺序
        
        Args:
            routing_data: Routing数据字典
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        operations = routing_data.get("operations", [])
        if not operations:
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证工序号唯一性
        operation_nos = [op.get("operation_no") for op in operations if op.get("operation_no")]
        if len(operation_nos) != len(set(operation_nos)):
            errors.append("工序号不能重复")
        
        # 验证工序必填字段
        for idx, op in enumerate(operations, start=1):
            if not op.get("operation_code"):
                errors.append(f"第{idx}个工序缺少工序代码")
            if not op.get("operation_name"):
                errors.append(f"第{idx}个工序缺少工序名称")
            if not op.get("operation_type"):
                errors.append(f"第{idx}个工序缺少工序类型")
            if not op.get("work_center_id"):
                errors.append(f"第{idx}个工序缺少工作中心ID")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_routing_work_centers(routing_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        验证Routing工作中心有效性
        
        Args:
            routing_data: Routing数据字典
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        operations = routing_data.get("operations", [])
        if not operations:
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证每个工序的工作中心是否存在且有效
        for idx, op in enumerate(operations, start=1):
            work_center_id = op.get("work_center_id")
            if work_center_id:
                work_center = db.query(WorkCenter).filter(
                    WorkCenter.work_center_id == work_center_id
                ).first()
                if not work_center:
                    errors.append(f"第{idx}个工序的工作中心不存在: {work_center_id}")
                elif hasattr(work_center, 'status') and work_center.status != "ACTIVE":
                    warnings.append(f"第{idx}个工序的工作中心状态非激活: {work_center_id}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_routing_times(routing_data: Dict[str, Any]) -> ValidationResult:
        """
        验证Routing时间参数合理性
        
        Args:
            routing_data: Routing数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        operations = routing_data.get("operations", [])
        if not operations:
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证时间参数
        for idx, op in enumerate(operations, start=1):
            setup_time = op.get("setup_time", 0)
            machine_time = op.get("machine_time", 0)
            labor_time = op.get("labor_time", 0)
            
            if setup_time < 0:
                errors.append(f"第{idx}个工序的调机时间不能小于0")
            if machine_time < 0:
                errors.append(f"第{idx}个工序的机器时间不能小于0")
            if labor_time < 0:
                errors.append(f"第{idx}个工序的人工时间不能小于0")
            
            # 警告：如果所有时间都是0
            if setup_time == 0 and machine_time == 0 and labor_time == 0:
                warnings.append(f"第{idx}个工序的所有时间参数均为0")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_routing(routing_data: Dict[str, Any], db: Session) -> ValidationResult:
        """
        完整的Routing验证
        
        Args:
            routing_data: Routing数据字典
            db: 数据库会话
            
        Returns:
            ValidationResult: 验证结果
            
        Raises:
            ValidationException: 验证失败时抛出
        """
        # 合并所有验证结果
        structure_result = RoutingValidator.validate_routing_structure(routing_data, db)
        operations_result = RoutingValidator.validate_routing_operations(routing_data, db)
        work_centers_result = RoutingValidator.validate_routing_work_centers(routing_data, db)
        times_result = RoutingValidator.validate_routing_times(routing_data)
        
        all_errors = (structure_result.errors + operations_result.errors + 
                     work_centers_result.errors + times_result.errors)
        all_warnings = (structure_result.warnings + operations_result.warnings + 
                       work_centers_result.warnings + times_result.warnings)
        
        is_valid = len(all_errors) == 0
        
        if not is_valid:
            raise ValidationException(
                error_code=ErrorCodes.ROUTING_VALIDATION_FAILED,
                detail="工艺路线验证失败",
                extra_data={
                    "errors": all_errors,
                    "warnings": all_warnings
                }
            )
        
        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=all_warnings
        )


class ProductionVersionValidator:
    """生产版本验证器"""
    
    @staticmethod
    def validate_production_version_status(
        production_version_id: str,
        db: Session,
        allowed_statuses: Optional[List[str]] = None
    ) -> ProductionVersion:
        """
        验证生产版本状态
        
        Args:
            production_version_id: 生产版本ID
            db: 数据库会话
            allowed_statuses: 允许的状态列表，默认为 ["RELEASED", "ACTIVE"]
            
        Returns:
            ProductionVersion: 生产版本对象
            
        Raises:
            NotFoundException: 生产版本不存在
            ValidationException: 生产版本状态不可用
        """
        if allowed_statuses is None:
            allowed_statuses = ["RELEASED", "ACTIVE"]
        
        pv = db.query(ProductionVersion).filter(
            ProductionVersion.production_version_id == production_version_id
        ).first()
        
        if not pv:
            raise NotFoundException(
                resource_type="ProductionVersion",
                resource_id=production_version_id
            )
        
        if pv.status not in allowed_statuses:
            raise ValidationException(
                error_code=ErrorCodes.PRODUCTION_VERSION_STATUS_INVALID,
                detail=f"生产版本状态不可用: {pv.status}，允许的状态: {allowed_statuses}",
                field="status",
                value=pv.status
            )
        
        return pv

