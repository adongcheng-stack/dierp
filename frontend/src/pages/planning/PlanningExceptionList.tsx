import { useEffect, useState } from 'react'
import { Button, Input, Modal, Select, Space, Table, message } from 'antd'
import { CheckCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  EXCEPTION_TYPE,
  fmtDate,
  fmtQty,
  RESOLUTION,
  SEVERITY,
  StatusTag,
} from './shared'

const PlanningExceptionList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [runNumber, setRunNumber] = useState<string | undefined>()
  const [severity, setSeverity] = useState<string | undefined>()
  const [resolution, setResolution] = useState<string | undefined>('OPEN')
  const [target, setTarget] = useState<any | null>(null)
  const [remarks, setRemarks] = useState('')
  const [resolveStatus, setResolveStatus] = useState('RESOLVED')

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/exceptions', {
        params: {
          run_number: runNumber,
          severity,
          resolution_status: resolution,
          limit: 300,
        },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取异常列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchRuns = async () => {
    try {
      const response = await api.get('/planning/mrp/runs')
      const items = response.data.items ?? []
      setRuns(items)
      if (!runNumber && items.length > 0) setRunNumber(items[0].run_number)
    } catch {
      setRuns([])
    }
  }

  useEffect(() => {
    fetchRuns()
  }, [])

  useEffect(() => {
    fetchRows()
  }, [runNumber, severity, resolution])

  const submitResolve = async () => {
    if (!target) return
    try {
      await api.post(`/planning/exceptions/${target.id}/resolve`, {
        resolution_status: resolveStatus,
        remarks,
      })
      message.success('异常状态已更新')
      setTarget(null)
      setRemarks('')
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '更新异常失败')
    }
  }

  const columns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (value: string) => <StatusTag value={value} map={SEVERITY} />,
    },
    {
      title: '异常类型',
      dataIndex: 'exception_type',
      key: 'exception_type',
      width: 120,
      render: (value: string) => EXCEPTION_TYPE[value] ?? value,
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    { title: '需求来源', dataIndex: 'requirement_ref', key: 'requirement_ref', width: 170 },
    {
      title: '短缺量',
      dataIndex: 'shortage_qty',
      key: 'shortage_qty',
      align: 'right' as const,
      width: 100,
      render: (value: number) => (value ? fmtQty(value) : '-'),
    },
    {
      title: '需求日期',
      dataIndex: 'shortage_date',
      key: 'shortage_date',
      width: 110,
      render: (value: string) => fmtDate(value),
    },
    { title: '处理建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
    {
      title: '处理状态',
      dataIndex: 'resolution_status',
      key: 'resolution_status',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={RESOLUTION} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: any) =>
        record.resolution_status === 'OPEN' || record.resolution_status === 'ACKNOWLEDGED' ? (
          <Button type="link" icon={<CheckCircleOutlined />} onClick={() => setTarget(record)}>
            处理
          </Button>
        ) : (
          <span className="text-ink-soft">已处理</span>
        ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="计划异常"
        description="MRP 运行产生的短缺、缺 BOM、提前期违规等异常，处理后形成计划闭环"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
            刷新
          </Button>
        }
      />

      <Space wrap className="mb-4">
        <Select
          allowClear
          style={{ width: 230 }}
          placeholder="MRP 批次"
          value={runNumber}
          onChange={setRunNumber}
          options={runs.map((item) => ({
            value: item.run_number,
            label: item.run_number,
          }))}
        />
        <Select
          allowClear
          style={{ width: 140 }}
          placeholder="级别"
          value={severity}
          onChange={setSeverity}
          options={[
            { value: 'CRITICAL', label: '严重' },
            { value: 'WARNING', label: '警告' },
            { value: 'INFO', label: '提示' },
          ]}
        />
        <Select
          allowClear
          style={{ width: 140 }}
          placeholder="处理状态"
          value={resolution}
          onChange={setResolution}
          options={[
            { value: 'OPEN', label: '待处理' },
            { value: 'ACKNOWLEDGED', label: '已确认' },
            { value: 'RESOLVED', label: '已解决' },
            { value: 'IGNORED', label: '已忽略' },
          ]}
        />
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title="处理计划异常"
        open={Boolean(target)}
        onOk={submitResolve}
        onCancel={() => setTarget(null)}
        okText="提交"
        destroyOnClose
      >
        {target && (
          <div className="space-y-3">
            <div className="rounded-md bg-surface-sunken px-3 py-2 text-sm">
              <div className="font-medium text-ink">
                {EXCEPTION_TYPE[target.exception_type] ?? target.exception_type} ·{' '}
                {target.material_code}
              </div>
              <div className="mt-1 text-ink-soft">{target.suggestion}</div>
            </div>
            <div>
              <div className="mb-1 text-sm text-ink-soft">处理结果</div>
              <Select
                style={{ width: '100%' }}
                value={resolveStatus}
                onChange={setResolveStatus}
                options={[
                  { value: 'RESOLVED', label: '已解决' },
                  { value: 'ACKNOWLEDGED', label: '已知悉，继续跟踪' },
                  { value: 'IGNORED', label: '忽略' },
                ]}
              />
            </div>
            <div>
              <div className="mb-1 text-sm text-ink-soft">处理说明</div>
              <Input.TextArea
                rows={3}
                value={remarks}
                onChange={(event) => setRemarks(event.target.value)}
                placeholder="例如：已联系供应商提前到货 / 已调整计划订单批量"
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default PlanningExceptionList
