import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { CheckOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  CONFIRMED: { label: '已确认', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface SupplierInvoice {
  invoice_number: string
  purchase_order_number: string
  supplier_id: string | null
  supplier_name: string | null
  amount: number
  tax_amount: number
  status: string
  invoice_date: string | null
  remarks: string | null
}

interface PoOption {
  purchase_order_number: string
  supplier_name: string | null
  status: string
  lines: { line_number: number; received_quantity: number; unit_price: number }[]
}

const SupplierInvoiceList: React.FC = () => {
  const [rows, setRows] = useState<SupplierInvoice[]>([])
  const [total, setTotal] = useState(0)
  const [pos, setPos] = useState<PoOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [searchParams] = useSearchParams()
  const [numberFilter, setNumberFilter] = useState(() => searchParams.get('invoice_number') || '')
  const [form] = Form.useForm()

  const selectedPo = Form.useWatch('purchase_order_number', form)
  const poOption = pos.find((p) => p.purchase_order_number === selectedPo)
  const receivedValue = poOption
    ? poOption.lines.reduce((s, l) => s + (l.received_quantity || 0) * (l.unit_price || 0), 0)
    : 0

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (numberFilter) params.invoice_number = numberFilter
      if (statusFilter) params.invoice_status = statusFilter
      const response = await api.get('/purchase/supplier-invoices', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载采购发票失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, numberFilter])

  const openCreate = async () => {
    form.resetFields()
    setCreateOpen(true)
    try {
      const response = await api.get('/purchase/purchase-orders', { params: { limit: 100 } })
      setPos(response.data?.items || response.data || [])
    } catch {
      // 选项加载失败不阻塞
    }
  }

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/purchase/supplier-invoices', {
        purchase_order_number: values.purchase_order_number,
        amount: values.amount,
        tax_amount: values.tax_amount ?? 0,
        remarks: values.remarks || undefined,
      })
      message.success(`采购发票 ${response.data.invoice_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建采购发票失败')
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
    { title: '采购单', dataIndex: 'purchase_order_number', width: 170 },
    { title: '供应商', dataIndex: 'supplier_name', width: 170, render: (v: string | null) => v || '-' },
    { title: '金额(含税)', dataIndex: 'amount', width: 120, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    { title: '税额', dataIndex: 'tax_amount', width: 100, align: 'right' as const, render: (v: number) => (v ?? 0).toFixed(2) },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const s = STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '开票日期', dataIndex: 'invoice_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '备注', dataIndex: 'remarks', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      render: (_: unknown, r: SupplierInvoice) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<CheckOutlined />}
              onClick={() => act(`/purchase/supplier-invoices/${r.invoice_number}/confirm`, `发票 ${r.invoice_number} 已确认进应付`)}>
              确认
            </Button>
          )}
          {r.status === 'DRAFT' && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/purchase/supplier-invoices/${r.invoice_number}/cancel`, `发票 ${r.invoice_number} 已作废`)}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="采购发票" description="三单匹配：发票金额不得超过采购单已收货价值，确认后进入应付口径" />
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
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1300 }} />
      </Card>

      <Modal
        title="新建采购发票"
        open={createOpen}
        onOk={submitCreate}
        confirmLoading={busy}
        onCancel={() => setCreateOpen(false)}
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="purchase_order_number" label="采购单" rules={[{ required: true, message: '请选择采购单' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="选择采购单（已收货价值为可开票上限）"
              options={pos.map((p) => ({
                value: p.purchase_order_number,
                label: `${p.purchase_order_number} · ${p.supplier_name || '-'} · ${p.status}`,
              }))}
            />
          </Form.Item>
          {poOption && (
            <div style={{ marginBottom: 12, color: '#888' }}>
              已收货价值上限：<strong>{receivedValue.toFixed(2)}</strong>
            </div>
          )}
          <Form.Item name="amount" label="发票金额(含税)" rules={[{ required: true, message: '请输入金额' }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} placeholder="≤ 已收货价值（超匹配后端拒绝）" />
          </Form.Item>
          <Form.Item name="tax_amount" label="税额">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SupplierInvoiceList
