import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { App as AntdApp, Dropdown, type MenuProps } from 'antd'
import {
  ChevronDown,
  ChevronRight,
  LogOut,
  Maximize,
  Minimize,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  RotateCw,
  Sun,
  User,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useConfirm } from '../common/ConfirmProvider'
import { useAuthStore } from '../../stores/authStore'
import useUIStore from '../../stores/uiStore'
import { useThemeStore } from '../../stores/themeStore'
import { resolveBreadcrumbs } from './menuConfig'
import { isMockMode, resetDb } from '../../mock'
import api, { getErrorMessage } from '../../services/api'

export function Header({ onToggleMobileNav }: { onToggleMobileNav?: () => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { theme, toggleTheme } = useThemeStore()
  const confirm = useConfirm()
  const { message } = AntdApp.useApp()

  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const breadcrumbs = resolveBreadcrumbs(location.pathname)

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true)
    window.setTimeout(() => window.location.reload(), 120)
  }, [])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      void document.documentElement.requestFullscreen()
    } else {
      void document.exitFullscreen()
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const handleLogout = () => {
    confirm({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      okText: '确认退出',
      cancelText: '取消',
      onOk: () => {
        logout()
        navigate('/login', { replace: true })
      },
    })
  }

  const handleResetDemo = () => {
    confirm({
      title: '重置演示数据',
      content: isMockMode
        ? '将清空本次演示中所有新增和修改的数据，并恢复到初始演示数据。确定继续吗？'
        : '将清空排程批次、插单场景、维护工单与故障记录等运行时数据，并重建一套演示场景。订单、BOM、工艺路线等主数据不受影响。确定继续吗？',
      okText: '确认重置',
      cancelText: '取消',
      icon: 'warning',
      onOk: async () => {
        if (isMockMode) {
          resetDb()
          window.location.reload()
          return
        }
        try {
          const { data } = await api.post('/planning/demo/reset', {
            rebuild_run: true,
            with_scenario: true,
          })
          const seeded = data?.seeded ?? {}
          message.success(
            `演示数据已重置：排程 ${seeded.run_number ?? '-'}，工序 ${seeded.operations ?? 0} 条，场景 ${seeded.scenario_id ? '1 个' : '无'}`
          )
          window.setTimeout(() => window.location.reload(), 700)
        } catch (error) {
          message.error(getErrorMessage(error))
        }
      },
    })
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <User className="h-4 w-4" />,
      label: (
        <div className="py-0.5">
          <div className="text-sm font-medium text-ink">{user?.full_name || user?.username || '未登录'}</div>
          <div className="flex items-center gap-2 text-xs text-ink-soft">
            {[user?.department, user?.role].filter(Boolean).map((part, index) => (
              <span key={part} className={index ? 'border-s border-line ps-2' : ''}>{part}</span>
            ))}
            {!user && <span>DIERP ERP</span>}
          </div>
        </div>
      ),
      disabled: true,
    },
    { type: 'divider' },
    // 演示数据重置：mock 模式所有用户可用；真实后端仅管理员（后端同样校验）
    ...(isMockMode || user?.role === 'ADMIN'
      ? [
          {
            key: 'reset-demo',
            icon: <RotateCw className="h-4 w-4" />,
            label: isMockMode ? '重置演示数据' : '清理演示数据',
          },
        ]
      : []),
    {
      key: 'logout',
      icon: <LogOut className="h-4 w-4" />,
      label: '退出登录',
      danger: true,
    },
  ]

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-surface px-4">
      {/* 左侧：折叠 + 刷新 + 面包屑 */}
      <nav className="flex min-w-0 items-center gap-2 text-[13px]">
        <button
          type="button"
          onClick={() => { toggleSidebar(); onToggleMobileNav?.() }}
          className="inline-flex h-11 w-11 items-center justify-center rounded-none text-ink-soft transition-colors hover:bg-surface-hover hover:text-ink"
          title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          {sidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        </button>

        <button
          type="button"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="inline-flex h-11 w-11 items-center justify-center rounded-none text-ink-faint transition-colors hover:bg-surface-hover hover:text-ink disabled:opacity-50"
          title="刷新数据"
        >
          <RotateCw className={cn('h-5 w-5', isRefreshing && 'animate-spin')} />
        </button>

        <div className="flex min-w-0 items-center gap-1 overflow-hidden">
          {breadcrumbs.map((crumb, index) => (
            <span key={`${crumb.path}-${index}`} className="flex items-center gap-1 whitespace-nowrap">
              {index > 0 && <ChevronRight className="h-3.5 w-3.5 text-ink-faint" aria-hidden="true" />}
              <button
                type="button"
                onClick={() => {
                  if (index < breadcrumbs.length - 1) navigate(crumb.path)
                }}
                className={cn(
                  'truncate transition-colors',
                  index === breadcrumbs.length - 1
                    ? 'cursor-default font-medium text-ink'
                    : 'text-ink-soft hover:text-ink'
                )}
              >
                {crumb.label}
              </button>
            </span>
          ))}
        </div>
      </nav>

      {/* 右侧操作区 */}
      <div className="flex shrink-0 items-center gap-1">
        <button
          type="button"
          onClick={toggleTheme}
          className="inline-flex h-11 w-11 items-center justify-center rounded-none text-ink-soft transition-colors hover:bg-surface-hover hover:text-ink"
          title={theme === 'light' ? '切换到暗色模式' : '切换到亮色模式'}
        >
          {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        </button>

        <button
          type="button"
          onClick={toggleFullscreen}
          className="inline-flex h-11 w-11 items-center justify-center rounded-none text-ink-soft transition-colors hover:bg-surface-hover hover:text-ink"
          title={isFullscreen ? '退出全屏' : '全屏'}
        >
          {isFullscreen ? <Minimize className="h-5 w-5" /> : <Maximize className="h-5 w-5" />}
        </button>

        <div className="mx-1 hidden h-5 w-px bg-line sm:block" />

        <Dropdown
          menu={{
            items: userMenuItems,
            onClick: ({ key }) => {
              if (key === 'logout') handleLogout()
              if (key === 'reset-demo') handleResetDemo()
            },
          }}
          placement="bottomRight"
          trigger={['click']}
        >
          <button
            type="button"
            className="flex items-center gap-2 rounded-none px-2 py-1.5 transition-colors hover:bg-surface-hover"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full border border-line bg-surface text-xs font-medium text-brand-ink">
              {(user?.full_name || user?.username || 'U').charAt(0)}
            </div>
            <span className="hidden max-w-[140px] truncate text-[13px] text-ink sm:block">
              {user?.full_name || user?.username || '用户'}
            </span>
            <ChevronDown className="h-4 w-4 text-ink-faint" />
          </button>
        </Dropdown>
      </div>
    </header>
  )
}
