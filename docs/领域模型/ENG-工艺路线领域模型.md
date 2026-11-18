# ENG模块 - 工艺路线子模块领域模型

**对应菜单：** `/eng/routings`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

工艺路线子模块负责管理产品的生产工艺流程，定义工序序列、工作中心和时间参数。工艺路线需要经过发布流程，只有RELEASED状态的工艺路线才能用于生产版本。

---

## 二、核心实体

### 2.1 Routing（工艺路线）

- **表：** `routings`
- **主键：** `id`（BaseModel），业务键：`routing_id`
- **状态枚举：** `RoutingStatus`（DRAFT, RELEASED, OBSOLETE）
- **关键字段：**
  - `routing_id`：工艺路线ID（唯一）
  - `version`：版本号
  - `material_code`：物料编码（外键 → materials.material_code）
  - `description`：描述
  - `plant_id`：工厂/生产地点
  - `base_unit`：基础单位（默认PNL）
  - `base_quantity`：基数（默认1）
  - `units_per_panel`：每拼板单元数
  - `panel_size`：拼板尺寸
  - `effective_date`：生效日期
  - `expiry_date`：失效日期
  - `status`：状态
  - `change_request_no`：工程变更单号（审计追踪）
- **关联：**
  - N:1 `Material`（物料）
  - 1:N `RoutingOperation`（工序）
  - 1:N `ProductionVersion`（生产版本）
- **说明：**
  - 工艺路线的基础单位通常为PNL（拼板），用于PCB行业
  - 只有RELEASED状态的工艺路线才能用于生产版本
  - DRAFT状态的工艺路线可以直接发布为RELEASED
  - RELEASED状态需创建新版本

### 2.2 RoutingOperation（工艺路线工序）

- **表：** `routing_operations`
- **关键字段：**
  - `routing_id`：工艺路线ID（外键）
  - `operation_no`：工序号（如0010, 0020）
  - `operation_code`：工序代码
  - `operation_name`：工序名称
  - `operation_type`：工序类型（internal/external/quality）
  - `work_center_id`：工作中心ID（外键 → work_centers.work_center_id，如果是internal类型）
  - **时间参数：**
    - `setup_time`：调机时间
    - `machine_time`：机器时间
    - `labor_time`：人工时间
    - `queue_time`：排队时间
  - **控制逻辑：**
    - `cost_relevant`：是否成本相关
    - `scheduling_relevant`：是否排程相关
    - `needs_reporting`：是否需要报工
    - `auto_deduct_material`：是否自动倒扣料
    - `trigger_quality_check`：是否触发质检
  - **外协参数（如果是external类型）：**
    - `service_code`：服务代码
    - `planned_delivery_days`：计划交付天数
    - `estimated_unit_price`：预估单价
  - **质检参数（如果是quality类型）：**
    - `inspection_plan_id`：检验计划ID
    - `sampling_rate`：抽样率
    - `inspection_type`：检验类型
- **说明：**
  - 工序按operation_no排序执行
  - 工序类型可以是internal（内部）、external（外协）或quality（质检）
  - 内部工序必须关联工作中心
  - 支持PCB行业特定的工序配置

---

## 三、状态机

### 3.1 Routing状态

- **DRAFT**：草稿，工艺路线创建但未发布
- **RELEASED**：已发布，已发布，可用于生产
- **OBSOLETE**：已废弃，已废弃，不再使用

### 3.2 状态转换规则

- DRAFT → RELEASED：发布（工程师）
- * → OBSOLETE：废弃（工程师）

---

## 四、业务规则

1. **工艺路线ID唯一性**：工艺路线ID（routing_id）必须在系统中唯一。
2. **物料存在性**：物料（material_code）必须存在。
3. **工序不能为空**：工艺路线必须包含至少一个工序。
4. **发布要求**：只有RELEASED状态的工艺路线才能用于生产版本。
5. **版本管理**：RELEASED状态需创建新版本。
6. **更新限制**：只能在DRAFT状态下更新，RELEASED状态需创建新版本。
7. **基础单位**：工艺路线的基础单位通常为PNL（拼板），用于PCB行业。
8. **工序顺序**：工序按operation_no排序执行。
9. **工作中心要求**：内部工序（internal类型）必须关联工作中心。

---

## 五、聚合根

**Routing聚合根**：Routing + RoutingOperation

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-ENG-006, UC-ENG-007, UC-ENG-008
- [用户故事文档](../用户故事/ENG-工艺路线用户故事.md)
- [状态机文档](../状态机图/ENG-工艺路线状态机.puml)
