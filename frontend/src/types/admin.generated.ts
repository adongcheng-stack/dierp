/**
 * GENERATED FILE - DO NOT EDIT BY HAND.
 * Source: ontology/model/admin.yaml (version 1.0.0)
 * Regenerate: python backend/ontology/generate_models.py
 */

/* eslint-disable */

import type {
  MaterialType,
  ProcurementType,
  MrpType,
  DocumentStatus,
  SalesOrderStatus,
  MpsPlanStatus,
  MrpRunType,
  MrpRunStatus,
  PlannedOrderType,
  PlannedOrderStatus,
  LotSizingRule,
  PlannerAction,
  MrpExceptionType,
  ExceptionSeverity,
  ResolutionStatus,
  DemandType,
  SupplyType,
  KitStatus,
  CostRateType,
  VarianceType,
  CostStatus,
  PurchaseOrderStatus,
  PurchaseRequestStatus,
  ReturnType,
  ReturnStatus,
  SupplierStatus,
  DeliveryStatus,
  InvoiceStatus,
  ReceivableEntryType,
  SupplierInvoiceStatus,
  PaymentMethod,
  AccountType,
  JournalStatus,
  PeriodStatus,
  ValuationDirection,
  CostSourceType,
  GlSourceType,
  StocktakeStatus,
  StockTransferStatus,
  ResourceStatus,
  ScheduleRunStatus,
  ScheduleAlgorithm,
  ScheduleOpStatus,
  ScheduleExceptionType,
  ScenarioType,
  MaintenanceType,
  MaintenanceStatus,
  FailureStatus,
  FailureSeverity,
  InspectionType,
  InspectionResult,
  InspectionStatus,
  NcrSourceType,
  NcrSeverity,
  NcrDisposition,
  NcrStatus,
  UserRole,
  AccessDomain,
  HttpWriteMethod,
  DepartmentStatus,
  DepartmentType,
  MenuType,
  MenuStatus,
  ParamType,
  LoginStatus,
  DashboardScope,
  AlertOperator,
  AlertLevel,
  TimeWindow,
  MesWorkOrderStatus,
  MesProcessTaskStatus,
} from '../../../ontology/generated/types'

export type {
  MaterialType,
  ProcurementType,
  MrpType,
  DocumentStatus,
  SalesOrderStatus,
  MpsPlanStatus,
  MrpRunType,
  MrpRunStatus,
  PlannedOrderType,
  PlannedOrderStatus,
  LotSizingRule,
  PlannerAction,
  MrpExceptionType,
  ExceptionSeverity,
  ResolutionStatus,
  DemandType,
  SupplyType,
  KitStatus,
  CostRateType,
  VarianceType,
  CostStatus,
  PurchaseOrderStatus,
  PurchaseRequestStatus,
  ReturnType,
  ReturnStatus,
  SupplierStatus,
  DeliveryStatus,
  InvoiceStatus,
  ReceivableEntryType,
  SupplierInvoiceStatus,
  PaymentMethod,
  AccountType,
  JournalStatus,
  PeriodStatus,
  ValuationDirection,
  CostSourceType,
  GlSourceType,
  StocktakeStatus,
  StockTransferStatus,
  ResourceStatus,
  ScheduleRunStatus,
  ScheduleAlgorithm,
  ScheduleOpStatus,
  ScheduleExceptionType,
  ScenarioType,
  MaintenanceType,
  MaintenanceStatus,
  FailureStatus,
  FailureSeverity,
  InspectionType,
  InspectionResult,
  InspectionStatus,
  NcrSourceType,
  NcrSeverity,
  NcrDisposition,
  NcrStatus,
  UserRole,
  AccessDomain,
  HttpWriteMethod,
  DepartmentStatus,
  DepartmentType,
  MenuType,
  MenuStatus,
  ParamType,
  LoginStatus,
  DashboardScope,
  AlertOperator,
  AlertLevel,
  TimeWindow,
  MesWorkOrderStatus,
  MesProcessTaskStatus,
}

/** 部门（组织架构树节点） */
export interface Department {
  code: string
  name: string
  parent_id?: number
  level?: number
  department_type?: DepartmentType
  manager?: string
  contact_phone?: string
  sort_order?: number
  status?: DepartmentStatus
  established_date?: string
  remark?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 系统菜单（路由与按钮权限声明） */
export interface Menu {
  code: string
  name: string
  parent_id?: number
  path?: string
  component?: string
  icon?: string
  menu_type?: MenuType
  permission?: string
  sort_order?: number
  visible?: boolean
  status?: MenuStatus
  id?: number
  created_at?: string
  updated_at?: string
}

/** 角色-菜单授权 */
export interface RoleMenu {
  role_code: UserRole
  menu_id: number
  id?: number
  created_at?: string
  updated_at?: string
}

/** 系统参数 */
export interface SystemParameter {
  param_key: string
  param_name: string
  param_value?: string
  param_type?: ParamType
  param_desc?: string
  is_system?: boolean
  remark?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 登录日志 */
export interface LoginLog {
  username: string
  role?: string
  login_status: LoginStatus
  message?: string
  ip_address?: string
  user_agent?: string
  login_time: string
  id?: number
  created_at?: string
  updated_at?: string
}
