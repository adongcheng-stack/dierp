import { Table, Button, Tag, Space, App as AntdApp, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const UserList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const response = await api.get('/users', {
        timeout: 30000 // 单独设置超时时间
      })
      setUsers(response.data || [])
    } catch (error: any) {
      console.error('获取用户列表失败:', error)
      if (error.code === 'ECONNABORTED') {
        message.error('请求超时，请检查后端服务是否正常运行')
      } else if (error.response) {
        message.error(error.response?.data?.detail || '获取用户列表失败')
      } else if (error.request) {
        message.error('无法连接到服务器，请检查后端服务是否运行')
      } else {
        message.error('获取用户列表失败')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (userId: number) => {
    try {
      await api.delete(`/users/${userId}`)
      message.success('用户已删除')
      fetchUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const getRoleTag = (role: string) => {
    const roleMap: { [key: string]: { color: string; text: string } } = {
      'SALES': { color: 'blue', text: '销售' },
      'SALES_MANAGER': { color: 'cyan', text: '销售经理' },
      'ENGINEER': { color: 'green', text: '工程' },
      'PLANNER': { color: 'orange', text: '计划' },
      'PRODUCTION': { color: 'purple', text: '生产' },
      'WAREHOUSE': { color: 'geekblue', text: '仓库' },
      'FINANCE': { color: 'gold', text: '财务' },
      'GENERAL_MANAGER': { color: 'red', text: '总经理' },
      'ADMIN': { color: 'volcano', text: '系统管理员' }
    }
    const roleInfo = roleMap[role] || { color: 'default', text: role }
    return <Tag color={roleInfo.color}>{roleInfo.text}</Tag>
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role',
      render: (role: string) => getRoleTag(role)
    },
    { title: '部门', dataIndex: 'department', key: 'department' },
    { title: '电话', dataIndex: 'phone', key: 'phone' },
    { 
      title: '状态', 
      dataIndex: 'is_active', 
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/admin/users/${record.id}/edit`)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除此用户吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="用户管理"
        description="维护系统账号与角色权限"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/admin/users/new')}
          >
            新建用户
          </Button>
        }
      />
      <Table
        columns={columns}
        dataSource={users}
        loading={loading}
        rowKey="id"
      />
    </div>
  )
}

export default UserList

