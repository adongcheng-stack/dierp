import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Col, Modal, Radio, Row, Select, Space, Statistic, Table, Tag, Tooltip, message } from 'antd'
import { CaretRightOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  ALGORITHM,
  EXCEPTION_TYPE,
  RUN_STATUS,
  SOURCE_TYPE,
  StatusTag,
  fmtDateTime,
  fmtMinutes,
  pct,
} from './shared'

const BAR_COLORS = ['#1677ff', '#13c2c2', '#722ed1', '#fa8c16', '#eb2f96', '#52c41a']

const ApsWorkbench: React.FC = () => {
  const [overview, setOverview] = useState<any>(null)
  const [runs, setRuns] = useState<any[]>([])
  const [selectedRun, setSelectedRun] = useState<string | undefined>()
  const [gantt, setGantt] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [runOpen, setRunOpen] = useState(false)
  const [algorithm, setAlgorithm] = useState('FORWARD')
  const [sourceType, setSourceType] = useState('PRODUCTION_ORDER')
  const [busy, setBusy] = useState(false)

  const fetchOverview = async () => {
    try {
      const response = await api.get('/planning/aps/overview')
      setOverview(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取 APS 概览失败')
    }
  }

  const fetchRuns = async () => {
    try {
      const response = await api.get('/planning/aps/runs', { params: { limit: 50 } })
      const items = response.data.items ?? []
      setRuns(items)
      setSelectedRun((current) => current ?? items[0]?.run_number)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取排程批次失败')
    }
  }

  const fetchGantt = async (runNumber?: string) => {
    if (!runNumber) {
      setGantt(null)
      return
    }
    setLoading(true)
    try {
      const response = await api.get(`/planning/aps/runs/${runNumber}/gantt`)
      setGantt(response.data)
    } catch (error) {
      setGantt(null)
      message.error(getErrorMessage(error) || '获取甘特图失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOverview()
    fetchRuns()
  }, [])

  useEffect(() => {
    fetchGantt(selectedRun)
  }, [selectedRun])

  const run = async () => {
    setBusy(true)
    try {
      const response = await api.post('/planning/aps/run', {
        algorithm,
        source_type: sourceType,
        run_name: `APS ${ALGORITHM[algorithm] ?? algorithm}`,
      })
      message.success(`排程完成：${response.data.run_number}（${response.data.operation_count} 道工序）`)
      setRunOpen(false)
      setSelectedRun(response.data.run_number)
      fetchRuns()
      fetchOverview()
    } catch (error) {
      message.error(getErrorMessage(error) || 'APS 排程失败')
    } finally {
      setBusy(false)
    }
  }

  const publish = async () => {
    if (!selectedRun) return
    setBusy(true)
    try {
      await api.post(`/planning/aps/runs/${selectedRun}/publish`)
      message.success(`批次 ${selectedRun} 已发布至生产执行`)
      fetchRuns()
      fetchOverview()
      fetchGantt(selectedRun)
    } catch (error) {
      message.error(getErrorMessage(error) || '发布失败')
    } finally {
      setBusy(false)
    }
  }

  // ── 甘特图时间轴 ────────────────────────────────────────────────
  const timeline = useMemo(() => {
    const rows: any[] = gantt?.gantt ?? []
    const all = rows.flatMap((row) => row.operations ?? [])
    if (all.length === 0) return null
    const starts = all.map((op: any) => new Date(op.planned_start).getTime())
    const ends = all.map((op: any) => new Date(op.planned_end).getTime())
    const min = Math.min(...starts)
    const max = Math.max(...ends)
    const span = (max - min) * 0.06 || 3600000
    return { start: min - span, end: max + span }
  }, [gantt])

  const tickCount = 6
  const ticks =
    timeline != null
      ? Array.from({ length: tickCount + 1 }, (_, index) => {
          const time = timeline.start + ((timeline.end - timeline.start) * index) / tickCount
          const date = new Date(time)
          return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(
            date.getHours(),
          ).padStart(2, '0')}:00`
        })
      : []

  const currentRun = runs.find((item) => item.run_number === selectedRun)

  const exceptionColumns = [
    {
      title: '类型',
      dataIndex: 'exception_type',
      key: 'type',
      width: 120,
      render: (value: string) => {
        const entry = EXCEPTION_TYPE[value]
        return <Tag color={entry?.color ?? 'default'}>{entry?.text ?? value}</Tag>
      },
    },
    { title: '工单', dataIndex: 'production_order_number', key: 'order', width: 170 },
    { title: '级别', dataIndex: 'severity', key: 'severity', width: 90, render: (value: string) => (value === 'CRITICAL' ? <Tag color="red">严重</Tag> : <Tag color="orange">警告</Tag>) },
    { title: '说明', dataIndex: 'message', key: 'message', ellipsis: true },
    { title: '建议动作', dataIndex: 'suggested_action', key: 'action', ellipsis: true },
  ]

  const [exceptions, setExceptions] = useState<any[]>([])
  useEffect(() => {
    if (!selectedRun) return
    api
      .get('/planning/aps/exceptions', { params: { run_number: selectedRun, limit: 50 } })
      .then((response) => setExceptions(response.data.items ?? []))
      .catch(() => setExceptions([]))
  }, [selectedRun, gantt])

  return (
    <div>
      <PageHeader
        title="APS 工作台"
        description="工作中心级有限产能排程：班次日历 × 并行产能 × 换产与技能约束，支持正排 / 倒排 / 混合"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => { fetchOverview(); fetchRuns(); fetchGantt(selectedRun) }}>
              刷新
            </Button>
            <Button icon={<SendOutlined />} disabled={currentRun?.status !== 'COMPLETED'} loading={busy} onClick={publish}>
              发布排程
            </Button>
            <Button type="primary" icon={<CaretRightOutlined />} onClick={() => setRunOpen(true)}>
              运行排程
            </Button>
          </Space>
        }
      />

      <Row gutter={16} className="mb-4">
        <Col span={4}>
          <Card size="small"><Statistic title="排程批次" value={overview?.runs ?? 0} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="已发布批次" value={overview?.published_runs ?? 0} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="排程工序" value={overview?.operations ?? 0} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="排程异常" value={overview?.exceptions ?? 0} suffix={<span style={{ fontSize: 13, color: '#cf1322' }}>{overview?.critical_exceptions ? `/${overview.critical_exceptions} 严重` : ''}</span>} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="可用资源" value={overview?.active_resources ?? 0} suffix={`/ ${overview?.resources ?? 0}`} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="模拟场景" value={overview?.scenarios ?? 0} /></Card>
        </Col>
      </Row>

      <Card
        size="small"
        className="mb-4"
        title={
          <Space>
            <span>产能甘特图</span>
            {currentRun && (
              <>
                <StatusTag value={currentRun.status} map={RUN_STATUS} />
                <Tag>{SOURCE_TYPE[currentRun.source_type] ?? currentRun.source_type}</Tag>
                <Tag>{ALGORITHM[currentRun.algorithm] ?? currentRun.algorithm}</Tag>
                <span style={{ color: 'var(--ink-soft, #8c8c8c)', fontSize: 12 }}>
                  {fmtDateTime(currentRun.horizon_start)} ~ {fmtDateTime(currentRun.horizon_end)} · {currentRun.operation_count} 道工序 · {currentRun.exception_count} 条异常
                </span>
              </>
            )}
          </Space>
        }
        extra={
          <Select
            style={{ width: 260 }}
            placeholder="选择排程批次"
            value={selectedRun}
            onChange={(value) => setSelectedRun(value)}
            options={runs.map((item) => ({ value: item.run_number, label: `${item.run_number} · ${item.run_name ?? ''}` }))}
          />
        }
      >
        {gantt && timeline ? (
          <div>
            {/* 时间轴刻度 */}
            <div style={{ display: 'flex', paddingLeft: 130, marginBottom: 4 }}>
              <div style={{ position: 'relative', flex: 1, height: 18 }}>
                {ticks.map((tick, index) => (
                  <span
                    key={index}
                    style={{
                      position: 'absolute',
                      left: `${(index / tickCount) * 100}%`,
                      transform: index === tickCount ? 'translateX(-100%)' : 'none',
                      fontSize: 11,
                      color: '#8c8c8c',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {tick}
                  </span>
                ))}
              </div>
            </div>
            {gantt.gantt.map((row: any, rowIndex: number) => (
              <div key={row.work_center_id} style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                <Tooltip title={row.description}>
                  <div style={{ width: 130, flexShrink: 0, fontSize: 13, fontWeight: 500, paddingRight: 8 }}>
                    {row.work_center_id}
                    <span style={{ color: '#8c8c8c', fontWeight: 400 }}> ×{row.capacity}</span>
                  </div>
                </Tooltip>
                <div
                  style={{
                    position: 'relative',
                    flex: 1,
                    height: 30,
                    background: '#fafafa',
                    border: '1px solid #f0f0f0',
                    borderRadius: 4,
                  }}
                >
                  {row.operations.map((op: any) => {
                    const left = pct(op.planned_start, timeline.start, timeline.end)
                    const right = pct(op.planned_end, timeline.start, timeline.end)
                    const width = Math.max(right - left, 0.6)
                    return (
                      <Tooltip
                        key={op.op_id}
                        title={
                          <div>
                            <div>{op.title}</div>
                            <div>{fmtDateTime(op.planned_start)} → {fmtDateTime(op.planned_end)}</div>
                            <div>调机 {fmtMinutes(op.setup_minutes)} + 加工 {fmtMinutes(op.run_minutes)} · 数量 {op.planned_qty}</div>
                          </div>
                        }
                      >
                        <div
                          style={{
                            position: 'absolute',
                            left: `${left}%`,
                            width: `${width}%`,
                            top: 4,
                            height: 22,
                            background: BAR_COLORS[rowIndex % BAR_COLORS.length],
                            opacity: 0.85,
                            borderRadius: 3,
                            cursor: 'default',
                            overflow: 'hidden',
                            fontSize: 11,
                            color: '#fff',
                            lineHeight: '22px',
                            paddingLeft: 4,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {op.production_order_number}
                        </div>
                      </Tooltip>
                    )
                  })}
                </div>
              </div>
            ))}
            {gantt.gantt.length === 0 && <div style={{ color: '#8c8c8c', padding: 16 }}>该批次暂无排程工序</div>}
          </div>
        ) : (
          <div style={{ color: '#8c8c8c', padding: 24, textAlign: 'center' }}>
            {loading ? '加载中…' : '暂无排程数据，请先运行排程'}
          </div>
        )}
      </Card>

      <Card size="small" title="排程异常（本批次）">
        <Table
          rowKey="exception_id"
          size="small"
          columns={exceptionColumns}
          dataSource={exceptions}
          pagination={false}
          locale={{ emptyText: '本批次无排程异常' }}
        />
      </Card>

      <Modal
        title="运行 APS 排程"
        open={runOpen}
        onCancel={() => setRunOpen(false)}
        onOk={run}
        confirmLoading={busy}
        okText="开始排程"
        width={480}
        destroyOnClose
      >
        <p className="mb-2 text-sm text-ink-soft">
          系统将按工作中心有限产能对未完工单进行排程，已存在的同范围草稿批次会被重新计算。
        </p>
        <div className="mb-3">
          <div className="mb-1 text-sm">排程来源</div>
          <Select
            style={{ width: '100%' }}
            value={sourceType}
            onChange={setSourceType}
            options={[
              { value: 'PRODUCTION_ORDER', label: '生产订单（已下达 / 生产中）' },
              { value: 'PLANNED_ORDER', label: '计划订单（自制）' },
            ]}
          />
        </div>
        <div>
          <div className="mb-1 text-sm">排程算法</div>
          <Radio.Group value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}>
            <Radio.Button value="FORWARD">正排</Radio.Button>
            <Radio.Button value="BACKWARD">倒排</Radio.Button>
            <Radio.Button value="MIXED">混合</Radio.Button>
          </Radio.Group>
        </div>
      </Modal>
    </div>
  )
}

export default ApsWorkbench
