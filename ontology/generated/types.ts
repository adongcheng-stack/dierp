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
