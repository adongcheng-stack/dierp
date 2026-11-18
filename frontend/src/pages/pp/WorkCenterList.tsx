import { Table, Button, Tag } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const WORK_CENTER_STATUS: { [key: string]: { color: string; text: string } } = {
  ACTIVE: { color: 'green', text: '启用' },
  INACTIVE: { color: 'default', text: '停用' },
  IN_MAINTENANCE: { color: 'orange', text: '维护中' }
}

const WorkCenterList: React.FC = () => {
  const [workCenters, setWorkCenters] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchWorkCenters()
  }, [])

  const fetchWorkCenters = async () => {
    setLoading(true)
    try {
      const response = await api.get('/pp/work-centers')
      setWorkCenters(response.data)
    } catch (error) {
      console.error('获取工作中心列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: '工作中心ID', dataIndex: 'work_center_id', key: 'work_center_id' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '类型', dataIndex: 'work_center_type', key: 'work_center_type' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const info = WORK_CENTER_STATUS[status] || { color: 'default', text: status }
        return <Tag color={info.color}>{info.text}</Tag>
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => navigate(`/pp/work-centers/${record.work_center_id}/edit`)}
        >
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="工作中心管理"
        description="维护产能资源与作业类型，供工单排产使用"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/pp/work-centers/new')}
          >
            新建工作中心
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={workCenters}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default WorkCenterList

