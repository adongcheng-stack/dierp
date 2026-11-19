# Night State
## Current Task
（空）
## Pending Tasks
- [ ] T103 P0 TTL/SHACL/demo 同步双绿（30min）
- [ ] T103 P0 TTL/SHACL/demo 同步双绿（30min）
- [ ] T104 P0 发货单后端 4 端点（45min）— 探针 8 断言
- [ ] T105 P0 发票+应收后端（40min）— 探针 6 断言
- [ ] T106 P0 种子+reset 卫生（25min）— reset×2 幂等+自洽
- [ ] T107 P0 前端 3 页（35min）— tsc EXIT=0
- [ ] T108 P0 mock 同构+snapshot v15（35min）— 探针 6 断言
- [ ] T109 P0 smoke_sd_delivery≥12+parity 扩项（30min）
- [ ] T110 P0 全门禁+日志+提交（15min）
- [ ] T201 P1 本体 4 实体+2 枚举（25min）
- [ ] T202 P1 TTL/SHACL 同步（20min）
- [ ] T203 P1 采购发票+三单匹配+confirm（30min）
- [ ] T204 P1 付款/收款+核销+视图升级（40min）
- [ ] T205 P1 前端发票页+资金核销页+台账升级（25min）
- [ ] T206 P1 mock+snapshot v16+种子+parity（20min）
- [ ] T207 P1 smoke_finance_loop≥14+全门禁+提交（20min）
- [ ] T301 P2★ 总账实体（30min）【stretch：仅剩余≥45min】
- [ ] T302 P2★ 科目种子+gl_rules+GlEngine.post（25min）【stretch】
- [ ] T303 P2★ 挂分录+端点+smoke_gl≥8（35min）【stretch】
- [ ] T304 P2★ 全门禁+提交（10min）【stretch】
## Completed Tasks
- [x] T101 P0 本体枚举+3（22:08 完成）— 证据：generate-types EXIT=0（46 枚举含 3 新）；validate-type-sync EXIT=0；validate-consistency EXIT=0；mappings v1.2.0
- [x] T102 P0 实体+3（22:18 完成）— 证据：generate_models EXIT=0（39 实体）；upgrade_planning EXIT=0（3 新表入库）；alembic check EXIT=0；validate-type-sync EXIT=0；tsc EXIT=0。注：FK 目标列为 sales_orders.order_number（sd.py 实际列名）
## Blocked Tasks
（空）
## Last Checkpoint
2026-11-19 22:03:54 启动（9h 预算至 2026-11-20 07:04）。注意：DIERP-demo.html 有用户未提交改动，不触碰。
