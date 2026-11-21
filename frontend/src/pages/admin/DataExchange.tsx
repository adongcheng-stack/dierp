import { useState } from 'react'
import { Button, Card, Select, Space, App as AntdApp, Upload } from 'antd'
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import api from '../../services/api'
import { PageHeader } from '../../components/layout/PageHeader'

const ENTITIES = [
  { value: 'customers', label: '客户' },
  { value: 'materials', label: '物料' },
  { value: 'suppliers', label: '供应商' },
  { value: 'sales-orders', label: '销售订单' },
  { value: 'production-orders', label: '生产订单' },
  { value: 'purchase-orders', label: '采购订单' },
]

/** 数据导入导出（仅 ADMIN）：JSON / CSV 导出 + JSON 批量导入（自然键幂等）。 */
const DataExchange: React.FC = () => {
  const { message: appMessage } = AntdApp.useApp()
  const [entity, setEntity] = useState('customers')
  const [busy, setBusy] = useState(false)

  const download = async (format: 'json' | 'csv') => {
    setBusy(true)
    try {
      const response = await api.get(`/admin/export/${entity}`, {
        params: { format },
        responseType: 'blob',
      })
      const blob = new Blob([response.data as any], {
        type: format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${entity}.${format}`
      anchor.click()
      URL.revokeObjectURL(url)
      appMessage.success(`已导出 ${entity}.${format}`)
    } catch (error: any) {
      appMessage.error(error?.userMessage ?? '导出失败')
    } finally {
      setBusy(false)
    }
  }

  const uploadProps: UploadProps = {
    accept: '.json,application/json',
    showUploadList: false,
    beforeUpload: async (file) => {
      setBusy(true)
      try {
        const text = await file.text()
        const parsed = JSON.parse(text)
        const rows = Array.isArray(parsed) ? parsed : parsed.items
        if (!Array.isArray(rows)) throw new Error('JSON 需为数组或含 items 数组')
        const response = await api.post(`/admin/import/${entity}`, { rows })
        appMessage.success(
          `导入完成：新增 ${response.data.created}，跳过 ${response.data.skipped}`,
        )
      } catch (error: any) {
        appMessage.error(error?.userMessage ?? error?.message ?? '导入失败')
      } finally {
        setBusy(false)
      }
      return false
    },
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="数据导入导出" description="主数据与单据的 JSON / CSV 导出，以及 JSON 幂等批量导入（仅管理员）" />
      <Card>
        <Space direction="vertical" className="w-full">
          <Space>
            <Select
              value={entity}
              onChange={setEntity}
              options={ENTITIES}
              className="w-48"
            />
            <Button icon={<DownloadOutlined />} loading={busy} onClick={() => void download('json')}>
              导出 JSON
            </Button>
            <Button icon={<DownloadOutlined />} loading={busy} onClick={() => void download('csv')}>
              导出 CSV
            </Button>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />} loading={busy}>导入 JSON</Button>
            </Upload>
          </Space>
          <p className="text-sm text-ink-soft">
            导入按自然键（如客户编码 / 物料编码）去重，仅创建新记录，不覆盖既有业务数据。
          </p>
        </Space>
      </Card>
    </div>
  )
}

export default DataExchange
