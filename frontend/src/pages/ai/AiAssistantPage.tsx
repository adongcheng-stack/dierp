import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Button, Card, Collapse, Descriptions, Empty, Input, Radio, Space, Spin, Table, Tag, Typography,
} from 'antd'
import type { TableColumnsType } from 'antd'
import { ReloadOutlined, SendOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  askAi, describeAiError, getAiPing, getDashboardInsights,
  type AiChatResponse, type AiErrorDetail, type AiInsightAlert, type AiInsightsResponse,
} from '../../services/ai'
import intentMeta from '../../mock/ai-intents.json'
// 枚举中文标签唯一事实源：ontology/src/mappings.json → generated/types.ts
import { ENUM_LABELS } from '../../../../ontology/generated/types'

interface IntentMeta {
  code: string
  label: string
  description: string
  downlink: string | null
  output_enums?: Record<string, string | undefined>
}

const INTENTS = intentMeta.intents as IntentMeta[]
const ENUM_LABEL_MAP = ENUM_LABELS as unknown as Record<string, Record<string, string>>

function enumLabel(enumName: string, value: unknown): string {
  if (value === null || value === undefined) return '—'
  return ENUM_LABEL_MAP[enumName]?.[String(value)] ?? String(value)
}

const EXAMPLES: Record<string, string> = {
  kitting_shortage: '这周哪些工单缺料？',
  material_below_safety: '哪些原材料低于安全库存？',
  order_delay_risk: '哪些订单 7 天内要交付但还没完工？',
  open_mrp_exceptions: '还有哪些严重的计划异常？',
  customer_credit_status: '客户 CUST001 信用超额了吗？',
  ar_overdue: '30 天以上未收款的应收有哪些？',
  open_nonconformance: '还有哪些严重的不合格品没关闭？',
  mes_work_order_progress: '工单 GD-20260914-00001 的工序进度怎么样？',
}

const SHACL_LABEL: Record<string, string> = {
  passed: '通过',
  skipped: '未执行',
  failed: '未通过',
}

function renderCell(value: unknown) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  return String(value)
}

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'red',
  WARNING: 'orange',
  INFO: 'blue',
}

function formatInsightValue(alert: AiInsightAlert, value: number | null) {
  if (value === null || value === undefined) return '—'
  if (alert.value_kind === 'ratio') return `${(value * 100).toFixed(0)}%`
  if (alert.value_kind === 'amount' || alert.value_kind === 'qty') return value.toFixed(2)
  return String(Math.round(value))
}

type MesRow = Record<string, unknown>

interface MesTaskGroup {
  task: MesRow
  reports: MesRow[]
}

const MES_TASK_STATUS_COLOR: Record<string, string> = {
  PENDING: 'default',
  RUNNING: 'processing',
  IN_PROGRESS: 'processing',
  PAUSED: 'orange',
  COMPLETED: 'green',
  CLOSED: 'green',
  CANCELLED: 'red',
}

function mesText(value: unknown) {
  return value === null || value === undefined ? '—' : String(value)
}

function MesOrderSummary({ row }: { row: MesRow }) {
  return (
    <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }}>
      <Descriptions.Item label="工单号">{renderCell(row.work_order_no)}</Descriptions.Item>
      <Descriptions.Item label="产品">{renderCell(row.product_name)}</Descriptions.Item>
      <Descriptions.Item label="工单状态">{renderCell(row.order_status)}</Descriptions.Item>
      <Descriptions.Item label="计划数量">{mesText(row.order_quantity)}</Descriptions.Item>
      <Descriptions.Item label="已完工">{mesText(row.order_completed_quantity)}</Descriptions.Item>
      <Descriptions.Item label="合格 / 报废">
        {`${mesText(row.order_qualified_quantity)} / ${mesText(row.order_scrapped_quantity)}`}
      </Descriptions.Item>
      <Descriptions.Item label="计划开始">{renderCell(row.planned_start_date)}</Descriptions.Item>
      <Descriptions.Item label="计划结束">{renderCell(row.planned_end_date)}</Descriptions.Item>
    </Descriptions>
  )
}

/**
 * MES 工单进度专用视图：工序按 task_sequence、报工按 report_time 时序展示，
 * 无报工记录的工序用红色底纹与"无报工记录"标签显著标注。
 */
function MesProgressCard({ result }: { result: AiChatResponse }) {
  const rows = result.data.rows as MesRow[]
  const reason = result.data.reason

  // 0 行：工单号不存在，与"工单存在但无工序"明确区分
  if (rows.length === 0) {
    const notFound = reason === 'work_order_not_found'
    return (
      <Card title="MES 工单进度" className="mb-4" size="small">
        <Alert
          type={notFound ? 'warning' : 'info'}
          showIcon
          message={notFound ? '工单号不存在' : 'MES 未返回可展示的数据'}
          description={
            notFound
              ? '请确认工单号是否正确，或该工单尚未同步到 MES。'
              : 'MES 已连接，但本次查询没有返回工序或报工数据，请稍后重试。'
          }
        />
      </Card>
    )
  }

  const head = rows[0]
  const groups = new Map<string, MesTaskGroup>()
  rows.forEach((row) => {
    if (row.process_task_id === null || row.process_task_id === undefined) return
    const key = String(row.process_task_id)
    const hasReport = row.report_id !== null && row.report_id !== undefined
    const group = groups.get(key)
    if (group) {
      if (hasReport) group.reports.push(row)
      return
    }
    groups.set(key, { task: row, reports: hasReport ? [row] : [] })
  })
  const tasks = Array.from(groups.values()).sort(
    (a, b) => Number(a.task.task_sequence ?? 0) - Number(b.task.task_sequence ?? 0),
  )
  tasks.forEach((group) => {
    group.reports.sort((a, b) =>
      String(a.report_time ?? '').localeCompare(String(b.report_time ?? '')),
    )
  })
  const noReportCount = tasks.filter((group) => group.reports.length === 0).length

  // 工单存在但没有工序任务：显式提示，不渲染空表
  if (tasks.length === 0) {
    return (
      <Card title="MES 工单进度" className="mb-4" size="small">
        <Alert
          className="mb-3"
          type="info"
          showIcon
          message="工单存在，但没有工序任务或报工记录"
          description="MES 中该工单尚未拆分工序任务，暂无可跟进的报工数据。"
        />
        <MesOrderSummary row={head} />
      </Card>
    )
  }

  const taskColumns: TableColumnsType<MesTaskGroup> = [
    {
      title: '工序顺序',
      key: 'task_sequence',
      width: 90,
      render: (_: unknown, group) => mesText(group.task.task_sequence),
    },
    {
      title: '工序',
      key: 'process_name',
      render: (_: unknown, group) => (
        <Space size={4}>
          <span>{renderCell(group.task.process_name)}</span>
          {group.reports.length === 0 && <Tag color="red">无报工记录</Tag>}
        </Space>
      ),
    },
    {
      title: '任务状态',
      key: 'task_status',
      width: 110,
      render: (_: unknown, group) => (
        <Tag color={MES_TASK_STATUS_COLOR[String(group.task.task_status)] ?? 'default'}>
          {renderCell(group.task.task_status)}
        </Tag>
      ),
    },
    {
      title: '设备',
      key: 'equipment_id',
      width: 80,
      render: (_: unknown, group) => renderCell(group.task.equipment_id),
    },
    {
      title: '完成数量',
      key: 'task_completed_quantity',
      width: 90,
      render: (_: unknown, group) => mesText(group.task.task_completed_quantity),
    },
    {
      title: '合格数量',
      key: 'task_qualified_quantity',
      width: 90,
      render: (_: unknown, group) => mesText(group.task.task_qualified_quantity),
    },
    {
      title: '报废数量',
      key: 'task_scrapped_quantity',
      width: 90,
      render: (_: unknown, group) => mesText(group.task.task_scrapped_quantity),
    },
    {
      title: '报工记录',
      key: 'reports',
      width: 100,
      render: (_: unknown, group) =>
        group.reports.length === 0 ? (
          <Typography.Text type="danger">缺失</Typography.Text>
        ) : (
          `${group.reports.length} 条`
        ),
    },
  ]

  const reportColumns: TableColumnsType<MesRow> = [
    { title: '报工时间', dataIndex: 'report_time', key: 'report_time' },
    { title: '报工数量', dataIndex: 'report_completed_quantity', key: 'report_completed_quantity' },
    { title: '合格数量', dataIndex: 'report_qualified_quantity', key: 'report_qualified_quantity' },
    { title: '报废数量', dataIndex: 'report_scrapped_quantity', key: 'report_scrapped_quantity' },
    { title: '缺陷原因', dataIndex: 'defect_reason', key: 'defect_reason', render: renderCell },
    { title: '实际工时', dataIndex: 'actual_hours', key: 'actual_hours' },
  ]

  return (
    <Card title="MES 工单进度" className="mb-4" size="small">
      <Alert
        className="mb-3"
        type={noReportCount > 0 ? 'warning' : 'success'}
        showIcon
        message={
          noReportCount > 0
            ? `${noReportCount} 道工序尚无报工记录`
            : '所有工序均有报工记录'
        }
        description={
          noReportCount > 0
            ? '下方表格中红色底纹的工序在 MES 中没有对应报工记录，请重点跟进。'
            : undefined
        }
      />
      <MesOrderSummary row={head} />
      <Table
        className="mt-3"
        size="small"
        rowKey={(group) => String(group.task.process_task_id)}
        pagination={false}
        dataSource={tasks}
        columns={taskColumns}
        scroll={{ x: 'max-content' }}
        rowClassName={(group) => (group.reports.length === 0 ? 'bg-red-50' : '')}
        expandable={{
          rowExpandable: (group) => group.reports.length > 0,
          expandedRowRender: (group) => (
            <Table
              size="small"
              pagination={false}
              rowKey={(row) => String(row.row_key ?? row.report_id)}
              dataSource={group.reports}
              columns={reportColumns}
            />
          ),
        }}
      />
    </Card>
  )
}

/** AI 助手：受控问数页面（只读意图、可溯源、无写操作）。 */
const AiAssistantPage: React.FC = () => {
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AiChatResponse | null>(null)
  const [error, setError] = useState<{ text: string; detail?: AiErrorDetail } | null>(null)
  const [insightsWindow, setInsightsWindow] = useState<'7d' | '30d'>('7d')
  const [insights, setInsights] = useState<AiInsightsResponse | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(true)
  const [insightsError, setInsightsError] = useState<string | null>(null)
  const [insightsReload, setInsightsReload] = useState(0)
  const [insightDetailOpen, setInsightDetailOpen] = useState(false)
  // null=探测中；false=未启用（MES 标签不可点，且不发起查询）
  const [mesAvailable, setMesAvailable] = useState<boolean | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    getAiPing()
      .then((data) => {
        if (active) setMesAvailable(Boolean(data.mes_query_enabled))
      })
      .catch(() => {
        // 探测失败按未启用处理：既不报错，也不假装可查
        if (active) setMesAvailable(false)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true
    setInsightsLoading(true)
    setInsightsError(null)
    setInsightDetailOpen(false)
    getDashboardInsights(insightsWindow)
      .then((data) => {
        if (active) setInsights(data)
      })
      .catch((err) => {
        if (!active) return
        setInsights(null)
        setInsightsError(describeAiError(err).text)
      })
      .finally(() => {
        if (active) setInsightsLoading(false)
      })
    return () => {
      active = false
    }
  }, [insightsWindow, insightsReload])

  const insightColumns: TableColumnsType<AiInsightAlert> = [
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (value: string) => (
        <Tag color={SEVERITY_COLOR[value] ?? 'default'}>{enumLabel('ExceptionSeverity', value)}</Tag>
      ),
    },
    {
      title: '异常',
      key: 'title',
      render: (_: unknown, record) => (
        <div>
          <div>{record.title}</div>
          <Typography.Text type="secondary" className="!text-xs">{record.metric}</Typography.Text>
        </div>
      ),
    },
    {
      title: '当前值',
      key: 'current_value',
      width: 100,
      render: (_: unknown, record) => formatInsightValue(record, record.current_value),
    },
    {
      title: '阈值',
      key: 'threshold',
      width: 100,
      render: (_: unknown, record) => formatInsightValue(record, record.threshold),
    },
    {
      title: '偏离',
      dataIndex: 'deviation_text',
      key: 'deviation_text',
    },
    {
      title: '关联单据',
      dataIndex: 'evidence_total',
      key: 'evidence_total',
      width: 90,
      render: (value: number) => `${value} 张`,
    },
    {
      title: '下钻',
      key: 'drilldown',
      width: 70,
      render: (_: unknown, record) =>
        record.drilldown ? (
          <Button type="link" size="small" className="!px-0" onClick={() => navigate(record.drilldown as string)}>
            查看
          </Button>
        ) : (
          '—'
        ),
    },
  ]

  const scrollToBottom = () => {
    const element = scrollRef.current
    if (!element) return
    requestAnimationFrame(() => {
      element.scrollTop = element.scrollHeight
    })
  }

  // 提问结果/错误渲染后自动滚到底部；用户仍可向上滚动查看历史内容
  useEffect(() => {
    if (loading || (!result && !error)) return
    const element = scrollRef.current
    if (!element) return
    requestAnimationFrame(() => {
      element.scrollTop = element.scrollHeight
    })
  }, [result, error, loading])

  const submit = async (text: string) => {
    const value = text.trim()
    if (!value || loading) return
    setQuestion(value)
    setLoading(true)
    setError(null)
    scrollToBottom()
    try {
      setResult(await askAi(value))
    } catch (err) {
      setResult(null)
      setError(describeAiError(err))
    } finally {
      setLoading(false)
    }
  }

  const intent = result ? INTENTS.find((item) => item.code === result.intent.code) : undefined
  const columns = (result?.data.columns ?? []).map((name) => {
    const enumName = intent?.output_enums?.[name]
    return {
      title: name,
      dataIndex: name,
      key: name,
      render: enumName
        ? (value: unknown) => enumLabel(enumName, value)
        : renderCell,
    }
  })

  return (
    <div className="ai-assistant-page mx-auto flex h-full min-h-0 w-full max-w-5xl flex-col">
      <div className="shrink-0">
        <PageHeader
          title="AI 助手"
          description="受控问数：只读意图 · 参数校验 · 结果可溯源，不执行任何写操作。"
        />
      </div>

      <div ref={scrollRef} className="ai-scroll min-h-0 flex-1 overflow-y-auto pe-1">
      <Card
        className="insights-card mb-4"
        title="异常解读"
        extra={(
          <Space>
            <Radio.Group
              size="small"
              optionType="button"
              buttonStyle="solid"
              value={insightsWindow}
              onChange={(event) => setInsightsWindow(event.target.value as '7d' | '30d')}
              options={[
                { label: '近 7 天', value: '7d' },
                { label: '近 30 天', value: '30d' },
              ]}
            />
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={insightsLoading}
              onClick={() => setInsightsReload((value) => value + 1)}
            >
              刷新
            </Button>
          </Space>
        )}
      >
        {insightsLoading ? (
          <div className="flex items-center gap-3 py-6 text-ink-soft">
            <Spin />
            <span>正在汇总驾驶舱与 MRP 异常…</span>
          </div>
        ) : insightsError ? (
          <Alert type="error" showIcon message={insightsError} />
        ) : insights ? (
          <>
            {insights.alerts.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前窗口内没有需要关注的异常。" />
            ) : (
              <Table
                size="small"
                rowKey="code"
                pagination={false}
                dataSource={insights.alerts}
                columns={insightColumns}
                scroll={{ x: 'max-content' }}
                sticky={{ offsetHeader: 46, getContainer: () => scrollRef.current ?? window }}
                expandable={{
                  expandedRowRender: (record) => (
                    <div className="space-y-2">
                      <Descriptions size="small" column={1}>
                        <Descriptions.Item label="归因">{record.attribution || '—'}</Descriptions.Item>
                        <Descriptions.Item label="建议">{record.suggestion || '—'}</Descriptions.Item>
                      </Descriptions>
                      <Table
                        size="small"
                        pagination={false}
                        rowKey={(item) => `${item.table}:${item.record_ref}`}
                        dataSource={record.evidence}
                        columns={[
                          { title: '表', dataIndex: 'table', key: 'table' },
                          { title: '记录', dataIndex: 'record_ref', key: 'record_ref' },
                        ]}
                      />
                    </div>
                  ),
                }}
              />
            )}
            <div className="mt-3">
              <Button
                type="link"
                size="small"
                className="!px-0"
                onClick={() => setInsightDetailOpen((open) => !open)}
              >
                {insightDetailOpen ? '收起详情' : '显示详情'}
              </Button>
              {insightDetailOpen && (
                <Alert
                  className="mt-2"
                  type={insights.summary.critical > 0 ? 'error' : insights.summary.warning > 0 ? 'warning' : 'success'}
                  showIcon
                  message={insights.narrative}
                  description={`共 ${insights.summary.total} 项：严重 ${insights.summary.critical} · 警告 ${insights.summary.warning} · 提示 ${insights.summary.info}`}
                />
              )}
            </div>
            <Typography.Text type="secondary" className="mt-2 block !text-xs">
              解读来源：
              {insights.narration_source === 'llm' ? `LLM 润色（${insights.model}）` : '确定性模板'}
              {` · 生成于 ${insights.generated_at}`}
            </Typography.Text>
          </>
        ) : null}
      </Card>

      {error && (
        <Alert
          className="mb-4"
          type={error.detail?.code === 'AI_MES_UNAVAILABLE' ? 'warning' : 'error'}
          showIcon
          message={error.text}
          description={
            error.detail
              ? `错误码：${error.detail.code}${error.detail.trace_id ? ` · trace_id：${error.detail.trace_id}` : ''}`
              : undefined
          }
        />
      )}

      {loading && (
        <Card className="mb-4">
          <div className="flex items-center gap-3 py-6 text-ink-soft">
            <Spin />
            <span>正在解析意图并执行只读查询…</span>
          </div>
        </Card>
      )}

      {result && !loading && (
        <>
          <Card className="mb-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Tag color="blue">{result.intent.label}</Tag>
              <Tag>{result.intent.code}</Tag>
              {result.intent.code === 'mes_work_order_progress' && (
                <Tag color="purple">MES（外部）</Tag>
              )}
              <Typography.Text type="secondary">
                {result.data.row_count} 条 · {result.limits.elapsed_ms} ms · {result.model}
              </Typography.Text>
            </div>
            <Typography.Paragraph className="!mb-0">{result.answer}</Typography.Paragraph>
          </Card>

          {result.intent.code === 'mes_work_order_progress' ? (
            <MesProgressCard result={result} />
          ) : (
            <Card title="结果数据" className="mb-4" size="small">
              {result.data.row_count === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="未找到符合条件的结果，可调整问题中的时间窗口或过滤条件后重试。"
                />
              ) : (
                <Table
                  size="small"
                  rowKey={(_row, index) => String(index)}
                  columns={columns}
                  dataSource={result.data.rows}
                  pagination={false}
                  scroll={{ x: 'max-content' }}
                />
              )}
            </Card>
          )}

          <Collapse
            key={`provenance-${result.trace_id}`}
            className="mb-4"
            size="small"
            items={[
              {
                key: 'provenance',
                label: '溯源',
                children: (
                  <Table
                    size="small"
                    rowKey={(_row, index) => String(index)}
                    pagination={false}
                    dataSource={result.provenance}
                    columns={[
                      {
                        title: '来源',
                        dataIndex: 'source_system',
                        key: 'source_system',
                        width: 110,
                        render: (value: string | undefined) =>
                          value === 'MES' ? (
                            <Tag color="purple">MES（外部）</Tag>
                          ) : (
                            <Tag>ERP</Tag>
                          ),
                      },
                      { title: '表', dataIndex: 'table', key: 'table' },
                      { title: '记录', dataIndex: 'record_ref', key: 'record_ref' },
                      {
                        title: '本体类',
                        dataIndex: 'ontology_class',
                        key: 'ontology_class',
                        render: (value: string) => value?.split('#').pop() ?? '—',
                      },
                      {
                        title: '下钻',
                        key: 'downlink',
                        render: () =>
                          intent?.downlink ? (
                            <Button
                              type="link"
                              size="small"
                              className="!px-0"
                              onClick={() => navigate(intent.downlink as string)}
                            >
                              查看单据
                            </Button>
                          ) : (
                            <Typography.Text type="secondary">无对应页面</Typography.Text>
                          ),
                      },
                    ]}
                  />
                ),
              },
            ]}
          />

          <Collapse
            key={`limits-${result.trace_id}`}
            size="small"
            items={[
              {
                key: 'limits',
                label: '本次查询限额',
                children: (
                  <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }}>
                    <Descriptions.Item label="trace_id">
                      <Typography.Text copyable>{result.trace_id}</Typography.Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="SHACL">
                      {SHACL_LABEL[result.limits.shacl ?? ''] ?? result.limits.shacl ?? '—'}
                      <Tag className="ms-2">{result.limits.coverage}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="行数">
                      {result.data.row_count} / {result.limits.max_rows}
                      {result.limits.truncated && <Tag color="orange" className="ms-2">已截断</Tag>}
                    </Descriptions.Item>
                    <Descriptions.Item label="超时预算">
                      {result.limits.timeout_seconds}s
                    </Descriptions.Item>
                  </Descriptions>
                ),
              },
            ]}
          />
        </>
      )}
      </div>

      <div className="shrink-0 border-t border-line pt-3">
        <Card className="mb-0">
          <Input.TextArea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="用一句话描述你要查的业务问题，例如：这周哪些工单缺料？"
            autoSize={{ minRows: 2, maxRows: 5 }}
            maxLength={500}
            showCount
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault()
                void submit(question)
              }
            }}
          />
          <div className="mt-3 flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <Space size={[6, 6]} wrap>
                {INTENTS.map((item) => {
                  // MES 能力需服务端显式开启；未启用时不渲染为可点标签
                  const mesDisabled = item.code === 'mes_work_order_progress' && mesAvailable !== true
                  return (
                    <Tag
                      key={item.code}
                      className={mesDisabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}
                      icon={<ThunderboltOutlined />}
                      title={mesDisabled ? 'MES 只读查询未启用' : undefined}
                      onClick={() => {
                        if (!mesDisabled) void submit(EXAMPLES[item.code] ?? item.description)
                      }}
                    >
                      {item.label}
                      {mesDisabled ? '（未启用）' : ''}
                    </Tag>
                  )
                })}
              </Space>
            </div>
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={loading}
              disabled={!question.trim()}
              className="shrink-0"
              onClick={() => void submit(question)}
            >
              提问
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default AiAssistantPage
