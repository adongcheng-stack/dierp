# ENG模块 - MI管理子模块领域模型

**对应菜单：** `/eng/mis`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

MI管理子模块负责管理制造指令（Manufacturing Instruction），包含详细的工艺参数和操作指导。MI可以基于工艺路线自动生成草稿，需要经过审核和发布流程。

---

## 二、核心实体

### 2.1 MI（制造指令）

- **表：** `mis`
- **主键：** `id`（BaseModel），业务键：`mi_number`
- **状态枚举：** `MIStatus`（DRAFT, REVIEWING, APPROVED, RELEASED, OBSOLETE）
- **关键字段：**
  - `mi_number`：MI编号（唯一）
  - `version`：版本号
  - `material_code`：物料编码（外键 → materials.material_code）
  - `description`：描述
  - `status`：状态
  - `effective_date`：生效日期
  - `expiry_date`：失效日期
  - `content`：MI内容（JSON格式，含工艺参数与指令集列表）
- **关联：**
  - N:1 `Material`（物料）
  - 1:N `ProductionVersion`（生产版本）
  - 1:N `LotCard`（LOT卡，通过production_order关联）
- **说明：**
  - MI内容以JSON格式存储，包含指令集列表和描述
  - MI可以基于工艺路线自动生成草稿
  - 工程师可以添加MI指令集列表和描述，调整指令集顺序（使用上下箭头）
  - 可在DRAFT或REVIEWING状态下更新
  - 发布时需要MI已制作且已审核通过
  - 发布后的修改需走变更/新版本流程

---

## 三、状态机

### 3.1 MI状态

- **DRAFT**：草稿，MI创建但未提交
- **REVIEWING**：审核中，正在审核
- **APPROVED**：已审批，审核通过
- **RELEASED**：已发布，已发布，可用于生产
- **OBSOLETE**：已废弃，已废弃，不再使用

### 3.2 状态转换规则

- DRAFT → REVIEWING：提交审核（工程师）
- REVIEWING → APPROVED：审核通过（工程师）
- REVIEWING → DRAFT：审核拒绝（工程师）
- APPROVED → RELEASED：发布（工程师）
- * → OBSOLETE：废弃（工程师）

---

## 四、业务规则

1. **MI编号唯一性**：MI编号（mi_number）必须在系统中唯一。
2. **物料存在性**：物料（material_code）必须存在。
3. **内容格式**：MI内容以JSON格式存储，包含指令集列表和描述。
4. **自动生成**：MI可以基于工艺路线自动生成草稿，预填指令集列表。
5. **编辑功能**：工程师可以添加MI指令集列表和描述，调整指令集顺序（使用上下箭头）。
6. **更新限制**：可在DRAFT或REVIEWING状态下更新，发布后的修改需走变更/新版本流程。
7. **发布要求**：发布时需要MI已制作且已审核通过。发布后的MI可用于生产版本发布和生产订单/工单下达。
8. **审核流程**：MI必须经过审批流程：DRAFT → REVIEWING → APPROVED → RELEASED。

---

## 五、聚合根

**MI聚合根**：MI

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-ENG-009, UC-ENG-010, UC-ENG-011, UC-ENG-012, UC-ENG-013
- [用户故事文档](../用户故事/ENG-MI管理用户故事.md)
- [状态机文档](../状态机图/ENG-MI管理状态机.puml)
