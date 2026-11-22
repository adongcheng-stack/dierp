import { Button, Space } from 'antd'
import { AlertOutlined } from '@ant-design/icons'

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="加载中" className="flex flex-col">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center gap-4 border-b border-line py-3 last:border-b-0">
          <span className="animate-skeleton-pulse h-3 w-24 bg-surface-hover" />
          <span className="animate-skeleton-pulse h-3 flex-1 bg-surface-hover" />
          <span className="animate-skeleton-pulse h-3 w-16 bg-surface-hover" />
        </div>
      ))}
    </div>
  )
}

export function EmptyState({ text, actionText, onAction }: { text: string; actionText?: string; onAction?: () => void }) {
  return (
    <div className="flex flex-col items-start gap-2 py-8">
      <p className="text-md text-ink-soft">{text}</p>
      {actionText && onAction && (
        <Button type="link" onClick={onAction} className="!px-0">{actionText}</Button>
      )}
    </div>
  )
}

export function ErrorState({ text, onRetry }: { text: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-4 border-s-2 border-status-error ps-4 py-6">
      <Space align="start">
        <AlertOutlined className="mt-1 text-status-error" aria-hidden="true" />
        <span className="text-md text-ink">{text}</span>
      </Space>
      {onRetry && <Button onClick={onRetry}>刷新</Button>}
    </div>
  )
}
