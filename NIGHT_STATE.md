# Night State
## Current Task
（空）

## Pending Tasks
- [ ] T903 前端部分转换界面+mock v19+全门禁
- [ ] 长期债剩余：token 静默续期（已用 8h TTL 缓解）/ PR 行级部分转换 / 依赖审计
- [ ] 长期债（设计 §七，不阻塞主线）：实际成本移动加权 / 月结流程 / 遗留表收养迁移 / 前端组件测试 / 依赖审计 / token 静默续期 / PR 行级部分转换

## Completed Tasks
- [x] T902 convert-lines 端点（17:00 完成）— 证据：probe_pr_partial 12/12（部分数量/多次转换/状态联动/重复行/超余量/已转满/整单兼容）；pytest+smoke_purchase+parity 全绿
- [x] T901 PR 部分转换本体（16:45 完成）— 证据：+PARTIALLY_CONVERTED 枚举、+converted_quantity/converted_po_numbers 列；空库 upgrade+check 绿（revision 13289641368f）；开发库真实 ALTER 升级到 head；alembic check/tsc/pytest 全绿
- [x] T805 移动加权全链路终验（16:10 完成）— 证据：smoke_valuation 14/14（收货/发货/红冲/领料/盘点/完工/余额恒等式/数量同步/差异科目/reset）；全门禁 31 项全绿（十冒烟+十探针+E2E 4/4）；设计 §七「实际成本移动加权」长期债偿还
- [x] T804 前端估值视图+mock v18（15:30 完成）— 证据：库存台账+移动均价/金额列、新估值流水页+菜单路由；后端 GET /mm/valuation-moves 与台账估值字段；mock v18（5 估值种子+7 钩子+同构端点）；tsc EXIT=0、E2E 4/4、九冒烟/parity/probe_valuation 全绿。注：后端 8000 需重启加载新枚举（旧进程 500）
- [x] T803 GL 口径切换（14:55 完成）— 证据：smoke_gl_loop 22/22（出库分录金额=估值快照对账、期初分录借1405/贷4001、reset 后仅留期初）；probe_valuation 9/9；mock-gl 探针/pytest/tsc 全绿。注：GlSourceType +OPENING/COST_VARIANCE（PG ALTER TYPE）；科目 6402 存货差异（共 10）；4 处出库分录改用 ValuationMove.amount；期初/负金额差异分录自动过账
- [x] T802 估值服务+期初/7 处收口（14:30 完成）— 证据：grep current_stock 写入仅剩 service 1 处；probe_valuation 9/9（加权/快照红冲/幂等/负金额/除零回退）；九冒烟+pytest 全绿。注：期初种子早于演示发货；收口含 mm/pp/purchase/sd 7 处+演示种子 1 处；采购端点无 current_user 用 system
- [x] T801 移动加权本体（13:50 完成）— 证据：generate_models 53 实体；枚举 56；空库 upgrade head + check 绿（增量 revision 0a76753d37bf）；开发库 stamp head；本体双校验/tsc/pytest 全绿
- [x] T703 全门禁终验（13:10 完成）— 证据：29 项全绿（本体×2/alembic/pytest/九冒烟/parity×2/前端×5 含 E2E 4/4/九探针）；E2E 已纳入门禁
- [x] T701 Alembic 收养迁移（12:55 完成）— 证据：空库 hserp_mvp_adopt_test 从零 upgrade head + alembic check「No new upgrade operations detected」；开发库 stamp e43a92f00037 (head)；pytest 28；四冒烟+parity EXIT=0。注：e43a92f00037 由空库 autogenerate（2375 行），手工补 use_alter 自引用 FK fk_work_center_parent；4 张 MVP 遗留表仍排除
- [x] T603 P3 月结流程（10:40 完成）— 证据：smoke_gl_loop 20/20（预览/结账/反结账+结转后试算平衡）；probe-mock-gl 9/9；全门禁 28 项全绿。注：GlSourceType +PERIOD_CLOSE（PG ALTER TYPE 扩展）；GL_ACCOUNTS 9 科目（+3131 本年利润）；损益结转四行分录（6001/5001/6401/3131）；引擎金额统一量化到分（修浮点不平衡）
- [x] T602 凭证溯源+账龄统一（10:10 完成）— 证据：smoke_gl_loop 17/17（source_ref 过滤/单号过滤）；账龄分桶改按 invoice_date（设计 §4.2）；凭证 source_ref 可点击跳来源单据（8 事件映射）；5 单据页 URL 参数预填单号；四 mock 探针 EXIT=0；tsc EXIT=0；pytest 28 passed。注：批量脚本多次静默丢编辑，改用 edit 工具逐处补齐
- [x] T601 P2 GL 三事件钩子补齐（09:30 完成）— 证据：smoke_gl_loop 15/15（领料/盘点/完工分录+试算平衡）；四 mock 探针回归 EXIT=0；tsc EXIT=0；pytest 28 passed；parity EXIT=0。注：盘盈反向借贷 custom lines；GL 失败记日志不阻断业务
- [x] T507 P3 smoke_inventory_loop+全门禁（09:00 完成）— 证据：smoke_inventory_loop 13/13 EXIT=0（仓库/盘点快照/盘盈/负库存并发 400/状态机/调拨双流水/重复确认/批次效期/KPI 勾稽/复位）；全门禁 31 项全绿（本体×2/alembic/pytest/九冒烟/parity×2/前端×4/九探针）
- [x] T506 P3 mock v17 同构（08:15 完成）— 证据：probe-mock-stock 8/8 EXIT=0 双跑稳定（仓库/盘点快照+diff/盘盈+流水/负库存 400/from=to 400/调拨双流水总量不变/重复确认 400/finance-kpi）；四探针回归 EXIT=0；mock-rbac EXIT=0；parity 集合 +3 EXIT=0；tsc EXIT=0；pytest 28 passed。注：snapshot v17 +warehouses(2 种子)/stocktakes/stockTransfers；finance-kpi mock 聚合同源；踩坑：mock materials 响应为裸数组（探针取数需兼容）
- [x] T505 P3 前端 3 页+看板 KPI 卡（07:55 完成）— 证据：npx tsc --noEmit EXIT=0。注：StocktakeList/StockTransferList/BatchTracking（预警行+估算标注）；经营看板新增资金维度 4 卡（应收/应付/回款率/现金）；菜单 mm 组 +3；路由 ×3。踩坑：看板 Row 插入时孤立了交期风险卡（JSX 单父元素），Dashboard.tsx 修正归位
- [x] T504 P3 批次效期视图+看板 KPI（07:35 完成）— 证据：/mm/batch-tracking 200（ACTIVE 批聚合+estimate_pending/warning 口径）；/dashboard/finance-kpi 200 且应收 5300 与 receivables 台账勾稽、现金 0 与 trial-balance 一致；pytest 28 passed。注：LotCard 无效期字段→completed_at+shelf_life_days 估算（偏差记录）；在制批不告警只标 estimate_pending
- [x] T503 P3 盘点+调拨后端（07:22 完成）— 证据：probe_mm_stock 8/8 EXIT=0 双跑稳定（仓库在册/盘点快照+diff/盘盈+ADJUSTMENT 流水/负库存 400（并发场景）/调拨创建/from=to 400/两笔流水总量不变/重复确认 400）；pytest 28 passed。注：仓库主数据探针幂等（已存在可接受）+reset 标记清理；调拨不动 current_stock 总量
- [x] T502 P3 TTL/SHACL 双绿（07:08 完成）— 证据：validate-type-sync EXIT=0（KEY_ENUMS +2、S45-S47 三形状 STK/TRF pattern）+ validate-consistency EXIT=0
- [x] T501 P3 本体 3 实体+2 枚举（07:02 完成）— 证据：generate_models 51 实体；generate-types 54 枚举；upgrade_planning EXIT=0（3 新表）；alembic check EXIT=0；validate-type-sync EXIT=0；tsc EXIT=0；pytest 28 passed
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
- [x] T402 mock v16 资金域同构（06:00 完成）— 证据：probe-mock-gl 8/8 EXIT=0（科目/确认分录/金额勾稽/付款/开票/发货标准成本/试算平衡/期间）；probe-mock-sd/finance 回归 EXIT=0；mock-rbac EXIT=0；parity 集合 +4 EXIT=0；tsc EXIT=0。注：snapshot v16 +glAccounts(8)/glFiscalPeriods/glJournalEntries/glJournalLines；postMockGl 镜像后端引擎；踩坑：confirm 路由参数 _ctx 而钩子引用 ctx → ReferenceError 被 catch 吞（改用 _ctx 后修复）
- [x] T403 全门禁终验（06:40 完成）— 证据：全门禁 28 项全绿（本体×2/alembic/pytest/八冒烟/parity×2/前端×4/七探针含 mock-gl 8/8）；日志与里程碑 P2 已闭合（后端+前端+mock 全绿）
## Blocked Tasks
（空）
## Last Checkpoint
2026-11-20 16:10 收尾：主线 31 + 补强 3 + 长期债 3 + 移动加权 5 共 42 任务完成，全门禁 31 项绿。交接摘要 v5。

## 交接摘要（2026-11-20 09:00，v3）
- **完成**：P0 三线打通（订单/资金/库存出库）；P1 应付/核销双闭环 + AP 新口径；P2 总账引擎+前端+mock GL；P3 库存补强（盘点/调拨/仓库 11 端点+3 页）+ 批次效期视图 + 看板资金 4 卡。四批次全部「本体→生成→alembic→端点→前端→mock→smoke」节奏闭合。
- **代码状态**：master 干净（仅 DIERP-demo.html 用户未提交改动，全程未触碰）；alembic head 0a76753d37bf；本体 mappings v1.8.0（56 枚举）；planning.yaml 53 实体；mock snapshot v18。
- **未完成/移交（长期债 §七）**：实际成本移动加权 / 月结流程（期间 CLOSE+差异结转）/ 遗留表收养迁移 / 前端组件测试 / 依赖审计 / token 静默续期 / PR 行级部分转换。另：发票红字冲回、期初 opening entry（demo 口径未做）。
- **建议下一步**：主线四批已收官。建议下一夜班从长期债挑「月结流程」（期间 CLOSE+差异结转+收入成本匹配，与总账引擎衔接最紧）或「遗留表收养迁移」（一次性技术债，风险中等）。
