# 共享组件使用文档

## 文档说明

**版本：** v1.0  
**创建日期：** 2025-12-12  
**最后更新：** 2025-12-12

本文档介绍前端共享组件的使用方法。

---

## 一、组件列表

### 1. MaterialSelect - 物料选择组件

物料下拉选择组件，支持搜索、过滤和自动加载。

#### 基本用法

```typescript
import MaterialSelect from '@/components/common/MaterialSelect'

<Form.Item name="material_code" label="物料编码">
  <MaterialSelect />
</Form.Item>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| value | string | - | 选中的物料编码 |
| onChange | (value: string) => void | - | 值变化回调 |
| materialType | string | - | 物料类型过滤（FG/RAW/SEMI） |
| showActiveOnly | boolean | true | 只显示激活的物料 |
| placeholder | string | "请选择物料" | 占位符 |
| disabled | boolean | false | 是否禁用 |
| ...rest | SelectProps | - | 其他 Ant Design Select 属性 |

#### 示例

```typescript
// 只显示成品物料
<MaterialSelect 
  materialType="FG"
  showActiveOnly={true}
/>

// 禁用状态
<MaterialSelect 
  disabled={true}
  value={materialCode}
/>

// 自定义占位符
<MaterialSelect 
  placeholder="请选择父物料"
  onChange={(value) => console.log('选中物料:', value)}
/>
```

#### 特性

- ✅ 自动加载物料列表
- ✅ 支持搜索过滤
- ✅ 支持物料类型过滤
- ✅ 支持状态过滤（只显示激活物料）
- ✅ 显示格式：`物料编码 - 物料名称`

---

### 2. CustomerSelect - 客户选择组件

客户下拉选择组件，支持搜索和自动加载。

#### 基本用法

```typescript
import CustomerSelect from '@/components/common/CustomerSelect'

<Form.Item name="customer_id" label="客户">
  <CustomerSelect />
</Form.Item>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| value | string | - | 选中的客户ID |
| onChange | (value: string) => void | - | 值变化回调 |
| showActiveOnly | boolean | true | 只显示激活的客户 |
| placeholder | string | "请选择客户" | 占位符 |
| disabled | boolean | false | 是否禁用 |
| ...rest | SelectProps | - | 其他 Ant Design Select 属性 |

#### 示例

```typescript
// 只显示激活客户
<CustomerSelect 
  showActiveOnly={true}
/>

// 禁用状态
<CustomerSelect 
  disabled={fromQuotation}
  value={customerId}
/>

// 自定义占位符
<CustomerSelect 
  placeholder="请选择客户"
  onChange={(value) => {
    // 处理客户选择
    handleCustomerChange(value)
  }}
/>
```

#### 特性

- ✅ 自动加载客户列表
- ✅ 支持搜索过滤
- ✅ 支持状态过滤（只显示激活客户）
- ✅ 显示格式：`客户ID - 公司名称`

---

### 3. FormButtons - 表单按钮组件

统一的表单操作按钮组件，包含保存和取消按钮。

#### 基本用法

```typescript
import FormButtons from '@/components/common/FormButtons'

<FormButtons 
  loading={loading}
  onSave={handleSave}
  cancelPath="/sd/sales-orders"
/>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| loading | boolean | false | 保存按钮加载状态 |
| onSave | () => void | - | 保存按钮点击回调 |
| onCancel | () => void | - | 取消按钮点击回调（可选） |
| saveText | string | "保存" | 保存按钮文本 |
| cancelText | string | "取消" | 取消按钮文本 |
| showCancel | boolean | true | 是否显示取消按钮 |
| cancelPath | string | - | 取消时跳转的路径（可选） |

#### 示例

```typescript
// 基本用法
<FormButtons 
  loading={loading}
  onSave={handleSave}
/>

// 自定义按钮文本
<FormButtons 
  loading={loading}
  onSave={handleSave}
  saveText="提交"
  cancelText="返回"
/>

// 自定义取消行为
<FormButtons 
  loading={loading}
  onSave={handleSave}
  onCancel={() => {
    // 自定义取消逻辑
    if (hasUnsavedChanges) {
      // confirm 来自 useConfirm()，见「统一确认弹窗」
      confirm({
        title: '确认取消',
        content: '有未保存的更改，确定要取消吗？',
        onOk: () => navigate('/sd/sales-orders')
      })
    } else {
      navigate('/sd/sales-orders')
    }
  }}
/>

// 只显示保存按钮
<FormButtons 
  loading={loading}
  onSave={handleSave}
  showCancel={false}
/>
```

#### 特性

- ✅ 统一的按钮样式和行为
- ✅ 自动处理取消导航
- ✅ 支持自定义取消逻辑
- ✅ 支持自定义按钮文本

---

### 4. StandardTable - 标准表格组件

标准化的表格组件，支持分页、刷新和API集成。

#### 基本用法

```typescript
import StandardTable from '@/components/common/StandardTable'

<StandardTable
  apiEndpoint="/sd/sales-orders"
  columns={columns}
  rowKey="order_number"
/>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| apiEndpoint | string | - | API端点（必填） |
| apiParams | Record<string, any> | {} | API请求参数 |
| columns | TableProps['columns'] | - | 表格列定义（必填） |
| rowKey | string \| (record: T) => string | 'id' | 行键 |
| onRefresh | () => void | - | 刷新回调 |
| showActions | boolean | true | 是否显示操作栏 |
| actionButtons | React.ReactNode | - | 自定义操作按钮 |
| ...rest | TableProps | - | 其他 Ant Design Table 属性 |

#### 示例

```typescript
// 基本用法
const columns = [
  { title: '订单号', dataIndex: 'order_number', key: 'order_number' },
  { title: '客户', dataIndex: 'customer_id', key: 'customer_id' },
  { title: '状态', dataIndex: 'status', key: 'status' },
]

<StandardTable
  apiEndpoint="/sd/sales-orders"
  columns={columns}
  rowKey="order_number"
/>

// 带筛选参数
<StandardTable
  apiEndpoint="/sd/sales-orders"
  apiParams={{
    status: 'APPROVED',
    customer_id: selectedCustomerId
  }}
  columns={columns}
  rowKey="order_number"
/>

// 自定义操作按钮
<StandardTable
  apiEndpoint="/sd/sales-orders"
  columns={columns}
  rowKey="order_number"
  actionButtons={
    <>
      <Button onClick={handleExport}>导出</Button>
      <Button type="primary" onClick={handleCreate}>新建</Button>
    </>
  }
/>

// 隐藏操作栏
<StandardTable
  apiEndpoint="/sd/sales-orders"
  columns={columns}
  rowKey="order_number"
  showActions={false}
/>
```

#### 特性

- ✅ 自动分页
- ✅ 自动加载数据
- ✅ 支持刷新
- ✅ 支持筛选参数
- ✅ 统一的加载状态
- ✅ 统一的错误处理

---

### 5. useConfirm - 统一确认弹窗

**不要再使用 `Modal.confirm`**。`Modal.confirm` 是 antd 的紧凑布局，没有标题分隔线和关闭按钮，与普通表单弹窗不一致。
统一走 `ConfirmProvider` 提供的 `confirm()`，弹窗结构为「图标 + 标题 + 关闭按钮 + 分隔线 + 底部按钮栏」。

`ConfirmProvider` 已在 `main.tsx` 全局挂载，页面内只需取用：

```typescript
import { useConfirm } from '@/components/common/ConfirmProvider'

const confirm = useConfirm()

confirm({
  title: '确认关闭',
  icon: 'warning',            // 'info'(默认) | 'warning'
  content: '关闭后不可撤销，确定要关闭吗？',
  okText: '确认关闭',
  cancelText: '取消',
  danger: false,              // 确认按钮是否用危险色
  onOk: async () => {         // 返回 Promise 时按钮自动 loading，完成后关闭
    await api.post('/sd/sales-orders/xxx/close')
  },
  onCancel: () => {}
})
```

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | ReactNode | - | 标题（自动带图标） |
| content | ReactNode | - | 正文内容 |
| icon | 'info' \| 'warning' | 'info' | 标题图标语义，删除/废弃/关闭类建议用 warning |
| okText | string | 确定 | 确认按钮文案 |
| cancelText | string | 取消 | 取消按钮文案 |
| danger | boolean | false | 确认按钮是否使用危险色 |
| width | number | 420 | 弹窗宽度 |
| maskClosable | boolean | false | 点击遮罩是否关闭 |
| onOk | () => void \| Promise&lt;void&gt; | - | 确认回调 |
| onCancel | () => void | - | 取消回调 |

---

## 二、迁移指南

### 2.1 迁移 MaterialSelect

#### 迁移前

```typescript
const [materials, setMaterials] = useState<any[]>([])

useEffect(() => {
  fetchMaterials()
}, [])

const fetchMaterials = async () => {
  try {
    const response = await api.get('/mm/materials')
    setMaterials(response.data)
  } catch (error) {
    console.error('获取物料列表失败:', error)
  }
}

<Form.Item name="material_code">
  <Select placeholder="请选择物料" showSearch>
    {materials.map((material) => (
      <Option key={material.material_code} value={material.material_code}>
        {material.material_code} - {material.material_name}
      </Option>
    ))}
  </Select>
</Form.Item>
```

#### 迁移后

```typescript
import MaterialSelect from '@/components/common/MaterialSelect'

<Form.Item name="material_code">
  <MaterialSelect />
</Form.Item>
```

**优势：**
- ✅ 减少约20行代码
- ✅ 自动处理加载状态
- ✅ 统一的搜索和过滤逻辑

---

### 2.2 迁移 CustomerSelect

#### 迁移前

```typescript
const [customers, setCustomers] = useState<any[]>([])

useEffect(() => {
  fetchCustomers()
}, [])

const fetchCustomers = async () => {
  try {
    const response = await api.get('/sd/customers')
    setCustomers(response.data)
  } catch (error) {
    console.error('获取客户列表失败:', error)
  }
}

<Form.Item name="customer_id">
  <Select placeholder="请选择客户" showSearch>
    {customers.map((customer) => (
      <Option key={customer.customer_id} value={customer.customer_id}>
        {customer.customer_id} - {customer.legal_name}
      </Option>
    ))}
  </Select>
</Form.Item>
```

#### 迁移后

```typescript
import CustomerSelect from '@/components/common/CustomerSelect'

<Form.Item name="customer_id">
  <CustomerSelect />
</Form.Item>
```

**优势：**
- ✅ 减少约20行代码
- ✅ 自动处理加载状态
- ✅ 统一的搜索逻辑

---

### 2.3 迁移 FormButtons

#### 迁移前

```typescript
<Space>
  <Button type="primary" loading={loading} onClick={handleSave}>
    保存
  </Button>
  <Button onClick={() => navigate('/sd/sales-orders')}>
    取消
  </Button>
</Space>
```

#### 迁移后

```typescript
import FormButtons from '@/components/common/FormButtons'

<FormButtons 
  loading={loading}
  onSave={handleSave}
  cancelPath="/sd/sales-orders"
/>
```

**优势：**
- ✅ 统一的按钮样式
- ✅ 简化的导航逻辑
- ✅ 支持自定义取消行为

---

## 三、最佳实践

### 3.1 组件选择

- **MaterialSelect**: 所有需要选择物料的场景
- **CustomerSelect**: 所有需要选择客户的场景
- **FormButtons**: 所有表单页面的操作按钮
- **StandardTable**: 所有需要分页列表的场景

### 3.2 错误处理

使用共享组件时，建议配合 `errorHandler` 工具：

```typescript
import { handleApiError } from '@/utils/errorHandler'

try {
  await api.post('/sd/sales-orders', data)
  message.success('创建成功')
} catch (error) {
  handleApiError(error)
}
```

### 3.3 状态管理

对于频繁使用的数据（如物料列表），建议使用状态管理：

```typescript
import useMaterialStore from '@/stores/materialStore'

const { materials, setMaterials } = useMaterialStore()

// 在组件中使用
useEffect(() => {
  if (materials.length === 0) {
    // 加载物料列表
  }
}, [])
```

---

## 四、常见问题

### Q1: MaterialSelect 如何自定义显示格式？

A: 目前组件固定显示 `物料编码 - 物料名称` 格式。如需自定义，可以：
1. 修改组件源码
2. 或创建新的自定义组件

### Q2: StandardTable 如何支持服务端排序？

A: 可以在 `apiParams` 中传递排序参数，或扩展组件支持排序回调。

### Q3: FormButtons 如何支持更多按钮？

A: 可以使用 `actionButtons` 属性添加自定义按钮，或扩展组件支持更多预设按钮。

---

## 五、扩展开发

### 5.1 创建新的共享组件

1. 在 `frontend/src/components/common/` 目录下创建新组件
2. 遵循现有组件的代码风格
3. 添加 TypeScript 类型定义
4. 更新本文档

### 5.2 组件设计原则

- ✅ 单一职责：每个组件只负责一个功能
- ✅ 可复用：组件应该可以在多个场景使用
- ✅ 可配置：通过 Props 支持不同使用场景
- ✅ 类型安全：使用 TypeScript 定义类型

---

**文档版本：** v1.0  
**最后更新：** 2025-12-12  
**维护者：** 开发团队

