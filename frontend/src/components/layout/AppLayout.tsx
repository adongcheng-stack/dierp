import React, { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Sidebar, SIDEBAR_WIDTH } from './Sidebar'
import { Header } from './Header'
import { PageTabs, type TabItem } from './PageTabs'
import { resolvePageLabel } from './menuConfig'
import useUIStore from '../../stores/uiStore'

interface AppLayoutProps {
  children: React.ReactNode
}

const HOME_TAB: TabItem = { key: '/', label: '仪表盘', closable: false }

/**
 * 应用外壳：侧边栏 + 顶栏 + 多页签 + 内容区。
 * 结构与视觉均对齐 MES：内容区为下沉底色，页面自身负责面板与工具条。
 */
const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarCollapsed } = useUIStore()
  const [tabs, setTabs] = useState<TabItem[]>([HOME_TAB])

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

  return (
    <div className="h-screen overflow-hidden bg-surface-sunken">
      <Sidebar />

      <div
        className="flex h-full flex-col transition-[margin] duration-300 ease-in-out"
        style={{ marginLeft: sidebarCollapsed ? 0 : SIDEBAR_WIDTH }}
      >
        <div className="z-30 shrink-0">
          <Header />
          <PageTabs
            tabs={tabs}
            activeKey={location.pathname}
            onTabClick={(tab) => navigate(tab.key)}
            onTabClose={handleTabClose}
          />
        </div>

        <main className="min-h-0 flex-1 overflow-auto">
          <div className="page-content p-4">{children}</div>
        </main>
      </div>
    </div>
  )
}

export default AppLayout
