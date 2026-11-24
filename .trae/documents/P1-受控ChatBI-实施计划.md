# P1 受控 ChatBI（收窄范围）实施计划

## Context

P0（语义底座与安全前置）已完成并全绿（16 项门禁 / 117 passed / alembic check 通过）。
本轮按 `2026-11-24/ai-ontology-design/outputs/02-实施计划-DIERP-AI原生化.md` v1.1 进入 P1，
但范围收窄为：

- **W1.1 意图注册表**：7 个手写只读意图 + 角色白名单 + `export_ai_intent_meta.py --check` + 门禁接入；
- **W1.2 受控查询执行器**：`ask()` 编排链路（确定性解析器、模式闸、SHACL 闸、权限闸、执行、溯源、审计、限流、超时），LLM 调用层只用 mock/stub；
- **W1.6 验收基准集**：13 条验收问题逐条落测试 + 最小演示数据集。

**明确不在本轮**：W1.3 路由扩展、W1.4 前端页面与 mock handlers、W1.5 异常解读、W1.7 ROI 文档、
真实模型服务、MCP、工作流 AI；不做任何 AI 写操作。

约束沿用计划：不新增 AI 写操作、不改既有表结构/API 契约、不引入前端依赖、不使用 PG 专有语法（测试跑 SQLite）、
权限数据只来自生成物 `security_policy.py`。

---

## 1. 意图注册表（W1.1）

### 新建文件

`backend/services/ai/intents/`（每意图一个模块，`__init__.py` 汇总注册）

| 文件 | intent_code | 主要实体（primary） | 角色 |
|---|---|---|---|
| `kitting.py` | `kitting_shortage` | KittingResult | PLANNER/PRODUCTION/GENERAL_MANAGER |
| `orders.py` | `order_delay_risk` | SalesOrder | SALES/SALES_MANAGER/PLANNER/GENERAL_MANAGER |
| `inventory.py` | `material_below_safety` | Material | WAREHOUSE/PLANNER/PRODUCTION/GENERAL_MANAGER |
| `planning_exceptions.py` | `open_mrp_exceptions` | MrpException | PLANNER/GENERAL_MANAGER |
| `credit.py` | `customer_credit_status` | Customer | SALES_MANAGER/FINANCE/GENERAL_MANAGER |
| `receivables.py` | `ar_overdue` | SalesInvoice | FINANCE/GENERAL_MANAGER |
| `quality.py` | `open_nonconformance` | NonConformanceReport | ENGINEER/PRODUCTION/GENERAL_MANAGER |

- 复用 P0 的 `IntentSpec/QueryResult/Provenance`（`backend/services/ai/intent.py`）。
- `QueryResult` 增加可选字段 `reason: str | None = None`（仅内部使用，用于“客户不存在”等空结果说明）。
- `intents/__init__.py` 在导入时把 7 个 spec 写入 `intent.INTENTS`，并导出 `INTENT_REGISTRY`。
- 参数模型全部继承 `BoundIntent`（`extra="forbid"`）；`limit` 用 `Field(ge=1, le=200)`。
- 取数口径严格按设计 §7.2.1：
  - #1 `kit_status='SHORT'`，`checked_at desc`，`shortage_qty` 为空按 0 不计行；
  - #2 `status IN (APPROVED, IN_PRODUCTION)`、`delivery_date ∈ [now, now+within_days]`；风险 = 无生产订单 或 存在 `planned_finish_date IS NULL/晚于交付日` 的未完工生产订单；输出不含单价/金额；
  - #3 `current_stock < safety_stock`，按缺额 `safety_stock-current_stock` 降序；
  - #4 `resolution_status='OPEN'` 默认，`shortage_qty desc`；
  - #5 应收余额 = `SUM(receivable_entries.amount)`（带符号，不按类型二次拼符号）；未完成订单 = `status IN (APPROVED, IN_PRODUCTION)` 的 `total_amount` 之和；占用比 `(ar_balance+open_order_amount)/credit_limit`，`credit_limit<=0` 返回 `None`；客户不存在 → 空结果 + `reason=customer_not_found`；
  - #6 `status IN (ISSUED, PARTIALLY_PAID)`、`received_amount < amount`、`due_date < now-days_overdue`、`amount>0`；未收 = `amount-received_amount`；
  - #7 默认 `status IN (OPEN, UNDER_REVIEW, DISPOSITIONED)`。
- 每个 handler 只用 ORM 表达式（无 `text(`/f-string SQL/`execute(`），强制 `limit()`，时间统一 `datetime.now()` 且在 Python 侧算边界。
- `record_key/downlink`：`result_number /pp/kitting`、`order_number /sd/sales-orders`、`material_code /mm/materials`、`id + downlink=None`、`customer_id /sd/customers`、`invoice_number /sd/invoices`、`ncr_number /qms/ncrs`（均已在 `frontend/src/App.tsx` 证实存在）。
- `output_fields`：金额列（`credit_limit/ar_balance/open_order_amount/amount/received_amount/outstanding`）仅 FINANCE/GENERAL_MANAGER/ADMIN 可见，`"*"` 缺省剔除。
- `shacl_coverage` 按 P0 规则计算，预期 3 full（#3/#4/#7）+ 1 partial（#1）+ 3 none（#2/#5/#6）。

### 脚本与导出物

- 新建 `backend/scripts/export_ai_intent_meta.py`：`--write` 生成、`--check` 漂移校验（退出非 0）。
- 新建 `frontend/src/mock/ai-intents.json`（由 `--write` 生成，含 7 个 code、角色矩阵、`record_key/downlink`、参数摘要）。
- 门禁接入：`backend/scripts/check_ai_catalog.py` 显式 `import backend.services.ai.intents`（触发注册），
  并**修正**现有 `spec.params_model()` 实例化校验（必填参数模型会误报）为 `issubclass(..., BoundIntent)` + `extra=="forbid"` 断言。
  保持 gate 仍为 **16 项**（设计 §11.1：`ai-intents.json --check` 由 `check_ai_catalog.py` 代理）。

### 测试

- 新建 `backend/tests/test_ai_intents.py`：7 个 code、字段齐备、`record_key` 真实列、handler 静态扫描
  （禁止 `text(`/f-string SQL/`execute(`）、每个意图 ≥3 正例 + 1 空结果、取数口径精确数值断言（I4）、金额列裁剪、`export --check` 往返。

---

## 2. 受控查询执行器（W1.2）

### 新建文件

- `backend/services/ai/ratelimit.py`：进程内滑窗 `dict[username, deque]`，超限抛 `AI_RATE_LIMITED`（429）；可注入时钟，测试可 reset。
- `backend/services/ai/proposer.py`：
  - `normalize()`：去空白、全角转半角、截断 `AI_MAX_QUESTION_CHARS`；
  - `preclassify()`：schema/DDL 关键词 → `AI_INTENT_UNKNOWN(reason=SCHEMA_REJECTED)`；写操作动词（删除/修改/更新/新增/创建/写入/导入）→ `AI_INTENT_UNKNOWN`（审计 `REJECTED_INTENT`）；
  - `RuleBasedProposer`：只按设计 §7.1.1 规则表映射意图与显式参数（单号/客户/物料类型同义词/严重度/未关闭/时间窗口/前 N 条），不做语义猜测；
  - `LLMProposer`：包装注入的 LLM client，最多 2 次调用；非法 JSON → `AI_INTENT_UNKNOWN`；合法 JSON 交给模式闸（未知意图/多余参数由闸拒绝）。
- `backend/services/ai/llm.py`：`LLMClient` 协议 + `call_proposal()/call_narration()`；`build_narration_payload(result, columns, allow_external_data)` 做字段白名单（剔除 `record_key`、`customer_id`、金额列）；`AI_LLM_ALLOW_EXTERNAL_DATA=false` 时 payload 只含聚合值。默认 `AI_LLM_ENABLED=false` 不实例化真实 client。
- `backend/services/ai/executor.py`：
  - `_apply_statement_timeout(db, seconds)`：PG → `SET LOCAL statement_timeout`（唯一允许的 `text()` + int 字面量）；SQLite → `set_progress_handler`；不可用则仅 Python 预算；
  - `execute_intent()`：记录 `time.monotonic()`，超预算抛 `AI_EXECUTION_TIMEOUT`；结果按 `AI_MAX_ROWS` 二次截断；异常归一为 `AI_EXECUTION_FAILED`。
- `backend/services/ai/answer.py`：模板渲染（数字全部来自结果）、字段白名单裁剪、空结果区分“无匹配/条件不合法”、数字回查 `numbers(text) ⊆ numbers(rows)`。
- `backend/services/ai/pipeline.py`：`ask(question, user, db, request_id=None, *, proposer=None, llm_client=None, now=None)` 12 步链路；
  统一 catch `AIException` 后按 code+reject_reason 映射审计状态（OK / REJECTED_SCHEMA / REJECTED_INTENT / REJECTED_PARAM / REJECTED_SHACL / REJECTED_PERMISSION / REJECTED_TIMEOUT / REJECTED_RATE_LIMIT / FAILED），
  调 `write_ai_query_log()`（P0 独立 session + commit），返回 `{trace_id, answer, intent, data, provenance, limits, model}`。
- 溯源：`executor`/pipeline 校验每行 `record_key` 列非空、`sources` 非空且表在 `Base.metadata`，缺失抛 `AI_PROVENANCE_INCOMPLETE`。

### 测试

- `backend/tests/test_ai_pipeline.py`：正常链路、参数/枚举拒绝、权限拒绝、溯源缺失、行数截断、审计三类落库（重开 session 可查、403/422/504 有行、`AI_LOG_QUESTION=false` 不存原文）、限流第 21 次 429、超时（慢 handler + PG/SQLite 分支单测）、数字回查、字段白名单。
- `backend/tests/test_ai_llm.py`：非法 JSON/未知意图/多余参数被拒且 ≤2 次调用；出域 payload 不含行级明细。

---

## 3. 13 条验收用例（W1.6）

- 新建 `backend/tests/fixtures/ai_demo_dataset.py`：固定种子数据集，覆盖 7 意图各 ≥3 条，
  含“已关闭 NCR、已解决 MRP 异常、已收款发票、无生产订单的销售订单”；所有单号以模块常量导出，测试不硬编码示意值。
- 新建 `backend/tests/test_ai_acceptance.py`：对附录 A 的 13 条逐条断言
  `intent/params → data.columns → data.rows 数值 → provenance（record_key/downlink/shacl）→ 审计行`。
  - #6 断言 422 + `InConstraintComponent` + 审计 `REJECTED_SHACL`；
  - #10 断言 422 `AI_INTENT_UNKNOWN` + 审计 `REJECTED_INTENT` + 相关表行数不变；
  - #11 断言 `REJECTED_SCHEMA`（规则模式）与 LLM stub 越界 JSON 被拒；
  - #12 WAREHOUSE 问信用 → 403 `AI_PERMISSION_DENIED` + `REJECTED_PERMISSION`；
  - 数值断言：信用占用比、逾期未收金额、齐套缺料数、超期发票未收额。
- 数据集可重复初始化（同 fixture 两次结果一致）。

---

## 4. 关键实现决策 / 偏差说明

1. `QueryResult.sources` 保持 P0 的 `Provenance(table, record_key, ontology_iri)`；响应层把 `record_key` 映射为 `record_ref`，
   满足计划“按 record_key 组装”的验收口径，不破坏 P0 类型。
2. `check_ai_catalog.py` 不再实例化必填参数模型（否则信用意图会让门禁误报），改为结构断言。
3. 金额字段最小化验收用 **SALES_MANAGER vs FINANCE**（同为信用意图合法角色）做差分；
   W1.4 计划中的 WAREHOUSE vs FINANCE 组合在设计中无任何意图同时允许二者，属计划与设计不一致，
   本轮按设计角色矩阵执行并在最终报告标注该偏差。
4. W1.3 路由、W1.4 前端、W1.5 洞察、W1.7 文档不在本轮；`export_ai_intent_meta.py --check` 仍纳入门禁代理校验。

---

## 5. 验证命令（每完成一个工作项执行）

```powershell
# 工作项 W1.1
python backend/scripts/export_ai_intent_meta.py --check
python backend/scripts/check_ai_catalog.py
python -m pytest -q backend/tests/test_ai_intents.py

# 工作项 W1.2
python -m pytest -q backend/tests/test_ai_pipeline.py backend/tests/test_ai_llm.py

# 工作项 W1.6
python -m pytest -q backend/tests/test_ai_acceptance.py

# 全量
python -m pytest -q                    # cwd=backend
python backend/scripts/gate.py          # 期望 16 项全绿
```

> `alembic check` 需本地 PG；本轮不新增表/迁移，仍按 §5 执行一次取证。
