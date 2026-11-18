import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker, Switch, Descriptions } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'

const { Option } = Select

interface FactoryProductMappingFormData {
  customer_id: string
  factory_product_number: string
  material_code: string
  production_version_id?: string
  is_default: boolean
  effective_date: string
  expiry_date?: string
}

const FactoryProductMappingForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [customers, setCustomers] = useState<any[]>([])
  const [productionVersions, setProductionVersions] = useState<any[]>([])
  const [selectedMaterial, setSelectedMaterial] = useState<any>(null)
  const isEdit = !!id

  useEffect(() => {
    fetchCustomers()
    if (isEdit) {
      fetchMapping()
    }
  }, [id])

  // 监听来自新建产品页面的消息（独立useEffect，避免依赖问题）
  useEffect(() => {
    const handleMessage = async (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        return
      }
      
      if (event.data.type === 'PRODUCT_CREATED') {
        const materialCode = event.data.materialCode
        // 自动刷新产品信息
        if (materialCode) {
          try {
            const response = await api.get(`/mm/materials/${materialCode}`)
            const material = response.data
            if (material) {
              setSelectedMaterial(material)
              // 获取生产版本
              try {
                const pvResponse = await api.get('/eng/production-versions', {
                  params: { limit: 1000 }
                })
                const allVersions = pvResponse.data || []
                const filteredVersions = allVersions.filter((pv: any) => 
                  pv.material_code === materialCode && (pv.status === 'RELEASED' || pv.status === 'ACTIVE')
                )
                setProductionVersions(filteredVersions)
              } catch (error) {
                console.error('获取生产版本列表失败:', error)
                setProductionVersions([])
              }
              form.setFieldsValue({ production_version_id: undefined })
              message.success('产品创建成功，已自动加载产品信息')
            }
          } catch (error) {
            console.error('获取产品信息失败:', error)
          }
        }
      }
    }
    
    window.addEventListener('message', handleMessage)
    
    return () => {
      window.removeEventListener('message', handleMessage)
    }
  }, [form])

  const fetchCustomers = async () => {
    try {
      // 只获取已激活的客户
      const response = await api.get('/sd/customers', {
        params: {
          status: 'ACTIVE'
        }
      })
      setCustomers(response.data || [])
    } catch (error) {
      console.error('获取客户列表失败:', error)
    }
  }

  const fetchProductionVersions = async (materialCode: string) => {
    try {
      const response = await api.get('/eng/production-versions', {
        params: { limit: 1000 }
      })
      const allVersions = response.data || []
      // 过滤出匹配物料编码的生产版本
      const filteredVersions = allVersions.filter((pv: any) => 
        pv.material_code === materialCode && (pv.status === 'RELEASED' || pv.status === 'ACTIVE')
      )
      setProductionVersions(filteredVersions)
    } catch (error) {
      console.error('获取生产版本列表失败:', error)
      setProductionVersions([])
    }
  }

  const fetchMapping = async () => {
    try {
      const response = await api.get(`/sd/factory-product-mappings/by-id/${id}`)
      const mapping = response.data
      if (mapping) {
        form.setFieldsValue({
          ...mapping,
          effective_date: mapping.effective_date ? dayjs(mapping.effective_date) : undefined,
          expiry_date: mapping.expiry_date ? dayjs(mapping.expiry_date) : undefined,
        })
        // 编辑模式下，使用material_code（即factory_product_number）加载物料信息
        const materialCode = mapping.material_code || mapping.factory_product_number
        if (materialCode) {
          try {
            const materialResponse = await api.get(`/mm/materials/${materialCode}`)
            const materialData = materialResponse.data
            if (materialData) {
              setSelectedMaterial(materialData)
            }
          } catch (err) {
            console.error('获取物料信息失败:', err)
          }
          fetchProductionVersions(materialCode)
        }
      }
    } catch (error) {
      message.error('获取产品主数据信息失败')
      navigate('/eng/factory-product-mappings')
    }
  }

  const handleFactoryProductNumberChange = async (factoryProductNumber: string) => {
    if (!factoryProductNumber) {
      setSelectedMaterial(null)
      setProductionVersions([])
      form.setFieldsValue({ production_version_id: undefined })
      return
    }

    // 使用本厂编号作为产品编码查找产品
    try {
      const response = await api.get(`/mm/materials/${factoryProductNumber}`)
      const material = response.data
      if (material) {
        setSelectedMaterial(material)
        fetchProductionVersions(factoryProductNumber)
        form.setFieldsValue({ production_version_id: undefined })
      } else {
        setSelectedMaterial(null)
        setProductionVersions([])
      }
    } catch (error) {
      // 物料不存在，清空物料信息
      setSelectedMaterial(null)
      setProductionVersions([])
      form.setFieldsValue({ production_version_id: undefined })
    }
  }

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      // 本厂编号作为产品编码
      const materialCode = values.factory_product_number
      
      // 检查产品是否存在
      if (!selectedMaterial) {
        message.warning('请先创建对应的产品主数据，本厂编号将作为产品编码使用')
        setLoading(false)
        return
      }

      const formData: FactoryProductMappingFormData = {
        customer_id: values.customer_id,
        factory_product_number: values.factory_product_number,
        material_code: materialCode, // 使用本厂编号作为产品编码
        production_version_id: values.production_version_id || undefined,
        is_default: values.is_default || false,
        effective_date: values.effective_date.toISOString(),
        expiry_date: values.expiry_date ? values.expiry_date.toISOString() : undefined,
      }
      
      if (isEdit) {
        await api.put(`/sd/factory-product-mappings/${id}`, formData)
        message.success('产品主数据更新成功')
      } else {
        await api.post('/sd/factory-product-mappings', formData)
        message.success('产品主数据创建成功')
      }
      navigate('/eng/factory-product-mappings')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      message.error(errorMsg)
      console.error('产品主数据操作失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑产品主数据' : '新建产品主数据'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            is_default: true,
            effective_date: dayjs(),
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customer_id"
                label="客户"
                rules={[{ required: true, message: '请选择客户' }]}
              >
                <Select placeholder="请选择客户" showSearch disabled={isEdit}>
                  {customers.map(customer => (
                    <Option key={customer.customer_id} value={customer.customer_id}>
                      {customer.legal_name} ({customer.customer_id})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="factory_product_number"
                label="本厂编号（唯一标识）"
                rules={[{ required: true, message: '请输入本厂编号' }]}
                extra={
                  <div>
                    <div>本厂编号作为产品主数据的唯一标识，同时也是产品编码</div>
                    {!selectedMaterial && form.getFieldValue('factory_product_number') && (
                      <Button 
                        type="link" 
                        size="small" 
                        style={{ padding: 0, height: 'auto', marginTop: '4px' }}
                        onClick={() => {
                          const factoryProductNumber = form.getFieldValue('factory_product_number')
                          window.open(`/mm/materials/new?material_code=${factoryProductNumber}`, '_blank')
                        }}
                      >
                        该编号对应的产品不存在，点击这里创建产品
                      </Button>
                    )}
                  </div>
                }
              >
                <Input 
                  placeholder="如：HS1004ENIGAB01" 
                  disabled={isEdit}
                  onChange={(e) => {
                    if (!isEdit) {
                      handleFactoryProductNumberChange(e.target.value)
                    }
                  }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="production_version_id"
                label="生产版本（可选）"
                extra="选择产品编码后，会显示该产品的可用生产版本"
              >
                <Select
                  placeholder="请选择生产版本（可选）"
                  showSearch
                  allowClear
                  disabled={!selectedMaterial}
                  filterOption={(input, option) => {
                    const text = String(option?.children ?? '')
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                >
                  {productionVersions.map((pv: any) => (
                    <Option key={pv.production_version_id} value={pv.production_version_id}>
                      {pv.production_version_id} - {pv.material_code} ({pv.status === 'RELEASED' ? '已发布' : pv.status === 'ACTIVE' ? '激活' : pv.status})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {!selectedMaterial && form.getFieldValue('factory_product_number') && (
            <Card 
              style={{ marginTop: 16, marginBottom: 16 }}
              size="small"
            >
              <div style={{ padding: '24px', textAlign: 'center', color: 'hsl(var(--ink-faint))' }}>
                <div>本厂编号 "{form.getFieldValue('factory_product_number')}" 对应的产品不存在</div>
                <div style={{ marginTop: '8px' }}>
                  <Button 
                    type="link" 
                    size="small"
                    onClick={() => {
                      const factoryProductNumber = form.getFieldValue('factory_product_number')
                      window.open(`/mm/materials/new?material_code=${factoryProductNumber}`, '_blank')
                    }}
                  >
                    点击这里创建产品（产品编码将使用本厂编号）
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {!selectedMaterial && !form.getFieldValue('factory_product_number') && (
            <Card 
              style={{ marginTop: 16, marginBottom: 16 }}
              size="small"
            >
              <div style={{ padding: '24px', textAlign: 'center', color: 'hsl(var(--ink-faint))' }}>
                <div>请输入本厂编号，系统将自动查找对应的产品主数据信息</div>
                <div style={{ marginTop: '8px', fontSize: '12px' }}>
                  本厂编号将作为产品编码使用
                </div>
              </div>
            </Card>
          )}

          {selectedMaterial && (
            <Card 
              style={{ marginTop: 16, marginBottom: 16 }}
              size="small"
              extra={
                <Button 
                  type="link" 
                  size="small"
                  onClick={() => navigate(`/mm/materials/${selectedMaterial.material_code}/edit`)}
                >
                  编辑物料主数据
                </Button>
              }
            >
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="产品编码" span={1}>
                  <strong>{selectedMaterial.material_code}</strong>
                </Descriptions.Item>
                <Descriptions.Item label="产品名称" span={1}>
                  <strong>{selectedMaterial.material_name}</strong>
                </Descriptions.Item>
                <Descriptions.Item label="产品类型">{selectedMaterial.material_type || '-'}</Descriptions.Item>
                <Descriptions.Item label="物料分类">{selectedMaterial.category || '-'}</Descriptions.Item>
                <Descriptions.Item label="规格型号">{selectedMaterial.specification || '-'}</Descriptions.Item>
                <Descriptions.Item label="计量单位">{selectedMaterial.unit || '-'}</Descriptions.Item>
                <Descriptions.Item label="基础单位">{selectedMaterial.base_unit || '-'}</Descriptions.Item>
                <Descriptions.Item label="生产单位">{selectedMaterial.production_unit || '-'}</Descriptions.Item>
                <Descriptions.Item label="转换系数">{selectedMaterial.conversion_factor || '-'}</Descriptions.Item>
                <Descriptions.Item label="品牌/厂家">{selectedMaterial.brand || '-'}</Descriptions.Item>
                <Descriptions.Item label="状态">{selectedMaterial.status || '-'}</Descriptions.Item>
                <Descriptions.Item label="版本">{selectedMaterial.version || '-'}</Descriptions.Item>
              </Descriptions>
              
              <div style={{ marginTop: 16 }}>
                <h4 style={{ marginBottom: 12 }}>PCB专有工程属性</h4>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="层数">{selectedMaterial.layer_count || '-'}</Descriptions.Item>
                  <Descriptions.Item label="板厚(mm)">{selectedMaterial.board_thickness || '-'}</Descriptions.Item>
                  <Descriptions.Item label="厚度公差">{selectedMaterial.thickness_tolerance || '-'}</Descriptions.Item>
                  <Descriptions.Item label="铜厚">{selectedMaterial.copper_weight || '-'}</Descriptions.Item>
                  <Descriptions.Item label="板材等级">{selectedMaterial.material_grade || '-'}</Descriptions.Item>
                  <Descriptions.Item label="表面处理">{selectedMaterial.surface_finish || '-'}</Descriptions.Item>
                  <Descriptions.Item label="阻焊颜色">{selectedMaterial.solder_mask_color || '-'}</Descriptions.Item>
                  <Descriptions.Item label="字符颜色">{selectedMaterial.silkscreen_color || '-'}</Descriptions.Item>
                  <Descriptions.Item label="阻抗控制">{selectedMaterial.impedance_control ? '是' : '否'}</Descriptions.Item>
                  <Descriptions.Item label="最小线距(mm)">{selectedMaterial.min_line_space || '-'}</Descriptions.Item>
                  <Descriptions.Item label="最小孔径(mm)">{selectedMaterial.min_hole_size || '-'}</Descriptions.Item>
                </Descriptions>
              </div>

              <div style={{ marginTop: 16 }}>
                <h4 style={{ marginBottom: 12 }}>尺寸信息</h4>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="单位长度(mm)">{selectedMaterial.unit_length || '-'}</Descriptions.Item>
                  <Descriptions.Item label="单位宽度(mm)">{selectedMaterial.unit_width || '-'}</Descriptions.Item>
                  <Descriptions.Item label="大板长度(mm)">{selectedMaterial.panel_length || '-'}</Descriptions.Item>
                  <Descriptions.Item label="大板宽度(mm)">{selectedMaterial.panel_width || '-'}</Descriptions.Item>
                  <Descriptions.Item label="每板单位数">{selectedMaterial.units_per_panel || '-'}</Descriptions.Item>
                </Descriptions>
              </div>

              <div style={{ marginTop: 16 }}>
                <h4 style={{ marginBottom: 12 }}>供应链计划</h4>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="采购类型">{selectedMaterial.procurement_type || '-'}</Descriptions.Item>
                  <Descriptions.Item label="MRP控制器">{selectedMaterial.mrp_controller || '-'}</Descriptions.Item>
                  <Descriptions.Item label="提前期(天)">{selectedMaterial.lead_time_days || '-'}</Descriptions.Item>
                  <Descriptions.Item label="安全库存">{selectedMaterial.safety_stock || '-'}</Descriptions.Item>
                  <Descriptions.Item label="最大批量">{selectedMaterial.max_lot_size || '-'}</Descriptions.Item>
                  <Descriptions.Item label="当前库存">{selectedMaterial.current_stock || '-'}</Descriptions.Item>
                </Descriptions>
              </div>

              {selectedMaterial.description && (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ marginBottom: 12 }}>描述</h4>
                  <div style={{ padding: '8px', background: 'hsl(var(--surface-hover))', borderRadius: '4px' }}>
                    {selectedMaterial.description}
                  </div>
                </div>
              )}
            </Card>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="is_default"
                label="默认映射"
                valuePropName="checked"
              >
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="effective_date"
                label="生效日期"
                rules={[{ required: true, message: '请选择生效日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="expiry_date"
                label="失效日期（可选）"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/eng/factory-product-mappings')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default FactoryProductMappingForm

