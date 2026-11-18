# 某某ERP系统 - 术语表（Glossary）

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-12-12  
**最后更新：** 2025-01-XX

本文档定义了某某ERP系统中使用的重要术语、缩写和概念，帮助开发团队、业务人员和用户理解系统的业务和技术术语。

---

## 一、业务术语（Business Terms）

### A

**AOI（Automated Optical Inspection）**
- **中文名称**：自动光学检测
- **定义**：使用光学设备自动检测PCB板的质量和缺陷
- **使用场景**：工艺路线中的质检工序类型

### B

**BOM（Bill of Materials）**
- **中文名称**：物料清单
- **定义**：定义产品的物料组成结构，包含所有子物料及其用量
- **使用场景**：用于计算生产所需的原材料，是生产版本的重要组成部分
- **相关实体**：BOM, BOMItem

**本厂编号（Factory Product Number）**
- **英文名称**：Factory Product Number
- **定义**：客户使用的产品编号，用于标识客户的产品，通常为14位编号
- **使用场景**：在创建销售订单时，系统根据客户ID和本厂编号查找FactoryProductMapping，获取系统内部的物料编码和生产版本
- **示例**：HS1004ENIGAB01

**本厂编号映射（Factory Product Mapping）**
- **英文名称**：Factory Product Mapping
- **定义**：将客户的本厂编号映射到系统内部的物料编码和生产版本
- **使用场景**：创建销售订单时，系统根据客户ID和本厂编号自动查找映射，获取物料编码和生产版本
- **相关实体**：FactoryProductMapping

**报价单（Quotation）**
- **英文名称**：Quotation
- **定义**：向客户提供的报价单，包含产品信息（本厂编号、产品名称）、价格和有效期。报价单预估报价采用手动计算模式（点击"计算报价"按钮）
- **使用场景**：销售员创建报价单，经过三级审核（串行：一级审核SALES_MANAGER → 二级审核ENGINEER → 三级审核ACCOUNT_MANAGER或GENERAL_MANAGER）后，销售员经客户确认（客户确认是线下确认，销售员在系统中标记"客户已确认"），可以转成销售订单
- **相关实体**：Quotation, QuotationItem
- **审批流程**：三级审核流程（串行）：DRAFT → 待一级审核（SALES_MANAGER） → 待二级审核（ENGINEER） → 待三级审核（ACCOUNT_MANAGER或GENERAL_MANAGER） → APPROVED → 销售员经客户确认 → 可转订单

### C

**客户（Customer）**
- **英文名称**：Customer
- **定义**：与公司有业务往来的客户，包含基本信息、地址、联系人等
- **使用场景**：客户管理、报价单、销售订单的基础数据
- **相关实体**：Customer, CustomerAddress, CustomerContact, CustomerPartnerFunction, CustomerSalesData

**销售员经客户确认报价单（Sales Representative Confirms with Customer）**
- **英文名称**：Sales Representative Confirms with Customer
- **定义**：销售员与客户确认报价单，客户确认是线下确认，销售员在系统中标记"客户已确认"。客户确认后可以转为销售订单
- **使用场景**：报价单通过三级审核后，进入"销售员经客户确认"状态。客户确认后可以转为销售订单。客户不确认时，报价单退回草稿状态，销售员可修改后重新提交审核

**工序（Operation）**
- **英文名称**：Routing Operation
- **定义**：工艺路线中的单个生产步骤，定义工序类型、工作中心、时间参数等
- **使用场景**：工艺路线由多个工序组成，生产人员按照工序进行报工
- **相关实体**：RoutingOperation

**工序报工（Operation Report）**
- **英文名称**：Operation Report
- **定义**：记录生产订单/工单的工序报工信息，包括报工数量、时间和质量数据。系统根据生产订单/工单号自动查询关联的LOT卡（1:1关系），并自动填充报工单中的LOT卡号字段（只读、不可修改）
- **使用场景**：生产人员完成某个工序后，进行报工，系统更新生产进度。如果找不到LOT卡，不允许保存报工
- **相关实体**：OperationReport

**生产订单/工单（Production Order / Work Order）**
- **英文名称**：Production Order / Work Order
- **定义**：生产订单和工单在系统中由同一个实体`ProductionOrder`承担，既承接销售订单，又作为生产执行和报工的载体。工单状态与生产订单状态一致
- **使用场景**：在生产计划与控制模块中，生产订单也称为工单。创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡（1:1关系）
- **相关实体**：ProductionOrder

**工作中心（Work Center）**
- **英文名称**：Work Center
- **定义**：生产资源的基本单位，可以是单台机器、机组、人工工位或产线
- **使用场景**：工艺路线中的工序需要指定工作中心，工序报工时也需要指定工作中心
- **相关实体**：WorkCenter

**工作流（Workflow）**
- **英文名称**：Workflow
- **定义**：定义审批流程的结构，包含多个节点和顺序
- **使用场景**：报价单审批、销售订单多部门评审等审批流程
- **相关实体**：Workflow, WorkflowNode, WorkflowInstance, WorkflowInstanceNode

### D

**订单评审（Order Review）**
- **英文名称**：Contract Review / Order Review
- **定义**：销售订单需要经过多部门评审（销售、工程、物料、财务）的流程
- **使用场景**：销售订单提交后，需要经过四个部门顺序评审，确保订单可执行
- **相关实体**：ContractReview

**对账（Reconciliation）**
- **英文名称**：Reconciliation
- **定义**：财务人员对销售订单进行对账，确认订单金额和收款情况
- **使用场景**：销售订单签收后，财务人员进行对账，完成后订单状态变为RECONCILED

### F

**返单（Return Order）**
- **英文名称**：Return Order
- **定义**：客户重复下单，可以选择历史报价单的销售订单
- **使用场景**：创建销售订单时，如果选择返单（is_return_order=true），可以选择历史报价单（包括已关联的），并且可以修改数量

### G

**工艺路线（Routing）**
- **英文名称**：Routing
- **定义**：定义产品的生产工艺流程，包含工序序列、工作中心和时间参数
- **使用场景**：生产版本的重要组成部分，用于指导生产执行和工序报工
- **相关实体**：Routing, RoutingOperation

### J

**价格（Price）**
- **英文名称**：Price
- **定义**：产品或服务的价格
- **使用场景**：报价单中的单价、总金额等

### K

**库存（Stock / Inventory）**
- **英文名称**：Stock / Inventory
- **定义**：物料的当前可用数量
- **使用场景**：物料管理、生产领料时需要检查库存是否充足
- **相关字段**：Material.current_stock

### L

**领料（Material Issue）**
- **英文名称**：Material Issue
- **定义**：从仓库领料用于生产的操作
- **使用场景**：生产订单下达后，物料管理员创建生产领料单，从仓库领料
- **相关实体**：MaterialIssue

### M

**MI（Manufacturing Instruction）**
- **中文名称**：制造指令
- **定义**：包含详细的工艺参数和操作指导，用于指导生产人员按照标准工艺进行生产
- **使用场景**：生产版本的重要组成部分，发布生产版本时MI是必选的
- **相关实体**：MI

**物料（Material）**
- **英文名称**：Material
- **定义**：物料主数据，包含物料的基本信息、PCB工程属性、供应链计划和库存信息。物料主数据管理中不显示成品(FG类型)，成品通过工程管理模块的产品主数据管理进行维护
- **使用场景**：系统的基础数据，BOM、工艺路线、生产订单/工单等都基于物料
- **相关实体**：Material

**产品主数据（Product Master Data）**
- **英文名称**：Product Master Data
- **定义**：成品(FG类型)的主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）。产品主数据包含产品基本信息、PCB专有工程属性（层数、板厚、铜厚、表面处理等）、技术参数、尺寸信息、供应链计划参数等
- **使用场景**：产品主数据由工程管理模块统一管理，ENG模块拥有产品主数据的完整CRUD权限。SD模块可以创建（自动创建）、查询、引用产品主数据，但不能修改、删除产品主数据（需ENG模块操作）。所有产品主数据的所有权属于ENG模块
- **相关实体**：Material（material_type='FG'）

**物料编码（Material Code）**
- **英文名称**：Material Code
- **定义**：系统内部用于标识物料的唯一编码
- **使用场景**：物料的主键，用于关联BOM、工艺路线、生产订单等

**物料事务（Material Transaction）**
- **英文名称**：Material Transaction
- **定义**：记录所有物料库存变动的事务（入库、出库、调整等）
- **使用场景**：每次物料库存变动都会生成一条MaterialTransaction记录，用于库存追溯
- **相关实体**：MaterialTransaction

### P

**PCB（Printed Circuit Board）**
- **中文名称**：印刷电路板
- **定义**：本系统面向的制造行业，PCB是电子设备的基础组件
- **使用场景**：系统设计考虑了PCB行业的特定需求，如拼板、层码、表面处理等

**PNL（Panel）**
- **中文名称**：拼板
- **定义**：PCB生产的基本单位，一个Panel包含多个Unit（单元）
- **使用场景**：生产单位通常为PNL，用于PCB行业的生产和BOM计算

**PCS（Pieces）**
- **中文名称**：个/件
- **定义**：基础单位，通常用于销售和库存
- **使用场景**：销售单位通常为PCS，用于客户交付

**生产版本（Production Version）**
- **英文名称**：Production Version
- **定义**：BOM、工艺路线和MI的组合，是生产订单/工单的基础。BOM和工艺路线准备可以并行进行，无依赖关系。生产版本建立必须等待BOM和工艺路线都准备好
- **使用场景**：创建生产订单/工单时，必须选择生产版本，系统根据生产版本自动填充物料编码等信息。生产版本发布需要MI已制作且MI审核通过
- **相关实体**：ProductionVersion

**生产版本发布（Production Version Release）**
- **英文名称**：Production Version Release
- **定义**：将生产版本从创建状态发布为可用状态，发布时MI是必选的
- **使用场景**：在生产执行全流程中，MI制作环节包含生产版本发布，发布后的生产版本可用于生产订单下达
- **流程位置**：订单评审 → 产品主数据确认 → BOM和工艺路线准备 → 生产版本建立 → MI制作（含生产版本发布）→ 生产订单下达

**生产订单/工单（Production Order / Work Order）**
- **英文名称**：Production Order / Work Order
- **定义**：生产执行的依据，关联销售订单和生产版本。在实现中，`ProductionOrder`同时承担"生产订单"和"工单"的职责，工单状态与生产订单状态一致
- **使用场景**：销售订单审批通过后，创建生产订单/工单，启动生产执行流程。创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡（1:1关系）。如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI
- **相关实体**：ProductionOrder

**生产领料（Production Material Issue）**
- **英文名称**：Production Material Issue
- **定义**：从仓库领料用于生产的单据
- **使用场景**：生产订单/工单下达后，物料管理员创建生产领料单
- **相关实体**：MaterialIssue

**LOT卡（Lot Card）**
- **英文名称**：Lot Card
- **定义**：由MI自动生成的生产批次卡，关联生产订单/工单，用于工序报工。一个生产订单/工单对应一个LOT卡（1:1关系）
- **使用场景**：创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡，自动复制MI内容并写回lot_number到生产订单/工单。工序报工时，系统根据生产订单/工单号自动查询关联的LOT卡，并自动填充报工单中的LOT卡号字段（只读、不可修改）
- **相关实体**：LotCard
- **编辑功能**：支持编辑LOT卡的MI内容（mi_content）和备注（remarks），支持JSON格式解析为列表，每一条指令/属性项可单独编辑

### Q

**评审（Review / Approval）**
- **英文名称**：Review / Approval
- **定义**：对业务单据进行审核和批准的过程
- **使用场景**：报价单审批、销售订单多部门评审等

### S

**销售订单（Sales Order）**
- **英文名称**：Sales Order
- **定义**：客户下达的销售订单，是生产计划的源头
- **使用场景**：销售员创建销售订单，经过多部门评审后，可以创建生产订单/工单
- **相关实体**：SalesOrder

**生产单位（Production Unit）**
- **英文名称**：Production Unit
- **定义**：用于生产的单位，通常为PNL（拼板）
- **使用场景**：生产订单、BOM、工艺路线使用生产单位

**销售单位（Sales Unit）**
- **英文名称**：Sales Unit
- **定义**：用于销售的单位，通常为PCS（个）
- **使用场景**：销售订单使用销售单位

**单位转换系数（Conversion Factor）**
- **英文名称**：Conversion Factor
- **定义**：销售单位和生产单位之间的转换系数
- **使用场景**：1 PNL = N PCS，用于计算生产数量

### T

**投产（Release）**
- **英文名称**：Release
- **定义**：将BOM、工艺路线、生产订单等从草稿状态发布为可用状态
- **使用场景**：BOM、工艺路线发布后可以用于生产版本，生产订单下达后可以开始生产

### W

**外协（External）**
- **英文名称**：External
- **定义**：需要外包给外部供应商完成的工序
- **使用场景**：工艺路线中的工序类型，系统会自动生成采购申请

### X

**新单（New Order）**
- **英文名称**：New Order
- **定义**：客户首次下单，只能选择已批准且未关联的报价单
- **使用场景**：创建销售订单时，如果选择新单，只能选择已批准且未关联的报价单，数量不可修改

### Y

**已关联（Linked）**
- **英文名称**：Linked
- **定义**：报价单已关联到销售订单的状态
- **使用场景**：报价单关联到销售订单后，状态变为LINKED，新单不能再选择已关联的报价单

---

## 二、状态枚举（Status Enums）

### 2.1 客户状态（Customer Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | 客户刚创建，未提交审批 |
| PENDING_SALES_MANAGER | 待销售经理审批 | Pending Sales Manager Approval | 客户已提交审批，等待销售经理审批 |
| PENDING_FINANCE | 待财务审批 | Pending Finance Approval | 销售经理审批通过，等待财务审批 |
| PENDING_GENERAL_MANAGER | 待总经理审批 | Pending General Manager Approval | 财务审批通过，等待总经理审批 |
| PENDING_APPROVAL | 待审批 | Pending Approval | 兼容老值，不再使用 |
| FROZEN | 已建档（冻结） | Frozen | 已建档但等待激活 |
| ACTIVE | 激活 | Active | 客户审批通过，可以用于业务 |
| BLOCKED | 已冻结 | Blocked | 客户被冻结，不能用于业务 |
| INACTIVE | 未激活 | Inactive | 客户未激活，不能用于业务 |

### 2.2 报价单状态（Quotation Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | 报价单刚创建，未提交审批 |
| PENDING_SALES | 待一级审核 | Pending First Level Approval | 报价单已提交，等待销售经理（SALES_MANAGER）一级审核 |
| PENDING_ENGINEER | 待二级审核 | Pending Second Level Approval | 一级审核通过，等待工程师（ENGINEER）二级审核 |
| PENDING_ACCOUNT_MANAGER | 待三级审核 | Pending Third Level Approval | 二级审核通过，等待客户经理（ACCOUNT_MANAGER）或总经理（GENERAL_MANAGER）三级审核 |
| PENDING_GENERAL_MANAGER | 待三级审核 | Pending Third Level Approval | 二级审核通过，等待客户经理（ACCOUNT_MANAGER）或总经理（GENERAL_MANAGER）三级审核（兼容老值） |
| APPROVED | 已批准 | Approved | 报价单三级审核通过，进入"销售员经客户确认"状态 |
| REJECTED | 已拒绝 | Rejected | 报价单被拒绝，退回草稿状态，销售员可以修改后重新提交。退回操作记录审核历史，保存退回原因 |
| CUSTOMER_CONFIRMED | 销售员经客户确认 | Sales Representative Confirms with Customer | 销售员与客户确认报价单（客户确认是线下确认，销售员在系统中标记"客户已确认"），可以转成销售订单 |
| LINKED | 已关联 | Linked | 报价单已关联到销售订单 |
| CANCELLED | 已取消 | Cancelled | 报价单已取消 |

### 2.3 销售订单状态（Sales Order Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | 销售订单刚创建，未提交评审 |
| PENDING_REVIEW | 待评审 | Pending Review | 销售订单已提交评审，等待各部门评审 |
| REVIEWING | 评审中 | Reviewing | 销售订单正在评审中 |
| APPROVED | 已批准 | Approved | 销售订单评审通过，可以创建生产订单 |
| REJECTED | 已拒绝 | Rejected | 销售订单被拒绝 |
| IN_PRODUCTION | 生产中 | In Production | 销售订单关联的生产订单已开始生产 |
| COMPLETED | 已完成 | Completed | 销售订单关联的所有生产订单都已完成 |
| SHIPPED | 已发货 | Shipped | 销售订单已发货 |
| DELIVERED | 已签收 | Delivered | 销售订单已签收 |
| RECONCILED | 已对账 | Reconciled | 销售订单对账完成 |
| CLOSED | 已关闭 | Closed | 销售订单已关闭 |
| CANCELLED | 已取消 | Cancelled | 销售订单已取消 |

### 2.4 评审状态（Review Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| PENDING | 待评审 | Pending | 等待评审 |
| REVIEWING | 评审中 | Reviewing | 正在评审中 |
| APPROVED | 已批准 | Approved | 评审通过 |
| REJECTED | 已拒绝 | Rejected | 评审被拒绝 |

### 2.5 BOM状态（BOM Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| NEW | 新建 | New | BOM刚创建 |
| REVIEWING | 评审中 | Reviewing | BOM正在评审中 |
| RELEASED | 已发布 | Released | BOM已发布，可以用于生产版本 |
| PRODUCING | 生产中 | Producing | BOM正在生产中 |
| OBSOLETE | 已废弃 | Obsolete | BOM已废弃 |

### 2.6 工艺路线状态（Routing Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | 工艺路线刚创建 |
| RELEASED | 已发布 | Released | 工艺路线已发布，可以用于生产版本 |
| OBSOLETE | 已废弃 | Obsolete | 工艺路线已废弃 |

### 2.7 MI状态（MI Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | MI刚创建 |
| REVIEWING | 评审中 | Reviewing | MI正在评审中 |
| APPROVED | 已批准 | Approved | MI已批准 |
| RELEASED | 已发布 | Released | MI已发布，可以用于生产版本 |
| OBSOLETE | 已废弃 | Obsolete | MI已废弃 |

### 2.8 生产订单状态（Production Order Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | 生产订单刚创建 |
| RELEASED | 已下达 | Released | 生产订单已下达，可以开始生产 |
| IN_PRODUCTION | 生产中 | In Production | 生产订单正在生产中 |
| COMPLETED | 已完成 | Completed | 生产订单已完成 |
| CLOSED | 已关闭 | Closed | 生产订单已关闭 |
| CANCELLED | 已取消 | Cancelled | 生产订单已取消 |

### 2.9 工序报工状态（Operation Report Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| PENDING | 待处理 | Pending | 工序报工刚创建 |
| IN_PROGRESS | 进行中 | In Progress | 工序报工正在进行中 |
| COMPLETED | 已完成 | Completed | 工序报工已完成 |
| REJECTED | 已拒绝 | Rejected | 工序报工被拒绝 |

### 2.10 工作中心状态（Work Center Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| ACTIVE | 激活 | Active | 工作中心正常使用 |
| INACTIVE | 未激活 | Inactive | 工作中心未激活 |
| IN_MAINTENANCE | 维护中 | In Maintenance | 工作中心正在维护 |

### 2.11 物料状态（Material Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| ACTIVE | 激活 | Active | 物料正常使用 |
| OBSOLETE | 已废弃 | Obsolete | 物料已废弃 |
| DRAFT | 草稿 | Draft | 物料刚创建 |

### 2.12 物料类型（Material Type）

| 类型值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| FG | 成品 | Finished Goods | 最终交付给客户的产品 |
| RAW | 原材料 | Raw Material | 用于生产的原材料 |
| SEMI | 半成品 | Semi-finished Goods | 生产过程中的半成品 |

### 2.13 工作流状态（Workflow Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRAFT | 草稿 | Draft | 工作流实例刚创建 |
| PENDING | 待处理 | Pending | 工作流实例等待处理 |
| APPROVED | 已批准 | Approved | 工作流实例已批准 |
| REJECTED | 已拒绝 | Rejected | 工作流实例被拒绝 |
| COMPLETED | 已完成 | Completed | 工作流实例已完成 |

### 2.14 工作流节点状态（Workflow Node Status）

| 状态值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| PENDING | 待处理 | Pending | 节点等待处理 |
| APPROVED | 已批准 | Approved | 节点已批准 |
| REJECTED | 已拒绝 | Rejected | 节点被拒绝 |

---

## 三、角色定义（Role Definitions）

| 角色代码 | 中文名称 | 英文名称 | 主要职责 |
|---------|---------|---------|---------|
| SALES | 销售员 | Sales | 创建和维护客户信息、创建报价单、创建销售订单、与客户确认报价单 |
| SALES_MANAGER | 销售经理 | Sales Manager | 审批报价单（一级审核）、审批销售订单（销售部门评审节点） |
| ENGINEER | 工程师 | Engineer | 创建和维护BOM、工艺路线、MI、生产版本、产品主数据，审批报价单（二级审核），审批销售订单（工程部门评审节点） |
| PLANNER | 计划员 | Planner | 创建生产订单/工单、下达生产订单/工单、管理生产计划、LOT卡管理 |
| PRODUCTION | 生产人员 | Production | 创建生产订单/工单、进行工序报工、查看生产进度 |
| WAREHOUSE | 物料管理员 | Warehouse | 管理物料主数据（不包含成品FG）、处理生产领料、审批销售订单（物料部门评审节点） |
| FINANCE | 财务人员 | Finance | 审批销售订单（财务部门评审节点）、处理对账 |
| ACCOUNT_MANAGER | 客户经理 | Account Manager | 审批报价单（三级审核，与GENERAL_MANAGER共同承担） |
| GENERAL_MANAGER | 总经理 | General Manager | 审批报价单（三级审核，与ACCOUNT_MANAGER共同承担） |
| ADMIN | 系统管理员 | Administrator | 用户管理、角色管理、工作流配置、系统配置 |

---

## 四、单位定义（Unit Definitions）

### 4.1 基础单位（Base Unit）

| 单位代码 | 中文名称 | 英文名称 | 说明 |
|---------|---------|---------|------|
| PCS | 个/件 | Pieces | 基础单位，通常用于销售和库存 |
| PNL | 拼板 | Panel | 生产单位，通常用于生产，一个Panel包含多个Unit |
| KG | 千克 | Kilogram | 重量单位，用于原材料 |
| SHT | 张 | Sheet | 面积单位，用于板材 |

### 4.2 单位转换

- **1 PNL = N PCS**：转换系数由物料主数据定义（Material.conversion_factor）
- **销售单位**：通常为PCS，用于客户交付
- **生产单位**：通常为PNL，用于生产执行

---

## 五、工序类型（Operation Type）

| 类型值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| internal | 内部工序 | Internal | 在公司内部完成的工序，需要工作中心 |
| external | 外协工序 | External | 需要外包给外部供应商完成的工序，系统会自动生成采购申请 |
| quality | 质检工序 | Quality | 质量检验工序，系统会触发生成检验单 |

---

## 六、工作中心类型（Work Center Type）

| 类型值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| MACHINE | 单台机器 | Machine | 单台生产设备 |
| MACHINE_GROUP | 机组 | Machine Group | 多台设备组成的机组 |
| LABOR | 人工工位 | Labor | 人工操作工位 |
| PRODUCTION_LINE | 产线 | Production Line | 完整的生产线 |

---

## 七、物料事务类型（Material Transaction Type）

| 类型值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| ISSUE | 出库 | Issue | 物料出库，quantity为负数 |
| RECEIPT | 入库 | Receipt | 物料入库，quantity为正数 |
| ADJUSTMENT | 调整 | Adjustment | 库存调整，quantity可以为正数或负数 |

---

## 八、BOM物料类别（BOM Item Category）

| 类别值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| STOCK_ITEM | 库存物料 | Stock Item | 需要从库存领用的物料 |
| SUB_ASSEMBLY | 半成品 | Sub Assembly | 半成品，需要先生产 |
| CONSUMABLE | 耗材 | Consumable | 消耗性物料，不需要精确跟踪 |

---

## 九、PCB行业特定术语（PCB Industry Terms）

### 9.1 PCB工程属性

| 术语 | 中文名称 | 英文名称 | 说明 |
|------|---------|---------|------|
| 层数 | Layer Count | Layer Count | PCB的层数，如2层、4层、6层等 |
| 板厚 | Board Thickness | Board Thickness | PCB的厚度，单位：mm |
| 铜厚 | Copper Weight | Copper Weight | PCB的铜箔厚度 |
| 材料等级 | Material Grade | Material Grade | PCB基材的等级 |
| 表面处理 | Surface Finish | Surface Finish | PCB表面的处理方式，如OSP、ENIG、HASL等 |
| 阻焊颜色 | Solder Mask Color | Solder Mask Color | PCB阻焊层的颜色 |
| 丝印颜色 | Silkscreen Color | Silkscreen Color | PCB丝印层的颜色 |
| 阻抗控制 | Impedance Control | Impedance Control | 是否有阻抗控制要求 |
| 最小线距 | Minimum Line Space | Minimum Line Space | 最小线间距，单位：mm |
| 最小孔径 | Minimum Hole Size | Minimum Hole Size | 最小孔径，单位：mm |
| 单元尺寸 | Unit Size | Unit Size | 单个PCB单元的尺寸 |
| 拼板尺寸 | Panel Size | Panel Size | 拼板的尺寸 |
| 每拼板单元数 | Units Per Panel | Units Per Panel | 每个拼板包含的单元数量 |

### 9.2 PCB工艺类别

| 类别值 | 中文名称 | 英文名称 | 说明 |
|--------|---------|---------|------|
| DRILLING | 钻孔 | Drilling | 钻孔工序 |
| PLATING | 电镀 | Plating | 电镀工序 |
| ETCHING | 蚀刻 | Etching | 蚀刻工序 |
| LAMINATION | 压合 | Lamination | 压合工序 |
| AOI | 自动光学检测 | Automated Optical Inspection | 自动光学检测工序 |

---

## 十、缩写词（Abbreviations）

| 缩写 | 全称 | 中文名称 | 说明 |
|------|------|---------|------|
| BOM | Bill of Materials | 物料清单 | 定义产品的物料组成结构 |
| MI | Manufacturing Instruction | 制造指令 | 包含详细的工艺参数和操作指导 |
| PCB | Printed Circuit Board | 印刷电路板 | 本系统面向的制造行业 |
| PCS | Pieces | 个/件 | 基础单位 |
| PNL | Panel | 拼板 | 生产单位 |
| ERP | Enterprise Resource Planning | 企业资源计划 | 企业资源计划系统 |
| SD | Sales & Distribution | 销售与分销 | 销售与分销模块 |
| ENG | Engineering | 工程管理 | 工程管理模块 |
| MM | Material Management | 物料管理 | 物料管理模块 |
| PP | Production Planning | 生产计划与控制 | 生产计划与控制模块 |
| AOI | Automated Optical Inspection | 自动光学检测 | 使用光学设备自动检测PCB板的质量和缺陷 |
| OSP | Organic Solderability Preservative | 有机可焊性保护膜 | PCB表面处理方式 |
| ENIG | Electroless Nickel Immersion Gold | 化学镍金 | PCB表面处理方式 |
| HASL | Hot Air Solder Leveling | 热风整平 | PCB表面处理方式 |
| JWT | JSON Web Token | JSON Web令牌 | 用户认证令牌 |
| API | Application Programming Interface | 应用程序编程接口 | 系统接口 |
| REST | Representational State Transfer | 表述性状态转移 | RESTful API架构风格 |
| JSON | JavaScript Object Notation | JavaScript对象表示法 | 数据交换格式 |

---

## 十一、系统模块（System Modules）

| 模块代码 | 中文名称 | 英文名称 | 说明 |
|---------|---------|---------|------|
| SD | 销售与分销 | Sales & Distribution | 客户管理、报价单、销售订单、订单评审 |
| ENG | 工程管理 | Engineering | BOM管理、工艺路线、MI制作、生产版本 |
| MM | 物料管理 | Material Management | 物料主数据、库存管理、生产领料 |
| PP | 生产计划与控制 | Production Planning & Control | 工作中心、生产订单、工序报工 |

---

## 十二、数据关系术语（Data Relationship Terms）

### 12.1 关系类型

| 术语 | 中文名称 | 英文名称 | 说明 |
|------|---------|---------|------|
| 一对多 | One-to-Many | One-to-Many | 一个实体可以关联多个实体 |
| 多对一 | Many-to-One | Many-to-One | 多个实体可以关联一个实体 |
| 多对多 | Many-to-Many | Many-to-Many | 多个实体可以关联多个实体 |
| 外键 | Foreign Key | Foreign Key | 用于关联其他表的字段 |
| 主键 | Primary Key | Primary Key | 唯一标识实体的字段 |

### 12.2 关联关系示例

- **Customer → Quotation**：一对多，一个客户可以有多个报价单
- **Quotation → SalesOrder**：多对一，一个报价单可以关联一个销售订单
- **SalesOrder → ProductionOrder**：一对多，一个销售订单可以有多个生产订单/工单
- **Material（产品主数据） → BOM**：一对多，一个产品主数据可以有多个BOM（不同版本）
- **BOM → BOMItem**：一对多，一个BOM可以有多个BOM明细
- **Material（产品主数据） → Routing**：一对多，一个产品主数据可以有多个工艺路线（不同版本）
- **Routing → RoutingOperation**：一对多，一个工艺路线可以有多个工序
- **ProductionVersion → BOM + Routing + MI**：多对一，一个生产版本关联一个BOM、一个工艺路线和一个MI（可选）
- **ProductionOrder → LotCard**：一对一（1:1），一个生产订单/工单对应一个LOT卡
- **LotCard → MI**：多对一，一个LOT卡关联一个MI

---

## 十三、业务流程术语（Business Process Terms）

### 13.1 核心业务流程

| 术语 | 中文名称 | 说明 |
|------|---------|------|
| 客户建档 | Customer Creation | 创建客户并审批，使客户状态变为ACTIVE |
| 报价流程 | Quotation Process | 创建报价单 → 三级审核（串行：一级审核SALES_MANAGER → 二级审核ENGINEER → 三级审核ACCOUNT_MANAGER或GENERAL_MANAGER） → 销售员经客户确认 → 转销售订单 |
| 销售订单流程 | Sales Order Process | 创建销售订单 → 多部门评审 → 创建生产订单/工单 |
| 生产执行流程 | Production Execution Process | 创建生产订单/工单 → 下达 → LOT卡生成 → 工序报工 → 完成 |
| 发货对账流程 | Shipping & Reconciliation Process | 发货 → 签收 → 对账 → 关闭 |

### 13.2 审批流程

| 术语 | 中文名称 | 说明 |
|------|---------|------|
| 报价单审批流程 | Quotation Approval Process | 三级审核流程（串行）：DRAFT → 待一级审核（SALES_MANAGER） → 待二级审核（ENGINEER） → 待三级审核（ACCOUNT_MANAGER或GENERAL_MANAGER） → APPROVED → 销售员经客户确认 → 可转订单。任何一级审核不通过时，报价单状态退回草稿（DRAFT），退回操作记录审核历史，保存退回原因 |
| 销售订单评审流程 | Sales Order Review Process | 销售部门 → 工程部门 → 物料部门 → 财务部门顺序评审 |

---

## 十四、技术术语（Technical Terms）

### 14.1 系统架构

| 术语 | 中文名称 | 说明 |
|------|---------|------|
| 前端 | Frontend | React + TypeScript + Ant Design |
| 后端 | Backend | FastAPI + Python |
| 数据库 | Database | PostgreSQL |
| ORM | 对象关系映射 | SQLAlchemy |
| API | 应用程序编程接口 | RESTful API |

### 14.2 数据格式

| 术语 | 中文名称 | 说明 |
|------|---------|------|
| JSON | JavaScript对象表示法 | 用于数据交换和存储复杂数据结构 |
| JWT | JSON Web令牌 | 用于用户认证和授权 |
| ISO 8601 | ISO 8601日期时间格式 | 用于日期时间格式化 |

---

## 十五、总结

### 15.1 术语分类统计

- **业务术语**：50+ 个
- **状态枚举**：14 个枚举类型，100+ 个状态值
- **角色定义**：9 个角色
- **单位定义**：4 个基础单位
- **工序类型**：3 种类型
- **工作中心类型**：4 种类型
- **物料事务类型**：3 种类型
- **BOM物料类别**：3 种类别
- **PCB行业特定术语**：15+ 个
- **缩写词**：20+ 个

### 15.2 使用建议

1. **开发人员**：在编写代码时，应使用本文档中定义的术语，保持一致性
2. **业务人员**：在讨论需求时，应使用本文档中的业务术语，避免歧义
3. **新员工**：应首先阅读本文档，了解系统的基本术语和概念
4. **文档维护**：当系统新增术语时，应及时更新本文档

---

**文档版本：** v1.4  
**最后更新：** 2025-01-XX  
**维护者：** 开发团队

