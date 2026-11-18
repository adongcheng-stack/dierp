import { Tag } from 'antd'

export const RUN_STATUS: Record<string, { color: string; text: string }> = {
  DRAFT: { color: 'default', text: '草稿' },
  RUNNING: { color: 'processing', text: '运算中' },
  COMPLETED: { color: 'blue', text: '已完成' },
  PUBLISHED: { color: 'green', text: '已发布' },
  FAILED: { color: 'red', text: '失败' },
}

export const ALGORITHM: Record<string, string> = {
  FORWARD: '正排（尽早开工）',
  BACKWARD: '倒排（按交期回推）',
  MIXED: '混合排程',
}

export const SOURCE_TYPE: Record<string, string> = {
  PRODUCTION_ORDER: '生产订单',
  PLANNED_ORDER: '计划订单',
}

export const EXCEPTION_TYPE: Record<string, { color: string; text: string }> = {
  CAPACITY_OVERLOAD: { color: 'orange', text: '产能超载' },
  DUE_DATE_RISK: { color: 'red', text: '交期风险' },
  MATERIAL_SHORTAGE: { color: 'volcano', text: '缺料风险' },
  SKILL_MISMATCH: { color: 'purple', text: '技能不匹配' },
  CHANGEOVER_LIMIT: { color: 'gold', text: '换产超限' },
  RESOURCE_DOWN: { color: 'magenta', text: '资源停机' },
}

export const SCENARIO_TYPE: Record<string, string> = {
  INSERT_ORDER: '紧急插单',
  EQUIPMENT_DOWN: '设备停机',
  MATERIAL_DELAY: '物料延迟',
}

export const IMPACT_LEVEL: Record<string, { color: string; text: string }> = {
  LOW: { color: 'green', text: '低' },
  MEDIUM: { color: 'orange', text: '中' },
  HIGH: { color: 'red', text: '高' },
}

export const RESOURCE_STATUS: Record<string, { color: string; text: string }> = {
  ACTIVE: { color: 'green', text: '可用' },
  MAINTENANCE: { color: 'orange', text: '保养中' },
  DOWN: { color: 'red', text: '停机' },
}

export function StatusTag({ value, map }: { value: string; map: Record<string, { color: string; text: string }> }) {
  const entry = map[value]
  return <Tag color={entry?.color ?? 'default'}>{entry?.text ?? value}</Tag>
}

export function fmtMinutes(value: number | null | undefined): string {
  const number = Number(value ?? 0)
  if (number >= 60) {
    const hours = Math.floor(number / 60)
    const minutes = Math.round(number % 60)
    return minutes ? `${hours}h${minutes}m` : `${hours}h`
  }
  return `${Math.round(number)}m`
}

export function fmtDateTime(value: string | null | undefined): string {
  return value ? value.replace('T', ' ').slice(0, 19) : '-'
}

export function fmtDate(value: string | null | undefined): string {
  return value ? value.slice(0, 10) : '-'
}

/** 把时间映射为时间轴百分比（用于简易甘特条定位） */
export function pct(value: string, rangeStart: number, rangeEnd: number): number {
  const time = new Date(value).getTime()
  if (rangeEnd <= rangeStart) return 0
  return Math.min(100, Math.max(0, ((time - rangeStart) / (rangeEnd - rangeStart)) * 100))
}
