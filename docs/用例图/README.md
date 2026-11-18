# 用例图文件说明

本目录包含按代码菜单子模块组织的用例图文件，使用PlantUML格式编写。

## 文件列表

### SD模块（销售与分销）

1. **SD-客户管理用例图.puml**
   - 用例：UC-SD-001（创建客户）、UC-SD-002（审批客户）、UC-SD-003（创建本厂编号映射）
   - 对应菜单：`/sd/customers`

2. **SD-报价单用例图.puml**
   - 用例：UC-SD-004（创建报价单）、UC-SD-005（提交报价单审批）、UC-SD-006（审批报价单）、UC-SD-007（拒绝报价单）、UC-SD-008（重新提交报价单）、UC-SD-009（销售员经客户确认报价单）
   - 对应菜单：`/sd/quotations`

3. **SD-销售订单用例图.puml**
   - 用例：UC-SD-010（创建销售订单）、UC-SD-011（提交销售订单评审）、UC-SD-012（销售部门评审订单）、UC-SD-013（工程部门评审订单）、UC-SD-014（物料部门评审订单）、UC-SD-015（财务部门评审订单）、UC-SD-016（拒绝销售订单）、UC-SD-017（销售发货）、UC-SD-018（销售签收）、UC-SD-019（对账）、UC-SD-020（关闭销售订单）
   - 对应菜单：`/sd/sales-orders`

### ENG模块（工程管理）

4. **ENG-产品主数据用例图.puml**
   - 用例：UC-ENG-001（产品主数据管理）、UC-ENG-001A（产品列表查询）
   - 对应菜单：`/eng/factory-product-mappings`

5. **ENG-BOM管理用例图.puml**
   - 用例：UC-ENG-003（创建BOM）、UC-ENG-004（更新BOM）、UC-ENG-005（发布BOM）
   - 对应菜单：`/eng/boms`

6. **ENG-工艺路线用例图.puml**
   - 用例：UC-ENG-006（创建工艺路线）、UC-ENG-007（更新工艺路线）、UC-ENG-008（发布工艺路线）
   - 对应菜单：`/eng/routings`

7. **ENG-MI管理用例图.puml**
   - 用例：UC-ENG-009（创建MI）、UC-ENG-010（基于工艺路线生成MI草稿）、UC-ENG-011（更新MI）、UC-ENG-012（审批MI）、UC-ENG-013（发布MI）
   - 对应菜单：`/eng/mis`

8. **ENG-生产版本用例图.puml**
   - 用例：UC-ENG-014（创建生产版本）、UC-ENG-015（更新生产版本）、UC-ENG-016（发布生产版本）
   - 对应菜单：`/eng/production-versions`

### PP模块（生产计划与控制）

9. **PP-工作中心用例图.puml**
   - 用例：UC-PP-001（创建工作中心）、UC-PP-002（更新工作中心）
   - 对应菜单：`/pp/work-centers`

10. **PP-工单管理用例图.puml**
    - 用例：UC-PP-003（创建生产订单/工单）、UC-PP-004（下达生产订单/工单）、UC-PP-004A（开始生产）、UC-PP-007（完成生产订单/工单）、UC-PP-008（关闭生产订单/工单）、UC-PP-010（生产进度查看）
    - 对应菜单：`/pp/production-orders`

11. **PP-LOT卡管理用例图.puml**
    - 用例：UC-PP-009A（LOT卡生成）、UC-PP-009B（LOT卡查询）、UC-PP-009C（LOT卡列表）、UC-PP-009D（LOT卡详情查看）、UC-PP-009E（LOT卡编辑）
    - 对应菜单：`/pp/lot-cards`

12. **PP-工序报工用例图.puml**
    - 用例：UC-PP-005（创建工序报工）、UC-PP-006（更新工序报工）
    - 对应菜单：`/pp/operation-reports`

### MM模块（物料管理）

13. **MM-物料主数据用例图.puml**
    - 用例：UC-ENG-002（创建物料）、UC-ENG-002A（更新物料）、UC-MM-002（查看物料库存）、UC-MM-003（查看物料事务历史）
    - 对应菜单：`/mm/materials`

14. **MM-生产领料用例图.puml**
    - 用例：UC-MM-001（创建生产领料单）、UC-MM-002（查看物料库存）
    - 对应菜单：`/mm/material-issues`

### 用户与权限管理模块

15. **USER-用户管理用例图.puml**
    - 用例：UC-USER-001（创建用户）、UC-USER-002（更新用户）、UC-USER-003（删除用户）、UC-USER-004（用户登录）、UC-USER-005（用户登出）
    - 对应菜单：`/admin/users`

## 使用方法

1. 使用PlantUML工具或在线编辑器（如 http://www.plantuml.com/plantuml/uml/）打开.puml文件
2. 可以导出为PNG、SVG等格式
3. 所有用例图都包含参与者、用例、用例关系（包含、扩展）和说明注释

## 版本信息

- **创建日期**：2025-01-XX
- **版本**：v1.5
- **基于**：某某ERP系统用例文档 v1.5
- **需求文档**：某某ERP系统MVP版本需求规格说明书 v1.4
