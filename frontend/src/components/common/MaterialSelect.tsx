import { Select, SelectProps } from 'antd'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select

interface MaterialSelectProps extends Omit<SelectProps, 'options'> {
  value?: string
  onChange?: (value: string) => void
  materialType?: string // 物料类型过滤
  showActiveOnly?: boolean // 只显示激活的物料
  excludeCodes?: string[] // 排除的物料编码列表（如父物料）
}

const MaterialSelect: React.FC<MaterialSelectProps> = ({
  value,
  onChange,
  materialType,
  showActiveOnly = true,
  excludeCodes = [],
  ...rest
}) => {
  const [materials, setMaterials] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchMaterials()
  }, [materialType, excludeCodes])

  const fetchMaterials = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (showActiveOnly) {
        params.status = 'ACTIVE'
      }
      if (materialType) {
        params.material_type = materialType
      }
      
      const response = await api.get('/mm/materials', { params })
      let filteredMaterials = response.data || []
      
      // 排除指定的物料编码
      if (excludeCodes && excludeCodes.length > 0) {
        filteredMaterials = filteredMaterials.filter(
          (material: any) => !excludeCodes.includes(material.material_code)
        )
      }
      
      setMaterials(filteredMaterials)
    } catch (error) {
      console.error('获取物料列表失败:', error)
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
      placeholder="请选择物料"
      {...rest}
    >
      {materials.map((material) => (
        <Option key={material.material_code} value={material.material_code}>
          {material.material_code} - {material.material_name}
        </Option>
      ))}
    </Select>
  )
}

export default MaterialSelect

