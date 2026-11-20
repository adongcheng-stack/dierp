import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Boxes,
  Building2,
  ClipboardCheck,
  ClipboardList,
  FileText,
  Layers,
  PackageMinus,
  RefreshCw,
  Ticket,
  Users,
} from 'lucide-react'
import api from '../services/api'
import { PageHeader } from '../components/layout/PageHeader'
import { cn } from '../lib/utils'

interface KpiItem {
  key: string
  label: string
  hint: string
  value: number
  icon: typeof Users
  accent: string
  path: string
}

const QUICK_ACTIONS = [
  { label: '新建客户', path: '/sd/customers/new', icon: Users },
  { label: '新建报价单', path: '/sd/quotations/new', icon: FileText },
  { label: '新建销售订单', path: '/sd/sales-orders/new', icon: ClipboardList },
  { label: '新建 BOM', path: '/eng/boms/new', icon: Boxes },
  { label: '新建工单', path: '/pp/production-orders/new', icon: ClipboardCheck },
  { label: '生产领料', path: '/mm/material-issues/new', icon: PackageMinus },
]

const STATUS_LABEL: Record<string, string> = {
  PENDING: '待审批',
  PENDING_SALES_MANAGER: '待销售经理审批',
  PENDING_FINANCE: '待财务审批',
  PENDING_GENERAL_MANAGER: '待总经理审批',
  PENDING_APPROVAL: '待审批',
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [counts, setCounts] = useState({
    customers: 0,
    quotations: 0,
    salesOrders: 0,
    productionOrders: 0,
    materials: 0,
    mis: 0,
  })
  const [pendingQuotations, setPendingQuotations] = useState<Record<string, unknown>[]>([])

  const fetchAll = useCallback(async () => {
    setLoading(true)
    const endpoints = {
      customers: '/sd/customers',
      quotations: '/sd/quotations',
      salesOrders: '/sd/sales-orders',
      productionOrders: '/pp/production-orders',
      materials: '/mm/materials',
      mis: '/eng/mis',
    }

    const entries = Object.entries(endpoints)
    const results = await Promise.allSettled(entries.map(([, url]) => api.get(url)))

    const nextCounts = { ...counts }
    results.forEach((result, index) => {
      const key = entries[index][0] as keyof typeof nextCounts
      if (result.status === 'fulfilled' && Array.isArray(result.value.data)) {
        nextCounts[key] = result.value.data.length
      }
    })
    setCounts(nextCounts)

    try {
      const pending = await api.get('/sd/quotations/pending-approval')
      setPendingQuotations(Array.isArray(pending.data) ? pending.data.slice(0, 5) : [])
    } catch {
      setPendingQuotations([])
    }

    setLoading(false)
    // counts 只作为初值，避免把自身放进依赖导致循环刷新
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    void fetchAll()
  }, [fetchAll])

  const kpis: KpiItem[] = [
    {
      key: 'customers',
      label: '客户总数',
      hint: '已建档客户',
      value: counts.customers,
      icon: Users,
      accent: 'bg-brand-soft text-brand-ink',
      path: '/sd/customers',
    },
    {
      key: 'quotations',
      label: '报价单',
      hint: '累计报价单',
      value: counts.quotations,
      icon: FileText,
      accent: 'bg-[hsl(var(--chart-warning)/0.12)] text-[hsl(var(--chart-warning))]',
      path: '/sd/quotations',
    },
    {
      key: 'salesOrders',
      label: '销售订单',
      hint: '累计销售订单',
      value: counts.salesOrders,
      icon: ClipboardList,
      accent: 'bg-[hsl(var(--chart-success)/0.12)] text-[hsl(var(--chart-success))]',
      path: '/sd/sales-orders',
    },
    {
      key: 'productionOrders',
      label: '生产订单',
      hint: '累计生产工单',
      value: counts.productionOrders,
      icon: ClipboardCheck,
      accent: 'bg-[hsl(var(--b-500)/0.12)] text-[hsl(var(--b-500))]',
      path: '/pp/production-orders',
    },
    {
      key: 'materials',
      label: '物料主数据',
      hint: '不含成品物料',
      value: counts.materials,
      icon: Layers,
      accent: 'bg-[hsl(var(--n-400)/0.16)] text-ink-soft',
      path: '/mm/materials',
    },
    {
      key: 'mis',
      label: 'MI 资料',
      hint: '制造指示单',
      value: counts.mis,
      icon: Building2,
      accent: 'bg-[hsl(var(--destructive)/0.1)] text-destructive',
      path: '/eng/mis',
    },
  ]

  return (
    <div>
      <PageHeader
        title="工作台"
        description="销售报价 → 工程数据 → 生产执行 → 物料管理，全流程业务总览"
        actions={
          <button
            type="button"
            onClick={() => void fetchAll()}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-line bg-card px-3 text-xs font-medium text-ink-soft transition-colors hover:bg-surface-hover hover:text-ink"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
            刷新
          </button>
        }
      />

      {/* KPI 卡片 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {kpis.map((kpi) => {
          const Icon = kpi.icon
          return (
            <button
              key={kpi.key}
              type="button"
              onClick={() => navigate(kpi.path)}
              className="panel group p-4 text-left transition-colors hover:border-line-strong"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-xs text-ink-soft">{kpi.label}</p>
                  <p className="mt-2 text-2xl font-semibold leading-none tabular-nums text-ink">
                    {loading ? '—' : kpi.value}
                  </p>
                </div>
                <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-md', kpi.accent)}>
                  <Icon className="h-4 w-4" />
                </span>
              </div>
              <p className="mt-3 truncate text-xs text-ink-faint">{kpi.hint}</p>
            </button>
          )
        })}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {/* 待我审批 */}
        <div className="panel flex min-h-[280px] flex-col overflow-hidden lg:col-span-2">
          <div className="panel-muted flex shrink-0 items-center justify-between px-4 py-2.5">
            <h2 className="text-sm font-semibold text-ink">待我审批的报价单</h2>
            <button
              type="button"
              onClick={() => navigate('/sd/pending-approvals')}
              className="inline-flex items-center gap-1 text-xs text-brand-ink transition-colors hover:text-brand-hover"
            >
              查看全部 <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {loading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-9 animate-skeleton-pulse rounded-md bg-secondary" />
              ))}
            </div>
          ) : pendingQuotations.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 py-10 text-center">
              <ClipboardCheck className="h-8 w-8 text-ink-faint" />
              <p className="text-sm font-medium text-ink">暂无待审批事项</p>
              <p className="text-xs text-ink-soft">新的报价单提交后会出现在这里</p>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {pendingQuotations.map((item) => {
                const record = item as Record<string, string | number | undefined>
                const number = String(record.quotation_number ?? record.quotationNumber ?? '-')
                const customer = String(
                  record.customer_name ?? record.customerName ?? record.customer_id ?? '-'
                )
                const status = String(record.status ?? record.quotation_status ?? 'PENDING')
                return (
                  <li key={number}>
                    <button
                      type="button"
                      onClick={() => navigate('/sd/pending-approvals')}
                      className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition-colors hover:bg-surface-hover"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-ink">{number}</p>
                        <p className="mt-0.5 truncate text-xs text-ink-soft">{customer}</p>
                      </div>
                      <span className="shrink-0 rounded-full bg-[hsl(var(--chart-warning)/0.12)] px-2 py-0.5 text-xs text-[hsl(var(--chart-warning))]">
                        {STATUS_LABEL[status] ?? status}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* 快捷入口 */}
        <div className="panel flex flex-col overflow-hidden">
          <div className="panel-muted flex shrink-0 items-center justify-between px-4 py-2.5">
            <h2 className="text-sm font-semibold text-ink">快捷入口</h2>
            <Ticket className="h-4 w-4 text-ink-faint" />
          </div>
          <div className="grid grid-cols-2 gap-2 p-3">
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon
              return (
                <button
                  key={action.path}
                  type="button"
                  onClick={() => navigate(action.path)}
                  className="flex flex-col items-start gap-2 rounded-md border border-line bg-card px-3 py-3 text-left transition-colors hover:border-brand/40 hover:bg-brand-soft/50"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-md bg-secondary text-ink-soft">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-xs font-medium text-ink">{action.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* 业务链路说明 */}
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        {[
          { title: '销售管理', desc: '客户建档 → 报价三级审核 → 销售订单 → 发货签收', path: '/sd/customers' },
          { title: '工程管理', desc: 'BOM → 工艺路线 → MI → 生产版本建立', path: '/eng/boms' },
          { title: '生产与物料', desc: '工作中心 → 工单 → LOT卡 → 工序报工 → 生产领料', path: '/pp/work-centers' },
        ].map((item) => (
          <button
            key={item.title}
            type="button"
            onClick={() => navigate(item.path)}
            className="panel group flex items-center justify-between gap-3 p-4 text-left transition-colors hover:border-line-strong"
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">{item.title}</p>
              <p className="mt-1 text-xs leading-5 text-ink-soft">{item.desc}</p>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5" />
          </button>
        ))}
      </div>
    </div>
  )
}

export default Dashboard
