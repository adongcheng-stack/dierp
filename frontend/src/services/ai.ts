import api from './api'

/** AI 问答对外契约（与 backend/api/routers/ai.py + pipeline.ask 返回结构一致）。 */
export interface AiIntentPayload {
  code: string
  label: string
  params: Record<string, unknown>
}

export interface AiProvenance {
  table: string
  record_ref: string
  ontology_class: string
  source_system?: 'ERP' | 'MES' | string
}

export interface AiLimits {
  row_count: number
  truncated: boolean
  shacl: string | null
  coverage: string
  timeout_seconds: number
  max_rows: number
  elapsed_ms: number
}

export interface AiChatResponse {
  trace_id: string
  request_id?: string | null
  intent: AiIntentPayload
  answer: string
  data: {
    columns: string[]
    rows: Record<string, unknown>[]
    row_count: number
    reason?: string | null
  }
  provenance: AiProvenance[]
  limits: AiLimits
  model: string
}

export interface AiErrorDetail {
  code: string
  message: string
  trace_id?: string | null
}

export interface AiQueryLogItem {
  trace_id: string
  request_id?: string | null
  username?: string | null
  role?: string | null
  question?: string | null
  intent_code?: string | null
  intent?: Record<string, unknown> | null
  status: string
  error_code?: string | null
  shacl_status?: string | null
  row_count?: number | null
  latency_ms?: number | null
  model?: string | null
  provenance?: unknown
  feedback_score?: number | null
  feedback_comment?: string | null
  created_at?: string | null
}

export interface AiQueryPage {
  items: AiQueryLogItem[]
  total: number
  page: number
  page_size: number
}

/** A4 异常解读：与 backend/services/ai/insights.py 返回结构一致。 */
export interface AiInsightEvidence {
  table: string
  record_ref: string
  label: string
}

export interface AiInsightAlert {
  code: string
  title: string
  severity: 'CRITICAL' | 'WARNING' | 'INFO' | string
  scope: string
  metric: string
  value_kind: 'ratio' | 'amount' | 'count' | 'qty' | string
  current_value: number | null
  threshold: number | null
  operator: string
  deviation: number | null
  deviation_text: string
  evidence: AiInsightEvidence[]
  evidence_total: number
  drilldown: string | null
  attribution: string
  suggestion: string
  amount_masked: boolean
}

export interface AiInsightsSummary {
  total: number
  critical: number
  warning: number
  info: number
  truncated: boolean
}

export interface AiInsightsResponse {
  window: string
  generated_at: string
  summary: AiInsightsSummary
  alerts: AiInsightAlert[]
  narrative: string
  narration_source: 'template' | 'llm' | string
  model: string
}

export const ERROR_TEXT: Record<string, string> = {
  AI_DISABLED: 'AI 功能已关闭，请联系管理员开启 AI_ENABLED。',
  AI_CHATBI_DISABLED: 'AI 问答已关闭（本体检索仍可用）。',
  AI_INTENT_UNKNOWN: '无法识别该问题对应的查询意图，请换一种问法。',
  AI_PARAM_INVALID: '查询参数不合法，请检查问题中的条件。',
  AI_PERMISSION_DENIED: '当前角色无权执行该查询。',
  AI_QUERY_TOO_BROAD: '查询范围过大，请补充过滤条件。',
  AI_EXECUTION_TIMEOUT: '查询超时，请缩小范围后重试。',
  AI_RATE_LIMITED: '请求过于频繁，请稍后再试。',
  AI_LLM_EGRESS_BLOCKED: 'LLM 数据出域配置不允许该调用。',
  AI_EXECUTION_FAILED: '查询执行失败，请稍后重试。',
  AI_PROVENANCE_INCOMPLETE: '溯源信息不完整，回答已被拒绝。',
  AI_MES_UNAVAILABLE: 'MES 只读查询未启用或暂时不可用。',
}

/** 把后端结构化错误映射为可展示文案。 */
export function describeAiError(error: unknown): { text: string; detail?: AiErrorDetail } {
  const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })?.response
  const detail = response?.data?.detail as AiErrorDetail | string | undefined
  if (detail && typeof detail === 'object' && typeof detail.code === 'string') {
    return { text: ERROR_TEXT[detail.code] ?? detail.message, detail }
  }
  if (typeof detail === 'string' && detail) return { text: detail }
  if (response?.status === 401) return { text: '登录已过期，请重新登录。' }
  if (response?.status === 403) return { text: '当前角色无权使用 AI 助手。' }
  if (response?.status === 504) return { text: ERROR_TEXT.AI_EXECUTION_TIMEOUT }
  return { text: 'AI 请求失败，请稍后重试。' }
}

export interface AiPing {
  ok: boolean
  ai_enabled: boolean
  chatbi_enabled: boolean
  mes_query_enabled: boolean
}

export async function getAiPing(): Promise<AiPing> {
  const { data } = await api.get<AiPing>('/ai/ping')
  return data
}

export async function askAi(
  question: string,
  context?: Record<string, unknown>
): Promise<AiChatResponse> {
  const { data } = await api.post<AiChatResponse>('/ai/chat', { question, context })
  return data
}

export async function getAiQueries(params?: {
  page?: number
  page_size?: number
}): Promise<AiQueryPage> {
  const { data } = await api.get<AiQueryPage>('/ai/queries', { params })
  return data
}

export async function sendAiFeedback(
  traceId: string,
  body: { score: number; comment?: string }
): Promise<{ trace_id: string; feedback_score: number; feedback_comment?: string | null }> {
  const { data } = await api.post(`/ai/queries/${encodeURIComponent(traceId)}/feedback`, body)
  return data
}

export async function getDashboardInsights(window: '7d' | '30d' = '7d'): Promise<AiInsightsResponse> {
  const { data } = await api.get<AiInsightsResponse>('/ai/insights/dashboard', {
    params: { window },
  })
  return data
}
