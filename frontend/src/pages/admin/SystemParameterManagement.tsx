import { useCallback, useEffect, useState } from 'react'
import { App as AntdApp, Button, Input, Popconfirm, Space, Table, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { EntityFormModal, type FieldDef } from './components/EntityFormModal'

interface Param {
  id: number
  param_key: string
  param_name: string
  param_value?: string | null
  param_type: string
  param_desc?: string | null
  is_system: boolean
  remark?: string | null
}

const FIELDS: FieldDef[] = [
  { name: 'param_key', label: '参数键', required: true },
  { name: 'param_name', label: '参数名称', required: true },
  { name: 'param_value', label: '参数值', type: 'textarea' },
  { name: 'param_type', label: '类型', type: 'select', options: [
    { label: 'STRING', value: 'STRING' }, { label: 'INT', value: 'INT' },
    { label: 'BOOLEAN', value: 'BOOLEAN' }, { label: 'JSON', value: 'JSON' },
  ] },
  { name: 'param_desc', label: '参数说明' },
  { name: 'is_system', label: '系统内置', type: 'switch' },
  { name: 'remark', label: '备注', type: 'textarea' },
]

/** 系统参数：按 key 查询、增删改（内置参数不可删）。 */
const SystemParameterManagement: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [rows, setRows] = useState<Param[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Param | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/system/parameters')
      setRows(res.data?.items ?? [])
    } catch (error: any) { message.error(error?.userMessage ?? '加载参数失败') }
    finally { setLoading(false) }
  }, [message])
  useEffect(() => { void load() }, [load])

  const save = async (values: Record<string, any>) => {
    try {
      if (editing) await api.put(`/system/parameters/${editing.id}`, values)
      else await api.post('/system/parameters', values)
      message.success('参数已保存'); setOpen(false); setEditing(null); await load()
    } catch (error: any) { message.error(error?.response?.data?.detail ?? '保存失败') }
  }

  const remove = async (id: number) => {
    try {
      await api.delete(`/system/parameters/${id}`)
      message.success('参数已删除'); await load()
    } catch (error: any) { message.error(error?.response?.data?.detail ?? '删除失败') }
  }

  const visible = rows.filter((r) =>
    !keyword || r.param_key.includes(keyword) || r.param_name.includes(keyword))

  const columns = [
    { title: '参数键', dataIndex: 'param_key', width: 220 },
    { title: '名称', dataIndex: 'param_name', width: 160 },
    { title: '参数值', dataIndex: 'param_value', ellipsis: true },
    { title: '类型', dataIndex: 'param_type', width: 100, render: (v: string) => <Tag>{v}</Tag> },
    { title: '内置', dataIndex: 'is_system', width: 80,
      render: (v: boolean) => <Tag color={v ? 'red' : 'default'}>{v ? '是' : '否'}</Tag> },
    { title: '说明', dataIndex: 'param_desc', ellipsis: true },
    { title: '操作', key: 'actions', width: 140, render: (_: unknown, r: Param) => (
      <Space>
        <Button size="small" type="link" onClick={() => { setEditing(r); setOpen(true) }}>编辑</Button>
        {!r.is_system && (
          <Popconfirm title="删除该参数？" onConfirm={() => void remove(r.id)}>
            <Button size="small" type="link" danger>删除</Button>
          </Popconfirm>
        )}
      </Space>
    ) },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="系统参数" description="集中维护运行参数；内置参数不可删除（仅管理员）"
        actions={<Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setOpen(true) }}>新增参数</Button>} />
      <Input.Search allowClear placeholder="按参数键/名称搜索" className="w-64"
        onSearch={setKeyword} onChange={(e) => { if (!e.target.value) setKeyword('') }} />
      <Table rowKey="id" columns={columns} dataSource={visible} loading={loading} pagination={{ pageSize: 20 }} size="middle" />
      <EntityFormModal open={open} title={editing ? '编辑参数' : '新增参数'} fields={FIELDS}
        initial={editing} onOk={save} onCancel={() => { setOpen(false); setEditing(null) }} />
    </div>
  )
}

export default SystemParameterManagement
