import { Table, Button, Card, Space, Tag, App as AntdApp, Input, Select } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'
import { PlusOutlined, EyeOutlined, EditOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { Option } = Select
const { Search } = Input

const MIList: React.FC = () => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [mis, setMIs] = useState<any[]>([])
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    fetchMIs()
  }, [statusFilter])

  const fetchMIs = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (statusFilter) {
        params.status = statusFilter
      }
      const response = await api.get('/eng/mis', { params })
      setMIs(response.data || [])
    } catch (error) {
      message.error('获取MI列表失败')
    } finally {
      setLoading(false)
    }
  }

  const getStatusTag = (status: string) => {
    const statusMap: { [key: string]: { color: string; text: string } } = {
      'DRAFT': { color: 'default', text: '草稿' },
      'REVIEWING': { color: 'processing', text: '待审核' },
      'APPROVED': { color: 'success', text: '已批准' },
      'RELEASED': { color: 'success', text: '已发布' },
      'OBSOLETE': { color: 'error', text: '已作废' }
    }
    const statusInfo = statusMap[status] || { color: 'default', text: status }
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
  }

  const filteredMIs = mis.filter(mi => {
    if (searchText) {
      return mi.mi_number?.toLowerCase().includes(searchText.toLowerCase()) ||
             mi.material_code?.toLowerCase().includes(searchText.toLowerCase())
    }
    return true
  })

  const instructionColumns = [
    {
      title: '序号',
      dataIndex: 'sequence',
      key: 'sequence',
      width: 80,
      render: (seq: number) => <strong>{seq}</strong>
    },
    {
      title: '工序代码',
      dataIndex: 'operation_code',
      key: 'operation_code',
      width: 120
    },
    {
      title: '工序名称',
      dataIndex: 'operation_name',
      key: 'operation_name',
      width: 150
    },
    {
      title: '指令类型',
      dataIndex: 'instruction_type',
      key: 'instruction_type',
      width: 150
    },
    {
      title: '指令内容',
      dataIndex: 'instruction_content',
      key: 'instruction_content',
      ellipsis: true
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    }
  ]

  const columns = [
    {
      title: 'MI编号',
      dataIndex: 'mi_number',
      key: 'mi_number',
      width: 150,
      render: (text: string) => <strong>{text}</strong>
    },
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 150
    },
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      width: 100
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '生效日期',
      dataIndex: 'effective_date',
      key: 'effective_date',
      width: 180,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/eng/mis/${record.mi_number}/review`)}
          >
            查看
          </Button>
          {record.status === 'DRAFT' && (
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => navigate(`/eng/mis/${record.mi_number}/edit`)}
            >
              编辑
            </Button>
          )}
          {record.status === 'REVIEWING' && (
            <Button
              type="link"
              onClick={() => navigate(`/eng/mis/${record.mi_number}/review`)}
            >
              审核
            </Button>
          )}
        </Space>
      )
    }
  ]

  const expandedRowRender = (record: any) => {
    // 优先使用API返回的instructions数组
    const instructions = record.instructions && Array.isArray(record.instructions) 
      ? record.instructions 
      : []
    
    if (instructions.length === 0) {
      return (
        <div style={{ padding: '20px', textAlign: 'center', color: 'hsl(var(--ink-faint))' }}>
          暂无指令项
        </div>
      )
    }

    return (
      <Table
        columns={instructionColumns}
        dataSource={[...instructions].sort((a: any, b: any) => a.sequence - b.sequence)}
        rowKey={(record: any) => record.id || record.sequence}
        pagination={false}
        size="small"
        style={{ margin: '16px 0' }}
      />
    )
  }

  return (
    <div>
      <Card
        title="MI管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/eng/mis/new')}
          >
            新建MI
          </Button>
        }
      >
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Search
              placeholder="搜索MI编号、物料编码"
              allowClear
              style={{ width: 300 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="MI状态"
              allowClear
              style={{ width: 150 }}
              onChange={setStatusFilter}
            >
              <Option value="DRAFT">草稿</Option>
              <Option value="REVIEWING">待审核</Option>
              <Option value="APPROVED">已批准</Option>
              <Option value="RELEASED">已发布</Option>
              <Option value="OBSOLETE">已作废</Option>
            </Select>
          </Space>
        </Space>

        <Table
          columns={columns}
          dataSource={filteredMIs}
          rowKey="mi_number"
          loading={loading}
          scroll={{ x: 1200 }}
          expandable={{
            expandedRowRender,
            rowExpandable: () => true
          }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>
    </div>
  )
}

export default MIList

