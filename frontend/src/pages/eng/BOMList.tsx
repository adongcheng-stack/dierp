import { Table, Button, Tag } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const BOM_STATUS: { [key: string]: { color: string; text: string } } = {
  NEW: { color: 'default', text: '新建' },
  REVIEWING: { color: 'orange', text: '审阅中' },
  RELEASED: { color: 'green', text: '已发布' },
  PRODUCING: { color: 'blue', text: '生产中' },
  OBSOLETE: { color: 'default', text: '已失效' }
}

const BOMList: React.FC = () => {
  const [boms, setBoms] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchBOMs()
  }, [])

  const fetchBOMs = async () => {
    setLoading(true)
    try {
      const response = await api.get('/eng/boms')
      setBoms(response.data)
    } catch (error) {
      console.error('获取BOM列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: 'BOM编号', dataIndex: 'bom_number', key: 'bom_number' },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '父项物料', dataIndex: 'parent_material_code', key: 'parent_material_code' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const info = BOM_STATUS[status] || { color: 'default', text: status }
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
          onClick={() => navigate(`/eng/boms/${record.bom_number}/edit`)}
        >
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="BOM管理"
        description="维护产品物料清单，作为生产版本与领料核算的依据"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/eng/boms/new')}
          >
            新建BOM
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={boms}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default BOMList
