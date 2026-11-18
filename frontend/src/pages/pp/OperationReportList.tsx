import { Table, Button, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const REPORT_STATUS: { [key: string]: { color: string; text: string } } = {
  PENDING: { color: 'orange', text: '待处理' },
  IN_PROGRESS: { color: 'blue', text: '进行中' },
  COMPLETED: { color: 'green', text: '已完成' },
  REJECTED: { color: 'red', text: '已拒绝' }
}

const OperationReportList: React.FC = () => {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchReports()
  }, [])

  const fetchReports = async () => {
    setLoading(true)
    try {
      const response = await api.get('/pp/operation-reports')
      setReports(response.data)
    } catch (error) {
      console.error('获取工序报工列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: '报工单号', dataIndex: 'report_number', key: 'report_number' },
    { title: '生产订单号', dataIndex: 'production_order_number', key: 'production_order_number' },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'work_center_id' },
    { title: '工序号', dataIndex: 'operation_no', key: 'operation_no' },
    { title: '报工数量', dataIndex: 'reported_quantity', key: 'reported_quantity' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const info = REPORT_STATUS[status] || { color: 'default', text: status }
        return <Tag color={info.color}>{info.text}</Tag>
      }
    },
  ]

  return (
    <div>
      <PageHeader
        title="工序报工"
        description="按 LOT 卡与工序登记报工数量与工时"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/pp/operation-reports/new')}
          >
            新建报工
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={reports}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default OperationReportList

