import { Table, Button, Card, Space, Tag, App as AntdApp, Input, Select, Modal, Form, DatePicker, Row, Col } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { Option } = Select
const { Search } = Input
const { TextArea } = Input

const ProductionVersionList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [productionVersions, setProductionVersions] = useState<any[]>([])
  const [searchText, setSearchText] = useState('')
  const [releaseModalVisible, setReleaseModalVisible] = useState(false)
  const [releaseForm] = Form.useForm()
  const [releasing, setReleasing] = useState(false)
  const [currentReleasePV, setCurrentReleasePV] = useState<any>(null)
  const [materials, setMaterials] = useState<any[]>([])
  const [boms, setBoms] = useState<any[]>([])
  const [routings, setRoutings] = useState<any[]>([])
  const [mis, setMis] = useState<any[]>([])
  const [selectedMaterial, setSelectedMaterial] = useState<string>('')

  useEffect(() => {
    fetchProductionVersions()
    fetchMaterials()
  }, [])

  useEffect(() => {
    if (selectedMaterial) {
      fetchBOMs()
      fetchRoutings()
      fetchMIs()
    }
  }, [selectedMaterial])

  const fetchProductionVersions = async () => {
    setLoading(true)
    try {
      const response = await api.get('/eng/production-versions')
      setProductionVersions(response.data || [])
    } catch (error) {
      message.error('获取生产版本列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchMaterials = async () => {
    try {
      const response = await api.get('/mm/materials')
      setMaterials(response.data)
    } catch (error) {
      console.error('获取物料列表失败:', error)
    }
  }

  const fetchBOMs = async () => {
    try {
      const response = await api.get('/eng/boms', {
        params: { material_code: selectedMaterial }
      })
      setBoms(response.data || [])
    } catch (error) {
      console.error('获取BOM列表失败:', error)
      setBoms([])
    }
  }

  const fetchRoutings = async () => {
    try {
      const response = await api.get('/eng/routings', {
        params: { material_code: selectedMaterial }
      })
      setRoutings(response.data || [])
    } catch (error) {
      console.error('获取工艺路线列表失败:', error)
      setRoutings([])
    }
  }

  const fetchMIs = async () => {
    try {
      const response = await api.get('/eng/mis', {
        params: { material_code: selectedMaterial }
      })
      setMis(response.data || [])
    } catch (error) {
      console.error('获取MI列表失败:', error)
      setMis([])
    }
  }

  const handleReleaseClick = async (record: any) => {
    setCurrentReleasePV(record)
    setSelectedMaterial(record.material_code)
    
    // 加载数据
    try {
      const [bomsRes, routingsRes, misRes] = await Promise.all([
        api.get('/eng/boms', { params: { material_code: record.material_code } }),
        api.get('/eng/routings', { params: { material_code: record.material_code } }),
        api.get('/eng/mis', { params: { material_code: record.material_code } })
      ])
      setBoms(bomsRes.data || [])
      setRoutings(routingsRes.data || [])
      setMis(misRes.data || [])
    } catch (error) {
      console.error('加载数据失败:', error)
    }
    
    // 填充表单
    releaseForm.setFieldsValue({
      ...record,
      effective_date: record.effective_date ? dayjs(record.effective_date) : undefined,
      expiry_date: record.expiry_date ? dayjs(record.expiry_date) : undefined
    })
    
    setReleaseModalVisible(true)
  }

  const handleRelease = async () => {
    try {
      await releaseForm.validateFields()
      const values = releaseForm.getFieldsValue()
      
      // 发布时MI必选
      if (!values.mi_number) {
        message.error('发布生产版本时MI必选，请选择MI')
        return
      }
      
      setReleasing(true)
      
      // 先更新生产版本
      const formData = {
        material_code: values.material_code,
        bom_number: values.bom_number,
        routing_id: values.routing_id,
        mi_number: values.mi_number || undefined,
        version: values.version,
        effective_date: values.effective_date.format('YYYY-MM-DD HH:mm:ss'),
        expiry_date: values.expiry_date ? values.expiry_date.format('YYYY-MM-DD HH:mm:ss') : undefined,
        description: values.description
      }
      
      await api.put(`/eng/production-versions/${currentReleasePV.production_version_id}`, formData)
      
      // 然后发布
      await api.post(`/eng/production-versions/${currentReleasePV.production_version_id}/release`)
      
      message.success('生产版本发布成功')
      setReleaseModalVisible(false)
      releaseForm.resetFields()
      fetchProductionVersions()
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请填写所有必填字段')
      } else {
        message.error(error.response?.data?.detail || '发布失败')
      }
    } finally {
      setReleasing(false)
    }
  }

  const filteredProductionVersions = productionVersions.filter(pv => {
    if (searchText) {
      return pv.production_version_id?.toLowerCase().includes(searchText.toLowerCase()) ||
             pv.material_code?.toLowerCase().includes(searchText.toLowerCase())
    }
    return true
  })

  const columns = [
    {
      title: '生产版本ID',
      dataIndex: 'production_version_id',
      key: 'production_version_id',
      width: 200,
      render: (text: string) => <strong>{text}</strong>
    },
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 150
    },
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      width: 100
    },
    {
      title: 'BOM',
      dataIndex: 'bom_number',
      key: 'bom_number',
      width: 150
    },
    {
      title: '工艺路线',
      dataIndex: 'routing_id',
      key: 'routing_id',
      width: 150
    },
    {
      title: 'MI',
      dataIndex: 'mi_number',
      key: 'mi_number',
      width: 150
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: { [key: string]: { color: string; text: string } } = {
          'DRAFT': { color: 'default', text: '草稿' },
          'RELEASED': { color: 'success', text: '已发布' },
          'ACTIVE': { color: 'processing', text: '激活' }
        }
        const statusInfo = statusMap[status] || { color: 'default', text: status }
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
      }
    },
    {
      title: '生效日期',
      dataIndex: 'effective_date',
      key: 'effective_date',
      width: 180,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space>
          {record.status === 'DRAFT' && (
            <>
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => navigate(`/eng/production-versions/${record.production_version_id}/edit`)}
              >
                编辑
              </Button>
              <Button
                type="link"
                style={{ color: 'hsl(var(--chart-success))' }}
                onClick={() => handleReleaseClick(record)}
              >
                发布
              </Button>
            </>
          )}
        </Space>
      )
    }
  ]

  return (
    <div>
      <Card
        title="生产版本管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/eng/production-versions/new')}
          >
            新建生产版本
          </Button>
        }
      >
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Search
            placeholder="搜索生产版本ID、物料编码"
            allowClear
            style={{ width: 300 }}
            onSearch={setSearchText}
            onChange={(e) => !e.target.value && setSearchText('')}
          />
        </Space>

        <Table
          columns={columns}
          dataSource={filteredProductionVersions}
          rowKey="production_version_id"
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>

      <Modal
        title="发布生产版本"
        open={releaseModalVisible}
        onCancel={() => {
          setReleaseModalVisible(false)
          releaseForm.resetFields()
        }}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => {
            setReleaseModalVisible(false)
            releaseForm.resetFields()
          }}>
            取消
          </Button>,
          <Button
            key="release"
            type="primary"
            loading={releasing}
            onClick={handleRelease}
            style={{ backgroundColor: 'hsl(var(--chart-success))', borderColor: 'hsl(var(--chart-success))' }}
          >
            发布
          </Button>
        ]}
      >
        <Form
          form={releaseForm}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="material_code"
                label="物料编码"
                rules={[{ required: true, message: '请选择物料' }]}
              >
                <Select
                  placeholder="请选择物料"
                  showSearch
                  disabled
                >
                  {materials.map(material => (
                    <Option key={material.material_code} value={material.material_code}>
                      {material.material_code} - {material.material_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="version"
                label="版本号"
                rules={[{ required: true, message: '请输入版本号' }]}
              >
                <Input placeholder="例如: V1.0" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="bom_number"
                label="BOM"
                rules={[{ required: true, message: '请选择BOM' }]}
              >
                <Select
                  placeholder="请选择BOM"
                  showSearch
                >
                  {boms.map(bom => (
                    <Option key={bom.bom_number} value={bom.bom_number}>
                      {bom.bom_number} - {bom.version}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="routing_id"
                label="工艺路线"
                rules={[{ required: true, message: '请选择工艺路线' }]}
              >
                <Select
                  placeholder="请选择工艺路线"
                  showSearch
                >
                  {routings.map(routing => (
                    <Option key={routing.routing_id} value={routing.routing_id}>
                      {routing.routing_id} - {routing.version}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="mi_number"
                label="MI（发布时必选）"
                rules={[{ required: true, message: '发布时MI必选' }]}
              >
                <Select
                  placeholder="请选择MI（必选）"
                  showSearch
                  notFoundContent={mis.length === 0 ? "该物料暂无MI" : "未找到"}
                >
                  {mis.map(mi => (
                    <Option key={mi.mi_number} value={mi.mi_number}>
                      {mi.mi_number} - {mi.version} ({mi.status === 'APPROVED' ? '已批准' : mi.status})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="effective_date"
                label="生效日期"
                rules={[{ required: true, message: '请选择生效日期' }]}
              >
                <DatePicker
                  style={{ width: '100%' }}
                  showTime
                  format="YYYY-MM-DD HH:mm:ss"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="expiry_date"
                label="失效日期"
              >
                <DatePicker
                  style={{ width: '100%' }}
                  showTime
                  format="YYYY-MM-DD HH:mm:ss"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProductionVersionList

