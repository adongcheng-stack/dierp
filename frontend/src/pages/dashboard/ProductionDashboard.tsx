import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Card, Col, Row, Tag } from 'antd'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { KpiCard } from './components/KpiCard'
import { AlertPanel, type AlertItem } from './components/AlertPanel'
import { TimeWindowBar } from './components/TimeWindowBar'
import ProductionProgressBoard from './ProductionProgressBoard'

const pct = (v: number | undefined) => `${((v ?? 0) * 100).toFixed(1)}%`

/** 生产驾驶舱：工单/OEE/质量 + 内嵌生产进度甘特 + 本体预警。 */
const ProductionDashboard: React.FC = () => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [window, setWindow] = useState('ALL')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData((await api.get('/dashboard/production', { params: { window } })).data)
    } catch (error: any) {
      message.error(error?.userMessage ?? '加载生产驾驶舱失败')
    } finally { setLoading(false) }
  }, [message, window])
  useEffect(() => { void load() }, [load])

  const production = data?.production ?? {}
  const quality = data?.quality ?? {}
  const equipment = data?.equipment ?? {}
  const workCenters: any[] = equipment.work_centers ?? []

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="生产驾驶舱" description="工单完成率 / OEE / 不良与交期风险，阈值由本体 DashboardRule 驱动"
        actions={<TimeWindowBar value={window} onChange={setWindow} loading={loading} />} />
      <Row gutter={[12, 12]}>
        <Col xs={12} md={6}>
          <KpiCard title="工单完成率" value={pct(production.completion_rate)}
            tone={(production.completion_rate ?? 0) < 0.8 ? 'warn' : 'good'}
            onClick={() => navigate('/pp/production-orders')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="在制工单" value={String(production.open_orders ?? 0)}
            onClick={() => navigate('/pp/production-orders')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="逾期工单" value={String(production.delayed_orders ?? 0)}
            tone={(production.delayed_orders ?? 0) > 0 ? 'bad' : 'good'} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="一次合格率" value={pct(quality.first_pass_rate)}
            tone={(quality.first_pass_rate ?? 0) < 0.95 ? 'warn' : 'good'}
            onClick={() => navigate('/qms/inspections')} />
        </Col>
      </Row>

      <Card title="工作中心 OEE" size="small" loading={loading}>
        <div className="flex flex-col gap-2">
          {workCenters.length === 0 && <div className="text-xs text-ink-faint">暂无工作中心数据</div>}
          {workCenters.map((wc) => (
            <div key={wc.work_center_id} className="flex items-center gap-3">
              <span className="w-20 shrink-0 text-xs text-ink-soft">{wc.work_center_id}</span>
              <div className="h-2 flex-1 rounded bg-surface-hover">
                <div className={`h-full rounded ${wc.oee < 0.7 ? 'bg-status-error' : 'bg-status-success'}`}
                  style={{ width: `${Math.min((wc.oee ?? 0) * 100, 100)}%` }} />
              </div>
              <span className="w-14 text-right text-xs tabular-nums">{pct(wc.oee)}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card size="small" title="生产进度（甘特）">
        <ProductionProgressBoard embedded />
      </Card>

      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-ink">生产预警</span>
        <Tag>{(data?.alerts ?? []).length} 条</Tag>
      </div>
      <AlertPanel alerts={(data?.alerts ?? []) as AlertItem[]} />
    </div>
  )
}

export default ProductionDashboard
