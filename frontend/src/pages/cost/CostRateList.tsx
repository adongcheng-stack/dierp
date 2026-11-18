import { useEffect, useMemo, useState } from 'react'
import { Button, Form, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import { EditOutlined, ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { RATE_TYPE, fmtMoney } from './shared'

const CostRateList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [workCenters, setWorkCenters] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [workCenter, setWorkCenter] = useState<string | undefined>()
  const [rateType, setRateType] = useState<string | undefined>()
  const [editing, setEditing] = useState<any | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/cost/rates', {
        params: { limit: 300, work_center_id: workCenter, rate_type: rateType },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取成本费率失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchWorkCenters = async () => {
    try {
      const response = await api.get('/pp/work-centers', { params: { limit: 300 } })
      const data = response.data
      const list = Array.isArray(data) ? data : data?.items ?? []
      setWorkCenters(list)
    } catch {
      setWorkCenters([])
    }
  }

  useEffect(() => {
    fetchRows()
    fetchWorkCenters()
  }, [workCenter, rateType])

  const workCenterOptions = workCenters.map((wc: any) => ({
    value: wc.work_center_id,
    label: `${wc.work_center_id} · ${wc.description ?? ''}`,
  }))

  const openEdit = (record: any) => {
    setEditing(record)
    form.setFieldsValue({
      rate_per_hour: record.rate_per_hour,
      status: record.status ?? 'ACTIVE',
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    if (!editing) return
    setSaving(true)
    try {
      await api.put(`/planning/cost/rates/${editing.rate_id}`, {
        work_center_id: editing.work_center_id,
        rate_type: editing.rate_type,
        rate_per_hour: values.rate_per_hour,
        currency: editing.currency ?? 'CNY',
        status: values.status,
      })
      message.success('成本费率已更新')
      setModalOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '保存成本费率失败')
    } finally {
      setSaving(false)
    }
  }

  const filteredRows = useMemo(() => rows, [rows])

  const columns = [
    { title: '费率编号', dataIndex: 'rate_id', key: 'rate_id', width: 150 },
    { title: '工作中心', dataIndex: 'work_center_id', key: 'work_center_id', width: 130 },
    {
      title: '费率类型',
      dataIndex: 'rate_type',
      key: 'rate_type',
      width: 120,
      render: (value: string) => <Tag color="blue">{RATE_TYPE[value] ?? value}</Tag>,
    },
    {
      title: '费率（元/小时）',
      dataIndex: 'rate_per_hour',
      key: 'rate_per_hour',
      align: 'right' as const,
      width: 150,
      render: (value: number) => <b>{fmtMoney(value)}</b>,
    },
    {
      title: '币种',
      dataIndex: 'currency',
      key: 'currency',
      width: 70,
    },
    {
      title: '生效自',
      dataIndex: 'effective_from',
      key: 'effective_from',
      width: 160,
      render: (value: string) => value?.slice(0, 10) ?? '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value: string) => (
        <Tag color={value === 'ACTIVE' ? 'green' : 'default'}>{value}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="成本费率"
        description="维护工作中心的人工、设备、制造费用费率，驱动标准成本与实际成本计算"
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
          placeholder="工作中心"
          value={workCenter}
          onChange={setWorkCenter}
          options={workCenterOptions}
        />
        <Select
          allowClear
          style={{ width: 150 }}
          placeholder="费率类型"
          value={rateType}
          onChange={setRateType}
          options={[
            { value: 'LABOR', label: '人工费率' },
            { value: 'MACHINE', label: '设备费率' },
            { value: 'OVERHEAD', label: '制造费用' },
          ]}
        />
      </Space>

      <Table
        rowKey="rate_id"
        columns={columns}
        dataSource={filteredRows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1100 }}
      />

      <Modal
        title={editing ? `编辑费率 ${editing.rate_id}` : '编辑成本费率'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={submit}
        confirmLoading={saving}
        okText="保存"
        width={460}
        destroyOnClose
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item name="rate_per_hour" label="费率（元/小时）" rules={[{ required: true, message: '请输入费率' }]}>
            <InputNumber style={{ width: '100%' }} min={0} precision={2} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              options={[
                { value: 'ACTIVE', label: '生效' },
                { value: 'INACTIVE', label: '停用' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CostRateList