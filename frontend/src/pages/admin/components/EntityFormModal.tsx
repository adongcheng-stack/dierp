import { useEffect } from 'react'
import { Form, Input, InputNumber, Modal, Select, Switch } from 'antd'

export interface FieldDef {
  name: string
  label: string
  type?: 'text' | 'textarea' | 'number' | 'select' | 'switch'
  options?: Array<{ label: string; value: string | number }>
  required?: boolean
  placeholder?: string
}

interface Props {
  open: boolean
  title: string
  fields: FieldDef[]
  initial?: Record<string, any> | null
  onOk: (values: Record<string, any>) => Promise<void> | void
  onCancel: () => void
}

/** 系统管理通用新增/编辑弹窗：字段由本体模型对应的 FieldDef 声明驱动。 */
export function EntityFormModal({ open, title, fields, initial, onOk, onCancel }: Props) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (open) form.setFieldsValue(initial ?? {})
  }, [open, initial, form])

  const submit = async () => {
    const values = await form.validateFields()
    await onOk(values)
  }

  return (
    <Modal open={open} title={title} onOk={submit} onCancel={onCancel} destroyOnClose>
      <Form form={form} layout="vertical" preserve={false}>
        {fields.map((field) => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            rules={field.required ? [{ required: true, message: `请输入${field.label}` }] : undefined}
          >
            {field.type === 'number' ? (
              <InputNumber className="w-full" />
            ) : field.type === 'select' ? (
              <Select options={field.options} allowClear />
            ) : field.type === 'switch' ? (
              <Switch />
            ) : field.type === 'textarea' ? (
              <Input.TextArea rows={3} />
            ) : (
              <Input placeholder={field.placeholder} />
            )}
          </Form.Item>
        ))}
      </Form>
    </Modal>
  )
}
