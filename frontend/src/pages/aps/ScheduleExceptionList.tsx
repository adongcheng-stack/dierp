import { useEffect, useState } from 'react'
import { Button, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { EXCEPTION_TYPE, StatusTag, fmtDateTime } from './shared'

const ScheduleExceptionList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [runNumber, setRunNumber] = useState<string | undefined>()
  const [exceptionType, setExceptionType] = useState<string | undefined>()
  const [severity, setSeverity] = useState<string | undefined>()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/aps/exceptions', {
        params: { limit: 500, run_number: runNumber, exception_type: exceptionType, severity },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取排程异常失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [runNumber, exceptionType, severity])

  useEffect(() => {
    api
      .get('/planning/aps/runs', { params: { limit: 100 } })
      .then((response) => setRuns(response.data.items ?? []))
      .catch(() => setRuns([]))
  }, [])

  const columns = [
    { title: '异常编号', dataIndex: 'exception_id', key: 'exception_id', width: 140 },
    { title: '批次', dataIndex: 'run_number', key: 'run_number', width: 160 },
    {
      title: '类型',
      dataIndex: 'exception_type',
      key: 'type',
      width: 120,
      render: (value: string) => <StatusTag value={value} map={EXCEPTION_TYPE} />,
    },
    { title: '工单', dataIndex: 'production_order_number', key: 'order', width: 170 },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'wc', width: 100 },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (value: string) => (value === 'CRITICAL' ? <Tag color="red">严重</Tag> : <Tag color="orange">警告</Tag>),
    },
    {
      title: '说明',
      dataIndex: 'message',
      key: 'message',
      ellipsis: { showTitle: false } as any,
      render: (value: string) => (
        <Tooltip title={value} placement="topLeft">
          {value}
        </Tooltip>
      ),
    },
    {
      title: '建议动作',
      dataIndex: 'suggested_action',
      key: 'action',
      ellipsis: { showTitle: false } as any,
      render: (value: string) => (
        <Tooltip title={value} placement="topLeft">
          {value}
        </Tooltip>
      ),
    },
    { title: '产生时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: fmtDateTime },
  ]

  return (
    <div>
      <PageHeader
        title="排程异常"
        description="产能超载 / 交期风险 / 缺料 / 技能不匹配 / 换产超限 / 资源停机，六类异常统一预警"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
            刷新
          </Button>
        }
      />

      <Space wrap className="mb-4">
        <Select
          allowClear
          style={{ width: 220 }}
          placeholder="按批次筛选"
          value={runNumber}
          onChange={setRunNumber}
          options={runs.map((item) => ({ value: item.run_number, label: item.run_number }))}
        />
        <Select
          allowClear
          style={{ width: 160 }}
          placeholder="按类型筛选"
          value={exceptionType}
          onChange={setExceptionType}
          options={Object.entries(EXCEPTION_TYPE).map(([value, entry]) => ({ value, label: entry.text }))}
        />
        <Select
          allowClear
          style={{ width: 130 }}
          placeholder="按级别筛选"
          value={severity}
          onChange={setSeverity}
          options={[
            { value: 'CRITICAL', label: '严重' },
            { value: 'WARNING', label: '警告' },
          ]}
        />
      </Space>

      <Table
        rowKey="exception_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1400 }}
      />
    </div>
  )
}

export default ScheduleExceptionList
