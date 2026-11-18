import { Tag } from 'antd'

export const COST_STATUS: Record<string, { color: string; text: string }> = {
  OPEN: { color: 'default', text: '待归集' },
  COLLECTED: { color: 'blue', text: '已归集' },
  SETTLED: { color: 'green', text: '已结算' },
}

export const VARIANCE_TYPE: Record<string, string> = {
  MATERIAL_PRICE: '材料价格差异',
  MATERIAL_USAGE: '材料用量差异',
  LABOR_RATE: '人工费率差异',
  LABOR_EFFICIENCY: '人工效率差异',
  OVERHEAD: '制造费用差异',
}

export const RATE_TYPE: Record<string, string> = {
  LABOR: '人工费率',
  MACHINE: '设备费率',
  OVERHEAD: '制造费用',
}

export function StatusTag({ value, map }: { value: string; map: Record<string, { color: string; text: string }> }) {
  const entry = map[value]
  return <Tag color={entry?.color ?? 'default'}>{entry?.text ?? value}</Tag>
}

export function fmtMoney(value: number | null | undefined): string {
  const number = Number(value ?? 0)
  return number.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function fmtQty(value: number | null | undefined): string {
  return String(Number(value ?? 0).toFixed(2))
}