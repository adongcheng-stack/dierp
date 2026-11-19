import { useEffect, useState } from 'react'
import { Card, Table, Tag, message, Button, Space } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const ACCOUNT_TYPE: Record<string, { label: string; color: string }> = {
  ASSET: { label: '资产', color: 'blue' },
  LIABILITY: { label: '负债', color: 'orange' },
  EQUITY: { label: '权益', color: 'purple' },
  REVENUE: { label: '收入', color: 'green' },
  EXPENSE: { label: '成本费用', color: 'red' },
}

interface Account {
  account_code: string
  account_name: string
  account_type: string
  parent_code: string | null
  is_leaf: boolean
}

const AccountList: React.FC = () => {
  const [rows, setRows] = useState<Account[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/finance/accounts')
      setRows(response.data.items || [])
    } catch (error) {
      message.error(getErrorMessage(error) || '加载科目表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '科目编码', dataIndex: 'account_code', width: 120 },
    { title: '科目名称', dataIndex: 'account_name' },
    {
      title: '科目类别',
      dataIndex: 'account_type',
      width: 120,
      render: (v: string) => {
        const t = ACCOUNT_TYPE[v] || { label: v, color: 'default' }
        return <Tag color={t.color}>{t.label}</Tag>
      },
    },
    { title: '上级科目', dataIndex: 'parent_code', width: 120, render: (v: string | null) => v || '—' },
    {
      title: '明细科目',
      dataIndex: 'is_leaf',
      width: 100,
      render: (v: boolean) => (v ? <Tag color="green">叶子</Tag> : <Tag>汇总</Tag>),
    },
  ]

  return (
    <div>
      <PageHeader title="会计科目" description="总账科目表（P2 demo：8 个一级明细科目，种子维护）" />
      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
          </Space>
        }
      >
        <Table rowKey="account_code" columns={columns} dataSource={rows} loading={loading}
          pagination={false} />
      </Card>
    </div>
  )
}

export default AccountList
