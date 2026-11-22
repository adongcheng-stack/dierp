import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Col, Input, Row, Select, Space, Statistic, Table, Tag, message } from 'antd'
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { fmtDate, fmtQty, KIT_STATUS, StatusTag } from './shared'

const SOURCE_TYPE: Record<string, { color: string; text: string }> = {
  PRODUCTION_ORDER: { color: 'geekblue', text: '生产订单' },
  PLANNED_ORDER: { color: 'purple', text: '计划订单' },
}

const KittingList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [sourceType, setSourceType] = useState<string | undefined>()
  const [kitStatus, setKitStatus] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [recomputing, setRecomputing] = useState<string | null>(null)

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/kitting', {
        params: {
          source_type: sourceType,
          kit_status: kitStatus,
          limit: 300,
        },
      })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取齐套分析结果失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRows()
  }, [sourceType, kitStatus])

  const filteredRows = useMemo(() => {
    const text = keyword.trim().toLowerCase()
    if (!text) return rows
    return rows.filter((row) =>
      [row.result_number, row.source_ref, row.material_code, row.remarks]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(text))
    )
  }, [rows, keyword])

  const summary = useMemo(() => {
    const total = rows.length
    const full = rows.filter((row) => row.kit_status === 'FULL').length
    const partial = rows.filter((row) => row.kit_status === 'PARTIAL').length
    const short = rows.filter((row) => row.kit_status === 'SHORT').length
    return { total, full, partial, short }
  }, [rows])

  const recompute = async (record: any) => {
    const key = `${record.source_type}:${record.source_ref}`
    setRecomputing(key)
    try {
      const path =
        record.source_type === 'PLANNED_ORDER'
          ? `/planning/kitting/planned-orders/${record.source_ref}`
          : `/planning/kitting/production-orders/${record.source_ref}`
      await api.post(path)
      message.success(`${record.source_ref} 齐套分析已更新`)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '齐套分析失败')
    } finally {
      setRecomputing(null)
    }
  }

  const shortageColumns = [
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    { title: '物料名称', dataIndex: 'material_name', key: 'material_name', ellipsis: true },
    {
      title: '需求量',
      dataIndex: 'required_qty',
      key: 'required_qty',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: '可用量',
      dataIndex: 'available_qty',
      key: 'available_qty',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: '缺口',
      dataIndex: 'shortage_qty',
      key: 'shortage_qty',
      align: 'right' as const,
      width: 90,
      render: (value: number) => (
        <span style={{ color: value > 0 ? 'var(--color-error)' : undefined, fontWeight: value > 0 ? 600 : 400 }}>
          {fmtQty(value)}
        </span>
      ),
    },
    {
      title: '需求日期',
      dataIndex: 'needed_date',
      key: 'needed_date',
      width: 110,
      render: (value: string) => fmtDate(value),
    },
  ]

  const columns = [
    { title: '分析编号', dataIndex: 'result_number', key: 'result_number', width: 170 },
    {
      title: '来源类型',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 100,
      render: (value: string) => <StatusTag value={value} map={SOURCE_TYPE} />,
    },
    { title: '来源单据', dataIndex: 'source_ref', key: 'source_ref', width: 170 },
    { title: '成品物料', dataIndex: 'material_code', key: 'material_code', width: 150 },
    {
      title: '齐套状态',
      dataIndex: 'kit_status',
      key: 'kit_status',
      width: 110,
      render: (value: string) => <StatusTag value={value} map={KIT_STATUS} />,
    },
    {
      title: '需求数量',
      dataIndex: 'required_qty',
      key: 'required_qty',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: '可用数量',
      dataIndex: 'available_qty',
      key: 'available_qty',
      align: 'right' as const,
      width: 100,
      render: fmtQty,
    },
    {
      title: '缺口数量',
      dataIndex: 'shortage_qty',
      key: 'shortage_qty',
      align: 'right' as const,
      width: 100,
      render: (value: number) => (
        <span style={{ color: value > 0 ? 'var(--color-error)' : undefined }}>{fmtQty(value)}</span>
      ),
    },
    {
      title: '检查时间',
      dataIndex: 'checked_at',
      key: 'checked_at',
      width: 160,
      render: (value: string) => value?.replace('T', ' ').slice(0, 19) ?? '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 110,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Button
          type="link"
          icon={<SyncOutlined />}
          loading={recomputing === `${record.source_type}:${record.source_ref}`}
          onClick={() => recompute(record)}
        >
          重算
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="齐套分析"
        description="按生产订单 / 计划订单检查 BOM 组件齐套情况，输出缺口物料与最早齐套日期"
        actions={
          <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
            刷新
          </Button>
        }
      />

      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="分析单据" value={summary.total} suffix="单" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="齐套" value={summary.full} suffix="单" valueStyle={{ color: 'var(--color-success)' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="部分缺料" value={summary.partial} suffix="单" valueStyle={{ color: 'var(--color-warning)' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic title="缺料" value={summary.short} suffix="单" valueStyle={{ color: 'var(--color-error)' }} />
          </Card>
        </Col>
      </Row>

      <Space wrap className="mb-4">
        <Select
          allowClear
          style={{ width: 150 }}
          placeholder="来源类型"
          value={sourceType}
          onChange={setSourceType}
          options={[
            { value: 'PRODUCTION_ORDER', label: '生产订单' },
            { value: 'PLANNED_ORDER', label: '计划订单' },
          ]}
        />
        <Select
          allowClear
          style={{ width: 150 }}
          placeholder="齐套状态"
          value={kitStatus}
          onChange={setKitStatus}
          options={[
            { value: 'FULL', label: '齐套' },
            { value: 'PARTIAL', label: '部分缺料' },
            { value: 'SHORT', label: '缺料' },
          ]}
        />
        <Input.Search
          allowClear
          style={{ width: 260 }}
          placeholder="搜索单据号 / 物料"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
      </Space>

      <Table
        rowKey="result_number"
        columns={columns}
        dataSource={filteredRows}
        loading={loading}
        pagination={{ pageSize: 12, showSizeChanger: false }}
        scroll={{ x: 1300 }}
        expandable={{
          expandedRowRender: (record: any) => {
            const details = record.shortage_details ?? []
            return (
              <div>
                <div className="mb-2 flex items-center gap-2 text-sm">
                  <span className="text-ink-soft">缺料结论：</span>
                  <Tag color={KIT_STATUS[record.kit_status]?.color}>
                    {KIT_STATUS[record.kit_status]?.text ?? record.kit_status}
                  </Tag>
                  <span className="text-ink-soft">{record.remarks ?? '-'}</span>
                </div>
                {details.length > 0 ? (
                  <Table
                    size="small"
                    rowKey={(item: any) => `${item.material_code}-${item.needed_date}`}
                    columns={shortageColumns}
                    dataSource={details}
                    pagination={false}
                  />
                ) : (
                  <div className="rounded-md bg-status-success/10 px-3 py-2 text-sm text-status-success">
                    该单据 BOM 组件全部齐套，无需补料。
                  </div>
                )}
              </div>
            )
          },
        }}
      />
    </div>
  )
}

export default KittingList
