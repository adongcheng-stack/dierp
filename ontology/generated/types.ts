/**
 * GENERATED FILE - DO NOT EDIT BY HAND.
 * Source: ontology/src/mappings.json (namespace https://dierp.local/ontology/erp/v1#)
 * Regenerate: python ontology/scripts/generate-types.py
 */

export type MaterialType = 'FG' | 'SEMI' | 'RAW' | 'PACKAGING' | 'SERVICE';

export type ProcurementType = 'MAKE' | 'BUY' | 'SUB';

export type MrpType = 'MRP' | 'REORDER_POINT' | 'NONE';

export type DocumentStatus = 'DRAFT' | 'RELEASED' | 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CLOSED' | 'CANCELLED';

export type SalesOrderStatus = 'DRAFT' | 'PENDING_REVIEW' | 'REVIEWING' | 'APPROVED' | 'REJECTED' | 'IN_PRODUCTION' | 'COMPLETED' | 'SHIPPED' | 'DELIVERED' | 'RECONCILED' | 'CLOSED' | 'CANCELLED';

export type MpsPlanStatus = 'DRAFT' | 'RELEASED' | 'CLOSED' | 'CANCELLED';

export type MrpRunType = 'REGENERATIVE' | 'NET_CHANGE';

export type MrpRunStatus = 'RUNNING' | 'COMPLETED' | 'FAILED';

export type PlannedOrderType = 'PRODUCTION' | 'PURCHASE' | 'TRANSFER';

export type PlannedOrderStatus = 'PLANNED' | 'FIRMED' | 'RELEASED' | 'CANCELLED';

export type LotSizingRule = 'LOT_FOR_LOT' | 'FIXED_LOT' | 'MIN_MAX' | 'EOQ' | 'PERIOD_ORDER';

export type PlannerAction = 'NONE' | 'RELEASE' | 'EXPEDITE' | 'DELAY' | 'CANCEL';

export type MrpExceptionType = 'SHORTAGE' | 'EXCESS' | 'LATE' | 'EARLY' | 'NO_BOM' | 'NO_POLICY' | 'LEAD_TIME_VIOLATION' | 'CAPACITY_OVERLOAD';

export type ExceptionSeverity = 'INFO' | 'WARNING' | 'CRITICAL';

export type ResolutionStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'IGNORED';

export type DemandType = 'SALES_ORDER' | 'FORECAST' | 'SAFETY_STOCK' | 'DEPENDENT' | 'MPS';

export type SupplyType = 'ON_HAND' | 'PRODUCTION_ORDER' | 'PURCHASE_ORDER' | 'PLANNED_ORDER';

export type KitStatus = 'FULL' | 'PARTIAL' | 'SHORT';

export type CostRateType = 'LABOR' | 'MACHINE' | 'OVERHEAD';

export type VarianceType = 'MATERIAL_PRICE' | 'MATERIAL_USAGE' | 'LABOR_RATE' | 'LABOR_EFFICIENCY' | 'OVERHEAD';

export type CostStatus = 'OPEN' | 'COLLECTED' | 'SETTLED';

export type PurchaseOrderStatus = 'DRAFT' | 'RELEASED' | 'PARTIALLY_RECEIVED' | 'RECEIVED' | 'CLOSED' | 'CANCELLED';

export type PurchaseRequestStatus = 'DRAFT' | 'RELEASED' | 'PARTIALLY_CONVERTED' | 'CONVERTED' | 'CANCELLED';

export type ReturnType = 'RETURN' | 'CLAIM';

export type ReturnStatus = 'DRAFT' | 'APPROVED' | 'REJECTED' | 'CLOSED';

export type SupplierStatus = 'ACTIVE' | 'INACTIVE';

export type DeliveryStatus = 'DRAFT' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';

export type InvoiceStatus = 'DRAFT' | 'ISSUED' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';

export type ReceivableEntryType = 'INVOICE' | 'RECEIPT' | 'ADJUST' | 'RECEIPT_REVERSE' | 'INVOICE_REVERSE';

export type SupplierInvoiceStatus = 'DRAFT' | 'CONFIRMED' | 'CANCELLED';

export type PaymentMethod = 'TRANSFER' | 'CASH' | 'BILL';

export type AccountType = 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE';

export type JournalStatus = 'DRAFT' | 'POSTED';

export type PeriodStatus = 'OPEN' | 'CLOSED';

export type ValuationDirection = 'IN' | 'OUT';

export type CostSourceType = 'PURCHASE_RECEIPT' | 'PURCHASE_RETURN' | 'PRODUCTION_COMPLETE' | 'MATERIAL_ISSUE' | 'SALES_ISSUE' | 'SALES_RETURN' | 'STOCKTAKE' | 'OPENING' | 'TRANSFER';

export type GlSourceType = 'SALES_INVOICE_ISSUED' | 'SALES_INVOICE_REVERSED' | 'SALES_DELIVERY_SHIPPED' | 'SUPPLIER_INVOICE_CONFIRMED' | 'SUPPLIER_PAYMENT_PAID' | 'RECEIPT_PAID' | 'RECEIPT_PAID_REVERSE' | 'MATERIAL_ISSUE' | 'STOCK_ADJUST' | 'PRODUCTION_COMPLETE' | 'PERIOD_CLOSE' | 'OPENING' | 'COST_VARIANCE';

export type StocktakeStatus = 'DRAFT' | 'APPROVED' | 'CANCELLED';

export type StockTransferStatus = 'DRAFT' | 'CONFIRMED' | 'CANCELLED';

export type ResourceStatus = 'ACTIVE' | 'MAINTENANCE' | 'DOWN';

export type ScheduleRunStatus = 'DRAFT' | 'RUNNING' | 'COMPLETED' | 'PUBLISHED' | 'FAILED';

export type ScheduleAlgorithm = 'FORWARD' | 'BACKWARD' | 'MIXED';

export type ScheduleOpStatus = 'PLANNED' | 'LOCKED' | 'PUBLISHED' | 'CANCELLED';

export type ScheduleExceptionType = 'CAPACITY_OVERLOAD' | 'DUE_DATE_RISK' | 'MATERIAL_SHORTAGE' | 'SKILL_MISMATCH' | 'CHANGEOVER_LIMIT' | 'RESOURCE_DOWN';

export type ScenarioType = 'INSERT_ORDER' | 'EQUIPMENT_DOWN' | 'MATERIAL_DELAY';

export type MaintenanceType = 'INSPECTION' | 'LUBRICANT' | 'REPAIR' | 'OVERHAUL';

export type MaintenanceStatus = 'PLANNED' | 'IN_PROGRESS' | 'DONE' | 'CANCELLED';

export type FailureStatus = 'OPEN' | 'PROCESSING' | 'CLOSED';

export type FailureSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type InspectionType = 'INCOMING' | 'IN_PROCESS' | 'FINAL';

export type InspectionResult = 'PASS' | 'FAIL' | 'HOLD';

export type InspectionStatus = 'DRAFT' | 'COMPLETED' | 'CANCELLED';

export type NcrSourceType = 'INSPECTION' | 'REPORT' | 'LOT_CARD' | 'MANUAL';

export type NcrSeverity = 'MINOR' | 'MAJOR' | 'CRITICAL';

export type NcrDisposition = 'REWORK' | 'SCRAP' | 'USE_AS_IS' | 'RETURN' | 'REVIEW';

export type NcrStatus = 'OPEN' | 'UNDER_REVIEW' | 'DISPOSITIONED' | 'CLOSED';

export type UserRole = 'SALES' | 'SALES_MANAGER' | 'ENGINEER' | 'PLANNER' | 'PRODUCTION' | 'WAREHOUSE' | 'FINANCE' | 'GENERAL_MANAGER' | 'ADMIN';

export type AccessDomain = 'sd' | 'eng' | 'pp' | 'mm' | 'planning' | 'qms' | 'purchase' | 'finance' | 'users' | 'admin' | 'system' | 'auth' | 'dashboard' | 'traceability' | 'ai';

export type HttpWriteMethod = 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type DepartmentStatus = 'ACTIVE' | 'INACTIVE';

export type DepartmentType = 'COMPANY' | 'DIVISION' | 'DEPARTMENT' | 'TEAM' | 'WORKSHOP';

export type MenuType = 'DIRECTORY' | 'MENU' | 'BUTTON';

export type MenuStatus = 'ACTIVE' | 'INACTIVE';

export type ParamType = 'STRING' | 'INT' | 'BOOLEAN' | 'JSON';

export type LoginStatus = 'SUCCESS' | 'FAIL';

export type DashboardScope = 'HOME' | 'MANAGEMENT' | 'PRODUCTION' | 'PROGRESS' | 'FINANCE' | 'SALES';

export type AlertOperator = 'LT' | 'LTE' | 'GT' | 'GTE';

export type AlertLevel = 'INFO' | 'WARNING' | 'CRITICAL';

export type TimeWindow = 'ALL' | 'LAST30' | 'LAST90' | 'LAST365';

export type MesWorkOrderStatus = 'DRAFT' | 'SUBMITTED' | 'IN_PRODUCTION' | 'PAUSED' | 'COMPLETED' | 'CLOSED';

export type MesProcessTaskStatus = 'PENDING' | 'COMPLETED';

export type AiQueryStatus = 'OK' | 'REJECTED_PERMISSION' | 'REJECTED_TIMEOUT' | 'REJECTED_RATE_LIMIT' | 'REJECTED_TOO_BROAD' | 'REJECTED_SCHEMA' | 'REJECTED_INTENT' | 'REJECTED_SHACL' | 'REJECTED_PARAM' | 'FAILED';

export type AiShaclStatus = 'passed' | 'partial' | 'skipped' | 'failed';

export const ENUM_LABELS = {
  MaterialType: {
    FG: '产成品',
    SEMI: '半成品',
    RAW: '原材料',
    PACKAGING: '包装物',
    SERVICE: '服务',
  },
  MrpExceptionType: {
    SHORTAGE: '物料短缺',
    EXCESS: '物料过剩',
    LATE: '交期延迟',
    EARLY: '交期提前',
    NO_BOM: '缺少物料清单',
    NO_POLICY: '缺少计划策略',
    LEAD_TIME_VIOLATION: '提前期违约',
    CAPACITY_OVERLOAD: '产能超载',
  },
  ExceptionSeverity: {
    INFO: '提示',
    WARNING: '警告',
    CRITICAL: '严重',
  },
  ResolutionStatus: {
    OPEN: '未处理',
    ACKNOWLEDGED: '已确认',
    RESOLVED: '已解决',
    IGNORED: '已忽略',
  },
  KitStatus: {
    FULL: '齐套',
    PARTIAL: '部分齐套',
    SHORT: '缺料',
  },
  NcrSeverity: {
    MINOR: '轻微',
    MAJOR: '主要',
    CRITICAL: '严重',
  },
  NcrStatus: {
    OPEN: '未关闭',
    UNDER_REVIEW: '评审中',
    DISPOSITIONED: '已处置',
    CLOSED: '已关闭',
  },
  NcrDisposition: {
    REWORK: '返工',
    SCRAP: '报废',
    USE_AS_IS: '让步接收',
    RETURN: '退货',
    REVIEW: '待评审',
  },
  InvoiceStatus: {
    DRAFT: '草稿',
    ISSUED: '已开具',
    PARTIALLY_PAID: '部分收款',
    PAID: '已收款',
    CANCELLED: '已作废',
  },
  SalesOrderStatus: {
    DRAFT: '草稿',
    PENDING_REVIEW: '待评审',
    REVIEWING: '评审中',
    APPROVED: '已批准',
    REJECTED: '已驳回',
    IN_PRODUCTION: '生产中',
    COMPLETED: '已完工',
    SHIPPED: '已发货',
    DELIVERED: '已交付',
    RECONCILED: '已对账',
    CLOSED: '已关闭',
    CANCELLED: '已取消',
  },
  VarianceType: {
    MATERIAL_PRICE: '材料价差',
    MATERIAL_USAGE: '材料量差',
    LABOR_RATE: '人工费率差异',
    LABOR_EFFICIENCY: '人工效率差异',
    OVERHEAD: '制造费用差异',
  },
  MesWorkOrderStatus: {
    DRAFT: '草稿',
    SUBMITTED: '已提交',
    IN_PRODUCTION: '生产中',
    PAUSED: '已暂停',
    COMPLETED: '已完工',
    CLOSED: '已关闭',
  },
  MesProcessTaskStatus: {
    PENDING: '待开工',
    COMPLETED: '已完成',
  },
} as const;
