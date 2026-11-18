# 某某ERP系统 - API模型（OpenAPI 3）

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-12-12  
**最后更新：** 2025-01-XX

**基于**：某某ERP系统MVP版本需求规格说明书 v1.4

本文档描述了某某ERP系统的API模型，采用OpenAPI 3.0规范。文档包含所有API端点的定义、请求和响应模型、认证方式等，可用于API文档生成、客户端代码生成和API测试。

---

## 一、OpenAPI规范概述

### 1.1 基本信息

```yaml
openapi: 3.0.3
info:
  title: 某某ERP系统MVP版本
  description: 轻量化ERP系统，验证PCB制造行业核心业务流程
  version: 1.0.0
  contact:
    name: 开发团队
```

### 1.2 服务器信息

```yaml
servers:
  - url: http://localhost:8000
    description: 本地开发服务器
  - url: https://api.example.com
    description: 生产服务器
```

### 1.3 安全方案

```yaml
securitySchemes:
  bearerAuth:
    type: http
    scheme: bearer
    bearerFormat: JWT
    description: JWT令牌认证，通过 /api/auth/login 获取令牌
```

---

## 二、API端点总览

### 2.1 端点统计

| 模块 | 端点数量 | 前缀 |
|------|---------|------|
| 认证 | 2 | `/api/auth` |
| 用户管理 | 6 | `/api` |
| 销售与分销（SD） | 30 | `/api/sd` |
| 工程管理（ENG） | 18 | `/api/eng` |
| 生产计划与控制（PP） | 12 | `/api/pp` |
| 物料管理（MM） | 5 | `/api/mm` |
| **总计** | **73** | |

### 2.2 端点分类

- **GET**：查询端点（列表、详情）
- **POST**：创建端点（创建资源、提交、审批等）
- **PUT**：更新端点（更新资源）
- **DELETE**：删除端点（软删除）

---

## 三、认证API

### 3.1 POST /api/auth/login

**描述**：用户登录，获取访问令牌

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/x-www-form-urlencoded:
      schema:
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

**响应**：
```yaml
responses:
  '200':
    description: 登录成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/Token'
  '401':
    description: 用户名或密码错误
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/Error'
```

**Token模型**：
```yaml
Token:
  type: object
  properties:
    access_token:
      type: string
      description: JWT访问令牌
    token_type:
      type: string
      example: bearer
```

---

### 3.2 GET /api/auth/me

**描述**：获取当前用户信息

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/UserResponse'
  '401':
    description: 未授权
```

---

## 四、用户管理API

### 4.1 POST /api/users

**描述**：创建用户

**安全**：需要Bearer Token（ADMIN角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/UserCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 用户创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/UserResponse'
  '400':
    description: 用户名或邮箱已存在
```

---

### 4.2 GET /api/users

**描述**：获取用户列表

**安全**：需要Bearer Token（ADMIN角色）

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
    description: 跳过记录数
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
    description: 返回记录数
  - name: role
    in: query
    schema:
      type: string
    description: 角色过滤
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/UserResponse'
```

---

### 4.3 GET /api/users/{user_id}

**描述**：获取用户详情

**安全**：需要Bearer Token（ADMIN角色）

**路径参数**：
```yaml
parameters:
  - name: user_id
    in: path
    required: true
    schema:
      type: integer
    description: 用户ID
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/UserResponse'
  '404':
    description: 用户不存在
```

---

### 4.4 PUT /api/users/{user_id}

**描述**：更新用户

**安全**：需要Bearer Token（ADMIN角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/UserUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/UserResponse'
```

---

### 4.5 DELETE /api/users/{user_id}

**描述**：删除用户（软删除）

**安全**：需要Bearer Token（ADMIN角色）

**响应**：
```yaml
responses:
  '204':
    description: 删除成功
```

---

### 4.6 GET /api/users/me

**描述**：获取当前登录用户信息

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/UserResponse'
```

---

### 4.7 GET /api/roles

**描述**：获取所有角色列表

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/RoleInfo'
```

---

## 五、销售与分销API（SD Module）

### 5.1 客户管理

#### POST /api/sd/customers

**描述**：创建客户

**安全**：需要Bearer Token（SALES角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/CustomerCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 客户创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/CustomerResponse'
  '400':
    description: 客户ID已存在
```

---

#### GET /api/sd/customers

**描述**：获取客户列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: status
    in: query
    schema:
      type: string
      enum: [DRAFT, PENDING_APPROVAL, ACTIVE, BLOCKED, INACTIVE]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/CustomerResponse'
```

---

#### GET /api/sd/customers/{customer_id}

**描述**：获取客户详情

**安全**：需要Bearer Token

**路径参数**：
```yaml
parameters:
  - name: customer_id
    in: path
    required: true
    schema:
      type: string
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/CustomerResponse'
  '404':
    description: 客户不存在
```

---

#### PUT /api/sd/customers/{customer_id}

**描述**：更新客户

**安全**：需要Bearer Token（SALES角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/CustomerUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/CustomerResponse'
```

---

### 5.2 报价单管理

#### POST /api/sd/quotations

**描述**：创建报价单

**安全**：需要Bearer Token（SALES角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/QuotationCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 报价单创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/QuotationResponse'
```

---

#### GET /api/sd/quotations

**描述**：获取报价单列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: customer_id
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [DRAFT, PENDING_SALES, PENDING_FINANCE, PENDING_GENERAL_MANAGER, APPROVED, REJECTED, CUSTOMER_CONFIRMED, LINKED, CANCELLED]
  - name: is_return_order
    in: query
    schema:
      type: boolean
    description: 是否返单（用于销售订单创建时的报价单过滤）
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/QuotationResponse'
```

---

#### GET /api/sd/quotations/{quotation_number}

**描述**：获取报价单详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/QuotationResponse'
  '404':
    description: 报价单不存在
```

---

#### PUT /api/sd/quotations/{quotation_number}

**描述**：更新报价单

**安全**：需要Bearer Token（SALES角色，仅REJECTED状态可更新）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/QuotationUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/QuotationResponse'
```

---

#### POST /api/sd/quotations/{quotation_number}/submit

**描述**：提交报价单审批

**安全**：需要Bearer Token（SALES角色）

**响应**：
```yaml
responses:
  '200':
    description: 提交成功
    content:
      application/json:
        schema:
          type: object
          properties:
            message:
              type: string
              example: 报价单已提交审批
  '400':
    description: 报价单状态无效或必填字段不完整
```

---

#### POST /api/sd/quotations/{quotation_number}/approve

**描述**：审批报价单

**安全**：需要Bearer Token（SALES_MANAGER/FINANCE/GENERAL_MANAGER角色）

**请求体**：
```yaml
requestBody:
  required: false
  content:
    application/json:
      schema:
        type: object
        properties:
          comment:
            type: string
            description: 审批意见
```

**响应**：
```yaml
responses:
  '200':
    description: 审批成功
    content:
      application/json:
        schema:
          type: object
          properties:
            message:
              type: string
              example: 报价单审批通过
```

---

#### POST /api/sd/quotations/{quotation_number}/reject

**描述**：拒绝报价单

**安全**：需要Bearer Token（SALES_MANAGER/FINANCE/GENERAL_MANAGER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required:
          - comment
        properties:
          comment:
            type: string
            description: 拒绝原因（必填）
```

**响应**：
```yaml
responses:
  '200':
    description: 拒绝成功
```

---

#### GET /api/sd/quotations/pending-approval

**描述**：获取待审批报价单列表

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/QuotationResponse'
```

---

#### GET /api/sd/quotations/{quotation_number}/approval-status

**描述**：获取报价单审批状态

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ApprovalStatusResponse'
```

---

### 5.3 销售订单管理

#### POST /api/sd/sales-orders

**描述**：创建销售订单

**安全**：需要Bearer Token（SALES角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/SalesOrderCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 销售订单创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
  '400':
    description: 物料编码不存在或必填字段不完整
```

---

#### GET /api/sd/sales-orders

**描述**：获取销售订单列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: customer_id
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [DRAFT, PENDING_REVIEW, REVIEWING, APPROVED, REJECTED, IN_PRODUCTION, COMPLETED, SHIPPED, DELIVERED, RECONCILED, CLOSED, CANCELLED]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/SalesOrderResponse'
```

---

#### GET /api/sd/sales-orders/{order_number}

**描述**：获取销售订单详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
  '404':
    description: 销售订单不存在
```

---

#### PUT /api/sd/sales-orders/{order_number}

**描述**：更新销售订单

**安全**：需要Bearer Token（SALES角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/SalesOrderUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
```

---

#### POST /api/sd/sales-orders/{order_number}/submit

**描述**：提交销售订单评审

**安全**：需要Bearer Token（SALES角色）

**响应**：
```yaml
responses:
  '200':
    description: 提交成功
    content:
      application/json:
        schema:
          type: object
          properties:
            message:
              type: string
              example: 销售订单已提交评审
```

---

#### GET /api/sd/sales-orders/{order_number}/review-status

**描述**：获取销售订单评审状态

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ReviewStatusResponse'
```

**ReviewStatusResponse模型**：
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

---

#### POST /api/sd/sales-orders/{order_number}/approve

**描述**：审批销售订单（多部门评审）

**安全**：需要Bearer Token（相应部门角色）

**请求体**：
```yaml
requestBody:
  required: false
  content:
    application/json:
      schema:
        type: object
        properties:
          comment:
            type: string
            description: 评审意见
```

**响应**：
```yaml
responses:
  '200':
    description: 审批成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
  '403':
    description: 当前用户没有权限审批此节点
```

---

#### POST /api/sd/sales-orders/{order_number}/reject

**描述**：拒绝销售订单

**安全**：需要Bearer Token（相应部门角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required:
          - comment
        properties:
          comment:
            type: string
            description: 拒绝原因（必填）
```

**响应**：
```yaml
responses:
  '200':
    description: 拒绝成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
```

---

#### POST /api/sd/sales-orders/{order_number}/ship

**描述**：销售发货

**安全**：需要Bearer Token（SALES角色）

**响应**：
```yaml
responses:
  '200':
    description: 发货成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
```

---

#### POST /api/sd/sales-orders/{order_number}/deliver

**描述**：销售签收

**安全**：需要Bearer Token（SALES角色）

**响应**：
```yaml
responses:
  '200':
    description: 签收成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
```

---

#### POST /api/sd/sales-orders/{order_number}/reconcile

**描述**：对账

**安全**：需要Bearer Token（FINANCE角色）

**响应**：
```yaml
responses:
  '200':
    description: 对账成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
```

---

#### POST /api/sd/sales-orders/{order_number}/close

**描述**：关闭销售订单

**安全**：需要Bearer Token（SALES/FINANCE角色）

**响应**：
```yaml
responses:
  '200':
    description: 关闭成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/SalesOrderResponse'
```

---

### 5.4 本厂编号映射管理

#### POST /api/sd/factory-product-mappings

**描述**：创建本厂编号映射

**安全**：需要Bearer Token（SALES/ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/FactoryProductMappingCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 映射创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/FactoryProductMappingResponse'
```

---

#### GET /api/sd/factory-product-mappings

**描述**：获取本厂编号映射列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: customer_id
    in: query
    schema:
      type: string
  - name: factory_product_number
    in: query
    schema:
      type: string
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/FactoryProductMappingResponse'
```

---

#### GET /api/sd/factory-product-mappings/{customer_id}/{product_number}

**描述**：根据客户ID和本厂编号获取默认映射

**安全**：需要Bearer Token

**路径参数**：
```yaml
parameters:
  - name: customer_id
    in: path
    required: true
    schema:
      type: string
  - name: product_number
    in: path
    required: true
    schema:
      type: string
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/FactoryProductMappingResponse'
  '404':
    description: 映射不存在
```

---

#### GET /api/sd/factory-product-mappings/by-id/{mapping_id}

**描述**：根据ID获取映射

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/FactoryProductMappingResponse'
```

---

#### PUT /api/sd/factory-product-mappings/{mapping_id}

**描述**：更新本厂编号映射

**安全**：需要Bearer Token（SALES/ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/FactoryProductMappingUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/FactoryProductMappingResponse'
```

---

#### DELETE /api/sd/factory-product-mappings/{mapping_id}

**描述**：删除本厂编号映射（软删除）

**安全**：需要Bearer Token（SALES/ENGINEER角色）

**响应**：
```yaml
responses:
  '204':
    description: 删除成功
```

---

## 六、工程管理API（ENG Module）

### 6.1 BOM管理

#### POST /api/eng/boms

**描述**：创建BOM

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/BOMCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: BOM创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/BOMResponse'
```

---

#### GET /api/eng/boms

**描述**：获取BOM列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: parent_material_code
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [NEW, REVIEWING, RELEASED, PRODUCING, OBSOLETE]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/BOMResponse'
```

---

#### GET /api/eng/boms/{bom_number}

**描述**：获取BOM详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/BOMResponse'
```

---

#### PUT /api/eng/boms/{bom_number}

**描述**：更新BOM

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/BOMUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/BOMResponse'
```

---

### 6.2 工艺路线管理

#### POST /api/eng/routings

**描述**：创建工艺路线

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/RoutingCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 工艺路线创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/RoutingResponse'
```

---

#### GET /api/eng/routings

**描述**：获取工艺路线列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: material_code
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [DRAFT, RELEASED, OBSOLETE]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/RoutingResponse'
```

---

#### GET /api/eng/routings/{routing_id}

**描述**：获取工艺路线详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/RoutingResponse'
```

---

#### GET /api/eng/routings/{routing_id}/operations

**描述**：获取工艺路线的工序列表

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/RoutingOperationResponse'
```

---

#### PUT /api/eng/routings/{routing_id}

**描述**：更新工艺路线

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/RoutingUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/RoutingResponse'
```

---

### 6.3 MI管理

#### POST /api/eng/mis

**描述**：创建MI

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/MICreate'
```

**响应**：
```yaml
responses:
  '201':
    description: MI创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MIResponse'
```

---

#### GET /api/eng/mis

**描述**：获取MI列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: material_code
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [DRAFT, REVIEWING, APPROVED, RELEASED, OBSOLETE]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/MIResponse'
```

---

#### GET /api/eng/mis/{mi_number}

**描述**：获取MI详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MIResponse'
```

---

#### PUT /api/eng/mis/{mi_number}

**描述**：更新MI

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/MIUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MIResponse'
```

---

#### POST /api/eng/mis/{mi_number}/submit

**描述**：提交MI审批

**安全**：需要Bearer Token（ENGINEER角色）

**响应**：
```yaml
responses:
  '200':
    description: 提交成功
```

---

#### POST /api/eng/mis/{mi_number}/approve

**描述**：审批MI

**安全**：需要Bearer Token（ENGINEER角色）

**响应**：
```yaml
responses:
  '200':
    description: 审批成功
```

---

#### POST /api/eng/mis/{mi_number}/reject

**描述**：拒绝MI

**安全**：需要Bearer Token（ENGINEER角色）

**响应**：
```yaml
responses:
  '200':
    description: 拒绝成功
```

---

### 6.4 生产版本管理

#### POST /api/eng/production-versions

**描述**：创建生产版本

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/ProductionVersionCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 生产版本创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionVersionResponse'
```

---

#### GET /api/eng/production-versions

**描述**：获取生产版本列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: material_code
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [ACTIVE, OBSOLETE]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/ProductionVersionResponse'
```

---

#### GET /api/eng/production-versions/{production_version_id}

**描述**：获取生产版本详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionVersionResponse'
```

---

#### PUT /api/eng/production-versions/{production_version_id}

**描述**：更新生产版本

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/ProductionVersionUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionVersionResponse'
```

---

#### POST /api/eng/production-versions/{production_version_id}/release

**描述**：发布生产版本

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required:
          - mi_number
        properties:
          mi_number:
            type: string
            description: MI编号（发布时必选）
```

**响应**：
```yaml
responses:
  '200':
    description: 发布成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionVersionResponse'
  '400':
    description: MI未关联或状态不是RELEASED
```

---

## 七、生产计划与控制API（PP Module）

### 7.1 工作中心管理

#### POST /api/pp/work-centers

**描述**：创建工作中心

**安全**：需要Bearer Token（ENGINEER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/WorkCenterCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 工作中心创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/WorkCenterResponse'
```

---

#### GET /api/pp/work-centers

**描述**：获取工作中心列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: plant_id
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [ACTIVE, INACTIVE, IN_MAINTENANCE]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/WorkCenterResponse'
```

---

#### GET /api/pp/work-centers/{work_center_id}

**描述**：获取工作中心详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/WorkCenterResponse'
```

---

### 7.2 生产订单管理

#### POST /api/pp/production-orders

**描述**：创建生产订单

**安全**：需要Bearer Token（PLANNER/PRODUCTION角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/ProductionOrderCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 生产订单创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### GET /api/pp/production-orders

**描述**：获取生产订单列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: sales_order_number
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [DRAFT, RELEASED, IN_PRODUCTION, COMPLETED, CLOSED, CANCELLED]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### GET /api/pp/production-orders/{order_number}

**描述**：获取生产订单详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### GET /api/pp/production-orders/{order_number}/operations

**描述**：获取生产订单的工序列表

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/RoutingOperationResponse'
```

---

#### PUT /api/pp/production-orders/{order_number}

**描述**：更新生产订单

**安全**：需要Bearer Token（PLANNER角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/ProductionOrderUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### POST /api/pp/production-orders/{order_number}/release

**描述**：下达生产订单

**安全**：需要Bearer Token（PLANNER角色）

**响应**：
```yaml
responses:
  '200':
    description: 下达成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### POST /api/pp/production-orders/{order_number}/close

**描述**：关闭生产订单

**安全**：需要Bearer Token（PLANNER角色）

**响应**：
```yaml
responses:
  '200':
    description: 关闭成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### POST /api/pp/production-orders/{order_number}/start

**描述**：开始生产订单

**安全**：需要Bearer Token（PRODUCTION角色）

**响应**：
```yaml
responses:
  '200':
    description: 开始成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

#### POST /api/pp/production-orders/{order_number}/complete

**描述**：完成生产订单

**安全**：需要Bearer Token（PRODUCTION角色）

**响应**：
```yaml
responses:
  '200':
    description: 完成成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/ProductionOrderResponse'
```

---

### 7.3 工序报工管理

#### POST /api/pp/operation-reports

**描述**：创建工序报工

**安全**：需要Bearer Token（PRODUCTION角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/OperationReportCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 工序报工创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/OperationReportResponse'
```

---

#### GET /api/pp/operation-reports

**描述**：获取工序报工列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: production_order_number
    in: query
    schema:
      type: string
  - name: status
    in: query
    schema:
      type: string
      enum: [PENDING, IN_PROGRESS, COMPLETED, REJECTED]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/OperationReportResponse'
```

---

#### GET /api/pp/production-progress

**描述**：获取生产进度

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: production_order_number
    in: query
    schema:
      type: string
      required: true
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: object
          properties:
            production_order_number:
              type: string
            total_operations:
              type: integer
            completed_operations:
              type: integer
            progress_percentage:
              type: number
              format: float
            operations:
              type: array
              items:
                type: object
                properties:
                  operation_no:
                    type: string
                  operation_name:
                    type: string
                  status:
                    type: string
                  reported_quantity:
                    type: number
```

---

## 八、物料管理API（MM Module）

### 8.1 物料主数据管理

#### POST /api/mm/materials

**描述**：创建物料

**安全**：需要Bearer Token（ENGINEER/WAREHOUSE角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/MaterialCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 物料创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MaterialResponse'
```

---

#### GET /api/mm/materials

**描述**：获取物料列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: material_type
    in: query
    schema:
      type: string
      enum: [FG, RAW, SEMI]
  - name: status
    in: query
    schema:
      type: string
      enum: [ACTIVE, OBSOLETE, DRAFT]
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/MaterialResponse'
```

---

#### GET /api/mm/materials/{material_code}

**描述**：获取物料详情

**安全**：需要Bearer Token

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MaterialResponse'
```

---

#### PUT /api/mm/materials/{material_code}

**描述**：更新物料

**安全**：需要Bearer Token（ENGINEER/WAREHOUSE角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/MaterialUpdate'
```

**响应**：
```yaml
responses:
  '200':
    description: 更新成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MaterialResponse'
```

---

### 8.2 生产领料管理

#### POST /api/mm/material-issues

**描述**：创建生产领料单

**安全**：需要Bearer Token（WAREHOUSE角色）

**请求体**：
```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        $ref: '#/components/schemas/MaterialIssueCreate'
```

**响应**：
```yaml
responses:
  '201':
    description: 生产领料单创建成功
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/MaterialIssueResponse'
  '400':
    description: 领料数量超过库存或单位不一致
```

---

#### GET /api/mm/material-issues

**描述**：获取生产领料单列表

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: skip
    in: query
    schema:
      type: integer
      default: 0
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: production_order_number
    in: query
    schema:
      type: string
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: array
          items:
            $ref: '#/components/schemas/MaterialIssueResponse'
```

---

#### GET /api/mm/inventory

**描述**：获取物料库存信息

**安全**：需要Bearer Token

**查询参数**：
```yaml
parameters:
  - name: material_code
    in: query
    schema:
      type: string
```

**响应**：
```yaml
responses:
  '200':
    description: 成功
    content:
      application/json:
        schema:
          type: object
          properties:
            material_code:
              type: string
            material_name:
              type: string
            current_stock:
              type: number
              format: float
            safety_stock:
              type: number
              format: float
            unit:
              type: string
```

---

## 九、数据模型（Schemas）

### 9.1 通用模型

#### Error（错误响应）

```yaml
Error:
  type: object
  properties:
    detail:
      type: string
      description: 错误详情
    error_code:
      type: string
      description: 错误代码
```

---

### 9.2 认证模型

#### Token（令牌）

```yaml
Token:
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

---

### 9.3 用户模型

#### UserCreate（创建用户）

```yaml
UserCreate:
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
    full_name:
      type: string
    role:
      type: string
      enum: [SALES, SALES_MANAGER, ENGINEER, PLANNER, PRODUCTION, WAREHOUSE, FINANCE, GENERAL_MANAGER, ADMIN]
    department:
      type: string
    phone:
      type: string
    is_active:
      type: boolean
      default: true
```

#### UserUpdate（更新用户）

```yaml
UserUpdate:
  allOf:
    - $ref: '#/components/schemas/UserCreate'
    - type: object
      properties:
        password:
          type: string
          format: password
          description: 可选，如果不提供则不更新密码
```

#### UserResponse（用户响应）

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
    updated_at:
      type: string
      format: date-time
```

#### RoleInfo（角色信息）

```yaml
RoleInfo:
  type: object
  properties:
    value:
      type: string
      description: 角色代码
    label:
      type: string
      description: 角色名称
```

---

### 9.4 销售与分销模型

#### CustomerCreate（创建客户）

```yaml
CustomerCreate:
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
      maxLength: 200
    tax_id:
      type: string
      maxLength: 50
    customer_industry:
      type: string
      maxLength: 50
    customer_website:
      type: string
      maxLength: 200
    credit_limit:
      type: number
      format: float
    customer_status:
      type: string
      enum: [DRAFT, PENDING_APPROVAL, ACTIVE, BLOCKED, INACTIVE]
      default: DRAFT
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

#### CustomerResponse（客户响应）

```yaml
CustomerResponse:
  type: object
  properties:
    id:
      type: integer
    customer_id:
      type: string
    legal_name:
      type: string
    trade_name:
      type: string
    tax_id:
      type: string
    customer_industry:
      type: string
    customer_website:
      type: string
    customer_status:
      type: string
    credit_limit:
      type: number
      format: float
    addresses:
      type: array
      items:
        $ref: '#/components/schemas/CustomerAddressResponse'
    contacts:
      type: array
      items:
        $ref: '#/components/schemas/CustomerContactResponse'
    partner_functions:
      type: array
      items:
        $ref: '#/components/schemas/CustomerPartnerFunctionResponse'
    sales_data:
      type: array
      items:
        $ref: '#/components/schemas/CustomerSalesDataResponse'
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
```

#### QuotationCreate（创建报价单）

```yaml
QuotationCreate:
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

#### QuotationResponse（报价单响应）

```yaml
QuotationResponse:
  type: object
  properties:
    id:
      type: integer
    quotation_number:
      type: string
    customer_id:
      type: string
    product_number:
      type: string
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
    total_amount:
      type: number
      format: float
    currency:
      type: string
    valid_until:
      type: string
      format: date
    status:
      type: string
    remarks:
      type: string
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
```

#### SalesOrderCreate（创建销售订单）

```yaml
SalesOrderCreate:
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
      description: 是否返单
    remarks:
      type: string
    material_code:
      type: string
      description: 物料编码（可选，如果提供则直接使用，否则自动查找映射）
    production_version_id:
      type: string
      description: 生产版本ID（可选）
    sales_unit:
      type: string
      description: 销售单位（可选）
    production_quantity:
      type: number
      format: float
      description: 生产数量（可选）
    production_unit:
      type: string
      description: 生产单位（可选）
    conversion_factor:
      type: number
      format: float
      description: 单位转换系数（可选）
```

#### SalesOrderUpdate（更新销售订单）

```yaml
SalesOrderUpdate:
  type: object
  required:
    - customer_id
    - product_number
    - quantity
    - delivery_date
  properties:
    quotation_number:
      type: string
    customer_id:
      type: string
    product_number:
      type: string
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
    remarks:
      type: string
```

#### SalesOrderResponse（销售订单响应）

```yaml
SalesOrderResponse:
  type: object
  properties:
    id:
      type: integer
    order_number:
      type: string
    quotation_number:
      type: string
    customer_id:
      type: string
    product_number:
      type: string
    quantity:
      type: number
      format: float
    unit_price:
      type: number
      format: float
    total_amount:
      type: number
      format: float
    currency:
      type: string
    delivery_date:
      type: string
      format: date-time
    status:
      type: string
      enum: [DRAFT, PENDING_REVIEW, REVIEWING, APPROVED, REJECTED, IN_PRODUCTION, COMPLETED, SHIPPED, DELIVERED, RECONCILED, CLOSED, CANCELLED]
    is_return_order:
      type: boolean
    review_status:
      type: string
    remarks:
      type: string
    material_code:
      type: string
    production_version_id:
      type: string
    sales_unit:
      type: string
    production_quantity:
      type: number
      format: float
    production_unit:
      type: string
    conversion_factor:
      type: number
      format: float
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
```

#### FactoryProductMappingCreate（创建本厂编号映射）

```yaml
FactoryProductMappingCreate:
  type: object
  required:
    - customer_id
    - factory_product_number
    - material_code
    - effective_date
  properties:
    customer_id:
      type: string
    factory_product_number:
      type: string
      description: 本厂编号
    material_code:
      type: string
    production_version_id:
      type: string
    is_default:
      type: boolean
      default: true
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
```

#### FactoryProductMappingUpdate（更新本厂编号映射）

```yaml
FactoryProductMappingUpdate:
  type: object
  properties:
    material_code:
      type: string
    production_version_id:
      type: string
    is_default:
      type: boolean
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
```

#### FactoryProductMappingResponse（本厂编号映射响应）

```yaml
FactoryProductMappingResponse:
  type: object
  properties:
    id:
      type: integer
    customer_id:
      type: string
    factory_product_number:
      type: string
    material_code:
      type: string
    production_version_id:
      type: string
    is_default:
      type: boolean
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### CustomerAddressPayload（客户地址载荷）

```yaml
CustomerAddressPayload:
  type: object
  required:
    - address_type
    - detail_address
  properties:
    address_type:
      type: string
      enum: [HEADQUARTERS, PLANT, WAREHOUSE, BILLING]
    detail_address:
      type: string
    location:
      type: string
    postal_code:
      type: string
    country:
      type: string
      default: 中国
    province:
      type: string
    city:
      type: string
    district:
      type: string
    is_default_shipping:
      type: boolean
      default: false
    is_default_billing:
      type: boolean
      default: false
```

#### CustomerContactPayload（客户联系人载荷）

```yaml
CustomerContactPayload:
  type: object
  required:
    - contact_name
  properties:
    is_primary_contact:
      type: boolean
      default: false
    contact_name:
      type: string
    contact_role:
      type: string
    contact_department:
      type: string
    contact_phone:
      type: string
    contact_email:
      type: string
```

#### CustomerPartnerFunctionPayload（客户合作属性载荷）

```yaml
CustomerPartnerFunctionPayload:
  type: object
  required:
    - partner_function_type
  properties:
    partner_function_type:
      type: string
    partner_start_date:
      type: string
      format: date
    partner_name:
      type: string
    partnership_description:
      type: string
```

#### CustomerSalesDataPayload（客户销售数据载荷）

```yaml
CustomerSalesDataPayload:
  type: object
  properties:
    sales_organization:
      type: string
    account_manager_name:
      type: string
    sales_assistant_name:
      type: string
    trading_currency:
      type: string
      default: CNY
    primary_trade_country:
      type: string
    incoterms:
      type: string
    shipping_conditions:
      type: string
```

#### ContractReviewResponse（订单评审响应）

```yaml
ContractReviewResponse:
  type: object
  properties:
    id:
      type: integer
    sales_order_number:
      type: string
    reviewer_role:
      type: string
    reviewer:
      type: string
    review_result:
      type: string
      enum: [APPROVED, REJECTED]
    review_comment:
      type: string
    reviewed_at:
      type: string
      format: date-time
```

---

### 9.5 工程管理模型

#### BOMItemCreate（创建BOM明细）

```yaml
BOMItemCreate:
  type: object
  required:
    - material_code
    - quantity
    - unit
  properties:
    line_number:
      type: integer
      description: 行号（可选，如果未提供则自动生成）
    material_code:
      type: string
    item_category:
      type: string
      enum: [STOCK_ITEM, SUB_ASSEMBLY, CONSUMABLE]
    quantity:
      type: number
      format: float
    unit:
      type: string
    scrap_rate:
      type: number
      format: float
      description: 损耗率%
    calculation_formula:
      type: string
    layer_code:
      type: string
      description: PCB层码
    material_type:
      type: string
    process_step:
      type: string
    remarks:
      type: string
```

#### BOMCreate（创建BOM）

```yaml
BOMCreate:
  type: object
  required:
    - parent_material_code
    - version
    - effective_date
    - items
  properties:
    bom_number:
      type: string
      description: BOM编号（可选，如果未提供则自动生成）
    parent_material_code:
      type: string
    version:
      type: string
      default: V1.0
    plant_id:
      type: string
    bom_type:
      type: string
      default: PRODUCTION
    base_quantity:
      type: number
      format: float
      default: 1
    base_uom:
      type: string
      default: PNL
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    description:
      type: string
    status:
      type: string
      enum: [NEW, REVIEWING, RELEASED, PRODUCING, OBSOLETE]
    items:
      type: array
      items:
        $ref: '#/components/schemas/BOMItemCreate'
      minItems: 1
      description: BOM明细列表（至少包含一个）
```

#### BOMUpdate（更新BOM）

```yaml
BOMUpdate:
  allOf:
    - $ref: '#/components/schemas/BOMCreate'
    - type: object
      properties:
        bom_number:
          type: string
          description: BOM编号（不可修改）
```

#### BOMItemResponse（BOM明细响应）

```yaml
BOMItemResponse:
  type: object
  properties:
    id:
      type: integer
    line_number:
      type: integer
    material_code:
      type: string
    item_category:
      type: string
    quantity:
      type: number
      format: float
    unit:
      type: string
    scrap_rate:
      type: number
      format: float
    calculation_formula:
      type: string
    layer_code:
      type: string
    material_type:
      type: string
    process_step:
      type: string
    remarks:
      type: string
```

#### BOMResponse（BOM响应）

```yaml
BOMResponse:
  type: object
  properties:
    id:
      type: integer
    bom_number:
      type: string
    version:
      type: string
    parent_material_code:
      type: string
    plant_id:
      type: string
    bom_type:
      type: string
    base_quantity:
      type: number
      format: float
    base_uom:
      type: string
    status:
      type: string
    description:
      type: string
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    items:
      type: array
      items:
        $ref: '#/components/schemas/BOMItemResponse'
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### RoutingOperationCreate（创建工艺路线工序）

```yaml
RoutingOperationCreate:
  type: object
  required:
    - operation_no
    - operation_code
    - operation_name
    - operation_type
    - work_center_id
  properties:
    operation_no:
      type: string
      description: 工序号（如0010, 0020）
    operation_code:
      type: string
    operation_name:
      type: string
    operation_type:
      type: string
      enum: [internal, external, quality]
    work_center_id:
      type: string
    sop_link:
      type: string
    setup_time:
      type: number
      format: float
      default: 0
      description: 调机时间（分钟）
    machine_time:
      type: number
      format: float
      default: 0
      description: 机器时间（分钟）
    labor_time:
      type: number
      format: float
      default: 0
      description: 人工时间（分钟）
    queue_time:
      type: number
      format: float
      default: 0
      description: 排队缓冲（分钟）
    cost_relevant:
      type: boolean
      default: true
    scheduling_relevant:
      type: boolean
      default: true
    needs_reporting:
      type: boolean
      default: true
    auto_deduct_material:
      type: boolean
      default: false
    trigger_quality_check:
      type: boolean
      default: false
    service_code:
      type: string
      description: 外协服务代码（当operation_type=external时）
    planned_delivery_days:
      type: number
      format: float
      description: 计划交期（天，当operation_type=external时）
    estimated_unit_price:
      type: number
      format: float
      description: 预估单价（当operation_type=external时）
    estimated_currency:
      type: string
      description: 预估货币（当operation_type=external时）
    suggested_supplier:
      type: string
      description: 建议供应商（当operation_type=external时）
    generate_purchase_req:
      type: boolean
      default: false
      description: 自动生成采购申请（当operation_type=external时）
    inspection_plan_id:
      type: string
      description: 检验计划（当operation_type=quality时）
    sampling_rate:
      type: number
      format: float
      description: 抽检率%（当operation_type=quality时）
    verification_logic:
      type: string
      description: 质检逻辑（当operation_type=quality时）
    remarks:
      type: string
```

#### RoutingCreate（创建工艺路线）

```yaml
RoutingCreate:
  type: object
  required:
    - material_code
    - version
    - effective_date
    - operations
  properties:
    routing_id:
      type: string
      description: 工艺路线ID（可选，如果未提供则自动生成）
    material_code:
      type: string
    version:
      type: string
    base_unit:
      type: string
      default: PNL
    base_quantity:
      type: number
      format: float
      default: 1
    units_per_panel:
      type: integer
      default: 1
    panel_size:
      type: string
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    change_request_no:
      type: string
      description: 工程变更单号
    operations:
      type: array
      items:
        $ref: '#/components/schemas/RoutingOperationCreate'
      minItems: 1
      description: 工序列表（至少包含一个）
```

#### RoutingUpdate（更新工艺路线）

```yaml
RoutingUpdate:
  allOf:
    - $ref: '#/components/schemas/RoutingCreate'
    - type: object
      properties:
        routing_id:
          type: string
          description: 工艺路线ID（不可修改）
```

#### RoutingOperationResponse（工艺路线工序响应）

```yaml
RoutingOperationResponse:
  type: object
  properties:
    id:
      type: integer
    routing_id:
      type: string
    operation_no:
      type: string
    operation_code:
      type: string
    operation_name:
      type: string
    operation_type:
      type: string
    work_center_id:
      type: string
    sop_link:
      type: string
    setup_time:
      type: number
      format: float
    machine_time:
      type: number
      format: float
    labor_time:
      type: number
      format: float
    queue_time:
      type: number
      format: float
    cost_relevant:
      type: boolean
    scheduling_relevant:
      type: boolean
    needs_reporting:
      type: boolean
    auto_deduct_material:
      type: boolean
    trigger_quality_check:
      type: boolean
    service_code:
      type: string
    planned_delivery_days:
      type: number
      format: float
    estimated_unit_price:
      type: number
      format: float
    estimated_currency:
      type: string
    suggested_supplier:
      type: string
    generate_purchase_req:
      type: boolean
    inspection_plan_id:
      type: string
    sampling_rate:
      type: number
      format: float
    verification_logic:
      type: string
    remarks:
      type: string
```

#### RoutingResponse（工艺路线响应）

```yaml
RoutingResponse:
  type: object
  properties:
    id:
      type: integer
    routing_id:
      type: string
    version:
      type: string
    material_code:
      type: string
    base_unit:
      type: string
    base_quantity:
      type: number
      format: float
    units_per_panel:
      type: integer
    panel_size:
      type: string
    status:
      type: string
      enum: [DRAFT, RELEASED, OBSOLETE]
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    change_request_no:
      type: string
    operations:
      type: array
      items:
        $ref: '#/components/schemas/RoutingOperationResponse'
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### MICreate（创建MI）

```yaml
MICreate:
  type: object
  required:
    - material_code
    - version
    - effective_date
  properties:
    mi_number:
      type: string
      description: MI编号（可选，如果未提供则自动生成）
    material_code:
      type: string
    routing_id:
      type: string
      description: 工艺路线ID（可选，如果提供则自动生成MI草稿）
    version:
      type: string
    description:
      type: string
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    instructions:
      type: array
      items:
        type: object
        properties:
          sequence:
            type: integer
            description: 指令序号
          name:
            type: string
            description: 指令名称
          description:
            type: string
            description: 指令描述
      description: MI指令集列表
```

#### MIUpdate（更新MI）

```yaml
MIUpdate:
  allOf:
    - $ref: '#/components/schemas/MICreate'
    - type: object
      properties:
        mi_number:
          type: string
          description: MI编号（不可修改）
```

#### MIResponse（MI响应）

```yaml
MIResponse:
  type: object
  properties:
    id:
      type: integer
    mi_number:
      type: string
    version:
      type: string
    material_code:
      type: string
    description:
      type: string
    status:
      type: string
      enum: [DRAFT, REVIEWING, APPROVED, RELEASED, OBSOLETE]
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    content:
      type: string
      description: MI内容（JSON格式）
    instructions:
      type: array
      items:
        type: object
        properties:
          sequence:
            type: integer
          name:
            type: string
          description:
            type: string
      description: MI指令集列表（从content解析）
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### ProductionVersionCreate（创建生产版本）

```yaml
ProductionVersionCreate:
  type: object
  required:
    - material_code
    - bom_number
    - routing_id
    - version
    - effective_date
  properties:
    production_version_id:
      type: string
      description: 生产版本ID（可选，如果未提供则自动生成）
    material_code:
      type: string
    bom_number:
      type: string
      description: BOM编号（必选）
    routing_id:
      type: string
      description: 工艺路线ID（必选）
    mi_number:
      type: string
      description: MI编号（可选，创建时可选，发布时必选）
    version:
      type: string
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
```

#### ProductionVersionUpdate（更新生产版本）

```yaml
ProductionVersionUpdate:
  allOf:
    - $ref: '#/components/schemas/ProductionVersionCreate'
    - type: object
      properties:
        production_version_id:
          type: string
          description: 生产版本ID（不可修改）
```

#### ProductionVersionResponse（生产版本响应）

```yaml
ProductionVersionResponse:
  type: object
  properties:
    id:
      type: integer
    production_version_id:
      type: string
    version:
      type: string
    material_code:
      type: string
    bom_number:
      type: string
    routing_id:
      type: string
    mi_number:
      type: string
    status:
      type: string
      enum: [ACTIVE, OBSOLETE]
    effective_date:
      type: string
      format: date-time
    expiry_date:
      type: string
      format: date-time
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

---

### 9.6 生产计划与控制模型

#### WorkCenterCreate（创建工作中心）

```yaml
WorkCenterCreate:
  type: object
  required:
    - work_center_id
    - description
    - work_center_type
    - plant_id
  properties:
    work_center_id:
      type: string
    description:
      type: string
    work_center_type:
      type: string
      enum: [MACHINE, MACHINE_GROUP, LABOR, PRODUCTION_LINE]
    plant_id:
      type: string
    status:
      type: string
      enum: [ACTIVE, INACTIVE, IN_MAINTENANCE]
      default: ACTIVE
    parent_work_center_id:
      type: string
    hierarchy_level:
      type: integer
      default: 1
    work_center_category:
      type: string
    usage:
      type: string
    queue_time:
      type: number
      format: float
    wait_time:
      type: number
      format: float
    move_time:
      type: number
      format: float
    capacity_category:
      type: string
    factory_calendar_id:
      type: string
    shift_start_time:
      type: string
    shift_finish_time:
      type: string
    break_time:
      type: number
      format: float
    capacity_utilization:
      type: number
      format: float
    number_of_capacities:
      type: integer
    cost_center_id:
      type: string
    process_category:
      type: string
      description: 工艺类别（PCB行业特定）
    activity_types:
      type: array
      items:
        type: object
        properties:
          activity_type:
            type: string
          description:
            type: string
          unit:
            type: string
          standard_value:
            type: number
            format: float
      description: 作业类型列表（JSON格式）
    technical_attributes:
      type: array
      items:
        type: object
        properties:
          attribute_name:
            type: string
          attribute_value:
            type: string
      description: 技术属性列表（JSON格式）
```

#### WorkCenterResponse（工作中心响应）

```yaml
WorkCenterResponse:
  type: object
  properties:
    id:
      type: integer
    work_center_id:
      type: string
    description:
      type: string
    work_center_type:
      type: string
    status:
      type: string
    plant_id:
      type: string
    parent_work_center_id:
      type: string
    hierarchy_level:
      type: integer
    work_center_category:
      type: string
    usage:
      type: string
    queue_time:
      type: number
      format: float
    wait_time:
      type: number
      format: float
    move_time:
      type: number
      format: float
    capacity_category:
      type: string
    factory_calendar_id:
      type: string
    shift_start_time:
      type: string
    shift_finish_time:
      type: string
    break_time:
      type: number
      format: float
    capacity_utilization:
      type: number
      format: float
    number_of_capacities:
      type: integer
    cost_center_id:
      type: string
    process_category:
      type: string
    activity_types:
      type: array
      items:
        type: object
    technical_attributes:
      type: array
      items:
        type: object
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### ProductionOrderCreate（创建生产订单）

```yaml
ProductionOrderCreate:
  type: object
  required:
    - sales_order_number
    - production_version_id
    - quantity
  properties:
    sales_order_number:
      type: string
    production_version_id:
      type: string
      description: 生产版本ID（必填）
    material_code:
      type: string
      description: 物料编码（可选，通过生产版本自动填充）
    quantity:
      type: number
      format: float
    unit:
      type: string
      default: PNL
    planned_start_date:
      type: string
      format: date-time
    planned_finish_date:
      type: string
      format: date-time
    lot_number:
      type: string
    remarks:
      type: string
```

#### ProductionOrderUpdate（更新生产订单）

```yaml
ProductionOrderUpdate:
  allOf:
    - $ref: '#/components/schemas/ProductionOrderCreate'
    - type: object
      properties:
        order_number:
          type: string
          description: 生产订单号（不可修改）
```

#### ProductionOrderResponse（生产订单响应）

```yaml
ProductionOrderResponse:
  type: object
  properties:
    id:
      type: integer
    order_number:
      type: string
    sales_order_number:
      type: string
    material_code:
      type: string
    production_version_id:
      type: string
    quantity:
      type: number
      format: float
    unit:
      type: string
    sales_quantity:
      type: number
      format: float
      description: 关联的销售订单数量
    sales_unit:
      type: string
      description: 关联的销售订单单位
    conversion_factor:
      type: number
      format: float
      description: 单位转换系数
    planned_start_date:
      type: string
      format: date-time
    planned_finish_date:
      type: string
      format: date-time
    actual_start_date:
      type: string
      format: date-time
    actual_finish_date:
      type: string
      format: date-time
    status:
      type: string
      enum: [DRAFT, RELEASED, IN_PRODUCTION, COMPLETED, CLOSED, CANCELLED]
    lot_number:
      type: string
    remarks:
      type: string
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### OperationReportCreate（创建工序报工）

```yaml
OperationReportCreate:
  type: object
  required:
    - production_order_number
    - routing_operation_id
    - work_center_id
    - operation_no
    - reported_quantity
    - good_quantity
  properties:
    production_order_number:
      type: string
    routing_operation_id:
      type: integer
      description: 工艺路线工序ID
    work_center_id:
      type: string
    operation_no:
      type: string
    operation_name:
      type: string
    reported_quantity:
      type: number
      format: float
      description: 报工数量
    good_quantity:
      type: number
      format: float
      description: 良品数量
    scrap_quantity:
      type: number
      format: float
      default: 0
      description: 报废数量
    setup_time:
      type: number
      format: float
      description: 实际调机时间（分钟）
    machine_time:
      type: number
      format: float
      description: 实际机器时间（分钟）
    labor_time:
      type: number
      format: float
      description: 实际人工时间（分钟）
    remarks:
      type: string
```

#### OperationReportResponse（工序报工响应）

```yaml
OperationReportResponse:
  type: object
  properties:
    id:
      type: integer
    report_number:
      type: string
    production_order_number:
      type: string
    routing_operation_id:
      type: integer
    work_center_id:
      type: string
    operation_no:
      type: string
    operation_name:
      type: string
    reported_quantity:
      type: number
      format: float
    good_quantity:
      type: number
      format: float
    scrap_quantity:
      type: number
      format: float
    setup_time:
      type: number
      format: float
    machine_time:
      type: number
      format: float
    labor_time:
      type: number
      format: float
    status:
      type: string
      enum: [PENDING, IN_PROGRESS, COMPLETED, REJECTED]
    reported_by:
      type: string
    reported_at:
      type: string
      format: date-time
    remarks:
      type: string
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
```

---

### 9.7 物料管理模型

#### MaterialCreate（创建物料）

```yaml
MaterialCreate:
  type: object
  required:
    - material_code
    - material_name
    - material_type
    - base_unit
  properties:
    material_code:
      type: string
      maxLength: 50
    material_name:
      type: string
      maxLength: 200
    material_type:
      type: string
      enum: [FG, RAW, SEMI]
    status:
      type: string
      enum: [ACTIVE, OBSOLETE, DRAFT]
      default: ACTIVE
    base_unit:
      type: string
      enum: [PCS, PNL, KG, SHT]
    production_unit:
      type: string
    conversion_factor:
      type: number
      format: float
      default: 1.0
    description:
      type: string
    # PCB工程属性（当material_type=FG时）
    layer_count:
      type: integer
      description: 层数
    board_thickness:
      type: number
      format: float
      description: 板厚（mm）
    copper_weight:
      type: string
      description: 铜厚
    material_grade:
      type: string
      description: 材料等级
    surface_finish:
      type: string
      description: 表面处理
    solder_mask_color:
      type: string
      description: 阻焊颜色
    silkscreen_color:
      type: string
      description: 丝印颜色
    impedance_control:
      type: boolean
      description: 是否有阻抗控制
    min_line_space:
      type: number
      format: float
      description: 最小线距（mm）
    min_hole_size:
      type: number
      format: float
      description: 最小孔径（mm）
    unit_length:
      type: number
      format: float
      description: 单元长度（mm）
    unit_width:
      type: number
      format: float
      description: 单元宽度（mm）
    panel_length:
      type: number
      format: float
      description: 拼板长度（mm）
    panel_width:
      type: number
      format: float
      description: 拼板宽度（mm）
    units_per_panel:
      type: integer
      description: 每拼板单元数
    # 供应链计划
    procurement_type:
      type: string
      enum: [MAKE, BUY, BOTH]
    valuation_method:
      type: string
      enum: [STANDARD, MOVING_AVERAGE, FIFO]
    safety_stock:
      type: number
      format: float
      description: 安全库存
    reorder_point:
      type: number
      format: float
      description: 再订货点
    current_stock:
      type: number
      format: float
      default: 0
      description: 当前库存
```

#### MaterialUpdate（更新物料）

```yaml
MaterialUpdate:
  allOf:
    - $ref: '#/components/schemas/MaterialCreate'
    - type: object
      properties:
        material_code:
          type: string
          description: 物料编码（不可修改）
```

#### MaterialResponse（物料响应）

```yaml
MaterialResponse:
  type: object
  properties:
    id:
      type: integer
    material_code:
      type: string
    material_name:
      type: string
    material_type:
      type: string
    status:
      type: string
    base_unit:
      type: string
    production_unit:
      type: string
    conversion_factor:
      type: number
      format: float
    description:
      type: string
    # PCB工程属性
    layer_count:
      type: integer
    board_thickness:
      type: number
      format: float
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
    # 供应链计划
    procurement_type:
      type: string
    valuation_method:
      type: string
    safety_stock:
      type: number
      format: float
    reorder_point:
      type: number
      format: float
    current_stock:
      type: number
      format: float
    created_by:
      type: string
    created_at:
      type: string
      format: date-time
    updated_by:
      type: string
    updated_at:
      type: string
      format: date-time
```

#### MaterialIssueCreate（创建生产领料单）

```yaml
MaterialIssueCreate:
  type: object
  required:
    - production_order_number
    - material_code
    - quantity
    - unit
    - warehouse
  properties:
    production_order_number:
      type: string
    material_code:
      type: string
    quantity:
      type: number
      format: float
      description: 领料数量
    unit:
      type: string
      description: 单位（必须与物料的单位一致）
    warehouse:
      type: string
      description: 仓库
    issued_by:
      type: string
      description: 领料人
    remarks:
      type: string
```

#### MaterialIssueResponse（生产领料单响应）

```yaml
MaterialIssueResponse:
  type: object
  properties:
    id:
      type: integer
    issue_number:
      type: string
    production_order_number:
      type: string
    material_code:
      type: string
    quantity:
      type: number
      format: float
    unit:
      type: string
    warehouse:
      type: string
    issued_by:
      type: string
    issued_at:
      type: string
      format: date-time
    remarks:
      type: string
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
```

---

## 十、错误处理

### 10.1 错误响应格式

所有API错误响应都遵循统一的格式：

```yaml
Error:
  type: object
  required:
    - detail
  properties:
    detail:
      type: string
      description: 错误详情
    error_code:
      type: string
      description: 错误代码（可选）
    field:
      type: string
      description: 错误字段（验证错误时）
```

### 10.2 常见错误代码

| HTTP状态码 | 错误代码 | 描述 |
|-----------|---------|------|
| 400 | VALIDATION_ERROR | 请求参数验证失败 |
| 401 | UNAUTHORIZED | 未授权，需要登录 |
| 403 | FORBIDDEN | 权限不足 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突（如ID已存在） |
| 422 | UNPROCESSABLE_ENTITY | 业务逻辑错误 |
| 500 | INTERNAL_SERVER_ERROR | 服务器内部错误 |

### 10.3 错误响应示例

**验证错误（400）**：
```json
{
  "detail": "物料编码不存在",
  "error_code": "VALIDATION_ERROR",
  "field": "material_code"
}
```

**权限错误（403）**：
```json
{
  "detail": "您当前没有权限审批此节点",
  "error_code": "FORBIDDEN"
}
```

**资源不存在（404）**：
```json
{
  "detail": "销售订单不存在",
  "error_code": "NOT_FOUND"
}
```

---

## 十一、API使用示例

### 11.1 认证流程

```bash
# 1. 用户登录
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=password123

# 响应
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# 2. 使用令牌访问API
GET /api/sd/customers
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 11.2 创建销售订单流程

```bash
# 1. 创建销售订单
POST /api/sd/sales-orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_id": "C001",
  "product_number": "HS1004ENIGAB01",
  "quantity": 1000,
  "delivery_date": "2025-12-31T00:00:00Z",
  "is_return_order": false
}

# 响应
{
  "id": 1,
  "order_number": "SO-20251212-0001",
  "customer_id": "C001",
  "product_number": "HS1004ENIGAB01",
  "material_code": "MAT001",
  "production_version_id": "PV001",
  "quantity": 1000,
  "sales_unit": "PCS",
  "production_quantity": 100,
  "production_unit": "PNL",
  "conversion_factor": 10.0,
  "status": "DRAFT",
  ...
}

# 2. 提交评审
POST /api/sd/sales-orders/SO-20251212-0001/submit
Authorization: Bearer <token>

# 3. 查看评审状态
GET /api/sd/sales-orders/SO-20251212-0001/review-status
Authorization: Bearer <token>

# 4. 审批（销售部门）
POST /api/sd/sales-orders/SO-20251212-0001/approve
Authorization: Bearer <token>
Content-Type: application/json

{
  "comment": "销售部门评审通过"
}
```

### 11.3 创建生产订单流程

```bash
# 1. 创建生产订单
POST /api/pp/production-orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "sales_order_number": "SO-20251212-0001",
  "production_version_id": "PV001",
  "quantity": 100,
  "unit": "PNL",
  "planned_start_date": "2025-12-15T00:00:00Z",
  "planned_finish_date": "2025-12-25T00:00:00Z"
}

# 2. 下达生产订单
POST /api/pp/production-orders/PO-20251212-0001/release
Authorization: Bearer <token>

# 3. 获取工序列表
GET /api/pp/production-orders/PO-20251212-0001/operations
Authorization: Bearer <token>

# 4. 创建工序报工
POST /api/pp/operation-reports
Authorization: Bearer <token>
Content-Type: application/json

{
  "production_order_number": "PO-20251212-0001",
  "routing_operation_id": 1,
  "work_center_id": "WC001",
  "operation_no": "0010",
  "operation_name": "开料",
  "reported_quantity": 100,
  "good_quantity": 98,
  "scrap_quantity": 2
}
```

---

## 十二、API版本管理

### 12.1 版本策略

- **当前版本**：v1.0.0
- **版本号格式**：主版本号.次版本号.修订号（遵循语义化版本）
- **向后兼容**：次版本号和修订号的更新保持向后兼容
- **破坏性变更**：主版本号更新时可能包含破坏性变更

### 12.2 版本标识

版本信息通过以下方式标识：

1. **URL路径**：`/api/v1/...`（未来可能支持）
2. **请求头**：`Accept: application/vnd.hserp.v1+json`（未来可能支持）
3. **文档版本**：本文档的版本号

---

## 十三、API限制和配额

### 13.1 请求限制

- **速率限制**：1000请求/分钟/用户
- **并发限制**：10并发请求/用户
- **请求大小**：最大10MB

### 13.2 配额管理

- **分页限制**：默认每页100条，最大1000条
- **查询超时**：30秒
- **批量操作**：最多100条记录/次

---

## 十四、最佳实践

### 14.1 认证和授权

1. **安全存储令牌**：不要将JWT令牌存储在localStorage，建议使用httpOnly cookie
2. **令牌刷新**：实现令牌刷新机制，避免频繁登录
3. **权限检查**：前端应进行权限检查，但后端必须进行最终验证

### 14.2 错误处理

1. **统一错误处理**：使用统一的错误处理中间件
2. **详细错误信息**：开发环境提供详细错误，生产环境提供友好提示
3. **错误日志**：记录所有错误日志，便于排查问题

### 14.3 性能优化

1. **分页查询**：列表查询必须使用分页
2. **字段过滤**：只请求需要的字段（未来可能支持）
3. **缓存策略**：合理使用缓存，减少API调用
4. **批量操作**：尽量使用批量API，减少请求次数

### 14.4 数据验证

1. **前端验证**：提供即时反馈，提升用户体验
2. **后端验证**：后端必须进行完整验证，确保数据安全
3. **业务规则**：遵循业务规则，确保数据一致性

---

## 十五、总结

### 15.1 API统计

- **总端点数**：73+
- **模块数**：5（认证、用户、SD、ENG、PP、MM）
- **数据模型数**：30+

### 15.2 核心特性

- ✅ **RESTful设计**：遵循RESTful API设计原则
- ✅ **JWT认证**：基于JWT的无状态认证
- ✅ **角色权限**：细粒度的角色权限控制
- ✅ **工作流引擎**：支持多部门顺序审批流程
- ✅ **PCB行业特定**：支持拼板、本厂编号、生产版本等特性
- ✅ **状态同步**：生产订单状态自动同步销售订单状态
- ✅ **单位转换**：支持销售单位（PCS）和生产单位（PNL）之间的转换

### 15.3 文档维护

- **更新频率**：随代码更新同步更新
- **维护者**：开发团队
- **反馈渠道**：通过项目Issue反馈

---

**文档版本：** v1.3  
**最后更新：** 2025-12-12  
**维护者：** 开发团队