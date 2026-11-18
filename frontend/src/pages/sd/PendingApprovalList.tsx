import { Table, Button, Card, Modal, Input, App as AntdApp, Tag, Space } from 'antd'
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'

const { TextArea } = Input

const PendingApprovalList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [pendingApprovals, setPendingApprovals] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [rejectModalVisible, setRejectModalVisible] = useState(false)
  const [selectedQuotation, setSelectedQuotation] = useState<any>(null)
  const [comment, setComment] = useState('')
  const [approving, setApproving] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchPendingApprovals()
  }, [])

  const fetchPendingApprovals = async () => {
    setLoading(true)
    try {
      const response = await api.get('/sd/quotations/pending-approval')
      setPendingApprovals(response.data || [])
    } catch (error: any) {
      console.error('获取待审核列表失败:', error)
      message.error('获取待审核列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!selectedQuotation) return

    setApproving(true)
    try {
      await api.post(`/sd/quotations/${selectedQuotation.quotation_number}/approve`, {
        comment: comment || undefined
      })
      message.success('审核通过')
      setApprovalModalVisible(false)
      setComment('')
      setSelectedQuotation(null)
      fetchPendingApprovals()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '审核失败')
    } finally {
      setApproving(false)
    }
  }

  const handleReject = async () => {
    if (!selectedQuotation || !comment.trim()) {
      message.warning('请填写拒绝原因')
      return
    }

    setApproving(true)
    try {
      await api.post(`/sd/quotations/${selectedQuotation.quotation_number}/reject`, {
        comment: comment
      })
      message.success('已拒绝')
      setRejectModalVisible(false)
      setComment('')
      setSelectedQuotation(null)
      fetchPendingApprovals()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setApproving(false)
    }
  }

  const openApprovalModal = (quotation: any) => {
    setSelectedQuotation(quotation)
    setComment('')
    setApprovalModalVisible(true)
  }

  const openRejectModal = (quotation: any) => {
    setSelectedQuotation(quotation)
    setComment('')
    setRejectModalVisible(true)
  }

  const getStatusTag = (status: string) => {
    const statusMap: { [key: string]: { color: string; text: string } } = {
      'DRAFT': { color: 'default', text: '草稿' },
      'PENDING_SALES': { color: 'orange', text: '待销售审核' },
      'PENDING_FINANCE': { color: 'blue', text: '待财务审核' },
      'PENDING_GENERAL_MANAGER': { color: 'purple', text: '待总经理审核' },
      'APPROVED': { color: 'green', text: '已审核' },
      'REJECTED': { color: 'red', text: '已拒绝' },
      'CUSTOMER_CONFIRMED': { color: 'cyan', text: '客户已确认' },
      'CANCELLED': { color: 'default', text: '已取消' }
    }
    const statusInfo = statusMap[status] || { color: 'default', text: status }
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
  }

  const columns = [
    { title: '报价单号', dataIndex: 'quotation_number', key: 'quotation_number' },
    { title: '客户代码', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '产品编号', dataIndex: 'product_number', key: 'product_number' },
    { 
      title: '总金额', 
      dataIndex: 'total_amount', 
      key: 'total_amount',
      render: (amount: number) => amount ? `¥${amount.toFixed(2)}` : '-'
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => getStatusTag(status)
    },
    { title: '当前节点', dataIndex: 'current_node', key: 'current_node' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/sd/quotations/${record.quotation_number}/edit`)}
          >
            查看
          </Button>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={() => openApprovalModal(record)}
          >
            通过
          </Button>
          <Button
            danger
            icon={<CloseOutlined />}
            onClick={() => openRejectModal(record)}
          >
            拒绝
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card title="待审核报价单">
        <Table
          columns={columns}
          dataSource={pendingApprovals}
          loading={loading}
          rowKey="quotation_number"
        />
      </Card>

      {/* 审核通过对话框 */}
      <Modal
        title="审核通过"
        open={approvalModalVisible}
        onOk={handleApprove}
        onCancel={() => {
          setApprovalModalVisible(false)
          setComment('')
          setSelectedQuotation(null)
        }}
        confirmLoading={approving}
      >
        <div style={{ marginBottom: 16 }}>
          <p><strong>报价单号：</strong>{selectedQuotation?.quotation_number}</p>
          <p><strong>客户代码：</strong>{selectedQuotation?.customer_id}</p>
          <p><strong>产品编号：</strong>{selectedQuotation?.product_number}</p>
        </div>
        <div>
          <p>审核意见（可选）：</p>
          <TextArea
            rows={4}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="请输入审核意见"
          />
        </div>
      </Modal>

      {/* 拒绝对话框 */}
      <Modal
        title="拒绝审核"
        open={rejectModalVisible}
        onOk={handleReject}
        onCancel={() => {
          setRejectModalVisible(false)
          setComment('')
          setSelectedQuotation(null)
        }}
        confirmLoading={approving}
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 16 }}>
          <p><strong>报价单号：</strong>{selectedQuotation?.quotation_number}</p>
          <p><strong>客户代码：</strong>{selectedQuotation?.customer_id}</p>
          <p><strong>产品编号：</strong>{selectedQuotation?.product_number}</p>
        </div>
        <div>
          <p style={{ color: 'hsl(var(--destructive))' }}>拒绝原因（必填）：</p>
          <TextArea
            rows={4}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="请填写拒绝原因"
            required
          />
        </div>
      </Modal>
    </div>
  )
}

export default PendingApprovalList

