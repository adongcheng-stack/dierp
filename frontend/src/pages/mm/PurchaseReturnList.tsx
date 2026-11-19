import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { CheckOutlined, CloseOutlined, FileProtectOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const RETURN_TYPE: Record<string, { label: string; color: string }> = {
  RETURN: { label: '退货', color: 'orange' },
  CLAIM: { label: '索赔', color: 'purple' },
}

const RETURN_STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  APPROVED: { label: '已审批', color: 'success' },
  REJECTED: { label: '已驳回', color: 'error' },
  CLOSED: { label: '已关闭', color: 'default' },
}

interface ReturnLine {
  line_number: number
  purchase_order_line_number: number
  material_code: string
  quantity: number
  unit: string
  unit_price: number
}

interface PurchaseReturn {
  return_number: string
  purchase_order_number: string
  supplier_name: string | null
  return_type: string
  status: string
  return_date: string | null
  total_amount: number
  reason: string | null
  lines: ReturnLine[]
}

interface PoOption {
  purchase_order_number: string
  supplier_name: string | null
  status: string
  lines: { line_number: number; material_code: string; received_quantity: number; outstanding_quantity: number; unit: string; unit_price: number }[]
}

const PurchaseReturnList: React.FC = () => {
  const [rows, setRows] = useState<PurchaseReturn[]>([])
  const [orders, setOrders] = useState<PoOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const selectedPo = Form.useWatch('purchase_order_number', form)
  const selectedType = Form.useWatch('return_type', form)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/purchase/purchase-returns')
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取退货索赔单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    api.get('/purchase/purchase-orders')
      .then((r) => setOrders(r.data.items ?? []))
      .catch(() => setOrders([]))
  }, [])

  // 只允许对「已有到货」的采购单退货/索赔
  const returnableOrders = useMemo(
    () => orders.filter((o) => o.lines.some((l) => l.received_quantity > 0)),
    [orders]
  )
  const selectedOrder = useMemo(
    () => returnableOrders.find((o) => o.purchase_order_number === selectedPo),
    [returnableOrders, selectedPo]
  )

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({ return_type: 'RETURN' })
    setCreateOpen(true)
  }

  const submitCreate = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      const lines = (values.lines ?? [])
        .filter((line: any) => line?.purchase_order_line_number != null && Number(line.quantity) > 0)
        .map((line: any) => ({
          purchase_order_line_number: line.purchase_order_line_number,
          quantity: Number(line.quantity),
        }))
      if (lines.length === 0) {
        message.warning('请至少为一行填写大于 0 的数量')
        setBusy(false)
        return
      }
      const response = await api.post('/purchase/purchase-returns', {
        purchase_order_number: values.purchase_order_number,
        return_type: values.return_type,
        reason: values.reason || undefined,
        lines,
      })
      message.success(`退货索赔单 ${response.data.return_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建退货索赔单失败')
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
    { title: '单号', dataIndex: 'return_number', key: 'n', width: 170 },
    {
      title: '采购单', dataIndex: 'purchase_order_number', key: 'po', width: 165,
      render: (v: string) =>
        v ? (
          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => navigate('/mm/purchase-orders')}>
            {v}
          </Button>
        ) : ('-'),
    },
    { title: '供应商', dataIndex: 'supplier_name', key: 'sup', width: 140, render: (v: string | null) => v || '-' },
    {
      title: '类型', dataIndex: 'return_type', key: 't', width: 90,
      render: (v: string) => <Tag color={RETURN_TYPE[v]?.color ?? 'default'}>{RETURN_TYPE[v]?.label ?? v}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', key: 's', width: 95,
      render: (v: string) => <Tag color={RETURN_STATUS[v]?.color ?? 'default'}>{RETURN_STATUS[v]?.label ?? v}</Tag>,
    },
    { title: '日期', dataIndex: 'return_date', key: 'd', width: 110, render: (v: string | null) => (v ? v.slice(0, 10) : '-') },
    {
      title: '金额', dataIndex: 'total_amount', key: 'amt', width: 110, align: 'right' as const,
      render: (v: number) => `¥${Number(v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
    },
    { title: '原因', dataIndex: 'reason', key: 'r', ellipsis: true },
    {
      title: '操作', key: 'act', width: 190,
      render: (_: unknown, row: PurchaseReturn) => (
        <Space>
          {row.status === 'DRAFT' && row.return_type === 'RETURN' && (
            <Button size="small" type="primary" icon={<CheckOutlined />}
              onClick={() => act(`/purchase/purchase-returns/${row.return_number}/approve`, '退货已审批，库存已扣减')}>
              审批退货
            </Button>
          )}
          {row.status === 'DRAFT' && row.return_type === 'CLAIM' && (
            <Button size="small" type="primary" icon={<CheckOutlined />}
              onClick={() => act(`/purchase/purchase-returns/${row.return_number}/approve`, '索赔已确认')}>
              确认索赔
            </Button>
          )}
          {row.status === 'DRAFT' && (
            <Button size="small" danger icon={<CloseOutlined />}
              onClick={() => act(`/purchase/purchase-returns/${row.return_number}/reject`, '已驳回')}>
              驳回
            </Button>
          )}
          {row.status === 'APPROVED' && (
            <Button size="small" icon={<FileProtectOutlined />}
              onClick={() => act(`/purchase/purchase-returns/${row.return_number}/close`, '已关闭')}>
              关闭
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const expandedRowRender = (record: PurchaseReturn) => (
    <Table
      rowKey="line_number" size="small" pagination={false} dataSource={record.lines}
      columns={[
        { title: '行', dataIndex: 'line_number', key: 'ln', width: 60 },
        { title: '来源采购行', dataIndex: 'purchase_order_line_number', key: 'pol', width: 100 },
        { title: '物料', dataIndex: 'material_code', key: 'm', width: 150 },
        { title: '数量', dataIndex: 'quantity', key: 'q', width: 90, align: 'right' as const },
        { title: '单位', dataIndex: 'unit', key: 'u', width: 70 },
        { title: '单价', dataIndex: 'unit_price', key: 'p', width: 100, align: 'right' as const },
      ]}
    />
  )

  return (
    <div>
      <PageHeader
        title="退货 / 索赔"
        description="针对已到货物资：退货（RETURN）审批后扣减库存并冲减应付；索赔（CLAIM）只登记金额，不动库存"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
        }
      />
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建退货 / 索赔</Button>
      </Space>
      <Card>
        <Table
          rowKey="return_number"
          columns={columns}
          dataSource={rows}
          loading={loading}
          expandable={{ expandedRowRender }}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 张` }}
          size="middle"
        />
      </Card>

      <Modal
        title="新建退货 / 索赔"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={submitCreate}
        confirmLoading={busy}
        okText="创建"
        width={760}
        forceRender
      >
        <Form form={form} layout="vertical">
          <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
            <Form.Item name="return_type" label="类型" style={{ width: 180, marginRight: 12 }}
              rules={[{ required: true, message: '请选择类型' }]}>
              <Select
                options={Object.entries(RETURN_TYPE).map(([value, item]) => ({ value, label: item.label }))}
              />
            </Form.Item>
            <Form.Item name="purchase_order_number" label="采购单（须已有到货）" style={{ flex: 1 }}
              rules={[{ required: true, message: '请选择采购单' }]}>
              <Select
                showSearch placeholder="选择采购单" optionFilterProp="label"
                options={returnableOrders.map((o) => ({
                  value: o.purchase_order_number,
                  label: `${o.purchase_order_number} ${o.supplier_name ?? ''}（${RETURN_STATUS[o.status]?.label ?? o.status}）`,
                }))}
              />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="reason" label="原因">
            <Input.TextArea rows={2} placeholder="质量问题描述 / 退货原因" />
          </Form.Item>

          {selectedOrder && (
            <Form.List name="lines">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => (
                    <Space.Compact key={field.key} style={{ width: '100%', marginBottom: 8 }}>
                      <Form.Item
                        name={[field.name, 'purchase_order_line_number']} noStyle
                        rules={[{ required: true, message: '选择采购行' }]}
                      >
                        <Select
                          showSearch placeholder="选择采购行（已到货）" style={{ width: '50%' }} optionFilterProp="label"
                          options={selectedOrder.lines
                            .filter((l) => l.received_quantity > 0)
                            .map((l) => ({
                              value: l.line_number,
                              label: `行${l.line_number} ${l.material_code}（已收 ${l.received_quantity} ${l.unit}）`,
                            }))}
                        />
                      </Form.Item>
                      <Form.Item
                        name={[field.name, 'quantity']} noStyle
                        rules={[{ required: true, message: '数量' }]}
                      >
                        <InputNumber min={0.01} placeholder={selectedType === 'CLAIM' ? '索赔数量' : '退货数量'} style={{ width: '30%' }} />
                      </Form.Item>
                      <Button danger type="link" onClick={() => remove(field.name)}>删</Button>
                    </Space.Compact>
                  ))}
                  <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ purchase_order_line_number: undefined, quantity: 1 })}>
                    添加行
                  </Button>
                </>
              )}
            </Form.List>
          )}
        </Form>
      </Modal>
    </div>
  )
}

export default PurchaseReturnList
