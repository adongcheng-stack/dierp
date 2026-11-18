import { useEffect, useState } from 'react'
import { Button, Input, Modal, Select, Space, Table, message } from 'antd'
import { ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import api, { getErrorMessage } from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { fmtMoney } from './shared'

const StandardCostList: React.FC = () => {
  const [rows, setRows] = useState<any[]>([])
  const [materials, setMaterials] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [rollupOpen, setRollupOpen] = useState(false)
  const [rolling, setRolling] = useState(false)
  const [deep, setDeep] = useState(true)
  const [selectCodes, setSelectCodes] = useState<string[]>([])

  const fetchRows = async () => {
    setLoading(true)
    try {
      const response = await api.get('/planning/cost/standard', { params: { limit: 300 } })
      setRows(response.data.items ?? [])
    } catch (error) {
      message.error(getErrorMessage(error) || '获取标准成本失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchMaterials = async () => {
    try {
      const response = await api.get('/mm/materials')
      const data = response.data
      const list = Array.isArray(data) ? data : data?.items ?? []
      setMaterials(list)
    } catch {
      setMaterials([])
    }
  }

  useEffect(() => {
    fetchRows()
    fetchMaterials()
  }, [])

  const filteredRows = rows.filter((row) => {
    const text = keyword.trim().toLowerCase()
    if (!text) return true
    return [row.material_code, row.cost_id, row.version].some((value) =>
      String(value ?? '').toLowerCase().includes(text)
    )
  })

  const materialOptions = materials.map((material) => ({
    value: material.material_code,
    label: `${material.material_code} · ${material.material_name ?? ''}`,
  }))

  const runRollup = async () => {
    const codes = selectCodes.length ? selectCodes : materials.map((m) => m.material_code)
    if (!codes.length) {
      message.warning('没有可选物料')
      return
    }
    setRolling(true)
    try {
      await api.post('/planning/cost/standard/rollup', {
        material_codes: codes,
        version: '1',
        roll_deep: deep,
      })
      message.success(`标准成本已滚动 ${codes.length} 个物料`)
      setRollupOpen(false)
      fetchRows()
    } catch (error) {
      message.error(getErrorMessage(error) || '滚动标准成本失败')
    } finally {
      setRolling(false)
    }
  }

  const columns = [
    { title: '成本编号', dataIndex: 'cost_id', key: 'cost_id', width: 150 },
    { title: '物料', dataIndex: 'material_code', key: 'material_code', width: 160 },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 70,
    },
    {
      title: '材料成本',
      dataIndex: 'material_cost',
      key: 'material_cost',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '人工成本',
      dataIndex: 'labor_cost',
      key: 'labor_cost',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '制造费用',
      dataIndex: 'overhead_cost',
      key: 'overhead_cost',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '标准总成本',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right' as const,
      width: 130,
      render: (value: number) => <b>{fmtMoney(value)}</b>,
    },
    {
      title: '单价',
      dataIndex: 'unit_cost',
      key: 'unit_cost',
      align: 'right' as const,
      width: 120,
      render: (value: number) => fmtMoney(value),
    },
    {
      title: '币种',
      dataIndex: 'currency',
      key: 'currency',
      width: 70,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
    },
    {
      title: '滚动时间',
      dataIndex: 'rolled_up_at',
      key: 'rolled_up_at',
      width: 160,
      render: (value: string) => value?.replace('T', ' ').slice(0, 19) ?? '-',
    },
  ]

  return (
    <div>
      <PageHeader
        title="标准成本"
        description="按 BOM 用量 × 物料单价 + 工艺费率滚动计算物料标准成本，作为计划与成本差异的基准"
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchRows} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => setRollupOpen(true)}>
              滚动标准成本
            </Button>
          </Space>
        }
      />

      <Space wrap className="mb-4">
        <Input.Search
          allowClear
          style={{ width: 280 }}
          placeholder="搜索物料 / 成本编号"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
      </Space>

      <Table
        rowKey="cost_id"
        columns={columns}
        dataSource={filteredRows}
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1300 }}
      />

      <Modal
        title="滚动标准成本"
        open={rollupOpen}
        onOk={runRollup}
        onCancel={() => setRollupOpen(false)}
        confirmLoading={rolling}
        okText="开始滚动"
        width={640}
        destroyOnClose
      >
        <p className="mb-2 text-sm text-ink-soft">
          选择物料进行标准成本滚动；留空则对全部物料滚动。选择「多层滚动」会先计算 BOM 子件成本再汇总父件。
        </p>
        <Select
          mode="multiple"
          style={{ width: '100%' }}
          placeholder="选择物料（留空=全部）"
          showSearch
          optionFilterProp="label"
          value={selectCodes}
          onChange={setSelectCodes}
          options={materialOptions}
          className="mb-3"
        />
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="cost-deep"
            checked={deep}
            onChange={(event) => setDeep(event.target.checked)}
          />
          <label htmlFor="cost-deep" className="text-sm">
            多层滚动（先子件后父件）
          </label>
        </div>
      </Modal>
    </div>
  )
}

export default StandardCostList