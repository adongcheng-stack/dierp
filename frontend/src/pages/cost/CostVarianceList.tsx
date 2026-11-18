import { useEffect, useState } from 'react'
import { Button, Modal, Select, Space, Table, message } from 'antd'
import { ReloadOutlined, LineChartOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { VARIANCE_TYPE, fmtMoney } from './shared'

const CostVarianceList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [orderNumber, setOrderNumber] = useState<string | undefined>()
  const [analyzeOpen, setAnalyzeOpen] = useState(false)
  const [targetOrder, setTargetOrder] = useState<string | undefined>()
  const [busy, setBusy] = useState(false)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/cost/variances', {
        params: { limit: 500, production_order_number: orderNumber },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取差异分析失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchOrders = async () => {
    try {
      const response = await api.get('/pp/production-orders', { params: { limit: 300 } })
      const data = response.data
      const list = Array.isArray(data) ? data : data?.items ?? []
      setOrders(list)
    } catch {
      setOrders([])
    }
  }

  useEffect(() => {
    fetchRows()
    fetchOrders()
  }, [orderNumber])

  const orderOptions = orders.map((order) => ({
    value: order.order_number,
    label: `${order.order_number} · ${order.material_code}`,
  }))

  const analyze = async (orderNumberValue: string) => {
    setBusy(true)
    try {
      await api.post('/planning/cost/variances/analyze', {
        production_order_number: orderNumberValue,
      })
      message.success(`工单 ${orderNumberValue} 差异分析完成`)
      setAnalyzeOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '差异分析失败')
      throw error
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '差异编号', dataIndex: 'variance_number', key: 'variance_number', width: 170 },
    { title: '工单号', dataIndex: 'production_order_number', key: 'production_order_number', width: 170 },
    {
      title: '差异类型',
      dataIndex: 'variance_type',
      key: 'variance_type',
      width: 130,
      render: (value: string) => VARIANCE_TYPE[value] ?? value,
    },
    {
      title: '标准金额',
      dataIndex: 'standard_amount',
      key: 'standard_amount',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '实际金额',
      dataIndex: 'actual_amount',
      key: 'actual_amount',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '差异金额',
      dataIndex: 'variance_amount',
      key: 'variance_amount',
      align: 'right' as const,
      width: 120,
      render: (value: number) => (
        <span style={{ color: value > 0 ? '#cf1322' : value < 0 ? '#389e0d' : undefined, fontWeight: value !== 0 ? 600 : 400 }}>
          {fmtMoney(value)}
        </span>
      ),
    },
    {
      title: '差异率',
      dataIndex: 'variance_pct',
      key: 'variance_pct',
      align: 'right' as const,
      width: 90,
      render: (value: number) => `${value ?? 0}%`,
    },
    {
      title: '分析时间',
      dataIndex: 'analyzed_at',
      key: 'analyzed_at',
      width: 160,
      render: (value: string) => value?.replace('T', ' ').slice(0, 19) ?? '-',
    },
    {
      title: '说明',
      dataIndex: 'remarks',
      key: 'remarks',
      ellipsis: true,
    },
  ]

  return (
    <div>
      <PageHeader
        title="差异分析"
        description="对比标准成本与实际成本，定位材料价格 / 用量 / 人工 / 制造费用差异"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<LineChartOutlined />} onClick={() => setAnalyzeOpen(true)}>
              差异分析
            </Button>
          </Space>
        }
      />

      <Space wrap className="mb-4">
        <Select
          allowClear
          style={{ width: 220 }}
          placeholder="按工单筛选"
          showSearch
          optionFilterProp="label"
          value={orderNumber}
          onChange={setOrderNumber}
          options={orderOptions}
        />
      </Space>

      <Table
        rowKey="variance_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title="差异分析"
        open={analyzeOpen}
        onCancel={() => setAnalyzeOpen(false)}
        onOk={() => targetOrder && analyze(targetOrder)}
        confirmLoading={busy}
        okText="分析"
        width={520}
        destroyOnClose
      >
        <p className="mb-2 text-sm text-ink-soft">
          选择工单，系统将重新归集其实际成本并生成价格 / 用量 / 人工 / 费用五类差异。
        </p>
        <Select
          style={{ width: '100%' }}
          placeholder="选择工单"
          showSearch
          optionFilterProp="label"
          value={targetOrder}
          onChange={setTargetOrder}
          options={orderOptions}
        />
      </Modal>
    </div>
  )
}

export default CostVarianceList