import { useEffect, useState } from 'react'
import { Button, Card, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, Tag, message } from 'antd'
import { FileDoneOutlined, PlusOutlined, ReloadOutlined, RollbackOutlined } from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const INVOICE_STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  ISSUED: { label: '已开票', color: 'processing' },
  PARTIALLY_PAID: { label: '部分核销', color: 'warning' },
  PAID: { label: '已核销', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface Invoice {
  invoice_number: string
  sales_order_number: string
  delivery_number: string | null
  customer_id: string | null
  customer_name: string | null
  amount: number
  currency: string
  status: string
  invoice_date: string | null
  due_date: string | null
  received_amount: number
  remarks: string | null
}

interface OrderOption {
  order_number: string
  customer_id: string | null
  quantity: number
  unit_price: number
  status: string
}

interface DeliveryOption {
  delivery_number: string
  sales_order_number: string
  status: string
  quantity: number
}

const InvoiceList: React.FC = () => {
  const [rows, setRows] = useState<Invoice[]>([])
  const [total, setTotal] = useState(0)
  const [orders, setOrders] = useState<OrderOption[]>([])
  const [deliveries, setDeliveries] = useState<DeliveryOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  // searchParams 必须先声明：下面的 numberFilter 初始化闭包会立即读取它
  const [searchParams] = useSearchParams()
  const [numberFilter, setNumberFilter] = useState(() => searchParams.get('invoice_number') || '')
  const [customerFilter, setCustomerFilter] = useState<string>('')
  const [form] = Form.useForm()

  const selectedOrder = Form.useWatch('sales_order_number', form)

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (statusFilter) params.invoice_status = statusFilter
      if (customerFilter) params.customer_id = customerFilter
      if (numberFilter) params.invoice_number = numberFilter
      const response = await api.get('/sd/invoices', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载发票失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const fromUrl = searchParams.get('customer_id') || ''
    setCustomerFilter(fromUrl)
  }, [])

  useEffect(() => {
    fetchData()
  }, [statusFilter, customerFilter, numberFilter])

  const openCreate = async () => {
    form.resetFields()
    setCreateOpen(true)
    try {
      const response = await api.get('/sd/sales-orders', { params: { limit: 100 } })
      setOrders(response.data || [])
    } catch {
      // 订单选项加载失败不阻塞
    }
  }

  // 选定订单后加载其可挂的已发货单
  useEffect(() => {
    if (!createOpen || !selectedOrder) {
      setDeliveries([])
      return
    }
    let cancelled = false
    const load = async () => {
      try {
        const response = await api.get('/sd/deliveries', { params: { order_number: selectedOrder, limit: 50 } })
        if (!cancelled) {
          setDeliveries(
            (response.data.items || []).filter(
              (d: DeliveryOption) => d.status === 'SHIPPED' || d.status === 'DELIVERED',
            ),
          )
        }
      } catch {
        if (!cancelled) setDeliveries([])
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [selectedOrder, createOpen])

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/sd/invoices', {
        sales_order_number: values.sales_order_number,
        delivery_number: values.delivery_number || undefined,
        amount: values.amount,
        due_date: values.due_date ? dayjs(values.due_date).format('YYYY-MM-DDTHH:mm:ss') : undefined,
        remarks: values.remarks || undefined,
      })
      message.success(`发票 ${response.data.invoice_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建发票失败')
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
    { title: '发票号', dataIndex: 'invoice_number', width: 170 },
    { title: '销售订单', dataIndex: 'sales_order_number', width: 170 },
    { title: '关联发货单', dataIndex: 'delivery_number', width: 170, render: (v: string | null) => v || '-' },
    { title: '客户', dataIndex: 'customer_name', width: 160, render: (v: string | null) => v || '-' },
    {
      title: '金额',
      key: 'amount',
      width: 130,
      render: (_: unknown, r: Invoice) => `${r.amount?.toFixed(2)} ${r.currency || ''}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (v: string) => {
        const s = INVOICE_STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '已核销',
      dataIndex: 'received_amount',
      width: 110,
      render: (v: number, r: Invoice) =>
        r.status === 'DRAFT' ? '-' : (v ?? 0).toFixed(2),
    },
    { title: '开票日期', dataIndex: 'invoice_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '到期日', dataIndex: 'due_date', width: 120, render: (v: string | null) => (v ? v.slice(0, 10) : '-') },
    { title: '备注', dataIndex: 'remarks', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: unknown, r: Invoice) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<FileDoneOutlined />}
              onClick={() => act(`/sd/invoices/${r.invoice_number}/issue`, `发票 ${r.invoice_number} 已开票并生成应收`)}>
              确认开票
            </Button>
          )}
          {(r.status === 'ISSUED' || r.status === 'PARTIALLY_PAID') && Number(r.received_amount || 0) === 0 && (
            <Popconfirm
              title="红字冲回该发票？"
              description="生成负向应收流水与红字凭证，发票转为已作废；已有收款须先红冲收款单。"
              onConfirm={() => act(`/sd/invoices/${r.invoice_number}/reverse`, `发票 ${r.invoice_number} 已红字冲回`)}
            >
              <Button size="small" danger icon={<RollbackOutlined />}>红字冲回</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="销售发票" description="对已发货数量开票：确认开票生成应收流水，核销情况见应收台账" />
      <Card
        extra={
          <Space>
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 130 }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={Object.entries(INVOICE_STATUS).map(([k, v]) => ({ value: k, label: v.label }))}
            />
            <Input
              allowClear
              placeholder="客户编码"
              style={{ width: 150 }}
              value={customerFilter}
              onChange={(e) => setCustomerFilter(e.target.value)}
            />
            <Input
              allowClear
              placeholder="按单号过滤"
              style={{ width: 160 }}
              value={numberFilter}
              onChange={(event) => setNumberFilter(event.target.value)}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建发票</Button>
          </Space>
        }
      >
        <Table rowKey="invoice_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1500 }} />
      </Card>

      <Modal
        title="新建销售发票"
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
              placeholder="选择销售订单（可开票上限=已发货量×单价）"
              options={orders.map((o) => ({
                value: o.order_number,
                label: `${o.order_number} · 订购 ${o.quantity} × ${o.unit_price} · ${o.status}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="delivery_number" label="关联发货单（可空）">
            <Select
              allowClear
              placeholder={selectedOrder ? '仅显示该订单已发货的单' : '先选择销售订单'}
              disabled={!selectedOrder}
              options={deliveries.map((d) => ({
                value: d.delivery_number,
                label: `${d.delivery_number} · ${d.quantity} · ${d.status}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="amount" label="开票金额" rules={[{ required: true, message: '请输入开票金额' }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} placeholder="≤ 已发货可开票上限（超开后端拒绝）" />
          </Form.Item>
          <Form.Item name="due_date" label="到期日（默认取订单交付期）">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default InvoiceList
