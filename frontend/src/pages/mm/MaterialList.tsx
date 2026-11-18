import { Table, Button } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const MaterialList: React.FC = () => {
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchMaterials()
  }, [])

  const fetchMaterials = async () => {
    setLoading(true)
    try {
      const response = await api.get('/mm/materials')
      // 物料主数据管理中不显示成品(FG类型)
      const allMaterials = response.data || []
      const nonFgMaterials = allMaterials.filter((m: any) => m.material_type !== 'FG')
      setMaterials(nonFgMaterials)
    } catch (error) {
      console.error('获取物料列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: '物料编码', dataIndex: 'material_code', key: 'material_code' },
    { title: '物料名称', dataIndex: 'material_name', key: 'material_name' },
    { title: '分类', dataIndex: 'category', key: 'category' },
    { title: '单位', dataIndex: 'unit', key: 'unit' },
    { title: '当前库存', dataIndex: 'current_stock', key: 'current_stock' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => navigate(`/mm/materials/${record.material_code}/edit`)}
        >
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="物料主数据管理"
        description="维护原材料与半成品主数据；成品物料请在产品主数据中管理"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/mm/materials/new')}
          >
            新建物料
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={materials}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default MaterialList

