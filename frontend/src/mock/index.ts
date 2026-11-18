import api from '../services/api'
import { mockAdapter } from './adapter'
import { hasStoredDb, resetDb } from './db'

export const isMockMode = import.meta.env.VITE_MOCK === 'true'

/** 在应用渲染前把 axios 换成内存演示数据适配器 */
export function setupMockApi(): void {
  if (!isMockMode) return
  api.defaults.adapter = mockAdapter
  // 演示模式不需要等待后端
  api.defaults.timeout = 0
}

export { hasStoredDb, resetDb }
