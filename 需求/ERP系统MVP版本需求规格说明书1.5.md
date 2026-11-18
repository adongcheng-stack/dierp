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
- **规范数据管理**：建立统一的主数据管理体系，确保数据的准确性和一致性。支持产品主数据自动创建（SD子系统调用ENG子系统API），产品主数据由工程管理子系统统一管理
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

- **SD子系统（销售与分销）**：客户管理、报价单管理、销售订单管理、订单评审等
- **ENG子系统（工程管理）**：产品主数据管理、BOM管理、工艺路线管理、MI管理、生产版本管理等
- **PP子系统（生产计划与控制）**：工作中心管理、生产订单/工单管理、LOT卡管理、工序报工等
- **MM子系统（物料管理）**：物料主数据管理、生产领料、库存管理等

#### 1.3.2 业务流程范围

本MVP版本支持以下核心业务流程：

- **基础数据配置**：为了确保系统流程能够正常执行，系统上线前必须完成基础数据配置，请参考1.3.5 配置管理子系统内容
- **客户建档流程**：销售员创建客户主数据，销售经理审批，激活客户
- **销售报价流程**：从客户询价到报价单创建、三级审核（串行：销售经理→工程师→客户经理/总经理）、销售员经客户确认报价单的完整流程。报价单创建时，如果本厂编号不存在，SD子系统自动调用ENG子系统API创建产品主数据
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

#### 1.3.5 配置管理子系统

为了确保系统流程能够正常执行，系统上线前必须完成以下基础数据配置：

**1. 客户主数据配置（必须）**
- **客户建档**：创建客户主数据，包含客户基本信息、合作属性、地址信息、联系人信息、销售数据等
- **客户审批**：销售经理审批客户，审批通过后客户状态更新为"激活"（ACTIVE）
- **前置条件**：只有激活状态的客户才能用于报价单和销售订单创建

**2. 物料主数据配置（必须）**
- **物料主数据录入**：创建和维护物料主数据，包含物料编码、名称、分类（原材料、辅材、化工材料、半成品、维修等）、规格型号、计量单位、库存信息等
- **物料分类**：物料主数据管理中不显示成品（FG类型），成品通过工程管理子系统的产品主数据管理进行维护
- **前置条件**：物料主数据必须存在，才能用于BOM创建和生产领料

**3. 工作中心配置（必须）**
- **工作中心设置**：创建和维护工作中心主数据，包含工作中心代码、描述、类型（单台机器、机组、人工工位、产线）、所属工厂、状态等
- **层级关系**：设置工作中心的层级关系（父工作中心、层级级别），支持多级工作中心结构
- **时间参数**：配置工作中心的时间参数，包括排队时间（Queue Time）、等待时间（Wait Time）、传送时间（Move Time）等
- **产能数据**：配置工作中心的产能数据，包括能力类别、工厂日历、班次时间、产能利用率、能力数量等
- **成本数据**：配置工作中心的成本数据，包括成本中心、工艺类别等
- **前置条件**：工作中心必须存在且状态为"激活"（ACTIVE），才能用于工艺路线创建和生产排程

**4. 产品主数据配置（建议提前准备）**
- **产品主数据创建**：创建产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）
- **PCB专有属性**：配置产品的PCB专有工程属性，包括层数、板厚、铜厚、表面处理等
- **自动创建说明**：虽然SD子系统可以在报价单创建时自动创建产品主数据，但建议提前在工程管理子系统创建完整的产品主数据，以确保数据准确性和一致性
- **前置条件**：产品主数据必须存在，才能用于报价单、销售订单、BOM、工艺路线和生产版本创建

**5. BOM（物料清单）配置（创建生产订单前必须）**
- **BOM创建**：创建物料清单，定义产品的物料组成结构（父项产品、子项物料、用量等）
- **BOM版本管理**：管理BOM版本，确保使用正确的BOM版本
- **BOM发布**：发布BOM，使其状态为"已发布"（RELEASED）
- **前置条件**：只有RELEASED状态的BOM才能用于生产版本和生产订单创建

**6. 工艺路线配置（创建生产订单前必须）**
- **工艺路线创建**：创建工艺路线，定义产品的生产工艺流程，包含工序序列、工作中心、标准时间（调机时间、机器时间、人工时间、排队缓冲）等
- **工艺路线版本管理**：管理工艺路线版本，确保使用正确的工艺路线版本
- **工艺路线发布**：发布工艺路线，使其状态为"已发布"（RELEASED）
- **前置条件**：只有RELEASED状态的工艺路线才能用于生产版本和生产订单创建

**7. 生产版本配置（创建生产订单前必须）**
- **生产版本建立**：将BOM和工艺路线组合，建立生产版本
- **MI关联**：如果生产版本需要关联MI（制造指令），则必须确保MI已创建且状态为"已发布"（RELEASED）
- **生产版本发布**：发布生产版本，使其可用于生产订单创建
- **前置条件**：生产版本必须存在且已发布，才能用于生产订单创建

**8. MI（制造指令）配置（可选，但建议提前准备）**
- **MI创建**：创建制造指令，包含客户型号、技术参数、生产要求等
- **MI审核**：对MI进行审核，确认技术参数和生产要求
- **MI发布**：发布MI，使其状态为"已发布"（RELEASED）
- **前置条件**：如果生产版本关联了MI，则MI必须存在且状态为RELEASED，才能创建生产订单。如果MI不存在，系统不允许创建生产订单或提示用户先创建MI

**配置顺序建议：**
1. 首先配置基础数据：客户主数据、物料主数据、工作中心
2. 然后配置产品数据：产品主数据、BOM、工艺路线
3. 最后配置生产数据：生产版本、MI（如需要）

**配置责任人：**
- **客户主数据**：销售员创建，销售经理审批
- **物料主数据**：计划员（物控岗）创建和维护
- **工作中心**：计划员创建和维护
- **产品主数据、BOM、工艺路线、生产版本、MI**：工程师创建和维护

### 1.4 系统概述

#### 1.4.1 系统定位

某某ERP系统MVP版本是一个面向PCB制造企业的核心业务管理系统，专注于销售、工程、生产、物料等核心业务流程的信息化管理。

#### 1.4.2 系统特点

- **行业特色**：针对PCB制造行业的特点，支持本厂编号管理（14位编码，同时作为产品编码）、PCB专有属性管理（层数、板厚、铜厚、表面处理等）、MI管理、LOT卡管理等行业特色功能
- **流程驱动**：以业务流程为核心，通过工作流引擎实现业务流程的自动化管理。支持串行审核流程（报价单三级审核、订单多部门评审）、状态自动同步（生产订单状态同步销售订单状态）
- **数据统一**：建立统一的主数据管理体系，确保数据的准确性和一致性。产品主数据由工程管理子系统统一管理，SD子系统可以引用和自动创建，但不能修改和删除
- **自动化处理**：支持产品主数据自动创建（SD子系统调用ENG子系统API）、LOT卡自动生成（生产订单与LOT卡1:1关系）、领料需求自动生成（基于BOM）、库存自动更新等自动化处理
- **灵活扩展**：采用模块化设计，支持后续功能扩展和系统升级

#### 1.4.3 系统架构

系统采用前后端分离的架构设计：

- **前端**：提供友好的用户交互界面
- **后端**：基于FastAPI框架的RESTful API服务，提供业务逻辑处理和数据访问
- **数据库**：PostgreSQL关系型数据库，存储业务数据
- **工作流引擎**：支持业务流程的自动化流转和状态管理

#### 1.4.4 用户角色

系统支持以下用户角色（系统角色枚举），各角色按模块划分职责：

**SD子系统（销售与分销）角色：**
- **销售员（SALES）**：负责客户建档、客户信息维护、报价单创建、报价单预估报价、销售订单创建、返单快速下单等
- **销售经理（SALES_MANAGER）**：负责报价单一级审核、销售订单评审（销售部门评审）等
- **工程师（ENGINEER）**：参与报价单二级审核，负责确认价格策略和交期承诺
- **总经理（GENERAL_MANAGER）**：负责报价单三级审核（与客户经理二选一）、销售订单评审等

**ENG子系统（工程管理）角色：**
- **工程师（ENGINEER）**：负责产品主数据管理、BOM创建和管理、工艺路线创建和管理、MI创建和管理、生产版本建立等。工程师也负责MI审核，确认技术参数和生产要求

**PP子系统（生产计划与控制）角色：**
- **计划员（PLANNER）**：负责工作中心管理、生产订单/工单管理、LOT卡查询和管理、生产进度查看、生产订单关闭等
- **生产人员（PRODUCTION）**：负责工序报工、不良品记录、LOT卡查询和查看等

**MM子系统（物料管理）角色：**
- **计划员（PLANNER）**：负责物料主数据管理、物料列表查询、库存查询、生产领料单创建、缺料单生成等（物控岗）
- **仓库管理员（WAREHOUSE）**：负责生产领料处理、领料单审核、库存查询等

**跨子系统角色：**
- **财务人员（FINANCE）**：负责销售订单评审（财务部门评审）等
- **系统管理员（ADMIN）**：负责系统配置、用户管理、角色权限管理等，拥有所有子系统的操作权限

**说明：**
- 系统角色枚举包括：SALES、SALES_MANAGER、ENGINEER、PLANNER、PRODUCTION、WAREHOUSE、FINANCE、GENERAL_MANAGER、ADMIN
- 业务角色（如客户经理、审核员、产线工人、生产主管、物控员等）通过分配相应的系统角色来实现权限控制
- 系统管理员（ADMIN）角色拥有所有子系统的操作权限，可以绕过所有角色限制

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

- **版本号**：v1.4
- **创建日期**：2025-01-XX
- **最后更新**：2025-01-XX

#### 1.5.4 术语定义

- **本厂编号**：某某内部为每个产品分配的唯一标识，14位编码，同时作为产品编码（material_code）。产品主数据以本厂编号作为唯一标识
- **LOT卡**：生产批次卡，由MI自动生成，关联生产订单/工单，是工序报工的批次依据。一个生产订单/工单对应一个LOT卡（1:1关系）。在生产订单/工单创建时，如果关联了MI，系统自动生成LOT卡，自动复制MI内容到LOT卡，并将lot_number写回生产订单
- **MI**：制造指令（Manufacturing Instruction），包含客户型号、技术参数、生产要求等，是生产执行的依据。MI由工程管理子系统创建和管理，发布后的MI可用于生产版本发布和生产订单/工单下达
- **BOM**：物料清单（Bill of Materials），定义产品的物料组成结构，包含父项产品、子项物料、用量等。只有RELEASED状态的BOM才能用于生产版本
- **工艺路线**：定义产品的生产工艺流程，包含工序序列、工作中心、标准时间等。标准时间包括调机时间（Setup Time，工序开始前的设备调试准备时间）、机器时间（Machine Time，机器运行时间，按基准数量计算）、人工时间（Labor Time，人工辅助操作时间，按基准数量计算）、排队缓冲（Queue Time，物料到达工作中心后开始加工前的平均排队等待时间）等时间参数（单位：分钟），用于生产计划排程、成本计算和产能管理。只有RELEASED状态的工艺路线才能用于生产版本
- **生产版本**：将BOM和工艺路线组合，形成可执行的生产版本。发布生产版本时需要MI已关联且状态为RELEASED
- **生产订单/工单**：生产订单/工单，包含生产数量、交期、关联的MI、BOM、工艺路线、工序任务、工作中心、计划时间等
- **工序报工**：记录各工序的完成情况，包含完成数量、良品数量、不良品数量、工时等，关联LOT卡号。系统根据生产订单/工单自动查询关联的LOT卡（1:1关系），自动填充报工单中的LOT卡号字段（只读、不可修改）

---

## 二、术语

### 术语列表

术语名称|说明
-|-
客户|客户主数据，包含客户基本信息、多个合作属性、多个地址信息、多个联系人信息、销售数据等
报价单|销售报价单，包含客户主数据、产品主数据、价格条款、交付条款等，支持三级审核流程
销售订单|销售订单，由报价单转换或返单创建，包含订单信息、产品明细、交期承诺等
产品主数据|产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）。产品主数据包括产品基本信息、PCB专有工程属性（层数、板厚、铜厚、表面处理等）、技术参数、尺寸信息、供应链计划参数等。产品主数据管理只显示成品(FG类型)的物料
物料|物料主数据，包含物料编码、名称、分类（原材料、辅材、化工材料、半成品、维修等）、规格型号、库存信息等。物料主数据管理中不显示成品(FG类型)，成品通过产品主数据管理进行维护
BOM|物料清单，定义产品的物料组成结构，包含父项产品、子项物料、用量等
工艺路线|定义产品的生产工艺流程，包含工序序列、工作中心、标准时间等。标准时间包括调机时间（Setup Time，工序开始前的设备调试准备时间）、机器时间（Machine Time，机器运行时间，按基准数量计算）、人工时间（Labor Time，人工辅助操作时间，按基准数量计算）、排队缓冲（Queue Time，物料到达工作中心后开始加工前的平均排队等待时间）等时间参数（单位：分钟），用于生产计划排程、成本计算和产能管理
生产版本|将BOM和工艺路线组合，形成可执行的生产版本
MI|制造指令，包含客户型号、技术参数、生产要求等，是生产执行的依据
工作中心|生产资源主数据，包含工作中心代码、类型、产能数据、成本数据等
生产订单/工单|生产订单/工单，包含生产数量、交期、关联的MI、BOM、工艺路线、工序任务、工作中心、计划时间等
LOT卡|生产批次卡，由MI自动生成，关联生产订单/工单，包含MI内容、数量、单位、状态等信息，是工序报工的批次依据。一个生产订单/工单对应一个LOT卡（1:1关系）。在生产订单/工单创建时，如果关联了MI，自动生成LOT卡。如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI
领料单|生产领料单，包含领料明细、库存信息、发放记录等
报工单|工序报工记录，包含完成数量、良品数量、不良品数量、工时等，关联LOT卡号

### 关系图

关系图按子系统分组展示，便于理解各子系统的实体关系。详细的关系图文件请参考`docs/ER图/`目录。

#### 配置管理子系统关系图

系统上线前必须完成的基础数据配置及其关系如下：

**1. 基础数据配置（配置顺序：1）**

基础数据配置是系统运行的基础，必须在系统上线前完成，包括：

- **客户主数据**：创建客户主数据，包含客户基本信息、合作属性、地址信息、联系人信息、销售数据等。销售经理审批后，客户状态更新为"激活"（ACTIVE）。只有激活状态的客户才能用于报价单和销售订单创建。
- **物料主数据（非FG类型）**：创建和维护物料主数据，包含物料编码、名称、分类（原材料、辅材、化工材料、半成品、维修等）、规格型号、计量单位、库存信息等。物料主数据必须存在，才能用于BOM创建和生产领料。
- **工作中心**：创建和维护工作中心主数据，包含工作中心代码、描述、类型（单台机器、机组、人工工位、产线）、所属工厂、状态等。配置工作中心的层级关系、时间参数、产能数据和成本数据。工作中心必须存在且状态为"激活"（ACTIVE），才能用于工艺路线创建和生产排程。

**配置责任人**：客户主数据由销售员创建、销售经理审批；物料主数据和工作中心由计划员（物控岗）创建和维护。

**2. 产品数据配置（配置顺序：2）**

产品数据配置定义了产品的工程数据，在创建生产订单前必须完成，包括：

- **产品主数据（FG类型）**：创建产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）。配置产品的PCB专有工程属性，包括层数、板厚、铜厚、表面处理等。虽然SD子系统可以在报价单创建时自动创建产品主数据，但建议提前在工程管理子系统创建完整的产品主数据，以确保数据准确性和一致性。产品主数据必须存在，才能用于报价单、销售订单、BOM、工艺路线和生产版本创建。
- **BOM（物料清单）**：创建物料清单，定义产品的物料组成结构（父项产品、子项物料、用量等）。管理BOM版本，发布BOM使其状态为"已发布"（RELEASED）。只有RELEASED状态的BOM才能用于生产版本和生产订单创建。
- **工艺路线**：创建工艺路线，定义产品的生产工艺流程，包含工序序列、工作中心、标准时间（调机时间、机器时间、人工时间、排队缓冲）等。管理工艺路线版本，发布工艺路线使其状态为"已发布"（RELEASED）。只有RELEASED状态的工艺路线才能用于生产版本和生产订单创建。
- **MI（制造指令）**：创建制造指令，包含客户型号、技术参数、生产要求等。对MI进行审核，发布MI使其状态为"已发布"（RELEASED）。MI配置为可选，但建议提前准备。如果生产版本关联了MI，则MI必须存在且状态为RELEASED，才能创建生产订单。

**配置责任人**：产品主数据、BOM、工艺路线、MI均由工程师创建和维护。

**3. 生产数据配置（配置顺序：3）**

生产数据配置将产品数据组合成可用于生产的版本，在创建生产订单前必须完成，包括：

- **生产版本**：将BOM和工艺路线组合，建立生产版本。如果生产版本需要关联MI（制造指令），则必须确保MI已创建且状态为"已发布"（RELEASED）。发布生产版本，使其可用于生产订单创建。生产版本必须存在且已发布，才能用于生产订单创建。

**配置责任人**：生产版本由工程师建立和维护。

**配置关系图：**

```plantuml
@startuml 配置管理子系统关系图
skinparam linetype ortho

title 配置管理子系统ER图

package "基础数据配置" {
  entity customers {
    customer_id VARCHAR <<PK>>
    customer_status ENUM
  }
  
  entity materials_non_fg {
    material_code VARCHAR <<PK>>
    material_type VARCHAR
  }
  
  entity work_centers {
    work_center_id VARCHAR <<PK>>
    status ENUM
  }
}

package "产品数据配置" {
  entity materials_fg {
    material_code VARCHAR <<PK>>
    material_type VARCHAR
  }
  
  entity boms {
    bom_number VARCHAR <<PK>>
    parent_material_code VARCHAR <<FK>>
    status ENUM
  }
  
  entity routings {
    routing_id VARCHAR <<PK>>
    material_code VARCHAR <<FK>>
    status ENUM
  }
  
  entity mi {
    mi_number VARCHAR <<PK>>
    material_code VARCHAR <<FK>>
    status ENUM
  }
}

package "生产数据配置" {
  entity production_versions {
    production_version_id VARCHAR <<PK>>
    material_code VARCHAR <<FK>>
    bom_number VARCHAR <<FK>>
    routing_id VARCHAR <<FK>>
    mi_number VARCHAR <<FK>>
    status VARCHAR
  }
}

' 配置关系
customers ..> materials_fg : "前置条件：\n客户必须激活"
materials_non_fg ||--o{ boms : "用于BOM明细"
materials_fg ||--o{ boms : "创建BOM"
materials_fg ||--o{ routings : "创建工艺路线"
materials_fg ||--o{ mi : "创建MI"
work_centers ||--o{ routings : "用于工艺路线工序"
boms ||--o{ production_versions : "组成"
routings ||--o{ production_versions : "组成"
mi ||--o{ production_versions : "组成（可选）"

note right of customers
  配置顺序：1
  责任人：销售员创建，销售经理审批
  前置条件：只有激活状态的客户
  才能用于报价单和销售订单创建
end note

note right of materials_non_fg
  配置顺序：1
  责任人：计划员（物控岗）
  前置条件：物料主数据必须存在，
  才能用于BOM创建和生产领料
end note

note right of work_centers
  配置顺序：1
  责任人：计划员
  前置条件：工作中心必须存在且
  状态为ACTIVE，才能用于工艺
  路线创建和生产排程
end note

note right of materials_fg
  配置顺序：2
  责任人：工程师
  前置条件：产品主数据必须存在，
  才能用于报价单、销售订单、
  BOM、工艺路线和生产版本创建
  说明：SD子系统可以自动创建，
  但建议提前准备
end note

note right of boms
  配置顺序：2
  责任人：工程师
  前置条件：只有RELEASED状态的
  BOM才能用于生产版本和生产
  订单创建
end note

note right of routings
  配置顺序：2
  责任人：工程师
  前置条件：只有RELEASED状态的
  工艺路线才能用于生产版本和
  生产订单创建
end note

note right of mi
  配置顺序：3（可选）
  责任人：工程师
  前置条件：如果生产版本关联了
  MI，则MI必须存在且状态为
  RELEASED，才能创建生产订单
end note

note right of production_versions
  配置顺序：3
  责任人：工程师
  前置条件：生产版本必须存在且
  已发布，才能用于生产订单创建
  说明：组合BOM、工艺路线和MI
  （可选）形成生产版本
end note

@enduml
```

#### SD子系统（销售与分销）关系图

```plantuml
@startuml SD子系统ER图
skinparam linetype ortho

title SD子系统（销售与分销）ER图

package "SD子系统" {
  entity customers {
    id SERIAL <<PK>>
    customer_id VARCHAR <<UK>>
    legal_name VARCHAR
    trade_name VARCHAR
    tax_id VARCHAR
    customer_status ENUM
    customer_industry VARCHAR
  }
  
  entity customer_addresses {
    id SERIAL <<PK>>
    customer_id VARCHAR <<FK>>
    address_type VARCHAR
    detail_address VARCHAR
    location VARCHAR
  }
  
  entity customer_contacts {
    id SERIAL <<PK>>
    customer_id VARCHAR <<FK>>
    is_primary_contact BOOLEAN
    contact_name VARCHAR
    contact_role VARCHAR
    contact_phone VARCHAR
    contact_email VARCHAR
  }
  
  entity customer_sales_data {
    id SERIAL <<PK>>
    customer_id VARCHAR <<FK>>
    sales_organization VARCHAR
    account_manager_name VARCHAR
    trading_currency VARCHAR
  }
  
  entity quotations {
    id SERIAL <<PK>>
    quotation_number VARCHAR <<UK>>
    customer_id VARCHAR <<FK>>
    product_number VARCHAR
    quantity NUMERIC
    unit_price NUMERIC
    status ENUM
    sales_approver VARCHAR
    engineer_approver VARCHAR
    account_manager_approver VARCHAR
    customer_confirmed BOOLEAN
  }
  
  entity quotation_items {
    id SERIAL <<PK>>
    quotation_number VARCHAR <<FK>>
    line_number INTEGER
    material_code VARCHAR
    quantity NUMERIC
    unit_price NUMERIC
  }
  
  entity sales_orders {
    id SERIAL <<PK>>
    order_number VARCHAR <<UK>>
    quotation_number VARCHAR <<FK>>
    customer_id VARCHAR <<FK>>
    material_code VARCHAR <<FK>>
    production_version_id VARCHAR <<FK>>
    quantity NUMERIC
    status ENUM
    is_return_order BOOLEAN
  }
  
  entity contract_reviews {
    id SERIAL <<PK>>
    sales_order_number VARCHAR <<FK>>
    review_node VARCHAR
    reviewer_role VARCHAR
    review_result VARCHAR
  }
  
  entity factory_product_mappings {
    id SERIAL <<PK>>
    customer_id VARCHAR <<FK>>
    factory_product_number VARCHAR
    material_code VARCHAR <<FK>>
    production_version_id VARCHAR <<FK>>
  }
}

' 关系定义
customers ||--o{ customer_addresses : has
customers ||--o{ customer_contacts : has
customers ||--|| customer_sales_data : has
customers ||--o{ quotations : places
customers ||--o{ sales_orders : orders
customers ||--o{ factory_product_mappings : has
quotations ||--o{ quotation_items : contains
quotations ||--o{ sales_orders : converts_to
sales_orders ||--o{ contract_reviews : has

@enduml
```

#### ENG子系统（工程管理）关系图

```plantuml
@startuml ENG子系统ER图
skinparam linetype ortho

title ENG子系统（工程管理）ER图

package "ENG子系统" {
  entity materials {
    id SERIAL <<PK>>
    material_code VARCHAR <<UK>>
    material_name VARCHAR
    material_type VARCHAR
    category VARCHAR
    layer_count INTEGER
    board_thickness NUMERIC
    copper_weight NUMERIC
    surface_finish VARCHAR
  }
  
  entity boms {
    id SERIAL <<PK>>
    bom_number VARCHAR <<UK>>
    parent_material_code VARCHAR <<FK>>
    version VARCHAR
    status ENUM
    effective_date DATE
  }
  
  entity bom_items {
    id SERIAL <<PK>>
    bom_number VARCHAR <<FK>>
    material_code VARCHAR <<FK>>
    line_number INTEGER
    quantity NUMERIC
    unit VARCHAR
  }
  
  entity routings {
    id SERIAL <<PK>>
    routing_id VARCHAR <<UK>>
    material_code VARCHAR <<FK>>
    version VARCHAR
    status ENUM
    effective_date DATE
  }
  
  entity routing_operations {
    id SERIAL <<PK>>
    routing_id VARCHAR <<FK>>
    operation_no VARCHAR
    operation_name VARCHAR
    work_center_id VARCHAR <<FK>>
    setup_time NUMERIC
    machine_time NUMERIC
    labor_time NUMERIC
    queue_time NUMERIC
  }
  
  entity mi {
    id SERIAL <<PK>>
    mi_number VARCHAR <<UK>>
    material_code VARCHAR <<FK>>
    version VARCHAR
    status ENUM
    content TEXT
    effective_date DATE
  }
  
  entity production_versions {
    id SERIAL <<PK>>
    production_version_id VARCHAR <<UK>>
    material_code VARCHAR <<FK>>
    bom_number VARCHAR <<FK>>
    routing_id VARCHAR <<FK>>
    mi_number VARCHAR <<FK>>
    version VARCHAR
    status VARCHAR
  }
  
  entity factory_product_mappings {
    id SERIAL <<PK>>
    customer_id VARCHAR <<FK>>
    factory_product_number VARCHAR
    material_code VARCHAR <<FK>>
    production_version_id VARCHAR <<FK>>
  }
}

' 关系定义
materials ||--o{ boms : has
boms ||--o{ bom_items : contains
materials ||--o{ bom_items : used_in
materials ||--o{ routings : has
routings ||--o{ routing_operations : contains
materials ||--o{ mi : has
materials ||--o{ production_versions : has
boms ||--o{ production_versions : used_in
routings ||--o{ production_versions : used_in
mi ||--o{ production_versions : used_in
materials ||--o{ factory_product_mappings : mapped_by

note right of materials
  产品主数据（material_type='FG'）
  物料主数据（material_type='RAW','SEMI'等）
end note

note right of production_versions
  生产版本
  将BOM、工艺路线和MI组合
  发布时需要MI已关联且状态为RELEASED
end note

@enduml
```

#### PP子系统（生产计划与控制）关系图

```plantuml
@startuml PP子系统ER图
skinparam linetype ortho

title PP子系统（生产计划与控制）ER图

package "PP子系统" {
  entity work_centers {
    id SERIAL <<PK>>
    work_center_id VARCHAR <<UK>>
    description VARCHAR
    work_center_type VARCHAR
    status ENUM
    parent_work_center_id VARCHAR <<FK>>
    hierarchy_level INTEGER
    queue_time NUMERIC
    wait_time NUMERIC
    move_time NUMERIC
    capacity_category VARCHAR
  }
  
  entity production_orders {
    id SERIAL <<PK>>
    order_number VARCHAR <<UK>>
    sales_order_number VARCHAR <<FK>>
    material_code VARCHAR <<FK>>
    production_version_id VARCHAR <<FK>>
    quantity NUMERIC
    status ENUM
    lot_number VARCHAR
    planned_start_date DATE
    actual_start_date DATE
    actual_finish_date DATE
  }
  
  entity lot_cards {
    id SERIAL <<PK>>
    lot_number VARCHAR <<UK>>
    production_order_number VARCHAR <<FK>>
    mi_number VARCHAR <<FK>>
    material_code VARCHAR <<FK>>
    quantity NUMERIC
    status VARCHAR
    mi_content TEXT
  }
  
  entity operation_reports {
    id SERIAL <<PK>>
    report_number VARCHAR <<UK>>
    production_order_number VARCHAR <<FK>>
    lot_number VARCHAR <<FK>>
    work_center_id VARCHAR <<FK>>
    operation_no VARCHAR
    reported_quantity NUMERIC
    good_quantity NUMERIC
    defective_quantity NUMERIC
    actual_hours NUMERIC
    report_date TIMESTAMP
  }
}

' 关系定义
work_centers ||--o{ work_centers : parent
work_centers ||--o{ operation_reports : reports_to
production_orders ||--o| lot_cards : "关联(1:1)"
production_orders ||--o{ operation_reports : generates
lot_cards ||--o{ operation_reports : "关联"

note right of production_orders
  生产订单/工单
  在实现中同时承担"生产订单"和"工单"的职责
  如果关联了MI，自动生成LOT卡（1:1关系）
end note

note right of lot_cards
  LOT卡（生产批次卡）
  一个生产订单/工单对应一个LOT卡（1:1关系）
  由MI自动生成，是工序报工的批次依据
end note

@enduml
```

#### MM子系统（物料管理）关系图

```plantuml
@startuml MM子系统ER图
skinparam linetype ortho

title MM子系统（物料管理）ER图

package "MM子系统" {
  entity materials {
    id SERIAL <<PK>>
    material_code VARCHAR <<UK>>
    material_name VARCHAR
    material_type VARCHAR
    category VARCHAR
    current_stock NUMERIC
    safety_stock NUMERIC
  }
  
  entity material_transactions {
    id SERIAL <<PK>>
    transaction_number VARCHAR <<UK>>
    material_code VARCHAR <<FK>>
    transaction_type VARCHAR
    quantity NUMERIC
    reference_number VARCHAR
    transaction_date TIMESTAMP
  }
  
  entity material_issues {
    id SERIAL <<PK>>
    issue_number VARCHAR <<UK>>
    production_order_number VARCHAR <<FK>>
    material_code VARCHAR <<FK>>
    quantity NUMERIC
    unit VARCHAR
    issued_at TIMESTAMP
  }
}

' 关系定义
materials ||--o{ material_transactions : transacted
materials ||--o{ material_issues : issued
material_issues ..> material_transactions : creates

note right of materials
  物料主数据
  不显示FG类型（FG类型在产品主数据管理中显示）
  包含库存信息
end note

note right of material_issues
  生产领料（领料单）
  系统根据生产订单/工单关联的BOM自动生成领料需求
  领料后自动更新物料库存
end note

@enduml
```

#### 跨子系统关系图

```plantuml
@startuml 跨子系统ER关系图
skinparam linetype ortho

title 某某ERP系统 - 跨子系统ER关系图

package "SD子系统" {
  entity customers
  entity quotations
  entity sales_orders
}

package "ENG子系统" {
  entity materials
  entity boms
  entity routings
  entity mi
  entity production_versions
}

package "PP子系统" {
  entity work_centers
  entity production_orders
  entity lot_cards
  entity operation_reports
}

package "MM子系统" {
  entity material_issues
  entity material_transactions
}

' 跨子系统关系
customers ||--o{ quotations : "创建"
quotations ||--o{ sales_orders : "转为"
sales_orders ||--o{ production_orders : "创建"
materials ||--o{ sales_orders : "引用"
production_versions ||--o{ sales_orders : "使用"
production_versions ||--o{ production_orders : "使用"
mi ||--o{ lot_cards : "生成"
production_orders ||--o| lot_cards : "关联(1:1)"
production_orders ||--o{ material_issues : "生成"
production_orders ||--o{ operation_reports : "产生"
lot_cards ||--o{ operation_reports : "关联"
work_centers ||--o{ operation_reports : "报工到"
boms ||--o{ production_versions : "组成"
routings ||--o{ production_versions : "组成"
mi ||--o{ production_versions : "组成"

note right of sales_orders
  销售订单
  引用产品主数据（materials）
  引用生产版本（production_versions）
  创建生产订单（production_orders）
end note

note right of production_orders
  生产订单/工单
  基于销售订单创建
  使用生产版本（BOM+工艺路线+MI）
  如果关联MI，自动生成LOT卡（1:1关系）
end note

@enduml
```

## 三、用例

### SD子系统（销售与分销）

#### 用例列表

用例|功能说明
-|-
客户建档|创建新客户主数据，包含客户基本信息、多个合作属性、多个地址信息、多个联系人信息、销售数据等
客户信息修改|修改已存在的客户主数据信息
维护地址信息|为客户添加或修改地址信息
维护联系人信息|为客户添加或修改联系人信息，包括联系人姓名、角色、部门、电话、邮箱等
报价单创建|创建销售报价单，包含客户信息、产品信息（本厂编号、产品名称）、价格条款等。创建报价单时，如果输入的14位本厂编号不存在对应的产品主数据，SD子系统调用ENG子系统的产品主数据创建API自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品）。自动创建的产品主数据不需要审核。产品主数据由工程管理子系统统一管理
报价单预估报价|根据板规格参数、工艺参数、加价选项等计算报价明细成本，包括交货面积、成本/平米、成本PCS、报价价格、工程费、板材费、测试架费用等，并生成工序成本明细。采用手动计算模式（点击"计算报价"按钮）
报价单审核|三级审核流程（串行）：一级审核（销售经理SALES_MANAGER）、二级审核（工程师ENGINEER）、三级审核（客户经理ACCOUNT_MANAGER或总经理GENERAL_MANAGER）
报价转订单|将已通过审核并获客户确认的报价单转为销售订单
返单快速下单|老客户重复下单，系统自动识别并匹配历史订单信息，快速创建销售订单
销售订单管理|查看、编辑、审核销售订单
订单评审|对销售订单进行评审，确认价格、交期等条款

#### 用例图

```plantuml
@startuml SD子系统用例图

title SD子系统（销售与分销）用例图

left to right direction

actor 销售员 as sales
actor 销售经理 as salesManager
actor 客户经理 as accountManager
actor 系统 as system

rectangle SD子系统 {
  
  package "客户管理" {
    usecase "客户建档" as UC1
    usecase "客户信息修改" as UC2
    usecase "维护地址信息" as UC3
    usecase "维护联系人信息" as UC3A
    usecase "查看客户档案" as UC4
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
sales --> UC3 : 维护地址信息
sales --> UC3A : 维护联系人信息
sales --> UC4 : 查看客户档案
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

' 工程师用例
actor 工程师 as engineer
engineer --> UC14 : 二级审核

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
UC13 ..> UC14 : <<include>>
UC14 ..> UC15 : <<include>>
UC9 ..> UC12 : <<include>>
UC10 ..> UC11 : <<include>>
UC7 ..> UC8 : <<include>>

note right of UC1
  创建客户主数据
  包含基本信息、合作属性、
  地址、联系人、销售数据
end note

note right of UC3A
  维护联系人信息
  包括联系人姓名、角色、部门、
  电话、邮箱等信息
  支持设置主联系人
end note

note right of UC5
  创建报价单
  包含客户、产品（本厂编号、产品名称）、
  价格、交付条款等信息
  如果本厂编号对应的产品主数据不存在，SD子系统调用ENG子系统API自动创建产品主数据
end note

note right of UC5A
  报价单预估报价
  根据板规格参数、工艺参数、加价选项
  手动计算报价明细成本
  包括交货面积、成本/平米、报价价格、
  工程费、板材费、工序成本明细等
  采用手动计算模式（点击"计算报价"按钮）
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

### ENG子系统（工程管理）

#### 用例列表

用例|功能说明
-|-
产品主数据管理|创建和维护产品主数据，以本厂编号作为唯一标识，本厂编号同时作为产品编码。产品主数据管理只显示成品(FG类型)的物料。新建产品主数据时，如果本厂编号对应的产品不存在，系统提供创建产品的快捷入口。产品主数据由工程管理子系统统一管理，SD子系统可以创建（自动创建）、查询、引用产品主数据，但不能修改、删除产品主数据（需ENG子系统操作）。ENG子系统拥有产品主数据的完整CRUD权限
产品列表查询|查询产品主数据列表，支持按本厂编号、产品名称、产品系列等条件筛选和分页
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
@startuml ENG子系统用例图

title ENG子系统（工程管理）用例图

left to right direction

actor 工程师 as engineer
actor 审核员 as reviewer
actor 系统 as system

rectangle ENG子系统 {
  
  package "产品管理" {
    usecase "产品主数据管理" as UC0
    usecase "产品列表查询" as UC0A
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
engineer --> UC0A : 查询产品
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
  管理产品主数据（工程管理子系统）
  以本厂编号为唯一标识
  本厂编号同时作为产品编码
  只显示成品(FG类型)的物料
  如果本厂编号对应的产品主数据不存在，系统提供创建产品的快捷入口
  其他模块（SD、MM）可以引用和自动创建
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

### PP子系统（生产计划与控制）

#### 用例列表

用例|功能说明
-|-
工作中心管理|创建和维护工作中心主数据，包含基本信息、产能数据、成本数据等
工作中心激活|激活工作中心，使其可用于生产
工作中心停用|停用工作中心
工序报工|记录工序完成情况，包含完成数量、良品数量、不良品数量、工时等
LOT卡管理|LOT卡的全生命周期管理，包括自动生成、查询、详情查看、编辑、状态管理等
LOT卡生成|创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡，自动复制MI内容并写回lot_number到生产订单。如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI
LOT卡查询|查询LOT卡信息，支持按生产订单号、MI编号、状态等条件查询
LOT卡列表|查看LOT卡列表，支持按生产订单号、MI编号、状态等条件筛选和分页
LOT卡详情查看|查看LOT卡的详细信息，包括MI内容、生产信息、关联的报工记录等
LOT卡编辑|编辑LOT卡的MI内容（mi_content）和备注（remarks），支持JSON格式解析为列表，每一条指令/属性项可单独编辑
不良品管理|记录不良品信息，包含不良原因、处理方式等
生产订单关闭|关闭已完成的生产订单
生产进度查看|查看生产订单的执行进度

#### 用例图

```plantuml
@startuml PP子系统用例图

title PP子系统（生产计划与控制）用例图

left to right direction

actor 计划员 as planner
actor 产线工人 as worker
actor 生产主管 as supervisor
actor 系统 as system

rectangle PP子系统 {
  
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

### MM子系统（物料管理）

#### 用例列表

用例|功能说明
-|-
物料主数据管理|创建和维护物料主数据，包含物料编码、名称、分类（原材料、辅材、化工材料、半成品、维修等）、规格、库存信息等。物料主数据管理中不显示成品(FG类型)，成品通过工程管理子系统的产品主数据管理进行维护
物料列表查询|查询物料列表，支持条件过滤
生产领料|根据生产订单/工单创建领料单，包含领料明细、库存信息等
库存查询|查询物料当前库存、安全库存等信息
缺料单生成|当库存不足时，生成缺料单

#### 用例图

```plantuml
@startuml MM子系统用例图

title MM子系统（物料管理）用例图

left to right direction

actor 物控员 as materialController
actor 仓库管理员 as warehouseKeeper
actor 系统 as system

rectangle MM子系统 {
  
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

note right of UC1
  管理物料主数据
  包含编码、名称、分类
  （原材料、辅材、半成品、维修等）、
  规格、库存等信息
  不包含成品（FG类型）
  成品通过工程管理子系统的产品主数据管理
end note

note right of UC4
  根据生产订单/工单创建领料单
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

销售报价流程是销售业务的起点，从客户询价开始，经过报价单创建、报价计算、三级审核、销售员经客户确认报价单等环节，最终可以转为销售订单。流程包括：

1. **报价单创建**：销售员根据客户需求创建报价单，填写客户信息、产品信息（本厂编号、产品名称）、价格条款等。如果输入的14位本厂编号不存在对应的产品主数据，SD子系统调用ENG子系统的产品主数据创建API自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），并自动填充产品名称。自动创建的产品主数据不需要审核。产品主数据由工程管理子系统统一管理，销售子系统可以引用和自动创建
2. **报价单预估报价**：销售员填写板规格参数（出货长、出货宽、利用率、PNL参数等）、工艺参数（层数、板厚、铜厚、线宽线距、表面处理等）、加价选项（常规加价、特殊加价、额外加价等）后，点击"计算报价"按钮手动计算报价明细成本。计算内容包括：
   - **交货面积计算**：根据出货长、出货宽、订单数量计算交货面积（m²）
   - **基础成本计算**：根据基础成本基准值和层数调整系数计算成本/平米
   - **加价计算**：根据常规加价、特殊加价、额外加价选项计算总加价/平米
   - **最终成本计算**：基础成本 + 加价，得到最终成本/平米和成本PCS
   - **报价价格计算**：在成本基础上按利润率系数（如1.3，即30%利润）计算报价价格/平米和报价价格PCS
   - **费用计算**：计算工程费（根据层数）、板材费（成本×面积）、测试架费用（根据测试点数）、其他费用（最低消费等）
   - **最终总价计算**：工程费 + 板材费 + 测试架费用 + 其他费用
   - **工序成本分摊**：将成本按比例分摊到各工序（开料、钻孔、电镀、线路、阻焊、表面处理、成型等），生成工序成本明细
   - 系统采用手动计算模式（点击"计算报价"按钮）
   - 计算结果保存到报价单主表和报价明细工序表
3. **一级审核**：销售经理（SALES_MANAGER）进行一级审核，检查报价单的基本信息和价格合理性。审核不通过时，报价单退回草稿状态，销售员可修改后重新提交。退回操作记录审核历史，保存退回原因
4. **二级审核**：工程师（ENGINEER）进行二级审核，确认价格策略和交期承诺。审核不通过时，报价单退回草稿状态，销售员可修改后重新提交。退回操作记录审核历史，保存退回原因
5. **三级审核**：客户经理（ACCOUNT_MANAGER）或总经理（GENERAL_MANAGER）进行三级审核，最终确认报价单。审核不通过时，报价单退回草稿状态，销售员可修改后重新提交。退回操作记录审核历史，保存退回原因
6. **销售员经客户确认报价单**：销售员与客户确认报价单，客户确认是线下确认，销售员在系统中标记"客户已确认"。客户确认后可以转为销售订单。客户不确认时，报价单退回草稿状态，销售员可修改后重新提交审核。退回操作记录审核历史，保存退回原因
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

待三级审核 --> 销售员经客户确认报价单 : 三级审核通过

state 销售员经客户确认报价单 {
  销售员经客户确认报价单 : 销售员与客户沟通
  销售员经客户确认报价单 : 客户线下确认报价单
  销售员经客户确认报价单 : 销售员在系统中标记"客户已确认"
  销售员经客户确认报价单 : 可以转为销售订单
}

销售员经客户确认报价单 --> 草稿 : 客户不确认\n退回修改

销售员经客户确认报价单 --> 已转订单 : 客户确认\n转为销售订单
销售员经客户确认报价单 --> 已归档 : 客户不转单\n归档

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
  等待工程师（ENGINEER）审核
  确认价格策略
end note

note right of 待三级审核
  等待客户经理审核
  最终确认报价
end note

note right of 销售员经客户确认报价单
  销售员经客户确认报价单
  客户确认是线下确认
  销售员在系统中标记"客户已确认"
  客户确认后可以转为订单
  客户不确认时退回草稿状态
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
2. **产品主数据确认**：确认或创建产品主数据（本厂编号），如果输入的14位本厂编号不存在对应的产品主数据，SD子系统调用ENG子系统的产品主数据创建API自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），并自动填充产品名称。自动创建的产品主数据不需要审核。产品主数据由工程管理子系统统一管理
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
  如果本厂编号对应的产品主数据不存在，SD子系统调用ENG子系统API自动创建
  自动创建的产品主数据不需要审核
  产品主数据由工程管理子系统统一管理
end note

note right of 订单信息录入
  手动录入订单信息
  包括产品、数量、价格、交期等
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

1. **BOM创建**：创建新的BOM，指定父项产品（本厂编号）和版本信息。如果本厂编号对应的产品主数据不存在，系统提示用户创建。产品主数据由工程管理子系统创建，以本厂编号作为唯一标识
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

state 新建BOM {
  新建BOM : 输入BOM编号
  新建BOM : 选择父项产品（本厂编号）
  新建BOM : 设置版本信息
  新建BOM : 产品主数据创建（工程管理子系统）
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
待审核 --> 草稿 : 审核不通过\n退回修改\n记录审核历史，保存退回原因

state 已发布 {
  已发布 : BOM可用
  已发布 : 可用于生产
  已发布 : 可创建新版本
}

已发布 --> 新建BOM : 创建新版本
已发布 --> [*] : 流程结束

note right of 新建BOM
  创建新的BOM
  指定父项产品（本厂编号）
  产品主数据由工程管理子系统创建
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

1. **工艺路线创建**：创建新的工艺路线，指定父项产品（本厂编号）和版本信息。如果本厂编号对应的产品主数据不存在，系统提示用户创建。产品主数据由工程管理子系统创建，以本厂编号作为唯一标识
2. **添加工序**：在工艺路线中添加工序，设置工序序列、工作中心、标准时间等信息
3. **工艺路线保存**：保存工艺路线，可以保存为草稿或直接发布
4. **工艺路线审核**：对工艺路线进行审核，确认工艺流程的准确性
5. **工艺路线发布**：发布工艺路线，使其可用于生产
6. **版本管理**：可以基于现有工艺路线创建新版本

#### 流程图

```plantuml
@startuml 工艺路线创建流程状态图

title 工艺路线创建流程状态图

[*] --> 新建工艺路线 : 创建工艺路线

state 新建工艺路线 {
  新建工艺路线 : 输入工艺路线编号
  新建工艺路线 : 选择父项产品（本厂编号）
  新建工艺路线 : 设置版本信息
  新建工艺路线 : 产品主数据创建（工程管理子系统）
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
待审核 --> 草稿 : 审核不通过\n退回修改\n记录审核历史，保存退回原因

state 已发布 {
  已发布 : 工艺路线可用
  已发布 : 可用于生产
  已发布 : 可创建新版本
}

已发布 --> 新建工艺路线 : 创建新版本
已发布 --> [*] : 流程结束

note right of 新建工艺路线
  创建新的工艺路线
  指定父项产品（本厂编号）
  产品主数据由工程管理子系统创建
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

生产领料流程用于处理生产订单/工单的物料发放，包括创建领料单、库存检查、物料发放、审核确认等环节。流程包括：

1. **创建领料单**：根据生产订单/工单自动生成领料需求，创建领料单
2. **库存检查**：系统自动检查物料库存，显示当前库存和安全库存
3. **库存预警**：当库存低于安全库存时，系统自动预警
4. **物料发放**：仓库管理员根据领料单发放物料，记录实际发放数量
5. **领料审核**：对领料单进行审核确认

#### 流程图

```plantuml
@startuml 生产领料流程状态图

title 生产领料流程状态图

[*] --> 创建领料单 : 生产订单/工单下达

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

库存检查 --> 物料发放 : 开始发放

state 物料发放 {
  物料发放 : 记录实际发放数量
  物料发放 : 更新库存
  物料发放 : 记录库位信息
}

物料发放 --> 领料审核 : 发放完成

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
  根据生产订单/工单
  自动生成领料需求
end note

note right of 库存检查
  自动检查库存
  显示库存信息
end note

note right of 物料发放
  记录实际发放
  更新库存信息
end note

@enduml
```

### 工序报工流程

#### 流程说明

工序报工流程用于记录生产工序的完成情况，包括报工数据录入、不良品管理、工时记录等环节。流程包括：

1. **选择生产订单/工单并自动读取LOT卡**：选择要报工的生产订单/工单后，系统根据生产订单号自动查询关联的LOT卡（一个生产订单/工单对应一个LOT卡，1:1关系），并自动填充报工单中的LOT卡号字段（只读、不可修改）；如找不到LOT卡，则不允许保存报工
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
2. **产品主数据确认**：确认或创建产品主数据，以本厂编号作为唯一标识。如果本厂编号对应的产品主数据不存在，系统提示用户创建。产品主数据由工程管理子系统统一管理
3. **BOM和工艺路线准备**：准备产品的BOM和工艺路线（基于产品主数据的本厂编号）。BOM和工艺路线准备可以并行进行，无依赖关系
4. **生产版本建立**：将BOM和工艺路线组合，建立生产版本。生产版本建立必须等待BOM和工艺路线都准备好。如果任一准备失败，生产版本建立失败，提示用户
5. **MI制作**：根据订单创建制造指令，包含技术参数和生产要求。MI制作需要生产版本已建立
6. **生产版本发布**：发布生产版本，使其可用于生产订单下达。生产版本发布需要MI已制作且MI审核通过
7. **生产订单下达**：下达生产订单/工单，如果关联了MI，系统根据MI自动生成LOT卡，LOT卡包含MI内容和生产信息，并将lot_number写回生产订单。如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI。由于生产订单承担工单职责，工单状态与生产订单状态一致
8. **物料领料**：根据生产订单/工单领料
9. **工序报工**：各工序完成后进行报工，系统根据生产订单/工单自动读取LOT卡号并填充到报工单中，LOT卡号不可修改
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
}

MI制作 --> 生产版本发布 : MI审核通过

state 生产版本发布 {
  生产版本发布 : 发布生产版本
  生产版本发布 : 使其可用于生产订单下达
}

生产版本发布 --> 生产订单下达 : 生产版本已发布

state 生产订单下达 {
  生产订单下达 : 下达生产订单/工单
  生产订单下达 : 如果关联了MI，自动生成LOT卡
  生产订单下达 : 分配工作中心
  生产订单下达 : 工单状态与生产订单状态一致
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
  产品主数据由工程管理子系统统一管理
  产品类型为成品(FG)
  支持自动创建（如需要）
end note

note right of MI制作
  创建制造指令
  包含技术参数
  MI制作需要生产版本已建立
end note

note right of 生产版本建立
  组合BOM和工艺路线
  建立生产版本
  必须等待BOM和工艺路线都准备好
  如果任一准备失败，生产版本建立失败
end note

note right of 生产版本发布
  发布生产版本
  需要MI已制作且MI审核通过
  使其可用于生产订单下达
end note

note right of 生产订单下达
  在MI审核通过
  生产版本发布后
  下达生产订单/工单
  如果关联了MI，自动生成LOT卡
  如果MI不存在，不允许创建或提示用户先创建MI
  工单状态与生产订单状态一致
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

### 生产订单/工单状态转换

#### 状态说明

生产订单/工单的状态流转规则如下：

1. **DRAFT（草稿）**：生产订单/工单初始状态，已创建但未下达
2. **RELEASED（已下达）**：生产订单/工单已下达，可以开始生产
3. **IN_PRODUCTION（生产中）**：生产订单/工单已开始生产，正在进行工序执行
4. **COMPLETED（已完成）**：生产订单/工单的所有工序已完成
5. **CLOSED（已关闭）**：生产订单/工单已关闭，流程结束
6. **CANCELLED（已取消）**：生产订单/工单已取消，流程终止

由于生产订单承担工单职责，工单状态与生产订单状态一致。

#### 状态转换规则

生产订单/工单的状态转换遵循以下规则：

- **DRAFT → RELEASED**：下达生产订单/工单（通过"下达生产订单"操作）
- **DRAFT → CANCELLED**：取消生产订单/工单
- **RELEASED → IN_PRODUCTION**：开始生产（通过"开始生产"操作）
- **RELEASED → CANCELLED**：取消生产订单/工单
- **RELEASED → CLOSED**：关闭生产订单/工单（特殊情况，通过"关闭生产订单"操作）
- **IN_PRODUCTION → COMPLETED**：完成生产订单/工单（通过"完成生产订单"操作）
- **IN_PRODUCTION → CANCELLED**：取消生产订单/工单
- **IN_PRODUCTION → CLOSED**：关闭生产订单/工单（特殊情况，通过"关闭生产订单"操作）
- **COMPLETED → CLOSED**：关闭生产订单/工单（通过"关闭生产订单"操作）
- **CLOSED**：终态，不允许再流转
- **CANCELLED**：终态，不允许再流转

#### 状态机图

```plantuml
@startuml 生产订单状态转换状态机图

title 生产订单/工单状态转换状态机图

[*] --> DRAFT : 创建生产订单/工单

state DRAFT {
  DRAFT : 草稿状态
  DRAFT : 已创建但未下达
  DRAFT : 可编辑、可删除
}

DRAFT --> RELEASED : 下达生产订单\n（release_production_order）
DRAFT --> CANCELLED : 取消生产订单/工单

state RELEASED {
  RELEASED : 已下达状态
  RELEASED : 生产订单/工单已下达
  RELEASED : 可以开始生产
  RELEASED : 可以关闭（特殊情况）
}

RELEASED --> IN_PRODUCTION : 开始生产\n（start_production_order）
RELEASED --> CANCELLED : 取消生产订单/工单
RELEASED --> CLOSED : 关闭生产订单/工单\n（close_production_order）

state IN_PRODUCTION {
  IN_PRODUCTION : 生产中状态
  IN_PRODUCTION : 正在进行工序执行
  IN_PRODUCTION : 可以进行工序报工
  IN_PRODUCTION : 可以关闭（特殊情况）
}

IN_PRODUCTION --> COMPLETED : 完成生产订单/工单\n（complete_production_order）
IN_PRODUCTION --> CANCELLED : 取消生产订单/工单
IN_PRODUCTION --> CLOSED : 关闭生产订单/工单\n（close_production_order）

state COMPLETED {
  COMPLETED : 已完成状态
  COMPLETED : 所有工序已完成
  COMPLETED : 等待关闭
}

COMPLETED --> CLOSED : 关闭生产订单/工单\n（close_production_order）

state CLOSED {
  CLOSED : 已关闭状态
  CLOSED : 流程结束
  CLOSED : 终态，不允许再流转
}

CLOSED --> [*] : 流程结束

state CANCELLED {
  CANCELLED : 已取消状态
  CANCELLED : 流程终止
  CANCELLED : 终态，不允许再流转
}

CANCELLED --> [*] : 流程终止

note right of DRAFT
  生产订单/工单初始状态
  可编辑、可删除
  必须从DRAFT状态才能下达
end note

note right of RELEASED
  生产订单/工单已下达
  可以开始生产
  可以关闭（特殊情况）
  如果关联了MI，自动生成LOT卡
end note

note right of IN_PRODUCTION
  生产订单/工单生产中
  可以进行工序报工
  系统根据生产订单/工单
  自动读取LOT卡号
end note

note right of COMPLETED
  生产订单/工单已完成
  所有工序已完成
  等待关闭
end note

note right of CLOSED
  生产订单/工单已关闭
  流程结束
  终态，不允许再流转
end note

note right of CANCELLED
  生产订单/工单已取消
  流程终止
  终态，不允许再流转
end note

@enduml
```

#### 状态转换触发操作

1. **下达生产订单/工单**（DRAFT → RELEASED）
   - 操作：调用"下达生产订单"接口
   - 前置条件：生产订单状态必须为DRAFT
   - 后置条件：状态更新为RELEASED，如果关联了MI，自动生成LOT卡

2. **开始生产**（RELEASED → IN_PRODUCTION）
   - 操作：调用"开始生产"接口
   - 前置条件：生产订单状态必须为RELEASED
   - 后置条件：状态更新为IN_PRODUCTION，记录实际开始时间

3. **完成生产订单/工单**（IN_PRODUCTION → COMPLETED）
   - 操作：调用"完成生产订单"接口
   - 前置条件：生产订单状态必须为IN_PRODUCTION
   - 后置条件：状态更新为COMPLETED，记录实际完成时间

4. **关闭生产订单/工单**（RELEASED/IN_PRODUCTION/COMPLETED → CLOSED）
   - 操作：调用"关闭生产订单"接口
   - 前置条件：生产订单状态必须为RELEASED、IN_PRODUCTION或COMPLETED
   - 后置条件：状态更新为CLOSED，记录实际完成时间，同步销售订单状态

5. **取消生产订单/工单**（DRAFT/RELEASED/IN_PRODUCTION → CANCELLED）
   - 操作：取消生产订单/工单
   - 前置条件：生产订单状态必须为DRAFT、RELEASED或IN_PRODUCTION
   - 后置条件：状态更新为CANCELLED，流程终止

#### 状态转换限制

- **CLOSED**和**CANCELLED**为终态，不允许再流转
- 状态转换必须遵循状态机图定义的转换规则，不允许跨状态转换
- 状态转换时会进行验证，不符合规则的状态转换将被拒绝

#### 与销售订单状态的同步

生产订单/工单的状态会影响关联的销售订单状态：

- 当有生产订单/工单状态变为IN_PRODUCTION时，销售订单状态自动更新为IN_PRODUCTION
- 当所有生产订单/工单状态为COMPLETED或CLOSED时，销售订单状态自动更新为COMPLETED
