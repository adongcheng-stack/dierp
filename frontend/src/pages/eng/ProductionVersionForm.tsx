import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'

const { Option } = Select
const { TextArea } = Input

interface ProductionVersionFormData {
  material_code: string
  bom_number: string
  routing_id: string
  mi_number: string
  version: string
  effective_date: string
  expiry_date?: string
  description?: string
}

const ProductionVersionForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [materials, setMaterials] = useState<any[]>([])
  const [boms, setBoms] = useState<any[]>([])
  const [routings, setRoutings] = useState<any[]>([])
  const [mis, setMis] = useState<any[]>([])
  const [selectedMaterial, setSelectedMaterial] = useState<string>('')
  const isEdit = !!id

  useEffect(() => {
    fetchMaterials()
    if (isEdit) {
      fetchProductionVersion()
    }
  }, [id])

  useEffect(() => {
    if (selectedMaterial) {
      fetchBOMs()
      fetchRoutings()
      fetchMIs()
    }
  }, [selectedMaterial])

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

  const fetchProductionVersion = async () => {
    try {
      const response = await api.get(`/eng/production-versions/${id}`)
      const data = response.data
      setSelectedMaterial(data.material_code)
      form.setFieldsValue({
        ...data,
        effective_date: data.effective_date ? dayjs(data.effective_date) : undefined,
        expiry_date: data.expiry_date ? dayjs(data.expiry_date) : undefined
      })
      // 加载后获取BOM、Routing、MI列表
      await Promise.all([fetchBOMs(), fetchRoutings(), fetchMIs()])
    } catch (error) {
      message.error('获取生产版本信息失败')
      navigate('/eng/production-versions')
    }
  }

  const handleMaterialChange = (materialCode: string) => {
    setSelectedMaterial(materialCode)
    form.setFieldsValue({
      bom_number: undefined,
      routing_id: undefined,
      mi_number: undefined
    })
  }

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      const formData: ProductionVersionFormData = {
        material_code: values.material_code,
        bom_number: values.bom_number,
        routing_id: values.routing_id,
        mi_number: values.mi_number && values.mi_number.trim() ? values.mi_number.trim() : undefined,  // 确保 undefined 而不是空字符串
        version: values.version,
        effective_date: values.effective_date ? values.effective_date.toISOString() : undefined,
        expiry_date: values.expiry_date ? values.expiry_date.toISOString() : undefined,
        description: values.description
      }

      if (isEdit) {
        await api.put(`/eng/production-versions/${id}`, formData)
        message.success('生产版本更新成功')
      } else {
        await api.post('/eng/production-versions', formData)
        message.success('生产版本创建成功')
      }
      navigate('/eng/production-versions')
    } catch (error: any) {
      console.error('生产版本操作失败:', error)
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || '操作失败'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑生产版本' : '新建生产版本'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            version: 'V1.0'
          }}
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
                  onChange={handleMaterialChange}
                  disabled={isEdit}
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
                  placeholder={selectedMaterial ? "请选择BOM" : "请先选择物料"}
                  showSearch
                  disabled={!selectedMaterial}
                  notFoundContent={selectedMaterial ? (boms.length === 0 ? "该物料暂无BOM" : "未找到") : "请先选择物料"}
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
                  placeholder={selectedMaterial ? "请选择工艺路线" : "请先选择物料"}
                  showSearch
                  disabled={!selectedMaterial}
                  notFoundContent={selectedMaterial ? (routings.length === 0 ? "该物料暂无工艺路线" : "未找到") : "请先选择物料"}
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
                label="MI（可选，发布时必选）"
              >
                <Select
                  placeholder={selectedMaterial ? "请选择MI（可选）" : "请先选择物料"}
                  showSearch
                  allowClear
                  disabled={!selectedMaterial}
                  notFoundContent={selectedMaterial ? (mis.length === 0 ? "该物料暂无MI" : "未找到") : "请先选择物料"}
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
            <TextArea rows={4} placeholder="请输入描述" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/eng/production-versions')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default ProductionVersionForm

