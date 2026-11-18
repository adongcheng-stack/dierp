# ENG模块 - 工艺路线子模块用户故事

**对应菜单：** `/eng/routings`  
**对应用例：** UC-ENG-006, UC-ENG-007, UC-ENG-008

---

## US-ENG-006: 创建工艺路线

**用户故事：**
```
As an 工程师
I want 创建工艺路线，定义产品的生产工艺流程
So that 我可以明确生产的工序序列、工作中心和时间参数，用于生产计划和报工
```

**优先级：** P0  
**验收标准：**
- Given 物料已存在
- When 工程师创建工艺路线并添加工序
- Then 系统创建工艺路线记录，状态为DRAFT
- And 系统创建工序记录
- And 工艺路线的基础单位通常为PNL（拼板）
- And 工序按operation_no排序执行
- And 工序类型可以是internal、external或quality

**相关用例：** UC-ENG-006

---

## US-ENG-008: 发布工艺路线

**用户故事：**
```
As an 工程师
I want 发布工艺路线
So that 工艺路线可以用于生产版本，指导生产执行
```

**优先级：** P0  
**验收标准：**
- Given 工艺路线状态为DRAFT
- When 工程师发布工艺路线
- Then 工艺路线状态更新为RELEASED
- And 只有RELEASED状态的工艺路线才能用于生产版本

**相关用例：** UC-ENG-008

---

**用户故事统计：**
- P0（关键）：2个
- 总计：2个
