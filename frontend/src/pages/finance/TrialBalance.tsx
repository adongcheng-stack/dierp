import { useEffect, useState } from 'react'
import { Alert, Button, Card, Select, Space, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const ACCOUNT_TYPE: Record<string, string> = {
  ASSET: '资产',
  LIABILITY: '负债',
  EQUITY: '权益',
  REVENUE: '收入',
  EXPENSE: '成本费用',
}

interface TrialRow {
  account_code: string
  account_name: string
  account_type: string
  debit_total: number
  credit_total: number
  balance: number
}

const money = (v: number | undefined | null) => (v ?? 0).toFixed(2)

const TrialBalance: React.FC = () => {
  const [rows, setRows] = useState<TrialRow[]>([])
  const [totals, setTotals] = useState({ total_debit: 0, total_credit: 0, balanced: true })
  const [periods, setPeriods] = useState<string[]>([])
  const [periodFilter, setPeriodFilter] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {}
      if (periodFilter) params.period_code = periodFilter
      const response = await api.get('/finance/trial-balance', { params })
      setRows(response.data.items || [])
      setTotals({
        total_debit: response.data.total_debit ?? 0,
        total_credit: response.data.total_credit ?? 0,
        balanced: response.data.balanced ?? true,
      })
    } catch (error) {
      message.error(getErrorMessage(error) || '加载余额表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchPeriods = async () => {
    try {
      const response = await api.get('/finance/periods')
      setPeriods((response.data.items || []).map((p: { period_code: string }) => p.period_code))
    } catch {
      // 期间选项加载失败不阻塞
    }
  }

  useEffect(() => {
    fetchData()
  }, [periodFilter])

  useEffect(() => {
    fetchPeriods()
  }, [])

  const columns = [
    { title: '科目编码', dataIndex: 'account_code', width: 110 },
    { title: '科目名称', dataIndex: 'account_name' },
    {
      title: '类别',
      dataIndex: 'account_type',
      width: 100,
      render: (v: string) => ACCOUNT_TYPE[v] || v,
    },
    { title: '借方发生', dataIndex: 'debit_total', width: 140, align: 'right' as const, render: money },
    { title: '贷方发生', dataIndex: 'credit_total', width: 140, align: 'right' as const, render: money },
    {
      title: '余额(借-贷)',
      dataIndex: 'balance',
      width: 140,
      align: 'right' as const,
      render: (v: number) => (
        <strong style={{ color: v >= 0 ? '#cf1322' : '#389e0d' }}>{money(v)}</strong>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="余额表 / 试算平衡" description="按科目聚合已过账凭证：借方发生、贷方发生与余额（铁律 Σ借 = Σ贷）" />
      {!totals.balanced && (
        <Alert
          type="error"
          showIcon
          message={`试算不平衡：Σ借 ${money(totals.total_debit)} ≠ Σ贷 ${money(totals.total_credit)}`}
          style={{ marginBottom: 12 }}
        />
      )}
      <Card
        extra={
          <Space>
            <Select
              allowClear
              placeholder="会计期间"
              style={{ width: 130 }}
              value={periodFilter}
              onChange={setPeriodFilter}
              options={periods.map((p) => ({ value: p, label: p }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
          </Space>
        }
      >
        <Table
          rowKey="account_code"
          columns={columns}
          dataSource={rows}
          loading={loading}
          pagination={false}
          summary={() => (
            <Table.Summary fixed>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={3}>
                  <strong>合计</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  <strong>{money(totals.total_debit)}</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  <strong>{money(totals.total_credit)}</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <Tag color={totals.balanced ? 'green' : 'red'}>
                    {totals.balanced ? 'Σ借 = Σ贷 ✓' : 'Σ借 ≠ Σ贷'}
                  </Tag>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>
    </div>
  )
}

export default TrialBalance
