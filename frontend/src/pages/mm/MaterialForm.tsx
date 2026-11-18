import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, InputNumber, DatePicker, Switch, Divider } from 'antd'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'

const { Option } = Select
const { TextArea } = Input

interface MaterialFormData {
  material_code: string
  material_name: string
  category: string
  specification?: string
  unit: string
  brand?: string
  min_package?: string
  current_stock: number
  safety_stock: number
  description?: string
  material_type?: string
  status?: string
  version?: string
  base_unit?: string
  production_unit?: string
  conversion_factor?: number
  layer_count?: number
  board_thickness?: number
  thickness_tolerance?: string
  copper_weight?: string
  material_grade?: string
  surface_finish?: string
  solder_mask_color?: string
  silkscreen_color?: string
  impedance_control?: boolean
  min_line_space?: number
  min_hole_size?: number
  unit_length?: number
  unit_width?: number
  panel_length?: number
  panel_width?: number
  units_per_panel?: number
  procurement_type?: string
  mrp_controller?: string
  lead_time_days?: number
  max_lot_size?: number
  min_order_quantity?: number
  order_multiple?: number
  abc_class?: string
  shelf_life_days?: number
  default_location?: string
  storage_condition?: string
  batch_tracking?: boolean
  valuation_method?: string
  standard_price?: number
  currency?: string
  last_cost_update?: any
}

const MaterialForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { code } = useParams<{ code?: string }>()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const isEdit = !!code
  // 判断是否从产品主数据页面跳转过来（有material_code参数表示是从产品主数据跳转的）
  const isFromProductMaster = !isEdit && !!searchParams.get('material_code')

  useEffect(() => {
    if (isEdit) {
      fetchMaterial()
    } else {
      // 新建模式：从URL参数中读取material_code并自动填充
      const materialCodeFromUrl = searchParams.get('material_code')
      if (materialCodeFromUrl) {
        form.setFieldsValue({
          material_code: materialCodeFromUrl,
          // 从产品主数据跳转过来时，自动设置为成品
          material_type: 'FG',
          category: '成品'
        })
      }
    }
  }, [code, searchParams])

  const fetchMaterial = async () => {
    try {
      const response = await api.get(`/mm/materials/${code}`)
      form.setFieldsValue({
        ...response.data,
        last_cost_update: response.data.last_cost_update ? dayjs(response.data.last_cost_update) : undefined
      })
    } catch (error) {
      message.error('获取产品信息失败')
      navigate('/mm/materials')
    }
  }

  const onFinish = async (values: MaterialFormData) => {
    setLoading(true)
    try {
      if (isEdit) {
        await api.put(`/mm/materials/${code}`, values)
        message.success('产品更新成功')
        navigate('/mm/materials')
      } else {
        await api.post('/mm/materials', values)
        message.success('产品创建成功')
        
        // 如果是从产品主数据页面跳转过来的，关闭窗口并通知父窗口刷新
        if (isFromProductMaster) {
          // 通知父窗口产品已创建
          if (window.opener) {
            window.opener.postMessage({
              type: 'PRODUCT_CREATED',
              materialCode: values.material_code
            }, window.location.origin)
            // 延迟关闭，确保消息已发送
            setTimeout(() => {
              window.close()
            }, 500)
          } else {
            // 如果没有父窗口，返回产品主数据页面
            navigate('/eng/factory-product-mappings/new')
          }
        } else {
          navigate('/mm/materials')
        }
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑产品' : '新建产品'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            category: '原材料/基材',
            unit: '张',
            current_stock: 0,
            safety_stock: 0,
            material_type: 'RAW',
            status: 'ACTIVE',
            base_unit: 'PCS',
            production_unit: 'PCS',
            conversion_factor: 1,
            impedance_control: false,
            batch_tracking: false,
            procurement_type: 'MAKE',
            valuation_method: 'STANDARD',
            currency: 'CNY'
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="material_code"
                label="产品编码"
                rules={[{ required: true, message: '请输入产品编码' }]}
              >
                <Input placeholder="请输入产品编码" disabled={isEdit} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="material_name"
                label="产品名称"
                rules={[{ required: true, message: '请输入产品名称' }]}
              >
                <Input placeholder="请输入产品名称" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="material_type" label="产品类型">
                <Select disabled={isEdit || isFromProductMaster}>
                  {isFromProductMaster ? (
                    <Option value="FG">成品(FG)</Option>
                  ) : (
                    <>
                      <Option value="RAW">原材料(RAW)</Option>
                      <Option value="SEMI">半成品(SEMI)</Option>
                      <Option value="REPAIR">维修(REPAIR)</Option>
                    </>
                  )}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="status" label="状态">
                <Select>
                  <Option value="ACTIVE">活跃</Option>
                  <Option value="OBSOLETE">报废/呆滞</Option>
                  <Option value="DRAFT">工程研发中</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="version" label="版本">
                <Input placeholder="如：A.0 / B.1" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category"
                label="物料分类"
                rules={[{ required: true, message: '请选择物料分类' }]}
              >
                <Select disabled={isEdit || isFromProductMaster}>
                  <Option value="原材料/基材">原材料/基材</Option>
                  <Option value="辅材">辅材</Option>
                  <Option value="化工材料">化工材料</Option>
                  <Option value="成品">成品</Option>
                  <Option value="维修">维修</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="unit"
                label="计量单位"
                rules={[{ required: true, message: '请选择计量单位' }]}
              >
                <Select>
                  <Option value="张">张</Option>
                  <Option value="卷">卷</Option>
                  <Option value="公斤">公斤</Option>
                  <Option value="个">个</Option>
                  <Option value="PNL">PNL (Panel)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="base_unit" label="基础计量单位">
                <Select>
                  <Option value="PCS">PCS</Option>
                  <Option value="PNL">PNL</Option>
                  <Option value="KG">KG</Option>
                  <Option value="SHT">SHT</Option>
                  <Option value="SET">SET</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="production_unit" label="生产计量单位">
                <Select>
                  <Option value="PNL">PNL</Option>
                  <Option value="PCS">PCS</Option>
                  <Option value="SET">SET</Option>
                  <Option value="KG">KG</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="conversion_factor" label="单位换算 (生产->基础)">
                <InputNumber min={0.0001} style={{ width: '100%' }} placeholder="如：6 表示 1 PNL=6 PCS" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="specification"
            label="规格型号"
          >
            <Input placeholder="请输入规格型号" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="brand"
                label="品牌/厂家"
              >
                <Input placeholder="请输入品牌/厂家" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="min_package"
                label="最小包装"
              >
                <Input placeholder="如：10张/箱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="current_stock"
                label="当前库存"
                rules={[{ required: true, message: '请输入当前库存' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入当前库存" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="safety_stock"
                label="安全库存"
                rules={[{ required: true, message: '请输入安全库存' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入安全库存" />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>PCB工程属性</h3>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="layer_count" label="层数">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="board_thickness" label="板厚(mm)">
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="thickness_tolerance" label="厚度公差">
                <Input placeholder="+/-0.1" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="copper_weight" label="铜厚">
                <Input placeholder="如：1oz" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="material_grade" label="材料等级">
                <Input placeholder="如：FR4-Tg170" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="surface_finish" label="表面处理">
                <Input placeholder="ENIG / HASL / OSP" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="solder_mask_color" label="阻焊颜色">
                <Input placeholder="GREEN" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="silkscreen_color" label="丝印颜色">
                <Input placeholder="WHITE" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="impedance_control" valuePropName="checked">
                <Switch checkedChildren="阻抗控制" unCheckedChildren="无阻抗" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="min_line_space" label="最小线距(mm)">
                <InputNumber min={0} step={0.001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="min_hole_size" label="最小孔径(mm)">
                <InputNumber min={0} step={0.001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="unit_length" label="单元长(mm)">
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="unit_width" label="单元宽(mm)">
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="panel_length" label="Panel长(mm)">
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="panel_width" label="Panel宽(mm)">
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="units_per_panel" label="每Panel单元数">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>供应链计划参数</h3>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="procurement_type" label="采购类型">
                <Select>
                  <Option value="MAKE">MAKE(自制)</Option>
                  <Option value="BUY">BUY(外购)</Option>
                  <Option value="SUB">SUB(全外协)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="mrp_controller" label="MRP控制器">
                <Input placeholder="如：PLANNER-A" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="lead_time_days" label="交货周期(天)">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="safety_stock" label="安全库存">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="max_lot_size" label="最大批量">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="min_order_quantity" label="最小订货量">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="order_multiple" label="订货倍数">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="abc_class" label="ABC分类">
                <Input placeholder="如：A/B/C" />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>库存管理</h3>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="shelf_life_days" label="保质期(天)">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="default_location" label="默认库位">
                <Input placeholder="如：WH-FG-01" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="storage_condition" label="存储条件">
                <Input placeholder="如：VACUUM_PACK" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="batch_tracking" valuePropName="checked">
                <Switch checkedChildren="批次追踪" unCheckedChildren="不追踪" />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>财务成本</h3>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="valuation_method" label="计价方法">
                <Select>
                  <Option value="STANDARD">STANDARD</Option>
                  <Option value="MOVING_AVG">MOVING_AVG</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="standard_price" label="标准价格">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="currency" label="货币">
                <Input placeholder="CNY" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="last_cost_update" label="最后成本更新">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="请输入物料描述" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/mm/materials')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default MaterialForm

