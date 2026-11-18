import { create } from 'zustand'

interface UIState {
  // 侧边栏折叠状态
  sidebarCollapsed: boolean
  
  // 全局加载状态
  globalLoading: boolean
  
  // 消息提示
  message: {
    type?: 'success' | 'error' | 'warning' | 'info'
    content?: string
  } | null
  
  // Actions
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setGlobalLoading: (loading: boolean) => void
  showMessage: (type: 'success' | 'error' | 'warning' | 'info', content: string) => void
  clearMessage: () => void
}

const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  globalLoading: false,
  message: null,
  
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  
  setGlobalLoading: (loading) => set({ globalLoading: loading }),
  
  showMessage: (type, content) =>
    set({ message: { type, content } }),
  
  clearMessage: () => set({ message: null })
}))

export default useUIStore

