import { useEffect, useState } from 'react'
import { Button, Card, Col, Row, Space, Statistic } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

interface Overview {
  standard_costs: number
  production_costs: number
  open_costs: number
  settled_costs: number
  variances: number
  adverse_variances: number
  settlements: number
  rates: number
  cost_centers: number
}

const CostWorkbench: React.FC = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchOverview = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/cost/overview')
      setData(response.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOverview()
  }, [])

  return (
    <div>
      <PageHeader
        title="成本工作台"
        description="标准成本、工单实际成本、差异分析与结算的一体化成本控制台"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchOverview} loading={loading}>
            刷新
          </Button>
        }
      />

      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="标准成本版本" value={data?.standard_costs ?? 0} suffix="个" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="工单成本" value={data?.production_costs ?? 0} suffix="单" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="待归集/在归集" value={data?.open_costs ?? 0} suffix="单" valueStyle={{ color: '#d46b08' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="已结算" value={data?.settled_costs ?? 0} suffix="单" valueStyle={{ color: '#389e0d' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="差异明细" value={data?.variances ?? 0} suffix="条" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="超支差异" value={data?.adverse_variances ?? 0} suffix="条" valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="结算单据" value={data?.settlements ?? 0} suffix="张" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="成本费率 / 成本中心" value={data?.rates ?? 0} suffix={` / ${data?.cost_centers ?? 0}`} />
          </Card>
        </Col>
      </Row>

      <Card size="small">
        <Space wrap size={[8, 8]}>
          <span className="text-sm font-medium text-ink">成本闭环：</span>
          <span className="text-sm text-ink-soft">标准成本滚动（BOM × 单价 + 工艺费率）</span>
          <span>→</span>
          <span className="text-sm text-ink-soft">工单实际归集（领料 + 报工 × 费率）</span>
          <span>→</span>
          <span className="text-sm text-ink-soft">差异分析（价格 / 用量 / 人工 / 费用）</span>
          <span>→</span>
          <span className="text-sm text-ink-soft">结算入账</span>
        </Space>
      </Card>
    </div>
  )
}

export default CostWorkbench