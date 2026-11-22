import { useEffect, useState } from 'react'
import { Button, Card, Space, Table, Tag, Tooltip, message } from 'antd'
import { ReloadOutlined, WarningOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface BatchRow {
  material_code: string
  material_name: string | null
  shelf_life_days: number | null
  lot_count: number
  lot_qty: number
  last_completed_at: string | null
  estimated_expiry: string | null
  days_to_expiry: number | null
  warning: boolean
  estimate_pending: boolean
}

const BatchTracking: React.FC = () => {
  const [rows, setRows] = useState<BatchRow[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/mm/batch-tracking')
      setRows(response.data.items || [])
    } catch (error) {
      message.error(getErrorMessage(error) || '加载批次效期失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '物料编码', dataIndex: 'material_code', width: 180 },
    { title: '物料名称', dataIndex: 'material_name', render: (v: string | null) => v || '-' },
    {
      title: '效期(天)',
      dataIndex: 'shelf_life_days',
      width: 100,
      align: 'right' as const,
      render: (v: number | null) => v ?? '—',
    },
    { title: '批次数', dataIndex: 'lot_count', width: 90, align: 'right' as const },
    { title: '在制/在库量', dataIndex: 'lot_qty', width: 120, align: 'right' as const, render: (v: number) => v?.toFixed(2) },
    {
      title: '最近完成',
      dataIndex: 'last_completed_at',
      width: 150,
      render: (v: string | null) => (v ? v.slice(0, 16).replace('T', ' ') : '—'),
    },
    {
      title: '估算到期',
      dataIndex: 'estimated_expiry',
      width: 130,
      render: (v: string | null) =>
        v ? (
          <Tooltip title="按最近完成时间 + 效期天数估算">
            {v} <span style={{ color: 'var(--color-muted)' }}>(估)</span>
          </Tooltip>
        ) : (
          <Tag>待完工序</Tag>
        ),
    },
    {
      title: '剩余天数',
      dataIndex: 'days_to_expiry',
      width: 110,
      align: 'right' as const,
      render: (v: number | null) => {
        if (v === null) return <Tag>—</Tag>
        if (v < 0) return <Tag color="error">已过期 {-v} 天</Tag>
        return <span style={{ color: v <= 30 ? 'var(--color-error)' : undefined }}>{v}</span>
      },
    },
    {
      title: '预警',
      dataIndex: 'warning',
      width: 110,
      render: (v: boolean, r: BatchRow) =>
        v ? <Tag icon={<WarningOutlined />} color="error">临期/过期</Tag> : r.estimate_pending ? <Tag>无法估算</Tag> : <Tag color="green">正常</Tag>,
    },
  ]

  return (
    <div>
      <PageHeader title="批次效期" description="按物料聚合 ACTIVE LOT 卡（纯读视图）；到期日按「最近完成 + 效期天数」估算，≤30 天或已过期预警" />
      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
          </Space>
        }
      >
        <Table
          rowKey="material_code"
          columns={columns}
          dataSource={rows}
          loading={loading}
          pagination={false}
          rowClassName={(r: BatchRow) => (r.warning ? 'ant-table-row-warning' : '')}
          scroll={{ x: 1100 }}
        />
      </Card>
    </div>
  )
}

export default BatchTracking
