import { useEffect, useState } from 'react'
import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Modal,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  message,
} from 'antd'
import { EyeOutlined, PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  EXCEPTION_TYPE,
  fmtDate,
  fmtQty,
  ORDER_TYPE,
  PLANNED_ORDER_STATUS,
  RUN_STATUS,
  SEVERITY,
  StatusTag,
} from './shared'

const { RangePicker } = DatePicker

const MrpRunList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [mpsOptions, setMpsOptions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detail, setDetail] = useState<any | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [form] = Form.useForm()
  const demandSource = Form.useWatch('demand_source', form)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/mrp/runs')
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取 MRP 运行记录失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchMpsOptions = async () => {
    try {
      const response = await api.get('/planning/mps', { params: { status: 'RELEASED' } })
      setMpsOptions(response.data.items ?? [])
    } catch {
      setMpsOptions([])
    }
  }

  useEffect(() => {
    fetchRows()
    fetchMpsOptions()
  }, [])

  const openRun = () => {
    form.setFieldsValue({
      range: [dayjs(), dayjs().add(56, 'day')],
      run_type: 'REGENERATIVE',
      demand_source: 'AUTO',
      include_forecast: true,
      include_safety_stock: true,
      mps_number: undefined,
    })
    setModalOpen(true)
  }

  const submitRun = async () => {
    const values = await form.validateFields()
    try {
      await api.post('/planning/mrp/run', {
        horizon_start: values.range[0].startOf('day').toISOString(),
        horizon_end: values.range[1].endOf('day').toISOString(),
        run_type: values.run_type,
        demand_source: values.demand_source,
        mps_number: values.demand_source === 'MPS' ? values.mps_number : undefined,
        include_forecast: values.include_forecast,
        include_safety_stock: values.include_safety_stock,
      })
      message.success('MRP 运算完成')
      setModalOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || 'MRP 运算失败')
    }
  }

  const openDetail = async (row: any) => {
    setDetailOpen(true)
    setDetailLoading(true)
    setDetail(null)
    try {
      const response = await api.get(`/planning/mrp/runs/${row.run_number}`)
      setDetail(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取 MRP 明细失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const columns = [
    { title: '批次号', dataIndex: 'run_number', key: 'run_number', width: 170 },
    {
      title: '计划区间',
      key: 'horizon',
      width: 200,
      render: (_: any, record: any) =>
        `${fmtDate(record.horizon_start)} ~ ${fmtDate(record.horizon_end)}`,
    },
    { title: '运算方式', dataIndex: 'run_type', key: 'run_type', width: 110 },
    { title: '需求来源', dataIndex: 'demand_source', key: 'demand_source', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={RUN_STATUS} />,
    },
    {
      title: '需求行',
      dataIndex: 'total_requirements',
      key: 'total_requirements',
      align: 'right' as const,
      width: 80,
    },
    {
      title: '计划生产',
      dataIndex: 'planned_production_count',
      key: 'planned_production_count',
      align: 'right' as const,
      width: 90,
    },
    {
      title: '计划采购',
      dataIndex: 'planned_purchase_count',
      key: 'planned_purchase_count',
      align: 'right' as const,
      width: 90,
    },
    {
      title: '异常',
      dataIndex: 'exception_count',
      key: 'exception_count',
      align: 'right' as const,
      width: 70,
      render: (value: number) => (
        <span style={{ color: value ? '#cf1322' : undefined }}>{value}</span>
      ),
    },
    {
      title: '完成时间',
      dataIndex: 'finished_at',
      key: 'finished_at',
      width: 160,
      render: (value: string) => value?.replace('T', ' ').slice(0, 19) ?? '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      render: (_: any, record: any) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
          明细
        </Button>
      ),
    },
  ]

  const requirementColumns = [
    { title: '层级', dataIndex: 'requirement_level', key: 'requirement_level', width: 60 },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 140 },
    { title: '需求类型', dataIndex: 'demand_type', key: 'demand_type', width: 110 },
    { title: '需求来源', dataIndex: 'demand_ref', key: 'demand_ref', width: 160 },
    {
      title: '需求量',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '已覆盖',
      dataIndex: 'covered_qty',
      key: 'covered_qty',
      align: 'right' as const,
      render: fmtQty,
    },
    {
      title: '短缺',
      dataIndex: 'shortage_qty',
      key: 'shortage_qty',
      align: 'right' as const,
      render: (value: number) => (
        <span style={{ color: value > 0 ? '#cf1322' : undefined }}>{fmtQty(value)}</span>
      ),
    },
    {
      title: '需求日期',
      dataIndex: 'due_date',
      key: 'due_date',
      width: 110,
      render: (value: string) => fmtDate(value),
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  ]

  const plannedColumns = [
    { title: '计划订单', dataIndex: 'planned_order_number', key: 'planned_order_number', width: 170 },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 140 },
    {
      title: '类型',
      dataIndex: 'order_type',
      key: 'order_type',
      width: 80,
      render: (value: string) => <StatusTag value={value} map={ORDER_TYPE} />,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right' as const,
      render: fmtQty,
    },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 70 },
    {
      title: '开始',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => <StatusTag value={value} map={PLANNED_ORDER_STATUS} />,
    },
  ]

  const exceptionColumns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (value: string) => <StatusTag value={value} map={SEVERITY} />,
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 140 },
    {
      title: '异常类型',
      dataIndex: 'exception_type',
      key: 'exception_type',
      width: 120,
      render: (value: string) => EXCEPTION_TYPE[value] ?? value,
    },
    { title: '需求来源', dataIndex: 'requirement_ref', key: 'requirement_ref', width: 150 },
    {
      title: '短缺量',
      dataIndex: 'shortage_qty',
      key: 'shortage_qty',
      align: 'right' as const,
      render: fmtQty,
    },
    { title: '建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
  ]

  return (
    <div>
      <PageHeader
        title="MRP 运算"
        description="按低层码逐级净算需求，生成计划生产/采购订单，并保留需求-供应追溯链"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={openRun}>
              运行 MRP
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="run_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 10, showSizeChanger: false }}
      />

      <Modal
        title="运行物料需求计划"
        open={modalOpen}
        onOk={submitRun}
        onCancel={() => setModalOpen(false)}
        okText="开始运算"
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
          <Form.Item name="run_type" label="运算方式">
            <Select
              options={[
                { value: 'REGENERATIVE', label: '全重排（重新生成全部建议）' },
                { value: 'NET_CHANGE', label: '净变更（仅处理变化）' },
              ]}
            />
          </Form.Item>
          <Form.Item name="demand_source" label="独立需求来源">
            <Select
              options={[
                { value: 'AUTO', label: '自动选择最新已下达 MPS' },
                { value: 'MPS', label: '指定 MPS' },
                { value: 'SALES', label: '销售订单' },
                { value: 'FORECAST', label: '预测' },
              ]}
            />
          </Form.Item>
          {demandSource === 'MPS' && (
            <Form.Item
              name="mps_number"
              label="MPS 计划"
              rules={[{ required: true, message: '请选择 MPS' }]}
            >
              <Select
                placeholder="选择已下达的 MPS"
                options={mpsOptions.map((item) => ({
                  value: item.mps_number,
                  label: `${item.mps_number} · ${item.plan_name ?? ''}`,
                }))}
              />
            </Form.Item>
          )}
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
        title={detail ? `${detail.run_number} · MRP 结果` : 'MRP 结果'}
        width={1180}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        loading={detailLoading}
      >
        {detail && (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Statistic title="需求行" value={detail.total_requirements} />
              <Statistic title="计划生产" value={detail.planned_production_count} />
              <Statistic title="计划采购" value={detail.planned_purchase_count} />
              <Statistic
                title="异常"
                value={detail.exception_count}
                valueStyle={{ color: detail.exception_count ? '#cf1322' : undefined }}
              />
            </div>
            <Tabs
              items={[
                {
                  key: 'requirements',
                  label: `需求行 (${detail.requirements?.length ?? 0})`,
                  children: (
                    <Table
                      size="small"
                      rowKey="id"
                      columns={requirementColumns}
                      dataSource={detail.requirements ?? []}
                      pagination={{ pageSize: 10, showSizeChanger: false }}
                      scroll={{ x: 1000 }}
                    />
                  ),
                },
                {
                  key: 'planned',
                  label: `计划订单 (${detail.planned_orders?.length ?? 0})`,
                  children: (
                    <Table
                      size="small"
                      rowKey="id"
                      columns={plannedColumns}
                      dataSource={detail.planned_orders ?? []}
                      pagination={{ pageSize: 10, showSizeChanger: false }}
                      scroll={{ x: 1000 }}
                    />
                  ),
                },
                {
                  key: 'exceptions',
                  label: `异常 (${detail.exceptions?.length ?? 0})`,
                  children: (
                    <Table
                      size="small"
                      rowKey="id"
                      columns={exceptionColumns}
                      dataSource={detail.exceptions ?? []}
                      pagination={{ pageSize: 10, showSizeChanger: false }}
                      scroll={{ x: 900 }}
                    />
                  ),
                },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

export default MrpRunList
