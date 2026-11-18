import { Tag } from 'antd'
import dayjs from 'dayjs'

export const MPS_STATUS: Record<string, { color: string; text: string }> = {
  DRAFT: { color: 'default', text: '草稿' },
  RELEASED: { color: 'green', text: '已下达' },
  CLOSED: { color: 'default', text: '已关闭' },
}

export const RUN_STATUS: Record<string, { color: string; text: string }> = {
  RUNNING: { color: 'processing', text: '运行中' },
  COMPLETED: { color: 'green', text: '已完成' },
  FAILED: { color: 'red', text: '失败' },
}

export const PLANNED_ORDER_STATUS: Record<string, { color: string; text: string }> = {
  PLANNED: { color: 'blue', text: '建议' },
  FIRMED: { color: 'gold', text: '已确认' },
  RELEASED: { color: 'green', text: '已下达' },
  CANCELLED: { color: 'default', text: '已取消' },
}

export const ORDER_TYPE: Record<string, { color: string; text: string }> = {
  PRODUCTION: { color: 'geekblue', text: '自制' },
  PURCHASE: { color: 'orange', text: '采购' },
  TRANSFER: { color: 'purple', text: '调拨' },
}

export const EXCEPTION_TYPE: Record<string, string> = {
  SHORTAGE: '物料短缺',
  EXCESS: '库存过量',
  LATE: '预计延迟',
  EARLY: '预计提前',
  NO_BOM: '缺少BOM',
  NO_POLICY: '缺少计划参数',
  LEAD_TIME_VIOLATION: '提前期违规',
  CAPACITY_OVERLOAD: '产能超负荷',
}

export const SEVERITY: Record<string, { color: string; text: string }> = {
  INFO: { color: 'blue', text: '提示' },
  WARNING: { color: 'orange', text: '警告' },
  CRITICAL: { color: 'red', text: '严重' },
}

export const RESOLUTION: Record<string, { color: string; text: string }> = {
  OPEN: { color: 'red', text: '待处理' },
  ACKNOWLEDGED: { color: 'gold', text: '已确认' },
  RESOLVED: { color: 'green', text: '已解决' },
  IGNORED: { color: 'default', text: '已忽略' },
}

export const KIT_STATUS: Record<string, { color: string; text: string }> = {
  FULL: { color: 'green', text: '齐套' },
  PARTIAL: { color: 'orange', text: '部分缺料' },
  SHORT: { color: 'red', text: '缺料' },
}

export const PLANNER_ACTION: Record<string, { color: string; text: string }> = {
  NONE: { color: 'default', text: '无需动作' },
  RELEASE: { color: 'green', text: '建议下达' },
  EXPEDITE: { color: 'red', text: '建议加急' },
  DELAY: { color: 'gold', text: '建议推迟' },
  CANCEL: { color: 'default', text: '建议取消' },
}

export function StatusTag({
  value,
  map,
  fallback,
}: {
  value?: string | null
  map: Record<string, { color: string; text: string }>
  fallback?: string
}) {
  if (!value) return <span className="text-ink-soft">-</span>
  const info = map[value] ?? { color: 'default', text: fallback ?? value }
  return <Tag color={info.color}>{info.text}</Tag>
}

export function fmtQty(value?: number | null): string {
  if (value === undefined || value === null) return '-'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

export function fmtDate(value?: string | null, pattern = 'YYYY-MM-DD'): string {
  if (!value) return '-'
  const date = dayjs(value)
  return date.isValid() ? date.format(pattern) : value
}
