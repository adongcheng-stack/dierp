import { useEffect, useState } from 'react'
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { MAINTENANCE_STATUS, MAINTENANCE_TYPE, StatusTag, fmtDate } from './shared'

const MaintenancePlanList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [resources, setResources] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/eam/plans', { params: { limit: 200 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取维护计划失败')
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
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ maintenance_type: 'INSPECTION', cycle_days: 30 })
    setFormOpen(true)
  }

  const openEdit = (row: any) => {
    setEditing(row)
    form.resetFields()
    form.setFieldsValue({
      resource_id: row.resource_id,
      maintenance_type: row.maintenance_type,
      cycle_days: row.cycle_days,
      next_due_at: row.next_due_at ? row.next_due_at.slice(0, 10) : undefined,
      responsible: row.responsible,
      notes: row.notes,
    })
    setFormOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      const payload = {
        ...values,
        next_due_at: values.next_due_at ? values.next_due_at.format('YYYY-MM-DDT08:00:00') : undefined,
      }
      if (editing) {
        await api.put(`/planning/eam/plans/${editing.plan_id}`, payload)
        message.success(`维护计划 ${editing.plan_id} 已更新`)
      } else {
        const response = await api.post('/planning/eam/plans', payload)
        message.success(`维护计划 ${response.data.plan_id} 已创建`)
      }
      setFormOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '保存维护计划失败')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
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
    { title: '上次执行', dataIndex: 'last_executed_at', key: 'last', width: 120, render: fmtDate },
    { title: '下次到期', dataIndex: 'next_due_at', key: 'next', width: 120, render: fmtDate },
    { title: '责任人', dataIndex: 'responsible', key: 'responsible', width: 110 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={MAINTENANCE_STATUS} />,
    },
    { title: '备注', dataIndex: 'notes', key: 'notes', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: any, row: any) => (
        <Button type="link" size="small" onClick={() => openEdit(row)}>
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="维护计划"
        description="按设备资源维护周期计划：到期后可一键生成维护工单，完成后自动顺延下次到期时间"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" onClick={openCreate}>
              新建维护计划
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="plan_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title={editing ? `编辑维护计划 ${editing.plan_id}` : '新建维护计划'}
        open={formOpen}
        onCancel={() => setFormOpen(false)}
        onOk={submit}
        confirmLoading={busy}
        okText={editing ? '保存' : '创建'}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="resource_id"
            label="设备资源"
            rules={[{ required: true, message: '请选择设备资源' }]}
          >
            <Select
              placeholder="选择 APS 设备资源"
              disabled={!!editing}
              options={resources.map((item) => ({
                value: item.resource_id,
                label: `${item.resource_id} · ${item.resource_name ?? ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="maintenance_type" label="维护类型" rules={[{ required: true }]}>
            <Select
              options={Object.entries(MAINTENANCE_TYPE).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="cycle_days" label="维护周期（天）" rules={[{ required: true }]}>
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="next_due_at" label="下次到期日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="responsible" label="责任人">
            <Input placeholder="维护责任人" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="维护内容说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default MaintenancePlanList
