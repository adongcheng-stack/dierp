import { describe, expect, it, vi } from 'vitest'
import { getErrorMessage, handleApiError } from './errorHandler'

describe('统一错误处理', () => {
  it('403 拦截器标记优先展示', () => {
    const error = {
      response: { status: 403, data: { detail: '原始后端文案' } },
      userMessage: '权限不足：当前角色无权执行该操作',
    }
    expect(getErrorMessage(error)).toBe('权限不足：当前角色无权执行该操作')
  })

  it('无标记时读取后端 detail 字符串', () => {
    expect(getErrorMessage({ response: { status: 400, data: { detail: '客户编码已存在' } } }))
      .toBe('客户编码已存在')
  })

  it('结构化业务错误读取 message 字段', () => {
    expect(
      getErrorMessage({ response: { status: 400, data: { detail: { message: 'BOM 存在循环引用' } } } })
    ).toBe('BOM 存在循环引用')
  })

  it('无响应时使用 error.message', () => {
    expect(getErrorMessage({ message: 'Network Error' })).toBe('Network Error')
  })

  it('handleApiError 走调用方提供的 notifier', () => {
    const error = vi.fn()
    handleApiError({ response: { status: 500, data: { detail: '内部错误' } } }, { error })
    expect(error).toHaveBeenCalledWith('内部错误')
  })
})
