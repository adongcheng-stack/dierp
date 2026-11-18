# MM模块 - 生产领料子模块领域模型

**对应菜单：** `/mm/material-issues`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

生产领料子模块负责管理生产领料单，从仓库领料用于生产。系统根据生产订单/工单关联的BOM自动生成领料需求，实时显示库存信息。

---

## 二、核心实体

### 2.1 MaterialIssue（生产领料）

- **表：** `material_issues`
- **主键：** `id`（BaseModel），业务键：`issue_number`
- **需求名：** 领料单
- **关键字段：**
  - `issue_number`：领料单号（唯一）
  - `production_order_number`：关联生产订单/工单号（外键 → production_orders.order_number）
  - `material_code`：物料编码（外键 → materials.material_code）
  - `quantity`：领料数量
  - `unit`：单位
  - `issued_by`：领料人
  - `issued_at`：领料时间
  - `warehouse`：仓库
  - `remarks`：备注
- **关联：**
  - N:1 `ProductionOrder`（生产订单/工单）
  - N:1 `Material`（物料）
  - 1:N `MaterialTransaction`（物料事务）
- **说明：**
  - 系统根据生产订单/工单关联的BOM自动生成领料需求
  - 实时显示库存信息（当前库存、在途量、可用量）
  - 当库存不足时，可生成缺料单
  - 领料后自动更新物料库存
  - 创建MaterialTransaction记录

---

## 三、业务规则

1. **领料单号唯一性**：领料单号（issue_number）必须在系统中唯一。
2. **生产订单关联**：生产领料单必须关联生产订单/工单。
3. **BOM自动生成**：系统根据生产订单/工单关联的BOM自动生成领料需求。
4. **库存显示**：实时显示库存信息（当前库存、在途量、可用量）。
5. **缺料处理**：当库存不足时，可生成缺料单。
6. **库存更新**：领料后自动更新物料库存。
7. **事务记录**：创建MaterialTransaction记录，记录物料事务历史。
8. **生产订单状态要求**：生产订单状态为RELEASED或IN_PRODUCTION时才能创建领料单。

---

## 四、聚合根

**库存聚合**：Material + MaterialIssue + MaterialTransaction

---

## 五、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-MM-001
- [用户故事文档](../用户故事/MM-生产领料用户故事.md)
- [数据模型文档](../某某ERP系统%20-%20数据模型（ER）.md)
