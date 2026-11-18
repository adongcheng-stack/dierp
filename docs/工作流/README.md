# 某某ERP系统 - 工作流模型文档索引

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-01-XX  
**最后更新：** 2025-01-XX

**基于**：某某ERP系统MVP版本需求规格说明书 v1.4

本文档是某某ERP系统工作流模型（PlantUML格式）文档的索引，按菜单子功能模块组织。所有工作流使用PlantUML活动图格式。

---

## 文档结构

### SD模块（销售与分销）

1. **[客户管理工作流](./workflow-sd-customers.puml)**
   - 客户管理流程

2. **[报价单工作流](./workflow-sd-quotations.puml)**
   - 销售报价流程
   - 报价转订单流程

3. **[销售订单工作流](./workflow-sd-sales-orders.puml)**
   - 返单快速下单流程
   - 新单下单流程
   - 销售订单评审流程

### ENG模块（工程管理）

4. **[BOM管理工作流](./workflow-eng-boms.puml)**
   - BOM管理流程

5. **[工艺路线工作流](./workflow-eng-routings.puml)**
   - 工艺路线管理流程

6. **[MI管理工作流](./workflow-eng-mi.puml)**
   - MI管理流程

7. **[生产版本工作流](./workflow-eng-production-versions.puml)**
   - 生产版本管理流程

### PP模块（生产计划与控制）

8. **[工单管理工作流](./workflow-pp-production-orders.puml)**
   - 生产订单创建流程
   - 开始生产流程
   - 生产订单关闭流程

9. **[生产领料工作流](./workflow-pp-material-issues.puml)**
   - 生产领料流程

10. **[工序报工工作流](./workflow-pp-operation-reports.puml)**
    - 工序报工流程

### MM模块（物料管理）

11. **[物料主数据工作流](./workflow-mm-materials.puml)**
    - 物料主数据管理流程

### 跨模块流程

12. **[跨模块工作流](./workflow-cross-module.puml)**
    - 完整订单到生产流程

---

## 完整文档

- **[完整工作流模型文档](../某某ERP系统%20-%20工作流模型.puml)** - 包含所有流程的完整版本

---

## 使用方法

1. **使用PlantUML工具**：
   - 下载PlantUML工具：http://plantuml.com/download
   - 使用命令行工具或IDE插件打开.puml文件

2. **在线编辑器**：
   - 访问 http://www.plantuml.com/plantuml/uml/
   - 复制.puml文件内容到编辑器
   - 可以导出为PNG、SVG等格式

3. **VS Code插件**：
   - 安装"PlantUML"插件
   - 打开.puml文件，按Alt+D预览

4. **导出图片**：
   - 使用PlantUML CLI：`java -jar plantuml.jar workflow-*.puml`
   - 或使用在线工具导出

---

## 相关文档

- [需求规格说明书](../../需求/某某ERP系统MVP版本需求规格说明书1.4.md)
- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [工作流文档（Markdown格式）](./workflow-index.md)
- [状态机模型](../某某ERP系统%20-%20状态机模型（State%20Machine）.md)
- [事件模型](../某某ERP系统%20-%20事件模型（Event%20Model）.md)
- [服务模型](../某某ERP系统%20-%20服务模型（Service%20Contracts）.md)

---

**文档版本：** v1.4  
**最后更新：** 2025-01-XX  
**维护者：** 开发团队

