import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, Switch } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select

interface UserFormData {
  username?: string
  email: string
  password?: string
  full_name?: string
  role: string
  department?: string
  phone?: string
  is_active: boolean
}

const UserForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [roles, setRoles] = useState<any[]>([])
  const [loadingRoles, setLoadingRoles] = useState(false)
  const [departments, setDepartments] = useState<any[]>([])
  const isEdit = !!id

  useEffect(() => {
    fetchRoles()
    fetchDepartments()
    if (isEdit) {
      fetchUser()
    }
  }, [id])

  const fetchDepartments = async () => {
    try {
      const response = await api.get('/system/departments')
      setDepartments(response.data?.items || [])
    } catch (error: any) {
      console.error('获取部门列表失败:', error)
    }
  }

  const fetchRoles = async () => {
    setLoadingRoles(true)
    try {
      const response = await api.get('/roles')
      setRoles(response.data || [])
    } catch (error: any) {
      console.error('获取角色列表失败:', error)
      message.error('获取角色列表失败')
    } finally {
      setLoadingRoles(false)
    }
  }

  const fetchUser = async () => {
    try {
      const response = await api.get(`/users/${id}`)
      const user = response.data
      form.setFieldsValue({
        username: user.username,
        email: user.email,
        full_name: user.full_name,
        role: user.role,
        department: user.department,
        phone: user.phone,
        is_active: user.is_active
      })
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取用户信息失败')
      navigate('/admin/users')
    }
  }

  const onFinish = async (values: UserFormData) => {
    setLoading(true)
    try {
      const formData: any = {
        email: values.email,
        full_name: values.full_name,
        role: values.role,
        department: values.department,
        phone: values.phone,
        is_active: values.is_active
      }

      // 只有新建或修改密码时才包含密码字段
      if (!isEdit || values.password) {
        if (!values.password) {
          message.error('请输入密码')
          setLoading(false)
          return
        }
        formData.password = values.password
      }

      if (isEdit) {
        await api.put(`/users/${id}`, formData)
        message.success('用户更新成功')
      } else {
        if (!values.username) {
          message.error('请输入用户名')
          setLoading(false)
          return
        }
        formData.username = values.username
        await api.post('/users', formData)
        message.success('用户创建成功')
      }
      navigate('/admin/users')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑用户' : '新建用户'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            is_active: true
          }}
        >
          {!isEdit && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="username"
                  label="用户名"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <Input placeholder="请输入用户名" />
                </Form.Item>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="email"
                label="邮箱"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' }
                ]}
              >
                <Input placeholder="请输入邮箱" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="password"
                label={isEdit ? '密码（留空则不修改）' : '密码'}
                rules={!isEdit ? [{ required: true, message: '请输入密码' }] : []}
              >
                <Input.Password placeholder={isEdit ? '留空则不修改密码' : '请输入密码'} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="full_name"
                label="姓名"
              >
                <Input placeholder="请输入姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="role"
                label="角色"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select
                  placeholder="请选择角色"
                  loading={loadingRoles}
                  disabled={loadingRoles}
                >
                  {roles.map(role => (
                    <Option key={role.role} value={role.role}>
                      {role.name} - {role.description}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="department"
                label="部门"
              >
                <Select placeholder="选择所属部门" allowClear showSearch
                  optionFilterProp="children"
                  options={departments.map((dept) => ({ label: dept.name, value: dept.name }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="电话"
              >
                <Input placeholder="请输入电话" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="状态"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/admin/users')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default UserForm

