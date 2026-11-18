# 用户与权限管理模块 - 用户管理子模块领域模型

**对应菜单：** `/admin/users`  
**版本：** v1.0  
**创建日期：** 2025-01-XX

---

## 一、模块概述

用户管理子模块负责管理系统用户，包括用户创建、更新、删除、登录、登出等功能。用户通过角色进行权限控制。

---

## 二、核心实体

### 2.1 User（用户）

- **表：** `users`
- **主键：** `id`（BaseModel），业务键：`username`
- **角色枚举：** `UserRole`（SALES, SALES_MANAGER, ENGINEER, PLANNER, PRODUCTION, WAREHOUSE, FINANCE, ACCOUNT_MANAGER, GENERAL_MANAGER, ADMIN）
- **关键字段：**
  - `username`：用户名（唯一）
  - `email`：邮箱（唯一）
  - `password_hash`：密码哈希
  - `full_name`：全名
  - `role`：角色（Enum）
  - `department`：部门
  - `is_active`：是否激活
  - `phone`：电话
- **角色说明：**
  - `SALES`：销售员，负责客户管理、报价单创建和销售订单创建
  - `SALES_MANAGER`：销售经理，负责报价单一级审核、销售订单评审
  - `ENGINEER`：工程师，负责工程数据管理、报价单二级审核、销售订单工程部门评审
  - `PLANNER`：计划员，负责生产计划和生产订单管理
  - `PRODUCTION`：生产人员，负责生产执行和工序报工
  - `WAREHOUSE`：物料管理员，负责物料管理和生产领料
  - `FINANCE`：财务人员，负责报价单三级审核、销售订单财务部门评审、对账
  - `ACCOUNT_MANAGER`：客户经理，负责报价单三级审核（与GENERAL_MANAGER共同承担）
  - `GENERAL_MANAGER`：总经理，负责报价单三级审核（与ACCOUNT_MANAGER共同承担）
  - `ADMIN`：系统管理员，负责用户管理和系统配置
- **说明：**
  - 用户名和邮箱必须唯一
  - 密码需要进行哈希处理
  - 只有激活的用户才能登录
  - 支持软删除（is_deleted字段）

---

## 三、业务规则

1. **用户名唯一性**：用户名（username）必须在系统中唯一。
2. **邮箱唯一性**：邮箱（email）必须在系统中唯一。
3. **密码安全**：密码需要进行哈希处理，不存储明文密码。
4. **激活要求**：只有激活的用户（is_active=true）才能登录系统。
5. **角色权限**：用户通过角色进行权限控制，不同角色具有不同的操作权限。
6. **软删除**：支持软删除（is_deleted字段），保留用户历史记录。

---

## 四、聚合根

**User聚合根**：User

---

## 五、相关文档

- [用例文档](../某某ERP系统02%20-%20用例（Use%20Cases）.md) - UC-USER-001 至 UC-USER-005
- [用户故事文档](../用户故事/USER-用户管理用户故事.md)
- [数据模型文档](../某某ERP系统%20-%20数据模型（ER）.md)
