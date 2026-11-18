import { Form, Input, Button, Card, Space, App as AntdApp, Row, Col, Table, Modal, Select } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const { TextArea } = Input
const { Option } = Select

interface LotCardInstruction {
  id?: number
  sequence: number
  operation_code?: string  // 工序代码（参考工艺路线工序）
  operation_name?: string  // 工序名称（参考工艺路线工序）
  instruction_type: string
  instruction_content: string
  description?: string
}

interface LotCardFormData {
  remarks?: string | null
  instructions?: LotCardInstruction[]
}

const LotCardForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const [instructionForm] = Form.useForm()
  const navigate = useNavigate()
  const { lotNumber } = useParams<{ lotNumber?: string }>()
  const [loading, setLoading] = useState(false)
  const [lotCard, setLotCard] = useState<any>(null)
  const [instructions, setInstructions] = useState<LotCardInstruction[]>([])
  const [editingInstruction, setEditingInstruction] = useState<LotCardInstruction | null>(null)
  const [instructionModalVisible, setInstructionModalVisible] = useState(false)
  const isEdit = !!lotNumber

  useEffect(() => {
    if (isEdit) {
      fetchLotCard()
    }
  }, [lotNumber])

  const fetchLotCard = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/pp/lot-cards/by-lot-number/${lotNumber}`)
      const data = response.data
      setLotCard(data)
      
      // 加载指令项列表，确保数据类型正确
      if (data.instructions && Array.isArray(data.instructions)) {
        // 确保所有字段都是正确的类型
        const normalizedInstructions = data.instructions.map((inst: any) => ({
          id: inst.id,
          sequence: Number(inst.sequence) || 0,
          operation_code: inst.operation_code ? String(inst.operation_code) : undefined,
          operation_name: inst.operation_name ? String(inst.operation_name) : undefined,
          instruction_type: String(inst.instruction_type || ''),
          instruction_content: String(inst.instruction_content || ''),
          description: inst.description ? String(inst.description) : undefined
        }))
        setInstructions(normalizedInstructions)
      } else {
        setInstructions([])
      }
      
      form.setFieldsValue({
        remarks: data.remarks || ''
      })
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '获取LOT卡信息失败'
      message.error(errorMsg)
      console.error('获取LOT卡信息失败:', error)
      navigate('/pp/lot-cards')
    } finally {
      setLoading(false)
    }
  }

  // 添加指令项
  const handleAddInstruction = () => {
    setEditingInstruction(null)
    instructionForm.resetFields()
    setInstructionModalVisible(true)
  }

  // 编辑指令项
  const handleEditInstruction = (instruction: LotCardInstruction) => {
    setEditingInstruction(instruction)
    instructionForm.setFieldsValue(instruction)
    setInstructionModalVisible(true)
  }

  // 删除指令项
  const handleDeleteInstruction = (sequence: number) => {
    const newInstructions = instructions.filter(inst => inst.sequence !== sequence)
    // 重新排序序号
    const sortedInstructions = newInstructions.map((inst, index) => ({
      ...inst,
      sequence: index + 1
    }))
    setInstructions(sortedInstructions)
    message.success('指令项已删除')
  }

  // 保存指令项
  const handleSaveInstruction = () => {
    instructionForm.validateFields().then(values => {
      // 确保数据类型正确
      const normalizedValues = {
        sequence: Number(values.sequence) || 0,
        operation_code: values.operation_code ? String(values.operation_code).trim() : undefined,
        operation_name: values.operation_name ? String(values.operation_name).trim() : undefined,
        instruction_type: String(values.instruction_type || '').trim(),
        instruction_content: String(values.instruction_content || '').trim(),
        description: values.description ? String(values.description).trim() : undefined
      }
      
      if (editingInstruction) {
        // 更新现有指令项
        setInstructions(instructions.map(inst => 
          inst.sequence === editingInstruction.sequence 
            ? { ...inst, ...normalizedValues }
            : inst
        ))
        message.success('指令项已更新')
      } else {
        // 添加新指令项
        const maxSequence = instructions.length > 0 
          ? Math.max(...instructions.map(inst => inst.sequence))
          : 0
        const newInstructions = [...instructions, { 
          ...normalizedValues, 
          sequence: maxSequence + 1 
        }]
        // 按序号排序
        newInstructions.sort((a, b) => a.sequence - b.sequence)
        setInstructions(newInstructions)
        message.success('指令项已添加')
      }
      setInstructionModalVisible(false)
      instructionForm.resetFields()
      setEditingInstruction(null)
    }).catch(() => {
      message.error('请填写所有必填字段')
    })
  }

  // 表格列定义
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
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: LotCardInstruction) => (
        <Space>
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
  ]

  const onFinish = async (values: LotCardFormData) => {
    setLoading(true)
    try {
      // 验证指令项序号唯一性
      const sequences = instructions.map(inst => inst.sequence)
      const uniqueSequences = new Set(sequences)
      if (sequences.length !== uniqueSequences.size) {
        message.error('指令项序号不能重复，请检查并修改')
        setLoading(false)
        return
      }

      // 验证必填字段
      for (const inst of instructions) {
        const instructionType = inst.instruction_type
        const instructionContent = inst.instruction_content
        
        if (!instructionType || (typeof instructionType === 'string' && !instructionType.trim())) {
          message.error(`指令项 #${inst.sequence} 的指令类型不能为空`)
          setLoading(false)
          return
        }
        if (!instructionContent || (typeof instructionContent === 'string' && !instructionContent.trim())) {
          message.error(`指令项 #${inst.sequence} 的指令内容不能为空`)
          setLoading(false)
          return
        }
      }

      const payload: LotCardFormData = {
        remarks: values.remarks?.trim() || null,
        instructions: instructions.map(inst => ({
          sequence: inst.sequence,
          instruction_type: String(inst.instruction_type || '').trim(),
          instruction_content: String(inst.instruction_content || '').trim(),
          description: inst.description ? String(inst.description).trim() : ''
        }))
      }

      await api.put(`/pp/lot-cards/${lotNumber}`, payload)
      message.success('LOT卡更新成功')
      navigate('/pp/lot-cards')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '更新LOT卡失败'
      message.error(errorMsg)
      console.error('更新LOT卡失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title={isEdit ? '编辑LOT卡' : '新建LOT卡'}
        description={isEdit ? '修改LOT卡内容和备注信息' : 'LOT卡由系统自动生成，不支持手动创建'}
      />
      <Card>
        {lotCard && (
          <Card size="small" style={{ marginBottom: 24, backgroundColor: 'hsl(var(--surface-hover))' }}>
            <Row gutter={[16, 8]}>
              <Col span={12}>
                <strong>LOT卡号：</strong>{lotCard.lot_number}
              </Col>
              <Col span={12}>
                <strong>生产订单号：</strong>{lotCard.production_order_number}
              </Col>
              <Col span={12}>
                <strong>MI编号：</strong>{lotCard.mi_number}
              </Col>
              <Col span={12}>
                <strong>物料编码：</strong>{lotCard.material_code}
              </Col>
              <Col span={12}>
                <strong>数量：</strong>{lotCard.quantity} {lotCard.unit}
              </Col>
              <Col span={12}>
                <strong>状态：</strong>{lotCard.status}
              </Col>
            </Row>
          </Card>
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          disabled={loading}
        >
          <Card 
            title="MI指令项" 
            style={{ marginBottom: 24 }}
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAddInstruction}
              >
                添加指令项
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
                emptyText: '暂无指令项，请点击"添加指令项"按钮添加'
              }}
            />
          </Card>

          <Form.Item
            label="备注"
            name="remarks"
            tooltip="可在此添加LOT卡的备注说明"
          >
            <TextArea
              rows={4}
              placeholder="请输入备注信息"
              maxLength={1000}
              showCount
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                保存
              </Button>
              <Button onClick={() => navigate('/pp/lot-cards')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* 编辑指令项Modal */}
      <Modal
        title={editingInstruction ? '编辑指令项' : '添加指令项'}
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
          {editingInstruction && (
            <Form.Item name="sequence" label="序号" rules={[{ required: true }]}>
              <Input type="number" disabled />
            </Form.Item>
          )}
          <Form.Item name="operation_code" label="工序代码">
            <Input placeholder="请输入工序代码（参考工艺路线工序）" />
          </Form.Item>
          <Form.Item name="operation_name" label="工序名称">
            <Input placeholder="请输入工序名称（参考工艺路线工序）" />
          </Form.Item>
          <Form.Item name="instruction_type" label="指令类型" rules={[{ required: true, message: '请输入指令类型' }]}>
            <Select 
              placeholder="请选择或输入指令类型"
              showSearch
              allowClear
              mode="tags"
              tokenSeparators={[',']}
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
            </Select>
          </Form.Item>
          <Form.Item name="instruction_content" label="指令内容" rules={[{ required: true, message: '请输入指令内容' }]}>
            <TextArea rows={6} placeholder="请输入详细的指令内容，例如：开料尺寸、钻孔参数、电镀要求等" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <TextArea rows={3} placeholder="请输入指令的说明或注意事项（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default LotCardForm
