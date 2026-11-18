import { useEffect, useState } from 'react'
import { Button, Card, Col, Row, Space, Statistic, Table, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  INSPECTION_RESULT,
  INSPECTION_TYPE,
  NCR_SEVERITY,
  NCR_SOURCE,
  StatusTag,
  fmtDateTime,
} from './shared'

const QmsWorkbench: React.FC = () => {
  const [overview, setOverview] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await api.get('/qms/overview')
      setOverview(response.data)
    } catch (error) {
      message.error(getErrorMessage(error) || '获取质量管理概览失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const failColumns = [
    { title: '检验单号', dataIndex: 'inspection_number', key: 'inspection_number', width: 170 },
    {
      title: '环节',
      dataIndex: 'inspection_type',
      key: 'inspection_type',
      width: 110,
      render: (v: string) => <StatusTag value={v} map={INSPECTION_TYPE} />,
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    { title: '不合格', dataIndex: 'quantity_rejected', key: 'quantity_rejected', width: 90, align: 'right' as const },
    { title: '检验时间', dataIndex: 'inspected_at', key: 'inspected_at', width: 150, render: fmtDateTime },
    {
      title: '结论',
      dataIndex: 'result',
      key: 'result',
      width: 90,
      render: (v: string) => <StatusTag value={v} map={INSPECTION_RESULT} />,
    },
  ]

  const ncrColumns = [
    { title: 'NCR编号', dataIndex: 'ncr_number', key: 'ncr_number', width: 170 },
    {
      title: '来源',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 90,
      render: (v: string) => <StatusTag value={v} map={NCR_SOURCE} />,
    },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 80, align: 'right' as const },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (v: string) => <StatusTag value={v} map={NCR_SEVERITY} />,
    },
    { title: 'EAM故障', dataIndex: 'failure_number', key: 'failure_number', width: 150, render: (v: string) => v || '-' },
    { title: '缺陷描述', dataIndex: 'defect_desc', key: 'defect_desc', ellipsis: true },
  ]

  return (
    <div>
      <PageHeader
        title="质量管理"
        description="来料 / 过程 / 终检三环节检验与不合格品（NCR）闭环，联动报工与设备故障"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        }
      />

      <Row gutter={[16, 16]} className="mb-4">
        <Col span={4}>
          <Card>
            <Statistic title="检验单" value={overview?.inspections ?? 0} suffix={`/ 完成 ${overview?.inspections_completed ?? 0}`} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="不合格检验" value={overview?.inspections_fail ?? 0} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="NCR总数" value={overview?.ncrs ?? 0} suffix={`/ 关闭 ${overview?.ncrs_closed ?? 0}`} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="待处理 NCR" value={overview?.ncrs_open ?? 0} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="设备原因 NCR" value={overview?.ncrs_equipment ?? 0} valueStyle={{ color: '#d46b08' }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="严重 NCR" value={overview?.ncrs_critical ?? 0} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-4">
        <Col span={4}>
          <Card>
            <Statistic title="来料检验" value={overview?.incoming ?? 0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="过程检验" value={overview?.in_process ?? 0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="终检" value={overview?.final ?? 0} />
          </Card>
        </Col>
      </Row>

      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card title="不合格检验单（最近）" size="small">
          <Table
            rowKey="inspection_number"
            columns={failColumns}
            dataSource={overview?.recent_fail_inspections ?? []}
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        </Card>
        <Card title="待处理不合格品记录（最近）" size="small">
          <Table
            rowKey="ncr_number"
            columns={ncrColumns}
            dataSource={overview?.open_ncr_items ?? []}
            pagination={false}
            size="small"
            scroll={{ x: 900 }}
          />
        </Card>
      </Space>
    </div>
  )
}

export default QmsWorkbench