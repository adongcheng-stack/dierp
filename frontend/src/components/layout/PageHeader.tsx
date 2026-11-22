import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: ReactNode
  actions?: ReactNode
}

/**
 * 页面标题区骨架（与 MES 同一规格）：
 * 标题只建立层级，不做营销页式字号对比；操作区与标题基线对齐。
 */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-lg font-semibold tracking-tight text-ink">{title}</h1>
        {description && <div className="mt-1 text-sm text-ink-soft">{description}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
