# ENG模块 - BOM管理子模块用户故事

**对应菜单：** `/eng/boms`  
**对应用例：** UC-ENG-003, UC-ENG-004, UC-ENG-005

---

## US-ENG-003: 创建BOM

**用户故事：**
```
As an 工程师
I want 创建BOM（物料清单），定义产品的物料组成结构
So that 我可以明确生产所需的所有原材料和用量，用于物料需求计算
```

**优先级：** P0  
**验收标准：**
- Given 父物料已存在
- When 工程师创建BOM并添加BOM明细
- Then 系统创建BOM记录，状态为NEW
- And 系统创建BOM明细记录
- And BOM的base_uom通常为PNL（拼板）
- And BOMItem可以包含层码、物料类型等PCB专用信息

**相关用例：** UC-ENG-003

---

## US-ENG-005: 发布BOM

**用户故事：**
```
As an 工程师
I want 发布BOM
So that BOM可以用于生产版本，指导生产领料
```

**优先级：** P0  
**验收标准：**
- Given BOM状态为REVIEWING
- When 工程师发布BOM
- Then BOM状态更新为RELEASED
- And 只有RELEASED状态的BOM才能用于生产版本

**相关用例：** UC-ENG-005

---

**用户故事统计：**
- P0（关键）：2个
- 总计：2个
