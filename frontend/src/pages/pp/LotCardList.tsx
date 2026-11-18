import { Table, Button, Input, Select, Space, App as AntdApp, Tag, Card, Descriptions, Modal } from 'antd'
import { EyeOutlined, SearchOutlined, EditOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const { Option } = Select

// LOT卡状态映射
const lotCardStatusMap: Record<string, { label: string; color: string }> = {
  'ACTIVE': { label: '活跃', color: 'success' },
  'COMPLETED': { label: '已完成', color: 'processing' },
  'CANCELLED': { label: '已取消', color: 'error' }
}

interface LotCardInstruction {
  id: number
  lot_number: string
  sequence: number
  instruction_type?: string
  instruction_content?: string
  description?: string
}

interface LotCard {
  id: number
  lot_number: string
  production_order_number: string
  mi_number: string
  material_code: string
  quantity: number
  unit: string
  status: string
  instructions?: LotCardInstruction[]  // 指令项数组
  created_at?: string
  completed_at?: string
  remarks?: string
}

const LotCardList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [lotCards, setLotCards] = useState<LotCard[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<LotCard | null>(null)
  const [detailVisible, setDetailVisible] = useState(false)
  const navigate = useNavigate()

  // 筛选条件
  const [filters, setFilters] = useState<{
    production_order_number: string
    mi_number: string
    status?: string
  }>({
    production_order_number: '',
    mi_number: '',
    status: undefined
  })

  useEffect(() => {
    fetchLotCards()
  }, [])

  const fetchLotCards = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filters.production_order_number) {
        params.production_order_number = filters.production_order_number
      }
      if (filters.mi_number) {
        params.mi_number = filters.mi_number
      }
      if (filters.status) {
        params.status = filters.status
      }

      const response = await api.get('/pp/lot-cards', { params })
      setLotCards(response.data || [])
    } catch (error: any) {
      console.error('获取LOT卡列表失败:', error)
      const errorMsg = error.response?.data?.detail?.message || error.response?.data?.detail || error.message || '获取LOT卡列表失败'
      message.error(errorMsg)
      setLotCards([])
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    fetchLotCards()
  }

  const handleReset = () => {
    setFilters({
      production_order_number: '',
      mi_number: '',
      status: undefined
    })
    setTimeout(() => {
      fetchLotCards()
    }, 100)
  }

  const handleViewDetail = (record: LotCard) => {
    setSelectedRecord(record)
    setDetailVisible(true)
  }

  const columns = [
    {
      title: 'LOT卡号',
      dataIndex: 'lot_number',
      key: 'lot_number',
      width: 150,
      fixed: 'left' as const
    },
    {
      title: '生产订单号',
      dataIndex: 'production_order_number',
      key: 'production_order_number',
      width: 150,
      render: (text: string) => (
        <Button
          type="link"
          onClick={() => navigate(`/pp/production-orders/${text}`)}
          style={{ padding: 0 }}
        >
          {text}
        </Button>
      )
    },
    {
      title: 'MI编号',
      dataIndex: 'mi_number',
      key: 'mi_number',
      width: 150
    },
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 150
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      render: (quantity: number, record: LotCard) => `${quantity} ${record.unit}`
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusInfo = lotCardStatusMap[status] || { label: status, color: 'default' }
        return <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => date ? new Date(date).toLocaleString('zh-CN') : '-'
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (date: string) => date ? new Date(date).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: LotCard) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            查看详情
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/pp/lot-cards/${record.lot_number}/edit`)}
          >
            编辑
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div>
      <PageHeader
        title="LOT卡管理"
        description="LOT卡由系统在创建生产订单时根据MI自动生成，用于工序报工。支持按生产订单号、MI编号、状态等条件查询"
      />

        {/* 筛选条件 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space wrap>
            <Input
              placeholder="生产订单号"
              value={filters.production_order_number}
              onChange={(e) => setFilters({ ...filters, production_order_number: e.target.value })}
              style={{ width: 200 }}
              allowClear
            />
            <Input
              placeholder="MI编号"
              value={filters.mi_number}
              onChange={(e) => setFilters({ ...filters, mi_number: e.target.value })}
              style={{ width: 200 }}
              allowClear
            />
            <Select
              placeholder="状态"
              value={filters.status}
              onChange={(value) => setFilters({ ...filters, status: value })}
              style={{ width: 150 }}
              allowClear
            >
              <Option value="ACTIVE">活跃</Option>
              <Option value="COMPLETED">已完成</Option>
              <Option value="CANCELLED">已取消</Option>
            </Select>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
              查询
            </Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Card>

        <Table
          columns={columns}
          dataSource={lotCards}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
            pageSizeOptions: ['10', '20', '50', '100']
          }}
        />

      {/* 详情弹窗 */}
      <Modal
        title="LOT卡详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedRecord && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="LOT卡号" span={2}>
              {selectedRecord.lot_number}
            </Descriptions.Item>
            <Descriptions.Item label="生产订单号">
              {selectedRecord.production_order_number}
            </Descriptions.Item>
            <Descriptions.Item label="MI编号">
              {selectedRecord.mi_number}
            </Descriptions.Item>
            <Descriptions.Item label="物料编码">
              {selectedRecord.material_code}
            </Descriptions.Item>
            <Descriptions.Item label="数量">
              {selectedRecord.quantity} {selectedRecord.unit}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={lotCardStatusMap[selectedRecord.status]?.color || 'default'}>
                {lotCardStatusMap[selectedRecord.status]?.label || selectedRecord.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {selectedRecord.created_at ? new Date(selectedRecord.created_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {selectedRecord.completed_at ? new Date(selectedRecord.completed_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>
              {selectedRecord.remarks || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="MI指令项" span={2}>
              {selectedRecord.instructions && selectedRecord.instructions.length > 0 ? (
                <Table
                  columns={[
                    { title: '序号', dataIndex: 'sequence', key: 'sequence', width: 80 },
                    { title: '工序代码', dataIndex: 'operation_code', key: 'operation_code', width: 120 },
                    { title: '工序名称', dataIndex: 'operation_name', key: 'operation_name', width: 150 },
                    { title: '指令类型', dataIndex: 'instruction_type', key: 'instruction_type', width: 150 },
                    { title: '指令内容', dataIndex: 'instruction_content', key: 'instruction_content', ellipsis: true },
                    { title: '说明', dataIndex: 'description', key: 'description', ellipsis: true }
                  ]}
                  dataSource={[...selectedRecord.instructions].sort((a, b) => a.sequence - b.sequence)}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  scroll={{ y: 200 }}
                />
              ) : (
                <span style={{ color: 'hsl(var(--ink-faint))' }}>暂无指令项</span>
              )}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default LotCardList
