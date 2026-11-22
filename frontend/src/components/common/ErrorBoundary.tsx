import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** 自定义降级界面；未提供时使用内置的纯 HTML 兜底（不依赖 antd，避免样式引擎自身出错时二次崩溃） */
  fallback?: (error: Error, reset: () => void) => ReactNode
  /** 错误上报回调，可接入监控平台 */
  onError?: (error: Error, info: ErrorInfo) => void
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * 全局渲染错误边界。
 *
 * 挂在应用最外层：任意子组件在 render / 生命周期 / 构造函数中抛错时，
 * 不再整页白屏，而是展示可恢复的提示界面。演示环境下用户可点「重试」继续操作。
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // 控制台保留堆栈供排查；生产可通过 onError 上报
    console.error('[ErrorBoundary] 页面渲染异常', error, info.componentStack)
    this.props.onError?.(error, info)
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render(): ReactNode {
    const { error } = this.state
    if (!error) return this.props.children
    if (this.props.fallback) return this.props.fallback(error, this.reset)

    return (
      <div role="alert" style={styles.container}>
        <div style={styles.card}>
          <div style={styles.icon}>!</div>
          <h1 style={styles.title}>页面加载失败</h1>
          <p style={styles.desc}>
            页面渲染过程中出现异常，您可以重试当前操作或重新加载页面。
          </p>
          <pre style={styles.detail}>{error.message}</pre>
          <div style={styles.actions}>
            <button type="button" style={styles.primary} onClick={this.reset}>
              重试
            </button>
            <button
              type="button"
              style={styles.secondary}
              onClick={() => window.location.reload()}
            >
              重新加载
            </button>
          </div>
        </div>
      </div>
    )
  }
}

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    background: 'var(--color-paper-2)',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  card: {
    maxWidth: '560px',
    width: '100%',
    padding: '32px',
    borderRadius: '12px',
    background: 'var(--color-paper)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
    textAlign: 'center' as const,
  },
  icon: {
    width: '48px',
    height: '48px',
    margin: '0 auto 16px',
    borderRadius: '50%',
    background: 'color-mix(in srgb, var(--color-error) 10%, var(--color-paper))',
    color: 'var(--color-error)',
    fontSize: '28px',
    lineHeight: '48px',
    fontWeight: 700,
  },
  title: { margin: '0 0 8px', fontSize: '20px', color: 'var(--color-ink)' },
  desc: { margin: '0 0 16px', fontSize: '14px', color: 'var(--color-ink-soft)' },
  detail: {
    margin: '0 0 24px',
    padding: '12px',
    borderRadius: '6px',
    background: 'var(--color-paper-2)',
    color: 'var(--color-muted)',
    fontSize: '12px',
    textAlign: 'left' as const,
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  },
  actions: { display: 'flex', gap: '12px', justifyContent: 'center' },
  primary: {
    padding: '8px 20px',
    border: 'none',
    borderRadius: '6px',
    background: 'var(--color-accent)',
    color: 'var(--color-paper)',
    fontSize: '14px',
    cursor: 'pointer',
  },
  secondary: {
    padding: '8px 20px',
    border: '1px solid var(--color-field-edge)',
    borderRadius: '6px',
    background: 'var(--color-paper)',
    color: 'var(--color-ink-soft)',
    fontSize: '14px',
    cursor: 'pointer',
  },
}

export default ErrorBoundary
