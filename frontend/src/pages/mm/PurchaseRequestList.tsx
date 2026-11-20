import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { CheckOutlined, FileDoneOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const PR_STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  RELEASED: { label: '已下达', color: 'processing' },
  PARTIALLY_CONVERTED: { label: '部分转换', color: 'orange' },
  CONVERTED: { label: '已转采购单', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

const LINE_STATUS: Record<string, { label: string; color: string }> = {
  OPEN: { label: '待转换', color: 'processing' },
  CONVERTED: { label: '已转换', color: 'success' },
}

interface PrLine {
  line_number: number
  material_code: string
  quantity: number
  unit: string
  unit_price: number
  status: string
  converted_quantity: number
  remaining_quantity: number
}

interface PurchaseRequest {
  purchase_request_number: string
  supplier_id: string | null
  supplier_name: string | null
  status: string
  request_date: string | null
  expected_date: string | null
  currency: string
  total_amount: number
  requested_by: string | null
  converted_po_number: string | null
  converted_po_numbers: string | null
  remarks: string | null
  lines: PrLine[]
}

interface MaterialOption {
  material_code: string
  material_name: string
  unit: string
}

const PurchaseRequestList: React.FC = () => {
  const [rows, setRows] = useState<PurchaseRequest[]>([])
  const [materials, setMaterials] = useState<MaterialOption[]>([])
  const [suppliers, setSuppliers] = useState<{ supplier_code: string; supplier_name: string }[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [partialOpen, setPartialOpen] = useState<PurchaseRequest | null>(null)
  const [selectedLineKeys, setSelectedLineKeys] = useState<number[]>([])
  const [lineQtyOverrides, setLineQtyOverrides] = useState<Record<number, number>>({})
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/purchase/purchase-requests')
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取采购申请失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    api.get('/purchase/suppliers/refs').then((r) => setSuppliers(r.data ?? [])).catch(() => setSuppliers([]))
    api.get('/mm/materials', { params: { limit: 500 } })
      .then((r) => setMaterials(r.data ?? []))
      .catch(() => setMaterials([]))
  }, [])

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({ lines: [{ material_code: undefined, quantity: 1, unit_price: 0 }] })
    setCreateOpen(true)
  }

  const submitCreate = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      const lines = (values.lines ?? []).map((line: any) => ({
        material_code: line.material_code,
        quantity: Number(line.quantity),
        unit_price: Number(line.unit_price ?? 0),
        remarks: line.remarks || undefined,
      }))
      const response = await api.post('/purchase/purchase-requests', {
        supplier_id: values.supplier_id,
        supplier_name: suppliers.find((s) => s.supplier_code === values.supplier_id)?.supplier_name,
        requested_by: values.requested_by || undefined,
        remarks: values.remarks || undefined,
        lines,
      })
      message.success(`采购申请 ${response.data.purchase_request_number} 已创建`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建采购申请失败')
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

  const openPartial = (row: PurchaseRequest) => {
    setPartialOpen(row)
    const openLines = row.lines.filter((l) => l.status !== 'CONVERTED')
    setSelectedLineKeys(openLines.length === 1 ? [openLines[0].line_number] : [])
    setLineQtyOverrides({})
  }

  const submitPartial = async () => {
    if (!partialOpen || selectedLineKeys.length === 0) {
      message.warning('请至少选择一行进行转换')
      return
    }
    const lines = partialOpen.lines
      .filter((l) => selectedLineKeys.includes(l.line_number))
      .map((l) => ({
        line_number: l.line_number,
        quantity: lineQtyOverrides[l.line_number] ?? l.remaining_quantity,
      }))
    setBusy(true)
    try {
      const response = await api.post(
        `/purchase/purchase-requests/${partialOpen.purchase_request_number}/convert-lines`,
        { lines },
      )
      message.success(`已生成采购单 ${response.data.new_po_number}`)
      setPartialOpen(null)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '部分转换失败')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '申请单号', dataIndex: 'purchase_request_number', key: 'n', width: 175 },
    { title: '供应商', dataIndex: 'supplier_name', key: 'sup', width: 150, render: (v: string | null) => v || '-' },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 110,
      render: (v: string) => <Tag color={PR_STATUS[v]?.color ?? 'default'}>{PR_STATUS[v]?.label ?? v}</Tag>,
    },
    { title: '申请日期', dataIndex: 'request_date', key: 'd', width: 110, render: (v: string | null) => (v ? v.slice(0, 10) : '-') },
    { title: '期望到货', dataIndex: 'expected_date', key: 'e', width: 110, render: (v: string | null) => (v ? v.slice(0, 10) : '-') },
    {
      title: '预估金额', dataIndex: 'total_amount', key: 'amt', width: 110, align: 'right' as const,
      render: (v: number) => `¥${Number(v ?? 0).toLocaleString()}`,
    },
    { title: '申请人', dataIndex: 'requested_by', key: 'by', width: 90, render: (v: string | null) => v || '-' },
    {
      title: '转出采购单', dataIndex: 'converted_po_numbers', key: 'po', width: 200,
      render: (v: string | null, row: PurchaseRequest) => {
        const numbers = (v || row.converted_po_number || '').split(',').filter(Boolean)
        return numbers.length ? (
          <Space size={0} wrap>
            {numbers.map((n) => (
              <Button key={n} type="link" size="small" onClick={() => navigate('/mm/purchase-orders')}>{n}</Button>
            ))}
          </Space>
        ) : ('-')
      },
    },
    { title: '备注', dataIndex: 'remarks', key: 'r', ellipsis: true },
    {
      title: '操作', key: 'act', width: 210,
      render: (_: unknown, row: PurchaseRequest) => (
        <Space>
          {row.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<CheckOutlined />}
              onClick={() => act(`/purchase/purchase-requests/${row.purchase_request_number}/release`, '采购申请已下达')}>
              下达
            </Button>
          )}
          {row.status === 'RELEASED' && (
            <Button size="small" type="primary" icon={<FileDoneOutlined />}
              onClick={() => act(`/purchase/purchase-requests/${row.purchase_request_number}/convert`, '已转采购单')}>
              整单转换
            </Button>
          )}
          {['RELEASED', 'PARTIALLY_CONVERTED'].includes(row.status) && (
            <Button size="small" icon={<FileDoneOutlined />} onClick={() => openPartial(row)}>
              部分转换
            </Button>
          )}
          {['DRAFT', 'RELEASED'].includes(row.status) && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/purchase/purchase-requests/${row.purchase_request_number}/cancel`, '采购申请已作废')}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const expandedRowRender = (record: PurchaseRequest) => (
    <Table
      rowKey="line_number" size="small" pagination={false} dataSource={record.lines}
      columns={[
        { title: '行', dataIndex: 'line_number', key: 'ln', width: 60 },
        { title: '物料', dataIndex: 'material_code', key: 'm', width: 150 },
        { title: '数量', dataIndex: 'quantity', key: 'q', width: 90, align: 'right' as const },
        { title: '单位', dataIndex: 'unit', key: 'u', width: 70 },
        { title: '预估单价', dataIndex: 'unit_price', key: 'p', width: 100, align: 'right' as const },
        {
          title: '行状态', dataIndex: 'status', key: 's', width: 100,
          render: (v: string) => <Tag color={LINE_STATUS[v]?.color ?? 'default'}>{LINE_STATUS[v]?.label ?? v}</Tag>,
        },
      ]}
    />
  )

  return (
    <div>
      <PageHeader
        title="采购申请"
        description="需求方提出采购申请：下达后可整单或按行部分转采购单（支持部分数量、多次转换），转换后可到货收货"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
        }
      />
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建采购申请</Button>
      </Space>
      <Card>
        <Table
          rowKey="purchase_request_number"
          columns={columns}
          dataSource={rows}
          loading={loading}
          expandable={{ expandedRowRender }}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 张` }}
          size="middle"
        />
      </Card>

      <Modal
        title="新建采购申请"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={submitCreate}
        confirmLoading={busy}
        okText="创建"
        width={720}
        forceRender
      >
        <Form form={form} layout="vertical">
          <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
            <Form.Item name="supplier_id" label="供应商" style={{ flex: 1, marginRight: 12 }}>
              <Select
                allowClear placeholder="选择供应商（可空）"
                options={suppliers.map((s) => ({ value: s.supplier_code, label: `${s.supplier_code} ${s.supplier_name}` }))}
                optionFilterProp="label" showSearch
              />
            </Form.Item>
            <Form.Item name="requested_by" label="申请人" style={{ width: 160 }}>
              <Input placeholder="申请人" />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="申请说明" />
          </Form.Item>
          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space.Compact key={field.key} style={{ width: '100%', marginBottom: 8 }}>
                    <Form.Item
                      name={[field.name, 'material_code']} noStyle
                      rules={[{ required: true, message: '请选择物料' }]}
                    >
                      <Select
                        showSearch placeholder="选择物料" style={{ width: '45%' }} optionFilterProp="label"
                        options={materials.map((m) => ({ value: m.material_code, label: `${m.material_code} ${m.material_name ?? ''}` }))}
                      />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, 'quantity']} noStyle
                      rules={[{ required: true, message: '数量' }]}
                    >
                      <InputNumber min={0.01} placeholder="数量" style={{ width: '18%' }} />
                    </Form.Item>
                    <Form.Item name={[field.name, 'unit_price']} noStyle>
                      <InputNumber min={0} placeholder="预估单价" style={{ width: '22%' }} />
                    </Form.Item>
                    <Button danger type="link" onClick={() => remove(field.name)}>删</Button>
                  </Space.Compact>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ material_code: undefined, quantity: 1, unit_price: 0 })}>
                  添加行
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal
        title={`部分转换 · ${partialOpen?.purchase_request_number ?? ''}`}
        open={Boolean(partialOpen)}
        onOk={submitPartial}
        confirmLoading={busy}
        onCancel={() => setPartialOpen(null)}
        okText="生成采购单"
        width={720}
      >
        <div className="mb-3 text-sm text-ink-soft">
          勾选要转换的行，可调整本次转换数量（默认转剩余全部）；可多次转换直到全部转完。
        </div>
        <Table
          rowKey="line_number"
          size="small"
          pagination={false}
          dataSource={(partialOpen?.lines ?? []).filter((l) => l.status !== 'CONVERTED')}
          rowSelection={{
            selectedRowKeys: selectedLineKeys,
            onChange: (keys) => setSelectedLineKeys(keys as number[]),
          }}
          columns={[
            { title: '行', dataIndex: 'line_number', width: 50 },
            { title: '物料', dataIndex: 'material_code' },
            { title: '申请数量', dataIndex: 'quantity', width: 100, align: 'right' as const },
            { title: '可转余量', dataIndex: 'remaining_quantity', width: 100, align: 'right' as const },
            {
              title: '本次转换数量',
              key: 'convert_qty',
              width: 150,
              render: (_: unknown, line: PrLine) => (
                <InputNumber
                  min={0.01}
                  max={line.remaining_quantity}
                  value={lineQtyOverrides[line.line_number] ?? line.remaining_quantity}
                  onChange={(value) => setLineQtyOverrides((prev) => ({
                    ...prev,
                    [line.line_number]: Number(value ?? line.remaining_quantity),
                  }))}
                  style={{ width: '100%' }}
                />
              ),
            },
          ]}
        />
      </Modal>
    </div>
  )
}

export default PurchaseRequestList
