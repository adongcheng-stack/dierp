# DIERP 升级方案：模型-本体驱动的计划与控制系统（P0 计划闭环）

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.4 |
| 适用范围 | 现有 DIERP 制造 ERP MVP 之上的第一阶段升级 |
| 核心目标 | 在既有执行层数据之上长出“计划引擎”，把业务记录系统升级为计划与控制系统 |
| 实施方式 | 模型-本体驱动：枚举、实体、约束、规则统一收口，再生成后端模型与前端类型 |
| 本阶段范围 | P0：MPS / MRP / 计划订单 / 需求追溯 / 异常 / 齐套 / 计划参数；P1：成本引擎 / APS 有限产能排程 / 轻量 EAM 与 OEE / 轻量 QMS（均已完成）；P2：双向追溯（已完成）、经营看板 |
| 暂不包含 | QMS 高级特性（SPC / 8D / 供应商质量评分）、SRM/WMS、财务总账、工业级排程优化器 |
| 参考文档 | `docs/new/00.DIERP MVP 现状与能力缺口分析.md`、`02/03/04.DIERP 下一阶段实施计划.md` |

---

## 1. 升级判断

现有 MVP 已覆盖销售报价、BOM、工艺路线、生产订单、LOT 卡、工序报工、领料等执行层骨架，但生产订单主要依赖人工建立，系统还不能自动回答：

- 需要生产什么、生产多少？
- 什么时候开始生产/采购？
- 库存、在途、在制能否满足？
- 缺什么料、缺多少、最早何时齐套？
- 哪些计划订单需要确认、下达或调整？
- 每个计划订单的来源与扣减依据是什么？

因此第一阶段不铺 APS、成本、QMS，而是聚焦一条可演示、可验收的主线：

> 销售订单/预测 → MPS → MRP 净需求 → 计划生产/采购订单 → 确认下达 → 齐套/缺料 → 异常闭环

---

## 2. 模型-本体驱动架构

### 2.1 分层

```text
业务概念 / 枚举 / 约束 / 规则
        │
        ▼
ontology/src/mappings.json        枚举唯一事实源
ontology/src/erp-ontology.ttl     OWL 类与属性
ontology/src/shapes.ttl           SHACL 约束
ontology/src/rules.swrl           派生规则
ontology/model/planning.yaml      计划域 operational model
        │
        ├── python backend/ontology/generate_models.py
        │       ├── backend/common/models/planning.py        SQLAlchemy 模型
        │       └── frontend/src/types/planning.generated.ts  TS 接口/枚举
        │
        ├── ontology/generated/types.ts
        └── 双栈校验：Node + Python
        │
        ▼
服务层：MPS / MRP / 齐套 / 单号
        │
        ▼
API 层：/api/planning/*
        │
        ▼
前端页面 + mock 演示适配器
```

### 2.2 单一事实源

- **枚举**只改 `ontology/src/mappings.json`；
- **计划域实体/字段**只改 `ontology/model/planning.yaml`；
- **语义约束**在 `ontology/src/shapes.ttl`；
- 生成物 `backend/common/models/planning.py`、`frontend/src/types/planning.generated.ts` 不手工编辑；
- 运行时枚举校验由 `backend/ontology/registry.py` 承担。

这一步解决的是“模型漂移”问题：后端字段、前端类型、接口枚举、文档术语不再各写一份。

---

## 3. 计划域模型

### 3.1 新增实体（18 个）

| 分类 | 实体 | 作用 |
|---|---|---|
| 参数 | `PlanningPolicy` | 物料计划类型、采购类型、批量规则、提前期、安全库存、MOQ、倍数、计划员 |
| 需求 | `Forecast`、`MpsPlan`、`MpsEntry` | 预测、主生产计划头、按周 bucket 的 MPS 行 |
| 运算 | `MrpRun`、`MrpRequirement`、`PlannedOrder`、`PeggingLink`、`MrpException` | 运行批次、需求行、计划订单、需求-供应追溯、异常 |
| 齐套 | `KittingResult` | 工单/计划订单齐套结论与缺料明细 |
| 采购闭环 | `PurchaseOrder`、`PurchaseOrderLine` | 采购类计划订单下达后的采购单 |
| 预留 | `WorkCalendar`、`CostRate`、`StandardCost`、`ProductionCost`、`CostVariance`、`CostSettlement` | 工作日历与下一阶段成本引擎 |

### 3.2 关键枚举

- `ProcurementType`: `MAKE / BUY / SUB`
- `MrpType`: `MRP / REORDER_POINT / NONE`
- `MpsPlanStatus`: `DRAFT / RELEASED / CLOSED / CANCELLED`
- `PlannedOrderType`: `PRODUCTION / PURCHASE / TRANSFER`
- `PlannedOrderStatus`: `PLANNED / FIRMED / RELEASED / CANCELLED`
- `LotSizingRule`: `LOT_FOR_LOT / FIXED_LOT / MIN_MAX / EOQ / PERIOD_ORDER`
- `MrpExceptionType`: `SHORTAGE / EXCESS / LATE / EARLY / NO_BOM / NO_POLICY / LEAD_TIME_VIOLATION / CAPACITY_OVERLOAD`
- `KitStatus`: `FULL / PARTIAL / SHORT`

### 3.3 计划订单状态机

```text
建议 PLANNED ──确认──▶ 已确认 FIRMED ──下达──▶ 已下达 RELEASED
      │                    │
      └──────取消──────────┴──▶ 已取消 CANCELLED
```

规则：

1. 只有 `PLANNED` 可确认；
2. `PLANNED/FIRMED` 可下达；
3. 生产类下达生成正式生产订单，采购类生成采购订单与行；
4. 已下达保留来源追溯，不直接删除；
5. 重跑 MRP 不覆盖已确认/已下达计划订单。

---

## 4. 计划引擎

### 4.1 可用量口径

```text
可用量 = 现有库存
       − 已分配/预留
       + 在途采购（按预计到货日）
       + 在制工单（按预计完工日）
       − 安全库存
```

MRP 按需求日期滚动计算，不使用单一静态可用量；齐套分析与 MRP 使用同一口径。

### 4.2 MPS

输入：销售订单、预测、安全库存、计划区间。

处理：

1. 过滤有效销售订单与预测；
2. 按物料 + 周 bucket 汇总；
3. 按物料滚动期初库存、毛需求、预计可用；
4. `净需求 = max(0, 安全库存 + 毛需求 − 期初库存)`；
5. 生成 MPS 行与计划接收量；
6. 人工确认后下达，作为 MRP 独立需求。

### 4.3 MRP

```text
1. 收集独立需求：MPS 净需求 / 销售订单 / 预测 / 安全库存；
2. 按需求日期排序；
3. 按低层码从低到高展开 BOM；
4. 对每个物料滚动计算：净需求 = 毛需求 − 可用量；
5. 净需求 > 0 时按批量规则调整建议量；
6. 按提前期倒推计划开始日期；
7. 生成计划生产订单或计划采购订单；
8. 计划生产订单作为下层物料毛需求继续展开；
9. 输出需求行、计划订单、Pegging、异常与运行日志。
```

批量规则已支持：逐批、固定批量、最小/最大、经济批量、周期汇总；并叠加 MOQ、订单倍数、最大批量约束。

每个计划订单可回答：

- 来源哪张销售订单/预测/MPS 行；
- BOM 第几层；
- 扣减了哪些库存；
- 为什么是这个数量与开始日期；
- 使用了什么批量规则与提前期。

### 4.4 齐套分析

- 按生产订单或计划订单展开有效 BOM；
- 组件需求量 = 成品数量 × BOM 用量 ÷ BOM 基础数量；
- 按当前库存计算可用量；
- 输出齐套状态、缺口物料、缺口数量、需求日期与备注；
- 历史工单没有对应 BOM 版本时，回退使用当前有效 BOM，避免演示数据出现噪声。

### 4.5 异常

- `SHORTAGE` 物料短缺；
- `NO_BOM` 自制物料缺少已发布 BOM；
- `NO_POLICY` 缺少计划参数；
- 预留 `LATE / EARLY / EXCESS / LEAD_TIME_VIOLATION / CAPACITY_OVERLOAD`；
- 异常支持严重级别、处理状态、处理人、处理时间与备注。

---

## 5. 后端服务与 API

### 5.1 服务层

```
backend/services/planning/
├── common.py           日期、批量、BOM、低层码、Decimal 工具
├── mps_engine.py       MPS 生成/下达
├── mrp_engine.py       多级 MRP、净需求、计划订单、Pegging、异常
├── kitting_service.py  工单/计划订单齐套分析
└── __init__.py
```

辅助：

- `backend/ontology/registry.py`：枚举运行时校验；
- `backend/common/utils/number_generator.py`：通用单号生成。

### 5.2 API 一览

前缀：`/api/planning`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | 计划工作台概览 |
| POST | `/mps/generate` | 生成 MPS |
| GET | `/mps` | MPS 列表 |
| GET | `/mps/{mps_number}` | MPS 明细 |
| POST | `/mps/{mps_number}/release` | 下达 MPS |
| POST | `/mps/{mps_number}/close` | 关闭 MPS |
| POST | `/mrp/run` | 运行 MRP |
| GET | `/mrp/runs` | MRP 运行列表 |
| GET | `/mrp/runs/{run_number}` | 运行明细（需求行/计划订单/异常） |
| GET | `/mrp/runs/{run_number}/pegging` | 需求-供应追溯 |
| GET | `/planned-orders` | 计划订单列表 |
| GET | `/planned-orders/{number}` | 计划订单详情 + Pegging |
| POST | `/planned-orders/{number}/confirm` | 确认 |
| POST | `/planned-orders/{number}/release` | 下达并生成工单/采购单 |
| GET | `/exceptions` | 异常列表 |
| POST | `/exceptions/{id}/resolve` | 处理异常 |
| GET | `/kitting` | 齐套结果列表 |
| GET | `/kitting/{result_number}` | 齐套详情 |
| GET | `/kitting/by-source/{type}/{ref}` | 按来源查齐套 |
| POST | `/kitting/production-orders/{order_number}` | 重算工单齐套 |
| POST | `/kitting/planned-orders/{number}` | 重算计划订单齐套 |
| GET/POST | `/policies` | 计划参数列表/新建 |
| PUT/DELETE | `/policies/{policy_id}` | 计划参数更新/删除 |

---

## 6. 前端页面

生产计划菜单下新增 7 个页面：

| 路由 | 页面 | 主要能力 |
|---|---|---|
| `/pp/planning` | 计划工作台 | 计划闭环状态、最近 MRP 统计、异常/缺料入口 |
| `/pp/mps` | 主生产计划 | 生成、列表、明细抽屉、下达 |
| `/pp/mrp` | MRP 运算 | 运行参数、运行记录、需求/计划订单/异常三页签 |
| `/pp/planned-orders` | 计划订单 | 批次/类型/状态筛选、确认、下达 |
| `/pp/planning-exceptions` | 计划异常 | 级别/类型/处理状态筛选、处理闭环 |
| `/pp/kitting` | 齐套分析 | 齐套统计、短缺明细展开、重算 |
| `/pp/planning-policies` | 计划参数 | 列表、筛选、新建/编辑/删除，RAW 物料默认采购 |

页面风格与现有 ERP 一致：Ant Design 表格 + `PageHeader` + 克制的统计卡片，不引入额外设计体系。信息架构对齐 `docs/new` 的验收要求：参数 → MPS → MRP → 计划订单 → 异常 → 齐套。

### 演示适配器

`frontend/src/mock/handlers.ts` 已实现全部 `/planning/*` mock 路由，包括：

- 轻量 MPS/MRP 运算；
- 计划订单确认/下达（生成 `PO-*` / `PUR-*`）；
- 异常处理；
- 齐套重算；
- 计划参数 CRUD。

`snapshot.json` 已包含计划演示数据并升级为 `version: 2`，用于清理浏览器旧 localStorage。

---

## 7. 演示数据与命令

当前演示快照（mock `snapshot.json` version 8）：

- MPS：`MPS-20261117-001`（36 行）
- MRP：`MRP-20261117-001`（23 需求行、11 计划订单、12 异常、31 条 Pegging）
- 齐套：4 单（均为部分缺料）
- 计划参数：10 条
- 预测：8 条
- BOM：4 套已发布成品 BOM
- 成本：12 费率 / 10 标准成本 / 3 工单成本 / 15 差异 / 1 结算
- APS：1 个已发布批次（12 道工序、14 条异常）+ 1 个插单场景
- EAM：6 维护计划 / 2 维护工单 / 1 故障记录，`RES-DRILL-B-01` 保养中
- QMS：3 检验单（IQC/IPQC/FQC）+ 2 不合格品记录（含 1 条设备原因联动 EAM 故障）

重建命令：

```bash
python backend/upgrade_planning.py            # 幂等主数据种子（含报工工艺关联 + QMS 演示数据）
python backend/scripts/refresh_planning_demo.py  # MPS/MRP/齐套
python backend/scripts/reset_demo.py          # 一键重置 APS/EAM/QMS 运行时数据并重建演示场景
```

验证命令：

```bash
python backend/scripts/smoke_planning.py
python backend/scripts/smoke_planning_api.py
python backend/scripts/smoke_cost.py
python backend/scripts/smoke_aps.py && python backend/scripts/smoke_aps_api.py
python backend/scripts/smoke_eam.py && python backend/scripts/smoke_eam_api.py
python backend/scripts/smoke_qms.py
python backend/scripts/smoke_demo_reset.py
cd ontology && npm run check:node && python scripts/validate-consistency.py
cd frontend && npm run build && npm run build:mock
```

演示入口：

- 开发：`cd frontend && npm run dev:mock`
- 静态演示：`frontend/dist-demo`，可直接打开 `index.html` 或部署静态站点
- 默认账号：`admin / admin123`

---

## 8. 验收对照

| 验收项 | 状态 |
|---|---|
| 计划参数可维护并影响 MRP | 已完成 |
| 基于销售订单/预测生成 MPS | 已完成 |
| BOM 多层展开与净需求 | 已完成 |
| 生成计划生产/采购订单 | 已完成 |
| 计划订单来源追溯与 Pegging | 已完成 |
| 计划订单确认/下达/转单 | 已完成 |
| 工单/计划订单齐套与缺料 | 已完成 |
| MRP 异常分类与处理 | 已完成 |
| mock/真实接口切换 | 前端通过 axios adapter，保留切换点 |
| 演示数据覆盖缺料场景 | 已完成（4 单部分缺料） |
| P1 成本引擎（标准/实际/差异/结算） | 已完成 |
| P1 APS 排程（甘特/异常/插单/发布） | 已完成 |
| P1 轻量 EAM（计划/工单/故障/OEE） | 已完成 |
| EAM 语义层（3 类 / 3 Shape / 19 属性） | 已完成，SHACL 全量 conform |
| P1 轻量 QMS（来料/过程/终检 + NCR 闭环） | 已完成 |
| QMS 语义层（2 类 / 2 Shape / 22 属性） | 已完成，SHACL 全量 conform |
| QMS 双向联动（报工→NCR、NCR→EAM 故障） | 已完成，`smoke_qms.py` 全链路验证 |
| P2 双向追溯（批次/物料/订单 正向+反向全链路） | 已完成，`smoke_traceability.py` + `smoke_traceability_api.py` 验证 |
| P2 经营看板（六域 KPI + 自动点评） | 已完成，`smoke_dashboard.py` 验证 |
| N1 工程化加固（git/pytest/parity 校验） | 已完成，`backend/tests` 25 用例 + `check_demo_parity.py` 19 项事实 |
| N2 权限收紧（RBAC 域写权限门 + CORS 白名单） | 已完成，`test_permissions.py` 6 用例 |
| N3 采购闭环（采购单页面/收货/库存回冲） | 已完成，`smoke_purchase.py` 全链路验证 |
| 演示数据一键重置（菜单 + CLI + API） | 已完成，支持幂等与管理员校验 |
| 前端分包与首屏优化 | 已完成，全部 chunk < 500KB，无构建告警 |

---

## 9. 下一阶段

| 阶段 | 内容 | 前置 |
|---|---|---|
| P1 | APS 有限产能排程：日历/班次、设备、技能、换产、甘特图、插单模拟（已完成） | 计划订单闭环稳定 |
| P1 | 轻量 QMS：IQC/IPQC/FQC、不合格品闭环（已完成） | 工单/批次数据完整 |
| P1 | 轻量 EAM：设备台账、点检、故障、OEE（已完成） | APS 需要设备/停机数据 |
| P1 | 制造成本核算：标准成本、实际归集、差异分析（已完成） | 领料/报工/费率可用 |
| P2 | 双向追溯（已完成，见 §P2 双向追溯） | 订单/批次/报工数据完整 |
| P2 | SRM/WMS、业财一体、经营看板 | 主数据与执行数据质量达标 |

### P1 成本引擎（已完成）

成本域在计划域模型里已预留 `CostRate / StandardCost / ProductionCost / CostVariance / CostSettlement` 五个实体，本轮直接落地：

| 层 | 实体 | 职责 |
|---|---|---|
| 费率 | `CostRate` | 工作中心的人工/设备/制造费用费率（元/小时） |
| 标准 | `StandardCost` | 按 BOM 用量 × 物料单价 + 工艺费率，多层滚动物料标准成本 |
| 实际 | `ProductionCost` | 按工单归集实际领料 + 报工工时 × 费率 |
| 差异 | `CostVariance` | 材料价格/用量、人工费率/效率、制造费用五类差异 |
| 结算 | `CostSettlement` | 对完工工单结算，固化实际成本 |

服务实现：`backend/services/planning/cost_engine.py`（`CostEngine`），提供：
- `rollup_standard_cost` / `rollup_many`：标准成本滚动
- `collect_production_cost`：工单实际成本归集
- `analyze_variances`：差异分析
- `settle`：工单结算
- `upsert_rate`：费率维护

API 一览（前缀 `/api/planning/cost`）：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | 成本工作台概览 |
| GET/PUT | `/rates`、`/rates/{rate_id}` | 成本费率 |
| POST/GET | `/standard/rollup`、`/standard`、`/standard/{material}` | 标准成本滚动与查询 |
| POST/GET | `/production/collect`、`/production`、`/production/{order}` | 工单实际成本 |
| POST/GET | `/variances/analyze`、`/variances` | 差异分析 |
| POST/GET | `/settlement/settle`、`/settlements` | 成本结算 |

前端页面（`frontend/src/pages/cost/`）：成本工作台、标准成本、工单成本、差异分析、成本结算、成本费率。演示快照已注入 12 条费率、10 个标准成本、3 单工单成本、15 条差异与 1 张结算。

验证命令：`python backend/scripts/smoke_cost.py`、`python backend/scripts/smoke_cost_api.py`（可选）。

### P1 高级排程 APS（已完成）

APS 在计划订单闭环之上把「什么时候做」落到工序级：以工作中心有限产能日历为约束，把已下达工单/自制计划订单展开为带开始/结束时间的排程工序，并产出可解释的排程异常。

**实体清单（8 个，均由 `ontology/model/planning.yaml` 生成）**：

| 分类 | 实体 | 作用 |
|---|---|---|
| 主数据 | `Resource` | 设备/人力资源，绑定工作中心，带技能标签与状态（ACTIVE/MAINTENANCE/DOWN） |
| 主数据 | `SkillMatrix` | 人员技能矩阵（技能码 + 熟练度） |
| 主数据 | `ChangeoverMatrix` | 同工作中心相邻工序的换产时间矩阵 |
| 排程 | `ScheduleRun` | 排程运算批次（算法、窗口、状态、工序/异常计数） |
| 排程 | `ScheduledOperation` | 排程工序（工单 × 工序 × 工作中心 × 起止时间） |
| 异常 | `ScheduleException` | 六类排程异常记录（类型、级别、建议动作） |
| 模拟 | `ScenarioSimulation` | 插单/设备停机/物料延迟模拟场景 |
| 模拟 | `ScenarioImpact` | 模拟影响明细（原/新完工时间、延期天数、影响级别） |

**引擎职责**（`backend/services/planning/aps_engine.py` · `ApsEngine`）：

- `run`：正排/倒排/混合（`FORWARD / BACKWARD / MIXED`），来源支持 `PRODUCTION_ORDER`（已下达/生产中工单）与 `PLANNED_ORDER`（自制计划订单）；按工作中心粒度做有界排程（非工业级优化器）。
- `WorkCenterCalendar`：有限产能日历，从 `WorkCalendar` 派生班次窗口、休息、利用率、工作日，按机器数维护占用区间，`find_slot` 处理换班与周末。
- 约束建模：产能（班次 × 利用率 × 机器数）、工序时间（调机 + 机加 + 人工）、工序顺序、技能矩阵、换产时间、齐套状态。
- `publish`：批次发布，工序状态置为 PUBLISHED，作为生产执行依据。
- `simulate`：插单（INSERT_ORDER）/设备停机（EQUIPMENT_DOWN）/物料延迟（MATERIAL_DELAY）三类扰动，输出影响明细而不污染已发布排程。

**六类排程异常与触发规则**：

| 类型 | 触发规则 | 默认级别 |
|---|---|---|
| `CAPACITY_OVERLOAD` | 日历窗口内找不到可用产能槽位；或工单缺少已发布工艺路线 | WARNING |
| `DUE_DATE_RISK` | 工单最后一道工序排程结束时间超过计划完工日期 | WARNING |
| `MATERIAL_SHORTAGE` | 齐套结果为 SHORT（严重，不宜下达）/ PARTIAL（警告，存在风险） | CRITICAL/WARNING |
| `SKILL_MISMATCH` | 工序编码前缀（DRL/ETC/MIL/TST）在工作中心找不到具备该技能码的可用资源 | WARNING |
| `CHANGEOVER_LIMIT` | 同工作中心相邻两道工序的换产时间超过 30 分钟阈值 | WARNING |
| `RESOURCE_DOWN` | 工作中心存在 status ≠ ACTIVE 的资源（保养/停机）；全部机器停机时工序顺延 | WARNING/CRITICAL |

**API 一览（前缀 `/api/planning/aps`，14 条路由）**：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | APS 工作台概览 |
| POST | `/run` | 运行排程（算法/来源/窗口） |
| GET | `/runs` | 排程批次列表 |
| GET | `/runs/{run_number}` | 批次明细（含工序与异常） |
| GET | `/runs/{run_number}/gantt` | 甘特图数据（按工作中心分组） |
| POST | `/runs/{run_number}/publish` | 发布批次 |
| GET | `/exceptions` | 排程异常列表（批次/类型/级别筛选） |
| POST | `/simulate` | 插单/扰动模拟 |
| GET | `/scenarios` | 模拟场景列表 |
| GET | `/scenarios/{scenario_id}` | 场景明细（含影响明细） |
| GET | `/resources` | 资源列表 |
| GET | `/skills` | 技能矩阵列表 |
| GET | `/changeovers` | 换产矩阵列表 |
| GET | `/calendars` | 工作中心日历列表 |

**前端页面（`frontend/src/pages/aps/`，5 个）**：APS 工作台（统计卡 + 产能甘特图 + 运行/发布/模拟入口）、排程批次（明细抽屉 + 发布）、插单模拟、排程异常、排程主数据（资源/技能/换产/日历）。路由挂在 `/aps/*`，菜单独立「高级排程」分组。

**演示数据**（`backend/upgrade_planning.py` 幂等种子）：6 资源（RES-DRILL-A-01/02、RES-DRILL-B-01、RES-DRILL-C-01、RES-DRILL-D-01、RES-OPR-001）、4 技能、4 条换产矩阵、4 个工作中心日历；演示工单 PO-APS-01~04（其中 PO-APS-04 交期仅 1 天 → 必现交期风险异常），PO-APS-01/04 预置部分缺料齐套快照 → 缺料异常；前端演示快照由 `frontend/scripts/seed_aps_schedule.cjs` 用同构轻量算法预置排程结果。

验证命令：`python backend/scripts/smoke_aps.py`（引擎直调）、`python backend/scripts/smoke_aps_api.py`（API 全链路）。

### P1 轻量 EAM 与 OEE（已完成）

EAM 补上「设备」这一层事实：APS 的资源停机、成本的效率差异、OEE 的可用/性能/良品都从这里取数。

**实体清单（3 个，由 `ontology/model/planning.yaml` 生成）**：

| 实体 | 语义类型（OWL） | SHACL Shape | 作用 |
|---|---|---|---|
| `MaintenancePlan` | `NormativeRule` | `MaintenancePlanShape` (S32) | 周期维护计划：周期天数、下次到期、状态、责任工作中心 |
| `MaintenanceOrder` | `Document` | `MaintenanceOrderShape` (S33) | 维护工单：来源计划、计划/完成时间、执行人、停机时长 |
| `EquipmentFailure` | `EventRecord` | `EquipmentFailureShape` (S34) | 故障记录：设备、严重度、停机起止、根因、纠正措施、闭环状态 |

语义层同步补齐：3 个 `owl:Class`、3 个 NodeShape、19 个数据属性声明；`ScheduledOperationShape` 补上遗漏的 `:status`，`validate-type-sync.js` 的 `KEY_ENUMS` 支持按 Shape 作用域匹配，解决 `severity` 同名枚举（`ExceptionSeverity` / `FailureSeverity`）冲突。EAM 落地后本体规模为 29 实体 / 32 枚举 / 34 NodeShape，SHACL 全量 conform。

**引擎职责**（`backend/services/planning/eam_engine.py` · `EamEngine`）：

- `generate_due_orders`：扫描 `next_due_at <= as_of` 的计划，幂等生成维护工单，并把计划下次到期顺延一个周期；
- `complete_order`：完工登记，写实际工时与停机；
- `report_failure` / `resolve_failure`：故障上报与闭环，记录停机区间供 OEE 使用；
- `oee_snapshot`：按工作中心输出可用率 / 性能率 / 良品率 / OEE 与停机资源。

**OEE 口径（后端与 mock 完全一致）**：

| 指标 | 公式 |
|---|---|
| 可用率 A | `1 - 故障停机分钟 / 班次时长`，班次时长取工作中心日历或默认班次 |
| 性能率 P | `标准工时 / 实际工时`；标准工时 = 路由工序 `(setup + machine + labor) × min(报工数/工单数, 1)`，实际工时 = 报工 `machine_time + labor_time`；缺数据按 1 |
| 良品率 Q | `good_quantity / reported_quantity`，无报工按 1 |
| OEE | `A × P × Q`（演示值：全厂 ≈ 0.65，DRILL-B ≈ 0.31 —— 停机 2.5h + 实际工时高于标准工时） |

> 本轮同时修正了报工数据底座：`seed_operation_report_routing` 为演示报工补齐 `routing_operation_id` 与工时，否则性能率会恒为 1，OEE 失去解释力。

**API 一览（前缀 `/api/planning/eam`，11 条路由）**：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | EAM 工作台概览（计划/到期/工单/故障） |
| GET/POST | `/plans` | 维护计划列表 / 新建 |
| PUT | `/plans/{plan_id}` | 维护计划更新 |
| GET | `/orders` | 维护工单列表 |
| POST | `/orders/{order_number}/complete` | 维护工单完工 |
| GET/POST | `/failures` | 故障列表 / 上报 |
| POST | `/failures/{failure_number}/resolve` | 故障闭环 |
| GET | `/oee` | OEE 快照（可按工作中心过滤） |
| POST | `/generate-due-orders` | 到期计划批量生成保养单 |

**前端页面（`frontend/src/pages/eam/`，4 个）**：设备工作台（统计卡 + OEE 表 + 到期计划 + 未关闭故障）、维护计划、维护工单、设备故障。路由挂在 `/eam/*`，菜单独立「设备管理」分组。

**演示数据**：6 条维护计划、2 张维护工单、1 条故障记录；`RES-DRILL-B-01` 置为 `MAINTENANCE`，同时驱动 APS「资源停机」异常与 OEE 可用率下降。mock 快照 version 升至 **6**，报工补齐工艺关联与工时，前端 OEE 性能率可展示真实差异（DRILL-B ≈ 42%）。

**演示数据一键重置**（演示多轮后恢复初始态）：

| 入口 | 命令 / 操作 | 说明 |
|---|---|---|
| 前端菜单 | 右上角头像 →「清理演示数据」 | 仅管理员；调用 `POST /api/planning/demo/reset`，成功后自动刷新 |
| 命令行 | `python backend/scripts/reset_demo.py` | 支持 `--keep-run` / `--no-scenario` / `--json` |
| 服务层 | `backend/services/planning/demo_reset.py` | `reset_planning_demo()`，可被脚本或其他服务复用 |

清空范围：排程批次/工序/异常、插单场景/影响、维护计划/工单、故障记录；**不动**客户、订单、BOM、工艺路线、生产订单、物料、成本费率等主数据。重置后自动重建：EAM 种子 + 报工工艺关联 + 一个已发布排程批次 + 一个插单模拟场景，可重复执行。

验证命令：`python backend/scripts/smoke_eam.py`（引擎直调）、`python backend/scripts/smoke_eam_api.py`（API 全链路）、`python backend/scripts/smoke_demo_reset.py`（重置 API + 幂等 + 权限）。

### P1 轻量 QMS 质量管理（已完成）

QMS 把「质量」从终检记录升级为贯穿 **来料 → 过程 → 终检** 的闭环，并把不合格品与报工报废、设备故障连成一条链。

**实体清单（2 个，由 `ontology/model/planning.yaml` 生成）**：

| 实体 | 语义类型（OWL） | SHACL Shape | 作用 |
|---|---|---|---|
| `InspectionOrder` | `Document` | `InspectionOrderShape` (S35) | 统一检验单：`inspection_type` 区分来料/过程/终检，记录检验数、合格/不合格数与 PASS/FAIL/HOLD 结论 |
| `NonConformanceReport` | `EventRecord` | `NonConformanceReportShape` (S36) | 不合格品闭环：开立 → 评审 → 处置 → 关闭，记录缺陷、根因、处置方式与设备联动结果 |

语义层同步补齐 2 个 `owl:Class`、2 个 NodeShape、22 个数据属性；`KEY_ENUMS` 增加 7 个 QMS 枚举的作用域绑定（`InspectionType` / `InspectionResult` / `InspectionStatus` / `NcrSourceType` / `NcrSeverity` / `NcrDisposition` / `NcrStatus`），其中 `:status` 与 `:severity` 通过 Shape 作用域与既有枚举共存。QMS 落地后本体规模：**31 实体 / 39 枚举 / 36 NodeShape**，SHACL 全量 conform。

**引擎职责**（`backend/services/planning/qms_engine.py` · `QmsEngine`）：

- `create_inspection` / `complete_inspection`：建单与完成检验；结论 FAIL 且允许时自动开立 NCR；
- `create_ncr`：来源为报工单（`source_type=REPORT`）时，自动按生产订单解析物料、带出批次与报废数量；
- `review_ncr` / `disposition_ncr`：评审、处置；判定 `equipment_cause=True` 时自动调用 `EamEngine.record_failure` 并把故障号回写 `failure_number`；
- `close_ncr`：必须已有处置方式才能关闭，形成不可跳步的闭环；
- `overview`：检验单/不合格品的统计口径（打开、已关闭、严重、设备原因）。

**API 一览（前缀 `/api/qms`）**：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/overview` | 质量工作台概览 |
| GET/POST | `/inspections` | 检验单列表 / 新建 |
| POST | `/inspections/{inspection_number}/complete` | 完成检验（自动判结论、可选自动开 NCR） |
| GET/POST | `/ncrs` | 不合格品列表 / 开立 |
| POST | `/ncrs/{ncr_number}/review` | 评审（可触发 EAM 故障联动） |
| POST | `/ncrs/{ncr_number}/disposition` | 处置 |
| POST | `/ncrs/{ncr_number}/close` | 关闭 |
| GET | `/operation-reports/scrap` | 报废>0 的报工单（下拉来源，带物料/批次） |

**前端页面（`frontend/src/pages/qms/`）**：质量工作台、检验单、不合格品记录；菜单独立「质量管理」分组，路由 `/qms/*`。列表页内置新建/完成/评审/处置/关闭弹窗，无需额外表单页。

**演示数据**：3 张检验单（IQC PASS / IPQC FAIL / FQC PASS）、2 条 NCR（1 条过程检验产生并完成返工闭环、1 条设备原因 UNDER_REVIEW 并联动 EAM 故障）；mock 快照 version 升至 **8**。`reset_demo.py` 会一并清理检验单/NCR 与 QMS 专用报废报工单，再幂等重建。

验证命令：`python backend/scripts/smoke_qms.py`（检验→NCR→EAM 联动→处置关闭全链路）。

### P2 双向追溯（已完成）

追溯把散落在销售/生产/质量/设备里的记录串成**一条可解释的链**：任何一个批次、物料或订单都能回答「它从哪来、到哪去、中间发生过什么」。

**架构决策（ADR-20261118-01）**：追溯实现为**只读派生查询引擎**，不新增实体、不写库——追溯图完全由既有单据链接推导，为「查询」发明实体反而违反单一事实源原则。原料批次级追溯（需给 `MaterialIssue` 增列并做 DDL 迁移）列为后续项，须人工在场执行。

| 能力 | 端点 | 链路 |
|---|---|---|
| 正向（批次） | `GET /api/traceability/lots/{lot}` | LOT → 工单 → 销售订单 → 客户；+ 领料 / 报工（良品+报废）/ 检验 / NCR / EAM 故障 |
| 反向（物料） | `GET /api/traceability/materials/{code}` | 物料 → 领料 → 工单 → 批次 → 销售 → 客户；+ 检验 / NCR / 故障 / 采购行→供应商 |
| 订单（自动识别） | `GET /api/traceability/orders/{no}` | 生产订单直接展开；销售订单 → 1..N 工单 → 客户 |
| 根搜索 | `GET /api/traceability/search?q=` | 批次 / 工单 / 销售订单 / 物料 / NCR（NCR 命中可跳转到其批次/物料） |
| 概览 | `GET /api/traceability/overview` | 可追溯对象计数 |

实现：`backend/services/planning/traceability_engine.py`（`TraceEngine`，单层 ≤50 节点防噪）；前端 `frontend/src/pages/traceability/TraceabilityExplorer.tsx`（搜索 + 演示入口 + 链路 Timeline + 节点明细 + Tree 关系图），菜单入口在「生产执行 → 批次追溯」。mock 侧在 `handlers.ts` 同构实现，快照 version 9（补齐 PO-APS-01..04 的销售订单关联）。

验证：`python backend/scripts/smoke_traceability.py`（引擎 7 组断言）与 `python backend/scripts/smoke_traceability_api.py`（TestClient 6 组断言，含 404）。

### P2 经营看板 MVP（已完成）

经营看板把六大域 KPI 收进一屏，全部由既有单据**实时推导**（与追溯同类的只读派生查询，不落库）：

| 域 | KPI | 口径 |
|---|---|---|
| 销售 | 订单额 / 未交订单 | `total_amount` 汇总；状态在 APPROVED/IN_PRODUCTION 等视为未交 |
| 生产 | 完成率 / 状态分布 / 逾期在制 | 已完工+关闭 ÷ 全部；`planned_finish_date < 今日` 且未完结 |
| 质量 | 一次合格率 / OPEN NCR | 1 − Σ不合格 ÷ Σ检验数（已完成检验）；OPEN/UNDER_REVIEW 计未关闭 |
| 设备 | 综合 OEE / 停机 / 分中心 | 复用 `EamEngine.oee_snapshot` 同一口径 |
| 成本 | 差异合计 / 五类构成 | `CostVariance.variance_amount` 按 `variance_type` 汇总 |
| 交期 | 逾期销售/工单 / 到期保养 | 承诺交期与计划完工日已过且未完结；保养 `next_due_at` 到期 |

页面 `frontend/src/pages/dashboard/ManagementDashboard.tsx`（`/dashboard/management`，菜单「生产执行 → 经营看板」）含 KPI 卡、分中心 OEE 条、状态分布、差异构成与**自动经营点评**（规则生成演示话术，如「DRILL-B OEE 31%，建议优先排维」）。mock 侧 `GET /dashboard/management` 与引擎同构，OEE 直接复用 mock 的 `eamOeeSnapshot`。

验证：`python backend/scripts/smoke_dashboard.py`（引擎 KPI 断言 + 自动点评 + TestClient API 一致性）。注意：真实后端需重启以加载新路由 `/api/dashboard/*`、`/api/traceability/*`。

### N1-N3 工程化加固 / 权限收紧 / 采购闭环（已完成）

| 项 | 内容 |
|---|---|
| N1 版本控制 | `git init` + 全量基线提交；此后每个夜间任务独立提交，可回滚 |
| N1 单元测试 | `backend/tests/`（SQLite 内存库夹具，模型无方言依赖）：编号生成 6 例、QMS 闭环 4 例（含报工→NCR 物料解析、设备联动幂等）、看板点评规则 4 例、追溯图容器 3 例、RBAC 6 例 |
| N1 演示数据一致性 | `check_demo_parity.py`：mock 快照 ↔ 数据库种子 19 项关键事实对比（APS 工单销售关联、检验/NCR 事实、采购单、库存等），不一致即退出码 1 |
| N1 冒烟去日期化 | traceability 冒烟断言改为「静态单据精确 + 动态单据前缀」，消除跨午夜失效 |
| N2 RBAC | `auth.py` 新增 `WRITE_ROLE_POLICY` + `require_write_permission`（按域 × 写方法），`main.py` 单点挂载；GET 保持开放（冒烟契约）；CORS 收敛为 `ERP_CORS_ORIGINS` 白名单；前端 403 统一文案 |
| N3 采购闭环 | 新增 `api/routers/purchase.py`（列表/详情/收货/关闭），收货实时回冲 `Material.current_stock`，超量与状态机保护；`PurchaseOrderList.tsx` 页面（`/pp/purchase-orders`）；`seed_purchase_demo_data` 两张 RELEASED 演示单；`demo_reset` 清理采购表 + **物料库存基线复位**（领料/到货多轮演示可重复） |

权限矩阵（写操作）：sd=SALES/SALES_MANAGER/总经理，eng=ENGINEER，pp/mm/purchase=PRODUCTION/PLANNER/WAREHOUSE 系，planning/qms=PLANNER/总经理，users=仅 ADMIN；ADMIN 恒通过。多账号演示时注意：用非授权角色执行写操作会得到 403（演示话术可顺势讲权限设计）。

### 前端交付优化（已完成）

- 路由级 `React.lazy`：首页只加载布局与工作台，其余 50+ 页面按访问加载；
- `manualChunks` 按依赖层次分包：`react-vendor` / `vendor` / `rc`（含 cssinjs）/ `antd-icons` / `antd-table` / `antd`，全部 chunk < 500KB，构建无体积告警；
- 分包后补充 chunk 循环检测：72 个产物 chunk 无循环依赖，浏览器实测 0 console error。

---

## 10. 结论

本轮升级不是继续堆业务记录页面，而是用本体把“计划域”的概念、枚举、约束、字段先定义清楚，再由模型生成器落到后端与前端。这样做的直接收益：

1. **计划结果可解释**：来源、层级、扣减、批量、提前期都能追溯；
2. **模型不漂移**：枚举与实体只有一个上游；
3. **可演示**：演示库稳定覆盖 MPS → MRP → 计划订单 → 齐套/异常完整链路；
4. **可扩展**：APS、QMS、EAM、成本、业财都在同一本体与模型体系下继续生长。
