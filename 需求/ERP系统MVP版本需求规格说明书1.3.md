# 某某ERP系统MVP版本需求规格说明书

## 一、项目概述

### 1.1 项目背景

某某是一家专业的PCB（印制电路板）制造企业，随着业务规模的不断扩大和市场竞争的加剧，传统的管理方式已无法满足企业快速发展的需求。为了提高企业管理效率、优化业务流程、降低运营成本，某某决定建设一套符合PCB行业特点的ERP（企业资源计划）系统。

当前企业面临的主要挑战包括：

- **业务流程分散**：销售、工程、生产、物料等各业务环节缺乏统一的信息化管理平台，数据流转依赖人工传递，效率低下
- **数据管理混乱**：客户信息、产品数据、订单信息等关键业务数据分散在多个系统中，缺乏统一的数据标准和规范
- **生产管理粗放**：生产计划、物料需求、工序报工等环节缺乏精细化管理，难以准确掌握生产进度和成本
- **决策支持不足**：缺乏实时的业务数据分析和报表，管理层难以快速获取决策所需的信息

为了应对这些挑战，某某启动了ERP系统MVP（最小可行产品）版本的建设，旨在构建一个覆盖核心业务流程的信息化管理平台。

### 1.2 项目目标

本项目旨在建设一套符合PCB行业特点的ERP系统MVP版本，实现以下目标：

#### 1.2.1 业务目标

- **提升业务效率**：通过系统化的业务流程管理，减少人工操作，提高业务处理效率。支持返单快速下单，自动识别返单并匹配历史订单信息，跳过报价环节
- **优化订单管理**：建立从客户建档、客户询价、报价、三级审核、客户确认、订单评审到生产执行的完整订单管理流程
- **加强生产管控**：实现生产订单/工单、LOT卡管理、工序报工等生产环节的精细化管理。支持LOT卡自动生成（1:1关系），工序报工时自动关联LOT卡
- **规范数据管理**：建立统一的主数据管理体系，确保数据的准确性和一致性。支持产品主数据自动创建（SD模块调用ENG模块API），产品主数据由工程管理模块统一管理
- **流程自动化**：实现报价单三级审核（串行）、订单多部门评审（串行）、生产订单状态同步销售订单状态等自动化流程

#### 1.2.2 技术目标

- **系统集成**：实现销售、工程、生产、物料等各业务模块的有机集成
- **数据标准化**：建立统一的数据标准和编码规范，为后续系统扩展奠定基础
- **流程自动化**：通过工作流引擎实现业务流程的自动化流转和状态管理
- **可扩展性**：采用模块化设计，支持后续功能扩展和系统升级

#### 1.2.3 管理目标

- **提高决策效率**：通过实时数据分析和报表，为管理层提供决策支持
- **降低运营成本**：通过优化业务流程和减少人工操作，降低企业运营成本
- **提升客户满意度**：通过快速响应客户需求和准确交付，提升客户满意度

### 1.3 项目范围

#### 1.3.1 功能范围

本MVP版本涵盖以下核心业务模块：

- **SD模块（销售与分销）**：客户管理、报价单管理、销售订单管理、订单评审等
- **ENG模块（工程管理）**：产品主数据管理、BOM管理、工艺路线管理、MI管理、生产版本管理等
- **PP模块（生产计划与控制）**：工作中心管理、生产订单/工单管理、LOT卡管理、工序报工等
- **MM模块（物料管理）**：物料主数据管理、生产领料、库存管理等

#### 1.3.2 业务流程范围

本MVP版本支持以下核心业务流程：

- **客户建档流程**：销售员创建客户主数据，销售经理审批，激活客户
- **销售报价流程**：从客户询价到报价单创建、三级审核（串行：销售经理→工程师→客户经理/总经理）、销售员经客户确认报价单的完整流程。报价单创建时，如果本厂编号不存在，SD模块自动调用ENG模块API创建产品主数据
- **报价转订单流程**：将已通过审核并获客户确认的报价单转为销售订单
- **返单快速下单流程**：老客户重复下单，系统自动识别返单并匹配历史订单信息，快速创建销售订单，跳过报价环节
- **新单下单流程**：新客户或新产品下单，完整录入订单信息，经过订单审核等环节，创建销售订单
- **订单评审流程**：销售订单的多部门评审流程（串行：销售部门→工程部门→物料部门→财务部门），所有部门评审通过后订单状态更新为已批准
- **生产订单创建流程**：基于已批准的销售订单创建生产订单/工单。如果生产版本关联了MI，系统检查MI是否存在且状态为RELEASED，如果关联了MI则自动生成LOT卡（1:1关系），复制MI内容到LOT卡，并将lot_number写回生产订单
- **生产领料流程**：根据生产订单/工单关联的BOM自动生成领料需求，创建领料单，物控岗发放物料，生产线领料，自动更新库存
- **开始生产流程**：将生产订单/工单状态从RELEASED更新为IN_PRODUCTION，记录实际开始时间，同步销售订单状态
- **工序报工流程**：各工序完成后进行报工，系统根据生产订单/工单自动查询关联的LOT卡（1:1关系），自动填充报工单中的LOT卡号字段（只读、不可修改），记录完成数量、良品数量、不良品数量、工时等，更新生产进度
- **生产订单关闭流程**：当所有工序完成后，关闭生产订单（状态：CLOSED），记录实际完成时间。当所有生产订单/工单状态为COMPLETED或CLOSED时，更新销售订单状态为COMPLETED

#### 1.3.3 技术范围

- **系统架构**：采用前后端分离的架构
- **数据库**：使用PostgreSQL作为主数据库
- **接口规范**：采用RESTful API设计规范
- **权限管理**：基于角色的访问控制（RBAC）

#### 1.3.4 非功能范围

本MVP版本暂不包含以下内容（将在后续版本中实现）：

- 财务模块（应收应付、成本核算等）
- 采购模块（采购订单、供应商管理等）
- 质量管理模块（质检流程、不良品分析等）
- 设备管理模块（设备维护、设备台账等）
- 人力资源模块（员工管理、考勤管理等）
- 高级报表和数据分析功能
- 移动端应用

### 1.4 系统概述

#### 1.4.1 系统定位

某某ERP系统MVP版本是一个面向PCB制造企业的核心业务管理系统，专注于销售、工程、生产、物料等核心业务流程的信息化管理。

#### 1.4.2 系统特点

- **行业特色**：针对PCB制造行业的特点，支持本厂编号管理（14位编码，同时作为产品编码）、PCB专有属性管理（层数、板厚、铜厚、表面处理等）、MI管理、LOT卡管理等行业特色功能
- **流程驱动**：以业务流程为核心，通过工作流引擎实现业务流程的自动化管理。支持串行审核流程（报价单三级审核、订单多部门评审）、状态自动同步（生产订单状态同步销售订单状态）
- **数据统一**：建立统一的主数据管理体系，确保数据的准确性和一致性。产品主数据由工程管理模块统一管理，SD模块可以引用和自动创建，但不能修改和删除
- **自动化处理**：支持产品主数据自动创建（SD模块调用ENG模块API）、LOT卡自动生成（生产订单与LOT卡1:1关系）、领料需求自动生成（基于BOM）、库存自动更新等自动化处理
- **灵活扩展**：采用模块化设计，支持后续功能扩展和系统升级

#### 1.4.3 系统架构

系统采用前后端分离的架构设计：

- **前端**：提供友好的用户交互界面
- **后端**：基于FastAPI框架的RESTful API服务，提供业务逻辑处理和数据访问
- **数据库**：PostgreSQL关系型数据库，存储业务数据
- **工作流引擎**：支持业务流程的自动化流转和状态管理

#### 1.4.4 用户角色

系统支持以下用户角色（系统角色枚举），各角色按模块划分职责：

**SD模块（销售与分销）角色：**
- **销售员（SALES）**：负责客户建档、客户信息维护、报价单创建、报价单预估报价、销售订单创建、返单快速下单等
- **销售经理（SALES_MANAGER）**：负责报价单一级审核、销售订单评审（销售部门评审）等
- **工程师（ENGINEER）**：参与报价单二级审核，负责确认价格策略和交期承诺
- **总经理（GENERAL_MANAGER）**：负责报价单三级审核（与客户经理二选一）、销售订单评审等

**ENG模块（工程管理）角色：**
- **工程师（ENGINEER）**：负责产品主数据管理、BOM创建和管理、工艺路线创建和管理、MI创建和管理、生产版本建立等。工程师也负责MI审核，确认技术参数和生产要求

**PP模块（生产计划与控制）角色：**
- **计划员（PLANNER）**：负责工作中心管理、生产订单/工单管理、LOT卡查询和管理、生产进度查看、生产订单关闭等
- **生产人员（PRODUCTION）**：负责工序报工、不良品记录、LOT卡查询和查看等

**MM模块（物料管理）角色：**
- **计划员（PLANNER）**：负责物料主数据管理、物料列表查询、库存查询、生产领料单创建、缺料单生成等（物控岗）
- **仓库管理员（WAREHOUSE）**：负责生产领料处理、领料单审核、库存查询等

**跨模块角色：**
- **财务人员（FINANCE）**：负责销售订单评审（财务部门评审）等
- **系统管理员（ADMIN）**：负责系统配置、用户管理、角色权限管理等，拥有所有模块的操作权限

**说明：**
- 系统角色枚举包括：SALES、SALES_MANAGER、ENGINEER、PLANNER、PRODUCTION、WAREHOUSE、FINANCE、GENERAL_MANAGER、ADMIN
- 业务角色（如客户经理、审核员、产线工人、生产主管、物控员等）通过分配相应的系统角色来实现权限控制
- 系统管理员（ADMIN）角色拥有所有模块的操作权限，可以绕过所有角色限制

### 1.5 文档说明

#### 1.5.1 文档目的

本文档旨在详细描述某某ERP系统MVP版本的功能需求、业务流程、数据模型等，为系统设计、开发、测试和实施提供依据。

#### 1.5.2 文档结构

本文档包含以下主要内容：

- **第一章 项目概述**：介绍项目背景、目标、范围和系统概述
- **第二章 实体**：定义系统的核心业务实体及其关系
- **第三章 用例**：描述各业务模块的功能用例
- **第四章 流程说明**：详细说明各业务流程的处理逻辑

#### 1.5.3 文档版本

- **版本号**：v1.3
- **创建日期**：2025-01-XX
- **最后更新**：2025-01-XX

#### 1.5.4 术语定义

- **本厂编号**：某某内部为每个产品分配的唯一标识，14位编码，同时作为产品编码（material_code）。产品主数据以本厂编号作为唯一标识
- **LOT卡**：生产批次卡，由MI自动生成，关联生产订单/工单，是工序报工的批次依据。一个生产订单/工单对应一个LOT卡（1:1关系）。在生产订单/工单创建时，如果关联了MI，系统自动生成LOT卡，自动复制MI内容到LOT卡，并将lot_number写回生产订单
- **MI**：制造指令（Manufacturing Instruction），包含客户型号、技术参数、生产要求等，是生产执行的依据。MI由工程管理模块创建和管理，发布后的MI可用于生产版本发布和生产订单/工单下达
- **BOM**：物料清单（Bill of Materials），定义产品的物料组成结构，包含父项产品、子项物料、用量等。只有RELEASED状态的BOM才能用于生产版本
- **工艺路线**：定义产品的生产工艺流程，包含工序序列、工作中心、标准时间等。只有RELEASED状态的工艺路线才能用于生产版本
- **生产版本**：将BOM和工艺路线组合，形成可执行的生产版本。发布生产版本时需要MI已关联且状态为RELEASED
- **生产订单/工单**：生产订单/工单，包含生产数量、交期、关联的MI、BOM、工艺路线、工序任务、工作中心、计划时间等。当前实现中由实体 ProductionOrder 同时承担"生产订单+工单"职责，工单状态与生产订单状态一致
- **工序报工**：记录各工序的完成情况，包含完成数量、良品数量、不良品数量、工时等，关联LOT卡号。系统根据生产订单/工单自动查询关联的LOT卡（1:1关系），自动填充报工单中的LOT卡号字段（只读、不可修改）

---

## 二、实体

### 实体列表

实体名称|说明
-|-
客户|客户主数据，包含客户基本信息、合作属性、地址信息、联系人信息、销售数据等
报价单|销售报价单，包含客户信息、产品信息、价格条款、交付条款等，支持三级审核流程
销售订单|销售订单，由报价单转换或返单创建，包含订单信息、产品明细、交期承诺等
产品主数据|产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）。产品主数据包含物料主数据中成品(FG)的所有内容，包括产品基本信息、PCB专有工程属性（层数、板厚、铜厚、表面处理等）、技术参数、尺寸信息、供应链计划参数等。产品主数据管理只显示成品(FG类型)的物料
物料|物料主数据，包含物料编码、名称、分类（原材料、辅材、化工材料、半成品、维修等）、规格型号、库存信息等。物料主数据管理中不显示成品(FG类型)，成品通过产品主数据管理进行维护
BOM|物料清单，定义产品的物料组成结构，包含父项产品、子项物料、用量等
工艺路线|定义产品的生产工艺流程，包含工序序列、工作中心、标准时间等
生产版本|将BOM和工艺路线组合，形成可执行的生产版本
MI|制造指令，包含客户型号、技术参数、生产要求等，是生产执行的依据
工作中心|生产资源主数据，包含工作中心代码、类型、产能数据、成本数据等
生产订单|生产执行订单/工单，包含生产数量、交期、关联的MI、BOM、工艺路线、工序任务、工作中心、计划时间等；当前实现中由实体 ProductionOrder 同时承担“生产订单+工单”职责
LOT卡|生产批次卡，由MI自动生成，关联生产订单/工单，包含MI内容、数量、单位、状态等信息，是工序报工的批次依据
领料单|生产领料单，包含领料明细、库存信息、发放记录等
报工单|工序报工记录，包含完成数量、良品数量、不良品数量、工时等，关联LOT卡号

### ER图

```plantuml
@startuml 某某ERP系统ER图

title 某某ERP系统MVP版本ER图

entity "客户" as customer {
  * customerId : VARCHAR
  --
  * legalName : VARCHAR
  tradeName : VARCHAR
  taxId : VARCHAR
  customerStatus : VARCHAR
  customerIndustry : VARCHAR
}

entity "产品主数据" as product {
  * internalCode : VARCHAR
  --
  * productName : VARCHAR
  customerModel : VARCHAR
  pcbAttributes : JSON
  layerCount : INTEGER
  boardThickness : DECIMAL
  copperWeight : VARCHAR
  surfaceFinish : VARCHAR
  productStatus : VARCHAR
}

entity "报价单" as quotation {
  * quotationId : VARCHAR
  --
  * customerId : VARCHAR
  * internalCode : VARCHAR
  productName : VARCHAR
  quantity : DECIMAL
  unitPrice : DECIMAL
  quotationStatus : VARCHAR
  approvalLevel : INTEGER
}

entity "销售订单" as salesOrder {
  * orderId : VARCHAR
  --
  * customerId : VARCHAR
  quotationId : VARCHAR
  orderType : VARCHAR
  orderDate : DATE
  deliveryDate : DATE
  orderStatus : VARCHAR
}

entity "物料" as material {
  * materialId : VARCHAR
  --
  * materialName : VARCHAR
  materialCategory : VARCHAR
  materialType : VARCHAR
  unit : VARCHAR
  specification : VARCHAR
  currentStock : DECIMAL
  safetyStock : DECIMAL
}

entity "BOM" as bom {
  * bomId : VARCHAR
  --
  * internalCode : VARCHAR
  version : VARCHAR
  effectiveDate : DATE
  expiryDate : DATE
  bomStatus : VARCHAR
}

entity "BOM明细" as bomItem {
  * bomId : VARCHAR
  * materialId : VARCHAR
  --
  usage : DECIMAL
  unit : VARCHAR
  sequence : INTEGER
}

entity "工艺路线" as routing {
  * routingId : VARCHAR
  --
  * internalCode : VARCHAR
  version : VARCHAR
  effectiveDate : DATE
  expiryDate : DATE
}

entity "工艺路线明细" as routingItem {
  * routingId : VARCHAR
  * sequence : INTEGER
  --
  operationName : VARCHAR
  workCenterId : VARCHAR
  standardTime : DECIMAL
}

entity "生产版本" as productionVersion {
  * versionId : VARCHAR
  --
  * internalCode : VARCHAR
  bomId : VARCHAR
  routingId : VARCHAR
  version : VARCHAR
  effectiveDate : DATE
}

entity "MI" as mi {
  * miId : VARCHAR
  --
  * customerId : VARCHAR
  clientCode : VARCHAR
  clientModel : VARCHAR
  productionType : VARCHAR
  layers : INTEGER
  boardThickness : DECIMAL
  miStatus : VARCHAR
}

entity "工作中心" as workCenter {
  * workCenterId : VARCHAR
  --
  * description : VARCHAR
  workCenterType : VARCHAR
  plantId : VARCHAR
  status : VARCHAR
  capacityCategory : VARCHAR
}

entity "生产订单" as productionOrder {
  * productionOrderId : VARCHAR
  --
  * salesOrderId : VARCHAR
  * miId : VARCHAR
  * productionVersionId : VARCHAR
  quantity : DECIMAL
  orderDate : DATE
  deliveryDate : DATE
  orderStatus : VARCHAR
  lotNumber : VARCHAR
}

entity "工单" as workOrder {
  * workOrderId : VARCHAR
  --
  * productionOrderId : VARCHAR
  * operationSequence : INTEGER
  * workCenterId : VARCHAR
  plannedQuantity : DECIMAL
  plannedStartTime : DATETIME
  plannedEndTime : DATETIME
  workOrderStatus : VARCHAR
}

entity "领料单" as pickingList {
  * pickingListId : VARCHAR
  --
  * productionOrderId : VARCHAR
  pickingDate : DATE
  pickingStatus : VARCHAR
}

entity "领料明细" as pickingItem {
  * pickingListId : VARCHAR
  * materialId : VARCHAR
  --
  requiredQuantity : DECIMAL
  actualIssued : DECIMAL
  unit : VARCHAR
}

entity "LOT卡" as lotCard {
  * lotNumber : VARCHAR
  --
  * productionOrderNumber : VARCHAR
  * miNumber : VARCHAR
  * materialCode : VARCHAR
  quantity : DECIMAL
  unit : VARCHAR
  status : VARCHAR
  miContent : TEXT
  completedAt : DATETIME
  remarks : TEXT
}

entity "报工单" as processReport {
  * reportId : VARCHAR
  --
  * workOrderId : VARCHAR
  * productionOrderNumber : VARCHAR
  lotNumber : VARCHAR
  completedQuantity : DECIMAL
  goodQuantity : DECIMAL
  defectiveQuantity : DECIMAL
  actualHours : DECIMAL
  reportDate : DATETIME
}

' 关系
customer ||--o{ quotation : "创建"
product ||--o{ quotation : "报价"
quotation ||--o| salesOrder : "转为"
customer ||--o{ salesOrder : "下单"
product ||--o{ salesOrder : "订购"
salesOrder ||--o{ productionOrder : "生成"

product ||--o{ bom : "作为父项"
bom ||--o{ bomItem : "包含"
material ||--o{ bomItem : "作为子项"

product ||--o{ routing : "定义工艺"
routing ||--o{ routingItem : "包含工序"
workCenter ||--o{ routingItem : "使用"

product ||--o{ productionVersion : "关联"
bom ||--o{ productionVersion : "关联"
routing ||--o{ productionVersion : "关联"

customer ||--o{ mi : "创建"
mi ||--o{ productionOrder : "依据"
mi ||--o{ lotCard : "生成"
productionVersion ||--o{ productionOrder : "使用"
product ||--o{ productionOrder : "生产"

productionOrder ||--o| lotCard : "关联"
productionOrder ||--o{ workOrder : "生成"
workCenter ||--o{ workOrder : "执行"

productionOrder ||--o{ pickingList : "领料"
pickingList ||--o{ pickingItem : "包含"
material ||--o{ pickingItem : "领取"

workOrder ||--o{ processReport : "报工"
lotCard ||--o{ processReport : "关联"
productionOrder ||--o{ processReport : "关联"

@enduml
```

## 三、用例

### SD模块（销售与分销）

#### 用例列表

用例|功能说明
-|-
客户建档|创建新客户主数据，包含客户基本信息、合作属性、地址信息、联系人信息、销售数据等
客户信息修改|修改已存在的客户主数据信息
维护送货地址|为客户添加或修改送货地址信息
产品主数据管理|创建和维护产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码。产品主数据包含物料主数据中成品(FG)的所有内容，包括产品基本信息、PCB专有工程属性、技术参数、尺寸信息、供应链计划参数等。新建产品主数据时，如果本厂编号对应的产品不存在，系统提供创建产品的快捷入口。产品主数据管理只显示成品(FG类型)的物料
报价单创建|创建销售报价单，包含客户信息、产品信息（本厂编号、产品名称）、价格条款等。创建报价单时，如果输入的14位本厂编号不存在对应的产品主数据，系统自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品）
报价单预估报价|根据板规格参数、工艺参数、加价选项等自动计算报价明细成本，包括交货面积、成本/平米、成本PCS、报价价格、工程费、板材费、测试架费用等，并生成工序成本明细。支持实时计算和手动计算两种模式
报价单审核|三级审核流程：一级审核、二级审核、三级审核
报价转订单|将已通过审核并获客户确认的报价单转为销售订单
返单快速下单|老客户重复下单，系统自动识别并匹配历史订单信息，快速创建销售订单
销售订单管理|查看、编辑、审核销售订单
订单评审|对销售订单进行评审，确认价格、交期等条款

#### 用例图

```plantuml
@startuml SD模块用例图

title SD模块（销售与分销）用例图

left to right direction

actor 销售员 as sales
actor 销售经理 as salesManager
actor 客户经理 as accountManager
actor 系统 as system

rectangle SD模块 {
  
  package "客户管理" {
    usecase "客户建档" as UC1
    usecase "客户信息修改" as UC2
    usecase "维护送货地址" as UC3
    usecase "查看客户档案" as UC4
  }
  
  package "产品管理" {
    usecase "产品主数据管理" as UC4A
    usecase "产品列表查询" as UC4B
  }
  
  package "报价管理" {
    usecase "报价单创建" as UC5
    usecase "报价单预估报价" as UC5A
    usecase "报价单审核" as UC6
    usecase "报价单列表" as UC7
    usecase "报价单详情" as UC8
  }
  
  package "订单管理" {
    usecase "报价转订单" as UC9
    usecase "返单快速下单" as UC10
    usecase "销售订单管理" as UC11
    usecase "订单评审" as UC12
  }
  
  package "订单审核" {
    usecase "一级审核" as UC13
    usecase "二级审核" as UC14
    usecase "三级审核" as UC15
  }
}

' 销售员用例
sales --> UC1 : 创建新客户
sales --> UC2 : 修改客户信息
sales --> UC3 : 维护地址
sales --> UC4 : 查看客户档案
sales --> UC4A : 管理产品
sales --> UC4B : 查询产品
sales --> UC5 : 创建报价单
sales --> UC5A : 预估报价
sales --> UC7 : 查看报价列表
sales --> UC8 : 查看报价详情
sales --> UC9 : 转订单
sales --> UC10 : 返单下单
sales --> UC11 : 管理订单

' 销售经理用例
salesManager --> UC6 : 审核报价
salesManager --> UC12 : 评审订单
salesManager --> UC13 : 一级审核
salesManager --> UC14 : 二级审核

' 客户经理用例
accountManager --> UC15 : 三级审核
accountManager --> UC12 : 评审订单

' 系统用例
system --> UC10 : 自动识别返单
system --> UC10 : 匹配历史订单

' 用例关系
UC5 ..> UC5A : <<include>>
UC5 ..> UC6 : <<include>>
UC6 ..> UC13 : <<include>>
UC6 ..> UC14 : <<include>>
UC6 ..> UC15 : <<include>>
UC9 ..> UC12 : <<include>>
UC10 ..> UC11 : <<include>>
UC7 ..> UC8 : <<include>>

note right of UC1
  创建客户主数据
  包含基本信息、合作属性、
  地址、联系人、销售数据
end note

note right of UC4A
  管理产品主数据
  以本厂编号为唯一标识
  本厂编号同时作为产品编码
  包含物料主数据中成品(FG)的所有内容
  只显示成品(FG类型)的物料
end note

note right of UC5
  创建报价单
  包含客户、产品（本厂编号、产品名称）、
  价格、交付条款等信息
  自动创建产品主数据（如需要）
end note

note right of UC5A
  报价单预估报价
  根据板规格参数、工艺参数、加价选项
  自动计算报价明细成本
  包括交货面积、成本/平米、报价价格、
  工程费、板材费、工序成本明细等
  支持实时计算和手动计算
end note

note right of UC6
  三级审核流程
  确保报价准确性
end note

note right of UC10
  自动识别返单
  匹配历史订单
  快速创建订单
end note

@enduml
```

### ENG模块（工程管理）

#### 用例列表

用例|功能说明
-|-
产品主数据管理|创建和维护产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码。产品主数据包含物料主数据中成品(FG)的所有内容。产品主数据管理只显示成品(FG类型)的物料。新建产品主数据时，如果本厂编号对应的产品不存在，系统提供创建产品的快捷入口
BOM创建|创建物料清单，定义产品的物料组成结构（父项为产品主数据，产品编码为本厂编号）
BOM版本管理|创建BOM新版本，管理BOM版本历史
BOM物料管理|在BOM中添加、编辑、删除物料
工艺路线创建|创建工艺路线，定义产品的生产工艺流程
工艺路线版本管理|创建工艺路线新版本，管理版本历史
工艺路线工序管理|在工艺路线中添加、编辑、删除工序
生产版本建立|将BOM和工艺路线组合，建立生产版本
MI创建|创建制造指令，包含客户型号、技术参数等
MI审核|对MI进行审核，确认技术参数和生产要求
MI修改|根据审核意见修改MI

#### 用例图

```plantuml
@startuml ENG模块用例图

title ENG模块（工程管理）用例图

left to right direction

actor 工程师 as engineer
actor 审核员 as reviewer
actor 系统 as system

rectangle ENG模块 {
  
  package "产品管理" {
    usecase "产品主数据管理" as UC0
  }
  
  package "BOM管理" {
    usecase "BOM创建" as UC1
    usecase "BOM版本管理" as UC2
    usecase "BOM物料管理" as UC3
    usecase "BOM列表" as UC4
    usecase "BOM详情" as UC5
  }
  
  package "工艺路线管理" {
    usecase "工艺路线创建" as UC6
    usecase "工艺路线版本管理" as UC7
    usecase "工艺路线工序管理" as UC8
    usecase "工艺路线列表" as UC9
  }
  
  package "生产版本管理" {
    usecase "生产版本建立" as UC10
    usecase "生产版本列表" as UC11
  }
  
  package "MI管理" {
    usecase "MI创建" as UC12
    usecase "MI审核" as UC13
    usecase "MI修改" as UC14
    usecase "MI列表" as UC15
    usecase "MI详情" as UC16
  }
}

' 工程师用例
engineer --> UC0 : 管理产品
engineer --> UC1 : 创建BOM
engineer --> UC2 : 管理版本
engineer --> UC3 : 管理物料
engineer --> UC4 : 查看列表
engineer --> UC5 : 查看详情
engineer --> UC6 : 创建工艺路线
engineer --> UC7 : 管理版本
engineer --> UC8 : 管理工序
engineer --> UC9 : 查看列表
engineer --> UC10 : 建立生产版本
engineer --> UC11 : 查看列表
engineer --> UC12 : 创建MI
engineer --> UC14 : 修改MI
engineer --> UC15 : 查看列表
engineer --> UC16 : 查看详情

' 审核员用例
reviewer --> UC13 : 审核MI
reviewer --> UC15 : 查看列表
reviewer --> UC16 : 查看详情

' 系统用例
system --> UC10 : 组合BOM和工艺路线

' 用例关系
UC1 ..> UC3 : <<include>>
UC6 ..> UC8 : <<include>>
UC10 ..> UC1 : <<include>>
UC10 ..> UC6 : <<include>>
UC12 ..> UC13 : <<include>>
UC13 ..> UC14 : <<extend>>
UC4 ..> UC5 : <<include>>
UC15 ..> UC16 : <<include>>

note right of UC0
  管理产品主数据
  以本厂编号为唯一标识
  本厂编号同时作为产品编码
  包含物料主数据中成品(FG)的所有内容
  只显示成品(FG类型)的物料
  支持自动创建产品（如需要）
end note

note right of UC1
  创建物料清单
  定义产品物料组成
  父项为产品主数据（产品编码为本厂编号）
end note

note right of UC6
  创建工艺路线
  定义生产工艺流程
end note

note right of UC10
  组合BOM和工艺路线
  建立可执行的生产版本
end note

note right of UC12
  创建制造指令
  包含技术参数和生产要求
end note

@enduml
```

### PP模块（生产计划与控制）

#### 用例列表

用例|功能说明
-|-
工作中心管理|创建和维护工作中心主数据，包含基本信息、产能数据、成本数据等
工作中心激活|激活工作中心，使其可用于生产
工作中心停用|停用工作中心
工序报工|记录工序完成情况，包含完成数量、良品数量、不良品数量、工时等
LOT卡管理|LOT卡的全生命周期管理，包括自动生成、查询、详情查看、编辑、状态管理等
LOT卡生成|创建生产订单/工单时，系统根据MI自动生成LOT卡，自动复制MI内容并写回lot_number到生产订单
LOT卡查询|查询LOT卡信息，支持按生产订单号、MI编号、状态等条件查询
LOT卡列表|查看LOT卡列表，支持按生产订单号、MI编号、状态等条件筛选和分页
LOT卡详情查看|查看LOT卡的详细信息，包括MI内容、生产信息、关联的报工记录等
LOT卡编辑|编辑LOT卡的MI内容（mi_content）和备注（remarks），支持JSON格式解析为列表，每一条指令/属性项可单独编辑
不良品管理|记录不良品信息，包含不良原因、处理方式等
生产订单关闭|关闭已完成的生产订单
生产进度查看|查看生产订单的执行进度

#### 用例图

```plantuml
@startuml PP模块用例图

title PP模块（生产计划与控制）用例图

left to right direction

actor 计划员 as planner
actor 产线工人 as worker
actor 生产主管 as supervisor
actor 系统 as system

rectangle PP模块 {
  
  package "工作中心管理" {
    usecase "工作中心管理" as UC1
    usecase "工作中心激活" as UC2
    usecase "工作中心停用" as UC3
    usecase "工作中心列表" as UC4
  }
  
  package "LOT卡管理" {
    usecase "LOT卡生成" as UC4A
    usecase "LOT卡查询" as UC4B
    usecase "LOT卡详情查看" as UC4C
    usecase "LOT卡列表" as UC4D
    usecase "LOT卡编辑" as UC4E
  }
  
  package "生产执行" {
    usecase "工序报工" as UC5
    usecase "不良品管理" as UC6
    usecase "生产进度查看" as UC7
  }
  
  package "生产订单管理" {
    usecase "生产订单关闭" as UC8
    usecase "生产订单列表" as UC9
  }
}

' 计划员用例
planner --> UC1 : 管理工作中心
planner --> UC2 : 激活工作中心
planner --> UC3 : 停用工作中心
planner --> UC4 : 查看列表

planner --> UC4B : 查询LOT卡
planner --> UC4C : 查看LOT卡详情
planner --> UC4D : 查看LOT卡列表
planner --> UC4E : 编辑LOT卡

planner --> UC7 : 查看进度
planner --> UC8 : 关闭订单
planner --> UC9 : 查看订单列表

' 产线工人用例
worker --> UC5 : 工序报工
worker --> UC6 : 记录不良品

worker --> UC4B : 查询LOT卡
worker --> UC4C : 查看LOT卡详情

' 生产主管用例
supervisor --> UC4B : 查询LOT卡
supervisor --> UC4C : 查看LOT卡详情
supervisor --> UC4D : 查看LOT卡列表
supervisor --> UC4E : 编辑LOT卡

supervisor --> UC7 : 查看进度
supervisor --> UC8 : 关闭订单
supervisor --> UC9 : 查看订单列表

' 系统用例
system --> UC4A : 自动生成LOT卡
system --> UC5 : 自动读取LOT卡号
system --> UC5 : 自动计算工时差异
system --> UC6 : 自动计算不良品数量

' 用例关系
UC5 ..> UC6 : <<include>>
UC5 ..> UC4B : <<include>>
UC4D ..> UC4C : <<include>>
UC4B ..> UC4C : <<include>>
UC4E ..> UC4C : <<extend>>
UC7 ..> UC9 : <<include>>
UC1 ..> UC2 : <<extend>>
UC1 ..> UC3 : <<extend>>

note right of UC1
  管理工作中心主数据
  包含基本信息、产能、
  成本等数据
end note

note right of UC4A
  系统在创建生产订单/工单时
  根据MI自动生成LOT卡
  复制MI内容并写回lot_number
end note

note right of UC4E
  编辑LOT卡内容
  支持编辑MI内容和备注
  JSON格式解析为列表
  每个项可单独编辑
end note

note right of UC5
  记录工序完成情况
  包含数量、工时等信息
  自动读取LOT卡号且不可修改
end note

note right of UC6
  记录不良品信息
  包含原因和处理方式
end note

note right of UC7
  查看生产进度
  基于ProductionProgress数据
end note

@enduml
```

### MM模块（物料管理）

#### 用例列表

用例|功能说明
-|-
产品主数据管理|创建和维护产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码。产品主数据包含物料主数据中成品(FG)的所有内容。产品主数据管理只显示成品(FG类型)的物料。新建产品主数据时，如果本厂编号对应的产品不存在，系统提供创建产品的快捷入口，创建的产品自动设置为成品类型且不可修改
物料主数据管理|创建和维护物料主数据，包含物料编码、名称、分类（原材料、辅材、化工材料、半成品、维修等）、规格、库存信息等。物料主数据管理中不显示成品(FG类型)，成品通过产品主数据管理进行维护。新建物料页面标题为"新建产品"，当从产品主数据页面跳转创建产品时，物料类型和物料分类自动设为成品且不可修改。编辑产品时，产品类型和物料分类不能修改
物料列表查询|查询物料列表，支持条件过滤
生产领料|根据生产订单创建领料单，包含领料明细、库存信息等
库存查询|查询物料当前库存、安全库存等信息
缺料单生成|当库存不足时，生成缺料单

#### 用例图

```plantuml
@startuml MM模块用例图

title MM模块（物料管理）用例图

left to right direction

actor 物控员 as materialController
actor 仓库管理员 as warehouseKeeper
actor 系统 as system

rectangle MM模块 {
  
  package "产品主数据" {
    usecase "产品主数据管理" as UC0
    usecase "产品列表查询" as UC0A
  }
  
  package "物料主数据" {
    usecase "物料主数据管理" as UC1
    usecase "物料列表查询" as UC2
    usecase "库存查询" as UC3
  }
  
  package "生产领料" {
    usecase "生产领料" as UC4
    usecase "缺料单生成" as UC5
    usecase "领料单审核" as UC6
  }
}

' 物控员用例
materialController --> UC0 : 管理产品
materialController --> UC0A : 查询产品
materialController --> UC1 : 管理物料
materialController --> UC2 : 查询物料
materialController --> UC3 : 查询库存
materialController --> UC4 : 创建领料单
materialController --> UC5 : 生成缺料单

' 仓库管理员用例
warehouseKeeper --> UC4 : 处理领料
warehouseKeeper --> UC6 : 审核领料单
warehouseKeeper --> UC3 : 查询库存

' 系统用例
system --> UC4 : 自动生成领料需求
system --> UC4 : 实时显示库存
system --> UC5 : 库存不足预警

' 用例关系
UC4 ..> UC6 : <<include>>
UC4 ..> UC5 : <<extend>>
UC2 ..> UC3 : <<include>>

note right of UC0
  管理产品主数据
  以本厂编号为唯一标识
  本厂编号同时作为产品编码
  包含物料主数据中成品(FG)的所有内容
  只显示成品(FG类型)的物料
  支持自动创建产品（如需要）
end note

note right of UC1
  管理物料主数据
  包含编码、名称、分类
  （原材料、辅材、半成品、维修等）、
  规格、库存等信息
  不包含成品（FG类型）
  成品通过产品主数据管理
end note

note right of UC4
  根据生产订单创建领料单
  自动显示库存信息
  支持部分领料
end note

note right of UC5
  库存不足时
  自动生成缺料单
end note

@enduml
```

## 四、流程说明

### 销售报价流程

#### 流程说明

销售报价流程是销售业务的起点，从客户询价开始，经过报价单创建、报价计算、三级审核、客户确认等环节，最终可以转为销售订单。流程包括：

1. **报价单创建**：销售员根据客户需求创建报价单，填写客户信息、产品信息（本厂编号、产品名称）、价格条款等。如果输入的14位本厂编号不存在对应的产品主数据，系统自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），并自动填充产品名称
2. **报价单预估报价**：销售员填写板规格参数（出货长、出货宽、利用率、PNL参数等）、工艺参数（层数、板厚、铜厚、线宽线距、表面处理等）、加价选项（常规加价、特殊加价、额外加价等）后，系统自动计算报价明细成本。计算内容包括：
   - **交货面积计算**：根据出货长、出货宽、订单数量计算交货面积（m²）
   - **基础成本计算**：根据基础成本基准值和层数调整系数计算成本/平米
   - **加价计算**：根据常规加价、特殊加价、额外加价选项计算总加价/平米
   - **最终成本计算**：基础成本 + 加价，得到最终成本/平米和成本PCS
   - **报价价格计算**：在成本基础上按利润率系数（如1.3，即30%利润）计算报价价格/平米和报价价格PCS
   - **费用计算**：计算工程费（根据层数）、板材费（成本×面积）、测试架费用（根据测试点数）、其他费用（最低消费等）
   - **最终总价计算**：工程费 + 板材费 + 测试架费用 + 其他费用
   - **工序成本分摊**：将成本按比例分摊到各工序（开料、钻孔、电镀、线路、阻焊、表面处理、成型等），生成工序成本明细
   - 系统支持实时计算（修改参数时自动计算）和手动计算（点击"计算报价"按钮）两种模式
   - 计算结果保存到报价单主表和报价明细工序表
3. **一级审核**：销售经理进行一级审核，检查报价单的基本信息和价格合理性。审核不通过时，报价单退回草稿状态，销售员可修改后重新提交
4. **二级审核**：工程部门进行二级审核，确认价格策略和交期承诺。审核不通过时，报价单退回草稿状态，销售员可修改后重新提交
5. **三级审核**：客户经理进行三级审核，最终确认报价单。审核不通过时，报价单退回草稿状态，销售员可修改后重新提交
6. **客户确认**：客户确认报价单后，可以转为销售订单
7. **报价转订单**：将已确认的报价单转为销售订单

#### 流程图

```plantuml
@startuml 销售报价流程状态图

title 销售报价流程状态图

[*] --> 草稿 : 创建报价单

state 草稿 {
  草稿 : 填写客户信息
  草稿 : 填写产品信息（本厂编号、产品名称）
  草稿 : 填写价格条款
  草稿 : 可随时编辑
  草稿 : 自动创建产品主数据（如需要）
}

草稿 --> 待一级审核 : 提交审核
待一级审核 --> 草稿 : 审核不通过\n退回修改

待一级审核 --> 待二级审核 : 一级审核通过
待二级审核 --> 草稿 : 审核不通过\n退回修改

待二级审核 --> 待三级审核 : 二级审核通过
待三级审核 --> 草稿 : 审核不通过\n退回修改

待三级审核 --> 客户确认 : 三级审核通过
客户确认 --> 待三级审核 : 客户不确认\n退回

客户确认 --> 已转订单 : 转为销售订单
客户确认 --> 已归档 : 客户不转单\n归档

已转订单 --> [*] : 流程结束
已归档 --> [*] : 流程结束

note right of 草稿
  报价单初始状态
  可以随时编辑修改
end note

note right of 待一级审核
  等待销售经理审核
  检查基本信息
end note

note right of 待二级审核
  等待部门经理审核
  确认价格策略
end note

note right of 待三级审核
  等待客户经理审核
  最终确认报价
end note

note right of 客户确认
  客户确认报价单
  可以转为订单
end note

@enduml
```

### 返单快速下单流程

#### 流程说明

返单快速下单流程针对老客户重复下单的场景，系统自动识别返单并匹配历史订单信息，快速创建销售订单，跳过报价环节。流程包括：

1. **返单识别**：系统自动检测是否为返单（相同客户、相同产品主数据（本厂编号）、在时间范围内）
2. **历史订单匹配**：系统自动匹配历史订单，显示历史价格、交期等信息
3. **订单信息填充**：系统自动填充订单信息，包括产品主数据（本厂编号）、价格、交期等
4. **订单确认**：销售员确认订单信息，可以调整数量、价格等
5. **订单创建**：创建销售订单，进入生产流程

#### 流程图

```plantuml
@startuml 返单快速下单流程状态图

title 返单快速下单流程状态图

[*] --> 返单识别 : 客户下单

state 返单识别 {
  返单识别 : 系统检测客户
  返单识别 : 系统检测产品主数据（本厂编号）
  返单识别 : 系统检测时间范围
}

返单识别 --> 历史订单匹配 : 识别为返单
返单识别 --> 新单流程 : 识别为新单

state 历史订单匹配 {
  历史订单匹配 : 查询历史订单
  历史订单匹配 : 匹配产品主数据（本厂编号）
  历史订单匹配 : 匹配价格信息
  历史订单匹配 : 匹配交期信息
}

历史订单匹配 --> 订单信息填充 : 匹配成功

state 订单信息填充 {
  订单信息填充 : 自动填充产品主数据（本厂编号）
  订单信息填充 : 自动填充价格
  订单信息填充 : 自动填充交期
  订单信息填充 : 自动填充付款方式
}

订单信息填充 --> 订单确认 : 填充完成

state 订单确认 {
  订单确认 : 确认产品主数据（本厂编号）
  订单确认 : 调整数量
  订单确认 : 调整价格（如需要）
  订单确认 : 确认交期
}

订单确认 --> 订单创建 : 确认提交
订单确认 --> 订单信息填充 : 需要修改

订单创建 --> [*] : 订单创建成功

note right of 返单识别
  系统自动检测
  是否为返单
end note

note right of 历史订单匹配
  自动匹配历史订单
  显示历史信息
end note

note right of 订单信息填充
  自动填充订单信息
  减少人工输入
end note

note right of 订单确认
  销售员确认订单
  可以调整信息
end note

@enduml
```

### 新单下单流程

#### 流程说明

新单下单流程针对新客户或新产品下单的场景，需要完整录入订单信息，经过订单审核等环节，创建销售订单。流程包括：

1. **客户选择**：选择或创建客户主数据，确认客户信息
2. **产品主数据确认**：确认或创建产品主数据（本厂编号），如果输入的14位本厂编号不存在对应的产品主数据，系统自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），并自动填充产品名称
3. **订单信息录入**：手动录入订单信息，包括产品主数据（本厂编号）、数量、价格、交期、付款方式等
4. **价格确认**：确认订单价格，可以查询历史价格作为参考
5. **订单审核**：对订单进行审核，确认订单信息的完整性和准确性
6. **订单创建**：创建销售订单，进入生产流程

#### 流程图

```plantuml
@startuml 新单下单流程状态图

title 新单下单流程状态图

[*] --> 客户选择 : 新单下单

state 客户选择 {
  客户选择 : 选择已有客户
  客户选择 : 创建新客户（如需要）
  客户选择 : 确认客户信息
  客户选择 : 确认送货地址
}

客户选择 --> 产品主数据确认 : 客户确认完成

state 产品主数据确认 {
  产品主数据确认 : 输入本厂编号
  产品主数据确认 : 确认产品主数据
  产品主数据确认 : 自动创建产品主数据（如需要）
  产品主数据确认 : 确认产品名称
  产品主数据确认 : 确认PCB专有属性
}

产品主数据确认 --> 订单信息录入 : 产品确认完成

state 订单信息录入 {
  订单信息录入 : 录入产品主数据（本厂编号）
  订单信息录入 : 录入订单数量
  订单信息录入 : 录入单价
  订单信息录入 : 录入交期
  订单信息录入 : 选择付款方式
  订单信息录入 : 录入其他条款
}

订单信息录入 --> 价格确认 : 信息录入完成
订单信息录入 --> 订单信息录入 : 继续添加产品

state 价格确认 {
  价格确认 : 确认订单总价
  价格确认 : 查询历史价格（如需要）
  价格确认 : 调整价格（如需要）
  价格确认 : 确认价格条款
}

价格确认 --> 订单审核 : 价格确认完成
价格确认 --> 订单信息录入 : 需要修改

state 订单审核 {
  订单审核 : 审核订单信息
  订单审核 : 审核价格合理性
  订单审核 : 审核交期可行性
  订单审核 : 确认订单完整性
}

订单审核 --> 订单创建 : 审核通过
订单审核 --> 订单信息录入 : 审核不通过\n退回修改

state 订单创建 {
  订单创建 : 创建销售订单
  订单创建 : 生成订单编号
  订单创建 : 订单状态更新
}

订单创建 --> [*] : 订单创建成功

note right of 客户选择
  选择或创建客户
  确认客户信息
  确认送货地址
end note

note right of 产品主数据确认
  确认或创建产品主数据
  以本厂编号为唯一标识
  支持自动创建（如需要）
end note

note right of 订单信息录入
  手动录入订单信息
  包括产品、数量、价格、交期等
  支持添加多个产品
end note

note right of 价格确认
  确认订单价格
  可查询历史价格参考
  可调整价格
end note

note right of 订单审核
  审核订单信息
  确认完整性和准确性
  审核不通过可退回修改
end note

@enduml
```

### BOM创建流程

#### 流程说明

BOM创建流程用于定义产品的物料组成结构，包括创建BOM、添加物料、版本管理等环节。流程包括：

1. **产品主数据创建**：创建产品主数据，以本厂编号作为唯一标识，填写产品基本信息、PCB专有工程属性等
2. **BOM创建**：创建新的BOM，指定父项产品（本厂编号）和版本信息
2. **添加物料**：在BOM中添加子项物料，设置用量等信息
3. **BOM保存**：保存BOM，可以保存为草稿或直接发布
4. **BOM审核**：对BOM进行审核，确认物料清单的准确性
5. **BOM发布**：发布BOM，使其可用于生产
6. **版本管理**：可以基于现有BOM创建新版本

#### 流程图

```plantuml
@startuml BOM创建流程状态图

title BOM创建流程状态图

[*] --> 新建BOM : 创建BOM

state 产品主数据创建 {
  产品主数据创建 : 生成本厂编号
  产品主数据创建 : 填写产品基本信息
  产品主数据创建 : 填写PCB专有属性
  产品主数据创建 : 设置客户型号映射
}

产品主数据创建 --> 新建BOM : 产品创建完成

state 新建BOM {
  新建BOM : 输入BOM编号
  新建BOM : 选择父项产品（本厂编号）
  新建BOM : 设置版本信息
}

新建BOM --> 添加物料 : 开始添加物料

state 添加物料 {
  添加物料 : 选择子项物料
  添加物料 : 设置用量
  添加物料 : 设置单位
  添加物料 : 添加备注
}

添加物料 --> 添加物料 : 继续添加
添加物料 --> BOM保存 : 完成添加

state BOM保存 {
  BOM保存 : 保存为草稿
  BOM保存 : 直接发布
}

BOM保存 --> 草稿 : 保存为草稿
BOM保存 --> 待审核 : 直接发布

state 草稿 {
  草稿 : 可继续编辑
  草稿 : 可添加物料
  草稿 : 可删除物料
}

草稿 --> 添加物料 : 继续编辑
草稿 --> 待审核 : 提交审核

state 待审核 {
  待审核 : 等待审核
  待审核 : 不可编辑
}

待审核 --> 已发布 : 审核通过
待审核 --> 草稿 : 审核不通过\n退回修改

state 已发布 {
  已发布 : BOM可用
  已发布 : 可用于生产
  已发布 : 可创建新版本
}

已发布 --> 新建BOM : 创建新版本
已发布 --> [*] : 流程结束

note right of 产品主数据创建
  创建产品主数据
  以本厂编号为唯一标识
  包含PCB专有工程属性
end note

note right of 新建BOM
  创建新的BOM
  指定父项产品（本厂编号）
end note

note right of 添加物料
  添加子项物料
  设置用量等信息
end note

note right of 待审核
  等待审核
  确认物料清单准确性
end note

note right of 已发布
  BOM已发布
  可用于生产
end note

@enduml
```

### 工艺路线创建流程

#### 流程说明

工艺路线创建流程用于定义产品的生产工艺流程，包括创建工艺路线、添加工序、版本管理等环节。流程包括：

1. **产品主数据创建**：创建产品主数据，以本厂编号作为唯一标识，填写产品基本信息、PCB专有工程属性等
2. **工艺路线创建**：创建新的工艺路线，指定父项产品（本厂编号）和版本信息
3. **添加工序**：在工艺路线中添加工序，设置工序序列、工作中心、标准时间等信息
4. **工艺路线保存**：保存工艺路线，可以保存为草稿或直接发布
5. **工艺路线审核**：对工艺路线进行审核，确认工艺流程的准确性
6. **工艺路线发布**：发布工艺路线，使其可用于生产
7. **版本管理**：可以基于现有工艺路线创建新版本

#### 流程图

```plantuml
@startuml 工艺路线创建流程状态图

title 工艺路线创建流程状态图

[*] --> 新建工艺路线 : 创建工艺路线

state 产品主数据创建 {
  产品主数据创建 : 生成本厂编号
  产品主数据创建 : 填写产品基本信息
  产品主数据创建 : 填写PCB专有属性
  产品主数据创建 : 设置客户型号映射
}

产品主数据创建 --> 新建工艺路线 : 产品创建完成

state 新建工艺路线 {
  新建工艺路线 : 输入工艺路线编号
  新建工艺路线 : 选择父项产品（本厂编号）
  新建工艺路线 : 设置版本信息
}

新建工艺路线 --> 添加工序 : 开始添加工序

state 添加工序 {
  添加工序 : 设置工序序列
  添加工序 : 选择工作中心
  添加工序 : 设置标准时间
  添加工序 : 设置工序名称
  添加工序 : 添加备注
}

添加工序 --> 添加工序 : 继续添加
添加工序 --> 工艺路线保存 : 完成添加

state 工艺路线保存 {
  工艺路线保存 : 保存为草稿
  工艺路线保存 : 直接发布
}

工艺路线保存 --> 草稿 : 保存为草稿
工艺路线保存 --> 待审核 : 直接发布

state 草稿 {
  草稿 : 可继续编辑
  草稿 : 可添加工序
  草稿 : 可删除工序
  草稿 : 可调整工序顺序
}

草稿 --> 添加工序 : 继续编辑
草稿 --> 待审核 : 提交审核

state 待审核 {
  待审核 : 等待审核
  待审核 : 不可编辑
}

待审核 --> 已发布 : 审核通过
待审核 --> 草稿 : 审核不通过\n退回修改

state 已发布 {
  已发布 : 工艺路线可用
  已发布 : 可用于生产
  已发布 : 可创建新版本
}

已发布 --> 新建工艺路线 : 创建新版本
已发布 --> [*] : 流程结束

note right of 产品主数据创建
  创建产品主数据
  以本厂编号为唯一标识
  包含PCB专有工程属性
end note

note right of 新建工艺路线
  创建新的工艺路线
  指定父项产品（本厂编号）
end note

note right of 添加工序
  添加工序信息
  设置序列、工作中心、标准时间等
end note

note right of 待审核
  等待审核
  确认工艺流程准确性
end note

note right of 已发布
  工艺路线已发布
  可用于生产
end note

@enduml
```

### 生产领料流程

#### 流程说明

生产领料流程用于处理生产订单的物料发放，包括创建领料单、库存检查、物料发放、审核确认等环节。流程包括：

1. **创建领料单**：根据生产订单自动生成领料需求，创建领料单
2. **库存检查**：系统自动检查物料库存，显示当前库存和安全库存
3. **库存预警**：当库存低于安全库存时，系统自动预警
4. **物料发放**：仓库管理员根据领料单发放物料，记录实际发放数量
5. **领料审核**：对领料单进行审核确认
6. **缺料处理**：当库存不足时，生成缺料单

#### 流程图

```plantuml
@startuml 生产领料流程状态图

title 生产领料流程状态图

[*] --> 创建领料单 : 生产订单下达

state 创建领料单 {
  创建领料单 : 根据生产订单生成
  创建领料单 : 显示物料需求
  创建领料单 : 显示BOM信息
}

创建领料单 --> 库存检查 : 自动检查库存

state 库存检查 {
  库存检查 : 检查当前库存
  库存检查 : 检查安全库存
  库存检查 : 计算可用库存
}

库存检查 --> 库存充足 : 库存充足
库存检查 --> 库存不足 : 库存不足

state 库存充足 {
  库存充足 : 可以正常领料
  库存充足 : 显示库存信息
}

state 库存不足 {
  库存不足 : 库存低于需求
  库存不足 : 显示预警信息
}

库存充足 --> 物料发放 : 开始发放
库存不足 --> 缺料处理 : 生成缺料单

state 物料发放 {
  物料发放 : 记录实际发放数量
  物料发放 : 更新库存
  物料发放 : 记录库位信息
}

物料发放 --> 领料审核 : 发放完成

state 缺料处理 {
  缺料处理 : 生成缺料单
  缺料处理 : 通知采购
  缺料处理 : 部分领料
}

缺料处理 --> 物料发放 : 部分物料发放
缺料处理 --> [*] : 等待补货

state 领料审核 {
  领料审核 : 审核领料单
  领料审核 : 确认发放数量
  领料审核 : 确认库位信息
}

领料审核 --> 已确认 : 审核通过
领料审核 --> 物料发放 : 审核不通过\n退回

state 已确认 {
  已确认 : 领料完成
  已确认 : 库存已扣减
  已确认 : 可用于生产
}

已确认 --> [*] : 流程结束

note right of 创建领料单
  根据生产订单
  自动生成领料需求
end note

note right of 库存检查
  自动检查库存
  显示库存信息
end note

note right of 库存不足
  库存不足时
  自动预警
end note

note right of 物料发放
  记录实际发放
  更新库存信息
end note

note right of 缺料处理
  生成缺料单
  通知采购补货
end note

@enduml
```

### 工序报工流程

#### 流程说明

工序报工流程用于记录生产工序的完成情况，包括报工数据录入、不良品管理、工时记录等环节。流程包括：

1. **选择生产订单/工单并自动读取LOT卡**：选择要报工的生产订单/工单后，系统根据生产订单号自动查询关联的LOT卡，并自动填充报工单中的LOT卡号字段（只读、不可修改）；如找不到LOT卡，则不允许保存报工
2. **任务确认**：确认当前工序任务，显示生产订单、LOT卡号、工序名称、计划数量等信息
3. **报工数据录入**：录入完成数量、良品数量、不良品数量等数据
4. **不良品管理**：记录不良品信息，包括不良原因、处理方式等
5. **工时记录**：记录实际工时，系统自动计算工时差异
6. **设备信息**：记录使用的设备信息和设备状态
7. **报工保存**：保存报工记录，更新生产进度

#### 流程图

```plantuml
@startuml 工序报工流程状态图

title 工序报工流程状态图

[*] --> 任务确认 : 工序开始

state 任务确认 {
  任务确认 : 确认生产订单
  任务确认 : 确认工序名称
  任务确认 : 确认计划数量
  任务确认 : 确认工作中心
}

任务确认 --> 报工数据录入 : 开始报工

state 报工数据录入 {
  报工数据录入 : 录入完成数量
  报工数据录入 : 录入良品数量
  报工数据录入 : 系统自动计算不良品数量
}

报工数据录入 --> 不良品管理 : 有不良品
报工数据录入 --> 工时记录 : 无不良品

state 不良品管理 {
  不良品管理 : 记录不良原因
  不良品管理 : 选择处理方式
  不良品管理 : 记录责任工序
  不良品管理 : 添加备注
}

不良品管理 --> 工时记录 : 不良品记录完成

state 工时记录 {
  工时记录 : 记录开始时间
  工时记录 : 记录结束时间
  工时记录 : 系统自动计算实际工时
  工时记录 : 系统自动计算工时差异
}

工时记录 --> 设备信息 : 工时记录完成

state 设备信息 {
  设备信息 : 选择设备
  设备信息 : 记录设备状态
  设备信息 : 记录异常情况
  设备信息 : 记录操作员
}

设备信息 --> 报工保存 : 信息录入完成

state 报工保存 {
  报工保存 : 保存报工记录
  报工保存 : 更新生产进度
  报工保存 : 更新库存
  报工保存 : 生成报工单
}

报工保存 --> 已报工 : 保存成功

state 已报工 {
  已报工 : 报工完成
  已报工 : 进度已更新
  已报工 : 可进行下一工序
}

已报工 --> [*] : 流程结束

note right of 任务确认
  确认当前工序任务
  显示相关信息
end note

note right of 报工数据录入
  录入完成数量
  系统自动计算不良品
end note

note right of 不良品管理
  记录不良品信息
  包含原因和处理方式
end note

note right of 工时记录
  记录工时信息
  系统自动计算差异
end note

note right of 报工保存
  保存报工记录
  更新生产进度
end note

@enduml
```

### 生产执行全流程

#### 流程说明

生产执行全流程从销售订单开始，经过订单评审、BOM和工艺路线准备、生产版本建立、MI制作、生产版本发布、生产订单下达、物料领料、工序报工等环节，最终完成生产并入库。流程包括：

1. **订单评审**：对销售订单进行评审，确认价格、交期等
2. **产品主数据确认**：确认或创建产品主数据，以本厂编号作为唯一标识
3. **BOM和工艺路线准备**：准备产品的BOM和工艺路线（基于产品主数据的本厂编号）
4. **生产版本建立**：将BOM和工艺路线组合，建立生产版本
5. **MI制作**：根据订单创建制造指令，包含技术参数和生产要求
6. **生产版本发布**：发布生产版本，使其可用于生产订单下达
7. **生产订单下达**：下达生产订单/工单，系统根据MI自动生成LOT卡，LOT卡包含MI内容和生产信息，并将lot_number写回生产订单
8. **物料领料**：根据生产订单领料
9. **工序报工**：各工序完成后进行报工，系统根据生产订单自动读取LOT卡号并填充到报工单中，LOT卡号不可修改
10. **成品入库**：生产完成后，成品入库

#### 流程图

```plantuml
@startuml 生产执行全流程状态图

title 生产执行全流程状态图

[*] --> 订单评审 : 销售订单创建

state 订单评审 {
  订单评审 : 评审价格
  订单评审 : 评审交期
  订单评审 : 评审技术可行性
}

订单评审 --> 产品主数据确认 : 评审通过
订单评审 --> [*] : 评审不通过

state 产品主数据确认 {
  产品主数据确认 : 确认产品本厂编号
  产品主数据确认 : 创建产品主数据（如需要）
  产品主数据确认 : 确认PCB专有属性
}

产品主数据确认 --> BOM准备 : 产品确认完成
产品主数据确认 --> 工艺路线准备 : 产品确认完成

state BOM准备 {
  BOM准备 : 创建或选择BOM
  BOM准备 : 确认物料清单
}

state 工艺路线准备 {
  工艺路线准备 : 创建或选择工艺路线
  工艺路线准备 : 确认工序序列
}

BOM准备 --> 生产版本建立 : BOM准备完成
工艺路线准备 --> 生产版本建立 : 工艺路线准备完成

state 生产版本建立 {
  生产版本建立 : 组合BOM和工艺路线
  生产版本建立 : 建立生产版本
}

生产版本建立 --> MI制作 : 生产版本建立完成

state MI制作 {
  MI制作 : 创建MI
  MI制作 : 填写技术参数
  MI制作 : MI审核
  MI制作 : 生产版本发布
}

MI制作 --> 生产订单下达 : MI审核通过\n生产版本已发布

state 生产订单下达 {
  生产订单下达 : 下达生产订单/工单
  生产订单下达 : 生成工单并自动生成LOT卡
  生产订单下达 : 分配工作中心
}

生产订单下达 --> 物料领料 : 订单下达完成

state 物料领料 {
  物料领料 : 创建领料单
  物料领料 : 检查库存
  物料领料 : 发放物料
}

物料领料 --> 工序执行 : 领料完成

state 工序执行 {
  工序执行 : 读取LOT卡号（自动填充，不可修改）
  工序执行 : 执行各工序
  工序执行 : 工序报工
  工序执行 : 记录不良品
}

工序执行 --> 工序执行 : 下一工序
工序执行 --> 成品入库 : 所有工序完成

state 成品入库 {
  成品入库 : 成品检验
  成品入库 : 成品入库
  成品入库 : 更新库存
}

成品入库 --> [*] : 流程结束

note right of 订单评审
  评审销售订单
  确认价格和交期
end note

note right of 产品主数据确认
  确认或创建产品主数据
  以本厂编号为唯一标识
  本厂编号同时作为产品编码
  产品类型为成品(FG)
  支持自动创建（如需要）
end note

note right of MI制作
  创建制造指令
  包含技术参数
  发布生产版本
end note

note right of 生产版本建立
  组合BOM和工艺路线
  建立生产版本
  后续在MI制作中发布
end note

note right of 生产订单下达
  在MI审核通过
  生产版本发布后
  下达生产订单
  生成工单
end note

note right of 工序执行
  执行各工序
  记录完成情况
end note

note right of 成品入库
  成品检验入库
  更新库存
end note

@enduml
```
