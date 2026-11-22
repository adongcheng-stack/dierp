import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { DeleteOutlined, PlusOutlined, ReloadOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  PAID: { label: '已支付', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface Allocation {
  invoice_number: string
  allocated_amount: number
}

interface Payment {
  payment_number: string
  supplier_id: string | null
  supplier_name: string | null
  amount: number
  payment_date: string | null
  method: string
  status: string
  remarks: string | null
  allocated_amount: number
  allocations: Allocation[]
}

interface SupplierOption {
  supplier_code: string
  supplier_name: string | null
}

interface InvoiceOption {
  invoice_number: string
  supplier_id: string | null
  amount: number
  status: string
}

const PaymentList: React.FC = () => {
  const [rows, setRows] = useState<Payment[]>([])
  const [total, setTotal] = useState(0)
  const [suppliers, setSuppliers] = useState<SupplierOption[]>([])
  const [invoices, setInvoices] = useState<InvoiceOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [payOpen, setPayOpen] = useState<Payment | null>(null)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [searchParams] = useSearchParams()
  const [numberFilter, setNumberFilter] = useState(() => searchParams.get('payment_number') || '')
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
      if (numberFilter) params.payment_number = numberFilter
      if (statusFilter) params.payment_status = statusFilter
      const response = await api.get('/purchase/payments', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载付款单失败')
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
      const response = await api.get('/purchase/suppliers', { params: { limit: 100 } })
      setSuppliers(response.data?.items || response.data || [])
    } catch {
      // 选项加载失败不阻塞
    }
  }

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/purchase/payments', {
        supplier_id: values.supplier_id,
        amount: values.amount,
        method: values.method || 'TRANSFER',
        remarks: values.remarks || undefined,
      })
      message.success(`付款单 ${response.data.payment_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建付款单失败')
    } finally {
      setBusy(false)
    }
  }

  const openPay = async (p: Payment) => {
    payForm.resetFields()
    payForm.setFieldsValue({ allocations: [{ invoice_number: undefined, allocated_amount: undefined }] })
    setPayOpen(p)
    try {
      const response = await api.get('/purchase/supplier-invoices', {
        params: { supplier_id: p.supplier_id, invoice_status: 'CONFIRMED', limit: 100 },
      })
      setInvoices(response.data.items || [])
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
        message.warning(`核销合计 ${payTotal.toFixed(2)} 超过付款金额 ${payOpen.amount.toFixed(2)}`)
        return
      }
      setBusy(true)
      const response = await api.post(`/purchase/payments/${payOpen.payment_number}/pay`, { allocations })
      message.success(`付款单 ${response.data.payment_number} 已支付并核销 ${payTotal.toFixed(2)}`)
      setPayOpen(null)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '支付失败')
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
    { title: '付款单号', dataIndex: 'payment_number', width: 170 },
    { title: '供应商', dataIndex: 'supplier_name', width: 170, render: (v: string | null) => v || '-' },
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
    { title: '付款日期', dataIndex: 'payment_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
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
      render: (_: unknown, r: Payment) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<SendOutlined />} onClick={() => openPay(r)}>
              支付/核销
            </Button>
          )}
          {r.status === 'DRAFT' && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/purchase/payments/${r.payment_number}/cancel`, `付款单 ${r.payment_number} 已作废`)}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="付款单" description="支付时按核销明细冲减采购发票已付额，一单可核销多张发票" />
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
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建付款单</Button>
          </Space>
        }
      >
        <Table rowKey="payment_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1300 }} />
      </Card>

      <Modal
        title="新建付款单"
        open={createOpen}
        onOk={submitCreate}
        confirmLoading={busy}
        onCancel={() => setCreateOpen(false)}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="supplier_id" label="供应商" rules={[{ required: true, message: '请选择供应商' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={suppliers.map((s) => ({
                value: s.supplier_code,
                label: `${s.supplier_code} · ${s.supplier_name || '-'}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="amount" label="付款金额" rules={[{ required: true, message: '请输入金额' }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="method" label="付款方式" initialValue="TRANSFER">
            <Select options={[{ value: 'TRANSFER', label: '转账' }, { value: 'CASH', label: '现金' }, { value: 'BILL', label: '票据' }]} />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`支付/核销 · ${payOpen?.payment_number || ''}（金额 ${payOpen?.amount.toFixed(2) ?? '-'}）`}
        open={Boolean(payOpen)}
        onOk={submitPay}
        confirmLoading={busy}
        onCancel={() => setPayOpen(null)}
        width={640}
      >
        <div style={{ marginBottom: 8, color: 'var(--color-muted)' }}>
          核销合计：<strong>{payTotal.toFixed(2)}</strong> / {payOpen?.amount.toFixed(2) ?? '-'}
          （核销对象=该供应商已确认发票，后端校验单票累计不超发票额）
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
                      style={{ width: 280 }}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        placeholder="已确认发票"
                        options={invoices.map((i) => ({
                          value: i.invoice_number,
                          label: `${i.invoice_number} · ${i.amount.toFixed(2)}`,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, 'allocated_amount']}
                      rules={[{ required: true, message: '金额' }]}
                    >
                      <InputNumber min={0.01} placeholder="核销金额" style={{ width: 160 }} />
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

export default PaymentList
