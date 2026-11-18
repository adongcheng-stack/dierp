import { Form, Input, Select, Card, Row, Col, App as AntdApp, DatePicker, InputNumber, Switch } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'
import CustomerSelect from '../../components/common/CustomerSelect'
import FormButtons from '../../components/common/FormButtons'
import { handleApiError } from '../../utils/errorHandler'

const { Option } = Select
const { TextArea } = Input

interface SalesOrderFormData {
  quotation_number?: string
  customer_id: string
  product_number: string
  quantity: number
  unit_price: number
  delivery_date: string
  is_return_order: boolean
  remarks?: string
  // 新增字段
  material_code?: string
  production_version_id?: string
  sales_unit?: string
  production_quantity?: number
  production_unit?: string
  conversion_factor?: number
}

const SalesOrderForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [quotations, setQuotations] = useState<any[]>([])
  const [loadingQuotations, setLoadingQuotations] = useState(false)
  const [fromQuotation, setFromQuotation] = useState(false)
  const [isReturnOrder, setIsReturnOrder] = useState(false)
  const [mappingInfo, setMappingInfo] = useState<any>(null) // 存储自动映射的信息
  const [loadingMapping, setLoadingMapping] = useState(false)
  const isEdit = !!id
  const isInitialized = useRef(false) // 标记是否已初始化

  // 使用 Form.useWatch 监听返单字段变化
  const watchedIsReturnOrder = Form.useWatch('is_return_order', form) || false

  useEffect(() => {
    fetchQuotations(false) // 初始加载时，默认按新单获取
    if (isEdit) {
      fetchSalesOrder()
    } else {
      isInitialized.current = true
    }
  }, [id])

  // 当表单中的返单字段值变化时，更新状态并重新获取报价单
  useEffect(() => {
    // 只在已初始化且值真正变化时处理（避免初始化时的重复调用）
    if (isInitialized.current && watchedIsReturnOrder !== isReturnOrder && watchedIsReturnOrder !== undefined) {
      console.log('检测到返单状态变化:', watchedIsReturnOrder, '当前状态:', isReturnOrder)
      setIsReturnOrder(watchedIsReturnOrder)
      // 清空已选择的报价单（使用 setTimeout 避免在渲染过程中更新表单）
      setTimeout(() => {
        form.setFieldsValue({ quotation_number: undefined })
      }, 0)
      setFromQuotation(false)
      // 根据返单状态重新获取报价单列表
      fetchQuotations(watchedIsReturnOrder)
    }
  }, [watchedIsReturnOrder])



  const fetchQuotations = async (isReturn: boolean = false) => {
    setLoadingQuotations(true)
    try {
      // 如果是返单，只显示已关联的报价单
      // 如果是新单，只显示已批准的报价单
      const params: any = {
        is_return_order: isReturn
      }
      
      const response = await api.get('/sd/quotations', { params })
      const quotations = response.data || []
      setQuotations(quotations)
      if (quotations.length === 0) {
        console.log(isReturn 
          ? '暂无可用的报价单（需要状态为已关联）'
          : '暂无可用的报价单（需要状态为已批准）'
        )
      }
    } catch (error: any) {
      console.error('获取报价单列表失败:', error)
      handleApiError(error, message)
    } finally {
      setLoadingQuotations(false)
    }
  }

  const fetchSalesOrder = async () => {
    try {
      const response = await api.get(`/sd/sales-orders/${id}`)
      const data = response.data
      const isReturn = data.is_return_order || false
      setIsReturnOrder(isReturn)
      form.setFieldsValue({
        ...data,
        delivery_date: data.delivery_date ? dayjs(data.delivery_date) : undefined
      })
      if (data.quotation_number) {
        setFromQuotation(true)
      }
      // 如果已有物料编码，显示映射信息
      if (data.material_code) {
        setMappingInfo({
          material_code: data.material_code,
          production_version_id: data.production_version_id,
          is_default: true,
        })
      }
      // 根据返单状态重新获取报价单列表
      fetchQuotations(isReturn)
      isInitialized.current = true // 标记已初始化
    } catch (error) {
      message.error('获取销售订单信息失败')
      navigate('/sd/sales-orders')
    }
  }

  const handleQuotationChange = (quotationNumber: string) => {
    const quotation = quotations.find(q => q.quotation_number === quotationNumber)
    if (quotation) {
      form.setFieldsValue({
        customer_id: quotation.customer_id,
        product_number: quotation.product_number,
        quantity: quotation.quantity,
        unit_price: quotation.unit_price
      })
      setFromQuotation(true)
      // 尝试查找本厂编号映射
      if (quotation.customer_id && quotation.product_number) {
        checkMapping(quotation.customer_id, quotation.product_number)
      }
    }
  }

  const handleProductNumberChange = async (productNumber: string) => {
    const customerId = form.getFieldValue('customer_id')
    if (customerId && productNumber) {
      await checkMapping(customerId, productNumber)
    } else {
      setMappingInfo(null)
    }
  }

  const checkMapping = async (customerId: string, productNumber: string) => {
    if (!customerId || !productNumber) {
      setMappingInfo(null)
      return
    }
    
    setLoadingMapping(true)
    try {
      const response = await api.get(`/sd/factory-product-mappings/${customerId}/${productNumber}`)
      setMappingInfo(response.data)
      // 自动填充物料和生产版本信息
      if (response.data) {
        form.setFieldsValue({
          material_code: response.data.material_code,
          production_version_id: response.data.production_version_id
        })
        message.success('已找到本厂编号映射，物料和生产版本信息已自动填充')
      }
    } catch (error: any) {
      // 如果找不到映射，静默处理（不显示错误消息）
      if (error.response?.status === 404) {
        setMappingInfo(null)
        // 404 是正常情况，不需要显示错误
      } else {
        console.error('查找映射失败:', error)
        // 其他错误才显示
        message.warning('查找本厂编号映射失败，请手动选择物料和生产版本')
      }
    } finally {
      setLoadingMapping(false)
    }
  }

  // 监听客户和产品编号变化，自动查找映射
  const watchedCustomerId = Form.useWatch('customer_id', form)
  const watchedProductNumber = Form.useWatch('product_number', form)

  useEffect(() => {
    if (watchedCustomerId && watchedProductNumber && !fromQuotation) {
      checkMapping(watchedCustomerId, watchedProductNumber)
    }
  }, [watchedCustomerId, watchedProductNumber])

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      // 检查是否有物料编码（必填）
      const materialCode = values.material_code || mappingInfo?.material_code
      if (!materialCode) {
        message.error('请先选择物料或创建本厂编号映射')
        setLoading(false)
        return
      }
      
      const formData: SalesOrderFormData = {
        quotation_number: values.quotation_number || undefined,
        customer_id: values.customer_id,
        product_number: values.product_number,
        quantity: values.quantity,
        unit_price: values.unit_price,
        delivery_date: values.delivery_date ? values.delivery_date.toISOString() : new Date().toISOString(),
        is_return_order: values.is_return_order || false,
        remarks: values.remarks,
        // 传递物料和生产版本信息
        material_code: materialCode,
        production_version_id: values.production_version_id || mappingInfo?.production_version_id || undefined,
        sales_unit: values.sales_unit || mappingInfo?.sales_unit || undefined,
        production_quantity: values.production_quantity || undefined,
        production_unit: values.production_unit || mappingInfo?.production_unit || undefined,
        conversion_factor: values.conversion_factor || mappingInfo?.conversion_factor || undefined
      }
      
      if (isEdit) {
        // 后端使用 order_number 作为路径参数
        await api.put(`/sd/sales-orders/${id}`, formData)
        message.success('销售订单更新成功')
      } else {
        await api.post('/sd/sales-orders', formData)
        message.success('销售订单创建成功')
      }
      navigate('/sd/sales-orders')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      message.error(errorMsg)
      console.error('销售订单操作失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑销售订单' : '新建销售订单'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            is_return_order: false
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="quotation_number"
                label="报价单号（可选，从报价单转单）"
              >
                <Select 
                  placeholder={isReturnOrder ? "请选择报价单（可选，返单只显示已关联的报价单）" : "请选择报价单（可选，新单只显示已批准的报价单）"} 
                  allowClear
                  loading={loadingQuotations}
                  onChange={handleQuotationChange}
                  showSearch
                  notFoundContent={
                    loadingQuotations 
                      ? '加载中...' 
                      : quotations.length === 0 
                        ? (isReturnOrder 
                          ? '暂无可用的报价单（需要状态为已关联）'
                          : '暂无可用的报价单（需要状态为已批准）')
                        : '未找到'
                  }
                  filterOption={(input, option) => {
                    const text = String(option?.children ?? '')
                    return text.toLowerCase().includes(input.toLowerCase())
                  }}
                >
                  {quotations.map(quotation => {
                    const statusText: { [key: string]: string } = {
                      'APPROVED': '已批准',
                      'LINKED': '已关联',
                      'CUSTOMER_CONFIRMED': '客户已确认'
                    }
                    const statusLabel = statusText[quotation.status] || quotation.status
                    const displayText = `${quotation.quotation_number} - ${quotation.customer_id} - ${quotation.product_number} (${statusLabel})`
                    return (
                      <Option 
                        key={quotation.quotation_number} 
                        value={quotation.quotation_number}
                      >
                        {displayText}
                      </Option>
                    )
                  })}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="is_return_order"
                label="是否返单"
                valuePropName="checked"
              >
                <Switch 
                  checkedChildren="是" 
                  unCheckedChildren="否"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customer_id"
                label="客户"
                rules={[{ required: true, message: '请选择客户' }]}
              >
                <CustomerSelect disabled={fromQuotation} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="product_number"
                label="产品编号（本厂编号）"
                rules={[{ required: true, message: '请输入产品编号' }]}
                extra={loadingMapping ? '正在查找映射...' : mappingInfo ? `已找到映射：物料 ${mappingInfo.material_code}${mappingInfo.production_version_id ? `，生产版本 ${mappingInfo.production_version_id}` : ''}` : '输入本厂编号后，系统会自动查找对应的物料编码和生产版本'}
              >
                <Input 
                  placeholder="如：HS1004ENIGAB01" 
                  disabled={fromQuotation}
                  onChange={(e) => {
                    if (!fromQuotation) {
                      handleProductNumberChange(e.target.value)
                    }
                  }}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 显示自动映射的信息 */}
          {mappingInfo && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={24}>
                <Card size="small" title="自动映射信息" style={{ background: 'hsl(var(--brand-soft))', borderColor: 'hsl(var(--brand) / 0.45)' }}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <div><strong>物料编码：</strong>{mappingInfo.material_code}</div>
                    </Col>
                    <Col span={6}>
                      <div><strong>生产版本：</strong>{mappingInfo.production_version_id || '未指定'}</div>
                    </Col>
                    <Col span={6}>
                      <div><strong>默认映射：</strong>{mappingInfo.is_default ? '是' : '否'}</div>
                    </Col>
                    <Col span={6}>
                      <div><strong>生效日期：</strong>{mappingInfo.effective_date ? new Date(mappingInfo.effective_date).toLocaleDateString('zh-CN') : '-'}</div>
                    </Col>
                  </Row>
                  <div style={{ marginTop: 8, fontSize: '12px', color: 'hsl(var(--ink-soft))' }}>
                    提示：创建销售订单时，系统会自动使用这些信息填充物料编码和生产版本
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
                <InputNumber 
                  min={0} 
                  style={{ width: '100%' }} 
                  placeholder="请输入数量" 
                  disabled={fromQuotation && !isReturnOrder} 
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="unit_price"
                label="单价"
                rules={[{ required: true, message: '请输入单价' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入单价" disabled={fromQuotation} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="delivery_date"
                label="交货日期"
                rules={[{ required: true, message: '请选择交货日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="remarks"
            label="备注"
          >
            <TextArea rows={4} placeholder="请输入备注信息" />
          </Form.Item>

          <Form.Item>
            <FormButtons
              loading={loading}
              onSave={() => form.submit()}
              saveText={isEdit ? '更新' : '创建'}
              cancelPath="/sd/sales-orders"
            />
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default SalesOrderForm

