import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  ShoppingCart,
  Users,
  FileText,
  ClipboardList,
  CheckSquare,
  Factory,
  Boxes,
  Route,
  Layers,
  FileCog,
  PackageSearch,
  CalendarClock,
  Building2,
  ClipboardCheck,
  Ticket,
  Activity,
  Package,
  PackageMinus,
  ShieldCheck,
  UserCog,
  BadgeCheck,
  ClipboardX,
  Network,
  Gauge,
} from 'lucide-react'

export interface NavItem {
  key: string
  label: string
  icon: LucideIcon
  /** 有 path 的项可直接跳转；否则为可展开分组 */
  path?: string
  children?: NavItem[]
}

/** ERP 导航结构：与 MES 一致的两级菜单（分组 + 页面） */
export const NAV_ITEMS: NavItem[] = [
  { key: '/', label: '仪表盘', icon: LayoutDashboard, path: '/' },
  {
    key: 'sd',
    label: '销售与分销',
    icon: ShoppingCart,
    children: [
      { key: '/sd/customers', label: '客户管理', icon: Users, path: '/sd/customers' },
      { key: '/sd/quotations', label: '报价单', icon: FileText, path: '/sd/quotations' },
      { key: '/sd/sales-orders', label: '销售订单', icon: ClipboardList, path: '/sd/sales-orders' },
      { key: '/sd/pending-approvals', label: '待我审批', icon: CheckSquare, path: '/sd/pending-approvals' },
    ],
  },
  {
    key: 'eng',
    label: '工程管理',
    icon: Factory,
    children: [
      { key: '/eng/boms', label: 'BOM管理', icon: Boxes, path: '/eng/boms' },
      { key: '/eng/routings', label: '工艺路线', icon: Route, path: '/eng/routings' },
      { key: '/eng/production-versions', label: '生产版本', icon: Layers, path: '/eng/production-versions' },
      { key: '/eng/mis', label: 'MI管理', icon: FileCog, path: '/eng/mis' },
      {
        key: '/eng/factory-product-mappings',
        label: '产品主数据',
        icon: PackageSearch,
        path: '/eng/factory-product-mappings',
      },
    ],
  },
  {
    key: 'pp',
    label: '生产计划',
    icon: CalendarClock,
    children: [
      { key: '/pp/planning', label: '计划工作台', icon: LayoutDashboard, path: '/pp/planning' },
      { key: '/pp/mps', label: '主生产计划', icon: CalendarClock, path: '/pp/mps' },
      { key: '/pp/mrp', label: 'MRP 运算', icon: Activity, path: '/pp/mrp' },
      { key: '/pp/planned-orders', label: '计划订单', icon: ClipboardList, path: '/pp/planned-orders' },
      { key: '/pp/purchase-orders', label: '采购订单', icon: Boxes, path: '/pp/purchase-orders' },
      {
        key: '/pp/planning-exceptions',
        label: '计划异常',
        icon: CheckSquare,
        path: '/pp/planning-exceptions',
      },
      { key: '/pp/kitting', label: '齐套分析', icon: PackageSearch, path: '/pp/kitting' },
      {
        key: '/pp/planning-policies',
        label: '计划参数',
        icon: Layers,
        path: '/pp/planning-policies',
      },
      { key: '/pp/work-centers', label: '工作中心', icon: Building2, path: '/pp/work-centers' },
      { key: '/pp/production-orders', label: '工单管理', icon: ClipboardCheck, path: '/pp/production-orders' },
      { key: '/pp/lot-cards', label: 'LOT卡管理', icon: Ticket, path: '/pp/lot-cards' },
      { key: '/trace/explorer', label: '批次追溯', icon: Network, path: '/trace/explorer' },
      { key: '/dashboard/management', label: '经营看板', icon: Gauge, path: '/dashboard/management' },
      { key: '/pp/operation-reports', label: '工序报工', icon: Activity, path: '/pp/operation-reports' },
    ],
  },
  {
    key: 'cost',
    label: '成本管理',
    icon: Activity,
    children: [
      { key: '/cost/workbench', label: '成本工作台', icon: LayoutDashboard, path: '/cost/workbench' },
      { key: '/cost/standard', label: '标准成本', icon: FileCog, path: '/cost/standard' },
      { key: '/cost/production', label: '工单成本', icon: ClipboardList, path: '/cost/production' },
      { key: '/cost/variances', label: '差异分析', icon: Activity, path: '/cost/variances' },
      { key: '/cost/settlements', label: '成本结算', icon: ClipboardCheck, path: '/cost/settlements' },
      { key: '/cost/rates', label: '成本费率', icon: Layers, path: '/cost/rates' },
    ],
  },
  {
    key: 'aps',
    label: '高级排程',
    icon: CalendarClock,
    children: [
      { key: '/aps/workbench', label: 'APS 工作台', icon: LayoutDashboard, path: '/aps/workbench' },
      { key: '/aps/runs', label: '排程批次', icon: ClipboardList, path: '/aps/runs' },
      { key: '/aps/scenarios', label: '插单模拟', icon: FileCog, path: '/aps/scenarios' },
      { key: '/aps/exceptions', label: '排程异常', icon: PackageSearch, path: '/aps/exceptions' },
      { key: '/aps/master-data', label: '排程主数据', icon: Building2, path: '/aps/master-data' },
    ],
  },
  {
    key: 'eam',
    label: '设备管理',
    icon: Building2,
    children: [
      { key: '/eam/workbench', label: '设备工作台', icon: LayoutDashboard, path: '/eam/workbench' },
      { key: '/eam/plans', label: '维护计划', icon: CalendarClock, path: '/eam/plans' },
      { key: '/eam/orders', label: '维护工单', icon: ClipboardList, path: '/eam/orders' },
      { key: '/eam/failures', label: '设备故障', icon: PackageSearch, path: '/eam/failures' },
    ],
  },
  {
    key: 'qms',
    label: '质量管理',
    icon: BadgeCheck,
    children: [
      { key: '/qms/workbench', label: '质量工作台', icon: LayoutDashboard, path: '/qms/workbench' },
      { key: '/qms/inspections', label: '检验单', icon: ClipboardCheck, path: '/qms/inspections' },
      { key: '/qms/ncrs', label: '不合格品记录', icon: ClipboardX, path: '/qms/ncrs' },
    ],
  },
  {
    key: 'mm',
    label: '物料管理',
    icon: Package,
    children: [
      { key: '/mm/materials', label: '物料主数据', icon: Boxes, path: '/mm/materials' },
      { key: '/mm/material-issues', label: '生产领料', icon: PackageMinus, path: '/mm/material-issues' },
    ],
  },
  {
    key: 'admin',
    label: '系统管理',
    icon: ShieldCheck,
    children: [{ key: '/admin/users', label: '用户管理', icon: UserCog, path: '/admin/users' }],
  },
]

/** path → 页面名称（面包屑 / 标签页用） */
export const PATH_LABEL_MAP: Record<string, string> = (() => {
  const map: Record<string, string> = {}
  const walk = (items: NavItem[]) => {
    for (const item of items) {
      if (item.path) map[item.path] = item.label
      if (item.children) walk(item.children)
    }
  }
  walk(NAV_ITEMS)
  return map
})()

/** 详情页（/new、/:id/edit、/:id/review）继承列表页的名称 */
export function resolvePageLabel(pathname: string): string {
  if (PATH_LABEL_MAP[pathname]) return PATH_LABEL_MAP[pathname]

  const segments = pathname.split('/').filter(Boolean)
  if (segments.length === 0) return '仪表盘'

  const tail = segments[segments.length - 1]
  const parentPath = '/' + segments.slice(0, -1).join('/')
  const parentLabel = PATH_LABEL_MAP[parentPath]

  if (parentLabel) {
    if (tail === 'new') return `${parentLabel} · 新增`
    if (tail === 'edit') return `${parentLabel} · 编辑`
    if (tail === 'review') return `${parentLabel} · 审核`
    return parentLabel
  }

  return tail
}

/** 面包屑：优先用菜单层级，找不到时退回路径分段 */
export function resolveBreadcrumbs(pathname: string): { label: string; path: string }[] {
  const crumbs: { label: string; path: string }[] = [{ label: '首页', path: '/' }]
  const segments = pathname.split('/').filter(Boolean)
  if (segments.length === 0) return crumbs

  const groupPath = '/' + segments[0]
  const group = NAV_ITEMS.find((item) =>
    item.children?.some((child) => child.path?.startsWith(groupPath))
  )

  if (group) {
    crumbs.push({ label: group.label, path: groupPath })
  }

  const basePath = segments.length >= 2 ? '/' + segments.slice(0, 2).join('/') : groupPath
  const baseLabel = PATH_LABEL_MAP[basePath]
  if (baseLabel && baseLabel !== group?.label) {
    crumbs.push({ label: baseLabel, path: basePath })
  }

  if (segments.length > 2) {
    crumbs.push({ label: resolvePageLabel(pathname), path: pathname })
  }

  return crumbs
}
