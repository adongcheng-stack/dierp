import { useEffect, useState } from 'react'
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd'
import { PlusOutlined, ReloadOutlined, SolutionOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { FAILURE_SEVERITY, FAILURE_STATUS, StatusTag, fmtDateTime } from './shared'

const EquipmentFailureList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [resources, setResources] = useState<any[]>([])
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [resolveTarget, setResolveTarget] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [reportForm] = Form.useForm()
  const [resolveForm] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/eam/failures', {
        params: { limit: 200, status: statusFilter },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取故障记录失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchResources = async () => {
    try {
      const response = await api.get('/planning/aps/resources', { params: { limit: 200 } })
      setResources(response.data.items ?? [])
    } catch {
      // 资源列表获取失败不阻塞页面
    }
  }

  useEffect(() => {
    fetchRows()
    fetchResources()
  }, [statusFilter])

  const submitReport = async () => {
    const values = await reportForm.validateFields()
    setBusy(true)
    try {
      const response = await api.post('/planning/eam/failures', {
        ...values,
        occurred_at: values.occurred_at ? values.occurred_at.format('YYYY-MM-DDTHH:mm:00') : undefined,
      })
      message.success(`故障 ${response.data.failure_number} 已上报`)
      setReportOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '上报故障失败')
    } finally {
      setBusy(false)
    }
  }

  const openResolve = (row: any) => {
    setResolveTarget(row)
    resolveForm.resetFields()
    resolveForm.setFieldsValue({ downtime_hours: row.downtime_hours ?? undefined })
  }

  const submitResolve = async () => {
    const values = await resolveForm.validateFields()
    setBusy(true)
    try {
      await api.post(`/planning/eam/failures/${resolveTarget.failure_number}/resolve`, values)
      message.success(`故障 ${resolveTarget.failure_number} 已关闭`)
      setResolveTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '关闭故障失败')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
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
    { title: '根本原因', dataIndex: 'root_cause', key: 'root_cause', ellipsis: true, render: (v: string) => v || '-' },
    { title: '处置措施', dataIndex: 'action_taken', key: 'action_taken', ellipsis: true, render: (v: string) => v || '-' },
    {
      title: '停机(h)',
      dataIndex: 'downtime_hours',
      key: 'downtime_hours',
      width: 90,
      align: 'right' as const,
      render: (value: number) => (value > 0 ? <span style={{ color: 'var(--color-error)' }}>{value}</span> : value),
    },
    { title: '发生时间', dataIndex: 'occurred_at', key: 'occurred_at', width: 160, render: fmtDateTime },
    { title: '解决时间', dataIndex: 'resolved_at', key: 'resolved_at', width: 160, render: fmtDateTime },
    { title: '上报人', dataIndex: 'reported_by', key: 'reported_by', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={FAILURE_STATUS} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_: any, row: any) =>
        row.status !== 'CLOSED' ? (
          <Button type="link" size="small" icon={<SolutionOutlined />} onClick={() => openResolve(row)}>
            解决
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <PageHeader
        title="设备故障"
        description="故障上报 → 根因分析 → 处置关闭的完整闭环；停机时长进入 OEE 可用率估算，资源停机联动 APS 排程异常"
        actions={
          <Space>
            <Select
              allowClear
              placeholder="状态筛选"
              style={{ width: 130 }}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
              options={Object.entries(FAILURE_STATUS).map(([value, item]) => ({ value, label: item.text }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => { reportForm.resetFields(); setReportOpen(true) }}>
              上报故障
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="failure_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1600 }}
      />

      <Modal
        title="上报设备故障"
        open={reportOpen}
        onCancel={() => setReportOpen(false)}
        onOk={submitReport}
        confirmLoading={busy}
        okText="上报"
        destroyOnClose
      >
        <Form form={reportForm} layout="vertical">
          <Form.Item
            name="resource_id"
            label="设备资源"
            rules={[{ required: true, message: '请选择设备资源' }]}
          >
            <Select
              placeholder="选择故障设备"
              options={resources.map((item) => ({
                value: item.resource_id,
                label: `${item.resource_id} · ${item.resource_name ?? ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="severity" label="严重程度" rules={[{ required: true }]} initialValue="MEDIUM">
            <Select
              options={Object.entries(FAILURE_SEVERITY).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="occurred_at" label="发生时间">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="downtime_hours" label="停机时长（小时）">
            <InputNumber min={0} max={720} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="description"
            label="故障描述"
            rules={[{ required: true, message: '请填写故障现象' }]}
          >
            <Input.TextArea rows={3} placeholder="故障现象、影响范围等" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`解决故障 ${resolveTarget?.failure_number ?? ''}`}
        open={!!resolveTarget}
        onCancel={() => setResolveTarget(null)}
        onOk={submitResolve}
        confirmLoading={busy}
        okText="确认关闭"
        destroyOnClose
      >
        <p className="mb-3">
          确认故障已处置完成。关闭后写入根因与措施，停机时长计入 OEE 可用率估算。
        </p>
        <Form form={resolveForm} layout="vertical">
          <Form.Item name="root_cause" label="根本原因" rules={[{ required: true, message: '请填写根本原因' }]}>
            <Input.TextArea rows={2} placeholder="5Why / 鱼骨图分析结论" />
          </Form.Item>
          <Form.Item name="action_taken" label="处置措施" rules={[{ required: true, message: '请填写处置措施' }]}>
            <Input.TextArea rows={2} placeholder="已采取的维修/更换/调整措施" />
          </Form.Item>
          <Form.Item name="downtime_hours" label="停机时长（小时）">
            <InputNumber min={0} max={720} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default EquipmentFailureList
