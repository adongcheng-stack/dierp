import { useEffect, useState } from 'react'
import { Button, Card, Col, Modal, Row, Space, Statistic, Table, message } from 'antd'
import { CaretRightOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  FAILURE_SEVERITY,
  FAILURE_STATUS,
  MAINTENANCE_TYPE,
  StatusTag,
  fmtDateTime,
  fmtPct,
  oeeColor,
} from './shared'

const EamWorkbench: React.FC = () => {
  const [overview, setOverview] = useState<any>(null)
  const [oee, setOee] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [overviewResponse, oeeResponse] = await Promise.all([
        api.get('/planning/eam/overview'),
        api.get('/planning/eam/oee'),
      ])
      setOverview(overviewResponse.data)
      setOee(oeeResponse.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取 EAM 概览失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const generateDueOrders = async () => {
    setBusy(true)
    try {
      const response = await api.post('/planning/eam/generate-due-orders', {})
      const count = response.data.generated ?? 0
      message.success(count > 0 ? `已自动生成 ${count} 张维护工单` : '当前没有到期的维护计划')
      setGenerateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '生成到期保养工单失败')
    } finally {
      setBusy(false)
    }
  }

  const duePlanColumns = [
    { title: '计划编号', dataIndex: 'plan_id', key: 'plan_id', width: 170 },
    { title: '设备资源', dataIndex: 'resource_id', key: 'resource_id', width: 150 },
    {
      title: '维护类型',
      dataIndex: 'maintenance_type',
      key: 'maintenance_type',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={MAINTENANCE_TYPE} />,
    },
    { title: '周期(天)', dataIndex: 'cycle_days', key: 'cycle_days', width: 90, align: 'right' as const },
    { title: '下次到期', dataIndex: 'next_due_at', key: 'next_due_at', width: 160, render: fmtDateTime },
    { title: '责任人', dataIndex: 'responsible', key: 'responsible', width: 110 },
  ]

  const failureColumns = [
    { title: '故障编号', dataIndex: 'failure_number', key: 'failure_number', width: 160 },
    { title: '设备资源', dataIndex: 'resource_id', key: 'resource_id', width: 150 },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'work_center_id', width: 100 },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={FAILURE_SEVERITY} />,
    },
    { title: '故障描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '发生时间', dataIndex: 'occurred_at', key: 'occurred_at', width: 160, render: fmtDateTime },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={FAILURE_STATUS} />,
    },
  ]

  return (
    <div>
      <PageHeader
        title="设备管理工作台"
        description="设备台账（与 APS 资源打通）· 周期维护计划 · 维护工单 · 故障闭环 · OEE 简化估算"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<CaretRightOutlined />} onClick={() => setGenerateOpen(true)}>
              生成到期保养单
            </Button>
          </Space>
        }
      />

      <Row gutter={16} className="mb-4">
        <Col span={3}>
          <Card size="small"><Statistic title="维护计划" value={overview?.plans ?? 0} /></Card>
        </Col>
        <Col span={3}>
          <Card size="small">
            <Statistic
              title="到期保养"
              value={overview?.due_plans ?? 0}
              suffix={<span style={{ fontSize: 13, color: '#d46b08' }}>待生成</span>}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small">
            <Statistic
              title="维护工单"
              value={overview?.orders ?? 0}
              suffix={<span style={{ fontSize: 13, color: '#389e0d' }}>{overview?.orders_done ?? 0} 完成</span>}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small">
            <Statistic
              title="未关闭故障"
              value={overview?.open_failures ?? 0}
              suffix={
                <span style={{ fontSize: 13, color: '#cf1322' }}>
                  {overview?.critical_failures ? `${overview.critical_failures} 严重` : ''}
                </span>
              }
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small">
            <Statistic
              title="可用资源"
              value={(overview?.resources ?? 0) - (overview?.resources_down ?? 0)}
              suffix={`/ ${overview?.resources ?? 0}`}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="全厂 OEE（简化）"
              value={fmtPct(oee?.summary?.oee)}
              valueStyle={{ color: oeeColor(oee?.summary?.oee) }}
              suffix={
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>
                  A{fmtPct(oee?.summary?.availability, 0)} × P{fmtPct(oee?.summary?.performance, 0)} × Q
                  {fmtPct(oee?.summary?.quality, 0)}
                </span>
              }
            />
          </Card>
        </Col>
      </Row>

      <Card size="small" className="mb-4" title="OEE 按工作中心（可用率 × 性能率 × 良品率）">
        <Table
          rowKey="work_center_id"
          size="small"
          loading={loading}
          pagination={false}
          locale={{ emptyText: '暂无工作中心数据' }}
          dataSource={oee?.work_centers ?? []}
          columns={[
            { title: '工作中心', dataIndex: 'work_center_id', key: 'wc', width: 120 },
            { title: '说明', dataIndex: 'description', key: 'desc', ellipsis: true },
            { title: '班次(h)', dataIndex: 'shift_hours', key: 'shift', width: 80, align: 'right' as const },
            {
              title: '故障停机(h)',
              dataIndex: 'downtime_hours',
              key: 'downtime',
              width: 110,
              align: 'right' as const,
              render: (value: number) => (value > 0 ? <span style={{ color: '#cf1322' }}>{value}</span> : value),
            },
            {
              title: '可用率',
              dataIndex: 'availability',
              key: 'a',
              width: 90,
              render: (value: number) => <span style={{ color: oeeColor(value) }}>{fmtPct(value, 0)}</span>,
            },
            {
              title: '性能率',
              dataIndex: 'performance',
              key: 'p',
              width: 90,
              render: (value: number) => <span style={{ color: oeeColor(value) }}>{fmtPct(value, 0)}</span>,
            },
            {
              title: '良品率',
              dataIndex: 'quality',
              key: 'q',
              width: 90,
              render: (value: number) => <span style={{ color: oeeColor(value) }}>{fmtPct(value, 0)}</span>,
            },
            {
              title: 'OEE',
              dataIndex: 'oee',
              key: 'oee',
              width: 90,
              render: (value: number) => (
                <span style={{ color: oeeColor(value), fontWeight: 600 }}>{fmtPct(value)}</span>
              ),
            },
            {
              title: '停机资源',
              dataIndex: 'down_resources',
              key: 'down',
              width: 160,
              render: (value: string[]) => (value?.length ? value.join('、') : '-'),
            },
          ]}
        />
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card size="small" title="到期维护计划（next_due_at 已到）">
            <Table
              rowKey="plan_id"
              size="small"
              loading={loading}
              pagination={false}
              locale={{ emptyText: '没有到期维护计划' }}
              dataSource={overview?.due_plan_items ?? []}
              columns={duePlanColumns}
              scroll={{ x: 700 }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="未关闭故障（联动 APS 资源停机）">
            <Table
              rowKey="failure_number"
              size="small"
              loading={loading}
              pagination={false}
              locale={{ emptyText: '没有未关闭故障' }}
              dataSource={overview?.open_failure_items ?? []}
              columns={failureColumns}
              scroll={{ x: 700 }}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title="生成到期保养工单"
        open={generateOpen}
        onCancel={() => setGenerateOpen(false)}
        onOk={generateDueOrders}
        confirmLoading={busy}
        okText="开始生成"
      >
        <p>
          系统将扫描全部维护计划，为 <strong>next_due_at 已到期</strong> 的计划自动生成维护工单。
          同一计划同一日期不会重复生成，生成后计划的下次到期时间自动顺延一个周期。
        </p>
      </Modal>
    </div>
  )
}

export default EamWorkbench
