import { useCallback, useEffect, useState } from 'react'
import { App as AntdApp, Button, Popconfirm, Space, Table, Tag, Tree, Modal } from 'antd'
import { PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { EntityFormModal, type FieldDef } from './components/EntityFormModal'

interface MenuNode {
  id: number
  code: string
  name: string
  parent_id?: number | null
  path?: string | null
  menu_type: string
  permission?: string | null
  sort_order: number
  visible: boolean
  status: string
  children?: MenuNode[]
}
interface RoleRow { code: string; name: string; menu_count: number; user_count: number }

const FIELDS: FieldDef[] = [
  { name: 'code', label: '菜单编码', required: true },
  { name: 'name', label: '菜单名称', required: true },
  { name: 'parent_id', label: '上级菜单 ID', type: 'number' },
  { name: 'path', label: '路由地址' },
  { name: 'menu_type', label: '类型', type: 'select', options: [
    { label: '目录', value: 'DIRECTORY' }, { label: '菜单', value: 'MENU' }, { label: '按钮', value: 'BUTTON' },
  ] },
  { name: 'permission', label: '权限标识' },
  { name: 'sort_order', label: '排序号', type: 'number' },
  { name: 'visible', label: '可见', type: 'switch' },
  { name: 'status', label: '状态', type: 'select', options: [
    { label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'INACTIVE' },
  ] },
]

const toTreeData = (nodes: MenuNode[]): any[] => nodes.map((node) => ({
  key: node.id, title: `${node.name} (${node.code})`,
  children: node.children ? toTreeData(node.children) : undefined,
}))

/** 菜单管理 + 角色授权：菜单树维护与角色-菜单勾选。 */
const MenuManagement: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [menus, setMenus] = useState<MenuNode[]>([])
  const [roles, setRoles] = useState<RoleRow[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<MenuNode | null>(null)
  const [grantRole, setGrantRole] = useState<RoleRow | null>(null)
  const [checkedKeys, setCheckedKeys] = useState<number[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [menuRes, roleRes] = await Promise.all([
        api.get('/system/menus/tree'), api.get('/system/roles'),
      ])
      setMenus(menuRes.data ?? [])
      setRoles(roleRes.data?.items ?? [])
    } catch (error: any) {
      message.error(error?.userMessage ?? '加载菜单失败')
    } finally { setLoading(false) }
  }, [message])
  useEffect(() => { void load() }, [load])

  const openGrant = async (role: RoleRow) => {
    try {
      const res = await api.get(`/system/roles/${role.code}/menus`)
      setCheckedKeys(res.data?.menu_ids ?? [])
      setGrantRole(role)
    } catch (error: any) { message.error('加载角色授权失败') }
  }

  const saveGrant = async () => {
    if (!grantRole) return
    try {
      await api.post(`/system/roles/${grantRole.code}/menus`, { menu_ids: checkedKeys })
      message.success(`已更新角色 ${grantRole.name} 的菜单授权`)
      setGrantRole(null); await load()
    } catch (error: any) { message.error('保存授权失败') }
  }

  const save = async (values: Record<string, any>) => {
    try {
      if (editing) await api.put(`/system/menus/${editing.id}`, values)
      else await api.post('/system/menus', values)
      message.success('菜单已保存'); setOpen(false); setEditing(null); await load()
    } catch (error: any) { message.error(error?.response?.data?.detail ?? '保存失败') }
  }

  const remove = async (id: number) => {
    try {
      await api.delete(`/system/menus/${id}`)
      message.success('菜单已删除'); await load()
    } catch (error: any) { message.error(error?.response?.data?.detail ?? '删除失败') }
  }

  const columns = [
    { title: '编码', dataIndex: 'code', width: 140 },
    { title: '名称', dataIndex: 'name' },
    { title: '路由', dataIndex: 'path', width: 200 },
    { title: '类型', dataIndex: 'menu_type', width: 100,
      render: (v: string) => <Tag color={v === 'DIRECTORY' ? 'blue' : v === 'BUTTON' ? 'orange' : 'green'}>{v}</Tag> },
    { title: '权限标识', dataIndex: 'permission', width: 180 },
    { title: '排序', dataIndex: 'sort_order', width: 70 },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag> },
    { title: '操作', key: 'actions', width: 170, render: (_: unknown, r: MenuNode) => (
      <Space>
        <Button size="small" type="link" onClick={() => { setEditing(r); setOpen(true) }}>编辑</Button>
        <Popconfirm title="删除该菜单？" onConfirm={() => void remove(r.id)}>
          <Button size="small" type="link" danger>删除</Button>
        </Popconfirm>
      </Space>
    ) },
  ]

  const roleColumns = [
    { title: '角色', dataIndex: 'name' },
    { title: '编码', dataIndex: 'code' },
    { title: '菜单数', dataIndex: 'menu_count', width: 90 },
    { title: '用户数', dataIndex: 'user_count', width: 90 },
    { title: '操作', key: 'actions', width: 120, render: (_: unknown, r: RoleRow) => (
      <Button size="small" type="link" icon={<SafetyCertificateOutlined />} onClick={() => void openGrant(r)}>分配菜单</Button>
    ) },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="菜单管理" description="维护系统菜单树与角色-菜单授权（仅管理员）"
        actions={<Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setOpen(true) }}>新增菜单</Button>} />
      <Table rowKey="id" columns={columns} dataSource={menus} loading={loading}
        pagination={false} expandable={{ defaultExpandAllRows: true }} size="middle" />
      <PageHeader title="角色授权" description="勾选该角色可访问的菜单，保存后立即生效于角色菜单矩阵" />
      <Table rowKey="code" columns={roleColumns} dataSource={roles} pagination={false} size="middle" />
      <EntityFormModal open={open} title={editing ? '编辑菜单' : '新增菜单'} fields={FIELDS}
        initial={editing} onOk={save} onCancel={() => { setOpen(false); setEditing(null) }} />
      <Modal open={!!grantRole} title={`分配菜单 · ${grantRole?.name ?? ''}`} onOk={saveGrant}
        onCancel={() => setGrantRole(null)} width={480}>
        <Tree checkable checkStrictly defaultExpandAll treeData={toTreeData(menus)}
          checkedKeys={checkedKeys} onCheck={(keys) => setCheckedKeys(keys as number[])} />
      </Modal>
    </div>
  )
}

export default MenuManagement
