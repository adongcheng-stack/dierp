/** 与后端保持一致的编号规则：QT-YYYYMMDD-0001 / SO-… / PO-… / LOT-… / MI-… / OR-… */

export function nowIso(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  )
}

export function todayDatePart(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`
}

export function nextId(items: any[]): number {
  return items.reduce((max, item) => Math.max(max, Number(item?.id) || 0), 0) + 1
}

/** 安全解码 URL 路径参数：非法编码时回落原值 */
export function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

/**
 * 生成业务编号。相同前缀 + 当天日期共用一套序号，
 * 只匹配「PREFIX-YYYYMMDD-数字」的形式，避免和 MI-HF1004… 这类编号冲突。
 */
export function nextNumber(items: any[], field: string, prefix: string): string {
  const datePart = todayDatePart()
  const pattern = new RegExp(`^${prefix}-${datePart}-(\\d+)$`)
  let max = 0
  for (const item of items) {
    const matched = pattern.exec(String(item?.[field] ?? ''))
    if (matched) max = Math.max(max, Number(matched[1]))
  }
  return `${prefix}-${datePart}-${String(max + 1).padStart(4, '0')}`
}

export function round(value: number, digits = 2): number {
  if (!Number.isFinite(value)) return 0
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

export function toNumber(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

/** 按查询参数过滤列表（只处理明确的字段） */
export function applyEquals(items: any[], query: Record<string, any>, fields: string[]): any[] {
  let result = items
  for (const field of fields) {
    const value = query[field]
    if (value === undefined || value === null || value === '') continue
    result = result.filter((item) => String(item?.[field]) === String(value))
  }
  return result
}

export function paginate(items: any[], query: Record<string, any>): any[] {
  const skip = Math.max(0, Number(query.skip ?? 0) || 0)
  const hasLimit = query.limit !== undefined && query.limit !== null && query.limit !== ''
  const limit = hasLimit ? Math.max(0, Number(query.limit)) : items.length
  return items.slice(skip, skip + limit)
}

export function searchText(items: any[], query: Record<string, any>, fields: string[]): any[] {
  const keyword = String(query.search ?? query.keyword ?? '').trim().toLowerCase()
  if (!keyword) return items
  return items.filter((item) =>
    fields.some((field) => String(item?.[field] ?? '').toLowerCase().includes(keyword))
  )
}
