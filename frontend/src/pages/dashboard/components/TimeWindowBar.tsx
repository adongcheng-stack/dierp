import { Select } from 'antd'

export const WINDOW_OPTIONS = [
  { value: 'ALL', label: '全部数据' },
  { value: 'LAST30', label: '近 30 天' },
  { value: 'LAST90', label: '近 90 天' },
  { value: 'LAST365', label: '近 1 年' },
]

interface Props {
  value: string
  onChange: (value: string) => void
  loading?: boolean
}

/** 驾驶舱通用时间窗口筛选（口径与本体 TimeWindow 枚举一致）。 */
export function TimeWindowBar({ value, onChange, loading }: Props) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-ink-soft">时间范围</span>
      <Select
        value={value}
        onChange={onChange}
        options={WINDOW_OPTIONS}
        className="w-32"
        loading={loading}
      />
    </div>
  )
}
