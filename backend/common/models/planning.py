"""
GENERATED FILE - DO NOT EDIT BY HAND.
Source: ontology/model/planning.yaml (version 1.2.0)
Ontology: https://dierp.local/ontology/erp/v1#
Regenerate: python backend/ontology/generate_models.py
"""

from sqlalchemy import Column, ForeignKey, Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from enum import Enum
from backend.common.models.base import BaseModel


# ======================================================================
# 枚举（来自 ontology/src/mappings.json，唯一事实源）
# ======================================================================

class ProcurementType(str, Enum):
    """ProcurementType"""
    MAKE = "MAKE"
    BUY = "BUY"
    SUB = "SUB"

class MrpType(str, Enum):
    """MrpType"""
    MRP = "MRP"
    REORDER_POINT = "REORDER_POINT"
    NONE = "NONE"

class MrpRunType(str, Enum):
    """MrpRunType"""
    REGENERATIVE = "REGENERATIVE"
    NET_CHANGE = "NET_CHANGE"

class MrpRunStatus(str, Enum):
    """MrpRunStatus"""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PlannedOrderType(str, Enum):
    """PlannedOrderType"""
    PRODUCTION = "PRODUCTION"
    PURCHASE = "PURCHASE"
    TRANSFER = "TRANSFER"

class PlannedOrderStatus(str, Enum):
    """PlannedOrderStatus"""
    PLANNED = "PLANNED"
    FIRMED = "FIRMED"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"

class LotSizingRule(str, Enum):
    """LotSizingRule"""
    LOT_FOR_LOT = "LOT_FOR_LOT"
    FIXED_LOT = "FIXED_LOT"
    MIN_MAX = "MIN_MAX"
    EOQ = "EOQ"
    PERIOD_ORDER = "PERIOD_ORDER"

class PlannerAction(str, Enum):
    """PlannerAction"""
    NONE = "NONE"
    RELEASE = "RELEASE"
    EXPEDITE = "EXPEDITE"
    DELAY = "DELAY"
    CANCEL = "CANCEL"

class MrpExceptionType(str, Enum):
    """MrpExceptionType"""
    SHORTAGE = "SHORTAGE"
    EXCESS = "EXCESS"
    LATE = "LATE"
    EARLY = "EARLY"
    NO_BOM = "NO_BOM"
    NO_POLICY = "NO_POLICY"
    LEAD_TIME_VIOLATION = "LEAD_TIME_VIOLATION"
    CAPACITY_OVERLOAD = "CAPACITY_OVERLOAD"

class ExceptionSeverity(str, Enum):
    """ExceptionSeverity"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class ResolutionStatus(str, Enum):
    """ResolutionStatus"""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class DemandType(str, Enum):
    """DemandType"""
    SALES_ORDER = "SALES_ORDER"
    FORECAST = "FORECAST"
    SAFETY_STOCK = "SAFETY_STOCK"
    DEPENDENT = "DEPENDENT"
    MPS = "MPS"

class SupplyType(str, Enum):
    """SupplyType"""
    ON_HAND = "ON_HAND"
    PRODUCTION_ORDER = "PRODUCTION_ORDER"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    PLANNED_ORDER = "PLANNED_ORDER"

class KitStatus(str, Enum):
    """KitStatus"""
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    SHORT = "SHORT"

class CostRateType(str, Enum):
    """CostRateType"""
    LABOR = "LABOR"
    MACHINE = "MACHINE"
    OVERHEAD = "OVERHEAD"

class VarianceType(str, Enum):
    """VarianceType"""
    MATERIAL_PRICE = "MATERIAL_PRICE"
    MATERIAL_USAGE = "MATERIAL_USAGE"
    LABOR_RATE = "LABOR_RATE"
    LABOR_EFFICIENCY = "LABOR_EFFICIENCY"
    OVERHEAD = "OVERHEAD"

class CostStatus(str, Enum):
    """CostStatus"""
    OPEN = "OPEN"
    COLLECTED = "COLLECTED"
    SETTLED = "SETTLED"

class PurchaseOrderStatus(str, Enum):
    """PurchaseOrderStatus"""
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class PurchaseRequestStatus(str, Enum):
    """PurchaseRequestStatus"""
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"

class ReturnType(str, Enum):
    """ReturnType"""
    RETURN = "RETURN"
    CLAIM = "CLAIM"

class ReturnStatus(str, Enum):
    """ReturnStatus"""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"

class DeliveryStatus(str, Enum):
    """DeliveryStatus"""
    DRAFT = "DRAFT"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class InvoiceStatus(str, Enum):
    """InvoiceStatus"""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

class ReceivableEntryType(str, Enum):
    """ReceivableEntryType"""
    INVOICE = "INVOICE"
    RECEIPT = "RECEIPT"
    ADJUST = "ADJUST"

class SupplierInvoiceStatus(str, Enum):
    """SupplierInvoiceStatus"""
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class PaymentMethod(str, Enum):
    """PaymentMethod"""
    TRANSFER = "TRANSFER"
    CASH = "CASH"
    BILL = "BILL"

class AccountType(str, Enum):
    """AccountType"""
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

class JournalStatus(str, Enum):
    """JournalStatus"""
    DRAFT = "DRAFT"
    POSTED = "POSTED"

class PeriodStatus(str, Enum):
    """PeriodStatus"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class GlSourceType(str, Enum):
    """GlSourceType"""
    SALES_INVOICE_ISSUED = "SALES_INVOICE_ISSUED"
    SALES_DELIVERY_SHIPPED = "SALES_DELIVERY_SHIPPED"
    SUPPLIER_INVOICE_CONFIRMED = "SUPPLIER_INVOICE_CONFIRMED"
    SUPPLIER_PAYMENT_PAID = "SUPPLIER_PAYMENT_PAID"
    RECEIPT_PAID = "RECEIPT_PAID"
    MATERIAL_ISSUE = "MATERIAL_ISSUE"
    STOCK_ADJUST = "STOCK_ADJUST"
    PRODUCTION_COMPLETE = "PRODUCTION_COMPLETE"

class StocktakeStatus(str, Enum):
    """StocktakeStatus"""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"

class StockTransferStatus(str, Enum):
    """StockTransferStatus"""
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class ResourceStatus(str, Enum):
    """ResourceStatus"""
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DOWN = "DOWN"

class ScheduleRunStatus(str, Enum):
    """ScheduleRunStatus"""
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

class ScheduleAlgorithm(str, Enum):
    """ScheduleAlgorithm"""
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    MIXED = "MIXED"

class ScheduleOpStatus(str, Enum):
    """ScheduleOpStatus"""
    PLANNED = "PLANNED"
    LOCKED = "LOCKED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"

class ScheduleExceptionType(str, Enum):
    """ScheduleExceptionType"""
    CAPACITY_OVERLOAD = "CAPACITY_OVERLOAD"
    DUE_DATE_RISK = "DUE_DATE_RISK"
    MATERIAL_SHORTAGE = "MATERIAL_SHORTAGE"
    SKILL_MISMATCH = "SKILL_MISMATCH"
    CHANGEOVER_LIMIT = "CHANGEOVER_LIMIT"
    RESOURCE_DOWN = "RESOURCE_DOWN"

class ScenarioType(str, Enum):
    """ScenarioType"""
    INSERT_ORDER = "INSERT_ORDER"
    EQUIPMENT_DOWN = "EQUIPMENT_DOWN"
    MATERIAL_DELAY = "MATERIAL_DELAY"

class MaintenanceType(str, Enum):
    """MaintenanceType"""
    INSPECTION = "INSPECTION"
    LUBRICANT = "LUBRICANT"
    REPAIR = "REPAIR"
    OVERHAUL = "OVERHAUL"

class MaintenanceStatus(str, Enum):
    """MaintenanceStatus"""
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"

class FailureStatus(str, Enum):
    """FailureStatus"""
    OPEN = "OPEN"
    PROCESSING = "PROCESSING"
    CLOSED = "CLOSED"

class FailureSeverity(str, Enum):
    """FailureSeverity"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class InspectionType(str, Enum):
    """InspectionType"""
    INCOMING = "INCOMING"
    IN_PROCESS = "IN_PROCESS"
    FINAL = "FINAL"

class InspectionResult(str, Enum):
    """InspectionResult"""
    PASS = "PASS"
    FAIL = "FAIL"
    HOLD = "HOLD"

class InspectionStatus(str, Enum):
    """InspectionStatus"""
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class NcrSourceType(str, Enum):
    """NcrSourceType"""
    INSPECTION = "INSPECTION"
    REPORT = "REPORT"
    LOT_CARD = "LOT_CARD"
    MANUAL = "MANUAL"

class NcrSeverity(str, Enum):
    """NcrSeverity"""
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"

class NcrDisposition(str, Enum):
    """NcrDisposition"""
    REWORK = "REWORK"
    SCRAP = "SCRAP"
    USE_AS_IS = "USE_AS_IS"
    RETURN = "RETURN"
    REVIEW = "REVIEW"

class NcrStatus(str, Enum):
    """NcrStatus"""
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    DISPOSITIONED = "DISPOSITIONED"
    CLOSED = "CLOSED"


class PlanningPolicy(BaseModel):
    """物料计划参数策略"""
    __tablename__ = "planning_policies"

    policy_id = Column(String(50), nullable=False, unique=True, index=True, comment="策略编号")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, unique=True, index=True, comment="物料编码")

    mrp_type = Column(SQLEnum(MrpType), default=MrpType.MRP, comment="MRP/订货点/不计划")

    procurement_type = Column(SQLEnum(ProcurementType), default=ProcurementType.MAKE, comment="自制/采购/委外")

    lot_sizing_rule = Column(SQLEnum(LotSizingRule), default=LotSizingRule.LOT_FOR_LOT, comment="批量规则")

    fixed_lot_size = Column(Numeric(15, 4), default=0, comment="固定批量")

    min_order_qty = Column(Numeric(15, 4), default=0, comment="最小起订量")

    max_order_qty = Column(Numeric(15, 4), comment="最大批量")

    order_multiple = Column(Numeric(15, 4), default=1, comment="整数倍")

    eoq = Column(Numeric(15, 4), comment="经济订货量")

    lead_time_days = Column(Integer, default=0, comment="提前期天数")

    safety_time_days = Column(Integer, default=0, comment="安全时间天数")

    safety_stock = Column(Numeric(15, 4), default=0, comment="安全库存")

    reorder_point = Column(Numeric(15, 4), default=0, comment="订货点")

    planner_code = Column(String(50), comment="计划员")

    abc_class = Column(String(10), comment="ABC 分类")

    is_active = Column(Boolean, default=True, comment="是否启用")

    remarks = Column(Text)



class Forecast(BaseModel):
    """需求预测"""
    __tablename__ = "forecasts"

    forecast_number = Column(String(50), nullable=False, unique=True, index=True)

    version = Column(String(20), default="1")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True)

    customer_id = Column(String(50), ForeignKey("customers.customer_id"))

    quantity = Column(Numeric(15, 2), nullable=False)

    unit = Column(String(20), nullable=False)

    due_date = Column(DateTime, nullable=False, index=True)

    bucket_type = Column(String(20), default="WEEK")

    status = Column(String(20), index=True, default="RELEASED")

    consumed_quantity = Column(Numeric(15, 2), default=0)

    remarks = Column(Text)



class MpsPlan(BaseModel):
    """主生产计划"""
    __tablename__ = "mps_plans"

    mps_number = Column(String(50), nullable=False, unique=True, index=True)

    version = Column(String(20), default="1")

    plan_name = Column(String(200))

    plant_id = Column(String(50))

    horizon_start = Column(DateTime, nullable=False)

    horizon_end = Column(DateTime, nullable=False)

    bucket_type = Column(String(20), default="WEEK")

    status = Column(String(20), index=True, default="DRAFT")

    demand_source = Column(String(20), default="MIXED")

    total_gross = Column(Numeric(15, 2), default=0)

    total_planned = Column(Numeric(15, 2), default=0)

    generated_by = Column(String(50))

    generated_at = Column(DateTime)

    remarks = Column(Text)



class MpsEntry(BaseModel):
    """MPS 计划行"""
    __tablename__ = "mps_entries"

    mps_number = Column(String(50), ForeignKey("mps_plans.mps_number"), nullable=False, index=True)

    line_number = Column(Integer, nullable=False)

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True)

    bucket_date = Column(DateTime, nullable=False, index=True)

    opening_stock = Column(Numeric(15, 2), default=0)

    gross_requirement = Column(Numeric(15, 2), default=0)

    sales_demand = Column(Numeric(15, 2), default=0)

    forecast_demand = Column(Numeric(15, 2), default=0)

    scheduled_receipt = Column(Numeric(15, 2), default=0)

    projected_available = Column(Numeric(15, 2), default=0)

    net_requirement = Column(Numeric(15, 2), default=0)

    planned_receipt = Column(Numeric(15, 2), default=0)

    planner_action = Column(SQLEnum(PlannerAction), default=PlannerAction.NONE)

    remarks = Column(Text)



class MrpRun(BaseModel):
    """MRP 运算批次"""
    __tablename__ = "mrp_runs"

    run_number = Column(String(50), nullable=False, unique=True, index=True)

    run_type = Column(SQLEnum(MrpRunType), default=MrpRunType.REGENERATIVE)

    status = Column(SQLEnum(MrpRunStatus), index=True, default=MrpRunStatus.RUNNING)

    horizon_start = Column(DateTime, nullable=False)

    horizon_end = Column(DateTime, nullable=False)

    demand_source = Column(String(20), default="AUTO")

    mps_number = Column(String(50), ForeignKey("mps_plans.mps_number"))

    plant_id = Column(String(50))

    total_demands = Column(Integer, default=0)

    total_requirements = Column(Integer, default=0)

    planned_production_count = Column(Integer, default=0)

    planned_purchase_count = Column(Integer, default=0)

    exception_count = Column(Integer, default=0)

    shortage_count = Column(Integer, default=0)

    started_at = Column(DateTime)

    finished_at = Column(DateTime)

    run_by = Column(String(50))

    log_text = Column(Text)

    remarks = Column(Text)



class MrpRequirement(BaseModel):
    """MRP 需求行"""
    __tablename__ = "mrp_requirements"

    run_number = Column(String(50), ForeignKey("mrp_runs.run_number"), nullable=False, index=True)

    line_number = Column(Integer, nullable=False)

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True)

    requirement_level = Column(Integer, index=True, default=0)

    demand_type = Column(SQLEnum(DemandType), nullable=False)

    demand_ref = Column(String(100))

    parent_planned_order = Column(String(50))

    quantity = Column(Numeric(15, 2), nullable=False)

    covered_qty = Column(Numeric(15, 2), default=0)

    shortage_qty = Column(Numeric(15, 2), default=0)

    due_date = Column(DateTime, nullable=False, index=True)

    status = Column(String(20), default="OPEN")

    remarks = Column(Text)



class PlannedOrder(BaseModel):
    """计划订单"""
    __tablename__ = "planned_orders"

    planned_order_number = Column(String(50), nullable=False, unique=True, index=True)

    run_number = Column(String(50), ForeignKey("mrp_runs.run_number"), index=True)

    order_type = Column(SQLEnum(PlannedOrderType), nullable=False, index=True)

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True)

    quantity = Column(Numeric(15, 2), nullable=False)

    unit = Column(String(20), nullable=False)

    start_date = Column(DateTime, nullable=False)

    due_date = Column(DateTime, nullable=False, index=True)

    status = Column(SQLEnum(PlannedOrderStatus), index=True, default=PlannedOrderStatus.PLANNED)

    procurement_type = Column(String(20))

    supplier_id = Column(String(50))

    lot_sizing_rule = Column(String(20))

    lead_time_days = Column(Integer, default=0)

    demand_type = Column(String(20))

    demand_ref = Column(String(100))

    parent_planned_order = Column(String(50))

    conversion_order_number = Column(String(50))

    confirmed_by = Column(String(50))

    confirmed_at = Column(DateTime)

    remarks = Column(Text)



class PeggingLink(BaseModel):
    """需求-供应追溯链"""
    __tablename__ = "pegging_links"

    run_number = Column(String(50), ForeignKey("mrp_runs.run_number"), index=True)

    planned_order_number = Column(String(50), ForeignKey("planned_orders.planned_order_number"), index=True)

    demand_type = Column(SQLEnum(DemandType), nullable=False)

    demand_ref = Column(String(100))

    supply_type = Column(SQLEnum(SupplyType), nullable=False)

    supply_ref = Column(String(100))

    pegged_qty = Column(Numeric(15, 2), nullable=False)

    pegged_at = Column(DateTime)



class MrpException(BaseModel):
    """MRP 异常"""
    __tablename__ = "mrp_exceptions"

    run_number = Column(String(50), ForeignKey("mrp_runs.run_number"), index=True)

    exception_type = Column(SQLEnum(MrpExceptionType), nullable=False, index=True)

    severity = Column(SQLEnum(ExceptionSeverity), nullable=False, index=True)

    material_code = Column(String(50), ForeignKey("materials.material_code"), index=True)

    requirement_ref = Column(String(100))

    planned_order_number = Column(String(50))

    shortage_qty = Column(Numeric(15, 2), default=0)

    shortage_date = Column(DateTime)

    suggestion = Column(Text)

    resolution_status = Column(SQLEnum(ResolutionStatus), index=True, default=ResolutionStatus.OPEN)

    resolved_by = Column(String(50))

    resolved_at = Column(DateTime)

    remarks = Column(Text)



class PurchaseOrder(BaseModel):
    """采购订单"""
    __tablename__ = "purchase_orders"

    purchase_order_number = Column(String(50), nullable=False, unique=True, index=True)

    supplier_id = Column(String(50), index=True)

    supplier_name = Column(String(200))

    status = Column(SQLEnum(PurchaseOrderStatus), index=True, default=PurchaseOrderStatus.DRAFT)

    order_date = Column(DateTime)

    expected_date = Column(DateTime)

    currency = Column(String(10), default="CNY")

    total_amount = Column(Numeric(15, 2), default=0)

    source_planned_order = Column(String(50))

    remarks = Column(Text)



class PurchaseOrderLine(BaseModel):
    """采购订单行"""
    __tablename__ = "purchase_order_lines"

    purchase_order_number = Column(String(50), ForeignKey("purchase_orders.purchase_order_number"), nullable=False, index=True)

    line_number = Column(Integer, nullable=False)

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True)

    quantity = Column(Numeric(15, 2), nullable=False)

    received_quantity = Column(Numeric(15, 2), default=0)

    unit = Column(String(20), nullable=False)

    unit_price = Column(Numeric(15, 4), default=0)

    expected_date = Column(DateTime)

    status = Column(String(20), default="OPEN")

    remarks = Column(Text)



class Supplier(BaseModel):
    """供应商主数据"""
    __tablename__ = "suppliers"

    supplier_code = Column(String(50), nullable=False, unique=True, index=True, comment="供应商编码")

    supplier_name = Column(String(200), nullable=False, comment="供应商名称")

    short_name = Column(String(50), comment="简称")

    supplier_type = Column(String(20), default="MATERIAL", comment="供应商类型(MATERIAL/OUTSOURCE/SERVICE)")

    status = Column(String(20), index=True, default="ACTIVE", comment="状态(ACTIVE/INACTIVE)")

    contact_person = Column(String(50), comment="联系人")

    contact_phone = Column(String(30), comment="联系电话")

    email = Column(String(100), comment="邮箱")

    address = Column(String(200), comment="地址")

    tax_number = Column(String(50), comment="税号")

    bank_account = Column(String(50), comment="银行账号")

    payment_terms = Column(String(50), comment="付款条款")

    lead_time_days = Column(Integer, default=0, comment="默认交货天数")

    default_currency = Column(String(10), default="CNY", comment="默认币种")

    rating = Column(Integer, default=3, comment="评级(1-5)")

    remarks = Column(Text)



class PurchaseRequest(BaseModel):
    """采购申请"""
    __tablename__ = "purchase_requests"

    purchase_request_number = Column(String(50), nullable=False, unique=True, index=True, comment="采购申请号")

    supplier_id = Column(String(50), index=True, comment="供应商编码")

    supplier_name = Column(String(200), comment="供应商名称")

    status = Column(SQLEnum(PurchaseRequestStatus), index=True, default=PurchaseRequestStatus.DRAFT, comment="申请状态")

    request_date = Column(DateTime, comment="申请日期")

    expected_date = Column(DateTime, comment="期望到货日期")

    currency = Column(String(10), default="CNY", comment="币种")

    total_amount = Column(Numeric(15, 2), default=0, comment="预估总金额")

    source_planned_order = Column(String(50), comment="来源计划订单")

    requested_by = Column(String(50), comment="申请人")

    converted_po_number = Column(String(50), comment="转换生成的采购单号")

    remarks = Column(Text)



class PurchaseRequestLine(BaseModel):
    """采购申请行"""
    __tablename__ = "purchase_request_lines"

    purchase_request_number = Column(String(50), ForeignKey("purchase_requests.purchase_request_number"), nullable=False, index=True, comment="所属采购申请")

    line_number = Column(Integer, nullable=False, comment="行号")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="物料编码")

    quantity = Column(Numeric(15, 2), nullable=False, comment="申请数量")

    unit = Column(String(20), nullable=False, comment="单位")

    unit_price = Column(Numeric(15, 4), default=0, comment="预估单价")

    expected_date = Column(DateTime, comment="期望到货日期")

    status = Column(String(20), default="OPEN", comment="行状态(OPEN/CONVERTED)")

    remarks = Column(Text)



class PurchaseReturn(BaseModel):
    """采购退货索赔单"""
    __tablename__ = "purchase_returns"

    return_number = Column(String(50), nullable=False, unique=True, index=True, comment="退货索赔单号")

    purchase_order_number = Column(String(50), ForeignKey("purchase_orders.purchase_order_number"), nullable=False, index=True, comment="来源采购单")

    supplier_id = Column(String(50), index=True, comment="供应商编码")

    supplier_name = Column(String(200), comment="供应商名称")

    return_type = Column(SQLEnum(ReturnType), index=True, default=ReturnType.RETURN, comment="类型(退货/索赔)")

    status = Column(SQLEnum(ReturnStatus), index=True, default=ReturnStatus.DRAFT, comment="单据状态")

    return_date = Column(DateTime, comment="退货/索赔日期")

    total_amount = Column(Numeric(15, 2), default=0, comment="总金额(索赔额/退货额)")

    reason = Column(Text, comment="退货/索赔原因")

    remarks = Column(Text)



class PurchaseReturnLine(BaseModel):
    """采购退货行"""
    __tablename__ = "purchase_return_lines"

    return_number = Column(String(50), ForeignKey("purchase_returns.return_number"), nullable=False, index=True, comment="所属退货单")

    line_number = Column(Integer, nullable=False, comment="行号")

    purchase_order_line_number = Column(Integer, comment="来源采购行号")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="物料编码")

    quantity = Column(Numeric(15, 2), nullable=False, comment="数量")

    unit = Column(String(20), nullable=False, comment="单位")

    unit_price = Column(Numeric(15, 4), default=0, comment="单价")

    remarks = Column(Text)



class CostRate(BaseModel):
    """成本费率"""
    __tablename__ = "cost_rates"

    rate_id = Column(String(50), nullable=False, unique=True, index=True)

    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), index=True)

    rate_type = Column(SQLEnum(CostRateType), nullable=False, index=True)

    rate_per_hour = Column(Numeric(15, 4), nullable=False)

    currency = Column(String(10), default="CNY")

    effective_from = Column(DateTime)

    effective_to = Column(DateTime)

    status = Column(String(20), default="ACTIVE")

    remarks = Column(Text)



class WorkCalendar(BaseModel):
    """工作中心日历"""
    __tablename__ = "work_calendars"

    calendar_id = Column(String(50), nullable=False, unique=True, index=True)

    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), nullable=False, unique=True, index=True)

    shift_start = Column(String(10), default="08:00")

    shift_end = Column(String(10), default="20:00")

    break_hours = Column(Numeric(10, 2), default=1)

    capacity_hours = Column(Numeric(10, 2), default=10)

    utilization = Column(Numeric(5, 2), default=100)

    workdays = Column(String(50), default="1,2,3,4,5,6")

    status = Column(String(20), default="ACTIVE")



class StandardCost(BaseModel):
    """标准成本"""
    __tablename__ = "standard_costs"

    cost_id = Column(String(50), nullable=False, unique=True, index=True)

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True)

    version = Column(String(20), default="1")

    cost_date = Column(DateTime, index=True)

    material_cost = Column(Numeric(15, 4), default=0)

    labor_cost = Column(Numeric(15, 4), default=0)

    overhead_cost = Column(Numeric(15, 4), default=0)

    total_cost = Column(Numeric(15, 4), default=0)

    unit_cost = Column(Numeric(15, 4), default=0)

    currency = Column(String(10), default="CNY")

    status = Column(String(20), default="ACTIVE")

    rolled_up_at = Column(DateTime)

    cost_method = Column(String(20), default="STANDARD")

    remarks = Column(Text)



class ProductionCost(BaseModel):
    """工单实际成本归集"""
    __tablename__ = "production_costs"

    cost_id = Column(String(50), nullable=False, unique=True, index=True)

    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), nullable=False, unique=True, index=True)

    material_code = Column(String(50))

    quantity = Column(Numeric(15, 2))

    material_cost_actual = Column(Numeric(15, 4), default=0)

    labor_cost_actual = Column(Numeric(15, 4), default=0)

    overhead_actual = Column(Numeric(15, 4), default=0)

    total_actual = Column(Numeric(15, 4), default=0)

    standard_cost = Column(Numeric(15, 4), default=0)

    wip_value = Column(Numeric(15, 4), default=0)

    status = Column(SQLEnum(CostStatus), index=True, default=CostStatus.OPEN)

    collected_at = Column(DateTime)

    settled_at = Column(DateTime)

    remarks = Column(Text)



class CostVariance(BaseModel):
    """成本差异"""
    __tablename__ = "cost_variances"

    variance_number = Column(String(50), nullable=False, unique=True, index=True)

    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), index=True)

    variance_type = Column(SQLEnum(VarianceType), nullable=False, index=True)

    standard_amount = Column(Numeric(15, 4), default=0)

    actual_amount = Column(Numeric(15, 4), default=0)

    variance_amount = Column(Numeric(15, 4), default=0)

    variance_pct = Column(Numeric(10, 2), default=0)

    analyzed_at = Column(DateTime)

    remarks = Column(Text)



class CostSettlement(BaseModel):
    """工单成本结算"""
    __tablename__ = "cost_settlements"

    settlement_number = Column(String(50), nullable=False, unique=True, index=True)

    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), index=True)

    total_cost = Column(Numeric(15, 4), default=0)

    wip_value = Column(Numeric(15, 4), default=0)

    settlement_status = Column(SQLEnum(CostStatus), default=CostStatus.SETTLED)

    settled_at = Column(DateTime)

    remarks = Column(Text)



class KittingResult(BaseModel):
    """齐套分析结果"""
    __tablename__ = "kitting_results"

    result_number = Column(String(50), nullable=False, unique=True, index=True)

    source_type = Column(String(30), default="PRODUCTION_ORDER")

    source_ref = Column(String(50), nullable=False, index=True)

    material_code = Column(String(50))

    kit_status = Column(SQLEnum(KitStatus), index=True, default=KitStatus.FULL)

    required_qty = Column(Numeric(15, 2), default=0)

    available_qty = Column(Numeric(15, 2), default=0)

    shortage_qty = Column(Numeric(15, 2), default=0)

    shortage_details = Column(Text, comment="JSON 数组")

    checked_at = Column(DateTime)

    remarks = Column(Text)



class Resource(BaseModel):
    """设备资源"""
    __tablename__ = "resources"

    resource_id = Column(String(50), nullable=False, unique=True, index=True, comment="资源编码")

    resource_name = Column(String(200))

    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), index=True)

    resource_type = Column(String(50), default="MACHINE")

    capacity_per_shift = Column(Numeric(10, 2), default=10)

    shift_start = Column(String(10), default="08:00")

    shift_end = Column(String(10), default="20:00")

    workdays = Column(String(50), default="1,2,3,4,5,6")

    status = Column(SQLEnum(ResourceStatus), index=True, default=ResourceStatus.ACTIVE)

    skill_tags = Column(Text, comment="JSON 数组，能力标签")

    notes = Column(Text)



class SkillMatrix(BaseModel):
    """人员技能矩阵"""
    __tablename__ = "skill_matrices"

    skill_id = Column(String(50), nullable=False, unique=True, index=True)

    resource_id = Column(String(50), ForeignKey("resources.resource_id"), nullable=False, index=True)

    skill_code = Column(String(50), nullable=False, index=True)

    skill_name = Column(String(200))

    proficiency = Column(Numeric(5, 2), default=1)

    status = Column(String(20), default="ACTIVE")



class ChangeoverMatrix(BaseModel):
    """换产矩阵"""
    __tablename__ = "changeover_matrices"

    changeover_id = Column(String(50), nullable=False, unique=True, index=True)

    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), index=True)

    from_operation = Column(String(50))

    to_operation = Column(String(50))

    changeover_minutes = Column(Numeric(10, 2), default=0)

    status = Column(String(20), default="ACTIVE")



class ScheduleRun(BaseModel):
    """排程运算批次"""
    __tablename__ = "schedule_runs"

    run_number = Column(String(50), nullable=False, unique=True, index=True)

    run_name = Column(String(200))

    algorithm = Column(SQLEnum(ScheduleAlgorithm), default=ScheduleAlgorithm.FORWARD)

    status = Column(SQLEnum(ScheduleRunStatus), index=True, default=ScheduleRunStatus.DRAFT)

    horizon_start = Column(DateTime, nullable=False)

    horizon_end = Column(DateTime, nullable=False)

    source_type = Column(String(30), default="PRODUCTION_ORDER")

    generated_by = Column(String(50))

    generated_at = Column(DateTime)

    published_at = Column(DateTime)

    operation_count = Column(Integer, default=0)

    exception_count = Column(Integer, default=0)

    notes = Column(Text)



class ScheduledOperation(BaseModel):
    """排程工序"""
    __tablename__ = "scheduled_operations"

    op_id = Column(String(50), nullable=False, unique=True, index=True)

    run_number = Column(String(50), ForeignKey("schedule_runs.run_number"), nullable=False, index=True)

    production_order_number = Column(String(50), ForeignKey("production_orders.order_number"), index=True)

    planned_order_number = Column(String(50), index=True)

    material_code = Column(String(50), index=True)

    operation_no = Column(String(20))

    operation_name = Column(String(200))

    work_center_id = Column(String(50), index=True)

    resource_id = Column(String(50), index=True)

    sequence = Column(Integer, default=0)

    planned_qty = Column(Numeric(15, 2), default=0)

    setup_minutes = Column(Numeric(10, 2), default=0)

    run_minutes = Column(Numeric(10, 2), default=0)

    planned_start = Column(DateTime)

    planned_end = Column(DateTime)

    status = Column(SQLEnum(ScheduleOpStatus), index=True, default=ScheduleOpStatus.PLANNED)



class ScheduleException(BaseModel):
    """排程异常"""
    __tablename__ = "schedule_exceptions"

    exception_id = Column(String(50), nullable=False, unique=True, index=True)

    run_number = Column(String(50), ForeignKey("schedule_runs.run_number"), index=True)

    exception_type = Column(SQLEnum(ScheduleExceptionType), index=True)

    production_order_number = Column(String(50), index=True)

    work_center_id = Column(String(50))

    resource_id = Column(String(50))

    severity = Column(String(20), default="WARNING")

    message = Column(Text)

    suggested_action = Column(Text)

    created_at = Column(DateTime)



class ScenarioSimulation(BaseModel):
    """插单模拟场景"""
    __tablename__ = "scenario_simulations"

    scenario_id = Column(String(50), nullable=False, unique=True, index=True)

    run_number = Column(String(50), ForeignKey("schedule_runs.run_number"), index=True)

    scenario_type = Column(SQLEnum(ScenarioType), nullable=False)

    description = Column(Text)

    reference_ref = Column(String(50))

    created_by = Column(String(50))

    created_at = Column(DateTime)

    impact_summary = Column(Text)

    status = Column(String(20), default="DRAFT")



class ScenarioImpact(BaseModel):
    """插单影响明细"""
    __tablename__ = "scenario_impacts"

    impact_id = Column(String(50), nullable=False, unique=True, index=True)

    scenario_id = Column(String(50), ForeignKey("scenario_simulations.scenario_id"), index=True)

    production_order_number = Column(String(50), index=True)

    material_code = Column(String(50))

    affected_days = Column(Numeric(10, 2), default=0)

    original_due_date = Column(DateTime)

    new_due_date = Column(DateTime)

    delay_days = Column(Numeric(10, 2), default=0)

    impact_level = Column(String(20), default="LOW")



class MaintenancePlan(BaseModel):
    """设备维护计划"""
    __tablename__ = "maintenance_plans"

    plan_id = Column(String(50), nullable=False, unique=True, index=True, comment="维护计划编号")

    resource_id = Column(String(50), ForeignKey("resources.resource_id"), nullable=False, index=True, comment="设备资源")

    maintenance_type = Column(SQLEnum(MaintenanceType), default=MaintenanceType.INSPECTION, comment="维护类型（点检/润滑/维修/大保养）")

    cycle_days = Column(Integer, default=30, comment="维护周期（天）")

    last_executed_at = Column(DateTime, comment="上次执行时间")

    next_due_at = Column(DateTime, index=True, comment="下次到期时间")

    responsible = Column(String(50), comment="责任人")

    status = Column(SQLEnum(MaintenanceStatus), index=True, default=MaintenanceStatus.PLANNED)

    notes = Column(Text)



class MaintenanceOrder(BaseModel):
    """维护工单"""
    __tablename__ = "maintenance_orders"

    order_number = Column(String(50), nullable=False, unique=True, index=True)

    resource_id = Column(String(50), ForeignKey("resources.resource_id"), nullable=False, index=True, comment="设备资源")

    plan_id = Column(String(50), ForeignKey("maintenance_plans.plan_id"), index=True, comment="来源维护计划，手工单可为空")

    maintenance_type = Column(SQLEnum(MaintenanceType), default=MaintenanceType.INSPECTION, comment="维护类型")

    planned_date = Column(DateTime, nullable=False, index=True, comment="计划执行日期")

    completed_at = Column(DateTime, comment="完成时间")

    downtime_hours = Column(Numeric(10, 2), default=0, comment="停机时长（小时）")

    executed_by = Column(String(50), comment="执行人")

    result_note = Column(Text, comment="执行结果记录")

    status = Column(SQLEnum(MaintenanceStatus), index=True, default=MaintenanceStatus.PLANNED)



class EquipmentFailure(BaseModel):
    """设备故障记录"""
    __tablename__ = "equipment_failures"

    failure_number = Column(String(50), nullable=False, unique=True, index=True)

    resource_id = Column(String(50), ForeignKey("resources.resource_id"), nullable=False, index=True, comment="设备资源")

    work_center_id = Column(String(50), ForeignKey("work_centers.work_center_id"), index=True, comment="所属工作中心，冗余便于 OEE 汇总")

    occurred_at = Column(DateTime, nullable=False, index=True, comment="故障发生时间")

    resolved_at = Column(DateTime, comment="故障解决时间")

    severity = Column(SQLEnum(FailureSeverity), index=True, default=FailureSeverity.MEDIUM, comment="严重程度")

    description = Column(Text, comment="故障描述")

    root_cause = Column(Text, comment="根本原因")

    action_taken = Column(Text, comment="处置措施")

    downtime_hours = Column(Numeric(10, 2), default=0, comment="停机时长（小时）")

    status = Column(SQLEnum(FailureStatus), index=True, default=FailureStatus.OPEN)

    reported_by = Column(String(50), comment="上报人")



class InspectionOrder(BaseModel):
    """检验单"""
    __tablename__ = "inspection_orders"

    inspection_number = Column(String(50), nullable=False, unique=True, index=True, comment="检验单号")

    inspection_type = Column(SQLEnum(InspectionType), nullable=False, index=True, comment="检验环节（来料/过程/终检）")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="被检物料")

    lot_number = Column(String(50), index=True, comment="关联 LOT 卡（过程/终检）")

    purchase_order_number = Column(String(50), ForeignKey("purchase_orders.purchase_order_number"), index=True, comment="关联采购订单（来料）")

    report_number = Column(String(50), index=True, comment="关联报工单（过程）")

    quantity_inspected = Column(Numeric(15, 2), default=0, comment="检验数量")

    quantity_ok = Column(Numeric(15, 2), default=0, comment="合格数量")

    quantity_rejected = Column(Numeric(15, 2), default=0, comment="不合格数量")

    inspector = Column(String(50), comment="检验员")

    inspected_at = Column(DateTime, index=True, comment="检验时间")

    result = Column(SQLEnum(InspectionResult), index=True, comment="检验结论")

    status = Column(SQLEnum(InspectionStatus), index=True, default=InspectionStatus.DRAFT)

    remarks = Column(Text, comment="备注")



class NonConformanceReport(BaseModel):
    """不合格品记录（NCR）"""
    __tablename__ = "non_conformance_reports"

    ncr_number = Column(String(50), nullable=False, unique=True, index=True, comment="不合格编号")

    source_type = Column(SQLEnum(NcrSourceType), index=True, default=NcrSourceType.INSPECTION, comment="来源类型")

    source_ref = Column(String(100), index=True, comment="来源单据号")

    inspection_number = Column(String(50), ForeignKey("inspection_orders.inspection_number"), index=True, comment="来源检验单（可空）")

    report_number = Column(String(50), index=True, comment="来源报工单（可空）")

    lot_number = Column(String(50), index=True, comment="涉及批次")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="物料")

    quantity = Column(Numeric(15, 2), default=0, comment="不合格数量")

    defect_code = Column(String(50), comment="缺陷代码")

    defect_desc = Column(Text, comment="缺陷描述")

    severity = Column(SQLEnum(NcrSeverity), index=True, default=NcrSeverity.MAJOR, comment="严重程度")

    disposition = Column(SQLEnum(NcrDisposition), index=True, comment="处置方式")

    disposition_note = Column(Text, comment="处置说明")

    root_cause = Column(Text, comment="根本原因")

    equipment_cause = Column(Boolean, default=False, comment="是否判定为设备原因（触发 EAM 联动）")

    failure_number = Column(String(50), index=True, comment="联动生成的 EAM 故障号（可空）")

    status = Column(SQLEnum(NcrStatus), index=True, default=NcrStatus.OPEN)

    reviewed_by = Column(String(50), comment="评审人")

    reviewed_at = Column(DateTime, comment="评审时间")

    closed_by = Column(String(50), comment="关闭人")

    closed_at = Column(DateTime, comment="关闭时间")



class SalesDelivery(BaseModel):
    """发货单"""
    __tablename__ = "sales_deliveries"

    delivery_number = Column(String(50), nullable=False, unique=True, index=True, comment="发货单号(DK 前缀)")

    sales_order_number = Column(String(50), ForeignKey("sales_orders.order_number"), nullable=False, index=True, comment="来源销售订单")

    customer_id = Column(String(50), ForeignKey("customers.customer_id"), index=True, comment="客户编码")

    customer_name = Column(String(200), comment="客户名称")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="物料编码")

    quantity = Column(Numeric(15, 2), nullable=False, comment="发货数量")

    unit = Column(String(20), nullable=False, comment="单位")

    unit_price = Column(Numeric(15, 4), default=0, comment="销售单价")

    status = Column(SQLEnum(DeliveryStatus), index=True, default=DeliveryStatus.DRAFT, comment="发货状态(DRAFT/SHIPPED/DELIVERED/CANCELLED)")

    ship_date = Column(DateTime, comment="发货时间")

    delivery_date = Column(DateTime, comment="签收时间")

    remarks = Column(Text, comment="备注")



class SalesInvoice(BaseModel):
    """销售发票"""
    __tablename__ = "sales_invoices"

    invoice_number = Column(String(50), nullable=False, unique=True, index=True, comment="发票号(INV 前缀)")

    sales_order_number = Column(String(50), ForeignKey("sales_orders.order_number"), nullable=False, index=True, comment="来源销售订单")

    delivery_number = Column(String(50), ForeignKey("sales_deliveries.delivery_number"), index=True, comment="关联发货单(可空)")

    customer_id = Column(String(50), ForeignKey("customers.customer_id"), index=True, comment="客户编码")

    customer_name = Column(String(200), comment="客户名称")

    amount = Column(Numeric(15, 2), nullable=False, comment="开票金额")

    currency = Column(String(10), default="CNY", comment="币种")

    status = Column(SQLEnum(InvoiceStatus), index=True, default=InvoiceStatus.DRAFT, comment="发票状态(DRAFT/ISSUED/PARTIALLY_PAID/PAID/CANCELLED)")

    invoice_date = Column(DateTime, comment="开票日期")

    due_date = Column(DateTime, comment="到期日(按订单交付期或客户条款)")

    received_amount = Column(Numeric(15, 2), default=0, comment="已核销金额(默认0")

    remarks = Column(Text, comment="备注")



class ReceivableEntry(BaseModel):
    """应收流水"""
    __tablename__ = "receivable_entries"

    entry_number = Column(String(50), nullable=False, unique=True, index=True, comment="流水号(AR 前缀)")

    invoice_number = Column(String(50), ForeignKey("sales_invoices.invoice_number"), nullable=False, index=True, comment="关联发票")

    customer_id = Column(String(50), ForeignKey("customers.customer_id"), index=True, comment="客户编码")

    entry_type = Column(SQLEnum(ReceivableEntryType), index=True, default=ReceivableEntryType.INVOICE, comment="流水类型(INVOICE/RECEIPT/ADJUST)")

    amount = Column(Numeric(15, 2), nullable=False, comment="金额(正开票/负收款)")

    entry_date = Column(DateTime, comment="流水日期")

    reference_number = Column(String(50), index=True, comment="参考单号(如收款单号)")

    remarks = Column(Text, comment="备注")



class SupplierInvoice(BaseModel):
    """采购发票"""
    __tablename__ = "supplier_invoices"

    invoice_number = Column(String(50), nullable=False, unique=True, index=True, comment="发票号(PI 前缀)")

    purchase_order_number = Column(String(50), ForeignKey("purchase_orders.purchase_order_number"), nullable=False, index=True, comment="来源采购单")

    supplier_id = Column(String(50), index=True, comment="供应商编码")

    supplier_name = Column(String(200), comment="供应商名称")

    amount = Column(Numeric(15, 2), nullable=False, comment="发票金额(含税)")

    tax_amount = Column(Numeric(15, 2), default=0, comment="税额")

    status = Column(SQLEnum(SupplierInvoiceStatus), index=True, default=SupplierInvoiceStatus.DRAFT, comment="发票状态(DRAFT/CONFIRMED/CANCELLED)")

    invoice_date = Column(DateTime, comment="开票日期")

    remarks = Column(Text, comment="备注")



class SupplierPayment(BaseModel):
    """付款单"""
    __tablename__ = "supplier_payments"

    payment_number = Column(String(50), nullable=False, unique=True, index=True, comment="付款单号(PAY 前缀)")

    supplier_id = Column(String(50), index=True, comment="供应商编码")

    supplier_name = Column(String(200), comment="供应商名称")

    amount = Column(Numeric(15, 2), nullable=False, comment="付款金额")

    payment_date = Column(DateTime, comment="付款日期")

    method = Column(SQLEnum(PaymentMethod), index=True, default=PaymentMethod.TRANSFER, comment="付款方式(TRANSFER/CASH/BILL)")

    status = Column(String(20), index=True, default="DRAFT", comment="单据状态(DRAFT/PAID/CANCELLED)")

    remarks = Column(Text, comment="备注")



class PaymentAllocation(BaseModel):
    """付款核销明细"""
    __tablename__ = "payment_allocations"

    payment_number = Column(String(50), ForeignKey("supplier_payments.payment_number"), nullable=False, index=True, comment="所属付款单")

    invoice_number = Column(String(50), ForeignKey("supplier_invoices.invoice_number"), nullable=False, index=True, comment="核销采购发票")

    allocated_amount = Column(Numeric(15, 2), nullable=False, comment="核销金额")

    remarks = Column(Text, comment="备注")



class Receipt(BaseModel):
    """收款单"""
    __tablename__ = "receipts"

    receipt_number = Column(String(50), nullable=False, unique=True, index=True, comment="收款单号(RC 前缀)")

    customer_id = Column(String(50), ForeignKey("customers.customer_id"), index=True, comment="客户编码")

    customer_name = Column(String(200), comment="客户名称")

    amount = Column(Numeric(15, 2), nullable=False, comment="收款金额")

    receipt_date = Column(DateTime, comment="收款日期")

    method = Column(SQLEnum(PaymentMethod), index=True, default=PaymentMethod.TRANSFER, comment="收款方式(TRANSFER/CASH/BILL)")

    status = Column(String(20), index=True, default="DRAFT", comment="单据状态(DRAFT/PAID/CANCELLED)")

    remarks = Column(Text, comment="备注")



class ReceiptAllocation(BaseModel):
    """收款核销明细"""
    __tablename__ = "receipt_allocations"

    receipt_number = Column(String(50), ForeignKey("receipts.receipt_number"), nullable=False, index=True, comment="所属收款单")

    invoice_number = Column(String(50), ForeignKey("sales_invoices.invoice_number"), nullable=False, index=True, comment="核销销售发票")

    allocated_amount = Column(Numeric(15, 2), nullable=False, comment="核销金额")

    remarks = Column(Text, comment="备注")



class Account(BaseModel):
    """会计科目"""
    __tablename__ = "gl_accounts"

    account_code = Column(String(20), nullable=False, unique=True, index=True, comment="科目编码(如 1122)")

    account_name = Column(String(100), nullable=False, comment="科目名称")

    account_type = Column(SQLEnum(AccountType), nullable=False, index=True, comment="科目类别(ASSET/LIABILITY/EQUITY/REVENUE/EXPENSE)")

    parent_code = Column(String(20), index=True, comment="上级科目编码(可空)")

    is_leaf = Column(Boolean, default=False, comment="是否明细科目(叶子)")



class JournalEntry(BaseModel):
    """记账凭证"""
    __tablename__ = "gl_journal_entries"

    entry_number = Column(String(50), nullable=False, unique=True, index=True, comment="凭证号(JE 前缀)")

    entry_date = Column(DateTime, nullable=False, comment="记账日期")

    period_code = Column(String(7), nullable=False, index=True, comment="会计期间(YYYY-MM)")

    status = Column(SQLEnum(JournalStatus), index=True, default=JournalStatus.DRAFT, comment="凭证状态(DRAFT/POSTED)")

    source_type = Column(SQLEnum(GlSourceType), nullable=False, index=True, comment="业务事件来源")

    source_ref = Column(String(50), nullable=False, index=True, comment="来源单据号")

    remarks = Column(Text, comment="备注")



class JournalLine(BaseModel):
    """分录行"""
    __tablename__ = "gl_journal_lines"

    entry_number = Column(String(50), ForeignKey("gl_journal_entries.entry_number"), nullable=False, index=True, comment="所属凭证")

    line_number = Column(Integer, nullable=False, comment="行号")

    account_code = Column(String(20), ForeignKey("gl_accounts.account_code"), nullable=False, index=True, comment="科目编码")

    debit = Column(Numeric(15, 2), default=0, comment="借方金额")

    credit = Column(Numeric(15, 2), default=0, comment="贷方金额")

    summary = Column(String(200), comment="摘要")



class FiscalPeriod(BaseModel):
    """会计期间"""
    __tablename__ = "gl_fiscal_periods"

    period_code = Column(String(7), nullable=False, unique=True, index=True, comment="期间编码(YYYY-MM)")

    start_date = Column(DateTime, nullable=False, comment="起始日")

    end_date = Column(DateTime, nullable=False, comment="截止日")

    status = Column(SQLEnum(PeriodStatus), index=True, default=PeriodStatus.OPEN, comment="期间状态(OPEN/CLOSED)")



class Warehouse(BaseModel):
    """仓库"""
    __tablename__ = "warehouses"

    warehouse_code = Column(String(50), nullable=False, unique=True, index=True, comment="仓库编码")

    warehouse_name = Column(String(100), nullable=False, comment="仓库名称")

    location = Column(String(200), comment="位置/地址")

    is_active = Column(Boolean, default=True, comment="是否启用")

    remarks = Column(Text, comment="备注")



class Stocktake(BaseModel):
    """盘点单"""
    __tablename__ = "stocktakes"

    stocktake_number = Column(String(50), nullable=False, unique=True, index=True, comment="盘点单号(STK 前缀)")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="盘点物料")

    warehouse = Column(String(50), index=True, comment="盘点仓库(可空，参考字段不迁移)")

    book_qty = Column(Numeric(15, 2), nullable=False, comment="账面数量(创建时快照)")

    counted_qty = Column(Numeric(15, 2), nullable=False, comment="实盘数量")

    diff = Column(Numeric(15, 2), default=0, comment="差异(实盘-账面，创建时计算)")

    status = Column(SQLEnum(StocktakeStatus), index=True, default=StocktakeStatus.DRAFT, comment="盘点状态(DRAFT/APPROVED/CANCELLED)")

    stocktake_date = Column(DateTime, comment="盘点日期")

    remarks = Column(Text, comment="备注")



class StockTransfer(BaseModel):
    """调拨单"""
    __tablename__ = "stock_transfers"

    transfer_number = Column(String(50), nullable=False, unique=True, index=True, comment="调拨单号(TRF 前缀)")

    from_warehouse_code = Column(String(50), nullable=False, index=True, comment="调出仓库")

    to_warehouse_code = Column(String(50), nullable=False, index=True, comment="调入仓库")

    material_code = Column(String(50), ForeignKey("materials.material_code"), nullable=False, index=True, comment="调拨物料")

    quantity = Column(Numeric(15, 2), nullable=False, comment="调拨数量")

    status = Column(SQLEnum(StockTransferStatus), index=True, default=StockTransferStatus.DRAFT, comment="调拨状态(DRAFT/CONFIRMED/CANCELLED)")

    transfer_date = Column(DateTime, comment="调拨日期")

    remarks = Column(Text, comment="备注")

