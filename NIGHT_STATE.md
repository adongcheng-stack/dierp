# Night State
## Current Task
（空）

## Pending Tasks
- [ ] T402 mock v16 资金域同构（5 钩子+/finance 4 端点+parity）+探针（30min）— 探针≥6 断言
- [ ] T403 全门禁+交接更新+提交（20min）
- [ ] P3 批次拆解（下夜班）：盘点/调拨/批次效期视图/看板资金 KPI（设计 §六，约 4 任务）
- [ ] T302 P2★ 科目种子+gl_rules+GlEngine.post（25min）【stretch】
- [ ] T303 P2★ 挂分录+端点+smoke_gl≥8（35min）【stretch】
- [ ] T304 P2★ 全门禁+提交（10min）【stretch】
- [ ] T202 P1 TTL/SHACL 同步（20min）
- [ ] T203 P1 采购发票+三单匹配+confirm（30min）
- [ ] T204 P1 付款/收款+核销+视图升级（40min）
- [ ] T205 P1 前端发票页+资金核销页+台账升级（25min）
- [ ] T206 P1 mock+snapshot v15+种子+parity（20min）
- [ ] T207 P1 smoke_finance_loop≥14+全门禁+提交（20min）
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
- [x] T103 P0 TTL/SHACL/demo 双绿（22:26 完成）— 证据：validate-type-sync EXIT=0（3 枚举三角同步+3 Shape 在册）；validate-consistency EXIT=0；demo.ttl +3 双类型实例（120×25.5=3060 勾稽）；SHACL pattern DK/INV/AR-YYYYMMDD-XXXX
- [x] T104 P0 发货单后端（23:40 完成）— 证据：探针 8/8 PASS EXIT=0（创建/超发400/扣库存/SALES_ISSUE流水/订单SHIPPED/签收DELIVERED/红字冲回/非法流转400）；pytest 28 passed EXIT=0。注：sd.py +6 端点（GET×2+POST×4），写权限走路由级 _write_gate；Customer 无 customer_name 用 trade_name||legal_name
- [x] T105 P0 发票+应收后端（23:55 完成）— 证据：探针 6/6 PASS EXIT=0（创建INV/超开400/未发货开票400/issue+AR流水勾稽/重复issue400/receivables聚合）；T104 探针回归 8/8；pytest 28 passed。注：sd.py +5 端点；_check_invoice_cap 支持 exclude 自身（issue 复查不重复计数）；账龄桶 current/30/60/90+
- [x] T106 P0 种子+reset 卫生（00:10 完成）— 证据：reset×2 均 EXIT=0 且两轮后 deliveries=2(1 DRAFT/1 SHIPPED)/invoices=1(ISSUED 5300)/AR=1/库存 75=95-20/种子 SALES_ISSUE 流水恰 1 条；upgrade_planning 幂等 0 新增；pytest 28 passed。注：修了一个 UOW FK 乱序（发票 add 后补 flush）；探针残留 22 单已被新清理列表清除
- [x] T107 P0 前端 3 页（00:35 完成）— 证据：npx tsc --noEmit EXIT=0。注：DeliveryList/InvoiceList/ReceivableView 三页 + menuConfig 销售与分销 4→7 项（lucide Truck/Receipt/Wallet）+ App.tsx 路由 ×3；余量/金额上限由后端 400 兜底前端提示；发票页支持 ?customer_id= 下钻预过滤
- [x] T108 P0 mock 同构+snapshot v14（01:25 完成）— 证据：probe-mock-sd.mjs 6/6 EXIT=0（种子2单/创建DK/超发400/ship扣库存+流水/issue+应收聚合/超开400）；check:mock-rbac EXIT=0；tsc EXIT=0。注：版本按实际 13→14（任务行 v15 系笔误，见偏差记录）；探针曾因漏传 query:{} 全 500，已修；snapshot 外科手术式编辑保持原格式
- [x] T109 P0 smoke+parity（01:55 完成）— 证据：smoke_sd_delivery.py 14/14 EXIT=0（设计 3.6 全序列+reset 复位基线 2/1/1）；check_demo_parity.py EXIT=0（31 项含发货单/发票/AR 扩项）；probe-mock-sd 回归 6/6（双目录可跑）；pytest 28 passed。注：reset 新增探针/冒烟标记订单定向清理（修复 parity 残留错配）；冒烟改为起点+终点双 reset 且失败也复位
- [x] T110 P0 全门禁+日志+提交（02:20 完成）— 证据：17 项门禁全绿（本体双校验/alembic/pytest 28/六冒烟/parity 31 项/rbac parity/tsc/双构建/mock-rbac/三探针 8+6+6）；docs/夜间开发日志-20261120.md；设计文档 §十 P0 置 ✅
- [x] T201 P1 本体 5 表+2 枚举（02:30 完成）— 证据：generate_models 44 实体；upgrade_planning EXIT=0；alembic check EXIT=0；generate-types 48 枚举；validate-type-sync EXIT=0；tsc EXIT=0；pytest 28 passed。注：分表 receipt_allocations（设计决策）；付款/收款 status 用 string 内联；踩坑：types.ts 必须用 ontology 生成器单独重生成（generate_models 不覆盖它）
- [x] T202 P1 TTL/SHACL 双绿（02:40 完成）— 证据：validate-type-sync EXIT=0（KEY_ENUMS 含 PaymentMethod 双形状限定）+ validate-consistency EXIT=0；S40-S44 五形状 PI/PAY/RC pattern
- [x] T203 P1 采购发票+三单匹配（03:00 完成）— 证据：probe_purchase_invoice 6/6 EXIT=0（创建PI/超匹配400/confirm/重复confirm400/cancel/未收货PO400）；pytest 28 passed；smoke_purchase_loop 回归 EXIT=0。注：Supplier 主键列名为 supplier_code（非 supplier_id）；purchase.py 需补 User/get_current_user 导入（既有文件从未用过）；5 新表已入 reset 清理列表（核销明细先于父单据、供应商发票先于采购单）；探针遵循 T109 教训起点+终点双 reset
- [x] T204 P1 付款/收款+核销+视图升级（03:25 完成）— 证据：probe_finance_payments 8/8 EXIT=0（付款创建/核销PAID+明细/超发票额400/收款创建/核销→PARTIALLY_PAID+AR负流水/超收核销400/补足→PAID/AP新口径+应收递减）；smoke_purchase_loop 33 OK（AP 断言升级为 P1 口径）；smoke_sd_delivery EXIT=0；parity EXIT=0；pytest 28 passed。注：ap-view 未开票暂估按 PO 净额（扣已批退货）；收款核销同事务冲减 received_amount+状态联动+RECEIPT 流水
- [x] T205 P1 前端 3 页+AP 台账升级（03:55 完成）— 证据：npx tsc --noEmit EXIT=0。注：SupplierInvoiceList/PaymentList（核销对话框 Form.List 多行+合计校验）/ReceiptList；ApView +4 列（已确认发票/已核销/未核销/未开票暂估）；菜单采购+2 销售+1；路由 ×3
- [x] T206 P1 mock v15+parity（04:20 完成）— 证据：probe-mock-finance 9/9（含前置）EXIT=0；probe-mock-sd 回归 6/6；check:mock-rbac EXIT=0；check_demo_parity EXIT=0（集合存在 +5）；tsc EXIT=0；pytest 28 passed。注：snapshot v15 +5 空集合（种子延后决策见偏差记录）；mock ap-view 同步 P1 口径；探针 cap 须取 PO 详情（列表行无单价）
- [x] T207 P1 smoke_finance_loop+全门禁（04:55 完成）— 证据：smoke_finance_loop 15/15 EXIT=0（三单匹配/确认/付款核销/AP 递减/收款核销/账龄勾稽/复位）；全门禁 20 项全绿（本体双校验/alembic/pytest/七冒烟/parity×2/前端×4/六探针）；日志与里程碑已更新
- [x] T301 P2★ 总账实体（05:05 完成）— 证据：generate_models 48 实体；generate-types 52 枚举；upgrade_planning EXIT=0（4 新表）；alembic check EXIT=0；validate-type-sync EXIT=0；tsc EXIT=0；pytest 28 passed
- [x] T302 P2★ 科目种子+gl_rules+GlEngine（05:20 完成）— 证据：gl_rules.py（8 科目+8 事件映射）；gl_engine.py 幂等/平衡/拒绝路径直调验证全过；reset 后 accounts=8/periods=1 保留、entries=0 清空；pytest 28 passed。注：凭证+分录行入 _clear（科目/期间为种子保留）
- [x] T303 P2★ 挂分录 5 处+finance 路由 6 端点+smoke_gl（05:45 完成）— 证据：smoke_gl_loop 11/11 EXIT=0（科目/发票确认分录/金额勾稽/开票分录/发货标准成本分录/付款/收款/试算平衡/发生额/期间/复位）；smoke_finance/sd/purchase 回归 EXIT=0；parity EXIT=0；tsc EXIT=0；pytest 28 passed。注：新路由 finance.py 挂 /api/finance；发货分录=数量×物料标准成本（无成本则跳过并打日志——非沉默，stdout 可见）；GL 失败不阻断业务事务；踩坑 InstrumentedAttribute 无枚举属性（须 import JournalStatus）
- [x] T304 P2★ 全门禁终验（06:00 完成）— 证据：全门禁 24 项全绿（本体×2/alembic/pytest/八冒烟/parity×2/前端×4/六探针）；里程碑 P2 已勾稽（注明前端页未做的边界）
- [x] T401 P2 前端财务管理 3 页（05:30 完成）— 证据：npx tsc --noEmit EXIT=0；/finance 四数据源真实后端 200。注：AccountList/JournalEntryList（展开行分录）/TrialBalance（Σ借=Σ贷 铁律横幅+合计行）；新一级菜单「财务管理」3 项；路由 ×3。P2 前端缺口关闭
## Blocked Tasks
（空）
## Last Checkpoint
2026-11-20 06:05 收尾：P0+P1+P2★ 全部 21 任务完成（22:03–06:05，7h02m/9h）。提交链 T101→T304 共 21 个 night commit（23348ad…9ceed69+本提交）。

## 交接摘要（2026-11-20 06:05）
- **完成**：P0 发货/销售发票/应收三线打通（后端 11 端点+前端 3 页+mock v14）；P1 应付/核销双闭环（采购发票三单匹配、付款/收款核销 13 端点、AP 新口径、前端 3 页、mock v15）；P2★ 总账引擎（4 实体、8 科目种子、GlEngine 幂等/平衡、5 业务钩子、/finance 6 端点、smoke_gl 11 断言）。全门禁 24 项绿。
- **代码状态**：master 干净（仅 DIERP-demo.html 用户未提交改动，全程未触碰）；alembic 基线绿；本体 mappings v1.4.0（52 枚举）；planning.yaml 48 实体。
- **未完成/移交**：① P2 前端财务管理 3 页+mock v16（后端 /finance/* 已就绪）② P3 库存补强+看板资金维度（需先拆原子任务）③ 发票 cancel 红字流程（P1 设计明确未含）④ 期初 opening entry 未做（demo 口径，增量入账）。
- **建议下一步**：下一夜班先补 P2 前端 3 页（约 35min，端点契约见 backend/api/routers/finance.py），再拆 P3 任务清单（对齐 §六+坑清单）。
