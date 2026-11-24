# DIERP 领域本体（Ontology）

本目录承载 DIERP 制造 ERP 的**语义层**，用于把“业务概念、枚举、约束、派生规则”从代码里抽出来，作为后端模型、前端类型和数据库脚本的共同上游。

当前覆盖：**P0 计划域（MPS / MRP / 计划订单 / 需求追溯 / 异常 / 齐套 / 计划参数）**，以及**业财闭环（总账/会计期间）、库存估值（移动加权）、采购与质量、组织权限、驾驶舱预警**；三类运营模型共 59 个实体，均已在 OWL 本体中声明对应类（4 个单据行项目按约定走父单据形状校验）。

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

### AI 只读投影 `model/ai-projection.yaml`

该文件**不是**模型生成源：不写入 `generate_models.py` 的模型列表，也不参与 `validate-consistency.py` 的 YAML 校验，因此修改它不会生成任何 SQLAlchemy/TS 代码。

它只做两件事，供 AI 语义目录（`backend/services/ai/catalog.py`）构建只读契约：

1. `entities`：登记未进入 YAML 的遗留表（materials / sales_orders / production_orders / customers）对 AI 可见的字段白名单与本体锚点；
2. `entity_overrides`：登记 YAML 实体的“物理列 → 形状 `sh:path`”覆盖（如 `forecast_number → documentNumber`）与域例外（SalesInvoice / ReceivableEntry → `finance`）。

约束：投影字段必须存在于 `Base.metadata`；类/形状必须存在于 TTL；形状路径未命中数必须为 0，否则目录构建直接失败。**override 不写回 `model/*.yaml`**。

---

## 3. 常用命令

在仓库根目录执行：

```bash
# 1) 由 mappings.json 重新生成 TS 枚举
cd ontology
python scripts/generate-types.py

# 2) 双栈一致性校验（含 YAML 实体 → 本体类/顶层范畴/形状覆盖）
npm run check:node
python scripts/validate-consistency.py

# 3) 生成物漂移检查（CI 门禁项，只读不写；回到仓库根目录）
cd ..
python backend/ontology/generate_models.py --check
python ontology/scripts/generate-types.py --check

# 4) 由 model/*.yaml 重新生成后端模型与前端类型
python backend/ontology/generate_models.py

# 5) 增量创建计划/成本表并写入种子数据
python backend/upgrade_planning.py

# 6) 后端计划冒烟
python backend/scripts/smoke_planning.py
python backend/scripts/smoke_planning_api.py

# 7) 重建演示数据并导出前端 mock 快照
python backend/scripts/refresh_planning_demo.py
```

> 运行 Python 脚本时需保证仓库根目录在 `PYTHONPATH` 中，或直接在根目录执行。

---

## 4. 当前运营模型（59 个实体 / 3 份 YAML）

| 模型文件 | 实体数 | 主要域 |
|---|---|---|
| `model/planning.yaml`（53） | 53 | 计划参数、需求预测/MPS、MRP 运算与追溯、采购闭环、齐套、成本与业财闭环（总账/期间）、库存估值、仓储、排程、质量、设备、销售/资金应收应付 |
| `model/admin.yaml`（5） | 5 | 部门、菜单、角色菜单授权、系统参数、登录日志 |
| `model/dashboard.yaml`（1） | 1 | 驾驶舱预警规则 `DashboardRule` |

其中业财闭环新增实体：`Account`、`JournalEntry`、`JournalLine`、`FiscalPeriod`、`InventoryValuation`、`ValuationMove`（均已在 `erp-ontology.ttl` / `shapes.ttl` 中声明，S51-S52）。

枚举共 69 个，唯一事实源为 `src/mappings.json`；每个实体字段引用的枚举都必须有定义，关键枚举须在 `validate-type-sync.js` 的 `KEY_ENUMS` 中与 SHACL `sh:in` 对齐。

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
