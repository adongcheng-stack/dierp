# MM模块 - 物料主数据子模块领域模型

**对应菜单：** `/mm/materials`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

物料主数据子模块负责管理非成品类物料（原材料、半成品等）的主数据。物料主数据管理不显示FG类型的物料（FG类型物料在产品主数据管理中显示）。

---

## 二、核心实体

### 2.1 Material（物料）

- **表：** `materials`
- **主键：** `id`（BaseModel），业务键：`material_code`
- **关键字段：**
  - **基本字段：**
    - `material_code`：物料编码（唯一）
    - `material_name`：物料名称
    - `category`：物料分类
    - `material_type`：物料类型（FG/RAW/SEMI）
      - FG：成品（Finished Goods）- 不在物料主数据管理中显示
      - RAW：原材料（Raw Material）
      - SEMI：半成品（Semi-finished）
    - `unit`：单位
    - `status`：状态
  - **PCB属性：**
    - `layer_count`：层数
    - `board_thickness`：板厚
    - `copper_weight`：铜厚
    - `surface_finish`：表面处理
    - `solder_mask_color`：阻焊颜色
    - `silkscreen_color`：字符颜色
    - `impedance_control`：阻抗控制
  - **尺寸：**
    - `unit_length`：单位长度
    - `unit_width`：单位宽度
    - `panel_length`：拼板长度
    - `panel_width`：拼板宽度
    - `units_per_panel`：每拼板单元数
  - **供应链：**
    - `procurement_type`：采购类型
    - `mrp_controller`：MRP控制者
    - `lead_time_days`：提前期（天）
  - **成本：**
    - `valuation_method`：计价方法
    - `standard_price`：标准价格
    - `currency`：货币
  - **单位转换：**
    - `base_unit`：基础单位
    - `production_unit`：生产单位
    - `conversion_factor`：转换系数
- **关联：**
  - 1:N `BOMItem`（作为BOM明细）
  - 1:N `Routing`（工艺路线）
  - 1:N `MI`（制造指令）
  - 1:N `ProductionVersion`（生产版本）
  - 1:N `MaterialIssue`（生产领料）
  - 1:N `MaterialTransaction`（物料事务）
- **说明：**
  - 物料主数据管理不显示FG类型的物料
  - FG类型物料在产品主数据管理中显示
  - 支持PCB专有属性
  - 支持单位转换

### 2.2 MaterialTransaction（物料事务）

- **表：** `material_transactions`
- **关键字段：**
  - `transaction_number`：事务编号
  - `material_code`：物料编码（外键）
  - `transaction_type`：事务类型（ISSUE, RETURN, RECEIPT, ADJUSTMENT等）
  - `quantity`：数量
  - `unit`：单位
  - `reference_number`：参考编号
  - `reference_type`：参考类型（PRODUCTION_ORDER, MATERIAL_ISSUE等）
  - `warehouse`：仓库
  - `transaction_date`：事务日期
  - `operator`：操作人
- **说明：** 记录库存进出、调整明细，用于物料事务历史查询。

---

## 三、业务规则

1. **物料编码唯一性**：物料编码（material_code）必须在系统中唯一。
2. **显示规则**：物料主数据管理不显示FG类型的物料，FG类型物料在产品主数据管理中显示。
3. **物料类型**：物料类型包括RAW（原材料）、SEMI（半成品），不包括FG（成品）。
4. **PCB属性**：支持PCB专有属性（层数、板厚、铜厚、表面处理等）。
5. **单位转换**：支持单位转换（基础单位、生产单位、转换系数）。
6. **库存跟踪**：通过MaterialTransaction记录物料事务历史。

---

## 四、聚合根

**库存聚合**：Material + MaterialIssue + MaterialTransaction

---

## 五、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-ENG-002, UC-ENG-002A, UC-MM-002, UC-MM-003
- [用户故事文档](../用户故事/MM-物料主数据用户故事.md)
- [数据模型文档](../某某ERP系统%20-%20数据模型（ER）.md)
