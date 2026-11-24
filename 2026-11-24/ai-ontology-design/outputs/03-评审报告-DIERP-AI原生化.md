# DIERP AI 原生化 · 评审报告

- 文档版本：v1.0
- 日期：2026-11-24
- 评审对象：
  - `01-系统设计-DIERP-AI原生化.md`（下称"设计"）
  - `02-实施计划-DIERP-AI原生化.md`（下称"计划"）
- 评审方式：逐条复核两份文档的断言，回到仓库代码/本体/门禁与生成链路取证；对文档中的数据类断言用一次性脚本复算（脚本位于 `work/`，非交付物）。
- 结论：**3 项阻断、12 项重要、12 项建议**。方向（本体做查询契约、AI 不生成 SQL、四层校验）成立；但 P0 的"新增访问域"改动面被显著低估、目录合并前提在 6 个 YAML 实体上不成立、SHACL 闸示例代码不可执行；P1 的 13 条验收中有多条按当前设计无法通过，安全叙事存在过度承诺。建议按第五节顺序修补后再进入编码。

---

## 0. 分级定义

| 级别 | 含义 |
|---|---|
| **阻断** | 按文档实施会直接撞既有门禁、或设计自述的能力无法实现；不修复则 P0/P1 出口不成立 |
| **重要** | 不阻断编译/门禁，但会造成安全承诺落空、语义错误、验收不可判定或返工 |
| **建议** | 成本/收益或口径问题，可在对应工作项内顺带处理 |

---

## 1. 阻断

### B1 `ai` 访问域的真实改动面是 5 个文件 + 3 份生成物，而非"security.ttl 7 行"

**问题**
设计 §0 第 5 点（`01:21`）与 §11.2（`01:785-786`）称"安全策略只改 `security.ttl` 7 行并重新生成双栈产物（生成器与 parity 脚本零改动）"；计划 W0.2 的文件清单（`02:68-69`）同样只列 `security.ttl` + 两份生成物。实际 `ai` 是**封闭枚举**的新值，至少还要改 `shapes.ttl` 与 `mappings.json`，否则本体门禁必失败。

**证据**
- `ontology/src/shapes.ttl:1159-1163`：`:AccessDomainShape` 对 `:domainCode` 使用硬编码 `sh:in`，共 14 个域，不含 `ai`。
- `ontology/src/mappings.json:63`：`AccessDomain` 枚举 14 个值，不含 `ai`。
- `ontology/scripts/validate-consistency.py:39`：`security.ttl` 被列入 `DATA_TTLS`；同文件 `:100-105` 用 `shapes.ttl` 对其做 `pyshacl` 校验。新增 `:DOMAIN_AI` 会触发 S48（"访问域编码必须来自 AccessDomain 枚举"）。
- `ontology/scripts/validate-type-sync.js:96`：用 `AccessDomainShape` 反向校验 `AccessDomain` 枚举；只改一处必然失败。
- `ontology/generated/types.ts:121`：`AccessDomain` 联合类型；`backend/scripts/gate.py:29` 运行 `generate-types.py --check`。
- 计划 W0.2 验收第 5 条（`02:78`）还明确要求"`validate-type-sync.js` 与 `validate-consistency.py` 仍绿"——这与它的文件清单自相矛盾。

**影响**
W0.2 按文档实施会连续触发 3 条门禁（`validate-consistency`、`validate-type-sync`、`generate-types --check`），P0 出口"`ai` 域双栈策略一致"不成立，且失败信息（S48）会被误判为本体损坏而非变更遗漏。

**修改建议**
1. 把 W0.2 的文件范围改为 5 处：`ontology/src/security.ttl`、`ontology/src/shapes.ttl`（`:1162` 加 `"ai"`）、`ontology/src/mappings.json`（`AccessDomain` 加 `"ai"`）、`ontology/generated/types.ts`（`generate-types.py` 重新生成）、`backend/common/utils/security_policy.py` + `frontend/src/types/authorization.generated.ts`。
2. 验收增加 `python backend/ontology/generate-types.py --check` 与"三验证器全绿"的显式断言。
3. 把设计 §0 第 5 点改为准确描述（"本体侧 3 个文件 + 3 份生成物"），避免后续评审按"仅 7 行"估算风险。
4. 若坚持零本体改动，则只能放弃新增访问域、在 `require_ai_access` 内写死角色集合；但这与源文档 D2（权限来自本体）冲突，需产品决策，不能静默采用。

---

### B2 目录合并的"camel→snake 确定性"前提在 6 个 YAML 实体上不成立

**问题**
设计 §5.2（`01:241`）称"snake↔camel 对 59 个 YAML 实体是确定性的"，并只把 `SalesOrderShape`/`ProductionOrderShape` 视为遗留形状的特例，用**仅限投影文件**的 `rdf_overrides` 处理（`01:243-245`、`01:249-283`）。实测有 9 个 NodeShape 使用抽象路径 `documentNumber`/`dueDate`，其中 **6 个是 YAML 托管实体**，其物理列名都不是 `document_number`，且 YAML 实体没有任何 override 通道。

**证据**
- 对 `shapes.ttl` 与 `ontology/model/*.yaml` 的交叉统计（`work/review_shapes.py`、`work/review_shape_fields.py`）：

| 本体类 | 表格 | 形状使用的抽象路径 | 实际首列 | 是否有 `document_number` |
|---|---|---|---|---|
| Forecast | `forecasts` | `documentNumber` | `forecast_number` | 否 |
| MpsPlan | `mps_plans` | `documentNumber` | `mps_number` | 否 |
| MrpRun | `mrp_runs` | `documentNumber` | `run_number` | 否 |
| PlannedOrder | `planned_orders` | `documentNumber` | `planned_order_number` | 否 |
| PurchaseOrder | `purchase_orders` | `documentNumber` | `purchase_order_number` | 否 |
| ScheduleRun | `schedule_runs` | `documentNumber` | `run_number` | 否 |
| ProductionOrder | `production_orders` | `documentNumber` | `order_number` | 否（已有 override） |
| SalesOrder | `sales_orders` | `documentNumber`/`dueDate` | `order_number`/`delivery_date` | 否（已有 override） |
| BOM | `boms` | `documentNumber` | —（既无 YAML 也未纳入投影） | — |

- `shapes.ttl:69/91/108/155/182/251/269/343/644` 为上述抽象路径的出处。
- 设计 §5.2 第 4 步（`01:233-237`）要求"投影字段必须在 `Base.metadata` 中存在，缺失即构建失败"；`rdf_overrides` 的定义只出现在投影文件（`01:261-265`），YAML 实体无此字段。
- `ontology/scripts/validate-consistency.py` 的 Check5 只校验"每个 YAML 实体有 NodeShape"，不校验路径与列名对应，因此这个问题不会被既有门禁提前发现。

**影响**
`check_ai_catalog.py` 要么在这 6 个实体上构建失败（违反"缺失即失败"），要么把 `document_number` 当作新字段加入目录、随后被"列存在"校验拦下；若实现者选择"警告并跳过"，这 6 个实体的必填/枚举约束会被静默丢弃——恰好 `order_delay_risk` 依赖的 `planned_orders`/`purchase_orders` 都在其中。P0 出口与"约束来自本体"的核心主张同时落空。

**修改建议**
1. 把 `rdf_overrides` 从"投影专用"提升为**实体级通用能力**：YAML 实体也可声明 `rdf_overrides`，由 `check_ai_catalog` 断言"值为形状真实使用的 path、键为实体真实列"。
2. 不用全局别名表：`MrpRun` 与 `ScheduleRun` 都映射 `run_number`，全局别名会串表，必须按实体声明。
3. W0.4 验收增加"未命中形状路径 = 0"，并在文件清单里列出上述 6 个实体的期望映射；同时把 BOM 明确标注为"不进入目录"。
4. 设计 §5.2 的"确定性"表述改为"camel→snake 对多数实体成立；抽象命名由实体级 `rdf_overrides` 兜底，未覆盖即构建失败"。

---

### B3 §5.4 的 SHACL 闸示例代码不可执行，且与仓库既有正确用法矛盾

**问题**
设计 §5.4（`01:294-312`）给出的闸门实现有三处硬错误：返回值解包错误、`FieldMeta` 不存在 `datatype_iri`、`shape_path_set`/`shapes_graph` 为未定义符号。按文档照抄无法通过 W0.5 的第一条正例。

**证据**
- `pyshacl.validate()` 返回 `(conforms, results_graph, results_text)`；设计写 `_, _, report = validate(...)` 后对 `report.subjects(...)` 迭代——第三个返回值是字符串，`str` 没有 `subjects`。仓库内正确用法见 `ontology/scripts/validate-consistency.py:103`（`conforms, results_graph, _ = validate(...)`）。
- 设计 `FieldMeta` 字段清单（`01:191-210`）只有 `name/db_name/rdf_name/data_type/enum/required/...`，没有 `datatype_iri`；而 `01:308` 直接使用 `field.datatype_iri`。若为了跑通而把枚举类 IRI 当 datatype，`Literal` 的 datatype 与 `sh:in` 的 `xsd:string` 不匹配，会导致**全量误拒**。
- `01:304-306` 的 `shape_path_set(entity.shape_iri)` 与 `shapes_graph` 未在管道中定义/传入。
- 同段注释"`advanced=True` 关闭 OWL 推理"也把两个无关参数混为一谈（`inference="none"` 才是关闭推理）。

**影响**
W0.5 无法按文档编码；若实现者自行"猜"返回值和 datatype，最可能的两种结果是运行时崩溃或所有枚举参数被拒，而两者都会被误读为"闸门生效"。

**修改建议**
1. 给出可执行版本：`conforms, results_graph, _ = validate(...)`；遍历 `results_graph` 时按 `SH.resultPath`/`SH.resultMessage` 提取。
2. 明确 datatype 映射表：`string/enum → xsd:string`、`int → xsd:integer`、`decimal → xsd:decimal`、`bool → xsd:boolean`、`datetime → xsd:dateTime`，枚举一律字符串，不使用类 IRI。
3. `shacl_check(entity, params, shape_paths, shapes_graph)` 显式传参，或由 `catalog` 提供 `EntityMeta.shape_paths`。
4. W0.5 单测至少覆盖：合法枚举通过、非法枚举 `InConstraintComponent`、未提供路径不误报、`skipped` 状态返回 `skipped` 而非 `passed`。

---

## 2. 重要

### I1 审计写入不会持久化，`request_id` 关联也无法实现

**问题**
设计 §7.3 第 10 步（`01:584`）与 §9.1 要求把问答写入 `ai_query_logs`，并用 `request_id` 关联 `operation_logs`（`01:707`）；但仓库的 `get_db()` 不提交事务，且 `pipeline.ask()` 的签名拿不到请求上下文。

**证据**
- `backend/common/database/base.py:59-65`：`get_db()` 只 `yield db`，无 `commit`；既有写服务均显式 `db.commit()`。
- 设计 `01:147`：`pipeline.ask(question, user, db)`；`01:584` 的审计是管道内一步；`01:707` 声称与 `operation_logs.request_id` 关联。
- `backend/api/main.py` 的审计中间件在请求结束后写 `operation_logs`，`request_id` 只存在于 `Request` 上。

**影响**
审计行会随会话关闭回滚——D3 的实际目标（可追溯问答）完全落空；W1.2 验收第 5 条"可关联"无法实现。该问题在 SQLite 测试中同样复现，但只有"查库断言"才能发现，`status=OK` 的响应断言发现不了。

**修改建议**
- 管道显式 `db.commit()`（或使用独立 `SessionLocal()` 写审计，避免与只读事务耦合）；异常路径先 `rollback` 再写。
- 把 `request_id: str` 作为 `ask()` 的显式参数由路由注入；`trace_id` 由管道生成并写响应。
- W0.6/W1.2 验收增加"请求结束后重新开 session 能查到该行"与"403/422 请求也落审计"。

---

### I2 "四道闸全部 fail-closed"名不符实

**问题**
设计 §0 第 3 点（`01:15`）与 §3 原则 3 称四道闸全部 fail-closed；但 SHACL 闸对 3/7 个意图是 `skipped`、对 2 个是 `partial`（`01:499-505`），"数据域闸"在现状下对所有业务域直接放行（`01:438-440` 自述）。

**证据**
- `01:499-505`：`customer_credit_status` 无形状；`order_delay_risk`、`open_mrp_exceptions` 的参数不在形状覆盖内；`ar_overdue` 的 `days_overdue` 无覆盖。
- `01:438-440`：域闸明确"现状下业务域均开放"，等于恒真。
- `backend/common/utils/security_policy.py`：`READ_OPEN_DOMAINS` 含 11 个业务域，`READ_ROLE_POLICY` 仅 3 个。

**影响**
安全评审与验收会按"四闸都拦"设计负例，实际只有 pydantic 与意图角色白名单是硬控制；`skipped` 被当作 `passed` 会在回答里产生"已通过约束校验"的错误安全感。这是对 D2 承诺的实质性削弱。

**修改建议**
- 把叙事改为"两层硬控制（参数模式、意图角色）+ 一层覆盖式约束校验（SHACL，按意图声明覆盖度）+ 一层完整性检查（溯源）"。
- 在 `check_ai_catalog`/`IntentSpec` 中显式声明 `shacl_coverage: full|partial|none`，并让响应回传真实状态；`skipped` 必须在验收中作为合法值断言，不能写死 `passed`。
- 若要真正 fail-closed，需为剩余意图补 NodeShape（属于本体扩面，建议列入 P2 W2.4 而非 P0 承诺）。

---

### I3 13 条验收问题中有 5 条按当前设计无法通过或语义错误

**问题**
附录 A 的 13 条被写成 P1 出口的硬标准（`01:853-871`），但确定性解析器的触发词表、状态默认值与错误码分类不足以支撑其中多条。

**证据**
1. **#2**（`01:860`）要求从"PO-20261120-0007 齐套了吗"抽取单号；`01:466` 的触发词只有 `客户 {id}`、`类型 {token}`、`{N} 天内/以上`、`CRITICAL`、`SHORT`，**没有单号正则**，`kitting_shortage` 的 `source_ref` 无法被填。
2. **#5**（`01:863`）"哪些原材料低于安全库存"要求"原材料→RAW"；设计没有同义词表，`material_type` 只会得到字面 token。
3. **#7**（`01:865`）"还有哪些 CRITICAL 的计划异常"语义是"未处理"，但 `open_mrp_exceptions` 的参数只有 `severity/exception_type/limit`（`01:494`），没有 `resolution_status`；模型里该列存在（`backend/common/models/planning.py:682`），不筛就会把 RESOLVED/IGNORED 一起返回。
4. **#13**（`01:871`）"没关闭的质量异常"同理：`status` 无默认值，缺省返回含 CLOSED 的全部 NCR；中文"没关闭"也没有映射规则。
5. **#11**（`01:869`）期望 `REJECTED_SCHEMA`，但 LLM 关闭时自然路径是无意图 → `AI_INTENT_UNKNOWN`（`01:596-604`），两者在 §9.3 的审计状态集合里也缺一项。

**影响**
P1 出口"13 条全部按预期通过"无法达成；演示会出现"问 A 答 B"或"把已解决异常算作待办"，直接损害可信度。若为了让测试变绿而在测试里放宽断言，验收就失去意义。

**修改建议**
- 在 §7.1 增加**显式规则表**（每意图一节）：单号正则（`^(SO|PO|WO)-...`）、同义词（原材料→RAW、成品→FG、半成品→SEMI、包装→PACKAGING）、状态词（未关闭/未处理→OPEN、已审核→UNDER_REVIEW）、时间词（本周→本周一 00:00 起）。
- 把 `resolution_status=OPEN`、`status in (OPEN, UNDER_REVIEW, DISPOSITIONED)` 写进意图默认参数。
- 在管道第 1 步后增加"schema/DDL 关键词"前置分类，命中即 `REJECTED_SCHEMA`，再进入意图匹配。
- 把 #11 改为两条：规则模式下断言"无意图 + 不产生 SQL"；LLM 模式下用 stub 返回越界 JSON，断言 schema 闸拒绝。
- 附录 A 的示例答案（`01:643` 的"缺 12 PN"）改用 W1.6 fixture 数据，或明确标注"示意，非仓库种子"。

---

### I4 三个核心意图的取数口径未定义到可编码

**问题**
`order_delay_risk`、`customer_credit_status`、`ar_overdue` 是全篇最"像业务"的三个意图，但只给了参数与类型，没有给状态集合、金额符号、分母与空值策略；参考实现里还存在明显语义错误。

**证据**
- `order_delay_risk`（`01:542-562`）：状态集合含 `SHIPPED`（`backend/common/models/sd.py` 的 `SalesOrderStatus` 中 SHIPPED 表示已发货），与"还没完工"矛盾；注释称"计划完工晚于交付日"，但代码没有使用 `planned_finish_date`（`backend/common/models/pp.py` 中存在该列）；无生产订单的订单未处理。
- `customer_credit_status`（`01:495-496`）：应收余额如何由 `receivable_entries` 的 `INVOICE/RECEIPT/ADJUST/INVOICE_REVERSE/RECEIPT_REVERSE` 汇总、未完成订单取哪些状态、占用比分母是什么，全部未定义。
- `ar_overdue`（`01:496`）：没有排除 `PAID/CANCELLED`，也没有用 `received_amount < amount` 处理部分收款；两列都在模型里（`backend/common/models/planning.py:1498-1500`）。
- 设计 §7.6 的 Agent 守则（`01:567-569`）只约束"怎么写 SQL"，没有约束"业务口径"。

**影响**
不同实现者会给出不同数字；C1 的 ROI 叙事失去可比口径；验收只能断言"有行"，无法断言"数字对"。

**修改建议**
- 为每个意图增加"取数口径"小节：允许状态、金额符号（`INVOICE +`、`RECEIPT -`、`ADJUST ±`、`*_REVERSE` 取反）、时间基准（本地时区）、分母、空值处理。
- `order_delay_risk` 状态改为 `APPROVED/IN_PRODUCTION`，并加入 `planned_finish_date > delivery_date` 或"无生产订单"作为风险条件。
- `ar_overdue` 明确 `status NOT IN (PAID, CANCELLED)` 且 `received_amount < amount`。
- 在 `IntentSpec` 上增加文档级 `formula` 字段，供 C1 与前端说明引用（不要求代码实现）。

---

### I5 LLM 数据出境与源文档的硬约束冲突，且无技术控制

**问题**
源文档明确"严禁把生产数据发给公有云 API"（`docs/DIERP-AI-ERP提升方案-深度研究-20261124.md:163`）；设计允许任意 `AI_LLM_BASE_URL`，并在润色时把 `rows`（生产数据）序列化后发送（`01:591`），没有任何"仅内网/自托管"的校验或开关；W1.5 的 LLM 解读也没有对应验收。

**证据**
- `01:591`："把 `rows` 以 JSON 传入"。
- `01:809-813`：`AI_LLM_BASE_URL/API_KEY/MODEL` 无 host 限制；`AI_LLM_NARRATION_ENABLED` 只控制开关，不控制去向。
- W1.5（`02:230-238`）只验收"模板兜底"，不验收"出境边界"。

**影响**
一条配置就可能让客户名、金额、信用额度出境，属于合规红线；且该风险不会在离线测试中暴露。

**修改建议**
- 增加 `AI_LLM_ALLOW_EXTERNAL_DATA`（默认 `false`）：为 `false` 时校验 `AI_LLM_BASE_URL` 的 host 必须在内网/回环/显式白名单，否则启动失败或 `/chat` 返回 403。
- 润色只传"聚合值与字段白名单"（例如仅 `count/sum/名称`），不传整行；`AI_LLM_NARRATION_ENABLED` 默认保持 `false`。
- W1.5 增加验收：外部 URL + 未开启开关 → 拒绝；开启后日志含"已脱敏字段清单"。

---

### I6 没有单次查询的执行时长闸，且"超时"承诺无配置支撑

**问题**
设计把"超时"写进执行器职责（`01:176`），但 §12 的 12 个环境变量（`01:805-818`）没有查询超时项；§13 又明确"不得使用 `SET LOCAL statement_timeout`"；`AI_MAX_ROWS` 只限制返回行数，不限制执行时间。

**证据**
- `01:176`（执行器职责含"超时"）与 `01:805-818`（无 `AI_QUERY_TIMEOUT`）矛盾。
- `01:521`：`material_below_safety` 用 `current_stock < safety_stock` 过滤并按差值排序，两列无索引时会全表扫描 + 排序。
- `01:569` 只承诺 `limit()` 与 `AI_MAX_ROWS` 截断。

**影响**
慢查询会占满 worker；限流只限 QPS，不限单次耗时；P1 演示在真实数据量下可能超时，而文档无法解释。

**修改建议**
- 增加 `AI_QUERY_TIMEOUT_SECONDS`（默认 5），按方言实现：PG 连接级 `statement_timeout`、SQLite 用线程/语句中断；或统一用 `ThreadPoolExecutor + future.result(timeout)` 并在超时后回滚。
- 为 `materials.safety_stock/current_stock`、`sales_orders.delivery_date`、`sales_invoices.due_date` 评估索引；在 W1.2 加"超时 → `AI_EXECUTION_TIMEOUT`（504）"的验收。
- 在 §12 明确"超时"的落地方式，删除 §13 与 `01:176` 的矛盾。

---

### I7 计划与设计的计数、文件清单、字段名仍有多处不一致

**问题**
两份文档在 7 个意图加入后未完全同步；按当前文本验收会得到互相矛盾的口径。

**证据**
| 位置 | 现状 | 应为 |
|---|---|---|
| `02:60` | "11 个环境变量" | 设计 §12 共 12 行 |
| `02:229` (W1.4) | "6 类问题" | 7 个意图 / 6 类业务问题 |
| `02:255`、`02:261` (W1.6) | "12 条验收问题" | 13 条 |
| `02:284` (W2.1) | "6 个意图" | 7 个 |
| `02:485` (P1 出口) | "5 类高频问题（缺料、延期、库存、信用、应收）" | 6 类（加质量） |
| `02:504` (R1) | "12 条验收问题" | 13 条 |
| `02:388-389` (文件清单) | 无 `intents/quality.py` | W1.1 `02:172` 已含 |
| `01:16` | "4 处文档前提需修正" | §2 为 K1–K5 共 5 行 |
| `01:787` | "新增 5 个测试文件" | 计划实际约 10 个测试文件 |
| `01:654` | `provenance.filters: {"status":"SHORT"}` | 实际参数为 `kit_status`（`01:644`） |

**影响**
评审/交接会按旧数字验收；文件清单漏项会导致 W1.1 交付不完整；`status/kit_status` 混用会让实现者写错字段名。

**修改建议**
以"7 意图 / 13 条验收 / 6 类业务问题 / 12 个环境变量"为唯一口径全文替换；文件清单补 `quality.py` 与 B1 的 4 个文件；`01:654` 改为 `kit_status`。

---

### I8 `EntityMeta` 缺 `domain`，`IntentSpec.entity` 单值无法表达跨表意图

**问题**
设计的目录契约（`01:191-217`）没有 `domain` 字段，但响应示例返回 `"domain":"planning"`（`01:682`），`check_ai_catalog` 还要求校验域。另一方面 `IntentSpec.entity: str`（`01:473-485`）与 `shacl_check(entity, params)`（`01:294`）只支持单实体，而意图 2 写的是"`SalesOrderShape` + `ProductionOrderShape`"（`01:492`）。

**证据**
- `01:191-217`（FieldMeta/EntityMeta 字段）；`01:682`（响应含 domain）；`01:438-440`（域闸依赖意图手工声明的 domains）。
- `ontology/model/planning.yaml` 无 `domain` 字段；同一文件同时包含计划与财务实体（`SalesInvoice`/`ReceivableEntry`），按文件推导域会把财务实体标成 planning。
- `01:492` 与 `01:294` 的单实体签名冲突。

**影响**
目录无法输出可信的实体域，`check_ai_catalog` 的域校验只能退化为"意图域合法"，与原则 2"权限域来自本体/YAML"不符；跨表意图的 SHACL 覆盖范围不确定。

**修改建议**
- `EntityMeta` 增加 `domain`；投影显式声明，YAML 增加可选的实体级 `domain`（缺省可按文件推导，但需在文档中标注推导规则与例外清单）。
- `IntentSpec` 改为 `entities: list[str]` + `primary_entity: str`，明确 SHACL 只对 `primary_entity` 或列出的实体集合执行；同步修正 `shacl_check` 签名。

---

### I9 事件型实体没有稳定单据号，溯源闸只能"形式通过"

**问题**
第 8 步要求"每条 row 有 `record_ref`，缺失即整条失败"（`01:582`），下钻映射按 `record_ref` 跳转（`01:760`）；但 `mrp_exceptions` 没有单据号列。

**证据**
- `backend/common/models/planning.py:660-682`：`MrpException` 只有 `run_number/material_code/exception_type/...`，无 `exception_number`。
- `01:582` 与 `01:760` 的"可点击下钻"隐含 `record_ref` 是全局唯一单据号。

**影响**
实现者只能用 `id` 或拼接键，前者不可读、后者不可跳转；C1 宣称的"100% 可溯源"无法验证（只能验证"字段非空"）。

**修改建议**
- 在 `IntentSpec` 中为每个实体声明 `record_key`（单据号 / 复合键 / `id`）与 `downlink`（可为 `null`）。
- `mrp_exceptions` 使用 `run_number + material_code + exception_type` 展示，`downlink` 指向 MRP 运行详情而非单据详情；验收改为"溯源信息可展示且可定位到运行批次"。
- 明确 `provenance_kind=summary` 时的 `sources` 至少包含"表名 + 统计时间 + 口径"。

---

### I10 未定义字段最小化与跨客户可见性，D2 的"无权限数据不可见"无验收

**问题**
`order_delay_risk` 允许 `SALES`/`PLANNER`（`01:492`），但 `SalesOrder` 含 `unit_price/total_amount`（`backend/common/models/sd.py:361-362`），且没有 salesperson/owner 列可做行级过滤；设计只在 §13 声明"不做行级权限"，未给出字段级约束。

**证据**
- `01:492`（角色矩阵）、`01:502`（返回字段未列举金额是否排除）。
- `backend/common/models/sd.py:361-362`：`unit_price`、`total_amount` 等商业敏感列。
- `01:6`（D2 验收口径"无权限数据不可见"）在附录 A 中没有对应测试。

**影响**
AI 可能把"全客户订单金额"以自然语言直接呈现给销售，形成比列表页更易消费的泄露面；即便现状 REST 匿名可读，也不能用"不新增"作为未验收的理由。

**修改建议**
- 为每个意图定义输出列白名单（默认排除金额类；`FINANCE/SALES_MANAGER` 才允许金额）。
- 在 D2 验收中写可验证命题："同一角色下，AI 返回的字段集合 ⊆ 该角色可访问的 REST 字段集合"，并加一条对比测试。
- 若业务要求销售只看自己客户，需先给 `sales_orders` 增加归属列，再谈行级过滤；本次应明确"不做"，并在 UI 加"数据范围为全公司"提示。

---

### I11 P0 的检索验收 `search("库存")` 在本体文本中命中不了 `Material`

**问题**
W0.3 验收第 2 条（`02:91`）要求 `search("库存")` 命中 `Material`；但按设计 `01:347` 的检索范围（类标签、注释、类名、枚举值），`Material` 的标签/注释里没有"库存"。

**证据**
- `ontology/src/erp-ontology.ttl:42-43`：`Material` 的 `rdfs:label "物料"`、`rdfs:comment "原材料、半成品、成品、包装材料与服务性物料的统一抽象。"`，不含"库存"。
- `ontology/src/erp-ontology.ttl:227-230`：DatatypeProperty 没有 `rdfs:label`。
- "库存"实际出现在 `:63/:65/:102/:461` 的注释/标签（采购退货、销售发货、PlanningPolicy、InventoryValuation）。

**影响**
P0 的唯一语义检索验收直接失败；若实现者为了过测把检索范围扩到字段注释，又会与 §5.5 的"只给意图清单，不给表结构"（`01:576`）冲突。

**修改建议**
- 给 DatatypeProperty 补 `rdfs:label`（本体改动，需过类型同步门禁），检索范围明确包含"字段标签/枚举 code"。
- 验收改为两条：`search("物料")` 命中 `Material`；`search("安全库存")` 返回非空且包含 `PlanningPolicy`/`Material`（按相关度排序断言）。
- 若不想改本体，则把该验收降级为"describe('Material') 可用 + search 返回非空"。

---

### I12 P1 的数据前提被排在 P3（C2），演示会出现"验收全绿但页面全空"

**问题**
源文档路线图把 C2（演示数据扩充）放在 P3（`docs/DIERP-AI-ERP提升方案-深度研究-20261124.md:209`），而 P1 的 7 个意图与 C1 ROI 叙事需要足够的非空数据；计划 W1.6 只用 pytest fixture 造数（`02:264`），`npm run dev:mock` 与真实 PG 的演示数据未纳入。

**证据**
- 源文档 `:207-209`（P1 验收"5 类高频问题"、C2 在 P3）。
- 计划 W1.6（`02:255-263`）：fixture 断言"结构而非具体业务值"。
- `PO-20261120-0007` 在仓库中只出现在设计文档，没有种子数据（全仓检索无命中）。

**影响**
13 条验收可以靠空结果"通过"，但 C1 的 ROI 数字、P1 演示与用户评审都拿不到有说服力的输出；验收与实际价值脱节。

**修改建议**
- 在 W1.6 增加"最小演示数据集"子项：7 个意图各至少 3 条有效记录，覆盖缺料/延期/低库存/异常/信用/应收/质量；数据进入 `backend/scripts/reset_demo.py` 与前端 mock。
- 或把 C2 的"最小集"提前到 P1，并在偏差表登记（与源文档 P3 的偏离）。
- 附录 A 的 `PO-20261120-0007` 改用该数据集中的真实单号，或标注"示意"。

---

## 3. 建议

### S1 SPARQL 端点与"无外泄面"的表述不成立；`demo.ttl` 前后矛盾
- **证据**：`01:344` 明确"不加载 `demo.ttl`"，`01:357` 却写"图内只有本体与 demo 实例"；同段称"不构成数据外泄面"，但设计 §5.1 把 `security.ttl` 载入图，其中含 JWT 配置（`secretKeyEnv`/`algorithm`/`expireMinutes`，见 `ontology/src/security.ttl` 的 JwtConfig 块）。
- **影响**：文档自相矛盾；SPARQL 端点即使仅 ADMIN 可用，也暴露完整 RBAC 矩阵与 JWT 配置项。
- **修改建议**：P0 不做通用 SPARQL，改为 3 个服务端模板（`entity_describe`/`intent_meta`/`rule_meta`）；若保留，则从图中剔除 `security.ttl` 的 JwtConfig，并修正 `01:357` 的表述；把"不加载 demo.ttl"登记为对 A1 的偏差（源文档 `:157` 明确含 `demo.ttl`）。

### S2 `advanced=True` 无必要，且 2 个 `sh:sparql` 形状在"部分实例"上会误报
- **证据**：`01:312` 使用 `advanced=True`；`shapes.ttl:208/508` 存在 `sh:sparql` 约束（PlannedOrder/MpsEntry）；这类约束在只含过滤字段的图上会因 `FILTER NOT EXISTS` 为真而误报，而 §5.4 只跳过 `MinCountConstraintComponent`（`01:319`）。
- **影响**：当前 7 个意图未传 `materialCode`，暂不触发；一旦 P2 新增计划类意图就会误拒。
- **修改建议**：`advanced=False`；把闸限定为"每意图声明的参数级约束白名单"，不整形状校验；为 `sh:sparql` 形状加显式跳过规则与注释。

### S3 延迟阈值不可移植
- **证据**：W0.4 验收 "<300ms cold"（`02:114`）、W0.5 "<50ms"（`02:131`）依赖机器与冷启动。
- **影响**：CI 抖动会导致误报；不同开发机无法复现。
- **修改建议**：改为"构建成功 + 目录规模断言"与"相对预算（首次/二次调用比值）"，或仅在性能专项中测量。

### S4 "mock 与真实后端行为一致"不可验证
- **证据**：总览 P1 出口（`02:16`）与 P1 出口检查表（`02:488`）要求一致，但没有定义比较方法；`ai-intents.json` 只导出意图与角色矩阵。
- **影响**：两套查询逻辑（TS/Python）必然漂移，且没有测试能发现。
- **修改建议**：引入 golden 契约：同一 fixture 数据下，mock 与后端对 7 个意图各输出一份 JSON 快照并 diff；或把承诺收敛为"意图清单/角色矩阵/schema 一致"。

### S5 审计保存原始问题，缺脱敏与保留策略
- **证据**：`01:710` 的 `question` 列存原文；`AI_LOG_PROMPTS`（`01:610`）只覆盖 LLM prompt。
- **影响**：客户名、金额、人名可能长期留存；与"最小化"原则不一致。
- **修改建议**：增加 `AI_LOG_QUESTION`（默认 true 但可关）、长度截断（已有 500）与保留期；P2 再评估加密/脱敏。

### S6 `AI_CHATBI_ENABLED=false` 会把 A1 一起关掉
- **证据**：`01:807` 写"关闭后 `/api/ai/*` 返回 503"，而 A1 的本体检索属于 P0、应在 ChatBI 关闭时仍可用。
- **影响**：运维为了降风险关闭 ChatBI，会连带关闭本体检索与实体查询。
- **修改建议**：拆为 `AI_ENABLED`（总开关）与 `AI_CHATBI_ENABLED`（仅 `/chat`），路由分别判定。

### S7 运行时依赖可再收敛
- **证据**：`owlrl` 只被 `validate-consistency.py` 使用（构建期）；`PyYAML` 只被生成器/目录构建使用；`ontology_service` 运行时只需 `rdflib`，闸门只需 `pyshacl`。
- **影响**：镜像多两个不必要的运行时包，增加供应链面。
- **修改建议**：`requirements.txt` 加 `rdflib/pyshacl/PyYAML`；`owlrl` 放 `requirements-dev.txt`（或 CI 单独安装）；在 W0.1 验收里注明"镜像内 import rdflib/pyshacl 成功"。

### S8 `check_rbac_parity` 不能作为 `ai` 策略正确性的证据
- **证据**：`backend/scripts/check_rbac_parity.py` 比对的是同一生成器产出的 Python 与 TS 两份文件，属同源一致性检查；它不校验"路由前缀 ↔ 域码"是否覆盖。
- **影响**：文档用"parity 自动覆盖"支撑 D2，容易被理解为"策略语义正确"。
- **修改建议**：保留 parity 作为防漂移闸；另加一条路由探针测试（匿名 401 / 8 个业务角色 200 / 未知角色 403），这才是 D2 的行为证据。

### S9 `coverage.legacy_declared: 0` 掩盖 9 张已声明类但未暴露的表
- **证据**：`01:682` 的响应示例；设计 §1.2 自己列出 9 张"只有类、无字段元数据"的表。
- **影响**：读者会以为"未覆盖 = 0"，与 §1.2 的诚实声明冲突。
- **修改建议**：响应增加 `not_exposed: 9` 与清单（或 `legacy_declared: 9` 但注明"不在本次目录"）；前端在"能力边界"里展示。

### S10 Docker 镜像验证没有落成工作项
- **证据**：`01:798` 只写"无需改动；但需在镜像内验证"；计划 W0.1 的验收（`02:57-63`）没有 `docker build`。
- **影响**：F3（运行镜像缺解析库）是本设计最重要的修正之一，但没有一条可执行验收防止回归。
- **修改建议**：W0.1 增加"`docker build` + 容器内 `python -c 'import rdflib,pyshacl; from backend.services.ai.ontology_service import ...'` + 加载 5 个 TTL 成功"；并在 CI 增加可选镜像构建 job。

### S11 `datetime.utcnow()` 与仓库既有时间口径不一致
- **证据**：`01:543` 使用 `datetime.utcnow()`；仓库既有代码使用 `datetime.now()`（本地时区）。
- **影响**：7 天窗口在 UTC+8 下偏移 8 小时，边界日期会错一天。
- **修改建议**：统一使用 `datetime.now()`，或显式声明全部时间为 UTC 并在入库/展示层转换；在文档中写清时间基准。

### S12 附录 A 的示例答案使用了不存在的种子单号
- **证据**：`01:643` 的示例回答包含 `PO-20261120-0007`；全仓检索该单号只出现在设计文档。
- **影响**：评审者会以为已有演示数据；实现者按此写测试会得到空结果。
- **修改建议**：改用 W1.6 fixture 的单号，或在示例标题标注"示意数据"；与 I12 的最小数据集一起维护。

---

## 4. 与外部提升方案的偏差复核

| 源文档条目 | 设计/计划处理 | 评审结论 |
|---|---|---|
| A1 含 `demo.ttl`（`:157`） | 设计 §1.1 明确不加载 `demo.ttl`（`01:344`） | **偏差未登记**：§2 的 K1–K5 与计划 D1–D10 都没有这一条；建议补登 |
| A2 "LLM 只产出符合 SHACL 的意图" | 设计 §7.1/§7.3 对齐 | 一致 |
| D3 "落 OperationLog" | 设计改为新建 `ai_query_logs` 并用 `request_id` 关联（`01:707`） | 偏差仅在 §1.7，计划 D 表未登记；且关联实现有 I1 缺陷 |
| C1 路线图 P3 vs 优先级矩阵 P1 | 计划 D3 取 P1 | 正确，源文档 `:207-209` 确为冲突 |
| C2 数据扩充 P3 | 计划 D8 "保持" | 与 P1 验收/演示需求倒挂（I12） |
| C6 变更影响分析 | 计划 D10 不做 | 理由成立（仓库无 ECN 模型） |
| "严禁生产数据发公有云"（`:163`） | 设计未设技术控制（I5） | **未覆盖**，需补开关与验收 |

---

## 5. 建议的修补顺序（最小改动路径）

1. **先修 B1/B2/B3**：这三项决定 P0 能否过门禁、目录能否构建、闸门能否运行；对应更新计划 W0.2/W0.4/W0.5 的文件范围与验收。
2. **再修 I3/I4/I11/I12**：先把"验收问题 → 解析规则 → 取数口径 → 数据集"闭环，否则 P1 的出口标准不可达。
3. **再修 I1/I2/I5/I6**：审计持久化、安全叙事、LLM 出境、查询超时，这四项决定 D2/D3 是否可对外承诺。
4. **其余 I7–I10、S1–S12**：随对应工作项顺带处理，其中 I7 的计数统一应在下一次提交前完成，避免评审按旧口径复核。

---

## 6. 复核方法

- 代码/本体证据均给出文件与行号；行号以当前工作区为准。
- 数据类断言用一次性脚本复算：`work/review_checks.py`（YAML 实体数、重复表/类、枚举）、`work/review_shapes.py`（抽象路径形状与目标类）、`work/review_shape_fields.py`（抽象路径对应物理列）。脚本不进入交付物。
- 未运行任何测试或门禁（评审为静态复核）；文中"会失败"的结论均基于门禁脚本的显式断言逻辑，可在修复前用 `python backend/scripts/gate.py` 复现。
