import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, InputNumber, Modal, Space, Table, Tag, message } from 'antd'
import { CheckOutlined, PlusOutlined, ReloadOutlined, FileSearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const PO_STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  RELEASED: { label: '已下达', color: 'processing' },
  PARTIALLY_RECEIVED: { label: '部分到货', color: 'warning' },
  RECEIVED: { label: '已到货', color: 'success' },
  CLOSED: { label: '已关闭', color: 'default' },
  CANCELLED: { label: '已作废', color: 'error' },
}

const LINE_STATUS: Record<string, { label: string; color: string }> = {
  OPEN: { label: '待到货', color: 'processing' },
  PARTIAL: { label: '部分到货', color: 'warning' },
  RECEIVED: { label: '已到货', color: 'success' },
}

interface PoLine {
  line_number: number
  material_code: string
  quantity: number
  received_quantity: number
  outstanding_quantity: number
  unit: string
  unit_price: number
  status: string
}

interface PurchaseOrder {
  purchase_order_number: string
  supplier_id: string
  supplier_name: string
  status: string
  order_date: string | null
  expected_date: string | null
  currency: string
  total_amount: number
  remarks: string | null
  lines: PoLine[]
}

const PurchaseOrderList: React.FC = () => {
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [receiveTarget, setReceiveTarget] = useState<PurchaseOrder | null>(null)
  const [receiveForm] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/purchase/purchase-orders')
      setOrders(response.data.items ?? [])
      setTotal(response.data.total ?? 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取采购单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const openReceive = (order: PurchaseOrder) => {
    setReceiveTarget(order)
    // 表单改由 forceRender 常驻挂载，打开前先清空再回填余量
    receiveForm.resetFields()
    const defaults: Record<string, number | undefined> = {}
    for (const line of order.lines) {
      if (line.outstanding_quantity > 0) {
        defaults[`qty_${line.line_number}`] = line.outstanding_quantity
      }
    }
    receiveForm.setFieldsValue(defaults)
  }

  const submitReceive = async () => {
    if (!receiveTarget) return
    setSubmitting(true)
    try {
      const values = receiveForm.getFieldsValue()
      const lines = receiveTarget.lines
        .filter((line) => line.outstanding_quantity > 0)
        .map((line) => ({
          line_number: line.line_number,
          quantity: values[`qty_${line.line_number}`],
        }))
        .filter((item) => Number(item.quantity) > 0)

      // 全部为 0 时后端会静默跳过并返回原状态，前端必须先拦住（否则提示“部分到货”是误导）
      if (lines.length === 0) {
        message.warning('请至少为一行填写大于 0 的收货数量')
        setSubmitting(false)
        return
      }

      const response = await api.post(
        `/purchase/purchase-orders/${receiveTarget.purchase_order_number}/receive`,
        { lines, received_by: 'web' }
      )
      message.success(`收货成功：${response.data.status === 'RECEIVED' ? '整单到货' : '部分到货'}`)
      setReceiveTarget(null)
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '收货失败')
    } finally {
      setSubmitting(false)
    }
  }

  const closeOrder = async (order: PurchaseOrder) => {
    try {
      await api.post(`/purchase/purchase-orders/${order.purchase_order_number}/close`)
      message.success('采购单已关闭')
      fetchData()
    } catch (error) {
      message.error(getErrorMessage(error) || '关闭失败')
    }
  }

  const columns = useMemo(
    () => [
      { title: '采购单号', dataIndex: 'purchase_order_number', key: 'purchase_order_number', width: 170 },
      { title: '供应商', dataIndex: 'supplier_name', key: 'supplier_name', width: 160 },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 110,
        render: (v: string) => <Tag color={PO_STATUS[v]?.color ?? 'default'}>{PO_STATUS[v]?.label ?? v}</Tag>,
      },
      {
        title: '单据日期',
        dataIndex: 'order_date',
        key: 'order_date',
        width: 120,
        render: (v: string | null) => (v ? v.slice(0, 10) : '-'),
      },
      {
        title: '期望到货',
        dataIndex: 'expected_date',
        key: 'expected_date',
        width: 120,
        render: (v: string | null) => (v ? v.slice(0, 10) : '-'),
      },
      {
        title: '金额',
        dataIndex: 'total_amount',
        key: 'total_amount',
        width: 110,
        align: 'right' as const,
        render: (v: number) => `¥${Number(v ?? 0).toLocaleString()}`,
      },
      { title: '备注', dataIndex: 'remarks', key: 'remarks', ellipsis: true },
      {
        title: '操作',
        key: 'action',
        width: 170,
        render: (_: unknown, record: PurchaseOrder) => (
          <Space>
            {['RELEASED', 'PARTIALLY_RECEIVED'].includes(record.status) && (
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => openReceive(record)}>
                收货
              </Button>
            )}
            {record.status !== 'CLOSED' && record.status !== 'CANCELLED' && (
              <Button size="small" icon={<CheckOutlined />} onClick={() => closeOrder(record)}>
                关闭
              </Button>
            )}
          </Space>
        ),
      },
    ],
    [orders]
  )

  const expandedRowRender = (record: PurchaseOrder) => (
    <Table
      rowKey="line_number"
      size="small"
      pagination={false}
      dataSource={record.lines}
      columns={[
        { title: '行', dataIndex: 'line_number', key: 'line_number', width: 60 },
        { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
        { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 90, align: 'right' as const },
        { title: '已收', dataIndex: 'received_quantity', key: 'received_quantity', width: 90, align: 'right' as const },
        { title: '余量', dataIndex: 'outstanding_quantity', key: 'outstanding_quantity', width: 90, align: 'right' as const },
        { title: '单位', dataIndex: 'unit', key: 'unit', width: 70 },
        { title: '单价', dataIndex: 'unit_price', key: 'unit_price', width: 90, align: 'right' as const },
        {
          title: '行状态',
          dataIndex: 'status',
          key: 'status',
          width: 100,
          render: (v: string) => <Tag color={LINE_STATUS[v]?.color ?? 'default'}>{LINE_STATUS[v]?.label ?? v}</Tag>,
        },
        {
          title: '来料检验',
          key: 'iqc',
          width: 100,
          render: (_: unknown, line: PoLine) =>
            line.received_quantity > 0 ? (
              <Button
                type="link"
                size="small"
                icon={<FileSearchOutlined />}
                onClick={() =>
                  navigate(
                    `/qms/inspections?material_code=${line.material_code}&purchase_order_number=${record.purchase_order_number}`
                  )
                }
              >
                IQC
              </Button>
            ) : null,
        },
      ]}
    />
  )

  return (
    <div>
      <PageHeader
        title="采购订单"
        description="MRP 计划订单下达后自动生成采购单；到货收货实时回冲原料库存，形成「计划 → 采购 → 领料」闭环"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        }
      />

      <Card>
        <Table
          rowKey="purchase_order_number"
          columns={columns}
          dataSource={orders}
          loading={loading}
          expandable={{ expandedRowRender }}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 张` }}
          size="middle"
        />
      </Card>

      <Modal
        title={`收货 · ${receiveTarget?.purchase_order_number ?? ''}`}
        open={receiveTarget !== null}
        onOk={submitReceive}
        onCancel={() => setReceiveTarget(null)}
        confirmLoading={submitting}
        okText="确认收货"
        forceRender
      >
        <Form form={receiveForm} layout="vertical">
          {(receiveTarget?.lines ?? [])
            .filter((line) => line.outstanding_quantity > 0)
            .map((line) => (
              <Form.Item
                key={line.line_number}
                name={`qty_${line.line_number}`}
                label={`${line.material_code}（余量 ${line.outstanding_quantity} ${line.unit}）`}
                rules={[{ required: true, message: '请输入收货数量' }]}
              >
                <InputNumber min={0} max={line.outstanding_quantity} style={{ width: '100%' }} addonAfter={line.unit} />
              </Form.Item>
            ))}
        </Form>
      </Modal>

      <div className="mt-3 text-xs text-ink-faint">共 {total} 张采购单；到货即回冲物料库存，多轮演示可用「重置演示数据」恢复基线。</div>
    </div>
  )
}

export default PurchaseOrderList
