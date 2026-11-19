import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { CheckOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  APPROVED: { label: '已审批', color: 'success' },
  CANCELLED: { label: '已作废', color: 'error' },
}

interface Stocktake {
  stocktake_number: string
  material_code: string
  warehouse: string | null
  book_qty: number
  counted_qty: number
  diff: number
  status: string
  stocktake_date: string | null
  remarks: string | null
}

interface MaterialOption {
  material_code: string
  material_name: string | null
  current_stock: number
}

const StocktakeList: React.FC = () => {
  const [rows, setRows] = useState<Stocktake[]>([])
  const [total, setTotal] = useState(0)
  const [materials, setMaterials] = useState<MaterialOption[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [form] = Form.useForm()

  const selectedMaterial = Form.useWatch('material_code', form)
  const materialOption = materials.find((m) => m.material_code === selectedMaterial)

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (statusFilter) params.stocktake_status = statusFilter
      const response = await api.get('/mm/stocktakes', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载盘点单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter])

  const openCreate = async () => {
    form.resetFields()
    setCreateOpen(true)
    try {
      const response = await api.get('/mm/materials', { params: { limit: 100 } })
      setMaterials(response.data?.items || response.data || [])
    } catch {
      // 选项加载失败不阻塞
    }
  }

  const submitCreate = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const response = await api.post('/mm/stocktakes', {
        material_code: values.material_code,
        counted_qty: values.counted_qty,
        warehouse: values.warehouse || undefined,
        remarks: values.remarks || undefined,
      })
      message.success(`盘点单 ${response.data.stocktake_number} 已创建（差异 ${response.data.diff}）`)
      setCreateOpen(false)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建盘点单失败')
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
    { title: '盘点单号', dataIndex: 'stocktake_number', width: 170 },
    { title: '物料', dataIndex: 'material_code', width: 180 },
    { title: '仓库', dataIndex: 'warehouse', width: 110, render: (v: string | null) => v || '—' },
    { title: '账面数量', dataIndex: 'book_qty', width: 110, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    { title: '实盘数量', dataIndex: 'counted_qty', width: 110, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    {
      title: '差异',
      dataIndex: 'diff',
      width: 100,
      align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#389e0d' : v < 0 ? '#cf1322' : undefined }}>{v?.toFixed(2)}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const s = STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    { title: '盘点日期', dataIndex: 'stocktake_date', width: 160, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '备注', dataIndex: 'remarks', ellipsis: true },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      render: (_: unknown, r: Stocktake) => (
        <Space>
          {r.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<CheckOutlined />}
              onClick={() => act(`/mm/stocktakes/${r.stocktake_number}/approve`, `盘点单 ${r.stocktake_number} 已审批并校正库存`)}>
              审批
            </Button>
          )}
          {r.status === 'DRAFT' && (
            <Button size="small" danger icon={<StopOutlined />}
              onClick={() => act(`/mm/stocktakes/${r.stocktake_number}/cancel`, `盘点单 ${r.stocktake_number} 已作废`)}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="库存盘点" description="实盘 vs 账面：审批后写 ADJUSTMENT 流水并校正现存量（调整后库存 ≥ 0）" />
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
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建盘点</Button>
          </Space>
        }
      >
        <Table rowKey="stocktake_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }} scroll={{ x: 1300 }} />
      </Card>

      <Modal
        title="新建盘点单"
        open={createOpen}
        onOk={submitCreate}
        confirmLoading={busy}
        onCancel={() => setCreateOpen(false)}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="material_code" label="物料" rules={[{ required: true, message: '请选择物料' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="选择物料（账面数量自动取现存量快照）"
              options={materials.map((m) => ({
                value: m.material_code,
                label: `${m.material_code} · ${m.material_name || '-'} · 现存 ${m.current_stock}`,
              }))}
            />
          </Form.Item>
          {materialOption && (
            <div style={{ marginBottom: 12, color: '#888' }}>
              当前账面数量：<strong>{materialOption.current_stock}</strong>
            </div>
          )}
          <Form.Item name="counted_qty" label="实盘数量" rules={[{ required: true, message: '请输入实盘数量' }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="warehouse" label="仓库（选填）">
            <Input placeholder="如 WH-PD01" />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="选填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default StocktakeList
