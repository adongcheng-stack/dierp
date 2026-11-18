import { useCallback, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent } from 'react'
import { Check, ChevronsRight } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * 滑块验证（拖动到最右侧完成验证）
 * ----------------------------------------------------------------
 * - 纯前端交互校验，用于登录前的防呆 / 人机确认，不做服务端校验。
 * - 受控点：`resetSignal` 变化时重置为未验证（登录失败后要求重新拖动）。
 * - 支持鼠标 / 触摸 / 键盘（← → 移动，Enter 确认）。
 */

const HANDLE_WIDTH = 42
const TRACK_PADDING = 4
const VERIFY_THRESHOLD = 2

interface SliderCaptchaProps {
  disabled?: boolean
  /** 数值变化即重置为未验证状态 */
  resetSignal?: number
  onVerified: () => void
  onReset?: () => void
  className?: string
}

export function SliderCaptcha({
  disabled = false,
  resetSignal = 0,
  onVerified,
  onReset,
  className,
}: SliderCaptchaProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const startXRef = useRef(0)
  const offsetRef = useRef(0)
  const [maxOffset, setMaxOffset] = useState(0)
  const [offset, setOffset] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [verified, setVerified] = useState(false)

  const syncOffset = useCallback((value: number) => {
    offsetRef.current = value
    setOffset(value)
  }, [])

  // 测量可拖拽距离（轨道宽度 - 内边距 - 滑块宽度）
  useEffect(() => {
    const el = trackRef.current
    if (!el) return
    const measure = () =>
      setMaxOffset(Math.max(0, el.clientWidth - HANDLE_WIDTH - TRACK_PADDING * 2))
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const reset = useCallback(() => {
    setVerified(false)
    setDragging(false)
    syncOffset(0)
  }, [syncOffset])

  // 外部要求重置
  useEffect(() => {
    reset()
  }, [resetSignal, reset])

  const complete = useCallback(() => {
    syncOffset(maxOffset)
    setVerified(true)
    onVerified()
  }, [maxOffset, onVerified, syncOffset])

  const handlePointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (disabled || verified) return
    event.preventDefault()
    startXRef.current = event.clientX - offsetRef.current
    setDragging(true)
  }

  useEffect(() => {
    if (!dragging) return
    const handleMove = (event: PointerEvent) => {
      const next = Math.min(Math.max(0, event.clientX - startXRef.current), maxOffset)
      syncOffset(next)
    }
    const handleUp = () => {
      setDragging(false)
      if (maxOffset > 0 && offsetRef.current >= maxOffset - VERIFY_THRESHOLD) {
        complete()
      } else {
        syncOffset(0)
        onReset?.()
      }
    }
    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleUp)
    window.addEventListener('pointercancel', handleUp)
    return () => {
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleUp)
      window.removeEventListener('pointercancel', handleUp)
    }
  }, [dragging, maxOffset, complete, onReset, syncOffset])

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (disabled || verified) return
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
      event.preventDefault()
      syncOffset(Math.min(maxOffset, offsetRef.current + 8))
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
      event.preventDefault()
      syncOffset(Math.max(0, offsetRef.current - 8))
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (maxOffset > 0 && offsetRef.current >= maxOffset - VERIFY_THRESHOLD) complete()
    }
  }

  const translate = verified ? maxOffset : offset
  const progressWidth = verified ? '100%' : `calc(${translate}px + ${HANDLE_WIDTH}px + ${TRACK_PADDING}px)`

  return (
    <div
      ref={trackRef}
      className={cn(
        'relative h-10 w-full overflow-hidden rounded-md border transition-colors',
        verified ? 'border-brand/50 bg-brand/10' : 'border-input bg-secondary/50',
        disabled && 'opacity-60',
        className,
      )}
    >
      {/* 已拖拽进度 */}
      <div
        className={cn(
          'absolute inset-y-0 left-0 rounded-md transition-[width] duration-150 ease-ui',
          verified ? 'bg-brand/15' : dragging ? 'bg-brand/15' : 'bg-brand/10',
        )}
        style={{ width: progressWidth }}
      />

      {/* 提示文字 */}
      <div
        className={cn(
          'pointer-events-none absolute inset-0 flex items-center justify-center gap-1.5 px-3 text-xs transition-colors',
          verified ? 'font-medium text-brand-ink' : 'text-ink-faint',
        )}
      >
        {verified ? (
          <>
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
            验证通过
          </>
        ) : (
          <span className="truncate">
            {dragging ? '松开滑块完成验证' : '按住滑块，拖动到最右侧完成验证'}
          </span>
        )}
      </div>

      {/* 滑块 */}
      <button
        type="button"
        role="slider"
        aria-label="安全验证滑块"
        aria-valuemin={0}
        aria-valuemax={maxOffset}
        aria-valuenow={translate}
        aria-disabled={disabled || verified}
        tabIndex={verified ? -1 : 0}
        disabled={disabled || verified}
        onPointerDown={handlePointerDown}
        onKeyDown={handleKeyDown}
        style={{
          width: HANDLE_WIDTH,
          top: TRACK_PADDING,
          transform: `translateX(${translate}px)`,
          transition: dragging ? 'none' : 'transform 180ms cubic-bezier(0.22, 1, 0.36, 1)',
          left: TRACK_PADDING,
        }}
        className={cn(
          'absolute flex h-8 items-center justify-center rounded-md border shadow-card',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
          dragging ? 'cursor-grabbing' : 'cursor-grab',
          verified
            ? 'border-brand bg-brand text-white'
            : 'border-line-strong bg-card text-ink-soft hover:border-brand hover:text-brand',
          (disabled || verified) && 'cursor-default',
        )}
      >
        {verified ? (
          <Check className="h-4 w-4" aria-hidden="true" />
        ) : (
          <ChevronsRight className="h-4 w-4" aria-hidden="true" />
        )}
      </button>
    </div>
  )
}

export default SliderCaptcha
