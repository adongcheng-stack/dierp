import { useCallback, useEffect, useState } from 'react'
import { App as AntdApp, Input, Table, Tag } from 'antd'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface LoginLogRow {
  id: number
  username: string
  role?: string | null
  login_status: string
  message?: string | null
  ip_address?: string | null
  user_agent?: string | null
  login_time: string
}

/** 登录日志：登录成功/失败事实流（append-only），仅 ADMIN 可查。 */
const LoginLogList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [rows, setRows] = useState<LoginLogRow[]>([])
  const [loading, setLoading] = useState(false)
  const [username, setUsername] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/system/login-logs', { params: username ? { username } : {} })
      setRows(res.data?.items ?? [])
    } catch (error: any) { message.error(error?.userMessage ?? '加载登录日志失败') }
    finally { setLoading(false) }
  }, [message, username])
  useEffect(() => { void load() }, [load])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '时间', dataIndex: 'login_time', width: 180,
      render: (v: string) => v?.replace('T', ' ').slice(0, 19) ?? '-' },
    { title: '账号', dataIndex: 'username', width: 130 },
    { title: '角色', dataIndex: 'role', width: 140, render: (v: string | null) => v ?? '-' },
    { title: '结果', dataIndex: 'login_status', width: 100,
      render: (v: string) => <Tag color={v === 'SUCCESS' ? 'green' : 'red'}>{v}</Tag> },
    { title: '说明', dataIndex: 'message', ellipsis: true },
    { title: 'IP', dataIndex: 'ip_address', width: 130 },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="登录日志" description="登录成功与失败的事实记录，支持按账号筛选（仅管理员）" />
      <Input.Search allowClear placeholder="按账号筛选" className="w-56"
        onSearch={setUsername} onChange={(e) => { if (!e.target.value) setUsername('') }} />
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading}
        pagination={{ pageSize: 20 }} size="middle" />
    </div>
  )
}

export default LoginLogList
