# 某某ERP系统 - 业务流程文档索引

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-01-XX  
**最后更新：** 2025-01-XX

本文档是某某ERP系统业务流程文档的索引，按菜单子功能模块组织。本文档基于需求规格说明书v1.4编写。

---

## 文档结构

### SD模块（销售与分销）

1. **[客户管理业务流程](./workflow-sd-customers.md)**
   - 客户创建流程
   - 客户审批流程

2. **[报价单业务流程](./workflow-sd-quotations.md)**
   - 销售报价流程
   - 报价转订单流程
   - 报价单状态说明

3. **[销售订单业务流程](./workflow-sd-sales-orders.md)**
   - 返单快速下单流程
   - 新单下单流程
   - 销售订单评审流程
   - 销售订单状态说明

### ENG模块（工程管理）

4. **[BOM管理业务流程](./workflow-eng-boms.md)**
   - BOM创建流程
   - BOM审核发布流程
   - BOM状态说明

5. **[工艺路线管理业务流程](./workflow-eng-routings.md)**
   - 工艺路线创建流程
   - 工艺路线审核发布流程
   - 工艺路线状态说明

6. **[生产版本管理业务流程](./workflow-eng-production-versions.md)**
   - 生产版本建立流程
   - 生产版本发布流程
   - 生产版本状态说明

7. **[MI管理业务流程](./workflow-eng-mis.md)**
   - MI创建流程
   - MI审核发布流程
   - MI状态说明

8. **[产品主数据管理业务流程](./workflow-eng-products.md)**
   - 产品主数据创建流程
   - 产品主数据特点说明

### PP模块（生产计划与控制）

9. **[工作中心管理业务流程](./workflow-pp-work-centers.md)**
   - 工作中心创建流程
   - 工作中心激活/停用流程

10. **[工单管理业务流程](./workflow-pp-production-orders.md)**
    - 生产订单创建流程
    - 生产订单关闭流程
    - 生产订单状态说明

11. **[LOT卡管理业务流程](./workflow-pp-lot-cards.md)**
    - LOT卡生成流程
    - LOT卡特点说明

12. **[工序报工业务流程](./workflow-pp-operation-reports.md)**
    - 工序报工流程
    - 报工规则说明

### MM模块（物料管理）

13. **[物料主数据管理业务流程](./workflow-mm-materials.md)**
    - 物料创建流程
    - 物料审核激活流程
    - 物料主数据特点

14. **[生产领料业务流程](./workflow-mm-material-issues.md)**
    - 生产领料流程
    - 领料规则说明

### 跨模块流程

15. **[跨模块业务流程](./workflow-cross-module.md)**
    - 完整订单到生产流程
    - 跨模块流程规则说明

---

## 完整文档

- **[完整业务流程文档（Markdown格式）](./workflow.md)** - 包含所有流程的完整版本（Markdown格式）
- **[完整工作流模型文档（PlantUML格式）](../某某ERP系统%20-%20工作流模型.puml)** - 包含所有流程的完整版本（PlantUML格式）

## PlantUML格式工作流文档

所有工作流也提供PlantUML格式，位于同一目录下，文件名以`.puml`结尾：

- **[工作流模型文档索引（PlantUML格式）](./README.md)** - PlantUML格式工作流文档索引

---

## 相关文档

- [需求规格说明书](../需求/某某ERP系统MVP版本需求规格说明书1.4.md)
- [用例文档](./某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [状态机模型](./某某ERP系统%20-%20状态机模型（State%20Machine）.md)
- [事件模型](./某某ERP系统%20-%20事件模型（Event%20Model）.md)
- [服务模型](./某某ERP系统%20-%20服务模型（Service%20Contracts）.md)

---

**文档版本：** v1.4  
**最后更新：** 2025-01-XX  
**维护者：** 开发团队

