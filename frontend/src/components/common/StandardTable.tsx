import { Table, TableProps, Button, Space } from 'antd'
import { useState, useEffect } from 'react'
import api from '../../services/api'

interface StandardTableProps<T = any> extends Omit<TableProps<T>, 'dataSource' | 'loading'> {
  apiEndpoint: string // API端点
  apiParams?: Record<string, any> // API参数
  columns: TableProps<T>['columns']
  rowKey?: string | ((record: T) => string)
  onRefresh?: () => void
  showActions?: boolean
  actionButtons?: React.ReactNode
}

const StandardTable = <T extends Record<string, any>>({
  apiEndpoint,
  apiParams = {},
  columns,
  rowKey = 'id',
  onRefresh,
  showActions = true,
  actionButtons,
  ...rest
}: StandardTableProps<T>) => {
  const [data, setData] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  })

  const fetchData = async (page = 1, pageSize = 10) => {
    setLoading(true)
    try {
      const params = {
        ...apiParams,
        skip: (page - 1) * pageSize,
        limit: pageSize
      }
      
      const response = await api.get(apiEndpoint, { params })
      setData(response.data || [])
      
      // 如果API返回了总数，更新分页
      if (response.headers['x-total-count']) {
        setPagination(prev => ({
          ...prev,
          total: parseInt(response.headers['x-total-count'])
        }))
      }
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(pagination.current, pagination.pageSize)
  }, [apiEndpoint, JSON.stringify(apiParams), pagination.current, pagination.pageSize])

  const handleTableChange = (newPagination: any) => {
    setPagination(prev => ({
      ...prev,
      current: newPagination.current,
      pageSize: newPagination.pageSize
    }))
  }

  const handleRefresh = () => {
    fetchData(pagination.current, pagination.pageSize)
    if (onRefresh) {
      onRefresh()
    }
  }

  return (
    <div>
      {showActions && (
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button onClick={handleRefresh}>刷新</Button>
            {actionButtons}
          </Space>
        </div>
      )}
      <Table<T>
        dataSource={data}
        columns={columns}
        rowKey={rowKey}
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`
        }}
        onChange={handleTableChange}
        {...rest}
      />
    </div>
  )
}

export default StandardTable

