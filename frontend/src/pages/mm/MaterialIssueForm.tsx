import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, InputNumber } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select

interface MaterialIssueFormData {
  production_order_number: string
  material_code: string
  quantity: number
  unit: string
  warehouse?: string
  batch_number?: string
  purchase_order_number?: string
  remarks?: string
}

const MaterialIssueForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [materials, setMaterials] = useState<any[]>([])
  const [productionOrders, setProductionOrders] = useState<any[]>([])
  const [selectedMaterial, setSelectedMaterial] = useState<any>(null)
  const [loadingProductionOrders, setLoadingProductionOrders] = useState(false)

  useEffect(() => {
    fetchMaterials()
    fetchProductionOrders()
  }, [])

  const fetchMaterials = async () => {
    try {
      const response = await api.get('/mm/materials')
      setMaterials(response.data || [])
    } catch (error: any) {
      console.error('获取物料列表失败:', error)
      message.error('获取物料列表失败')
    }
  }

  const fetchProductionOrders = async () => {
    setLoadingProductionOrders(true)
    try {
      // 获取所有生产订单，过滤掉已完成和已关闭的订单
      const response = await api.get('/pp/production-orders', { params: { limit: 1000 } })
      const allOrders = response.data || []
      // 过滤掉已完成和已关闭的订单
      const availableOrders = allOrders.filter((order: any) => 
        order.status !== 'COMPLETED' && order.status !== 'CLOSED'
      )
      setProductionOrders(availableOrders)
      if (availableOrders.length === 0) {
        console.warn('暂无可用的生产订单')
        message.warning('暂无可用的生产订单（已完成和已关闭的订单不能创建领料单），请先创建或选择其他状态的生产订单')
      } else {
        // 统计各状态的订单数量
        const statusCounts = availableOrders.reduce((acc: any, order: any) => {
          acc[order.status] = (acc[order.status] || 0) + 1
          return acc
        }, {})
        console.log('可用生产订单状态统计:', statusCounts)
      }
    } catch (error: any) {
      console.error('获取生产订单列表失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '获取生产订单列表失败'
      message.error(errorMsg)
      setProductionOrders([])
    } finally {
      setLoadingProductionOrders(false)
    }
  }

  const handleProductionOrderChange = async (orderNumber: string) => {
    if (!orderNumber) {
      setSelectedMaterial(null)
      form.setFieldsValue({ material_code: undefined, unit: undefined })
      return
    }

    // 获取生产订单详情
    try {
      const response = await api.get(`/pp/production-orders/${orderNumber}`)
      const order = response.data
      
      if (order && order.material_code) {
        // 根据物料编码查找物料信息
        const material = materials.find(m => m.material_code === order.material_code)
        if (material) {
          setSelectedMaterial(material)
          form.setFieldsValue({ 
            material_code: order.material_code,
            unit: material.unit  // 使用物料的单位，因为库存是以物料单位存储的
          })
        } else {
          // 如果物料列表中找不到，尝试从API获取
          try {
            const materialResponse = await api.get(`/mm/materials/${order.material_code}`)
            const fetchedMaterial = materialResponse.data
            setSelectedMaterial(fetchedMaterial)
            form.setFieldsValue({ 
              material_code: order.material_code,
              unit: fetchedMaterial.unit  // 使用物料的单位
            })
          } catch (error) {
            console.error('获取物料信息失败:', error)
            message.warning(`生产订单的物料 ${order.material_code} 不存在，请手动选择物料`)
          }
        }
      }
    } catch (error: any) {
      console.error('获取生产订单详情失败:', error)
      message.error('获取生产订单详情失败，请手动选择物料')
    }
  }

  const handleMaterialChange = (materialCode: string) => {
    const material = materials.find(m => m.material_code === materialCode)
    setSelectedMaterial(material)
    if (material) {
      form.setFieldsValue({ unit: material.unit })
    }
  }

  const onFinish = async (values: MaterialIssueFormData) => {
    setLoading(true)
    try {
      // 验证库存
      if (selectedMaterial && values.quantity > selectedMaterial.current_stock) {
        message.error(`库存不足: 当前库存 ${selectedMaterial.current_stock} ${selectedMaterial.unit}，需要 ${values.quantity} ${values.unit}`)
        setLoading(false)
        return
      }

      await api.post('/mm/material-issues', values)
      message.success('领料单创建成功')
      navigate('/mm/material-issues')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      console.error('创建领料单失败:', error)
      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="新建生产领料单">
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="production_order_number"
                label="生产订单号"
                rules={[{ required: true, message: '请选择生产订单' }]}
                extra={productionOrders.length > 0 ? "提示：建议选择状态为\"已下达\"或\"生产中\"的生产订单进行领料" : undefined}
              >
                <Select
                  placeholder={loadingProductionOrders ? "加载中..." : (productionOrders.length === 0 ? "暂无生产订单" : "请选择生产订单")}
                  showSearch
                  allowClear
                  loading={loadingProductionOrders}
                  onChange={handleProductionOrderChange}
                  filterOption={(input, option) => {
                    const text = (option?.label as string) || ''
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                  notFoundContent={loadingProductionOrders ? "加载中..." : (productionOrders.length === 0 ? "暂无生产订单，请先创建生产订单" : "未找到匹配的生产订单")}
                  disabled={loadingProductionOrders || productionOrders.length === 0}
                  optionLabelProp="label"
                >
                  {productionOrders.map(order => {
                    const statusText: { [key: string]: string } = {
                      'DRAFT': '草稿',
                      'RELEASED': '已下达',
                      'IN_PRODUCTION': '生产中',
                      'COMPLETED': '已完成',
                      'CLOSED': '已关闭',
                      'CANCELLED': '已取消'
                    }
                    const statusLabel = statusText[order.status] || order.status
                    const displayText = `${order.order_number} - ${order.material_code} - 数量: ${order.quantity} (${statusLabel})`
                    return (
                      <Option key={order.order_number} value={order.order_number} label={displayText}>
                        {displayText}
                      </Option>
                    )
                  })}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="material_code"
                label="物料"
                rules={[{ required: true, message: '请选择物料' }]}
              >
                <Select
                  placeholder="选择生产订单后将自动填充，也可手动选择"
                  showSearch
                  onChange={handleMaterialChange}
                  filterOption={(input, option) => {
                    const text = (option?.label as string) || ''
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                  optionLabelProp="label"
                >
                  {materials.map(material => {
                    const displayText = `${material.material_name} (${material.material_code})`
                    return (
                      <Option key={material.material_code} value={material.material_code} label={displayText}>
                        {displayText}
                      </Option>
                    )
                  })}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {selectedMaterial && (
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 16, padding: 12, background: 'hsl(var(--surface-hover))', borderRadius: 4 }}>
                  <div><strong>当前库存：</strong>{selectedMaterial.current_stock || 0} {selectedMaterial.unit}</div>
                  <div><strong>安全库存：</strong>{selectedMaterial.safety_stock || 0} {selectedMaterial.unit}</div>
                  {selectedMaterial.current_stock !== undefined && selectedMaterial.safety_stock !== undefined && 
                   selectedMaterial.current_stock < selectedMaterial.safety_stock && (
                    <div style={{ marginTop: 8, color: 'hsl(var(--destructive))', fontSize: '12px' }}>
                      ⚠️ 当前库存低于安全库存
                    </div>
                  )}
                </div>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="quantity"
                label="领料数量"
                rules={[
                  { required: true, message: '请输入领料数量' },
                  {
                    validator: (_, value) => {
                      if (selectedMaterial && value > selectedMaterial.current_stock) {
                        return Promise.reject(new Error('领料数量不能超过当前库存'))
                      }
                      return Promise.resolve()
                    }
                  }
                ]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入领料数量" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="unit"
                label="单位"
                rules={[{ required: true, message: '请输入单位' }]}
              >
                <Input placeholder="单位" disabled />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="warehouse"
                label="仓库"
              >
                <Input placeholder="请输入仓库" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="batch_number"
                label="原料批次号"
                tooltip="填写后可在追溯页沿「领料 → 原料批次 → 采购单 → 供应商」反查来源"
              >
                <Input placeholder="如 BATCH-RM-FR4-150-20261120" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="purchase_order_number"
                label="来源采购单号"
                tooltip="用于把批次关联到供应商；留空则追溯仅展示批次号"
              >
                <Input placeholder="如 PUR-20261120-0001" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="remarks"
            label="备注"
          >
            <Input.TextArea rows={3} placeholder="请输入备注信息" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                创建
              </Button>
              <Button onClick={() => navigate('/mm/material-issues')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default MaterialIssueForm

