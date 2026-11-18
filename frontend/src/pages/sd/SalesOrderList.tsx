import { Table, Button, Tag, Space, App as AntdApp, Modal, Input, Steps, Timeline, Descriptions } from 'antd'
import { PlusOutlined, TruckOutlined, CheckCircleOutlined, SendOutlined, CheckOutlined, CloseOutlined, FileTextOutlined, LockOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { useAuthStore } from '../../stores/authStore'
import { PageHeader } from '../../components/layout/PageHeader'
import { useConfirm } from '../../components/common/ConfirmProvider'

const { TextArea } = Input

const SalesOrderList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [rejectModalVisible, setRejectModalVisible] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<any>(null)
  const [comment, setComment] = useState('')
  const [approving, setApproving] = useState(false)
  const [reviewStatus, setReviewStatus] = useState<any>(null)
  const [loadingReviewStatus, setLoadingReviewStatus] = useState(false)
  const [reviewModalVisible, setReviewModalVisible] = useState(false)
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const confirm = useConfirm()

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    setLoading(true)
    try {
      const response = await api.get('/sd/sales-orders')
      setOrders(response.data)
    } catch (error) {
      console.error('获取销售订单列表失败:', error)
      message.error('获取销售订单列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleShip = async (orderNumber: string) => {
    try {
      await api.post(`/sd/sales-orders/${orderNumber}/ship`)
      message.success('订单已发货')
      fetchOrders()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发货失败')
    }
  }

  const handleDeliver = async (orderNumber: string) => {
    try {
      await api.post(`/sd/sales-orders/${orderNumber}/deliver`)
      message.success('订单已签收')
      fetchOrders()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '签收失败')
    }
  }

  const handleReconcile = async (orderNumber: string) => {
    try {
      await api.post(`/sd/sales-orders/${orderNumber}/reconcile`)
      message.success('订单已对账')
      fetchOrders()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '对账失败')
    }
  }

  const handleClose = async (orderNumber: string) => {
    confirm({
      title: '确认关闭',
      icon: 'warning',
      content: '关闭后将同时关闭所有关联的生产订单，此操作不可撤销。确定要关闭吗？',
      onOk: async () => {
        try {
          await api.post(`/sd/sales-orders/${orderNumber}/close`)
          message.success('订单已关闭')
          fetchOrders()
        } catch (error: any) {
          message.error(error.response?.data?.detail || '关闭失败')
        }
      }
    })
  }

  const handleSubmit = async (orderNumber: string) => {
    try {
      const response = await api.post(`/sd/sales-orders/${orderNumber}/submit`)
      console.log('提交审核响应:', response.data)
      message.success(response.data?.message || '订单已提交审核')
      
      // 刷新订单列表
      await fetchOrders()
      
      // 更新选中订单的状态（如果存在）
      if (selectedOrder && selectedOrder.order_number === orderNumber) {
        setSelectedOrder({
          ...selectedOrder,
          status: 'PENDING_REVIEW'
        })
      }
      
      // 如果评审状态对话框是打开的，刷新评审状态
      if (reviewModalVisible && selectedOrder?.order_number === orderNumber) {
        // 等待一小段时间确保数据库已更新
        setTimeout(async () => {
          await fetchReviewStatus(orderNumber, false)
        }, 500)
      }
    } catch (error: any) {
      console.error('提交审核失败:', error)
      message.error(error.response?.data?.detail || '提交失败')
    }
  }

  const handleApprove = async () => {
    if (!selectedOrder) return

    setApproving(true)
    try {
      // 后端使用 Pydantic 模型接收 body：必须保证请求体是一个 JSON 对象（至少 {}）
      const payload = comment?.trim() ? { comment: comment.trim() } : {}
      await api.post(`/sd/sales-orders/${selectedOrder.order_number}/approve`, payload)
      message.success('审批通过')
      setApprovalModalVisible(false)
      setComment('')
      setSelectedOrder(null)
      fetchOrders()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '审批失败')
    } finally {
      setApproving(false)
    }
  }

  const handleReject = async () => {
    if (!selectedOrder || !comment.trim()) {
      message.warning('请填写拒绝原因')
      return
    }

    setApproving(true)
    try {
      await api.post(`/sd/sales-orders/${selectedOrder.order_number}/reject`, {
        comment: comment
      })
      message.success('已拒绝')
      setRejectModalVisible(false)
      setComment('')
      setSelectedOrder(null)
      fetchOrders()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setApproving(false)
    }
  }

  const openApprovalModal = (order: any) => {
    setSelectedOrder(order)
    setComment('')
    setApprovalModalVisible(true)
  }

  const openRejectModal = (order: any) => {
    setSelectedOrder(order)
    setComment('')
    setRejectModalVisible(true)
  }

  const fetchReviewStatus = async (orderNumber: string, showModal: boolean = true) => {
    setLoadingReviewStatus(true)
    try {
      const response = await api.get(`/sd/sales-orders/${orderNumber}/review-status`)
      const data = response.data
      
      // 添加调试日志
      console.log('评审状态数据:', {
        has_workflow: data.has_workflow,
        can_approve: data.can_approve,
        current_user_role: data.current_user_role,
        current_node: data.workflow_status?.current_node,
        debug_info: data.debug_info
      })
      
      setReviewStatus(data)
      if (showModal) {
        setReviewModalVisible(true)
      }
      return data
    } catch (error: any) {
      console.error('获取评审状态失败:', error)
      message.error('获取评审状态失败')
      return null
    } finally {
      setLoadingReviewStatus(false)
    }
  }

  // 检查当前用户是否可以审批当前节点
  const canApproveCurrentNode = (_order: any) => {
    if (!user || !reviewStatus?.has_workflow) return false
    
    // 如果后端已经返回了 can_approve 标志，直接使用（更可靠）
    if (reviewStatus.can_approve !== undefined) {
      return reviewStatus.can_approve
    }
    
    // 否则使用前端逻辑判断（作为后备）
    const currentRole = user.role
    const workflowStatus = reviewStatus.workflow_status
    
    if (!workflowStatus?.current_node) return false
    
    // 根据当前节点判断需要的角色
    // 注意：销售部门评审允许 SALES 和 SALES_MANAGER 角色
    const nodeRoleMap: { [key: string]: string[] } = {
      'SALES_REVIEW': ['SALES', 'SALES_MANAGER', 'ADMIN'],  // 允许 SALES 和 SALES_MANAGER
      'ENGINEERING_REVIEW': ['ENGINEER', 'ADMIN'],
      'MATERIAL_REVIEW': ['WAREHOUSE', 'ADMIN'],
      'FINANCE_REVIEW': ['FINANCE', 'ADMIN']
    }
    
    const requiredRoles = nodeRoleMap[workflowStatus.current_node] || []
    return requiredRoles.includes(currentRole)
  }

  const getStatusTag = (status: string) => {
    const statusMap: { [key: string]: { color: string; text: string } } = {
      'DRAFT': { color: 'default', text: '草稿' },
      'PENDING_REVIEW': { color: 'orange', text: '待订单评审' },
      'REVIEWING': { color: 'blue', text: '评审中' },
      'APPROVED': { color: 'green', text: '已批准' },
      'REJECTED': { color: 'red', text: '已拒绝' },
      'IN_PRODUCTION': { color: 'cyan', text: '生产中' },
      'COMPLETED': { color: 'blue', text: '已完成' },
      'SHIPPED': { color: 'purple', text: '已发货' },
      'DELIVERED': { color: 'green', text: '已签收' },
      'RECONCILED': { color: 'geekblue', text: '已对账' },
      'CLOSED': { color: 'default', text: '已关闭' },
      'CANCELLED': { color: 'default', text: '已取消' }
    }
    const statusInfo = statusMap[status] || { color: 'default', text: status }
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
  }

  const columns = [
    { title: '订单号', dataIndex: 'order_number', key: 'order_number' },
    { title: '客户代码', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '产品编号', dataIndex: 'product_number', key: 'product_number' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
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
        // 检查是否可以审批（需要先获取评审状态）
        const canReview = (record.status === 'PENDING_REVIEW' || record.status === 'REVIEWING')
        const canEdit = record.status === 'DRAFT'

        return (
          <Space>
            {canEdit && (
              <Button 
                type="link" 
                onClick={() => navigate(`/sd/sales-orders/${record.order_number}/edit`)}
              >
                编辑
              </Button>
            )}
            {record.status === 'DRAFT' && (
              <Button
                type="link"
                icon={<SendOutlined />}
                onClick={() => handleSubmit(record.order_number)}
              >
                提交审核
              </Button>
            )}
            {canReview && (
              <>
                <Button
                  type="link"
                  icon={<FileTextOutlined />}
                  onClick={() => {
                    setSelectedOrder(record)
                    fetchReviewStatus(record.order_number)
                  }}
                >
                  评审状态
                </Button>
                <Button
                  type="link"
                  icon={<CheckOutlined />}
                  style={{ color: 'hsl(var(--chart-success))' }}
                  onClick={async () => {
                    try {
                      // 先设置选中订单，确保 reviewStatus 能正确获取
                      setSelectedOrder(record)
                      
                      const statusData = await fetchReviewStatus(record.order_number, false)
                      console.log('审批按钮点击 - 状态数据:', statusData)
                      console.log('审批按钮点击 - can_approve:', statusData?.can_approve)
                      console.log('审批按钮点击 - debug_info:', statusData?.debug_info)
                      
                      // 优先使用后端返回的 can_approve 标志
                      const canApprove = statusData?.can_approve === true
                      console.log('审批按钮点击 - 最终canApprove:', canApprove)
                      
                      if (statusData && canApprove) {
                        openApprovalModal(record)
                      } else {
                        // 如果无法审批，显示评审状态对话框
                        setReviewModalVisible(true)
                        const reason = statusData?.debug_info 
                          ? `当前用户角色: ${statusData.debug_info.current_user_role}, 节点要求角色: ${statusData.debug_info.node_approver_role}, can_approve: ${statusData.debug_info.can_approve}`
                          : statusData?.can_approve === false
                          ? '后端返回 can_approve: false'
                          : '请查看评审状态了解详情'
                        message.warning(`您当前没有权限审批此节点。${reason}`)
                      }
                    } catch (error) {
                      console.error('审批按钮错误:', error)
                      message.error('获取评审状态失败')
                    }
                  }}
                >
                  通过
                </Button>
                <Button
                  type="link"
                  danger
                  icon={<CloseOutlined />}
                  onClick={async () => {
                    try {
                      const statusData = await fetchReviewStatus(record.order_number, false)
                      console.log('拒绝按钮点击 - 状态数据:', statusData)
                      console.log('拒绝按钮点击 - canApproveCurrentNode结果:', canApproveCurrentNode(record))
                      
                      if (statusData && canApproveCurrentNode(record)) {
                        openRejectModal(record)
                      } else {
                        // 如果无法审批，显示评审状态对话框
                        setReviewModalVisible(true)
                        const reason = statusData?.debug_info 
                          ? `当前用户角色: ${statusData.debug_info.current_user_role}, 节点要求角色: ${statusData.debug_info.node_approver_role}`
                          : '请查看评审状态了解详情'
                        message.warning(`您当前没有权限审批此节点。${reason}`)
                      }
                    } catch (error) {
                      console.error('拒绝按钮错误:', error)
                      message.error('获取评审状态失败')
                    }
                  }}
                >
                  拒绝
                </Button>
              </>
            )}
            {(record.status === 'COMPLETED' || record.status === 'IN_PRODUCTION') && (
              <Button
                type="link"
                icon={<TruckOutlined />}
                style={{ color: 'hsl(var(--brand))' }}
                onClick={() => handleShip(record.order_number)}
              >
                发货
              </Button>
            )}
            {record.status === 'SHIPPED' && (
              <Button
                type="link"
                icon={<CheckCircleOutlined />}
                style={{ color: 'hsl(var(--chart-success))' }}
                onClick={() => handleDeliver(record.order_number)}
              >
                签收
              </Button>
            )}
            {record.status === 'DELIVERED' && (
              <Button
                type="link"
                icon={<FileTextOutlined />}
                style={{ color: 'hsl(var(--brand))' }}
                onClick={() => handleReconcile(record.order_number)}
              >
                对账
              </Button>
            )}
            {record.status === 'RECONCILED' && (
              <Button
                type="link"
                icon={<LockOutlined />}
                style={{ color: 'hsl(var(--brand))' }}
                onClick={() => handleClose(record.order_number)}
              >
                关闭
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
        title="销售订单管理"
        description="销售订单评审、发货与对账全流程跟踪"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/sd/sales-orders/new')}
          >
            新建订单
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={orders}
        loading={loading}
        rowKey="order_number"
      />

      {/* 审批通过对话框 */}
      <Modal
        title="审批通过"
        open={approvalModalVisible}
        onOk={handleApprove}
        onCancel={() => {
          setApprovalModalVisible(false)
          setComment('')
          setSelectedOrder(null)
        }}
        confirmLoading={approving}
        okText="确认通过"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p><strong>订单号：</strong>{selectedOrder?.order_number}</p>
          <p><strong>客户代码：</strong>{selectedOrder?.customer_id}</p>
          <p><strong>产品编号：</strong>{selectedOrder?.product_number}</p>
          <p><strong>总金额：</strong>¥{selectedOrder?.total_amount?.toFixed(2)}</p>
        </div>
        <div>
          <p>审批意见（可选）：</p>
          <TextArea
            rows={4}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="请输入审批意见"
          />
        </div>
      </Modal>

      {/* 拒绝对话框 */}
      <Modal
        title="拒绝审批"
        open={rejectModalVisible}
        onOk={handleReject}
        onCancel={() => {
          setRejectModalVisible(false)
          setComment('')
          setSelectedOrder(null)
        }}
        confirmLoading={approving}
        okButtonProps={{ danger: true }}
        okText="确认拒绝"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p><strong>订单号：</strong>{selectedOrder?.order_number}</p>
          <p><strong>客户代码：</strong>{selectedOrder?.customer_id}</p>
          <p><strong>产品编号：</strong>{selectedOrder?.product_number}</p>
          <p><strong>总金额：</strong>¥{selectedOrder?.total_amount?.toFixed(2)}</p>
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

      {/* 评审状态对话框 */}
      <Modal
        title="订单评审状态"
        open={reviewModalVisible}
        onCancel={() => {
          setReviewModalVisible(false)
          setReviewStatus(null)
        }}
        footer={[
          <Button key="close" onClick={() => {
            setReviewModalVisible(false)
            setReviewStatus(null)
          }}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {loadingReviewStatus ? (
          <div style={{ textAlign: 'center', padding: '20px' }}>加载中...</div>
        ) : !reviewStatus ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'hsl(var(--ink-faint))' }}>
            未获取到评审状态信息
          </div>
        ) : !reviewStatus.has_workflow ? (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <p style={{ color: 'hsl(var(--destructive))', marginBottom: 10, fontSize: 16, fontWeight: 'bold' }}>
              {reviewStatus.message || '未找到评审工作流实例'}
            </p>
            {reviewStatus.order_status && (
              <p style={{ color: 'hsl(var(--ink-soft))', marginBottom: 10 }}>
                当前订单状态: <Tag color={reviewStatus.order_status === 'DRAFT' ? 'default' : 'blue'}>
                  {reviewStatus.order_status === 'DRAFT' ? '草稿' : 
                   reviewStatus.order_status === 'PENDING_REVIEW' ? '待订单评审' :
                   reviewStatus.order_status === 'REVIEWING' ? '评审中' :
                   reviewStatus.order_status === 'APPROVED' ? '已批准' :
                   reviewStatus.order_status}
                </Tag>
              </p>
            )}
            {selectedOrder && selectedOrder.status === 'DRAFT' && (
              <div style={{ marginTop: 20 }}>
                <p style={{ color: 'hsl(var(--ink-faint))', marginBottom: 15 }}>
                  该订单尚未提交审核，请先提交审核以启动评审流程
                </p>
                <Button 
                  type="primary" 
                  size="large"
                  icon={<SendOutlined />}
                  onClick={async () => {
                    try {
                      await handleSubmit(selectedOrder.order_number)
                      // 提交成功后，刷新评审状态
                      setTimeout(async () => {
                        await fetchReviewStatus(selectedOrder.order_number, false)
                      }, 500)
                    } catch (error) {
                      console.error('提交审核失败:', error)
                    }
                  }}
                >
                  提交审核
                </Button>
              </div>
            )}
            {selectedOrder && selectedOrder.status !== 'DRAFT' && (
              <p style={{ color: 'hsl(var(--ink-faint))', marginTop: 15 }}>
                提示：只有草稿状态的订单可以提交审核。当前订单状态为 {selectedOrder.status}，无法提交审核。
              </p>
            )}
          </div>
        ) : (
          <div>
            <Descriptions column={2} bordered style={{ marginBottom: 20 }}>
              <Descriptions.Item label="工作流状态">
                <Tag color={reviewStatus.workflow_status?.status === 'COMPLETED' ? 'green' : 
                           reviewStatus.workflow_status?.status === 'REJECTED' ? 'red' : 'blue'}>
                  {reviewStatus.workflow_status?.status === 'COMPLETED' ? '已完成' :
                   reviewStatus.workflow_status?.status === 'REJECTED' ? '已拒绝' : '进行中'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="当前节点">
                {reviewStatus.workflow_status?.current_node ? 
                  reviewStatus.workflow_status.nodes?.find((n: any) => n.node_id === reviewStatus.workflow_status.current_node)?.node_name || 
                  reviewStatus.workflow_status.current_node : '未知'}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 20 }}>
              <h4>评审进度</h4>
              <Steps
                direction="vertical"
                current={reviewStatus.workflow_status?.nodes?.filter((n: any) => n.status === 'APPROVED').length || 0}
                status={reviewStatus.workflow_status?.status === 'REJECTED' ? 'error' : 'process'}
              >
                {reviewStatus.workflow_status?.nodes && reviewStatus.workflow_status.nodes.length > 0 ? (
                  // 按 node_id 去重，只显示唯一的节点
                  Array.from(
                    new Map(
                      reviewStatus.workflow_status.nodes.map((node: any) => [node.node_id, node])
                    ).values()
                  ).map((node: any) => (
                  <Steps.Step
                    key={node.node_id}
                    title={node.node_name}
                    description={
                      <div>
                        {node.status === 'APPROVED' && (
                          <div>
                            <Tag color="green">已通过</Tag>
                            {node.approver && <span>审批人: {node.approver}</span>}
                            {node.approved_at && <span style={{ marginLeft: 10 }}>时间: {new Date(node.approved_at).toLocaleString()}</span>}
                            {node.comment && <div style={{ marginTop: 5, color: 'hsl(var(--ink-soft))' }}>意见: {node.comment}</div>}
                          </div>
                        )}
                        {node.status === 'REJECTED' && (
                          <div>
                            <Tag color="red">已拒绝</Tag>
                            {node.approver && <span>审批人: {node.approver}</span>}
                            {node.approved_at && <span style={{ marginLeft: 10 }}>时间: {new Date(node.approved_at).toLocaleString()}</span>}
                            {node.comment && <div style={{ marginTop: 5, color: 'hsl(var(--ink-soft))' }}>原因: {node.comment}</div>}
                          </div>
                        )}
                        {node.status === 'PENDING' && (
                          <div>
                            <Tag color="orange">待审批</Tag>
                            {reviewStatus.workflow_status?.current_node === node.node_id && 
                             canApproveCurrentNode(selectedOrder) && (
                              <span style={{ marginLeft: 10, color: 'hsl(var(--brand))' }}>（您可审批）</span>
                            )}
                          </div>
                        )}
                      </div>
                    }
                  />
                  ))
                ) : (
                  <div style={{ padding: '20px', textAlign: 'center', color: 'hsl(var(--ink-faint))' }}>
                    暂无评审节点信息
                  </div>
                )}
              </Steps>
            </div>

            {reviewStatus.review_history && reviewStatus.review_history.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <h4>评审历史</h4>
                <Timeline>
                  {reviewStatus.review_history.map((review: any, index: number) => (
                    <Timeline.Item
                      key={index}
                      color={review.review_result === 'APPROVED' ? 'green' : 'red'}
                    >
                      <div>
                        <strong>{review.reviewer}</strong> ({review.reviewer_role}) - 
                        <Tag color={review.review_result === 'APPROVED' ? 'green' : 'red'} style={{ marginLeft: 8 }}>
                          {review.review_result === 'APPROVED' ? '通过' : '拒绝'}
                        </Tag>
                        {review.reviewed_at && (
                          <span style={{ marginLeft: 8, color: 'hsl(var(--ink-faint))' }}>
                            {new Date(review.reviewed_at).toLocaleString()}
                          </span>
                        )}
                        {review.review_comment && (
                          <div style={{ marginTop: 5, color: 'hsl(var(--ink-soft))' }}>{review.review_comment}</div>
                        )}
                      </div>
                    </Timeline.Item>
                  ))}
                </Timeline>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default SalesOrderList

