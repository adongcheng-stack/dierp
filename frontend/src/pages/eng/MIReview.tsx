import { Card, Row, Col, Button, Space, App as AntdApp, Tag, Descriptions, Input, Divider, Table } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'
import dayjs from 'dayjs'

const { TextArea } = Input

interface MIReviewProps {
  miNumber?: string
}

const MIReview: React.FC<MIReviewProps> = ({ miNumber: propMiNumber }) => {
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [mi, setMi] = useState<any>(null)
  const [comment, setComment] = useState('')
  const [pendingMIs, setPendingMIs] = useState<any[]>([])
  const miNumber = propMiNumber || id

  useEffect(() => {
    if (miNumber) {
      fetchMI()
    }
    fetchPendingMIs()
  }, [miNumber])

  const fetchMI = async () => {
    try {
      const response = await api.get(`/eng/mis/${miNumber}`)
      setMi(response.data)
    } catch (error) {
      message.error('获取MI信息失败')
    }
  }

  const fetchPendingMIs = async () => {
    try {
      const response = await api.get('/eng/mis', {
        params: { status: 'REVIEWING' }
      })
      setPendingMIs(response.data || [])
    } catch (error) {
      console.error('获取待审核MI列表失败:', error)
    }
  }

  const handleApprove = async () => {
    if (!comment.trim()) {
      message.warning('请填写审核意见')
      return
    }
    
    setLoading(true)
    try {
      await api.post(`/eng/mis/${miNumber}/approve`, { comment })
      message.success('MI审核通过')
      setComment('')
      fetchMI()
      fetchPendingMIs()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '审核失败')
    } finally {
      setLoading(false)
    }
  }

  const handleReject = async () => {
    if (!comment.trim()) {
      message.warning('请填写驳回原因')
      return
    }
    
    setLoading(true)
    try {
      await api.post(`/eng/mis/${miNumber}/reject`, { comment })
      message.success('MI已驳回')
      setComment('')
      fetchMI()
      fetchPendingMIs()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '驳回失败')
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

  const parseContent = (contentStr?: string) => {
    if (!contentStr) return {}
    try {
      return JSON.parse(contentStr)
    } catch {
      return {}
    }
  }

  // 获取指令项列表（优先使用API返回的instructions数组）
  const getInstructions = (mi: any) => {
    if (mi?.instructions && Array.isArray(mi.instructions)) {
      return mi.instructions
    }
    // 兼容旧格式：从content JSON中解析
    const content = parseContent(mi?.content)
    return content.instructions || []
  }

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
      key: 'instruction_content'
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    }
  ]

  if (!mi && miNumber) {
    return <div>加载中...</div>
  }

  const content = parseContent(mi?.content)

  return (
    <div>
      <Row gutter={16}>
        <Col span={16}>
          <Card 
            title="MI详细信息"
            extra={mi && getStatusTag(mi.status)}
          >
            {mi && (
              <Descriptions column={2} bordered>
                <Descriptions.Item label="MI编号">{mi.mi_number}</Descriptions.Item>
                <Descriptions.Item label="版本号">{mi.version}</Descriptions.Item>
                <Descriptions.Item label="物料编码">{mi.material_code}</Descriptions.Item>
                <Descriptions.Item label="状态">{getStatusTag(mi.status)}</Descriptions.Item>
                <Descriptions.Item label="生效日期">
                  {mi.effective_date ? dayjs(mi.effective_date).format('YYYY-MM-DD HH:mm:ss') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="失效日期">
                  {mi.expiry_date ? dayjs(mi.expiry_date).format('YYYY-MM-DD HH:mm:ss') : '-'}
                </Descriptions.Item>
                {content.pcb_type && (
                  <Descriptions.Item label="PCB类型">
                    {content.pcb_type === 'rigid' ? '刚性板' : 
                     content.pcb_type === 'flex' ? '柔性板' :
                     content.pcb_type === 'rigid-flex' ? '刚柔结合板' :
                     content.pcb_type === 'aluminum' ? '铝基板' : content.pcb_type}
                  </Descriptions.Item>
                )}
                {content.layers && (
                  <Descriptions.Item label="层数">{content.layers}层</Descriptions.Item>
                )}
                {content.board_thickness && (
                  <Descriptions.Item label="板厚">{content.board_thickness} mm</Descriptions.Item>
                )}
                {content.copper_thickness && (
                  <Descriptions.Item label="铜厚">{content.copper_thickness} oz</Descriptions.Item>
                )}
                {content.surface_treatment && (
                  <Descriptions.Item label="表面处理">
                    {content.surface_treatment === 'hasl' ? '喷锡(HASL)' :
                     content.surface_treatment === 'enigma' ? '沉金(ENIG)' :
                     content.surface_treatment === 'osp' ? '有机保焊膜(OSP)' :
                     content.surface_treatment === 'immersion-silver' ? '沉银' : content.surface_treatment}
                  </Descriptions.Item>
                )}
                {content.solder_mask_color && (
                  <Descriptions.Item label="阻焊颜色">{content.solder_mask_color}</Descriptions.Item>
                )}
                {content.legend_color && (
                  <Descriptions.Item label="字符颜色">{content.legend_color}</Descriptions.Item>
                )}
                {content.delivery_size && (
                  <Descriptions.Item label="交货尺寸">{content.delivery_size} mm</Descriptions.Item>
                )}
                {content.panel_method && (
                  <Descriptions.Item label="拼板方式">{content.panel_method}</Descriptions.Item>
                )}
                {content.test_requirement && (
                  <Descriptions.Item label="测试要求">
                    {content.test_requirement === 'fly-probe' ? '飞针测试' :
                     content.test_requirement === 'fixture' ? '测试架测试' :
                     content.test_requirement === 'aoi' ? 'AOI测试' :
                     content.test_requirement === 'none' ? '无需测试' : content.test_requirement}
                  </Descriptions.Item>
                )}
                {content.special_requirements && (
                  <Descriptions.Item label="特殊要求" span={2}>
                    {content.special_requirements}
                  </Descriptions.Item>
                )}
                {mi.description && (
                  <Descriptions.Item label="描述" span={2}>
                    {mi.description}
                  </Descriptions.Item>
                )}
              </Descriptions>
            )}

            {/* MI指令项列表 */}
            <Card 
              title="MI指令项" 
              style={{ marginTop: 16 }}
            >
              {(() => {
                const instructions = getInstructions(mi)
                return instructions.length > 0 ? (
                  <Table
                    columns={instructionColumns}
                    dataSource={[...instructions].sort((a: any, b: any) => a.sequence - b.sequence)}
                    rowKey={(record: any) => record.id || record.sequence}
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <div style={{ padding: '20px', textAlign: 'center', color: 'hsl(var(--ink-faint))' }}>
                    暂无指令项
                  </div>
                )
              })()}
            </Card>
          </Card>
        </Col>

        <Col span={8}>
          <Card title="审核操作">
            <TextArea
              rows={8}
              placeholder="请输入审核意见..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <Divider />
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                type="primary"
                block
                onClick={handleApprove}
                loading={loading}
                style={{ backgroundColor: 'hsl(var(--chart-success))', borderColor: 'hsl(var(--chart-success))' }}
              >
                通过审核
              </Button>
              <Button
                danger
                block
                onClick={handleReject}
                loading={loading}
              >
                驳回申请
              </Button>
            </Space>
          </Card>

          <Card 
            title={`待审核列表 (${pendingMIs.length})`}
            style={{ marginTop: 16 }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {pendingMIs.map((item) => (
                <div
                  key={item.mi_number}
                  onClick={() => navigate(`/eng/mis/${item.mi_number}/review`)}
                  style={{
                    padding: '12px',
                    backgroundColor: item.mi_number === miNumber ? 'hsl(var(--brand-soft))' : 'hsl(var(--surface-hover))',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    borderLeft: item.mi_number === miNumber ? '4px solid hsl(var(--brand))' : '4px solid transparent'
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: '5px' }}>{item.mi_number}</div>
                  <div style={{ fontSize: '12px', color: 'hsl(var(--ink-soft))' }}>
                    {item.material_code} | {item.version}
                  </div>
                </div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default MIReview

