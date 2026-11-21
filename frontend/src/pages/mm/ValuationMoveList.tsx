import { useEffect, useState } from 'react'
import { Button, Card, Input, Select, Space, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface Move {
  move_number: string
  material_code: string
  direction: 'IN' | 'OUT'
  qty: number
  unit_cost: number
  amount: number
  balance_qty: number
  balance_amount: number
  source_type: string
  source_ref: string
  reversal_of: string | null
  created_at: string | null
}

const SOURCE_LABELS: Record<string, string> = {
  PURCHASE_RECEIPT: '采购收货',
  PURCHASE_RETURN: '采购退货',
  PRODUCTION_COMPLETE: '完工入库',
  MATERIAL_ISSUE: '生产领料',
  SALES_ISSUE: '销售发货',
  SALES_RETURN: '销售退回',
  STOCKTAKE: '盘点调整',
  OPENING: '期初建账',
  TRANSFER: '仓库调拨',
}

const ValuationMoveList: React.FC = () => {
  const [rows, setRows] = useState<Move[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [materialFilter, setMaterialFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string | undefined>()

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (materialFilter) params.material_code = materialFilter
      if (sourceFilter) params.source_type = sourceFilter
      const response = await api.get('/mm/valuation-moves', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载估值流水失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [sourceFilter])

  const columns = [
    { title: '流水号', dataIndex: 'move_number', width: 170 },
    { title: '物料', dataIndex: 'material_code', width: 180 },
    {
      title: '方向',
      dataIndex: 'direction',
      width: 80,
      render: (v: string) => <Tag color={v === 'IN' ? 'green' : 'orange'}>{v === 'IN' ? '入库' : '出库'}</Tag>,
    },
    {
      title: '业务事件',
      dataIndex: 'source_type',
      width: 120,
      render: (v: string) => SOURCE_LABELS[v] || v,
    },
    { title: '来源单据', dataIndex: 'source_ref', width: 180 },
    { title: '数量', dataIndex: 'qty', width: 100, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    { title: '单价(成本快照)', dataIndex: 'unit_cost', width: 140, align: 'right' as const, render: (v: number) => v?.toFixed(4) },
    { title: '金额', dataIndex: 'amount', width: 120, align: 'right' as const, render: (v: number) => `¥${(v ?? 0).toFixed(2)}` },
    { title: '余额(数量)', dataIndex: 'balance_qty', width: 120, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    { title: '余额(金额)', dataIndex: 'balance_amount', width: 130, align: 'right' as const, render: (v: number) => `¥${(v ?? 0).toFixed(2)}` },
    { title: '红冲来源', dataIndex: 'reversal_of', width: 160, render: (v: string | null) => v || '-' },
    { title: '时间', dataIndex: 'created_at', width: 150, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
  ]

  return (
    <div>
      <PageHeader title="估值流水" description="移动加权实际成本流水：每次出入库的成本快照、余额与业务来源（红冲按原单价）" />
      <Card
        extra={
          <Space>
            <Input
              allowClear
              placeholder="物料编码"
              style={{ width: 160 }}
              value={materialFilter}
              onChange={(event) => setMaterialFilter(event.target.value)}
              onPressEnter={fetchData}
            />
            <Select
              allowClear
              placeholder="业务事件"
              style={{ width: 140 }}
              value={sourceFilter}
              onChange={setSourceFilter}
              options={Object.entries(SOURCE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          </Space>
        }
      >
        <Table rowKey="move_number" columns={columns} dataSource={rows} loading={loading}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 条` }} scroll={{ x: 1600 }} />
      </Card>
    </div>
  )
}

export default ValuationMoveList
