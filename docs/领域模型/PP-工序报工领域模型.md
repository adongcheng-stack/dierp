# PP模块 - 工序报工子模块领域模型

**对应菜单：** `/pp/operation-reports`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

工序报工子模块负责管理工序报工记录，记录工序完成情况。系统根据生产订单/工单号自动查询关联的LOT卡（1:1关系），自动填充LOT卡号。

---

## 二、核心实体

### 2.1 OperationReport（工序报工 / 报工单）

- **表：** `operation_reports`
- **主键：** `id`（BaseModel），业务键：`report_number`
- **状态枚举：** `OperationReportStatus`（PENDING, IN_PROGRESS, COMPLETED, REJECTED）
- **关键字段：**
  - `report_number`：报工单号（唯一）
  - `production_order_number`：关联生产订单/工单号（外键 → production_orders.order_number）
  - `lot_number`：LOT卡号（外键 → lot_cards.lot_number，系统根据生产订单/工单号自动查询关联的LOT卡，1:1关系，只读、不可修改）
  - `routing_operation_id`：关联工艺路线工序（外键 → routing_operations.id）
  - `work_center_id`：工作中心ID（外键 → work_centers.work_center_id）
  - `operation_no`：工序号
  - `operation_name`：工序名称
  - **数量：**
    - `reported_quantity`：报工数量
    - `good_quantity`：良品数量
    - `scrap_quantity`：报废数量
  - **时间：**
    - `setup_time`：调机时间
    - `machine_time`：机器时间
    - `labor_time`：人工时间
  - **报工人及时间：**
    - `reported_by`：报工人
    - `reported_at`：报工时间
  - `status`：报工状态
  - `rejection_reason`：拒绝原因（如果被拒绝）
- **关联：**
  - N:1 `ProductionOrder`（生产订单/工单）
  - N:1 `LotCard`（LOT卡）
  - N:1 `RoutingOperation`（工艺路线工序）
  - N:1 `WorkCenter`（工作中心）
- **说明：**
  - 系统根据生产订单/工单号自动查询关联的LOT卡（一个生产订单/工单对应一个LOT卡，1:1关系）
  - 系统自动填充报工单中的LOT卡号字段（只读、不可修改）
  - 如果找不到LOT卡，不允许保存报工
  - 在PENDING/IN_REVIEW状态下可更新报工
  - 如果工序配置了自动倒扣料，则扣减物料库存
  - 报工完成后更新生产进度

---

## 三、状态机

### 3.1 OperationReport状态

- **PENDING**：待报工，工序报工记录创建，等待报工
- **IN_PROGRESS**：进行中，正在报工
- **COMPLETED**：已完成，报工完成
- **REJECTED**：已拒绝，报工被拒绝（如质检不合格）

### 3.2 状态转换规则

- PENDING → IN_PROGRESS：开始报工（生产人员）
- IN_PROGRESS → COMPLETED：完成报工（生产人员）
- IN_PROGRESS → REJECTED：拒绝报工（生产人员/质检）
- REJECTED → IN_PROGRESS：重新报工（生产人员）

---

## 四、业务规则

1. **报工单号唯一性**：报工单号（report_number）必须在系统中唯一。
2. **LOT卡自动查询**：系统根据生产订单/工单号自动查询关联的LOT卡（1:1关系）。
3. **LOT卡号只读**：系统自动填充LOT卡号字段（只读、不可修改）。
4. **LOT卡必选**：如果找不到LOT卡，不允许保存报工。
5. **更新限制**：在PENDING/IN_REVIEW状态下可更新报工，已完结/审核通过的报工不可直接修改。
6. **自动倒扣料**：如果工序配置了自动倒扣料，则扣减物料库存。
7. **生产进度更新**：报工完成后更新生产进度。
8. **生产完成判断**：当所有工序都已报工完成时，系统自动判断生产订单是否完成。

---

## 五、聚合根

**OperationReport聚合根**：OperationReport（关联ProductionOrder、LotCard、RoutingOperation、WorkCenter）

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-PP-005, UC-PP-006
- [用户故事文档](../用户故事/PP-工序报工用户故事.md)
- [状态机文档](../状态机图/PP-工序报工状态机.puml)
