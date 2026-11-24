# MES 语义映射校正与最小只读链路勘察实施计划

## Context

用户要求把 ERP↔MES 的语义映射从“实体目录”推进到“与真实 MES 字段对齐”，并尽可能跑通一条“工单号 → 工序进度/报工记录”的只读链路。约束：MES 仓库只读、不引入不必要依赖、密钥不落盘、校验规则与门禁口径不放宽、接口不可达时不得伪造连通。

本轮已完成对 `D:\project\mes` 的只读勘察。结论是：MES 有 HTTP REST 接口，但本机网关/核心服务未启动；MySQL 端口可达但仓库内的默认凭证均被拒绝。因此链路按“受阻”如实收口，本轮不新增连接器代码。映射校正仍可基于 MES 真实 DDL 与实体类完成。

## 一、勘察结论

### 1. 技术栈与运行方式

- Java 8 + Spring Boot 2.7.18 + Spring Cloud 2021.0.9 + Spring Cloud Alibaba（Nacos）+ MyBatis-Plus 3.5.5。
- Maven 多模块：`mes-common`、`mes-entity`、`mes-device-client`、`mes-core`、`mes-gateway`、`mes-report`、`mes-image`、`mes-pdf-service`。
- `mes-gateway` 端口 9080，`mes-core` 端口 9081；设备采集网关 `DevLib/mcp` 8082；PDF 服务 9083。
- 启动依赖 Nacos（配置/注册）与 MySQL/Redis；MES 仓库自带启停脚本，禁止直接命令行 `mvn/npm` 启停。

### 2. 持久化方案

- MySQL 8.0，库 `mesdb`，默认连接 `jdbc:mysql://127.0.0.1:3306/mesdb`，可用 `DB_HOST/DB_USER/DB_PASSWORD` 覆盖。
- Redis `127.0.0.1:6379`。
- 测试环境完整 DDL：`DevLib/branches/20261101/DBscript/测试环境/01-mes_ddl.sql`；当前 trunk 实体类在 `DevLib/trunk/src/mes-backend/mes-entity`。

### 3. 对外接口与认证

- 网关统一前缀 `/api/v1/**`，JWT 认证：`Authorization: Bearer <token>`；白名单含 `/api/v1/auth/login`、`/api/v1/enums/**`、`/api/v1/dict-data/**`、`/actuator/**`。
- 登录：`POST /api/v1/auth/login`，响应 `LoginVo`（`accessToken/refreshToken/expiresIn/userInfo`）。
- **无 OpenAPI**：pom 中无 springdoc/swagger/knife4j 依赖，也无生成的接口文档。
- 与本链路相关的接口：
  - `GET /api/v1/production/work-orders/page`（`WorkOrderListQry`，含 `workOrderNo/status/...`）
  - `POST /api/v1/production/process-report/tasks`（`IdCmd`，按工单取工序任务）
  - `GET /api/v1/production/process-report/page`（`ProcessReportListQry`，按工单/工序/时间查报工）
  - `POST /api/v1/production/process-report/sn-tasks`（按 SN 查任务）

### 4. 七类实体（真实表 / 主键 / 关键关联）

| 实体 | 真实表 | 主键 | 关键字段与关联 |
|---|---|---|---|
| WorkOrder | `prd_work_order` | `id BIGINT` 自增 | `work_order_no`(唯一)、`quantity/completed_quantity/qualified_quantity/scrapped_quantity`、`status`、`planned_start_date/planned_end_date/actual_start_date/actual_end_date`、`workshop_id`、`production_line` |
| Operation（工单工序任务） | `prd_process_task` | `id BIGINT` 自增 | `work_order_id`→`prd_work_order.id`、`process_id`→`prd_process.id`、`sequence`、`planned_start_date/planned_end_date`、`completed/qualified/scrapped_quantity`、`status`、`equipment_id`→`equ_equipment.id` |
| 报工 | `prd_process_report` | `id BIGINT` 自增 | `process_task_id`→`prd_process_task.id`、`work_order_id`、`process_id`、`equipment_id`、`employee_id`、`report_time/report_date`、`completed/qualified/scrapped_quantity`、`defect_reason`、`actual_hours` |
| Equipment | `equ_equipment` | `id BIGINT` 自增 | `code`(唯一)、`name`、`type`、`status`、`workshop_id`、`production_line`、`asset_type` |
| Material | `mat_material` | `id BIGINT` 自增 | `code`(唯一)、`name`、`category`、`product_category`、`material_type`、`unit_in/unit_out`、`safety_stock`、`status` |
| InspectionOrder | `qc_check_record` | `id BIGINT` 自增 | `check_no`(唯一)、`check_type`、`target_id/target_type`、`work_order_id`、`process_task_id`、`check_time`、`inspector_id`、`equipment_id`、`result` |
| ScrapRecord | `qc_scrap_record` | `id BIGINT` 自增 | `target_id/target_type`、`scrap_reason`、`scrap_date`、`operator_id` |
| Warehouse | `biz_warehouse` | `id BIGINT` 自增 | `code`(唯一)、`name`、`type`、`address`、`status` |

关联均为逻辑关联（索引，无外键）；`target_type` 取值为 `MATERIAL/SEMI_PRODUCT/FINISHED_PRODUCT`。

### 5. 最小链路可用性判定（受阻，未伪造）

- `127.0.0.1:9080/9081`：连接被拒，网关与核心服务均未启动。
- `127.0.0.1:3306`：端口可达，但用仓库配置中的 `root/root`、`root/mesdb168`、`root/123456` 连接均返回 `Access denied`；环境中也没有 `DB_HOST/DB_USER/DB_PASSWORD`。无法确认 `mesdb` 是否存在，更无法做只读查询。
- `8848`（Nacos）不可达，单独启动 `mes-core` 也缺少注册/配置中心。
- 结论：HTTP 与数据库两条路径都被“凭证/服务未启动”阻断。本轮不新增 MES 连接器、不 mock、不宣称已连通。

## 二、映射校正方案（唯一功能改动）

目标文件：`ontology/model/mes-mapping.yaml`（`version` 升为 `1.1`）。

关键约束：`build_mes_mapping()` 校验 `ontology_property` 是否存在于 `ontology.describe(class)` 返回的属性中，而 `describe()` 只暴露该类 SHACL Shape 声明的 `sh:path`。因此只能映射 Shape 已声明的属性；MES 有、ERP 本体未声明的字段必须显式列入 `unmapped_fields` 并写原因。校验代码与门禁不改。

统一在 YAML 增加（校验器会忽略这些键，仅作文档与后续工具消费）：

```yaml
unmapped_reasons:
  ScrapRecord: "……"
# 每个 mapping 内：
unmapped_fields:
  - mes_field: xxx
    reason: "……"
```

### 2.1 Equipment → Resource（表 `equ_equipment`）

- `code` → `resourceId`
- `name` → `resourceName`
- `status` → `status`，`enum: ResourceStatus`，`value_map`：
  - `"25001"` → `ACTIVE`（运行）
  - `"25002"` → `ACTIVE`（空闲）
  - `"25003"` → `DOWN`（故障）
  - `"25004"` → `MAINTENANCE`（维修中）
- 显式 unmapped：
  - `type`：ERP `resourceType` 仅允许 `MACHINE/LABOR`，MES 是工艺设备类别码 `13001..13005`，语义不同。
  - `workshop_id`：ERP `workCenterId` 是产能/成本归集单元，与“车间”不等价；MES 无工作中心主数据。
  - `production_line`、`asset_type`：本体 Resource Shape 未声明对应属性。
  - `status` 的 `25005`（停用）/`25006`（报废）：`ResourceStatus` 无对应码，不硬凑。

### 2.2 WorkOrder → ProductionOrder（表 `prd_work_order`）

- `work_order_no` → `documentNumber`
- `quantity` → `quantity`
- `status` → `status`，`enum: DocumentStatus`，`value_map`：
  - `DRAFT` → `DRAFT`
  - `SUBMITTED` → `RELEASED`
  - `IN_PRODUCTION` → `IN_PROGRESS`
  - `COMPLETED` → `COMPLETED`
- 显式 unmapped：
  - `status=PAUSED`：`DocumentStatus` 无“暂停”码，保留原值、不硬映射。
  - `completed_quantity/qualified_quantity/scrapped_quantity`：ProductionOrder Shape 只声明 `quantity`，无完工/合格/报废数量属性。
  - `planned_start_date/planned_end_date/actual_start_date/actual_end_date`：该 Shape 未声明日期属性。
  - `priority/workshop_id/production_line/product_id/...`：Shape 未声明。

### 2.3 Operation → ScheduledOperation（表 `prd_process_task`）

- `process_id` → `opId`（工序主数据记录 ID；Shape 的“工序记录编号”）
- `planned_start_date` → `plannedStart`
- `planned_end_date` → `plannedEnd`
- 显式 unmapped：
  - `status`：MES 是执行态 `PENDING/IN_PROGRESS/COMPLETED/REWORKED/SCRAPPED`；ERP `ScheduleOpStatus` 是排程发布态 `PLANNED/LOCKED/PUBLISHED/CANCELLED`，不同源。
  - `workCenterId`：任务只有 `equipment_id`，设备不是工作中心。
  - `operationNumber`：MES 无独立“工序号”列；`process_id` 已映射到 `opId`，不再重复占用。
  - `sequence`、`completed/qualified/scrapped_quantity`、`equipment_id`：Shape 未声明对应属性或语义不等价。

### 2.4 Material → Material（表 `mat_material`）

- `code` → `materialCode`
- `product_category` → `materialType`，`enum: MaterialType`：
  - `FINISHED_PRODUCT` → `FG`
  - `SEMI_PRODUCT` → `SEMI`
  - `RAW_MATERIAL` → `RAW`
- `material_type` → `procurementType`，`enum: ProcurementType`：
  - `PURCHASED` → `BUY`
  - `SELF_PRODUCED` → `MAKE`
- 显式 unmapped：
  - `product_category=AUXILIARY`：ERP `MaterialType` 无“辅料”，`PACKAGING` 是包装物，语义不等价。
  - `name/specification/model/unit_in/unit_out/safety_stock/min_stock/status/category`：Material Shape 仅声明 `materialCode/materialType/procurementType`。

### 2.5 InspectionOrder → InspectionOrder（表 `qc_check_record`）

- `check_no` → `inspectionNumber`
- `check_type` → `inspectionType`，`enum: InspectionType`：
  - `IQC` → `INCOMING`
  - `IPQC` → `IN_PROCESS`
  - `OQC` → `FINAL`
  - `FQC` → `FINAL`
- `result` → `result`，`enum: InspectionResult`：
  - `PASS` → `PASS`
  - `FAIL` → `FAIL`
- 显式 unmapped：
  - `result=PENDING`：ERP 第三态是 `HOLD`（挂起），与“待定”不完全等价，不硬映射。
  - `status`：`qc_check_record` 无状态列（只有 result）。
  - `materialCode`：MES 只有 `target_id/target_type`，需按 target 关联物料主数据才能得到编码；字段级映射不做隐式 JOIN。
  - `quantityInspected/quantityRejected`：质检记录表无数量列（仅在明细/报工中）。
  - `check_time/inspector_id/remark/serial_number/standard_id/equipment_id`：InspectionOrder Shape 未声明或需关联查询。

### 2.6 Warehouse → Warehouse（表 `biz_warehouse`）

- `code` → `warehouseCode`
- `name` → `warehouseName`
- 显式 unmapped：
  - `address/status/type`：Warehouse Shape 只声明 `warehouseCode/warehouseName`；`type` 还是中文枚举描述，不是稳定码值。

### 2.7 ScrapRecord（整实体 unmapped）

- 本体没有“报废记录”类；最接近的 `NonConformanceReport` 是“不合格品闭环（开立→评审→处置→关闭）”，其 `ncrNumber/defectCode/sourceType/...` 与 `qc_scrap_record` 的 `target_id/target_type/scrap_reason/scrap_date/operator_id` 语义和字段均不匹配，且报废数量不在该表。
- 结论：保持整实体 `unmapped`，原因写入 `unmapped_reasons.ScrapRecord`，不为覆盖率硬凑。

### 2.8 覆盖率与预期结果

- `mes_catalog` 仍为 7 个实体；映射实体仍为 6 个；**覆盖率保持 6/7 = 85.71%**。
- 变化在“真实对齐”：旧 v1 的 6 个 `mes_table` 与绝大多数字段名（`mes_equipment/mes_work_order/...`、`equipment_code/work_center_code/plan_qty/...`）并非 MES 实际表/列；新映射全部改为实测表名与列名，并删除不存在的字段。

## 三、最小只读链路：本轮不新增代码

- 触发条件不满足：无可用 HTTP 服务、无可用 DB 凭证，按任务要求如实受阻，不伪造。
- 解除阻塞后的最小实现（待确认后另起任务）：
  - HTTP 路线：`POST /api/v1/auth/login` 取 JWT → `GET /api/v1/production/work-orders/page?workOrderNo=...` → `POST /api/v1/production/process-report/tasks {workOrderId}` 取工序进度 → `GET /api/v1/production/process-report/page?workOrderId=...` 取报工。复用现有 `run_intent()` 的参数绑定/SHACL/角色闸/审计/溯源。
  - DB 路线：只读账号 + 参数化查询 `prd_work_order / prd_process_task / prd_process_report`；如新增 MySQL 驱动，需说明理由（当前 ERP 为 PostgreSQL，跨库必须新增驱动）。
- 凭证要求：只经环境变量注入（如 `MES_BASE_URL`、`MES_USERNAME`、`MES_PASSWORD` 或 `MES_DB_DSN`），不写入仓库与日志。

## 四、改动清单

- 修改：`ontology/model/mes-mapping.yaml`
  - 6 个实体的 `mes_table`、`mes_field`、`value_map` 全部按真实 MES 校正。
  - 新增 `unmapped_fields` / `unmapped_reasons` 文档键。
  - `ScrapRecord` 保持整实体未映射并写原因。
- 不改：`backend/services/ai/semantics.py`、`backend/scripts/check_ai_catalog.py`、`backend/tests/**`、MES 仓库、前端。
- 不新增依赖。

## 五、验证

在 `d:\project\erp` 下执行：

```powershell
python backend/scripts/check_ai_catalog.py
python -m pytest backend/tests/test_ai_semantics.py -q
python -m pytest backend/tests -q
python backend/scripts/gate.py
python backend/scripts/export_ai_intent_meta.py --check
```

通过标准：

- `check_ai_catalog.py`：MES 语义校验无 problems；实体 7、覆盖 6/7、unmapped=`ScrapRecord`。
- `test_ai_semantics.py`：`problems == []`、`unmapped == ["ScrapRecord"]`、`coverage ≈ 6/7`、全部属性/枚举码合法、接口只读且角色受控。
- 全量 pytest 与 gate 维持既有通过数（不因本次改动回退）。
- 如任一门禁/测试失败：立即 `send_message_to_session` 汇报并停止扩面。

## 六、风险与口径

- **枚举版本差异**：`EquipmentEntity` 当前用 Integer 枚举（`25001..25006`），而 `branches/20261101` 测试 DDL 仍显示 VARCHAR（`RUNNING/...`）。映射以当前 trunk 实体/枚举码为准，并在 YAML 注释中标注该差异。
- **未连库核对**：受凭证阻塞，字段以 trunk 实体 + 测试环境 DDL 为准；最终报告明确说明“未做 DB 实库核对”。
- **不放松门禁**：不修改校验器、不扩大 Shape、不为覆盖率添加不存在字段。
- **只读与密钥**：不修改 MES；不把任何凭证写入仓库、日志或文档。
