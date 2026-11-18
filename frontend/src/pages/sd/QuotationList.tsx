import { Table, Button, Tag, Space, App as AntdApp, Modal, Input } from 'antd'
import { PlusOutlined, EditOutlined, SendOutlined, EyeOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { useAuthStore } from '../../stores/authStore'
import { PageHeader } from '../../components/layout/PageHeader'

const { TextArea } = Input

// 报价单状态中文映射（与表格标签共用，避免弹窗里露出英文枚举）
const QUOTATION_STATUS_TEXT: { [key: string]: string } = {
  DRAFT: '草稿',
  PENDING_SALES: '待销售审核',
  PENDING_FINANCE: '待财务审核',
  PENDING_GENERAL_MANAGER: '待总经理审核',
  APPROVED: '已审核',
  REJECTED: '已拒绝',
  CUSTOMER_CONFIRMED: '客户已确认',
  LINKED: '已转订单',
  CANCELLED: '已取消'
}

const QuotationList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [quotations, setQuotations] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [rejectModalVisible, setRejectModalVisible] = useState(false)
  const [selectedQuotation, setSelectedQuotation] = useState<any>(null)
  const [comment, setComment] = useState('')
  const [approving, setApproving] = useState(false)
  const navigate = useNavigate()
  const { user } = useAuthStore()

  useEffect(() => {
    fetchQuotations()
  }, [])

  const fetchQuotations = async () => {
    setLoading(true)
    try {
      const response = await api.get('/sd/quotations', {
        timeout: 30000 // 单独设置超时时间
      })
      setQuotations(response.data || [])
    } catch (error: any) {
      console.error('获取报价单列表失败:', error)
      if (error.code === 'ECONNABORTED') {
        message.error('请求超时，请检查后端服务是否正常运行')
      } else if (error.response) {
        message.error(error.response?.data?.detail || '获取报价单列表失败')
      } else if (error.request) {
        message.error('无法连接到服务器，请检查后端服务是否运行')
      } else {
        message.error('获取报价单列表失败')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (quotationNumber: string) => {
    try {
      await api.post(`/sd/quotations/${quotationNumber}/submit`)
      message.success('报价单已提交审核')
      fetchQuotations()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '提交失败')
    }
  }

  const handleViewApprovalStatus = async (quotationNumber: string) => {
    try {
      const response = await api.get(`/sd/quotations/${quotationNumber}/approval-status`)
      const status = response.data
      
      Modal.info({
        title: '审核状态',
        width: 600,
        content: (
          <div>
            <p><strong>报价单号：</strong>{status.quotation_number}</p>
            <p><strong>当前状态：</strong>{QUOTATION_STATUS_TEXT[status.status] || status.status}</p>
            {status.workflow_enabled && status.approval_history && status.approval_history.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <p><strong>审核历史：</strong></p>
                {status.approval_history.map((item: any, index: number) => (
                  <div key={index} style={{ marginTop: 8, padding: 8, background: 'hsl(var(--surface-hover))', borderRadius: 4 }}>
                    <p><strong>{item.node_name}：</strong>
                      {item.status === 'APPROVED' ? <Tag color="green">已通过</Tag> : 
                       item.status === 'REJECTED' ? <Tag color="red">已拒绝</Tag> : 
                       <Tag color="orange">待审核</Tag>}
                    </p>
                    {item.approver && <p>审核人：{item.approver}</p>}
                    {item.approved_at && <p>审核时间：{new Date(item.approved_at).toLocaleString()}</p>}
                    {item.comment && <p>意见：{item.comment}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取审核状态失败')
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
      fetchQuotations()
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
      fetchQuotations()
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
      'LINKED': { color: 'geekblue', text: '已转订单' },
      'CANCELLED': { color: 'default', text: '已取消' }
    }
    const statusInfo = statusMap[status] || { color: 'default', text: QUOTATION_STATUS_TEXT[status] || status }
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
  }

  const columns = [
    { title: '报价单号', dataIndex: 'quotation_number', key: 'quotation_number' },
    { title: '客户代码', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '产品编号', dataIndex: 'product_number', key: 'product_number' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '单价', dataIndex: 'unit_price', key: 'unit_price' },
    { title: '总金额', dataIndex: 'total_amount', key: 'total_amount' },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => {
        const canApprove = ['PENDING_SALES', 'PENDING_FINANCE', 'PENDING_GENERAL_MANAGER'].includes(record.status) &&
          user && (
            (record.status === 'PENDING_SALES' && user.role === 'SALES_MANAGER') ||
            (record.status === 'PENDING_FINANCE' && user.role === 'FINANCE') ||
            (record.status === 'PENDING_GENERAL_MANAGER' && user.role === 'GENERAL_MANAGER')
          )

        return (
          <Space>
            {/* 允许编辑 DRAFT 和 REJECTED 状态的报价单 */}
            {(record.status === 'DRAFT' || record.status === 'REJECTED') && (
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => navigate(`/sd/quotations/${record.quotation_number}/edit`)}
              >
                编辑
              </Button>
            )}
            {/* 允许 DRAFT 状态的报价单提交审核 */}
            {record.status === 'DRAFT' && (
              <Button
                type="link"
                icon={<SendOutlined />}
                onClick={() => handleSubmit(record.quotation_number)}
              >
                提交审核
              </Button>
            )}
            {/* 只有业务员（SALES）才能重新提交被拒绝的报价单 */}
            {record.status === 'REJECTED' && user && user.role === 'SALES' && (
              <Button
                type="link"
                icon={<SendOutlined />}
                onClick={() => handleSubmit(record.quotation_number)}
              >
                重新提交
              </Button>
            )}
            {canApprove && (
              <>
                <Button
                  type="link"
                  icon={<CheckOutlined />}
                  style={{ color: 'hsl(var(--chart-success))' }}
                  onClick={() => openApprovalModal(record)}
                >
                  通过
                </Button>
                <Button
                  type="link"
                  danger
                  icon={<CloseOutlined />}
                  onClick={() => openRejectModal(record)}
                >
                  拒绝
                </Button>
              </>
            )}
            {(record.status === 'PENDING_SALES' || 
              record.status === 'PENDING_FINANCE' || 
              record.status === 'PENDING_GENERAL_MANAGER' ||
              record.status === 'APPROVED' ||
              record.status === 'REJECTED') && (
              <Button
                type="link"
                icon={<EyeOutlined />}
                onClick={() => handleViewApprovalStatus(record.quotation_number)}
              >
                审核状态
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
        title="报价单管理"
        description="报价单三级审核流程：销售经理 → 财务 → 总经理"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/sd/quotations/new')}
          >
            新建报价单
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={quotations}
        loading={loading}
        rowKey="id"
      />

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
        okText="确认通过"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p><strong>报价单号：</strong>{selectedQuotation?.quotation_number}</p>
          <p><strong>客户代码：</strong>{selectedQuotation?.customer_id}</p>
          <p><strong>产品编号：</strong>{selectedQuotation?.product_number}</p>
          <p><strong>总金额：</strong>¥{selectedQuotation?.total_amount?.toFixed(2)}</p>
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
        okText="确认拒绝"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p><strong>报价单号：</strong>{selectedQuotation?.quotation_number}</p>
          <p><strong>客户代码：</strong>{selectedQuotation?.customer_id}</p>
          <p><strong>产品编号：</strong>{selectedQuotation?.product_number}</p>
          <p><strong>总金额：</strong>¥{selectedQuotation?.total_amount?.toFixed(2)}</p>
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

export default QuotationList

