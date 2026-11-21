import { useEffect, useState } from 'react'
import { Button, Card, Col, Empty, Input, Row, Space, Statistic, Table, Tag, Timeline, Tree, message } from 'antd'
import { ForkOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

/** 节点类型 → 中文名 / 颜色（与后端 traceability_engine 契约一致） */
const TYPE_META: Record<string, { label: string; color: string }> = {
  LOT: { label: '批次', color: 'blue' },
  PRODUCTION_ORDER: { label: '生产订单', color: 'geekblue' },
  SALES_ORDER: { label: '销售订单', color: 'cyan' },
  CUSTOMER: { label: '客户', color: 'purple' },
  MATERIAL: { label: '物料', color: 'orange' },
  MATERIAL_ISSUE: { label: '领料', color: 'gold' },
  MATERIAL_BATCH: { label: '原料批次', color: 'gold' },
  OPERATION_REPORT: { label: '报工', color: 'green' },
  INSPECTION: { label: '检验', color: 'blue' },
  NCR: { label: '不合格品', color: 'red' },
  EQUIPMENT_FAILURE: { label: '设备故障', color: 'volcano' },
  PURCHASE_ORDER: { label: '采购单', color: 'lime' },
  PURCHASE_ORDER_LINE: { label: '采购行', color: 'lime' },
}

interface TraceNode {
  key: string
  type: string
  id: string
  title: string
  status: string | null
  quantity: number | null
  time: string | null
  meta: Record<string, unknown>
}

interface TraceEdge {
  from: string
  to: string
  label: string
}

interface TraceResult {
  root: string
  direction: string
  nodes: TraceNode[]
  edges: TraceEdge[]
  truncated: boolean
}

interface SearchHit {
  type: string
  id: string
  title: string
  meta: { trace_lot?: string; trace_material?: string; material_code?: string }
}

const DEMO_HINTS = [
  { label: '演示批次（FAIL→NCR→EAM）', value: 'LOT-20251230-0003' },
  { label: '演示批次（报废 12）', value: 'LOT-20251230-0002' },
  { label: '反向物料追溯', value: 'HF1004ENIGAB02' },
  { label: '销售订单 1→4 工单', value: 'SO-20251231-0001' },
]

/** 由边构建从根出发的 BFS 链路（用于 Timeline 展示） */
function buildChain(root: string, nodes: TraceNode[], edges: TraceEdge[]): Array<{ label: string; node: TraceNode }> {
  const byKey = new Map(nodes.map((n) => [n.key, n]))
  const outgoing = new Map<string, TraceEdge[]>()
  for (const edge of edges) {
    const list = outgoing.get(edge.from) ?? []
    list.push(edge)
    outgoing.set(edge.from, list)
  }
  const chain: Array<{ label: string; node: TraceNode }> = []
  const seen = new Set<string>([root])
  const queue: Array<{ key: string; label: string }> = [{ key: root, label: '追溯起点' }]
  while (queue.length > 0 && chain.length < 40) {
    const current = queue.shift()!
    const node = byKey.get(current.key)
    if (node) chain.push({ label: current.label, node })
    for (const edge of outgoing.get(current.key) ?? []) {
      if (!seen.has(edge.to)) {
        seen.add(edge.to)
        queue.push({ key: edge.to, label: edge.label })
      }
    }
  }
  return chain
}

function metaSummary(node: TraceNode): string {
  const parts: string[] = []
  for (const [k, v] of Object.entries(node.meta ?? {})) {
    if (v === null || v === undefined || v === '') continue
    const label =
      {
        material_code: '物料',
        sales_order_number: '销售订单',
        lot_number: '批次',
        operation_name: '工序',
        good_quantity: '良品',
        scrap_quantity: '报废',
        quantity_rejected: '不合格',
        warehouse: '仓库',
        resource_id: '设备',
        severity: '严重度',
        disposition: '处置',
        defect_desc: '缺陷',
        equipment_cause: '设备原因',
        supplier: '供应商',
        received_quantity: '已收',
        production_order_number: '工单',
        type: '环节',
        result: '结论',
        industry: '行业',
        material_name: '名称',
        mi_number: 'MI',
        trace_lot: '批次',
        trace_material: '物料',
      }[k] ?? k
    parts.push(`${label}: ${String(v)}`)
  }
  return parts.join('　')
}

const TraceabilityExplorer: React.FC = () => {
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TraceResult | null>(null)
  const [suggestions, setSuggestions] = useState<SearchHit[] | null>(null)
  const [overview, setOverview] = useState<Record<string, number> | null>(null)

  const fetchOverview = async () => {
    try {
      const response = await api.get('/traceability/overview')
      setOverview(response.data)
    } catch (error) {
      console.warn('[traceability] overview 加载失败', error)
    }
  }

  useEffect(() => {
    fetchOverview()
  }, [])

  const runTrace = async (hit: SearchHit) => {
    setLoading(true)
    setSuggestions(null)
    try {
      let response
      if (hit.type === 'LOT') {
        response = await api.get(`/traceability/lots/${encodeURIComponent(hit.id)}`)
      } else if (hit.type === 'MATERIAL') {
        response = await api.get(`/traceability/materials/${encodeURIComponent(hit.id)}`)
      } else if (hit.type === 'PRODUCTION_ORDER' || hit.type === 'SALES_ORDER') {
        response = await api.get(`/traceability/orders/${encodeURIComponent(hit.id)}`)
      } else if (hit.type === 'NCR') {
        // NCR 本身不是根：优先跳到批次，其次物料
        if (hit.meta?.trace_lot) {
          response = await api.get(`/traceability/lots/${encodeURIComponent(hit.meta.trace_lot)}`)
        } else if (hit.meta?.trace_material) {
          response = await api.get(`/traceability/materials/${encodeURIComponent(hit.meta.trace_material)}`)
        } else {
          message.warning('该 NCR 缺少可追溯根节点')
          setLoading(false)
          return
        }
      } else {
        message.warning(`暂不支持从 ${TYPE_META[hit.type]?.label ?? hit.type} 追溯`)
        setLoading(false)
        return
      }
      setResult(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '追溯查询失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (value: string) => {
    const q = value.trim()
    if (!q) {
      message.warning('请输入批次号 / 物料 / 工单 / 销售订单 / NCR 编号')
      return
    }
    setLoading(true)
    setResult(null)
    setSuggestions(null)
    try {
      const response = await api.get('/traceability/search', { params: { q } })
      const items: SearchHit[] = response.data.items ?? []
      if (items.length === 0) {
        message.warning(`未找到与「${q}」匹配的可追溯对象`)
        return
      }
      await runTrace(items[0])
      if (items.length > 1) setSuggestions(items.slice(1))
    } catch (error) {
      message.error(getErrorMessage(error) || '搜索失败')
    } finally {
      setLoading(false)
    }
  }

  const chain = result ? buildChain(result.root, result.nodes, result.edges) : []
  const rootNode = result?.nodes.find((n) => n.key === result.root)

  const columns = [
    { title: '节点', dataIndex: 'title', key: 'title', width: 240 },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 110,
      render: (v: string) => <Tag color={TYPE_META[v]?.color ?? 'default'}>{TYPE_META[v]?.label ?? v}</Tag>,
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 120, render: (v: string | null) => v ?? '-' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 90, align: 'right' as const, render: (v: number | null) => (v === null ? '-' : v) },
    { title: '时间', dataIndex: 'time', key: 'time', width: 160, render: (v: string | null) => (v ? v.replace('T', ' ') : '-') },
    { title: '关键信息', key: 'meta', ellipsis: true, render: (_: unknown, record: TraceNode) => metaSummary(record) || '-' },
  ]

  return (
    <div>
      <PageHeader
        title="双向追溯"
        description="批次 / 物料 / 订单全链路追溯：正向（批次 → 工单 → 销售/客户 → 报工 → 检验 → NCR → 设备故障），反向（物料 → 领料 → 工单 → 批次 → 客户）"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchOverview} loading={loading}>
            刷新
          </Button>
        }
      />

      <Card className="mb-4">
        <Space.Compact style={{ width: '100%', maxWidth: 640 }}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="输入批次号 / 物料 / 工单号 / 销售订单号 / NCR 编号"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={() => handleSearch(keyword)}
            allowClear
          />
          <Button type="primary" icon={<ForkOutlined />} loading={loading} onClick={() => handleSearch(keyword)}>
            追溯
          </Button>
        </Space.Compact>
        <div className="mt-3 flex flex-wrap gap-2">
          {DEMO_HINTS.map((hint) => (
            <Tag
              key={hint.value}
              className="cursor-pointer"
              color="processing"
              onClick={() => {
                setKeyword(hint.value)
                handleSearch(hint.value)
              }}
            >
              {hint.label} · {hint.value}
            </Tag>
          ))}
        </div>
        {overview && (
          <Row gutter={16} className="mt-4">
            <Col span={4}>
              <Statistic title="可追溯批次" value={overview.lots ?? 0} />
            </Col>
            <Col span={4}>
              <Statistic title="生产订单" value={overview.production_orders ?? 0} />
            </Col>
            <Col span={4}>
              <Statistic title="销售订单" value={overview.sales_orders ?? 0} />
            </Col>
            <Col span={4}>
              <Statistic title="物料" value={overview.materials ?? 0} />
            </Col>
            <Col span={4}>
              <Statistic title="检验/NCR" value={`${overview.inspections ?? 0} / ${overview.ncrs ?? 0}`} />
            </Col>
            <Col span={4}>
              <Statistic title="设备故障" value={overview.equipment_failures ?? 0} />
            </Col>
          </Row>
        )}
      </Card>

      {result && rootNode && (
        <>
          <Card
            className="mb-4"
            title={
              <Space>
                <span>追溯链路</span>
                <Tag color={TYPE_META[rootNode.type]?.color}>{TYPE_META[rootNode.type]?.label}</Tag>
                <span className="text-ink-soft">{rootNode.title}</span>
                <Tag color={result.direction === 'FORWARD' ? 'green' : 'orange'}>
                  {result.direction === 'FORWARD' ? '正向' : '反向'}
                </Tag>
                {result.truncated && <Tag color="warning">已截断</Tag>}
              </Space>
            }
          >
            <Timeline
              items={chain.map((step) => ({
                color: TYPE_META[step.node.type]?.color ?? 'blue',
                children: (
                  <span>
                    <Tag>{step.label}</Tag>
                    <span className="font-medium">{step.node.title}</span>
                    {step.node.status && <Tag className="ml-2">{step.node.status}</Tag>}
                  </span>
                ),
              }))}
            />
          </Card>

          <Card title={`节点明细（${result.nodes.length} 节点 / ${result.edges.length} 边）`} className="mb-4">
            <Table
              rowKey="key"
              columns={columns}
              dataSource={result.nodes}
              pagination={false}
              size="small"
              rowClassName={(record) => (record.key === result.root ? 'bg-blue-50' : '')}
            />
          </Card>

          <Card title="追溯关系图（Tree）">
            <TraceTree result={result} />
          </Card>
        </>
      )}

      {suggestions && suggestions.length > 0 && (
        <Card title={`其他匹配（${suggestions.length}）`} className="mb-4">
          <Table
            rowKey={(record) => `${record.type}:${record.id}`}
            columns={[
              { title: '对象', dataIndex: 'title', key: 'title' },
              {
                title: '类型',
                dataIndex: 'type',
                key: 'type',
                width: 120,
                render: (v: string) => <Tag color={TYPE_META[v]?.color ?? 'default'}>{TYPE_META[v]?.label ?? v}</Tag>,
              },
              {
                title: '操作',
                key: 'action',
                width: 100,
                render: (_: unknown, record: SearchHit) => (
                  <Button size="small" type="link" onClick={() => runTrace(record)}>
                    追溯
                  </Button>
                ),
              },
            ]}
            dataSource={suggestions}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {!result && !loading && (
        <Card>
          <Empty description="输入编号开始追溯，或点击上方演示入口" />
        </Card>
      )}
    </div>
  )
}

/** 由边构建 antd Tree（根 → 子节点，双向合并） */
function TraceTree({ result }: { result: TraceResult }) {
  const byKey = new Map(result.nodes.map((n) => [n.key, n]))
  const childrenOf = new Map<string, Array<{ key: string; label: string }>>()
  for (const edge of result.edges) {
    for (const [parent, child, label] of [
      [edge.from, edge.to, edge.label],
      [edge.to, edge.from, edge.label],
    ] as Array<[string, string, string]>) {
      const list = childrenOf.get(parent) ?? []
      if (!list.some((x) => x.key === child)) list.push({ key: child, label })
      childrenOf.set(parent, list)
    }
  }

  const buildNode = (key: string, label: string, depth: number): Record<string, unknown> => {
    const node = byKey.get(key)
    const title = (
      <span>
        <Tag color={TYPE_META[node?.type ?? '']?.color ?? 'default'}>{label}</Tag>
        <span className={node?.key === result.root ? 'font-semibold' : ''}>{node?.title ?? key}</span>
      </span>
    )
    if (depth >= 4) return { key, title }
    const kids = (childrenOf.get(key) ?? []).filter((k) => k.key !== key)
    return { key, title, children: kids.map((k) => buildNode(k.key, k.label, depth + 1)) }
  }

  return (
    <Tree
      defaultExpandAll
      selectable={false}
      showLine
      treeData={[buildNode(result.root, '追溯起点', 0)]}
    />
  )
}

export default TraceabilityExplorer
