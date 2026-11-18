# 某某ERP系统 - 服务模型（Service Contracts）

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-12-12  
**最后更新：** 2025-01-XX

**基于**：某某ERP系统MVP版本需求规格说明书 v1.4

本文档描述了某某ERP系统的服务模型，定义了各个业务服务的接口、操作规范、依赖关系和契约规范。服务模型采用面向服务的架构（SOA）设计原则，确保服务的可重用性、可维护性和可扩展性。

---

## 一、服务模型概述

### 1.1 服务架构

某某ERP系统采用**模块化服务架构**，将业务功能划分为多个独立的服务模块：

- **认证服务（Auth Service）**：用户认证和授权
- **用户管理服务（User Service）**：用户和角色管理
- **销售与分销服务（SD Service）**：客户、报价单、销售订单管理
- **工程管理服务（ENG Service）**：BOM、工艺路线、MI、生产版本管理
- **生产计划与控制服务（PP Service）**：工作中心、生产订单、工序报工管理
- **物料管理服务（MM Service）**：物料主数据、库存、领料管理
- **工作流服务（Workflow Service）**：审批流程引擎

### 1.2 服务设计原则

1. **单一职责原则**：每个服务只负责一个业务领域
2. **接口隔离原则**：服务接口设计简洁、明确
3. **依赖倒置原则**：服务之间通过接口交互，降低耦合
4. **契约优先**：服务接口定义明确，遵循OpenAPI规范
5. **无状态设计**：服务调用不依赖会话状态
6. **幂等性**：关键操作支持幂等性，可安全重试

### 1.3 服务通信协议

- **协议**：HTTP/HTTPS
- **数据格式**：JSON
- **认证方式**：JWT Bearer Token
- **API风格**：RESTful

---

## 二、服务分类

### 2.1 服务模块列表

| 服务模块 | 服务名称 | 服务标识 | 描述 |
|---------|---------|---------|------|
| 认证 | AuthService | `auth` | 用户登录、令牌管理 |
| 用户管理 | UserService | `user` | 用户CRUD、角色管理 |
| 销售与分销 | SDService | `sd` | 客户、报价单、销售订单 |
| 工程管理 | ENGService | `eng` | BOM、工艺路线、MI、生产版本 |
| 生产计划与控制 | PPService | `pp` | 工作中心、生产订单、报工 |
| 物料管理 | MMService | `mm` | 物料主数据、库存、领料 |
| 工作流 | WorkflowService | `workflow` | 审批流程引擎 |

### 2.2 服务层次结构

```
┌─────────────────────────────────────────┐
│         前端应用层（Frontend）            │
└─────────────────┬───────────────────────┘
                  │ HTTP/JSON
┌─────────────────▼───────────────────────┐
│         API网关层（API Gateway）         │
│  - 路由转发                                │
│  - 认证授权                                │
│  - 请求限流                                │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│  SD   │   │  ENG  │   │  PP   │
│Service│   │Service│   │Service│
└───┬───┘   └───┬───┘   └───┬───┘
    │           │           │
    └───────────┼───────────┘
                │
        ┌───────▼───────┐
        │  Workflow     │
        │  Service      │
        └───────┬───────┘
                │
        ┌───────▼───────┐
        │   Database    │
        │  (PostgreSQL) │
        └───────────────┘
```

---

## 三、认证服务（Auth Service）

### 3.1 服务标识

- **服务名称**：AuthService
- **服务标识**：`auth`
- **基础路径**：`/api/auth`

### 3.2 服务接口

#### 3.2.1 登录接口

**接口名称**：`login`  
**HTTP方法**：POST  
**路径**：`/api/auth/login`

**请求契约**：
```yaml
LoginRequest:
  type: object
  required:
    - username
    - password
  properties:
    username:
      type: string
      description: 用户名
    password:
      type: string
      format: password
      description: 密码
```

**响应契约**：
```yaml
LoginResponse:
  type: object
  required:
    - access_token
    - token_type
  properties:
    access_token:
      type: string
      description: JWT访问令牌
    token_type:
      type: string
      example: bearer
```

**服务操作规范**：
- 验证用户名和密码
- 生成JWT令牌（包含用户ID、角色、过期时间）
- 返回令牌和令牌类型

**错误处理**：
- `401 UNAUTHORIZED`：用户名或密码错误

---

#### 3.2.2 获取当前用户信息

**接口名称**：`getCurrentUser`  
**HTTP方法**：GET  
**路径**：`/api/auth/me`

**请求契约**：
- 需要Bearer Token认证

**响应契约**：
```yaml
UserInfoResponse:
  type: object
  properties:
    id:
      type: integer
    username:
      type: string
    email:
      type: string
    full_name:
      type: string
    role:
      type: string
    department:
      type: string
```

**服务操作规范**：
- 从JWT令牌中提取用户ID
- 查询用户信息
- 返回用户详细信息

**错误处理**：
- `401 UNAUTHORIZED`：令牌无效或已过期

---

### 3.3 服务依赖

- **UserService**：查询用户信息

---

## 四、用户管理服务（User Service）

### 4.1 服务标识

- **服务名称**：UserService
- **服务标识**：`user`
- **基础路径**：`/api`

### 4.2 服务接口

#### 4.2.1 创建用户

**接口名称**：`createUser`  
**HTTP方法**：POST  
**路径**：`/api/users`

**请求契约**：
```yaml
CreateUserRequest:
  type: object
  required:
    - username
    - email
    - password
    - role
  properties:
    username:
      type: string
      minLength: 3
      maxLength: 50
    email:
      type: string
      format: email
    password:
      type: string
      format: password
      minLength: 6
    role:
      type: string
      enum: [SALES, SALES_MANAGER, ENGINEER, PLANNER, PRODUCTION, WAREHOUSE, FINANCE, GENERAL_MANAGER, ADMIN]
    full_name:
      type: string
    department:
      type: string
    phone:
      type: string
    is_active:
      type: boolean
      default: true
```

**响应契约**：
```yaml
UserResponse:
  type: object
  properties:
    id:
      type: integer
    username:
      type: string
    email:
      type: string
    full_name:
      type: string
    role:
      type: string
    department:
      type: string
    phone:
      type: string
    is_active:
      type: boolean
    created_at:
      type: string
      format: date-time
```

**服务操作规范**：
- 验证用户名和邮箱唯一性
- 密码加密存储（bcrypt）
- 创建用户记录
- 返回用户信息

**权限要求**：
- 需要ADMIN角色

**错误处理**：
- `400 BAD_REQUEST`：用户名或邮箱已存在
- `403 FORBIDDEN`：权限不足

---

#### 4.2.2 获取用户列表

**接口名称**：`listUsers`  
**HTTP方法**：GET  
**路径**：`/api/users`

**请求契约**：
```yaml
ListUsersRequest:
  type: object
  properties:
    skip:
      type: integer
      default: 0
    limit:
      type: integer
      default: 100
    role:
      type: string
      description: 角色过滤
```

**响应契约**：
```yaml
ListUsersResponse:
  type: array
  items:
    $ref: '#/components/schemas/UserResponse'
```

**服务操作规范**：
- 支持分页查询
- 支持按角色过滤
- 排除已删除用户（软删除）
- 返回用户列表

**权限要求**：
- 需要ADMIN角色

---

#### 4.2.3 更新用户

**接口名称**：`updateUser`  
**HTTP方法**：PUT  
**路径**：`/api/users/{user_id}`

**服务操作规范**：
- 验证用户存在
- 更新用户信息
- 如果提供新密码，则加密后更新
- 返回更新后的用户信息

**权限要求**：
- 需要ADMIN角色

---

#### 4.2.4 删除用户

**接口名称**：`deleteUser`  
**HTTP方法**：DELETE  
**路径**：`/api/users/{user_id}`

**服务操作规范**：
- 软删除用户（设置`is_deleted=True`）
- 不物理删除数据
- 返回204 No Content

**权限要求**：
- 需要ADMIN角色

---

#### 4.2.5 获取角色列表

**接口名称**：`listRoles`  
**HTTP方法**：GET  
**路径**：`/api/roles`

**响应契约**：
```yaml
ListRolesResponse:
  type: array
  items:
    type: object
    properties:
      value:
        type: string
        description: 角色代码
      label:
        type: string
        description: 角色名称
```

**服务操作规范**：
- 返回所有可用角色
- 角色信息从UserRole枚举获取

---

### 4.3 服务依赖

- **Database**：用户数据持久化

---

## 五、销售与分销服务（SD Service）

### 5.1 服务标识

- **服务名称**：SDService
- **服务标识**：`sd`
- **基础路径**：`/api/sd`

### 5.2 服务接口

#### 5.2.1 客户管理服务

**服务名称**：`CustomerService`  
**服务标识**：`sd.customer`

##### 创建客户

**接口名称**：`createCustomer`  
**HTTP方法**：POST  
**路径**：`/api/sd/customers`

**请求契约**：
```yaml
CreateCustomerRequest:
  type: object
  required:
    - customer_id
    - legal_name
  properties:
    customer_id:
      type: string
      maxLength: 50
    legal_name:
      type: string
      maxLength: 200
    trade_name:
      type: string
    tax_id:
      type: string
    customer_industry:
      type: string
    customer_website:
      type: string
    credit_limit:
      type: number
      format: float
    customer_status:
      type: string
      enum: [DRAFT, PENDING_APPROVAL, ACTIVE, BLOCKED, INACTIVE]
    partner_functions:
      type: array
      items:
        $ref: '#/components/schemas/CustomerPartnerFunctionPayload'
    customer_addresses:
      type: array
      items:
        $ref: '#/components/schemas/CustomerAddressPayload'
    customer_contacts:
      type: array
      items:
        $ref: '#/components/schemas/CustomerContactPayload'
    sales_data:
      type: array
      items:
        $ref: '#/components/schemas/CustomerSalesDataPayload'
```

**服务操作规范**：
- 验证客户ID唯一性
- 创建客户主记录
- 创建关联的地址、联系人、合作角色、销售数据记录
- 返回完整的客户信息

**权限要求**：
- 需要SALES角色

**错误处理**：
- `400 BAD_REQUEST`：客户ID已存在
- `403 FORBIDDEN`：权限不足

---

##### 获取客户列表

**接口名称**：`listCustomers`  
**HTTP方法**：GET  
**路径**：`/api/sd/customers`

**服务操作规范**：
- 支持分页查询
- 支持按状态过滤
- 返回客户列表（包含关联数据）

---

##### 获取客户详情

**接口名称**：`getCustomer`  
**HTTP方法**：GET  
**路径**：`/api/sd/customers/{customer_id}`

**服务操作规范**：
- 查询客户主记录
- 查询关联的地址、联系人、合作角色、销售数据
- 返回完整的客户信息

**错误处理**：
- `404 NOT_FOUND`：客户不存在

---

##### 更新客户

**接口名称**：`updateCustomer`  
**HTTP方法**：PUT  
**路径**：`/api/sd/customers/{customer_id}`

**服务操作规范**：
- 验证客户存在
- 更新客户主记录
- 更新或创建关联的地址、联系人、合作角色、销售数据
- 返回更新后的客户信息

**权限要求**：
- 需要SALES角色

---

#### 5.2.2 报价单管理服务

**服务名称**：`QuotationService`  
**服务标识**：`sd.quotation`

##### 创建报价单

**接口名称**：`createQuotation`  
**HTTP方法**：POST  
**路径**：`/api/sd/quotations`

**请求契约**：
```yaml
CreateQuotationRequest:
  type: object
  required:
    - customer_id
    - product_number
    - quantity
    - unit_price
  properties:
    customer_id:
      type: string
    product_number:
      type: string
      description: 本厂编号
    product_series:
      type: string
    layers:
      type: integer
    quantity:
      type: number
      format: float
    unit_price:
      type: number
      format: float
    currency:
      type: string
      default: CNY
    valid_until:
      type: string
      format: date
    remarks:
      type: string
```

**服务操作规范**：
- 自动生成报价单号（QT-YYYYMMDD-XXXX）
- 计算总金额（quantity × unit_price）
- 设置初始状态为DRAFT
- 创建报价单记录
- 返回报价单信息

**权限要求**：
- 需要SALES角色

---

##### 提交报价单审批

**接口名称**：`submitQuotation`  
**HTTP方法**：POST  
**路径**：`/api/sd/quotations/{quotation_number}/submit`

**服务操作规范**：
- 验证报价单状态为DRAFT或REJECTED
- 如果状态为REJECTED，清除之前的审批信息
- 启动报价单审批工作流
- 设置状态为PENDING_SALES
- 返回提交结果

**权限要求**：
- 需要SALES角色（REJECTED状态只能由SALES角色重新提交）

**错误处理**：
- `400 BAD_REQUEST`：报价单状态无效或必填字段不完整

---

##### 审批报价单

**接口名称**：`approveQuotation`  
**HTTP方法**：POST  
**路径**：`/api/sd/quotations/{quotation_number}/approve`

**服务操作规范**：
- 获取当前工作流实例
- 验证当前用户有权限审批当前节点
- 推进工作流到下一个节点
- 如果所有节点都审批通过，设置状态为APPROVED
- 记录审批信息
- 返回审批结果

**权限要求**：
- 需要相应审批节点的角色（SALES_MANAGER/FINANCE/GENERAL_MANAGER）

**错误处理**：
- `403 FORBIDDEN`：当前用户没有权限审批此节点

---

##### 拒绝报价单

**接口名称**：`rejectQuotation`  
**HTTP方法**：POST  
**路径**：`/api/sd/quotations/{quotation_number}/reject`

**服务操作规范**：
- 获取当前工作流实例
- 验证当前用户有权限审批当前节点
- 标记工作流为REJECTED
- 设置报价单状态为REJECTED
- 记录拒绝原因
- 返回拒绝结果

**权限要求**：
- 需要相应审批节点的角色

---

#### 5.2.3 销售订单管理服务

**服务名称**：`SalesOrderService`  
**服务标识**：`sd.sales_order`

##### 创建销售订单

**接口名称**：`createSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders`

**请求契约**：
```yaml
CreateSalesOrderRequest:
  type: object
  required:
    - customer_id
    - product_number
    - quantity
    - delivery_date
  properties:
    quotation_number:
      type: string
      description: 报价单号（可选）
    customer_id:
      type: string
    product_number:
      type: string
      description: 本厂编号
    quantity:
      type: number
      format: float
    unit_price:
      type: number
      format: float
    delivery_date:
      type: string
      format: date-time
    is_return_order:
      type: boolean
      default: false
    remarks:
      type: string
    material_code:
      type: string
      description: 物料编码（可选，如果提供则直接使用，否则自动查找映射）
    production_version_id:
      type: string
      description: 生产版本ID（可选）
```

**服务操作规范**：
1. **本厂编号映射查找**：
   - 如果未提供`material_code`，根据`customer_id`和`product_number`查找`FactoryProductMapping`
   - 如果找到映射，自动填充`material_code`和`production_version_id`
   - 如果未找到映射，返回错误

2. **物料信息验证**：
   - 验证`material_code`对应的物料存在且状态为ACTIVE
   - 如果提供了`production_version_id`，验证生产版本存在且状态为ACTIVE

3. **单位转换计算**：
   - 从物料主数据获取`base_unit`、`production_unit`、`conversion_factor`
   - 计算`production_quantity = quantity / conversion_factor`
   - 设置`sales_unit = base_unit`（通常是PCS）
   - 设置`production_unit`和`conversion_factor`

4. **报价单关联**：
   - 如果提供了`quotation_number`，验证报价单存在且状态符合要求
   - 如果是返单，允许选择已关联的报价单
   - 如果是新单，只能选择已批准且未关联的报价单

5. **创建订单**：
   - 自动生成订单号（SO-YYYYMMDD-XXXX）
   - 计算总金额（quantity × unit_price）
   - 设置初始状态为DRAFT
   - 创建销售订单记录
   - 返回订单信息

**权限要求**：
- 需要SALES角色

**错误处理**：
- `400 BAD_REQUEST`：物料编码不存在或必填字段不完整
- `404 NOT_FOUND`：本厂编号映射不存在

---

##### 提交销售订单评审

**接口名称**：`submitSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/submit`

**服务操作规范**：
- 验证订单状态为DRAFT
- 启动销售订单多部门评审工作流（SALES_ORDER_REVIEW）
- 设置订单状态为PENDING_REVIEW
- 设置`review_status = "PENDING"`
- 返回提交结果

**权限要求**：
- 需要SALES角色

**服务依赖**：
- **WorkflowService**：启动工作流实例

---

##### 获取销售订单评审状态

**接口名称**：`getSalesOrderReviewStatus`  
**HTTP方法**：GET  
**路径**：`/api/sd/sales-orders/{order_number}/review-status`

**响应契约**：
```yaml
ReviewStatusResponse:
  type: object
  properties:
    has_workflow:
      type: boolean
      description: 是否有工作流实例
    can_approve:
      type: boolean
      description: 当前用户是否可以审批
    current_user_role:
      type: string
      description: 当前用户角色
    current_node:
      type: object
      properties:
        node_id:
          type: string
        node_name:
          type: string
        approver_role:
          type: string
    nodes:
      type: array
      items:
        type: object
        properties:
          node_id:
            type: string
          node_name:
            type: string
          status:
            type: string
            enum: [PENDING, APPROVED, REJECTED]
          approver:
            type: string
          approved_at:
            type: string
            format: date-time
    review_history:
      type: array
      items:
        $ref: '#/components/schemas/ContractReviewResponse'
    debug_info:
      type: object
      description: 调试信息（开发环境）
```

**服务操作规范**：
- 查询销售订单的工作流实例
- 如果工作流实例不存在且订单状态为PENDING_REVIEW，自动创建
- 获取工作流状态和节点信息
- 检查当前用户是否有权限审批当前节点
- 查询评审历史记录
- 返回评审状态信息

**服务依赖**：
- **WorkflowService**：获取工作流状态

---

##### 审批销售订单

**接口名称**：`approveSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/approve`

**服务操作规范**：
- 获取销售订单的工作流实例
- 验证当前用户有权限审批当前节点
- 推进工作流到下一个节点
- 记录评审信息到`ContractReview`表
- 如果所有节点都审批通过：
  - 设置订单状态为APPROVED
  - 设置`review_status = "APPROVED"`
  - 如果关联了报价单，将报价单状态更新为LINKED
- 否则：
  - 设置订单状态为REVIEWING
  - 设置`review_status = "REVIEWING"`
- 返回审批结果

**权限要求**：
- 需要相应审批节点的角色（SALES_MANAGER/ENGINEER/WAREHOUSE/FINANCE）
- 对于SALES_REVIEW节点，允许SALES和SALES_MANAGER角色

**服务依赖**：
- **WorkflowService**：推进工作流

**错误处理**：
- `403 FORBIDDEN`：当前用户没有权限审批此节点
- `404 NOT_FOUND`：工作流实例不存在

---

##### 拒绝销售订单

**接口名称**：`rejectSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/reject`

**服务操作规范**：
- 获取销售订单的工作流实例
- 验证当前用户有权限审批当前节点
- 标记工作流为REJECTED
- 设置订单状态为REJECTED
- 设置`review_status = "REJECTED"`
- 记录评审信息到`ContractReview`表
- 返回拒绝结果

**权限要求**：
- 需要相应审批节点的角色
- 对于SALES_REVIEW节点，允许SALES和SALES_MANAGER角色

**服务依赖**：
- **WorkflowService**：拒绝工作流

---

##### 销售发货

**接口名称**：`shipSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/ship`

**服务操作规范**：
- 验证订单状态为COMPLETED
- 设置订单状态为SHIPPED
- 返回订单信息

**权限要求**：
- 需要SALES角色

---

##### 销售签收

**接口名称**：`deliverSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/deliver`

**服务操作规范**：
- 验证订单状态为SHIPPED
- 设置订单状态为DELIVERED
- 返回订单信息

**权限要求**：
- 需要SALES角色

---

##### 对账

**接口名称**：`reconcileSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/reconcile`

**服务操作规范**：
- 验证订单状态为DELIVERED
- 设置订单状态为RECONCILED
- 返回订单信息

**权限要求**：
- 需要FINANCE角色

---

##### 关闭销售订单

**接口名称**：`closeSalesOrder`  
**HTTP方法**：POST  
**路径**：`/api/sd/sales-orders/{order_number}/close`

**服务操作规范**：
- 验证订单状态为RECONCILED
- 设置订单状态为CLOSED
- 关闭关联的所有生产订单
- 同步其他相关状态
- 返回订单信息

**权限要求**：
- 需要SALES或FINANCE角色

**服务依赖**：
- **PPService**：关闭关联的生产订单

---

#### 5.2.4 本厂编号映射服务

**服务名称**：`FactoryProductMappingService`  
**服务标识**：`sd.factory_product_mapping`

##### 创建本厂编号映射

**接口名称**：`createFactoryProductMapping`  
**HTTP方法**：POST  
**路径**：`/api/sd/factory-product-mappings`

**服务操作规范**：
- 验证客户存在
- 验证物料存在且状态为ACTIVE
- 如果提供了`production_version_id`，验证生产版本存在且状态为ACTIVE
- 如果`is_default=True`，将同一客户同一本厂编号的其他映射设置为非默认
- 创建映射记录
- 返回映射信息

**权限要求**：
- 需要SALES或ENGINEER角色

---

##### 获取本厂编号映射

**接口名称**：`getFactoryProductMapping`  
**HTTP方法**：GET  
**路径**：`/api/sd/factory-product-mappings/{customer_id}/{product_number}`

**服务操作规范**：
- 根据客户ID和本厂编号查找默认映射
- 验证映射在有效期内（`effective_date <= now <= expiry_date`）
- 返回映射信息

**错误处理**：
- `404 NOT_FOUND`：映射不存在或已过期

---

### 5.3 服务依赖

- **MMService**：验证物料存在
- **ENGService**：验证生产版本存在
- **WorkflowService**：审批流程管理

---

## 六、工程管理服务（ENG Service）

### 6.1 服务标识

- **服务名称**：ENGService
- **服务标识**：`eng`
- **基础路径**：`/api/eng`

### 6.2 服务接口

#### 6.2.1 BOM管理服务

**服务名称**：`BOMService`  
**服务标识**：`eng.bom`

##### 创建BOM

**接口名称**：`createBOM`  
**HTTP方法**：POST  
**路径**：`/api/eng/boms`

**服务操作规范**：
- 验证父物料存在
- 如果未提供`bom_number`，自动生成
- 验证BOM明细列表不为空
- 如果未提供`line_number`，自动生成（10, 20, 30...）
- 创建BOM主记录
- 创建BOM明细记录
- 设置初始状态为NEW
- 返回BOM信息

**权限要求**：
- 需要ENGINEER角色

**服务依赖**：
- **MMService**：验证物料存在

---

##### 获取BOM详情

**接口名称**：`getBOM`  
**HTTP方法**：GET  
**路径**：`/api/eng/boms/{bom_number}`

**服务操作规范**：
- 查询BOM主记录
- 查询BOM明细列表（按`line_number`排序）
- 返回完整的BOM信息

**错误处理**：
- `404 NOT_FOUND`：BOM不存在

---

##### 更新BOM

**接口名称**：`updateBOM`  
**HTTP方法**：PUT  
**路径**：`/api/eng/boms/{bom_number}`

**服务操作规范**：
- 验证BOM存在
- 验证BOM状态允许修改（NEW或REVIEWING）
- 更新BOM主记录
- 删除旧的BOM明细
- 创建新的BOM明细
- 返回更新后的BOM信息

**权限要求**：
- 需要ENGINEER角色

---

#### 6.2.2 工艺路线管理服务

**服务名称**：`RoutingService`  
**服务标识**：`eng.routing`

##### 创建工艺路线

**接口名称**：`createRouting`  
**HTTP方法**：POST  
**路径**：`/api/eng/routings`

**服务操作规范**：
- 验证物料存在
- 如果未提供`routing_id`，自动生成
- 验证工序列表不为空
- 验证工序号唯一性
- 创建工艺路线主记录
- 创建工序记录（按`operation_no`排序）
- 设置初始状态为DRAFT
- 返回工艺路线信息

**权限要求**：
- 需要ENGINEER角色

**服务依赖**：
- **MMService**：验证物料存在
- **PPService**：验证工作中心存在

---

##### 获取工艺路线详情

**接口名称**：`getRouting`  
**HTTP方法**：GET  
**路径**：`/api/eng/routings/{routing_id}`

**服务操作规范**：
- 查询工艺路线主记录
- 查询工序列表（按`operation_no`排序）
- 返回完整的工艺路线信息

**错误处理**：
- `404 NOT_FOUND`：工艺路线不存在

---

##### 获取工艺路线工序列表

**接口名称**：`getRoutingOperations`  
**HTTP方法**：GET  
**路径**：`/api/eng/routings/{routing_id}/operations`

**服务操作规范**：
- 查询工艺路线的所有工序
- 按`operation_no`排序
- 返回工序列表

---

##### 更新工艺路线

**接口名称**：`updateRouting`  
**HTTP方法**：PUT  
**路径**：`/api/eng/routings/{routing_id}`

**服务操作规范**：
- 验证工艺路线存在
- 验证工艺路线状态允许修改（DRAFT）
- 更新工艺路线主记录
- 删除旧的工序记录
- 创建新的工序记录
- 返回更新后的工艺路线信息

**权限要求**：
- 需要ENGINEER角色

---

#### 6.2.3 MI管理服务

**服务名称**：`MIService`  
**服务标识**：`eng.mi`

##### 创建MI

**接口名称**：`createMI`  
**HTTP方法**：POST  
**路径**：`/api/eng/mis`

**服务操作规范**：
- 验证物料存在
- 如果未提供`mi_number`，自动生成
- 如果提供了`routing_id`：
  - 查询工艺路线的所有工序
  - 基于工序自动生成MI指令集草稿
  - 每个工序对应一个指令项
- 将指令集列表序列化为JSON存储到`content`字段
- 创建MI记录
- 设置初始状态为DRAFT
- 返回MI信息

**权限要求**：
- 需要ENGINEER角色

**服务依赖**：
- **MMService**：验证物料存在
- **RoutingService**：获取工艺路线工序（如果提供了routing_id）

---

##### 获取MI详情

**接口名称**：`getMI`  
**HTTP方法**：GET  
**路径**：`/api/eng/mis/{mi_number}`

**服务操作规范**：
- 查询MI主记录
- 从`content`字段解析指令集列表
- 返回完整的MI信息（包含指令集列表）

**错误处理**：
- `404 NOT_FOUND`：MI不存在

---

##### 更新MI

**接口名称**：`updateMI`  
**HTTP方法**：PUT  
**路径**：`/api/eng/mis/{mi_number}`

**服务操作规范**：
- 验证MI存在
- 验证MI状态允许修改（DRAFT或REVIEWING）
- 将指令集列表序列化为JSON存储到`content`字段
- 更新MI记录
- 返回更新后的MI信息

**权限要求**：
- 需要ENGINEER角色

---

##### 提交MI审批

**接口名称**：`submitMI`  
**HTTP方法**：POST  
**路径**：`/api/eng/mis/{mi_number}/submit`

**服务操作规范**：
- 验证MI状态为DRAFT
- 设置状态为REVIEWING
- 返回提交结果

**权限要求**：
- 需要ENGINEER角色

---

##### 审批MI

**接口名称**：`approveMI`  
**HTTP方法**：POST  
**路径**：`/api/eng/mis/{mi_number}/approve`

**服务操作规范**：
- 验证MI状态为REVIEWING
- 设置状态为APPROVED
- 返回审批结果

**权限要求**：
- 需要ENGINEER角色

---

##### 拒绝MI

**接口名称**：`rejectMI`  
**HTTP方法**：POST  
**路径**：`/api/eng/mis/{mi_number}/reject`

**服务操作规范**：
- 验证MI状态为REVIEWING
- 设置状态为DRAFT（允许修改后重新提交）
- 返回拒绝结果

**权限要求**：
- 需要ENGINEER角色

---

#### 6.2.4 生产版本管理服务

**服务名称**：`ProductionVersionService`  
**服务标识**：`eng.production_version`

##### 创建生产版本

**接口名称**：`createProductionVersion`  
**HTTP方法**：POST  
**路径**：`/api/eng/production-versions`

**服务操作规范**：
- 验证物料存在
- 验证BOM存在且状态为RELEASED
- 验证工艺路线存在且状态为RELEASED
- 如果提供了`mi_number`，验证MI存在且状态为RELEASED
- 如果未提供`production_version_id`，自动生成
- 创建生产版本记录
- 设置初始状态为ACTIVE
- 返回生产版本信息

**权限要求**：
- 需要ENGINEER角色

**服务依赖**：
- **MMService**：验证物料存在
- **BOMService**：验证BOM存在
- **RoutingService**：验证工艺路线存在
- **MIService**：验证MI存在（如果提供）

---

##### 获取生产版本详情

**接口名称**：`getProductionVersion`  
**HTTP方法**：GET  
**路径**：`/api/eng/production-versions/{production_version_id}`

**服务操作规范**：
- 查询生产版本记录
- 返回生产版本信息

**错误处理**：
- `404 NOT_FOUND`：生产版本不存在

---

##### 更新生产版本

**接口名称**：`updateProductionVersion`  
**HTTP方法**：PUT  
**路径**：`/api/eng/production-versions/{production_version_id}`

**服务操作规范**：
- 验证生产版本存在
- 验证生产版本状态为ACTIVE
- 如果更新了BOM或工艺路线，验证新的BOM/工艺路线存在且状态为RELEASED
- 如果更新了MI，验证新的MI存在且状态为RELEASED
- 更新生产版本记录
- 返回更新后的生产版本信息

**权限要求**：
- 需要ENGINEER角色

---

##### 发布生产版本

**接口名称**：`releaseProductionVersion`  
**HTTP方法**：POST  
**路径**：`/api/eng/production-versions/{production_version_id}/release`

**请求契约**：
```yaml
ReleaseProductionVersionRequest:
  type: object
  required:
    - mi_number
  properties:
    mi_number:
      type: string
      description: MI编号（发布时必选）
```

**服务操作规范**：
- 验证生产版本存在
- 验证MI存在且状态为RELEASED
- 关联MI到生产版本
- 返回生产版本信息

**权限要求**：
- 需要ENGINEER角色

**错误处理**：
- `400 BAD_REQUEST`：MI未关联或状态不是RELEASED

---

### 6.3 服务依赖

- **MMService**：验证物料存在
- **PPService**：验证工作中心存在

---

## 七、生产计划与控制服务（PP Service）

### 7.1 服务标识

- **服务名称**：PPService
- **服务标识**：`pp`
- **基础路径**：`/api/pp`

### 7.2 服务接口

#### 7.2.1 工作中心管理服务

**服务名称**：`WorkCenterService`  
**服务标识**：`pp.work_center`

##### 创建工作中心

**接口名称**：`createWorkCenter`  
**HTTP方法**：POST  
**路径**：`/api/pp/work-centers`

**服务操作规范**：
- 验证工作中心ID唯一性
- 将作业类型列表和技术属性列表序列化为JSON存储
- 创建工作中心记录
- 设置初始状态为ACTIVE
- 返回工作中心信息

**权限要求**：
- 需要ENGINEER角色

---

##### 获取工作中心详情

**接口名称**：`getWorkCenter`  
**HTTP方法**：GET  
**路径**：`/api/pp/work-centers/{work_center_id}`

**服务操作规范**：
- 查询工作中心记录
- 从JSON字段解析作业类型列表和技术属性列表
- 返回完整的工作中心信息

**错误处理**：
- `404 NOT_FOUND`：工作中心不存在

---

#### 7.2.2 生产订单管理服务

**服务名称**：`ProductionOrderService`  
**服务标识**：`pp.production_order`

##### 创建生产订单

**接口名称**：`createProductionOrder`  
**HTTP方法**：POST  
**路径**：`/api/pp/production-orders`

**服务操作规范**：
1. **验证销售订单**：
   - 验证销售订单存在且状态为APPROVED

2. **获取生产版本信息**：
   - 优先使用销售订单的`production_version_id`
   - 如果销售订单没有，使用请求中的`production_version_id`
   - 验证生产版本存在且状态为ACTIVE
   - 从生产版本获取`material_code`、`bom_number`、`routing_id`

3. **单位转换计算**：
   - 从销售订单获取`sales_quantity`、`sales_unit`、`conversion_factor`
   - 计算`production_quantity = sales_quantity / conversion_factor`
   - 从物料主数据获取`production_unit`

4. **创建订单**：
   - 自动生成订单号（PO-YYYYMMDD-XXXX）
   - 设置初始状态为DRAFT
   - 创建生产订单记录
   - 返回订单信息

**权限要求**：
- 需要PLANNER或PRODUCTION角色

**服务依赖**：
- **SDService**：获取销售订单信息
- **ENGService**：获取生产版本信息
- **MMService**：获取物料信息

---

##### 下达生产订单

**接口名称**：`releaseProductionOrder`  
**HTTP方法**：POST  
**路径**：`/api/pp/production-orders/{order_number}/release`

**服务操作规范**：
- 验证订单状态为DRAFT
- 设置订单状态为RELEASED
- 返回订单信息

**权限要求**：
- 需要PLANNER角色

---

##### 开始生产订单

**接口名称**：`startProductionOrder`  
**HTTP方法**：POST  
**路径**：`/api/pp/production-orders/{order_number}/start`

**服务操作规范**：
- 验证订单状态为RELEASED
- 设置订单状态为IN_PRODUCTION
- 设置`actual_start_date = now()`
- 调用`sync_sales_order_status`同步销售订单状态
- 返回订单信息

**权限要求**：
- 需要PRODUCTION角色

**服务依赖**：
- **SDService**：同步销售订单状态

---

##### 完成生产订单

**接口名称**：`completeProductionOrder`  
**HTTP方法**：POST  
**路径**：`/api/pp/production-orders/{order_number}/complete`

**服务操作规范**：
- 验证订单状态为IN_PRODUCTION
- 设置订单状态为COMPLETED
- 设置`actual_finish_date = now()`
- 调用`sync_sales_order_status`同步销售订单状态
- 返回订单信息

**权限要求**：
- 需要PRODUCTION角色

**服务依赖**：
- **SDService**：同步销售订单状态

---

##### 关闭生产订单

**接口名称**：`closeProductionOrder`  
**HTTP方法**：POST  
**路径**：`/api/pp/production-orders/{order_number}/close`

**服务操作规范**：
- 验证订单状态为COMPLETED
- 设置订单状态为CLOSED
- 调用`sync_sales_order_status`同步销售订单状态
- 返回订单信息

**权限要求**：
- 需要PLANNER角色

**服务依赖**：
- **SDService**：同步销售订单状态

---

##### 获取生产订单工序列表

**接口名称**：`getProductionOrderOperations`  
**HTTP方法**：GET  
**路径**：`/api/pp/production-orders/{order_number}/operations`

**服务操作规范**：
- 查询生产订单关联的生产版本
- 从生产版本获取工艺路线ID
- 查询工艺路线的所有工序
- 返回工序列表

**服务依赖**：
- **ENGService**：获取工艺路线工序

---

#### 7.2.3 工序报工管理服务

**服务名称**：`OperationReportService`  
**服务标识**：`pp.operation_report`

##### 创建工序报工

**接口名称**：`createOperationReport`  
**HTTP方法**：POST  
**路径**：`/api/pp/operation-reports`

**服务操作规范**：
- 验证生产订单存在且状态为RELEASED或IN_PRODUCTION
- 验证工序存在且属于该生产订单的工艺路线
- 验证工作中心存在
- 自动生成报工单号（OR-YYYYMMDD-XXXX）
- 创建工序报工记录
- 设置初始状态为PENDING
- 返回报工信息

**权限要求**：
- 需要PRODUCTION角色

**服务依赖**：
- **ProductionOrderService**：验证生产订单
- **RoutingService**：验证工序
- **WorkCenterService**：验证工作中心

---

##### 获取工序报工列表

**接口名称**：`listOperationReports`  
**HTTP方法**：GET  
**路径**：`/api/pp/operation-reports`

**服务操作规范**：
- 支持分页查询
- 支持按生产订单号过滤
- 支持按状态过滤
- 返回报工列表

---

##### 获取生产进度

**接口名称**：`getProductionProgress`  
**HTTP方法**：GET  
**路径**：`/api/pp/production-orders/{order_number}/progress`

**服务操作规范**：
- 查询生产订单关联的工艺路线
- 查询所有工序的报工记录
- 计算每个工序的完成进度
- 计算整体生产进度
- 返回进度信息（包含工序列表、完成状态、报工记录）

**响应契约**：
```yaml
ProductionProgressResponse:
  type: object
  properties:
    order_number:
      type: string
    overall_progress:
      type: number
      format: float
      description: 整体进度百分比（0-100）
    total_operations:
      type: integer
    completed_operations:
      type: integer
    operations:
      type: array
      items:
        type: object
        properties:
          operation_no:
            type: integer
          operation_name:
            type: string
          work_center_id:
            type: string
          status:
            type: string
            enum: [PENDING, IN_PROGRESS, COMPLETED]
          reports:
            type: array
            items:
              $ref: '#/components/schemas/OperationReportResponse'
```

**服务依赖**：
- **RoutingService**：获取工艺路线工序
- **OperationReportService**：获取报工记录

---

### 7.3 服务依赖

- **SDService**：获取销售订单信息、同步销售订单状态
- **ENGService**：获取生产版本、工艺路线信息
- **MMService**：获取物料信息

---

## 八、物料管理服务（MM Service）

### 8.1 服务标识

- **服务名称**：MMService
- **服务标识**：`mm`
- **基础路径**：`/api/mm`

### 8.2 服务接口

#### 8.2.1 物料主数据管理服务

**服务名称**：`MaterialService`  
**服务标识**：`mm.material`

##### 创建物料

**接口名称**：`createMaterial`  
**HTTP方法**：POST  
**路径**：`/api/mm/materials`

**请求契约**：
```yaml
CreateMaterialRequest:
  type: object
  required:
    - material_code
    - material_name
    - category
    - unit
  properties:
    material_code:
      type: string
      maxLength: 50
    material_name:
      type: string
      maxLength: 200
    category:
      type: string
      description: 物料分类（原材料/基材、辅材、化工材料、成品等）
    specification:
      type: string
    unit:
      type: string
      description: 计量单位（PCS、张、卷、公斤等）
    brand:
      type: string
    min_package:
      type: string
    current_stock:
      type: number
      format: float
      default: 0
    safety_stock:
      type: number
      format: float
      default: 0
    description:
      type: string
    material_type:
      type: string
      enum: [FG, RAW, SEMI]
      description: FG=成品，RAW=原材料，SEMI=半成品
    base_unit:
      type: string
      description: 基础单位（通常为PCS）
    production_unit:
      type: string
      description: 生产单位
    conversion_factor:
      type: number
      format: float
      description: 单位转换系数（base_unit = production_unit × conversion_factor）
    # PCB相关属性
    layer_count:
      type: integer
    board_thickness:
      type: number
      format: float
    thickness_tolerance:
      type: string
    copper_weight:
      type: string
    material_grade:
      type: string
    surface_finish:
      type: string
    solder_mask_color:
      type: string
    silkscreen_color:
      type: string
    impedance_control:
      type: boolean
    min_line_space:
      type: number
      format: float
    min_hole_size:
      type: number
      format: float
    unit_length:
      type: number
      format: float
    unit_width:
      type: number
      format: float
    panel_length:
      type: number
      format: float
    panel_width:
      type: number
      format: float
    units_per_panel:
      type: integer
    # 采购相关属性
    procurement_type:
      type: string
      enum: [INTERNAL, EXTERNAL]
    mrp_controller:
      type: string
    lead_time_days:
      type: integer
    max_lot_size:
      type: integer
    min_order_quantity:
      type: integer
    order_multiple:
      type: integer
    abc_class:
      type: string
      enum: [A, B, C]
    shelf_life_days:
      type: integer
    default_location:
      type: string
    storage_condition:
      type: string
    batch_tracking:
      type: boolean
    valuation_method:
      type: string
      enum: [FIFO, LIFO, AVERAGE, STANDARD]
    standard_price:
      type: number
      format: float
    currency:
      type: string
      default: CNY
```

**服务操作规范**：
- 验证物料编码唯一性
- 设置初始状态为DRAFT
- 创建物料记录
- 返回物料信息

**权限要求**：
- 需要ENGINEER或WAREHOUSE角色

**错误处理**：
- `400 BAD_REQUEST`：物料编码已存在

---

##### 获取物料列表

**接口名称**：`listMaterials`  
**HTTP方法**：GET  
**路径**：`/api/mm/materials`

**请求契约**：
```yaml
ListMaterialsRequest:
  type: object
  properties:
    skip:
      type: integer
      default: 0
    limit:
      type: integer
      default: 100
    category:
      type: string
      description: 物料分类过滤
    material_type:
      type: string
      description: 物料类型过滤（FG/RAW/SEMI）
    status:
      type: string
      description: 状态过滤（ACTIVE/OBSOLETE/DRAFT）
    search:
      type: string
      description: 搜索关键词（物料编码、物料名称）
```

**响应契约**：
```yaml
ListMaterialsResponse:
  type: array
  items:
    $ref: '#/components/schemas/MaterialResponse'
```

**服务操作规范**：
- 支持分页查询
- 支持按分类、类型、状态过滤
- 支持关键词搜索（物料编码、物料名称）
- 返回物料列表

---

##### 获取物料详情

**接口名称**：`getMaterial`  
**HTTP方法**：GET  
**路径**：`/api/mm/materials/{material_code}`

**服务操作规范**：
- 查询物料记录
- 返回完整的物料信息

**错误处理**：
- `404 NOT_FOUND`：物料不存在

---

##### 更新物料

**接口名称**：`updateMaterial`  
**HTTP方法**：PUT  
**路径**：`/api/mm/materials/{material_code}`

**服务操作规范**：
- 验证物料存在
- 验证物料状态允许修改（DRAFT或ACTIVE）
- 更新物料记录
- 返回更新后的物料信息

**权限要求**：
- 需要ENGINEER或WAREHOUSE角色

---

##### 激活物料

**接口名称**：`activateMaterial`  
**HTTP方法**：POST  
**路径**：`/api/mm/materials/{material_code}/activate`

**服务操作规范**：
- 验证物料存在且状态为DRAFT
- 设置状态为ACTIVE
- 返回物料信息

**权限要求**：
- 需要ENGINEER或WAREHOUSE角色

---

##### 停用物料

**接口名称**：`deactivateMaterial`  
**HTTP方法**：POST  
**路径**：`/api/mm/materials/{material_code}/deactivate`

**服务操作规范**：
- 验证物料存在且状态为ACTIVE
- 设置状态为OBSOLETE
- 返回物料信息

**权限要求**：
- 需要ENGINEER或WAREHOUSE角色

---

#### 8.2.2 库存管理服务

**服务名称**：`InventoryService`  
**服务标识**：`mm.inventory`

##### 获取库存信息

**接口名称**：`getInventory`  
**HTTP方法**：GET  
**路径**：`/api/mm/materials/{material_code}/inventory`

**服务操作规范**：
- 查询物料的当前库存
- 查询安全库存
- 计算可用库存（当前库存 - 安全库存）
- 返回库存信息

**响应契约**：
```yaml
InventoryResponse:
  type: object
  properties:
    material_code:
      type: string
    current_stock:
      type: number
      format: float
    safety_stock:
      type: number
      format: float
    available_stock:
      type: number
      format: float
    unit:
      type: string
```

---

##### 更新库存

**接口名称**：`updateInventory`  
**HTTP方法**：PUT  
**路径**：`/api/mm/materials/{material_code}/inventory`

**请求契约**：
```yaml
UpdateInventoryRequest:
  type: object
  required:
    - quantity
    - transaction_type
  properties:
    quantity:
      type: number
      format: float
      description: 数量（正数为入库，负数为出库）
    transaction_type:
      type: string
      enum: [IN, OUT, ADJUSTMENT]
      description: 事务类型（入库/出库/调整）
    reference_number:
      type: string
      description: 参考单号（如生产订单号、领料单号）
    remarks:
      type: string
```

**服务操作规范**：
- 验证物料存在
- 更新当前库存（current_stock += quantity）
- 创建库存事务记录（MaterialTransaction）
- 返回更新后的库存信息

**权限要求**：
- 需要WAREHOUSE角色

**错误处理**：
- `400 BAD_REQUEST`：出库数量超过可用库存

---

##### 获取库存事务记录

**接口名称**：`listInventoryTransactions`  
**HTTP方法**：GET  
**路径**：`/api/mm/materials/{material_code}/transactions`

**服务操作规范**：
- 支持分页查询
- 支持按事务类型过滤
- 支持按日期范围过滤
- 返回库存事务记录列表

---

#### 8.2.3 领料管理服务

**服务名称**：`MaterialIssueService`  
**服务标识**：`mm.material_issue`

##### 创建领料单

**接口名称**：`createMaterialIssue`  
**HTTP方法**：POST  
**路径**：`/api/mm/material-issues`

**请求契约**：
```yaml
CreateMaterialIssueRequest:
  type: object
  required:
    - production_order_number
    - material_code
    - quantity
  properties:
    production_order_number:
      type: string
      description: 生产订单号
    material_code:
      type: string
    quantity:
      type: number
      format: float
    remarks:
      type: string
```

**服务操作规范**：
- 验证生产订单存在且状态为RELEASED或IN_PRODUCTION
- 验证物料存在且状态为ACTIVE
- 验证库存充足（当前库存 >= quantity）
- 自动生成领料单号（MI-YYYYMMDD-XXXX）
- 创建领料单记录
- 设置初始状态为PENDING
- 返回领料单信息

**权限要求**：
- 需要PRODUCTION或WAREHOUSE角色

**服务依赖**：
- **PPService**：验证生产订单
- **MaterialService**：验证物料和库存

**错误处理**：
- `400 BAD_REQUEST`：库存不足或生产订单状态无效

---

##### 审批领料单

**接口名称**：`approveMaterialIssue`  
**HTTP方法**：POST  
**路径**：`/api/mm/material-issues/{issue_number}/approve`

**服务操作规范**：
- 验证领料单存在且状态为PENDING
- 更新库存（出库）
- 创建库存事务记录
- 设置领料单状态为APPROVED
- 返回领料单信息

**权限要求**：
- 需要WAREHOUSE角色

---

##### 拒绝领料单

**接口名称**：`rejectMaterialIssue`  
**HTTP方法**：POST  
**路径**：`/api/mm/material-issues/{issue_number}/reject`

**服务操作规范**：
- 验证领料单存在且状态为PENDING
- 设置领料单状态为REJECTED
- 返回领料单信息

**权限要求**：
- 需要WAREHOUSE角色

---

##### 获取领料单列表

**接口名称**：`listMaterialIssues`  
**HTTP方法**：GET  
**路径**：`/api/mm/material-issues`

**服务操作规范**：
- 支持分页查询
- 支持按生产订单号过滤
- 支持按状态过滤
- 返回领料单列表

---

### 8.3 服务依赖

- **PPService**：验证生产订单
- **Database**：物料数据持久化

---

## 九、工作流服务（Workflow Service）

### 9.1 服务标识

- **服务名称**：WorkflowService
- **服务标识**：`workflow`
- **基础路径**：`/api/workflow`

### 9.2 服务接口

#### 9.2.1 工作流定义管理服务

**服务名称**：`WorkflowDefinitionService`  
**服务标识**：`workflow.definition`

##### 创建工作流定义

**接口名称**：`createWorkflow`  
**HTTP方法**：POST  
**路径**：`/api/workflow/workflows`

**请求契约**：
```yaml
CreateWorkflowRequest:
  type: object
  required:
    - workflow_id
    - workflow_name
    - nodes
  properties:
    workflow_id:
      type: string
      description: 工作流ID（如QUOTATION_APPROVAL、SALES_ORDER_REVIEW）
    workflow_name:
      type: string
    description:
      type: string
    nodes:
      type: array
      items:
        type: object
        required:
          - node_id
          - node_name
          - node_type
          - order
        properties:
          node_id:
            type: string
          node_name:
            type: string
          node_type:
            type: string
            enum: [START, APPROVAL, END]
          approver_role:
            type: string
            description: 审批人角色（APPROVAL节点必填）
          order:
            type: integer
            description: 节点顺序
          config:
            type: object
            description: 节点配置（JSON对象）
```

**服务操作规范**：
- 验证工作流ID唯一性
- 验证节点顺序连续且唯一
- 验证START和END节点存在且唯一
- 创建工作流定义记录
- 创建节点记录
- 返回工作流定义信息

**权限要求**：
- 需要ADMIN角色

---

##### 获取工作流定义列表

**接口名称**：`listWorkflows`  
**HTTP方法**：GET  
**路径**：`/api/workflow/workflows`

**服务操作规范**：
- 返回所有工作流定义列表（包含节点信息）

---

##### 获取工作流定义详情

**接口名称**：`getWorkflow`  
**HTTP方法**：GET  
**路径**：`/api/workflow/workflows/{workflow_id}`

**服务操作规范**：
- 查询工作流定义记录
- 查询关联的节点列表（按order排序）
- 返回完整的工作流定义信息

**错误处理**：
- `404 NOT_FOUND`：工作流定义不存在

---

#### 9.2.2 工作流实例管理服务

**服务名称**：`WorkflowInstanceService`  
**服务标识**：`workflow.instance`

##### 启动工作流实例

**接口名称**：`startWorkflowInstance`  
**HTTP方法**：POST  
**路径**：`/api/workflow/instances`

**请求契约**：
```yaml
StartWorkflowInstanceRequest:
  type: object
  required:
    - workflow_id
    - business_id
    - business_type
  properties:
    workflow_id:
      type: string
      description: 工作流定义ID
    business_id:
      type: string
      description: 业务对象ID（如报价单号、销售订单号）
    business_type:
      type: string
      description: 业务类型（如QUOTATION、SALES_ORDER）
```

**服务操作规范**：
- 验证工作流定义存在
- 验证业务对象ID唯一性（同一业务对象只能有一个进行中的实例）
- 自动生成实例ID（WFI-YYYYMMDD-XXXX）
- 创建工作流实例记录
- 创建第一个节点实例（START节点后的第一个APPROVAL节点）
- 设置实例状态为PENDING
- 设置当前节点ID
- 返回工作流实例信息

**权限要求**：
- 由业务服务调用，不需要直接权限

**错误处理**：
- `400 BAD_REQUEST`：工作流定义不存在或业务对象已有进行中的实例

---

##### 获取工作流实例状态

**接口名称**：`getWorkflowInstanceStatus`  
**HTTP方法**：GET  
**路径**：`/api/workflow/instances/{instance_id}`

**服务操作规范**：
- 查询工作流实例记录
- 查询所有节点实例（按order排序）
- 检查当前用户是否有权限审批当前节点
- 返回工作流实例状态信息

**响应契约**：
```yaml
WorkflowInstanceStatusResponse:
  type: object
  properties:
    instance_id:
      type: string
    workflow_id:
      type: string
    business_id:
      type: string
    business_type:
      type: string
    status:
      type: string
      enum: [PENDING, APPROVED, REJECTED, CANCELLED, COMPLETED]
    current_node_id:
      type: string
    current_node_name:
      type: string
    can_approve:
      type: boolean
      description: 当前用户是否可以审批
    nodes:
      type: array
      items:
        type: object
        properties:
          node_id:
            type: string
          node_name:
            type: string
          status:
            type: string
            enum: [PENDING, APPROVED, REJECTED]
          approver:
            type: string
          approved_at:
            type: string
            format: date-time
          comment:
            type: string
```

---

##### 审批工作流节点

**接口名称**：`approveWorkflowNode`  
**HTTP方法**：POST  
**路径**：`/api/workflow/instances/{instance_id}/approve`

**请求契约**：
```yaml
ApproveWorkflowNodeRequest:
  type: object
  properties:
    comment:
      type: string
      description: 审批意见
```

**服务操作规范**：
- 验证工作流实例存在且状态为PENDING
- 验证当前用户有权限审批当前节点（角色匹配）
- 更新当前节点实例状态为APPROVED
- 记录审批人、审批时间、审批意见
- 移动到下一个节点：
  - 如果还有下一个APPROVAL节点，创建节点实例并设置为PENDING
  - 如果是最后一个节点，设置实例状态为COMPLETED
- 返回工作流实例信息

**权限要求**：
- 需要相应审批节点的角色

**错误处理**：
- `403 FORBIDDEN`：当前用户没有权限审批此节点
- `400 BAD_REQUEST`：工作流实例状态无效

---

##### 拒绝工作流节点

**接口名称**：`rejectWorkflowNode`  
**HTTP方法**：POST  
**路径**：`/api/workflow/instances/{instance_id}/reject`

**请求契约**：
```yaml
RejectWorkflowNodeRequest:
  type: object
  required:
    - reason
  properties:
    reason:
      type: string
      description: 拒绝原因
```

**服务操作规范**：
- 验证工作流实例存在且状态为PENDING
- 验证当前用户有权限审批当前节点
- 更新当前节点实例状态为REJECTED
- 记录拒绝人、拒绝时间、拒绝原因
- 设置实例状态为REJECTED
- 返回工作流实例信息

**权限要求**：
- 需要相应审批节点的角色

**错误处理**：
- `403 FORBIDDEN`：当前用户没有权限审批此节点

---

##### 取消工作流实例

**接口名称**：`cancelWorkflowInstance`  
**HTTP方法**：POST  
**路径**：`/api/workflow/instances/{instance_id}/cancel`

**服务操作规范**：
- 验证工作流实例存在且状态为PENDING
- 设置实例状态为CANCELLED
- 返回工作流实例信息

**权限要求**：
- 需要ADMIN角色或业务对象创建者

---

##### 获取工作流实例历史

**接口名称**：`getWorkflowInstanceHistory`  
**HTTP方法**：GET  
**路径**：`/api/workflow/instances/{instance_id}/history`

**服务操作规范**：
- 查询工作流实例的所有节点实例
- 按时间顺序排序
- 返回审批历史记录

---

### 9.3 服务依赖

- **Database**：工作流数据持久化
- **UserService**：验证用户角色权限

---

## 十、服务依赖关系图

### 10.1 服务依赖矩阵

| 服务 | 依赖的服务 |
|------|-----------|
| AuthService | UserService |
| UserService | Database |
| SDService | MMService, ENGService, WorkflowService |
| ENGService | MMService, PPService |
| PPService | SDService, ENGService, MMService |
| MMService | PPService, Database |
| WorkflowService | UserService, Database |

### 10.2 服务依赖关系说明

1. **认证服务（AuthService）**
   - 依赖UserService查询用户信息进行认证

2. **用户管理服务（UserService）**
   - 直接访问数据库进行用户数据持久化

3. **销售与分销服务（SDService）**
   - 依赖MMService验证物料存在
   - 依赖ENGService验证生产版本存在
   - 依赖WorkflowService进行审批流程管理

4. **工程管理服务（ENGService）**
   - 依赖MMService验证物料存在
   - 依赖PPService验证工作中心存在

5. **生产计划与控制服务（PPService）**
   - 依赖SDService获取销售订单信息、同步销售订单状态
   - 依赖ENGService获取生产版本、工艺路线信息
   - 依赖MMService获取物料信息

6. **物料管理服务（MMService）**
   - 依赖PPService验证生产订单
   - 直接访问数据库进行物料数据持久化

7. **工作流服务（WorkflowService）**
   - 依赖UserService验证用户角色权限
   - 直接访问数据库进行工作流数据持久化

### 10.3 服务调用流程图

```
┌─────────────┐
│  前端应用    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  API Gateway │
└──────┬──────┘
       │
   ┌───┴───┬──────────┬──────────┬──────────┐
   │       │          │          │          │
   ▼       ▼          ▼          ▼          ▼
┌────┐ ┌────┐    ┌────┐    ┌────┐    ┌────┐
│Auth│ │User│    │ SD │    │ENG │    │ PP │
└─┬──┘ └─┬──┘    └─┬──┘    └─┬──┘    └─┬──┘
  │      │         │         │         │
  │      │         │         │         │
  │      │    ┌────┴────┐    │         │
  │      │    │         │    │         │
  │      │    ▼         ▼    ▼         ▼
  │      │ ┌────┐   ┌────┐ ┌────┐   ┌────┐
  │      │ │ MM │   │Work│ │ MM │   │ SD │
  │      │ └────┘   │flow│ └────┘   └────┘
  │      │          └────┘
  │      │
  └──────┘
     │
     ▼
┌─────────────┐
│  Database   │
└─────────────┘
```

---

## 十一、服务契约规范

### 11.1 请求契约规范

#### 11.1.1 通用请求头

所有API请求必须包含以下请求头：

```yaml
Headers:
  Authorization:
    type: string
    description: Bearer Token（格式：Bearer {token}）
    required: true
  Content-Type:
    type: string
    default: application/json
  X-Request-ID:
    type: string
    description: 请求唯一标识（用于追踪和日志）
    required: false
```

#### 11.1.2 分页请求规范

所有列表查询接口支持分页，使用以下参数：

```yaml
PaginationRequest:
  type: object
  properties:
    skip:
      type: integer
      minimum: 0
      default: 0
      description: 跳过的记录数
    limit:
      type: integer
      minimum: 1
      maximum: 1000
      default: 100
      description: 返回的记录数
```

#### 11.1.3 排序请求规范

支持排序的接口使用以下参数：

```yaml
SortRequest:
  type: object
  properties:
    sort_by:
      type: string
      description: 排序字段
    sort_order:
      type: string
      enum: [ASC, DESC]
      default: ASC
      description: 排序方向
```

### 11.2 响应契约规范

#### 11.2.1 通用响应格式

所有API响应遵循统一格式：

```yaml
StandardResponse:
  type: object
  properties:
    code:
      type: integer
      description: 响应状态码（200表示成功）
    message:
      type: string
      description: 响应消息
    data:
      type: object
      description: 响应数据
    timestamp:
      type: string
      format: date-time
      description: 响应时间戳
    request_id:
      type: string
      description: 请求ID（用于追踪）
```

#### 11.2.2 分页响应格式

列表查询接口返回分页信息：

```yaml
PaginatedResponse:
  type: object
  properties:
    items:
      type: array
      description: 数据列表
    total:
      type: integer
      description: 总记录数
    skip:
      type: integer
      description: 跳过的记录数
    limit:
      type: integer
      description: 每页记录数
    has_more:
      type: boolean
      description: 是否有更多数据
```

#### 11.2.3 错误响应格式

错误响应遵循统一格式：

```yaml
ErrorResponse:
  type: object
  required:
    - code
    - message
  properties:
    code:
      type: integer
      description: HTTP状态码
    message:
      type: string
      description: 错误消息
    error_code:
      type: string
      description: 业务错误代码
    details:
      type: object
      description: 错误详情
    timestamp:
      type: string
      format: date-time
    request_id:
      type: string
```

### 11.3 数据格式规范

#### 11.3.1 日期时间格式

- **日期**：`YYYY-MM-DD`（如：2025-12-12）
- **日期时间**：`YYYY-MM-DDTHH:mm:ssZ`（ISO 8601格式，如：2025-12-12T10:30:00Z）
- **时间戳**：Unix时间戳（秒）

#### 11.3.2 金额格式

- 使用`number`类型，`format: float`
- 保留2位小数
- 货币代码使用ISO 4217标准（如：CNY、USD）

#### 11.3.3 编码规范

- 所有业务编码（如订单号、物料编码）使用字符串类型
- 编码格式遵循业务规则（如：SO-20251212-0001）
- 编码唯一性由服务保证

---

## 十二、错误处理规范

### 12.1 HTTP状态码规范

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功，无返回内容 |
| 400 | Bad Request | 请求参数错误、业务规则验证失败 |
| 401 | Unauthorized | 未认证或令牌无效 |
| 403 | Forbidden | 已认证但权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如唯一性约束违反） |
| 422 | Unprocessable Entity | 请求格式正确但语义错误 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 12.2 业务错误代码规范

业务错误代码采用分层结构：`{SERVICE}.{MODULE}.{ERROR}`

示例：
- `SD.CUSTOMER.DUPLICATE_ID`：客户ID重复
- `MM.MATERIAL.NOT_FOUND`：物料不存在
- `PP.ORDER.INVALID_STATUS`：订单状态无效
- `WORKFLOW.INSTANCE.NOT_FOUND`：工作流实例不存在

### 12.3 错误处理流程

1. **参数验证错误**：返回400 Bad Request，包含详细的验证错误信息
2. **业务规则错误**：返回400 Bad Request，包含业务错误代码和说明
3. **权限错误**：返回403 Forbidden，不暴露资源是否存在的信息
4. **资源不存在**：返回404 Not Found
5. **系统错误**：返回500 Internal Server Error，记录详细错误日志

### 12.4 错误响应示例

```json
{
  "code": 400,
  "message": "请求参数验证失败",
  "error_code": "SD.CUSTOMER.DUPLICATE_ID",
  "details": {
    "field": "customer_id",
    "value": "CUST001",
    "reason": "客户ID已存在"
  },
  "timestamp": "2025-12-12T10:30:00Z",
  "request_id": "req-1234567890"
}
```

---

## 十三、服务版本管理

### 13.1 版本号规范

采用语义化版本号：`MAJOR.MINOR.PATCH`

- **MAJOR**：不兼容的API变更
- **MINOR**：向后兼容的功能新增
- **PATCH**：向后兼容的问题修复

### 13.2 版本控制策略

1. **URL版本控制**：在路径中包含版本号
   - 示例：`/api/v1/sd/customers`
   - 当前版本：v1

2. **版本兼容性**：
   - 新版本必须向后兼容至少一个主版本
   - 废弃的API至少保留一个主版本周期

3. **版本公告**：
   - 重大版本变更提前30天公告
   - 提供迁移指南和兼容性说明

### 13.3 API废弃策略

1. **废弃标记**：在响应头中标记废弃的API
   ```
   Deprecation: true
   Sunset: 2026-12-12
   ```

2. **废弃周期**：
   - 标记为废弃后至少保留6个月
   - 在废弃期间提供替代方案

---

## 十四、服务安全规范

### 14.1 认证机制

1. **JWT令牌认证**：
   - 令牌有效期：24小时
   - 刷新令牌有效期：7天
   - 令牌包含：用户ID、角色、过期时间

2. **令牌刷新**：
   - 提供令牌刷新接口
   - 刷新时验证刷新令牌有效性

### 14.2 授权机制

1. **基于角色的访问控制（RBAC）**：
   - 每个接口定义所需角色
   - 用户必须拥有相应角色才能访问

2. **权限检查**：
   - 在API网关层进行统一权限验证
   - 服务层进行二次验证

### 14.3 数据安全

1. **敏感数据加密**：
   - 密码使用bcrypt加密存储
   - 传输使用HTTPS

2. **数据脱敏**：
   - 日志中不记录敏感信息（密码、令牌）
   - 响应中不返回敏感字段

3. **SQL注入防护**：
   - 使用参数化查询
   - 禁止直接拼接SQL

### 14.4 请求安全

1. **请求限流**：
   - 每个用户每分钟最多100次请求
   - 每个IP每分钟最多1000次请求

2. **请求验证**：
   - 验证请求来源
   - 验证请求签名（可选）

---

## 十五、服务性能要求

### 15.1 响应时间要求

| 操作类型 | 响应时间要求 |
|---------|------------|
| 查询操作 | < 500ms |
| 创建操作 | < 1000ms |
| 更新操作 | < 1000ms |
| 删除操作 | < 500ms |
| 批量操作 | < 5000ms |

### 15.2 并发性能要求

- **并发用户数**：支持至少1000个并发用户
- **TPS**：每秒至少处理500个事务
- **数据库连接池**：最小10个，最大100个连接

### 15.3 可用性要求

- **服务可用性**：99.9%（年度停机时间 < 8.76小时）
- **故障恢复时间**：< 30分钟
- **数据备份**：每日自动备份，保留30天

---

## 十六、服务监控和日志

### 16.1 监控指标

1. **服务健康指标**：
   - 服务可用性
   - 响应时间
   - 错误率

2. **业务指标**：
   - 接口调用次数
   - 业务操作统计
   - 数据量统计

3. **资源指标**：
   - CPU使用率
   - 内存使用率
   - 数据库连接数

### 16.2 日志规范

1. **日志级别**：
   - **DEBUG**：调试信息
   - **INFO**：一般信息（请求、响应）
   - **WARN**：警告信息
   - **ERROR**：错误信息
   - **FATAL**：严重错误

2. **日志格式**：
   ```
   [TIMESTAMP] [LEVEL] [SERVICE] [REQUEST_ID] [MESSAGE] [CONTEXT]
   ```

3. **日志内容**：
   - 记录所有API请求和响应
   - 记录业务操作关键步骤
   - 记录错误和异常信息
   - 不记录敏感信息（密码、令牌）

### 16.3 告警机制

1. **告警条件**：
   - 服务不可用
   - 错误率 > 5%
   - 响应时间 > 5秒
   - 数据库连接池耗尽

2. **告警通知**：
   - 发送邮件通知
   - 发送短信通知（严重告警）
   - 记录到告警系统

---

## 十七、服务测试规范

### 17.1 单元测试

- 每个服务方法必须有单元测试
- 测试覆盖率 > 80%
- 使用Mock对象隔离依赖

### 17.2 集成测试

- 测试服务之间的集成
- 测试数据库操作
- 测试工作流流程

### 17.3 API测试

- 使用OpenAPI规范生成测试用例
- 测试所有接口的正常流程和异常流程
- 测试权限控制

### 17.4 性能测试

- 进行压力测试和负载测试
- 验证性能指标是否满足要求
- 识别性能瓶颈

---

## 十八、服务部署规范

### 18.1 部署环境

1. **开发环境（DEV）**：
   - 用于开发和调试
   - 数据可以重置

2. **测试环境（TEST）**：
   - 用于功能测试和集成测试
   - 数据接近生产环境

3. **预生产环境（STAGING）**：
   - 用于生产前验证
   - 数据与生产环境一致

4. **生产环境（PROD）**：
   - 正式运行环境
   - 高可用性配置

### 18.2 部署流程

1. **代码提交**：提交到版本控制系统
2. **自动化构建**：CI/CD自动构建和测试
3. **部署到测试环境**：自动部署并运行测试
4. **部署到预生产环境**：手动审批后部署
5. **部署到生产环境**：手动审批后部署，支持回滚

### 18.3 配置管理

1. **环境变量**：使用环境变量管理配置
2. **配置中心**：使用配置中心管理动态配置
3. **密钥管理**：使用密钥管理服务存储敏感信息

---

## 十九、附录

### 19.1 术语表

| 术语 | 说明 |
|------|------|
| SOA | 面向服务的架构（Service-Oriented Architecture） |
| API Gateway | API网关，统一入口和路由 |
| JWT | JSON Web Token，用于认证的令牌 |
| RBAC | 基于角色的访问控制 |
| BOM | 物料清单（Bill of Materials） |
| MI | 制造指令（Manufacturing Instruction） |
| TPS | 每秒事务数（Transactions Per Second） |

### 19.2 参考文档

- [OpenAPI 3.0规范](https://swagger.io/specification/)
- [RESTful API设计指南](https://restfulapi.net/)
- [JWT规范](https://jwt.io/)
- [某某ERP系统 - API模型（OpenAPI 3）](./某某ERP系统%20-%20API模型（OpenAPI%203）.md)
- [某某ERP系统 - 领域模型（Domain Model）](./某某ERP系统%20-%20领域模型（Domain%20Model）.md)

### 19.3 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| v1.0 | 2025-12-12 | 初始版本 | - |
| v1.1 | 2025-12-12 | 添加服务依赖关系图 | - |
| v1.2 | 2025-12-12 | 完善服务接口规范 | - |
| v1.3 | 2025-12-12 | 添加服务契约、错误处理、监控等规范 | - |
| v1.4 | 2025-12-12 | 添加服务编排、服务示例、服务治理等内容 | - |

---

## 二十、服务编排和组合场景

### 20.1 服务编排概述

服务编排是指将多个服务组合起来完成复杂的业务流程。在某某ERP系统中，许多业务场景需要跨多个服务协作完成。

### 20.2 典型服务编排场景

#### 20.2.1 销售订单创建完整流程

**场景描述**：从客户询价到创建销售订单的完整流程

**服务调用序列**：
```
1. SDService.createCustomer (创建客户)
   ↓
2. SDService.createQuotation (创建报价单)
   ↓
3. SDService.submitQuotation (提交报价单审批)
   ↓
4. WorkflowService.startWorkflowInstance (启动审批流程)
   ↓
5. WorkflowService.approveWorkflowNode (多级审批)
   ↓
6. SDService.createSalesOrder (创建销售订单)
   ↓
7. SDService.submitSalesOrder (提交订单评审)
   ↓
8. WorkflowService.startWorkflowInstance (启动评审流程)
   ↓
9. WorkflowService.approveWorkflowNode (多部门评审)
   ↓
10. PPService.createProductionOrder (创建生产订单)
```

**服务依赖关系**：
- SDService → WorkflowService（审批流程）
- SDService → MMService（验证物料）
- SDService → ENGService（验证生产版本）
- PPService → SDService（获取销售订单信息）

---

#### 20.2.2 生产订单下达流程

**场景描述**：从销售订单到生产订单下达的完整流程

**服务调用序列**：
```
1. PPService.createProductionOrder
   ├─→ SDService.getSalesOrder (获取销售订单)
   ├─→ ENGService.getProductionVersion (获取生产版本)
   ├─→ MMService.getMaterial (获取物料信息)
   └─→ 计算单位转换
   ↓
2. PPService.releaseProductionOrder (下达生产订单)
   ↓
3. PPService.startProductionOrder (开始生产)
   ├─→ SDService.syncSalesOrderStatus (同步销售订单状态)
   └─→ 设置订单状态为IN_PRODUCTION
   ↓
4. MMService.createMaterialIssue (创建领料单)
   ├─→ PPService.getProductionOrder (验证生产订单)
   ├─→ MMService.getInventory (检查库存)
   └─→ 创建领料单
   ↓
5. MMService.approveMaterialIssue (审批领料单)
   ├─→ MMService.updateInventory (更新库存)
   └─→ 创建库存事务记录
```

---

#### 20.2.3 工程数据建立流程

**场景描述**：从物料创建到生产版本发布的完整流程

**服务调用序列**：
```
1. MMService.createMaterial (创建物料)
   ↓
2. ENGService.createBOM (创建BOM)
   ├─→ MMService.getMaterial (验证物料)
   └─→ 创建BOM明细
   ↓
3. ENGService.createRouting (创建工艺路线)
   ├─→ MMService.getMaterial (验证物料)
   ├─→ PPService.getWorkCenter (验证工作中心)
   └─→ 创建工序
   ↓
4. ENGService.createMI (创建MI)
   ├─→ MMService.getMaterial (验证物料)
   ├─→ ENGService.getRouting (获取工艺路线)
   └─→ 基于工艺路线生成指令集
   ↓
5. ENGService.submitMI (提交MI审批)
   ↓
6. ENGService.approveMI (审批MI)
   ↓
7. ENGService.createProductionVersion (创建生产版本)
   ├─→ MMService.getMaterial (验证物料)
   ├─→ ENGService.getBOM (验证BOM)
   ├─→ ENGService.getRouting (验证工艺路线)
   └─→ ENGService.getMI (验证MI)
   ↓
8. ENGService.releaseProductionVersion (发布生产版本)
   └─→ 关联MI到生产版本
```

---

### 20.3 服务编排模式

#### 20.3.1 顺序编排

多个服务按顺序调用，前一个服务的输出作为后一个服务的输入。

**示例**：创建销售订单 → 提交评审 → 创建生产订单

#### 20.3.2 并行编排

多个服务可以并行调用，提高性能。

**示例**：创建生产订单时，可以并行验证物料、生产版本、销售订单

#### 20.3.3 条件编排

根据业务条件决定调用哪些服务。

**示例**：如果提供了`material_code`，直接使用；否则查找本厂编号映射

#### 20.3.4 循环编排

重复调用某个服务直到满足条件。

**示例**：工作流审批节点循环推进直到所有节点完成

---

## 二十一、服务调用示例

### 21.1 创建销售订单完整示例

#### 21.1.1 请求示例

**场景**：创建新销售订单，使用本厂编号映射

```http
POST /api/sd/sales-orders
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "customer_id": "CUST001",
  "product_number": "PROD-2024-001",
  "quantity": 1000,
  "unit_price": 15.50,
  "delivery_date": "2025-12-31T00:00:00Z",
  "remarks": "急单，请优先安排生产"
}
```

#### 21.1.2 服务内部调用流程

```python
# 1. 验证客户存在
customer = SDService.getCustomer(customer_id="CUST001")

# 2. 查找本厂编号映射
mapping = SDService.getFactoryProductMapping(
    customer_id="CUST001",
    product_number="PROD-2024-001"
)
# 返回: {
#   "material_code": "MAT-001",
#   "production_version_id": "PV-001"
# }

# 3. 验证物料存在
material = MMService.getMaterial(material_code="MAT-001")
# 获取: base_unit="PCS", production_unit="张", conversion_factor=1.0

# 4. 验证生产版本存在
production_version = ENGService.getProductionVersion(
    production_version_id="PV-001"
)

# 5. 计算单位转换
production_quantity = quantity / conversion_factor  # 1000 / 1.0 = 1000

# 6. 创建销售订单
sales_order = SDService.createSalesOrder({
    "customer_id": "CUST001",
    "material_code": "MAT-001",
    "production_version_id": "PV-001",
    "quantity": 1000,
    "production_quantity": 1000,
    "sales_unit": "PCS",
    "production_unit": "张",
    "conversion_factor": 1.0,
    "unit_price": 15.50,
    "total_amount": 15500.00,
    "delivery_date": "2025-12-31T00:00:00Z",
    "status": "DRAFT"
})
```

#### 21.1.3 响应示例

```json
{
  "code": 201,
  "message": "销售订单创建成功",
  "data": {
    "order_number": "SO-20251212-0001",
    "customer_id": "CUST001",
    "material_code": "MAT-001",
    "production_version_id": "PV-001",
    "quantity": 1000,
    "production_quantity": 1000,
    "sales_unit": "PCS",
    "production_unit": "张",
    "unit_price": 15.50,
    "total_amount": 15500.00,
    "delivery_date": "2025-12-31T00:00:00Z",
    "status": "DRAFT",
    "created_at": "2025-12-12T10:30:00Z"
  },
  "timestamp": "2025-12-12T10:30:00Z",
  "request_id": "req-1234567890"
}
```

---

### 21.2 工作流审批示例

#### 21.2.1 启动工作流实例

```http
POST /api/workflow/instances
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "workflow_id": "QUOTATION_APPROVAL",
  "business_id": "QT-20251212-0001",
  "business_type": "QUOTATION"
}
```

#### 21.2.2 审批工作流节点

```http
POST /api/workflow/instances/WFI-20251212-0001/approve
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "comment": "报价合理，同意"
}
```

#### 21.2.3 获取工作流状态

```http
GET /api/workflow/instances/WFI-20251212-0001
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应示例**：
```json
{
  "code": 200,
  "message": "获取工作流状态成功",
  "data": {
    "instance_id": "WFI-20251212-0001",
    "workflow_id": "QUOTATION_APPROVAL",
    "business_id": "QT-20251212-0001",
    "business_type": "QUOTATION",
    "status": "PENDING",
    "current_node_id": "SALES_MANAGER_REVIEW",
    "current_node_name": "销售经理审批",
    "can_approve": true,
    "nodes": [
      {
        "node_id": "SALES_REVIEW",
        "node_name": "销售审批",
        "status": "APPROVED",
        "approver": "user001",
        "approved_at": "2025-12-12T10:00:00Z",
        "comment": "报价合理"
      },
      {
        "node_id": "SALES_MANAGER_REVIEW",
        "node_name": "销售经理审批",
        "status": "PENDING",
        "approver": null,
        "approved_at": null,
        "comment": null
      },
      {
        "node_id": "FINANCE_REVIEW",
        "node_name": "财务审批",
        "status": "PENDING",
        "approver": null,
        "approved_at": null,
        "comment": null
      }
    ]
  }
}
```

---

### 21.3 生产订单创建示例

#### 21.3.1 请求示例

```http
POST /api/pp/production-orders
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "sales_order_number": "SO-20251212-0001"
}
```

#### 21.3.2 服务内部调用流程

```python
# 1. 获取销售订单信息
sales_order = SDService.getSalesOrder(order_number="SO-20251212-0001")
# 返回: {
#   "order_number": "SO-20251212-0001",
#   "material_code": "MAT-001",
#   "production_version_id": "PV-001",
#   "quantity": 1000,
#   "production_quantity": 1000,
#   "sales_unit": "PCS",
#   "production_unit": "张",
#   "conversion_factor": 1.0,
#   "status": "APPROVED"
# }

# 2. 获取生产版本信息
production_version = ENGService.getProductionVersion(
    production_version_id="PV-001"
)
# 返回: {
#   "production_version_id": "PV-001",
#   "material_code": "MAT-001",
#   "bom_number": "BOM-001",
#   "routing_id": "RT-001",
#   "status": "ACTIVE"
# }

# 3. 获取物料信息
material = MMService.getMaterial(material_code="MAT-001")
# 返回: {
#   "material_code": "MAT-001",
#   "production_unit": "张",
#   ...
# }

# 4. 创建生产订单
production_order = PPService.createProductionOrder({
    "sales_order_number": "SO-20251212-0001",
    "material_code": "MAT-001",
    "production_version_id": "PV-001",
    "bom_number": "BOM-001",
    "routing_id": "RT-001",
    "quantity": 1000,
    "production_quantity": 1000,
    "production_unit": "张",
    "status": "DRAFT"
})
```

---

## 二十二、服务治理

### 22.1 服务注册与发现

#### 22.1.1 服务注册

每个服务启动时向服务注册中心注册：

```yaml
服务注册信息:
  service_id: sd-service
  service_name: SDService
  service_version: 1.0.0
  base_url: http://sd-service:8001
  health_check_url: http://sd-service:8001/health
  metadata:
    tags: [sales, distribution]
    environment: production
```

#### 22.1.2 服务发现

服务通过服务注册中心发现其他服务：

```python
# 服务发现示例
from service_registry import ServiceRegistry

registry = ServiceRegistry()
mm_service = registry.discover("mm-service")
# 返回: {
#   "base_url": "http://mm-service:8002",
#   "version": "1.0.0",
#   "status": "healthy"
# }
```

---

### 22.2 服务熔断与降级

#### 22.2.1 熔断机制

当服务调用失败率达到阈值时，触发熔断：

```yaml
熔断配置:
  failure_threshold: 50%  # 失败率阈值
  timeout: 60s  # 熔断持续时间
  half_open_requests: 5  # 半开状态测试请求数
```

**熔断状态**：
- **CLOSED**：正常状态，允许请求通过
- **OPEN**：熔断状态，直接拒绝请求
- **HALF_OPEN**：半开状态，允许少量请求测试

#### 22.2.2 降级策略

当服务不可用时，使用降级策略：

```python
# 降级策略示例
@circuit_breaker(failure_threshold=0.5, timeout=60)
def get_material(material_code: str):
    try:
        return mm_service.get_material(material_code)
    except ServiceUnavailable:
        # 降级：返回缓存数据或默认值
        return get_cached_material(material_code) or get_default_material()
```

---

### 22.3 服务限流

#### 22.3.1 限流策略

**令牌桶算法**：
- 每个服务维护一个令牌桶
- 请求需要消耗令牌
- 令牌按固定速率补充

**配置示例**：
```yaml
限流配置:
  rate_limit:
    per_user: 100  # 每个用户每分钟100次
    per_ip: 1000  # 每个IP每分钟1000次
    per_service: 10000  # 每个服务每分钟10000次
```

#### 22.3.2 限流响应

当超过限流阈值时，返回429 Too Many Requests：

```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后重试",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60,
  "timestamp": "2025-12-12T10:30:00Z"
}
```

---

### 22.4 服务监控

#### 22.4.1 健康检查

每个服务提供健康检查接口：

```http
GET /health
```

**响应示例**：
```json
{
  "status": "healthy",
  "service": "sd-service",
  "version": "1.0.0",
  "uptime": 86400,
  "dependencies": {
    "database": "healthy",
    "mm-service": "healthy",
    "eng-service": "healthy"
  }
}
```

#### 22.4.2 指标收集

收集以下指标：
- **请求数**：总请求数、成功数、失败数
- **响应时间**：平均响应时间、P50、P95、P99
- **错误率**：按错误类型统计
- **资源使用**：CPU、内存、数据库连接数

---

### 22.5 服务版本管理

#### 22.5.1 版本兼容性

- **主版本号**：不兼容的API变更
- **次版本号**：向后兼容的功能新增
- **修订版本号**：向后兼容的问题修复

#### 22.5.2 版本路由

API网关根据请求头路由到不同版本：

```http
GET /api/sd/customers
X-API-Version: 1.0
```

---

## 二十三、服务最佳实践

### 23.1 服务设计最佳实践

#### 23.1.1 单一职责原则

每个服务只负责一个业务领域，避免服务职责过重。

**好的设计**：
- `CustomerService`：只负责客户管理
- `QuotationService`：只负责报价单管理

**不好的设计**：
- `SalesService`：同时负责客户、报价单、订单管理

#### 23.1.2 接口设计原则

1. **RESTful设计**：使用标准HTTP方法和状态码
   - GET：查询资源
   - POST：创建资源
   - PUT：更新资源（全量更新）
   - PATCH：更新资源（部分更新）
   - DELETE：删除资源

2. **资源导向**：URL表示资源，而非操作
   - ✅ 好的设计：`POST /api/sd/sales-orders/{order_number}/approve`
   - ❌ 不好的设计：`POST /api/sd/approveSalesOrder`

3. **版本控制**：在URL中包含版本号
   - 示例：`/api/v1/sd/customers`
   - 支持多版本共存

4. **分页支持**：列表接口必须支持分页
   - 使用`skip`和`limit`参数
   - 返回总记录数和分页信息

5. **错误处理**：使用标准HTTP状态码和统一错误格式
   - 400：请求参数错误
   - 401：未认证
   - 403：权限不足
   - 404：资源不存在
   - 500：服务器错误

#### 23.1.3 数据一致性原则

1. **事务管理**：
   - 跨服务操作使用分布式事务或补偿机制
   - 单服务内操作使用数据库事务

2. **最终一致性**：
   - 允许跨服务数据最终一致
   - 使用事件驱动架构保证数据同步

3. **幂等性设计**：
   - 关键操作支持幂等性
   - 使用唯一标识符防止重复操作

#### 23.1.4 服务通信最佳实践

1. **同步调用**：
   - 用于实时性要求高的场景
   - 设置合理的超时时间
   - 使用连接池提高性能

2. **异步调用**：
   - 用于耗时操作或非关键路径
   - 使用消息队列解耦服务
   - 提供回调机制获取结果

3. **服务降级**：
   - 非关键服务不可用时提供降级方案
   - 使用缓存数据或默认值
   - 保证核心功能可用

### 23.2 服务实现最佳实践

#### 23.2.1 代码组织

1. **分层架构**：
   ```
   service/
   ├── api/          # API接口层
   ├── service/      # 业务逻辑层
   ├── repository/   # 数据访问层
   └── model/        # 数据模型层
   ```

2. **依赖注入**：
   - 使用依赖注入框架管理依赖
   - 便于测试和替换实现

3. **配置管理**：
   - 使用配置文件管理环境相关配置
   - 敏感信息使用环境变量或密钥管理

#### 23.2.2 错误处理

1. **统一异常处理**：
   - 定义业务异常基类
   - 统一异常转换和响应格式

2. **错误日志**：
   - 记录详细的错误信息
   - 包含请求上下文和堆栈信息
   - 不记录敏感信息

3. **错误恢复**：
   - 实现重试机制
   - 提供降级方案
   - 记录错误用于分析

#### 23.2.3 性能优化

1. **数据库优化**：
   - 合理使用索引
   - 避免N+1查询问题
   - 使用连接池

2. **缓存策略**：
   - 缓存热点数据
   - 设置合理的过期时间
   - 使用缓存更新策略

3. **异步处理**：
   - 耗时操作异步处理
   - 使用消息队列解耦
   - 批量处理提高效率

### 23.3 服务测试最佳实践

#### 23.3.1 单元测试

1. **测试覆盖率**：
   - 核心业务逻辑覆盖率 > 90%
   - 使用Mock隔离依赖

2. **测试用例设计**：
   - 测试正常流程
   - 测试边界条件
   - 测试异常情况

#### 23.3.2 集成测试

1. **服务集成测试**：
   - 测试服务间调用
   - 使用测试数据库
   - 清理测试数据

2. **端到端测试**：
   - 测试完整业务流程
   - 模拟真实场景
   - 验证数据一致性

#### 23.3.3 性能测试

1. **负载测试**：
   - 测试系统在正常负载下的表现
   - 验证性能指标

2. **压力测试**：
   - 测试系统极限负载
   - 识别性能瓶颈

3. **稳定性测试**：
   - 长时间运行测试
   - 检测内存泄漏
   - 验证系统稳定性

---

## 二十四、服务扩展性设计

### 24.1 水平扩展

#### 24.1.1 无状态设计

1. **服务无状态**：
   - 服务实例不保存会话状态
   - 状态存储在共享存储（数据库、缓存）

2. **负载均衡**：
   - 使用负载均衡器分发请求
   - 支持多实例部署

#### 24.1.2 数据分片

1. **数据库分片**：
   - 按业务维度分片（如按客户ID）
   - 使用分片键路由查询

2. **缓存分片**：
   - 使用一致性哈希分片
   - 支持动态扩容

### 24.2 垂直扩展

#### 24.2.1 资源优化

1. **CPU优化**：
   - 使用异步处理提高CPU利用率
   - 优化算法减少计算量

2. **内存优化**：
   - 合理使用缓存
   - 及时释放不用的资源
   - 避免内存泄漏

3. **I/O优化**：
   - 使用连接池
   - 批量操作减少I/O次数
   - 使用异步I/O

### 24.3 服务拆分策略

#### 24.3.1 拆分原则

1. **按业务领域拆分**：
   - 每个服务负责一个业务领域
   - 服务间低耦合

2. **按数据模型拆分**：
   - 每个服务拥有独立的数据模型
   - 避免跨服务事务

3. **按团队拆分**：
   - 每个团队负责一个服务
   - 提高开发效率

#### 24.3.2 拆分步骤

1. **识别边界**：
   - 分析业务领域
   - 识别服务边界

2. **数据迁移**：
   - 设计数据迁移方案
   - 保证数据一致性

3. **接口适配**：
   - 保持接口兼容
   - 逐步迁移调用方

---

## 二十五、服务安全最佳实践

### 25.1 认证安全

#### 25.1.1 令牌管理

1. **令牌生成**：
   - 使用强随机数生成令牌
   - 设置合理的过期时间
   - 包含必要的用户信息

2. **令牌存储**：
   - 客户端安全存储令牌
   - 服务端验证令牌有效性
   - 支持令牌刷新

3. **令牌撤销**：
   - 支持令牌主动撤销
   - 记录撤销的令牌
   - 验证时检查撤销列表

#### 25.1.2 密码安全

1. **密码加密**：
   - 使用bcrypt等强加密算法
   - 设置合理的加密强度
   - 不存储明文密码

2. **密码策略**：
   - 要求强密码（长度、复杂度）
   - 定期更换密码
   - 防止密码重用

### 25.2 授权安全

#### 25.2.1 权限验证

1. **多层验证**：
   - API网关层验证
   - 服务层二次验证
   - 数据层权限控制

2. **最小权限原则**：
   - 用户只拥有必要的权限
   - 定期审查权限分配

#### 25.2.2 数据权限

1. **行级权限**：
   - 用户只能访问自己的数据
   - 管理员可以访问所有数据

2. **字段级权限**：
   - 敏感字段需要特殊权限
   - 根据角色返回不同字段

### 25.3 数据安全

#### 25.3.1 传输安全

1. **HTTPS加密**：
   - 所有API使用HTTPS
   - 使用有效的SSL证书
   - 定期更新证书

2. **数据加密**：
   - 敏感数据加密传输
   - 使用强加密算法

#### 25.3.2 存储安全

1. **数据库加密**：
   - 敏感字段加密存储
   - 使用数据库加密功能

2. **备份安全**：
   - 备份数据加密
   - 安全存储备份
   - 定期测试恢复

### 25.4 安全审计

#### 25.4.1 日志记录

1. **操作日志**：
   - 记录所有关键操作
   - 包含操作人、时间、内容

2. **访问日志**：
   - 记录所有API访问
   - 包含IP、用户、时间

#### 25.4.2 安全监控

1. **异常检测**：
   - 检测异常访问模式
   - 检测暴力破解尝试
   - 检测数据泄露风险

2. **告警机制**：
   - 安全事件实时告警
   - 通知安全团队
   - 记录安全事件

---

## 二十六、服务运维最佳实践

### 26.1 部署管理

#### 26.1.1 容器化部署

1. **Docker镜像**：
   - 使用多阶段构建
   - 优化镜像大小
   - 使用官方基础镜像

2. **容器编排**：
   - 使用Kubernetes编排
   - 配置资源限制
   - 设置健康检查

#### 26.1.2 配置管理

1. **环境配置**：
   - 使用ConfigMap管理配置
   - 敏感信息使用Secret
   - 支持配置热更新

2. **版本管理**：
   - 配置版本化
   - 支持配置回滚
   - 记录配置变更历史

### 26.2 监控告警

#### 26.2.1 指标监控

1. **系统指标**：
   - CPU、内存、磁盘使用率
   - 网络流量
   - 进程状态

2. **应用指标**：
   - 请求数、响应时间
   - 错误率、成功率
   - 业务指标

3. **数据库指标**：
   - 连接数、查询时间
   - 慢查询
   - 锁等待

#### 26.2.2 日志管理

1. **日志收集**：
   - 集中收集所有服务日志
   - 使用ELK或类似工具
   - 支持日志查询和分析

2. **日志分析**：
   - 实时分析错误日志
   - 统计访问模式
   - 识别异常行为

#### 26.2.3 告警配置

1. **告警规则**：
   - 服务不可用
   - 错误率超过阈值
   - 响应时间过长
   - 资源使用率过高

2. **告警通知**：
   - 邮件通知
   - 短信通知（紧急）
   - 钉钉/企业微信通知

### 26.3 故障处理

#### 26.3.1 故障预防

1. **健康检查**：
   - 定期健康检查
   - 自动重启异常服务
   - 隔离故障实例

2. **容量规划**：
   - 监控资源使用趋势
   - 提前扩容
   - 预留缓冲容量

#### 26.3.2 故障恢复

1. **自动恢复**：
   - 服务自动重启
   - 自动故障转移
   - 自动扩容

2. **手动恢复**：
   - 故障诊断流程
   - 恢复操作手册
   - 回滚方案

#### 26.3.3 故障复盘

1. **故障记录**：
   - 记录故障详情
   - 分析根本原因
   - 制定改进措施

2. **持续改进**：
   - 实施改进措施
   - 验证改进效果
   - 更新运维文档

---

## 二十七、服务文档规范

### 27.1 API文档

#### 27.1.1 OpenAPI规范

1. **文档结构**：
   - 使用OpenAPI 3.0规范
   - 包含完整的接口定义
   - 包含请求/响应示例

2. **文档内容**：
   - 接口描述
   - 参数说明
   - 响应格式
   - 错误码说明

#### 27.1.2 文档维护

1. **文档更新**：
   - 代码变更同步更新文档
   - 使用代码生成文档
   - 定期审查文档准确性

2. **文档版本**：
   - 文档版本化
   - 记录变更历史
   - 支持多版本共存

### 27.2 服务文档

#### 27.2.1 服务说明文档

1. **服务概述**：
   - 服务职责
   - 服务边界
   - 主要功能

2. **技术文档**：
   - 技术架构
   - 依赖关系
   - 部署说明

#### 27.2.2 开发文档

1. **开发指南**：
   - 环境搭建
   - 代码规范
   - 开发流程

2. **测试文档**：
   - 测试用例
   - 测试数据
   - 测试环境

### 27.3 运维文档

#### 27.3.1 部署文档

1. **部署步骤**：
   - 环境准备
   - 部署流程
   - 验证方法

2. **配置说明**：
   - 配置项说明
   - 配置示例
   - 配置变更流程

#### 27.3.2 运维手册

1. **日常运维**：
   - 监控检查
   - 日志查看
   - 性能优化

2. **故障处理**：
   - 常见问题
   - 故障诊断
   - 恢复步骤

---

## 二十八、服务演进策略

### 28.1 版本演进

#### 28.1.1 版本规划

1. **版本策略**：
   - 主版本：不兼容变更
   - 次版本：新功能
   - 修订版本：问题修复

2. **兼容性保证**：
   - 至少保持一个主版本的兼容性
   - 提供迁移指南
   - 支持平滑升级

#### 28.1.2 废弃策略

1. **废弃流程**：
   - 提前公告废弃计划
   - 标记废弃的API
   - 提供替代方案
   - 设置废弃期限

2. **迁移支持**：
   - 提供迁移工具
   - 提供迁移文档
   - 技术支持

### 28.2 功能演进

#### 28.2.1 新功能开发

1. **需求分析**：
   - 分析业务需求
   - 评估技术可行性
   - 设计服务接口

2. **开发流程**：
   - 设计评审
   - 开发实现
   - 测试验证
   - 文档更新

#### 28.2.2 功能优化

1. **性能优化**：
   - 识别性能瓶颈
   - 优化方案设计
   - 实施优化
   - 验证效果

2. **体验优化**：
   - 收集用户反馈
   - 分析使用数据
   - 优化交互流程

### 28.3 架构演进

#### 28.3.1 服务拆分

1. **拆分时机**：
   - 服务职责过重
   - 团队规模扩大
   - 性能瓶颈

2. **拆分方案**：
   - 识别服务边界
   - 设计拆分方案
   - 逐步实施

#### 28.3.2 技术升级

1. **技术选型**：
   - 评估新技术
   - 评估迁移成本
   - 制定升级计划

2. **升级实施**：
   - 渐进式升级
   - 充分测试
   - 回滚方案

---

## 二十九、服务质量保证

### 29.1 代码质量

#### 29.1.1 代码规范

1. **编码规范**：
   - 遵循语言编码规范
   - 使用代码检查工具
   - 代码审查

2. **代码结构**：
   - 清晰的模块划分
   - 合理的依赖关系
   - 良好的命名规范

#### 29.1.2 代码审查

1. **审查流程**：
   - 提交前自检
   - 同行审查
   - 技术负责人审查

2. **审查要点**：
   - 代码逻辑正确性
   - 性能问题
   - 安全问题
   - 可维护性

### 29.2 测试质量

#### 29.2.1 测试覆盖

1. **覆盖率要求**：
   - 单元测试覆盖率 > 80%
   - 集成测试覆盖主要流程
   - 端到端测试覆盖关键场景

2. **测试质量**：
   - 测试用例设计合理
   - 测试数据准备充分
   - 测试环境稳定

#### 29.2.2 自动化测试

1. **CI/CD集成**：
   - 代码提交自动运行测试
   - 测试失败阻止部署
   - 测试报告自动生成

2. **测试维护**：
   - 及时更新测试用例
   - 修复失败的测试
   - 保持测试代码质量

---

## 三十、服务模型总结

### 30.1 服务模型概览

某某ERP系统采用模块化服务架构，包含以下核心服务：

1. **认证服务（AuthService）**：提供用户认证和授权功能
2. **用户管理服务（UserService）**：管理用户和角色
3. **销售与分销服务（SDService）**：管理客户、报价单、销售订单
4. **工程管理服务（ENGService）**：管理BOM、工艺路线、MI、生产版本
5. **生产计划与控制服务（PPService）**：管理工作中心、生产订单、工序报工
6. **物料管理服务（MMService）**：管理物料主数据、库存、领料
7. **工作流服务（WorkflowService）**：提供审批流程引擎

### 30.2 服务设计特点

1. **模块化设计**：每个服务独立部署，职责清晰
2. **接口标准化**：遵循RESTful规范和OpenAPI标准
3. **契约优先**：明确定义服务接口和操作规范
4. **依赖管理**：清晰的服务依赖关系和调用规范
5. **可扩展性**：支持水平扩展和垂直扩展
6. **高可用性**：支持服务熔断、降级、限流等机制

### 30.3 服务通信模式

1. **同步调用**：用于实时性要求高的场景
2. **异步调用**：用于耗时操作或非关键路径
3. **事件驱动**：用于服务间解耦和数据同步

### 30.4 服务质量保证

1. **性能要求**：响应时间、并发性能、可用性要求明确
2. **安全机制**：认证、授权、数据安全规范完善
3. **监控告警**：完善的监控指标和告警机制
4. **测试规范**：单元测试、集成测试、性能测试要求明确

### 30.5 服务演进策略

1. **版本管理**：语义化版本号，支持多版本共存
2. **功能演进**：新功能开发和功能优化流程规范
3. **架构演进**：服务拆分和技术升级策略明确

---

## 三十一、服务实现参考

### 31.1 服务实现架构

#### 31.1.1 分层架构

每个服务采用分层架构设计：

```
服务实现架构:
├── API层（API Layer）
│   ├── 路由定义
│   ├── 请求验证
│   ├── 响应格式化
│   └── 异常处理
├── 服务层（Service Layer）
│   ├── 业务逻辑
│   ├── 服务编排
│   ├── 事务管理
│   └── 权限验证
├── 仓储层（Repository Layer）
│   ├── 数据访问
│   ├── 查询优化
│   └── 缓存管理
└── 模型层（Model Layer）
    ├── 数据模型
    ├── 业务模型
    └── 值对象
```

#### 31.1.2 依赖注入

使用依赖注入框架管理服务依赖：

```python
# 依赖注入示例
from dependency_injector import containers, providers

class ServiceContainer(containers.DeclarativeContainer):
    # 配置
    config = providers.Configuration()
    
    # 数据库
    database = providers.Singleton(
        Database,
        connection_string=config.database.url
    )
    
    # 仓储
    material_repository = providers.Factory(
        MaterialRepository,
        db=database
    )
    
    # 服务
    material_service = providers.Factory(
        MaterialService,
        repository=material_repository
    )
    
    # API
    material_api = providers.Factory(
        MaterialAPI,
        service=material_service
    )
```

### 31.2 服务实现示例

#### 31.2.1 物料服务实现示例

```python
# 服务层实现
class MaterialService:
    def __init__(self, repository: MaterialRepository):
        self.repository = repository
    
    def create_material(self, request: CreateMaterialRequest) -> Material:
        # 1. 验证物料编码唯一性
        if self.repository.exists_by_code(request.material_code):
            raise BusinessException("物料编码已存在")
        
        # 2. 创建物料对象
        material = Material(
            material_code=request.material_code,
            material_name=request.material_name,
            category=request.category,
            status=MaterialStatus.DRAFT
        )
        
        # 3. 保存到数据库
        return self.repository.save(material)
    
    def get_material(self, material_code: str) -> Material:
        material = self.repository.find_by_code(material_code)
        if not material:
            raise NotFoundException("物料不存在")
        return material
    
    def list_materials(self, request: ListMaterialsRequest) -> List[Material]:
        return self.repository.find_all(
            skip=request.skip,
            limit=request.limit,
            filters=request.filters
        )

# API层实现
class MaterialAPI:
    def __init__(self, service: MaterialService):
        self.service = service
    
    @router.post("/materials")
    async def create_material(
        self,
        request: CreateMaterialRequest,
        current_user: User = Depends(get_current_user)
    ) -> StandardResponse[MaterialResponse]:
        # 权限验证
        if not current_user.has_role([Role.ENGINEER, Role.WAREHOUSE]):
            raise ForbiddenException("权限不足")
        
        # 调用服务
        material = self.service.create_material(request)
        
        # 返回响应
        return StandardResponse(
            code=201,
            message="物料创建成功",
            data=MaterialResponse.from_entity(material)
        )
```

#### 31.2.2 工作流服务实现示例

```python
# 工作流服务实现
class WorkflowInstanceService:
    def __init__(
        self,
        workflow_repository: WorkflowRepository,
        instance_repository: WorkflowInstanceRepository,
        node_repository: WorkflowNodeInstanceRepository
    ):
        self.workflow_repository = workflow_repository
        self.instance_repository = instance_repository
        self.node_repository = node_repository
    
    def start_instance(self, request: StartWorkflowInstanceRequest) -> WorkflowInstance:
        # 1. 验证工作流定义存在
        workflow = self.workflow_repository.find_by_id(request.workflow_id)
        if not workflow:
            raise NotFoundException("工作流定义不存在")
        
        # 2. 验证业务对象唯一性
        existing = self.instance_repository.find_by_business(
            request.business_id,
            request.business_type
        )
        if existing and existing.status == WorkflowStatus.PENDING:
            raise BusinessException("业务对象已有进行中的工作流实例")
        
        # 3. 创建工作流实例
        instance = WorkflowInstance(
            instance_id=self._generate_instance_id(),
            workflow_id=request.workflow_id,
            business_id=request.business_id,
            business_type=request.business_type,
            status=WorkflowStatus.PENDING
        )
        
        # 4. 创建第一个节点实例
        first_node = workflow.get_first_approval_node()
        node_instance = WorkflowNodeInstance(
            instance_id=instance.instance_id,
            node_id=first_node.node_id,
            status=NodeStatus.PENDING
        )
        
        # 5. 保存
        instance.current_node_id = first_node.node_id
        instance = self.instance_repository.save(instance)
        self.node_repository.save(node_instance)
        
        return instance
    
    def approve_node(
        self,
        instance_id: str,
        user: User,
        comment: str = None
    ) -> WorkflowInstance:
        # 1. 获取工作流实例
        instance = self.instance_repository.find_by_id(instance_id)
        if not instance:
            raise NotFoundException("工作流实例不存在")
        
        # 2. 验证状态
        if instance.status != WorkflowStatus.PENDING:
            raise BusinessException("工作流实例状态无效")
        
        # 3. 验证权限
        current_node = instance.get_current_node()
        if not user.has_role([current_node.approver_role]):
            raise ForbiddenException("当前用户没有权限审批此节点")
        
        # 4. 更新当前节点状态
        current_node_instance = self.node_repository.find_current(instance_id)
        current_node_instance.status = NodeStatus.APPROVED
        current_node_instance.approver = user.username
        current_node_instance.approved_at = datetime.now()
        current_node_instance.comment = comment
        self.node_repository.save(current_node_instance)
        
        # 5. 移动到下一个节点
        next_node = instance.get_next_node()
        if next_node:
            # 创建下一个节点实例
            next_node_instance = WorkflowNodeInstance(
                instance_id=instance.instance_id,
                node_id=next_node.node_id,
                status=NodeStatus.PENDING
            )
            self.node_repository.save(next_node_instance)
            instance.current_node_id = next_node.node_id
        else:
            # 所有节点完成
            instance.status = WorkflowStatus.COMPLETED
        
        # 6. 保存实例
        return self.instance_repository.save(instance)
```

### 31.3 服务间调用实现

#### 31.3.1 服务客户端实现

```python
# 服务客户端基类
class ServiceClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def _request(
        self,
        method: str,
        path: str,
        headers: dict = None,
        data: dict = None
    ) -> dict:
        url = f"{self.base_url}{path}"
        headers = headers or {}
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ServiceException(f"服务调用失败: {str(e)}")

# 物料服务客户端
class MaterialServiceClient(ServiceClient):
    def get_material(self, material_code: str, token: str) -> dict:
        headers = {"Authorization": f"Bearer {token}"}
        return self._request("GET", f"/materials/{material_code}", headers=headers)
    
    def list_materials(self, filters: dict, token: str) -> dict:
        headers = {"Authorization": f"Bearer {token}"}
        return self._request("GET", "/materials", headers=headers, data=filters)

# 使用示例
material_client = MaterialServiceClient(base_url="http://mm-service:8002")
material = material_client.get_material("MAT-001", token="...")
```

#### 31.3.2 服务调用封装

```python
# 服务调用封装
class ServiceCaller:
    def __init__(self):
        self.material_client = MaterialServiceClient(
            base_url=os.getenv("MM_SERVICE_URL")
        )
        self.eng_client = ENGServiceClient(
            base_url=os.getenv("ENG_SERVICE_URL")
        )
    
    @retry(max_attempts=3, backoff=exponential_backoff)
    @circuit_breaker(failure_threshold=0.5, timeout=60)
    def get_material(self, material_code: str, token: str) -> Material:
        try:
            response = self.material_client.get_material(material_code, token)
            return Material.from_dict(response["data"])
        except ServiceException as e:
            # 降级：返回缓存数据
            cached = self._get_cached_material(material_code)
            if cached:
                return cached
            raise
```

### 31.4 错误处理实现

#### 31.4.1 异常定义

```python
# 业务异常基类
class BusinessException(Exception):
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

# 具体异常类
class NotFoundException(BusinessException):
    def __init__(self, message: str):
        super().__init__(message, error_code="NOT_FOUND")

class ValidationException(BusinessException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.details = details

class ForbiddenException(BusinessException):
    def __init__(self, message: str):
        super().__init__(message, error_code="FORBIDDEN")
```

#### 31.4.2 异常处理中间件

```python
# 异常处理中间件
@app.exception_handler(BusinessException)
async def business_exception_handler(
    request: Request,
    exc: BusinessException
) -> JSONResponse:
    status_code = 400
    if isinstance(exc, NotFoundException):
        status_code = 404
    elif isinstance(exc, ForbiddenException):
        status_code = 403
    
    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": exc.message,
            "error_code": exc.error_code,
            "timestamp": datetime.now().isoformat(),
            "request_id": request.headers.get("X-Request-ID")
        }
    )
```

---

## 三十二、服务模型检查清单

### 32.1 服务设计检查清单

- [ ] 服务职责单一，边界清晰
- [ ] 服务接口遵循RESTful规范
- [ ] 服务接口定义完整（请求/响应契约）
- [ ] 服务操作规范明确
- [ ] 服务依赖关系清晰
- [ ] 错误处理规范完善
- [ ] 权限要求明确

### 32.2 服务实现检查清单

- [ ] 代码结构清晰，分层合理
- [ ] 依赖注入使用正确
- [ ] 异常处理完善
- [ ] 日志记录规范
- [ ] 单元测试覆盖率高
- [ ] 集成测试完整
- [ ] 性能测试通过

### 32.3 服务部署检查清单

- [ ] 服务配置完整
- [ ] 健康检查接口正常
- [ ] 监控指标配置完善
- [ ] 日志收集配置正确
- [ ] 告警规则配置合理
- [ ] 服务注册成功
- [ ] 服务发现正常

### 32.4 服务文档检查清单

- [ ] API文档完整（OpenAPI规范）
- [ ] 服务说明文档完善
- [ ] 开发文档齐全
- [ ] 部署文档详细
- [ ] 运维手册完整
- [ ] 变更历史记录

---

## 三十三、服务模型常见问题

### 33.1 服务设计问题

#### Q1: 如何确定服务边界？

**A:** 服务边界应该基于业务领域划分：
- 每个服务负责一个业务领域（如客户管理、订单管理）
- 服务间通过接口交互，不直接访问对方数据库
- 服务拥有独立的数据模型

#### Q2: 如何处理跨服务事务？

**A:** 跨服务事务处理策略：
- **分布式事务**：使用两阶段提交（2PC）或Saga模式
- **最终一致性**：允许数据最终一致，使用事件驱动同步
- **补偿机制**：失败时执行补偿操作

#### Q3: 服务间如何共享数据？

**A:** 服务间数据共享原则：
- **不共享数据库**：每个服务拥有独立数据库
- **通过接口共享**：通过API接口获取数据
- **数据复制**：非关键数据可以复制到本地
- **事件同步**：通过事件机制同步数据

### 33.2 服务实现问题

#### Q4: 如何处理服务调用失败？

**A:** 服务调用失败处理策略：
- **重试机制**：使用指数退避重试
- **熔断机制**：失败率过高时熔断
- **降级策略**：返回缓存数据或默认值
- **超时设置**：设置合理的超时时间

#### Q5: 如何保证服务性能？

**A:** 服务性能优化方法：
- **数据库优化**：合理使用索引，避免N+1查询
- **缓存策略**：缓存热点数据
- **异步处理**：耗时操作异步处理
- **连接池**：使用连接池管理数据库连接
- **批量操作**：批量处理减少I/O次数

#### Q6: 如何实现服务版本管理？

**A:** 服务版本管理策略：
- **URL版本控制**：在路径中包含版本号（/api/v1/...）
- **请求头版本控制**：使用X-API-Version头
- **多版本共存**：支持多个版本同时运行
- **版本兼容性**：新版本向后兼容至少一个主版本

### 33.3 服务部署问题

#### Q7: 如何实现服务高可用？

**A:** 服务高可用实现：
- **多实例部署**：部署多个服务实例
- **负载均衡**：使用负载均衡器分发请求
- **健康检查**：定期检查服务健康状态
- **自动故障转移**：故障时自动切换到备用实例
- **数据备份**：定期备份数据

#### Q8: 如何监控服务状态？

**A:** 服务监控方法：
- **健康检查接口**：提供/health接口
- **指标收集**：收集请求数、响应时间、错误率等指标
- **日志收集**：集中收集所有服务日志
- **告警机制**：异常时发送告警通知
- **可视化展示**：使用监控面板展示指标

---

## 三十四、服务模型参考资源

### 34.1 技术文档

- [OpenAPI 3.0规范](https://swagger.io/specification/)
- [RESTful API设计指南](https://restfulapi.net/)
- [微服务架构模式](https://microservices.io/patterns/)
- [领域驱动设计](https://www.domainlanguage.com/ddd/)

### 34.2 工具和框架

- **API文档工具**：Swagger、Postman
- **服务注册发现**：Consul、Eureka、Nacos
- **API网关**：Kong、Zuul、Spring Cloud Gateway
- **服务监控**：Prometheus、Grafana、ELK
- **服务追踪**：Jaeger、Zipkin

### 34.3 最佳实践

- [微服务最佳实践](https://microservices.io/patterns/)
- [API设计最佳实践](https://restfulapi.net/)
- [服务治理最佳实践](https://www.nginx.com/blog/microservices-at-netflix-architectural-best-practices/)

---

## 三十五、文档变更记录

### 35.1 版本历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| v1.0 | 2025-12-12 | 初始版本，定义基础服务架构 | - |
| v1.1 | 2025-12-12 | 添加服务依赖关系图和详细说明 | - |
| v1.2 | 2025-12-12 | 完善服务接口规范，添加请求/响应契约 | - |
| v1.3 | 2025-12-12 | 添加服务契约、错误处理、监控等规范 | - |
| v1.4 | 2025-12-12 | 添加服务编排、服务示例、服务治理等内容 | - |
| v1.5 | 2025-12-12 | 完善服务实现参考、检查清单、常见问题等 | - |

### 35.2 主要变更内容

#### v1.5 (2025-12-12)
- 完善文档变更记录
- 添加服务实现参考代码示例
- 添加服务模型检查清单
- 添加服务模型常见问题解答
- 添加服务模型参考资源

#### v1.4 (2025-12-12)
- 添加服务编排和组合场景
- 添加服务调用示例
- 添加服务治理相关内容（注册发现、熔断降级、限流、监控）
- 添加服务最佳实践章节

#### v1.3 (2025-12-12)
- 添加服务契约规范（请求/响应格式）
- 添加错误处理规范
- 添加服务监控和日志规范
- 添加服务测试规范
- 添加服务部署规范

#### v1.2 (2025-12-12)
- 完善各服务接口的请求/响应契约
- 添加服务操作规范详细说明
- 添加权限要求和错误处理说明

#### v1.1 (2025-12-12)
- 添加服务依赖关系矩阵
- 添加服务依赖关系说明
- 添加服务调用流程图

#### v1.0 (2025-12-12)
- 初始版本
- 定义7个核心服务模块
- 定义服务设计原则和通信协议
- 定义各服务的基础接口

---

## 三十六、服务模型索引

### 36.1 服务快速索引

| 服务名称 | 服务标识 | 章节 | 主要功能 |
|---------|---------|------|---------|
| 认证服务 | auth | 第三章 | 用户登录、令牌管理 |
| 用户管理服务 | user | 第四章 | 用户CRUD、角色管理 |
| 销售与分销服务 | sd | 第五章 | 客户、报价单、销售订单 |
| 工程管理服务 | eng | 第六章 | BOM、工艺路线、MI、生产版本 |
| 生产计划与控制服务 | pp | 第七章 | 工作中心、生产订单、报工 |
| 物料管理服务 | mm | 第八章 | 物料主数据、库存、领料 |
| 工作流服务 | workflow | 第九章 | 审批流程引擎 |

### 36.2 接口快速索引

#### 认证服务接口
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

#### 用户管理服务接口
- `POST /api/users` - 创建用户
- `GET /api/users` - 获取用户列表
- `PUT /api/users/{user_id}` - 更新用户
- `DELETE /api/users/{user_id}` - 删除用户
- `GET /api/roles` - 获取角色列表

#### 销售与分销服务接口
- **客户管理**
  - `POST /api/sd/customers` - 创建客户
  - `GET /api/sd/customers` - 获取客户列表
  - `GET /api/sd/customers/{customer_id}` - 获取客户详情
  - `PUT /api/sd/customers/{customer_id}` - 更新客户
- **报价单管理**
  - `POST /api/sd/quotations` - 创建报价单
  - `POST /api/sd/quotations/{quotation_number}/submit` - 提交报价单审批
  - `POST /api/sd/quotations/{quotation_number}/approve` - 审批报价单
  - `POST /api/sd/quotations/{quotation_number}/reject` - 拒绝报价单
- **销售订单管理**
  - `POST /api/sd/sales-orders` - 创建销售订单
  - `POST /api/sd/sales-orders/{order_number}/submit` - 提交销售订单评审
  - `GET /api/sd/sales-orders/{order_number}/review-status` - 获取评审状态
  - `POST /api/sd/sales-orders/{order_number}/approve` - 审批销售订单
  - `POST /api/sd/sales-orders/{order_number}/reject` - 拒绝销售订单
  - `POST /api/sd/sales-orders/{order_number}/ship` - 销售发货
  - `POST /api/sd/sales-orders/{order_number}/deliver` - 销售签收
  - `POST /api/sd/sales-orders/{order_number}/reconcile` - 对账
  - `POST /api/sd/sales-orders/{order_number}/close` - 关闭销售订单
- **本厂编号映射**
  - `POST /api/sd/factory-product-mappings` - 创建本厂编号映射
  - `GET /api/sd/factory-product-mappings/{customer_id}/{product_number}` - 获取映射

#### 工程管理服务接口
- **BOM管理**
  - `POST /api/eng/boms` - 创建BOM
  - `GET /api/eng/boms/{bom_number}` - 获取BOM详情
  - `PUT /api/eng/boms/{bom_number}` - 更新BOM
- **工艺路线管理**
  - `POST /api/eng/routings` - 创建工艺路线
  - `GET /api/eng/routings/{routing_id}` - 获取工艺路线详情
  - `GET /api/eng/routings/{routing_id}/operations` - 获取工序列表
  - `PUT /api/eng/routings/{routing_id}` - 更新工艺路线
- **MI管理**
  - `POST /api/eng/mis` - 创建MI
  - `GET /api/eng/mis/{mi_number}` - 获取MI详情
  - `PUT /api/eng/mis/{mi_number}` - 更新MI
  - `POST /api/eng/mis/{mi_number}/submit` - 提交MI审批
  - `POST /api/eng/mis/{mi_number}/approve` - 审批MI
  - `POST /api/eng/mis/{mi_number}/reject` - 拒绝MI
- **生产版本管理**
  - `POST /api/eng/production-versions` - 创建生产版本
  - `GET /api/eng/production-versions/{production_version_id}` - 获取生产版本详情
  - `PUT /api/eng/production-versions/{production_version_id}` - 更新生产版本
  - `POST /api/eng/production-versions/{production_version_id}/release` - 发布生产版本

#### 生产计划与控制服务接口
- **工作中心管理**
  - `POST /api/pp/work-centers` - 创建工作中心
  - `GET /api/pp/work-centers/{work_center_id}` - 获取工作中心详情
- **生产订单管理**
  - `POST /api/pp/production-orders` - 创建生产订单
  - `POST /api/pp/production-orders/{order_number}/release` - 下达生产订单
  - `POST /api/pp/production-orders/{order_number}/start` - 开始生产订单
  - `POST /api/pp/production-orders/{order_number}/complete` - 完成生产订单
  - `POST /api/pp/production-orders/{order_number}/close` - 关闭生产订单
  - `GET /api/pp/production-orders/{order_number}/operations` - 获取生产订单工序列表
  - `GET /api/pp/production-orders/{order_number}/progress` - 获取生产进度
- **工序报工管理**
  - `POST /api/pp/operation-reports` - 创建工序报工
  - `GET /api/pp/operation-reports` - 获取工序报工列表

#### 物料管理服务接口
- **物料主数据管理**
  - `POST /api/mm/materials` - 创建物料
  - `GET /api/mm/materials` - 获取物料列表
  - `GET /api/mm/materials/{material_code}` - 获取物料详情
  - `PUT /api/mm/materials/{material_code}` - 更新物料
  - `POST /api/mm/materials/{material_code}/activate` - 激活物料
  - `POST /api/mm/materials/{material_code}/deactivate` - 停用物料
- **库存管理**
  - `GET /api/mm/materials/{material_code}/inventory` - 获取库存信息
  - `PUT /api/mm/materials/{material_code}/inventory` - 更新库存
  - `GET /api/mm/materials/{material_code}/transactions` - 获取库存事务记录
- **领料管理**
  - `POST /api/mm/material-issues` - 创建领料单
  - `POST /api/mm/material-issues/{issue_number}/approve` - 审批领料单
  - `POST /api/mm/material-issues/{issue_number}/reject` - 拒绝领料单
  - `GET /api/mm/material-issues` - 获取领料单列表

#### 工作流服务接口
- **工作流定义管理**
  - `POST /api/workflow/workflows` - 创建工作流定义
  - `GET /api/workflow/workflows` - 获取工作流定义列表
  - `GET /api/workflow/workflows/{workflow_id}` - 获取工作流定义详情
- **工作流实例管理**
  - `POST /api/workflow/instances` - 启动工作流实例
  - `GET /api/workflow/instances/{instance_id}` - 获取工作流实例状态
  - `POST /api/workflow/instances/{instance_id}/approve` - 审批工作流节点
  - `POST /api/workflow/instances/{instance_id}/reject` - 拒绝工作流节点
  - `POST /api/workflow/instances/{instance_id}/cancel` - 取消工作流实例
  - `GET /api/workflow/instances/{instance_id}/history` - 获取工作流实例历史

---

## 三十七、服务模型术语表

### 37.1 服务相关术语

| 术语 | 英文 | 说明 |
|------|------|------|
| 服务 | Service | 独立的业务功能模块，提供一组相关的业务能力 |
| 服务标识 | Service Identifier | 服务的唯一标识符，用于服务注册和发现 |
| 服务接口 | Service Interface | 服务对外提供的API接口 |
| 服务契约 | Service Contract | 服务接口的规范定义，包括请求/响应格式 |
| 服务依赖 | Service Dependency | 服务之间的依赖关系 |
| 服务编排 | Service Orchestration | 将多个服务组合起来完成复杂业务流程 |
| 服务治理 | Service Governance | 对服务的注册、发现、监控、限流等管理 |

### 37.2 架构相关术语

| 术语 | 英文 | 说明 |
|------|------|------|
| SOA | Service-Oriented Architecture | 面向服务的架构 |
| API网关 | API Gateway | 统一入口，负责路由、认证、限流等功能 |
| 服务注册中心 | Service Registry | 服务注册和发现的中心化组件 |
| 负载均衡 | Load Balancing | 将请求分发到多个服务实例 |
| 熔断器 | Circuit Breaker | 防止服务雪崩的保护机制 |
| 服务降级 | Service Degradation | 服务不可用时的降级策略 |
| 限流 | Rate Limiting | 限制服务调用频率的保护机制 |
| 分布式追踪 | Distributed Tracing | 追踪跨服务调用的请求链路 |
| 服务网格 | Service Mesh | 管理服务间通信的基础设施层 |

### 37.3 工作流相关术语

| 术语 | 英文 | 说明 |
|------|------|------|
| 工作流定义 | Workflow Definition | 工作流的模板定义，包含节点和流转规则 |
| 工作流实例 | Workflow Instance | 基于工作流定义创建的具体实例 |
| 工作流节点 | Workflow Node | 工作流中的一个步骤或审批点 |
| 节点实例 | Node Instance | 工作流实例中的具体节点执行记录 |
| 审批人角色 | Approver Role | 可以审批某个节点的角色 |
| 工作流状态 | Workflow Status | 工作流实例的当前状态（PENDING/APPROVED/REJECTED等） |

### 37.4 业务相关术语

| 术语 | 英文 | 说明 |
|------|------|------|
| BOM | Bill of Materials | 物料清单，定义产品的组成结构 |
| 工艺路线 | Routing | 定义产品的生产工艺流程 |
| MI | Manufacturing Instruction | 制造指令，包含生产操作指导 |
| 生产版本 | Production Version | 物料、BOM、工艺路线、MI的组合版本 |
| 本厂编号 | Factory Product Number | 客户产品在本厂的编号 |
| 销售单位 | Sales Unit | 销售时使用的计量单位 |
| 生产单位 | Production Unit | 生产时使用的计量单位 |
| 单位转换系数 | Conversion Factor | 销售单位与生产单位之间的转换比例 |

---

## 三十八、服务模型实施路线图

### 38.1 实施阶段规划

#### 第一阶段：基础服务建设（1-3个月）

**目标**：建立核心服务基础设施

**任务清单**：
- [ ] 搭建服务框架和基础架构
- [ ] 实现认证服务（AuthService）
- [ ] 实现用户管理服务（UserService）
- [ ] 建立API网关
- [ ] 建立服务注册中心
- [ ] 建立基础监控和日志系统

**交付物**：
- 认证和用户管理功能
- 基础服务框架
- 服务治理基础设施

#### 第二阶段：核心业务服务（4-6个月）

**目标**：实现核心业务服务

**任务清单**：
- [ ] 实现物料管理服务（MMService）
- [ ] 实现工程管理服务（ENGService）
- [ ] 实现销售与分销服务（SDService）
- [ ] 实现工作流服务（WorkflowService）
- [ ] 建立服务间调用机制
- [ ] 完善错误处理和监控

**交付物**：
- 物料、工程、销售管理功能
- 工作流审批功能
- 服务间集成能力

#### 第三阶段：生产管理服务（7-9个月）

**目标**：实现生产相关服务

**任务清单**：
- [ ] 实现生产计划与控制服务（PPService）
- [ ] 完善库存管理功能
- [ ] 实现领料管理功能
- [ ] 实现工序报工功能
- [ ] 完善服务编排能力
- [ ] 性能优化和压力测试

**交付物**：
- 生产订单管理功能
- 库存和领料管理功能
- 生产进度跟踪功能

#### 第四阶段：优化和完善（10-12个月）

**目标**：系统优化和功能完善

**任务清单**：
- [ ] 服务性能优化
- [ ] 安全加固
- [ ] 完善监控和告警
- [ ] 完善文档和测试
- [ ] 用户培训和上线准备
- [ ] 生产环境部署

**交付物**：
- 优化后的系统
- 完整的文档和测试
- 生产环境部署方案

### 38.2 技术选型建议

#### 38.2.1 开发框架

**推荐方案**：
- **Python**: FastAPI（高性能、自动生成API文档）
- **Java**: Spring Boot（成熟稳定、生态丰富）
- **Node.js**: Express/Koa（适合轻量级服务）

**选择依据**：
- 团队技术栈
- 性能要求
- 开发效率
- 社区支持

#### 38.2.2 数据库

**推荐方案**：
- **主数据库**: PostgreSQL（功能强大、支持JSON）
- **缓存**: Redis（高性能缓存）
- **搜索引擎**: Elasticsearch（全文搜索）

#### 38.2.3 服务治理

**推荐方案**：
- **API网关**: Kong/Nginx（路由、限流、认证）
- **服务注册**: Consul/Nacos（服务发现）
- **配置中心**: Apollo/Nacos（配置管理）
- **监控**: Prometheus + Grafana（指标监控）
- **日志**: ELK Stack（日志收集和分析）
- **追踪**: Jaeger/Zipkin（分布式追踪）

#### 38.2.4 消息队列

**推荐方案**：
- **RabbitMQ**: 功能完善、可靠性高
- **Kafka**: 高吞吐量、适合大数据场景
- **Redis Streams**: 轻量级、适合简单场景

### 38.3 风险识别和应对

#### 38.3.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 服务间通信失败 | 高 | 实现重试、熔断、降级机制 |
| 数据一致性 | 高 | 使用分布式事务或最终一致性方案 |
| 性能瓶颈 | 中 | 性能测试、优化、扩容 |
| 服务依赖复杂 | 中 | 清晰定义依赖关系，避免循环依赖 |

#### 38.3.2 业务风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 需求变更 | 中 | 灵活的服务设计，支持快速迭代 |
| 用户接受度 | 中 | 充分测试，用户培训 |
| 数据迁移 | 高 | 制定详细迁移方案，充分测试 |

#### 38.3.3 运维风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 服务故障 | 高 | 多实例部署，自动故障转移 |
| 数据丢失 | 高 | 定期备份，数据恢复演练 |
| 安全漏洞 | 高 | 安全审计，及时更新补丁 |

---

## 三十九、服务模型度量指标

### 39.1 服务健康度指标

#### 39.1.1 可用性指标

| 指标 | 计算公式 | 目标值 | 说明 |
|------|---------|--------|------|
| 服务可用率 | (总时间 - 故障时间) / 总时间 × 100% | ≥ 99.9% | 服务正常运行时间占比 |
| 平均故障间隔时间（MTBF） | 总运行时间 / 故障次数 | ≥ 720小时 | 两次故障之间的平均时间 |
| 平均故障恢复时间（MTTR） | 总故障时间 / 故障次数 | ≤ 30分钟 | 故障恢复的平均时间 |

#### 39.1.2 性能指标

| 指标 | 计算公式 | 目标值 | 说明 |
|------|---------|--------|------|
| 平均响应时间 | 总响应时间 / 请求数 | < 500ms | 接口平均响应时间 |
| P95响应时间 | 95%请求的响应时间 | < 1000ms | 95%请求的响应时间 |
| P99响应时间 | 99%请求的响应时间 | < 2000ms | 99%请求的响应时间 |
| 吞吐量 | 成功请求数 / 时间 | ≥ 500 TPS | 每秒处理的事务数 |

#### 39.1.3 质量指标

| 指标 | 计算公式 | 目标值 | 说明 |
|------|---------|--------|------|
| 错误率 | 错误请求数 / 总请求数 × 100% | < 1% | 请求失败的比例 |
| 成功率 | 成功请求数 / 总请求数 × 100% | ≥ 99% | 请求成功的比例 |
| 代码覆盖率 | 测试覆盖代码行数 / 总代码行数 × 100% | ≥ 80% | 单元测试覆盖率 |

### 39.2 服务依赖指标

#### 39.2.1 依赖复杂度

| 指标 | 计算公式 | 目标值 | 说明 |
|------|---------|--------|------|
| 依赖服务数 | 直接依赖的服务数量 | < 5 | 服务直接依赖的其他服务数 |
| 依赖深度 | 依赖链的最大深度 | < 3 | 服务依赖链的最大层级 |
| 循环依赖数 | 循环依赖的数量 | 0 | 应避免循环依赖 |

#### 39.2.2 服务调用指标

| 指标 | 计算公式 | 目标值 | 说明 |
|------|---------|--------|------|
| 服务调用成功率 | 成功调用数 / 总调用数 × 100% | ≥ 99% | 跨服务调用的成功率 |
| 服务调用平均延迟 | 总调用延迟 / 调用次数 | < 100ms | 服务间调用的平均延迟 |
| 服务调用超时率 | 超时调用数 / 总调用数 × 100% | < 0.1% | 服务调用超时的比例 |

### 39.3 业务指标

#### 39.3.1 业务处理指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 订单创建成功率 | 订单创建成功的比例 | ≥ 99.5% |
| 审批流程完成时间 | 从提交到审批完成的时间 | < 24小时 |
| 库存准确率 | 库存数据准确的比例 | ≥ 99.9% |
| 生产订单按时完成率 | 按时完成的生产订单比例 | ≥ 95% |

#### 39.3.2 用户体验指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 页面加载时间 | 前端页面加载时间 | < 2秒 |
| 操作响应时间 | 用户操作的响应时间 | < 1秒 |
| 系统可用性 | 用户可正常使用系统的时间 | ≥ 99.5% |

---

## 四十、服务模型总结与展望

### 40.1 服务模型核心价值

#### 40.1.1 业务价值

1. **提升业务效率**：
   - 自动化业务流程，减少人工操作
   - 实时数据同步，提高决策效率
   - 标准化流程，减少错误

2. **增强业务灵活性**：
   - 模块化设计，支持快速迭代
   - 服务独立部署，支持灰度发布
   - 易于扩展新功能

3. **降低业务风险**：
   - 完善的审批流程，降低业务风险
   - 数据一致性保证，减少数据错误
   - 完整的操作日志，支持审计追踪

#### 40.1.2 技术价值

1. **提高开发效率**：
   - 清晰的接口定义，减少沟通成本
   - 标准化开发流程，提高代码质量
   - 完善的文档，降低学习成本

2. **提升系统性能**：
   - 服务独立扩展，优化资源利用
   - 缓存机制，提高响应速度
   - 异步处理，提高并发能力

3. **增强系统可靠性**：
   - 服务隔离，故障不影响其他服务
   - 熔断降级，保证核心功能可用
   - 多实例部署，提高可用性

### 40.2 服务模型优势

1. **模块化设计**：
   - 每个服务职责单一，边界清晰
   - 易于理解和维护
   - 支持独立开发和部署

2. **标准化接口**：
   - 遵循RESTful规范
   - 统一的请求/响应格式
   - 完善的错误处理

3. **完善的治理机制**：
   - 服务注册和发现
   - 监控和告警
   - 限流和熔断

4. **良好的扩展性**：
   - 支持水平扩展
   - 支持垂直扩展
   - 易于添加新服务

### 40.3 未来发展方向

#### 40.3.1 技术演进

1. **云原生架构**：
   - 容器化部署
   - Kubernetes编排
   - 服务网格（Service Mesh）

2. **智能化升级**：
   - AI辅助决策
   - 智能推荐
   - 预测性分析

3. **数据驱动**：
   - 大数据分析
   - 实时数据流处理
   - 数据可视化

#### 40.3.2 功能扩展

1. **移动端支持**：
   - 移动APP开发
   - 移动端审批
   - 移动端数据查询

2. **第三方集成**：
   - 与ERP系统集成
   - 与财务系统集成
   - 与供应链系统集成

3. **国际化支持**：
   - 多语言支持
   - 多时区支持
   - 多币种支持

#### 40.3.3 服务优化

1. **性能优化**：
   - 数据库优化
   - 缓存策略优化
   - 异步处理优化

2. **安全加固**：
   - 零信任安全模型
   - 数据加密增强
   - 安全审计完善

3. **用户体验优化**：
   - 界面优化
   - 交互优化
   - 响应速度优化

### 40.4 持续改进计划

#### 40.4.1 短期计划（3个月）

- 完善服务监控和告警
- 优化服务性能
- 完善测试覆盖
- 完善文档

#### 40.4.2 中期计划（6个月）

- 引入服务网格
- 实现智能推荐
- 优化用户体验
- 扩展移动端功能

#### 40.4.3 长期计划（12个月）

- 云原生架构升级
- AI能力集成
- 大数据分析平台
- 国际化支持

---

## 四十一、附录：服务模型快速参考

### 41.1 服务接口快速查找

#### 按业务场景查找

**客户管理场景**：
- 创建客户：`POST /api/sd/customers`
- 查询客户：`GET /api/sd/customers/{customer_id}`
- 更新客户：`PUT /api/sd/customers/{customer_id}`

**报价单管理场景**：
- 创建报价单：`POST /api/sd/quotations`
- 提交审批：`POST /api/sd/quotations/{quotation_number}/submit`
- 审批报价单：`POST /api/sd/quotations/{quotation_number}/approve`

**销售订单管理场景**：
- 创建订单：`POST /api/sd/sales-orders`
- 提交评审：`POST /api/sd/sales-orders/{order_number}/submit`
- 查看评审状态：`GET /api/sd/sales-orders/{order_number}/review-status`
- 审批订单：`POST /api/sd/sales-orders/{order_number}/approve`

**生产管理场景**：
- 创建生产订单：`POST /api/pp/production-orders`
- 下达订单：`POST /api/pp/production-orders/{order_number}/release`
- 开始生产：`POST /api/pp/production-orders/{order_number}/start`
- 查看进度：`GET /api/pp/production-orders/{order_number}/progress`

**物料管理场景**：
- 创建物料：`POST /api/mm/materials`
- 查询物料：`GET /api/mm/materials/{material_code}`
- 查询库存：`GET /api/mm/materials/{material_code}/inventory`
- 更新库存：`PUT /api/mm/materials/{material_code}/inventory`

### 41.2 常见错误码快速查找

| HTTP状态码 | 错误码 | 说明 | 解决方案 |
|-----------|--------|------|---------|
| 400 | VALIDATION_ERROR | 请求参数验证失败 | 检查请求参数格式和必填项 |
| 401 | UNAUTHORIZED | 未认证或令牌无效 | 重新登录获取新令牌 |
| 403 | FORBIDDEN | 权限不足 | 联系管理员分配权限 |
| 404 | NOT_FOUND | 资源不存在 | 检查资源ID是否正确 |
| 409 | CONFLICT | 资源冲突 | 检查唯一性约束 |
| 429 | RATE_LIMIT_EXCEEDED | 请求过于频繁 | 等待后重试 |
| 500 | INTERNAL_ERROR | 服务器内部错误 | 联系技术支持 |

### 41.3 服务依赖快速查找

**SDService依赖**：
- MMService：验证物料存在、获取物料信息
- ENGService：验证生产版本存在、获取生产版本信息
- WorkflowService：启动审批流程、推进工作流节点

**ENGService依赖**：
- MMService：验证物料存在、获取物料信息
- PPService：验证工作中心存在、获取工作中心信息

**PPService依赖**：
- SDService：获取销售订单信息、同步销售订单状态
- ENGService：获取生产版本信息、获取工艺路线信息
- MMService：获取物料信息

**MMService依赖**：
- PPService：验证生产订单存在、获取生产订单信息

**WorkflowService依赖**：
- UserService：验证用户角色权限、获取用户信息

**AuthService依赖**：
- UserService：查询用户信息、验证用户密码

---

## 四十二、服务测试用例示例

### 42.1 单元测试示例

#### 42.1.1 物料服务单元测试

```python
import pytest
from unittest.mock import Mock, patch
from services.mm.material_service import MaterialService
from services.mm.material_repository import MaterialRepository
from models.material import Material, MaterialStatus

class TestMaterialService:
    @pytest.fixture
    def mock_repository(self):
        return Mock(spec=MaterialRepository)
    
    @pytest.fixture
    def material_service(self, mock_repository):
        return MaterialService(repository=mock_repository)
    
    def test_create_material_success(self, material_service, mock_repository):
        # 准备测试数据
        request = CreateMaterialRequest(
            material_code="MAT-001",
            material_name="测试物料",
            category="原材料",
            unit="PCS"
        )
        
        # Mock依赖
        mock_repository.exists_by_code.return_value = False
        mock_repository.save.return_value = Material(
            material_code="MAT-001",
            material_name="测试物料",
            status=MaterialStatus.DRAFT
        )
        
        # 执行测试
        result = material_service.create_material(request)
        
        # 验证结果
        assert result.material_code == "MAT-001"
        assert result.status == MaterialStatus.DRAFT
        mock_repository.exists_by_code.assert_called_once_with("MAT-001")
        mock_repository.save.assert_called_once()
    
    def test_create_material_duplicate_code(self, material_service, mock_repository):
        # 准备测试数据
        request = CreateMaterialRequest(
            material_code="MAT-001",
            material_name="测试物料",
            category="原材料",
            unit="PCS"
        )
        
        # Mock依赖
        mock_repository.exists_by_code.return_value = True
        
        # 执行测试并验证异常
        with pytest.raises(BusinessException) as exc_info:
            material_service.create_material(request)
        
        assert "物料编码已存在" in str(exc_info.value)
    
    def test_get_material_not_found(self, material_service, mock_repository):
        # Mock依赖
        mock_repository.find_by_code.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(NotFoundException) as exc_info:
            material_service.get_material("MAT-999")
        
        assert "物料不存在" in str(exc_info.value)
```

#### 42.1.2 工作流服务单元测试

```python
class TestWorkflowInstanceService:
    def test_start_instance_success(self):
        # 测试启动工作流实例成功
        pass
    
    def test_approve_node_success(self):
        # 测试审批节点成功
        pass
    
    def test_approve_node_permission_denied(self):
        # 测试审批节点权限不足
        pass
    
    def test_reject_node_success(self):
        # 测试拒绝节点成功
        pass
```

### 42.2 集成测试示例

#### 42.2.1 销售订单创建集成测试

```python
import pytest
from httpx import AsyncClient
from app import app

@pytest.mark.asyncio
class TestSalesOrderIntegration:
    async def test_create_sales_order_success(self, client: AsyncClient, auth_token: str):
        # 准备测试数据
        request_data = {
            "customer_id": "CUST001",
            "product_number": "PROD-001",
            "quantity": 1000,
            "unit_price": 15.50,
            "delivery_date": "2025-12-31T00:00:00Z"
        }
        
        # 执行请求
        response = await client.post(
            "/api/sd/sales-orders",
            json=request_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # 验证响应
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["order_number"].startswith("SO-")
        assert data["status"] == "DRAFT"
        assert data["quantity"] == 1000
        assert data["total_amount"] == 15500.00
    
    async def test_create_sales_order_mapping_not_found(self, client: AsyncClient, auth_token: str):
        # 测试本厂编号映射不存在的情况
        request_data = {
            "customer_id": "CUST999",
            "product_number": "PROD-999",
            "quantity": 1000,
            "unit_price": 15.50,
            "delivery_date": "2025-12-31T00:00:00Z"
        }
        
        response = await client.post(
            "/api/sd/sales-orders",
            json=request_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "映射不存在" in response.json()["message"]
```

### 42.3 端到端测试示例

#### 42.3.1 完整业务流程测试

```python
@pytest.mark.asyncio
class TestCompleteBusinessFlow:
    async def test_quotation_to_production_order_flow(self, client: AsyncClient):
        """测试从报价单到生产订单的完整流程"""
        
        # 1. 创建报价单
        quotation_response = await client.post(
            "/api/sd/quotations",
            json={
                "customer_id": "CUST001",
                "product_number": "PROD-001",
                "quantity": 1000,
                "unit_price": 15.50
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        quotation_number = quotation_response.json()["data"]["quotation_number"]
        
        # 2. 提交报价单审批
        await client.post(
            f"/api/sd/quotations/{quotation_number}/submit",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # 3. 审批报价单（多级审批）
        # ... 审批流程
        
        # 4. 创建销售订单
        sales_order_response = await client.post(
            "/api/sd/sales-orders",
            json={
                "quotation_number": quotation_number,
                "customer_id": "CUST001",
                "product_number": "PROD-001",
                "quantity": 1000,
                "delivery_date": "2025-12-31T00:00:00Z"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        order_number = sales_order_response.json()["data"]["order_number"]
        
        # 5. 提交销售订单评审
        await client.post(
            f"/api/sd/sales-orders/{order_number}/submit",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # 6. 多部门评审
        # ... 评审流程
        
        # 7. 创建生产订单
        production_order_response = await client.post(
            "/api/pp/production-orders",
            json={"sales_order_number": order_number},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert production_order_response.status_code == 201
```

---

## 四十三、服务部署配置示例

### 43.1 Docker配置示例

#### 43.1.1 服务Dockerfile

```dockerfile
# 销售与分销服务Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=sd-service
ENV SERVICE_PORT=8001

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### 43.1.2 Docker Compose配置

```yaml
version: '3.8'

services:
  # 数据库
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: hserp
      POSTGRES_USER: hserp_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hserp_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 销售与分销服务
  sd-service:
    build:
      context: ./services/sd
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://hserp_user:${DB_PASSWORD}@postgres:5432/hserp
      - REDIS_URL=redis://redis:6379
      - MM_SERVICE_URL=http://mm-service:8002
      - ENG_SERVICE_URL=http://eng-service:8003
      - WORKFLOW_SERVICE_URL=http://workflow-service:8007
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 物料管理服务
  mm-service:
    build:
      context: ./services/mm
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://hserp_user:${DB_PASSWORD}@postgres:5432/hserp
      - REDIS_URL=redis://redis:6379
      - PP_SERVICE_URL=http://pp-service:8005
    ports:
      - "8002:8002"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # API网关
  api-gateway:
    image: kong:3.4
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: postgres
      KONG_PG_DATABASE: kong
      KONG_PG_USER: kong_user
      KONG_PG_PASSWORD: ${KONG_PASSWORD}
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

### 43.2 Kubernetes配置示例

#### 43.2.1 Deployment配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sd-service
  namespace: hserp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sd-service
  template:
    metadata:
      labels:
        app: sd-service
    spec:
      containers:
      - name: sd-service
        image: hserp/sd-service:1.0.0
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: sd-service
  namespace: hserp
spec:
  selector:
    app: sd-service
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

#### 43.2.2 ConfigMap配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sd-service-config
  namespace: hserp
data:
  service.name: "sd-service"
  service.port: "8001"
  logging.level: "INFO"
  cache.ttl: "3600"
  pagination.default_limit: "100"
  pagination.max_limit: "1000"
```

#### 43.2.3 Secret配置

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: hserp
type: Opaque
stringData:
  url: "postgresql://user:password@postgres:5432/hserp"
  password: "your-secret-password"
```

---

## 四十四、服务监控配置示例

### 44.1 Prometheus监控配置

#### 44.1.1 服务指标暴露

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 请求计数器
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟直方图
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# 活跃连接数
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# 业务指标
orders_created = Counter(
    'orders_created_total',
    'Total orders created',
    ['customer_id', 'status']
)

# 中间件
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    status_code = response.status_code
    
    # 记录指标
    request_count.labels(method=method, endpoint=endpoint, status=status_code).inc()
    request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response

# 指标端点
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

#### 44.1.2 Prometheus配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'sd-service'
    static_configs:
      - targets: ['sd-service:8001']
    metrics_path: '/metrics'
    
  - job_name: 'mm-service'
    static_configs:
      - targets: ['mm-service:8002']
    metrics_path: '/metrics'
    
  - job_name: 'eng-service'
    static_configs:
      - targets: ['eng-service:8003']
    metrics_path: '/metrics'
```

### 44.2 Grafana仪表板配置

#### 44.2.1 服务健康仪表板

```json
{
  "dashboard": {
    "title": "服务健康监控",
    "panels": [
      {
        "title": "服务可用性",
        "targets": [
          {
            "expr": "up{service=\"sd-service\"}",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "请求响应时间",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
            "legendFormat": "P95响应时间"
          }
        ]
      },
      {
        "title": "错误率",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "错误率"
          }
        ]
      }
    ]
  }
}
```

---

## 四十五、服务性能调优指南

### 45.1 数据库性能优化

#### 45.1.1 索引优化

```sql
-- 为常用查询字段创建索引
CREATE INDEX idx_sales_order_customer ON sales_orders(customer_id);
CREATE INDEX idx_sales_order_status ON sales_orders(status);
CREATE INDEX idx_sales_order_created ON sales_orders(created_at);

-- 复合索引优化多条件查询
CREATE INDEX idx_sales_order_customer_status ON sales_orders(customer_id, status);
```

#### 45.1.2 查询优化

```python
# 避免N+1查询问题
# 不好的做法
for order in orders:
    customer = get_customer(order.customer_id)  # N次查询

# 好的做法
customer_ids = [order.customer_id for order in orders]
customers = get_customers_by_ids(customer_ids)  # 1次查询
customer_map = {c.id: c for c in customers}
for order in orders:
    customer = customer_map[order.customer_id]
```

#### 45.1.3 连接池优化

```python
# 数据库连接池配置
DATABASE_POOL_CONFIG = {
    "min_size": 10,
    "max_size": 100,
    "max_queries": 50000,
    "max_inactive_connection_lifetime": 300,
    "timeout": 30
}
```

### 45.2 缓存优化

#### 45.2.1 缓存策略

```python
# 多级缓存策略
class CacheStrategy:
    # L1: 本地缓存（内存）
    local_cache = TTLCache(maxsize=1000, ttl=60)
    
    # L2: Redis缓存
    redis_cache = RedisCache(ttl=3600)
    
    def get(self, key: str):
        # 先查本地缓存
        value = self.local_cache.get(key)
        if value:
            return value
        
        # 再查Redis缓存
        value = self.redis_cache.get(key)
        if value:
            self.local_cache[key] = value
            return value
        
        # 最后查数据库
        value = self.database.get(key)
        if value:
            self.redis_cache.set(key, value)
            self.local_cache[key] = value
        return value
```

#### 45.2.2 缓存预热

```python
# 服务启动时预热热点数据
async def warmup_cache():
    # 预热常用物料数据
    popular_materials = await get_popular_materials()
    for material in popular_materials:
        await cache.set(f"material:{material.code}", material)
    
    # 预热工作流定义
    workflows = await get_all_workflows()
    for workflow in workflows:
        await cache.set(f"workflow:{workflow.id}", workflow)
```

### 45.3 异步处理优化

#### 45.3.1 异步任务队列

```python
# 使用Celery处理耗时任务
from celery import Celery

app = Celery('hserp')

@app.task
def process_sales_order_async(order_id: str):
    # 异步处理销售订单
    order = get_sales_order(order_id)
    # 发送通知
    send_notification(order)
    # 生成报表
    generate_report(order)
    # 更新统计
    update_statistics(order)
```

#### 45.3.2 批量处理

```python
# 批量处理提高效率
async def batch_create_orders(orders: List[Order]):
    # 批量验证
    customer_ids = [o.customer_id for o in orders]
    customers = await batch_get_customers(customer_ids)
    
    # 批量创建
    created_orders = await batch_create(orders)
    
    # 批量发送通知
    await batch_send_notifications(created_orders)
    
    return created_orders
```

### 45.4 代码优化

#### 45.4.1 减少数据库查询

```python
# 使用预加载减少查询
from sqlalchemy.orm import joinedload

# 不好的做法
orders = session.query(SalesOrder).all()
for order in orders:
    customer = order.customer  # 每次查询数据库

# 好的做法
orders = session.query(SalesOrder).options(
    joinedload(SalesOrder.customer)
).all()
for order in orders:
    customer = order.customer  # 已预加载，不查询数据库
```

#### 45.4.2 使用生成器处理大数据

```python
# 使用生成器处理大量数据，避免内存溢出
def get_all_orders():
    offset = 0
    limit = 1000
    while True:
        orders = get_orders(offset=offset, limit=limit)
        if not orders:
            break
        for order in orders:
            yield order
        offset += limit
```

---

## 四十六、服务故障排查指南

### 46.1 常见故障类型

#### 46.1.1 服务不可用

**症状**：
- 服务健康检查失败
- 请求返回503错误
- 服务实例无法启动

**排查步骤**：
1. 检查服务日志
2. 检查服务资源使用情况（CPU、内存）
3. 检查数据库连接
4. 检查依赖服务状态
5. 检查网络连接

**解决方案**：
```bash
# 查看服务日志
docker logs sd-service

# 检查服务资源
docker stats sd-service

# 重启服务
docker restart sd-service

# 检查数据库连接
psql -h postgres -U hserp_user -d hserp -c "SELECT 1"
```

#### 46.1.2 性能问题

**症状**：
- 响应时间过长
- 请求超时
- 数据库连接池耗尽

**排查步骤**：
1. 分析慢查询日志
2. 检查数据库索引
3. 检查缓存命中率
4. 分析服务调用链
5. 检查资源使用情况

**解决方案**：
```sql
-- 查看慢查询
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- 分析查询计划
EXPLAIN ANALYZE SELECT * FROM sales_orders WHERE customer_id = 'CUST001';
```

#### 46.1.3 数据一致性问题

**症状**：
- 跨服务数据不一致
- 事务回滚失败
- 数据丢失

**排查步骤**：
1. 检查事务日志
2. 检查服务调用顺序
3. 检查数据同步状态
4. 检查补偿机制

**解决方案**：
```python
# 实现数据一致性检查
async def check_data_consistency():
    # 检查销售订单和生产订单一致性
    sales_orders = await get_sales_orders()
    for order in sales_orders:
        production_orders = await get_production_orders_by_sales_order(order.id)
        if not production_orders and order.status == 'APPROVED':
            logger.warning(f"数据不一致: 销售订单{order.id}已批准但无生产订单")
```

### 46.2 故障排查工具

#### 46.2.1 日志分析

```bash
# 查看错误日志
grep "ERROR" /var/log/sd-service.log | tail -100

# 查看特定时间段的日志
grep "2025-12-12 10:" /var/log/sd-service.log

# 统计错误类型
grep "ERROR" /var/log/sd-service.log | awk '{print $5}' | sort | uniq -c
```

#### 46.2.2 性能分析

```python
# 使用性能分析工具
import cProfile
import pstats

def profile_function(func):
    profiler = cProfile.Profile()
    profiler.enable()
    result = func()
    profiler.disable()
    
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    
    return result
```

#### 46.2.3 分布式追踪

```python
# 使用Jaeger进行分布式追踪
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# 在服务调用中使用
with tracer.start_as_current_span("create_sales_order"):
    # 服务调用代码
    pass
```

### 46.3 故障恢复流程

#### 46.3.1 故障检测

```python
# 自动故障检测
class HealthChecker:
    async def check_service_health(self):
        checks = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "dependencies": await self.check_dependencies()
        }
        
        if not all(checks.values()):
            # 触发告警
            await self.send_alert(checks)
            return False
        return True
```

#### 46.3.2 自动恢复

```python
# 自动故障恢复
class AutoRecovery:
    async def recover_service(self, service_name: str):
        # 1. 尝试重启服务
        await self.restart_service(service_name)
        
        # 2. 等待服务恢复
        await asyncio.sleep(30)
        
        # 3. 检查服务状态
        if await self.check_service_health(service_name):
            logger.info(f"服务{service_name}已恢复")
            return True
        
        # 4. 如果重启失败，切换到备用实例
        await self.failover_to_backup(service_name)
        return False
```

---

## 四十七、服务安全配置指南

### 47.1 认证安全配置

#### 47.1.1 JWT配置

```python
# JWT安全配置
JWT_CONFIG = {
    "algorithm": "HS256",
    "secret_key": os.getenv("JWT_SECRET_KEY"),  # 从环境变量读取
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "issuer": "hserp",
    "audience": "hserp-api"
}

# 令牌刷新机制
@app.post("/api/auth/refresh")
async def refresh_token(refresh_token: str):
    # 验证刷新令牌
    payload = verify_refresh_token(refresh_token)
    
    # 生成新访问令牌
    new_access_token = create_access_token(payload["user_id"])
    
    return {"access_token": new_access_token}
```

#### 47.1.2 密码安全

```python
# 密码加密配置
PASSWORD_CONFIG = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digits": True,
    "require_special_chars": True,
    "bcrypt_rounds": 12
}

# 密码验证
def validate_password(password: str) -> bool:
    if len(password) < PASSWORD_CONFIG["min_length"]:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*]', password):
        return False
    return True
```

### 47.2 授权安全配置

#### 47.2.1 角色权限配置

```python
# 角色权限矩阵
ROLE_PERMISSIONS = {
    "ADMIN": ["*"],  # 所有权限
    "SALES": [
        "sd:customer:create",
        "sd:customer:read",
        "sd:quotation:create",
        "sd:quotation:read",
        "sd:sales_order:create",
        "sd:sales_order:read"
    ],
    "SALES_MANAGER": [
        "sd:*:read",
        "sd:quotation:approve",
        "sd:sales_order:approve"
    ],
    "ENGINEER": [
        "eng:*:create",
        "eng:*:read",
        "eng:*:update"
    ]
}

# 权限检查装饰器
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user.has_permission(permission):
                raise ForbiddenException("权限不足")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 47.2.2 API限流配置

```python
# API限流配置
RATE_LIMIT_CONFIG = {
    "per_user": {
        "requests": 100,
        "window": 60  # 每分钟100次
    },
    "per_ip": {
        "requests": 1000,
        "window": 60  # 每分钟1000次
    },
    "per_endpoint": {
        "/api/auth/login": {
            "requests": 5,
            "window": 60  # 登录接口更严格
        }
    }
}

# 限流中间件
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(request: Request):
    # 登录逻辑
    pass
```

### 47.3 数据安全配置

#### 47.3.1 数据加密

```python
# 敏感数据加密
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY")
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# 使用示例
encryption = DataEncryption()
encrypted_phone = encryption.encrypt(user.phone)
```

#### 47.3.2 SQL注入防护

```python
# 使用参数化查询，防止SQL注入
# 不好的做法
query = f"SELECT * FROM users WHERE username = '{username}'"

# 好的做法
query = "SELECT * FROM users WHERE username = :username"
result = await db.execute(query, {"username": username})

# 使用ORM，自动防护SQL注入
user = await User.query.where(User.username == username).first()
```

### 47.4 传输安全配置

#### 47.4.1 HTTPS配置

```python
# HTTPS配置
SSL_CONFIG = {
    "certfile": "/path/to/cert.pem",
    "keyfile": "/path/to/key.pem",
    "ca_certs": "/path/to/ca.pem"
}

# 启动HTTPS服务
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        ssl_keyfile=SSL_CONFIG["keyfile"],
        ssl_certfile=SSL_CONFIG["certfile"]
    )
```

#### 47.4.2 CORS配置

```python
# CORS安全配置
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hserp.example.com"],  # 只允许特定域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600
)
```

---

## 四十八、服务日志配置指南

### 48.1 日志格式配置

#### 48.1.1 结构化日志

```python
# 使用结构化日志
import structlog

logger = structlog.get_logger()

# 记录业务日志
logger.info(
    "sales_order_created",
    order_number="SO-2025-001",
    customer_id="CUST001",
    total_amount=10000.00,
    created_by="user001"
)
```

#### 48.1.2 日志级别配置

```python
# 日志级别配置
import logging

LOG_LEVELS = {
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.WARNING
}

# 根据环境设置日志级别
log_level = LOG_LEVELS.get(os.getenv("ENV", "development"))
logging.basicConfig(level=log_level)

# 不同模块设置不同日志级别
logger_config = {
    "root": logging.INFO,
    "hserp.auth": logging.DEBUG,
    "hserp.sd": logging.INFO,
    "hserp.eng": logging.INFO,
    "hserp.pp": logging.INFO,
    "hserp.mm": logging.INFO,
    "hserp.workflow": logging.DEBUG
}

for module, level in logger_config.items():
    logging.getLogger(module).setLevel(level)
```

#### 48.1.3 日志格式配置

```python
# 统一日志格式配置
LOG_FORMAT = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/hserp/app.log",
            "formatter": "json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO"
    }
}
```

### 48.2 日志存储配置

#### 48.2.1 日志文件存储

```python
# 日志文件存储配置
LOG_STORAGE_CONFIG = {
    "base_path": "/var/log/hserp",
    "services": {
        "auth": {
            "path": "/var/log/hserp/auth",
            "max_size": "100MB",
            "backup_count": 10
        },
        "sd": {
            "path": "/var/log/hserp/sd",
            "max_size": "500MB",
            "backup_count": 20
        },
        "eng": {
            "path": "/var/log/hserp/eng",
            "max_size": "500MB",
            "backup_count": 20
        },
        "pp": {
            "path": "/var/log/hserp/pp",
            "max_size": "500MB",
            "backup_count": 20
        },
        "mm": {
            "path": "/var/log/hserp/mm",
            "max_size": "500MB",
            "backup_count": 20
        },
        "workflow": {
            "path": "/var/log/hserp/workflow",
            "max_size": "200MB",
            "backup_count": 10
        }
    }
}

# 日志文件命名规则
def get_log_filename(service_name: str, log_type: str = "app") -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"{LOG_STORAGE_CONFIG['services'][service_name]['path']}/{log_type}-{date_str}.log"
```

#### 48.2.2 日志集中存储（ELK Stack）

```python
# ELK Stack配置
ELK_CONFIG = {
    "elasticsearch": {
        "hosts": ["http://elasticsearch:9200"],
        "index_prefix": "hserp",
        "index_pattern": "hserp-{service}-{date}"
    },
    "logstash": {
        "host": "logstash",
        "port": 5044
    },
    "kibana": {
        "url": "http://kibana:5601"
    }
}

# 发送日志到ELK
from pythonjsonlogger import jsonlogger
import logging.handlers

class ELKHandler(logging.Handler):
    def __init__(self, elk_config):
        super().__init__()
        self.elk_config = elk_config
        # 初始化Elasticsearch客户端
        from elasticsearch import Elasticsearch
        self.es = Elasticsearch(elk_config["elasticsearch"]["hosts"])
    
    def emit(self, record):
        log_entry = self.format(record)
        # 发送到Elasticsearch
        index_name = f"hserp-{record.service}-{datetime.now().strftime('%Y.%m.%d')}"
        self.es.index(index=index_name, body=log_entry)
```

#### 48.2.3 日志数据库存储

```python
# 重要日志存储到数据库
class DatabaseLogHandler(logging.Handler):
    def __init__(self, db_session):
        super().__init__()
        self.db = db_session
    
    def emit(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
            "user_id": getattr(record, "user_id", None),
            "request_id": getattr(record, "request_id", None),
            "extra_data": getattr(record, "extra_data", {})
        }
        
        # 只存储ERROR和WARNING级别的日志
        if record.levelno >= logging.WARNING:
            self.db.execute(
                "INSERT INTO system_logs (timestamp, level, service, module, function, message, user_id, request_id, extra_data) "
                "VALUES (:timestamp, :level, :service, :module, :function, :message, :user_id, :request_id, :extra_data)",
                log_entry
            )
            self.db.commit()
```

### 48.3 日志查询和分析

#### 48.3.1 日志查询接口

```python
# 日志查询服务
from fastapi import Query
from typing import Optional
from datetime import datetime

@app.get("/api/admin/logs")
async def query_logs(
    service: Optional[str] = Query(None, description="服务名称"),
    level: Optional[str] = Query(None, description="日志级别"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    request_id: Optional[str] = Query(None, description="请求ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    查询系统日志
    """
    query = build_log_query(
        service=service,
        level=level,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        request_id=request_id,
        keyword=keyword
    )
    
    logs = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    total = await db.execute(query.count())
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

#### 48.3.2 日志统计分析

```python
# 日志统计分析
@app.get("/api/admin/logs/statistics")
async def get_log_statistics(
    service: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """
    获取日志统计信息
    """
    # 按级别统计
    level_stats = await db.execute("""
        SELECT level, COUNT(*) as count
        FROM system_logs
        WHERE (:service IS NULL OR service = :service)
        AND (:start_time IS NULL OR timestamp >= :start_time)
        AND (:end_time IS NULL OR timestamp <= :end_time)
        GROUP BY level
    """, {
        "service": service,
        "start_time": start_time,
        "end_time": end_time
    })
    
    # 按服务统计
    service_stats = await db.execute("""
        SELECT service, COUNT(*) as count
        FROM system_logs
        WHERE (:start_time IS NULL OR timestamp >= :start_time)
        AND (:end_time IS NULL OR timestamp <= :end_time)
        GROUP BY service
    """, {
        "start_time": start_time,
        "end_time": end_time
    })
    
    # 错误趋势分析
    error_trend = await db.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM system_logs
        WHERE level = 'ERROR'
        AND (:service IS NULL OR service = :service)
        AND (:start_time IS NULL OR timestamp >= :start_time)
        AND (:end_time IS NULL OR timestamp <= :end_time)
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, {
        "service": service,
        "start_time": start_time,
        "end_time": end_time
    })
    
    return {
        "level_statistics": level_stats,
        "service_statistics": service_stats,
        "error_trend": error_trend
    }
```

### 48.4 日志轮转和清理

#### 48.4.1 日志轮转配置

```python
# 日志轮转配置
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# 按大小轮转
rotating_handler = RotatingFileHandler(
    filename="/var/log/hserp/app.log",
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=10,
    encoding="utf-8"
)

# 按时间轮转（每天）
timed_handler = TimedRotatingFileHandler(
    filename="/var/log/hserp/app.log",
    when="midnight",
    interval=1,
    backupCount=30,  # 保留30天
    encoding="utf-8"
)

# 日志压缩
import gzip
import shutil

def compress_log_file(log_file: str):
    """压缩日志文件"""
    with open(log_file, "rb") as f_in:
        with gzip.open(f"{log_file}.gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(log_file)
```

#### 48.4.2 日志清理策略

```python
# 日志清理配置
LOG_CLEANUP_CONFIG = {
    "retention_days": {
        "DEBUG": 7,      # DEBUG日志保留7天
        "INFO": 30,      # INFO日志保留30天
        "WARNING": 90,   # WARNING日志保留90天
        "ERROR": 365,    # ERROR日志保留1年
        "CRITICAL": 730  # CRITICAL日志保留2年
    },
    "cleanup_schedule": "0 2 * * *"  # 每天凌晨2点执行清理
}

# 日志清理任务
async def cleanup_old_logs():
    """清理过期日志"""
    cutoff_date = datetime.now() - timedelta(days=max(LOG_CLEANUP_CONFIG["retention_days"].values()))
    
    # 清理文件日志
    for service, config in LOG_STORAGE_CONFIG["services"].items():
        log_path = config["path"]
        for log_file in os.listdir(log_path):
            file_path = os.path.join(log_path, log_file)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    os.remove(file_path)
                    logger.info(f"删除过期日志文件: {file_path}")
    
    # 清理数据库日志
    await db.execute("""
        DELETE FROM system_logs
        WHERE timestamp < :cutoff_date
        AND level NOT IN ('ERROR', 'CRITICAL')
    """, {"cutoff_date": cutoff_date})
    
    logger.info("日志清理完成")
```

### 48.5 日志最佳实践

#### 48.5.1 日志记录原则

1. **记录关键操作**：
   - 用户登录/登出
   - 数据创建/修改/删除
   - 审批流程状态变更
   - 系统错误和异常

2. **避免记录敏感信息**：
   - 不记录密码、令牌等敏感信息
   - 不记录完整的信用卡号、身份证号
   - 对敏感数据进行脱敏处理

3. **使用合适的日志级别**：
   - DEBUG：详细的调试信息
   - INFO：一般信息，记录业务流程
   - WARNING：警告信息，不影响功能但需要注意
   - ERROR：错误信息，功能受影响
   - CRITICAL：严重错误，系统可能无法继续运行

#### 48.5.2 日志性能优化

```python
# 异步日志记录，避免阻塞主线程
import asyncio
from queue import Queue
import threading

class AsyncLogHandler(logging.Handler):
    def __init__(self, target_handler):
        super().__init__()
        self.target_handler = target_handler
        self.queue = Queue()
        self.thread = threading.Thread(target=self._process_logs, daemon=True)
        self.thread.start()
    
    def emit(self, record):
        self.queue.put(record)
    
    def _process_logs(self):
        while True:
            try:
                record = self.queue.get(timeout=1)
                self.target_handler.emit(record)
            except:
                continue

# 使用示例
file_handler = logging.FileHandler("/var/log/hserp/app.log")
async_handler = AsyncLogHandler(file_handler)
logger.addHandler(async_handler)
```

#### 48.5.3 日志监控和告警

```python
# 日志监控配置
LOG_MONITORING_CONFIG = {
    "error_threshold": {
        "per_minute": 10,      # 每分钟错误数阈值
        "per_hour": 100        # 每小时错误数阈值
    },
    "alert_channels": ["email", "slack", "sms"]
}

# 日志监控服务
class LogMonitor:
    def __init__(self):
        self.error_count = {}
        self.last_check = datetime.now()
    
    async def check_error_rate(self):
        """检查错误率"""
        current_time = datetime.now()
        
        # 统计最近一分钟的错误数
        recent_errors = await db.execute("""
            SELECT COUNT(*) as count
            FROM system_logs
            WHERE level = 'ERROR'
            AND timestamp >= :since
        """, {
            "since": current_time - timedelta(minutes=1)
        })
        
        if recent_errors > LOG_MONITORING_CONFIG["error_threshold"]["per_minute"]:
            await self.send_alert(
                f"错误日志过多：最近1分钟有{recent_errors}条错误日志"
            )
    
    async def send_alert(self, message: str):
        """发送告警"""
        for channel in LOG_MONITORING_CONFIG["alert_channels"]:
            if channel == "email":
                await send_email_alert(message)
            elif channel == "slack":
                await send_slack_alert(message)
            elif channel == "sms":
                await send_sms_alert(message)

# 定期检查
async def monitor_logs():
    monitor = LogMonitor()
    while True:
        await monitor.check_error_rate()
        await asyncio.sleep(60)  # 每分钟检查一次
```

---

## 四十九、服务文档更新记录

### 49.1 版本历史

| 版本 | 日期 | 更新内容 | 更新人 |
|------|------|---------|--------|
| v1.0 | 2025-01-01 | 初始版本，包含基础服务模型 | 系统架构师 |
| v1.1 | 2025-02-15 | 添加服务编排和组合场景 | 系统架构师 |
| v1.2 | 2025-03-20 | 完善服务治理和最佳实践 | 系统架构师 |
| v1.3 | 2025-12-12 | 添加服务配置指南和故障排查 | 系统架构师 |

### 49.2 文档维护

**维护责任人**：系统架构师团队

**维护流程**：
1. 服务接口变更时，需同步更新本文档
2. 新增服务时，需添加对应的服务模型描述
3. 服务版本升级时，需更新版本历史记录
4. 定期审查文档，确保与实际实现保持一致

**文档审核**：
- 技术负责人审核服务接口设计
- 架构师审核服务依赖关系
- 运维团队审核部署和监控配置

### 49.3 变更管理

#### 49.3.1 变更类型

| 变更类型 | 影响范围 | 审批级别 | 文档更新要求 |
|---------|---------|---------|------------|
| 新增服务 | 系统架构 | 架构委员会 | 新增章节 |
| 服务接口变更 | 服务契约 | 技术负责人 | 更新接口定义 |
| 服务依赖变更 | 服务关系 | 架构师 | 更新依赖关系图 |
| 配置变更 | 部署运维 | 运维负责人 | 更新配置示例 |
| 文档修正 | 文档质量 | 文档维护人 | 更新对应章节 |

#### 49.3.2 变更流程

```mermaid
graph TD
    A[提出变更需求] --> B{变更类型}
    B -->|重大变更| C[架构委员会评审]
    B -->|一般变更| D[技术负责人评审]
    C --> E[批准变更]
    D --> E
    E --> F[实施变更]
    F --> G[更新文档]
    G --> H[文档审核]
    H --> I[发布新版本]
```

### 49.4 文档质量保证

#### 49.4.1 文档检查清单

- [ ] 所有服务接口都有完整的请求/响应契约
- [ ] 服务依赖关系图准确反映实际依赖
- [ ] 错误处理规范覆盖所有错误场景
- [ ] 配置示例经过验证，可直接使用
- [ ] 代码示例语法正确，可运行
- [ ] 术语表包含所有专业术语
- [ ] 版本历史记录完整

#### 49.4.2 文档审查标准

1. **完整性**：所有章节内容完整，无遗漏
2. **准确性**：技术描述准确，与实际实现一致
3. **清晰性**：表达清晰，易于理解
4. **一致性**：术语使用一致，格式统一
5. **实用性**：配置示例和代码可直接使用

---

## 五十、服务模型文档总结

### 50.1 文档概述

本文档全面描述了某某ERP系统的服务模型，涵盖了从服务设计、实现、部署到运维的完整生命周期。文档共包含50个章节，详细定义了7个核心业务服务的接口规范、依赖关系、安全要求、性能指标等。

### 50.2 核心服务模块

本文档定义了以下核心服务模块：

1. **认证服务（Auth Service）**：提供用户认证和授权功能
2. **用户管理服务（User Service）**：管理用户和角色信息
3. **销售与分销服务（SD Service）**：处理客户、报价单、销售订单等业务
4. **工程管理服务（ENG Service）**：管理BOM、工艺路线、MI、生产版本
5. **生产计划与控制服务（PP Service）**：管理工作中心、生产订单、工序报工
6. **物料管理服务（MM Service）**：管理物料主数据、库存、领料
7. **工作流服务（Workflow Service）**：提供审批流程引擎

### 50.3 服务设计原则

文档遵循以下服务设计原则：

- **单一职责原则**：每个服务只负责一个业务领域
- **接口隔离原则**：服务接口设计简洁、明确
- **依赖倒置原则**：服务之间通过接口交互，降低耦合
- **契约优先**：服务接口定义明确，遵循OpenAPI规范
- **无状态设计**：服务调用不依赖会话状态
- **幂等性**：关键操作支持幂等性，可安全重试

### 50.4 文档结构

文档分为以下几个主要部分：

1. **基础服务模型**（第一至十九章）：定义核心服务接口和规范
2. **服务扩展**（第二十至三十章）：服务编排、治理、最佳实践
3. **实施参考**（第三十一至四十章）：实现参考、检查清单、路线图
4. **配置指南**（第四十一至四十八章）：测试、部署、监控、性能、故障排查、安全、日志配置
5. **文档管理**（第四十九至五十章）：文档更新记录和总结

### 50.5 关键特性

#### 50.5.1 服务契约规范

- 所有服务接口遵循RESTful设计原则
- 使用OpenAPI 3.0规范定义接口契约
- 统一的请求/响应格式
- 完善的错误处理机制

#### 50.5.2 服务治理

- 服务注册与发现
- 负载均衡和容错机制
- 服务监控和告警
- 服务版本管理

#### 50.5.3 安全机制

- JWT令牌认证
- 基于角色的访问控制（RBAC）
- API限流保护
- 数据加密和传输安全

#### 50.5.4 运维支持

- 完整的部署配置示例
- 监控和日志配置指南
- 性能调优建议
- 故障排查手册

### 50.6 使用建议

#### 50.6.1 对于开发人员

1. 阅读第三至九章，了解各服务的接口规范
2. 参考第三十一章的服务实现参考
3. 遵循第十二章的错误处理规范
4. 使用第四十二章的测试用例示例

#### 50.6.2 对于架构师

1. 关注第一、二章的服务架构设计
2. 审查第十章的服务依赖关系
3. 参考第二十二至二十九章的服务治理和最佳实践
4. 使用第三十八章的实施路线图

#### 50.6.3 对于运维人员

1. 参考第十八章的服务部署规范
2. 使用第四十三章的部署配置示例
3. 配置第四十四章的监控方案
4. 遵循第四十六章的故障排查指南

### 50.7 后续工作

#### 50.7.1 文档完善

- 根据实际实施经验，持续完善服务模型
- 补充更多实际场景的服务编排示例
- 增加服务性能基准测试数据
- 完善服务监控指标和告警规则

#### 50.7.2 服务演进

- 根据业务发展需要，扩展新的服务模块
- 优化现有服务的性能和可用性
- 引入微服务治理框架（如Istio、Consul等）
- 实现服务网格（Service Mesh）架构

#### 50.7.3 技术升级

- 考虑引入GraphQL作为服务查询接口
- 探索事件驱动架构（Event-Driven Architecture）
- 引入服务编排引擎（如Camunda、Zeebe）
- 实现服务链路追踪（如Jaeger、Zipkin）

### 50.8 联系信息

**文档维护团队**：
- 系统架构师：负责服务模型设计和文档维护
- 技术负责人：负责服务实现和技术决策
- 运维团队：负责服务部署和运维支持

**反馈渠道**：
- 文档问题反馈：通过项目管理系统提交Issue
- 技术咨询：联系系统架构师团队
- 紧急问题：联系技术负责人

---

## 附录：文档索引

### 快速导航

#### 服务接口定义
- [认证服务](#三认证服务auth-service) - 第3章
- [用户管理服务](#四用户管理服务user-service) - 第4章
- [销售与分销服务](#五销售与分销服务sd-service) - 第5章
- [工程管理服务](#六工程管理服务eng-service) - 第6章
- [生产计划与控制服务](#七生产计划与控制服务pp-service) - 第7章
- [物料管理服务](#八物料管理服务mm-service) - 第8章
- [工作流服务](#九工作流服务workflow-service) - 第9章

#### 服务规范
- [服务契约规范](#十一服务契约规范) - 第11章
- [错误处理规范](#十二错误处理规范) - 第12章
- [服务版本管理](#十三服务版本管理) - 第13章
- [服务安全规范](#十四服务安全规范) - 第14章
- [服务性能要求](#十五服务性能要求) - 第15章

#### 实施指南
- [服务实现参考](#三十一服务实现参考) - 第31章
- [服务部署配置示例](#四十三服务部署配置示例) - 第43章
- [服务监控配置示例](#四十四服务监控配置示例) - 第44章
- [服务性能调优指南](#四十五服务性能调优指南) - 第45章
- [服务故障排查指南](#四十六服务故障排查指南) - 第46章

#### 最佳实践
- [服务最佳实践](#二十三服务最佳实践) - 第23章
- [服务安全最佳实践](#二十五服务安全最佳实践) - 第25章
- [服务运维最佳实践](#二十六服务运维最佳实践) - 第26章

---

**文档结束**

---

*本文档版本：v1.3*  
*最后更新：2025-12-12*  
*文档总页数：约350页（基于标准A4格式）*  
*文档总字数：约15万字*