import { AlertOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { Tag } from 'antd'

export interface AlertItem {
  code: string
  name: string
  level: string
  metric: string
  message: string
  actual?: number
  threshold?: number
}

const COLOR: Record<string, string> = {
  INFO: 'blue',
  WARNING: 'orange',
  CRITICAL: 'red',
}
const LABEL: Record<string, string> = {
  INFO: '提示',
  WARNING: '预警',
  CRITICAL: '严重',
}

/** 本体规则驱动的预警列表：列线分隔，不用卡片墙。 */
export function AlertPanel({ alerts }: { alerts: AlertItem[] }) {
  if (!alerts.length) {
    return (
      <div className="flex items-center gap-2 border-t border-line py-4 text-md text-ink-soft">
        <CheckCircleOutlined className="text-status-success" aria-hidden="true" />
        各项指标均在正常区间
      </div>
    )
  }
  return (
    <div className="flex flex-col">
      {alerts.map((alert) => (
        <div key={alert.code} className="flex items-start gap-3 border-b border-line py-3 last:border-b-0">
          <AlertOutlined
            className={`mt-1 shrink-0 ${alert.level === 'CRITICAL' ? 'text-status-error' : 'text-status-warning'}`}
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex items-center gap-3">
              <span className="text-md font-medium text-ink">{alert.name}</span>
              <Tag color={COLOR[alert.level] ?? 'default'}>{LABEL[alert.level] ?? alert.level}</Tag>
            </div>
            <div className="text-sm text-ink-soft">{alert.message}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
