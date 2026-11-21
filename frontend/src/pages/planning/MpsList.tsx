import { useEffect, useMemo, useState } from 'react'
import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'antd'
import { PlusOutlined, ReloadOutlined, SendOutlined, EyeOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  fmtDate,
  fmtQty,
  MPS_STATUS,
  PLANNER_ACTION,
  StatusTag,
} from './shared'

const { RangePicker } = DatePicker

const MpsList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detail, setDetail] = useState<any | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/mps')
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取 MPS 列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [])

  const openGenerate = () => {
    form.setFieldsValue({
      range: [dayjs(), dayjs().add(56, 'day')],
      plan_name: `MPS ${dayjs().format('YYYY-MM-DD')}`,
      demand_source: 'MIXED',
      include_forecast: true,
      include_safety_stock: true,
    })
    setModalOpen(true)
  }

  const submitGenerate = async () => {
    const values = await form.validateFields()
    try {
      await api.post('/planning/mps/generate', {
        horizon_start: values.range[0].startOf('day').toISOString(),
        horizon_end: values.range[1].endOf('day').toISOString(),
        plan_name: values.plan_name,
        demand_source: values.demand_source,
        include_forecast: values.include_forecast,
        include_safety_stock: values.include_safety_stock,
      })
      message.success('MPS 已生成')
      setModalOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '生成 MPS 失败')
    }
  }

  const openDetail = async (row: any) => {
    setDetailOpen(true)
    setDetailLoading(true)
    setDetail(null)
    try {
      const response = await api.get(`/planning/mps/${row.mps_number}`)
      setDetail(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取 MPS 明细失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const release = async (row: any) => {
    try {
      await api.post(`/planning/mps/${row.mps_number}/release`)
      message.success(`${row.mps_number} 已下达`)
      fetchRows()
      if (detail?.mps_number === row.mps_number) openDetail(row)
    } catch (error) {
      message.error(getErrorMessage(error) || '下达失败')
    }
  }

  const entries = useMemo(() => detail?.entries ?? [], [detail])

  const entryColumns = [
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    {
      title: '周bucket',
      dataIndex: 'bucket_date',
      key: 'bucket_date',
      width: 110,
      render: (value: string) => fmtDate(value),
    },
    {
      title: '期初库存',
      dataIndex: 'opening_stock',
      key: 'opening_stock',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '销售需求',
      dataIndex: 'sales_demand',
      key: 'sales_demand',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '预测需求',
      dataIndex: 'forecast_demand',
      key: 'forecast_demand',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '计划接收',
      dataIndex: 'planned_receipt',
      key: 'planned_receipt',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '预计可用',
      dataIndex: 'projected_available',
      key: 'projected_available',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '净需求',
      dataIndex: 'net_requirement',
      key: 'net_requirement',
      align: 'right' as const,
      render: (value: number) => (
        <span style={{ color: value > 0 ? '#cf1322' : undefined }}>{fmtQty(value)}</span>
      ),
    },
    {
      title: '计划员动作',
      dataIndex: 'planner_action',
      key: 'planner_action',
      width: 110,
      render: (value: string) => <StatusTag value={value} map={PLANNER_ACTION} />,
    },
  ]

  const columns = [
    { title: 'MPS 编号', dataIndex: 'mps_number', key: 'mps_number', width: 170 },
    { title: '计划名称', dataIndex: 'plan_name', key: 'plan_name', ellipsis: true },
    {
      title: '计划区间',
      key: 'horizon',
      width: 200,
      render: (_: any, record: any) =>
        `${fmtDate(record.horizon_start)} ~ ${fmtDate(record.horizon_end)}`,
    },
    {
      title: '毛需求',
      dataIndex: 'total_gross',
      key: 'total_gross',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: '计划接收',
      dataIndex: 'total_planned',
      key: 'total_planned',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={MPS_STATUS} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: any) => (
        <Space size={0}>
          <Button type="link" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
            明细
          </Button>
          {record.status === 'DRAFT' && (
            <Button type="link" icon={<SendOutlined />} onClick={() => release(record)}>
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
        title="主生产计划（MPS）"
        description="按周汇总销售订单、预测与安全库存，形成可下达的主生产计划"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openGenerate}>
              生成 MPS
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="mps_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 10, showSizeChanger: false }}
        expandable={{
          expandedRowRender: (record: any) => (
            <div className="text-sm text-ink-soft">
              计划员：{record.generated_by ?? '-'} 生成时间：
              {record.generated_at?.replace('T', ' ').slice(0, 19) ?? '-'} 需求来源：
              {record.demand_source}
            </div>
          ),
        }}
      />

      <Modal
        title="生成主生产计划"
        open={modalOpen}
        onOk={submitGenerate}
        onCancel={() => setModalOpen(false)}
        okText="生成"
        destroyOnClose
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item
            name="range"
            label="计划区间"
            rules={[{ required: true, message: '请选择计划区间' }]}
          >
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="plan_name" label="计划名称">
            <Input placeholder="例如：2027 年 1 月滚动计划" />
          </Form.Item>
          <Form.Item name="demand_source" label="需求来源">
            <Select
              options={[
                { value: 'MIXED', label: '销售订单 + 预测' },
                { value: 'SALES', label: '仅销售订单' },
                { value: 'FORECAST', label: '仅预测' },
              ]}
            />
          </Form.Item>
          <Space size="large">
            <Form.Item name="include_forecast" label="纳入预测" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="include_safety_stock" label="纳入安全库存" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Drawer
        title={detail ? `${detail.mps_number} · ${detail.plan_name ?? ''}` : 'MPS 明细'}
        width={1100}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        loading={detailLoading}
        extra={
          detail?.status === 'DRAFT' ? (
            <Button type="primary" onClick={() => release(detail)}>
              下达计划
            </Button>
          ) : (
            <Tag color="green">{MPS_STATUS[detail?.status]?.text ?? detail?.status}</Tag>
          )
        }
      >
        {detail && (
          <>
            <Table
              size="small"
              rowKey="id"
              columns={entryColumns}
              dataSource={entries}
              pagination={{ pageSize: 12, showSizeChanger: false }}
              scroll={{ x: 1000 }}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

export default MpsList
