import { useEffect, useState } from 'react'
import { Button, Card, Space, Table, message } from 'antd'
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface Aging {
  current: number
  d30: number
  d60: number
  d90: number
  d90p: number
}

interface ReceivableRow {
  customer_id: string | null
  customer_name: string | null
  invoice_count: number
  invoiced_amount: number
  received_amount: number
  outstanding_amount: number
  aging: Aging
}

interface Totals {
  invoiced_amount: number
  received_amount: number
  outstanding_amount: number
}

const money = (v: number | undefined | null) => (v ?? 0).toFixed(2)

const ReceivableView: React.FC = () => {
  const [rows, setRows] = useState<ReceivableRow[]>([])
  const [totals, setTotals] = useState<Totals>({ invoiced_amount: 0, received_amount: 0, outstanding_amount: 0 })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/sd/receivables')
      setRows(response.data.items || [])
      setTotals(response.data.totals || { invoiced_amount: 0, received_amount: 0, outstanding_amount: 0 })
    } catch (error) {
      message.error(getErrorMessage(error) || '加载应收台账失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '客户编码', dataIndex: 'customer_id', width: 140 },
    { title: '客户名称', dataIndex: 'customer_name', width: 200, render: (v: string | null) => v || '-' },
    { title: '发票数', dataIndex: 'invoice_count', width: 90 },
    { title: '开票额', key: 'invoiced', width: 130, render: (_: unknown, r: ReceivableRow) => money(r.invoiced_amount) },
    { title: '已收', key: 'received', width: 130, render: (_: unknown, r: ReceivableRow) => money(r.received_amount) },
    {
      title: '未收',
      key: 'outstanding',
      width: 130,
      render: (_: unknown, r: ReceivableRow) => <strong>{money(r.outstanding_amount)}</strong>,
    },
    { title: '未逾期', key: 'current', width: 120, render: (_: unknown, r: ReceivableRow) => money(r.aging?.current) },
    { title: '逾期 1-30', key: 'd30', width: 120, render: (_: unknown, r: ReceivableRow) => money(r.aging?.d30) },
    { title: '逾期 31-60', key: 'd60', width: 120, render: (_: unknown, r: ReceivableRow) => money(r.aging?.d60) },
    { title: '逾期 61-90', key: 'd90', width: 120, render: (_: unknown, r: ReceivableRow) => money(r.aging?.d90) },
    { title: '逾期 90+', key: 'd90p', width: 120, render: (_: unknown, r: ReceivableRow) => money(r.aging?.d90p) },
    {
      title: '操作',
      key: 'actions',
      width: 130,
      render: (_: unknown, r: ReceivableRow) => (
        <Button size="small" icon={<FileTextOutlined />}
          onClick={() => navigate(`/sd/invoices?customer_id=${encodeURIComponent(r.customer_id || '')}`)}>
          查看发票
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="应收台账" description={`按客户聚合：开票 ${money(totals.invoiced_amount)} · 已收 ${money(totals.received_amount)} · 未收 ${money(totals.outstanding_amount)}（收款核销见 P1）`} />
      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          </Space>
        }
      >
        <Table rowKey={(r) => r.customer_id || '-'} columns={columns} dataSource={rows} loading={loading}
          pagination={false} scroll={{ x: 1500 }} />
      </Card>
    </div>
  )
}

export default ReceivableView
