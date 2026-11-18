import { Table, Button, Space, Tag, App as AntdApp, Modal } from 'antd'
import { PlusOutlined, EditOutlined, CheckOutlined, SendOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

// 客户状态中文映射
const customerStatusMap: Record<string, { label: string; color: string }> = {
  'DRAFT': { label: '草稿', color: 'default' },
  'PENDING_SALES_MANAGER': { label: '待销售经理审批', color: 'processing' },
  'PENDING_FINANCE': { label: '待财务审批', color: 'processing' },
  'PENDING_GENERAL_MANAGER': { label: '待总经理审批', color: 'processing' },
  'PENDING_APPROVAL': { label: '待审批', color: 'processing' },
  'FROZEN': { label: '已建档(冻结)', color: 'warning' },
  'ACTIVE': { label: '激活', color: 'success' },
  'BLOCKED': { label: '冻结/停用', color: 'error' },
  'INACTIVE': { label: '未激活', color: 'default' }
}

const CustomerList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null)
  const [actionType, setActionType] = useState<'submit' | 'approve'>('submit')
  const navigate = useNavigate()

  useEffect(() => {
    fetchCustomers()
  }, [])

  const fetchCustomers = async () => {
    setLoading(true)
    try {
      const response = await api.get('/sd/customers')
      setCustomers(response.data)
    } catch (error) {
      console.error('获取客户列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 提交审批
  const handleSubmitForApproval = (customer: any) => {
    setSelectedCustomer(customer)
    setActionType('submit')
    setApprovalModalVisible(true)
  }

  // 审批通过
  const handleApprove = (customer: any) => {
    setSelectedCustomer(customer)
    setActionType('approve')
    setApprovalModalVisible(true)
  }

  // 激活客户（从冻结状态激活）
  const handleActivate = async (customer: any) => {
    try {
      await api.post(`/sd/customers/${customer.customer_id}/activate`)
      message.success('客户已激活')
      fetchCustomers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '激活失败')
    }
  }

  // 确认操作
  const handleConfirmAction = async () => {
    if (!selectedCustomer) return

    try {
      if (actionType === 'submit') {
        await api.post(`/sd/customers/${selectedCustomer.customer_id}/submit`)
        message.success('客户已提交审批')
      } else {
        await api.post(`/sd/customers/${selectedCustomer.customer_id}/approve`)
        message.success('客户审批通过')
      }
      setApprovalModalVisible(false)
      setSelectedCustomer(null)
      fetchCustomers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const columns = [
    { title: '客户代码', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '公司名称', dataIndex: 'legal_name', key: 'legal_name' },
    { title: '商号', dataIndex: 'trade_name', key: 'trade_name' },
    {
      title: '状态',
      dataIndex: 'customer_status',
      key: 'customer_status',
      render: (status: string) => {
        const statusInfo = customerStatusMap[status] || { label: status, color: 'default' }
        return <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => {
        const status = record.customer_status
        return (
          <Space>
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => navigate(`/sd/customers/${record.customer_id}/edit`)}
            >
              编辑
            </Button>
            {/* 提交审批：DRAFT, INACTIVE, PENDING_APPROVAL 状态显示 */}
            {(status === 'DRAFT' || status === 'INACTIVE' || status === 'PENDING_APPROVAL') && (
              <Button
                type="link"
                icon={<SendOutlined />}
                onClick={() => handleSubmitForApproval(record)}
              >
                提交审批
              </Button>
            )}
            {/* 审批通过：待审批状态显示（财务不参与审批） */}
            {/* 销售经理审批 PENDING_SALES_MANAGER */}
            {status === 'PENDING_SALES_MANAGER' && (
              <Button
                type="link"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
                style={{ color: 'hsl(var(--chart-success))' }}
              >
                审批
              </Button>
            )}
            {/* 总经理审批 PENDING_GENERAL_MANAGER */}
            {status === 'PENDING_GENERAL_MANAGER' && (
              <Button
                type="link"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
                style={{ color: 'hsl(var(--chart-success))' }}
              >
                审批
              </Button>
            )}
            {/* 激活：已建档(冻结)状态显示 */}
            {status === 'FROZEN' && (
              <Button
                type="link"
                icon={<CheckOutlined />}
                onClick={() => handleActivate(record)}
                style={{ color: 'hsl(var(--chart-success))' }}
              >
                激活
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
        title="客户管理"
        description="客户建档、多级审批与激活管理"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/sd/customers/new')}
          >
            新建客户
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={customers}
        loading={loading}
        rowKey="id"
      />

      {/* 审批确认对话框 */}
      <Modal
        title={actionType === 'submit' ? '提交审批' : '审批通过'}
        open={approvalModalVisible}
        onOk={handleConfirmAction}
        onCancel={() => {
          setApprovalModalVisible(false)
          setSelectedCustomer(null)
        }}
        okText="确认"
        cancelText="取消"
      >
        {actionType === 'approve' && (
          <p>确认审批通过该客户吗？</p>
        )}
        {actionType === 'submit' && (
          <p>确认提交该客户进行审批吗？</p>
        )}
      </Modal>
    </div>
  )
}

export default CustomerList

