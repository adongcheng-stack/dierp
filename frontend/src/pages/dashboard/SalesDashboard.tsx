import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Card, Col, Row, Table } from 'antd'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { KpiCard } from './components/KpiCard'
import { AlertPanel, type AlertItem } from './components/AlertPanel'
import { TimeWindowBar } from './components/TimeWindowBar'

const money = (v: number | undefined) => `¥${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
const pct = (v: number | undefined) => `${((v ?? 0) * 100).toFixed(1)}%`

/** 销售驾驶舱：订单 / 未交 / 报价转化 / 客户账龄 + 本体预警。 */
const SalesDashboard: React.FC = () => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [window, setWindow] = useState('ALL')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData((await api.get('/dashboard/sales', { params: { window } })).data)
    } catch (error: any) {
      message.error(error?.userMessage ?? '加载销售驾驶舱失败')
    } finally { setLoading(false) }
  }, [message, window])
  useEffect(() => { void load() }, [load])

  const sales = data?.sales ?? {}
  const quotation = data?.quotation ?? {}
  const columns = [
    { title: '客户', dataIndex: 'customer', ellipsis: true },
    { title: '应收余额', dataIndex: 'outstanding', width: 150,
      render: (v: number) => money(v) },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="销售驾驶舱" description="订单额 / 未交 / 报价转化率 / 客户账龄"
        actions={<TimeWindowBar value={window} onChange={setWindow} loading={loading} />} />
      <Row gutter={[12, 12]}>
        <Col xs={12} md={6}>
          <KpiCard title="订单总额" value={money(sales.amount_total)}
            onClick={() => navigate('/sd/sales-orders')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="未交订单" value={String(sales.open_orders ?? 0)}
            onClick={() => navigate('/sd/sales-orders')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="在手金额" value={money(sales.amount_open)} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="报价转化率" value={pct(quotation.conversion_rate)}
            hint={`${quotation.approved ?? 0}/${quotation.total ?? 0} 份已批准`}
            onClick={() => navigate('/sd/quotations')} />
        </Col>
      </Row>
      <Row gutter={[12, 12]}>
        <Col xs={24} md={10}>
          <Card title="客户应收账龄 TOP10" size="small" loading={loading}>
            <Table rowKey="customer" columns={columns} dataSource={data?.customers ?? []}
              pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} md={14}>
          <Card title="报价漏斗" size="small">
            <div className="flex flex-col gap-3">
              {[
                { label: '报价总数', value: quotation.total ?? 0, width: 100 },
                { label: '已批准', value: quotation.approved ?? 0,
                  width: Math.round((quotation.conversion_rate ?? 0) * 100) },
              ].map((row) => (
                <div key={row.label}>
                  <div className="mb-1 flex justify-between text-xs text-ink-soft">
                    <span>{row.label}</span><span>{row.value}</span>
                  </div>
                  <div className="h-3 rounded bg-surface-hover">
                    <div className="h-full rounded bg-brand" style={{ width: `${row.width}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
      <AlertPanel alerts={(data?.alerts ?? []) as AlertItem[]} />
    </div>
  )
}

export default SalesDashboard
