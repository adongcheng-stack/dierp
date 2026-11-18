# QMS（质量管理）模块实现计划

> 状态：已完成（v2）
> 版本：v2
> 关联：任务清单（四项遗留已完成）、EAM/报工数据底座、模型-本体驱动架构
>
> 完成情况：后端（QmsEngine / `/api/qms` 8 条路由 / 种子 / demo_reset 纳入）、前端（3 页面 + 菜单 + mock 快照 v8）、语义层（2 类 / 2 Shape / 7 枚举作用域绑定 / 22 属性 + demo.ttl 实例）、`smoke_qms.py` 全链路通过。

---

## 1. 目标与范围

在现有 ERP 上新增 **QMS（质量管理）** 模块，落地 **来料/过程/终检三环节检验 + 不合格品（NCR）闭环**，并与已有 EAM（设备故障）、报工（OperationReport）、LOT 卡数据底座双向联动，纳入演示数据一键重置。

**首期范围（用户已确认）：**
- 三检验单（来料/过程/终检）+ 不合格品闭环（NCR：开立→评审→处置→关闭）
- 双向联动：报工 scrap>0 → 可生成 NCR；NCR 处置为"设备原因" → 自动生成 EAM 故障
- 纳入 `demo_reset` 清理与种子重建

---

## 2. 数据底座对齐锚点

| 检验环节 | 锚点表 | 关键字段 | 说明 |
|---|---|---|---|
| 来料检验 | `purchase_order_lines` | material_code, quantity, received_quantity | 按采购订单行收货检验 |
| 过程检验 | `operation_reports` | report_number, good_quantity, scrap_quantity | 报工良品/报废分离处 |
| 终检 | `lot_cards` | lot_number, quantity | LOT 卡唯一批次收尾检验 |
| NCR→EAM | `EamEngine.record_failure` | resource_id, severity, description, reported_by | 设备原因时自动上报故障 |

---

## 3. 领域模型（新增 QMS 实体）

> 接入本体：**并入 `ontology/model/planning.yaml`**（与 EAM 一致，复用 `generate_models.py` 单一生成链路），重新生成 `backend/common/models/planning.py` 与前端类型。

### 3.1 InspectionOrder（检验单）
统一一张检验单，以 `inspection_type` 区分来料/过程/终检（避免三张几乎同构的表）。

| 字段 | 类型 | 说明 |
|---|---|---|
| inspection_number | string unique | 检验单号（IQC/IPQC/FQC 前缀） |
| inspection_type | enum `InspectionType` | INCOMING / IN_PROCESS / FINAL |
| material_code | string fk | 被检物料 |
| lot_number | string | 关联 LOT 卡（过程/终检） |
| purchase_order_number | string fk | 关联采购订单（来料） |
| report_number | string | 关联报工单（过程） |
| quantity_inspected | decimal | 检验数量 |
| quantity_ok | decimal | 合格数量 |
| quantity_rejected | decimal | 不合格数量 |
| inspector | string | 检验员 |
| inspected_at | datetime | 检验时间 |
| result | enum `InspectionResult` | PASS / FAIL / HOLD |
| status | enum `InspectionStatus` | DRAFT / COMPLETED / CANCELLED |
| remarks | text | |

### 3.2 NonConformanceReport（不合格品记录 NCR）
| 字段 | 类型 | 说明 |
|---|---|---|
| ncr_number | string unique | 不合格编号（NCR-…） |
| source_type | enum `NcrSourceType` | INSPECTION / REPORT / LOT_CARD / MANUAL |
| source_ref | string | 来源单据号 |
| inspection_number | string fk | 来源检验单（可空） |
| report_number | string fk | 来源报工单（可空） |
| lot_number | string | 涉及批次 |
| material_code | string fk | 物料 |
| quantity | decimal | 不合格数量 |
| defect_code | string | 缺陷代码 |
| defect_desc | text | 缺陷描述 |
| severity | enum `NcrSeverity` | MINOR / MAJOR / CRITICAL |
| disposition | enum `NcrDisposition` | REWORK / SCRAP / USE_AS_IS / RETURN / REVIEW |
| disposition_note | text | 处置说明 |
| root_cause | text | 根本原因 |
| equipment_cause | boolean | 是否判定为设备原因（触发 EAM 联动） |
| failure_number | string | 联动生成的 EAM 故障号（可空） |
| status | enum `NcrStatus` | OPEN / UNDER_REVIEW / DISPOSITIONED / CLOSED |
| reviewed_by / reviewed_at | | 评审人/时间 |
| closed_by / closed_at | | 关闭人/时间 |

### 3.3 枚举（追加到 `ontology/src/mappings.json`）
- `InspectionType`: INCOMING, IN_PROCESS, FINAL
- `InspectionResult`: PASS, FAIL, HOLD
- `InspectionStatus`: DRAFT, COMPLETED, CANCELLED
- `NcrSourceType`: INSPECTION, REPORT, LOT_CARD, MANUAL
- `NcrSeverity`: MINOR, MAJOR, CRITICAL
- `NcrDisposition`: REWORK, SCRAP, USE_AS_IS, RETURN, REVIEW
- `NcrStatus`: OPEN, UNDER_REVIEW, DISPOSITIONED, CLOSED

---

## 4. 后端实现

| 文件 | 内容 |
|---|---|
| `backend/upgrade_planning.py` | 新增 `seed_qms_demo_data()` 种子（幂等）；确保 import 触发 create_all 建 QMS 表 |
| `backend/services/planning/qms_engine.py` | `QmsEngine`：create_inspection, complete_inspection, create_ncr, review_ncr, disposition_ncr, close_ncr, overview |
| `backend/api/routers/qms.py` | 检验单/NCR CRUD + 状态流转 + overview；`/qms` 前缀 |
| `backend/api/main.py` | 注册 `qms.router` |
| `backend/services/planning/demo_reset.py` | `_clear` 增 QMS 表；`_rebuild_master_seed` 调 `seed_qms_demo_data`；返回计入 QMS 清理/重建计数 |

**联动逻辑（QmsEngine）：**
- 报工 scrap>0 → 前端/API 提供"由报工单生成 NCR"入口（按 report_number 拉取 scrap）
- NCR `disposition` 设 REVIEW 且 `equipment_cause=True` → 自动调 `EamEngine.record_failure()`，写回 `failure_number`

---

## 5. 前端实现（全部照 EAM 页面模式）

| 文件 | 内容 |
|---|---|
| `frontend/src/pages/qms/InspectionList.tsx` | 检验单列表（按类型 Tab 过滤） |
| `frontend/src/pages/qms/InspectionForm.tsx` | 新建/编辑检验单 |
| `frontend/src/pages/qms/NcrList.tsx` | NCR 列表（状态流转操作） |
| `frontend/src/pages/qms/NcrForm.tsx` | 新建 NCR（支持从报工单生成） |
| `frontend/src/components/layout/menuConfig.tsx` | 新增"质量管理"分组 + PATH_LABEL_MAP 自动生成 |
| `frontend/src/App.tsx` | lazy import + Route（`/qms/inspections`、`/qms/ncrs` 等） |
| `frontend/src/mock/handlers.ts` | QMS mock 路由（照 eam handlers） |
| `frontend/src/mock/db.ts` + snapshot | QMS mock 数据表 + 快照 |

---

## 6. 演示数据重置（纳入 demo_reset）

- 清理：`inspection_orders`, `non_conformance_reports`
- 重建种子：`seed_qms_demo_data` 生成：
  - 1 张来料检验 PASS
  - 1 张过程检验 FAIL（对应某条报工 scrap>0）
  - 1 张终检 PASS
  - 1 条 NCR（由过程检验产生，处置 REWORK，状态 CLOSED）
  - 1 条 NCR（设备原因，联动了 EAM 故障，状态 OPEN，展示双向联动）
- 返回结构计入 `cleared`/`seeded`

---

## 7. 校验与验收

- `npm run check:node` + `check:python`（本体双栈校验 exit 0，QMS 实例双类型标注一致）
- 新增 `backend/scripts/smoke_qms.py`：检验单创建/完成/NCR 开立→评审→处置→关闭 + 设备联动
- `npm run build` 无体积告警
- 浏览器实测 QMS 页面 0 console error
- 文档：`docs/演示脚本-10分钟.md`、`docs/演示环境发布指南.md` 补 QMS 章节

---

## 8. 涉及文件清单（汇总）

**后端（6）**：planning.yaml, mappings.json, planning.py(生成), upgrade_planning.py, qms_engine.py, qms.py(router), main.py, demo_reset.py
**前端（9）**：menuConfig.tsx, App.tsx, InspectionList.tsx, InspectionForm.tsx, NcrList.tsx, NcrForm.tsx, handlers.ts, db.ts, snapshot.json
**测试/文档（4）**：smoke_qms.py, 演示脚本-10分钟.md, 演示环境发布指南.md, 本计划文档

> 注：`planning.py`、`planning.generated.ts` 由生成器产出，不手改。