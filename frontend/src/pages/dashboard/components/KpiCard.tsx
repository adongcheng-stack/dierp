import type { ReactNode } from 'react'

export interface KpiAccent { bar: string; bg: string; text: string }

interface Props {
  title: string
  value: string
  suffix?: string
  hint?: string
  tone?: 'default' | 'good' | 'warn' | 'bad'
  icon?: ReactNode
  onClick?: () => void
  /** 兼容既有调用：颜色由语义 token 接管，不再用字面量着色 */
  accent?: KpiAccent
  /** 0~1 的占比，渲染为底部细进度条 */
  progress?: number
}

const TONE: Record<string, string> = {
  default: 'text-ink',
  good: 'text-status-success',
  warn: 'text-status-warning',
  bad: 'text-status-error',
}

/** 账本式的 KPI 单元：列线分隔，不做可点击磁贴的悬停抬升。 */
export function KpiCard({ title, value, suffix, hint, tone = 'default', icon, onClick, progress }: Props) {
  const interactive = Boolean(onClick)
  return (
    <div
      className={`kpi-cell border-s border-line ps-4 first:border-s-0 first:ps-0 ${interactive ? 'cursor-pointer' : ''}`}
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={interactive ? (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick?.()
        }
      } : undefined}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="min-w-0 truncate text-sm text-ink-soft">{title}</span>
        {icon && <span className="shrink-0 text-ink-soft" aria-hidden="true">{icon}</span>}
      </div>
      <div className={`mt-2 text-2xl font-semibold leading-none tabular-nums ${TONE[tone] ?? TONE.default}`}>
        {value}
        {suffix && <span className="ms-1 text-sm font-normal text-ink-soft">{suffix}</span>}
      </div>
      {progress != null && (
        <div className="mt-3 h-1 w-full overflow-hidden bg-surface-hover">
          <div
            className="h-full bg-brand"
            style={{ transform: `scaleX(${Math.min(Math.max(progress, 0), 1)})`, transformOrigin: 'left' }}
          />
        </div>
      )}
      {hint && <div className="mt-2 truncate text-sm text-ink-soft">{hint}</div>}
    </div>
  )
}
