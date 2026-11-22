import { useEffect, useState } from 'react'
import { Button, Card, Col, Drawer, Form, Input, Modal, Row, Select, Space, Table, Tag, message } from 'antd'
import { ExperimentOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { IMPACT_LEVEL, SCENARIO_TYPE, StatusTag, fmtDateTime } from './shared'

const ScenarioSimulationList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [simulateOpen, setSimulateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()
  const [detail, setDetail] = useState<any>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/aps/scenarios', { params: { limit: 200 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取模拟场景失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
    api
      .get('/planning/aps/runs', { params: { limit: 100 } })
      .then((response) => setRuns(response.data.items ?? []))
      .catch(() => setRuns([]))
  }, [])

  const simulate = async (values: any) => {
    setBusy(true)
    try {
      const response = await api.post('/planning/aps/simulate', values)
      message.success(`模拟完成：${response.data.impact_summary ?? response.data.scenario_id}`)
      setSimulateOpen(false)
      form.resetFields()
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '模拟失败')
    } finally {
      setBusy(false)
    }
  }

  const openDetail = async (scenarioId: string) => {
    try {
      const response = await api.get(`/planning/aps/scenarios/${scenarioId}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取模拟详情失败')
    }
  }

  const columns = [
    { title: '场景编号', dataIndex: 'scenario_id', key: 'scenario_id', width: 140 },
    { title: '批次', dataIndex: 'run_number', key: 'run_number', width: 160 },
    {
      title: '场景类型',
      dataIndex: 'scenario_type',
      key: 'type',
      width: 120,
      render: (value: string) => SCENARIO_TYPE[value] ?? value,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '影响摘要',
      dataIndex: 'impact_summary',
      key: 'summary',
      ellipsis: true,
      render: (value: string) => (value ? <Tag color="orange">{value}</Tag> : '-'),
    },
    { title: '创建人', dataIndex: 'created_by', key: 'created_by', width: 100 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: fmtDateTime },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_: any, row: any) => (
        <Button type="link" size="small" onClick={() => openDetail(row.scenario_id)}>
          影响明细
        </Button>
      ),
    },
  ]

  const impactColumns = [
    { title: '工单', dataIndex: 'production_order_number', key: 'order', width: 170 },
    { title: '物料', dataIndex: 'material_code', key: 'material', width: 150 },
    {
      title: '影响程度',
      dataIndex: 'impact_level',
      key: 'level',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={IMPACT_LEVEL} />,
    },
    { title: '受影响天数', dataIndex: 'affected_days', key: 'days', align: 'right' as const, width: 110, render: (v: number) => `${v} 天` },
    { title: '原计划完成', dataIndex: 'original_due_date', key: 'orig', width: 160, render: fmtDateTime },
    { title: '调整后完成', dataIndex: 'new_due_date', key: 'new', width: 160, render: fmtDateTime },
  ]

  return (
    <div>
      <PageHeader
        title="插单模拟"
        description="What-if 情景模拟：紧急插单 / 设备停机 / 物料延迟对现有排程的冲击量化，不影响已发布计划"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<ExperimentOutlined />} onClick={() => setSimulateOpen(true)}>
              新建模拟
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="scenario_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title="新建情景模拟"
        open={simulateOpen}
        onCancel={() => setSimulateOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={busy}
        okText="开始模拟"
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={simulate} initialValues={{ scenario_type: 'INSERT_ORDER' }}>
          <Form.Item name="run_number" label="排程批次" rules={[{ required: true, message: '请选择排程批次' }]}>
            <Select
              placeholder="选择要模拟的排程批次"
              options={runs.map((item) => ({
                value: item.run_number,
                label: `${item.run_number} · ${item.operation_count} 道工序`,
              }))}
            />
          </Form.Item>
          <Form.Item name="scenario_type" label="场景类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'INSERT_ORDER', label: '紧急插单' },
                { value: 'EQUIPMENT_DOWN', label: '设备停机' },
                { value: 'MATERIAL_DELAY', label: '物料延迟' },
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, next) => prev.scenario_type !== next.scenario_type}>
            {({ getFieldValue }) =>
              getFieldValue('scenario_type') === 'EQUIPMENT_DOWN' ? (
                <Form.Item
                  name="reference_ref"
                  label="停机工作中心"
                  rules={[{ required: true, message: '请输入工作中心编号（如 DRILL-A）' }]}
                >
                  <Input placeholder="如 DRILL-A" />
                </Form.Item>
              ) : getFieldValue('scenario_type') === 'INSERT_ORDER' ? (
                <Form.Item name="reference_ref" label="插单参考工单（可选）">
                  <Input placeholder="不填则模拟对所有工单的影响" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="模拟目的与背景（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={`模拟影响明细 ${detail?.scenario_id ?? ''}`}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={880}
        destroyOnClose
      >
        {detail && (
          <>
            <Row gutter={16} className="mb-4">
              <Col span={24}>
                <Card size="small">
                  <Space direction="vertical" size={2}>
                    <Space>
                      <Tag color="blue">{SCENARIO_TYPE[detail.scenario_type] ?? detail.scenario_type}</Tag>
                      <span>{detail.description ?? '-'}</span>
                    </Space>
                    {detail.impact_summary && <Tag color="orange">{detail.impact_summary}</Tag>}
                    <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>
                      批次 {detail.run_number} · {fmtDateTime(detail.created_at)} · {detail.created_by}
                    </span>
                  </Space>
                </Card>
              </Col>
            </Row>
            <Table
              rowKey="impact_id"
              size="small"
              columns={impactColumns}
              dataSource={detail.impacts ?? []}
              pagination={false}
              scroll={{ y: 420 }}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

export default ScenarioSimulationList
