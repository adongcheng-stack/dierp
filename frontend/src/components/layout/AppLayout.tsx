import React, { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { PageTabs, type TabItem } from './PageTabs'
import { resolvePageLabel } from './menuConfig'
import useUIStore from '../../stores/uiStore'

interface AppLayoutProps {
  children: React.ReactNode
}

const HOME_TAB: TabItem = { key: '/', label: '首页', closable: false }

/**
 * 应用外壳：侧边栏 + 顶栏 + 多页签 + 内容区。
 * 结构与视觉均对齐 MES：内容区为下沉底色，页面自身负责面板与工具条。
 */
const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarCollapsed } = useUIStore()
  const [tabs, setTabs] = useState<TabItem[]>([HOME_TAB])
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const canvasRef = useRef<HTMLElement>(null)
  const isAiPage = location.pathname === '/ai'

  useEffect(() => {
    canvasRef.current?.scrollTo(0, 0)
    setMobileNavOpen(false)
  }, [location.pathname])

  // 路由变化 → 追加页签（已存在则只切换激活态）
  useEffect(() => {
    // 兼容 /dashboard 这类等价入口，避免与首页页签重复
    const pathname = location.pathname === '/dashboard' ? '/' : location.pathname
    const label = resolvePageLabel(pathname)
    setTabs((prev) => {
      if (prev.some((tab) => tab.key === pathname)) return prev
      return [...prev, { key: pathname, label, closable: pathname !== '/' }]
    })
  }, [location.pathname])

  const handleTabClose = (key: string) => {
    setTabs((prev) => {
      const index = prev.findIndex((tab) => tab.key === key)
      if (index < 0) return prev
      const next = prev.filter((tab) => tab.key !== key)
      if (key === location.pathname) {
        const fallback = next[index - 1] ?? next[next.length - 1] ?? HOME_TAB
        navigate(fallback.key)
      }
      return next.length > 0 ? next : [HOME_TAB]
    })
  }

  /** 批量关闭的公共兜底：若当前激活页签被关掉，跳到保留列表里最近的页签 */
  const applyBatchClose = (next: TabItem[], fallback: string) => {
    setTabs(next.length > 0 ? next : [HOME_TAB])
    if (!next.some((tab) => tab.key === location.pathname)) {
      navigate(next.find((tab) => tab.key === fallback)?.key ?? fallback)
    }
  }

  const handleCloseOthers = (key: string) => {
    applyBatchClose(
      tabs.filter((tab) => !tab.closable || tab.key === key),
      key,
    )
  }

  const handleCloseLeft = (key: string) => {
    const index = tabs.findIndex((tab) => tab.key === key)
    if (index < 0) return
    applyBatchClose(
      tabs.filter((tab, i) => i >= index || !tab.closable),
      key,
    )
  }

  const handleCloseRight = (key: string) => {
    const index = tabs.findIndex((tab) => tab.key === key)
    if (index < 0) return
    applyBatchClose(
      tabs.filter((tab, i) => i <= index || !tab.closable),
      key,
    )
  }

  const handleCloseAll = () => {
    applyBatchClose(
      tabs.filter((tab) => !tab.closable),
      HOME_TAB.key,
    )
  }

  return (
    <div className="app-shell bg-surface-sunken" data-collapsed={sidebarCollapsed ? 'true' : 'false'}>
      <Sidebar mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />
      <button
        type="button"
        aria-label="关闭导航"
        tabIndex={mobileNavOpen ? 0 : -1}
        className={`app-sidebar-backdrop${mobileNavOpen ? ' is-open' : ''}`}
        onClick={() => setMobileNavOpen(false)}
      />

      <div className="app-main">
        <div className="shrink-0">
          <Header onToggleMobileNav={() => setMobileNavOpen((open) => !open)} />
          <PageTabs
            tabs={tabs}
            activeKey={location.pathname}
            onTabClick={(tab) => navigate(tab.key)}
            onTabClose={handleTabClose}
            onCloseOthers={handleCloseOthers}
            onCloseLeft={handleCloseLeft}
            onCloseRight={handleCloseRight}
            onCloseAll={handleCloseAll}
          />
        </div>

        <main ref={canvasRef} className={`app-canvas${isAiPage ? ' ai-canvas' : ''}`}>
          <div className={`page-content p-4 md:p-6${isAiPage ? ' ai-full-page' : ''}`}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default AppLayout
