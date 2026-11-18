import { useEffect, useState } from 'react'
import { Card, Table, Tabs, Tag, message } from 'antd'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { RESOURCE_STATUS, StatusTag } from './shared'

const parseWorkdays = (value: string | null | undefined): string => {
  if (!value) return '-'
  const names: Record<string, string> = { '1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '日' }
  return value
    .split(',')
    .map((day) => names[day.trim()] ?? day.trim())
    .join('、')
}

const ResourceTable: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/aps/resources', { params: { limit: 200 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取资源失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [])

  const columns = [
    { title: '资源编码', dataIndex: 'resource_id', key: 'resource_id', width: 150 },
    { title: '资源名称', dataIndex: 'resource_name', key: 'resource_name', width: 180 },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'wc', width: 110 },
    {
      title: '类型',
      dataIndex: 'resource_type',
      key: 'type',
      width: 100,
      render: (value: string) => (value === 'MACHINE' ? '设备' : value === 'LABOR' ? '人力' : value),
    },
    { title: '班次产能(h)', dataIndex: 'capacity_per_shift', align: 'right' as const, width: 110 },
    {
      title: '班次',
      key: 'shift',
      width: 120,
      render: (_: any, row: any) => `${row.shift_start ?? '08:00'} ~ ${row.shift_end ?? '20:00'}`,
    },
    { title: '工作日', key: 'workdays', width: 160, render: (_: any, row: any) => parseWorkdays(row.workdays) },
    {
      title: '能力标签',
      dataIndex: 'skill_tags',
      key: 'tags',
      render: (value: string | null) =>
        value
          ? value
              .split(',')
              .filter(Boolean)
              .map((tag) => (
                <Tag key={tag} color="blue">
                  {tag}
                </Tag>
              ))
          : '-',
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (value: string) => <StatusTag value={value} map={RESOURCE_STATUS} /> },
  ]

  return (
    <Table
      rowKey="resource_id"
      size="small"
      columns={columns}
      dataSource={rows}
      loading={loading}
      pagination={false}
      scroll={{ x: 1100 }}
    />
  )
}

const SkillTable: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api
      .get('/planning/aps/skills', { params: { limit: 200 } })
      .then((response) => setRows(response.data.items ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [])

  const columns = [
    { title: '技能编号', dataIndex: 'skill_id', key: 'skill_id', width: 120 },
    { title: '资源编码', dataIndex: 'resource_id', key: 'resource', width: 160 },
    { title: '技能编码', dataIndex: 'skill_code', key: 'code', width: 120, render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: '技能名称', dataIndex: 'skill_name', key: 'name', ellipsis: true },
    {
      title: '熟练度',
      dataIndex: 'proficiency',
      key: 'proficiency',
      width: 160,
      render: (value: number) => {
        const pctValue = Math.round(Number(value ?? 0) * 100)
        const color = pctValue >= 90 ? '#52c41a' : pctValue >= 70 ? '#faad14' : '#ff4d4f'
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3 }}>
              <div style={{ width: `${pctValue}%`, height: 6, background: color, borderRadius: 3 }} />
            </div>
            <span style={{ fontSize: 12 }}>{pctValue}%</span>
          </div>
        )
      },
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  ]

  return <Table rowKey="skill_id" size="small" columns={columns} dataSource={rows} loading={loading} pagination={false} />
}

const ChangeoverTable: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api
      .get('/planning/aps/changeovers', { params: { limit: 200 } })
      .then((response) => setRows(response.data.items ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [])

  const columns = [
    { title: '换产编号', dataIndex: 'changeover_id', key: 'changeover_id', width: 120 },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'wc', width: 120 },
    {
      title: '换产方向',
      key: 'direction',
      render: (_: any, row: any) => (
        <span>
          <Tag>{row.from_operation}</Tag> → <Tag>{row.to_operation}</Tag>
        </span>
      ),
    },
    {
      title: '换产时间',
      dataIndex: 'changeover_minutes',
      key: 'minutes',
      width: 140,
      render: (value: number) => (
        <span style={{ color: Number(value) > 30 ? '#cf1322' : undefined, fontWeight: Number(value) > 30 ? 600 : 400 }}>
          {value} 分钟{Number(value) > 30 ? '（超阈值 30m）' : ''}
        </span>
      ),
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  ]

  return <Table rowKey="changeover_id" size="small" columns={columns} dataSource={rows} loading={loading} pagination={false} />
}

const CalendarTable: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api
      .get('/planning/aps/calendars')
      .then((response) => setRows(response.data.items ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [])

  const columns = [
    { title: '日历编号', dataIndex: 'calendar_id', key: 'calendar_id', width: 140 },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'wc', width: 120 },
    {
      title: '班次',
      key: 'shift',
      width: 140,
      render: (_: any, row: any) => `${row.shift_start} ~ ${row.shift_end}`,
    },
    { title: '休息(h)', dataIndex: 'break_hours', align: 'right' as const, width: 90 },
    { title: '有效产能(h)', dataIndex: 'capacity_hours', align: 'right' as const, width: 110 },
    {
      title: '利用率',
      dataIndex: 'utilization',
      key: 'utilization',
      width: 140,
      render: (value: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3 }}>
            <div style={{ width: `${Math.min(100, Number(value ?? 0))}%`, height: 6, background: '#1677ff', borderRadius: 3 }} />
          </div>
          <span style={{ fontSize: 12 }}>{Number(value ?? 0)}%</span>
        </div>
      ),
    },
    { title: '工作日', key: 'workdays', render: (_: any, row: any) => parseWorkdays(row.workdays) },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v === 'ACTIVE' ? '启用' : v}</Tag> },
  ]

  return <Table rowKey="calendar_id" size="small" columns={columns} dataSource={rows} loading={loading} pagination={false} />
}

const ApsMasterData: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="排程主数据"
        description="设备资源 / 人员技能矩阵 / 换产矩阵 / 工作日历 —— 有限产能排程的四类约束基础"
      />
      <Card size="small">
        <Tabs
          items={[
            { key: 'resources', label: '设备资源', children: <ResourceTable /> },
            { key: 'skills', label: '技能矩阵', children: <SkillTable /> },
            { key: 'changeovers', label: '换产矩阵', children: <ChangeoverTable /> },
            { key: 'calendars', label: '工作日历', children: <CalendarTable /> },
          ]}
        />
      </Card>
    </div>
  )
}

export default ApsMasterData
