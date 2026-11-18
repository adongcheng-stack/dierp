import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, InputNumber } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select
const { TextArea } = Input

interface OperationReportFormData {
  production_order_number: string
  lot_number?: string
  routing_operation_id?: number
  work_center_id: string
  operation_no: string
  operation_name?: string
  reported_quantity: number
  good_quantity?: number
  scrap_quantity: number
  setup_time: number
  machine_time: number
  labor_time: number
  remarks?: string
}

const OperationReportForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [productionOrders, setProductionOrders] = useState<any[]>([])
  const [workCenters, setWorkCenters] = useState<any[]>([])
  const [selectedOrder, setSelectedOrder] = useState<any>(null)
  const [operations, setOperations] = useState<any[]>([])
  const [loadingProductionOrders, setLoadingProductionOrders] = useState(false)

  useEffect(() => {
    fetchProductionOrders()
    fetchWorkCenters()
  }, [])

  const fetchProductionOrders = async () => {
    setLoadingProductionOrders(true)
    try {
      // 只获取生产中的订单（IN_PRODUCTION），只有生产中的订单才能报工
      const response = await api.get('/pp/production-orders')
      const allOrders = response.data || []
      // 只显示生产中的订单
      const availableOrders = allOrders.filter((order: any) => 
        order.status === 'IN_PRODUCTION'
      )
      setProductionOrders(availableOrders)
      if (availableOrders.length === 0) {
        console.warn('暂无可报工的生产订单')
        message.warning('暂无可报工的生产订单（只有生产中的订单才能进行工序报工），请先将生产订单状态设置为生产中')
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

  const fetchWorkCenters = async () => {
    try {
      const response = await api.get('/pp/work-centers')
      setWorkCenters(response.data || [])
    } catch (error: any) {
      console.error('获取工作中心列表失败:', error)
      message.error('获取工作中心列表失败')
      setWorkCenters([])
    }
  }

  const handleOrderChange = async (orderNumber: string) => {
    const order = productionOrders.find(o => o.order_number === orderNumber)
    setSelectedOrder(order)
    if (order) {
      // 自动填充LOT卡号（优先从生产订单的lot_number字段获取）
      if (order.lot_number) {
        form.setFieldsValue({
          lot_number: order.lot_number
        })
        console.log('从生产订单获取LOT卡号:', order.lot_number)
      } else {
        // 如果生产订单没有lot_number，尝试从LOT卡API获取
        try {
          const lotCardResponse = await api.get(`/pp/lot-cards/${orderNumber}`)
          if (lotCardResponse.data && lotCardResponse.data.lot_number) {
            form.setFieldsValue({
              lot_number: lotCardResponse.data.lot_number
            })
            console.log('从LOT卡API获取LOT卡号:', lotCardResponse.data.lot_number)
          } else {
            message.warning('该生产订单没有关联的LOT卡，请先创建生产订单以自动生成LOT卡')
            form.setFieldsValue({
              lot_number: undefined
            })
          }
        } catch (error: any) {
          console.error('获取LOT卡失败:', error)
          const errorMsg = error.response?.data?.detail || error.message || '获取LOT卡失败'
          message.error(`获取LOT卡失败: ${errorMsg}，请确认该生产订单已关联LOT卡`)
          form.setFieldsValue({
            lot_number: undefined
          })
        }
      }
      
      // 获取该订单的工艺路线工序
      try {
        const response = await api.get(`/pp/production-orders/${orderNumber}/operations`)
        const ops = response.data || []
        console.log('获取到的工序列表:', ops, '数量:', ops.length)
        setOperations(ops)
        if (ops.length === 0) {
          message.warning(`该生产订单的物料 ${order.material_code} 暂无工艺路线或工序，请手动填写工序信息，或先为该物料创建工艺路线`)
          // 清空工序相关字段
          form.setFieldsValue({
            routing_operation_id: undefined,
            operation_no: undefined,
            operation_name: undefined,
            work_center_id: undefined
          })
        }
      } catch (error: any) {
        console.error('获取工序列表失败:', error)
        setOperations([])
        const errorMsg = error.response?.data?.detail || error.message || '获取工序列表失败'
        message.warning(`获取工序列表失败: ${errorMsg}，请手动填写工序信息`)
        // 清空工序相关字段
        form.setFieldsValue({
          routing_operation_id: undefined,
          operation_no: undefined,
          operation_name: undefined,
          work_center_id: undefined
        })
      }
    } else {
      setOperations([])
      // 清空所有相关字段
      form.setFieldsValue({
        lot_number: undefined,
        routing_operation_id: undefined,
        operation_no: undefined,
        operation_name: undefined,
        work_center_id: undefined
      })
    }
  }

  const handleOperationChange = (operationId: number | undefined) => {
    if (!operationId) {
      // 清空相关字段
      form.setFieldsValue({
        operation_no: undefined,
        operation_name: undefined,
        work_center_id: undefined
      })
      return
    }
    
    const operation = operations.find(op => op.id === operationId)
    if (operation) {
      form.setFieldsValue({
        operation_no: operation.operation_no,
        operation_name: operation.operation_name,
        work_center_id: operation.work_center_id
      })
      message.success(`已选择工序: ${operation.operation_name}`)
    } else {
      console.warn('未找到选中的工序:', operationId)
    }
  }

  const onFinish = async (values: OperationReportFormData) => {
    setLoading(true)
    try {
      // 确保所有数值字段都有默认值
      const formData = {
        production_order_number: values.production_order_number,
        lot_number: values.lot_number,
        routing_operation_id: values.routing_operation_id,
        work_center_id: values.work_center_id,
        operation_no: values.operation_no,
        operation_name: values.operation_name,
        reported_quantity: values.reported_quantity || 0,
        good_quantity: values.good_quantity,
        scrap_quantity: values.scrap_quantity || 0,
        setup_time: values.setup_time || 0,
        machine_time: values.machine_time || 0,
        labor_time: values.labor_time || 0,
        remarks: values.remarks
      }
      await api.post('/pp/operation-reports', formData)
      message.success('工序报工成功')
      navigate('/pp/operation-reports')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      message.error(errorMsg)
      console.error('工序报工失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="新建工序报工">
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            scrap_quantity: 0,
            setup_time: 0,
            machine_time: 0,
            labor_time: 0
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="production_order_number"
                label="生产订单号"
                rules={[{ required: true, message: '请选择生产订单' }]}
              >
                <Select
                  placeholder={loadingProductionOrders ? "加载中..." : (productionOrders.length === 0 ? "暂无可报工的生产订单" : "请选择生产订单（已排除已完成、已关闭和已取消的订单）")}
                  showSearch
                  allowClear
                  loading={loadingProductionOrders}
                  onChange={(value) => {
                    if (value) {
                      handleOrderChange(value)
                    } else {
                      // 清空时，清空所有相关字段
                      form.setFieldsValue({
                        lot_number: undefined,
                        routing_operation_id: undefined,
                        operation_no: undefined,
                        operation_name: undefined,
                        work_center_id: undefined
                      })
                      setSelectedOrder(null)
                      setOperations([])
                    }
                  }}
                  filterOption={(input, option) => {
                    const text = String(option?.children ?? '')
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                  notFoundContent={loadingProductionOrders ? "加载中..." : (productionOrders.length === 0 ? "暂无可报工的生产订单（已排除已完成、已关闭和已取消的订单），请先创建或下达生产订单" : "未找到匹配的生产订单")}
                  disabled={loadingProductionOrders || productionOrders.length === 0}
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
                    return (
                      <Option key={order.order_number} value={order.order_number}>
                        {order.order_number} - {order.material_code} - 数量: {order.quantity} ({statusLabel})
                      </Option>
                    )
                  })}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="lot_number"
                label="LOT卡号"
                tooltip="选择生产订单后自动填充，不可修改"
                rules={[{ required: true, message: 'LOT卡号不能为空，请先选择生产订单' }]}
              >
                <Input 
                  placeholder="请先选择生产订单，系统将自动填充LOT卡号" 
                  readOnly
                  disabled={true}
                  style={{ backgroundColor: 'hsl(var(--surface-hover))', cursor: 'not-allowed' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="routing_operation_id"
                label="工序（可选，选择后自动填充工序信息）"
                tooltip={operations.length === 0 ? "该生产订单暂无工序信息，请先为该物料创建工艺路线" : "选择工序后会自动填充工序号、工序名称和工作中心"}
              >
                <Select
                  placeholder={operations.length === 0 ? "暂无工序，请手动填写" : "请选择工序"}
                  onChange={handleOperationChange}
                  allowClear
                  showSearch
                  filterOption={(input, option) => {
                    const text = String(option?.children ?? '')
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                  notFoundContent={operations.length === 0 ? "暂无工序，请手动填写工序信息" : "未找到匹配的工序"}
                  disabled={operations.length === 0}
                  style={{ width: '100%' }}
                >
                  {operations.map(op => {
                    console.log('渲染工序选项:', op)
                    return (
                      <Option key={op.id} value={op.id}>
                        {op.operation_no} - {op.operation_name} ({op.work_center_id})
                      </Option>
                    )
                  })}
                </Select>
                {operations.length === 0 && selectedOrder && (
                  <div style={{ marginTop: 4, color: 'hsl(var(--destructive))', fontSize: '12px' }}>
                    ⚠️ 提示：物料 {selectedOrder.material_code} 暂无工艺路线或工序。请先到"工程管理 → 工艺路线"为该物料创建工艺路线并添加工序。
                  </div>
                )}
                {operations.length > 0 && (
                  <div style={{ marginTop: 4, color: 'hsl(var(--chart-success))', fontSize: '12px' }}>
                    ✓ 已加载 {operations.length} 个工序，请选择
                  </div>
                )}
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="work_center_id"
                label="工作中心"
                rules={[{ required: true, message: '请选择工作中心' }]}
              >
                <Select placeholder="请选择工作中心" showSearch>
                  {workCenters.map(wc => (
                    <Option key={wc.work_center_id} value={wc.work_center_id}>
                      {wc.description} ({wc.work_center_id})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="operation_no"
                label="工序号"
                rules={[{ required: true, message: '请输入工序号' }]}
              >
                <Input placeholder="如：0010" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="operation_name"
                label="工序名称"
              >
                <Input placeholder="如：CNC钻孔" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="reported_quantity"
                label="报工数量"
                rules={[{ required: true, message: '请输入报工数量' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入报工数量" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="good_quantity"
                label="良品数量"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入良品数量" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="scrap_quantity"
                label="报废数量"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入报废数量" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="setup_time"
                label="调机时间(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="machine_time"
                label="机器时间(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="labor_time"
                label="人工时间(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
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
                提交报工
              </Button>
              <Button onClick={() => navigate('/pp/operation-reports')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default OperationReportForm

