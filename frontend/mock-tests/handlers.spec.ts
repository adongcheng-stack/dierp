// Node 侧单元验证：直接驱动 mock handlers 状态机，不依赖浏览器。
// 运行：cd frontend && npx tsx mock-tests/handlers.spec.ts
import { handleMockRequest, MockApiError } from '../src/mock/handlers'

// localStorage 在浏览器/Node 都有；tsx 下 Node 24 已有全局 localStorage。
const store: Record<string, string> = {}
;(globalThis as any).localStorage = {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => {
    store[k] = String(v)
  },
  removeItem: (k: string) => {
    delete store[k]
  },
}
;(globalThis as any).window = globalThis

function call(method: string, path: string, body?: any, query: Record<string, any> = {}, user?: any) {
  return handleMockRequest({
    method,
    path,
    query,
    body: body ?? null,
    user: user ?? { username: 'admin', role: 'ADMIN', full_name: '系统管理员' },
    config: {},
  })
}

let pass = 0
let fail = 0
function check(label: string, ok: boolean) {
  if (ok) {
    pass += 1
    console.log(`  PASS ${label}`)
  } else {
    fail += 1
    console.log(`  FAIL ${label}`)
  }
}

console.log('== 列表接口 ==')
console.log('customers', call('GET', '/sd/customers').data.length)
console.log('quotations', call('GET', '/sd/quotations').data.length)
console.log('salesOrders', call('GET', '/sd/sales-orders').data.length)
console.log('materials', call('GET', '/mm/materials').data.length)
console.log('productionOrders', call('GET', '/pp/production-orders').data.length)
console.log('lotCards', call('GET', '/pp/lot-cards').data.length)
console.log('operationReports', call('GET', '/pp/operation-reports').data.length)
console.log('users', call('GET', '/users').data.length)
console.log('roles', call('GET', '/roles').data.length)
console.log('boms', call('GET', '/eng/boms').data.length)

console.log('== 认证 ==')
const login = call('POST', '/auth/login', { username: 'admin', password: 'admin123' })
check('登录返回 token', Boolean(login.data.access_token))
console.log('me', call('GET', '/auth/me', undefined, {}, { username: 'admin', role: 'ADMIN' }).data)

console.log('== 报价单审批流 ==')
const q = call('GET', '/sd/quotations').data[0]
check('报价详情', call('GET', `/sd/quotations/${q.quotation_number}`).data.quotation_number === q.quotation_number)
console.log('approval-status', call('GET', `/sd/quotations/${q.quotation_number}/approval-status`).data.status)

const newQ = call('POST', '/sd/quotations', {
  customer_id: 'FJ001', product_number: 'HF1004ENIGAB01', quantity: 5, unit_price: 100,
}).data
check('新建报价编号', /^QT-\d{8}-\d{4}$/.test(newQ.quotation_number))
check('新建为 DRAFT', newQ.status === 'DRAFT')
call('POST', `/sd/quotations/${newQ.quotation_number}/submit`, {})
check('提交后 PENDING_SALES', call('GET', `/sd/quotations/${newQ.quotation_number}`).data.status === 'PENDING_SALES')
call('POST', `/sd/quotations/${newQ.quotation_number}/approve`, {})
check('一审 PENDING_GENERAL_MANAGER', call('GET', `/sd/quotations/${newQ.quotation_number}`).data.status === 'PENDING_GENERAL_MANAGER')
call('POST', `/sd/quotations/${newQ.quotation_number}/approve`, {})
check('二审 APPROVED', call('GET', `/sd/quotations/${newQ.quotation_number}`).data.status === 'APPROVED')

console.log('== 销售订单 + 多节点评审 ==')
const newSO = call('POST', '/sd/sales-orders', {
  customer_id: 'FJ001', quotation_number: newQ.quotation_number,
  product_number: newQ.product_number, quantity: 5, unit_price: 100,
  material_code: newQ.product_number, production_version_id: 'PV-HF1004ENIGAB02-V1.0',
}).data
check('新建 SO DRAFT', newSO.status === 'DRAFT')
check('报价已 LINKED', call('GET', `/sd/quotations/${newQ.quotation_number}`).data.status === 'LINKED')
call('POST', `/sd/sales-orders/${newSO.order_number}/submit`, {})
check('SO PENDING_REVIEW', call('GET', `/sd/sales-orders/${newSO.order_number}`).data.status === 'PENDING_REVIEW')
for (let i = 0; i < 4; i += 1) call('POST', `/sd/sales-orders/${newSO.order_number}/approve`, {})
check('四节点后 APPROVED', call('GET', `/sd/sales-orders/${newSO.order_number}`).data.status === 'APPROVED')
console.log('review-status', call('GET', `/sd/sales-orders/${newSO.order_number}/review-status`).data.has_workflow)

console.log('== 生产订单 + LOT 卡 + 状态机 ==')
const newPO = call('POST', '/pp/production-orders', {
  sales_order_number: newSO.order_number, quantity: 5, material_code: newSO.material_code,
}).data
check('新建 PO DRAFT', newPO.status === 'DRAFT')
check('PO 自动生成 LOT', Boolean(newPO.lot_number))
console.log('lotCards 数量', call('GET', '/pp/lot-cards').data.length)
call('POST', `/pp/production-orders/${newPO.order_number}/release`, {})
check('下达 RELEASED', call('GET', `/pp/production-orders/${newPO.order_number}`).data.status === 'RELEASED')
call('POST', `/pp/production-orders/${newPO.order_number}/start`, {})
check('开始 IN_PRODUCTION', call('GET', `/pp/production-orders/${newPO.order_number}`).data.status === 'IN_PRODUCTION')
check('SO 同步 IN_PRODUCTION', call('GET', `/sd/sales-orders/${newSO.order_number}`).data.status === 'IN_PRODUCTION')
call('POST', `/pp/production-orders/${newPO.order_number}/complete`, {})
check('完成 COMPLETED', call('GET', `/pp/production-orders/${newPO.order_number}`).data.status === 'COMPLETED')
call('POST', `/pp/production-orders/${newPO.order_number}/close`, {})
check('关闭 CLOSED', call('GET', `/pp/production-orders/${newPO.order_number}`).data.status === 'CLOSED')

console.log('== 工序报工 ==')
// 新建一张独立的已审批销售订单用于报工测试
const so2 = call('POST', '/sd/sales-orders', {
  customer_id: 'FJ001', quotation_number: 'QT-20251216-0001',
  product_number: 'HF1004ENIGAB02', quantity: 5, unit_price: 100,
  material_code: 'HF1004ENIGAB02', production_version_id: 'PV-HF1004ENIGAB02-V1.0',
}).data
call('POST', `/sd/sales-orders/${so2.order_number}/submit`, {})
for (let i = 0; i < 4; i += 1) call('POST', `/sd/sales-orders/${so2.order_number}/approve`, {})
const po2 = call('POST', '/pp/production-orders', {
  sales_order_number: so2.order_number, quantity: 5, material_code: so2.material_code,
}).data
call('POST', `/pp/production-orders/${po2.order_number}/release`, {})
call('POST', `/pp/production-orders/${po2.order_number}/start`, {})
const wc = call('GET', '/pp/work-centers').data[0]
const or = call('POST', '/pp/operation-reports', {
  production_order_number: po2.order_number, work_center_id: wc.work_center_id, operation_no: '0010', reported_quantity: 2,
}).data
check('报工单号', /^OR-\d{8}-/.test(or.report_number))

console.log('== 领料扣库存 ==')
const matBefore = call('GET', '/mm/materials').data.find((m: any) => m.material_code === newSO.material_code)
call('POST', '/mm/material-issues', {
  production_order_number: po2.order_number, material_code: newSO.material_code, quantity: 1,
})
const matAfter = call('GET', '/mm/materials').data.find((m: any) => m.material_code === newSO.material_code)
check('库存减少 1', Number(matAfter.current_stock) === Number(matBefore.current_stock) - 1)

console.log('== 报价明细计算 ==')
const calc = call('POST', '/sd/quotations/calculate-details', { order_quantity: 10, delivery_length: 200, delivery_width: 150 }).data
check('计算总价', calc.final_total_price > 0)
check('工序明细', Array.isArray(calc.process_details) && calc.process_details.length > 0)

console.log('== 客户审批流 ==')
call('POST', '/sd/customers', { customer_id: 'C-DEMO-001', legal_name: '演示客户' })
check('新客户 DRAFT', call('GET', '/sd/customers/C-DEMO-001').data.customer_status === 'DRAFT')
call('POST', '/sd/customers/C-DEMO-001/submit', {})
check('提交 PENDING_SALES_MANAGER', call('GET', '/sd/customers/C-DEMO-001').data.customer_status === 'PENDING_SALES_MANAGER')
call('POST', '/sd/customers/C-DEMO-001/approve', {})
call('POST', '/sd/customers/C-DEMO-001/approve', {})
check('两次审批后 FROZEN', call('GET', '/sd/customers/C-DEMO-001').data.customer_status === 'FROZEN')
call('POST', '/sd/customers/C-DEMO-001/activate', {})
check('激活 ACTIVE', call('GET', '/sd/customers/C-DEMO-001').data.customer_status === 'ACTIVE')

console.log('== 工艺路线 / MI / PV ==')
const rt = call('GET', '/eng/routings').data.find((r: any) => r.status === 'DRAFT' || r.status === 'REJECTED')
if (rt) {
  call('POST', `/eng/routings/${rt.routing_id}/submit`, {})
  check('工艺路线发布', call('GET', `/eng/routings/${rt.routing_id}`).data.status === 'RELEASED')
} else {
  check('工艺路线发布（快照中已发布，跳过）', true)
}
const mi = call('GET', '/eng/mis').data.find((m: any) => m.status === 'DRAFT')
if (mi) {
  call('POST', `/eng/mis/${mi.mi_number}/submit`, {})
  call('POST', `/eng/mis/${mi.mi_number}/approve`, {})
  check('MI 审批通过', call('GET', `/eng/mis/${mi.mi_number}`).data.status === 'APPROVED')
}

console.log('== 错误路径 ==')
try {
  call('GET', '/sd/customers/NOPE-404')
  check('404 客户', false)
} catch (e) {
  check('404 客户', e instanceof MockApiError && e.status === 404)
}
try {
  call('GET', '/does/not/exist')
  check('404 未实现', false)
} catch (e) {
  check('404 未实现', e instanceof MockApiError && e.status === 404)
}

console.log(`\n通过 ${pass} / 失败 ${fail}`)
process.exit(fail > 0 ? 1 : 0)