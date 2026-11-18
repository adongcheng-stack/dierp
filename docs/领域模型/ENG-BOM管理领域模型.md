# ENG模块 - BOM管理子模块领域模型

**对应菜单：** `/eng/boms`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

BOM管理子模块负责管理物料清单（Bill of Materials），定义产品的物料组成结构。BOM需要经过审核和发布流程，只有RELEASED状态的BOM才能用于生产版本。

---

## 二、核心实体

### 2.1 BOM（物料清单）

- **表：** `boms`
- **主键：** `id`（BaseModel），业务键：`bom_number`
- **状态枚举：** `BOMStatus`（NEW, REVIEWING, RELEASED, PRODUCING, OBSOLETE）
- **关键字段：**
  - `bom_number`：BOM编号（唯一）
  - `version`：版本号
  - `parent_material_code`：父物料编码（外键 → materials.material_code）
  - `plant_id`：工厂/生产地点
  - `bom_type`：BOM类型（PRODUCTION/ENGINEERING/COST）
  - `base_quantity`：基数（默认1）
  - `base_uom`：基础单位（默认PNL）
  - `effective_date`：生效日期
  - `expiry_date`：失效日期
  - `status`：状态
  - `description`：描述
- **关联：**
  - N:1 `Material`（父物料）
  - 1:N `BOMItem`（BOM明细）
  - 1:N `ProductionVersion`（生产版本）
- **说明：**
  - BOM的base_uom通常为PNL（拼板），用于PCB行业
  - 只有RELEASED状态的BOM才能用于生产版本
  - RELEASED状态的BOM需要创建新版本而非直接修改
  - 可在NEW或REVIEWING状态下更新

### 2.2 BOMItem（BOM明细）

- **表：** `bom_items`
- **关键字段：**
  - `bom_number`：BOM编号（外键）
  - `line_number`：行号
  - `material_code`：物料编码（外键 → materials.material_code）
  - `item_category`：明细类别（STOCK_ITEM/SUB_ASSEMBLY/CONSUMABLE等）
  - `quantity`：单机用量
  - `unit`：单位
  - `scrap_rate`：损耗率（%）
  - `calculation_formula`：计算公式标识
  - `layer_code`：PCB层码/位置
  - `material_type`：物料类型（COPPER_FOIL/PREPREG/CORE等）或工序步骤
  - `process_step`：后工序步骤（如SOLDER_MASK）
  - `remarks`：备注
- **说明：**
  - BOMItem可以包含层码、物料类型等PCB专用信息
  - 明细不能为空
  - 支持PCB行业特定的物料分类和属性

---

## 三、状态机

### 3.1 BOM状态

- **NEW**：新建，BOM刚创建
- **REVIEWING**：审核中，正在审核
- **RELEASED**：已发布，审核通过，已发布
- **PRODUCING**：生产中，正在被生产订单使用
- **OBSOLETE**：已废弃，已废弃，不再使用

### 3.2 状态转换规则

- NEW → REVIEWING：提交审核（工程师）
- REVIEWING → RELEASED：审核通过（工程师）
- REVIEWING → NEW：审核拒绝（工程师）
- RELEASED → PRODUCING：被生产订单使用（系统自动）
- PRODUCING → RELEASED：生产订单完成（系统自动）
- * → OBSOLETE：废弃BOM（工程师）

---

## 四、业务规则

1. **BOM编号唯一性**：BOM编号（bom_number）必须在系统中唯一。
2. **父物料存在性**：父物料（parent_material_code）必须存在。
3. **明细不能为空**：BOM明细不能为空。
4. **发布要求**：只有RELEASED状态的BOM才能用于生产版本。
5. **版本管理**：RELEASED状态的BOM需要创建新版本而非直接修改。
6. **更新限制**：可在NEW或REVIEWING状态下更新，RELEASED状态需创建新版本。
7. **基础单位**：BOM的base_uom通常为PNL（拼板），用于PCB行业。

---

## 五、聚合根

**BOM聚合根**：BOM + BOMItem

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-ENG-003, UC-ENG-004, UC-ENG-005
- [用户故事文档](../用户故事/ENG-BOM管理用户故事.md)
- [状态机文档](../状态机图/ENG-BOM管理状态机.puml)
