import { Table, Button, Tag, Space, App as AntdApp } from 'antd'
import { PlusOutlined, EditOutlined, SendOutlined, DeleteOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { useConfirm } from '../../components/common/ConfirmProvider'

// 工艺路线状态中文映射
const routingStatusMap: Record<string, { label: string; color: string }> = {
  'DRAFT': { label: '草稿', color: 'default' },
  'RELEASED': { label: '已发布', color: 'success' },
  'OBSOLETE': { label: '已废弃', color: 'error' }
}

const RoutingList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [routings, setRoutings] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const confirm = useConfirm()

  useEffect(() => {
    fetchRoutings()
  }, [])

  const fetchRoutings = async () => {
    setLoading(true)
    try {
      const response = await api.get('/eng/routings')
      setRoutings(response.data)
    } catch (error) {
      console.error('获取工艺路线列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 提交审核（草稿 -> 已发布）
  const handleSubmit = async (routing: any) => {
    confirm({
      title: '确认提交',
      content: `确定要提交工艺路线 "${routing.routing_id}" 进行审核吗？`,
      onOk: async () => {
        try {
          await api.post(`/eng/routings/${routing.routing_id}/submit`)
          message.success('工艺路线已提交审核并发布')
          fetchRoutings()
        } catch (error: any) {
          message.error(error.response?.data?.detail || '提交失败')
        }
      }
    })
  }

  // 废弃工艺路线（已发布 -> 已废弃）
  const handleObsolete = async (routing: any) => {
    confirm({
      title: '确认废弃',
      icon: 'warning',
      content: `确定要废弃工艺路线 "${routing.routing_id}" 吗？`,
      onOk: async () => {
        try {
          await api.post(`/eng/routings/${routing.routing_id}/obsolete`)
          message.success('工艺路线已废弃')
          fetchRoutings()
        } catch (error: any) {
          message.error(error.response?.data?.detail || '废弃失败')
        }
      }
    })
  }

  const columns = [
    { title: '工艺路线ID', dataIndex: 'routing_id', key: 'routing_id' },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '物料编码', dataIndex: 'material_code', key: 'material_code' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusInfo = routingStatusMap[status] || { label: status, color: 'default' }
        return <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => {
        const status = record.status
        return (
          <Space>
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => navigate(`/eng/routings/${record.routing_id}/edit`)}
            >
              编辑
            </Button>
            {/* 提交审核：草稿状态显示 */}
            {status === 'DRAFT' && (
              <Button
                type="link"
                icon={<SendOutlined />}
                onClick={() => handleSubmit(record)}
                style={{ color: 'hsl(var(--brand))' }}
              >
                提交审核
              </Button>
            )}
            {/* 废弃：已发布状态显示 */}
            {status === 'RELEASED' && (
              <Button
                type="link"
                icon={<DeleteOutlined />}
                onClick={() => handleObsolete(record)}
                style={{ color: 'hsl(var(--destructive))' }}
              >
                废弃
              </Button>
            )}
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      <PageHeader
        title="工艺路线管理"
        description="维护工艺路线与工序顺序，支持提交审批与发布"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/eng/routings/new')}
          >
            新建工艺路线
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={routings}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default RoutingList

