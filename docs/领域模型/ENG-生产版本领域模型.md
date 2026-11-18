# ENG模块 - 生产版本子模块领域模型

**对应菜单：** `/eng/production-versions`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

生产版本子模块负责将BOM、工艺路线和MI组合成可执行的生产版本。生产版本建立必须等待BOM和工艺路线都准备好，MI在创建时是可选的，但在发布时是必选的。

---

## 二、核心实体

### 2.1 ProductionVersion（生产版本）

- **表：** `production_versions`
- **主键：** `id`（BaseModel），业务键：`production_version_id`
- **状态：** `status`（ACTIVE, RELEASED）
- **关键字段：**
  - `production_version_id`：生产版本ID（唯一）
  - `material_code`：物料编码（外键 → materials.material_code）
  - `bom_number`：BOM编号（外键 → boms.bom_number，必选）
  - `routing_id`：工艺路线ID（外键 → routings.routing_id，必选）
  - `mi_number`：MI编号（外键 → mis.mi_number，可选，但发布时必选）
  - `version`：版本号
  - `effective_date`：生效日期
  - `expiry_date`：失效日期
  - `status`：状态（ACTIVE/RELEASED）
  - `description`：描述
- **关联：**
  - N:1 `Material`（物料）
  - N:1 `BOM`（BOM）
  - N:1 `Routing`（工艺路线）
  - N:1 `MI`（制造指令，可选）
  - 1:N `ProductionOrder`（生产订单）
- **说明：**
  - 生产版本将BOM和工艺路线组合
  - BOM和工艺路线准备可以并行进行，无依赖关系
  - BOM和工艺路线是必选的
  - MI在创建时是可选的，但在发布生产版本时是必选的
  - 只有RELEASED状态的BOM和工艺路线才能用于生产版本
  - 发布时需要MI已关联且状态为RELEASED
  - 若需替换BOM/工艺路线/MI，应通过创建新生产版本处理

---

## 三、状态机

### 3.1 ProductionVersion状态

- **ACTIVE**：激活，生产版本已创建，处于激活状态
- **RELEASED**：已发布，生产版本已发布，可用于生产订单/工单下达

### 3.2 状态转换规则

- ACTIVE → RELEASED：发布生产版本（工程师）
  - 守卫条件：BOM和工艺路线为RELEASED，MI为RELEASED（发布时必选）

---

## 四、业务规则

1. **生产版本ID唯一性**：生产版本ID（production_version_id）必须在系统中唯一。
2. **BOM和工艺路线必选**：创建生产版本时，BOM和工艺路线是必选的。
3. **MI可选但发布时必选**：MI在创建时是可选的，但在发布生产版本时是必选的。
4. **状态要求**：只有RELEASED状态的BOM和工艺路线才能用于生产版本。
5. **发布要求**：
   - 发布时需要MI已关联且状态为RELEASED
   - 发布后的生产版本可用于生产订单/工单下达
6. **并行准备**：BOM和工艺路线准备可以并行进行，无依赖关系。
7. **建立失败处理**：生产版本建立必须等待BOM和工艺路线都准备好，如果任一准备失败，生产版本建立失败，提示用户。
8. **版本管理**：若需替换BOM/工艺路线/MI，应通过创建新生产版本处理。

---

## 五、聚合根

**ProductionVersion聚合根**：ProductionVersion（关联BOM、Routing、MI）

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-ENG-014, UC-ENG-015, UC-ENG-016
- [用户故事文档](../用户故事/ENG-生产版本用户故事.md)
- [状态机文档](../状态机图/ENG-生产版本状态机.puml)
