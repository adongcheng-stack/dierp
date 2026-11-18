# 某某ERP系统 - 用例文档索引

## 文档说明

**版本：** v1.5  
**创建日期：** 2025-12-12  
**最后更新：** 2025-01-XX

本文档是某某ERP系统用例文档的索引，按照菜单子功能模块组织，方便快速查找和导航。

---

## 一、销售与分销模块（SD Module）

### 1.1 客户管理
- **[use-cases-sd-customers.md](./use-cases-sd-customers.md)**
  - UC-SD-001: 创建客户
  - UC-SD-002: 审批客户

### 1.2 报价单管理
- **[use-cases-sd-quotations.md](./use-cases-sd-quotations.md)**
  - UC-SD-004: 创建报价单
  - UC-SD-005: 提交报价单审批
  - UC-SD-006: 审批报价单
  - UC-SD-007: 拒绝报价单
  - UC-SD-008: 重新提交报价单
  - UC-SD-009: 销售员经客户确认报价单

### 1.3 销售订单管理
- **[use-cases-sd-sales-orders.md](./use-cases-sd-sales-orders.md)**
  - UC-SD-003: 创建本厂编号映射
  - UC-SD-010: 创建销售订单
  - UC-SD-011: 提交销售订单评审
  - UC-SD-012: 销售部门评审订单
  - UC-SD-013: 工程部门评审订单
  - UC-SD-014: 物料部门评审订单
  - UC-SD-015: 财务部门评审订单
  - UC-SD-016: 拒绝销售订单
  - UC-SD-017: 销售发货
  - UC-SD-018: 销售签收
  - UC-SD-019: 对账
  - UC-SD-020: 关闭销售订单

---

## 二、工程管理模块（ENG Module）

### 2.1 产品主数据管理
- **[use-cases-eng-products.md](./use-cases-eng-products.md)**
  - UC-ENG-001: 产品主数据管理
  - UC-ENG-001A: 产品列表查询

### 2.2 BOM管理
- **[use-cases-eng-boms.md](./use-cases-eng-boms.md)**
  - UC-ENG-002: 创建物料
  - UC-ENG-002A: 更新物料
  - UC-ENG-003: 创建BOM
  - UC-ENG-004: 更新BOM
  - UC-ENG-005: 发布BOM

### 2.3 工艺路线管理
- **[use-cases-eng-routings.md](./use-cases-eng-routings.md)**
  - UC-ENG-006: 创建工艺路线
  - UC-ENG-007: 更新工艺路线
  - UC-ENG-008: 发布工艺路线

### 2.4 MI管理
- **[use-cases-eng-mis.md](./use-cases-eng-mis.md)**
  - UC-ENG-009: 创建MI
  - UC-ENG-010: 基于工艺路线生成MI草稿
  - UC-ENG-011: 更新MI
  - UC-ENG-012: 审批MI
  - UC-ENG-013: 发布MI

### 2.5 生产版本管理
- **[use-cases-eng-production-versions.md](./use-cases-eng-production-versions.md)**
  - UC-ENG-014: 创建生产版本
  - UC-ENG-015: 更新生产版本
  - UC-ENG-016: 发布生产版本

---

## 三、物料管理模块（MM Module）

### 3.1 物料主数据管理
- **[use-cases-mm-materials.md](./use-cases-mm-materials.md)**
  - UC-MM-002: 查看物料库存
  - UC-MM-003: 查看物料事务历史

**说明**：物料主数据的创建和更新用例在ENG模块中（UC-ENG-002和UC-ENG-002A），因为物料主数据由工程管理模块统一管理。

### 3.2 生产领料
- **[use-cases-mm-material-issues.md](./use-cases-mm-material-issues.md)**
  - UC-MM-001: 创建生产领料单
  - UC-MM-002: 查看物料库存
  - UC-MM-003: 查看物料事务历史

---

## 四、生产计划与控制模块（PP Module）

### 4.1 工作中心管理
- **[use-cases-pp-work-centers.md](./use-cases-pp-work-centers.md)**
  - UC-PP-001: 创建工作中心
  - UC-PP-002: 更新工作中心

### 4.2 工单管理
- **[use-cases-pp-production-orders.md](./use-cases-pp-production-orders.md)**
  - UC-PP-003: 创建生产订单/工单
  - UC-PP-004: 下达生产订单/工单
  - UC-PP-004A: 开始生产
  - UC-PP-007: 完成生产订单/工单
  - UC-PP-008: 关闭生产订单/工单
  - UC-PP-010: 生产进度查看

### 4.3 LOT卡管理
- **[use-cases-pp-lot-cards.md](./use-cases-pp-lot-cards.md)**
  - UC-PP-009: LOT卡管理
  - UC-PP-009A: LOT卡生成
  - UC-PP-009B: LOT卡查询
  - UC-PP-009C: LOT卡列表
  - UC-PP-009D: LOT卡详情查看
  - UC-PP-009E: LOT卡编辑

### 4.4 工序报工
- **[use-cases-pp-operation-reports.md](./use-cases-pp-operation-reports.md)**
  - UC-PP-005: 创建工序报工
  - UC-PP-006: 更新工序报工

---

## 五、用户与权限管理模块

### 5.1 用户管理
- **[use-cases-user-management.md](./use-cases-user-management.md)**
  - UC-USER-001: 创建用户
  - UC-USER-002: 更新用户
  - UC-USER-003: 删除用户
  - UC-USER-004: 用户登录
  - UC-USER-005: 用户登出

---

## 六、用例统计

### 6.1 按模块统计

| 模块 | 用例数量 | 高优先级 | 中优先级 | 低优先级 |
|------|---------|---------|---------|---------|
| SD（销售与分销） | 20 | 15 | 4 | 1 |
| ENG（工程管理） | 16 | 12 | 3 | 1 |
| PP（生产计划与控制） | 13 | 9 | 3 | 1 |
| MM（物料管理） | 3 | 2 | 1 | 0 |
| 用户与权限管理 | 5 | 1 | 3 | 1 |
| **总计** | **57** | **39** | **14** | **4** |

### 6.2 按功能统计

- **客户管理**：2个用例
- **报价单管理**：6个用例
- **销售订单管理**：12个用例
- **产品主数据管理**：2个用例
- **BOM管理**：5个用例
- **工艺路线管理**：3个用例
- **MI管理**：5个用例
- **生产版本管理**：3个用例
- **物料主数据管理**：2个用例
- **生产领料**：3个用例
- **工作中心管理**：2个用例
- **工单管理**：6个用例
- **LOT卡管理**：6个用例
- **工序报工**：2个用例
- **用户管理**：5个用例

---

## 七、相关文档

- [完整用例文档](./某某ERP系统02%20-%20用例（Use%20Cases）.md)
- [业务流程文档](./workflow.md)
- [需求规格说明书](../需求/某某ERP系统MVP版本需求规格说明书1.4.md)
- [领域模型文档](./某某ERP系统01%20-%20领域模型（Domain%20Model）.md)
- [用户故事文档](./某某ERP系统03%20-%20用户故事（User%20Stories）.md)

---

## 八、快速导航

### 按业务场景查找

#### 销售业务流程
1. [客户管理](./use-cases-sd-customers.md) → [报价单管理](./use-case-sd-quotations.md) → [销售订单管理](./use-case-sd-sales-orders.md)

#### 工程数据准备流程
1. [产品主数据管理](./use-cases-eng-products.md) → [BOM管理](./use-cases-eng-boms.md) → [工艺路线管理](./use-cases-eng-routings.md) → [MI管理](./use-cases-eng-mis.md) → [生产版本管理](./use-cases-eng-production-versions.md)

#### 生产执行流程
1. [工单管理](./use-cases-pp-production-orders.md) → [生产领料](./use-cases-mm-material-issues.md) → [工序报工](./use-cases-pp-operation-reports.md) → [LOT卡管理](./use-cases-pp-lot-cards.md)

---

**文档版本：** v1.5  
**最后更新：** 2025-01-XX  
**维护者：** 开发团队

