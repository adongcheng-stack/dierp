import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { CheckOutlined, PlusOutlined, ReloadOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const DELIVERY_STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  SHIPPED: { label: '已发货', color: 'processing' },
  DELIVERED: { label: '已签收', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface Delivery {
  delivery_number: string
  sales_order_number: string
  customer_id: string | null
  customer_name: string | null
  material_code: string
  quantity: number
  unit: string
  unit_price: number
  status: string
  ship_date: string | null
  delivery_date: string | null
  remarks: string | null
}

interface OrderOption {
  order_number: string
  customer_id: string | null
  material_code: string | null
  quantity: number
  status: string
}

const DeliveryList: React.FC = () => {
  const [rows, setRows] = useState<Delivery[]>([])
  const [total, setTotal] = useState(0)
  const [orders, setOrders] = useState<OrderOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [searchParams] = useSearchParams()
  const [numberFilter, setNumberFilter] = useState(() => searchParams.get('delivery_number') || '')
  const [orderFilter, setOrderFilter] = useState<string>('')
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (statusFilter) params.delivery_status = statusFilter
      if (orderFilter) params.order_number = orderFilter
      if (numberFilter) params.delivery_number = numberFilter
      const response = await api.get('/sd/deliveries', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载发货单失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchOrders = async () => {
    try {
      const response = await api.get('/sd/sales-orders', { params: { limit: 100 } })
      setOrders(response.data || [])
    } catch {
      // 订单选项加载失败不阻塞列表
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter, orderFilter, numberFilter])

  const openCreate = () => {
    form.resetFields()
    fetchOrders()
    setCreateOpen(true)
  }

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/sd/deliveries', {
        sales_order_number: values.sales_order_number,
        quantity: values.quantity,
        remarks: values.remarks || undefined,
      })
      message.success(`发货单 ${response.data.delivery_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建发货单失败')
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
    { title: '发货单号', dataIndex: 'delivery_number', width: 170 },
    { title: '销售订单', dataIndex: 'sales_order_number', width: 170 },
    { title: '客户', dataIndex: 'customer_name', width: 160, render: (v: string | null) => v || '-' },
    { title: '物料', dataIndex: 'material_code', width: 180 },
    {
      title: '数量',
      key: 'qty',
      width: 110,
      render: (_: unknown, r: Delivery) => `${r.quantity} ${r.unit}`,
    },
    { title: '单价', dataIndex: 'unit_price', width: 100, render: (v: number) => v?.toFixed(2) },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const s = DELIVERY_STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '发货时间', dataIndex: 'ship_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '签收时间', dataIndex: 'delivery_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '备注', dataIndex: 'remarks', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_: unknown, r: Delivery) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<SendOutlined />}
              onClick={() => act(`/sd/deliveries/${r.delivery_number}/ship`, `发货单 ${r.delivery_number} 已发货出库`)}>
              发货
            </Button>
          )}
          {r.status === 'SHIPPED' && (
            <Button size="small" icon={<CheckOutlined />}
              onClick={() => act(`/sd/deliveries/${r.delivery_number}/deliver`, `发货单 ${r.delivery_number} 已签收`)}>
              签收
            </Button>
          )}
          {(r.status === 'DRAFT' || r.status === 'SHIPPED') && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/sd/deliveries/${r.delivery_number}/cancel`, `发货单 ${r.delivery_number} 已作废`)}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="发货管理" description="按销售订单出库发货：发货扣成品库存并记流水，签收联动订单状态" />
      <Card
        extra={
          <Space>
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 130 }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={Object.entries(DELIVERY_STATUS).map(([k, v]) => ({ value: k, label: v.label }))}
            />
            <Input
              allowClear
              placeholder="销售订单号"
              style={{ width: 180 }}
              value={orderFilter}
              onChange={(e) => setOrderFilter(e.target.value)}
            />
            <Input
              allowClear
              placeholder="按单号过滤"
              style={{ width: 160 }}
              value={numberFilter}
              onChange={(event) => setNumberFilter(event.target.value)}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建发货单</Button>
          </Space>
        }
      >
        <Table rowKey="delivery_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1500 }} />
      </Card>

      <Modal
        title="新建发货单"
        open={createOpen}
        onOk={submitCreate}
        confirmLoading={busy}
        onCancel={() => setCreateOpen(false)}
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="sales_order_number" label="销售订单" rules={[{ required: true, message: '请选择销售订单' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="选择销售订单（余量不足时后端将拒绝）"
              options={orders.map((o) => ({
                value: o.order_number,
                label: `${o.order_number} · ${o.material_code || '-'} · 订购 ${o.quantity} · ${o.status}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="quantity" label="发货数量" rules={[{ required: true, message: '请输入发货数量' }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} placeholder="≤ 订单可发余量" />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DeliveryList
