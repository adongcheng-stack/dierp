# ER图文件说明

本目录包含按代码菜单子模块组织的ER图文件，使用PlantUML格式编写。

## 文件列表

### SD模块（销售与分销）

1. **SD-客户管理ER图.puml**
   - 实体：customers, customer_addresses, customer_contacts, customer_partner_functions, customer_sales_data, factory_product_mappings
   - 对应菜单：`/sd/customers`
   - 对应用例：UC-SD-001, UC-SD-002, UC-SD-003

2. **SD-报价单ER图.puml**
   - 实体：quotations, quotation_items
   - 对应菜单：`/sd/quotations`
   - 对应用例：UC-SD-004, UC-SD-005, UC-SD-006, UC-SD-007, UC-SD-008, UC-SD-009

3. **SD-销售订单ER图.puml**
   - 实体：sales_orders, contract_reviews
   - 对应菜单：`/sd/sales-orders`
   - 对应用例：UC-SD-010 至 UC-SD-020

### ENG模块（工程管理）

4. **ENG-产品主数据ER图.puml**
   - 实体：materials（material_type='FG'）, factory_product_mappings
   - 对应菜单：`/eng/factory-product-mappings`
   - 对应用例：UC-ENG-001, UC-ENG-001A
   - 说明：产品主数据通过materials实体实现（material_type='FG'）

5. **ENG-BOM管理ER图.puml**
   - 实体：boms, bom_items
   - 对应菜单：`/eng/boms`
   - 对应用例：UC-ENG-003, UC-ENG-004, UC-ENG-005

6. **ENG-工艺路线ER图.puml**
   - 实体：routings, routing_operations
   - 对应菜单：`/eng/routings`
   - 对应用例：UC-ENG-006, UC-ENG-007, UC-ENG-008

7. **ENG-MI管理ER图.puml**
   - 实体：mis
   - 对应菜单：`/eng/mis`
   - 对应用例：UC-ENG-009, UC-ENG-010, UC-ENG-011, UC-ENG-012, UC-ENG-013

8. **ENG-生产版本ER图.puml**
   - 实体：production_versions
   - 对应菜单：`/eng/production-versions`
   - 对应用例：UC-ENG-014, UC-ENG-015, UC-ENG-016

### PP模块（生产计划与控制）

9. **PP-工作中心ER图.puml**
   - 实体：work_centers
   - 对应菜单：`/pp/work-centers`
   - 对应用例：UC-PP-001, UC-PP-002

10. **PP-工单管理ER图.puml**
    - 实体：production_orders, operation_reports, material_issues
    - 对应菜单：`/pp/production-orders`
    - 对应用例：UC-PP-003, UC-PP-004, UC-PP-004A, UC-PP-007, UC-PP-008, UC-PP-010
    - 说明：生产订单在实现中同时承担工单职责

11. **PP-LOT卡管理ER图.puml**
    - 实体：lot_cards, production_orders, mis, materials, operation_reports
    - 对应菜单：`/pp/lot-cards`
    - 对应用例：UC-PP-009, UC-PP-009A, UC-PP-009B, UC-PP-009C, UC-PP-009D, UC-PP-009E
    - 说明：LOT卡有独立的lot_cards表，一个生产订单/工单对应一个LOT卡（1:1关系）

12. **PP-工序报工ER图.puml**
    - 实体：operation_reports
    - 对应菜单：`/pp/operation-reports`
    - 对应用例：UC-PP-005, UC-PP-006

### MM模块（物料管理）

13. **MM-物料主数据ER图.puml**
    - 实体：materials（非FG类型）, material_transactions
    - 对应菜单：`/mm/materials`
    - 对应用例：UC-ENG-002, UC-ENG-002A, UC-MM-002, UC-MM-003
    - 说明：物料主数据管理不显示FG类型的物料

14. **MM-生产领料ER图.puml**
    - 实体：material_issues, material_transactions
    - 对应菜单：`/mm/material-issues`
    - 对应用例：UC-MM-001
    - 说明：MaterialIssue对应需求文档中的"领料单"

### 用户与权限管理模块

15. **USER-用户管理ER图.puml**
    - 实体：users
    - 对应菜单：`/admin/users`
    - 对应用例：UC-USER-001 至 UC-USER-005

## 使用方法

1. 使用PlantUML工具或在线编辑器（如 http://www.plantuml.com/plantuml/uml/）打开.puml文件
2. 可以导出为PNG、SVG等格式
3. 所有ER图都包含：
   - 实体定义（表结构）
   - 实体关系（外键关系）
   - 说明注释

## ER图说明

每个ER图包含以下信息：

1. **实体定义**：实体的名称和字段
2. **实体关系**：实体之间的外键关系，包括：
   - `||--o{`：一对多关系（One-to-Many）
   - `}o--||`：多对一关系（Many-to-One）
   - `..>`：依赖关系（Dependency）
3. **说明注释**：关键业务规则和约束条件

## 关系类型说明

- **||--o{**: 一对多关系（One-to-Many），左侧实体是"一"，右侧实体是"多"
- **}o--||**: 多对一关系（Many-to-One），左侧实体是"多"，右侧实体是"一"
- **..>**: 依赖关系（Dependency），表示一个实体依赖另一个实体

## 字段标记说明

- **<<PK>>**: 主键（Primary Key）
- **<<FK>>**: 外键（Foreign Key）
- **<<UK>>**: 唯一键（Unique Key）

## 版本信息

- **创建日期**：2025-01-XX
- **版本**：v1.4
- **基于**：
  - 某某ERP系统MVP版本需求规格说明书 v1.4
  - 某某ERP系统ER图模型.puml v1.4
  - 某某ERP系统数据模型（ER）文档 v1.4

## 特殊说明

### LOT卡实现方式

根据需求文档1.4，LOT卡有独立的数据库表`lot_cards`：

1. **LOT卡表**：`lot_cards`表，包含lot_number（主键）、production_order_number、mi_number、material_code、quantity、unit、status、mi_content、completed_at、remarks等字段
2. **关系**：一个生产订单/工单对应一个LOT卡（1:1关系）
3. **自动生成**：在生产订单/工单创建时，如果关联了MI，系统根据MI自动生成LOT卡，复制MI内容，并将lot_number写回production_orders表
4. **MI依赖**：如果MI不存在，不允许创建生产订单/工单或提示用户先创建MI

在`PP-LOT卡管理ER图.puml`中，使用注释说明了LOT卡的实现方式和业务规则。

## 相关文档

- [ER图模型文档](../某某ERP系统%20-%20ER图模型.puml)
- [数据模型（ER）文档](../某某ERP系统%20-%20数据模型（ER）.md)
- [领域模型文档](../领域模型/)
- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [类图文档](../类图/)
