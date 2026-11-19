import { Table, Tag, Input, Space, Button } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface InventoryRow {
  material_code: string
  material_name: string
  category: string
  unit: string
  current_stock: number
  safety_stock: number
  stock_status: string
}

/** 库存充足度 Tag 配色（与后端 get_inventory 的 stock_status 语义对应） */
const STOCK_STATUS_COLOR: Record<string, string> = {
  充足: 'green',
  不足: 'red',
}

const InventoryLedger: React.FC = () => {
  const [rows, setRows] = useState<InventoryRow[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (keyword.trim()) params.material_code = keyword.trim()
      const response = await api.get('/mm/inventory', { params })
      setRows(response.data || [])
    } catch (error) {
      console.error('获取库存台账失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '物料编码', dataIndex: 'material_code', key: 'material_code' },
    { title: '物料名称', dataIndex: 'material_name', key: 'material_name' },
    { title: '分类', dataIndex: 'category', key: 'category', width: 120 },
    {
      title: '当前库存',
      dataIndex: 'current_stock',
      key: 'current_stock',
      width: 120,
      align: 'right' as const,
    },
    {
      title: '安全库存',
      dataIndex: 'safety_stock',
      key: 'safety_stock',
      width: 120,
      align: 'right' as const,
    },
    {
      title: '单位',
      dataIndex: 'unit',
      key: 'unit',
      width: 90,
    },
    {
      title: '库存状态',
      dataIndex: 'stock_status',
      key: 'stock_status',
      width: 110,
      render: (v: string) => <Tag color={STOCK_STATUS_COLOR[v] ?? 'default'}>{v}</Tag>,
    },
  ]

  return (
    <div>
      <PageHeader
        title="库存台账"
        description="物料可用量实时视图：生产领料扣减、采购到货回冲、完工成品入库都会即时反映到当前库存"
        actions={
          <Space.Compact>
            <Input
              prefix={<SearchOutlined />}
              placeholder="按物料编码搜索"
              allowClear
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={fetchData}
              style={{ width: 220 }}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
              刷新
            </Button>
          </Space.Compact>
        }
      />
      <Table
        columns={columns}
        dataSource={rows}
        loading={loading}
        rowKey="material_code"
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 项` }}
      />
    </div>
  )
}

export default InventoryLedger