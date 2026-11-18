# 某某ERP系统 - 领域模型（Domain Model）

**版本：** v1.4  
**创建日期：** 2025-12-18  
**最后更新：** 2025-01-XX  
**说明：** 本文档根据当前后端数据模型（SQLAlchemy models）和 ER 图文件 `某某ERP系统 - ER图模型.puml` 重新生成，用于恢复被清空的领域模型文档。

---

## 一、领域概述

### 1.1 业务领域

系统面向 PCB 制造行业，覆盖以下业务模块：

- **销售与分销（SD）**：客户、报价单、销售订单、本厂编号映射等
- **工程管理（ENG）**：物料主数据（含成品 FG）、BOM、工艺路线、MI、生产版本
- **物料管理（MM）**：物料、生产领料、物料事务
- **生产计划与控制（PP）**：工作中心、生产订单/工单、工序报工、LOT 卡、生产进度
- **用户与权限管理**：用户、角色
- **工作流**：工作流定义、工作流节点、工作流实例

### 1.2 核心流程概览

```text
客户建档 → 报价单 → 销售订单 → 订单评审 → 生产订单/工单 → 工艺准备（BOM/工艺路线/MI/生产版本）
→ LOT卡生成 → 物料领料 → 工序报工 → 生产进度 → 成品入库（后续可扩展）
```

---

## 二、核心实体按模块说明

> 下文只列出与代码中模型直接对应的主要字段和关系，方便与实现对照。

### 2.1 销售与分销模块（SD）

#### 2.1.1 Customer（客户）

- **表：** `customers`
- **主键：** `id`（BaseModel），业务键：`customer_id`
- **核心字段：**
  - `customer_id`：客户编号（业务唯一标识）
  - `legal_name` / `trade_name`：法定名称 / 常用名称
  - `tax_id`：税号
  - `customer_status`：客户状态（Enum：DRAFT, PENDING_SALES_MANAGER, PENDING_FINANCE, PENDING_GENERAL_MANAGER, FROZEN, ACTIVE, BLOCKED, INACTIVE 等）
  - 信用相关：`credit_limit` 等
- **关联：**
  - 1:N `CustomerAddress`（地址）
  - 1:N `CustomerContact`（联系人）
  - 1:N `CustomerPartnerFunction`（合作属性）
  - 1:N `CustomerSalesData`（销售数据）
  - 1:N `Quotation`（报价单）
  - 1:N `SalesOrder`（销售订单）

#### 2.1.2 CustomerAddress（客户地址）

- **表：** `customer_addresses`
- **关键字段：** `customer_id`, `address_type`, `detail_address` 等
- **说明：** 支持配送地址、账单地址等多种地址类型。

#### 2.1.3 CustomerContact（客户联系人）

- **表：** `customer_contacts`
- **关键字段：** `customer_id`, `contact_name`, `contact_role`, `contact_phone`, `contact_email` 等。

#### 2.1.4 CustomerPartnerFunction（客户合作属性）

- **表：** `customer_partner_functions`
- **关键字段：** `partner_role`（SOLD_TO, SHIP_TO, BILL_TO, PAYER），`partner_id` 等。

#### 2.1.5 CustomerSalesData（客户销售数据）

- **表：** `customer_sales_data`
- **关键字段：** 销售组织、客户经理、交易货币、交货条件等。

#### 2.1.6 FactoryProductMapping（本厂编号映射）

- **表：** `factory_product_mappings`
- **用途：** 将客户的本厂编号映射到内部物料编码和生产版本。
- **关键字段：** `customer_id`, `factory_product_number`, `material_code`, `production_version_id`, `is_default`, `effective_date`, `expiry_date`。

#### 2.1.7 Quotation（报价单）

- **表：** `quotations`
- **状态枚举：** `QuotationStatus`（DRAFT, PENDING_SALES, PENDING_ENGINEER, PENDING_ACCOUNT_MANAGER, APPROVED, REJECTED, CUSTOMER_CONFIRMED, LINKED, CANCELLED）
- **关键字段：**
  - 基本：`quotation_number`, `customer_id`, `product_number`（本厂编号，14位）, `quantity`, `unit_price`, `total_amount`, `currency`
  - 审批：`sales_approver`（一级审核，SALES_MANAGER）, `engineer_approver`（二级审核，ENGINEER）, `account_manager_approver`或`general_manager_approver`（三级审核，ACCOUNT_MANAGER或GENERAL_MANAGER）及时间戳
  - 工艺/产品配置：板材、板厚、铜厚、HDI 类型、阻焊/字符颜色、表面处理等
  - 报价计算：`delivery_area`, `actual_p_input`, `cost_per_m2`, `cost_per_pcs`, `quote_price_per_m2`, `quote_price_per_pcs`, `engineering_fee`, `board_material_fee`, `test_fixture`, `other_costs`, `final_total_price`, `process_details`（工序成本明细）
  - 服务、收货、开票、支付、SMT 等辅助信息
- **说明：** 
  - `content` 相关字段分散在结构化列中，不使用 JSON 存储。
  - 报价单预估报价采用手动计算模式（点击"计算报价"按钮）。
  - 报价单审批流程为三级审核串行：一级审核（SALES_MANAGER） → 二级审核（ENGINEER） → 三级审核（ACCOUNT_MANAGER或GENERAL_MANAGER）。
  - 审批通过后进入"销售员经客户确认"状态，客户确认是线下确认，销售员在系统中标记"客户已确认"。
  - 如果本厂编号对应的产品主数据不存在，SD模块调用ENG模块的产品主数据创建API自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），自动创建的产品主数据不需要审核。

#### 2.1.8 SalesOrder（销售订单）

- **表：** `sales_orders`
- **状态枚举：** `SalesOrderStatus`（DRAFT, PENDING_REVIEW, REVIEWING, APPROVED, REJECTED, IN_PRODUCTION, COMPLETED, SHIPPED, DELIVERED, RECONCILED, CLOSED, CANCELLED）
- **关键字段：** `order_number`, `customer_id`, `quotation_number`, `material_code`, `production_version_id`, `quantity`, 各阶段状态时间戳等。
- **关联：** 1:N `ProductionOrder`（在实现中为逻辑关联，通过 `sales_order_number`）。

---

### 2.2 工程管理模块（ENG）

> 物料（包括成品 FG）在代码中统一使用 `Material` 实体，通过 `material_type='FG'` 区分“产品主数据”。

#### 2.2.1 Material（物料 / 产品主数据）

- **表：** `materials`
- **关键字段：**
  - 基本：`material_code`（产品主数据中，material_code = 本厂编号）, `material_name`, `category`, `unit`, `status`, `material_type`（FG/RAW/SEMI）
  - PCB 属性：`layer_count`, `board_thickness`, `copper_weight`, `surface_finish`, `solder_mask_color`, `silkscreen_color`, `impedance_control` 等
  - 尺寸：`unit_length`, `unit_width`, `panel_length`, `panel_width`, `units_per_panel`
  - 供应链：`procurement_type`, `mrp_controller`, `lead_time_days` 等
  - 成本：`valuation_method`, `standard_price`, `currency`
- **说明：**
  - 产品主数据 = `Material` 且 `material_type='FG'`
  - 产品主数据以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）
  - 物料主数据管理页面不展示 FG，产品主数据管理页面只展示 FG
  - 产品主数据由工程管理模块统一管理，ENG模块拥有产品主数据的完整CRUD权限
  - SD模块可以创建（自动创建）、查询、引用产品主数据，但不能修改、删除产品主数据（需ENG模块操作）
  - 所有产品主数据的所有权属于ENG模块

#### 2.2.2 BOM & BOMItem

- **表：** `boms`, `bom_items`
- **BOM 状态：** `BOMStatus`（NEW, REVIEWING, RELEASED, PRODUCING, OBSOLETE）
- **BOM 关键字段：** `bom_number`, `version`, `parent_material_code`, `base_quantity`, `base_uom`, `status`, `effective_date`, `expiry_date`。
- **BOMItem 关键字段：** `bom_number`, `line_number`, `material_code`, `item_category`, `quantity`, `unit`, `scrap_rate`, `layer_code`, `material_type`, `process_step`。

#### 2.2.3 Routing & RoutingOperation（工艺路线及工序）

- **表：** `routings`, `routing_operations`
- **Routing 状态：** `RoutingStatus`（DRAFT, RELEASED, OBSOLETE）
- **Routing 关键字段：** `routing_id`, `version`, `material_code`, `plant_id`, `base_unit`, `base_quantity`, `units_per_panel`, `panel_size`, `status`, `effective_date`, `expiry_date`。
- **RoutingOperation 关键字段：**
  - 工序标识：`routing_id`, `operation_no`, `operation_code`, `operation_name`, `operation_type`
  - 工作中心：`work_center_id`
  - 时间参数：`setup_time`, `machine_time`, `labor_time`, `queue_time`
  - 控制逻辑：`cost_relevant`, `scheduling_relevant`, `needs_reporting`, `auto_deduct_material`, `trigger_quality_check`
  - 外协 & 质检参数：`service_code`, `planned_delivery_days`, `estimated_unit_price`, `inspection_plan_id`, `sampling_rate`, `inspection_type` 等

#### 2.2.4 MI（制造指令）

- **表：** `mis`
- **状态：** `MIStatus`（DRAFT, REVIEWING, APPROVED, RELEASED, OBSOLETE）
- **关键字段：** `mi_number`, `version`, `material_code`, `status`, `effective_date`, `expiry_date`, `content`（JSON，含工艺参数与指令集）。

#### 2.2.5 ProductionVersion（生产版本）

- **表：** `production_versions`
- **说明：** 将 BOM + Routing + MI 组合成可执行的生产版本。
- **关键字段：** `production_version_id`, `material_code`, `bom_number`, `routing_id`, `mi_number`, `version`, `effective_date`, `expiry_date`, `status`。

---

### 2.3 物料管理模块（MM）

#### 2.3.1 Material（物料）

- 同 2.2.1。

#### 2.3.2 MaterialIssue（生产领料）

- **表：** `material_issues`
- **需求名：** 领料单
- **关键字段：** `issue_number`, `production_order_number`, `material_code`, `quantity`, `unit`, `issued_by`, `issued_at`, `warehouse`, `remarks`。

#### 2.3.3 MaterialTransaction（物料事务）

- **表：** `material_transactions`
- **用途：** 记录库存进出、调整明细。
- **关键字段：** `transaction_number`, `material_code`, `transaction_type`, `quantity`, `unit`, `reference_number`, `reference_type`, `warehouse`, `transaction_date`, `operator`。

---

### 2.4 生产计划与控制模块（PP）

#### 2.4.1 WorkCenter（工作中心）

- **表：** `work_centers`
- **类型：** `WorkCenterType`（MACHINE, MACHINE_GROUP, LABOR, PRODUCTION_LINE）
- **状态：** `WorkCenterStatus`（ACTIVE, INACTIVE, IN_MAINTENANCE）
- **关键字段：** `work_center_id`, `description`, `work_center_type`, `plant_id`, 层级与产能、成本、工艺类别、技术属性等。

#### 2.4.2 ProductionOrder（生产订单/工单）

> 在实现中，`ProductionOrder` 同时承担“生产订单”和“工单”的职责：既承接销售订单，又作为生产执行和报工的载体，MVP 中不再单独建 WorkOrder 表。

- **表：** `production_orders`
- **状态：** `ProductionOrderStatus`（DRAFT, RELEASED, IN_PRODUCTION, COMPLETED, CLOSED, CANCELLED）
- **关键字段：**
  - `order_number`：生产订单（工单）号
  - `sales_order_number`：关联销售订单
  - `material_code`：生产物料（通常为 FG 产品）
  - `production_version_id`：关联生产版本
  - `quantity`, `unit`：生产数量与单位
  - 计划/实际时间：`planned_start_date`, `planned_finish_date`, `actual_start_date`, `actual_finish_date`
  - `status`：生产订单/工单状态
  - `lot_number`：关联 LOT 卡号
  - 销售订单数量和单位转换：`sales_quantity`, `sales_unit`, `conversion_factor`

#### 2.4.3 OperationReport（工序报工 / 报工单）

- **表：** `operation_reports`
- **状态：** `OperationReportStatus`（PENDING, IN_PROGRESS, COMPLETED, REJECTED）
- **关键字段：**
  - `report_number`：报工单号
  - `production_order_number`：关联生产订单/工单
  - `lot_number`：LOT 卡号（系统根据生产订单/工单号自动查询关联的LOT卡，1:1关系，只读、不可修改）
  - `routing_operation_id`：关联工艺路线工序
  - `work_center_id`, `operation_no`, `operation_name`
  - 数量：`reported_quantity`, `good_quantity`, `scrap_quantity`
  - 时间：`setup_time`, `machine_time`, `labor_time`
  - 报工人及时间：`reported_by`, `reported_at`
- **说明：**
  - 系统根据生产订单/工单号自动查询关联的LOT卡（一个生产订单/工单对应一个LOT卡，1:1关系）
  - 系统自动填充报工单中的LOT卡号字段（只读、不可修改）
  - 如果找不到LOT卡，不允许保存报工

#### 2.4.4 LotCard（LOT卡）

- **表：** `lot_cards`
- **说明：** 由 MI 自动生成的生产批次卡，关联生产订单/工单，用于工序报工。一个生产订单/工单对应一个LOT卡（1:1关系）。
- **关键字段：** 
  - `lot_number`：LOT卡号（系统自动生成）
  - `production_order_number`：关联生产订单/工单号（1:1关系）
  - `mi_number`：关联MI编号
  - `material_code`：物料编码
  - `quantity`, `unit`：数量、单位
  - `status`：状态（ACTIVE, COMPLETED, CANCELLED）
  - `mi_content`：MI内容（JSON格式，可编辑）
  - `completed_at`：完成时间
  - `remarks`：备注（可编辑）
- **生成逻辑：**
  - 创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡
  - 系统自动复制MI内容（mi_content）到LOT卡
  - 系统将lot_number写回生产订单/工单
  - 如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI
- **编辑功能：**
  - 支持编辑LOT卡的MI内容（mi_content）和备注（remarks）
  - 支持JSON格式解析为列表，每一条指令/属性项可单独编辑

#### 2.4.5 ProductionProgress（生产进度）

- **表：** `production_progress`
- **说明：** 用于生产进度看板，记录每个生产订单在各工序的计划与完成情况。

---

### 2.5 用户与权限管理

#### 2.5.1 User（用户）

- **表：** `users`
- **角色：** `UserRole`（SALES, SALES_MANAGER, ENGINEER, PLANNER, PRODUCTION, WAREHOUSE, FINANCE, ACCOUNT_MANAGER, GENERAL_MANAGER, ADMIN）
- **关键字段：** `username`, `email`, `password_hash`, `full_name`, `role`, `department`, `is_active`, `phone`。
- **角色说明：**
  - `SALES`：销售员，负责客户管理、报价单创建和销售订单创建
  - `SALES_MANAGER`：销售经理，负责报价单一级审核、销售订单评审
  - `ENGINEER`：工程师，负责工程数据管理、报价单二级审核、销售订单工程部门评审
  - `ACCOUNT_MANAGER`：客户经理，负责报价单三级审核（与GENERAL_MANAGER共同承担）
  - `GENERAL_MANAGER`：总经理，负责报价单三级审核（与ACCOUNT_MANAGER共同承担）

---

### 2.6 工作流模块

> 工作流模型位于独立的 `workflow` 相关表中（在 ER 图和工作流实现中定义），本重建文档不再逐字段展开，仅保留高层说明：

- `Workflow`：工作流定义
- `WorkflowNode`：工作流节点
- `WorkflowInstance`：工作流实例
- `WorkflowInstanceNode`：节点实例

---

## 三、聚合与关系概览（简要版）

- **Customer 聚合根**：Customer + Address + Contact + PartnerFunction + SalesData
- **销售订单聚合**：SalesOrder + ContractReview + ProductionOrder（逻辑关联）
- **工程数据聚合**：Material + BOM + BOMItem + Routing + RoutingOperation + MI + ProductionVersion
- **生产执行聚合**：ProductionOrder（工单） + LotCard + OperationReport + ProductionProgress
- **库存聚合**：Material + MaterialIssue + MaterialTransaction

---

> 说明：本文件为“重建版领域模型”，重点保证与**当前代码实现和 ER 图**一致，未逐字恢复原先所有叙述性文字。如需在某个模块上补充更详细的业务背景或规则，可以在此基础上逐段扩展。