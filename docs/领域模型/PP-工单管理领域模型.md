# PP模块 - 工单管理子模块领域模型

**对应菜单：** `/pp/production-orders`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

工单管理子模块负责管理生产订单/工单。在实现中，ProductionOrder同时承担"生产订单"和"工单"的职责：既承接销售订单，又作为生产执行和报工的载体，MVP中不再单独建WorkOrder表。

---

## 二、核心实体

### 2.1 ProductionOrder（生产订单/工单）

- **表：** `production_orders`
- **主键：** `id`（BaseModel），业务键：`order_number`
- **状态枚举：** `ProductionOrderStatus`（DRAFT, RELEASED, IN_PRODUCTION, COMPLETED, CLOSED, CANCELLED）
- **关键字段：**
  - `order_number`：生产订单（工单）号（唯一）
  - `sales_order_number`：关联销售订单号（外键 → sales_orders.order_number）
  - `material_code`：生产物料（通常为FG产品，外键 → materials.material_code）
  - `production_version_id`：关联生产版本（外键 → production_versions.production_version_id）
  - `quantity`：生产数量
  - `unit`：生产单位
  - **计划/实际时间：**
    - `planned_start_date`：计划开始日期
    - `planned_finish_date`：计划完成日期
    - `actual_start_date`：实际开始日期
    - `actual_finish_date`：实际完成日期
  - `status`：生产订单/工单状态
  - `lot_number`：关联LOT卡号（外键 → lot_cards.lot_number）
  - **销售订单数量和单位转换：**
    - `sales_quantity`：关联的销售订单数量
    - `sales_unit`：销售单位
    - `conversion_factor`：转换系数
  - `remarks`：备注
- **关联：**
  - N:1 `SalesOrder`（销售订单）
  - N:1 `Material`（物料）
  - N:1 `ProductionVersion`（生产版本）
  - N:1 `LotCard`（LOT卡，1:1关系）
  - 1:N `OperationReport`（工序报工）
- **说明：**
  - **生产订单在实现中同时承担工单职责，当前版本不单独建WorkOrder表**
  - 如果关联了MI，系统根据MI自动生成LOT卡（1:1关系）
  - 工单状态与生产订单状态一致
  - 下达时需要生产版本已发布，且MI已审核通过
  - 开始生产时记录实际开始时间，同步销售订单状态
  - 生产完成时检查所有工序是否已完成，更新物料库存（成品入库）
  - 关闭时会同时关闭关联的生产订单/工单

---

## 三、状态机

### 3.1 ProductionOrder状态

- **DRAFT**：草稿，生产订单创建但未下达
- **RELEASED**：已下达，生产订单已下达，可以开始生产
- **IN_PRODUCTION**：生产中，正在生产
- **COMPLETED**：已完成，生产完成
- **CLOSED**：已关闭，生产订单已关闭
- **CANCELLED**：已取消，生产订单被取消

### 3.2 状态转换规则

- DRAFT → RELEASED：下达订单（计划员/生产人员）
- RELEASED → IN_PRODUCTION：开始生产（计划员/生产人员）
- IN_PRODUCTION → COMPLETED：生产完成（系统自动）
- COMPLETED → CLOSED：关闭订单（计划员/生产人员）
- DRAFT → CANCELLED：取消订单（计划员/生产人员）
- RELEASED → CANCELLED：取消订单（计划员/生产人员，未开始生产时）

---

## 四、业务规则

1. **生产订单号唯一性**：生产订单号（order_number）必须在系统中唯一。
2. **销售订单关联**：生产订单必须关联销售订单。
3. **生产版本要求**：下达时需要生产版本已发布，且MI已审核通过。
4. **LOT卡生成**：如果关联了MI，系统根据MI自动生成LOT卡（1:1关系）。
5. **状态同步**：工单状态与生产订单状态一致。
6. **开始生产**：开始生产时记录实际开始时间，同步销售订单状态。
7. **生产完成**：当所有工序都已报工完成时，系统自动完成或手动完成。
8. **关闭关联**：关闭销售订单时，会同时关闭关联的生产订单/工单。
9. **取消限制**：如果已开始生产，需要先停止所有工序才能取消。

---

## 五、聚合根

**生产执行聚合**：ProductionOrder（工单） + LotCard + OperationReport + ProductionProgress

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-PP-003, UC-PP-004, UC-PP-004A, UC-PP-007, UC-PP-008, UC-PP-010
- [用户故事文档](../用户故事/PP-工单管理用户故事.md)
- [状态机文档](../状态机图/PP-工单管理状态机.puml)
