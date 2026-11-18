import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, InputNumber, Divider, Checkbox } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import api from '../../services/api'

const { Option } = Select

// 客户状态中文映射
const customerStatusMap: Record<string, string> = {
  'DRAFT': '草稿',
  'PENDING_SALES_MANAGER': '待销售经理审批',
  'PENDING_FINANCE': '待财务审批',
  'PENDING_GENERAL_MANAGER': '待总经理审批',
  'PENDING_APPROVAL': '待审批',
  'FROZEN': '已建档(冻结)',
  'ACTIVE': '激活',
  'BLOCKED': '冻结/停用',
  'INACTIVE': '未激活'
}

const CustomerForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [customerStatus, setCustomerStatus] = useState<string>('DRAFT')
  const isEdit = !!id

  useEffect(() => {
    if (isEdit) {
      fetchCustomer()
    }
  }, [id])

  const fetchCustomer = async () => {
    try {
      const response = await api.get(`/sd/customers/${id}`)
      const data = response.data
      setCustomerStatus(data.customer_status || 'DRAFT')
      form.setFieldsValue({
        ...data,
        partner_functions: data.partner_functions || [],
        customer_addresses: data.addresses || [],
        customer_contacts: data.contacts || [],
        sales_data: (data.sales_data && data.sales_data.length > 0) ? data.sales_data : [{}],
      })
    } catch (error) {
      message.error('获取客户信息失败')
      navigate('/sd/customers')
    }
  }

  const onFinish = async (values: any) => {
    const payload = {
      ...values,
      // 移除客户状态，由后端自动管理
      customer_status: undefined,
      partner_functions: values.partner_functions || [],
      customer_addresses: values.customer_addresses || [],
      customer_contacts: values.customer_contacts || [],
      sales_data: values.sales_data || []
    }
    setLoading(true)
    try {
      if (isEdit) {
        await api.put(`/sd/customers/${id}`, payload)
        message.success('客户更新成功')
        navigate('/sd/customers')
      } else {
        const response = await api.post('/sd/customers', payload)
        message.success('客户创建成功')
        // 新建成功后，导航到编辑页面，这样用户可以看到并点击"提交审批"按钮
        const customerId = response.data.customer_id || values.customer_id
        navigate(`/sd/customers/${customerId}/edit`)
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  // 提交客户审批（从草稿/未激活进入审批流）
  const handleSubmitForApproval = async () => {
    if (!isEdit) {
      message.warning('请先保存客户，再提交审批')
      return
    }

    setLoading(true)
    try {
      await api.post(`/sd/customers/${id}/submit`)
      message.success('客户已提交审批')
      // 重新加载客户信息以刷新状态
      await fetchCustomer()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '提交审批失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title={isEdit ? '编辑客户' : '新建客户'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            partner_functions: [{}],
            customer_addresses: [{ country: '中国' }],
            customer_contacts: [{}],
            sales_data: [{}]
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customer_id"
                label="客户代码"
                rules={[{ required: true, message: '请输入客户代码' }]}
              >
                <Input placeholder="请输入客户代码" disabled={isEdit} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="customer_status"
                label="客户状态"
              >
                <Input 
                  disabled 
                  placeholder={isEdit ? customerStatusMap[customerStatus] || customerStatus : '新建时自动设置为：草稿'} 
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="legal_name"
                label="公司法定全称"
                rules={[{ required: true, message: '请输入公司法定全称' }]}
              >
                <Input placeholder="请输入公司法定全称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="trade_name"
                label="常用商号/简称"
              >
                <Input placeholder="请输入常用商号/简称" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="tax_id"
                label="税号"
                rules={[{ required: true, message: '请输入税号' }]}
              >
                <Input placeholder="请输入税号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="customer_industry"
                label="所属行业"
              >
                <Select placeholder="请选择行业">
                  <Option value="汽车">汽车</Option>
                  <Option value="工业控制">工业控制</Option>
                  <Option value="医疗">医疗</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customer_website"
                label="公司网址"
              >
                <Input placeholder="请输入公司网址" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="credit_limit"
                label="信用额度"
              >
                <InputNumber style={{ width: '100%' }} placeholder="请输入信用额度" min={0} />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <h3>合作属性 / Partner Functions</h3>
          <Form.List name="partner_functions">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Card key={key} size="small" style={{ marginBottom: 12 }}>
                    <Row gutter={12}>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'partner_role']}
                          label="合作角色"
                          rules={[{ required: true, message: '请选择合作角色' }]}
                        >
                          <Select placeholder="选择角色">
                            <Option value="SOLD_TO">售达方</Option>
                            <Option value="SHIP_TO">送达方</Option>
                            <Option value="BILL_TO">开票方</Option>
                            <Option value="PAYER">付款方</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'partner_id']} label="合作方代码">
                          <Input placeholder="合作方代码" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item {...restField} name={[name, 'partner_name']} label="合作方名称">
                          <Input placeholder="合作方名称" />
                        </Form.Item>
                      </Col>
                      <Col span={4} style={{ display: 'flex', alignItems: 'center' }}>
                        <Button danger type="link" onClick={() => remove(name)}>
                          删除
                        </Button>
                      </Col>
                    </Row>
                    <Row gutter={12}>
                      <Col span={24}>
                        <Form.Item {...restField} name={[name, 'partnership_description']} label="合作描述">
                          <Input placeholder="合作描述" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add()} block>
                  新增合作角色
                </Button>
              </>
            )}
          </Form.List>

          <Divider />
          <h3>地址信息 / Addresses</h3>
          <Form.List name="customer_addresses">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Card key={key} size="small" style={{ marginBottom: 12 }}>
                    <Row gutter={12}>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'address_type']}
                          label="地址类型"
                          rules={[{ required: true, message: '请选择地址类型' }]}
                        >
                          <Select placeholder="选择类型">
                            <Option value="HEADQUARTERS">总部</Option>
                            <Option value="PLANT">工厂</Option>
                            <Option value="WAREHOUSE">仓库</Option>
                            <Option value="BILLING">账单</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={10}>
                        <Form.Item
                          {...restField}
                          name={[name, 'detail_address']}
                          label="详细地址"
                          rules={[{ required: true, message: '请输入详细地址' }]}
                        >
                          <Input placeholder="详细地址" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item {...restField} name={[name, 'location']} label="归属地">
                          <Input placeholder="归属地" />
                        </Form.Item>
                      </Col>
                      <Col span={4} style={{ display: 'flex', alignItems: 'center' }}>
                        <Button danger type="link" onClick={() => remove(name)}>
                          删除
                        </Button>
                      </Col>
                    </Row>
                    <Row gutter={12}>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'postal_code']} label="邮政编码">
                          <Input placeholder="邮政编码" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'country']} label="国家">
                          <Input placeholder="国家" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item {...restField} name={[name, 'province']} label="省">
                          <Input placeholder="省" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item {...restField} name={[name, 'city']} label="市">
                          <Input placeholder="市" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item {...restField} name={[name, 'district']} label="区">
                          <Input placeholder="区" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={12}>
                      <Col span={12}>
                        <Form.Item {...restField} name={[name, 'is_default_shipping']} valuePropName="checked">
                          <Checkbox>默认送货地址</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item {...restField} name={[name, 'is_default_billing']} valuePropName="checked">
                          <Checkbox>默认账单地址</Checkbox>
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add({ country: '中国' })} block>
                  新增地址
                </Button>
              </>
            )}
          </Form.List>

          <Divider />
          <h3>联系人信息 / Contacts</h3>
          <Form.List name="customer_contacts">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Card key={key} size="small" style={{ marginBottom: 12 }}>
                    <Row gutter={12}>
                      <Col span={4}>
                        <Form.Item {...restField} name={[name, 'is_primary_contact']} valuePropName="checked">
                          <Checkbox>主要联系人</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'contact_name']}
                          label="姓名"
                          rules={[{ required: true, message: '请输入联系人姓名' }]}
                        >
                          <Input placeholder="联系人姓名" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'contact_role']} label="职务">
                          <Input placeholder="职务" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'contact_department']} label="部门">
                          <Input placeholder="部门" />
                        </Form.Item>
                      </Col>
                      <Col span={2} style={{ display: 'flex', alignItems: 'center' }}>
                        <Button danger type="link" onClick={() => remove(name)}>
                          删除
                        </Button>
                      </Col>
                    </Row>
                    <Row gutter={12}>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'contact_phone']} label="电话">
                          <Input placeholder="电话" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item {...restField} name={[name, 'contact_email']} label="邮箱">
                          <Input placeholder="邮箱" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add()} block>
                  新增联系人
                </Button>
              </>
            )}
          </Form.List>

          <Divider />
          <h3>销售数据 / Sales Data</h3>
          <Form.List name="sales_data">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Card key={key} size="small" style={{ marginBottom: 12 }}>
                    <Row gutter={12}>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'sales_organization']} label="销售组织">
                          <Input placeholder="销售组织" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'account_manager_name']} label="业务员">
                          <Input placeholder="业务员姓名" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'sales_assistant_name']} label="跟单员">
                          <Input placeholder="跟单员姓名" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'trading_currency']} label="交易货币">
                          <Input placeholder="交易货币" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={12}>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'primary_trade_country']} label="主要贸易国">
                          <Input placeholder="主要贸易国" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item {...restField} name={[name, 'incoterms']} label="贸易术语">
                          <Input placeholder="INCOTERMS" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item {...restField} name={[name, 'shipping_conditions']} label="运输条件">
                          <Input placeholder="运输条件" />
                        </Form.Item>
                      </Col>
                      <Col span={4} style={{ display: 'flex', alignItems: 'center' }}>
                        {fields.length > 1 && (
                          <Button danger type="link" onClick={() => remove(name)}>
                            删除
                          </Button>
                        )}
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add()} block>
                  新增销售数据
                </Button>
              </>
            )}
          </Form.List>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {isEdit ? '更新' : '创建'}
              </Button>
              {isEdit && (customerStatus === 'DRAFT' || customerStatus === 'INACTIVE' || customerStatus === 'PENDING_APPROVAL') && (
                <Button onClick={handleSubmitForApproval} loading={loading}>
                  提交审批
                </Button>
              )}
              <Button onClick={() => navigate('/sd/customers')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default CustomerForm

