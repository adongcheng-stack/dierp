"""
业务规则验证模块

实现内容：
- 客户信用额度（含未完成订单总额）
- 物料库存（含安全库存）
- 工作中心产能（日产能 - 已排程占用）
- 多层级 BOM 展开与物料需求校验
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional, Any, Tuple

from sqlalchemy.orm import Session

from backend.common.exceptions import ValidationException, ErrorCodes
from backend.common.models.mm import Material
from backend.common.models.pp import WorkCenter, ProductionOrder
from backend.common.models.sd import Customer, SalesOrder, SalesOrderStatus
from backend.common.models.eng import BOM, ProductionVersion, Routing, RoutingOperation
from backend.common.models.planning import (
    ScheduledOperation,
    ScheduleOpStatus,
    WorkCalendar,
)


# 计入「未完成订单」的销售订单状态：已发货/已交付但未关闭的仍占用信用额度
_OPEN_SO_STATUSES = {
    SalesOrderStatus.DRAFT,
    SalesOrderStatus.PENDING_REVIEW,
    SalesOrderStatus.REVIEWING,
    SalesOrderStatus.APPROVED,
    SalesOrderStatus.IN_PRODUCTION,
    SalesOrderStatus.SHIPPED,
    SalesOrderStatus.DELIVERED,
}


def _m(value: Any) -> Decimal:
    """安全转 Decimal，空值按 0 处理。"""
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal("0")


def _as_date(value: Any) -> Optional[date]:
    """将 datetime / date / 'YYYY-MM-DD...' 字符串归一为 date。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) >= 10:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _parse_hhmm(value: Any) -> Optional[Tuple[int, int]]:
    """解析 'HH:MM' 时间字符串。"""
    if not isinstance(value, str) or ":" not in value:
        return None
    try:
        parts = value.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        if 0 <= hour <= 24 and 0 <= minute < 60:
            return hour, minute
        return None
    except (ValueError, IndexError):
        return None


class BusinessRulesValidator:
    """业务规则验证器"""

    # ── 客户信用额度 ────────────────────────────────────────────────────

    @staticmethod
    def calculate_outstanding_orders_amount(customer_id: str, db: Session) -> Decimal:
        """计算客户未完成订单总额（不含已关闭/已完成/已取消）。"""
        rows = db.query(SalesOrder.total_amount).filter(
            SalesOrder.customer_id == customer_id,
            SalesOrder.status.in_(list(_OPEN_SO_STATUSES)),
        ).all()
        return sum((_m(row[0]) for row in rows), Decimal("0"))

    @staticmethod
    def validate_customer_credit(
        customer_id: str,
        order_amount: Decimal,
        db: Session
    ) -> bool:
        """验证客户信用额度：未完成订单总额 + 本次订单不得超过额度。"""
        customer = db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()

        if not customer or not customer.credit_limit:
            return True

        credit_limit = _m(customer.credit_limit)
        outstanding = BusinessRulesValidator.calculate_outstanding_orders_amount(customer_id, db)
        total = outstanding + _m(order_amount)

        if total > credit_limit:
            raise ValidationException(
                error_code="CUSTOMER_CREDIT_EXCEEDED",
                detail=(
                    f"客户未完成订单总额 {outstanding} + 本次订单 {order_amount} "
                    f"= {total} 超过信用额度 {credit_limit}"
                ),
                field="order_amount",
                value=float(order_amount)
            )
        return True

    # ── 物料库存 ────────────────────────────────────────────────────────

    @staticmethod
    def validate_material_stock(
        material_code: str,
        required_quantity: Decimal,
        db: Session
    ) -> bool:
        material = db.query(Material).filter(
            Material.material_code == material_code
        ).first()

        if not material:
            return True

        current_stock = _m(material.current_stock)
        safety_stock = _m(material.safety_stock)
        available_stock = current_stock - safety_stock

        if _m(required_quantity) > available_stock:
            raise ValidationException(
                error_code="MATERIAL_STOCK_INSUFFICIENT",
                detail=(
                    f"物料 {material_code} 库存不足：需要 {required_quantity}，"
                    f"可用 {available_stock}（当前库存：{current_stock}，安全库存：{safety_stock}）"
                ),
                field="required_quantity",
                value=float(required_quantity)
            )
        return True

    # ── 工作中心产能 ────────────────────────────────────────────────────

    @staticmethod
    def _capacity_params(work_center_id: str, db: Session) -> Optional[Tuple[Decimal, Decimal]]:
        """返回 (日产能分钟, 利用率%)；无法推导时返回 None 表示跳过校验。"""
        work_center = db.query(WorkCenter).filter(
            WorkCenter.work_center_id == work_center_id
        ).first()
        if not work_center:
            return None

        # 优先使用 APS 工作中心日历，其次回退到工作中心自身字段
        calendar = db.query(WorkCalendar).filter(
            WorkCalendar.work_center_id == work_center_id
        ).first()
        if calendar:
            start, end = calendar.shift_start, calendar.shift_end
            break_hours = _m(calendar.break_hours if calendar.break_hours is not None else 1)
            utilization = _m(calendar.utilization if calendar.utilization is not None else 100)
        else:
            start, end = work_center.shift_start_time, work_center.shift_finish_time
            if not start or not end:
                return None
            break_hours = _m(work_center.break_time or 0)
            utilization = _m(
                work_center.capacity_utilization
                if work_center.capacity_utilization is not None else 100
            )

        start_parts, end_parts = _parse_hhmm(start), _parse_hhmm(end)
        if not start_parts or not end_parts or utilization <= 0:
            return None

        start_minutes = start_parts[0] * 60 + start_parts[1]
        end_minutes = end_parts[0] * 60 + end_parts[1]
        shift_minutes = Decimal(max(0, end_minutes - start_minutes)) - break_hours * 60
        machines = int(work_center.number_of_capacities or 1)
        daily = shift_minutes * utilization / Decimal("100") * machines
        if daily <= 0:
            return None
        return daily, utilization

    @staticmethod
    def calculate_daily_capacity_minutes(work_center_id: str, db: Session) -> Decimal:
        """工作中心日产能（折算利用率与能力数量后的有效机器分钟）。"""
        params = BusinessRulesValidator._capacity_params(work_center_id, db)
        return params[0] if params else Decimal("0")

    @staticmethod
    def calculate_occupied_capacity_minutes(
        work_center_id: str,
        planned_date: Any,
        db: Session
    ) -> Decimal:
        """指定日期已排程占用的有效机器分钟（排除已取消排程）。"""
        target = _as_date(planned_date)
        if target is None:
            return Decimal("0")

        params = BusinessRulesValidator._capacity_params(work_center_id, db)
        utilization = params[1] if params else Decimal("100")

        operations = db.query(ScheduledOperation).filter(
            ScheduledOperation.work_center_id == work_center_id,
            ScheduledOperation.status != ScheduleOpStatus.CANCELLED,
        ).all()

        total = Decimal("0")
        for op in operations:
            op_date = _as_date(op.planned_start) or _as_date(op.planned_end)
            if op_date != target:
                continue
            minutes = _m(op.setup_minutes) + _m(op.run_minutes)
            total += minutes * Decimal("100") / utilization
        return total

    @staticmethod
    def validate_work_center_capacity(
        work_center_id: str,
        required_time: Decimal,
        planned_date: Optional[Any],
        db: Session
    ) -> bool:
        """验证工作中心在计划日期是否有足够产能。"""
        params = BusinessRulesValidator._capacity_params(work_center_id, db)
        if params is None:
            return True  # 缺少日历/班次参数时不阻断业务

        daily, utilization = params
        occupied = BusinessRulesValidator.calculate_occupied_capacity_minutes(
            work_center_id, planned_date, db)
        required_effective = _m(required_time) * Decimal("100") / utilization

        if occupied + required_effective > daily:
            raise ValidationException(
                error_code="WC_CAPACITY_INSUFFICIENT",
                detail=(
                    f"工作中心 {work_center_id} 在 {_as_date(planned_date)} 产能不足："
                    f"已占用 {occupied} 分钟 + 需求 {required_time} 分钟"
                    f"（折算后 {required_effective}） > 日产能 {daily} 分钟"
                ),
                field="required_time",
                value=float(required_time)
            )
        return True

    @staticmethod
    def validate_production_order_capacity(
        production_order_data: Dict[str, Any],
        db: Session
    ) -> bool:
        """验证生产订单各工序的工作中心产能。"""
        production_version_id = production_order_data.get("production_version_id")
        if not production_version_id:
            return True

        pv = db.query(ProductionVersion).filter(
            ProductionVersion.production_version_id == production_version_id
        ).first()
        if not pv or not pv.routing_id:
            return True

        routing = db.query(Routing).filter(
            Routing.routing_id == pv.routing_id
        ).first()
        if not routing:
            return True

        operations = db.query(RoutingOperation).filter(
            RoutingOperation.routing_id == routing.routing_id
        ).all()

        for op in operations:
            if op.work_center_id and op.scheduling_relevant:
                quantity = _m(production_order_data.get("quantity", 1))
                setup_time = _m(op.setup_time)
                machine_time = _m(op.machine_time)
                required_time = setup_time + machine_time * quantity

                BusinessRulesValidator.validate_work_center_capacity(
                    work_center_id=op.work_center_id,
                    required_time=required_time,
                    planned_date=production_order_data.get("planned_start_date"),
                    db=db
                )
        return True

    # ── 多层级 BOM 展开 ─────────────────────────────────────────────────

    @staticmethod
    def explode_bom_requirements(
        root_material_code: str,
        quantity: Decimal,
        db: Session,
        root_bom_number: Optional[str] = None,
        _visited: Optional[set] = None
    ) -> Dict[str, Decimal]:
        """递归展开 BOM，返回每种物料的总需求量（已计入损耗率）。

        _visited 用于防御脏数据中的环，避免无限递归。
        """
        requirements: Dict[str, Decimal] = {}
        if not root_material_code:
            return requirements

        visited = set(_visited or ())
        if root_material_code in visited:
            return requirements
        visited.add(root_material_code)

        if root_bom_number:
            bom = db.query(BOM).filter(BOM.bom_number == root_bom_number).first()
        else:
            bom = db.query(BOM).filter(
                BOM.parent_material_code == root_material_code
            ).order_by(BOM.effective_date.desc()).first()

        if not bom:
            return requirements

        base = _m(bom.base_quantity)
        if base <= 0:
            base = Decimal("1")
        scale = _m(quantity) / base

        for item in bom.items:
            code = item.material_code
            if not code:
                continue
            item_qty = _m(item.quantity) * scale
            scrap = _m(item.scrap_rate) / Decimal("100")
            item_qty = item_qty * (Decimal("1") + scrap)

            requirements[code] = requirements.get(code, Decimal("0")) + item_qty
            for sub_code, sub_qty in BusinessRulesValidator.explode_bom_requirements(
                code, item_qty, db, _visited=visited
            ).items():
                requirements[sub_code] = requirements.get(sub_code, Decimal("0")) + sub_qty

        return requirements

    @staticmethod
    def validate_production_order_materials(
        production_order_data: Dict[str, Any],
        db: Session
    ) -> bool:
        """展开生产订单对应 BOM，并校验每种物料的可用库存。"""
        production_version_id = production_order_data.get("production_version_id")
        pv = None
        if production_version_id:
            pv = db.query(ProductionVersion).filter(
                ProductionVersion.production_version_id == production_version_id
            ).first()

        root_material_code = production_order_data.get("material_code")
        if not root_material_code and pv:
            root_material_code = pv.material_code
        if not root_material_code:
            return True

        quantity = _m(production_order_data.get("quantity", 1))
        requirements = BusinessRulesValidator.explode_bom_requirements(
            root_material_code, quantity, db,
            root_bom_number=pv.bom_number if pv else None
        )

        for material_code, required_qty in requirements.items():
            BusinessRulesValidator.validate_material_stock(material_code, required_qty, db)
        return True
