import { Table, Button } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const MaterialIssueList: React.FC = () => {
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchIssues()
  }, [])

  const fetchIssues = async () => {
    setLoading(true)
    try {
      const response = await api.get('/mm/material-issues')
      setIssues(response.data)
    } catch (error) {
      console.error('获取领料单列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: '领料单号', dataIndex: 'issue_number', key: 'issue_number' },
    { title: '生产订单号', dataIndex: 'production_order_number', key: 'production_order_number' },
    { title: '物料编码', dataIndex: 'material_code', key: 'material_code' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '原料批次', dataIndex: 'batch_number', key: 'batch_number', render: (v?: string) => v || '-' },
    { title: '来源采购单', dataIndex: 'purchase_order_number', key: 'purchase_order_number', render: (v?: string) => v || '-' },
    { title: '领料人', dataIndex: 'issued_by', key: 'issued_by' },
  ]

  return (
    <div>
      <PageHeader
        title="生产领料"
        description="按生产订单领料并自动扣减库存"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/mm/material-issues/new')}
          >
            新建领料单
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={issues}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default MaterialIssueList

