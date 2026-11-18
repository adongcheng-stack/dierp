# SD模块 - 报价单子模块领域模型

**对应菜单：** `/sd/quotations`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

报价单子模块负责管理销售报价单，包括报价单创建、三级审核流程、客户确认等。报价单采用手动计算模式，需要经过销售经理、工程师、客户经理或总经理的三级审核。

---

## 二、核心实体

### 2.1 Quotation（报价单）

- **表：** `quotations`
- **主键：** `id`（BaseModel），业务键：`quotation_number`
- **状态枚举：** `QuotationStatus`（DRAFT, PENDING_SALES, PENDING_ENGINEER, PENDING_ACCOUNT_MANAGER, APPROVED, REJECTED, CUSTOMER_CONFIRMED, LINKED, CANCELLED）
- **关键字段：**
  - **基本字段：**
    - `quotation_number`：报价单号
    - `customer_id`：客户ID（外键 → customers.customer_id）
    - `product_number`：本厂编号（14位）
    - `product_name`：产品名称
    - `quantity`：数量
    - `unit_price`：单价
    - `total_amount`：总金额
    - `currency`：货币
  - **审批字段：**
    - `sales_approver`：一级审核人（SALES_MANAGER）
    - `sales_approved_at`：一级审核时间
    - `engineer_approver`：二级审核人（ENGINEER）
    - `engineer_approved_at`：二级审核时间
    - `account_manager_approver`：三级审核人（ACCOUNT_MANAGER）
    - `general_manager_approver`：三级审核人（GENERAL_MANAGER）
    - `account_manager_approved_at`：三级审核时间
  - **工艺/产品配置：**
    - `board_spec`：板规格参数（出货长、出货宽、利用率、PNL参数等）
    - `process_params`：工艺参数（层数、板厚、铜厚、线宽线距、表面处理等）
    - `pricing_options`：加价选项（常规加价、特殊加价、额外加价等）
  - **报价计算：**
    - `delivery_area`：交货面积
    - `actual_p_input`：实际P输入
    - `cost_per_m2`：成本/平米
    - `cost_per_pcs`：成本PCS
    - `quote_price_per_m2`：报价价格/平米
    - `quote_price_per_pcs`：报价价格PCS
    - `engineering_fee`：工程费
    - `board_material_fee`：板材费
    - `test_fixture`：测试架费用
    - `other_costs`：其他费用
    - `final_total_price`：最终总价
    - `process_details`：工序成本明细（JSON格式）
  - **客户确认：**
    - `customer_confirmed`：客户已确认（布尔值）
    - `customer_confirmed_at`：客户确认时间
    - `customer_confirmed_by`：客户确认人（销售员代客户操作）
- **关联：**
  - N:1 `Customer`（客户）
  - 1:N `QuotationItem`（报价单明细）
- **说明：**
  - 报价单预估报价采用手动计算模式（点击"计算报价"按钮），不提供实时自动计算。
  - 报价单审批流程为三级审核串行：一级审核（SALES_MANAGER） → 二级审核（ENGINEER） → 三级审核（ACCOUNT_MANAGER或GENERAL_MANAGER）。
  - 审批通过后进入"销售员经客户确认"状态，客户确认是线下确认，销售员在系统中标记"客户已确认"。
  - 如果本厂编号对应的产品主数据不存在，SD模块调用ENG模块的产品主数据创建API自动创建产品主数据（产品编码为本厂编号，产品类型为成品FG，物料分类为成品），自动创建的产品主数据不需要审核。
  - 任何一级审核不通过时，报价单状态退回草稿（DRAFT），销售员可修改后重新提交。

### 2.2 QuotationItem（报价单明细）

- **表：** `quotation_items`
- **关键字段：**
  - `quotation_number`：报价单号（外键）
  - `line_number`：行号
  - `material_code`：物料编码
  - `quantity`：数量
  - `unit_price`：单价
  - `total_price`：总价
  - `description`：描述
- **说明：** 报价单可以包含多个明细项。

---

## 三、状态机

### 3.1 Quotation状态

- **DRAFT**：草稿，报价单创建但未提交
- **PENDING_SALES**：待一级审核，等待销售经理（SALES_MANAGER）审核
- **PENDING_ENGINEER**：待二级审核，等待工程师（ENGINEER）审核
- **PENDING_ACCOUNT_MANAGER**：待三级审核，等待客户经理（ACCOUNT_MANAGER）或总经理（GENERAL_MANAGER）审核
- **APPROVED**：已审批，所有三级审批通过
- **REJECTED**：已拒绝，任一审批节点被拒绝，退回草稿状态
- **CUSTOMER_CONFIRMED**：客户已确认，客户确认报价单（销售员代客户操作）
- **LINKED**：已关联，已关联到销售订单
- **CANCELLED**：已取消，报价单被取消

### 3.2 状态转换规则

- DRAFT → PENDING_SALES：提交审批（销售员）
- PENDING_SALES → PENDING_ENGINEER：一级审核通过（销售经理）
- PENDING_SALES → REJECTED：一级审核拒绝（销售经理）
- PENDING_ENGINEER → PENDING_ACCOUNT_MANAGER：二级审核通过（工程师）
- PENDING_ENGINEER → REJECTED：二级审核拒绝（工程师）
- PENDING_ACCOUNT_MANAGER → APPROVED：三级审核通过（客户经理/总经理）
- PENDING_ACCOUNT_MANAGER → REJECTED：三级审核拒绝（客户经理/总经理）
- REJECTED → DRAFT：退回草稿（系统自动）
- DRAFT → PENDING_SALES：重新提交（销售员）
- APPROVED → CUSTOMER_CONFIRMED：客户确认（销售员代客户操作）
- APPROVED → CANCELLED：取消报价单（销售员/销售经理）
- CUSTOMER_CONFIRMED → LINKED：创建销售订单（销售员）
- CUSTOMER_CONFIRMED → DRAFT：客户不确认（销售员）

---

## 四、业务规则

1. **客户状态要求**：只有ACTIVE状态的客户才能创建报价单。
2. **产品主数据自动创建**：如果本厂编号对应的产品主数据不存在，SD模块调用ENG模块API自动创建产品主数据，自动创建的产品主数据不需要审核。
3. **报价计算模式**：报价单预估报价采用手动计算模式（点击"计算报价"按钮），不提供实时自动计算。
4. **三级审核流程**：报价单必须经过三级审核流程（串行）：DRAFT → 待一级审核（SALES_MANAGER） → 待二级审核（ENGINEER） → 待三级审核（ACCOUNT_MANAGER或GENERAL_MANAGER） → APPROVED → 销售员经客户确认 → 可转订单。
5. **拒绝处理**：任何一级审核不通过时，报价单状态退回草稿（DRAFT），销售员可修改后重新提交。退回操作记录审核历史，保存退回原因。
6. **客户确认**：客户确认是线下确认，销售员在系统中标记"客户已确认"。客户确认后可以转为销售订单。客户不确认时，报价单退回草稿状态。
7. **本厂编号格式**：本厂编号必须为14位，系统需要验证格式。

---

## 五、聚合根

**Quotation聚合根**：Quotation + QuotationItem

---

## 六、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-SD-004, UC-SD-005, UC-SD-006, UC-SD-007, UC-SD-008, UC-SD-009
- [用户故事文档](../用户故事/SD-报价单用户故事.md)
- [状态机文档](../状态机图/SD-报价单状态机.puml)
