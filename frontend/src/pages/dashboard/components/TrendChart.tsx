import { useState } from 'react'

interface Point { label: string; value: number }

const format = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))

/** 轻量 SVG 趋势图（不引入图表库，保持离线包体积与构建稳定）。
 *  提供 Y 轴刻度/网格、hover 读数与可选目标线。 */
export function TrendChart({ data, height = 160, color = 'var(--color-accent)', target }: {
  data: Point[]; height?: number; color?: string; target?: number
}) {
  const [hover, setHover] = useState<number | null>(null)
  if (!data.length) {
    return <div className="flex h-40 items-center justify-center text-xs text-ink-faint">暂无趋势数据</div>
  }
  const width = 640
  const pad = { left: 44, right: 12, top: 12, bottom: 26 }
  const plotW = width - pad.left - pad.right
  const plotH = height - pad.top - pad.bottom
  const max = Math.max(...data.map((d) => d.value), target ?? 0, 1)
  const stepX = plotW / Math.max(data.length - 1, 1)
  const yPos = (v: number) => pad.top + (1 - v / max) * plotH
  const points = data.map((d, i) => ({ x: pad.left + i * stepX, y: yPos(d.value) }))
  const polyline = points.map((p) => `${p.x},${p.y}`).join(' ')
  const area = `${pad.left},${height - pad.bottom} ${polyline} ${points[points.length - 1].x},${height - pad.bottom}`
  const ticks = 4

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none" role="img" aria-label="趋势图">
      {/* Y 轴刻度与网格线 */}
      {Array.from({ length: ticks + 1 }, (_, i) => {
        const value = (max * (ticks - i)) / ticks
        const y = pad.top + (i * plotH) / ticks
        return (
          <g key={`y-${i}`}>
            <line x1={pad.left} y1={y} x2={width - pad.right} y2={y}
              stroke="currentColor" strokeOpacity={0.08} />
            <text x={pad.left - 6} y={y + 3} textAnchor="end" fontSize={10}
              className="fill-current opacity-50">{format(value)}</text>
          </g>
        )
      })}
      <polygon points={area} fill={color} fillOpacity={0.12} />
      <polyline points={polyline} fill="none" stroke={color} strokeWidth={2} />
      {/* 目标线 */}
      {target != null && target > 0 && (
        <g>
          <line x1={pad.left} y1={yPos(target)} x2={width - pad.right} y2={yPos(target)}
            stroke="var(--color-warning)" strokeWidth={1.5} strokeDasharray="5 3" strokeOpacity={0.9} />
          <text x={width - pad.right} y={yPos(target) - 5} textAnchor="end" fontSize={10} fill="var(--color-warning)">
            目标 {format(target)}
          </text>
        </g>
      )}
      {points.map((p, i) => (
        <g key={data[i].label}>
          <circle cx={p.x} cy={p.y} r={hover === i ? 4.5 : 3} fill={color} />
          <text x={p.x} y={height - 8} textAnchor="middle" fontSize={10} className="fill-current opacity-60">
            {data[i].label}
          </text>
          <rect x={p.x - stepX / 2} y={pad.top} width={Math.max(stepX, 1)} height={plotH}
            fill="transparent" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} />
          {hover === i && (
            <g>
              <line x1={p.x} y1={pad.top} x2={p.x} y2={height - pad.bottom}
                stroke="currentColor" strokeOpacity={0.3} strokeDasharray="3 3" />
              <rect x={Math.min(Math.max(p.x - 46, pad.left), width - pad.right - 92)}
                y={Math.max(p.y - 36, 2)} width={92} height={22} rx={3} fill="var(--color-ink)" fillOpacity={0.94} />
              <text x={Math.min(Math.max(p.x, pad.left + 46), width - pad.right - 46)}
                y={Math.max(p.y - 21, 17)} textAnchor="middle" fontSize={10} fill="var(--color-paper)">
                {data[i].label}: {format(data[i].value)}
              </text>
            </g>
          )}
        </g>
      ))}
    </svg>
  )
}
