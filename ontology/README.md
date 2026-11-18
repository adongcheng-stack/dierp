# DIERP 领域本体（Ontology）

本目录承载 DIERP 制造 ERP 的**语义层**，用于把“业务概念、枚举、约束、派生规则”从代码里抽出来，作为后端模型、前端类型和数据库脚本的共同上游。

当前覆盖：**P0 计划域（MPS / MRP / 计划订单 / 需求追溯 / 异常 / 齐套 / 计划参数）**，并已为后续 APS、QMS、EAM、成本与业财预留本体分类。

---

## 1. 目录结构

```
ontology/
├── src/
│   ├── erp-ontology.ttl      # OWL 类、对象属性、数据属性
│   ├── shapes.ttl            # SHACL 形状约束（必填、枚举、数值范围）
│   ├── rules.swrl            # SWRL 派生规则（如净需求、缺料判定）
│   └── mappings.json         # 枚举唯一事实源
├── model/
│   └── planning.yaml         # 计划域 operational model（模型生成唯一源）
├── data/
│   └── demo.ttl              # 演示本体实例
├── generated/
│   └── types.ts              # 由 mappings.json 生成的 TS 枚举/联合类型
├── scripts/
│   ├── generate-types.py     # mappings.json → generated/types.ts
│   ├── validate-type-sync.js # Node 侧：TTL / mappings / TS 枚举一致性
│   └── validate-consistency.py # Python 侧：TTL / SHACL / mappings / YAML 一致性
├── package.json
└── README.md
```

---

## 2. 单一事实源规则

| 内容 | 唯一事实源 | 生成/派生目标 |
|---|---|---|
| 枚举值 | `src/mappings.json` | `generated/types.ts`、`shapes.ttl`、后端枚举、前端联合类型 |
| 计划域实体与字段 | `model/planning.yaml` | `backend/common/models/planning.py`、`frontend/src/types/planning.generated.ts` |
| 语义约束 | `src/shapes.ttl` | 双栈校验脚本、接口层校验 |
| 派生业务规则 | `src/rules.swrl` | 文档、后续规则引擎/推理器 |
| 类与属性 | `src/erp-ontology.ttl` | 语义查询、追溯、后续知识图谱 |

**不要直接修改生成物**：

- `backend/common/models/planning.py`
- `frontend/src/types/planning.generated.ts`
- `ontology/generated/types.ts`

文件头均标注 `GENERATED FILE - DO NOT EDIT BY HAND`。改字段请改 `model/planning.yaml` 后重跑生成器；改枚举请先改 `mappings.json`。

---

## 3. 常用命令

在仓库根目录执行：

```bash
# 1) 由 mappings.json 重新生成 TS 枚举
cd ontology
python scripts/generate-types.py

# 2) 双栈一致性校验
npm run check:node
python scripts/validate-consistency.py

# 3) 由 planning.yaml 重新生成后端模型与前端类型
cd ..
python backend/ontology/generate_models.py

# 4) 增量创建计划/成本表并写入种子数据
python backend/upgrade_planning.py

# 5) 后端计划冒烟
python backend/scripts/smoke_planning.py
python backend/scripts/smoke_planning_api.py

# 6) 重建演示数据并导出前端 mock 快照
python backend/scripts/refresh_planning_demo.py
```

> 运行 Python 脚本时需保证仓库根目录在 `PYTHONPATH` 中，或直接在根目录执行。

---

## 4. 当前计划域模型（18 个实体）

| 分类 | 实体 |
|---|---|
| 计划参数 | `PlanningPolicy` |
| 需求输入 | `Forecast`、`MpsPlan`、`MpsEntry` |
| MRP 运算 | `MrpRun`、`MrpRequirement`、`PlannedOrder`、`PeggingLink`、`MrpException` |
| 执行闭环 | `KittingResult`、`PurchaseOrder`、`PurchaseOrderLine` |
| 日历/成本预留 | `WorkCalendar`、`CostRate`、`StandardCost`、`ProductionCost`、`CostVariance`、`CostSettlement` |

枚举覆盖：`ProcurementType`、`MrpType`、`MpsPlanStatus`、`MrpRunType/Status`、`PlannedOrderType/Status`、`LotSizingRule`、`PlannerAction`、`MrpExceptionType`、`ExceptionSeverity`、`ResolutionStatus`、`DemandType`、`SupplyType`、`KitStatus`、`CostRateType`、`VarianceType`、`CostStatus`、`PurchaseOrderStatus` 等。

---

## 5. 新增一个实体/字段的流程

1. 若涉及新枚举：先在 `src/mappings.json` 增加枚举与值。
2. 在 `model/planning.yaml` 增加实体或字段，明确类型、长度、默认值、外键、注释。
3. 若需要语义约束：同步补充 `src/shapes.ttl`。
4. 运行 `python backend/ontology/generate_models.py`。
5. 运行 `python backend/upgrade_planning.py`（或编写对应增量建表脚本）。
6. 运行双栈校验与后端冒烟。
7. 若前端需要展示，更新页面与 `frontend/src/mock/handlers.ts`、`snapshot.json`。

### 命名与枚举注意

- 数据库列、API 字段统一 `snake_case`。
- 本体 `DocumentStatus` 使用 `IN_PROGRESS`；现有生产工单状态使用 `IN_PRODUCTION`，两者不要混用。
- 枚举列在 SQLAlchemy 中使用 `SQLEnum`，字符串值需与 `mappings.json` 完全一致。
- 新增枚举值后必须重新生成 `generated/types.ts`，否则前端类型与后端会漂移。

---

## 6. 设计边界

- 本体是**模型与约束的上游**，不是运行时数据库；运行时仍以 PostgreSQL 为准。
- 当前不引入重型推理机；SWRL 规则作为语义说明与后续规则引擎输入。
- `planning.yaml` 只描述计划/成本域，不复制既有销售、工程、生产、物料主数据模型。
- 演示数据（`data/demo.ttl` 与前端 snapshot）用于验证语义和端到端流程，不替代真实迁移脚本。
