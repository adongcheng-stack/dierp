# DIERP AI 原生化 · 实施计划

- 文档版本：v1.0
- 日期：2026-11-24
- 配套设计：[01-系统设计-DIERP-AI原生化.md](01-系统设计-DIERP-AI原生化.md)
- 依据：[DIERP-AI-ERP提升方案-深度研究-20261124.md](../../../docs/DIERP-AI-ERP提升方案-深度研究-20261124.md)
- 计划口径：按"可独立验收的工作项"拆分，不按自然时间拆分；每项给出依赖、文件范围、验收口径与风险，可直接作为开发任务单。

---

## 0. 总览

| 阶段 | 目标 | 对应文档条目 | 出口标准 |
|---|---|---|---|
| **P0 语义底座** | 本体可被服务化检索；AI 安全域与审计表落地；门禁覆盖 | A1、D2（域级）、D3（表） | `GET /api/ai/ontology/*` 可用；`ai` 域双栈策略一致；`ai_query_logs` 迁移通过；新增门禁绿 |
| **P1 受控 ChatBI** | 7 个意图 + 四闸 + 前端页面 + 异常解读 + 验收基准 | A2、A4、D2（意图级）、D3（链路）、C1 | 13 条验收问题全部按预期通过；越权/注入/超范围问题全部被拒；mock 与真实后端行为一致 |
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
| D6 | 假设本体全库覆盖 | 增加 `ai-projection.yaml` 只读投影 | 88 表中 59 张有元数据、20 张无本体类（设计 §1.2）；不补投影则高频问题（订单/库存/信用）无法受控查询 |
| D7 | A3 MCP 在 P2 | 保持 P2 | 依赖 P1 的意图注册表稳定后再封装，避免工具契约反复变更 |
| D8 | B1/B2/C2/D4 在 P2/P3 | 保持 | 与文档一致；P3 仅预留 |
| D9 | 5 类高频问题含"本周产能利用率" | 替换为"低于安全库存物料"+"未处理计划异常"+"超期应收"，产能利用率延后 | `work_centers.capacity_utilization` 是主数据上的静态百分比（`backend/common/models/pp.py`），不是按周计算的负荷率；回答"本周"需重算排程工时/日历产能，属于新指标而非新查询，P1 不做以免制造误导性数字 |
| D10 | 文档 P1 还列了 C6 变更影响分析 | 本次不做 | 代码库无 ECN/变更单模型（`grep class Ecn` 为空），差异比对缺少领域数据模型；应先由工程域补 ECN 与 BOM/工艺差异接口，再由 AI 做解释层，避免把领域算法塞进 AI 层 |

---

## 2. 工作项分解

### P0 · 语义底座与安全前置

#### W0.1 运行时依赖与配置基线

- **目标**：让 `rdflib/pyshacl/owlrl/PyYAML` 在本地、CI、镜像三处可用；建立 `AISettings`。
- **涉及文件**
  - 改：`backend/requirements.txt`（新增 4 个包，锁定与 CI 一致的小版本）
  - 改：`.github/workflows/gate.yml`（用 `pip install -r backend/requirements.txt` 替代临时安装）
  - 新：`backend/services/ai/__init__.py`、`backend/services/ai/config.py`、`backend/services/ai/errors.py`
- **依赖**：无
- **验收**
  1. `pip install -r backend/requirements.txt` 后 `python -c "import rdflib, pyshacl, owlrl, yaml"` 成功；
  2. `get_settings()` 对 11 个环境变量给出设计 §12 的默认值，`monkeypatch` 可覆盖；
  3. `AIException` 能序列化为 `{"code","message","trace_id"}`，HTTP 状态映射符合设计 §7.5。
- **风险**：`pyshacl` 与 `rdflib` 版本不匹配会导致 `advanced=True` 报错。缓解：版本锁死并以 W0.5 的正反例单测作为兼容性证据。

#### W0.2 `ai` 访问域与双栈策略

- **目标**：`/api/ai/**` 强制登录；写操作 fail-closed；双栈 parity 自动覆盖。
- **涉及文件**
  - 改：`ontology/src/security.ttl`（新增 `:DOMAIN_AI`，7 行）
  - 再生成：`backend/common/utils/security_policy.py`、`frontend/src/types/authorization.generated.ts`
  - 新：`backend/api/routers/ai.py`（先只放 `require_ai_access` 与空 router）
  - 改：`backend/api/main.py`（import + `include_router(..., dependencies=[Depends(require_ai_access)])`，**不挂 `_gates`**）
- **依赖**：W0.1
- **验收**
  1. `python backend/ontology/generate_security.py --check` 通过；
  2. `python backend/scripts/check_rbac_parity.py` 通过，且输出含 `ai`；
  3. `WRITE_ROLE_POLICY["ai"] == frozenset()`；`READ_OPEN_DOMAINS` 不含 `ai`；
  4. 匿名 `GET /api/ai/health`（临时探针）→ 401；任一业务角色登录 → 200；
  5. `security.ttl` 未引入新谓词，`validate-type-sync.js` 与 `validate-consistency.py` 仍绿。
- **风险**：误把 `ai` 域声明为 `anonymousRead true` 会使 AI 匿名可达。缓解：验收第 3 条写成显式断言，并纳入 `check_ai_catalog.py`。

#### W0.3 本体检索服务（A1）

- **目标**：TTL 在进程内只读加载，提供实体描述、词法检索、规则元数据、受限 SPARQL。
- **涉及文件**
  - 新：`backend/services/ai/ontology_service.py`
  - 新：`backend/tests/test_ai_ontology_service.py`
  - 改：`backend/api/routers/ai.py`（`/ontology/entities`、`/entities/{name}`、`/search`、`/rules`、`/sparql`）
- **依赖**：W0.1、W0.2
- **验收**
  1. `describe("Material")` 返回标签/顶层分类/属性/形状 IRI，且 `ontology_iri` 以 `https://dierp.local/ontology/erp/v1#` 开头；
  2. `search("库存")` 命中 `Material` 且结果数 ≤ limit；
  3. `rules()` 返回 R1–Rn 的 id/label（解析失败降级为空列表，不抛异常）；
  4. SPARQL：`SELECT * WHERE {?s ?p ?o}` 被自动追加 `LIMIT 200`；含 `SERVICE`/`INSERT`/`FROM` 的查询返回 422；非 ADMIN 调用返回 403；
  5. 服务为单例，连续两次调用不重复解析（可用加载计数器断言）；
  6. 在无 `ontology/` 目录时给出明确错误而非 500 堆栈。
- **风险**：`Path(__file__).parents[n]` 在镜像与本地不一致。缓解：复用 `backend/ontology/registry.py` 的 `ROOT` 解析方式，并在 Dockerfile 冒烟里断言路径存在。

#### W0.4 语义目录与遗留投影

- **目标**：59 个 YAML 实体 + 投影实体合并为一张只读目录，字段/枚举/约束/形状完整。
- **涉及文件**
  - 新：`backend/services/ai/catalog.py`
  - 新：`ontology/model/ai-projection.yaml`（首批 4 张：materials / sales_orders / production_orders / customers）
  - 新：`backend/tests/test_ai_catalog.py`
  - 改：`ontology/README.md`（说明该文件不是模型生成源）
- **依赖**：W0.3
- **验收**
  1. 目录实体数 = 59 + 投影实体数；每个实体 `table` 在 `Base.metadata` 中存在；
  2. `Material` 的 `material_type` 字段 `enum` 等于 `["FG","SEMI","RAW","PACKAGING","SERVICE"]`（来自 `sh:in`，不是手写）；
  3. `material_code` 的 `pattern` 与 `MaterialShape` 完全一致；`required=True` 来自 `sh:minCount 1`；
  4. 投影实体 `coverage="projection"`；未列入投影的遗留表**不可**被任何意图引用；
  5. `sales_orders` 的 `rdf_overrides`（`order_number→documentNumber`、`delivery_date→dueDate`）生效；override 指向形状中不存在的 `sh:path` 时构建失败；
  6. 故意写错字段名/类名时目录构建失败并指出具体行；
  7. 目录构建耗时 <300ms（本机冷启动），二次调用走缓存。
- **风险**：`snake↔camel` 在个别字段上不成立（如缩写）。缓解：构建期输出"无法映射到形状属性"的字段清单，测试允许清单为空或显式白名单。

#### W0.5 四闸中的两闸（模式闸 + SHACL 闸）

- **目标**：参数严格模式校验 + 复用既有 NodeShape 的约束校验。
- **涉及文件**
  - 新：`backend/services/ai/intent.py`（`BoundIntent/IntentSpec/QueryResult/Provenance`）
  - 新：`backend/services/ai/gates.py`
  - 新：`backend/tests/test_ai_gates.py`
- **依赖**：W0.4
- **验收**
  1. 多余参数 → 422 且错误信息含字段名；类型错误 → 422；
  2. 枚举越界（`material_type="FOO"`）→ 违规项 `path=materialType, component=InConstraintComponent`；
  3. 只提供 `material_type` 时，**不**因缺少 `material_code` 的 `minCount` 而报错；
  4. 无形状实体（`Customer`）返回 `shacl="skipped"`；参数只部分被形状覆盖时返回 `shacl="partial"`，且不阻断；
  5. 正反例各 ≥6 组，全部覆盖 §5.4 算法分支；
  6. 单次校验耗时 <50ms（本机）。
- **风险**：`pyshacl` 的 `advanced=True` 与 OWL 推理交互产生额外违规。缓解：固定 `inference="none"`，仅过滤 minCount，其余违规全部保留（宁可误拒不可误放）。

#### W0.6 审计表与迁移（D3 表）

- **目标**：`ai_query_logs` 落地，纳入 Alembic 托管范围。
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
  5. 审计写入异常时不抛出到调用方（单测注入失败 session）。
- **风险**：忘记在 `env.py`/`conftest.py` 导入模型 → `alembic check` 把表判为"多余"。缓解：验收第 1、4 条同时卡住。

#### W0.7 门禁接入

- **目标**：AI 契约纳入聚合门禁，防止目录/意图/投影漂移。
- **涉及文件**
  - 新：`backend/scripts/check_ai_catalog.py`
  - 改：`backend/scripts/gate.py`（新增 1 项）
- **依赖**：W0.4、W0.5
- **验收**
  1. `python backend/scripts/check_ai_catalog.py` 在干净仓库退出 0，并打印覆盖率统计；
  2. 人为改坏投影字段/意图角色/形状 IRI，脚本分别以非 0 退出且错误可定位；
  3. `python backend/scripts/gate.py` 报告 16 项，AI 项通过。
- **风险**：门禁依赖导入 `backend.services.ai.*`，若其顶层 import 触发 DB 连接会拖慢门禁。缓解：`catalog.py` 只读 `Base.metadata` 不建引擎；引擎仅在使用时创建。

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
  2. 每个 handler 只使用 ORM 表达式（代码评审 checklist：无 `text(`、无 f-string SQL、无 `execute(`）；
  3. 每个 handler 强制 `limit()`，且 `row_count ≤ AI_MAX_ROWS`；
  4. 每个 `QueryResult.sources` 的 `record_ref` 非空（单测逐意图断言）；
  5. 意图 3/4 的枚举过滤与 SHACL 结果一致；意图 5 在无信用额度时返回"无额度"而非报错；
  6. 7 个意图各 ≥2 条正例 + 1 条边界例（空结果）；
  7. `python scripts/export_ai_intent_meta.py --check` 通过，且导出物含 7 个 code 与角色矩阵。
- **风险**：意图 2/5 跨表 + 相对时间，SQLite 与 PG 的日期比较差异。缓解：统一用 `datetime` 参数绑定，禁止数据库函数（`date_trunc` 等）；测试用固定 `now` 注入。

#### W1.2 编排管道、执行器与答案合成

- **目标**：`ask()` 11 步链路；确定性解析器（默认）与 LLM 提议器（可选）；溯源完整性强制。
- **涉及文件**
  - 新：`backend/services/ai/pipeline.py`、`proposer.py`、`llm.py`、`executor.py`、`answer.py`、`audit.py`、`ratelimit.py`
  - 新：`backend/tests/test_ai_pipeline.py`、`backend/tests/test_ai_llm.py`
- **依赖**：W1.1
- **验收**
  1. `AI_LLM_ENABLED=false` 时 13 条验收问题全部有确定结果：9 条业务问题命中预期意图；4 条拒绝类（#6 非法枚举、#10 越界意图、#11 注入、#12 越权）全部被对应闸门拒绝；
     参数抽取只认显式触发词（"客户 X"、"类型 X"、"N 天内"、"N 天以上"），不做语义猜测；
  2. LLM 返回非法 JSON / 未知意图 / 多余参数 → 全部被模式闸拒绝，且不重试风暴（≤2 次调用）；
  3. 溯源缺失时整条回答失败（`AI_PROVENANCE_INCOMPLETE`），不返回半成品；
  4. 限流：第 21 次请求返回 429；
  5. 审计：成功/拒绝/失败三类都写 `ai_query_logs`，`request_id` 与 `operation_logs` 可关联；
  6. 答案中的数字集合 ⊆ 查询结果数字集合（数字回查单测）。
- **风险**：确定性解析器关键词覆盖不足。缓解：解析器只映射到意图 + 显式参数（不猜值），未命中时返回"暂不支持 + 3 个建议问题"；LLM 只是增强。

#### W1.3 AI 路由、错误码与健康探针

- **目标**：完成 `/api/ai/*` 契约、错误映射、OpenAPI 文档。
- **涉及文件**
  - 改：`backend/api/routers/ai.py`（chat / queries / feedback / insights 占位）
  - 新：`backend/tests/test_ai_router.py`
- **依赖**：W1.2
- **验收**
  1. 设计 §8 的 9 条路由全部出现在 OpenAPI；
  2. 每个错误码有对应 HTTP 状态与 `detail.code`；
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
  1. `npm run dev:mock` 下完成 6 类问题演示，来源区显示实体/表/单据号/规则；
  2. 未登录访问 `/ai` 被路由守卫拦截；`WAREHOUSE` 角色问信用得到 403 文案；**合法角色 `POST /ai/chat` 在 mock 中返回 200（不被通用写门 403）**；
  3. `npx tsc --noEmit`、`eslint`、`vitest` 全绿；
  4. `node scripts/check-mock-rbac.mjs` 通过，且新增 3 条 AI 用例（匿名 401 / 越权 403 / 合法 200）；
  5. `python scripts/export_ai_intent_meta.py --check` 通过（mock 角色矩阵与后端注册表一致）；
  6. AI 页面为 `React.lazy` 路由，`vite build` 产物体积无显著增长（与基线对比记录）。
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
  3. `AI_LLM_ENABLED=false` 时使用模板文案，字段结构不变；
  4. 不改变既有 `/api/dashboard/*` 响应。
- **风险**：与 `alerts.py`/dashboard 服务职责重叠。缓解：解读层只调用既有服务取数，不重算指标。

#### W1.6 验收基准集与回归

- **目标**：把设计附录 A 的 12 问变成可重复执行的回归集。
- **涉及文件**
  - 新：`backend/tests/test_ai_acceptance.py`
  - 可选：`backend/scripts/probe_ai_chatbi.py`（需 DB，opt-in）
- **依赖**：W1.2、W1.3
- **验收**
  1. 12 条全部自动化通过（无需 LLM，无需 PG）；
  2. 报告输出每条的实际意图、命中/拒绝原因、耗时；
  3. 越权/注入类（#10、#11、#12）断言"无写操作 + 结构化拒绝"。
- **风险**：测试数据与真实库分布不同导致空结果。缓解：测试用固定 fixture 造数，断言结构而非具体业务值。

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

- **目标**：把 6 个意图暴露为 MCP 工具，供外部 Agent 调用。
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

#### W2.4 本体扩面

- **目标**：补齐 AI 高频区域的类/形状/投影，提升覆盖率。
- **涉及文件**
  - 改：`ontology/src/erp-ontology.ttl`（新增 Quotation/LotCard 等类）
  - 改：`ontology/src/shapes.ttl`（CustomerShape/WorkCenterShape/RoutingShape/QuotationShape/LotCardShape）
  - 改：`ontology/src/mappings.json`（如缺枚举）
  - 改：`ontology/model/ai-projection.yaml`（新增投影表）
- **依赖**：W2.3
- **验收**
  1. 每个新类有且仅有一个顶层分类（`validate-type-sync` 通过）；
  2. 每个新类有 NodeShape（`validate-consistency` 通过）；
  3. 新增枚举三向一致（TTL/mappings/生成物）；
  4. AI 覆盖率从 59+投影 提升到目标值，并在 `check_ai_catalog.py` 输出中体现。
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
                             credit,receivables}.py
backend/common/models/ai.py
backend/api/routers/ai.py
backend/migrations/versions/<rev>_add_ai_query_logs.py
backend/scripts/check_ai_catalog.py
backend/scripts/export_ai_intent_meta.py
backend/tests/{test_ai_ontology_service,test_ai_catalog,test_ai_gates,test_ai_intents,
               test_ai_pipeline,test_ai_llm,test_ai_router,test_ai_audit,
               test_ai_insights,test_ai_acceptance}.py
ontology/model/ai-projection.yaml
```

**修改（后端/本体）**
```
ontology/src/security.ttl
backend/common/utils/security_policy.py          # 生成物
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
frontend/src/types/authorization.generated.ts    # 生成物
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
```

> `alembic check` 需要 PostgreSQL；AI 新增门禁与单测均不依赖数据库，保证 CI 可移植。

---

## 6. 阶段出口检查清单

### P0 出口
- [ ] `ai` 域双栈一致，匿名 401，业务角色 200
- [ ] `/api/ai/ontology/*` 5 个只读接口可用，SPARQL 安全规则生效
- [ ] 目录覆盖 59 实体 + 4 投影实体，字段约束来自 shapes
- [ ] SHACL 闸正反例 ≥12 组通过
- [ ] `ai_query_logs` 迁移往返成功，`alembic check` 绿
- [ ] `check_ai_catalog.py` 入 gate，16 项全绿

### P1 出口
- [ ] 12 条验收问题全部符合预期（含 4 条必须拒绝：非法枚举/越界意图/注入/越权）
- [ ] 5 类高频问题（缺料、延期、库存、信用、应收）意图命中率 ≥90%，口径与文档 P1 出口一致
- [ ] 无 LLM 时功能完整；LLM 故障自动降级
- [ ] 溯源完整率 100%（缺证据即失败）
- [ ] 前端 mock 与真实后端对 401/403/200 行为一致
- [ ] `POST /chat` 前后业务表零变更
- [ ] C1 叙事文档完成，数字可复现

### P2 出口
- [ ] MCP 工具清单 = 只读意图清单，且无写工具
- [ ] 工作流建议不改变任何审批状态（单测证据）
- [ ] MES 映射项 100% 锚定本体类
- [ ] 本体扩面后全部本体门禁与生成物门禁绿

---

## 7. 风险登记册（跨阶段）

| ID | 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|---|
| R1 | 意图覆盖不足导致"问不到" | 高 | 体验差 | 以 12 条验收问题为最小集；未命中返回建议问题；按真实提问日志迭代（P2） |
| R2 | SHACL 误拒合法查询 | 中 | 功能不可用 | 只忽略未提供路径的 minCount；正反例回归；错误信息透出约束名 |
| R3 | 目录与真实列漂移 | 中 | 运行时 500 | 构建期失败 + 门禁；禁止懒校验 |
| R4 | 匿名读现状被误读为已做行级隔离 | 高 | 安全误判 | 文档明示"仅域/意图级"；D2 验收口径可执行 |
| R5 | LLM 输出被注入 | 中 | 越权/幻觉 | 封闭目录 + extra=forbid + 无 SQL 通道 + 数字回查 |
| R6 | 迁移遗漏 env/conftest 导入 | 中 | 门禁/测试失败 | 验收双卡点（alembic check + SQLite 建表） |
| R7 | 前端菜单/路由漏改 | 中 | 页面不可达 | vitest 断言 + tsc |
| R8 | 依赖版本不兼容（rdflib/pyshacl） | 中 | 服务启动失败 | 版本锁死 + W0.5 单测作为兼容性证据 |
| R9 | 审计表增长过快 | 低 | 性能 | 截断问题文本、只存摘要、按时间索引、归档策略单列 |
| R10 | 多实例下限流失效 | 低 | 限流不准 | 文档声明单进程局限；P2 视部署形态换集中式限流 |
