# DIERP AI 原生化 · 实施计划

- 文档版本：v1.1
- 日期：2026-11-24
- 配套设计：[01-系统设计-DIERP-AI原生化.md](01-系统设计-DIERP-AI原生化.md)（v1.1）
- 依据：[DIERP-AI-ERP提升方案-深度研究-20261124.md](../../../docs/DIERP-AI-ERP提升方案-深度研究-20261124.md)
- 计划口径：按"可独立验收的工作项"拆分，不按自然时间拆分；每项给出依赖、文件范围、验收口径与风险，可直接作为开发任务单。
- 历史版本：[v1.0](history/02-实施计划-DIERP-AI原生化-v1.0.md)

---

## 变更记录（v1.0 → v1.1）

按 [03-评审报告](03-评审报告-DIERP-AI原生化.md) 修订；设计同步升 v1.1。v1.0 原件保留在 `outputs/history/`。

| 评审项 | 处理 | 落点 |
|---|---|---|
| B1 | W0.2 文件清单改为 3 个本体源 + 3 份生成物；验收加 `generate-types --check`、`validate-consistency`、`validate-type-sync` | W0.2 |
| B2 | W0.4 增加 `entity_overrides` 与"形状路径未命中 = 0"；登记 6 个 YAML 实体的 `documentNumber` 映射；BOM 明确不进入目录 | W0.4 |
| B3 | W0.5 改为可执行实现（`conforms, results_graph, _`、datatype 映射、`advanced=False`、显式传参） | W0.5 |
| I1 | W0.6/W1.2 验收增加"独立 session 可查"与"403/422 也落审计" | W0.6、W1.2 |
| I2 | 全篇改"两层硬控制 + 覆盖式 SHACL + 溯源"；W0.4/W1.1 加 `shacl_coverage`；W2.4 补形状升级 | §0、W0.4、W1.1、W2.4 |
| I3 | W1.2 增加解析规则表/前置分类/默认状态；验证 13 条按新口径 | W1.2、W1.6 |
| I4 | W1.1 增加"取数口径"实现与 fixture 数值断言 | W1.1 |
| I5 | W1.2/W1.5 增加 LLM 出域与字段白名单验收 | W1.2、W1.5 |
| I6 | W1.2 增加 `AI_QUERY_TIMEOUT_SECONDS` 与方言分支验收 | W1.2 |
| I7 | 统一计数：7 意图 / 13 条 / 7 类 / 17 变量 / 10 测试文件 / 3 源 + 3 生成物 / 16 门禁 | 全文 |
| I8 | W0.4 增加 `EntityMeta.domain` 与域例外覆盖；W1.1 增加 `entities/primary_entity` | W0.4、W1.1 |
| I9 | W1.1 增加 `record_key/downlink`，W1.6 断言记录键 | W1.1、W1.6 |
| I10 | W1.1/W1.4 增加字段白名单与双角色差分验收 | W1.1、W1.4 |
| I11 | W0.3 修正检索验收（不再断言 `search("库存")→Material`） | W0.3 |
| I12 | W1.6 增加"最小演示数据集"（7 意图 × ≥3 条）并作为验收前置 | W1.6 |
| S1 | W0.3 SPARQL 改在剔除 JwtConfig 的 schema 图上执行；D6/D11 登记 demo.ttl 偏离 | W0.3、§1 |
| S2 | W0.5 `advanced=False`、`sh:sparql` 形状跳过 | W0.5 |
| S3 | 删除 `<300ms`/`<50ms` 等绝对耗时断言，改规模断言 | W0.4、W0.5 |
| S4 | W1.4 "mock 与后端一致"改为契约一致 + golden 快照 diff | W1.4 |
| S5 | W0.6/W1.2 增加 `AI_LOG_QUESTION` 与保留期常量验收 | W0.6、W1.2 |
| S6 | W0.1 改 `AI_ENABLED` / `AI_CHATBI_ENABLED` 双开关 | W0.1 |
| S7 | W0.1 `owlrl` 移 dev 依赖 | W0.1 |
| S8 | W0.2 增加路由探针行为测试，parity 只定位为防漂移 | W0.2 |
| S9 | W0.4/§6 覆盖率改为 `not_exposed: 25` + 清单 | W0.4、§6 |
| S10 | W0.1 增加 docker 镜像冒烟 | W0.1 |
| S11 | 全篇时间基准统一 `datetime.now()` | W1.1 |
| S12 | W1.6 数据集固定种子，验收不再硬编码示意单号 | W1.6 |
| 自检补正（v1.1 定稿前） | 对齐仓库：W1.1 应收余额口径改为 `SUM(receivable_entries.amount)`（`ReceivableEntryType` 实为 5 个值）；下钻路由以设计 §7.2 的真实路由为准 | W1.1 |

**统一口径**：7 个意图 · 13 条验收 · 7 类业务问题 · 17 个环境变量 · 10 个测试文件 · 10 条路由 · `ai` 域 = 3 个本体源 + 3 份生成物 · 聚合门禁 15 → 16 项。

---

## 0. 总览

| 阶段 | 目标 | 对应文档条目 | 出口标准 |
|---|---|---|---|
| **P0 语义底座** | 本体可被服务化检索；AI 安全域与审计表落地；门禁覆盖 | A1、D2（域级）、D3（表） | `GET /api/ai/ontology/*` 可用；`ai` 域双栈一致；`ai_query_logs` 迁移通过；新增门禁绿 |
| **P1 受控 ChatBI** | 7 个意图 + 分层控制 + 前端页面 + 异常解读 + 验收基准 | A2、A4、D2（意图级）、D3（链路）、C1 | 13 条验收问题全部按预期通过；越权/注入/超范围全部被拒；mock 与后端契约一致 |
| **P2 生态与工作流** | MCP 只读工具、工作流 AI 旁路、ERP-MES 语义映射、本体扩面 | A3、L2、B1 | MCP 工具清单 = 只读意图清单；工作流建议不直接改状态；映射项全部锚定既有本体类 |
| **P3 深化** | 成本闭环归因、排程解释、多租户接入点 | B2、C2、D4 | 仅完成接口与数据模型预留，功能可关停 |

**全局约束（每个工作项都必须满足）**
- 不新增任何 AI 写操作；不修改既有表结构与既有 API 契约。
- 不引入前端新依赖；AI 页面按路由懒加载。
- 新代码不得使用 PG 专有类型/语法（测试跑 SQLite）。
- 所有新增权限数据只来自 `security.ttl`，禁止在路由里硬编码角色矩阵。
- 门禁口径以 `backend/scripts/gate.py` 当前 15 项为基线，本计划新增 1 项后为 16 项。

---

## 1. 与文档路线图的偏差及理由

| 偏差 | 文档原计划 | 本计划 | 理由 |
|---|---|---|---|
| D1 | P1 一次性做 A1+A2 | P0 先做目录 + 闸（可独立验收），P1 再做意图与管道 | 目录与闸是纯新增只读代码，可先把"契约/约束/权限"跑通并纳入门禁；意图层依赖它们，分开可降低一次性大改的回归面 |
| D2 | D2 一次完成 | P0 做域级（TTL + 双栈生成物），P1 做意图级白名单 | 意图尚不存在时无法配置意图角色；且域级改动会触发 `generate_security --check` 与 parity，需单独一次提交保证可回滚 |
| D3 | C1 在 P3（路线图表），但优先级矩阵标为 P1 | 按矩阵取 P1（纯文档） | 文档自身口径冲突；C1 是零代码交付，且 P1 验收问题集就是 ROI 叙事的证据来源，提前可与业务对齐口径 |
| D4 | A4 在 P2 | 提前到 P1 | A4 只读聚合 + 模板，复用 `dashboard` 既有服务；P1 演示需要"能解释异常"的闭环 |
| D5 | A1 含"推理服务" | 改为"规则元数据 + 检索"，不做运行时推理 | `owlrl` 不支持 SWRL（见设计 §1.8）；派生逻辑已在 `business_rules.py`/`kitting_service.py` 中，重复实现会造第二事实源 |
| D6 | 假设本体全库覆盖 | 增加 `ai-projection.yaml` 只读投影 | 88 表中 59 张有 YAML 元数据、9 张只有类无字段、20 张无类（设计 §1.2）；不补投影则高频问题（订单/库存/信用）无法受控查询 |
| D7 | A3 MCP 在 P2 | 保持 P2 | 依赖 P1 的意图注册表稳定后再封装，避免工具契约反复变更 |
| D8 | B1/B2/C2/D4 在 P2/P3 | 保持 | 与文档一致；P3 仅预留 |
| D9 | 5 类高频问题含"本周产能利用率" | 替换为"低于安全库存物料"+"未处理计划异常"+"超期应收"，P1 覆盖 7 类 | `work_centers.capacity_utilization` 是主数据上的静态百分比（`backend/common/models/pp.py`），不是按周计算的负荷率；回答"本周"需重算排程工时/日历产能，属于新指标而非新查询，P1 不做以免制造误导性数字 |
| D10 | 文档 P1 还列了 C6 变更影响分析 | 本次不做 | 代码库无 ECN/变更单模型（`grep class Ecn` 为空），差异比对缺少领域数据模型；应先由工程域补 ECN 与 BOM/工艺差异接口，再由 AI 做解释层，避免把领域算法塞进 AI 层 |
| D11 | A1 含 `demo.ttl` 与通用 SPARQL | 不加载 `demo.ttl`；SPARQL 只在剔除 JwtConfig 的 schema 图执行 | 演示实例不应进入 AI 语义；`security.ttl` 含 JWT 配置三元组，直接暴露会泄露配置项。这是对 A1 的有意收窄（设计 K6/S1），P2 若要演示数据另建只读投影 |

---

## 2. 工作项分解

### P0 · 语义底座与安全前置

#### W0.1 运行时依赖与配置基线

- **目标**：让 `rdflib/pyshacl/PyYAML` 在本地、CI、镜像三处可用（`owlrl` 仅构建期）；建立 `AISettings`。
- **涉及文件**
  - 改：`backend/requirements.txt`（新增 `rdflib`、`pyshacl`、`PyYAML` 3 个运行时包，锁定与 CI 一致的小版本）
  - 新：`backend/requirements-dev.txt`（当前不存在；内容为 `owlrl`，仅 `ontology/scripts/validate-consistency.py` 使用）
  - 改：`.github/workflows/gate.yml`（用 `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` 替代临时安装）
  - 新：`backend/services/ai/__init__.py`、`backend/services/ai/config.py`、`backend/services/ai/errors.py`
- **依赖**：无
- **验收**
  1. `pip install -r backend/requirements.txt` 后 `python -c "import rdflib, pyshacl, yaml"` 成功；`import owlrl` 只在 dev 环境成立；
  2. `get_settings()` 对 **17 个**环境变量给出设计 §12 的默认值，`monkeypatch` 可覆盖；`AI_ENABLED` 与 `AI_CHATBI_ENABLED` 可独立关闭；
  3. 启动一致性校验：`AI_LLM_ENABLED=true` 且缺 `BASE_URL/MODEL` 时拒绝启动；公网 `http://` 且 `AI_LLM_ALLOW_EXTERNAL_DATA=false` 时拒绝启动；
  4. `AIException` 能序列化为 `{"code","message","trace_id"}`，HTTP 状态映射符合设计 §7.5（含 `AI_CHATBI_DISABLED`、`AI_EXECUTION_TIMEOUT`、`AI_LLM_EGRESS_BLOCKED`）；
  5. **镜像冒烟**：`docker build -f docker/backend.Dockerfile .` 后在容器内执行 `python -c "import rdflib, pyshacl, yaml; from backend.services.ai.config import get_settings; print(get_settings().enabled)"` 成功（评审 S10）。
- **风险**：`pyshacl` 与 `rdflib` 版本不匹配会在 `validate()` 时报错。缓解：版本锁死并以 W0.5 的正反例单测作为兼容性证据。

#### W0.2 `ai` 访问域与双栈策略（3 个本体源 + 3 份生成物）

- **目标**：`/api/ai/**` 强制登录；写操作 fail-closed；双栈 parity 自动覆盖。
- **涉及文件**（评审 B1：漏改任一处都会撞门禁）
  - 改：`ontology/src/security.ttl`（新增 `:DOMAIN_AI`，7 行）
  - 改：`ontology/src/shapes.ttl`（`:AccessDomainShape` 的 `sh:in` 追加 `"ai"`）
  - 改：`ontology/src/mappings.json`（`AccessDomain` 枚举追加 `"ai"`）
  - 再生成：`backend/common/utils/security_policy.py`、`frontend/src/types/authorization.generated.ts`、`ontology/generated/types.ts`
  - 新：`backend/api/routers/ai.py`（先只放 `require_ai_access` 与空 router）
  - 改：`backend/api/main.py`（import + `include_router(..., dependencies=[Depends(require_ai_access)])`，**不挂 `_gates`**）
- **依赖**：W0.1
- **验收**
  1. `python backend/ontology/generate_security.py --check` 通过；
  2. `python ontology/scripts/generate-types.py --check` 通过，`AccessDomain` 含 `"ai"`；
  3. `python backend/scripts/check_rbac_parity.py` 通过，且输出含 `ai`；
  4. `WRITE_ROLE_POLICY["ai"] == frozenset()`；`READ_OPEN_DOMAINS` 不含 `ai`；`READ_ROLE_POLICY["ai"]` 为 9 个角色；
  5. 匿名 `GET /api/ai/ping` → 401；9 个角色（含 ADMIN）登录 → 200；伪造角色 → 403（**路由探针测试**，评审 S8）；
  6. `node ontology/scripts/validate-type-sync.js` 与 `python ontology/scripts/validate-consistency.py` 仍绿（S48 不再触发）；
  7. `python backend/scripts/gate.py` 报告 16 项全绿。
- **风险**：误把 `ai` 域声明为 `anonymousRead true` 会使 AI 匿名可达。缓解：验收第 4/5 条写成显式断言，并纳入 `check_ai_catalog.py`；parity 只证明双栈一致，不证明策略正确，故必须有第 5 条行为测试。

#### W0.3 本体检索服务（A1）

- **目标**：TTL 在进程内只读加载，提供实体描述、词法检索、规则元数据、受限 SPARQL。
- **涉及文件**
  - 新：`backend/services/ai/ontology_service.py`
  - 新：`backend/tests/test_ai_ontology_service.py`
  - 改：`backend/api/routers/ai.py`（`/ontology/entities`、`/entities/{name}`、`/search`、`/rules`、`/sparql`）
- **依赖**：W0.1、W0.2
- **验收**
  1. `describe("Material")` 返回标签/顶层分类/属性/形状 IRI，且 `ontology_iri` 以 `https://dierp.local/ontology/erp/v1#` 开头；
  2. **检索**（评审 I11）：`search("物料")` 命中 `Material`；`search("库存")` 返回非空且包含 `InventoryValuation`；结果数 ≤ limit。**不**断言 `search("库存")→Material`（`Material` 的标签/注释不含"库存"，该断言必然失败）；
  3. `rules()` 返回 R1–Rn 的 id/label（解析失败降级为空列表，不抛异常）；
  4. SPARQL：`SELECT * WHERE {?s ?p ?o}` 被自动追加 `LIMIT 200`；含 `SERVICE`/`INSERT`/`FROM` 的查询返回 422；非 ADMIN 返回 403；**结果中不含 `JwtConfig` 的任何三元组，也不含 `demo.ttl` 实例**（评审 S1）；
  5. 服务为单例，连续两次调用不重复解析（加载计数器断言）；
  6. 在无 `ontology/` 目录时给出明确错误而非 500 堆栈。
- **风险**：`Path(__file__).parents[n]` 在镜像与本地不一致。缓解：复用 `backend/ontology/registry.py` 的 `ROOT` 解析方式，并在 W0.1 的 Docker 冒烟里断言路径存在。

#### W0.4 语义目录与遗留投影

- **目标**：59 个 YAML 实体 + 4 个投影实体合并为一张只读目录，字段/枚举/约束/形状完整，且形状路径全部可解释。
- **涉及文件**
  - 新：`backend/services/ai/catalog.py`
  - 新：`ontology/model/ai-projection.yaml`（4 张投影：materials / sales_orders / production_orders / customers；外加 `entity_overrides`：Forecast/MpsPlan/MrpRun/PlannedOrder/PurchaseOrder/ScheduleRun 的 `documentNumber` 映射，以及 SalesInvoice/ReceivableEntry 的 `domain: finance`）
  - 新：`backend/tests/test_ai_catalog.py`
  - 改：`ontology/README.md`（说明该文件不是模型生成源，`entity_overrides` 也不写回 YAML）
- **依赖**：W0.3
- **验收**
  1. 目录实体数 = 59 + 4 = **63**；`coverage` 统计为 `{ontology: 59, projection: 4, not_exposed: 25}`；每个实体 `table` 在 `Base.metadata` 中存在；
  2. **形状路径未命中数 = 0**（评审 B2）：`documentNumber` 由 `entity_overrides` 覆盖，`run_number→documentNumber` 在 `MrpRun`/`ScheduleRun` 上按实体分别登记；未覆盖即构建失败；
  3. `Material.material_type` 的 `enum` 等于 `["FG","SEMI","RAW","PACKAGING","SERVICE"]`（来自 `sh:in`，不是手写）；`material_code` 的 `pattern` 与 `MaterialShape` 一致；`required=True` 来自 `sh:minCount 1`；
  4. 每个实体 `domain` 非空：`SalesInvoice`/`ReceivableEntry` = `finance`，其余按文件/投影推导；`domain ∉ READ_OPEN_DOMAINS ∪ READ_ROLE_POLICY` 时构建失败；
  5. **`BOM` 不在目录中**（无 YAML、无投影），且任何意图都不得引用它；`sales_orders` 的 `rdf_overrides`（`order_number→documentNumber`、`delivery_date→dueDate`）生效；override 指向形状中不存在的 `sh:path` 时构建失败；
  6. 故意写错字段名/类名/域时目录构建失败并指出具体行；
  7. 二次调用走缓存（加载计数器不增加），**不断言毫秒级耗时**（评审 S3）。
- **风险**：抽象路径 `documentNumber` 在 6 个 YAML 实体上不成立。缓解：`entity_overrides` 按实体声明（不用全局别名，避免 `MrpRun`/`ScheduleRun` 串表）；验收第 2 条卡住"未命中即失败"。

#### W0.5 控制层：模式闸 + SHACL 闸

- **目标**：参数严格模式校验 + 复用既有 NodeShape 的约束校验；覆盖度如实回传。
- **涉及文件**
  - 新：`backend/services/ai/intent.py`（`BoundIntent/FieldMeta/EntityMeta/IntentSpec/QueryResult/Provenance`）
  - 新：`backend/services/ai/gates.py`
  - 新：`backend/tests/test_ai_gates.py`
- **依赖**：W0.4
- **验收**
  1. 多余参数 → 422 且错误信息含字段名；类型错误 → 422；
  2. 枚举越界（`material_type="FOO"`）→ 违规项 `path=materialType, component=InConstraintComponent`；`Literal` 的 datatype 为 `xsd:string`（**不是**枚举类 IRI）；
  3. 只提供 `material_type` 时，**不**因缺少 `material_code` 的 `minCount` 而报错；
  4. 状态只能取 `passed/partial/skipped/failed` 之一；无形状实体（`Customer`）→ `skipped`；含 `sh:sparql` 的形状（`PlannedOrder/MpsPlan`）→ `skipped`，不误报；
  5. 正反例各 ≥6 组，覆盖 §5.4 全部分支；`validate()` 的返回值按 `conforms, results_graph, _ = validate(...)` 解包（照抄设计示例即可运行）；
  6. 不设绝对耗时阈值；以"单次校验的 RDF 三元组数 ≤ 参数数 × 1"这类规模断言替代（评审 S3）。
- **风险**：`pyshacl` 高级特性/OWL 推理产生额外违规。缓解：固定 `inference="none"`、`advanced=False`（与 `ontology/scripts/validate-consistency.py:103` 一致），只过滤未提供路径的 `minCount`，其余违规全部保留（宁可误拒不可误放）。

#### W0.6 审计表与迁移（D3 表）

- **目标**：`ai_query_logs` 落地，纳入 Alembic 托管范围，并保证**写入可持久化**。
- **涉及文件**
  - 新：`backend/common/models/ai.py`
  - 新：`backend/migrations/versions/<rev>_add_ai_query_logs.py`
  - 改：`backend/migrations/env.py`、`backend/tests/conftest.py`
  - 新：`backend/tests/test_ai_audit.py`
- **依赖**：W0.1
- **验收**
  1. `python -m alembic check` → `No new upgrade operations detected.`；
  2. `upgrade head` / `downgrade -1` 可往返，且 downgrade 只删本表；
  3. 表不在 `LEGACY_UNMANAGED_TABLES` 中；
  4. SQLite 测试可建表并写入/查询（`JSON` 列可读写）；
  5. **持久化**（评审 I1）：用独立 `SessionLocal()` 写入一条审计后关闭，**重新开 session 必须能查到**（不是同一 session 内可见）；`get_db()` 不回滚/不 commit 的现状不适用于审计路径；
  6. `AI_LOG_QUESTION=false` 时 `question` 为 NULL 且 `question_sha256` 非空；保留期为代码常量，不在环境变量中。
- **风险**：忘记在 `env.py`/`conftest.py` 导入模型 → `alembic check` 把表判为"多余"。缓解：验收第 1、4 条同时卡住。

#### W0.7 门禁接入

- **目标**：AI 契约纳入聚合门禁，防止目录/意图/投影漂移。
- **涉及文件**
  - 新：`backend/scripts/check_ai_catalog.py`
  - 改：`backend/scripts/gate.py`（新增 1 项）
- **依赖**：W0.4、W0.5
- **验收**
  1. `python backend/scripts/check_ai_catalog.py` 在干净仓库退出 0，并打印 `{ontology: 59, projection: 4, not_exposed: 25}` 与未暴露清单；
  2. 覆盖设计 §11.1 的 7 类校验：目录构建、字段存在、`domain` 合法、形状路径命中 0 遗漏、投影/override 有效、意图注册表（含 `entities/primary_entity/record_key/shacl_coverage`）、覆盖率清单；
  3. 人为改坏投影字段/意图角色/形状 IRI/域，脚本分别非 0 退出且错误可定位；
  4. `python backend/scripts/gate.py` 报告 16 项，AI 项通过。
- **风险**：门禁导入 `backend.services.ai.*` 时若顶层触发 DB 连接会拖慢门禁。缓解：`catalog.py` 只读 `Base.metadata` 不建引擎；引擎仅在使用时创建。

---

### P1 · 受控 ChatBI

#### W1.1 意图契约与 7 个意图（A2 核心）

- **目标**：7 个手写只读意图（齐套/延期/库存/计划异常/信用/应收/质量），参数模型、角色矩阵、溯源字段齐备。
- **涉及文件**
  - 新：`backend/services/ai/intents/{__init__,kitting,inventory,orders,planning_exceptions,credit,receivables,quality}.py`
  - 新：`backend/scripts/export_ai_intent_meta.py`（`--write` 导出前端元数据，`--check` 漂移校验）
  - 新：`frontend/src/mock/ai-intents.json`（导出物，随 W1.4 一起提交）
  - 新：`backend/tests/test_ai_intents.py`
- **依赖**：W0.4、W0.5、W0.6、W0.7
- **验收**
  1. `INTENT_REGISTRY` 恰含 7 个 code，`check_ai_catalog.py` 通过；
  2. 每个 `IntentSpec` 都有 `entities/primary_entity/record_key/downlink/shacl_coverage`；`primary_entity` 在目录中；`record_key` 全是真实列（`mrp_exceptions` 无业务单号且 `run_number` 可空，用主键 `id`，`downlink=None`）；
  3. 每个 handler 只使用 ORM 表达式（评审 checklist：无 `text(`、无 f-string SQL、无 `execute(`）；时间统一 `datetime.now()`，窗口在 Python 侧算成具体时间点后绑定参数；
  4. 每个 handler 强制 `limit()`，且 `row_count ≤ AI_MAX_ROWS`；`QueryResult.sources` 的 `record_ref` 按 `record_key` 组装；
  5. **取数口径 fixture 断言**（评审 I4）：意图 2 断言 `SHIPPED` 不出现、`planned_finish_date > delivery_date` 被标记、无生产订单带 `risk_reason`；意图 5 断言应收余额 = `SUM(receivable_entries.amount)`（带符号金额：`INVOICE` 正、`RECEIPT` 负、`RECEIPT_REVERSE` 正、`INVOICE_REVERSE` 负，枚举共 5 个值），`credit_limit=0` 返回 null 比值；意图 6 断言 `DRAFT/PAID/CANCELLED` 排除、`ISSUED/PARTIALLY_PAID` 保留且部分收款按 `amount-received_amount`；
  6. 意图 7 默认 `status IN (OPEN, UNDER_REVIEW, DISPOSITIONED)`，意图 4 默认 `resolution_status=OPEN`；已关闭/已解决样本不出现；
  7. 每个意图 ≥3 条正例 + 1 条边界（空结果）；金额类列默认被 `output_fields` 裁剪，FINANCE/GM 可见；
  8. `python backend/scripts/export_ai_intent_meta.py --check` 通过，导出物含 7 个 code、角色矩阵、`record_key/downlink`。
- **风险**：意图 2/5/6 跨表 + 相对时间，SQLite 与 PG 的日期比较差异。缓解：禁止 DB 日期函数（`date_trunc` 等），统一绑定 Python 计算的 `datetime`；测试注入固定 `now`。

#### W1.2 编排管道、执行器与答案合成

- **目标**：`ask(question, user, db, request_id)` 12 步链路；确定性解析器（默认）与 LLM 提议器（可选）；溯源完整性强制；审计可持久化。
- **涉及文件**
  - 新：`backend/services/ai/pipeline.py`、`proposer.py`、`llm.py`、`executor.py`、`answer.py`、`audit.py`、`ratelimit.py`
  - 新：`backend/tests/test_ai_pipeline.py`、`backend/tests/test_ai_llm.py`
- **依赖**：W1.1
- **验收**
  1. `AI_LLM_ENABLED=false` 时 13 条验收问题全部有确定结果：9 条业务问题命中预期意图；4 条拒绝类（#6 非法枚举、#10 越界意图、#11 注入、#12 越权）被对应控制层拒绝；解析只认设计 §7.1.1 的规则表（单号正则/同义词/状态词/时间词），不做语义猜测；
  2. #11 在规则模式下由 **§7.1.2 前置分类**返回 `AI_INTENT_UNKNOWN` 且审计 `REJECTED_SCHEMA`；LLM 模式下用 stub 返回越界 JSON，被模式闸拒绝；
  3. LLM 返回非法 JSON / 未知意图 / 多余参数 → 全部被模式闸拒绝，且不重试风暴（≤2 次调用）；
  4. 溯源缺失时整条回答失败（`AI_PROVENANCE_INCOMPLETE`）；`shacl_status` 如实回传（`passed/partial/skipped/failed`），`skipped` 不写成 `passed`；
  5. 限流：第 21 次请求返回 429；
  6. **审计**（评审 I1）：成功/拒绝/失败三类都写 `ai_query_logs`，**独立 session commit**；请求结束后重新开 session 能查到；403/422/504 也有行；`request_id` 与 `operation_logs` 可关联；`AI_LOG_QUESTION=false` 时不存原文；
  7. **超时**（评审 I6）：注入慢查询后返回 504 `AI_EXECUTION_TIMEOUT`，PG 走 `statement_timeout`、SQLite 走 progress handler，两种方言都有单测；
  8. 答案中的数字集合 ⊆ 查询结果数字集合；字段白名单裁剪在 `answer.py` 生效（评审 I10）；
  9. **出域**（评审 I5）：`AI_LLM_ALLOW_EXTERNAL_DATA=false` 时发送 payload 不含行级明细（断言不含 `record_ref`/`customer_id`/金额列）。
- **风险**：确定性解析器关键词覆盖不足。缓解：解析器只映射到意图 + 显式参数（不猜值），未命中返回"暂不支持 + 3 个建议问题"；LLM 只是增强。

#### W1.3 AI 路由、错误码与健康探针

- **目标**：完成 `/api/ai/*` 契约、错误映射、OpenAPI 文档。
- **涉及文件**
  - 改：`backend/api/routers/ai.py`（chat / queries / feedback / insights 占位）
  - 新：`backend/tests/test_ai_router.py`
- **依赖**：W1.2
- **验收**
  1. 设计 §8.1 的 10 条路由全部出现在 OpenAPI；
  2. 每个错误码有对应 HTTP 状态与 `detail.code`；`AI_ENABLED=false` → 全部 503 `AI_DISABLED`，`AI_CHATBI_ENABLED=false` 时 `/chat` 503 而 `/ontology/*` 仍 200（评审 S6）；
  3. `POST /chat` 不写业务表（单测：调用前后 6 张关键表行数不变）；
  4. `GET /queries` 普通用户只能看到本人记录，ADMIN 可看全部；
  5. feedback 只能改本人记录（越权 403）。
- **风险**：`POST /chat` 被全局写审计记录为写操作，语义易混。缓解：保留 `operation_logs`（HTTP 轨迹）并在文档与 `ai_query_logs` 注释中说明二者关系。

#### W1.4 前端 AI 助手页与 mock

- **目标**：可对话、可看数据、可看溯源、可下钻；mock 模式完全可用。
- **涉及文件**
  - 新：`frontend/src/services/ai.ts`、`frontend/src/pages/ai/AiAssistantPage.tsx`（可拆 2–3 个子组件）
  - 改：`frontend/src/App.tsx`、`frontend/src/components/layout/menuConfig.tsx`、`navSections.ts`、`navSections.test.ts`
    （`NAV_SECTIONS` 是 `NAV_ITEMS` 的有序分区，模块加载即校验；`/ai` 必须插入"工作台"段并在 `NAV_ITEMS` 中同位置）
  - 改：`frontend/src/mock/handlers.ts`（新增 `/ai/*` 分流：登录 → 按 `ai-intents.json` 校验角色；**不走** method-based 写门）、`frontend/mock-tests/handlers.spec.ts`
- **依赖**：W1.3（契约冻结）、W1.1（导出 `ai-intents.json`）
- **验收**
  1. `npm run dev:mock` 下完成 **7 类**问题演示，来源区显示实体/表/单号/规则/`shacl_status`；
  2. 未登录访问 `/ai` 被路由守卫拦截；`WAREHOUSE` 角色问信用得到 403 文案；**合法角色 `POST /ai/chat` 在 mock 中返回 200（不被通用写门 403）**；
  3. `npx tsc --noEmit`、`eslint`、`vitest` 全绿；
  4. `node scripts/check-mock-rbac.mjs` 通过，且新增 3 条 AI 用例（匿名 401 / 越权 403 / 合法 200）；
  5. **一致性**（评审 S4）：`python backend/scripts/export_ai_intent_meta.py --check` 通过；对 13 条问题分别跑 mock 与后端，`{intent, params, columns, row_count, status}` 的 golden 快照 `diff` 为空（数据行内容允许不同）；
  6. **字段最小化**（评审 I10）：同一意图用 `WAREHOUSE` 与 `FINANCE` 两个角色各跑一次，后者多出金额列，前者不含金额列（mock 与后端各一份断言）；
  7. AI 页面为 `React.lazy` 路由，`vite build` 产物体积与基线对比有记录（不设硬阈值）。
- **风险**：菜单分组断言（`navSections.test.ts`）易漏改。缓解：验收第 3 条强制 vitest。

#### W1.5 A4 异常解读

- **目标**：把看板告警 / MRP 异常转成"是什么—为什么—建议"卡片，带证据链。
- **涉及文件**
  - 新：`backend/services/ai/insights.py`
  - 改：`backend/api/routers/ai.py`（`GET /insights/dashboard`）
  - 新：`backend/tests/test_ai_insights.py`
  - 改：`frontend/src/pages/dashboard/ManagementDashboard.tsx`（可选：嵌入入口）
- **依赖**：W1.2
- **验收**
  1. 输入窗口 `7d/30d`，返回 `{alerts:[{code,title,severity,evidence[],suggestion,drilldown}]}`；
  2. `evidence` 每项含 `table + record_ref`；无证据的告警不输出；
  3. `AI_LLM_ENABLED=false` 时使用模板文案，字段结构不变；启用润色时仍受 §7.4 出域规则约束（`ALLOW_EXTERNAL_DATA=false` 只发聚合值）；
  4. 不改变既有 `/api/dashboard/*` 响应。
- **风险**：与 `alerts.py`/dashboard 服务职责重叠。缓解：解读层只调用既有服务取数，不重算指标。

#### W1.6 验收基准集、最小演示数据集与回归

- **目标**：把设计附录 A 的 13 问变成可重复执行的回归集，并提供**自包含的演示数据**。
- **涉及文件**
  - 新：`backend/tests/test_ai_acceptance.py`
  - 新：`backend/tests/fixtures/ai_demo_dataset.py`（7 意图 × ≥3 条；含 1 个已关闭 NCR、1 个已解决 MRP 异常、1 个已收款发票、1 张无生产订单的销售订单）
  - 可选：`backend/scripts/probe_ai_chatbi.py`（需 DB，opt-in）
- **依赖**：W1.2、W1.3
- **验收**
  1. **13 条**全部自动化通过（无需 LLM，无需 PG）；
  2. 报告输出每条的实际意图、`params`、`record_key`、命中/拒绝原因；
  3. 越权/注入类（#10、#11、#12）断言"无写操作 + 结构化拒绝 + 审计状态"；
  4. 数值型断言来自 fixture 而非"有行"：信用占用比、逾期未收金额、齐套缺料数至少各 1 条精确断言；
  5. 数据集可重复初始化（同一 fixture 跑两次结果相同），单号全部由 fixture 常量提供，不在测试里硬编码示意值（评审 S12）。
- **风险**：测试数据与真实库分布不同导致空结果。缓解：数据集显式覆盖"命中/不命中/边界"三类样本，断言结构与数值而非全库统计。

#### W1.7 C1 ROI 量化叙事（文档）

- **目标**：把 P1 能力换算成可评审的业务价值口径。
- **涉及文件**
  - 新：`outputs/03-ROI量化叙事-DIERP-AI.md`（交付时撰写）
- **依赖**：W1.6
- **验收**
  1. 每个场景给出"现状耗时/步骤数 → 目标耗时/步骤数 → 假设与来源"；
  2. 所有数字标注为"测算假设"，可从验收基准集复现；
  3. 不承诺未经测量的百分比。
- **风险**：无基线数据导致叙事失真。缓解：明确"待实测"项，附测量方法。

---

### P2 · 生态与工作流

#### W2.1 MCP 只读工具层（A3）

- **目标**：把 7 个意图暴露为 MCP 工具，供外部 Agent 调用。
- **涉及文件**
  - 新：`backend/services/ai/mcp/{__init__,server,tools}.py`
  - 新：`backend/tests/test_ai_mcp_tools.py`
  - 改：`backend/scripts/check_ai_catalog.py`（工具清单 = 只读意图清单）
- **依赖**：W1.6
- **验收**
  1. 工具数 = 只读意图数，schema 由 `model_json_schema()` 生成；
  2. 无任何写工具；调用未知工具返回结构化错误；
  3. 服务角色由 `MCP_ROLE` 决定，默认 `GENERAL_MANAGER`，审计落 `ai_query_logs`（`username="mcp:<token_id>"`）；
  4. token 缺失/错误 → 拒绝。
- **风险**：工具契约随意图变更漂移。缓解：门禁比对清单，CI 阻断。

#### W2.2 L2 工作流 AI 旁路（A5 审批辅助/对账提示）

- **目标**：在报价/订单评审等节点给出建议，但由人工动作执行（对应文档 A5）。
- **涉及文件**
  - 新：`backend/services/ai/workflow_suggest.py`
  - 新：`backend/common/models/ai.py` 增 `workflow_ai_suggestions`（或独立文件）
  - 改：对应评审路由（只读调用建议接口，不改状态机）
- **依赖**：W1.6
- **验收**
  1. 建议接口只返回 `{suggestion, evidence_refs, confidence}`；
  2. 单测证明调用建议接口前后审批状态不变；
  3. 建议落表可追溯（建议 id 关联单据号）。
- **风险**：越权改状态。缓解：建议服务不注入写权限依赖，代码评审强制检查。

#### W2.3 ERP-MES 语义映射 v1（B1）

- **目标**：设备/工序/工单编码在两侧的语义对照，供追溯与异常解释。
- **涉及文件**
  - 新：`ontology/model/mes-mapping.yaml`
  - 新：`backend/services/ai/semantics.py`
  - 改：`backend/api/routers/ai.py`（`GET /semantics/mes`）
  - 改：`check_ai_catalog.py`（映射项校验）
- **依赖**：W1.6
- **验收**
  1. 每个映射项锚定已存在的本体类；
  2. 未匹配的 MES 字段返回 `unmapped` 列表而非猜测；
  3. 只读接口，角色 ≥ 现有 `traceability` 读策略。
- **风险**：映射靠人工维护易腐坏。缓解：门禁校验 + 覆盖率报表。

#### W2.4 本体扩面（含 SHACL 覆盖升级）

- **目标**：补齐 AI 高频区域的类/形状/投影，把 P1 中 `shacl_coverage=none` 的 3 个意图升级。
- **涉及文件**
  - 改：`ontology/src/erp-ontology.ttl`（新增 Quotation/LotCard 等类）
  - 改：`ontology/src/shapes.ttl`（`CustomerShape`、`WorkCenterShape`、`RoutingShape`、`QuotationShape`、`LotCardShape`；并补 `SalesInvoiceShape` 的账龄/收款字段、`SalesOrderShape` 的风险相关字段）
  - 改：`ontology/src/mappings.json`（如缺枚举）
  - 改：`ontology/model/ai-projection.yaml`（新增投影表）
  - 改：`backend/services/ai/intents/*`（`shacl_coverage` 声明随之升级）
- **依赖**：W2.3
- **验收**
  1. 每个新类有且仅有一个顶层分类（`validate-type-sync` 通过）；
  2. 每个新类有 NodeShape（`validate-consistency` 通过）；
  3. 新增枚举三向一致（TTL/mappings/生成物）；
  4. **覆盖升级**：意图 5（信用）从 `none → full`，意图 6（应收）从 `none → partial/full`，意图 2（延期）至少 `none → partial`，意图 1 从 `partial → full`（补 `sourceRef` 形状）；`check_ai_catalog.py` 输出的覆盖率与声明一致；
  5. AI 可访问实体数从 63 提升，且 `not_exposed` 清单同步减少。
- **风险**：本体改动触发全量生成物重生成（模型/TS/安全）。缓解：单独提交，先跑 `generate_models --check` 与 `generate-types --check` 确认影响面。

---

### P3 · 深化（仅预留）

| 工作项 | 内容 | 验收 |
|---|---|---|
| W3.1 成本闭环 AI 归因（C2） | 在 `ai-ontology-design` 之外新增成本差异意图族；复用 `finance` 既有服务 | 设计评审通过，接口占位返回 501 |
| W3.2 排程解释（B2） | 对 APS 结果给出"为什么这样排"的约束解释 | 解释只引用既有排程约束，不重算 |
| W3.3 多租户接入点（D4） | 审计表与意图层预留 `tenant_id`；本体域不扩展 | 迁移可加列且默认 NULL，不影响现有查询 |

---

## 3. 依赖关系（DAG）

```
W0.1 ──┬─> W0.2 ──> W0.3 ──> W0.4 ──> W0.5 ──> W0.7
       └─> W0.6 ────────────────────────────────┘
                                   │
                                   ▼
                    W1.1 ──> W1.2 ──┬─> W1.3 ──> W1.4
                                     ├─> W1.5
                                     └─> W1.6 ──> W1.7
                                                   │
                                     ┌─────────────┴──────────┐
                                     ▼                        ▼
                                   W2.1                     W2.2
                                     │                        │
                                     └──────> W2.3 ──> W2.4 <┘
                                                   │
                                                   ▼
                                            W3.1/W3.2/W3.3
```

**并行建议**
- W0.6（审计表）与 W0.2–W0.5 可并行（不同文件、无共享状态）。
- W1.4（前端）可在 W1.3 契约冻结后与 W1.5 并行。
- W1.7（文档）在 W1.6 通过后立即进行，不阻塞 P2。

---

## 4. 逐项文件影响清单（汇总）

**新增（后端）**
```
backend/services/ai/{__init__,config,errors,intent,gates,catalog,ontology_service,
                     proposer,llm,executor,answer,audit,ratelimit,pipeline,insights}.py
backend/services/ai/intents/{__init__,kitting,inventory,orders,planning_exceptions,
                             credit,receivables,quality}.py
backend/common/models/ai.py
backend/api/routers/ai.py
backend/migrations/versions/<rev>_add_ai_query_logs.py
backend/scripts/check_ai_catalog.py
backend/scripts/export_ai_intent_meta.py
backend/tests/{test_ai_ontology_service,test_ai_catalog,test_ai_gates,test_ai_intents,
               test_ai_pipeline,test_ai_llm,test_ai_router,test_ai_audit,
               test_ai_insights,test_ai_acceptance}.py
backend/tests/fixtures/ai_demo_dataset.py
ontology/model/ai-projection.yaml
backend/requirements-dev.txt                      # 当前不存在，新建（仅 owlrl）
```

**修改（后端/本体）**
```
ontology/src/security.ttl                         # 新增 :DOMAIN_AI
ontology/src/shapes.ttl                           # AccessDomainShape.sh:in 追加 "ai"
ontology/src/mappings.json                        # AccessDomain 追加 "ai"
ontology/generated/types.ts                       # 生成物
backend/common/utils/security_policy.py           # 生成物
frontend/src/types/authorization.generated.ts     # 生成物
backend/api/main.py
backend/common/models/__init__.py                # 可选：导出 ai（不影响 Base.metadata）
backend/migrations/env.py
backend/tests/conftest.py
backend/requirements.txt
backend/scripts/gate.py
.github/workflows/gate.yml
ontology/README.md
```

**新增（前端）**
```
frontend/src/services/ai.ts
frontend/src/pages/ai/AiAssistantPage.tsx
frontend/src/mock/ai-intents.json                # 由 export_ai_intent_meta.py 生成
```

**修改（前端）**
```
frontend/src/App.tsx
frontend/src/components/layout/menuConfig.tsx
frontend/src/components/layout/navSections.ts
frontend/src/components/layout/navSections.test.ts
frontend/src/mock/handlers.ts
frontend/mock-tests/handlers.spec.ts
frontend/mock-tests/golden/ai_acceptance.json   # S4：13 条契约快照
```

**交付文档**
```
outputs/03-ROI量化叙事-DIERP-AI.md               # W1.7
```

---

## 5. 验证与回归命令

每个工作项合并前至少执行：

```powershell
# 本体与双栈策略
python backend/ontology/generate_models.py --check
python backend/ontology/generate_security.py --check
python ontology/scripts/generate-types.py --check
node ontology/scripts/validate-type-sync.js
python ontology/scripts/validate-consistency.py

# 后端
python -m pytest -q                     # cwd=backend
python -m alembic check                 # cwd=backend，需本地 PG
python backend/scripts/check_rbac_parity.py
python backend/scripts/check_ai_catalog.py
python backend/scripts/export_ai_intent_meta.py --check

# 前端
npx tsc --noEmit && npx eslint . --ext ts,tsx --max-warnings 0
npx vitest run
node scripts/check-mock-rbac.mjs
npx tsx mock-tests/handlers.spec.ts

# 聚合
python backend/scripts/gate.py          # 期望 16 项全绿

# 镜像（W0.1 验收，评审 S10）
docker build -f docker/backend.Dockerfile -t dierp-backend:ai .
docker run --rm dierp-backend:ai python -c "import rdflib, pyshacl, yaml; print('ok')"
```

> `alembic check` 需要 PostgreSQL；AI 新增门禁与单测均不依赖数据库，保证 CI 可移植。
> 镜像冒烟只在 P0 出口执行一次（CI 可选 job），不进入每次提交的 hermetic 门禁。

---

## 6. 阶段出口检查清单

### P0 出口
- [ ] `ai` 域双栈一致（3 源 + 3 生成物），匿名 401，9 个角色（含 ADMIN）200，伪造角色 403
- [ ] `/api/ai/ontology/*` 5 个只读接口可用，SPARQL 仅在 schema 图执行且不含 JwtConfig/demo
- [ ] 目录覆盖 59 + 4 = 63，`not_exposed: 25` 有清单；形状路径未命中 = 0
- [ ] SHACL 闸正反例 ≥12 组通过，`skipped/partial/failed` 状态可断言
- [ ] `ai_query_logs` 迁移往返成功，`alembic check` 绿，**重开 session 能查到审计行**
- [ ] `check_ai_catalog.py` 入 gate，16 项全绿
- [ ] 镜像冒烟通过（`rdflib/pyshacl/yaml` 可导入）

### P1 出口
- [ ] **13 条**验收问题全部符合预期（含 4 条必须拒绝：非法枚举/越界意图/注入/越权）
- [ ] **7 类**业务问题（缺料、延期、库存、计划异常、信用、应收、质量）意图命中率 ≥90%，数值断言来自 fixture
- [ ] 无 LLM 时功能完整；LLM 故障自动降级；`ALLOW_EXTERNAL_DATA=false` 时无行级明细出境
- [ ] 溯源完整率 100%（缺证据即失败），`record_key` 与 `downlink` 全部有值或显式为 null
- [ ] 前端 mock 与真实后端对 13 条的 `{intent, params, columns, row_count, status}` 快照一致
- [ ] `POST /chat` 前后业务表零变更；查询超时返回 504 且落审计
- [ ] C1 叙事文档完成，数字可复现

### P2 出口
- [ ] MCP 工具清单 = 7 个只读意图清单，且无写工具
- [ ] 工作流建议不改变任何审批状态（单测证据）
- [ ] MES 映射项 100% 锚定本体类
- [ ] 本体扩面后全部本体门禁与生成物门禁绿；意图 5/6/2 的 `shacl_coverage` 已升级

---

## 7. 风险登记册（跨阶段）

| ID | 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|---|
| R1 | 意图覆盖不足导致"问不到" | 高 | 体验差 | 以 **13 条**验收问题为最小集；未命中返回建议问题；按真实提问日志迭代（P2） |
| R2 | SHACL 误拒合法查询 | 中 | 功能不可用 | 只忽略未提供路径的 minCount；`inference="none"` + `advanced=False`；正反例回归；错误信息透出约束名 |
| R3 | 目录与真实列漂移 | 中 | 运行时 500 | 构建期失败 + 门禁；形状路径未命中即失败；禁止懒校验 |
| R4 | 匿名读现状被误读为已做行级隔离 | 高 | 安全误判 | 文档明示"仅域/意图/字段级"；D2 验收口径可执行；UI 标注"全公司范围" |
| R5 | LLM 输出被注入 / 数据出境 | 中 | 越权/幻觉/外泄 | 封闭目录 + extra=forbid + 无 SQL 通道 + 数字回查 + 默认只发聚合值 + 启动校验 |
| R6 | 迁移遗漏 env/conftest 导入 | 中 | 门禁/测试失败 | 验收双卡点（alembic check + SQLite 建表） |
| R7 | 前端菜单/路由漏改 | 中 | 页面不可达 | vitest 断言 + tsc |
| R8 | 依赖版本不兼容（rdflib/pyshacl） | 中 | 服务启动失败 | 版本锁死 + W0.5 单测 + 镜像冒烟 |
| R9 | 审计表增长过快 | 低 | 性能 | 截断问题文本、只存摘要、按时间索引、保留期常量 |
| R10 | 多实例下限流失效 | 低 | 限流不准 | 文档声明单进程局限；P2 视部署形态换集中式限流 |
| R11 | 审计行随请求事务回滚而丢失 | 高（若不处理） | 溯源完全落空 | 独立 `SessionLocal()` + 显式 commit；验收"重开 session 可查" |
| R12 | 查询超时在 SQLite/PG 行为不一 | 中 | 部分环境无保护 | 方言分支 + Python 预算兜底；不可用时如实记审计 |
| R13 | `ai` 域只改 security.ttl 导致门禁失败 | 中 | P0 阻塞 | W0.2 清单固化 3 源 + 3 生成物；验收 4 个门禁命令 |
| R14 | 形状抽象路径漏配导致约束被静默丢弃 | 中 | 语义错误 | `entity_overrides` + "未命中 = 0" 构建期失败 |
