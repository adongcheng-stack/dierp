import { useEffect, useRef, useState } from 'react'
import { ChevronsLeft, ChevronsRight, X } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface TabItem {
  /** 路由 pathname */
  key: string
  label: string
  closable: boolean
}

interface PageTabsProps {
  tabs: TabItem[]
  activeKey: string
  onTabClick: (tab: TabItem) => void
  onTabClose: (key: string) => void
}

export function PageTabs({ tabs, activeKey, onTabClick, onTabClose }: PageTabsProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const updateScrollState = () => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 0)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }

  useEffect(() => {
    updateScrollState()
    const el = scrollRef.current
    if (!el) return
    el.addEventListener('scroll', updateScrollState)
    window.addEventListener('resize', updateScrollState)
    return () => {
      el.removeEventListener('scroll', updateScrollState)
      window.removeEventListener('resize', updateScrollState)
    }
  }, [tabs])

  // 激活标签滚入视野
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const active = el.querySelector<HTMLElement>(`[data-tab-key="${CSS.escape(activeKey)}"]`)
    active?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [activeKey])

  const scrollBy = (delta: number) => {
    scrollRef.current?.scrollBy({ left: delta, behavior: 'smooth' })
  }

  return (
    <div className="relative flex items-center gap-2 border-b border-line bg-surface px-3 py-1.5">
      <button
        type="button"
        onClick={() => scrollBy(-200)}
        disabled={!canScrollLeft}
        className={cn(
          'shrink-0 rounded-md p-1 transition-colors',
          canScrollLeft
            ? 'text-ink-faint hover:bg-surface-hover hover:text-ink'
            : 'cursor-not-allowed text-ink-faint/50'
        )}
        title="向左滚动"
      >
        <ChevronsLeft className="h-3.5 w-3.5" />
      </button>

      <div className="h-5 w-px shrink-0 bg-line" />

      <div
        ref={scrollRef}
        className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto scrollbar-hide"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            data-tab-key={tab.key}
            onClick={() => onTabClick(tab)}
            className={cn(
              'flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1 text-sm transition-colors',
              activeKey === tab.key
                ? 'bg-brand-soft font-medium text-brand-ink'
                : 'text-ink-soft hover:bg-surface-hover hover:text-ink'
            )}
          >
            <span className="max-w-[160px] truncate">{tab.label}</span>
            {tab.closable && (
              <span
                role="button"
                tabIndex={0}
                aria-label={`关闭 ${tab.label}`}
                onClick={(event) => {
                  event.stopPropagation()
                  onTabClose(tab.key)
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.stopPropagation()
                    onTabClose(tab.key)
                  }
                }}
                className="rounded p-0.5 hover:bg-line"
              >
                <X className="h-3 w-3" />
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="h-5 w-px shrink-0 bg-line" />

      <button
        type="button"
        onClick={() => scrollBy(200)}
        disabled={!canScrollRight}
        className={cn(
          'shrink-0 rounded-md p-1 transition-colors',
          canScrollRight
            ? 'text-ink-faint hover:bg-surface-hover hover:text-ink'
            : 'cursor-not-allowed text-ink-faint/50'
        )}
        title="向右滚动"
      >
        <ChevronsRight className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
