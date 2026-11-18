# 类图文件说明

本目录包含按代码菜单子模块组织的类图文件，使用PlantUML格式编写。

## 文件列表

### SD模块（销售与分销）

1. **SD-客户管理类图.puml**
   - 类：Customer, CustomerAddress, CustomerContact, CustomerPartnerFunction, CustomerSalesData, FactoryProductMapping
   - 对应菜单：`/sd/customers`
   - 对应用例：UC-SD-001, UC-SD-002, UC-SD-003

2. **SD-报价单类图.puml**
   - 类：Quotation, QuotationItem
   - 对应菜单：`/sd/quotations`
   - 对应用例：UC-SD-004, UC-SD-005, UC-SD-006, UC-SD-007, UC-SD-008, UC-SD-009

3. **SD-销售订单类图.puml**
   - 类：SalesOrder, ContractReview
   - 对应菜单：`/sd/sales-orders`
   - 对应用例：UC-SD-010 至 UC-SD-020

### ENG模块（工程管理）

4. **ENG-产品主数据类图.puml**
   - 类：Material（material_type='FG'）, FactoryProductMapping
   - 对应菜单：`/eng/factory-product-mappings`
   - 对应用例：UC-ENG-001, UC-ENG-001A
   - 说明：产品主数据通过Material实体实现（material_type='FG'）

5. **ENG-BOM管理类图.puml**
   - 类：BOM, BOMItem
   - 对应菜单：`/eng/boms`
   - 对应用例：UC-ENG-003, UC-ENG-004, UC-ENG-005

6. **ENG-工艺路线类图.puml**
   - 类：Routing, RoutingOperation
   - 对应菜单：`/eng/routings`
   - 对应用例：UC-ENG-006, UC-ENG-007, UC-ENG-008

7. **ENG-MI管理类图.puml**
   - 类：MI
   - 对应菜单：`/eng/mis`
   - 对应用例：UC-ENG-009, UC-ENG-010, UC-ENG-011, UC-ENG-012, UC-ENG-013

8. **ENG-生产版本类图.puml**
   - 类：ProductionVersion
   - 对应菜单：`/eng/production-versions`
   - 对应用例：UC-ENG-014, UC-ENG-015, UC-ENG-016

### PP模块（生产计划与控制）

9. **PP-工作中心类图.puml**
   - 类：WorkCenter
   - 对应菜单：`/pp/work-centers`
   - 对应用例：UC-PP-001, UC-PP-002

10. **PP-工单管理类图.puml**
    - 类：ProductionOrder, LotCard, OperationReport, MaterialIssue
    - 对应菜单：`/pp/production-orders`
    - 对应用例：UC-PP-003, UC-PP-004, UC-PP-004A, UC-PP-007, UC-PP-008, UC-PP-010
    - 说明：生产订单在实现中同时承担工单职责

11. **PP-LOT卡管理类图.puml**
    - 类：LotCard
    - 对应菜单：`/pp/lot-cards`
    - 对应用例：UC-PP-009, UC-PP-009A, UC-PP-009B, UC-PP-009C, UC-PP-009D, UC-PP-009E

12. **PP-工序报工类图.puml**
    - 类：OperationReport
    - 对应菜单：`/pp/operation-reports`
    - 对应用例：UC-PP-005, UC-PP-006

### MM模块（物料管理）

13. **MM-物料主数据类图.puml**
    - 类：Material（非FG类型）, MaterialTransaction
    - 对应菜单：`/mm/materials`
    - 对应用例：UC-ENG-002, UC-ENG-002A, UC-MM-002, UC-MM-003
    - 说明：物料主数据管理不显示FG类型的物料

14. **MM-生产领料类图.puml**
    - 类：MaterialIssue, MaterialTransaction
    - 对应菜单：`/mm/material-issues`
    - 对应用例：UC-MM-001
    - 说明：MaterialIssue对应需求文档中的"领料单"

### 用户与权限管理模块

15. **USER-用户管理类图.puml**
    - 类：User
    - 对应菜单：`/admin/users`
    - 对应用例：UC-USER-001 至 UC-USER-005

## 使用方法

1. 使用PlantUML工具或在线编辑器（如 http://www.plantuml.com/plantuml/uml/）打开.puml文件
2. 可以导出为PNG、SVG等格式
3. 所有类图都包含：
   - 类定义（属性）
   - 类关系（关联、组合、依赖等）
   - 说明注释

## 类图说明

每个类图包含以下信息：

1. **类定义**：类的名称和属性
2. **类关系**：类之间的关联关系，包括：
   - 组合关系（*--）：强拥有关系
   - 关联关系（-->）：引用关系
   - 依赖关系（..>）：使用关系
3. **说明注释**：关键业务规则和约束条件

## 版本信息

- **创建日期**：2025-01-XX
- **版本**：v1.4
- **基于**：
  - 某某ERP系统MVP版本需求规格说明书 v1.4
  - 某某ERP系统类图模型文档 v1.4
  - 某某ERP系统数据模型（ER）文档 v1.4

## 相关文档

- [类图文档](../某某ERP系统%20-%20类图（Class%20Diagram）.md)
- [领域模型文档](../领域模型/)
- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [数据模型（ER）文档](../某某ERP系统%20-%20数据模型（ER）.md)
