import { Select, SelectProps } from 'antd'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select

interface CustomerSelectProps extends Omit<SelectProps, 'options'> {
  value?: string
  onChange?: (value: string) => void
  showActiveOnly?: boolean // 只显示激活的客户
}

const CustomerSelect: React.FC<CustomerSelectProps> = ({
  value,
  onChange,
  showActiveOnly = true,
  ...rest
}) => {
  const [customers, setCustomers] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchCustomers()
  }, [])

  const fetchCustomers = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (showActiveOnly) {
        params.status = 'ACTIVE'
      }
      
      const response = await api.get('/sd/customers', { params })
      setCustomers(response.data || [])
    } catch (error) {
      console.error('获取客户列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Select
      value={value}
      onChange={onChange}
      loading={loading}
      showSearch
      filterOption={(input, option) =>
        (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
      }
      placeholder="请选择客户"
      {...rest}
    >
      {customers.map((customer) => (
        <Option key={customer.customer_id} value={customer.customer_id}>
          {customer.customer_id} - {customer.legal_name || customer.trade_name}
        </Option>
      ))}
    </Select>
  )
}

export default CustomerSelect

