# PP模块 - 工作中心子模块领域模型

**对应菜单：** `/pp/work-centers`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

工作中心子模块负责管理工作中心，定义生产能力和基础参数。工作中心支持层级结构，用于工艺路线和排产。

---

## 二、核心实体

### 2.1 WorkCenter（工作中心）

- **表：** `work_centers`
- **主键：** `id`（BaseModel），业务键：`work_center_id`
- **类型枚举：** `WorkCenterType`（MACHINE, MACHINE_GROUP, LABOR, PRODUCTION_LINE）
- **状态枚举：** `WorkCenterStatus`（ACTIVE, INACTIVE, IN_MAINTENANCE）
- **关键字段：**
  - `work_center_id`：工作中心代码（唯一）
  - `description`：描述
  - `work_center_type`：工作中心类型（MACHINE/MACHINE_GROUP/LABOR/PRODUCTION_LINE）
  - `plant_id`：工厂/生产地点
  - `status`：状态（ACTIVE/INACTIVE/IN_MAINTENANCE）
  - `parent_work_center_id`：父工作中心ID（外键，支持层级结构）
  - `hierarchy_level`：层级级别
  - **基础与调度数据：**
    - `work_center_category`：工作中心类别
    - `usage`：用途（PP01, PM01, QM01）
    - `standard_value_key`：标准值码
    - `control_key`：控制码
    - `queue_time`：排队时间（小时）
    - `wait_time`：等待时间（小时）
    - `move_time`：传送时间（小时）
  - **产能数据：**
    - `capacity_category`：能力类别
    - `factory_calendar_id`：工厂日历ID
    - `shift_start_time`：班次开始时间
    - `shift_finish_time`：班次结束时间
    - `break_time`：休息时间（小时）
    - `capacity_utilization`：产能利用率（%）
    - `number_of_capacities`：能力数量
    - `capacity_formula_setup`：能力公式-设置
    - `capacity_formula_processing`：能力公式-加工
    - `capacity_formula_teardown`：能力公式-拆卸
  - **成本核算数据：**
    - `cost_center_id`：成本中心代码
    - `activity_types`：活动类型（JSON数组）
  - **PCB行业特定数据：**
    - `process_category`：工艺类别（DRILLING, PLATING, ETCHING等）
    - `technical_attributes`：技术属性（JSON格式）
- **关联：**
  - N:1 `WorkCenter`（父工作中心，自引用）
  - 1:N `RoutingOperation`（工艺路线工序）
  - 1:N `OperationReport`（工序报工）
- **说明：**
  - 工作中心代码唯一
  - 支持层级结构（父工作中心）
  - 供工艺路线和排产使用
  - 创建时默认为ACTIVE状态
  - 工作中心代码不可修改

---

## 三、状态机

### 3.1 WorkCenter状态

- **ACTIVE**：激活，工作中心正常使用中
- **INACTIVE**：未激活，工作中心未激活，不可用
- **IN_MAINTENANCE**：维护中，工作中心正在维护，暂停使用

### 3.2 状态转换规则

- ACTIVE → IN_MAINTENANCE：开始维护（工程师/管理员）
- IN_MAINTENANCE → ACTIVE：维护完成（工程师/管理员）
- ACTIVE → INACTIVE：停用（工程师/管理员）
- INACTIVE → ACTIVE：激活（工程师/管理员）
- IN_MAINTENANCE → INACTIVE：停用（工程师/管理员）

---

## 四、业务规则

1. **工作中心代码唯一性**：工作中心代码（work_center_id）必须在系统中唯一。
2. **层级结构**：支持层级结构（父工作中心），通过parent_work_center_id实现。
3. **状态管理**：创建时默认为ACTIVE状态。
4. **维护检查**：开始维护前需检查是否有正在执行的生产任务。
5. **停用检查**：停用前需检查是否有正在执行的生产任务。
6. **代码不可修改**：工作中心代码不可修改。
7. **用途说明**：供工艺路线和排产使用。

---

## 五、聚合根

**WorkCenter聚合根**：WorkCenter（支持层级结构）

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-PP-001, UC-PP-002
- [用户故事文档](../用户故事/PP-工作中心用户故事.md)
- [状态机文档](../状态机图/PP-工作中心状态机.puml)
