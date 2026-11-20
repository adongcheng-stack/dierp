/**
 * 一次性行为探针：mock 总账（T402）——业务钩子自动分录与后端同构。
 *
 * 8 断言。用法：node scripts/probe-mock-gl.mjs
 */
import { build } from 'esbuild'
import { pathToFileURL } from 'node:url'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(here, '..')

globalThis.window = {
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  setTimeout,
  clearTimeout,
}

const workDir = await mkdtemp(path.join(tmpdir(), 'mock-gl-probe-'))
const outfile = path.join(workDir, 'handlers.mjs')

await build({
  entryPoints: [path.join(frontendRoot, 'src/mock/handlers.ts')],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile,
  logLevel: 'silent',
})

const { handleMockRequest } = await import(pathToFileURL(outfile).href)

const CHECKS = []
function check(name, cond, detail = '') {
  CHECKS.push([name, Boolean(cond)])
  console.log(`[${cond ? 'PASS' : 'FAIL'}] ${name} ${cond ? '' : detail}`)
}

const admin = { username: 'admin', role: 'ADMIN', full_name: '系统管理员' }
const call = (method, p, body = null) => {
  try {
    const r = handleMockRequest({ method, path: p, query: {}, body, user: admin, config: null })
    return { status: r.status, data: r.data }
  } catch (e) {
    return { status: e.status ?? 500, data: e.response?.data ?? null }
  }
}

// 1. 科目种子 8 个
const accounts = call('GET', '/finance/accounts')
check('1.科目表 9 个一级科目（含本年利润 3131）', accounts.status === 200 && accounts.data?.total === 9,
  `status=${accounts.status} total=${accounts.data?.total}`)

// 2. 采购收货+发票确认 → SUPPLIER_INVOICE_CONFIRMED 分录
const poList = call('GET', '/purchase/purchase-orders')
const po = (poList.data?.items ?? poList.data ?? []).find(
  (x) => x.status === 'RELEASED' && (x.lines ?? []).some((l) => (l.outstanding_quantity ?? 0) > 0)
)
const lines = (po?.lines ?? [])
  .filter((l) => (l.outstanding_quantity ?? 0) > 0)
  .map((l) => ({ line_number: l.line_number, quantity: l.outstanding_quantity }))
call('POST', `/purchase/purchase-orders/${po.purchase_order_number}/receive`, { lines })
const poDetail = call('GET', `/purchase/purchase-orders/${po.purchase_order_number}`)
const cap = (poDetail.data?.lines ?? []).reduce(
  (s, l) => s + (l.received_quantity ?? 0) * (l.unit_price ?? 0), 0
)
const inv = call('POST', '/purchase/supplier-invoices', {
  purchase_order_number: po.purchase_order_number, amount: Math.round(cap * 0.8 * 100) / 100,
})
console.log('[dbg] cap=', cap, 'create=', inv.status, JSON.stringify(inv.data).slice(0, 120))
console.log('[dbg] confirm=', call('POST', `/purchase/supplier-invoices/${inv.data?.invoice_number}/confirm`).status)
const pi = inv.data?.invoice_number
const jeSupplier = call('GET', '/finance/journal-entries', null)
const eSupplier = (jeSupplier.data?.items ?? []).find(
  (e) => e.source_type === 'SUPPLIER_INVOICE_CONFIRMED' && e.source_ref === pi
)
check('2.采购发票确认→分录 POSTED', Boolean(eSupplier) && eSupplier.status === 'POSTED',
  `entry=${eSupplier ? eSupplier.entry_number : 'none'}`)

// 3. 分录行 1405/2202 且金额=发票额、Σ借=Σ贷
if (eSupplier) {
  const detail = call('GET', `/finance/journal-entries/${eSupplier.entry_number}`)
  const l1405 = (detail.data?.lines ?? []).find((l) => l.account_code === '1405')
  const l2202 = (detail.data?.lines ?? []).find((l) => l.account_code === '2202')
  check('3.分录科目金额勾稽(1405/2202)',
    Boolean(l1405) && Boolean(l2202)
      && Math.abs(l1405.debit - inv.data.amount) < 0.01
      && Math.abs(l2202.credit - inv.data.amount) < 0.01,
    JSON.stringify(detail.data).slice(0, 200))
} else {
  check('3.分录科目金额勾稽(1405/2202)', false, 'no entry')
}

// 4. 付款核销 → SUPPLIER_PAYMENT_PAID 分录
const pay = call('POST', '/purchase/payments', { supplier_id: po.supplier_id, amount: 400 })
call('POST', `/purchase/payments/${pay.data.payment_number}/pay`, {
  allocations: [{ invoice_number: pi, allocated_amount: 300 }],
})
const jePay = (call('GET', '/finance/journal-entries').data?.items ?? []).find(
  (e) => e.source_type === 'SUPPLIER_PAYMENT_PAID' && e.source_ref === pay.data.payment_number
)
check('4.付款核销→分录 SUPPLIER_PAYMENT_PAID', Boolean(jePay))

// 5. 销售开票 → SALES_INVOICE_ISSUED 分录
const so = call('POST', '/sd/sales-orders', {
  customer_id: 'FJ002', product_number: 'PN-GL-MOCK', quantity: 10, unit_price: 25.5,
  delivery_date: '2026-02-10T00:00:00', material_code: 'HF1004ENIGAB01', sales_unit: 'PCS',
})
const dkc = call('POST', '/sd/deliveries', { sales_order_number: so.data.order_number, quantity: 10 })
call('POST', `/sd/deliveries/${dkc.data.delivery_number}/ship`)
const sdInv = call('POST', '/sd/invoices', {
  sales_order_number: so.data.order_number, amount: 255,
})
call('POST', `/sd/invoices/${sdInv.data.invoice_number}/issue`)
const jeSales = (call('GET', '/finance/journal-entries').data?.items ?? []).find(
  (e) => e.source_type === 'SALES_INVOICE_ISSUED' && e.source_ref === sdInv.data.invoice_number
)
check('5.开票→分录 SALES_INVOICE_ISSUED', Boolean(jeSales))

// 6. 发货 → SALES_DELIVERY_SHIPPED 分录（标准成本）
const jeShip = (call('GET', '/finance/journal-entries').data?.items ?? []).find(
  (e) => e.source_type === 'SALES_DELIVERY_SHIPPED' && e.source_ref === dkc.data.delivery_number
)
check('6.发货→分录 SALES_DELIVERY_SHIPPED(标准成本)', Boolean(jeShip))

// 7. 余额表 Σ借=Σ贷
const tb = call('GET', '/finance/trial-balance')
check('7.试算平衡 Σ借=Σ贷',
  tb.status === 200 && tb.data?.balanced === true && tb.data?.total_debit > 0,
  `debit=${tb.data?.total_debit} credit=${tb.data?.total_credit}`)

// 8. 期间 2026-11 OPEN
const periods = call('GET', '/finance/periods')
const p = (periods.data?.items ?? []).find((x) => x.period_code === '2026-11')
check('8.当月期间 OPEN', Boolean(p) && p.status === 'OPEN')

// 9. 月结闭环：预览 → 结账 → 反结账
const periodCode = new Date().toISOString().slice(0, 7)
let preview
try {
  const r = handleMockRequest({ method: 'GET', path: '/finance/month-end/preview',
    query: { period_code: periodCode }, body: null, user: admin, config: null })
  preview = { status: r.status, data: r.data }
} catch (e) {
  preview = { status: e.status ?? 500, data: e.response?.data ?? null }
}
const closed = call('POST', `/finance/periods/${periodCode}/close`)
const reopened = call('POST', `/finance/periods/${periodCode}/reopen`)
check('9.月结闭环(预览/CLOSE/REOPEN)',
  preview.status === 200 && preview.data?.balanced === true
    && closed.status === 200 && closed.data?.period_status === 'CLOSED'
    && reopened.status === 200 && reopened.data?.status === 'OPEN',
  `preview=${preview.status} close=${closed.status} reopen=${reopened.status} ${JSON.stringify(closed.data).slice(0,120)}`)

await rm(workDir, { recursive: true, force: true })

const passed = CHECKS.filter(([, ok]) => ok).length
console.log(`\n===== mock 总账探针：${passed}/${CHECKS.length} 通过 =====`)
process.exit(passed === CHECKS.length && CHECKS.length >= 6 ? 0 : 1)
