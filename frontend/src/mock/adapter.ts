import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { getDb, type MockUser } from './db'
import { handleMockRequest, MockApiError } from './handlers'

const MIN_DELAY = 90
const MAX_DELAY = 220

function delay(): Promise<void> {
  const duration = MIN_DELAY + Math.random() * (MAX_DELAY - MIN_DELAY)
  return new Promise((resolve) => window.setTimeout(resolve, duration))
}

function normalizePath(url: string): string {
  let path = url.replace(/^[a-z]+:\/\/[^/]+/i, '')
  path = path.split('?')[0]
  path = path.replace(/^\/api(?=\/|$)/, '')
  return path || '/'
}

function parseBody(data: unknown): any {
  if (data === undefined || data === null) return null
  if (typeof FormData !== 'undefined' && data instanceof FormData) {
    const result: Record<string, any> = {}
    data.forEach((value, key) => {
      result[key] = value
    })
    return result
  }
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch {
      return data
    }
  }
  return data
}

function resolveUser(config: InternalAxiosRequestConfig): MockUser | null {
  const headers = config.headers as any
  let token = ''
  if (headers) {
    token =
      typeof headers.get === 'function'
        ? String(headers.get('Authorization') ?? '')
        : String(headers.Authorization ?? headers.authorization ?? '')
  }
  if (!token.startsWith('Bearer ')) return null
  const raw = token.slice('Bearer '.length)
  if (!raw.startsWith('mock.')) return null
  const username = raw.slice('mock.'.length)
  const db = getDb()
  const user = (db.users as MockUser[]).find(
    (item) => item.username === username && !(item as any).is_deleted
  )
  return user ?? null
}

export const mockAdapter: AxiosAdapter = async (config) => {
  await delay()

  const method = (config.method ?? 'get').toUpperCase()
  const path = normalizePath(config.url ?? '')
  const query: Record<string, any> = { ...(config.params ?? {}) }
  const queryString = (config.url ?? '').split('?')[1]
  if (queryString) {
    new URLSearchParams(queryString).forEach((value, key) => {
      if (query[key] === undefined) query[key] = value
    })
  }

  const requestConfig = config as InternalAxiosRequestConfig

  try {
    const result = handleMockRequest({
      method,
      path,
      query,
      body: parseBody(config.data),
      user: resolveUser(requestConfig),
      config: requestConfig,
    })
    const response: AxiosResponse = {
      data: result.data,
      status: result.status,
      statusText: result.status === 201 ? 'Created' : 'OK',
      headers: {},
      config: requestConfig,
    }
    return response
  } catch (error) {
    if (error instanceof MockApiError) {
      error.response.config = requestConfig
      throw error
    }
    throw error
  }
}
