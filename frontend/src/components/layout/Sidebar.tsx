import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronRight, Factory } from 'lucide-react'
import { cn } from '../../lib/utils'
import useUIStore from '../../stores/uiStore'
import { NAV_ITEMS, type NavItem } from './menuConfig'

const SIDEBAR_WIDTH = 240

const NAV_BASE =
  'group flex w-full items-center gap-2.5 rounded-md py-2 text-sm transition-colors duration-150'

/** 当前路径是否落在某个菜单项下（详情页也高亮对应列表项） */
function isPathActive(pathname: string, path?: string) {
  if (!path) return false
  if (path === '/') return pathname === '/'
  return pathname === path || pathname.startsWith(`${path}/`)
}

function findActiveParent(pathname: string): string | null {
  for (const item of NAV_ITEMS) {
    if (item.children?.some((child) => isPathActive(pathname, child.path))) {
      return item.key
    }
  }
  return null
}

export function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarCollapsed } = useUIStore()

  const activeParent = useMemo(() => findActiveParent(location.pathname), [location.pathname])
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(
    () => new Set(activeParent ? [activeParent] : [])
  )

  // 路由变化时自动展开当前分组的父级
  useEffect(() => {
    if (activeParent) setExpandedKeys(new Set([activeParent]))
  }, [activeParent])

  const toggleExpand = (key: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const renderItem = (item: NavItem, level = 0) => {
    const hasChildren = !!item.children?.length
    const expanded = expandedKeys.has(item.key)
    const active = isPathActive(location.pathname, item.path)
    const parentActive = !hasChildren && level === 0 && active
    const Icon = item.icon

    return (
      <div key={item.key}>
        <button
          type="button"
          onClick={() => {
            if (hasChildren) toggleExpand(item.key)
            else if (item.path) navigate(item.path)
          }}
          aria-current={active && !hasChildren ? 'page' : undefined}
          aria-expanded={hasChildren ? expanded : undefined}
          className={cn(
            NAV_BASE,
            level > 0 ? 'pl-9 pr-3' : 'px-3',
            active && !hasChildren
              ? 'bg-brand-soft font-medium text-brand-ink'
              : parentActive
                ? 'bg-brand-soft font-medium text-brand-ink'
                : level === 0 && hasChildren && expanded
                  ? 'font-medium text-ink hover:bg-surface-hover'
                  : 'text-ink-soft hover:bg-surface-hover hover:text-ink'
          )}
        >
          <span
            className={cn(
              'shrink-0 transition-colors',
              active && !hasChildren
                ? 'text-brand-ink'
                : level === 0 && hasChildren && expanded
                  ? 'text-brand'
                  : 'text-ink-faint group-hover:text-ink-soft'
            )}
          >
            <Icon className={level > 0 ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
          </span>
          <span className="flex-1 truncate text-left">{item.label}</span>
          {hasChildren && (
            <ChevronRight
              className={cn(
                'h-3.5 w-3.5 shrink-0 text-ink-faint transition-transform duration-200',
                expanded && 'rotate-90'
              )}
            />
          )}
        </button>

        {hasChildren && (
          <div
            className="overflow-hidden transition-all duration-200 ease-in-out"
            style={{ maxHeight: expanded ? '1000px' : '0', opacity: expanded ? 1 : 0 }}
          >
            <div className="mt-0.5 space-y-0.5">
              {item.children!.map((child) => renderItem(child, level + 1))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-full flex-col border-r border-line bg-surface',
        'transition-[transform] duration-300 ease-in-out',
        sidebarCollapsed ? 'translate-x-[-240px]' : 'translate-x-0'
      )}
      style={{ width: SIDEBAR_WIDTH }}
    >
      {/* Logo 区域 */}
      <div className="flex h-14 shrink-0 items-center border-b border-line px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-card text-brand">
            <Factory className="h-5 w-5" />
          </div>
          <div className="overflow-hidden">
            <h1 className="truncate text-sm font-semibold tracking-tight text-ink">DIERP</h1>
            <p className="truncate text-xs text-ink-soft">ERP 管理系统</p>
          </div>
        </div>
      </div>

      {/* 菜单区域 */}
      <div className="flex min-h-0 flex-1 flex-col p-2">
        <nav className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide">
          <div className="space-y-0.5">{NAV_ITEMS.map((item) => renderItem(item))}</div>
        </nav>
        <div className="border-t border-line px-3 py-2 text-[11px] text-ink-faint">
Demo · v1.0
        </div>
      </div>
    </aside>
  )
}

export { SIDEBAR_WIDTH }
