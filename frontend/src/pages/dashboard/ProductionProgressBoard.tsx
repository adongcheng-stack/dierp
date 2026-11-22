import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Card, Col, Row, Table, Tag, Input } from 'antd'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { KpiCard } from './components/KpiCard'
import { AlertPanel, type AlertItem } from './components/AlertPanel'
import { TimeWindowBar } from './components/TimeWindowBar'
import { GanttChart } from './components/GanttChart'

interface Props { embedded?: boolean }

/** 生产进度看板：工序甘特 + 明细表，接 /dashboard/production-progress。 */
const ProductionProgressBoard: React.FC<Props> = ({ embedded = false }) => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [window, setWindow] = useState('ALL')
  const [order, setOrder] = useState('')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/dashboard/production-progress', {
        params: { window, ...(order ? { order } : {}) },
      })
      setData(res.data)
    } catch (error: any) {
      message.error(error?.userMessage ?? '加载生产进度失败')
    } finally { setLoading(false) }
  }, [message, window, order])
  useEffect(() => { void load() }, [load])

  const summary = data?.summary ?? {}
  const columns = [
    { title: '工单', dataIndex: 'production_order_number', width: 180 },
    { title: '工序', dataIndex: 'operation_name' },
    { title: '工作中心', dataIndex: 'work_center_id', width: 120 },
    { title: '计划/完成', key: 'qty', width: 130,
      render: (_: unknown, r: any) => `${r.completed_quantity}/${r.planned_quantity}` },
    { title: '完成率', dataIndex: 'completion_rate', width: 100,
      render: (v: number) => `${Math.round(v * 100)}%` },
    { title: '状态', dataIndex: 'status', width: 110,
      render: (v: string) => <Tag color={v === 'COMPLETED' ? 'green' : v === 'DELAYED' ? 'red' : 'blue'}>{v}</Tag> },
  ]

  return (
    <div className="flex flex-col gap-4">
      {!embedded && (
        <PageHeader title="生产进度看板" description="工序级进度甘特与异常（数据源：ProductionProgress）"
          actions={<TimeWindowBar value={window} onChange={setWindow} loading={loading} />} />
      )}
      <Row gutter={[12, 12]}>
        <Col xs={12} md={6}>
          <KpiCard title="工序数" value={String(summary.operations ?? 0)} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="涉及工单" value={String(summary.orders ?? 0)}
            onClick={() => navigate('/pp/production-orders')} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="平均完成率" value={`${Math.round((summary.avg_completion_rate ?? 0) * 100)}%`} />
        </Col>
        <Col xs={12} md={6}>
          <KpiCard title="延期工序" value={String(summary.by_status?.DELAYED ?? 0)}
            tone={(summary.by_status?.DELAYED ?? 0) > 0 ? 'bad' : 'good'} />
        </Col>
      </Row>
      <Card title="工序甘特" size="small" loading={loading}>
        <GanttChart rows={data?.rows ?? []} />
      </Card>
      {!embedded && (
        <>
          <Card size="small" title="工序明细">
            <Input.Search allowClear placeholder="按工单号筛选" className="mb-3 w-64"
              onSearch={setOrder} onChange={(e) => { if (!e.target.value) setOrder('') }} />
            <Table rowKey={(r: any) => `${r.production_order_number}-${r.operation_no}`}
              columns={columns} dataSource={data?.rows ?? []} pagination={{ pageSize: 10 }} size="small" />
          </Card>
          <AlertPanel alerts={(data?.alerts ?? []) as AlertItem[]} />
        </>
      )}
    </div>
  )
}

export default ProductionProgressBoard
