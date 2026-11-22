import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Card, Col, Row, Table, Tag } from 'antd'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { KpiCard } from './components/KpiCard'
import { AlertPanel, type AlertItem } from './components/AlertPanel'
import { TimeWindowBar } from './components/TimeWindowBar'
import { TrendChart } from './components/TrendChart'

const pct = (v: number | undefined) => `${((v ?? 0) * 100).toFixed(1)}%`
const money = (v: number | undefined) => `¥${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`

/** 财务驾驶舱：资金四卡 + 凭证趋势 + 期间状态 + 本体预警。 */
const FinanceDashboard: React.FC = () => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [window, setWindow] = useState('ALL')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData((await api.get('/dashboard/finance', { params: { window } })).data)
    } catch (error: any) {
      message.error(error?.userMessage ?? '加载财务驾驶舱失败')
    } finally { setLoading(false) }
  }, [message, window])
  useEffect(() => { void load() }, [load])

  const finance = data?.finance ?? {}
  const periods = data?.periods ?? []
  const columns = [
    { title: '期间', dataIndex: 'period_code' },
    { title: '状态', dataIndex: 'status', render: (v: string) => (
      <Tag color={v === 'CLOSED' ? 'default' : 'green'}>{v}</Tag>
    ) },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="财务驾驶舱" description="应收应付 / 回款率 / 现金流 / 月结状态"
        actions={<TimeWindowBar value={window} onChange={setWindow} loading={loading} />} />
      <Row gutter={[12, 12]}>
        <Col xs={12} md={6}>
          <KpiCard title="应收余额" value={money(finance.receivable_outstanding)}
            onClick={() => navigate('/sd/receivables')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="应付余额" value={money(finance.payable_open)}
            onClick={() => navigate('/mm/ap-view')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="回款率" value={pct(finance.collection_rate)}
            tone={(finance.collection_rate ?? 0) < 0.6 ? 'warn' : 'good'}
            onClick={() => navigate('/sd/receipts')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="现金流水（1002）" value={money(finance.cash_balance)}
            onClick={() => navigate('/finance/trial-balance')} />
        </Col>
      </Row>
      <Card title="凭证月度分布" size="small" loading={loading}>
        <TrendChart data={(data?.trend ?? []).map((t: any) => ({ label: t.month, value: t.entries }))} />
      </Card>
      <Row gutter={[12, 12]}>
        <Col xs={24} md={12}>
          <Card title="会计期间" size="small">
            <Table rowKey="period_code" columns={columns} dataSource={periods} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="资金构成" size="small">
            <div className="flex flex-col gap-2 text-sm">
              <div className="flex justify-between"><span className="text-ink-soft">已开票合计</span><span>{money(finance.invoiced_total)}</span></div>
              <div className="flex justify-between"><span className="text-ink-soft">已收款合计</span><span>{money(finance.collected_total)}</span></div>
              <div className="flex justify-between"><span className="text-ink-soft">已确认应付</span><span>{money(finance.supplier_confirmed_total)}</span></div>
              <div className="flex justify-between"><span className="text-ink-soft">已支付应付</span><span>{money(finance.supplier_paid_total)}</span></div>
            </div>
          </Card>
        </Col>
      </Row>
      <AlertPanel alerts={(data?.alerts ?? []) as AlertItem[]} />
    </div>
  )
}

export default FinanceDashboard
