# SD模块 - 销售订单子模块用户故事

**对应菜单：** `/sd/sales-orders`  
**对应用例：** UC-SD-010, UC-SD-011, UC-SD-012, UC-SD-013, UC-SD-014, UC-SD-015, UC-SD-016, UC-SD-017, UC-SD-018, UC-SD-019, UC-SD-020

---

## US-SD-010: 创建销售订单

**用户故事：**
```
As a 销售员
I want 创建销售订单，可以选择关联报价单或直接创建
So that 我可以将客户需求转化为正式订单，启动生产流程
```

**优先级：** P0  
**验收标准：**
- Given 客户状态为ACTIVE
- When 销售员创建销售订单
- Then 系统根据客户ID和本厂编号自动查找FactoryProductMapping
- And 系统自动填充material_code和production_version_id
- And 系统自动计算销售单位、生产单位、转换系数和生产数量
- And 如果是返单，可以选择历史报价单（包括已关联的）
- And 如果是新单，只能选择已批准且未关联的报价单
- And 如果关联了报价单，报价单状态更新为LINKED

**相关用例：** UC-SD-010

---

## US-SD-011: 提交销售订单评审

**用户故事：**
```
As a 销售员
I want 提交销售订单进行多部门评审
So that 销售、工程、物料、财务部门可以分别评审订单，确保订单可执行
```

**优先级：** P0  
**验收标准：**
- Given 销售订单状态为DRAFT
- When 销售员提交评审
- Then 系统创建工作流实例（SALES_ORDER_REVIEW）
- And 系统为所有节点创建节点实例（初始状态为PENDING）
- And 销售订单状态更新为PENDING_REVIEW
- And 销售部门可以开始评审

**相关用例：** UC-SD-011

---

## US-SD-012: 销售部门评审订单

**用户故事：**
```
As a 销售经理/销售员
I want 评审销售订单（销售部门评审节点）
So that 我可以确认订单的销售条款和客户要求是否合理
```

**优先级：** P0  
**验收标准：**
- Given 销售订单已提交评审，当前节点为SALES_REVIEW
- When 销售经理或销售员（SALES/SALES_MANAGER角色）审批通过
- Then 系统更新工作流节点状态为APPROVED
- And 系统记录ContractReview记录
- And 系统移动到下一个节点（ENGINEERING_REVIEW）
- And 销售订单状态更新为REVIEWING

**相关用例：** UC-SD-012

---

## US-SD-013: 工程部门评审订单

**用户故事：**
```
As an 工程师
I want 评审销售订单（工程部门评审节点）
So that 我可以确认订单的物料、BOM、工艺路线等工程数据是否完整和可执行
```

**优先级：** P0  
**验收标准：**
- Given 销售订单已提交评审，当前节点为ENGINEERING_REVIEW
- When 工程师（ENGINEER角色）审批通过
- Then 系统更新工作流节点状态为APPROVED
- And 系统记录ContractReview记录
- And 系统移动到下一个节点（WAREHOUSE_REVIEW）
- And 销售订单状态更新为REVIEWING

**相关用例：** UC-SD-013

---

## US-SD-014: 物料部门评审订单

**用户故事：**
```
As a 物料管理员
I want 评审销售订单（物料部门评审节点）
So that 我可以确认订单的物料库存是否充足，是否可以满足生产需求
```

**优先级：** P0  
**验收标准：**
- Given 销售订单已提交评审，当前节点为WAREHOUSE_REVIEW
- When 物料管理员（WAREHOUSE角色）审批通过
- Then 系统更新工作流节点状态为APPROVED
- And 系统记录ContractReview记录
- And 系统移动到下一个节点（FINANCE_REVIEW）
- And 销售订单状态更新为REVIEWING

**相关用例：** UC-SD-014

---

## US-SD-015: 财务部门评审订单

**用户故事：**
```
As a 财务人员
I want 评审销售订单（财务部门评审节点）
So that 我可以确认订单的财务条款、付款条件等是否符合公司财务政策
```

**优先级：** P0  
**验收标准：**
- Given 销售订单已提交评审，当前节点为FINANCE_REVIEW
- When 财务人员（FINANCE角色）审批通过
- Then 系统更新工作流节点状态为APPROVED
- And 系统记录ContractReview记录
- And 系统检查所有节点是否都已审批通过
- And 如果所有节点都已审批通过，销售订单状态更新为APPROVED

**相关用例：** UC-SD-015

---

## US-SD-016: 查看订单评审状态

**用户故事：**
```
As a 销售员/各部门评审人
I want 查看销售订单的评审状态
So that 我可以了解订单的评审进度，知道当前需要哪个部门评审
```

**优先级：** P1  
**验收标准：**
- Given 销售订单已提交评审
- When 用户查看订单评审状态
- Then 系统显示所有节点的评审进度（销售、工程、物料、财务）
- And 系统显示当前节点（current_node_id）
- And 系统显示每个节点的审批人、审批时间、审批意见

**相关用例：** UC-SD-011相关

---

## US-SD-017: 销售发货

**用户故事：**
```
As a 销售员
I want 记录销售订单的发货信息
So that 我可以跟踪订单的发货状态，客户可以了解货物状态
```

**优先级：** P1  
**验收标准：**
- Given 销售订单状态为COMPLETED
- When 销售员记录发货信息
- Then 销售订单状态更新为SHIPPED
- And 系统记录发货时间和发货人

**相关用例：** UC-SD-017

---

## US-SD-018: 销售签收

**用户故事：**
```
As a 销售员
I want 记录销售订单的客户签收信息
So that 我可以确认客户已收到货物，订单可以进入对账流程
```

**优先级：** P1  
**验收标准：**
- Given 销售订单状态为SHIPPED
- When 销售员记录客户签收信息
- Then 销售订单状态更新为DELIVERED
- And 系统记录签收时间和签收人

**相关用例：** UC-SD-018

---

## US-SD-019: 对账

**用户故事：**
```
As a 财务人员
I want 对销售订单进行对账
So that 我可以确认订单的财务结算，订单可以进入关闭流程
```

**优先级：** P2  
**验收标准：**
- Given 销售订单状态为DELIVERED
- When 财务人员对账
- Then 销售订单状态更新为RECONCILED
- And 系统记录对账时间和对账人

**相关用例：** UC-SD-019

---

## US-SD-020: 关闭销售订单

**用户故事：**
```
As a 销售员/财务人员
I want 关闭销售订单
So that 订单可以结束生命周期，系统可以清理相关资源
```

**优先级：** P2  
**验收标准：**
- Given 销售订单状态为RECONCILED
- When 销售员或财务人员关闭订单
- Then 销售订单状态更新为CLOSED
- And 系统关闭关联的生产订单/工单
- And 系统记录关闭时间和关闭人

**相关用例：** UC-SD-020

---

**用户故事统计：**
- P0（关键）：6个
- P1（高）：3个
- P2（中）：2个
- 总计：11个
