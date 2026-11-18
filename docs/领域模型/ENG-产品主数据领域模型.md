# ENG模块 - 产品主数据子模块领域模型

**对应菜单：** `/eng/factory-product-mappings`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

产品主数据子模块负责管理成品（FG类型）物料的主数据。产品主数据通过Material实体实现（material_type='FG'），以本厂编号作为唯一标识。

---

## 二、核心实体

### 2.1 Material（物料 / 产品主数据）

- **表：** `materials`
- **主键：** `id`（BaseModel），业务键：`material_code`
- **关键字段：**
  - **基本字段：**
    - `material_code`：物料编码（产品主数据中，material_code = 本厂编号）
    - `material_name`：物料名称
    - `category`：物料分类
    - `material_type`：物料类型（FG/RAW/SEMI）
      - FG：成品（Finished Goods）
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
- **关联：**
  - 1:N `BOM`（作为父物料）
  - 1:N `Routing`（工艺路线）
  - 1:N `MI`（制造指令）
  - 1:N `ProductionVersion`（生产版本）
  - 1:N `FactoryProductMapping`（本厂编号映射）
- **说明：**
  - **产品主数据 = Material 且 material_type='FG'**
  - 产品主数据以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）
  - 物料主数据管理页面不展示FG，产品主数据管理页面只展示FG
  - 产品主数据由工程管理模块统一管理，ENG模块拥有产品主数据的完整CRUD权限
  - SD模块可以创建（自动创建）、查询、引用产品主数据，但不能修改、删除产品主数据（需ENG模块操作）
  - 所有产品主数据的所有权属于ENG模块
  - 如果本厂编号对应的产品主数据不存在，SD模块调用ENG模块的产品主数据创建API自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），自动创建的产品主数据不需要审核

---

## 三、业务规则

1. **物料编码唯一性**：物料编码（material_code）必须在系统中唯一。
2. **产品主数据标识**：产品主数据 = Material 且 material_type='FG'。
3. **本厂编号映射**：产品主数据以本厂编号作为唯一标识，本厂编号同时作为产品编码（material_code）。
4. **显示规则**：物料主数据管理页面不展示FG，产品主数据管理页面只展示FG。
5. **权限管理**：
   - ENG模块拥有产品主数据的完整CRUD权限
   - SD模块可以创建（自动创建）、查询、引用产品主数据，但不能修改、删除产品主数据
   - 所有产品主数据的所有权属于ENG模块
6. **自动创建**：如果本厂编号对应的产品主数据不存在，SD模块调用ENG模块API自动创建产品主数据，自动创建的产品主数据不需要审核。

---

## 四、聚合根

**Material聚合根**：Material（作为产品主数据时，material_type='FG'）

---

## 五、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-ENG-001, UC-ENG-001A
- [用户故事文档](../用户故事/ENG-产品主数据用户故事.md)
- [数据模型文档](../某某ERP系统%20-%20数据模型（ER）.md)
