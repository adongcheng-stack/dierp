# 某某ERP系统 - 事件模型（Event Model）

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-12-12  
**最后更新：** 2025-01-XX

**基于**：某某ERP系统MVP版本需求规格说明书 v1.4

本文档描述了某某ERP系统的事件模型，包括事件定义、事件分类、事件发布和订阅机制、事件存储和处理。事件模型采用事件驱动架构（Event-Driven Architecture, EDA）设计原则，支持系统解耦、异步处理和实时响应。

---

## 一、事件模型概述

### 1.1 设计原则

1. **事件不可变性**：事件一旦发布，不可修改，只能追加新事件
2. **事件溯源**：通过事件序列可以重建系统状态
3. **最终一致性**：系统通过事件实现最终一致性，而非强一致性
4. **解耦性**：事件发布者和订阅者相互独立，降低系统耦合
5. **可追溯性**：所有事件都记录时间戳、操作人和上下文信息
6. **幂等性**：事件处理支持幂等性，可安全重试

### 1.2 事件驱动架构

```
┌─────────────┐
│  业务服务   │
│  (Service)  │
└──────┬──────┘
       │ 发布事件
       ▼
┌─────────────┐
│  事件总线   │
│ (Event Bus) │
└──────┬──────┘
       │ 分发事件
       ├──────────┬──────────┬──────────┐
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 事件订阅 │ │ 事件订阅 │ │ 事件订阅 │ │ 事件存储 │
│ 服务A    │ │ 服务B    │ │ 服务C    │ │ (Store)  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 1.3 事件分类

根据事件的性质和用途，事件分为以下几类：

- **领域事件（Domain Events）**：业务领域内发生的重要业务事件
- **集成事件（Integration Events）**：跨服务、跨系统的集成事件
- **系统事件（System Events）**：系统级别的技术事件
- **审计事件（Audit Events）**：用于审计追踪的事件

---

## 二、事件定义规范

### 2.1 事件结构

所有事件都遵循统一的事件结构：

```json
{
  "event_id": "evt_20251212_001",
  "event_type": "quotation.submitted",
  "event_version": "1.0",
  "timestamp": "2025-12-12T10:30:00Z",
  "source": "sd-service",
  "correlation_id": "corr_123456",
  "causation_id": "evt_20251212_000",
  "user_id": "user001",
  "user_role": "SALES",
  "payload": {
    "quotation_number": "QT-2025-001",
    "customer_id": "CUST001",
    "total_amount": 10000.00,
    "status": "PENDING_SALES"
  },
  "metadata": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "request_id": "req_123456"
  }
}
```

### 2.2 事件字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| event_id | String | 是 | 事件唯一标识 |
| event_type | String | 是 | 事件类型（命名空间.动作） |
| event_version | String | 是 | 事件版本号 |
| timestamp | DateTime | 是 | 事件发生时间（UTC） |
| source | String | 是 | 事件来源服务 |
| correlation_id | String | 是 | 关联ID（用于追踪相关事件） |
| causation_id | String | 否 | 因果ID（触发当前事件的上一个事件） |
| user_id | String | 是 | 操作人ID |
| user_role | String | 是 | 操作人角色 |
| payload | Object | 是 | 事件负载（业务数据） |
| metadata | Object | 否 | 元数据（技术信息） |

### 2.3 事件命名规范

事件类型采用分层命名空间：

```
<模块>.<实体>.<动作>

示例：
- sd.quotation.submitted
- sd.quotation.approved
- eng.bom.released
- pp.production_order.completed
```

---

## 三、销售与分销模块事件（SD Events）

### 3.1 客户相关事件

#### 3.1.1 customer.created

**事件类型**：`sd.customer.created`  
**触发时机**：客户创建完成  
**事件负载**：

```json
{
  "customer_id": "CUST001",
  "legal_name": "XX科技有限公司",
  "trade_name": "XX科技",
  "customer_status": "DRAFT",
  "created_by": "user001"
}
```

**订阅者**：
- 通知服务（发送欢迎邮件）
- 审计服务（记录审计日志）

#### 3.1.2 customer.submitted

**事件类型**：`sd.customer.submitted`  
**触发时机**：客户提交审批  
**事件负载**：

```json
{
  "customer_id": "CUST001",
  "customer_status": "PENDING_APPROVAL",
  "submitted_by": "user001"
}
```

**订阅者**：
- 工作流服务（启动审批流程）
- 通知服务（通知审批人）

#### 3.1.3 customer.approved

**事件类型**：`sd.customer.approved`  
**触发时机**：客户审批通过  
**事件负载**：

```json
{
  "customer_id": "CUST001",
  "customer_status": "ACTIVE",
  "approver": "sales_mgr001",
  "approved_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知创建人）
- 审计服务（记录审批日志）

#### 3.1.4 customer.blocked

**事件类型**：`sd.customer.blocked`  
**触发时机**：客户被冻结  
**事件负载**：

```json
{
  "customer_id": "CUST001",
  "customer_status": "BLOCKED",
  "blocked_by": "admin001",
  "block_reason": "信用额度超限",
  "blocked_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 订单服务（禁止创建新订单）
- 通知服务（通知相关人员）

### 3.2 报价单相关事件

#### 3.2.1 quotation.created

**事件类型**：`sd.quotation.created`  
**触发时机**：报价单创建完成  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "customer_id": "CUST001",
  "product_number": "HS1004ENIGAB01",
  "quantity": 100,
  "unit_price": 10.00,
  "total_amount": 1000.00,
  "status": "DRAFT",
  "created_by": "user001"
}
```

#### 3.2.2 quotation.submitted

**事件类型**：`sd.quotation.submitted`  
**触发时机**：报价单提交审批  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "customer_id": "CUST001",
  "total_amount": 1000.00,
  "status": "PENDING_SALES",
  "submitted_by": "user001"
}
```

**订阅者**：
- 工作流服务（启动审批流程）
- 通知服务（通知销售经理）

#### 3.2.3 quotation.sales_approved

**事件类型**：`sd.quotation.sales_approved`  
**触发时机**：销售部门审批通过  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "status": "PENDING_FINANCE",
  "sales_approver": "sales_mgr001",
  "sales_approved_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知财务部门）

#### 3.2.4 quotation.finance_approved

**事件类型**：`sd.quotation.finance_approved`  
**触发时机**：财务部门审批通过  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "status": "PENDING_GENERAL_MANAGER",
  "finance_approver": "finance001",
  "finance_approved_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知总经办）

#### 3.2.5 quotation.approved

**事件类型**：`sd.quotation.approved`  
**触发时机**：所有审批通过  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "status": "APPROVED",
  "general_manager_approver": "gm001",
  "approved_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知业务员和客户）
- 审计服务（记录审批完成）

#### 3.2.6 quotation.rejected

**事件类型**：`sd.quotation.rejected`  
**触发时机**：报价单被拒绝  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "status": "REJECTED",
  "rejected_by": "sales_mgr001",
  "reject_reason": "价格不合理",
  "rejected_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知业务员）

#### 3.2.7 quotation.customer_confirmed

**事件类型**：`sd.quotation.customer_confirmed`  
**触发时机**：客户确认报价单  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "status": "CUSTOMER_CONFIRMED",
  "customer_confirmed_at": "2025-12-12T10:30:00Z",
  "confirmed_by": "user001"
}
```

**订阅者**：
- 通知服务（通知业务员可以创建销售订单）

#### 3.2.8 quotation.linked

**事件类型**：`sd.quotation.linked`  
**触发时机**：报价单关联到销售订单  
**事件负载**：

```json
{
  "quotation_number": "QT-2025-001",
  "sales_order_number": "SO-2025-001",
  "status": "LINKED",
  "linked_at": "2025-12-12T10:30:00Z"
}
```

### 3.3 销售订单相关事件

#### 3.3.1 sales_order.created

**事件类型**：`sd.sales_order.created`  
**触发时机**：销售订单创建完成  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "quotation_number": "QT-2025-001",
  "customer_id": "CUST001",
  "product_number": "HS1004ENIGAB01",
  "material_code": "MAT001",
  "production_version_id": "PV001",
  "quantity": 100,
  "total_amount": 1000.00,
  "status": "DRAFT",
  "is_return_order": false,
  "created_by": "user001"
}
```

#### 3.3.2 sales_order.submitted

**事件类型**：`sd.sales_order.submitted`  
**触发时机**：销售订单提交评审  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "PENDING_REVIEW",
  "submitted_by": "user001"
}
```

**订阅者**：
- 工作流服务（启动订单评审流程）
- 通知服务（通知各部门评审人）

#### 3.3.3 sales_order.review_started

**事件类型**：`sd.sales_order.review_started`  
**触发时机**：订单评审开始  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "REVIEWING",
  "review_departments": ["SALES", "ENGINEER", "MATERIAL", "FINANCE"]
}
```

#### 3.3.4 sales_order.department_reviewed

**事件类型**：`sd.sales_order.department_reviewed`  
**触发时机**：某个部门完成评审  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "reviewer_role": "ENGINEER",
  "reviewer": "engineer001",
  "review_result": "APPROVED",
  "review_comment": "工程数据完整",
  "reviewed_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 工作流服务（更新评审进度）
- 通知服务（通知下一个评审部门）

#### 3.3.5 sales_order.approved

**事件类型**：`sd.sales_order.approved`  
**触发时机**：所有部门评审通过  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "APPROVED",
  "all_departments_approved": true,
  "approved_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 生产服务（可以创建生产订单）
- 通知服务（通知业务员和计划员）

#### 3.3.6 sales_order.rejected

**事件类型**：`sd.sales_order.rejected`  
**触发时机**：订单评审被拒绝  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "REJECTED",
  "rejected_by": "engineer001",
  "reject_reason": "工程数据不完整",
  "rejected_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知业务员）

#### 3.3.7 sales_order.production_started

**事件类型**：`sd.sales_order.production_started`  
**触发时机**：创建生产订单，开始生产  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "IN_PRODUCTION",
  "production_order_number": "PO-2025-001",
  "started_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 物料服务（准备生产领料）
- 通知服务（通知生产部门）

#### 3.3.8 sales_order.completed

**事件类型**：`sd.sales_order.completed`  
**触发时机**：生产完成  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "COMPLETED",
  "completed_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知业务员可以发货）

#### 3.3.9 sales_order.shipped

**事件类型**：`sd.sales_order.shipped`  
**触发时机**：货物已发出  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "SHIPPED",
  "shipping_date": "2025-12-12",
  "tracking_number": "SF1234567890",
  "shipped_by": "user001"
}
```

**订阅者**：
- 通知服务（通知客户）
- 财务服务（准备对账）

#### 3.3.10 sales_order.delivered

**事件类型**：`sd.sales_order.delivered`  
**触发时机**：客户已签收  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "DELIVERED",
  "delivered_at": "2025-12-12T10:30:00Z",
  "signed_by": "客户签收人"
}
```

**订阅者**：
- 财务服务（触发对账流程）

#### 3.3.11 sales_order.reconciled

**事件类型**：`sd.sales_order.reconciled`  
**触发时机**：财务已对账  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "RECONCILED",
  "reconciled_by": "finance001",
  "reconciled_at": "2025-12-12T10:30:00Z"
}
```

#### 3.3.12 sales_order.closed

**事件类型**：`sd.sales_order.closed`  
**触发时机**：订单关闭  
**事件负载**：

```json
{
  "order_number": "SO-2025-001",
  "status": "CLOSED",
  "closed_by": "user001",
  "closed_at": "2025-12-12T10:30:00Z"
}
```

---

## 四、工程管理模块事件（ENG Events）

### 4.1 BOM相关事件

#### 4.1.1 bom.created

**事件类型**：`eng.bom.created`  
**触发时机**：BOM创建完成  
**事件负载**：

```json
{
  "bom_number": "BOM-001",
  "parent_material_code": "MAT001",
  "version": "1.0",
  "status": "NEW",
  "created_by": "engineer001"
}
```

#### 4.1.2 bom.submitted

**事件类型**：`eng.bom.submitted`  
**触发时机**：BOM提交审核  
**事件负载**：

```json
{
  "bom_number": "BOM-001",
  "status": "REVIEWING",
  "submitted_by": "engineer001"
}
```

#### 4.1.3 bom.released

**事件类型**：`eng.bom.released`  
**触发时机**：BOM审核通过并发布  
**事件负载**：

```json
{
  "bom_number": "BOM-001",
  "status": "RELEASED",
  "released_by": "engineer001",
  "released_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 生产版本服务（可用于创建生产版本）
- 审计服务（记录发布日志）

### 4.2 工艺路线相关事件

#### 4.2.1 routing.created

**事件类型**：`eng.routing.created`  
**触发时机**：工艺路线创建完成  
**事件负载**：

```json
{
  "routing_id": "RT-001",
  "material_code": "MAT001",
  "version": "1.0",
  "status": "DRAFT",
  "created_by": "engineer001"
}
```

#### 4.2.2 routing.released

**事件类型**：`eng.routing.released`  
**触发时机**：工艺路线发布  
**事件负载**：

```json
{
  "routing_id": "RT-001",
  "status": "RELEASED",
  "released_by": "engineer001",
  "released_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 生产版本服务（可用于创建生产版本）
- 生产服务（可用于生产订单）

### 4.3 MI相关事件

#### 4.3.1 mi.created

**事件类型**：`eng.mi.created`  
**触发时机**：MI创建完成  
**事件负载**：

```json
{
  "mi_number": "MI-001",
  "material_code": "MAT001",
  "version": "1.0",
  "status": "DRAFT",
  "created_by": "engineer001"
}
```

#### 4.3.2 mi.submitted

**事件类型**：`eng.mi.submitted`  
**触发时机**：MI提交审核  
**事件负载**：

```json
{
  "mi_number": "MI-001",
  "status": "REVIEWING",
  "submitted_by": "engineer001"
}
```

**订阅者**：
- 通知服务（通知审核人）

#### 4.3.3 mi.approved

**事件类型**：`eng.mi.approved`  
**触发时机**：MI审核通过  
**事件负载**：

```json
{
  "mi_number": "MI-001",
  "status": "APPROVED",
  "approver": "engineer002",
  "approved_at": "2025-12-12T10:30:00Z"
}
```

#### 4.3.4 mi.released

**事件类型**：`eng.mi.released`  
**触发时机**：MI发布  
**事件负载**：

```json
{
  "mi_number": "MI-001",
  "status": "RELEASED",
  "released_by": "engineer001",
  "released_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 生产版本服务（可用于创建生产版本）

### 4.4 生产版本相关事件

#### 4.4.1 production_version.created

**事件类型**：`eng.production_version.created`  
**触发时机**：生产版本创建完成  
**事件负载**：

```json
{
  "production_version_id": "PV-001",
  "material_code": "MAT001",
  "bom_number": "BOM-001",
  "routing_id": "RT-001",
  "mi_number": "MI-001",
  "version": "1.0",
  "status": "ACTIVE",
  "created_by": "engineer001"
}
```

**订阅者**：
- 销售服务（可用于创建销售订单）
- 生产服务（可用于创建生产订单）

---

## 五、生产计划与控制模块事件（PP Events）

### 5.1 工作中心相关事件

#### 5.1.1 work_center.created

**事件类型**：`pp.work_center.created`  
**触发时机**：工作中心创建完成  
**事件负载**：

```json
{
  "work_center_id": "WC-001",
  "description": "钻孔工作中心",
  "work_center_type": "MACHINE",
  "status": "ACTIVE",
  "created_by": "engineer001"
}
```

#### 5.1.2 work_center.maintenance_started

**事件类型**：`pp.work_center.maintenance_started`  
**触发时机**：工作中心开始维护  
**事件负载**：

```json
{
  "work_center_id": "WC-001",
  "status": "IN_MAINTENANCE",
  "maintenance_started_at": "2025-12-12T10:30:00Z",
  "started_by": "engineer001"
}
```

**订阅者**：
- 生产服务（暂停分配生产任务）
- 通知服务（通知相关人员）

#### 5.1.3 work_center.maintenance_completed

**事件类型**：`pp.work_center.maintenance_completed`  
**触发时机**：工作中心维护完成  
**事件负载**：

```json
{
  "work_center_id": "WC-001",
  "status": "ACTIVE",
  "maintenance_completed_at": "2025-12-12T10:30:00Z",
  "completed_by": "engineer001"
}
```

**订阅者**：
- 生产服务（恢复分配生产任务）

### 5.2 生产订单相关事件

#### 5.2.1 production_order.created

**事件类型**：`pp.production_order.created`  
**触发时机**：生产订单创建完成  
**事件负载**：

```json
{
  "order_number": "PO-2025-001",
  "sales_order_number": "SO-2025-001",
  "material_code": "MAT001",
  "production_version_id": "PV-001",
  "quantity": 100,
  "status": "DRAFT",
  "created_by": "planner001"
}
```

#### 5.2.2 production_order.released

**事件类型**：`pp.production_order.released`  
**触发时机**：生产订单下达  
**事件负载**：

```json
{
  "order_number": "PO-2025-001",
  "status": "RELEASED",
  "planned_start_date": "2025-12-15",
  "planned_finish_date": "2025-12-20",
  "released_by": "planner001",
  "released_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 物料服务（准备生产领料）
- 通知服务（通知生产部门）

#### 5.2.3 production_order.started

**事件类型**：`pp.production_order.started`  
**触发时机**：生产订单开始生产  
**事件负载**：

```json
{
  "order_number": "PO-2025-001",
  "status": "IN_PRODUCTION",
  "actual_start_date": "2025-12-15T08:00:00Z",
  "started_by": "production001"
}
```

**订阅者**：
- 销售服务（更新销售订单状态为IN_PRODUCTION）

#### 5.2.4 production_order.completed

**事件类型**：`pp.production_order.completed`  
**触发时机**：生产订单完成  
**事件负载**：

```json
{
  "order_number": "PO-2025-001",
  "status": "COMPLETED",
  "actual_finish_date": "2025-12-20T18:00:00Z",
  "completed_quantity": 100,
  "good_quantity": 98,
  "scrap_quantity": 2
}
```

**订阅者**：
- 销售服务（更新销售订单状态为COMPLETED）
- 物料服务（成品入库）
- 通知服务（通知业务员）

#### 5.2.5 production_order.closed

**事件类型**：`pp.production_order.closed`  
**触发时机**：生产订单关闭  
**事件负载**：

```json
{
  "order_number": "PO-2025-001",
  "status": "CLOSED",
  "closed_by": "planner001",
  "closed_at": "2025-12-21T10:30:00Z"
}
```

### 5.3 工序报工相关事件

#### 5.3.1 operation_report.created

**事件类型**：`pp.operation_report.created`  
**触发时机**：工序报工记录创建  
**事件负载**：

```json
{
  "report_number": "OR-2025-001",
  "production_order_number": "PO-2025-001",
  "operation_no": "10",
  "work_center_id": "WC-001",
  "status": "PENDING",
  "created_by": "production001"
}
```

#### 5.3.2 operation_report.started

**事件类型**：`pp.operation_report.started`  
**触发时机**：开始报工  
**事件负载**：

```json
{
  "report_number": "OR-2025-001",
  "status": "IN_PROGRESS",
  "reported_by": "production001",
  "started_at": "2025-12-15T08:00:00Z"
}
```

#### 5.3.3 operation_report.completed

**事件类型**：`pp.operation_report.completed`  
**触发时机**：报工完成  
**事件负载**：

```json
{
  "report_number": "OR-2025-001",
  "status": "COMPLETED",
  "reported_quantity": 100,
  "good_quantity": 98,
  "scrap_quantity": 2,
  "setup_time": 30,
  "machine_time": 120,
  "labor_time": 60,
  "completed_at": "2025-12-15T10:30:00Z"
}
```

**订阅者**：
- 生产服务（更新生产进度）
- 物料服务（如果配置了自动倒扣料，则扣减库存）

#### 5.3.4 operation_report.rejected

**事件类型**：`pp.operation_report.rejected`  
**触发时机**：报工被拒绝（如质检不合格）  
**事件负载**：

```json
{
  "report_number": "OR-2025-001",
  "status": "REJECTED",
  "reject_reason": "质检不合格",
  "rejected_by": "quality001",
  "rejected_at": "2025-12-15T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知生产人员）

---

## 六、物料管理模块事件（MM Events）

### 6.1 物料相关事件

#### 6.1.1 material.created

**事件类型**：`mm.material.created`  
**触发时机**：物料创建完成  
**事件负载**：

```json
{
  "material_code": "MAT001",
  "material_name": "PCB板",
  "material_type": "FG",
  "status": "ACTIVE",
  "created_by": "engineer001"
}
```

#### 6.1.2 material.stock_changed

**事件类型**：`mm.material.stock_changed`  
**触发时机**：物料库存变更  
**事件负载**：

```json
{
  "material_code": "MAT001",
  "transaction_type": "ISSUE",
  "quantity": -50,
  "current_stock": 450,
  "reference_number": "PO-2025-001",
  "reference_type": "PRODUCTION_ORDER",
  "transaction_date": "2025-12-15T10:30:00Z",
  "operator": "warehouse001"
}
```

**订阅者**：
- 生产服务（检查库存是否充足）
- 通知服务（库存低于安全库存时通知）

### 6.2 生产领料相关事件

#### 6.2.1 material_issue.created

**事件类型**：`mm.material_issue.created`  
**触发时机**：生产领料单创建  
**事件负载**：

```json
{
  "issue_number": "MI-2025-001",
  "production_order_number": "PO-2025-001",
  "material_code": "MAT001",
  "quantity": 50,
  "created_by": "warehouse001"
}
```

#### 6.2.2 material_issue.completed

**事件类型**：`mm.material_issue.completed`  
**触发时机**：生产领料完成  
**事件负载**：

```json
{
  "issue_number": "MI-2025-001",
  "issued_quantity": 50,
  "issued_by": "warehouse001",
  "issued_at": "2025-12-15T10:30:00Z"
}
```

**订阅者**：
- 物料服务（扣减库存）
- 生产服务（更新生产订单领料状态）

---

## 七、工作流模块事件（Workflow Events）

### 7.1 工作流实例相关事件

#### 7.1.1 workflow_instance.started

**事件类型**：`workflow.instance.started`  
**触发时机**：工作流实例启动  
**事件负载**：

```json
{
  "instance_id": "WFI-2025-001",
  "workflow_id": "WF-QUOTATION-APPROVAL",
  "business_id": "QT-2025-001",
  "business_type": "QUOTATION",
  "status": "PENDING",
  "current_node_id": "NODE-001",
  "started_by": "user001"
}
```

**订阅者**：
- 通知服务（通知第一个节点审批人）

#### 7.1.2 workflow_instance.node_approved

**事件类型**：`workflow.instance.node_approved`  
**触发时机**：工作流节点审批通过  
**事件负载**：

```json
{
  "instance_id": "WFI-2025-001",
  "node_id": "NODE-001",
  "approver": "sales_mgr001",
  "approved_at": "2025-12-12T10:30:00Z",
  "has_next_node": true,
  "next_node_id": "NODE-002"
}
```

**订阅者**：
- 通知服务（通知下一个节点审批人）
- 工作流服务（激活下一个节点）

#### 7.1.3 workflow_instance.node_rejected

**事件类型**：`workflow.instance.node_rejected`  
**触发时机**：工作流节点审批被拒绝  
**事件负载**：

```json
{
  "instance_id": "WFI-2025-001",
  "node_id": "NODE-001",
  "rejected_by": "sales_mgr001",
  "reject_reason": "价格不合理",
  "rejected_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 通知服务（通知创建人）
- 业务服务（更新业务对象状态为REJECTED）

#### 7.1.4 workflow_instance.completed

**事件类型**：`workflow.instance.completed`  
**触发时机**：工作流实例完成  
**事件负载**：

```json
{
  "instance_id": "WFI-2025-001",
  "status": "COMPLETED",
  "completed_at": "2025-12-12T10:30:00Z"
}
```

**订阅者**：
- 业务服务（更新业务对象状态为APPROVED）
- 通知服务（通知相关人员）

---

## 八、事件发布和订阅机制

### 8.1 事件总线架构

```
┌─────────────────────────────────────────────────────────┐
│                    事件总线 (Event Bus)                  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  发布者      │  │  订阅者      │  │  事件存储    │  │
│  │  (Publisher) │  │  (Subscriber)│  │  (Store)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           事件路由 (Event Router)                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 8.2 事件发布

#### 8.2.1 发布流程

1. **业务操作触发**：业务服务执行操作（如创建报价单）
2. **生成事件**：根据业务操作生成对应事件
3. **验证事件**：验证事件格式和必填字段
4. **发布到事件总线**：将事件发布到事件总线
5. **持久化事件**：将事件存储到事件存储
6. **通知订阅者**：事件总线通知所有订阅者

#### 8.2.2 发布接口

```python
from typing import Dict, Any
from datetime import datetime
import uuid

class EventPublisher:
    """事件发布者"""
    
    def __init__(self, event_bus, event_store):
        self.event_bus = event_bus
        self.event_store = event_store
    
    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        user_id: str,
        user_role: str,
        correlation_id: str = None,
        causation_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """发布事件"""
        event_id = f"evt_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "event_version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": self._get_service_name(),
            "correlation_id": correlation_id or event_id,
            "causation_id": causation_id,
            "user_id": user_id,
            "user_role": user_role,
            "payload": payload,
            "metadata": metadata or {}
        }
        
        # 持久化事件
        self.event_store.save(event)
        
        # 发布到事件总线
        self.event_bus.publish(event)
        
        return event_id
```

### 8.3 事件订阅

#### 8.3.1 订阅模式

- **点对点（Point-to-Point）**：每个事件只被一个订阅者处理
- **发布-订阅（Pub-Sub）**：每个事件可以被多个订阅者处理
- **主题订阅（Topic Subscription）**：按事件类型订阅

#### 8.3.2 订阅接口

```python
from typing import Callable, List

class EventSubscriber:
    """事件订阅者"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.handlers = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件类型"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        self.event_bus.subscribe(event_type, self._handle_event)
    
    def _handle_event(self, event: Dict):
        """处理事件"""
        event_type = event.get("event_type")
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # 记录错误，但不中断其他处理器
                    logger.error(f"事件处理失败: {e}", exc_info=True)
```

### 8.4 事件路由

#### 8.4.1 路由规则

事件总线根据事件类型将事件路由到对应的订阅者：

```python
class EventRouter:
    """事件路由器"""
    
    def __init__(self):
        self.routes = {}
    
    def register_route(self, event_type_pattern: str, subscriber: EventSubscriber):
        """注册路由规则"""
        if event_type_pattern not in self.routes:
            self.routes[event_type_pattern] = []
        self.routes[event_type_pattern].append(subscriber)
    
    def route(self, event: Dict):
        """路由事件"""
        event_type = event.get("event_type")
        for pattern, subscribers in self.routes.items():
            if self._match_pattern(pattern, event_type):
                for subscriber in subscribers:
                    subscriber.handle(event)
    
    def _match_pattern(self, pattern: str, event_type: str) -> bool:
        """匹配事件类型模式"""
        # 支持通配符匹配，如 "sd.*" 匹配所有sd模块的事件
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")
        return pattern == event_type
```

### 8.5 事件总线实现

```python
from queue import Queue
from threading import Thread
from typing import Dict, List, Callable
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """事件总线"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue = Queue()
        self.running = False
        self.worker_thread = None
    
    def start(self):
        """启动事件总线"""
        self.running = True
        self.worker_thread = Thread(target=self._process_events, daemon=True)
        self.worker_thread.start()
    
    def stop(self):
        """停止事件总线"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()
    
    def publish(self, event: Dict):
        """发布事件"""
        self.event_queue.put(event)
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def _process_events(self):
        """处理事件队列"""
        while self.running:
            try:
                event = self.event_queue.get(timeout=1)
                self._dispatch(event)
            except:
                continue
    
    def _dispatch(self, event: Dict):
        """分发事件"""
        event_type = event.get("event_type")
        
        # 精确匹配
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                self._invoke_handler(handler, event)
        
        # 通配符匹配
        for pattern, handlers in self.subscribers.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event_type.startswith(prefix + "."):
                    for handler in handlers:
                        self._invoke_handler(handler, event)
    
    def _invoke_handler(self, handler: Callable, event: Dict):
        """调用事件处理器"""
        try:
            handler(event)
        except Exception as e:
            logger.error(f"事件处理失败: {e}", exc_info=True)
```

---

## 九、事件存储和处理

### 9.1 事件存储

#### 9.1.1 存储策略

事件存储采用事件溯源（Event Sourcing）模式：

- **追加写入**：事件只能追加，不能修改或删除
- **时间序列**：按时间顺序存储事件
- **持久化**：所有事件持久化到数据库或消息队列
- **可重放**：支持事件重放重建状态

#### 9.1.2 事件存储表结构

```sql
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50) NOT NULL,
    correlation_id VARCHAR(100),
    causation_id VARCHAR(100),
    user_id VARCHAR(50),
    user_role VARCHAR(50),
    payload JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_correlation_id ON events(correlation_id);
CREATE INDEX idx_events_user_id ON events(user_id);
```

#### 9.1.3 事件存储实现

```python
from sqlalchemy import Column, String, DateTime, JSON, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from backend.common.database.base import Base

class Event(Base):
    """事件存储模型"""
    __tablename__ = "events"
    
    id = Column(BigInteger, primary_key=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(50), nullable=False)
    correlation_id = Column(String(100), index=True)
    causation_id = Column(String(100))
    user_id = Column(String(50), index=True)
    user_role = Column(String(50))
    payload = Column(JSONB, nullable=False)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

class EventStore:
    """事件存储服务"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def save(self, event: Dict):
        """保存事件"""
        event_record = Event(
            event_id=event["event_id"],
            event_type=event["event_type"],
            event_version=event["event_version"],
            timestamp=datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")),
            source=event["source"],
            correlation_id=event.get("correlation_id"),
            causation_id=event.get("causation_id"),
            user_id=event.get("user_id"),
            user_role=event.get("user_role"),
            payload=event["payload"],
            metadata=event.get("metadata", {})
        )
        self.db.add(event_record)
        self.db.commit()
    
    def get_by_event_id(self, event_id: str) -> Dict:
        """根据事件ID获取事件"""
        event = self.db.query(Event).filter(
            Event.event_id == event_id
        ).first()
        return self._to_dict(event) if event else None
    
    def get_by_correlation_id(self, correlation_id: str) -> List[Dict]:
        """根据关联ID获取所有相关事件"""
        events = self.db.query(Event).filter(
            Event.correlation_id == correlation_id
        ).order_by(Event.timestamp).all()
        return [self._to_dict(e) for e in events]
    
    def get_by_type(self, event_type: str, limit: int = 100) -> List[Dict]:
        """根据事件类型获取事件"""
        events = self.db.query(Event).filter(
            Event.event_type == event_type
        ).order_by(Event.timestamp.desc()).limit(limit).all()
        return [self._to_dict(e) for e in events]
    
    def _to_dict(self, event: Event) -> Dict:
        """转换为字典"""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_version": event.event_version,
            "timestamp": event.timestamp.isoformat() + "Z",
            "source": event.source,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "user_id": event.user_id,
            "user_role": event.user_role,
            "payload": event.payload,
            "metadata": event.metadata
        }
```

### 9.2 事件处理

#### 9.2.1 事件处理器

```python
from abc import ABC, abstractmethod
from typing import Dict

class EventHandler(ABC):
    """事件处理器基类"""
    
    @abstractmethod
    def handle(self, event: Dict):
        """处理事件"""
        pass
    
    def can_handle(self, event: Dict) -> bool:
        """检查是否可以处理该事件"""
        return True

class NotificationEventHandler(EventHandler):
    """通知事件处理器"""
    
    def __init__(self, notification_service):
        self.notification_service = notification_service
    
    def handle(self, event: Dict):
        """处理通知事件"""
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        
        if event_type == "sd.quotation.approved":
            self._notify_quotation_approved(payload)
        elif event_type == "sd.sales_order.approved":
            self._notify_sales_order_approved(payload)
        # ... 其他事件类型
    
    def _notify_quotation_approved(self, payload: Dict):
        """通知报价单审批通过"""
        quotation_number = payload.get("quotation_number")
        # 发送通知
        self.notification_service.send(
            recipient=payload.get("created_by"),
            subject="报价单审批通过",
            message=f"报价单 {quotation_number} 已审批通过"
        )
    
    def _notify_sales_order_approved(self, payload: Dict):
        """通知销售订单审批通过"""
        order_number = payload.get("order_number")
        # 发送通知
        self.notification_service.send(
            recipient=payload.get("created_by"),
            subject="销售订单审批通过",
            message=f"销售订单 {order_number} 已审批通过，可以创建生产订单"
        )
```

#### 9.2.2 事件处理服务

```python
class EventProcessingService:
    """事件处理服务"""
    
    def __init__(self, event_bus, event_store, handlers: List[EventHandler]):
        self.event_bus = event_bus
        self.event_store = event_store
        self.handlers = handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """注册事件处理器"""
        for handler in self.handlers:
            # 订阅所有事件类型
            self.event_bus.subscribe("*", handler.handle)
    
    def process_event(self, event: Dict):
        """处理事件"""
        # 1. 保存事件
        self.event_store.save(event)
        
        # 2. 发布到事件总线
        self.event_bus.publish(event)
        
        # 3. 记录处理日志
        logger.info(f"事件已处理: {event['event_id']}")
```

### 9.3 事件重放

#### 9.3.1 重放机制

事件重放用于重建系统状态或修复数据不一致：

```python
class EventReplayService:
    """事件重放服务"""
    
    def __init__(self, event_store, event_bus):
        self.event_store = event_store
        self.event_bus = event_bus
    
    def replay_events(
        self,
        entity_type: str,
        entity_id: str,
        from_timestamp: datetime = None,
        to_timestamp: datetime = None
    ):
        """重放事件"""
        # 获取相关事件
        events = self._get_events(entity_type, entity_id, from_timestamp, to_timestamp)
        
        # 按时间顺序重放
        for event in events:
            # 重新发布事件
            self.event_bus.publish(event)
            logger.info(f"重放事件: {event['event_id']}")
    
    def _get_events(
        self,
        entity_type: str,
        entity_id: str,
        from_timestamp: datetime,
        to_timestamp: datetime
    ) -> List[Dict]:
        """获取事件列表"""
        query = self.event_store.db.query(Event).filter(
            Event.payload[entity_type].astext == entity_id
        )
        
        if from_timestamp:
            query = query.filter(Event.timestamp >= from_timestamp)
        if to_timestamp:
            query = query.filter(Event.timestamp <= to_timestamp)
        
        events = query.order_by(Event.timestamp).all()
        return [self.event_store._to_dict(e) for e in events]
```

---

## 十、事件驱动架构实现

### 10.1 架构设计

#### 10.1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     业务服务层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ SD服务   │  │ ENG服务   │  │ PP服务    │  │ MM服务    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │         │
│       └─────────────┼─────────────┼─────────────┘         │
│                     │             │                       │
│                     ▼             ▼                       │
┌─────────────────────┼─────────────┼───────────────────────┐
│              事件发布服务 (Event Publisher)                 │
└─────────────────────┬─────────────┬───────────────────────┘
                      │             │
                      ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                     事件总线 (Event Bus)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 事件路由     │  │ 事件存储     │  │ 事件分发     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 通知服务     │ │ 审计服务     │ │ 报表服务     │ │ 集成服务     │
│ (Subscriber) │ │ (Subscriber) │ │ (Subscriber) │ │ (Subscriber) │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### 10.2 服务集成示例

#### 10.2.1 报价单服务集成

```python
from backend.common.events.publisher import EventPublisher
from backend.common.models.sd import Quotation, QuotationStatus

class QuotationService:
    """报价单服务"""
    
    def __init__(self, db_session, event_publisher: EventPublisher):
        self.db = db_session
        self.event_publisher = event_publisher
    
    def create_quotation(self, quotation_data: Dict, user_id: str, user_role: str) -> Quotation:
        """创建报价单"""
        quotation = Quotation(**quotation_data)
        quotation.status = QuotationStatus.DRAFT
        quotation.created_by = user_id
        
        self.db.add(quotation)
        self.db.commit()
        
        # 发布事件
        self.event_publisher.publish(
            event_type="sd.quotation.created",
            payload={
                "quotation_number": quotation.quotation_number,
                "customer_id": quotation.customer_id,
                "product_number": quotation.product_number,
                "quantity": float(quotation.quantity),
                "unit_price": float(quotation.unit_price),
                "total_amount": float(quotation.total_amount),
                "status": quotation.status.value
            },
            user_id=user_id,
            user_role=user_role
        )
        
        return quotation
    
    def submit_quotation(self, quotation_number: str, user_id: str, user_role: str):
        """提交报价单审批"""
        quotation = self.db.query(Quotation).filter(
            Quotation.quotation_number == quotation_number
        ).first()
        
        if not quotation:
            raise ValueError("报价单不存在")
        
        quotation.status = QuotationStatus.PENDING_SALES
        self.db.commit()
        
        # 发布事件
        self.event_publisher.publish(
            event_type="sd.quotation.submitted",
            payload={
                "quotation_number": quotation.quotation_number,
                "customer_id": quotation.customer_id,
                "total_amount": float(quotation.total_amount),
                "status": quotation.status.value
            },
            user_id=user_id,
            user_role=user_role
        )
```

#### 10.2.2 通知服务订阅

```python
from backend.common.events.subscriber import EventSubscriber

class NotificationService:
    """通知服务"""
    
    def __init__(self, event_bus):
        self.subscriber = EventSubscriber(event_bus)
        self._register_handlers()
    
    def _register_handlers(self):
        """注册事件处理器"""
        # 订阅报价单相关事件
        self.subscriber.subscribe("sd.quotation.submitted", self._handle_quotation_submitted)
        self.subscriber.subscribe("sd.quotation.approved", self._handle_quotation_approved)
        self.subscriber.subscribe("sd.quotation.rejected", self._handle_quotation_rejected)
        
        # 订阅销售订单相关事件
        self.subscriber.subscribe("sd.sales_order.submitted", self._handle_sales_order_submitted)
        self.subscriber.subscribe("sd.sales_order.approved", self._handle_sales_order_approved)
        self.subscriber.subscribe("sd.sales_order.rejected", self._handle_sales_order_rejected)
    
    def _handle_quotation_submitted(self, event: Dict):
        """处理报价单提交事件"""
        payload = event.get("payload", {})
        quotation_number = payload.get("quotation_number")
        
        # 通知销售经理
        self.send_notification(
            recipient_role="SALES_MANAGER",
            subject="报价单待审批",
            message=f"报价单 {quotation_number} 已提交，等待审批"
        )
    
    def _handle_quotation_approved(self, event: Dict):
        """处理报价单审批通过事件"""
        payload = event.get("payload", {})
        quotation_number = payload.get("quotation_number")
        created_by = payload.get("created_by")
        
        # 通知业务员
        self.send_notification(
            recipient=created_by,
            subject="报价单审批通过",
            message=f"报价单 {quotation_number} 已审批通过"
        )
    
    def _handle_quotation_rejected(self, event: Dict):
        """处理报价单拒绝事件"""
        payload = event.get("payload", {})
        quotation_number = payload.get("quotation_number")
        created_by = payload.get("created_by")
        reject_reason = payload.get("reject_reason")
        
        # 通知业务员
        self.send_notification(
            recipient=created_by,
            subject="报价单审批被拒绝",
            message=f"报价单 {quotation_number} 审批被拒绝，原因：{reject_reason}"
        )
    
    def _handle_sales_order_submitted(self, event: Dict):
        """处理销售订单提交事件"""
        payload = event.get("payload", {})
        order_number = payload.get("order_number")
        
        # 通知各部门评审人
        departments = ["SALES_MANAGER", "ENGINEER", "WAREHOUSE", "FINANCE"]
        for dept in departments:
            self.send_notification(
                recipient_role=dept,
                subject="销售订单待评审",
                message=f"销售订单 {order_number} 已提交，等待评审"
            )
    
    def _handle_sales_order_approved(self, event: Dict):
        """处理销售订单审批通过事件"""
        payload = event.get("payload", {})
        order_number = payload.get("order_number")
        created_by = payload.get("created_by")
        
        # 通知业务员和计划员
        self.send_notification(
            recipient=created_by,
            subject="销售订单审批通过",
            message=f"销售订单 {order_number} 已审批通过，可以创建生产订单"
        )
        self.send_notification(
            recipient_role="PLANNER",
            subject="新订单待排程",
            message=f"销售订单 {order_number} 已审批通过，等待排程"
        )
    
    def _handle_sales_order_rejected(self, event: Dict):
        """处理销售订单拒绝事件"""
        payload = event.get("payload", {})
        order_number = payload.get("order_number")
        created_by = payload.get("created_by")
        reject_reason = payload.get("reject_reason")
        
        # 通知业务员
        self.send_notification(
            recipient=created_by,
            subject="销售订单评审被拒绝",
            message=f"销售订单 {order_number} 评审被拒绝，原因：{reject_reason}"
        )
    
    def send_notification(self, recipient: str = None, recipient_role: str = None, 
                         subject: str = "", message: str = ""):
        """发送通知"""
        # 实现通知发送逻辑
        pass
```

---

## 十一、事件处理最佳实践

### 11.1 事件设计原则

1. **事件粒度适中**：
   - 事件应该表示一个完整的业务操作
   - 避免过于细粒度的事件（如每个字段变更）
   - 避免过于粗粒度的事件（如整个业务流程）

2. **事件命名清晰**：
   - 使用动词过去式（如created, approved, completed）
   - 遵循命名空间规范（模块.实体.动作）
   - 事件名称应该清晰表达业务含义

3. **事件负载完整**：
   - 包含足够的信息供订阅者处理
   - 避免订阅者需要额外查询数据库
   - 包含业务对象的关键标识和状态

### 11.2 事件处理原则

1. **幂等性**：
   - 事件处理应该是幂等的
   - 重复处理同一事件应该产生相同结果
   - 使用事件ID或业务ID确保幂等性

2. **异步处理**：
   - 事件处理应该是异步的
   - 避免阻塞事件发布者
   - 使用消息队列或后台任务处理

3. **错误处理**：
   - 事件处理失败应该记录日志
   - 支持事件重试机制
   - 失败事件应该进入死信队列

### 11.3 事件订阅原则

1. **解耦性**：
   - 事件发布者和订阅者相互独立
   - 订阅者不应该知道其他订阅者
   - 通过事件总线实现解耦

2. **可扩展性**：
   - 新增订阅者不影响现有系统
   - 支持动态添加和移除订阅者
   - 使用主题订阅模式

3. **可靠性**：
   - 确保事件不丢失
   - 支持事件持久化
   - 支持事件重放

---

## 十二、事件监控和调试

### 12.1 事件监控

#### 12.1.1 监控指标

```python
class EventMetrics:
    """事件监控指标"""
    
    def __init__(self):
        self.event_count = {}  # 事件类型计数
        self.event_latency = {}  # 事件处理延迟
        self.event_errors = {}  # 事件处理错误
        self.subscriber_performance = {}  # 订阅者性能
    
    def record_event(self, event_type: str, processing_time: float):
        """记录事件处理"""
        if event_type not in self.event_count:
            self.event_count[event_type] = 0
        self.event_count[event_type] += 1
        
        if event_type not in self.event_latency:
            self.event_latency[event_type] = []
        self.event_latency[event_type].append(processing_time)
    
    def record_error(self, event_type: str, error: Exception):
        """记录事件处理错误"""
        if event_type not in self.event_errors:
            self.event_errors[event_type] = []
        self.event_errors[event_type].append({
            "error": str(error),
            "timestamp": datetime.now()
        })
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {}
        for event_type, count in self.event_count.items():
            latencies = self.event_latency.get(event_type, [])
            errors = self.event_errors.get(event_type, [])
            
            stats[event_type] = {
                "count": count,
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0,
                "error_count": len(errors),
                "error_rate": len(errors) / count if count > 0 else 0
            }
        return stats
```

#### 12.1.2 事件追踪

```python
class EventTracer:
    """事件追踪器"""
    
    def trace_event(self, event: Dict):
        """追踪事件"""
        correlation_id = event.get("correlation_id")
        event_id = event.get("event_id")
        
        # 记录事件追踪信息
        trace = {
            "event_id": event_id,
            "correlation_id": correlation_id,
            "event_type": event.get("event_type"),
            "timestamp": event.get("timestamp"),
            "source": event.get("source"),
            "subscribers": []
        }
        
        # 记录订阅者处理情况
        for subscriber in self.get_subscribers(event.get("event_type")):
            trace["subscribers"].append({
                "subscriber": subscriber.name,
                "status": "pending"
            })
        
        return trace
```

### 12.2 事件调试

#### 12.2.1 事件日志

```python
import logging

logger = logging.getLogger("events")

class EventLogger:
    """事件日志记录器"""
    
    def log_event_published(self, event: Dict):
        """记录事件发布"""
        logger.info(
            f"事件已发布: {event['event_id']}",
            extra={
                "event_type": event.get("event_type"),
                "correlation_id": event.get("correlation_id"),
                "user_id": event.get("user_id")
            }
        )
    
    def log_event_processed(self, event: Dict, subscriber: str, success: bool):
        """记录事件处理"""
        level = logging.INFO if success else logging.ERROR
        logger.log(
            level,
            f"事件已处理: {event['event_id']} by {subscriber}",
            extra={
                "event_type": event.get("event_type"),
                "subscriber": subscriber,
                "success": success
            }
        )
```

#### 12.2.2 事件查询接口

```python
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.get("/api/events")
async def query_events(
    event_type: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """查询事件"""
    query = event_store.db.query(Event)
    
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if correlation_id:
        query = query.filter(Event.correlation_id == correlation_id)
    if user_id:
        query = query.filter(Event.user_id == user_id)
    if start_time:
        query = query.filter(Event.timestamp >= start_time)
    if end_time:
        query = query.filter(Event.timestamp <= end_time)
    
    total = query.count()
    events = query.order_by(Event.timestamp.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return {
        "events": [event_store._to_dict(e) for e in events],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/api/events/{event_id}")
async def get_event(event_id: str):
    """获取单个事件"""
    event = event_store.get_by_event_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event

@router.get("/api/events/correlation/{correlation_id}")
async def get_events_by_correlation(correlation_id: str):
    """根据关联ID获取所有相关事件"""
    events = event_store.get_by_correlation_id(correlation_id)
    return {"events": events}
```

---

## 十三、事件模型总结

### 13.1 事件统计

本文档定义了以下事件：

| 模块 | 实体 | 事件数量 |
|------|------|---------|
| SD | 客户 | 4 |
| SD | 报价单 | 8 |
| SD | 销售订单 | 12 |
| ENG | BOM | 3 |
| ENG | 工艺路线 | 2 |
| ENG | MI | 4 |
| ENG | 生产版本 | 1 |
| PP | 工作中心 | 3 |
| PP | 生产订单 | 5 |
| PP | 工序报工 | 4 |
| MM | 物料 | 2 |
| MM | 生产领料 | 2 |
| Workflow | 工作流实例 | 4 |

**总计**：54个事件

### 13.2 关键特性

1. **事件驱动架构**：系统采用事件驱动架构，实现服务解耦
2. **事件溯源**：所有事件持久化存储，支持事件溯源
3. **异步处理**：事件处理采用异步模式，提高系统性能
4. **可追溯性**：通过correlation_id追踪相关事件
5. **可扩展性**：支持动态添加事件类型和订阅者

### 13.3 使用建议

1. **开发人员**：
   - 在业务操作完成后发布相应事件
   - 使用统一的事件发布接口
   - 确保事件负载包含足够信息

2. **架构师**：
   - 设计清晰的事件命名规范
   - 规划事件订阅关系
   - 设计事件存储和重放机制

3. **运维人员**：
   - 监控事件处理性能
   - 监控事件处理错误率
   - 定期检查事件存储空间

### 13.4 后续工作

1. **事件扩展**：
   - 根据业务需求，添加新的事件类型
   - 优化现有事件的定义
   - 添加事件版本管理

2. **性能优化**：
   - 优化事件存储性能
   - 使用消息队列（如RabbitMQ、Kafka）替代内存事件总线
   - 实现事件批量处理

3. **监控和告警**：
   - 实现事件处理监控面板
   - 设置事件处理异常告警
   - 分析事件处理性能瓶颈

---

## 附录：事件快速参考

### A.1 事件类型速查表

| 事件类型 | 模块 | 实体 | 说明 |
|---------|------|------|------|
| sd.customer.created | SD | 客户 | 客户创建 |
| sd.customer.submitted | SD | 客户 | 客户提交审批 |
| sd.customer.approved | SD | 客户 | 客户审批通过 |
| sd.customer.blocked | SD | 客户 | 客户被冻结 |
| sd.quotation.created | SD | 报价单 | 报价单创建 |
| sd.quotation.submitted | SD | 报价单 | 报价单提交审批 |
| sd.quotation.sales_approved | SD | 报价单 | 销售审批通过 |
| sd.quotation.finance_approved | SD | 报价单 | 财务审批通过 |
| sd.quotation.approved | SD | 报价单 | 所有审批通过 |
| sd.quotation.rejected | SD | 报价单 | 报价单被拒绝 |
| sd.quotation.customer_confirmed | SD | 报价单 | 客户确认报价单 |
| sd.quotation.linked | SD | 报价单 | 报价单关联到销售订单 |
| sd.sales_order.created | SD | 销售订单 | 销售订单创建 |
| sd.sales_order.submitted | SD | 销售订单 | 销售订单提交评审 |
| sd.sales_order.review_started | SD | 销售订单 | 订单评审开始 |
| sd.sales_order.department_reviewed | SD | 销售订单 | 部门评审完成 |
| sd.sales_order.approved | SD | 销售订单 | 所有部门评审通过 |
| sd.sales_order.rejected | SD | 销售订单 | 订单评审被拒绝 |
| sd.sales_order.production_started | SD | 销售订单 | 开始生产 |
| sd.sales_order.completed | SD | 销售订单 | 生产完成 |
| sd.sales_order.shipped | SD | 销售订单 | 已发货 |
| sd.sales_order.delivered | SD | 销售订单 | 已交付 |
| sd.sales_order.reconciled | SD | 销售订单 | 已对账 |
| sd.sales_order.closed | SD | 销售订单 | 订单关闭 |
| eng.bom.created | ENG | BOM | BOM创建 |
| eng.bom.submitted | ENG | BOM | BOM提交审核 |
| eng.bom.released | ENG | BOM | BOM发布 |
| eng.routing.created | ENG | 工艺路线 | 工艺路线创建 |
| eng.routing.released | ENG | 工艺路线 | 工艺路线发布 |
| eng.mi.created | ENG | MI | MI创建 |
| eng.mi.submitted | ENG | MI | MI提交审核 |
| eng.mi.approved | ENG | MI | MI审核通过 |
| eng.mi.released | ENG | MI | MI发布 |
| eng.production_version.created | ENG | 生产版本 | 生产版本创建 |
| pp.work_center.created | PP | 工作中心 | 工作中心创建 |
| pp.work_center.maintenance_started | PP | 工作中心 | 工作中心开始维护 |
| pp.work_center.maintenance_completed | PP | 工作中心 | 工作中心维护完成 |
| pp.production_order.created | PP | 生产订单 | 生产订单创建 |
| pp.production_order.released | PP | 生产订单 | 生产订单下达 |
| pp.production_order.started | PP | 生产订单 | 生产订单开始生产 |
| pp.production_order.completed | PP | 生产订单 | 生产订单完成 |
| pp.production_order.closed | PP | 生产订单 | 生产订单关闭 |
| pp.operation_report.created | PP | 工序报工 | 工序报工记录创建 |
| pp.operation_report.started | PP | 工序报工 | 开始报工 |
| pp.operation_report.completed | PP | 工序报工 | 报工完成 |
| pp.operation_report.rejected | PP | 工序报工 | 报工被拒绝 |
| mm.material.created | MM | 物料 | 物料创建 |
| mm.material.stock_changed | MM | 物料 | 物料库存变更 |
| mm.material_issue.created | MM | 生产领料 | 生产领料单创建 |
| mm.material_issue.completed | MM | 生产领料 | 生产领料完成 |
| workflow.instance.started | Workflow | 工作流实例 | 工作流实例启动 |
| workflow.instance.node_approved | Workflow | 工作流实例 | 工作流节点审批通过 |
| workflow.instance.node_rejected | Workflow | 工作流实例 | 工作流节点审批被拒绝 |
| workflow.instance.completed | Workflow | 工作流实例 | 工作流实例完成 |

### A.2 事件订阅关系表

| 事件类型 | 订阅服务 | 处理动作 |
|---------|---------|---------|
| sd.customer.submitted | 工作流服务 | 启动客户审批流程 |
| sd.customer.submitted | 通知服务 | 通知审批人 |
| sd.customer.approved | 通知服务 | 通知创建人 |
| sd.quotation.submitted | 工作流服务 | 启动报价单审批流程 |
| sd.quotation.submitted | 通知服务 | 通知销售经理 |
| sd.quotation.sales_approved | 通知服务 | 通知财务部门 |
| sd.quotation.finance_approved | 通知服务 | 通知总经办 |
| sd.quotation.approved | 通知服务 | 通知业务员和客户 |
| sd.quotation.rejected | 通知服务 | 通知业务员 |
| sd.quotation.customer_confirmed | 通知服务 | 通知业务员可以创建销售订单 |
| sd.sales_order.submitted | 工作流服务 | 启动订单评审流程 |
| sd.sales_order.submitted | 通知服务 | 通知各部门评审人 |
| sd.sales_order.department_reviewed | 工作流服务 | 更新评审进度 |
| sd.sales_order.department_reviewed | 通知服务 | 通知下一个评审部门 |
| sd.sales_order.approved | 生产服务 | 可以创建生产订单 |
| sd.sales_order.approved | 通知服务 | 通知业务员和计划员 |
| sd.sales_order.rejected | 通知服务 | 通知业务员 |
| sd.sales_order.production_started | 物料服务 | 准备生产领料 |
| sd.sales_order.production_started | 通知服务 | 通知生产部门 |
| sd.sales_order.completed | 通知服务 | 通知业务员可以发货 |
| sd.sales_order.shipped | 通知服务 | 通知客户 |
| sd.sales_order.shipped | 财务服务 | 准备对账 |
| sd.sales_order.delivered | 财务服务 | 触发对账流程 |
| eng.bom.released | 生产版本服务 | 可用于创建生产版本 |
| eng.bom.released | 审计服务 | 记录发布日志 |
| eng.routing.released | 生产版本服务 | 可用于创建生产版本 |
| eng.routing.released | 生产服务 | 可用于生产订单 |
| eng.mi.released | 生产版本服务 | 可用于创建生产版本 |
| eng.production_version.created | 销售服务 | 可用于创建销售订单 |
| eng.production_version.created | 生产服务 | 可用于创建生产订单 |
| pp.work_center.maintenance_started | 生产服务 | 暂停分配生产任务 |
| pp.work_center.maintenance_started | 通知服务 | 通知相关人员 |
| pp.work_center.maintenance_completed | 生产服务 | 恢复分配生产任务 |
| pp.production_order.released | 物料服务 | 准备生产领料 |
| pp.production_order.released | 通知服务 | 通知生产部门 |
| pp.production_order.started | 销售服务 | 更新销售订单状态为IN_PRODUCTION |
| pp.production_order.completed | 销售服务 | 更新销售订单状态为COMPLETED |
| pp.production_order.completed | 物料服务 | 成品入库 |
| pp.production_order.completed | 通知服务 | 通知业务员 |
| pp.operation_report.completed | 生产服务 | 更新生产进度 |
| pp.operation_report.completed | 物料服务 | 如果配置了自动倒扣料，则扣减库存 |
| pp.operation_report.rejected | 通知服务 | 通知生产人员 |
| mm.material.stock_changed | 生产服务 | 检查库存是否充足 |
| mm.material.stock_changed | 通知服务 | 库存低于安全库存时通知 |
| mm.material_issue.completed | 物料服务 | 扣减库存 |
| mm.material_issue.completed | 生产服务 | 更新生产订单领料状态 |
| workflow.instance.started | 通知服务 | 通知第一个节点审批人 |
| workflow.instance.node_approved | 通知服务 | 通知下一个节点审批人 |
| workflow.instance.node_approved | 工作流服务 | 激活下一个节点 |
| workflow.instance.node_rejected | 通知服务 | 通知创建人 |
| workflow.instance.node_rejected | 业务服务 | 更新业务对象状态为REJECTED |
| workflow.instance.completed | 业务服务 | 更新业务对象状态为APPROVED |
| workflow.instance.completed | 通知服务 | 通知相关人员 |

### A.3 事件处理流程图

#### A.3.1 报价单审批流程事件流

```
创建报价单
    ↓
发布: sd.quotation.created
    ↓
提交审批
    ↓
发布: sd.quotation.submitted
    ├─→ 工作流服务: 启动审批流程
    └─→ 通知服务: 通知销售经理
    ↓
销售审批通过
    ↓
发布: sd.quotation.sales_approved
    └─→ 通知服务: 通知财务部门
    ↓
财务审批通过
    ↓
发布: sd.quotation.finance_approved
    └─→ 通知服务: 通知总经办
    ↓
总经办审批通过
    ↓
发布: sd.quotation.approved
    ├─→ 通知服务: 通知业务员和客户
    └─→ 审计服务: 记录审批完成
    ↓
客户确认
    ↓
发布: sd.quotation.customer_confirmed
    └─→ 通知服务: 通知业务员可以创建销售订单
    ↓
创建销售订单
    ↓
发布: sd.quotation.linked
```

#### A.3.2 销售订单评审流程事件流

```
创建销售订单
    ↓
发布: sd.sales_order.created
    ↓
提交评审
    ↓
发布: sd.sales_order.submitted
    ├─→ 工作流服务: 启动订单评审流程
    └─→ 通知服务: 通知各部门评审人
    ↓
发布: sd.sales_order.review_started
    ↓
各部门评审（并行）
    ├─→ 销售部门评审
    ├─→ 工程部门评审
    ├─→ 物料部门评审
    └─→ 财务部门评审
    ↓
发布: sd.sales_order.department_reviewed (多次)
    ├─→ 工作流服务: 更新评审进度
    └─→ 通知服务: 通知下一个评审部门
    ↓
所有部门评审通过
    ↓
发布: sd.sales_order.approved
    ├─→ 生产服务: 可以创建生产订单
    └─→ 通知服务: 通知业务员和计划员
```

#### A.3.3 生产订单执行流程事件流

```
创建生产订单
    ↓
发布: pp.production_order.created
    ↓
下达订单
    ↓
发布: pp.production_order.released
    ├─→ 物料服务: 准备生产领料
    └─→ 通知服务: 通知生产部门
    ↓
开始生产
    ↓
发布: pp.production_order.started
    └─→ 销售服务: 更新销售订单状态为IN_PRODUCTION
    ↓
工序报工
    ├─→ 发布: pp.operation_report.created
    ├─→ 发布: pp.operation_report.started
    └─→ 发布: pp.operation_report.completed
        ├─→ 生产服务: 更新生产进度
        └─→ 物料服务: 自动倒扣料（如配置）
    ↓
生产完成
    ↓
发布: pp.production_order.completed
    ├─→ 销售服务: 更新销售订单状态为COMPLETED
    ├─→ 物料服务: 成品入库
    └─→ 通知服务: 通知业务员
    ↓
关闭订单
    ↓
发布: pp.production_order.closed
```

---

**文档结束**

---

*本文档版本：v1.0*  
*最后更新：2025-12-12*  
*文档总页数：约80页（基于标准A4格式）*  
*文档总字数：约4.5万字*