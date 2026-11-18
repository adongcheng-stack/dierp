import { useEffect, useState } from 'react'
import { Button, Modal, Select, Space, Table, message } from 'antd'
import { ReloadOutlined, CalculatorOutlined, SaveOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { COST_STATUS, StatusTag, fmtMoney, fmtQty } from './shared'

const ProductionCostList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | undefined>()
  const [collectOpen, setCollectOpen] = useState(false)
  const [targetOrder, setTargetOrder] = useState<string | undefined>()
  const [busy, setBusy] = useState(false)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/cost/production', {
        params: { limit: 300, status },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取工单成本失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchOrders = async () => {
    try {
      const response = await api.get('/pp/production-orders', { params: { limit: 300 } })
      const data = response.data
      const list = Array.isArray(data) ? data : data?.items ?? []
      setOrders(list.filter((item: any) => !['CANCELLED'].includes(item.status)))
    } catch {
      setOrders([])
    }
  }

  useEffect(() => {
    fetchRows()
    fetchOrders()
  }, [status])

  const orderOptions = orders.map((order) => ({
    value: order.order_number,
    label: `${order.order_number} · ${order.material_code} · ${fmtQty(order.quantity)}`,
  }))

  const openCollect = () => {
    setTargetOrder(undefined)
    setCollectOpen(true)
  }

  const collect = async (orderNumber: string) => {
    setBusy(true)
    try {
      const response = await api.post('/planning/cost/production/collect', {
        production_order_number: orderNumber,
      })
      message.success(`工单 ${orderNumber} 成本已归集`)
      setCollectOpen(false)
      fetchRows()
      return response.data
    } catch (error) {
      message.error(getErrorMessage(error) || '归集成本失败')
      throw error
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '成本编号', dataIndex: 'cost_id', key: 'cost_id', width: 150 },
    { title: '工单号', dataIndex: 'production_order_number', key: 'production_order_number', width: 170 },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right' as const,
      width: 90,
      render: fmtQty,
    },
    {
      title: '材料(实际)',
      dataIndex: 'material_cost_actual',
      key: 'material_cost_actual',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '人工(实际)',
      dataIndex: 'labor_cost_actual',
      key: 'labor_cost_actual',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '制造费用',
      dataIndex: 'overhead_actual',
      key: 'overhead_actual',
      align: 'right' as const,
      width: 110,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '实际总成本',
      dataIndex: 'total_actual',
      key: 'total_actual',
      align: 'right' as const,
      width: 130,
      render: (value: number) => <b>{fmtMoney(value)}</b>,
    },
    {
      title: '标准成本',
      dataIndex: 'standard_cost',
      key: 'standard_cost',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '在制品',
      dataIndex: 'wip_value',
      key: 'wip_value',
      align: 'right' as const,
      width: 110,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={COST_STATUS} />,
    },
    {
      title: '归集时间',
      dataIndex: 'collected_at',
      key: 'collected_at',
      width: 150,
      render: (value: string) => value?.replace('T', ' ').slice(0, 19) ?? '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 110,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Button
          type="link"
          icon={<CalculatorOutlined />}
          loading={busy}
          onClick={() => collect(record.production_order_number)}
        >
          归集
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="工单成本"
        description="按工单归集实际领料与工序报工成本，形成标准 vs 实际对比"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={openCollect}>
              归集工单成本
            </Button>
          </Space>
        }
      />

      <Space wrap className="mb-4">
        <Select
          allowClear
          style={{ width: 160 }}
          placeholder="成本状态"
          value={status}
          onChange={setStatus}
          options={[
            { value: 'OPEN', label: '待归集' },
            { value: 'COLLECTED', label: '已归集' },
            { value: 'SETTLED', label: '已结算' },
          ]}
        />
      </Space>

      <Table
        rowKey="cost_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 12, showSizeChanger: false }}
        scroll={{ x: 1500 }}
      />

      <Modal
        title="归集工单实际成本"
        open={collectOpen}
        onCancel={() => setCollectOpen(false)}
        onOk={() => targetOrder && collect(targetOrder)}
        confirmLoading={busy}
        okText="归集"
        width={520}
        destroyOnClose
      >
        <p className="mb-2 text-sm text-ink-soft">
          选择一张工单，系统将按其领料记录与工序报工（× 费率）归集实际成本。
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

export default ProductionCostList