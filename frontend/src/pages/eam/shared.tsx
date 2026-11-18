import { Tag } from 'antd'

/** 维护类型映射（与 mappings.json MaintenanceType 一致） */
export const MAINTENANCE_TYPE: Record<string, { color: string; text: string }> = {
  INSPECTION: { color: 'blue', text: '点检' },
  LUBRICANT: { color: 'cyan', text: '润滑' },
  REPAIR: { color: 'orange', text: '维修' },
  OVERHAUL: { color: 'purple', text: '大保养' },
}

/** 维护计划/工单状态映射（与 mappings.json MaintenanceStatus 一致） */
export const MAINTENANCE_STATUS: Record<string, { color: string; text: string }> = {
  PLANNED: { color: 'default', text: '计划中' },
  IN_PROGRESS: { color: 'processing', text: '执行中' },
  DONE: { color: 'green', text: '已完成' },
  CANCELLED: { color: 'default', text: '已取消' },
}

/** 故障状态映射（与 mappings.json FailureStatus 一致） */
export const FAILURE_STATUS: Record<string, { color: string; text: string }> = {
  OPEN: { color: 'red', text: '待处理' },
  PROCESSING: { color: 'orange', text: '处理中' },
  CLOSED: { color: 'green', text: '已关闭' },
}

/** 故障严重程度映射（与 mappings.json FailureSeverity 一致） */
export const FAILURE_SEVERITY: Record<string, { color: string; text: string }> = {
  LOW: { color: 'green', text: '低' },
  MEDIUM: { color: 'gold', text: '中' },
  HIGH: { color: 'orange', text: '高' },
  CRITICAL: { color: 'red', text: '严重' },
}

export function StatusTag({ value, map }: { value: string; map: Record<string, { color: string; text: string }> }) {
  const entry = map[value]
  return <Tag color={entry?.color ?? 'default'}>{entry?.text ?? value}</Tag>
}

export function fmtDateTime(value: string | null | undefined): string {
  return value ? value.replace('T', ' ').slice(0, 19) : '-'
}

export function fmtDate(value: string | null | undefined): string {
  return value ? value.slice(0, 10) : '-'
}

/** OEE 百分比展示（0.8472 -> 84.7%） */
export function fmtPct(value: number | null | undefined, digits = 1): string {
  const number = Number(value ?? 0) * 100
  return `${number.toFixed(digits)}%`
}

/** OEE 率值配色：>=85% 绿 / >=60% 橙 / 其余红 */
export function oeeColor(value: number | null | undefined): string {
  const pct = Number(value ?? 0) * 100
  if (pct >= 85) return '#389e0d'
  if (pct >= 60) return '#d46b08'
  return '#cf1322'
}
