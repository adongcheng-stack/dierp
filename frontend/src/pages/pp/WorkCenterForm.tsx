import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, InputNumber, Divider } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select

interface WorkCenterFormData {
  work_center_id: string
  description: string
  work_center_type: string
  plant_id: string
  status: string
  parent_work_center_id?: string
  hierarchy_level: number
  work_center_category?: string
  usage?: string
  process_category?: string
  standard_value_key?: string
  control_key?: string
  queue_time?: number
  wait_time?: number
  move_time?: number
  capacity_category?: string
  factory_calendar_id?: string
  shift_start_time?: string
  shift_finish_time?: string
  break_time?: number
  capacity_utilization?: number
  number_of_capacities?: number
  capacity_formula_setup?: string
  capacity_formula_processing?: string
  capacity_formula_teardown?: string
  cost_center_id?: string
  activity_types?: any[]
  technical_attributes?: any[]
}

const WorkCenterForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [workCenters, setWorkCenters] = useState<any[]>([])
  const [activityTypes, setActivityTypes] = useState<any[]>([])
  const [technicalAttributes, setTechnicalAttributes] = useState<any[]>([])
  const isEdit = !!id

  useEffect(() => {
    fetchWorkCenters()
    if (isEdit) {
      fetchWorkCenter()
    }
  }, [id])

  const fetchWorkCenters = async () => {
    try {
      const response = await api.get('/pp/work-centers')
      setWorkCenters(response.data)
    } catch (error) {
      console.error('获取工作中心列表失败:', error)
    }
  }

  const fetchWorkCenter = async () => {
    try {
      const response = await api.get(`/pp/work-centers/${id}`)
      const data = response.data
      form.setFieldsValue({
        ...data,
        activity_types: data.activity_types || [],
        technical_attributes: data.technical_attributes || []
      })
      setActivityTypes(data.activity_types || [])
      setTechnicalAttributes(data.technical_attributes || [])
    } catch (error) {
      message.error('获取工作中心信息失败')
      navigate('/pp/work-centers')
    }
  }

  const onFinish = async (values: WorkCenterFormData) => {
    const payload = {
      ...values,
      activity_types: values.activity_types || activityTypes || [],
      technical_attributes: values.technical_attributes || technicalAttributes || []
    }
    setLoading(true)
    try {
      if (isEdit) {
        await api.put(`/pp/work-centers/${id}`, payload)
        message.success('工作中心更新成功')
      } else {
        await api.post('/pp/work-centers', payload)
        message.success('工作中心创建成功')
      }
      navigate('/pp/work-centers')
    } catch (error: any) {
      console.error('工作中心操作失败:', error)
      console.error('请求数据:', payload)
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '操作失败'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑工作中心' : '新建工作中心'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            work_center_type: 'MACHINE_GROUP',
            status: 'ACTIVE',
            hierarchy_level: 1,
            usage: 'PP01'
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="work_center_id"
                label="工作中心代码"
                rules={[{ required: true, message: '请输入工作中心代码' }]}
              >
                <Input placeholder="如：DRILL-A" disabled={isEdit} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="description"
                label="工作中心描述"
                rules={[{ required: true, message: '请输入工作中心描述' }]}
              >
                <Input placeholder="如：CNC钻孔机组A (4轴)" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="work_center_type"
                label="工作中心类型"
                rules={[{ required: true, message: '请选择工作中心类型' }]}
              >
                <Select>
                  <Option value="MACHINE">MACHINE (单台机器)</Option>
                  <Option value="MACHINE_GROUP">MACHINE_GROUP (机组)</Option>
                  <Option value="LABOR">LABOR (人工工位)</Option>
                  <Option value="PRODUCTION_LINE">PRODUCTION_LINE (产线)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="plant_id"
                label="所属工厂代码"
                rules={[{ required: true, message: '请输入工厂代码' }]}
              >
                <Input placeholder="如：PLANT-1000" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="status"
                label="状态"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select>
                  <Option value="ACTIVE">ACTIVE (活动的)</Option>
                  <Option value="INACTIVE">INACTIVE (停用)</Option>
                  <Option value="IN_MAINTENANCE">IN_MAINTENANCE (维护中)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>层级关系</h3>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="parent_work_center_id"
                label="父工作中心代码"
              >
                <Select placeholder="请选择父工作中心" allowClear>
                  {workCenters
                    .filter(wc => wc.work_center_id !== id)
                    .map(wc => (
                      <Option key={wc.work_center_id} value={wc.work_center_id}>
                        {wc.description} ({wc.work_center_id})
                      </Option>
                    ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="hierarchy_level"
                label="层级"
              >
                <InputNumber min={1} max={5} style={{ width: '100%' }} placeholder="1=工厂, 2=部门/产线, 3=机组, 4=设备, 5=工位" />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>基础与调度数据</h3>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="work_center_category"
                label="工作中心类别"
              >
                <Select placeholder="请选择类别">
                  <Option value="0001">0001 (机器)</Option>
                  <Option value="0002">0002 (人工)</Option>
                  <Option value="0003">0003 (产线)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="usage"
                label="用途"
              >
                <Select>
                  <Option value="PP01">PP01 (生产)</Option>
                  <Option value="PM01">PM01 (设备维护)</Option>
                  <Option value="QM01">QM01 (质量检验)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="process_category"
                label="工艺类别"
              >
                <Select placeholder="请选择工艺类别">
                  <Option value="DRILLING">DRILLING (钻孔)</Option>
                  <Option value="PLATING">PLATING (电镀)</Option>
                  <Option value="ETCHING">ETCHING (蚀刻)</Option>
                  <Option value="LAMINATION">LAMINATION (压合)</Option>
                  <Option value="AOI">AOI (自动光学检测)</Option>
                  <Option value="SOLDER_MASK">SOLDER_MASK (阻焊)</Option>
                  <Option value="SURFACE_FINISH">SURFACE_FINISH (表面处理)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="standard_value_key" label="标准值码">
                <Input placeholder="如：SAP_02" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="control_key" label="控制码">
                <Input placeholder="如：PP01" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="factory_calendar_id" label="工厂日历ID">
                <Input placeholder="如：CN" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="queue_time" label="排队时间(小时)">
                <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="wait_time" label="等待时间(小时)">
                <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="move_time" label="传送时间(小时)">
                <InputNumber min={0} step={0.05} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>产能数据</h3>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="capacity_category" label="能力类别">
                <Select>
                  <Option value="001">001 (机器)</Option>
                  <Option value="002">002 (人工)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="shift_start_time" label="班次开始时间">
                <Input placeholder="08:00" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="shift_finish_time" label="班次结束时间">
                <Input placeholder="17:00" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="break_time" label="休息时间(小时)">
                <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="capacity_utilization" label="产能利用率(%)">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="number_of_capacities" label="能力数量">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="capacity_formula_setup" label="准备公式">
                <Input placeholder="SAPF01" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="capacity_formula_processing" label="处理公式">
                <Input placeholder="SAPF02" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="capacity_formula_teardown" label="清理公式">
                <Input placeholder="SAPF03" />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>成本核算</h3>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="cost_center_id" label="成本中心代码">
                <Input placeholder="如：CC-4210" />
              </Form.Item>
            </Col>
          </Row>

          <Form.List name="activity_types" initialValue={activityTypes.length ? activityTypes : [{ activity_type_id: 'ACT-SETUP', description: '机器准备作业', standard_rate: 0, unit_of_measure: 'CNY/H' }]}>
            {(fields, { add, remove }) => (
              <Card title="作业类型" style={{ marginBottom: 16 }}>
                {fields.map(({ key, name, ...restField }) => (
                  <Row gutter={12} key={key} style={{ marginBottom: 8 }}>
                    <Col span={5}>
                      <Form.Item {...restField} name={[name, 'activity_type_id']} label="作业类型">
                        <Input placeholder="ACT-SETUP" />
                      </Form.Item>
                    </Col>
                    <Col span={7}>
                      <Form.Item {...restField} name={[name, 'description']} label="描述">
                        <Input placeholder="机器准备作业" />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item {...restField} name={[name, 'standard_rate']} label="标准费率">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item {...restField} name={[name, 'unit_of_measure']} label="计量单位">
                        <Select>
                          <Option value="CNY/H">CNY/H</Option>
                          <Option value="USD/H">USD/H</Option>
                          <Option value="EUR/H">EUR/H</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={4} style={{ display: 'flex', alignItems: 'center' }}>
                      <Button danger type="link" onClick={() => remove(name)}>
                        删除
                      </Button>
                    </Col>
                  </Row>
                ))}
                <Button type="dashed" onClick={() => add()} block>
                  新增作业类型
                </Button>
              </Card>
            )}
          </Form.List>

          <Divider />
          <h3>技术属性</h3>
          <Form.List name="technical_attributes" initialValue={technicalAttributes.length ? technicalAttributes : [{ attribute_name: 'MinHoleSize', attribute_value: '0.15', unit: 'mm' }]}>
            {(fields, { add, remove }) => (
              <Card title="技术属性" style={{ marginBottom: 16 }}>
                {fields.map(({ key, name, ...restField }) => (
                  <Row gutter={12} key={key} style={{ marginBottom: 8 }}>
                    <Col span={6}>
                      <Form.Item {...restField} name={[name, 'attribute_name']} label="属性名">
                        <Input placeholder="如：MinHoleSize" />
                      </Form.Item>
                    </Col>
                    <Col span={10}>
                      <Form.Item {...restField} name={[name, 'attribute_value']} label="属性值">
                        <Input placeholder="属性值" />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item {...restField} name={[name, 'unit']} label="单位">
                        <Input placeholder="mm / μm / Layers" />
                      </Form.Item>
                    </Col>
                    <Col span={4} style={{ display: 'flex', alignItems: 'center' }}>
                      <Button danger type="link" onClick={() => remove(name)}>
                        删除
                      </Button>
                    </Col>
                  </Row>
                ))}
                <Button type="dashed" onClick={() => add()} block>
                  新增技术属性
                </Button>
              </Card>
            )}
          </Form.List>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/pp/work-centers')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default WorkCenterForm

