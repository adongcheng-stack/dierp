import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { ArrowRightOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  CONFIRMED: { label: '已确认', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface StockTransfer {
  transfer_number: string
  from_warehouse_code: string
  to_warehouse_code: string
  material_code: string
  quantity: number
  status: string
  transfer_date: string | null
  remarks: string | null
}

const StockTransferList: React.FC = () => {
  const [rows, setRows] = useState<StockTransfer[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (statusFilter) params.transfer_status = statusFilter
      const response = await api.get('/mm/stock-transfers', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载调拨单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter])

  const openCreate = () => {
    form.resetFields()
    setCreateOpen(true)
  }

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/mm/stock-transfers', {
        from_warehouse_code: values.from_warehouse_code,
        to_warehouse_code: values.to_warehouse_code,
        material_code: values.material_code,
        quantity: values.quantity,
        remarks: values.remarks || undefined,
      })
      message.success(`调拨单 ${response.data.transfer_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建调拨单失败')
    } finally {
      setBusy(false)
    }
  }

  const act = async (path: string, okText: string) => {
    try {
      await api.post(path)
      message.success(okText)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '操作失败')
    }
  }

  const columns = [
    { title: '调拨单号', dataIndex: 'transfer_number', width: 170 },
    {
      title: '调拨路径',
      key: 'route',
      width: 220,
      render: (_: unknown, r: StockTransfer) => (
        <Space size={4}>
          {r.from_warehouse_code}
          <ArrowRightOutlined style={{ color: 'var(--color-accent)' }} />
          {r.to_warehouse_code}
        </Space>
      ),
    },
    { title: '物料', dataIndex: 'material_code', width: 180 },
    { title: '数量', dataIndex: 'quantity', width: 100, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const s = STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '调拨日期', dataIndex: 'transfer_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '备注', dataIndex: 'remarks', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      render: (_: unknown, r: StockTransfer) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<ArrowRightOutlined />}
              onClick={() => act(`/mm/stock-transfers/${r.transfer_number}/confirm`, `调拨单 ${r.transfer_number} 已确认`)}>
              确认
            </Button>
          )}
          {r.status === 'DRAFT' && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/mm/stock-transfers/${r.transfer_number}/cancel`, `调拨单 ${r.transfer_number} 已作废`)}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="库存调拨" description="仓库间移库：确认后记调出/调入两笔流水，库存总量不变（demo 不迁移仓库字段）" />
      <Card
        extra={
          <Space>
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 120 }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={Object.entries(STATUS).map(([k, v]) => ({ value: k, label: v.label }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建调拨</Button>
          </Space>
        }
      >
        <Table rowKey="transfer_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1200 }} />
      </Card>

      <Modal
        title="新建调拨单"
        open={createOpen}
        onOk={submitCreate}
        confirmLoading={busy}
        onCancel={() => setCreateOpen(false)}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="from_warehouse_code" label="调出仓库" rules={[{ required: true, message: '请输入调出仓库编码' }]}>
            <Input placeholder="如 WH-PD01（须已存在）" />
          </Form.Item>
          <Form.Item name="to_warehouse_code" label="调入仓库" rules={[{ required: true, message: '请输入调入仓库编码' }]}>
            <Input placeholder="如 WH-PD02（须与调出不同）" />
          </Form.Item>
          <Form.Item name="material_code" label="物料编码" rules={[{ required: true, message: '请输入物料编码' }]}>
            <Input placeholder="如 HF1004ENIGAB01" />
          </Form.Item>
          <Form.Item name="quantity" label="调拨数量" rules={[{ required: true, message: '请输入数量' }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default StockTransferList
