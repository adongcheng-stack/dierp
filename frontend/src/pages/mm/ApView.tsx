import { useEffect, useState } from 'react'
import { Button, Card, Col, Row, Statistic, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const ApView: React.FC = () => {
  const [items, setItems] = useState<any[]>([])
  const [totalPayable, setTotalPayable] = useState(0)
  const [totalReceived, setTotalReceived] = useState(0)
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/purchase/ap-view')
      setItems(response.data.items ?? [])
      setTotalPayable(response.data.total_payable ?? 0)
      setTotalReceived(response.data.total_received ?? 0)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取应付账款失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const fmt = (v: number) =>
    `¥${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`

  const columns = [
    { title: '供应商编码', dataIndex: 'supplier_id', key: 'supplier_id', width: 130 },
    { title: '供应商', dataIndex: 'supplier_name', key: 'supplier_name' },
    { title: '已到货金额', dataIndex: 'received_amount', key: 'received_amount', width: 140, align: 'right' as const, render: fmt },
    { title: '已退金额', dataIndex: 'returned_amount', key: 'returned_amount', width: 130, align: 'right' as const, render: fmt },
    { title: '已结金额', dataIndex: 'closed_amount', key: 'closed_amount', width: 140, align: 'right' as const, render: fmt },
    {
      title: '应付金额',
      dataIndex: 'payable_amount',
      key: 'payable_amount',
      width: 150,
      align: 'right' as const,
      render: (v: number) =>
        v > 0 ? <span style={{ color: '#cf1322' }}>{fmt(v)}</span> : <Tag color="green">已结清</Tag>,
    },
  ]

  return (
    <div>
      <PageHeader
        title="应付账款"
        description="按供应商汇总采购到货应付：到货金额 = 收货数量 × 单价；整单关闭视为结清"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        }
      />
      <Row gutter={16} className="mb-4">
        <Col span={8}>
          <Card>
            <Statistic title="应付总额" value={totalPayable} precision={2} prefix="¥" valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="已到货总额" value={totalReceived} precision={2} prefix="¥" />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="供应商数" value={items.length} />
          </Card>
        </Col>
      </Row>
      <Card>
        <Table
          rowKey="supplier_id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 15, showSizeChanger: false, showTotal: (t) => `共 ${t} 家` }}
          scroll={{ x: 720 }}
        />
      </Card>
    </div>
  )
}

export default ApView