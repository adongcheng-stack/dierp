import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, Tag, message } from 'antd'
import { DeleteOutlined, PlusOutlined, ReloadOutlined, RollbackOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  PAID: { label: '已收款', color: 'success' },
  REVERSED: { label: '已红冲', color: 'warning' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface Allocation {
  invoice_number: string
  allocated_amount: number
}

interface Receipt {
  receipt_number: string
  customer_id: string | null
  customer_name: string | null
  amount: number
  receipt_date: string | null
  method: string
  status: string
  remarks: string | null
  allocated_amount: number
  allocations: Allocation[]
}

interface CustomerOption {
  customer_id: string
  legal_name: string | null
  trade_name: string | null
}

interface InvoiceOption {
  invoice_number: string
  customer_id: string | null
  amount: number
  received_amount: number
  status: string
}

const ReceiptList: React.FC = () => {
  const [rows, setRows] = useState<Receipt[]>([])
  const [total, setTotal] = useState(0)
  const [customers, setCustomers] = useState<CustomerOption[]>([])
  const [invoices, setInvoices] = useState<InvoiceOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [payOpen, setPayOpen] = useState<Receipt | null>(null)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [searchParams] = useSearchParams()
  const [numberFilter, setNumberFilter] = useState(() => searchParams.get('receipt_number') || '')
  const [form] = Form.useForm()
  const [payForm] = Form.useForm()

  const payAllocations = Form.useWatch('allocations', payForm) as Allocation[] | undefined
  const payTotal = useMemo(
    () => (payAllocations || []).reduce((s, a) => s + (Number(a?.allocated_amount) || 0), 0),
    [payAllocations],
  )

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (numberFilter) params.receipt_number = numberFilter
      if (statusFilter) params.receipt_status = statusFilter
      const response = await api.get('/sd/receipts', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载收款单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter, numberFilter])

  const openCreate = async () => {
    form.resetFields()
    setCreateOpen(true)
    try {
      const response = await api.get('/sd/customers', { params: { limit: 100 } })
      setCustomers(response.data?.items || response.data || [])
    } catch {
      // 选项加载失败不阻塞
    }
  }

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/sd/receipts', {
        customer_id: values.customer_id,
        amount: values.amount,
        method: values.method || 'TRANSFER',
        remarks: values.remarks || undefined,
      })
      message.success(`收款单 ${response.data.receipt_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建收款单失败')
    } finally {
      setBusy(false)
    }
  }

  const openPay = async (r: Receipt) => {
    payForm.resetFields()
    payForm.setFieldsValue({ allocations: [{ invoice_number: undefined, allocated_amount: undefined }] })
    setPayOpen(r)
    try {
      const response = await api.get('/sd/invoices', { params: { customer_id: r.customer_id, limit: 100 } })
      setInvoices(
        (response.data.items || []).filter(
          (i: InvoiceOption) => i.status === 'ISSUED' || i.status === 'PARTIALLY_PAID',
        ),
      )
    } catch {
      setInvoices([])
    }
  }

  const submitPay = async () => {
    if (!payOpen) return
    try {
      const values = await payForm.validateFields()
      const allocations = (values.allocations || [])
        .filter((a: Allocation) => a.invoice_number && Number(a.allocated_amount) > 0)
        .map((a: Allocation) => ({ invoice_number: a.invoice_number, allocated_amount: Number(a.allocated_amount) }))
      if (allocations.length === 0) {
        message.warning('请至少核销一张发票')
        return
      }
      if (payTotal > payOpen.amount + 1e-6) {
        message.warning(`核销合计 ${payTotal.toFixed(2)} 超过收款金额 ${payOpen.amount.toFixed(2)}`)
        return
      }
      setBusy(true)
      const response = await api.post(`/sd/receipts/${payOpen.receipt_number}/pay`, { allocations })
      message.success(`收款单 ${response.data.receipt_number} 已核销 ${payTotal.toFixed(2)}`)
      setPayOpen(null)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '核销失败')
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
    { title: '收款单号', dataIndex: 'receipt_number', width: 170 },
    { title: '客户', dataIndex: 'customer_name', width: 170, render: (v: string | null) => v || '-' },
    { title: '金额', dataIndex: 'amount', width: 110, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    { title: '已核销', dataIndex: 'allocated_amount', width: 110, align: 'right' as const, render: (v: number) => (v ?? 0).toFixed(2) },
    { title: '方式', dataIndex: 'method', width: 90 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const s = STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '收款日期', dataIndex: 'receipt_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    {
      title: '核销明细',
      dataIndex: 'allocations',
      ellipsis: true,
      render: (v: Allocation[]) =>
        (v || []).map((a) => `${a.invoice_number}:${a.allocated_amount.toFixed(2)}`).join('，') || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 190,
      render: (_: unknown, r: Receipt) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<SendOutlined />} onClick={() => openPay(r)}>
              核销
            </Button>
          )}
          {r.status === 'DRAFT' && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/sd/receipts/${r.receipt_number}/cancel`, `收款单 ${r.receipt_number} 已作废`)}>
              作废
            </Button>
          )}
          {r.status === 'PAID' && (
            <Popconfirm
              title="红字冲回该收款单？"
              description="将回退发票已收金额、生成红字应收流水与红字凭证，操作不可自动撤销。"
              onConfirm={() => act(`/sd/receipts/${r.receipt_number}/reverse`, `收款单 ${r.receipt_number} 已红字冲回`)}
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
      <PageHeader title="收款单" description="收款核销冲减销售发票已收金额并联动核销状态，同时记应收流水（RECEIPT）" />
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
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建收款单</Button>
          </Space>
        }
      >
        <Table rowKey="receipt_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1300 }} />
      </Card>

      <Modal
        title="新建收款单"
        open={createOpen}
        onOk={submitCreate}
        confirmLoading={busy}
        onCancel={() => setCreateOpen(false)}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="customer_id" label="客户" rules={[{ required: true, message: '请选择客户' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={customers.map((c) => ({
                value: c.customer_id,
                label: `${c.customer_id} · ${c.trade_name || c.legal_name || '-'}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="amount" label="收款金额" rules={[{ required: true, message: '请输入金额' }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="method" label="收款方式" initialValue="TRANSFER">
            <Select options={[{ value: 'TRANSFER', label: '转账' }, { value: 'CASH', label: '现金' }, { value: 'BILL', label: '票据' }]} />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`收款核销 · ${payOpen?.receipt_number || ''}（金额 ${payOpen?.amount.toFixed(2) ?? '-'}）`}
        open={Boolean(payOpen)}
        onOk={submitPay}
        confirmLoading={busy}
        onCancel={() => setPayOpen(null)}
        width={640}
      >
        <div style={{ marginBottom: 8, color: 'var(--color-muted)' }}>
          核销合计：<strong>{payTotal.toFixed(2)}</strong> / {payOpen?.amount.toFixed(2) ?? '-'}
          （核销对象=该客户已开票/部分核销发票，后端校验不超未收余额）
        </div>
        <Form form={payForm} layout="vertical">
          <Form.List name="allocations">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="baseline" style={{ display: 'flex' }}>
                    <Form.Item
                      name={[field.name, 'invoice_number']}
                      rules={[{ required: true, message: '选择发票' }]}
                      style={{ width: 300 }}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        placeholder="可核销发票"
                        options={invoices.map((i) => ({
                          value: i.invoice_number,
                          label: `${i.invoice_number} · ${i.amount.toFixed(2)} · 已收 ${(i.received_amount || 0).toFixed(2)}`,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, 'allocated_amount']}
                      rules={[{ required: true, message: '金额' }]}
                    >
                      <InputNumber min={0.01} placeholder="核销金额" style={{ width: 150 }} />
                    </Form.Item>
                    <Button icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                  </Space>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()} block>
                  加一行核销
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  )
}

export default ReceiptList
