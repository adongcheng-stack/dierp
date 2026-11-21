import { useCallback, useEffect, useState } from 'react'
import { App as AntdApp, Button, Table, Tag, Tree, Modal, Space } from 'antd'
import { SafetyCertificateOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface RoleRow { code: string; name: string; menu_count: number; user_count: number }
interface MenuNode { id: number; name: string; code: string; children?: MenuNode[] }

const toTreeData = (nodes: MenuNode[]): any[] => nodes.map((node) => ({
  key: node.id, title: `${node.name} (${node.code})`,
  children: node.children ? toTreeData(node.children) : undefined,
}))

/** 角色管理：角色来自本体 UserRole 枚举（唯一事实源），管理其菜单授权。 */
const RoleManagement: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [roles, setRoles] = useState<RoleRow[]>([])
  const [menus, setMenus] = useState<MenuNode[]>([])
  const [loading, setLoading] = useState(false)
  const [grantRole, setGrantRole] = useState<RoleRow | null>(null)
  const [checkedKeys, setCheckedKeys] = useState<number[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/system/roles')
      setRoles(res.data?.items ?? [])
    } catch (error: any) { message.error(error?.userMessage ?? '加载角色失败') }
    finally { setLoading(false) }
  }, [message])
  useEffect(() => { void load() }, [load])

  const openGrant = async (role: RoleRow) => {
    try {
      const [menuRes, grantRes] = await Promise.all([
        api.get('/system/menus/tree'), api.get(`/system/roles/${role.code}/menus`),
      ])
      setMenus(menuRes.data ?? [])
      setCheckedKeys(grantRes.data?.menu_ids ?? [])
      setGrantRole(role)
    } catch (error: any) { message.error('加载授权数据失败') }
  }

  const saveGrant = async () => {
    if (!grantRole) return
    try {
      await api.post(`/system/roles/${grantRole.code}/menus`, { menu_ids: checkedKeys })
      message.success(`角色 ${grantRole.name} 授权已更新`)
      setGrantRole(null); await load()
    } catch (error: any) { message.error('保存授权失败') }
  }

  const columns = [
    { title: '角色名称', dataIndex: 'name', width: 160,
      render: (v: string, r: RoleRow) => <Space><Tag color="blue">{v}</Tag><span className="text-xs text-ink-soft">{r.code}</span></Space> },
    { title: '角色编码', dataIndex: 'code', width: 180 },
    { title: '已授权菜单', dataIndex: 'menu_count', width: 120 },
    { title: '用户数', dataIndex: 'user_count', width: 100 },
    { title: '操作', key: 'actions', width: 140, render: (_: unknown, r: RoleRow) => (
      <Button size="small" type="link" icon={<SafetyCertificateOutlined />} onClick={() => void openGrant(r)}>
        分配菜单
      </Button>
    ) },
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="角色管理" description="角色由本体 UserRole 枚举定义，此处维护角色-菜单授权与用户归属（仅管理员）" />
      <Table rowKey="code" columns={columns} dataSource={roles} loading={loading} pagination={false} size="middle" />
      <Modal open={!!grantRole} title={`分配菜单 · ${grantRole?.name ?? ''}`} onOk={saveGrant}
        onCancel={() => setGrantRole(null)} width={480}>
        <Tree checkable checkStrictly defaultExpandAll treeData={toTreeData(menus)}
          checkedKeys={checkedKeys} onCheck={(keys) => setCheckedKeys(keys as number[])} />
      </Modal>
    </div>
  )
}

export default RoleManagement
