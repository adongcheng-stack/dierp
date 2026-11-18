import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker, InputNumber } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'

const { Option } = Select
const { TextArea } = Input

const ProductionOrderForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [salesOrders, setSalesOrders] = useState<any[]>([])
  const [currentSalesOrder, setCurrentSalesOrder] = useState<any>(null)
  const [selectedSalesOrder, setSelectedSalesOrder] = useState<any>(null)
  const [productionVersions, setProductionVersions] = useState<any[]>([])
  const [selectedProductionVersion, setSelectedProductionVersion] = useState<any>(null)
  const [loadingSalesOrders, setLoadingSalesOrders] = useState(false)
  const [loadingProductionVersions, setLoadingProductionVersions] = useState(false)
  const isEdit = !!id

  useEffect(() => {
    fetchSalesOrders()
    fetchProductionVersions()
  }, [])

  useEffect(() => {
    if (isEdit && productionVersions.length > 0) {
      fetchProductionOrder()
    }
  }, [id, productionVersions.length])

  const fetchSalesOrders = async () => {
    setLoadingSalesOrders(true)
    try {
      // 只获取已评审完成的销售订单（APPROVED）
      const response = await api.get('/sd/sales-orders', {
        params: { status: 'APPROVED', limit: 1000 }
      })
      const approvedOrders = response.data || []

      // 编辑模式：若当前订单不在筛选列表中，补充进去，避免下拉缺失
      if (isEdit && currentSalesOrder) {
        const exists = approvedOrders.some((o: any) => o.order_number === currentSalesOrder.order_number)
        if (!exists) {
          approvedOrders.push(currentSalesOrder)
        }
      }

      setSalesOrders(approvedOrders)
      if (approvedOrders.length === 0) {
        console.warn('暂无已评审完成的销售订单')
        message.warning('暂无已评审完成的销售订单，请先完成销售订单评审')
      }
    } catch (error: any) {
      console.error('获取销售订单列表失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '获取销售订单列表失败'
      message.error(errorMsg)
      setSalesOrders([])
    } finally {
      setLoadingSalesOrders(false)
    }
  }

  const fetchProductionVersions = async () => {
    setLoadingProductionVersions(true)
    try {
      // 只获取已发布或激活的生产版本
      const response = await api.get('/eng/production-versions', {
        params: { limit: 1000 }
      })
      const allVersions = response.data || []
      // 过滤出已发布或激活的生产版本
      const availableVersions = allVersions.filter((pv: any) => 
        pv.status === 'RELEASED' || pv.status === 'ACTIVE'
      )
      setProductionVersions(availableVersions)
      if (availableVersions.length === 0) {
        message.warning('暂无可用的生产版本（需要已发布或激活状态），请先创建并发布生产版本')
      }
    } catch (error: any) {
      console.error('获取生产版本列表失败:', error)
      message.error('获取生产版本列表失败')
      setProductionVersions([])
    } finally {
      setLoadingProductionVersions(false)
    }
  }

  const handleSalesOrderChange = async (salesOrderNumber: string) => {
    const order = salesOrders.find((o: any) => o.order_number === salesOrderNumber)
    setSelectedSalesOrder(order)
    if (order) {
      // 如果销售订单有生产版本，自动选择
      if (order.production_version_id) {
        const pv = productionVersions.find((v: any) => v.production_version_id === order.production_version_id)
        if (pv) {
          form.setFieldsValue({
            production_version_id: order.production_version_id,
            material_code: order.material_code || pv.material_code
          })
          setSelectedProductionVersion(pv)
          message.success(`已选择销售订单，生产版本和物料编码已自动填充`)
        }
      }
    }
  }

  const handleProductionVersionChange = async (productionVersionId: string) => {
    const pv = productionVersions.find((v: any) => v.production_version_id === productionVersionId)
    setSelectedProductionVersion(pv)
    if (pv) {
      // 自动填充物料编码
      form.setFieldsValue({
        material_code: pv.material_code
      })
      message.success(`已选择生产版本，物料编码已自动填充: ${pv.material_code}`)
    }
  }

  const fetchProductionOrder = async () => {
    if (!id) {
      console.error('缺少订单ID')
      return
    }
    
    try {
      const response = await api.get(`/pp/production-orders/${id}`)
      const data = response.data
      
      if (!data) {
        throw new Error('生产订单数据为空')
      }
      
      // 设置当前销售订单
      if (data.sales_order_number) {
        setCurrentSalesOrder({ order_number: data.sales_order_number })
        
        // 获取销售订单信息以显示单位转换
        try {
          const salesOrderResponse = await api.get(`/sd/sales-orders/${data.sales_order_number}`)
          setSelectedSalesOrder(salesOrderResponse.data)
        } catch (error) {
          console.error('获取销售订单信息失败:', error)
          // 不阻止继续执行
        }
      }
      
      // 安全地处理日期字段
      const formValues: any = { ...data }
      if (data.planned_start_date) {
        try {
          formValues.planned_start_date = dayjs(data.planned_start_date)
        } catch (e) {
          console.warn('日期解析失败 (planned_start_date):', data.planned_start_date, e)
          formValues.planned_start_date = undefined
        }
      } else {
        formValues.planned_start_date = undefined
      }
      
      if (data.planned_finish_date) {
        try {
          formValues.planned_finish_date = dayjs(data.planned_finish_date)
        } catch (e) {
          console.warn('日期解析失败 (planned_finish_date):', data.planned_finish_date, e)
          formValues.planned_finish_date = undefined
        }
      } else {
        formValues.planned_finish_date = undefined
      }
      
      form.setFieldsValue(formValues)
      
      // 设置选中的生产版本（确保 productionVersions 已加载）
      if (data.production_version_id && productionVersions.length > 0) {
        const pv = productionVersions.find((v: any) => v.production_version_id === data.production_version_id)
        if (pv) {
          setSelectedProductionVersion(pv)
        } else {
          console.warn(`未找到生产版本: ${data.production_version_id}`)
        }
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || '获取生产订单信息失败'
      message.error(errorMsg)
      console.error('获取生产订单信息失败:', error)
      // 延迟导航，让用户看到错误消息
      setTimeout(() => {
        navigate('/pp/production-orders')
      }, 2000)
    }
  }

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      const formData = {
        ...values,
        planned_start_date: values.planned_start_date ? values.planned_start_date.toISOString() : undefined,
        planned_finish_date: values.planned_finish_date ? values.planned_finish_date.toISOString() : undefined
      }
      if (isEdit) {
        await api.put(`/pp/production-orders/${id}`, formData)
        message.success('生产订单更新成功')
      } else {
        await api.post('/pp/production-orders', formData)
        message.success('生产订单创建成功')
      }
      navigate('/pp/production-orders')
    } catch (error: any) {
      console.error('生产订单操作失败:', error)
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || '操作失败'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑工单' : '新建工单'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            unit: 'PNL'
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="sales_order_number"
                label="销售订单号"
                rules={[{ required: true, message: '请选择销售订单' }]}
                extra="选择销售订单后，如果订单有生产版本，会自动填充"
              >
                <Select 
                  placeholder={loadingSalesOrders ? "加载中..." : (salesOrders.length === 0 ? "暂无已评审完成的销售订单" : "请选择已评审完成的销售订单")} 
                  showSearch
                  allowClear
                  loading={loadingSalesOrders}
                  onChange={handleSalesOrderChange}
                  filterOption={(input, option) => {
                    const text = String(option?.children ?? '')
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                  notFoundContent={loadingSalesOrders ? "加载中..." : (salesOrders.length === 0 ? "暂无已评审完成的销售订单，请先完成销售订单评审" : "未找到匹配的销售订单")}
                  disabled={loadingSalesOrders || salesOrders.length === 0}
                >
                  {salesOrders.map(order => (
                    <Option key={order.order_number} value={order.order_number}>
                      {order.order_number} - {order.product_number} - {order.customer_id} ({order.status})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="production_version_id"
                label="生产版本"
                rules={[{ required: true, message: '请选择生产版本' }]}
                extra="选择生产版本后会自动填充物料编码"
              >
                <Select
                  placeholder={loadingProductionVersions ? "加载中..." : (productionVersions.length === 0 ? "暂无可用生产版本" : "请选择生产版本")}
                  showSearch
                  allowClear
                  loading={loadingProductionVersions}
                  disabled={loadingProductionVersions || productionVersions.length === 0}
                  onChange={handleProductionVersionChange}
                  filterOption={(input, option) => {
                    const text = String(option?.children ?? '')
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                  notFoundContent={loadingProductionVersions ? "加载中..." : (productionVersions.length === 0 ? "暂无可用生产版本（需要已发布或激活状态），请先创建并发布生产版本" : "未找到匹配的生产版本")}
                >
                  {productionVersions.map((pv: any) => (
                    <Option key={pv.production_version_id} value={pv.production_version_id}>
                      {pv.production_version_id} - {pv.material_code} (BOM: {pv.bom_number}, 工艺路线: {pv.routing_id}{pv.mi_number ? `, MI: ${pv.mi_number}` : ''}) - {pv.status === 'RELEASED' ? '已发布' : pv.status === 'ACTIVE' ? '激活' : pv.status}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="material_code"
                label="物料编码（自动填充）"
                extra="由生产版本自动填充，无需手动选择"
              >
                <Input 
                  placeholder="选择生产版本后自动填充" 
                  disabled 
                  value={selectedProductionVersion?.material_code || form.getFieldValue('material_code')}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 显示销售订单的单位转换信息 */}
          {selectedSalesOrder && (selectedSalesOrder.sales_unit || selectedSalesOrder.production_unit || selectedSalesOrder.conversion_factor) && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={24}>
                <Card size="small" title="单位转换信息（来自销售订单）" style={{ background: 'hsl(var(--brand-soft))', borderColor: 'hsl(var(--brand) / 0.45)' }}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <div><strong>销售数量：</strong>{selectedSalesOrder.quantity} {selectedSalesOrder.sales_unit || 'PCS'}</div>
                    </Col>
                    <Col span={6}>
                      <div><strong>生产数量：</strong>{selectedSalesOrder.production_quantity || selectedSalesOrder.quantity} {selectedSalesOrder.production_unit || 'PNL'}</div>
                    </Col>
                    <Col span={6}>
                      <div><strong>转换系数：</strong>{selectedSalesOrder.conversion_factor || 1.0}</div>
                    </Col>
                    <Col span={6}>
                      <div><strong>物料编码：</strong>{selectedSalesOrder.material_code || '-'}</div>
                    </Col>
                  </Row>
                  <div style={{ marginTop: 8, fontSize: '12px', color: 'hsl(var(--ink-soft))' }}>
                    提示：创建生产订单时，系统会自动使用销售订单的单位转换信息
                  </div>
                </Card>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="quantity"
                label="数量"
                rules={[{ required: true, message: '请输入数量' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入数量" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="unit"
                label="单位"
                rules={[{ required: true, message: '请输入单位' }]}
              >
                <Input placeholder="如：PNL" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="lot_number"
                label="LOT卡号"
              >
                <Input placeholder="请输入LOT卡号" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="planned_start_date"
                label="计划开始日期"
              >
                <DatePicker style={{ width: '100%' }} showTime />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="planned_finish_date"
                label="计划完成日期"
              >
                <DatePicker style={{ width: '100%' }} showTime />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="remarks"
            label="备注"
          >
            <TextArea rows={3} placeholder="请输入备注信息" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/pp/production-orders')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default ProductionOrderForm

