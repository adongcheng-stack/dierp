# 状态机图文件说明

本目录包含按代码菜单子模块组织的状态机图文件，使用PlantUML格式编写。

## 文件列表

### SD模块（销售与分销）

1. **SD-客户管理状态机.puml**
   - 实体：Customer（客户）
   - 状态：DRAFT, PENDING_APPROVAL, ACTIVE, BLOCKED, INACTIVE
   - 对应菜单：`/sd/customers`
   - 对应ER表：`customers`

2. **SD-报价单状态机.puml**
   - 实体：Quotation（报价单）
   - 状态：DRAFT, PENDING_SALES, PENDING_ENGINEER, PENDING_ACCOUNT_MANAGER, APPROVED, REJECTED, CUSTOMER_CONFIRMED, LINKED, CANCELLED
   - 对应菜单：`/sd/quotations`
   - 对应ER表：`quotations`

3. **SD-销售订单状态机.puml**
   - 实体：SalesOrder（销售订单）
   - 状态：DRAFT, PENDING_REVIEW, REVIEWING, APPROVED, REJECTED, IN_PRODUCTION, COMPLETED, SHIPPED, DELIVERED, RECONCILED, CLOSED, CANCELLED
   - 对应菜单：`/sd/sales-orders`
   - 对应ER表：`sales_orders`

### ENG模块（工程管理）

4. **ENG-BOM管理状态机.puml**
   - 实体：BOM（物料清单）
   - 状态：NEW, REVIEWING, RELEASED, PRODUCING, OBSOLETE
   - 对应菜单：`/eng/boms`
   - 对应ER表：`boms`

5. **ENG-工艺路线状态机.puml**
   - 实体：Routing（工艺路线）
   - 状态：DRAFT, RELEASED, OBSOLETE
   - 对应菜单：`/eng/routings`
   - 对应ER表：`routings`

6. **ENG-MI管理状态机.puml**
   - 实体：MI（制造指令）
   - 状态：DRAFT, REVIEWING, APPROVED, RELEASED, OBSOLETE
   - 对应菜单：`/eng/mis`
   - 对应ER表：`mis`

7. **ENG-生产版本状态机.puml**
   - 实体：ProductionVersion（生产版本）
   - 状态：ACTIVE, RELEASED
   - 对应菜单：`/eng/production-versions`
   - 对应ER表：`production_versions`

**注意**：产品主数据（Material，material_type='FG'）没有状态机，因此未创建对应的状态机文件。

### PP模块（生产计划与控制）

8. **PP-工作中心状态机.puml**
   - 实体：WorkCenter（工作中心）
   - 状态：ACTIVE, INACTIVE, IN_MAINTENANCE
   - 对应菜单：`/pp/work-centers`
   - 对应ER表：`work_centers`

9. **PP-工单管理状态机.puml**
   - 实体：ProductionOrder（生产订单/工单）
   - 状态：DRAFT, RELEASED, IN_PRODUCTION, COMPLETED, CLOSED, CANCELLED
   - 对应菜单：`/pp/production-orders`
   - 对应ER表：`production_orders`

10. **PP-工序报工状态机.puml**
    - 实体：OperationReport（工序报工）
    - 状态：PENDING, IN_PROGRESS, COMPLETED, REJECTED
    - 对应菜单：`/pp/operation-reports`
    - 对应ER表：`operation_reports`

**注意**：LOT卡（LotCard）没有状态机，因此未创建对应的状态机文件。

### MM模块（物料管理）

**注意**：物料主数据（Material，非FG类型）和生产领料（MaterialIssue）没有状态机，因此未创建对应的状态机文件。

### 用户与权限管理模块

**注意**：用户（User）没有状态机，因此未创建对应的状态机文件。

## 使用方法

1. 使用PlantUML工具或在线编辑器（如 http://www.plantuml.com/plantuml/uml/）打开.puml文件
2. 可以导出为PNG、SVG等格式
3. 所有状态机图都包含：
   - 状态定义
   - 状态转换（带触发事件和操作人角色）
   - 状态说明注释

## 状态机图说明

每个状态机图包含以下信息：

1. **状态节点**：表示实体的可能状态
2. **状态转换**：从一个状态到另一个状态的转换，标注了：
   - 触发事件（如"提交审批"）
   - 操作人角色（如"销售员"）
3. **状态说明**：每个状态的业务含义和约束条件

## 版本信息

- **创建日期**：2025-01-XX
- **版本**：v1.4
- **基于**：
  - 某某ERP系统MVP版本需求规格说明书 v1.4
  - 某某ERP系统状态机模型文档 v1.4
  - 某某ERP系统数据模型（ER）文档 v1.4

## 相关文档

- [状态机模型文档](../某某ERP系统%20-%20状态机模型（State%20Machine）.md)
- [数据模型（ER）文档](../某某ERP系统%20-%20数据模型（ER）.md)
- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md)
