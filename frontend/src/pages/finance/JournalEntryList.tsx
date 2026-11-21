import { useEffect, useState } from 'react'
import { Button, Card, Select, Space, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

/** 凭证来源事件 → 单据列表路由（点击 source_ref 溯源跳转，设计 §5.3） */
const SOURCE_ROUTES: Record<string, { path: string; param: string }> = {
  SALES_INVOICE_ISSUED: { path: '/sd/invoices', param: 'invoice_number' },
  SALES_DELIVERY_SHIPPED: { path: '/sd/deliveries', param: 'delivery_number' },
  SUPPLIER_INVOICE_CONFIRMED: { path: '/mm/supplier-invoices', param: 'invoice_number' },
  SUPPLIER_PAYMENT_PAID: { path: '/mm/payments', param: 'payment_number' },
  RECEIPT_PAID: { path: '/sd/receipts', param: 'receipt_number' },
  MATERIAL_ISSUE: { path: '/mm/material-issues', param: 'issue_number' },
  STOCK_ADJUST: { path: '/mm/stocktakes', param: 'stocktake_number' },
  PRODUCTION_COMPLETE: { path: '/pp/production-orders', param: 'order_number' },
}

const SOURCE_TYPE: Record<string, string> = {
  SALES_INVOICE_ISSUED: '销售开票',
  SALES_DELIVERY_SHIPPED: '发货出库',
  SUPPLIER_INVOICE_CONFIRMED: '采购发票确认',
  SUPPLIER_PAYMENT_PAID: '付款核销',
  RECEIPT_PAID: '收款核销',
  MATERIAL_ISSUE: '生产领料',
  STOCK_ADJUST: '库存调整',
  PRODUCTION_COMPLETE: '完工入库',
}

const STATUS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  POSTED: { label: '已过账', color: 'success' },
}

interface JournalLine {
  line_number: number
  account_code: string
  debit: number
  credit: number
  summary: string | null
}

interface JournalEntry {
  entry_number: string
  entry_date: string | null
  period_code: string
  status: string
  source_type: string
  source_ref: string
  remarks: string | null
  lines: JournalLine[]
}

const money = (v: number | undefined | null) => (v ?? 0).toFixed(2)

const JournalEntryList: React.FC = () => {
  const navigate = useNavigate()
  const [rows, setRows] = useState<JournalEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<string | undefined>()
  const [statusFilter, setStatusFilter] = useState<string | undefined>()

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { limit: 100 }
      if (sourceFilter) params.source_type = sourceFilter
      if (statusFilter) params.entry_status = statusFilter
      const response = await api.get('/finance/journal-entries', { params })
      setRows(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载凭证失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [sourceFilter, statusFilter])

  const columns = [
    { title: '凭证号', dataIndex: 'entry_number', width: 150 },
    { title: '记账日期', dataIndex: 'entry_date', width: 150, render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '-') },
    { title: '期间', dataIndex: 'period_code', width: 90 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const s = STATUS[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '业务事件',
      dataIndex: 'source_type',
      width: 140,
      render: (v: string) => SOURCE_TYPE[v] || v,
    },
    {
      title: '来源单据',
      dataIndex: 'source_ref',
      width: 170,
      render: (ref: string, record: JournalEntry) => {
        const route = SOURCE_ROUTES[record.source_type]
        if (!route || !ref) return <span>{ref || '-'}</span>
        return (
          <a
            onClick={() => navigate(`${route.path}?${route.param}=${encodeURIComponent(ref)}`)}
            title={`跳转到 ${ref} 的来源单据`}
          >
            {ref}
          </a>
        )
      },
    },
    { title: '摘要', dataIndex: 'remarks', ellipsis: true },
  ]

  const expandedRowRender = (record: JournalEntry) => (
    <Table
      rowKey="line_number"
      size="small"
      pagination={false}
      dataSource={record.lines || []}
      columns={[
        { title: '行', dataIndex: 'line_number', width: 60 },
        { title: '科目', dataIndex: 'account_code', width: 100 },
        { title: '摘要', dataIndex: 'summary', ellipsis: true },
        { title: '借方', dataIndex: 'debit', width: 120, align: 'right' as const, render: money },
        { title: '贷方', dataIndex: 'credit', width: 120, align: 'right' as const, render: money },
      ]}
    />
  )

  return (
    <div>
      <PageHeader title="凭证查询" description="业务动作自动过账（SALES/RECEIPT/…），展开行可查分录借贷明细" />
      <Card
        extra={
          <Space>
            <Select
              allowClear
              placeholder="业务事件"
              style={{ width: 160 }}
              value={sourceFilter}
              onChange={setSourceFilter}
              options={Object.entries(SOURCE_TYPE).map(([k, v]) => ({ value: k, label: v }))}
            />
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 110 }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={Object.entries(STATUS).map(([k, v]) => ({ value: k, label: v.label }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          </Space>
        }
      >
        <Table
          rowKey="entry_number"
          columns={columns}
          dataSource={rows}
          loading={loading}
          expandable={{ expandedRowRender }}
          pagination={{ total, pageSize: 100, showTotal: (t) => `共 ${t} 张` }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  )
}

export default JournalEntryList
