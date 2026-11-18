import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark'

interface ThemeState {
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
}

/** 把主题写到 <html class="dark">，Tailwind 与 antd 共用这个开关 */
export function applyTheme(theme: ThemeMode) {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      setTheme: (theme) => {
        applyTheme(theme)
        set({ theme })
      },
      toggleTheme: () => {
        const next: ThemeMode = get().theme === 'light' ? 'dark' : 'light'
        applyTheme(next)
        set({ theme: next })
      },
    }),
    {
      name: 'erp-theme',
      onRehydrateStorage: () => (state) => {
        // 首屏渲染前恢复主题，避免亮暗闪烁
        applyTheme(state?.theme ?? 'light')
      },
    }
  )
)

// 模块加载时立即应用（persist 的 onRehydrate 是同步 localStorage，通常已完成）
applyTheme(useThemeStore.getState().theme)
