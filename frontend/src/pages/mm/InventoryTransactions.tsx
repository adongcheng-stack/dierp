import { useEffect, useState } from 'react'
import { Button, DatePicker, Input, Select, Space, Table, Tag, Tooltip } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const TX_TYPE: Record<string, { text: string; color: string }> = {
  ISSUE: { text: '领料出库', color: 'orange' },
  RECEIPT: { text: '到货入库', color: 'green' },
  RETURN: { text: '退货出库', color: 'red' },
  ADJUSTMENT: { text: '调整', color: 'blue' },
}

const REF_TYPE: Record<string, string> = {
  MATERIAL_ISSUE: '领料单',
  PURCHASE_ORDER: '采购单',
  PURCHASE_RETURN: '退货索赔单',
  STOCK_ADJUSTMENT: '库存调整',
}

interface TxRow {
  transaction_number: string
  material_code: string
  material_name: string | null
  transaction_type: string
  quantity: number
  unit: string
  reference_number: string | null
  reference_type: string | null
  warehouse: string | null
  transaction_date: string | null
  operator: string | null
  remarks: string | null
}

const { RangePicker } = DatePicker

const InventoryTransactions: React.FC = () => {
  const [rows, setRows] = useState<TxRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [dateRange, setDateRange] = useState<[any, any] | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: any = { limit: 200 }
      if (keyword.trim()) params.material_code = keyword.trim()
      if (typeFilter) params.transaction_type = typeFilter
      if (dateRange?.[0]) params.start_date = dateRange[0].format('YYYY-MM-DD') + 'T00:00:00'
      if (dateRange?.[1]) params.end_date = dateRange[1].format('YYYY-MM-DD') + 'T23:59:59'
      const response = await api.get('/mm/transactions', { params })
      setRows(response.data.items ?? [])
      setTotal(response.data.total ?? 0)
    } catch (error) {
      console.error('获取库存流水失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '流水号', dataIndex: 'transaction_number', key: 'n', width: 165 },
    { title: '物料编码', dataIndex: 'material_code', key: 'm', width: 145 },
    { title: '物料名称', dataIndex: 'material_name', key: 'mn', ellipsis: true, render: (v: string | null) => v || '-' },
    {
      title: '类型',
      dataIndex: 'transaction_type',
      key: 't',
      width: 105,
      render: (v: string) => {
        const item = TX_TYPE[v]
        return item ? <Tag color={item.color}>{item.text}</Tag> : <Tag>{v}</Tag>
      },
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'q',
      width: 100,
      align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: v < 0 ? '#cf1322' : '#3f8600', fontWeight: 600 }}>
          {v > 0 ? `+${v}` : v}
        </span>
      ),
    },
    { title: '单位', dataIndex: 'unit', key: 'u', width: 70 },
    {
      title: '关联单据',
      key: 'ref',
      width: 220,
      render: (_: unknown, row: TxRow) =>
        row.reference_number ? (
          <Tooltip title={REF_TYPE[row.reference_type ?? ''] ?? row.reference_type}>
            <span>{row.reference_number}</span>
          </Tooltip>
        ) : (
          '-'
        ),
    },
    { title: '仓库', dataIndex: 'warehouse', key: 'w', width: 90, render: (v: string | null) => v || '-' },
    { title: '发生时间', dataIndex: 'transaction_date', key: 'd', width: 160, render: (v: string | null) => (v ? v.replace('T', ' ').slice(0, 19) : '-') },
    { title: '操作人', dataIndex: 'operator', key: 'o', width: 100, render: (v: string | null) => v || '-' },
    { title: '备注', dataIndex: 'remarks', key: 'r', ellipsis: true },
  ]

  return (
    <div>
      <PageHeader
        title="库存流水"
        description="库存账本：生产领料（ISSUE）/ 采购到货（RECEIPT）/ 采购退货（RETURN）每笔变动可追溯，含关联单据号"
      />
      <Space style={{ marginBottom: 12 }} wrap>
        <Input
          prefix={<SearchOutlined />}
          placeholder="按物料编码搜索"
          allowClear
          style={{ width: 200 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={fetchData}
        />
        <Select
          allowClear
          placeholder="按类型筛选"
          style={{ width: 140 }}
          value={typeFilter}
          onChange={(v) => setTypeFilter(v)}
          options={Object.entries(TX_TYPE).map(([value, item]) => ({ value, label: item.text }))}
        />
        <RangePicker
          value={dateRange}
          onChange={(v) => setDateRange(v as [any, any] | null)}
          placeholder={['开始日期', '结束日期']}
        />
        <Button type="primary" onClick={fetchData} loading={loading}>
          查询
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => {
            setKeyword('')
            setTypeFilter(undefined)
            setDateRange(null)
            fetchData()
          }}
        >
          重置
        </Button>
      </Space>
      <Table
        rowKey="transaction_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false, showTotal: (t) => `共 ${t} 条` }}
        size="middle"
        scroll={{ x: 1250 }}
      />
      <div className="mt-3 text-xs text-ink-faint">共 {total} 条流水；正数为入库、负数为出库。</div>
    </div>
  )
}

export default InventoryTransactions
