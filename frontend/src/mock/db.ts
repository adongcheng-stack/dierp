import snapshot from './snapshot.json'

export interface MockUser {
  id: number
  username: string
  email: string
  full_name: string
  role: string
  department: string
  is_active?: boolean
}

export type MockDb = Record<string, any>

const STORAGE_KEY = 'dierp-demo-db-v1'

export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

export function createInitialDb(): MockDb {
  return clone(snapshot) as MockDb
}

let state: MockDb | null = null

/** 读取演示数据：优先使用浏览器里持久化的版本，否则回落到内置快照 */
export function getDb(): MockDb {
  if (state) return state
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed && parsed.version === (snapshot as any).version) {
        state = parsed as MockDb
        return state
      }
    }
  } catch {
    // 存储损坏时忽略，回落到快照
  }
  state = createInitialDb()
  return state
}

export function saveDb(): void {
  if (!state) return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // 忽略存储配额异常
  }
}

/** 恢复成内置快照，并清掉浏览器里的演示改动 */
export function resetDb(): void {
  state = createInitialDb()
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // 忽略
  }
}

export function hasStoredDb(): boolean {
  try {
    return Boolean(window.localStorage.getItem(STORAGE_KEY))
  } catch {
    return false
  }
}
