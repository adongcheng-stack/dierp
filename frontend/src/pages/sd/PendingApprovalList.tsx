import { Table, Button, Card, Modal, Input, App as AntdApp, Tag, Space, Tabs, Badge, Empty } from 'antd'
import { CheckOutlined, CloseOutlined, EyeOutlined, ArrowRightOutlined, ReloadOutlined } from '@ant-design/icons'
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'

const { TextArea } = Input

/* ───────────────────────── Tab 1：报价审批（原有逻辑原样保留） ───────────────────────── */

const QuotationApprovalTab: React.FC<{ onChanged: () => void }> = ({ onChanged }) => {
  const { message } = AntdApp.useApp()
  const [pendingApprovals, setPendingApprovals] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [rejectModalVisible, setRejectModalVisible] = useState(false)
  const [selectedQuotation, setSelectedQuotation] = useState<any>(null)
  const [comment, setComment] = useState('')
  const [approving, setApproving] = useState(false)
  const navigate = useNavigate()

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

  useEffect(() => {
    fetchPendingApprovals()
  }, [])

  const refresh = () => {
    fetchPendingApprovals()
    onChanged()
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
      refresh()
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
      refresh()
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
    <>
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
    </>
  )
}

/* ───────────────────────── 跨域待办：通用轻量 tab ───────────────────────── */

interface CrossDomainTabProps {
  title: string
  description: string
  targetPath: string
  fetcher: () => Promise<any[]>
  columns: any[]
  rowKey: string
  onChanged: () => void
}

/** 只读列表 + 「去处理」跳转：各域页面已有完整操作，这里负责汇聚与导航。 */
const CrossDomainTab: React.FC<CrossDomainTabProps> = ({
  title, description, targetPath, fetcher, columns, rowKey, onChanged,
}) => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      setRows(await fetcher())
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [fetcher])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return (
    <Card
      title={title}
      extra={
        <Button icon={<ReloadOutlined />} onClick={() => { fetchData(); onChanged() }} loading={loading}>
          刷新
        </Button>
      }
    >
      <div className="mb-3 text-xs text-ink-faint">{description}</div>
      <Table
        columns={[
          ...columns,
          {
            title: '操作',
            key: 'go',
            width: 110,
            render: () => (
              <Button type="link" size="small" icon={<ArrowRightOutlined />} onClick={() => navigate(targetPath)}>
                去处理
              </Button>
            ),
          },
        ]}
        dataSource={rows}
        loading={loading}
        rowKey={rowKey}
        pagination={rows.length > 10 ? { pageSize: 10 } : false}
        locale={{ emptyText: <Empty description="暂无待办" /> }}
      />
    </Card>
  )
}

/* ───────────────────────── 主页面：Tabs 汇聚 ───────────────────────── */

const PendingApprovalList: React.FC = () => {
  const [summaryTick, setSummaryTick] = useState(0)
  const [counts, setCounts] = useState<{ returns: number; ncrs: number; prs: number }>({
    returns: 0, ncrs: 0, prs: 0,
  })

  // 角标数量：并发拉取三类跨域待办（轻量分页 limit=1 只取 total 不够——直接拉列表计数，演示规模小）
  useEffect(() => {
    let alive = true
    const safe = async (url: string, pick: (d: any) => any[]) => {
      try {
        const r = await api.get(url)
        return pick(r.data).length
      } catch {
        return 0
      }
    }
    Promise.all([
      safe('/purchase/purchase-returns?status=DRAFT&limit=200', (d) => d.items ?? d ?? []),
      safe('/qms/ncrs?limit=200', (d) => (d.items ?? d ?? []).filter((x: any) => ['OPEN', 'UNDER_REVIEW'].includes(x.status))),
      safe('/purchase/purchase-requests?status=DRAFT&limit=200', (d) => d.items ?? d ?? []),
    ]).then(([returns, ncrs, prs]) => {
      if (alive) setCounts({ returns, ncrs, prs })
    })
    return () => { alive = false }
  }, [summaryTick])

  const onChanged = () => setSummaryTick((t) => t + 1)

  const fetchReturns = useCallback(async () => {
    const r = await api.get('/purchase/purchase-returns', { params: { status: 'DRAFT', limit: 200 } })
    return r.data.items ?? []
  }, [])

  const fetchNcrs = useCallback(async () => {
    const r = await api.get('/qms/ncrs', { params: { limit: 200 } })
    return (r.data.items ?? r.data ?? []).filter((x: any) =>
      ['OPEN', 'UNDER_REVIEW'].includes(x.status)
    )
  }, [])

  const fetchPrs = useCallback(async () => {
    const r = await api.get('/purchase/purchase-requests', { params: { status: 'DRAFT', limit: 200 } })
    return r.data.items ?? []
  }, [])

  const tabItems = [
    {
      key: 'quotation',
      label: '报价审批',
      children: <QuotationApprovalTab onChanged={onChanged} />,
    },
    {
      key: 'returns',
      label: <Badge count={counts.returns} size="small" offset={[8, 0]}>退货 / 索赔待审批</Badge>,
      children: (
        <CrossDomainTab
          title="待审批的退货 / 索赔单"
          description="RETURN 退货审批后扣减库存并冲减应付；CLAIM 索赔只确认金额。审批动作在「采购与库存 → 退货 / 索赔」页执行"
          targetPath="/mm/purchase-returns"
          fetcher={fetchReturns}
          rowKey="return_number"
          onChanged={onChanged}
          columns={[
            { title: '单号', dataIndex: 'return_number', key: 'n', width: 170 },
            { title: '采购单', dataIndex: 'purchase_order_number', key: 'po', width: 165 },
            { title: '供应商', dataIndex: 'supplier_name', key: 'sup', render: (v: string | null) => v || '-' },
            {
              title: '类型', dataIndex: 'return_type', key: 't', width: 90,
              render: (v: string) => (v === 'RETURN' ? <Tag color="orange">退货</Tag> : <Tag color="purple">索赔</Tag>),
            },
            {
              title: '金额', dataIndex: 'total_amount', key: 'amt', width: 110, align: 'right' as const,
              render: (v: number) => `¥${Number(v ?? 0).toLocaleString()}`,
            },
            { title: '原因', dataIndex: 'reason', key: 'r', ellipsis: true },
          ]}
        />
      ),
    },
    {
      key: 'ncrs',
      label: <Badge count={counts.ncrs} size="small" offset={[8, 0]}>不合格品待处理</Badge>,
      children: (
        <CrossDomainTab
          title="待处理的不合格品记录（NCR）"
          description="OPEN / 评审中的 NCR：评审、处置（返工/报废/让步接收/退货）在「质量管理 → 不合格品记录」页执行"
          targetPath="/qms/ncrs"
          fetcher={fetchNcrs}
          rowKey="ncr_number"
          onChanged={onChanged}
          columns={[
            { title: 'NCR 号', dataIndex: 'ncr_number', key: 'n', width: 165 },
            {
              title: '状态', dataIndex: 'status', key: 's', width: 100,
              render: (v: string) =>
                v === 'OPEN' ? <Tag color="red">待评审</Tag> : <Tag color="orange">评审中</Tag>,
            },
            {
              title: '来源', dataIndex: 'source_type', key: 'st', width: 90,
              render: (v: string) => ({ INSPECTION: '检验', REPORT: '报工', LOT_CARD: 'LOT卡', MANUAL: '手工' }[v] ?? v),
            },
            { title: '来源单据', dataIndex: 'source_ref', key: 'sr', width: 170, render: (v: string | null) => v || '-' },
            { title: '物料', dataIndex: 'material_code', key: 'm', width: 145 },
            { title: '数量', dataIndex: 'quantity', key: 'q', width: 80, align: 'right' as const },
            {
              title: '严重度', dataIndex: 'severity', key: 'sv', width: 90,
              render: (v: string) => ({ MINOR: <Tag>轻微</Tag>, MAJOR: <Tag color="orange">严重</Tag>, CRITICAL: <Tag color="red">致命</Tag> }[v] ?? v),
            },
          ]}
        />
      ),
    },
    {
      key: 'prs',
      label: <Badge count={counts.prs} size="small" offset={[8, 0]}>采购申请待下达</Badge>,
      children: (
        <CrossDomainTab
          title="待下达的采购申请"
          description="草稿申请需下达后才可整单转采购单；下达 / 转换 / 作废在「采购与库存 → 采购申请」页执行"
          targetPath="/mm/purchase-requests"
          fetcher={fetchPrs}
          rowKey="purchase_request_number"
          onChanged={onChanged}
          columns={[
            { title: '申请单号', dataIndex: 'purchase_request_number', key: 'n', width: 175 },
            { title: '供应商', dataIndex: 'supplier_name', key: 'sup', render: (v: string | null) => v || '-' },
            { title: '申请人', dataIndex: 'requested_by', key: 'by', width: 100, render: (v: string | null) => v || '-' },
            { title: '申请日期', dataIndex: 'request_date', key: 'd', width: 110, render: (v: string | null) => (v ? v.slice(0, 10) : '-') },
            {
              title: '预估金额', dataIndex: 'total_amount', key: 'amt', width: 110, align: 'right' as const,
              render: (v: number) => `¥${Number(v ?? 0).toLocaleString()}`,
            },
            { title: '备注', dataIndex: 'remarks', key: 'r', ellipsis: true },
          ]}
        />
      ),
    },
  ]

  return (
    <Card>
      <Tabs
        defaultActiveKey="quotation"
        items={tabItems}
        onChange={() => { /* 切换时各 tab 自行刷新 */ }}
      />
    </Card>
  )
}

export default PendingApprovalList
