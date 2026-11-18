/**
 * GENERATED FILE - DO NOT EDIT BY HAND.
 * Source: ontology/model/planning.yaml (version 1.1.0)
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
}

/** 物料计划参数策略 */
export interface PlanningPolicy {
  policy_id: string
  material_code: string
  mrp_type?: MrpType
  procurement_type?: ProcurementType
  lot_sizing_rule?: LotSizingRule
  fixed_lot_size?: number
  min_order_qty?: number
  max_order_qty?: number
  order_multiple?: number
  eoq?: number
  lead_time_days?: number
  safety_time_days?: number
  safety_stock?: number
  reorder_point?: number
  planner_code?: string
  abc_class?: string
  is_active?: boolean
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 需求预测 */
export interface Forecast {
  forecast_number: string
  version?: string
  material_code: string
  customer_id?: string
  quantity: number
  unit: string
  due_date: string
  bucket_type?: string
  status?: string
  consumed_quantity?: number
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 主生产计划 */
export interface MpsPlan {
  mps_number: string
  version?: string
  plan_name?: string
  plant_id?: string
  horizon_start: string
  horizon_end: string
  bucket_type?: string
  status?: string
  demand_source?: string
  total_gross?: number
  total_planned?: number
  generated_by?: string
  generated_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** MPS 计划行 */
export interface MpsEntry {
  mps_number: string
  line_number: number
  material_code: string
  bucket_date: string
  opening_stock?: number
  gross_requirement?: number
  sales_demand?: number
  forecast_demand?: number
  scheduled_receipt?: number
  projected_available?: number
  net_requirement?: number
  planned_receipt?: number
  planner_action?: PlannerAction
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** MRP 运算批次 */
export interface MrpRun {
  run_number: string
  run_type?: MrpRunType
  status?: MrpRunStatus
  horizon_start: string
  horizon_end: string
  demand_source?: string
  mps_number?: string
  plant_id?: string
  total_demands?: number
  total_requirements?: number
  planned_production_count?: number
  planned_purchase_count?: number
  exception_count?: number
  shortage_count?: number
  started_at?: string
  finished_at?: string
  run_by?: string
  log_text?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** MRP 需求行 */
export interface MrpRequirement {
  run_number: string
  line_number: number
  material_code: string
  requirement_level?: number
  demand_type: DemandType
  demand_ref?: string
  parent_planned_order?: string
  quantity: number
  covered_qty?: number
  shortage_qty?: number
  due_date: string
  status?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 计划订单 */
export interface PlannedOrder {
  planned_order_number: string
  run_number?: string
  order_type: PlannedOrderType
  material_code: string
  quantity: number
  unit: string
  start_date: string
  due_date: string
  status?: PlannedOrderStatus
  procurement_type?: string
  supplier_id?: string
  lot_sizing_rule?: string
  lead_time_days?: number
  demand_type?: string
  demand_ref?: string
  parent_planned_order?: string
  conversion_order_number?: string
  confirmed_by?: string
  confirmed_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 需求-供应追溯链 */
export interface PeggingLink {
  run_number?: string
  planned_order_number?: string
  demand_type: DemandType
  demand_ref?: string
  supply_type: SupplyType
  supply_ref?: string
  pegged_qty: number
  pegged_at?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** MRP 异常 */
export interface MrpException {
  run_number?: string
  exception_type: MrpExceptionType
  severity: ExceptionSeverity
  material_code?: string
  requirement_ref?: string
  planned_order_number?: string
  shortage_qty?: number
  shortage_date?: string
  suggestion?: string
  resolution_status?: ResolutionStatus
  resolved_by?: string
  resolved_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 采购订单 */
export interface PurchaseOrder {
  purchase_order_number: string
  supplier_id?: string
  supplier_name?: string
  status?: PurchaseOrderStatus
  order_date?: string
  expected_date?: string
  currency?: string
  total_amount?: number
  source_planned_order?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 采购订单行 */
export interface PurchaseOrderLine {
  purchase_order_number: string
  line_number: number
  material_code: string
  quantity: number
  received_quantity?: number
  unit: string
  unit_price?: number
  expected_date?: string
  status?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 成本费率 */
export interface CostRate {
  rate_id: string
  work_center_id?: string
  rate_type: CostRateType
  rate_per_hour: number
  currency?: string
  effective_from?: string
  effective_to?: string
  status?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 工作中心日历 */
export interface WorkCalendar {
  calendar_id: string
  work_center_id: string
  shift_start?: string
  shift_end?: string
  break_hours?: number
  capacity_hours?: number
  utilization?: number
  workdays?: string
  status?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 标准成本 */
export interface StandardCost {
  cost_id: string
  material_code: string
  version?: string
  cost_date?: string
  material_cost?: number
  labor_cost?: number
  overhead_cost?: number
  total_cost?: number
  unit_cost?: number
  currency?: string
  status?: string
  rolled_up_at?: string
  cost_method?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 工单实际成本归集 */
export interface ProductionCost {
  cost_id: string
  production_order_number: string
  material_code?: string
  quantity?: number
  material_cost_actual?: number
  labor_cost_actual?: number
  overhead_actual?: number
  total_actual?: number
  standard_cost?: number
  wip_value?: number
  status?: CostStatus
  collected_at?: string
  settled_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 成本差异 */
export interface CostVariance {
  variance_number: string
  production_order_number?: string
  variance_type: VarianceType
  standard_amount?: number
  actual_amount?: number
  variance_amount?: number
  variance_pct?: number
  analyzed_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 工单成本结算 */
export interface CostSettlement {
  settlement_number: string
  production_order_number?: string
  total_cost?: number
  wip_value?: number
  settlement_status?: CostStatus
  settled_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 齐套分析结果 */
export interface KittingResult {
  result_number: string
  source_type?: string
  source_ref: string
  material_code?: string
  kit_status?: KitStatus
  required_qty?: number
  available_qty?: number
  shortage_qty?: number
  shortage_details?: string
  checked_at?: string
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 设备资源 */
export interface Resource {
  resource_id: string
  resource_name?: string
  work_center_id?: string
  resource_type?: string
  capacity_per_shift?: number
  shift_start?: string
  shift_end?: string
  workdays?: string
  status?: ResourceStatus
  skill_tags?: string
  notes?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 人员技能矩阵 */
export interface SkillMatrix {
  skill_id: string
  resource_id: string
  skill_code: string
  skill_name?: string
  proficiency?: number
  status?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 换产矩阵 */
export interface ChangeoverMatrix {
  changeover_id: string
  work_center_id?: string
  from_operation?: string
  to_operation?: string
  changeover_minutes?: number
  status?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 排程运算批次 */
export interface ScheduleRun {
  run_number: string
  run_name?: string
  algorithm?: ScheduleAlgorithm
  status?: ScheduleRunStatus
  horizon_start: string
  horizon_end: string
  source_type?: string
  generated_by?: string
  generated_at?: string
  published_at?: string
  operation_count?: number
  exception_count?: number
  notes?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 排程工序 */
export interface ScheduledOperation {
  op_id: string
  run_number: string
  production_order_number?: string
  planned_order_number?: string
  material_code?: string
  operation_no?: string
  operation_name?: string
  work_center_id?: string
  resource_id?: string
  sequence?: number
  planned_qty?: number
  setup_minutes?: number
  run_minutes?: number
  planned_start?: string
  planned_end?: string
  status?: ScheduleOpStatus
  id?: number
  created_at?: string
  updated_at?: string
}

/** 排程异常 */
export interface ScheduleException {
  exception_id: string
  run_number?: string
  exception_type?: ScheduleExceptionType
  production_order_number?: string
  work_center_id?: string
  resource_id?: string
  severity?: string
  message?: string
  suggested_action?: string
  created_at?: string
  id?: number
  updated_at?: string
}

/** 插单模拟场景 */
export interface ScenarioSimulation {
  scenario_id: string
  run_number?: string
  scenario_type: ScenarioType
  description?: string
  reference_ref?: string
  created_by?: string
  created_at?: string
  impact_summary?: string
  status?: string
  id?: number
  updated_at?: string
}

/** 插单影响明细 */
export interface ScenarioImpact {
  impact_id: string
  scenario_id?: string
  production_order_number?: string
  material_code?: string
  affected_days?: number
  original_due_date?: string
  new_due_date?: string
  delay_days?: number
  impact_level?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 设备维护计划 */
export interface MaintenancePlan {
  plan_id: string
  resource_id: string
  maintenance_type?: MaintenanceType
  cycle_days?: number
  last_executed_at?: string
  next_due_at?: string
  responsible?: string
  status?: MaintenanceStatus
  notes?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 维护工单 */
export interface MaintenanceOrder {
  order_number: string
  resource_id: string
  plan_id?: string
  maintenance_type?: MaintenanceType
  planned_date: string
  completed_at?: string
  downtime_hours?: number
  executed_by?: string
  result_note?: string
  status?: MaintenanceStatus
  id?: number
  created_at?: string
  updated_at?: string
}

/** 设备故障记录 */
export interface EquipmentFailure {
  failure_number: string
  resource_id: string
  work_center_id?: string
  occurred_at: string
  resolved_at?: string
  severity?: FailureSeverity
  description?: string
  root_cause?: string
  action_taken?: string
  downtime_hours?: number
  status?: FailureStatus
  reported_by?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 检验单 */
export interface InspectionOrder {
  inspection_number: string
  inspection_type: InspectionType
  material_code: string
  lot_number?: string
  purchase_order_number?: string
  report_number?: string
  quantity_inspected?: number
  quantity_ok?: number
  quantity_rejected?: number
  inspector?: string
  inspected_at?: string
  result?: InspectionResult
  status?: InspectionStatus
  remarks?: string
  id?: number
  created_at?: string
  updated_at?: string
}

/** 不合格品记录（NCR） */
export interface NonConformanceReport {
  ncr_number: string
  source_type?: NcrSourceType
  source_ref?: string
  inspection_number?: string
  report_number?: string
  lot_number?: string
  material_code: string
  quantity?: number
  defect_code?: string
  defect_desc?: string
  severity?: NcrSeverity
  disposition?: NcrDisposition
  disposition_note?: string
  root_cause?: string
  equipment_cause?: boolean
  failure_number?: string
  status?: NcrStatus
  reviewed_by?: string
  reviewed_at?: string
  closed_by?: string
  closed_at?: string
  id?: number
  created_at?: string
  updated_at?: string
}
