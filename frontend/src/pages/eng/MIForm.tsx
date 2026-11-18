import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker, InputNumber, Table, Modal } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'
import { PlusOutlined, EditOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import { useConfirm } from '../../components/common/ConfirmProvider'

const { Option } = Select
const { TextArea } = Input

interface MIInstruction {
  sequence: number
  operation_code?: string  // 工序代码（参考工艺路线工序）
  operation_name?: string  // 工序名称（参考工艺路线工序）
  instruction_type: string
  instruction_content: string
  description?: string
}

interface MIContent {
  pcb_type?: string
  layers?: number
  board_thickness?: number
  copper_thickness?: number
  surface_treatment?: string
  solder_mask_color?: string
  legend_color?: string
  delivery_size?: string
  panel_method?: string
  test_requirement?: string
  special_requirements?: string
  instructions?: MIInstruction[]
}



const MIForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [materials, setMaterials] = useState<any[]>([])
  const [routings, setRoutings] = useState<any[]>([])
  const [selectedRouting, setSelectedRouting] = useState<string>('')
  const [instructions, setInstructions] = useState<MIInstruction[]>([])
  const [instructionModalVisible, setInstructionModalVisible] = useState(false)
  const [editingInstruction, setEditingInstruction] = useState<MIInstruction | null>(null)
  const [instructionForm] = Form.useForm()
  const [selectedMaterial, setSelectedMaterial] = useState<string>('')
  const isEdit = !!id
  const confirm = useConfirm()

  useEffect(() => {
    fetchMaterials()
    if (isEdit) {
      fetchMI()
    }
  }, [id])

  useEffect(() => {
    if (selectedMaterial) {
      fetchRoutings()
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

  const handleMaterialChange = (materialCode: string) => {
    setSelectedMaterial(materialCode)
    setSelectedRouting('')
    setInstructions([])
  }

  const handleRoutingChange = async (routingId: string) => {
    setSelectedRouting(routingId)
    if (routingId) {
      // 如果是编辑模式，询问是否覆盖现有指令
      if (isEdit && instructions.length > 0) {
        confirm({
          title: '确认覆盖',
          icon: 'warning',
          content: '当前MI已有指令，是否要用工艺路线生成的指令覆盖现有指令？',
          onOk: async () => {
            await generateInstructionsFromRouting(routingId)
          }
        })
      } else {
        await generateInstructionsFromRouting(routingId)
      }
    } else {
      // 清空选择时，如果是新建模式，清空指令；编辑模式不清空
      if (!isEdit) {
        setInstructions([])
      }
    }
  }

  const generateInstructionsFromRouting = async (routingId: string) => {
    try {
      // 获取工艺路线的工序列表
      const response = await api.get(`/eng/routings/${routingId}/operations`)
      const operations = response.data || []
      
      if (operations.length === 0) {
        message.warning('该工艺路线暂无工序')
        return
      }
      
      // 将工序转换为MI指令
      const newInstructions: MIInstruction[] = operations.map((op: any, index: number) => {
        // 构建指令内容
        let content = `工序编号: ${op.operation_no}\n工序代码: ${op.operation_code}\n工序名称: ${op.operation_name}\n工作中心: ${op.work_center_id}`
        
        // 添加时间参数
        if (op.setup_time > 0) {
          content += `\n调机时间: ${op.setup_time} 分钟`
        }
        if (op.machine_time > 0) {
          content += `\n机器时间: ${op.machine_time} 分钟`
        }
        if (op.labor_time > 0) {
          content += `\n人工时间: ${op.labor_time} 分钟`
        }
        
        // 添加备注
        if (op.remarks) {
          content += `\n备注: ${op.remarks}`
        }
        
        return {
          sequence: index + 1,
          instruction_type: op.operation_name || op.operation_code || '工序',
          instruction_content: content,
          description: op.remarks || undefined
        }
      })
      
      setInstructions(newInstructions)
      message.success(`已根据工艺路线自动生成 ${newInstructions.length} 条指令`)
    } catch (error: any) {
      console.error('获取工艺路线工序失败:', error)
      message.error('获取工艺路线工序失败: ' + (error.response?.data?.detail || error.message))
    }
  }

  const fetchMI = async () => {
    try {
      const response = await api.get(`/eng/mis/${id}`)
      const data = response.data
      setSelectedMaterial(data.material_code)
      
      // 加载指令项列表（从API直接获取）
      if (data.instructions && Array.isArray(data.instructions)) {
        setInstructions(data.instructions)
      } else {
        setInstructions([])
      }
      
      // 兼容旧格式：如果有content字段，尝试解析
      let contentData: MIContent = {}
      if (data.content) {
        try {
          contentData = JSON.parse(data.content)
          // 如果API没有返回instructions，但从content中解析到了，使用content中的
          if (!data.instructions && contentData.instructions) {
            setInstructions(contentData.instructions)
          }
        } catch (e) {
          console.error('解析MI内容失败:', e)
        }
      }
      
      form.setFieldsValue({
        material_code: data.material_code,
        version: data.version,
        description: data.description,
        effective_date: data.effective_date ? dayjs(data.effective_date) : undefined,
        expiry_date: data.expiry_date ? dayjs(data.expiry_date) : undefined,
        // 工艺参数（如果有）
        pcb_type: contentData.pcb_type,
        layers: contentData.layers,
        board_thickness: contentData.board_thickness,
        copper_thickness: contentData.copper_thickness,
        surface_treatment: contentData.surface_treatment,
        solder_mask_color: contentData.solder_mask_color,
        legend_color: contentData.legend_color,
        delivery_size: contentData.delivery_size,
        panel_method: contentData.panel_method,
        test_requirement: contentData.test_requirement,
        special_requirements: contentData.special_requirements
      })
      
      // 如果是编辑模式，加载工艺路线列表
      if (data.material_code) {
        fetchRoutings()
      }
    } catch (error) {
      message.error('获取MI信息失败')
      navigate('/eng/mis')
    }
  }

  const onFinish = async (values: any, shouldNavigate: boolean = true) => {
    // 没有指令项时先确认，取消则中止保存
    if (instructions.length === 0) {
      const proceed = await new Promise<boolean>((resolve) => {
        confirm({
          title: '确认保存',
          icon: 'warning',
          content: '当前没有MI指令项，是否继续保存？',
          okText: '继续保存',
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        })
      })
      if (!proceed) return undefined
    }

    setLoading(true)
    try {
      // 验证序号唯一性
      const sequences = instructions.map(inst => inst.sequence)
      const uniqueSequences = new Set(sequences)
      if (sequences.length !== uniqueSequences.size) {
        message.error('指令项序号不能重复，请检查并修改')
        setLoading(false)
        return
      }
      
      // 验证必填字段
      for (const inst of instructions) {
        if (!inst.instruction_type || !inst.instruction_type.trim()) {
          message.error(`指令项 #${inst.sequence} 的指令类型不能为空`)
          setLoading(false)
          return
        }
        if (!inst.instruction_content || !inst.instruction_content.trim()) {
          message.error(`指令项 #${inst.sequence} 的指令内容不能为空`)
          setLoading(false)
          return
        }
      }

      // 构建请求数据：使用instructions数组，不再使用content JSON
      const formData: any = {
        material_code: values.material_code,
        version: values.version,
        effective_date: values.effective_date ? values.effective_date.toISOString() : undefined,
        expiry_date: values.expiry_date ? values.expiry_date.toISOString() : undefined,
        description: values.description,
        instructions: instructions.map(inst => ({
          sequence: inst.sequence,
          instruction_type: inst.instruction_type,
          instruction_content: inst.instruction_content,
          description: inst.description || ''
        }))
      }

      if (isEdit) {
        const response = await api.put(`/eng/mis/${id}`, formData)
        message.success('MI更新成功')
        if (shouldNavigate) {
          navigate('/eng/mis')
        }
        return response.data
      } else {
        const response = await api.post('/eng/mis', formData)
        message.success('MI创建成功')
        if (shouldNavigate) {
          navigate('/eng/mis')
        }
        return response.data
      }
    } catch (error: any) {
      console.error('MI操作失败:', error)
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || '操作失败'
      message.error(errorMessage)
      throw error // 重新抛出错误，让 handleSubmit 可以处理
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    try {
      await form.validateFields()
      const values = form.getFieldsValue()
      
      // 先保存（不导航）
      const savedMI = await onFinish(values, false)
      
      // 然后提交审核（只有新建时才需要提交）
      if (!isEdit && savedMI) {
        const miNumber = savedMI.mi_number || `MI-${values.material_code}-${values.version}`
        try {
          await api.post(`/eng/mis/${miNumber}/submit`)
          message.success('MI已提交审核')
        } catch (submitError: any) {
          console.error('提交审核失败:', submitError)
          const errorMessage = submitError.response?.data?.detail || submitError.response?.data?.message || '提交审核失败'
          message.error(errorMessage)
          // 即使提交失败，MI也已经创建成功，所以仍然导航到列表页
        }
      }
      
      navigate('/eng/mis')
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请填写所有必填字段')
      } else {
        console.error('提交失败:', error)
        // 如果创建失败，不导航，让用户修复问题
      }
    }
  }

  const handleAddInstruction = () => {
    setEditingInstruction(null)
    instructionForm.resetFields()
    setInstructionModalVisible(true)
  }

  const handleEditInstruction = (instruction: MIInstruction) => {
    setEditingInstruction(instruction)
    instructionForm.setFieldsValue(instruction)
    setInstructionModalVisible(true)
  }

  const handleDeleteInstruction = (sequence: number) => {
    const newInstructions = instructions.filter(inst => inst.sequence !== sequence)
    // 重新排序序号
    const sortedInstructions = newInstructions.map((inst, index) => ({
      ...inst,
      sequence: index + 1
    }))
    setInstructions(sortedInstructions)
    message.success('指令已删除')
  }

  const handleMoveUp = (sequence: number) => {
    const sortedInstructions = [...instructions].sort((a, b) => a.sequence - b.sequence)
    const currentIndex = sortedInstructions.findIndex(inst => inst.sequence === sequence)
    
    if (currentIndex > 0) {
      // 交换位置
      const temp = sortedInstructions[currentIndex]
      sortedInstructions[currentIndex] = sortedInstructions[currentIndex - 1]
      sortedInstructions[currentIndex - 1] = temp
      
      // 重新分配序号
      const reorderedInstructions = sortedInstructions.map((inst, index) => ({
        ...inst,
        sequence: index + 1
      }))
      setInstructions(reorderedInstructions)
      message.success('指令已上移')
    } else {
      message.warning('已经是第一条指令，无法上移')
    }
  }

  const handleMoveDown = (sequence: number) => {
    const sortedInstructions = [...instructions].sort((a, b) => a.sequence - b.sequence)
    const currentIndex = sortedInstructions.findIndex(inst => inst.sequence === sequence)
    
    if (currentIndex < sortedInstructions.length - 1) {
      // 交换位置
      const temp = sortedInstructions[currentIndex]
      sortedInstructions[currentIndex] = sortedInstructions[currentIndex + 1]
      sortedInstructions[currentIndex + 1] = temp
      
      // 重新分配序号
      const reorderedInstructions = sortedInstructions.map((inst, index) => ({
        ...inst,
        sequence: index + 1
      }))
      setInstructions(reorderedInstructions)
      message.success('指令已下移')
    } else {
      message.warning('已经是最后一条指令，无法下移')
    }
  }

  const handleSaveInstruction = () => {
    instructionForm.validateFields().then(values => {
      if (editingInstruction) {
        // 更新现有指令
        setInstructions(instructions.map(inst => 
          inst.sequence === editingInstruction.sequence 
            ? { ...values, sequence: editingInstruction.sequence }
            : inst
        ))
        message.success('指令已更新')
      } else {
        // 添加新指令
        const maxSequence = instructions.length > 0 
          ? Math.max(...instructions.map(inst => inst.sequence))
          : 0
        const newInstructions = [...instructions, { ...values, sequence: maxSequence + 1 }]
        // 按序号排序
        newInstructions.sort((a, b) => a.sequence - b.sequence)
        setInstructions(newInstructions)
        message.success('指令已添加')
      }
      setInstructionModalVisible(false)
      instructionForm.resetFields()
      setEditingInstruction(null)
    }).catch(() => {
      message.error('请填写所有必填字段')
    })
  }

  const instructionColumns = [
    {
      title: '序号',
      dataIndex: 'sequence',
      key: 'sequence',
      width: 80,
      render: (seq: number) => <strong>{seq}</strong>
    },
    {
      title: '指令类型',
      dataIndex: 'instruction_type',
      key: 'instruction_type',
      width: 150
    },
    {
      title: '指令内容',
      dataIndex: 'instruction_content',
      key: 'instruction_content',
      ellipsis: true
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: MIInstruction) => {
        const sortedInstructions = [...instructions].sort((a, b) => a.sequence - b.sequence)
        const currentIndex = sortedInstructions.findIndex(inst => inst.sequence === record.sequence)
        const isFirst = currentIndex === 0
        const isLast = currentIndex === sortedInstructions.length - 1
        
        return (
          <Space>
            <Button
              type="link"
              size="small"
              icon={<ArrowUpOutlined />}
              disabled={isFirst}
              onClick={() => handleMoveUp(record.sequence)}
              title="上移"
            />
            <Button
              type="link"
              size="small"
              icon={<ArrowDownOutlined />}
              disabled={isLast}
              onClick={() => handleMoveDown(record.sequence)}
              title="下移"
            />
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditInstruction(record)}
            >
              编辑
            </Button>
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteInstruction(record.sequence)}
            >
              删除
            </Button>
          </Space>
        )
      }
    }
  ]

  return (
    <div>
      <Card 
        title={isEdit ? '编辑MI' : '创建MI（制造指令）'}
        extra={
          <span style={{ 
            padding: '4px 12px', 
            borderRadius: '12px', 
            fontSize: '12px',
            backgroundColor: 'hsl(var(--brand-soft))',
            color: 'hsl(var(--brand-ink))'
          }}>
            草稿
          </span>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            version: 'V1.0'
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="material_code"
                label="物料编码"
                rules={[{ required: true, message: '请选择物料' }]}
              >
                <Select
                  placeholder="请选择物料"
                  showSearch
                  disabled={isEdit}
                  onChange={handleMaterialChange}
                >
                  {materials.map(material => (
                    <Option key={material.material_code} value={material.material_code}>
                      {material.material_code} - {material.material_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="version"
                label="版本号"
                rules={[{ required: true, message: '请输入版本号' }]}
              >
                <Input placeholder="例如: V1.0" />
              </Form.Item>
            </Col>
            <Col span={8}>
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
                label="工艺路线（选择后自动生成指令）"
              >
                <Select
                  placeholder={selectedMaterial ? "请选择工艺路线" : "请先选择物料"}
                  showSearch
                  allowClear
                  disabled={!selectedMaterial}
                  value={selectedRouting}
                  onChange={handleRoutingChange}
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
            <Col span={8}>
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
            <Col span={8}>
              <Form.Item
                name="pcb_type"
                label="PCB类型"
              >
                <Select placeholder="请选择PCB类型">
                  <Option value="rigid">刚性板</Option>
                  <Option value="flex">柔性板</Option>
                  <Option value="rigid-flex">刚柔结合板</Option>
                  <Option value="aluminum">铝基板</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="layers"
                label="层数"
              >
                <Select placeholder="请选择层数">
                  <Option value={1}>单层板</Option>
                  <Option value={2}>双层板</Option>
                  <Option value={4}>4层板</Option>
                  <Option value={6}>6层板</Option>
                  <Option value={8}>8层板</Option>
                  <Option value={10}>10层板</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="board_thickness"
                label="板厚(mm)"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="例如: 1.6"
                  min={0}
                  step={0.1}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="copper_thickness"
                label="铜厚(oz)"
              >
                <Select placeholder="请选择铜厚">
                  <Option value={0.5}>0.5 oz</Option>
                  <Option value={1}>1 oz</Option>
                  <Option value={1.5}>1.5 oz</Option>
                  <Option value={2}>2 oz</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="surface_treatment"
                label="表面处理"
              >
                <Select placeholder="请选择表面处理">
                  <Option value="hasl">喷锡(HASL)</Option>
                  <Option value="enigma">沉金(ENIG)</Option>
                  <Option value="osp">有机保焊膜(OSP)</Option>
                  <Option value="immersion-silver">沉银</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="solder_mask_color"
                label="阻焊颜色"
              >
                <Select placeholder="请选择阻焊颜色">
                  <Option value="green">绿色</Option>
                  <Option value="blue">蓝色</Option>
                  <Option value="red">红色</Option>
                  <Option value="black">黑色</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="legend_color"
                label="字符颜色"
              >
                <Select placeholder="请选择字符颜色">
                  <Option value="white">白色</Option>
                  <Option value="black">黑色</Option>
                  <Option value="yellow">黄色</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="delivery_size"
                label="交货尺寸(mm)"
              >
                <Input placeholder="例如: 200x150" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="panel_method"
                label="拼板方式"
              >
                <Input placeholder="例如: 2x2" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="test_requirement"
                label="测试要求"
              >
                <Select placeholder="请选择测试要求">
                  <Option value="fly-probe">飞针测试</Option>
                  <Option value="fixture">测试架测试</Option>
                  <Option value="aoi">AOI测试</Option>
                  <Option value="none">无需测试</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="special_requirements"
            label="特殊要求"
          >
            <TextArea rows={3} placeholder="请输入特殊工艺要求或注意事项" />
          </Form.Item>

          <Card 
            title="MI指令集" 
            style={{ marginTop: '20px' }}
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAddInstruction}
              >
                添加指令
              </Button>
            }
          >
            <Table
              columns={instructionColumns}
              dataSource={[...instructions].sort((a, b) => a.sequence - b.sequence)}
              rowKey="sequence"
              pagination={false}
              size="small"
              locale={{
                emptyText: '暂无指令，请点击"添加指令"按钮添加'
              }}
            />
          </Card>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>

          <div style={{ 
            padding: '20px', 
            borderTop: '1px solid hsl(var(--line))', 
            backgroundColor: 'hsl(var(--surface-hover))',
            marginTop: '20px',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '10px'
          }}>
            <Button onClick={() => navigate('/eng/mis')}>
              取消
            </Button>
            <Button onClick={() => form.resetFields()}>
              重置表单
            </Button>
            <Button type="primary" onClick={onFinish} loading={loading}>
              保存草稿
            </Button>
            <Button type="primary" onClick={handleSubmit} loading={loading} style={{ backgroundColor: 'hsl(var(--chart-success))', borderColor: 'hsl(var(--chart-success))' }}>
              提交审核
            </Button>
          </div>
        </Form>

        <Modal
          title={editingInstruction ? '编辑指令' : '添加指令'}
          open={instructionModalVisible}
          onCancel={() => {
            setInstructionModalVisible(false)
            instructionForm.resetFields()
            setEditingInstruction(null)
          }}
          onOk={handleSaveInstruction}
          width={600}
        >
          <Form
            form={instructionForm}
            layout="vertical"
          >
            <Form.Item
              name="operation_code"
              label="工序代码"
            >
              <Input placeholder="请输入工序代码（参考工艺路线工序）" />
            </Form.Item>

            <Form.Item
              name="operation_name"
              label="工序名称"
            >
              <Input placeholder="请输入工序名称（参考工艺路线工序）" />
            </Form.Item>

            <Form.Item
              name="instruction_type"
              label="指令类型"
              rules={[{ required: true, message: '请输入指令类型' }]}
            >
              <Select 
                placeholder="请选择或输入指令类型"
                showSearch
                allowClear
                mode="tags"
                tokenSeparators={[',']}
                notFoundContent={null}
              >
                <Option value="开料">开料</Option>
                <Option value="钻孔">钻孔</Option>
                <Option value="沉铜">沉铜</Option>
                <Option value="图形转移">图形转移</Option>
                <Option value="电镀">电镀</Option>
                <Option value="蚀刻">蚀刻</Option>
                <Option value="阻焊">阻焊</Option>
                <Option value="字符">字符</Option>
                <Option value="表面处理">表面处理</Option>
                <Option value="成型">成型</Option>
                <Option value="测试">测试</Option>
                <Option value="包装">包装</Option>
                <Option value="其他">其他</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="instruction_content"
              label="指令内容"
              rules={[{ required: true, message: '请输入指令内容' }]}
            >
              <TextArea 
                rows={4} 
                placeholder="请输入详细的指令内容，例如：开料尺寸、钻孔参数、电镀要求等"
              />
            </Form.Item>

            <Form.Item
              name="description"
              label="说明"
            >
              <TextArea 
                rows={3} 
                placeholder="请输入指令的说明或注意事项（可选）"
              />
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  )
}

export default MIForm

