# ENG模块 - 产品主数据子模块用户故事

**对应菜单：** `/eng/factory-product-mappings`  
**对应用例：** UC-ENG-001, UC-ENG-001A

**说明：** 产品主数据通过Material实体实现（material_type='FG'），只显示成品类型的物料。

---

## US-ENG-001: 产品主数据管理

**用户故事：**
```
As an 工程师
I want 管理产品主数据（创建、更新、删除）
So that 我可以维护产品的完整信息，为BOM、工艺路线等提供基础数据
```

**优先级：** P0  
**验收标准：**
- Given 工程师已登录系统
- When 工程师创建产品主数据
- Then 系统创建Material记录，material_type='FG'
- And 产品编码（material_code）必须唯一
- And 系统只显示成品（FG类型）的物料
- And ENG模块拥有完整CRUD权限
- And SD模块可创建（自动创建）、查询、引用，但不能修改、删除

**相关用例：** UC-ENG-001

---

## US-ENG-001A: 产品列表查询

**用户故事：**
```
As an 工程师
I want 查询产品主数据列表
So that 我可以快速找到需要的产品信息
```

**优先级：** P0  
**验收标准：**
- Given 工程师已登录系统
- When 工程师查询产品列表
- Then 系统显示产品列表，只显示成品（FG类型）
- And 系统支持按本厂编号、产品名称、产品系列等条件筛选和分页

**相关用例：** UC-ENG-001A

---

**用户故事统计：**
- P0（关键）：2个
- 总计：2个
