import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker, Table, Modal, InputNumber, Switch, Divider } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'

const { Option } = Select
const { TextArea } = Input

interface RoutingOperation {
  operation_no: string
  operation_code: string
  operation_name: string
  operation_type: string
  work_center_id: string
  setup_time: number
  machine_time: number
  labor_time: number
  queue_time: number
  cost_relevant: boolean
  scheduling_relevant: boolean
  needs_reporting?: boolean
  auto_deduct_material?: boolean
  trigger_quality_check?: boolean
  sop_link?: string
  service_code?: string
  planned_delivery_days?: number
  estimated_unit_price?: number
  estimated_currency?: string
  suggested_supplier?: string
  generate_purchase_req?: boolean
  inspection_plan_id?: string
  sampling_rate?: number
  verification_logic?: string
  remarks?: string
}

const RoutingForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [materials, setMaterials] = useState<any[]>([])
  const [workCenters, setWorkCenters] = useState<any[]>([])
  const [operations, setOperations] = useState<RoutingOperation[]>([])
  const [operationModalVisible, setOperationModalVisible] = useState(false)
  const [operationForm] = Form.useForm()
  const [routingInfo, setRoutingInfo] = useState<any>(null) // 存储审计追踪信息
  const isEdit = !!id

  useEffect(() => {
    fetchMaterials()
    fetchWorkCenters()
    if (isEdit) {
      fetchRouting()
    }
  }, [id])

  const fetchMaterials = async () => {
    try {
      const response = await api.get('/mm/materials')
      setMaterials(response.data)
    } catch (error) {
      console.error('获取物料列表失败:', error)
    }
  }

  const fetchWorkCenters = async () => {
    try {
      const response = await api.get('/pp/work-centers')
      setWorkCenters(response.data)
    } catch (error) {
      console.error('获取工作中心列表失败:', error)
    }
  }

  const fetchRouting = async () => {
    try {
      const response = await api.get(`/eng/routings/${id}`)
      const data = response.data
      setRoutingInfo(data) // 保存审计追踪信息
      form.setFieldsValue({
        ...data,
        effective_date: data.effective_date ? dayjs(data.effective_date) : undefined,
        expiry_date: data.expiry_date ? dayjs(data.expiry_date) : undefined
      })
      // 获取工序列表（通过工艺路线ID）
      try {
        const opsResponse = await api.get(`/eng/routings/${data.routing_id}/operations`)
        setOperations(opsResponse.data || [])
      } catch (error: any) {
        // 如果获取工序失败，使用空数组
        console.warn('获取工序列表失败:', error)
        setOperations([])
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '获取工艺路线信息失败'
      message.error(errorMsg)
      console.error('获取工艺路线信息失败:', error)
      navigate('/eng/routings')
    }
  }

  const handleAddOperation = () => {
    operationForm.resetFields()
    setOperationModalVisible(true)
  }

  const handleSaveOperation = () => {
    operationForm.validateFields().then(values => {
      // 确保所有字段都有默认值
      const operation: RoutingOperation = {
        operation_no: values.operation_no,
        operation_code: values.operation_code,
        operation_name: values.operation_name,
        operation_type: values.operation_type,
        work_center_id: values.work_center_id,
        setup_time: values.setup_time || 0,
        machine_time: values.machine_time || 0,
        labor_time: values.labor_time || 0,
        queue_time: values.queue_time || 0,
        cost_relevant: values.cost_relevant !== undefined ? values.cost_relevant : true,
        scheduling_relevant: values.scheduling_relevant !== undefined ? values.scheduling_relevant : true,
        needs_reporting: values.needs_reporting !== undefined ? values.needs_reporting : true,
        auto_deduct_material: values.auto_deduct_material || false,
        trigger_quality_check: values.trigger_quality_check || false,
        sop_link: values.sop_link,
        service_code: values.service_code,
        planned_delivery_days: values.planned_delivery_days,
        estimated_unit_price: values.estimated_unit_price,
        estimated_currency: values.estimated_currency,
        suggested_supplier: values.suggested_supplier,
        generate_purchase_req: values.generate_purchase_req || false,
        inspection_plan_id: values.inspection_plan_id,
        sampling_rate: values.sampling_rate,
        verification_logic: values.verification_logic,
        remarks: values.remarks
      }
      setOperations([...operations, operation])
      setOperationModalVisible(false)
      operationForm.resetFields()
    })
  }

  const handleDeleteOperation = (index: number) => {
    setOperations(operations.filter((_, i) => i !== index))
  }

  const onFinish = async (values: any) => {
    // 验证是否有工序
    if (!operations || operations.length === 0) {
      message.error('请至少添加一个工序')
      return
    }
    
    setLoading(true)
    try {
      const formData = {
        ...values,
        effective_date: values.effective_date ? values.effective_date.toISOString() : undefined,
        expiry_date: values.expiry_date ? values.expiry_date.toISOString() : undefined,
        operations: operations
      }
      if (isEdit) {
        await api.put(`/eng/routings/${id}`, formData)
        message.success('工艺路线更新成功')
      } else {
        await api.post('/eng/routings', formData)
        message.success('工艺路线创建成功')
      }
      navigate('/eng/routings')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      message.error(errorMsg)
      console.error('工艺路线操作失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const operationColumns = [
    { title: '序号', key: 'index', render: (_: any, __: any, index: number) => index + 1 },
    { title: '工序号', dataIndex: 'operation_no', key: 'operation_no' },
    { title: '工序代码', dataIndex: 'operation_code', key: 'operation_code' },
    { title: '工序名称', dataIndex: 'operation_name', key: 'operation_name' },
    { title: '类型', dataIndex: 'operation_type', key: 'operation_type' },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'work_center_id' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, __: any, index: number) => (
        <Button
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => handleDeleteOperation(index)}
        >
          删除
        </Button>
      )
    }
  ]

  return (
    <div>
      <Card title={isEdit ? '编辑工艺路线' : '新建工艺路线'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            version: 'A01',
            base_unit: 'PNL',
            base_quantity: 1,
            units_per_panel: 1
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="routing_id"
                label="工艺路线ID"
                rules={[{ required: !isEdit, message: '请输入工艺路线ID' }]}
              >
                <Input placeholder="如：RT-2023-PCB-8801" disabled={isEdit} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="material_code"
                label="物料编码"
                rules={[{ required: true, message: '请选择物料' }]}
              >
                <Select placeholder="请选择物料" showSearch>
                  {materials.map(material => (
                    <Option key={material.material_code} value={material.material_code}>
                      {material.material_name} ({material.material_code})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="version"
                label="版本"
                rules={[{ required: true, message: '请输入版本' }]}
              >
                <Input placeholder="如：A01" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="plant_id"
                label="工厂代码"
                rules={[{ required: true, message: '请输入工厂代码' }]}
              >
                <Input placeholder="如：SZ-FACTORY-01" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="panel_size"
                label="Panel尺寸"
              >
                <Input placeholder="如：18x24 INCH" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="base_unit"
                label="基础单位"
                rules={[{ required: true, message: '请输入基础单位' }]}
              >
                <Input placeholder="如：PNL" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="base_quantity"
                label="基数"
                rules={[{ required: true, message: '请输入基数' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="如：1" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="units_per_panel"
                label="每Panel单元数"
                rules={[{ required: true, message: '请输入每Panel单元数' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} placeholder="如：12" />
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

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="description"
                label="描述"
              >
                <TextArea rows={2} placeholder="请输入工艺路线描述" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="change_request_no"
                label="工程变更单号"
              >
                <Input placeholder="如：ECN-2023-889" />
              </Form.Item>
            </Col>
          </Row>

          {isEdit && routingInfo && (
            <Card title="审计追踪" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={6}>
                  <div><strong>创建人：</strong>{routingInfo.created_by || '-'}</div>
                </Col>
                <Col span={6}>
                  <div><strong>创建时间：</strong>{routingInfo.created_at ? dayjs(routingInfo.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
                </Col>
                <Col span={6}>
                  <div><strong>最后修改人：</strong>{routingInfo.updated_by || '-'}</div>
                </Col>
                <Col span={6}>
                  <div><strong>最后修改时间：</strong>{routingInfo.updated_at ? dayjs(routingInfo.updated_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
                </Col>
              </Row>
            </Card>
          )}

          <Card
            title="工序列表"
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddOperation}>
                新增工序
              </Button>
            }
            style={{ marginTop: 16 }}
          >
            <Table
              columns={operationColumns}
              dataSource={operations}
              rowKey={(record) => `${record.operation_no}-${record.operation_code}`}
              pagination={false}
              locale={{ emptyText: '暂无工序，请点击"新增工序"添加' }}
            />
          </Card>

          <Form.Item style={{ marginTop: 24 }}>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/eng/routings')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Modal
        title="新增工序"
        open={operationModalVisible}
        onOk={handleSaveOperation}
        onCancel={() => setOperationModalVisible(false)}
        width={900}
      >
        <Form form={operationForm} layout="vertical">
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
                name="operation_code"
                label="工序代码"
                rules={[{ required: true, message: '请输入工序代码' }]}
              >
                <Input placeholder="如：DRL-001" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="operation_name"
            label="工序名称"
            rules={[{ required: true, message: '请输入工序名称' }]}
          >
            <Input placeholder="如：CNC钻孔 / 数控钻孔" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="operation_type"
                label="类型"
                rules={[{ required: true, message: '请选择类型' }]}
              >
                <Select>
                  <Option value="INTERNAL">内部</Option>
                  <Option value="EXTERNAL">外协</Option>
                  <Option value="QUALITY">质检</Option>
                </Select>
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

          <Form.Item name="sop_link" label="SOP链接">
            <Input placeholder="http://..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item
                name="setup_time"
                label="调机时间(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="machine_time"
                label="机器时间(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="labor_time"
                label="人工时间(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="queue_time"
                label="排队缓冲(分钟)"
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
          </Row>
          <Divider>控制逻辑</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="cost_relevant" valuePropName="checked" initialValue={true} label="成本相关">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="scheduling_relevant" valuePropName="checked" initialValue={true} label="排程相关">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="needs_reporting" valuePropName="checked" initialValue={true} label="需报工">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="auto_deduct_material" valuePropName="checked" initialValue={false} label="自动倒扣料">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="trigger_quality_check" valuePropName="checked" initialValue={false} label="触发质检">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item shouldUpdate={(prevValues, currentValues) => prevValues.operation_type !== currentValues.operation_type}>
            {({ getFieldValue }) => {
              const operationType = getFieldValue('operation_type')
              
              return (
                <>
                  {operationType === 'INTERNAL' && (
                    <>
                      <Divider>内部工序参数</Divider>
                      <Row gutter={16}>
                        <Col span={6}>
                          <Form.Item name="setup_time" label="调机时间(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="machine_time" label="机器时间(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="labor_time" label="人工时间(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="queue_time" label="排队缓冲(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                      </Row>
                    </>
                  )}

                  {operationType === 'EXTERNAL' && (
                    <>
                      <Divider>外协工序参数</Divider>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Form.Item name="service_code" label="服务代码">
                            <Input placeholder="如：SRV-ENIG-01" />
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item name="planned_delivery_days" label="计划交期(天)">
                            <InputNumber min={0} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Form.Item name="estimated_unit_price" label="预估单价">
                            <InputNumber min={0} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col span={8}>
                          <Form.Item name="estimated_currency" label="币种">
                            <Select placeholder="如：CNY">
                              <Option value="CNY">CNY</Option>
                              <Option value="USD">USD</Option>
                            </Select>
                          </Form.Item>
                        </Col>
                        <Col span={8}>
                          <Form.Item name="suggested_supplier" label="建议供应商">
                            <Input placeholder="供应商" />
                          </Form.Item>
                        </Col>
                      </Row>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Form.Item name="generate_purchase_req" valuePropName="checked" initialValue={false} label="自动生成采购申请">
                            <Switch checkedChildren="是" unCheckedChildren="否" />
                          </Form.Item>
                        </Col>
                      </Row>
                    </>
                  )}

                  {operationType === 'QUALITY' && (
                    <>
                      <Divider>质检工序参数</Divider>
                      <Row gutter={16}>
                        <Col span={6}>
                          <Form.Item name="setup_time" label="调机时间(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="machine_time" label="机器时间(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="labor_time" label="人工时间(分钟)">
                            <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                          </Form.Item>
                        </Col>
                      </Row>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Form.Item name="inspection_plan_id" label="检验计划">
                            <Input placeholder="如：QP-PCB-LEVEL2" />
                          </Form.Item>
                        </Col>
                        <Col span={8}>
                          <Form.Item name="sampling_rate" label="抽检率(%)">
                            <InputNumber min={0} max={100} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col span={8}>
                          <Form.Item name="verification_logic" label="判定逻辑">
                            <Select placeholder="如：BLOCK_ON_FAIL">
                              <Option value="BLOCK_ON_FAIL">失败锁单</Option>
                              <Option value="CONTINUE_ON_FAIL">失败继续</Option>
                              <Option value="AUTO_REWORK">自动返工</Option>
                            </Select>
                          </Form.Item>
                        </Col>
                      </Row>
                    </>
                  )}
                </>
              )
            }}
          </Form.Item>

          <Form.Item name="remarks" label="备注">
            <TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default RoutingForm

