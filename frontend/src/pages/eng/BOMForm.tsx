import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker, Table, Modal, InputNumber } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import MaterialSelect from '../../components/common/MaterialSelect'
import FormButtons from '../../components/common/FormButtons'
import { handleApiError } from '../../utils/errorHandler'
import useMaterialStore from '../../stores/materialStore'

const { Option } = Select

interface BOMItem {
  line_number?: number
  material_code: string
  quantity: number
  unit: string
  item_category?: string
  scrap_rate?: number
  calculation_formula?: string
  layer_code?: string
  material_type?: string
  process_step?: string
  remarks?: string
}

const BOMForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<BOMItem[]>([])
  const [itemModalVisible, setItemModalVisible] = useState(false)
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null)
  const [itemForm] = Form.useForm()
  const [bomInfo, setBomInfo] = useState<any>(null) // 存储审计追踪信息
  const { materials, setMaterials } = useMaterialStore() // 从 store 获取物料列表
  const isEdit = !!id
  
  // 获取父物料编码，用于排除
  const parentMaterialCode = Form.useWatch('parent_material_code', form)

  // 加载物料列表
  useEffect(() => {
    const loadMaterials = async () => {
      try {
        const response = await api.get('/mm/materials', { params: { limit: 1000 } })
        setMaterials(response.data || [])
      } catch (error) {
        console.error('加载物料列表失败:', error)
      }
    }
    loadMaterials()
  }, [setMaterials])

  useEffect(() => {
    if (isEdit) {
      fetchBOM()
    }
  }, [id])

  const fetchBOM = async () => {
    try {
      const response = await api.get(`/eng/boms/${id}`)
      const data = response.data
      setBomInfo(data) // 保存审计追踪信息
      form.setFieldsValue({
        ...data,
        effective_date: data.effective_date ? dayjs(data.effective_date) : undefined,
        expiry_date: data.expiry_date ? dayjs(data.expiry_date) : undefined
      })
      // BOM详情已经包含了items，直接使用
      setItems(data.items || [])
    } catch (error) {
      message.error('获取BOM信息失败')
      navigate('/eng/boms')
    }
  }

  const handleAddItem = () => {
    itemForm.resetFields()
    setEditingItemIndex(null)
    setItemModalVisible(true)
  }

  const handleEditItem = (index: number) => {
    const item = items[index]
    itemForm.setFieldsValue({
      ...item,
      line_number: item.line_number
    })
    setEditingItemIndex(index)
    setItemModalVisible(true)
  }

  const handleSaveItem = () => {
    itemForm.validateFields().then(values => {
      // 如果没有指定序号，自动生成（10的倍数）
      let lineNumber = values.line_number
      if (!lineNumber) {
        const maxLineNumber = items.length > 0 
          ? Math.max(...items.map(item => item.line_number || 0))
          : 0
        lineNumber = maxLineNumber + 10
      }
      
      // 确保所有字段都有值
      const item: BOMItem = {
        line_number: lineNumber,
        material_code: values.material_code,
        quantity: values.quantity || 0,
        unit: values.unit || '',
        item_category: values.item_category,
        scrap_rate: values.scrap_rate,
        calculation_formula: values.calculation_formula,
        layer_code: values.layer_code,
        material_type: values.material_type,
        process_step: values.process_step,
        remarks: values.remarks
      }
      
      if (editingItemIndex !== null) {
        // 编辑模式：更新现有项
        const newItems = [...items]
        newItems[editingItemIndex] = item
        setItems(newItems.sort((a, b) => (a.line_number || 0) - (b.line_number || 0)))
      } else {
        // 新增模式：添加新项
        const newItems = [...items, item].sort((a, b) => (a.line_number || 0) - (b.line_number || 0))
        setItems(newItems)
      }
      setItemModalVisible(false)
      setEditingItemIndex(null)
      itemForm.resetFields()
    })
  }

  const handleDeleteItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const onFinish = async (values: any) => {
    // 验证是否有物料明细
    if (!items || items.length === 0) {
      message.error('请至少添加一个物料明细')
      return
    }
    
    setLoading(true)
    let formData: any = null
    try {
      // 清理items数据，确保格式正确
      const cleanedItems = items.map(item => ({
        line_number: item.line_number || undefined,
        material_code: item.material_code,
        quantity: Number(item.quantity) || 0,
        unit: item.unit || '',
        item_category: item.item_category || undefined,
        scrap_rate: item.scrap_rate ? Number(item.scrap_rate) : undefined,
        calculation_formula: item.calculation_formula || undefined,
        layer_code: item.layer_code || undefined,
        material_type: item.material_type || undefined,
        process_step: item.process_step || undefined,
        remarks: item.remarks || undefined
      }))
      
      formData = {
        ...values,
        effective_date: values.effective_date ? values.effective_date.toISOString() : undefined,
        expiry_date: values.expiry_date ? values.expiry_date.toISOString() : undefined,
        items: cleanedItems
      }
      
      console.log('发送BOM数据:', JSON.stringify(formData, null, 2))
      
      if (isEdit) {
        await api.put(`/eng/boms/${id}`, formData)
        message.success('BOM更新成功')
      } else {
        await api.post('/eng/boms', formData)
        message.success('BOM创建成功')
      }
      navigate('/eng/boms')
    } catch (error: any) {
      // 显示详细的错误信息
      console.error('BOM操作失败 - 完整错误对象:', error)
      console.error('错误响应数据:', error.response?.data)
      
      if (error.response?.data) {
        const errorData = error.response.data
        
        // 处理 ValidationException 格式的错误（包含 extra_data.errors）
        if (errorData.detail) {
          if (typeof errorData.detail === 'object' && errorData.detail.extra_data?.errors) {
            // 这是 ValidationException 格式
            const errors = errorData.detail.extra_data.errors || []
            const errorMessage = errors.length > 0 
              ? errors.join('\n')
              : errorData.detail.detail || 'BOM验证失败'
            message.error(`BOM验证失败:\n${errorMessage}`)
            console.error('BOM验证错误详情:', errors)
          } else if (Array.isArray(errorData.detail)) {
            // FastAPI Pydantic 验证错误格式
            const errorMessages = errorData.detail.map((err: any) => {
              if (err.loc && err.msg) {
                return `${err.loc.join('.')}: ${err.msg}`
              }
              return err.msg || JSON.stringify(err)
            }).join('\n')
            message.error(`验证失败:\n${errorMessages}`)
            console.error('BOM验证错误:', errorData.detail)
          } else if (typeof errorData.detail === 'string') {
            message.error(errorData.detail)
          } else {
            // 尝试显示 detail 对象中的信息
            const detailStr = JSON.stringify(errorData.detail, null, 2)
            message.error(`验证失败:\n${detailStr}`)
            console.error('BOM验证错误详情:', errorData.detail)
          }
        } else {
          handleApiError(error, message)
        }
      } else {
        handleApiError(error, message)
      }
      
      if (formData) {
        console.error('请求数据:', JSON.stringify(formData, null, 2))
      } else {
        console.error('表单值:', values)
        console.error('物料明细:', items)
      }
    } finally {
      setLoading(false)
    }
  }

  const itemColumns = [
    { 
      title: '序号', 
      key: 'line_number', 
      width: 80,
      render: (_: any, record: BOMItem, index: number) => record.line_number || (index + 1) * 10
    },
    { 
      title: '物料编码', 
      dataIndex: 'material_code', 
      key: 'material_code',
      width: 150
    },
    {
      title: '描述',
      key: 'material_description',
      width: 200,
      render: (_: any, record: BOMItem) => {
        const material = materials.find(m => m.material_code === record.material_code)
        return material?.material_name || material?.description || '-'
      }
    },
    { 
      title: '物料类别', 
      dataIndex: 'item_category', 
      key: 'item_category',
      width: 120,
      render: (text: string) => {
        const categoryMap: { [key: string]: string } = {
          'STOCK_ITEM': '库存物料',
          'SUB_ASSEMBLY': '半成品',
          'CONSUMABLE': '耗材'
        }
        return categoryMap[text] || text
      }
    },
    { 
      title: '数量', 
      dataIndex: 'quantity', 
      key: 'quantity',
      width: 100
    },
    { 
      title: '单位', 
      dataIndex: 'unit', 
      key: 'unit',
      width: 80
    },
    { 
      title: '损耗率(%)', 
      dataIndex: 'scrap_rate', 
      key: 'scrap_rate',
      width: 100,
      render: (text: number) => text ? `${text}%` : '-'
    },
    { 
      title: 'PCB层信息', 
      key: 'pcb_info',
      width: 150,
      render: (_: any, record: BOMItem) => (
        <div>
          {record.layer_code && <div>层码: {record.layer_code}</div>}
          {record.material_type && <div>类型: {record.material_type}</div>}
          {record.process_step && <div>工序: {record.process_step}</div>}
        </div>
      )
    },
    { 
      title: '计算公式', 
      dataIndex: 'calculation_formula', 
      key: 'calculation_formula',
      width: 150
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, __: any, index: number) => (
        <Space>
          <Button
            type="link"
            onClick={() => handleEditItem(index)}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteItem(index)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div>
      <Card title={isEdit ? '编辑BOM' : '新建BOM'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            version: 'A.0',
            bom_type: 'PRODUCTION',
            base_quantity: 1,
            base_uom: 'PNL',
            status: 'NEW'
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="bom_number"
                label="BOM编号"
                rules={[{ required: !isEdit, message: '请输入BOM编号' }]}
              >
                <Input placeholder="如：BOM-PCB-23001" disabled={isEdit} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="parent_material_code"
                label="父项物料"
                rules={[{ required: true, message: '请选择父项物料' }]}
              >
                <MaterialSelect placeholder="请选择父项物料" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="version"
                label="版本"
                rules={[{ required: true, message: '请输入版本' }]}
              >
                <Input placeholder="如：A.0" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="plant_id" label="工厂/产线">
                <Input placeholder="如：SZ-FACTORY-01" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="bom_type" label="BOM类型">
                <Select>
                  <Option value="PRODUCTION">生产BOM</Option>
                  <Option value="ENGINEERING">工程BOM</Option>
                  <Option value="COST">成本BOM</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="status" label="状态">
                <Select>
                  <Option value="NEW">新建</Option>
                  <Option value="REVIEWING">审核中</Option>
                  <Option value="RELEASED">已发布</Option>
                  <Option value="PRODUCING">生产中</Option>
                  <Option value="OBSOLETE">作废</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {isEdit && bomInfo && (
            <Card title="审计追踪" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={6}>
                  <div><strong>创建人：</strong>{bomInfo.created_by || '-'}</div>
                </Col>
                <Col span={6}>
                  <div><strong>创建时间：</strong>{bomInfo.created_at ? dayjs(bomInfo.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
                </Col>
                <Col span={6}>
                  <div><strong>最后修改人：</strong>{bomInfo.updated_by || '-'}</div>
                </Col>
                <Col span={6}>
                  <div><strong>最后修改时间：</strong>{bomInfo.updated_at ? dayjs(bomInfo.updated_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
                </Col>
              </Row>
            </Card>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="base_quantity"
                label="基础数量"
                rules={[{ required: true, message: '请输入基础数量' }]}
              >
                <InputNumber min={0.0001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="base_uom"
                label="基础单位"
                rules={[{ required: true, message: '请选择基础单位' }]}
              >
                <Select>
                  <Option value="PNL">PNL</Option>
                  <Option value="SHT">SHT</Option>
                  <Option value="PCS">PCS</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="description" label="描述">
                <Input placeholder="BOM描述" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="effective_date"
                label="生效日期"
                rules={[{ required: true, message: '请选择生效日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="expiry_date"
                label="失效日期"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Card
            title="BOM物料清单"
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddItem}>
                新增物料
              </Button>
            }
            style={{ marginTop: 16 }}
          >
            <Table
              columns={itemColumns}
              dataSource={items.sort((a, b) => (a.line_number || 0) - (b.line_number || 0))}
              rowKey={(record) => `${record.material_code}-${record.line_number || 'new'}`}
              pagination={false}
              scroll={{ x: 1200 }}
              locale={{ emptyText: '暂无物料，请点击"新增物料"添加' }}
            />
          </Card>

          <Form.Item style={{ marginTop: 24 }}>
            <FormButtons
              loading={loading}
              onSave={() => form.submit()}
              saveText={isEdit ? '更新' : '创建'}
              cancelPath="/eng/boms"
            />
          </Form.Item>
        </Form>
      </Card>

      <Modal
        title={editingItemIndex !== null ? '编辑物料' : '新增物料'}
        open={itemModalVisible}
        onOk={handleSaveItem}
        onCancel={() => {
          setItemModalVisible(false)
          setEditingItemIndex(null)
          itemForm.resetFields()
        }}
        width={800}
      >
        <Form form={itemForm} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="line_number"
                label="序号"
              >
                <InputNumber 
                  min={10} 
                  step={10} 
                  style={{ width: '100%' }} 
                  placeholder="如：10, 20, 30"
                  formatter={(value) => value ? `${value}` : ''}
                />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item
                name="material_code"
                label="物料编码"
                rules={[{ required: true, message: '请选择物料' }]}
              >
                <MaterialSelect 
                  placeholder="请选择物料" 
                  excludeCodes={parentMaterialCode ? [parentMaterialCode] : []}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="item_category" label="物料类别">
                <Select placeholder="选择类别">
                  <Option value="STOCK_ITEM">库存物料</Option>
                  <Option value="SUB_ASSEMBLY">半成品</Option>
                  <Option value="CONSUMABLE">耗材</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="quantity"
                label="数量"
                rules={[{ required: true, message: '请输入数量' }]}
              >
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} placeholder="请输入数量" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="unit"
                label="单位"
                rules={[{ required: true, message: '请选择单位' }]}
              >
                <Select placeholder="选择单位">
                  <Option value="SHT">张 (SHT)</Option>
                  <Option value="PNL">拼板 (PNL)</Option>
                  <Option value="KG">公斤 (KG)</Option>
                  <Option value="M">米 (M)</Option>
                  <Option value="PCS">个 (PCS)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="scrap_rate" label="损耗率(%)">
                <InputNumber min={0} style={{ width: '100%' }} placeholder="如：3" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="calculation_formula" label="计算公式">
                <Input placeholder="如：AREA_FORMULA" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="layer_code" label="层码/位置">
                <Input placeholder="如：L1 / L1-L2" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="material_type" label="材料类型">
                <Select placeholder="选择材料类型" allowClear>
                  <Option value="COPPER_FOIL">铜箔 (COPPER_FOIL)</Option>
                  <Option value="PREPREG">PP片 (PREPREG)</Option>
                  <Option value="CORE">芯板 (CORE)</Option>
                  <Option value="SOLDER_MASK">阻焊油墨 (SOLDER_MASK)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="process_step" label="工序步骤">
                <Input placeholder="如：SOLDER_MASK" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="remarks"
            label="备注"
          >
            <Input placeholder="请输入备注" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default BOMForm

