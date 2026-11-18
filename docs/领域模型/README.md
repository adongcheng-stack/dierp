# 领域模型文件说明

本目录包含按代码菜单子模块组织的领域模型文件。

## 文件列表

### SD模块（销售与分销）

1. **SD-客户管理领域模型.md**
   - 实体：Customer, CustomerAddress, CustomerContact, CustomerPartnerFunction, CustomerSalesData, FactoryProductMapping
   - 对应菜单：`/sd/customers`
   - 对应用例：UC-SD-001, UC-SD-002, UC-SD-003

2. **SD-报价单领域模型.md**
   - 实体：Quotation, QuotationItem
   - 对应菜单：`/sd/quotations`
   - 对应用例：UC-SD-004, UC-SD-005, UC-SD-006, UC-SD-007, UC-SD-008, UC-SD-009

3. **SD-销售订单领域模型.md**
   - 实体：SalesOrder, ContractReview
   - 对应菜单：`/sd/sales-orders`
   - 对应用例：UC-SD-010 至 UC-SD-020

### ENG模块（工程管理）

4. **ENG-产品主数据领域模型.md**
   - 实体：Material（material_type='FG'）
   - 对应菜单：`/eng/factory-product-mappings`
   - 对应用例：UC-ENG-001, UC-ENG-001A
   - 说明：产品主数据通过Material实体实现（material_type='FG'）

5. **ENG-BOM管理领域模型.md**
   - 实体：BOM, BOMItem
   - 对应菜单：`/eng/boms`
   - 对应用例：UC-ENG-003, UC-ENG-004, UC-ENG-005

6. **ENG-工艺路线领域模型.md**
   - 实体：Routing, RoutingOperation
   - 对应菜单：`/eng/routings`
   - 对应用例：UC-ENG-006, UC-ENG-007, UC-ENG-008

7. **ENG-MI管理领域模型.md**
   - 实体：MI
   - 对应菜单：`/eng/mis`
   - 对应用例：UC-ENG-009, UC-ENG-010, UC-ENG-011, UC-ENG-012, UC-ENG-013

8. **ENG-生产版本领域模型.md**
   - 实体：ProductionVersion
   - 对应菜单：`/eng/production-versions`
   - 对应用例：UC-ENG-014, UC-ENG-015, UC-ENG-016

### PP模块（生产计划与控制）

9. **PP-工作中心领域模型.md**
   - 实体：WorkCenter
   - 对应菜单：`/pp/work-centers`
   - 对应用例：UC-PP-001, UC-PP-002

10. **PP-工单管理领域模型.md**
    - 实体：ProductionOrder
    - 对应菜单：`/pp/production-orders`
    - 对应用例：UC-PP-003, UC-PP-004, UC-PP-004A, UC-PP-007, UC-PP-008, UC-PP-010
    - 说明：生产订单在实现中同时承担工单职责

11. **PP-LOT卡管理领域模型.md**
    - 实体：LotCard
    - 对应菜单：`/pp/lot-cards`
    - 对应用例：UC-PP-009, UC-PP-009A, UC-PP-009B, UC-PP-009C, UC-PP-009D, UC-PP-009E

12. **PP-工序报工领域模型.md**
    - 实体：OperationReport
    - 对应菜单：`/pp/operation-reports`
    - 对应用例：UC-PP-005, UC-PP-006

### MM模块（物料管理）

13. **MM-物料主数据领域模型.md**
    - 实体：Material（非FG类型）, MaterialTransaction
    - 对应菜单：`/mm/materials`
    - 对应用例：UC-ENG-002, UC-ENG-002A, UC-MM-002, UC-MM-003
    - 说明：物料主数据管理不显示FG类型的物料

14. **MM-生产领料领域模型.md**
    - 实体：MaterialIssue
    - 对应菜单：`/mm/material-issues`
    - 对应用例：UC-MM-001
    - 说明：MaterialIssue对应需求文档中的"领料单"

### 用户与权限管理模块

15. **USER-用户管理领域模型.md**
    - 实体：User
    - 对应菜单：`/admin/users`
    - 对应用例：UC-USER-001 至 UC-USER-005

## 领域模型结构

每个领域模型文件包含以下部分：

1. **模块概述**：子模块的业务概述
2. **核心实体**：实体定义、关键字段、关联关系
3. **状态机**：状态定义和状态转换规则（如果有状态机）
4. **业务规则**：关键业务规则和约束条件
5. **聚合根**：聚合根定义
6. **相关文档**：相关用例、用户故事、状态机等文档链接

## 实体统计

### 按模块统计

| 模块 | 实体数量 | 主要实体 |
|------|---------|---------|
| SD-客户管理 | 6 | Customer, CustomerAddress, CustomerContact, CustomerPartnerFunction, CustomerSalesData, FactoryProductMapping |
| SD-报价单 | 2 | Quotation, QuotationItem |
| SD-销售订单 | 2 | SalesOrder, ContractReview |
| ENG-产品主数据 | 1 | Material（FG类型） |
| ENG-BOM管理 | 2 | BOM, BOMItem |
| ENG-工艺路线 | 2 | Routing, RoutingOperation |
| ENG-MI管理 | 1 | MI |
| ENG-生产版本 | 1 | ProductionVersion |
| PP-工作中心 | 1 | WorkCenter |
| PP-工单管理 | 1 | ProductionOrder |
| PP-LOT卡管理 | 1 | LotCard |
| PP-工序报工 | 1 | OperationReport |
| MM-物料主数据 | 2 | Material（非FG类型）, MaterialTransaction |
| MM-生产领料 | 1 | MaterialIssue |
| USER-用户管理 | 1 | User |
| **总计** | **25** | |

## 版本信息

- **创建日期**：2025-01-XX
- **版本**：v1.0
- **基于**：某某ERP系统领域模型文档 v1.4

## 相关文档

- [领域模型文档](../某某ERP系统01%20-%20领域模型（Domain%20Model）.md)
- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [用户故事文档](../用户故事/)
- [状态机文档](../状态机图/)
- [数据模型（ER）文档](../某某ERP系统%20-%20数据模型（ER）.md)
