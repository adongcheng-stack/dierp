import { useEffect, useState } from 'react'
import { Button, Card, Col, Descriptions, Empty, Row, Space, Statistic, Tag } from 'antd'
import {
  ArrowRightOutlined,
  CalendarOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { fmtQty, RUN_STATUS, StatusTag } from './shared'

interface Overview {
  latest_run: any | null
  mps_draft: number
  mps_released: number
  open_exceptions: number
  critical_exceptions: number
  short_kits: number
  planned_orders_open: number
  forecasts: number
  policies: number
}

const PlanningWorkbench: React.FC = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const fetchOverview = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/overview')
      setData(response.data)
    } catch (error) {
      console.error('获取计划概览失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOverview()
  }, [])

  const run = data?.latest_run

  return (
    <div>
      <PageHeader
        title="计划工作台"
        description="从主生产计划到物料需求、计划订单与齐套检查的一体化控制台"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchOverview} loading={loading}>
              刷新
            </Button>
            <Button icon={<CalendarOutlined />} onClick={() => navigate('/pp/mps')}>
              主生产计划
            </Button>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => navigate('/pp/mrp')}>
              运行 MRP
            </Button>
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={12} md={8} xl={4}>
          <Card loading={loading}>
            <Statistic title="MPS 草案" value={data?.mps_draft ?? 0} suffix="份" />
          </Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card loading={loading}>
            <Statistic title="已下达 MPS" value={data?.mps_released ?? 0} suffix="份" />
          </Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card loading={loading}>
            <Statistic
              title="待处理计划订单"
              value={data?.planned_orders_open ?? 0}
              suffix="张"
              valueStyle={{ color: '#1d4ed8' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card loading={loading}>
            <Statistic
              title="未处理异常"
              value={data?.open_exceptions ?? 0}
              suffix="条"
              valueStyle={{ color: data?.critical_exceptions ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card loading={loading}>
            <Statistic
              title="缺料/部分齐套"
              value={data?.short_kits ?? 0}
              suffix="单"
              valueStyle={{ color: data?.short_kits ? '#d46b08' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card loading={loading}>
            <Statistic title="生效计划参数" value={data?.policies ?? 0} suffix="条" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mt-4">
        <Col xs={24} xl={16}>
          <Card
            title="最近一次 MRP 运算"
            extra={
              run ? (
                <Button type="link" onClick={() => navigate('/pp/mrp')}>
                  查看运行记录 <ArrowRightOutlined />
                </Button>
              ) : null
            }
            loading={loading}
          >
            {run ? (
              <>
                <Descriptions column={{ xs: 1, md: 2, xl: 3 }} size="small">
                  <Descriptions.Item label="批次号">{run.run_number}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <StatusTag value={run.status} map={RUN_STATUS} />
                  </Descriptions.Item>
                  <Descriptions.Item label="运算方式">{run.run_type}</Descriptions.Item>
                  <Descriptions.Item label="需求来源">{run.demand_source}</Descriptions.Item>
                  <Descriptions.Item label="关联 MPS">{run.mps_number ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="执行人">{run.run_by ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="计划区间" span={2}>
                    {run.horizon_start?.slice(0, 10)} ~ {run.horizon_end?.slice(0, 10)}
                  </Descriptions.Item>
                  <Descriptions.Item label="完成时间">
                    {run.finished_at?.replace('T', ' ').slice(0, 19) ?? '-'}
                  </Descriptions.Item>
                </Descriptions>
                <Row gutter={[16, 16]} className="mt-3">
                  <Col span={6}>
                    <Statistic title="需求行" value={run.total_requirements} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="计划生产" value={run.planned_production_count} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="计划采购" value={run.planned_purchase_count} />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="异常"
                      value={run.exception_count}
                      valueStyle={{ color: run.exception_count ? '#cf1322' : undefined }}
                    />
                  </Col>
                </Row>
                <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-sm text-ink-soft">
                  {run.log_text}
                </div>
              </>
            ) : (
              <Empty description="还没有 MRP 运算记录">
                <Button type="primary" onClick={() => navigate('/pp/mrp')}>
                  去运行 MRP
                </Button>
              </Empty>
            )}
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card title="计划闭环" loading={loading}>
            <div className="space-y-3 text-sm">
              <button
                className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left hover:border-blue-400"
                onClick={() => navigate('/pp/mps')}
              >
                <span>1. 主生产计划（MPS）</span>
                <Space>
                  <Tag color={data?.mps_released ? 'green' : 'default'}>
                    {data?.mps_released ? '已下达' : '待生成'}
                  </Tag>
                  <ArrowRightOutlined />
                </Space>
              </button>
              <button
                className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left hover:border-blue-400"
                onClick={() => navigate('/pp/mrp')}
              >
                <span>2. 物料需求运算（MRP）</span>
                <Space>
                  <Tag color={run?.status === 'COMPLETED' ? 'green' : 'default'}>
                    {run?.status === 'COMPLETED' ? '已完成' : '待运行'}
                  </Tag>
                  <ArrowRightOutlined />
                </Space>
              </button>
              <button
                className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left hover:border-blue-400"
                onClick={() => navigate('/pp/planned-orders')}
              >
                <span>3. 计划订单确认 / 下达</span>
                <Space>
                  <Tag color={data?.planned_orders_open ? 'blue' : 'default'}>
                    {data?.planned_orders_open ?? 0} 张
                  </Tag>
                  <ArrowRightOutlined />
                </Space>
              </button>
              <button
                className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left hover:border-blue-400"
                onClick={() => navigate('/pp/planning-exceptions')}
              >
                <span>4. 计划异常处理</span>
                <Space>
                  <Tag color={data?.critical_exceptions ? 'red' : 'default'}>
                    {data?.open_exceptions ?? 0} 条
                  </Tag>
                  <ArrowRightOutlined />
                </Space>
              </button>
              <button
                className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left hover:border-blue-400"
                onClick={() => navigate('/pp/kitting')}
              >
                <span>5. 齐套分析与缺料清单</span>
                <Space>
                  <Tag color={data?.short_kits ? 'orange' : 'green'}>
                    {data?.short_kits ?? 0} 单缺料
                  </Tag>
                  <ArrowRightOutlined />
                </Space>
              </button>
            </div>
            <div className="mt-4 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
              <WarningOutlined className="mt-0.5" />
              <span>
                当前演示库有 {fmtQty(data?.forecasts ?? 0)} 条预测参与 MPS 计算；计划参数可在
                「计划参数」页维护。
              </span>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default PlanningWorkbench
