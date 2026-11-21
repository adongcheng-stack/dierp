import { useEffect, useState } from 'react'
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd'
import { CheckOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  INSPECTION_RESULT,
  INSPECTION_STATUS,
  INSPECTION_TYPE,
  StatusTag,
  fmtDateTime,
} from './shared'

const InspectionList: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [rows, setRows] = useState<any[]>([])
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [materials, setMaterials] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [completeTarget, setCompleteTarget] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/qms/inspections', {
        params: { limit: 200, type: typeFilter },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取检验单失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchMaterials = async () => {
    try {
      const response = await api.get('/mm/materials')
      setMaterials(response.data || [])
    } catch {
      setMaterials([])
    }
  }

  useEffect(() => {
    fetchRows()
  }, [typeFilter])

  useEffect(() => {
    fetchMaterials()
  }, [])

  // IQC 联动：从采购单页带 query 参数进入时，预填来料检验单并自动打开创建弹窗
  useEffect(() => {
    const materialCode = searchParams.get('material_code')
    const purchaseOrder = searchParams.get('purchase_order_number')
    if (!materialCode && !purchaseOrder) return
    form.resetFields()
    form.setFieldsValue({
      inspection_type: 'INCOMING',
      material_code: materialCode || undefined,
      purchase_order_number: purchaseOrder || undefined,
    })
    setCreateOpen(true)
  }, [])

  const openCreate = () => {
    form.resetFields()
    setCreateOpen(true)
  }

  const submitCreate = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      await api.post('/qms/inspections', values)
      message.success('检验单已创建')
      setCreateOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '创建检验单失败')
    } finally {
      setBusy(false)
    }
  }

  const openComplete = (row: any) => {
    setCompleteTarget(row)
    form.resetFields()
    form.setFieldsValue({
      quantity_ok: row.quantity_inspected ?? 0,
      quantity_rejected: 0,
      result: undefined,
    })
  }

  const submitComplete = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      await api.post(`/qms/inspections/${completeTarget.inspection_number}/complete`, {
        quantity_ok: values.quantity_ok,
        quantity_rejected: values.quantity_rejected,
        result: values.result,
        remarks: values.remarks,
        auto_create_ncr: true,
      })
      message.success(`检验单 ${completeTarget.inspection_number} 已完成`)
      setCompleteTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '完成检验失败')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '检验单号', dataIndex: 'inspection_number', key: 'inspection_number', width: 170 },
    {
      title: '环节',
      dataIndex: 'inspection_type',
      key: 'inspection_type',
      width: 110,
      render: (v: string) => <StatusTag value={v} map={INSPECTION_TYPE} />,
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    {
      title: 'LOT卡', dataIndex: 'lot_number', key: 'lot_number', width: 140,
      render: (v: string) =>
        v ? (
          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => navigate('/pp/lot-cards')}>
            {v}
          </Button>
        ) : ('-'),
    },
    {
      title: '采购单', dataIndex: 'purchase_order_number', key: 'purchase_order_number', width: 150,
      render: (v: string) =>
        v ? (
          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => navigate('/mm/purchase-orders')}>
            {v}
          </Button>
        ) : ('-'),
    },
    {
      title: '报工单', dataIndex: 'report_number', key: 'report_number', width: 170,
      render: (v: string) =>
        v ? (
          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => navigate('/pp/operation-reports')}>
            {v}
          </Button>
        ) : ('-'),
    },
    { title: '检验数', dataIndex: 'quantity_inspected', key: 'quantity_inspected', width: 90, align: 'right' as const },
    { title: '合格', dataIndex: 'quantity_ok', key: 'quantity_ok', width: 80, align: 'right' as const },
    { title: '不合格', dataIndex: 'quantity_rejected', key: 'quantity_rejected', width: 90, align: 'right' as const },
    { title: '检验员', dataIndex: 'inspector', key: 'inspector', width: 90 },
    { title: '检验时间', dataIndex: 'inspected_at', key: 'inspected_at', width: 150, render: fmtDateTime },
    {
      title: '结论',
      dataIndex: 'result',
      key: 'result',
      width: 90,
      render: (v: string) => (v ? <StatusTag value={v} map={INSPECTION_RESULT} /> : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => <StatusTag value={v} map={INSPECTION_STATUS} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_: any, row: any) =>
        row.status === 'DRAFT' ? (
          <Button type="link" size="small" icon={<CheckOutlined />} onClick={() => openComplete(row)}>
            完成
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <PageHeader
        title="检验单"
        description="来料 / 过程 / 终检三环节检验：完成时自动判定结论，不合格自动生成不合格品记录（NCR）"
        actions={
          <Space>
            <Select
              allowClear
              placeholder="按环节筛选"
              style={{ width: 150 }}
              value={typeFilter}
              onChange={(value) => setTypeFilter(value)}
              options={Object.entries(INSPECTION_TYPE).map(([value, item]) => ({ value, label: item.text }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建检验单
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="inspection_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1500 }}
      />

      <Modal
        title="新建检验单"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={submitCreate}
        confirmLoading={busy}
        okText="创建"
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="inspection_type" label="检验环节" rules={[{ required: true, message: '请选择检验环节' }]}>
            <Select
              placeholder="选择检验环节"
              options={Object.entries(INSPECTION_TYPE).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="material_code" label="物料" rules={[{ required: true, message: '请选择物料' }]}>
            <Select
              showSearch
              placeholder="选择被检物料"
              optionFilterProp="label"
              options={materials.map((m) => ({ value: m.material_code, label: `${m.material_code} ${m.material_name ?? ''}` }))}
            />
          </Form.Item>
          <Form.Item name="lot_number" label="LOT卡（过程/终检）">
            <Input placeholder="关联 LOT 卡号" />
          </Form.Item>
          <Form.Item name="purchase_order_number" label="采购订单（来料）">
            <Input placeholder="关联采购订单号" />
          </Form.Item>
          <Form.Item name="report_number" label="报工单（过程）">
            <Input placeholder="关联报工单号" />
          </Form.Item>
          <Form.Item name="quantity_inspected" label="检验数量">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="inspector" label="检验员">
            <Input placeholder="检验员姓名" />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`完成检验 ${completeTarget?.inspection_number ?? ''}`}
        open={!!completeTarget}
        onCancel={() => setCompleteTarget(null)}
        onOk={submitComplete}
        confirmLoading={busy}
        okText="确认完成"
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="quantity_ok" label="合格数量">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="quantity_rejected" label="不合格数量">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="result" label="检验结论">
            <Select
              placeholder="未填则按数量自动判定"
              allowClear
              options={Object.entries(INSPECTION_RESULT).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="不合格时说明原因" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default InspectionList