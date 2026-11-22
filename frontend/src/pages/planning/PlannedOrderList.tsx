import { useEffect, useState } from 'react'
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  message,
} from 'antd'
import { CheckOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  fmtDate,
  fmtQty,
  ORDER_TYPE,
  PLANNED_ORDER_STATUS,
  StatusTag,
} from './shared'

const PlannedOrderList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [runNumber, setRunNumber] = useState<string | undefined>()
  const [status, setStatus] = useState<string | undefined>('PLANNED')
  const [orderType, setOrderType] = useState<string | undefined>()
  const [releaseTarget, setReleaseTarget] = useState<any | null>(null)
  const [releaseLoading, setReleaseLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/planned-orders', {
        params: { run_number: runNumber, status, order_type: orderType, limit: 300 },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取计划订单失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchRuns = async () => {
    try {
      const response = await api.get('/planning/mrp/runs')
      setRuns(response.data.items ?? [])
    } catch {
      setRuns([])
    }
  }

  useEffect(() => {
    fetchRows()
  }, [runNumber, status, orderType])

  useEffect(() => {
    fetchRuns()
  }, [])

  const confirm = async (record: any) => {
    try {
      await api.post(`/planning/planned-orders/${record.planned_order_number}/confirm`)
      message.success(`${record.planned_order_number} 已确认`)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '确认失败')
    }
  }

  const openRelease = (record: any) => {
    form.resetFields()
    form.setFieldsValue({ auto_confirm: true })
    setReleaseTarget(record)
  }

  const submitRelease = async () => {
    if (!releaseTarget) return
    const values = await form.validateFields()
    setReleaseLoading(true)
    try {
      const response = await api.post(
        `/planning/planned-orders/${releaseTarget.planned_order_number}/release`,
        {
          sales_order_number: values.sales_order_number || undefined,
          supplier_id: values.supplier_id || undefined,
          supplier_name: values.supplier_name || undefined,
          unit_price: values.unit_price ?? undefined,
          auto_confirm: values.auto_confirm,
        }
      )
      message.success(
        `已下达，生成单据 ${response.data.created_order_number ?? ''}`
      )
      setReleaseTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '下达失败')
    } finally {
      setReleaseLoading(false)
    }
  }

  const columns = [
    {
      title: '计划订单',
      dataIndex: 'planned_order_number',
      key: 'planned_order_number',
      width: 170,
    },
    {
      title: '类型',
      dataIndex: 'order_type',
      key: 'order_type',
      width: 80,
      render: (value: string) => <StatusTag value={value} map={ORDER_TYPE} />,
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right' as const,
      render: (value: number, record: any) => `${fmtQty(value)} ${record.unit ?? ''}`,
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 110,
      render: (value: string) => fmtDate(value),
    },
    {
      title: '需求日期',
      dataIndex: 'due_date',
      key: 'due_date',
      width: 110,
      render: (value: string) => fmtDate(value),
    },
    {
      title: '需求来源',
      dataIndex: 'demand_ref',
      key: 'demand_ref',
      width: 160,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={PLANNED_ORDER_STATUS} />,
    },
    {
      title: '转换单据',
      dataIndex: 'conversion_order_number',
      key: 'conversion_order_number',
      width: 160,
      render: (value: string) => value ?? '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 170,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size={0}>
          {record.status === 'PLANNED' && (
            <Button type="link" icon={<CheckOutlined />} onClick={() => confirm(record)}>
              确认
            </Button>
          )}
          {(record.status === 'PLANNED' || record.status === 'FIRMED') && (
            <Button type="link" icon={<SendOutlined />} onClick={() => openRelease(record)}>
              下达
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="计划订单"
        description="MRP 生成的建议订单，确认后转换为生产订单或采购订单"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
            刷新
          </Button>
        }
      />

      <Space wrap className="mb-4">
        <Select
          allowClear
          style={{ width: 230 }}
          placeholder="MRP 批次"
          value={runNumber}
          onChange={setRunNumber}
          options={runs.map((item) => ({
            value: item.run_number,
            label: item.run_number,
          }))}
        />
        <Select
          allowClear
          style={{ width: 150 }}
          placeholder="订单类型"
          value={orderType}
          onChange={setOrderType}
          options={[
            { value: 'PRODUCTION', label: '自制' },
            { value: 'PURCHASE', label: '采购' },
            { value: 'TRANSFER', label: '调拨' },
          ]}
        />
        <Select
          allowClear
          style={{ width: 150 }}
          placeholder="状态"
          value={status}
          onChange={setStatus}
          options={[
            { value: 'PLANNED', label: '建议' },
            { value: 'FIRMED', label: '已确认' },
            { value: 'RELEASED', label: '已下达' },
            { value: 'CANCELLED', label: '已取消' },
          ]}
        />
      </Space>

      <Table
        rowKey="planned_order_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title={
          releaseTarget
            ? `下达计划订单 ${releaseTarget.planned_order_number}`
            : '下达计划订单'
        }
        open={Boolean(releaseTarget)}
        onOk={submitRelease}
        confirmLoading={releaseLoading}
        onCancel={() => setReleaseTarget(null)}
        okText="确认下达"
        destroyOnClose
      >
        {releaseTarget && (
          <>
            <div className="mb-4 rounded-md bg-surface-sunken px-3 py-2 text-sm text-ink-soft">
              {ORDER_TYPE[releaseTarget.order_type]?.text} · {releaseTarget.material_code} ·{' '}
              {fmtQty(releaseTarget.quantity)} {releaseTarget.unit} · 需求日期{' '}
              {fmtDate(releaseTarget.due_date)}
            </div>
            <Form form={form} layout="vertical">
              {releaseTarget.order_type === 'PRODUCTION' ? (
                <Form.Item
                  name="sales_order_number"
                  label="关联销售订单"
                  extra="留空时系统会沿需求追溯链自动寻找来源销售订单"
                >
                  <Input placeholder="例如 SO-20261117-0001" />
                </Form.Item>
              ) : (
                <>
                  <Form.Item name="supplier_id" label="供应商编码">
                    <Input placeholder="可留空，后续在采购单补录" />
                  </Form.Item>
                  <Form.Item name="supplier_name" label="供应商名称">
                    <Input />
                  </Form.Item>
                  <Form.Item name="unit_price" label="采购单价">
                    <InputNumber style={{ width: '100%' }} min={0} precision={4} />
                  </Form.Item>
                </>
              )}
            </Form>
          </>
        )}
      </Modal>
    </div>
  )
}

export default PlannedOrderList
