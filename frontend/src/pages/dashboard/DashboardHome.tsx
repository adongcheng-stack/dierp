import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Button, List, Tag } from 'antd'
import {
  ArrowRightOutlined, BarChartOutlined, CalendarOutlined, ControlOutlined,
  DashboardOutlined, FileTextOutlined, ShoppingCartOutlined, WalletOutlined,
  AppstoreOutlined, BuildOutlined,
} from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { KpiCard } from './components/KpiCard'
import { AlertPanel, type AlertItem } from './components/AlertPanel'
import { ErrorState, SkeletonRows } from '../../components/common/DataStates'

interface Cockpit { key: string; title: string; path: string; description: string }
interface Workbench { title: string; path: string; domain: string }

const ICONS: Record<string, React.ReactNode> = {
  management: <BarChartOutlined />, production: <ControlOutlined />,
  progress: <CalendarOutlined />, finance: <WalletOutlined />, sales: <ShoppingCartOutlined />,
}

const QUICK_ACTIONS = [
  { label: '新建客户', path: '/sd/customers/new', icon: <ShoppingCartOutlined /> },
  { label: '新建报价单', path: '/sd/quotations/new', icon: <FileTextOutlined /> },
  { label: '新建销售订单', path: '/sd/sales-orders/new', icon: <FileTextOutlined /> },
  { label: '新建 BOM', path: '/eng/boms/new', icon: <BuildOutlined /> },
  { label: '新建工单', path: '/pp/production-orders/new', icon: <ControlOutlined /> },
  { label: '生产领料', path: '/mm/material-issues/new', icon: <AppstoreOutlined /> },
]

const STATUS_LABEL: Record<string, string> = {
  PENDING: '待审批',
  PENDING_SALES_MANAGER: '待销售经理审批',
  PENDING_FINANCE: '待财务审批',
  PENDING_GENERAL_MANAGER: '待总经理审批',
  PENDING_APPROVAL: '待审批',
}

const pct = (v: number | undefined) => `${((v ?? 0) * 100).toFixed(1)}%`

/** 首页：待审批清单是主页签，其余指标与入口按列线排开。 */
const DashboardHome: React.FC = () => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [pending, setPending] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData((await api.get('/dashboard/home')).data)
    } catch (err: any) {
      const text = err?.userMessage ?? '加载首页数据失败'
      setError(text)
      message.error(text)
    }
    try {
      const result = await api.get('/sd/quotations/pending-approval')
      setPending(Array.isArray(result.data) ? result.data.slice(0, 5) : [])
    } catch {
      setPending([])
    } finally {
      setLoading(false)
    }
  }, [message])
  useEffect(() => { void load() }, [load])

  const summary = data?.summary ?? {}

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="首页"
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span>经营指标速览</span>
            <span className="border-s border-line ps-2">待办事项</span>
            <span className="border-s border-line ps-2">全部驾驶舱与工作台入口</span>
          </span>
        }
      />

      {error && !data ? (
        <ErrorState text={error} onRetry={() => void load()} />
      ) : loading && !data ? (
        <SkeletonRows rows={5} />
      ) : (
        <div className="flex flex-col gap-8">
          <section aria-label="待我审批的报价单">
            <div className="mb-3 flex items-baseline justify-between gap-4">
              <h2 className="text-lg font-semibold text-ink">待我审批的报价单</h2>
              <Button type="link" className="!px-0" onClick={() => navigate('/sd/pending-approvals')}>
                查看全部 <ArrowRightOutlined className="ms-1" aria-hidden="true" />
              </Button>
            </div>
            {pending.length === 0 ? (
              <div className="border-t border-line py-8 text-md text-ink-soft">暂无待审批事项</div>
            ) : (
              <List
                dataSource={pending}
                renderItem={(item) => {
                  const record = item as Record<string, string | number | undefined>
                  const number = String(record.quotation_number ?? '-')
                  const customer = String(record.customer_name ?? record.customer_id ?? '-')
                  const status = String(record.status ?? 'PENDING')
                  return (
                    <List.Item className="!border-b !border-line !py-3">
                      <List.Item.Meta
                        title={
                          <Button type="link" className="!px-0" onClick={() => navigate('/sd/pending-approvals')}>
                            {number}
                          </Button>
                        }
                        description={<span className="text-ink-soft">{customer}</span>}
                      />
                      <Tag color="warning">{STATUS_LABEL[status] ?? status}</Tag>
                    </List.Item>
                  )
                }}
              />
            )}
          </section>

          <section aria-label="经营指标" className="grid grid-cols-1 gap-4 border-t border-line pt-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="销售订单额" value={`¥${(summary.sales_amount ?? 0).toLocaleString()}`}
              hint="累计销售订单金额" onClick={() => navigate('/dashboard/sales')} />
            <KpiCard title="生产完成率" value={pct(summary.production_completion)}
              progress={summary.production_completion} hint="已完工工单占比"
              onClick={() => navigate('/dashboard/production')} />
            <KpiCard title="综合 OEE" value={pct(summary.oee)}
              progress={summary.oee} hint="设备综合效率"
              onClick={() => navigate('/dashboard/management')} />
            <KpiCard title="回款率" value={pct(summary.collection_rate)}
              progress={summary.collection_rate} hint="已开票金额回款占比"
              onClick={() => navigate('/dashboard/finance')} />
          </section>

          <section aria-label="快捷入口" className="border-t border-line pt-4">
            <h2 className="mb-3 text-lg font-semibold text-ink">快捷入口</h2>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {QUICK_ACTIONS.map((action) => (
                <Button key={action.path} type="link" className="!px-0" icon={action.icon}
                  onClick={() => navigate(action.path)}>
                  {action.label}
                </Button>
              ))}
            </div>
          </section>

          <section aria-label="工作台" className="border-t border-line pt-4">
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 md:grid-cols-3 xl:grid-cols-5">
              {(data?.workbenches ?? []).map((item: Workbench) => (
                <button key={item.path} type="button" onClick={() => navigate(item.path)}
                  className="flex min-w-0 items-baseline justify-between gap-2 border-b border-line pb-2 text-start">
                  <span className="truncate text-md font-medium text-ink">{item.title}</span>
                  <Tag className="!m-0">{item.domain}</Tag>
                </button>
              ))}
            </div>
          </section>

          <section aria-label="驾驶舱" className="border-t border-line pt-4">
            <h2 className="mb-3 text-lg font-semibold text-ink">驾驶舱</h2>
            <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
              {(data?.cockpits ?? []).map((item: Cockpit) => (
                <button key={item.key} type="button" onClick={() => navigate(item.path)}
                  className="flex min-w-0 items-start justify-between gap-3 border-b border-line py-3 text-start">
                  <span className="min-w-0">
                    <span className="flex items-center gap-2 text-md font-medium text-ink">
                      <span className="shrink-0 text-ink-soft" aria-hidden="true">{ICONS[item.key] ?? <DashboardOutlined />}</span>
                      <span className="truncate">{item.title}</span>
                    </span>
                    <span className="mt-1 block text-sm text-ink-soft">{item.description}</span>
                  </span>
                  <ArrowRightOutlined className="mt-1 shrink-0 text-ink-soft" aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>

          <section aria-label="全局预警" className="border-t border-line pt-4">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-ink">全局预警</h2>
            <AlertPanel alerts={(data?.alerts ?? []) as AlertItem[]} />
          </section>
        </div>
      )}
    </div>
  )
}

export default DashboardHome
