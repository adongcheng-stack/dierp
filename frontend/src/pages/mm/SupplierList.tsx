import { useEffect, useState } from 'react'
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, message } from 'antd'
import { PlusOutlined, ReloadOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const pct = (v: number | null | undefined) => (v == null ? '-' : `${(v * 100).toFixed(1)}%`)

/** 采购绩效 Tab：到货及时率（库存流水首到 vs 期望日期）+ 来料合格率（已完成 IQC）。 */
const SupplierPerformance: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/purchase/suppliers/performance')
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取供应商绩效失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = [
    { title: '供应商编码', dataIndex: 'supplier_id', key: 'sid', width: 120 },
    { title: '供应商', dataIndex: 'supplier_name', key: 'name' },
    {
      title: '评级',
      dataIndex: 'rating',
      key: 'rating',
      width: 100,
      render: (v: number) => <span className="tabular-nums">{Math.max(0, Number(v || 0))}</span>,
    },
    {
      title: '有收货采购单',
      dataIndex: 'po_received_count',
      key: 'po',
      width: 120,
      align: 'right' as const,
    },
    {
      title: '到货及时率',
      key: 'on_time',
      width: 150,
      render: (_: unknown, row: any) =>
        row.on_time_rate == null ? (
          '-'
        ) : (
          <span>
            {pct(row.on_time_rate)}
            <span className="ml-1 text-xs text-ink-faint">
              ({row.on_time_count}/{row.on_time_total})
            </span>
          </span>
        ),
    },
    {
      title: '来料合格率',
      key: 'iqc',
      width: 150,
      render: (_: unknown, row: any) =>
        row.iqc_pass_rate == null ? (
          '-'
        ) : (
          <span>
            {pct(row.iqc_pass_rate)}
            <span className="ml-1 text-xs text-ink-faint">({row.iqc_count} 批)</span>
          </span>
        ),
    },
    {
      title: '累计到货金额',
      dataIndex: 'received_amount',
      key: 'amt',
      width: 140,
      align: 'right' as const,
      render: (v: number) => `¥${Number(v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
    },
  ]

  return (
    <>
      <div className="mb-3 text-xs text-ink-faint">
        到货及时率 = 首到日期 ≤ 采购单期望日期（数据来自库存流水，reset 后需重新收货才有数据）；
        来料合格率 = 已完成来料检验（IQC）的 Σ合格数 ÷ Σ检验数
      </div>
      <Table
        rowKey="supplier_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={false}
        size="middle"
        scroll={{ x: 900 }}
      />
    </>
  )
}

const SUPPLIER_TYPE: Record<string, { text: string; color: string }> = {
  MATERIAL: { text: '物料供应商', color: 'blue' },
  OUTSOURCE: { text: '委外加工', color: 'purple' },
  SERVICE: { text: '服务商', color: 'cyan' },
}

const SupplierList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [busy, setBusy] = useState(false)
  const [form] = Form.useForm()

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/purchase/suppliers', {
        params: { limit: 200, keyword: keyword.trim() || undefined },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取供应商列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ supplier_type: 'MATERIAL', status: 'ACTIVE', default_currency: 'CNY', rating: 3, lead_time_days: 0 })
    setModalOpen(true)
  }

  const openEdit = (row: any) => {
    setEditing(row)
    form.resetFields()
    form.setFieldsValue(row)
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    setBusy(true)
    try {
      if (editing) {
        await api.put(`/purchase/suppliers/${editing.supplier_code}`, values)
        message.success('供应商已更新')
      } else {
        await api.post('/purchase/suppliers', values)
        message.success('供应商已创建')
      }
      setModalOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '保存供应商失败')
    } finally {
      setBusy(false)
    }
  }

  const toggle = async (row: any) => {
    try {
      await api.post(`/purchase/suppliers/${row.supplier_code}/toggle`)
      message.success(row.status === 'ACTIVE' ? '供应商已停用' : '供应商已启用')
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '操作失败')
    }
  }

  const columns = [
    { title: '编码', dataIndex: 'supplier_code', key: 'supplier_code', width: 110 },
    { title: '供应商名称', dataIndex: 'supplier_name', key: 'supplier_name' },
    {
      title: '类型',
      dataIndex: 'supplier_type',
      key: 'supplier_type',
      width: 110,
      render: (v: string) => {
        const item = SUPPLIER_TYPE[v]
        return item ? <Tag color={item.color}>{item.text}</Tag> : v
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (v: string) => (v === 'ACTIVE' ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
    },
    { title: '联系人', dataIndex: 'contact_person', key: 'contact_person', width: 90, render: (v: string) => v || '-' },
    { title: '联系电话', dataIndex: 'contact_phone', key: 'contact_phone', width: 130, render: (v: string) => v || '-' },
    { title: '交货天数', dataIndex: 'lead_time_days', key: 'lead_time_days', width: 95, align: 'right' as const },
    { title: '币种', dataIndex: 'default_currency', key: 'default_currency', width: 70 },
    {
      title: '评级',
      dataIndex: 'rating',
      key: 'rating',
      width: 80,
      render: (v: number) => <span className="tabular-nums">{Math.max(0, Number(v || 0))}</span>,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, row: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(row)}>
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={row.status === 'ACTIVE' ? <StopOutlined /> : <CheckCircleOutlined />}
            danger={row.status === 'ACTIVE'}
            onClick={() => toggle(row)}
          >
            {row.status === 'ACTIVE' ? '停用' : '启用'}
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="供应商管理"
        description="维护采购供应商主数据：新建 / 编辑 / 停用启用；采购订单可从供应商下拉选择"
        actions={
          <Space>
            <Input.Search
              placeholder="按编码/名称搜索"
              allowClear
              style={{ width: 220 }}
              onSearch={() => fetchRows()}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建供应商
            </Button>
          </Space>
        }
      />

      <Tabs
        defaultActiveKey="master"
        items={[
          {
            key: 'master',
            label: '供应商主数据',
            children: (
              <Table
                rowKey="supplier_code"
                columns={columns}
                dataSource={rows}
                loading={loading}
                pagination={{ pageSize: 15, showSizeChanger: false, showTotal: (t) => `共 ${t} 家` }}
                scroll={{ x: 1050 }}
              />
            ),
          },
          {
            key: 'performance',
            label: '采购绩效',
            children: <SupplierPerformance />,
          },
        ]}
      />

      <Modal
        title={editing ? `编辑供应商 · ${editing.supplier_code}` : '新建供应商'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={submit}
        confirmLoading={busy}
        okText="保存"
        destroyOnClose
        width={760}
      >
        <Form form={form} layout="vertical">
          <div className="grid grid-cols-2 gap-x-4">
            <Form.Item name="supplier_name" label="供应商名称" rules={[{ required: true, message: '请输入供应商名称' }]}>
              <Input placeholder="供应商全称" />
            </Form.Item>
            <Form.Item name="short_name" label="简称">
              <Input placeholder="简称（可选）" />
            </Form.Item>
            <Form.Item name="supplier_type" label="供应商类型">
              <Select options={Object.entries(SUPPLIER_TYPE).map(([value, item]) => ({ value, label: item.text }))} />
            </Form.Item>
            <Form.Item name="status" label="状态">
              <Select
                options={[
                  { value: 'ACTIVE', label: '启用' },
                  { value: 'INACTIVE', label: '停用' },
                ]}
              />
            </Form.Item>
            <Form.Item name="contact_person" label="联系人">
              <Input placeholder="联系人" />
            </Form.Item>
            <Form.Item name="contact_phone" label="联系电话">
              <Input placeholder="联系电话" />
            </Form.Item>
            <Form.Item name="email" label="邮箱">
              <Input placeholder="邮箱" />
            </Form.Item>
            <Form.Item name="address" label="地址">
              <Input placeholder="地址" />
            </Form.Item>
            <Form.Item name="tax_number" label="税号">
              <Input placeholder="税号" />
            </Form.Item>
            <Form.Item name="bank_account" label="银行账号">
              <Input placeholder="银行账号" />
            </Form.Item>
            <Form.Item name="payment_terms" label="付款条款">
              <Input placeholder="如：月结30天" />
            </Form.Item>
            <Form.Item name="lead_time_days" label="默认交货天数">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="default_currency" label="默认币种">
              <Input placeholder="CNY" />
            </Form.Item>
            <Form.Item name="rating" label="评级">
              <InputNumber min={1} max={5} style={{ width: '100%' }} />
            </Form.Item>
          </div>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SupplierList