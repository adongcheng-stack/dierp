import { Table, Tag, Input, Select, Space, App as AntdApp } from 'antd'
import { useEffect, useState } from 'react'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface OperationLogRow {
  id: number
  request_id: string
  username: string | null
  role: string | null
  method: string
  path: string
  status_code: number
  client_ip: string | null
  created_at: string | null
}

const METHOD_COLOR: Record<string, string> = {
  POST: 'green',
  PUT: 'blue',
  PATCH: 'cyan',
  DELETE: 'red',
}

/** 审计日志：写操作事实流（append-only），仅 ADMIN 可见。 */
const OperationLogList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [rows, setRows] = useState<OperationLogRow[]>([])
  const [loading, setLoading] = useState(false)
  const [username, setUsername] = useState<string | undefined>()
  const [method, setMethod] = useState<string | undefined>()

  const fetchLogs = async (
    filters?: { username?: string; method?: string },
  ) => {
    const activeUsername = filters ? filters.username : username
    const activeMethod = filters ? filters.method : method
    setLoading(true)
    try {
      const response = await api.get('/admin/operation-logs', {
        params: {
          ...(activeUsername ? { username: activeUsername } : {}),
          ...(activeMethod ? { method: activeMethod } : {}),
          limit: 200,
        },
      })
      setRows(response.data?.items ?? [])
    } catch (error: any) {
      message.error(error?.userMessage ?? error?.response?.data?.detail ?? '获取审计日志失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchLogs()
  }, [])

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 72 },
    {
      title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180,
      render: (value: string | null) => value?.replace('T', ' ').slice(0, 19) ?? '-',
    },
    {
      title: '操作人', dataIndex: 'username', key: 'username', width: 120,
      render: (value: string | null) => value ?? '匿名',
    },
    { title: '角色', dataIndex: 'role', key: 'role', width: 140,
      render: (value: string | null) => value ?? '-' },
    {
      title: '方法', dataIndex: 'method', key: 'method', width: 90,
      render: (value: string) => <Tag color={METHOD_COLOR[value] ?? 'default'}>{value}</Tag>,
    },
    { title: '路径', dataIndex: 'path', key: 'path' },
    {
      title: '状态', dataIndex: 'status_code', key: 'status_code', width: 90,
      render: (value: number) => (
        <Tag color={value >= 400 ? 'red' : 'green'}>{value}</Tag>
      ),
    },
    { title: '请求 ID', dataIndex: 'request_id', key: 'request_id', width: 160,
      render: (value: string) => <span className="text-xs text-ink-soft">{value.slice(0, 8)}</span> },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="操作审计日志" description="写操作事实流（append-only），仅管理员可查看" />
      <Space className="flex-wrap">
        <Input.Search
          allowClear
          placeholder="按操作人筛选"
          className="w-56"
          onSearch={(value) => { setUsername(value || undefined); void fetchLogs({ username: value || undefined, method }) }}
        />
        <Select
          allowClear
          placeholder="HTTP 方法"
          className="w-36"
          onChange={(value) => { setMethod(value); void fetchLogs({ username, method: value }) }}
          options={['POST', 'PUT', 'PATCH', 'DELETE'].map((m) => ({ label: m, value: m }))}
        />
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        size="middle"
      />
    </div>
  )
}

export default OperationLogList
