import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Modal, Row, Select, Space, Statistic, Tag, message } from 'antd'
import { CheckCircleOutlined, ReloadOutlined, LockOutlined, UnlockOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface Period {
  period_code: string
  start_date: string | null
  end_date: string | null
  status: string
}

interface Preview {
  period_code: string
  total_debit: number
  total_credit: number
  balanced: boolean
  revenue: number
  expense: number
  cost_5001: number
  cost_6401: number
  variance: number
  entry_count: number
  period_status: string
}

const money = (v: number | undefined | null) => (v ?? 0).toFixed(2)

const PeriodClose: React.FC = () => {
  const [periods, setPeriods] = useState<Period[]>([])
  const [selected, setSelected] = useState<string | undefined>()
  const [preview, setPreview] = useState<Preview | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)

  const fetchPeriods = async () => {
    setLoading(true)
    try {
      const response = await api.get('/finance/periods')
      const rows: Period[] = response.data.items || []
      setPeriods(rows)
      if (!selected && rows.length) setSelected(rows[0].period_code)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载会计期间失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchPreview = async (code?: string) => {
    if (!code) return
    try {
      const response = await api.get('/finance/month-end/preview', { params: { period_code: code } })
      setPreview(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '加载月结预览失败')
    }
  }

  useEffect(() => {
    fetchPeriods()
  }, [])

  useEffect(() => {
    fetchPreview(selected)
  }, [selected])

  const doAction = (action: 'close' | 'reopen') => {
    if (!selected) return
    Modal.confirm({
      title: action === 'close' ? `确认月结 ${selected}？` : `确认反结账 ${selected}？`,
      content:
        action === 'close'
          ? '月结将校验试算平衡并自动生成损益结转凭证，期间置为 CLOSED，之后禁止新分录过账。'
          : '反结账将期间恢复为 OPEN，不会删除已过账凭证。',
      okText: action === 'close' ? '确认月结' : '确认反结账',
      cancelText: '取消',
      onOk: async () => {
        setBusy(true)
        try {
          await api.post(`/finance/periods/${selected}/${action}`)
          message.success(action === 'close' ? '月结完成' : '反结账完成')
          await fetchPeriods()
          await fetchPreview(selected)
        } catch (error) {
          message.error(getErrorMessage(error) || '操作失败')
        } finally {
          setBusy(false)
        }
      },
    })
  }

  const isClosed = preview?.period_status === 'CLOSED'

  return (
    <div>
      <PageHeader
        title="期间与月结"
        description="试算平衡门禁 → 损益结转（收入成本匹配）→ 期间 CLOSE；反结账保留已过账凭证"
        actions={
          <Space>
            <Select
              style={{ width: 130 }}
              value={selected}
              onChange={setSelected}
              options={periods.map((p) => ({
                value: p.period_code,
                label: `${p.period_code}（${p.status === 'CLOSED' ? '已结账' : '开放'}）`,
              }))}
            />
            <Button icon={<ReloadOutlined />} onClick={() => { fetchPeriods(); fetchPreview(selected) }} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      />

      {preview && !preview.balanced && (
        <Alert
          type="error"
          showIcon
          message={`试算不平衡：借 ${money(preview.total_debit)} ≠ 贷 ${money(preview.total_credit)}，禁止月结`}
          style={{ marginBottom: 12 }}
        />
      )}

      <Row gutter={[16, 16]} className="mb-4">
        <Col span={6}>
          <Card>
            <Statistic
              title="期间状态"
              value={isClosed ? '已结账 (CLOSED)' : '开放 (OPEN)'}
              prefix={isClosed ? <LockOutlined /> : <UnlockOutlined />}
              valueStyle={{ color: isClosed ? 'var(--color-error)' : 'var(--color-success)', fontSize: 20 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="借方发生" value={money(preview?.total_debit)} precision={2} prefix="¥" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="贷方发生" value={money(preview?.total_credit)} precision={2} prefix="¥" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="试算平衡"
              value={preview?.balanced ? 'Σ借 = Σ贷 ✓' : 'Σ借 ≠ Σ贷'}
              valueStyle={{ color: preview?.balanced ? 'var(--color-success)' : 'var(--color-error)', fontSize: 20 }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={`${selected ?? '-'} 月结预览`}
        extra={
          <Space>
            {!isClosed && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                loading={busy}
                disabled={!preview?.balanced}
                onClick={() => doAction('close')}
              >
                月结
              </Button>
            )}
            {isClosed && (
              <Button icon={<UnlockOutlined />} loading={busy} onClick={() => doAction('reopen')}>
                反结账
              </Button>
            )}
          </Space>
        }
      >
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="凭证行数">{preview?.entry_count ?? 0}</Descriptions.Item>
          <Descriptions.Item label="收入（6001）">¥{money(preview?.revenue)}</Descriptions.Item>
          <Descriptions.Item label="生产成本（5001）">¥{money(preview?.cost_5001)}</Descriptions.Item>
          <Descriptions.Item label="主营业务成本（6401）">¥{money(preview?.cost_6401)}</Descriptions.Item>
          <Descriptions.Item label="成本费用合计">¥{money(preview?.expense)}</Descriptions.Item>
          <Descriptions.Item label="损益差额（收入−成本）">
            <Tag color={(preview?.variance ?? 0) >= 0 ? 'green' : 'red'}>¥{money(preview?.variance)}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

export default PeriodClose
