export interface GanttRow {
  production_order_number: string
  operation_name: string
  completion_rate: number
  planned_start_time: string | null
  planned_finish_time: string | null
  status: string
}

const COLORS: Record<string, string> = {
  COMPLETED: 'bg-status-success',
  IN_PROGRESS: 'bg-brand',
  DELAYED: 'bg-status-error',
  PENDING: 'bg-status-warning',
  CANCELLED: 'bg-surface-hover',
}
const LEGEND: Array<[string, string]> = [
  ['COMPLETED', '已完成'], ['IN_PROGRESS', '进行中'], ['DELAYED', '逾期'],
  ['PENDING', '待开始'], ['CANCELLED', '取消'],
]

const pad2 = (v: number) => String(v).padStart(2, '0')
const tickLabel = (t: number) => {
  const d = new Date(t)
  return `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

/** 轻量甘特图：按计划起止时间定位工序条，显示完成率填充、时间刻度与状态图例。 */
export function GanttChart({ rows }: { rows: GanttRow[] }) {
  if (!rows.length) {
    return <div className="flex h-40 items-center justify-center text-sm text-ink-soft">暂无工序进度数据</div>
  }
  const times = rows.flatMap((row) => [row.planned_start_time, row.planned_finish_time])
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value).getTime())
  const min = times.length ? Math.min(...times) : 0
  const max = times.length ? Math.max(...times) : min + 1
  const span = Math.max(max - min, 1)
  const ticks = Array.from({ length: 5 }, (_, i) => ({
    left: i * 25,
    label: tickLabel(min + (span * i) / 4),
  }))

  return (
    <div className="flex flex-col gap-2">
      {times.length > 0 && (
        <div className="flex items-center gap-3">
          <div className="w-48 shrink-0" />
          <div className="relative h-4 flex-1">
            {ticks.map((tick, index) => (
              <span
                key={tick.left}
                className={`absolute top-0 whitespace-nowrap text-xs tabular-nums text-ink-soft ${
                  index === 0 ? 'translate-x-0' : index === ticks.length - 1 ? '-translate-x-full' : '-translate-x-1/2'
                }`}
                style={{ left: `${tick.left}%` }}
              >
                {tick.label}
              </span>
            ))}
          </div>
          <div className="w-12 shrink-0" />
        </div>
      )}
      {rows.map((row, index) => {
        const start = row.planned_start_time ? new Date(row.planned_start_time).getTime() : min
        const end = row.planned_finish_time ? new Date(row.planned_finish_time).getTime() : max
        const left = ((start - min) / span) * 100
        const width = Math.max(((end - start) / span) * 100, 3)
        return (
          <div key={`${row.production_order_number}-${row.operation_name}-${index}`} className="flex items-center gap-3">
            <div className="w-48 shrink-0 truncate text-sm text-ink-soft" title={`${row.production_order_number}，${row.operation_name}`}>
              {row.production_order_number}，{row.operation_name}
            </div>
            <div className="relative h-5 flex-1 bg-surface-hover">
              <div
                className={`absolute inset-y-0 ${COLORS[row.status] ?? 'bg-surface-hover'}`}
                style={{ left: `${left}%`, width: `${width}%`, opacity: 0.85 }}
              >
                <div className="h-full bg-surface/40" style={{ transform: `scaleX(${Math.min(row.completion_rate, 1)})`, transformOrigin: 'left' }} />
              </div>
            </div>
            <div className="w-12 shrink-0 text-right text-sm tabular-nums text-ink-soft">
              {Math.round(row.completion_rate * 100)}%
            </div>
          </div>
        )
      })}
      <div className="mt-1 flex flex-wrap items-center gap-3 pl-0 text-xs text-ink-soft">
        {LEGEND.map(([key, label]) => (
          <span key={key} className="flex items-center gap-1">
            <i className={`inline-block h-2 w-2 ${COLORS[key]}`} />{label}
          </span>
        ))}
      </div>
    </div>
  )
}
