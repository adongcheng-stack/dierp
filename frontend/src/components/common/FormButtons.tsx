import { Button, Space } from 'antd'
import { useNavigate } from 'react-router-dom'

interface FormButtonsProps {
  loading?: boolean
  onSave?: () => void
  onCancel?: () => void
  saveText?: string
  cancelText?: string
  showCancel?: boolean
  cancelPath?: string // 取消时跳转的路径
}

const FormButtons: React.FC<FormButtonsProps> = ({
  loading = false,
  onSave,
  onCancel,
  saveText = '保存',
  cancelText = '取消',
  showCancel = true,
  cancelPath
}) => {
  const navigate = useNavigate()

  const handleCancel = () => {
    if (onCancel) {
      onCancel()
    } else if (cancelPath) {
      navigate(cancelPath)
    } else {
      navigate(-1) // 返回上一页
    }
  }

  return (
    <Space>
      <Button type="primary" loading={loading} onClick={onSave}>
        {saveText}
      </Button>
      {showCancel && (
        <Button onClick={handleCancel}>
          {cancelText}
        </Button>
      )}
    </Space>
  )
}

export default FormButtons

