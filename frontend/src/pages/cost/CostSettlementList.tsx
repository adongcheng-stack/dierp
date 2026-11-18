import { useEffect, useState } from 'react'
import { Button, Modal, Select, Space, Table, message } from 'antd'
import { ReloadOutlined, CheckCircleOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { COST_STATUS, StatusTag, fmtMoney } from './shared'

const CostSettlementList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [settleOpen, setSettleOpen] = useState(false)
  const [targetOrder, setTargetOrder] = useState<string | undefined>()
  const [busy, setBusy] = useState(false)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/cost/settlements', { params: { limit: 300 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取成本结算失败')
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
  }, [])

  const orderOptions = orders.map((order) => ({
    value: order.order_number,
    label: `${order.order_number} · ${order.material_code}`,
  }))

  const settle = async (orderNumberValue: string) => {
    setBusy(true)
    try {
      await api.post('/planning/cost/settlement/settle', {
        production_order_number: orderNumberValue,
      })
      message.success(`工单 ${orderNumberValue} 成本已结算`)
      setSettleOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '成本结算失败')
      throw error
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '结算编号', dataIndex: 'settlement_number', key: 'settlement_number', width: 160 },
    { title: '工单号', dataIndex: 'production_order_number', key: 'production_order_number', width: 170 },
    {
      title: '总成本',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right' as const,
      width: 130,
      render: (value: number) => <b>{fmtMoney(value)}</b>,
    },
    {
      title: '在制品价值',
      dataIndex: 'wip_value',
      key: 'wip_value',
      align: 'right' as const,
      width: 130,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '状态',
      dataIndex: 'settlement_status',
      key: 'settlement_status',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={COST_STATUS} />,
    },
    {
      title: '结算时间',
      dataIndex: 'settled_at',
      key: 'settled_at',
      width: 170,
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
        title="成本结算"
        description="对已完工工单进行成本结算，固化实际成本并转入在制品/总账口径"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => setSettleOpen(true)}>
              工单结算
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="settlement_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1000 }}
      />

      <Modal
        title="工单成本结算"
        open={settleOpen}
        onCancel={() => setSettleOpen(false)}
        onOk={() => targetOrder && settle(targetOrder)}
        confirmLoading={busy}
        okText="结算"
        width={520}
        destroyOnClose
      >
        <p className="mb-2 text-sm text-ink-soft">
          选择工单进行成本结算。结算会归集实际成本、生成差异分析并固化结算记录。
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

export default CostSettlementList