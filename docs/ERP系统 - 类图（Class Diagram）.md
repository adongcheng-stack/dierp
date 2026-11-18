# 某某ERP系统 - 类图（Class Diagram）

## 文档说明

**版本：** v1.4  
**创建日期：** 2025-12-12  
**最后更新：** 2025-01-XX

**基于**：某某ERP系统MVP版本需求规格说明书 v1.4

本文档使用Mermaid语法描述了某某ERP系统的类图（Class Diagram），按模块展示所有实体类及其属性、方法和关系。

---

## 一、销售与分销模块（SD Module）

### 1.1 客户管理类图

```mermaid
classDiagram
    class Customer {
        +Integer id
        +String customer_id
        +String legal_name
        +String trade_name
        +String tax_id
        +String customer_industry
        +String customer_website
        +Enum customer_status
        +BigDecimal credit_limit
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class CustomerAddress {
        +Integer id
        +String customer_id
        +String address_type
        +String detail_address
        +String location
        +String postal_code
        +String country
        +String province
        +String city
        +String district
        +Boolean is_default_shipping
        +Boolean is_default_billing
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class CustomerContact {
        +Integer id
        +String customer_id
        +Boolean is_primary_contact
        +String contact_name
        +String contact_role
        +String contact_department
        +String contact_phone
        +String contact_email
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class CustomerPartnerFunction {
        +Integer id
        +String customer_id
        +String partner_function_type
        +Date partner_start_date
        +String partner_name
        +String partnership_description
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class CustomerSalesData {
        +Integer id
        +String customer_id
        +String sales_organization
        +String account_manager_name
        +String sales_assistant_name
        +String trading_currency
        +String primary_trade_country
        +String incoterms
        +String shipping_conditions
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    Customer "1" --> "*" CustomerAddress : has
    Customer "1" --> "*" CustomerContact : has
    Customer "1" --> "*" CustomerPartnerFunction : has
    Customer "1" --> "*" CustomerSalesData : has
```

### 1.2 报价与订单类图

```mermaid
classDiagram
    class Customer {
        +String customer_id
        +String legal_name
    }
    
    class Quotation {
        +Integer id
        +String quotation_number
        +String customer_id
        +String product_number
        +BigDecimal quantity
        +BigDecimal unit_price
        +BigDecimal total_amount
        +String currency
        +Date valid_until
        +Enum status
        +String sales_approver
        +Timestamp sales_approved_at
        +String finance_approver
        +Timestamp finance_approved_at
        +String general_manager_approver
        +Timestamp general_manager_approved_at
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class QuotationItem {
        +Integer id
        +String quotation_number
        +Integer line_number
        +String material_code
        +String material_name
        +BigDecimal quantity
        +BigDecimal unit_price
        +BigDecimal total_price
        +String remarks
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class SalesOrder {
        +Integer id
        +String order_number
        +String quotation_number
        +String customer_id
        +String product_number
        +String material_code
        +String production_version_id
        +BigDecimal quantity
        +String sales_unit
        +BigDecimal production_quantity
        +String production_unit
        +BigDecimal conversion_factor
        +Date delivery_date
        +Enum status
        +Boolean is_return_order
        +String review_status
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class ContractReview {
        +Integer id
        +String sales_order_number
        +String reviewer_role
        +String reviewer
        +String review_result
        +String review_comment
        +Timestamp reviewed_at
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class Material {
        +String material_code
        +String material_name
    }
    
    class ProductionVersion {
        +String production_version_id
    }
    
    Customer "1" --> "*" Quotation : places
    Customer "1" --> "*" SalesOrder : orders
    Quotation "1" --> "*" QuotationItem : contains
    Quotation "1" --> "*" SalesOrder : converts_to
    SalesOrder "1" --> "*" ContractReview : has
    SalesOrder --> Material : references
    SalesOrder --> ProductionVersion : uses
```

### 1.3 本厂编号映射类图

```mermaid
classDiagram
    class Customer {
        +String customer_id
    }
    
    class FactoryProductMapping {
        +Integer id
        +String customer_id
        +String factory_product_number
        +String material_code
        +String production_version_id
        +Boolean is_default
        +Timestamp effective_date
        +Timestamp expiry_date
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class Material {
        +String material_code
        +String material_name
    }
    
    class ProductionVersion {
        +String production_version_id
    }
    
    Customer "1" --> "*" FactoryProductMapping : has
    Material "1" --> "*" FactoryProductMapping : mapped_by
    ProductionVersion "1" --> "*" FactoryProductMapping : mapped_by
```

---

## 二、工程管理模块（ENG Module）

### 2.1 物料管理类图

```mermaid
classDiagram
    class Material {
        +Integer id
        +String material_code
        +String material_name
        +String material_type
        +String status
        +String base_unit
        +String production_unit
        +BigDecimal conversion_factor
        +BigDecimal current_stock
        +BigDecimal safety_stock
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class BOM {
        +Integer id
        +String bom_number
        +String version
        +String parent_material_code
        +BigDecimal base_quantity
        +String base_uom
        +Enum status
        +Date effective_date
        +Date expiry_date
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class BOMItem {
        +Integer id
        +String bom_number
        +Integer line_number
        +String material_code
        +String item_category
        +BigDecimal quantity
        +String unit
        +BigDecimal scrap_rate
        +String layer_code
        +String material_type
        +String process_step
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    Material "1" --> "*" BOM : has
    BOM "1" --> "*" BOMItem : contains
    Material "1" --> "*" BOMItem : used_in
```

### 2.2 工艺路线类图

```mermaid
classDiagram
    class Material {
        +String material_code
        +String material_name
    }
    
    class Routing {
        +Integer id
        +String routing_id
        +String version
        +String material_code
        +String base_unit
        +BigDecimal base_quantity
        +Integer units_per_panel
        +String panel_size
        +Enum status
        +Date effective_date
        +Date expiry_date
        +String change_request_no
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class RoutingOperation {
        +Integer id
        +String routing_id
        +String operation_no
        +String operation_code
        +String operation_name
        +String operation_type
        +String work_center_id
        +String sop_link
        +BigDecimal setup_time
        +BigDecimal machine_time
        +BigDecimal labor_time
        +BigDecimal queue_time
        +Boolean cost_relevant
        +Boolean scheduling_relevant
        +Boolean needs_reporting
        +Boolean auto_deduct_material
        +Boolean trigger_quality_check
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class WorkCenter {
        +String work_center_id
        +String description
    }
    
    Material "1" --> "*" Routing : has
    Routing "1" --> "*" RoutingOperation : contains
    RoutingOperation --> WorkCenter : uses
```

### 2.3 生产版本类图

```mermaid
classDiagram
    class Material {
        +String material_code
    }
    
    class BOM {
        +String bom_number
    }
    
    class Routing {
        +String routing_id
    }
    
    class MI {
        +Integer id
        +String mi_number
        +String version
        +String material_code
        +String description
        +Enum status
        +Date effective_date
        +Date expiry_date
        +String content
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class ProductionVersion {
        +Integer id
        +String production_version_id
        +String version
        +String material_code
        +String bom_number
        +String routing_id
        +String mi_number
        +String status
        +Date effective_date
        +Date expiry_date
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    Material "1" --> "*" ProductionVersion : has
    BOM "1" --> "*" ProductionVersion : used_in
    Routing "1" --> "*" ProductionVersion : used_in
    MI "1" --> "*" ProductionVersion : used_in
    Material "1" --> "*" MI : has
```

---

## 三、物料管理模块（MM Module）

### 3.1 物料事务类图

```mermaid
classDiagram
    class Material {
        +String material_code
        +String material_name
        +BigDecimal current_stock
    }
    
    class MaterialIssue {
        +Integer id
        +String issue_number
        +String production_order_number
        +String material_code
        +BigDecimal quantity
        +String unit
        +String warehouse
        +String issued_by
        +Timestamp issued_at
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class MaterialTransaction {
        +Integer id
        +String transaction_number
        +String material_code
        +String transaction_type
        +BigDecimal quantity
        +String unit
        +String reference_number
        +String reference_type
        +Timestamp transaction_date
        +String operator
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class ProductionOrder {
        +String order_number
    }
    
    Material "1" --> "*" MaterialIssue : issued
    Material "1" --> "*" MaterialTransaction : transacted
    ProductionOrder "1" --> "*" MaterialIssue : generates
```

---

## 四、生产计划与控制模块（PP Module）

### 4.1 工作中心类图

```mermaid
classDiagram
    class WorkCenter {
        +Integer id
        +String work_center_id
        +String description
        +String work_center_type
        +String plant_id
        +Enum status
        +String parent_work_center_id
        +Integer hierarchy_level
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    WorkCenter "1" --> "*" WorkCenter : parent
```

### 4.2 生产订单类图

```mermaid
classDiagram
    class SalesOrder {
        +String order_number
        +String customer_id
    }
    
    class ProductionOrder {
        +Integer id
        +String order_number
        +String sales_order_number
        +String material_code
        +String production_version_id
        +BigDecimal quantity
        +String unit
        +BigDecimal sales_quantity
        +String sales_unit
        +BigDecimal conversion_factor
        +Date planned_start_date
        +Date planned_finish_date
        +Date actual_start_date
        +Date actual_finish_date
        +Enum status
        +String lot_number
        +String remarks
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class Material {
        +String material_code
    }
    
    class ProductionVersion {
        +String production_version_id
    }
    
    SalesOrder "1" --> "*" ProductionOrder : creates
    Material "1" --> "*" ProductionOrder : produces
    ProductionVersion "1" --> "*" ProductionOrder : uses
```

### 4.3 工序报工类图

```mermaid
classDiagram
    class ProductionOrder {
        +String order_number
    }
    
    class RoutingOperation {
        +Integer id
        +String routing_id
        +String operation_no
    }
    
    class WorkCenter {
        +String work_center_id
        +String description
    }
    
    class OperationReport {
        +Integer id
        +String report_number
        +String production_order_number
        +Integer routing_operation_id
        +String work_center_id
        +String operation_no
        +String operation_name
        +BigDecimal reported_quantity
        +BigDecimal good_quantity
        +BigDecimal scrap_quantity
        +BigDecimal setup_time
        +BigDecimal machine_time
        +BigDecimal labor_time
        +String reported_by
        +Timestamp reported_at
        +Enum status
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    ProductionOrder "1" --> "*" OperationReport : generates
    RoutingOperation "1" --> "*" OperationReport : reported_for
    WorkCenter "1" --> "*" OperationReport : reports_to
```

---

## 五、用户与权限管理模块

### 5.1 用户类图

```mermaid
classDiagram
    class User {
        +Integer id
        +String username
        +String email
        +String password_hash
        +String full_name
        +Enum role
        +String department
        +Boolean is_active
        +String phone
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
```

---

## 六、工作流模块

### 6.1 工作流类图

```mermaid
classDiagram
    class Workflow {
        +Integer id
        +String workflow_id
        +String workflow_name
        +String module
        +String description
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class WorkflowNode {
        +Integer id
        +String workflow_id
        +String node_id
        +String node_name
        +String node_type
        +String approver_role
        +Integer order
        +JSON config
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    class WorkflowInstance {
        +Integer id
        +String instance_id
        +String workflow_id
        +String business_id
        +String business_type
        +Enum status
        +String current_node_id
        +String created_by
        +Timestamp created_at
        +Timestamp completed_at
        +Boolean is_deleted
    }
    
    class WorkflowInstanceNode {
        +Integer id
        +String instance_id
        +String node_id
        +Enum status
        +String approver
        +Timestamp approved_at
        +String comment
        +Integer order
        +String created_by
        +Timestamp created_at
        +String updated_by
        +Timestamp updated_at
        +Boolean is_deleted
    }
    
    Workflow "1" --> "*" WorkflowNode : contains
    Workflow "1" --> "*" WorkflowInstance : instantiates
    WorkflowInstance "1" --> "*" WorkflowInstanceNode : has
```

---

## 七、跨模块关系类图

### 7.1 核心业务流程类图

```mermaid
classDiagram
    class Customer {
        +String customer_id
        +String legal_name
    }
    
    class Quotation {
        +String quotation_number
        +String customer_id
    }
    
    class SalesOrder {
        +String order_number
        +String customer_id
        +String quotation_number
        +String material_code
        +String production_version_id
    }
    
    class ProductionOrder {
        +String order_number
        +String sales_order_number
        +String material_code
        +String production_version_id
    }
    
    class Material {
        +String material_code
        +String material_name
    }
    
    class ProductionVersion {
        +String production_version_id
        +String material_code
        +String bom_number
        +String routing_id
    }
    
    class MaterialIssue {
        +String issue_number
        +String production_order_number
        +String material_code
    }
    
    class OperationReport {
        +String report_number
        +String production_order_number
        +Integer routing_operation_id
        +String work_center_id
    }
    
    Customer --> Quotation : places
    Customer --> SalesOrder : orders
    Quotation --> SalesOrder : converts_to
    SalesOrder --> ProductionOrder : creates
    Material --> SalesOrder : ordered
    Material --> ProductionOrder : produced
    ProductionVersion --> SalesOrder : specifies
    ProductionVersion --> ProductionOrder : defines
    ProductionOrder --> MaterialIssue : requires
    ProductionOrder --> OperationReport : tracks
```

---

## 八、数据类型说明

### 8.1 基本数据类型映射

| 数据库类型 | Java类型 | Python类型 | 说明 |
|-----------|---------|-----------|------|
| SERIAL | Integer | int | 自增整数 |
| VARCHAR(n) | String | str | 字符串 |
| NUMERIC(p,s) | BigDecimal | Decimal | 精确数值 |
| DATE | Date | date | 日期 |
| TIMESTAMP | Timestamp | datetime | 日期时间 |
| BOOLEAN | Boolean | bool | 布尔值 |
| ENUM | Enum | Enum | 枚举类型 |
| TEXT | String | str | 长文本 |
| JSON | JSON | dict | JSON对象 |

### 8.2 关系类型说明

- **1 --> ***: 一对多关系（One-to-Many）
- **1 --> 1**: 一对一关系（One-to-One）
- **-->**: 关联关系（Association）
- **-->**: 依赖关系（Dependency）

---

## 九、类图设计说明

### 9.1 设计原则

1. **单一职责原则**：每个类只负责一个业务实体
2. **关系清晰**：明确展示类之间的关联关系
3. **属性完整**：包含所有业务属性和审计字段
4. **模块化**：按业务模块组织类图

### 9.2 命名规范

- **类名**：使用PascalCase（如 `Customer`, `SalesOrder`）
- **属性名**：使用camelCase（如 `customerId`, `orderNumber`）
- **关系名**：使用动词短语（如 `has`, `contains`, `references`）

### 9.3 关系类型

- **组合关系（Composition）**：强拥有关系，用实心菱形表示
- **聚合关系（Aggregation）**：弱拥有关系，用空心菱形表示
- **关联关系（Association）**：一般关联，用实线箭头表示
- **依赖关系（Dependency）**：使用关系，用虚线箭头表示
- **继承关系（Inheritance）**：泛化关系，用实线三角箭头表示
- **实现关系（Realization）**：接口实现，用虚线三角箭头表示

### 9.4 类图使用说明

1. **属性可见性**：
   - `+` 表示 public（公共）
   - `-` 表示 private（私有）
   - `#` 表示 protected（受保护）
   - `~` 表示 package（包内可见）

2. **关系基数**：
   - `1` 表示一个
   - `*` 表示多个（0或多个）
   - `1..*` 表示一个或多个
   - `0..1` 表示零个或一个

3. **数据类型**：
   - 使用简化的类型表示（如 String, Integer, BigDecimal）
   - 枚举类型用 Enum 表示
   - 日期时间用 Timestamp 或 Date 表示

---

## 十、模块类图总结

### 10.1 模块统计

| 模块 | 类数量 | 主要类 |
|------|--------|--------|
| 销售与分销（SD） | 10 | Customer, Quotation, SalesOrder, ContractReview |
| 工程管理（ENG） | 7 | Material, BOM, Routing, ProductionVersion |
| 物料管理（MM） | 2 | MaterialIssue, MaterialTransaction |
| 生产计划与控制（PP） | 3 | WorkCenter, ProductionOrder, OperationReport |
| 用户与权限管理 | 1 | User |
| 工作流 | 4 | Workflow, WorkflowNode, WorkflowInstance |
| **总计** | **27** | |

### 10.2 核心类关系

1. **Customer（客户）**：作为销售模块的核心实体，关联多个子实体
2. **Material（物料）**：作为工程模块的核心实体，关联BOM、Routing、MI等
3. **ProductionVersion（生产版本）**：整合BOM、Routing、MI，连接销售和生产
4. **SalesOrder（销售订单）**：连接客户和生产的桥梁
5. **ProductionOrder（生产订单）**：连接销售和生产执行

### 10.3 关键业务流程类关系链

```
Customer → Quotation → SalesOrder → ProductionOrder → OperationReport
                ↓
         MaterialIssue
                ↓
         MaterialTransaction
```

---

## 十一、类图与ER图对比

### 11.1 相同点

- 都展示实体/类及其属性
- 都展示实体/类之间的关系
- 都按模块组织

### 11.2 不同点

| 特性 | ER图 | 类图 |
|------|------|------|
| 关注点 | 数据模型、表结构 | 对象模型、类结构 |
| 关系表示 | 外键关系 | 对象引用关系 |
| 属性类型 | 数据库类型 | 编程语言类型 |
| 用途 | 数据库设计 | 代码设计 |

### 11.3 使用场景

- **ER图**：用于数据库设计、数据建模、DBA工作
- **类图**：用于面向对象设计、代码开发、架构设计

---

## 十二、扩展说明

### 12.1 未来扩展

1. **服务层类图**：展示Service类的设计
2. **控制器类图**：展示API Controller的设计
3. **DTO类图**：展示数据传输对象的设计
4. **领域模型类图**：展示领域模型的设计

### 12.2 设计模式应用

1. **Repository模式**：数据访问层
2. **Service模式**：业务逻辑层
3. **DTO模式**：数据传输层
4. **Factory模式**：对象创建
5. **Strategy模式**：策略选择

---

## 十三、总结

### 13.1 类图特点

1. **完整性**：覆盖所有业务实体类
2. **清晰性**：关系明确，易于理解
3. **模块化**：按业务模块组织
4. **标准化**：遵循UML类图规范

### 13.2 关键设计决策

1. **实体类设计**：每个数据库表对应一个实体类
2. **关系设计**：使用对象引用而非外键ID
3. **属性设计**：包含业务属性和审计属性
4. **模块划分**：按业务功能模块组织

### 13.3 使用建议

1. **开发阶段**：参考类图进行代码实现
2. **设计阶段**：使用类图进行架构设计
3. **文档阶段**：使用类图进行技术文档编写
4. **培训阶段**：使用类图进行新人培训

---

**文档版本：** v1.0  
**最后更新：** 2025-12-12  
**维护者：** 开发团队