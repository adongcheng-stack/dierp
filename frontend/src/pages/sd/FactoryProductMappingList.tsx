import { Table, Button, Space, App as AntdApp, Tag, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const FactoryProductMappingList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [mappings, setMappings] = useState([])
  const [materials, setMaterials] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      // 并行获取映射和物料数据
      const [mappingsResponse, materialsResponse] = await Promise.all([
        api.get('/sd/factory-product-mappings', { params: { limit: 1000 } }),
        api.get('/mm/materials', { params: { limit: 1000 } })
      ])
      
      const allMappings = mappingsResponse.data || []
      const allMaterials = materialsResponse.data || []
      
      // 只保存成品(FG)物料，用于显示产品名称
      const fgMaterials = allMaterials.filter((m: any) => m.material_type === 'FG')
      setMaterials(fgMaterials)
      
      // 产品主数据管理只显示成品(FG类型)
      const fgMaterialCodes = new Set(
        fgMaterials.map((m: any) => m.material_code)
      )
      // 只保留material_code对应的物料是FG类型的映射
      const fgMappings = allMappings.filter((mapping: any) => 
        fgMaterialCodes.has(mapping.material_code)
      )
      setMappings(fgMappings)
    } catch (error) {
      console.error('获取产品主数据列表失败:', error)
      message.error('获取产品主数据列表失败')
    } finally {
      setLoading(false)
    }
  }

  const getMaterial = (materialCode: string) => {
    return materials.find((m: any) => m.material_code === materialCode)
  }

  const getMaterialName = (materialCode: string) => {
    const material = getMaterial(materialCode)
    return material ? material.material_name : '-'
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/sd/factory-product-mappings/${id}`)
      message.success('产品主数据已删除')
      fetchData()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const columns = [
    {
      title: '客户ID',
      dataIndex: 'customer_id',
      key: 'customer_id',
    },
    {
      title: '本厂编号（唯一标识）',
      dataIndex: 'factory_product_number',
      key: 'factory_product_number',
    },
    {
      title: '产品名称',
      dataIndex: 'material_name',
      key: 'material_name',
      render: (_: any, record: any) => {
        return getMaterialName(record.material_code) || '-'
      },
    },
    {
      title: '产品编码',
      dataIndex: 'material_code',
      key: 'material_code',
    },
    {
      title: '产品类型',
      dataIndex: 'material_type',
      key: 'material_type',
      render: (_: any, record: any) => {
        const material = getMaterial(record.material_code)
        return material?.material_type || '-'
      },
    },
    {
      title: '层数',
      dataIndex: 'layer_count',
      key: 'layer_count',
      render: (_: any, record: any) => {
        const material = getMaterial(record.material_code)
        return material?.layer_count || '-'
      },
    },
    {
      title: '板厚(mm)',
      dataIndex: 'board_thickness',
      key: 'board_thickness',
      render: (_: any, record: any) => {
        const material = getMaterial(record.material_code)
        return material?.board_thickness || '-'
      },
    },
    {
      title: '表面处理',
      dataIndex: 'surface_finish',
      key: 'surface_finish',
      render: (_: any, record: any) => {
        const material = getMaterial(record.material_code)
        return material?.surface_finish || '-'
      },
    },
    {
      title: '生产版本',
      dataIndex: 'production_version_id',
      key: 'production_version_id',
      render: (text: string) => text || '-',
    },
    {
      title: '默认映射',
      dataIndex: 'is_default',
      key: 'is_default',
      render: (isDefault: boolean) => (
        <Tag color={isDefault ? 'green' : 'default'}>
          {isDefault ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '生效日期',
      dataIndex: 'effective_date',
      key: 'effective_date',
      render: (text: string) => text ? new Date(text).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '失效日期',
      dataIndex: 'expiry_date',
      key: 'expiry_date',
      render: (text: string) => text ? new Date(text).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/eng/factory-product-mappings/${record.id}/edit`)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个产品主数据吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="产品主数据管理"
        description="以本厂编号作为唯一标识，包含物料主数据中成品(FG)的内容"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/eng/factory-product-mappings/new')}
          >
            新建产品主数据
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={mappings}
        loading={loading}
        rowKey="id"
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
      />
    </div>
  )
}

export default FactoryProductMappingList

