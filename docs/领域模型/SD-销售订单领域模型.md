# SD模块 - 销售订单子模块领域模型

**对应菜单：** `/sd/sales-orders`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

销售订单子模块负责管理销售订单，包括订单创建、多部门评审流程、发货、签收、对账、关闭等。销售订单需要经过销售、工程、物料、财务四个部门的串行评审。

---

## 二、核心实体

### 2.1 SalesOrder（销售订单）

- **表：** `sales_orders`
- **主键：** `id`（BaseModel），业务键：`order_number`
- **状态枚举：** `SalesOrderStatus`（DRAFT, PENDING_REVIEW, REVIEWING, APPROVED, REJECTED, IN_PRODUCTION, COMPLETED, SHIPPED, DELIVERED, RECONCILED, CLOSED, CANCELLED）
- **关键字段：**
  - **基本字段：**
    - `order_number`：订单号
    - `customer_id`：客户ID（外键 → customers.customer_id）
    - `quotation_number`：关联报价单号（可选，外键 → quotations.quotation_number）
    - `is_return_order`：是否返单（布尔值）
    - `factory_product_number`：本厂编号（14位）
    - `material_code`：物料编码（外键 → materials.material_code）
    - `production_version_id`：生产版本ID（外键 → production_versions.production_version_id）
    - `quantity`：数量
    - `unit`：单位
    - `delivery_date`：交货日期
  - **单位转换：**
    - `sales_unit`：销售单位
    - `production_unit`：生产单位
    - `conversion_factor`：转换系数
    - `production_quantity`：生产数量（quantity * conversion_factor）
  - **状态时间戳：**
    - `submitted_at`：提交评审时间
    - `approved_at`：审批通过时间
    - `shipped_at`：发货时间
    - `delivered_at`：签收时间
    - `reconciled_at`：对账时间
    - `closed_at`：关闭时间
  - **评审状态：**
    - `review_status`：评审状态（PENDING, REVIEWING, APPROVED, REJECTED）
- **关联：**
  - N:1 `Customer`（客户）
  - N:1 `Quotation`（报价单，可选）
  - N:1 `Material`（物料）
  - N:1 `ProductionVersion`（生产版本）
  - 1:N `ContractReview`（订单评审记录）
  - 1:N `ProductionOrder`（生产订单，逻辑关联）
- **说明：**
  - 创建销售订单时，系统根据客户ID和本厂编号自动查找FactoryProductMapping，自动填充material_code和production_version_id。
  - 如果是返单（is_return_order=true），可以选择历史报价单（包括已关联的）并修改数量。
  - 如果是新单，只能选择已批准且未关联的报价单，数量不可修改。
  - 如果关联了报价单，报价单状态更新为LINKED。
  - 销售订单必须经过多部门评审：销售部门 → 工程部门 → 物料部门 → 财务部门（串行）。
  - 评审过程中，订单状态为REVIEWING。
  - 当任一部门拒绝时，订单状态转为REJECTED，然后自动退回DRAFT。
  - 当所有部门都通过时，订单状态转为APPROVED。
  - 关闭销售订单时，会同时关闭关联的生产订单/工单。

### 2.2 ContractReview（订单评审记录）

- **表：** `contract_reviews`
- **关键字段：**
  - `sales_order_number`：销售订单号（外键）
  - `review_node`：评审节点（SALES_REVIEW, ENGINEERING_REVIEW, WAREHOUSE_REVIEW, FINANCE_REVIEW）
  - `reviewer_id`：评审人ID
  - `reviewer_role`：评审人角色
  - `review_status`：评审状态（APPROVED, REJECTED）
  - `review_comment`：评审意见
  - `reviewed_at`：评审时间
- **说明：** 记录每个部门的评审结果。

---

## 三、状态机

### 3.1 SalesOrder状态

- **DRAFT**：草稿，销售订单创建但未提交
- **PENDING_REVIEW**：待评审，已提交，等待订单评审
- **REVIEWING**：评审中，正在进行多部门评审（串行：销售→工程→物料→财务）
- **APPROVED**：已审批，所有部门评审通过
- **REJECTED**：已拒绝，任一部门评审拒绝，退回草稿状态
- **IN_PRODUCTION**：生产中，已创建生产订单，正在生产
- **COMPLETED**：已完成，生产完成
- **SHIPPED**：已发货，货物已发出
- **DELIVERED**：已交付，客户已签收
- **RECONCILED**：已对账，财务已对账
- **CLOSED**：已关闭，订单流程结束
- **CANCELLED**：已取消，订单被取消

### 3.2 状态转换规则

- DRAFT → PENDING_REVIEW：提交评审（销售员）
- PENDING_REVIEW → REVIEWING：开始评审（系统自动）
- REVIEWING → APPROVED：所有部门评审通过（系统自动）
- REVIEWING → REJECTED：任一部门评审拒绝（各部门评审人）
- REJECTED → DRAFT：退回草稿（系统自动）
- DRAFT → PENDING_REVIEW：重新提交（销售员）
- APPROVED → IN_PRODUCTION：创建生产订单（计划员/生产人员）
- IN_PRODUCTION → COMPLETED：生产完成（系统自动）
- COMPLETED → SHIPPED：发货（销售员）
- SHIPPED → DELIVERED：客户签收（销售员）
- DELIVERED → RECONCILED：财务对账（财务人员）
- RECONCILED → CLOSED：关闭订单（销售员/财务人员）

---

## 四、业务规则

1. **客户状态要求**：只有ACTIVE状态的客户才能创建销售订单。
2. **返单逻辑**：如果是返单（is_return_order=true），可以选择历史报价单（包括已关联的）并修改数量。
3. **新单逻辑**：如果是新单，只能选择已批准且未关联的报价单，数量不可修改。
4. **本厂编号映射**：创建销售订单时，系统根据客户ID和本厂编号自动查找FactoryProductMapping，获取material_code和production_version_id。
5. **多部门评审**：销售订单必须经过多部门评审（串行）：销售部门 → 工程部门 → 物料部门 → 财务部门。
6. **评审拒绝处理**：当任一部门拒绝时，订单状态转为REJECTED，然后自动退回DRAFT。拒绝后，销售员可以修改订单并重新提交评审。
7. **状态同步**：生产订单状态变化时，自动同步销售订单状态。如果所有生产订单都已完成，销售订单状态更新为COMPLETED。
8. **关闭关联**：关闭销售订单时，会同时关闭关联的生产订单/工单。

---

## 五、聚合根

**销售订单聚合**：SalesOrder + ContractReview + ProductionOrder（逻辑关联）

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-SD-010 至 UC-SD-020
- [用户故事文档](../用户故事/SD-销售订单用户故事.md)
- [状态机文档](../状态机图/SD-销售订单状态机.puml)
