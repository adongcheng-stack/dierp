# PP模块 - LOT卡管理子模块领域模型

**对应菜单：** `/pp/lot-cards`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

LOT卡管理子模块负责管理生产批次卡（LOT Card）。LOT卡由MI自动生成，关联生产订单/工单，用于工序报工。一个生产订单/工单对应一个LOT卡（1:1关系）。

---

## 二、核心实体

### 2.1 LotCard（LOT卡）

- **表：** `lot_cards`
- **主键：** `id`（BaseModel），业务键：`lot_number`
- **关键字段：**
  - `lot_number`：LOT卡号（系统自动生成，唯一）
  - `production_order_number`：关联生产订单/工单号（外键 → production_orders.order_number，1:1关系）
  - `mi_number`：关联MI编号（外键 → mis.mi_number）
  - `material_code`：物料编码（外键 → materials.material_code）
  - `quantity`：数量
  - `unit`：单位
  - `status`：状态（ACTIVE, COMPLETED, CANCELLED）
  - `mi_content`：MI内容（JSON格式，可编辑）
  - `completed_at`：完成时间
  - `remarks`：备注（可编辑）
- **关联：**
  - N:1 `ProductionOrder`（生产订单/工单，1:1关系）
  - N:1 `MI`（制造指令）
  - N:1 `Material`（物料）
  - 1:N `OperationReport`（工序报工）
- **说明：**
  - **一个生产订单/工单对应一个LOT卡（1:1关系）**
  - 创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡
  - 系统自动复制MI内容（mi_content）到LOT卡
  - 系统将lot_number写回生产订单/工单
  - 如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI
  - 支持编辑LOT卡的MI内容（mi_content）和备注（remarks）
  - 支持JSON格式解析为列表，每一条指令/属性项可单独编辑
  - 系统根据生产订单/工单号自动查询关联的LOT卡（1:1关系），用于工序报工

---

## 三、业务规则

1. **LOT卡号唯一性**：LOT卡号（lot_number）必须在系统中唯一。
2. **1:1关系**：一个生产订单/工单对应一个LOT卡（1:1关系）。
3. **自动生成**：创建生产订单/工单时，如果关联了MI，系统根据MI自动生成LOT卡。
4. **MI内容复制**：系统自动复制MI内容（mi_content）到LOT卡。
5. **MI必选**：如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI。
6. **编辑功能**：支持编辑LOT卡的MI内容（mi_content）和备注（remarks）。
7. **JSON格式**：支持JSON格式解析为列表，每一条指令/属性项可单独编辑。
8. **自动查询**：系统根据生产订单/工单号自动查询关联的LOT卡（1:1关系），用于工序报工。

---

## 四、聚合根

**LotCard聚合根**：LotCard（关联ProductionOrder、MI、Material）

---

## 五、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-PP-009, UC-PP-009A, UC-PP-009B, UC-PP-009C, UC-PP-009D, UC-PP-009E
- [用户故事文档](../用户故事/PP-LOT卡管理用户故事.md)
- [数据模型文档](../某某ERP系统%20-%20数据模型（ER）.md)
