# SD模块 - 客户管理子模块领域模型

**对应菜单：** `/sd/customers`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

客户管理子模块负责管理客户主数据，包括客户基本信息、地址、联系人、合作属性和销售数据。客户需要经过审批流程才能激活使用。

---

## 二、核心实体

### 2.1 Customer（客户）

- **表：** `customers`
- **主键：** `id`（BaseModel），业务键：`customer_id`
- **核心字段：**
  - `customer_id`：客户编号（业务唯一标识）
  - `legal_name` / `trade_name`：法定名称 / 常用名称
  - `tax_id`：税号
  - `customer_industry`：行业
  - `customer_website`：网站
  - `customer_status`：客户状态（Enum：DRAFT, PENDING_APPROVAL, ACTIVE, BLOCKED, INACTIVE）
  - 信用相关：`credit_limit` 等
- **关联：**
  - 1:N `CustomerAddress`（地址）
  - 1:N `CustomerContact`（联系人）
  - 1:N `CustomerPartnerFunction`（合作属性）
  - 1:N `CustomerSalesData`（销售数据）
  - 1:N `Quotation`（报价单）
  - 1:N `SalesOrder`（销售订单）
  - 1:N `FactoryProductMapping`（本厂编号映射）

### 2.2 CustomerAddress（客户地址）

- **表：** `customer_addresses`
- **关键字段：**
  - `customer_id`：客户ID（外键）
  - `address_type`：地址类型（HEADQUARTERS, PLANT, WAREHOUSE, BILLING）
  - `detail_address`：详细地址
  - `location`：位置
  - `postal_code`：邮编
  - `country`：国家（默认'中国'）
  - `province`：省份
  - `city`：城市
  - `district`：区县
  - `is_default_shipping`：是否默认发货地址
  - `is_default_billing`：是否默认账单地址
- **说明：** 支持配送地址、账单地址等多种地址类型。客户可以有多个地址，但只能有一个默认发货地址和一个默认账单地址。

### 2.3 CustomerContact（客户联系人）

- **表：** `customer_contacts`
- **关键字段：**
  - `customer_id`：客户ID（外键）
  - `contact_name`：联系人姓名
  - `contact_role`：联系人角色
  - `contact_department`：部门
  - `contact_phone`：电话
  - `contact_email`：邮箱
- **说明：** 支持添加多个联系人。

### 2.4 CustomerPartnerFunction（客户合作属性）

- **表：** `customer_partner_functions`
- **关键字段：**
  - `customer_id`：客户ID（外键）
  - `partner_role`：合作角色（SOLD_TO, SHIP_TO, BILL_TO, PAYER等）
  - `partner_id`：合作伙伴ID
  - `cooperation_type`：合作类型
  - `start_date`：合作开始日期
- **说明：** 支持添加多个合作属性。

### 2.5 CustomerSalesData（客户销售数据）

- **表：** `customer_sales_data`
- **关键字段：**
  - `customer_id`：客户ID（外键）
  - `sales_organization`：销售组织
  - `sales_channel`：销售渠道
  - `account_manager`：客户经理
  - `currency`：交易货币
  - `delivery_terms`：交货条件
- **说明：** 存储客户的销售相关数据。

### 2.6 FactoryProductMapping（本厂编号映射）

- **表：** `factory_product_mappings`
- **用途：** 将客户的本厂编号映射到内部物料编码和生产版本。
- **关键字段：**
  - `customer_id`：客户ID（外键）
  - `factory_product_number`：本厂编号（14位，同客户下唯一）
  - `material_code`：物料编码（外键 → materials.material_code）
  - `production_version_id`：生产版本ID（可选，外键 → production_versions.production_version_id）
  - `is_default`：是否默认
  - `effective_date`：生效日期
  - `expiry_date`：失效日期
- **说明：** 用于销售订单快速引用，系统根据客户ID和本厂编号自动查找映射。

---

## 三、状态机

### 3.1 Customer状态

- **DRAFT**：草稿，客户信息创建但未提交审批
- **PENDING_APPROVAL**：待审批，已提交审批，等待审批人审批
- **ACTIVE**：激活，审批通过，客户处于激活状态
- **BLOCKED**：冻结，客户被冻结，不能进行业务操作
- **INACTIVE**：未激活，客户处于未激活状态

### 3.2 状态转换规则

- DRAFT → PENDING_APPROVAL：提交审批（销售员）
- PENDING_APPROVAL → ACTIVE：审批通过（销售经理）
- PENDING_APPROVAL → DRAFT：审批拒绝（销售经理）
- ACTIVE → BLOCKED：冻结客户（销售经理/管理员）
- ACTIVE → INACTIVE：停用客户（销售经理/管理员）
- BLOCKED → ACTIVE：解冻客户（销售经理/管理员）
- INACTIVE → ACTIVE：激活客户（销售经理/管理员）

---

## 四、业务规则

1. **客户ID唯一性**：客户ID（customer_id）必须在系统中唯一。
2. **审批流程**：客户状态必须经过审批流程：DRAFT → PENDING_APPROVAL → ACTIVE。
3. **地址约束**：客户可以有多个地址，但只能有一个默认发货地址和一个默认账单地址。
4. **业务使用限制**：只有ACTIVE状态的客户才能创建报价单和销售订单。
5. **本厂编号唯一性**：本厂编号为14位，且在同一客户下唯一。

---

## 五、聚合根

**Customer聚合根**：Customer + CustomerAddress + CustomerContact + CustomerPartnerFunction + CustomerSalesData + FactoryProductMapping

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-SD-001, UC-SD-002, UC-SD-003
- [用户故事文档](../用户故事/SD-客户管理用户故事.md)
- [状态机文档](../状态机图/SD-客户管理状态机.puml)
