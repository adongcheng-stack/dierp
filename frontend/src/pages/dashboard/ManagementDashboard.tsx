import { useEffect, useState } from 'react'
import { Button, Space, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { ErrorState, SkeletonRows } from '../../components/common/DataStates'

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
const money = (value: number | undefined) => (value ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

interface FinanceKpi {
  receivable_outstanding: number
  payable_open: number
  collection_rate: number
  cash_balance: number
}

function Stat({ title, value, suffix, tone = 'default' }: { title: string; value: string; suffix?: string; tone?: 'default' | 'good' | 'bad' | 'warn' }) {
  const toneClass = tone === 'good' ? 'text-status-success' : tone === 'bad' ? 'text-status-error' : tone === 'warn' ? 'text-status-warning' : 'text-ink'
  return (
    <div className="border-s border-line ps-4 first:border-s-0 first:ps-0">
      <div className="truncate text-sm text-ink-soft">{title}</div>
      <div className={`mt-2 text-2xl font-semibold leading-none tabular-nums ${toneClass}`}>
        {value}{suffix && <span className="ms-1 text-sm font-normal text-ink-soft">{suffix}</span>}
      </div>
    </div>
  )
}

const ManagementDashboard: React.FC = () => {
  const [kpi, setKpi] = useState<Kpi | null>(null)
  const [finance, setFinance] = useState<FinanceKpi | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchData = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/dashboard/management')
      setKpi(response.data)
      const financeResponse = await api.get('/dashboard/finance-kpi')
      setFinance(financeResponse.data)
    } catch (err) {
      const text = getErrorMessage(err) || '获取经营看板失败'
      setError(text)
      message.error(text)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void fetchData() }, [])

  const varianceRows = Object.entries(kpi?.cost.variance_by_type ?? {}).map(([type, amount]) => ({
    key: type,
    type,
    amount,
  }))

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="经营看板"
        description="销售 / 生产 / 质量 / 设备 / 成本 / 交期 六域 KPI 一屏总览，全部由既有单据实时推导"
        actions={
          <Space>
            <span className="text-sm text-ink-soft">更新于 {kpi?.generated_at?.replace('T', ' ').slice(0, 16) ?? '-'}</span>
            <Button icon={<ReloadOutlined />} onClick={() => void fetchData()} loading={loading}>刷新</Button>
          </Space>
        }
      />

      {error && !kpi ? (
        <ErrorState text={error} onRetry={() => void fetchData()} />
      ) : loading && !kpi ? (
        <SkeletonRows rows={6} />
      ) : (
        <div className="flex flex-col gap-8">
          <section className="grid grid-cols-1 gap-4 border-t border-line pt-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <Stat title="销售订单额" value={`¥${money(kpi?.sales.amount_total)}`} suffix={`/ 未交 ${kpi?.sales.open_orders ?? 0} 单`} />
            <Stat title="生产完成率" value={pct(kpi?.production.completion_rate)} suffix={`/ 在制 ${kpi?.production.open_orders ?? 0}`} />
            <Stat title="一次合格率" value={pct(kpi?.quality.first_pass_rate)} suffix={`/ 检验 ${kpi?.quality.inspections ?? 0}`} />
            <Stat title="综合 OEE" value={pct(kpi?.equipment.oee)} suffix={`/ 停机 ${kpi?.equipment.downtime_hours ?? 0}h`} />
            <Stat title="成本差异" value={`¥${money(kpi?.cost.variance_total)}`}
              tone={(kpi?.cost.variance_total ?? 0) <= 0 ? 'bad' : 'good'} />
            <Stat title="交期风险" value={String((kpi?.delivery.delayed_sales_orders ?? 0) + (kpi?.delivery.delayed_production_orders ?? 0))}
              suffix="单逾期" tone={(kpi?.delivery.delayed_sales_orders ?? 0) > 0 ? 'bad' : 'default'} />
          </section>

          <section className="grid grid-cols-1 gap-4 border-t border-line pt-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat title="应收余额" value={`¥${money(finance?.receivable_outstanding)}`} tone="bad" />
            <Stat title="应付余额（已确认-已核销）" value={`¥${money(finance?.payable_open)}`} tone="warn" />
            <Stat title="回款率（收款÷开票）" value={pct(finance?.collection_rate)} />
            <Stat title="现金流水（银行存款 1002）" value={`¥${money(finance?.cash_balance)}`}
              tone={(finance?.cash_balance ?? 0) >= 0 ? 'good' : 'bad'} />
          </section>

          <section className="grid grid-cols-1 gap-6 border-t border-line pt-4 xl:grid-cols-3">
            <div className="min-w-0">
              <h2 className="mb-3 text-lg font-semibold text-ink">设备 OEE（分工作中心）</h2>
              <div className="table-scroll tinted-table">
                <Table
                  rowKey="work_center_id"
                  size="small"
                  pagination={false}
                  dataSource={kpi?.equipment.work_centers ?? []}
                  columns={[
                    { title: '工作中心', dataIndex: 'work_center_id', key: 'work_center_id', fixed: 'left' },
                    {
                      title: 'OEE',
                      dataIndex: 'oee',
                      key: 'oee',
                      width: 150,
                      render: (v: number) => {
                        const each = Math.round(v * 100)
                        const toneClass = v >= 0.7 ? 'bg-status-success' : v >= 0.5 ? 'bg-status-warning' : 'bg-status-error'
                        return (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-20 bg-surface-hover">
                              <div className={`h-full ${toneClass}`} style={{ transform: `scaleX(${each / 100})`, transformOrigin: 'left' }} />
                            </div>
                            <span className="text-sm tabular-nums text-ink">{each}%</span>
                          </div>
                        )
                      },
                    },
                    {
                      title: '停机',
                      dataIndex: 'downtime_hours',
                      key: 'downtime_hours',
                      width: 70,
                      align: 'right',
                      render: (v: number) => `${v}h`,
                    },
                  ]}
                />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-soft">
                <span>可用率 {pct(kpi?.equipment.availability)}</span>
                <span className="border-s border-line ps-4">性能率 {pct(kpi?.equipment.performance)}</span>
                <span className="border-s border-line ps-4">良品率 {pct(kpi?.equipment.quality)}</span>
                <span className="border-s border-line ps-4">未关闭故障 {kpi?.equipment.open_failures ?? 0}</span>
              </div>
            </div>

            <div className="min-w-0">
              <h2 className="mb-3 text-lg font-semibold text-ink">生产工单状态分布</h2>
              <Space wrap size={[8, 8]}>
                {Object.entries(kpi?.production.by_status ?? {}).map(([status, count]) => (
                  <Tag key={status} color={status === 'IN_PRODUCTION' ? 'processing' : status === 'COMPLETED' || status === 'CLOSED' ? 'success' : 'default'}>
                    {STATUS_LABELS[status] ?? status} <span className="ms-1 tabular-nums">{count}</span>
                  </Tag>
                ))}
              </Space>
              <div className="mt-6">
                <div className="text-sm text-ink-soft">逾期在制工单</div>
                <div className={`mt-2 text-2xl font-semibold tabular-nums ${(kpi?.production.delayed_orders ?? 0) > 0 ? 'text-status-error' : 'text-ink'}`}>
                  {kpi?.production.delayed_orders ?? 0}
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-x-4 text-sm text-ink-soft">
                <span>待保养计划 {kpi?.delivery.due_maintenance_plans ?? 0} 项</span>
                <span className="border-s border-line ps-4">已结算工单 {kpi?.cost.settlements ?? 0} 张</span>
              </div>
            </div>

            <div className="min-w-0">
              <h2 className="mb-3 text-lg font-semibold text-ink">成本差异构成</h2>
              <div className="table-scroll tinted-table">
                <Table
                  rowKey="key"
                  size="small"
                  pagination={false}
                  dataSource={varianceRows}
                  columns={[
                    { title: '差异类型', dataIndex: 'type', key: 'type', fixed: 'left', render: (v: string) => VARIANCE_LABELS[v] ?? v },
                    {
                      title: '金额',
                      dataIndex: 'amount',
                      key: 'amount',
                      align: 'right',
                      render: (v: number) => (
                        <span className={`tabular-nums ${v <= 0 ? 'text-status-error' : 'text-status-success'}`}>
                          {v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      ),
                    },
                  ]}
                />
              </div>
            </div>
          </section>

          <section className="border-t border-line pt-4">
            <h2 className="mb-3 text-lg font-semibold text-ink">经营点评（自动）</h2>
            <ul className="m-0 list-none space-y-3 p-0">
              {(kpi?.insights ?? []).map((item, index) => (
                <li key={index} className="flex gap-3 border-s-2 border-line ps-3 text-md text-ink">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  )
}

export default ManagementDashboard
