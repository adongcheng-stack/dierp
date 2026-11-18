import { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { fmtQty } from './shared'

const MRP_TYPE: Record<string, { color: string; text: string }> = {
  MRP: { color: 'blue', text: 'MRP 计算' },
  REORDER_POINT: { color: 'purple', text: '再订货点' },
  NONE: { color: 'default', text: '不参与计划' },
}

const PROCUREMENT_TYPE: Record<string, { color: string; text: string }> = {
  MAKE: { color: 'geekblue', text: '自制' },
  BUY: { color: 'orange', text: '采购' },
  SUB: { color: 'cyan', text: '委外' },
}

const LOT_RULE: Record<string, string> = {
  LOT_FOR_LOT: '逐批',
  FIXED_LOT: '固定批量',
  MIN_MAX: '最小最大',
  EOQ: '经济批量',
  PERIOD_ORDER: '周期汇总',
}

const ABC_CLASS: Record<string, { color: string; text: string }> = {
  A: { color: 'red', text: 'A 类' },
  B: { color: 'gold', text: 'B 类' },
  C: { color: 'green', text: 'C 类' },
}

interface PolicyFormValues {
  material_code: string
  mrp_type: string
  procurement_type: string
  lot_sizing_rule: string
  fixed_lot_size: number
  min_order_qty: number
  max_order_qty?: number | null
  order_multiple: number
  eoq?: number | null
  lead_time_days: number
  safety_time_days: number
  safety_stock: number
  reorder_point: number
  planner_code?: string
  abc_class?: string
  is_active: boolean
  remarks?: string
}

const DEFAULTS: PolicyFormValues = {
  material_code: '',
  mrp_type: 'MRP',
  procurement_type: 'MAKE',
  lot_sizing_rule: 'LOT_FOR_LOT',
  fixed_lot_size: 0,
  min_order_qty: 0,
  max_order_qty: null,
  order_multiple: 1,
  eoq: null,
  lead_time_days: 0,
  safety_time_days: 0,
  safety_stock: 0,
  reorder_point: 0,
  planner_code: '',
  abc_class: undefined,
  is_active: true,
  remarks: '',
}

const PlanningPolicyList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [materials, setMaterials] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [procurement, setProcurement] = useState<string | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<PolicyFormValues>()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/policies', { params: { limit: 300 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取计划参数失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchMaterials = async () => {
    try {
      const response = await api.get('/mm/materials')
      const data = response.data
      setMaterials(Array.isArray(data) ? data : data?.items ?? [])
    } catch {
      setMaterials([])
    }
  }

  useEffect(() => {
    fetchRows()
    fetchMaterials()
  }, [])

  const filteredRows = useMemo(() => {
    const text = keyword.trim().toLowerCase()
    return rows.filter((row) => {
      if (procurement && row.procurement_type !== procurement) return false
      if (!text) return true
      return [row.material_code, row.policy_id, row.planner_code]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(text))
    })
  }, [rows, keyword, procurement])

  const materialOptions = useMemo(
    () =>
      materials.map((material) => ({
        value: material.material_code,
        label: `${material.material_code} · ${material.material_name ?? ''}`,
      })),
    [materials]
  )

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue(DEFAULTS)
    setModalOpen(true)
  }

  const openEdit = (record: any) => {
    setEditing(record)
    form.resetFields()
    form.setFieldsValue({
      material_code: record.material_code,
      mrp_type: record.mrp_type ?? 'MRP',
      procurement_type: record.procurement_type ?? 'MAKE',
      lot_sizing_rule: record.lot_sizing_rule ?? 'LOT_FOR_LOT',
      fixed_lot_size: record.fixed_lot_size ?? 0,
      min_order_qty: record.min_order_qty ?? 0,
      max_order_qty: record.max_order_qty ?? null,
      order_multiple: record.order_multiple ?? 1,
      eoq: record.eoq ?? null,
      lead_time_days: record.lead_time_days ?? 0,
      safety_time_days: record.safety_time_days ?? 0,
      safety_stock: record.safety_stock ?? 0,
      reorder_point: record.reorder_point ?? 0,
      planner_code: record.planner_code ?? '',
      abc_class: record.abc_class ?? undefined,
      is_active: record.is_active ?? true,
      remarks: record.remarks ?? '',
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    const payload = {
      ...values,
      max_order_qty: values.max_order_qty ?? null,
      eoq: values.eoq ?? null,
      planner_code: values.planner_code || null,
      abc_class: values.abc_class || null,
      remarks: values.remarks || null,
    }
    setSaving(true)
    try {
      if (editing) {
        await api.put(`/planning/policies/${editing.policy_id}`, payload)
        message.success('计划参数已更新')
      } else {
        await api.post('/planning/policies', payload)
        message.success('计划参数已创建')
      }
      setModalOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '保存计划参数失败')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (record: any) => {
    try {
      await api.delete(`/planning/policies/${record.policy_id}`)
      message.success('计划参数已删除')
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '删除计划参数失败')
    }
  }

  const columns = [
    { title: '参数编号', dataIndex: 'policy_id', key: 'policy_id', width: 160 },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 160 },
    {
      title: '计划类型',
      dataIndex: 'mrp_type',
      key: 'mrp_type',
      width: 110,
      render: (value: string) => (
        <Tag color={MRP_TYPE[value]?.color}>{MRP_TYPE[value]?.text ?? value}</Tag>
      ),
    },
    {
      title: '采购类型',
      dataIndex: 'procurement_type',
      key: 'procurement_type',
      width: 90,
      render: (value: string) => (
        <Tag color={PROCUREMENT_TYPE[value]?.color}>
          {PROCUREMENT_TYPE[value]?.text ?? value}
        </Tag>
      ),
    },
    {
      title: '批量规则',
      dataIndex: 'lot_sizing_rule',
      key: 'lot_sizing_rule',
      width: 110,
      render: (value: string) => LOT_RULE[value] ?? value,
    },
    {
      title: '提前期',
      dataIndex: 'lead_time_days',
      key: 'lead_time_days',
      align: 'right' as const,
      width: 90,
      render: (value: number, record: any) =>
        `${value ?? 0} 天${record.safety_time_days ? ` + 缓冲 ${record.safety_time_days}` : ''}`,
    },
    {
      title: '安全库存',
      dataIndex: 'safety_stock',
      key: 'safety_stock',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: 'MOQ / 倍数',
      key: 'lot',
      align: 'right' as const,
      width: 120,
      render: (_: any, record: any) =>
        `${fmtQty(record.min_order_qty)} / ${fmtQty(record.order_multiple ?? 1)}`,
    },
    {
      title: 'ABC',
      dataIndex: 'abc_class',
      key: 'abc_class',
      width: 80,
      render: (value: string) =>
        value ? <Tag color={ABC_CLASS[value]?.color}>{ABC_CLASS[value]?.text ?? value}</Tag> : '-',
    },
    {
      title: '计划员',
      dataIndex: 'planner_code',
      key: 'planner_code',
      width: 100,
      render: (value: string) => value || '-',
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (value: boolean) => (
        <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size={0}>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该计划参数？"
            description="删除后该物料将按默认参数参与 MRP。"
            onConfirm={() => remove(record)}
            okText="删除"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="计划参数"
        description="维护物料的计划类型、提前期、批量规则、安全库存与默认计划员，直接驱动 MRP 结果"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建计划参数
            </Button>
          </Space>
        }
      />

      <Space wrap className="mb-4">
        <Input.Search
          allowClear
          style={{ width: 260 }}
          placeholder="搜索物料 / 参数编号"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Select
          allowClear
          style={{ width: 150 }}
          placeholder="采购类型"
          value={procurement}
          onChange={setProcurement}
          options={[
            { value: 'MAKE', label: '自制' },
            { value: 'BUY', label: '采购' },
            { value: 'SUB', label: '委外' },
          ]}
        />
      </Space>

      <Table
        rowKey="policy_id"
        columns={columns}
        dataSource={filteredRows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1400 }}
      />

      <Modal
        title={editing ? `编辑计划参数 ${editing.policy_id}` : '新建计划参数'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        width={760}
        destroyOnClose
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="material_code"
                label="物料"
                rules={[{ required: true, message: '请选择物料' }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  disabled={Boolean(editing)}
                  placeholder="选择物料"
                  options={materialOptions}
                  onChange={(value) => {
                    if (editing) return
                    const material = materials.find((item) => item.material_code === value)
                    if (!material) return
                    const procurement = ['RAW', 'PACK'].includes(material.material_type)
                      ? 'BUY'
                      : 'MAKE'
                    form.setFieldValue('procurement_type', procurement)
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="mrp_type" label="计划类型">
                <Select
                  options={[
                    { value: 'MRP', label: 'MRP 计算' },
                    { value: 'REORDER_POINT', label: '再订货点' },
                    { value: 'NONE', label: '不参与计划' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="procurement_type" label="采购类型">
                <Select
                  options={[
                    { value: 'MAKE', label: '自制' },
                    { value: 'BUY', label: '采购' },
                    { value: 'SUB', label: '委外' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="lot_sizing_rule" label="批量规则">
                <Select
                  options={Object.entries(LOT_RULE).map(([value, label]) => ({
                    value,
                    label,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="fixed_lot_size" label="固定批量">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="order_multiple" label="订单倍数">
                <InputNumber style={{ width: '100%' }} min={0} step={1} precision={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="min_order_qty" label="最小起订量（MOQ）">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_order_qty" label="最大订单量">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} placeholder="不限" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="eoq" label="经济批量（EOQ）">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} placeholder="可选" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="lead_time_days" label="提前期（天）">
                <InputNumber style={{ width: '100%' }} min={0} precision={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="safety_time_days" label="安全缓冲（天）">
                <InputNumber style={{ width: '100%' }} min={0} precision={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="safety_stock" label="安全库存">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="reorder_point" label="再订货点">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="abc_class" label="ABC 分类">
                <Select
                  allowClear
                  placeholder="可选"
                  options={[
                    { value: 'A', label: 'A 类' },
                    { value: 'B', label: 'B 类' },
                    { value: 'C', label: 'C 类' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="planner_code" label="计划员">
                <Input placeholder="例如 planner01" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_active" label="启用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="remarks" label="备注">
                <Input.TextArea rows={2} placeholder="例如：战略物料，提前期按供应商承诺设置" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}

export default PlanningPolicyList
