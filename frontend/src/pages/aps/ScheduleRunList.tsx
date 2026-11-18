import { useEffect, useState } from 'react'
import { Button, Descriptions, Drawer, Modal, Space, Table, Tag, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { ALGORITHM, RUN_STATUS, SOURCE_TYPE, StatusTag, fmtDateTime } from './shared'

const ScheduleRunList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [publishTarget, setPublishTarget] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/aps/runs', { params: { limit: 200 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取排程批次失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [])

  const openDetail = async (runNumber: string) => {
    try {
      const response = await api.get(`/planning/aps/runs/${runNumber}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取批次详情失败')
    }
  }

  const publish = async (runNumber: string) => {
    setBusy(true)
    try {
      await api.post(`/planning/aps/runs/${runNumber}/publish`)
      message.success(`批次 ${runNumber} 已发布`)
      setPublishTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '发布失败')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { title: '批次号', dataIndex: 'run_number', key: 'run_number', width: 170 },
    { title: '批次名称', dataIndex: 'run_name', key: 'run_name', ellipsis: true },
    {
      title: '算法',
      dataIndex: 'algorithm',
      key: 'algorithm',
      width: 170,
      render: (value: string) => ALGORITHM[value] ?? value,
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (value: string) => <StatusTag value={value} map={RUN_STATUS} /> },
    { title: '来源', dataIndex: 'source_type', key: 'source_type', width: 110, render: (value: string) => SOURCE_TYPE[value] ?? value },
    {
      title: '排程窗口',
      key: 'horizon',
      width: 260,
      render: (_: any, row: any) => `${fmtDateTime(row.horizon_start)} ~ ${fmtDateTime(row.horizon_end)}`,
    },
    { title: '工序数', dataIndex: 'operation_count', key: 'operation_count', align: 'right' as const, width: 90 },
    {
      title: '异常数',
      dataIndex: 'exception_count',
      key: 'exception_count',
      align: 'right' as const,
      width: 90,
      render: (value: number) => (value > 0 ? <span style={{ color: '#cf1322', fontWeight: 600 }}>{value}</span> : value),
    },
    { title: '发布时间', dataIndex: 'published_at', key: 'published_at', width: 160, render: fmtDateTime },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, row: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => openDetail(row.run_number)}>
            详情
          </Button>
          {row.status === 'COMPLETED' && (
            <Button type="link" size="small" onClick={() => setPublishTarget(row)}>
              发布
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="排程批次"
        description="APS 排程运算批次管理：正排 / 倒排 / 混合排程结果，发布后进入生产执行"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
            刷新
          </Button>
        }
      />

      <Table
        rowKey="run_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1400 }}
      />

      <Drawer
        title={`排程批次 ${detail?.run_number ?? ''}`}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={860}
        destroyOnClose
      >
        {detail && (
          <>
            <Descriptions size="small" column={2} className="mb-4" bordered>
              <Descriptions.Item label="批次名称">{detail.run_name ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <StatusTag value={detail.status} map={RUN_STATUS} />
              </Descriptions.Item>
              <Descriptions.Item label="算法">{ALGORITHM[detail.algorithm] ?? detail.algorithm}</Descriptions.Item>
              <Descriptions.Item label="来源">{SOURCE_TYPE[detail.source_type] ?? detail.source_type}</Descriptions.Item>
              <Descriptions.Item label="排程窗口" span={2}>
                {fmtDateTime(detail.horizon_start)} ~ {fmtDateTime(detail.horizon_end)}
              </Descriptions.Item>
              <Descriptions.Item label="工序数">{detail.operation_count}</Descriptions.Item>
              <Descriptions.Item label="异常数">{detail.exception_count}</Descriptions.Item>
              <Descriptions.Item label="发布时间" span={2}>{fmtDateTime(detail.published_at)}</Descriptions.Item>
            </Descriptions>

            <h4 className="mb-2">排程工序（{detail.operations?.length ?? 0}）</h4>
            <Table
              rowKey="op_id"
              size="small"
              pagination={false}
              scroll={{ y: 320 }}
              dataSource={detail.operations ?? []}
              columns={[
                { title: '工序号', dataIndex: 'op_id', width: 110 },
                { title: '工单', dataIndex: 'production_order_number', width: 170 },
                { title: '物料', dataIndex: 'material_code', width: 150 },
                { title: '工序', dataIndex: 'operation_name', width: 140 },
                { title: '工作中心', dataIndex: 'work_center_id', width: 110 },
                { title: '开始', dataIndex: 'planned_start', width: 150, render: fmtDateTime },
                { title: '结束', dataIndex: 'planned_end', width: 150, render: fmtDateTime },
                {
                  title: '状态',
                  dataIndex: 'status',
                  width: 90,
                  render: (value: string) =>
                    value === 'PUBLISHED' ? <Tag color="green">已发布</Tag> : <Tag>计划</Tag>,
                },
              ]}
            />
          </>
        )}
      </Drawer>

      <Modal
        title="发布排程"
        open={!!publishTarget}
        onCancel={() => setPublishTarget(null)}
        onOk={() => publishTarget && publish(publishTarget.run_number)}
        confirmLoading={busy}
        okText="发布"
      >
        <p>
          确认发布批次 <strong>{publishTarget?.run_number}</strong>？发布后工序状态变为「已发布」，可作为生产执行依据。
        </p>
      </Modal>
    </div>
  )
}

export default ScheduleRunList
