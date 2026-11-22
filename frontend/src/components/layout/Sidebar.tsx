import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronRight, Factory } from 'lucide-react'
import { cn } from '../../lib/utils'
import { NAV_ITEMS, type NavItem } from './menuConfig'
import { NAV_SECTIONS } from './navSections'

const SIDEBAR_WIDTH = 240

const NAV_BASE =
  'group flex w-full min-h-11 items-center gap-2.5 border-s-2 border-transparent text-sm transition-colors duration-150'

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

interface SidebarProps {
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

export function Sidebar({ mobileOpen = false, onCloseMobile }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()

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
            else if (item.path) {
              navigate(item.path)
              onCloseMobile?.()
            }
          }}
          aria-current={active && !hasChildren ? 'page' : undefined}
          aria-expanded={hasChildren ? expanded : undefined}
          aria-label={item.label}
          title={item.label}
          className={cn(
            NAV_BASE,
            level > 0 ? 'ps-9 pe-3' : 'px-3',
            active && !hasChildren
              ? 'border-brand bg-brand-soft font-semibold text-brand-ink'
              : parentActive
                ? 'border-brand bg-brand-soft font-semibold text-brand-ink'
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
          <span className="sidebar-label min-w-0 flex-1 truncate text-left">{item.label}</span>
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
            className="overflow-hidden"
            hidden={!expanded}
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
        'app-sidebar flex flex-col border-e border-line bg-surface',
        mobileOpen && 'is-open'
      )}
    >
      {/* Logo 区域 */}
      <div className="flex h-14 shrink-0 items-center border-b border-line px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-line text-brand">
            <Factory className="h-5 w-5" />
          </div>
          <div className="overflow-hidden">
            <h1 className="sidebar-label truncate text-sm font-semibold tracking-tight text-ink">DIERP</h1>
            <p className="sidebar-label truncate text-xs text-ink-soft">ERP 管理系统</p>
          </div>
        </div>
      </div>

      {/* 菜单区域 */}
      <div className="flex min-h-0 flex-1 flex-col p-2">
        <nav className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide">
          <div className="space-y-0.5">
            {NAV_SECTIONS.map((section, sectionIndex) => (
              <div key={section.title}>
                {sectionIndex > 0 && <div className="mx-3 my-2 border-t border-line" />}
                <div className="sidebar-label px-3 pb-1 pt-2 text-xs text-ink-soft">
                  {section.title}
                </div>
                {section.keys.map((key) => {
                  const item = NAV_ITEMS.find((candidate) => candidate.key === key)
                  return item ? <div key={item.key}>{renderItem(item)}</div> : null
                })}
              </div>
            ))}
          </div>
        </nav>
        <div className="border-t border-line px-3 py-2 text-xs text-ink-soft">
          <span className="sidebar-label">Demo</span>
          <span className="sidebar-label ms-2 border-s border-line ps-2">v1.0</span>
        </div>
      </div>
    </aside>
  )
}

export { SIDEBAR_WIDTH }
