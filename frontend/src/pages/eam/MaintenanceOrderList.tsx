import { useEffect, useState } from 'react'
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd'
import { CaretRightOutlined, CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { MAINTENANCE_STATUS, MAINTENANCE_TYPE, StatusTag, fmtDate, fmtDateTime } from './shared'

const MaintenanceOrderList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [completeTarget, setCompleteTarget] = useState<any>(null)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/eam/orders', {
        params: { limit: 200, status: statusFilter },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取维护工单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [statusFilter])

  const generateDueOrders = async () => {
    setBusy(true)
    try {
      const response = await api.post('/planning/eam/generate-due-orders', {})
      const count = response.data.generated ?? 0
      message.success(count > 0 ? `已自动生成 ${count} 张维护工单` : '当前没有到期的维护计划')
      setGenerateOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '生成到期保养工单失败')
    } finally {
      setBusy(false)
    }
  }

  const openComplete = (row: any) => {
    setCompleteTarget(row)
    form.resetFields()
    form.setFieldsValue({ downtime_hours: 1, executed_by: undefined })
  }

  const submitComplete = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      await api.post(`/planning/eam/orders/${completeTarget.order_number}/complete`, {
        downtime_hours: values.downtime_hours,
        executed_by: values.executed_by,
        result_note: values.result_note,
      })
      message.success(`维护工单 ${completeTarget.order_number} 已完成，来源计划已回写`)
      setCompleteTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '完成维护工单失败')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '工单编号', dataIndex: 'order_number', key: 'order_number', width: 160 },
    { title: '设备资源', dataIndex: 'resource_id', key: 'resource_id', width: 150 },
    { title: '来源计划', dataIndex: 'plan_id', key: 'plan_id', width: 170, render: (v: string) => v || '-' },
    {
      title: '维护类型',
      dataIndex: 'maintenance_type',
      key: 'maintenance_type',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={MAINTENANCE_TYPE} />,
    },
    { title: '计划日期', dataIndex: 'planned_date', key: 'planned_date', width: 120, render: fmtDate },
    { title: '完成时间', dataIndex: 'completed_at', key: 'completed_at', width: 160, render: fmtDateTime },
    {
      title: '停机(h)',
      dataIndex: 'downtime_hours',
      key: 'downtime_hours',
      width: 90,
      align: 'right' as const,
    },
    { title: '执行人', dataIndex: 'executed_by', key: 'executed_by', width: 100 },
    { title: '结果记录', dataIndex: 'result_note', key: 'result_note', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={MAINTENANCE_STATUS} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_: any, row: any) =>
        row.status === 'PLANNED' || row.status === 'IN_PROGRESS' ? (
          <Button type="link" size="small" icon={<CheckOutlined />} onClick={() => openComplete(row)}>
            完成
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <PageHeader
        title="维护工单"
        description="维护计划的执行单据：到期自动生成，完成时回写计划执行时间与下次到期时间"
        actions={
          <Space>
            <Select
              allowClear
              placeholder="状态筛选"
              style={{ width: 140 }}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
              options={Object.entries(MAINTENANCE_STATUS).map(([value, item]) => ({ value, label: item.text }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button icon={<CaretRightOutlined />} onClick={() => setGenerateOpen(true)}>
              生成到期保养单
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="order_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1400 }}
      />

      <Modal
        title={`完成维护工单 ${completeTarget?.order_number ?? ''}`}
        open={!!completeTarget}
        onCancel={() => setCompleteTarget(null)}
        onOk={submitComplete}
        confirmLoading={busy}
        okText="确认完成"
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="downtime_hours" label="停机时长（小时）">
            <InputNumber min={0} max={72} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="executed_by" label="执行人">
            <Input placeholder="维护执行人" />
          </Form.Item>
          <Form.Item name="result_note" label="执行结果">
            <Input.TextArea rows={3} placeholder="点检/维修结果、更换件、遗留问题等" />
          </Form.Item>
        </Form>
      </Modal>

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

export default MaintenanceOrderList
