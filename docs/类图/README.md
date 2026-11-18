# 某某ERP系统 - 类图文档索引

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-01-XX  
**最后更新：** 2025-01-XX

**基于**：某某ERP系统MVP版本需求规格说明书 v1.4

本文档是某某ERP系统类图文档的索引，按菜单子功能模块组织。所有类图使用Mermaid语法描述。

---

## 文档结构

### SD模块（销售与分销）

1. **[客户管理类图](./class-diagram-sd-customers.md)**
   - Customer（客户）
   - CustomerAddress（客户地址）
   - CustomerContact（客户联系人）
   - CustomerPartnerFunction（客户合作伙伴功能）
   - CustomerSalesData（客户销售数据）

2. **[报价单类图](./class-diagram-sd-quotations.md)**
   - Quotation（报价单）
   - QuotationItem（报价单明细）
   - Customer（客户）

3. **[销售订单类图](./class-diagram-sd-sales-orders.md)**
   - SalesOrder（销售订单）
   - ContractReview（合同评审）
   - Customer（客户）
   - Quotation（报价单）
   - Material（物料）
   - ProductionVersion（生产版本）

4. **[本厂编号映射类图](./class-diagram-sd-factory-product-mappings.md)**
   - FactoryProductMapping（本厂编号映射）
   - Customer（客户）
   - Material（物料）
   - ProductionVersion（生产版本）

### ENG模块（工程管理）

5. **[产品主数据类图](./class-diagram-eng-products.md)**
   - Material（物料，FG类型）
   - FactoryProductMapping（本厂编号映射）

6. **[BOM管理类图](./class-diagram-eng-boms.md)**
   - BOM（物料清单）
   - BOMItem（BOM明细）
   - Material（物料）

7. **[工艺路线类图](./class-diagram-eng-routings.md)**
   - Routing（工艺路线）
   - RoutingOperation（工艺路线工序）
   - Material（物料）
   - WorkCenter（工作中心）

8. **[MI管理类图](./class-diagram-eng-mis.md)**
   - MI（制造指令）
   - Material（物料）

9. **[生产版本类图](./class-diagram-eng-production-versions.md)**
   - ProductionVersion（生产版本）
   - Material（物料）
   - BOM（物料清单）
   - Routing（工艺路线）
   - MI（制造指令）

### PP模块（生产计划与控制）

10. **[工作中心类图](./class-diagram-pp-work-centers.md)**
    - WorkCenter（工作中心）

11. **[工单管理类图](./class-diagram-pp-production-orders.md)**
    - ProductionOrder（生产订单/工单）
    - SalesOrder（销售订单）
    - Material（物料）
    - ProductionVersion（生产版本）

12. **[LOT卡管理类图](./class-diagram-pp-lot-cards.md)**
    - LotCard（LOT卡）
    - ProductionOrder（生产订单/工单）
    - MI（制造指令）
    - Material（物料）

13. **[工序报工类图](./class-diagram-pp-operation-reports.md)**
    - OperationReport（工序报工）
    - ProductionOrder（生产订单/工单）
    - RoutingOperation（工艺路线工序）
    - WorkCenter（工作中心）
    - LotCard（LOT卡）

### MM模块（物料管理）

14. **[物料主数据类图](./class-diagram-mm-materials.md)**
    - Material（物料，非FG类型）
    - MaterialTransaction（物料事务）

15. **[生产领料类图](./class-diagram-mm-material-issues.md)**
    - MaterialIssue（生产领料）
    - MaterialTransaction（物料事务）
    - ProductionOrder（生产订单/工单）
    - Material（物料）

### 跨模块类图

16. **[跨模块关系类图](./class-diagram-cross-module.md)**
    - 核心业务流程类关系
    - 跨模块类关系链

---

## 完整文档

- **[完整类图文档](../某某ERP系统%20-%20类图（Class%20Diagram）.md)** - 包含所有类图的完整版本

---

## 相关文档

- [需求规格说明书](../需求/某某ERP系统MVP版本需求规格说明书1.4.md)
- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [状态机模型](../某某ERP系统%20-%20状态机模型（State%20Machine）.md)
- [事件模型](../某某ERP系统%20-%20事件模型（Event%20Model）.md)
- [服务模型](../某某ERP系统%20-%20服务模型（Service%20Contracts）.md)
- [ER图文档](../ER图/)
- [工作流文档](../工作流/)

---

## 类图使用说明

### 类图格式

所有类图使用Mermaid语法编写，支持以下工具查看：

1. **在线查看**：GitHub、GitLab等平台自动渲染Mermaid图表
2. **VS Code插件**：安装"Markdown Preview Mermaid Support"插件
3. **在线编辑器**：https://mermaid.live/
4. **导出图片**：使用Mermaid CLI或在线工具导出为PNG/SVG

### 类图符号说明

- **类名**：使用PascalCase（如 `Customer`, `SalesOrder`）
- **属性名**：使用camelCase（如 `customerId`, `orderNumber`）
- **关系名**：使用动词短语（如 `has`, `contains`, `references`）
- **可见性**：
  - `+` 表示 public（公共）
  - `-` 表示 private（私有）
  - `#` 表示 protected（受保护）
  - `~` 表示 package（包内可见）

### 关系类型说明

- **1 --> ***: 一对多关系（One-to-Many）
- **1 --> 1**: 一对一关系（One-to-One）
- **-->**: 关联关系（Association）

---

**文档版本：** v1.4  
**最后更新：** 2025-01-XX  
**维护者：** 开发团队

