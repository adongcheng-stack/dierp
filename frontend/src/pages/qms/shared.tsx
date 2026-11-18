import { Tag } from 'antd'

/** 检验环节映射（与 mappings.json InspectionType 一致） */
export const INSPECTION_TYPE: Record<string, { color: string; text: string }> = {
  INCOMING: { color: 'blue', text: '来料检验' },
  IN_PROCESS: { color: 'orange', text: '过程检验' },
  FINAL: { color: 'purple', text: '终检' },
}

/** 检验结论映射（与 mappings.json InspectionResult 一致） */
export const INSPECTION_RESULT: Record<string, { color: string; text: string }> = {
  PASS: { color: 'green', text: '合格' },
  FAIL: { color: 'red', text: '不合格' },
  HOLD: { color: 'gold', text: '待定' },
}

/** 检验单状态映射（与 mappings.json InspectionStatus 一致） */
export const INSPECTION_STATUS: Record<string, { color: string; text: string }> = {
  DRAFT: { color: 'default', text: '草稿' },
  COMPLETED: { color: 'green', text: '已完成' },
  CANCELLED: { color: 'default', text: '已取消' },
}

/** 不合格来源映射（与 mappings.json NcrSourceType 一致） */
export const NCR_SOURCE: Record<string, { color: string; text: string }> = {
  INSPECTION: { color: 'blue', text: '检验单' },
  REPORT: { color: 'cyan', text: '报工单' },
  LOT_CARD: { color: 'orange', text: 'LOT卡' },
  MANUAL: { color: 'default', text: '手工' },
}

/** 不合格严重程度映射（与 mappings.json NcrSeverity 一致） */
export const NCR_SEVERITY: Record<string, { color: string; text: string }> = {
  MINOR: { color: 'green', text: '轻微' },
  MAJOR: { color: 'orange', text: '一般' },
  CRITICAL: { color: 'red', text: '严重' },
}

/** 不合格处置方式映射（与 mappings.json NcrDisposition 一致） */
export const NCR_DISPOSITION: Record<string, { color: string; text: string }> = {
  REWORK: { color: 'blue', text: '返工' },
  SCRAP: { color: 'red', text: '报废' },
  USE_AS_IS: { color: 'gold', text: '让步接收' },
  RETURN: { color: 'purple', text: '退货' },
  REVIEW: { color: 'orange', text: '评审/待修' },
}

/** 不合格状态映射（与 mappings.json NcrStatus 一致） */
export const NCR_STATUS: Record<string, { color: string; text: string }> = {
  OPEN: { color: 'red', text: '待处理' },
  UNDER_REVIEW: { color: 'orange', text: '评审中' },
  DISPOSITIONED: { color: 'gold', text: '已处置' },
  CLOSED: { color: 'green', text: '已关闭' },
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

/** 物料名映射缓存（列表页传 Material 列表进来渲染） */
export function materialName(materialCode: string | undefined, materials: any[]): string {
  if (!materialCode) return '-'
  const mat = materials.find((m) => m.material_code === materialCode)
  return mat?.material_name || materialCode
}