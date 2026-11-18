import { Table, Button, Dropdown, App as AntdApp, Space } from 'antd'
import { PlusOutlined, EditOutlined, MoreOutlined } from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { useConfirm } from '../../components/common/ConfirmProvider'

const ProductionOrderList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const confirm = useConfirm()

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    setLoading(true)
    try {
      const response = await api.get('/pp/production-orders')
      setOrders(response.data)
    } catch (error) {
      console.error('获取生产订单列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (orderNumber: string, action: string) => {
    try {
      let endpoint = ''
      let successMsg = ''
      
      switch (action) {
        case 'release':
          endpoint = `/pp/production-orders/${orderNumber}/release`
          successMsg = '生产订单已下达'
          break
        case 'start':
          endpoint = `/pp/production-orders/${orderNumber}/start`
          successMsg = '生产订单已开始生产'
          break
        case 'complete':
          endpoint = `/pp/production-orders/${orderNumber}/complete`
          successMsg = '生产订单已完成'
          break
        case 'close':
          endpoint = `/pp/production-orders/${orderNumber}/close`
          successMsg = '生产订单已关闭'
          break
        default:
          return
      }

      await api.post(endpoint)
      message.success(successMsg)
      fetchOrders() // 刷新列表
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      message.error(errorMsg)
      console.error('修改生产订单状态失败:', error)
    }
  }

  const getStatusMenuItems = (record: any): MenuProps['items'] => {
    const items: MenuProps['items'] = []
    
    if (record.status === 'DRAFT') {
      items.push({
        key: 'release',
        label: '下达',
        onClick: () => {
          confirm({
            title: '确认下达',
            content: `确定要下达生产订单 ${record.order_number} 吗？`,
            onOk: () => handleStatusChange(record.order_number, 'release')
          })
        }
      })
    }
    
    if (record.status === 'RELEASED') {
      items.push({
        key: 'start',
        label: '开始生产',
        onClick: () => {
          confirm({
            title: '确认开始生产',
            content: `确定要开始生产订单 ${record.order_number} 吗？`,
            onOk: () => handleStatusChange(record.order_number, 'start')
          })
        }
      })
      // 关闭仅在「已完成」状态下允许（COMPLETED -> CLOSED）
    }

    if (record.status === 'IN_PRODUCTION') {
      items.push({
        key: 'complete',
        label: '完成',
        onClick: () => {
          confirm({
            title: '确认完成',
            content: `确定要完成生产订单 ${record.order_number} 吗？`,
            onOk: () => handleStatusChange(record.order_number, 'complete')
          })
        }
      })
      // 关闭仅在「已完成」状态下允许（COMPLETED -> CLOSED）
    }

    // 需求规定：所有工序完成后才可关闭生产订单
    if (record.status === 'COMPLETED') {
      items.push({
        key: 'close',
        label: '关闭',
        danger: true,
        onClick: () => {
          confirm({
            title: '确认关闭',
            icon: 'warning',
            content: `所有工序已完成，确定要关闭生产订单 ${record.order_number} 吗？`,
            onOk: () => handleStatusChange(record.order_number, 'close')
          })
        }
      })
    }

    return items.length > 0 ? items : undefined
  }

  const columns = [
    { title: '生产订单号', dataIndex: 'order_number', key: 'order_number' },
    { title: '销售订单号', dataIndex: 'sales_order_number', key: 'sales_order_number' },
    { title: '物料编码', dataIndex: 'material_code', key: 'material_code' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const statusMap: { [key: string]: { text: string; color: string } } = {
          'DRAFT': { text: '草稿', color: 'default' },
          'RELEASED': { text: '已下达', color: 'processing' },
          'IN_PRODUCTION': { text: '生产中', color: 'processing' },
          'COMPLETED': { text: '已完成', color: 'success' },
          'CLOSED': { text: '已关闭', color: 'default' },
          'CANCELLED': { text: '已取消', color: 'error' }
        }
        const statusInfo = statusMap[status] || { text: status, color: 'default' }
        return <span style={{ color: statusInfo.color === 'error' ? 'hsl(var(--destructive))' : statusInfo.color === 'success' ? 'hsl(var(--chart-success))' : statusInfo.color === 'processing' ? 'hsl(var(--brand))' : undefined }}>{statusInfo.text}</span>
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: any) => {
        const menuItems = getStatusMenuItems(record)
        return (
          <Space>
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => navigate(`/pp/production-orders/${record.order_number}/edit`)}
            >
              编辑
            </Button>
            {menuItems && menuItems.length > 0 && (
              <Dropdown menu={{ items: menuItems }} trigger={['click']}>
                <Button type="link" icon={<MoreOutlined />}>
                  更多
                </Button>
              </Dropdown>
            )}
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      <PageHeader
        title="工单管理"
        description="下达工单、推进生产状态并跟踪生产进度"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/pp/production-orders/new')}
          >
            新建工单
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={orders}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default ProductionOrderList

