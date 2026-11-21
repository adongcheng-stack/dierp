import { useCallback, useEffect, useState } from 'react'
import { App as AntdApp, Button, Popconfirm, Space, Table, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { EntityFormModal, type FieldDef } from './components/EntityFormModal'

interface Dept {
  id: number
  code: string
  name: string
  parent_id?: number | null
  level: number
  department_type: string
  manager?: string | null
  contact_phone?: string | null
  sort_order: number
  status: string
  remark?: string | null
  children?: Dept[]
}

const FIELDS: FieldDef[] = [
  { name: 'code', label: '部门编码', required: true },
  { name: 'name', label: '部门名称', required: true },
  { name: 'parent_id', label: '上级部门 ID', type: 'number' },
  { name: 'level', label: '层级', type: 'number' },
  { name: 'department_type', label: '部门类型', type: 'select', options: [
    { label: '公司', value: 'COMPANY' }, { label: '事业部', value: 'DIVISION' },
    { label: '部门', value: 'DEPARTMENT' }, { label: '小组', value: 'TEAM' },
    { label: '车间', value: 'WORKSHOP' },
  ] },
  { name: 'manager', label: '负责人' },
  { name: 'contact_phone', label: '联系电话' },
  { name: 'sort_order', label: '排序号', type: 'number' },
  { name: 'status', label: '状态', type: 'select', options: [
    { label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'INACTIVE' },
  ] },
  { name: 'remark', label: '备注', type: 'textarea' },
]

/** 部门管理：自引用树 + 增删改查（本体 Department 实体驱动字段）。 */
const DepartmentManagement: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [rows, setRows] = useState<Dept[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Dept | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows((await api.get('/system/departments/tree')).data ?? [])
    } catch (error: any) {
      message.error(error?.userMessage ?? '加载部门失败')
    } finally {
      setLoading(false)
    }
  }, [message])
  useEffect(() => { void load() }, [load])

  const save = async (values: Record<string, any>) => {
    try {
      if (editing) await api.put(`/system/departments/${editing.id}`, values)
      else await api.post('/system/departments', values)
      message.success(editing ? '部门已更新' : '部门已创建')
      setOpen(false); setEditing(null); await load()
    } catch (error: any) {
      message.error(error?.response?.data?.detail ?? '保存失败')
    }
  }

  const remove = async (id: number) => {
    try {
      await api.delete(`/system/departments/${id}`)
      message.success('部门已删除'); await load()
    } catch (error: any) {
      message.error(error?.response?.data?.detail ?? '删除失败')
    }
  }

  const columns = [
    { title: '编码', dataIndex: 'code', width: 130 },
    { title: '名称', dataIndex: 'name' },
    { title: '层级', dataIndex: 'level', width: 70 },
    { title: '类型', dataIndex: 'department_type', width: 100,
      render: (v: string) => <Tag>{v}</Tag> },
    { title: '负责人', dataIndex: 'manager', width: 110 },
    { title: '电话', dataIndex: 'contact_phone', width: 130 },
    { title: '排序', dataIndex: 'sort_order', width: 70 },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag> },
    { title: '操作', key: 'actions', width: 140, render: (_: unknown, r: Dept) => (
      <Space>
        <Button size="small" type="link" onClick={() => { setEditing(r); setOpen(true) }}>编辑</Button>
        <Popconfirm title="删除该部门？" onConfirm={() => void remove(r.id)}>
          <Button size="small" type="link" danger>删除</Button>
        </Popconfirm>
      </Space>
    ) },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="部门管理" description="组织架构树：支持多级部门、负责人与状态维护（仅管理员）"
        actions={<Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setOpen(true) }}>新增部门</Button>} />
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading}
        pagination={false} expandable={{ defaultExpandAllRows: true }} size="middle" />
      <EntityFormModal open={open} title={editing ? '编辑部门' : '新增部门'} fields={FIELDS}
        initial={editing} onOk={save} onCancel={() => { setOpen(false); setEditing(null) }} />
    </div>
  )
}

export default DepartmentManagement
