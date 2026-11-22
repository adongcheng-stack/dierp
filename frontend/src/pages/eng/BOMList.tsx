import { Table, Button, Tag, Select, Space } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'
import { ErrorState, SkeletonRows } from '../../components/common/DataStates'

const BOM_STATUS: { [key: string]: { color: string; text: string } } = {
  NEW: { color: 'default', text: '新建' },
  REVIEWING: { color: 'orange', text: '审阅中' },
  RELEASED: { color: 'green', text: '已发布' },
  PRODUCING: { color: 'blue', text: '生产中' },
  OBSOLETE: { color: 'default', text: '已失效' }
}

const BOMList: React.FC = () => {
  const [boms, setBoms] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const statusFilter = searchParams.get('status') ?? ''
  const navigate = useNavigate()

  useEffect(() => {
    fetchBOMs()
  }, [statusFilter])

  const fetchBOMs = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/eng/boms', { params: statusFilter ? { status: statusFilter } : {} })
      setBoms(response.data)
    } catch (err) {
      console.error('获取BOM列表失败:', err)
      setError('获取BOM列表失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: 'BOM编号', dataIndex: 'bom_number', key: 'bom_number', fixed: 'left' as const },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '父项物料', dataIndex: 'parent_material_code', key: 'parent_material_code' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const info = BOM_STATUS[status] || { color: 'default', text: status }
        return <Tag color={info.color}>{info.text}</Tag>
      }
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => navigate(`/eng/boms/${record.bom_number}/edit`)}
        >
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="BOM管理"
        description="维护产品物料清单，作为生产版本与领料核算的依据"
        actions={
          <Space wrap>
            <Select
              value={statusFilter || undefined}
              placeholder="状态"
              allowClear
              options={Object.entries(BOM_STATUS).map(([value, info]) => ({ value, label: info.text }))}
              onChange={(value) => {
                const next = new URLSearchParams(searchParams)
                if (value) next.set('status', value)
                else next.delete('status')
                setSearchParams(next)
              }}
              className="w-40"
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/eng/boms/new')}
            >
              新建BOM
            </Button>
          </Space>
        }
      />
      {error && !boms.length ? (
        <ErrorState text={error} onRetry={() => void fetchBOMs()} />
      ) : loading && !boms.length ? (
        <SkeletonRows rows={4} />
      ) : (
        <div className="table-scroll">
          <Table
            columns={columns}
            dataSource={boms}
            loading={loading}
            rowKey="id"
            scroll={{ x: 760 }}
          />
        </div>
      )}
    </div>
  )
}

export default BOMList
