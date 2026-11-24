# DIERP AI 原生化 · 交付说明

- 文档版本：v1.0
- 日期：2026-11-24
- 适用对象：运维、实施、验收与使用 AI 助手/异常解读的业务角色
- 关联文档：`01-系统设计-DIERP-AI原生化.md`、`02-实施计划-DIERP-AI原生化.md`、`03-评审报告-DIERP-AI原生化.md`
- 证据口径：本文所有结论均来自本轮仓库代码、门禁与真实接口/模型调用记录；未取证的能力不写入本文。

---

## 1. AI 功能与启停开关

AI 能力全部挂在 `/api/ai/*`，统一由 19 个 `AI_*` 环境变量控制，读取入口只有 `backend/services/ai/config.py`。

### 1.1 开关层级

| 开关 | 默认 | 作用 | 关闭后的表现 |
|---|---|---|---|
| `AI_ENABLED` | `true` | 总开关 | `/api/ai/*` 全部返回 `503 AI_DISABLED` |
| `AI_CHATBI_ENABLED` | `true` | 问数 + 异常解读 | `/api/ai/chat`、`/api/ai/insights/dashboard` 返回 `503 AI_CHATBI_DISABLED`；本体检索接口仍可用 |
| `AI_LLM_ENABLED` | `false` | 启用外部/本地大模型 | 使用确定性解析与模板叙述，功能完整可用 |
| `AI_LLM_NARRATION_ENABLED` | `false` | 允许 LLM 润色叙述 | 叙述固定走模板 |
| `AI_LLM_ALLOW_EXTERNAL_DATA` | `false` | 允许把行级数据发给 LLM | 只发送聚合统计，敏感列被剔除 |
| `AI_SPARQL_ENABLED` | `false` | 开放只读 SPARQL | 接口返回未启用；即使开启也只在 schema 图执行 |

启停探针：`GET /api/ai/ping` 返回 `{ok, ai_enabled, chatbi_enabled}`，不触达本体，用于区分"功能关闭"和"本体加载失败"。

### 1.2 其余环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `AI_LLM_BASE_URL` | 空 | OpenAI 兼容端点；`http://host` 会自动补 `/v1` |
| `AI_LLM_MODEL` | 空 | 主模型名 |
| `AI_LLM_API_KEY` | 空 | 仅进请求头，不入日志/审计/异常 |
| `AI_LLM_TIMEOUT_SECONDS` | `20` | 单次 HTTP 超时 |
| `AI_MAX_ROWS` | `200` | 结果行上限（超出截断并标注） |
| `AI_MAX_QUESTION_CHARS` | `500` | 问题长度上限 |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` | 每用户每分钟请求上限 |
| `AI_QUERY_TIMEOUT_SECONDS` | `5` | 只读查询超时 |
| `AI_ONTOLOGY_CACHE_TTL_SECONDS` | `300` | 本体缓存 TTL |
| `AI_LOG_PROMPTS` | `false` | 是否把提示词写入审计（默认不写） |
| `AI_LOG_QUESTION` | `true` | 是否记录原始问题用于审计 |
| `AI_MCP_TOKEN` | 空 | MCP 工具层 Bearer token；为空时 MCP 接口一律 401（fail-closed） |
| `AI_MCP_ROLE` | `GENERAL_MANAGER` | MCP 调用身份角色，工具清单与执行权限均按此角色裁剪 |

启动期一致性校验（不满足即拒绝启动，避免运行时静默降级）：

1. `AI_LLM_ENABLED=true` 时必须同时配置 `AI_LLM_BASE_URL` 与 `AI_LLM_MODEL`；
2. 端点不是 `localhost/127.0.0.1/::1` 时必须使用 `https://`；
3. 端点指向公网但 `AI_LLM_ALLOW_EXTERNAL_DATA=false` 时拒绝启动。

### 1.3 权限

- AI 访问域为 `ai`，角色白名单来自本体生成物 `security.ttl → authorization.generated`，未声明时 fail-closed（403）。
- 问数结果按意图的 `output_fields[role]` 裁剪；金额类字段对无权限角色返回掩码，并在响应中标记 `amount_masked=true`。
- 异常解读的 MRP 清单沿用 `open_mrp_exceptions` 的角色白名单；无权限角色看不到该清单。

---

## 2. 密钥注入方式（不落盘明文）

- 后端只从环境变量 `AI_LLM_API_KEY` 读取密钥；密钥只写入 HTTP `Authorization` 头。
- 密钥不写入数据库、不写入审计表、不写入异常信息；`AI_LOG_PROMPTS` 默认 `false`，提示词默认不入库。
- 免费网关场景：网关自身的统一密钥保存在网关容器的 sqlite 中，由网关进程读取；DIERP 侧通过部署环境变量注入同一密钥，仓库与 `.env` 示例中不保存明文。
- 本地网关允许空密钥（客户端不发 `Authorization` 头）；公网端点必须使用 https 且显式开启外发数据开关。

---

## 3. 免费网关的配额与 429 行为

免费网关是共享上游，**没有固定配额保证**；当所有可用模型都在限流或冷却期时，网关返回 HTTP 429。

DIERP 侧的实际处理（`backend/services/ai/llm.py`）：

1. 单次 `complete` 最多 2 次 HTTP 尝试（首次 + 1 次重试）；
2. 收到 429 或 404（上游模型失效）时短暂退避，然后按 `/v1/models` 自动发现备选模型；备选最多 3 个，跨族模型优先（同族常共用配额，429 往往一起命中）；`auto`/`fusion`/`claude-*` 这类路由别名不进入自动备选；
3. 仍失败则抛 `LLMError`，由调用方完整降级到模板，**不阻断问数与异常解读主链路**；
4. 响应记录 `narration_source`（`llm`/`template`）与实际 `model`，便于判断本次是否真的用了模型。

实测记录（2026-11-24 早前一轮真实模型调用，同一代码路径）：

- 主模型 `gemini-3.5-flash-lite`；首次调用返回
  `LLMHTTPError 429: All models exhausted: 1 route checked (1 rate-limited or on cooldown). Soonest reset ~74s`；
- 接口按设计降级，`narration_source=template`，功能可用；
- 等待约 95 秒后重试成功，实际使用跨族兜底模型 `flint-v1.0`，`narration_source=llm`，数字回查通过。

结论：429 是免费网关的常态风险，不等同于功能故障；页面会继续展示模板解读。

---

## 4. 降级链路的实际表现

### 4.1 问数（`POST /api/ai/chat`）

1. 规则/确定性解析器把问题映射到 7 个只读意图之一，参数做类型与权限校验；
2. 只读 SQL 查询业务库，SHACL/形状校验与行数、超时限制生效；
3. 模板生成叙述（计数、合计、比例），数字必须来自结果集；
4. 若开启 LLM 润色：只把已算好的结论交给 LLM 转述，LLM 不得计算或改变判定；返回文本需通过数字回查，否则回退模板。

### 4.2 异常解读（`GET /api/ai/insights/dashboard?window=7d|30d`）

1. 汇总 6 个驾驶舱 KPI 与 MRP 异常，生成结构化告警（当前值、阈值、偏离、关联单据、下钻路径、归因、建议）；
2. 模板叙述优先且始终可用；
3. LLM 只润色已算好的告警；数字回查不通过、超时、429、响应不可解析等任何失败都回退模板；
4. 返回 `narration_source`、`model` 与告警明细，页面据此展示，不因 LLM 失败而报错。

### 4.3 枚举展示

- 枚举中文标签唯一来源：`ontology/src/mappings.json` 的 `labels` → 重新生成 `ontology/generated/types.ts`（`ENUM_LABELS`）。
- 异常解读的告警标题、归因、严重度、叙述、LLM 输入均已使用中文标签；问数结果表的枚举列由前端按意图 `output_enums` 渲染中文标签。
- 后端结构化字段（如 `severity`）仍保留枚举码，供程序化消费；用户可见文案不再出现 `SHORTAGE`、`CRITICAL`、`RAW` 等码值。

---

## 5. 已知限制与风险

### 5.1 数据出域边界

- 默认 `AI_LLM_ALLOW_EXTERNAL_DATA=false`：只发送聚合统计（count/sum/min/max）与已脱敏的告警事实，不发送记录键、客户标识/名称、物料编码和任何金额列；金额类建议使用掩码文案。
- 开启该开关后才会发送行级明细；公网端点还必须使用 https，否则服务拒绝启动。
- **"本机地址"不等于"数据未出域"**：`localhost` 上的免费网关仍可能把请求转发到公网上游。DIERP 只能约束"发给网关的内容"和"端点协议"，无法保证网关自身的上游行为；对数据出域有硬性要求时，应使用完全本地部署的模型端点并关闭公网转发。
- 审计默认记录问题与结果元数据，不记录提示词；需要排障时再临时开启 `AI_LOG_PROMPTS`。

### 5.2 能力边界

- 只读：7 个意图全部为只读；不提供任何写操作。审计日志与反馈（`POST /api/ai/queries/{trace_id}/feedback`）是唯一写入。
- 不生成 SQL：问题只能映射到注册表内的意图，未命中即返回受控错误，不做自由 SQL。
- LLM 不参与计算与判定；它只做转述，数字回查失败即回退模板。
- 免费网关无 SLA：可能 429、超时或模型下线；降级链路保证功能可用，但叙述质量会降为模板。
- SPARQL 默认关闭；开启后也只在剔除了 JWT 配置的 schema 图上执行，并强制 `LIMIT`。
- 本次枚举标签统一覆盖 AI 异常解读与 7 个问数意图的输出列；其它业务页面既有的标签体系不在本次范围内。

### 5.3 运行与部署

- 测试使用 SQLite 内存库；生产为 PostgreSQL，SQL 未使用 PG 专有语法。
- 查询超时 5 秒、行数上限 200；超限会截断并在回答中标注。
- LLM 调用为同步阻塞，超时 20 秒；网关慢时会延长单次请求耗时，但不会影响其他接口。

---

## 6. P2 扩展：MCP 只读工具层与 ERP↔MES 语义映射 v1

### 6.1 MCP 工具层（`POST /api/ai/mcp`）

- 协议：JSON-RPC 2.0 子集，支持 `initialize`、`ping`、`tools/list`、`tools/call`；`protocolVersion=2024-11-05`。
- 鉴权：`Authorization: Bearer <AI_MCP_TOKEN>`，不依赖登录会话；token 未配置或错误返回 401，不做匿名开放。
- 工具清单：7 个只读意图，按 `security.ttl` 的 `AccessDomain`（`:anonymousRead`/`:readRole`）与意图 `allowed_roles` 派生；每个工具 `readOnlyHint=true`、`destructiveHint=false`。
- 读写边界：写方法清单（`POST/PUT/PATCH/DELETE`）来自 `security.ttl`；工具层不注册任何写意图，门禁会校验"工具集 = 只读意图集"且所有域已在 `security.ttl` 声明。
- 执行：复用 REST 的同一套参数绑定、SHACL、权限、只读查询与审计；返回 `structuredContent`（含 `data/provenance/limits`）与文本 `content`。
- 审计：`username = mcp:<sha256(token)[:12]>`，token 明文不落库、不写日志。
- 外部调用接入：把网关指向 `http://<host>:<port>/api/ai/mcp`，在请求头带上 Bearer token 即可。

### 6.2 ERP↔MES 语义映射 v1（`GET /api/ai/semantics/mes`）

- 映射文件：`ontology/model/mes-mapping.yaml`，v1 覆盖 6 个 MES 实体（Equipment、WorkOrder、Operation、Material、InspectionOrder、Warehouse）。
- 每个映射项必须指向既有本体类与既有属性；`ontology_class`、属性名、枚举名和码值全部在门禁中校验，缺失即失败。
- 枚举对照只使用 `mappings.json` 中已声明的码值（如 `MaterialType`、`ResourceStatus`、`DocumentStatus`、`ScheduleOpStatus`、`InspectionType/Result/Status`）。
- 未覆盖的 MES 实体显式进入 `unmapped`（v1 为 `ScrapRecord`），不做猜测性映射；当前覆盖率 6/7 = 85.71%。
- 接口只读，返回 `{version, source_system, items, unmapped, coverage, problems}`；`problems` 非空时接口返回 503，不输出半可信映射。

---

## 7. 本轮验证结果（实际执行）

| 验证项 | 命令 | 结果 |
|---|---|---|
| 后端测试 | `python -m pytest backend/tests -q` | 218 passed |
| 后端门禁 | `python backend/scripts/gate.py` | 16 项全部 PASS，失败 0 |
| 意图元数据漂移 | `python backend/scripts/export_ai_intent_meta.py --check` | 一致（7 个意图） |
| AI 语义目录门禁 | `python backend/scripts/check_ai_catalog.py` | 通过（含输出枚举标签、MCP 边界、MES 映射） |
| 本体生成物 | `python ontology/scripts/generate-types.py --check` | 一致 |
| 本体双栈同步 | `node ontology/scripts/validate-type-sync.js` | 全部通过（含 `ENUM_LABELS` 一致性） |
| 前端类型 | `npx tsc --noEmit` | 通过 |
| 前端 lint/测试/mock/构建 | 门禁内 eslint、vitest、mock RBAC、mock handlers、build | 全部 PASS |

真实模型验证沿用 2026-11-24 早前一轮的同路径实测：首次 429 降级模板，重试成功使用 `flint-v1.0`，数字回查通过。本轮未重复消耗免费配额，结论以该实测与本轮模板/降级测试为准。
