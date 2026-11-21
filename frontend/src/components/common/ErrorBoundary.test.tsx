import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ErrorBoundary from './ErrorBoundary'

let shouldThrow = true
function Bomb() {
  if (shouldThrow) throw new Error('模拟渲染异常')
  return <div>正常内容</div>
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    shouldThrow = true
  })

  it('子组件正常时原样渲染', () => {
    shouldThrow = false
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText('正常内容')).toBeInTheDocument()
  })

  it('子组件抛错时展示降级界面而非白屏', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('页面加载失败')).toBeInTheDocument()
    expect(screen.getByText('模拟渲染异常')).toBeInTheDocument()
    expect(consoleSpy).toHaveBeenCalled()
    consoleSpy.mockRestore()
  })

  it('调用 reset 后清除错误并恢复渲染', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary
        fallback={(_error, reset) => (
          <button
            type="button"
            onClick={() => {
              shouldThrow = false
              reset()
            }}
          >
            重试
          </button>
        )}
      >
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.queryByText('正常内容')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(screen.getByText('正常内容')).toBeInTheDocument()
    consoleSpy.mockRestore()
  })

  it('onError 上报回调被调用', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const onError = vi.fn()
    render(
      <ErrorBoundary onError={onError} fallback={() => <div>自定义降级</div>}>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText('自定义降级')).toBeInTheDocument()
    expect(onError).toHaveBeenCalledTimes(1)
    consoleSpy.mockRestore()
  })
})
