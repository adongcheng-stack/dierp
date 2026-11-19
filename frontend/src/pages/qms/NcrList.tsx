import { useEffect, useState } from 'react'
import { Button, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { CheckOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  NCR_DISPOSITION,
  NCR_SEVERITY,
  NCR_SOURCE,
  NCR_STATUS,
  StatusTag,
} from './shared'

const NcrList: React.FC = () => {
  const navigate = useNavigate()
  const [rows, setRows] = useState<any[]>([])
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [materials, setMaterials] = useState<any[]>([])
  const [scrapReports, setScrapReports] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [reviewTarget, setReviewTarget] = useState<any>(null)
  const [disposeTarget, setDisposeTarget] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/qms/ncrs', { params: { limit: 200, status: statusFilter } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取不合格品记录失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchOptions = async () => {
    try {
      const [matRes, scrapRes] = await Promise.all([
        api.get('/mm/materials'),
        api.get('/qms/operation-reports/scrap'),
      ])
      setMaterials(matRes.data || [])
      setScrapReports(scrapRes.data.items ?? [])
    } catch {
      setMaterials([])
      setScrapReports([])
    }
  }

  useEffect(() => {
    fetchRows()
  }, [statusFilter])

  useEffect(() => {
    fetchOptions()
  }, [])

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({ source_type: 'INSPECTION', severity: 'MAJOR' })
    setCreateOpen(true)
  }

  const submitCreate = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      // 选择报工单来源时，自动填充其物料与报废数量
      const payload: any = { ...values }
      if (values.source_type === 'REPORT' && values.report_number) {
        const report = scrapReports.find((r) => r.report_number === values.report_number)
        if (report) {
          payload.material_code = payload.material_code || report.material_code || undefined
          payload.lot_number = payload.lot_number || report.lot_number
          payload.quantity = payload.quantity ?? report.scrap_quantity
        }
      }
      await api.post('/qms/ncrs', payload)
      message.success('不合格品记录已开立')
      setCreateOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '开立不合格品记录失败')
    } finally {
      setBusy(false)
    }
  }

  const openReview = (row: any) => {
    setReviewTarget(row)
    form.resetFields()
    form.setFieldsValue({
      severity: row.severity,
      root_cause: row.root_cause,
      equipment_cause: row.equipment_cause,
      resource_id: 'RES-DRILL-B-01',
      failure_desc: `QMS 联动：NCR ${row.ncr_number}`,
    })
  }

  const submitReview = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      await api.post(`/qms/ncrs/${reviewTarget.ncr_number}/review`, {
        severity: values.severity,
        root_cause: values.root_cause,
        equipment_cause: values.equipment_cause,
        resource_id: values.resource_id,
        failure_desc: values.failure_desc,
      })
      message.success(`NCR ${reviewTarget.ncr_number} 已评审`)
      setReviewTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '评审失败')
    } finally {
      setBusy(false)
    }
  }

  const openDispose = (row: any) => {
    setDisposeTarget(row)
    form.resetFields()
    form.setFieldsValue({
      disposition: row.disposition,
      disposition_note: row.disposition_note,
      equipment_cause: row.equipment_cause,
      resource_id: 'RES-DRILL-B-01',
    })
  }

  const submitDispose = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      await api.post(`/qms/ncrs/${disposeTarget.ncr_number}/disposition`, {
        disposition: values.disposition,
        disposition_note: values.disposition_note,
        equipment_cause: values.equipment_cause,
        resource_id: values.resource_id,
        failure_desc: `QMS 联动：NCR ${disposeTarget.ncr_number}`,
      })
      message.success(`NCR ${disposeTarget.ncr_number} 已处置`)
      setDisposeTarget(null)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '处置失败')
    } finally {
      setBusy(false)
    }
  }

  const closeNcr = async (row: any) => {
    try {
      await api.post(`/qms/ncrs/${row.ncr_number}/close`, {})
      message.success(`NCR ${row.ncr_number} 已关闭`)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '关闭失败')
    }
  }

  const columns = [
    { title: 'NCR编号', dataIndex: 'ncr_number', key: 'ncr_number', width: 170 },
    {
      title: '来源',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 90,
      render: (v: string) => <StatusTag value={v} map={NCR_SOURCE} />,
    },
    {
      title: '来源单据',
      dataIndex: 'source_ref',
      key: 'source_ref',
      width: 170,
      render: (v: string, row: any) => {
        if (!v) return '-'
        const target =
          row.source_type === 'INSPECTION'
            ? '/qms/inspections'
            : row.source_type === 'REPORT'
              ? '/pp/operation-reports'
              : row.source_type === 'LOT_CARD'
                ? '/pp/lot-cards'
                : null
        return target ? (
          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => navigate(target)}>
            {v}
          </Button>
        ) : (
          v
        )
      },
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    { title: 'LOT卡', dataIndex: 'lot_number', key: 'lot_number', width: 140, render: (v: string) => v || '-' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 80, align: 'right' as const },
    { title: '缺陷', dataIndex: 'defect_code', key: 'defect_code', width: 130, render: (v: string) => v || '-' },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (v: string) => <StatusTag value={v} map={NCR_SEVERITY} />,
    },
    {
      title: '设备原因',
      dataIndex: 'equipment_cause',
      key: 'equipment_cause',
      width: 90,
      render: (v: boolean) => (v ? '是' : '-'),
    },
    { title: 'EAM故障', dataIndex: 'failure_number', key: 'failure_number', width: 150, render: (v: string) => v || '-' },
    {
      title: '处置',
      dataIndex: 'disposition',
      key: 'disposition',
      width: 100,
      render: (v: string) => (v ? <StatusTag value={v} map={NCR_DISPOSITION} /> : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => <StatusTag value={v} map={NCR_STATUS} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, row: any) => {
        const actions: React.ReactNode[] = []
        if (row.status === 'OPEN') {
          actions.push(
            <Button type="link" size="small" key="review" onClick={() => openReview(row)}>
              评审
            </Button>
          )
        }
        if (row.status === 'UNDER_REVIEW' || row.status === 'DISPOSITIONED') {
          actions.push(
            <Button type="link" size="small" key="dispose" onClick={() => openDispose(row)}>
              处置
            </Button>
          )
        }
        if (row.status !== 'CLOSED') {
          actions.push(
            <Button type="link" size="small" key="close" icon={<CheckOutlined />} onClick={() => closeNcr(row)}>
              关闭
            </Button>
          )
        }
        return actions.length ? actions : '-'
      },
    },
  ]

  return (
    <div>
      <PageHeader
        title="不合格品记录"
        description="不合格闭环：开立 → 评审 → 处置 → 关闭；判定设备原因时自动联动 EAM 故障"
        actions={
          <Space>
            <Select
              allowClear
              placeholder="按状态筛选"
              style={{ width: 140 }}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
              options={Object.entries(NCR_STATUS).map(([value, item]) => ({ value, label: item.text }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              开立 NCR
            </Button>
          </Space>
        }
      />

      <Table
        rowKey="ncr_number"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1700 }}
      />

      {/* 新建 NCR */}
      <Modal
        title="开立不合格品记录"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={submitCreate}
        confirmLoading={busy}
        okText="开立"
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="source_type" label="来源类型" rules={[{ required: true }]}>
            <Select
              options={Object.entries(NCR_SOURCE).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="report_number" label="来源报工单（报工 scrap>0 时可选）">
            <Select
              allowClear
              showSearch
              placeholder="选择带报废的报工单"
              optionFilterProp="label"
              options={scrapReports.map((r) => ({
                value: r.report_number,
                label: `${r.report_number} · ${r.production_order_number} · 报废${r.scrap_quantity}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="lot_number" label="LOT卡">
            <Input placeholder="涉及批次" />
          </Form.Item>
          <Form.Item name="material_code" label="物料" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={materials.map((m) => ({ value: m.material_code, label: `${m.material_code} ${m.material_name ?? ''}` }))}
            />
          </Form.Item>
          <Form.Item name="quantity" label="不合格数量">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="defect_code" label="缺陷代码">
            <Input placeholder="如 DRILL-OFFSET" />
          </Form.Item>
          <Form.Item name="defect_desc" label="缺陷描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="severity" label="严重程度" rules={[{ required: true }]}>
            <Select
              options={Object.entries(NCR_SEVERITY).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 评审 NCR */}
      <Modal
        title={`评审 NCR ${reviewTarget?.ncr_number ?? ''}`}
        open={!!reviewTarget}
        onCancel={() => setReviewTarget(null)}
        onOk={submitReview}
        confirmLoading={busy}
        okText="确认评审"
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="severity" label="严重程度">
            <Select
              options={Object.entries(NCR_SEVERITY).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="root_cause" label="根本原因">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="equipment_cause" label="判定为设备原因（联动 EAM 故障）" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="resource_id" label="联动设备资源">
            <Select
              options={['RES-DRILL-A-01', 'RES-DRILL-B-01', 'RES-DRILL-C-01', 'RES-DRILL-D-01'].map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
          <Form.Item name="failure_desc" label="故障描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 处置 NCR */}
      <Modal
        title={`处置 NCR ${disposeTarget?.ncr_number ?? ''}`}
        open={!!disposeTarget}
        onCancel={() => setDisposeTarget(null)}
        onOk={submitDispose}
        confirmLoading={busy}
        okText="确认处置"
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="disposition" label="处置方式" rules={[{ required: true }]}>
            <Select
              options={Object.entries(NCR_DISPOSITION).map(([value, item]) => ({ value, label: item.text }))}
            />
          </Form.Item>
          <Form.Item name="disposition_note" label="处置说明">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="equipment_cause" label="判定为设备原因（联动 EAM 故障）" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="resource_id" label="联动设备资源">
            <Select
              options={['RES-DRILL-A-01', 'RES-DRILL-B-01', 'RES-DRILL-C-01', 'RES-DRILL-D-01'].map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default NcrList