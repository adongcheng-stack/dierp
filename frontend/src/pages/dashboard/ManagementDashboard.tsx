import { useEffect, useState } from 'react'
import { Button, Card, Col, Row, Space, Statistic, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface Kpi {
  sales: { orders: number; open_orders: number; amount_total: number; amount_open: number }
  production: { orders: number; open_orders: number; by_status: Record<string, number>; completion_rate: number; delayed_orders: number }
  quality: { inspections: number; fail_inspections: number; first_pass_rate: number; ncrs: number; ncrs_open: number; ncrs_equipment: number }
  equipment: { oee: number; availability: number; performance: number; quality: number; open_failures: number; downtime_hours: number; work_centers: Array<{ work_center_id: string; oee: number; downtime_hours: number }> }
  cost: { variance_total: number; variance_by_type: Record<string, number>; settlements: number }
  delivery: { delayed_sales_orders: number; delayed_production_orders: number; due_maintenance_plans: number }
  insights: string[]
  generated_at: string
}

const VARIANCE_LABELS: Record<string, string> = {
  MATERIAL_PRICE: '材料价格',
  MATERIAL_USAGE: '材料用量',
  LABOR_RATE: '人工费率',
  LABOR_EFFICIENCY: '人工效率',
  OVERHEAD: '制造费用',
}

const STATUS_LABELS: Record<string, string> = {
  PLANNED: '已计划',
  RELEASED: '已下达',
  IN_PRODUCTION: '生产中',
  COMPLETED: '已完工',
  CLOSED: '已关闭',
}

const pct = (value: number | undefined) => `${((value ?? 0) * 100).toFixed(1)}%`

const ManagementDashboard: React.FC = () => {
  const [kpi, setKpi] = useState<Kpi | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/dashboard/management')
      setKpi(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取经营看板失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const varianceRows = Object.entries(kpi?.cost.variance_by_type ?? {}).map(([type, amount]) => ({
    key: type,
    type,
    amount,
  }))

  return (
    <div>
      <PageHeader
        title="经营看板"
        description="销售 / 生产 / 质量 / 设备 / 成本 / 交期 六域 KPI 一屏总览，全部由既有单据实时推导"
        actions={
          <Space>
            <span className="text-xs text-ink-faint">更新于 {kpi?.generated_at?.replace('T', ' ') ?? '-'}</span>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      />

      {/* 一级 KPI 卡 */}
      <Row gutter={[16, 16]} className="mb-4">
        <Col span={4}>
          <Card>
            <Statistic title="销售订单额" value={kpi?.sales.amount_total ?? 0} precision={2} prefix="¥" suffix={`/ 未交 ${kpi?.sales.open_orders ?? 0} 单`} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="生产完成率" value={pct(kpi?.production.completion_rate)} suffix={`/ 在制 ${kpi?.production.open_orders ?? 0}`} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="一次合格率" value={pct(kpi?.quality.first_pass_rate)} suffix={`/ 检验 ${kpi?.quality.inspections ?? 0}`} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="综合 OEE" value={pct(kpi?.equipment.oee)} suffix={`/ 停机 ${kpi?.equipment.downtime_hours ?? 0}h`} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="成本差异"
              value={(kpi?.cost.variance_total ?? 0).toLocaleString()}
              precision={2}
              prefix="¥"
              valueStyle={{ color: (kpi?.cost.variance_total ?? 0) <= 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="交期风险"
              value={(kpi?.delivery.delayed_sales_orders ?? 0) + (kpi?.delivery.delayed_production_orders ?? 0)}
              suffix="单逾期"
              valueStyle={{ color: (kpi?.delivery.delayed_sales_orders ?? 0) > 0 ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-4">
        {/* 设备 OEE 分中心 */}
        <Col span={8}>
          <Card title="设备 OEE（分工作中心）" size="small">
            <Table
              rowKey="work_center_id"
              size="small"
              pagination={false}
              dataSource={kpi?.equipment.work_centers ?? []}
              columns={[
                { title: '工作中心', dataIndex: 'work_center_id', key: 'work_center_id' },
                {
                  title: 'OEE',
                  dataIndex: 'oee',
                  key: 'oee',
                  width: 150,
                  render: (v: number) => {
                    const percent = Math.round(v * 100)
                    const color = v >= 0.7 ? '#52c41a' : v >= 0.5 ? '#faad14' : '#ff4d4f'
                    return (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-surface-hover">
                          <div className="h-full rounded-full" style={{ width: `${percent}%`, background: color }} />
                        </div>
                        <span className="text-xs tabular-nums" style={{ color }}>{percent}%</span>
                      </div>
                    )
                  },
                },
                {
                  title: '停机',
                  dataIndex: 'downtime_hours',
                  key: 'downtime_hours',
                  width: 70,
                  align: 'right' as const,
                  render: (v: number) => `${v}h`,
                },
              ]}
            />
            <div className="mt-3 text-xs text-ink-soft">
              可用率 {pct(kpi?.equipment.availability)} · 性能率 {pct(kpi?.equipment.performance)} · 良品率 {pct(kpi?.equipment.quality)}
              · 未关闭故障 {kpi?.equipment.open_failures ?? 0}
            </div>
          </Card>
        </Col>

        {/* 生产状态分布 */}
        <Col span={8}>
          <Card title="生产工单状态分布" size="small">
            <Space wrap size={[8, 8]}>
              {Object.entries(kpi?.production.by_status ?? {}).map(([status, count]) => (
                <Tag key={status} color={status === 'IN_PRODUCTION' ? 'processing' : status === 'COMPLETED' || status === 'CLOSED' ? 'success' : 'default'}>
                  {STATUS_LABELS[status] ?? status} · {count}
                </Tag>
              ))}
            </Space>
            <div className="mt-4">
              <Statistic title="逾期在制工单" value={kpi?.production.delayed_orders ?? 0} valueStyle={{ color: (kpi?.production.delayed_orders ?? 0) > 0 ? '#cf1322' : undefined }} />
            </div>
            <div className="mt-3 text-xs text-ink-soft">
              待保养计划 {kpi?.delivery.due_maintenance_plans ?? 0} 项 · 已结算工单 {kpi?.cost.settlements ?? 0} 张
            </div>
          </Card>
        </Col>

        {/* 成本差异构成 */}
        <Col span={8}>
          <Card title="成本差异构成" size="small">
            <Table
              rowKey="key"
              size="small"
              pagination={false}
              dataSource={varianceRows}
              columns={[
                { title: '差异类型', dataIndex: 'type', key: 'type', render: (v: string) => VARIANCE_LABELS[v] ?? v },
                {
                  title: '金额',
                  dataIndex: 'amount',
                  key: 'amount',
                  align: 'right' as const,
                  render: (v: number) => (
                    <span style={{ color: v <= 0 ? '#cf1322' : '#3f8600' }}>
                      {v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* 自动点评 */}
      <Card title="经营点评（自动）" size="small">
        <ul className="m-0 list-none space-y-2 p-0">
          {(kpi?.insights ?? []).map((item, index) => (
            <li key={index} className="text-sm text-ink">
              💡 {item}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

export default ManagementDashboard
