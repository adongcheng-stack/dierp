/**
 * 一次性行为探针：mock 资金域（T206）——采购发票/付款核销/收款核销与后端同构。
 *
 * 6 断言。用法：node scripts/probe-mock-finance.mjs
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

const workDir = await mkdtemp(path.join(tmpdir(), 'mock-fin-probe-'))
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

// 前置：找 RELEASED 采购单并整单收货
const poList = call('GET', '/purchase/purchase-orders')
const po = (poList.data?.items ?? poList.data ?? []).find(
  (x) => x.status === 'RELEASED' && (x.lines ?? []).some((l) => (l.outstanding_quantity ?? 0) > 0)
)
check('前置：存在可收货 RELEASED 采购单', Boolean(po), JSON.stringify(poList.data).slice(0, 150))
const lines = (po.lines ?? [])
  .filter((l) => (l.outstanding_quantity ?? 0) > 0)
  .map((l) => ({ line_number: l.line_number, quantity: l.outstanding_quantity }))
const recv = call('POST', `/purchase/purchase-orders/${po.purchase_order_number}/receive`, { lines })
check('前置：整单收货', recv.status === 200, `status=${recv.status}`)
// 收货后取详情（列表响应行不含单价/收货量），三单匹配上限=Σ已收量×单价
const poDetail = call('GET', `/purchase/purchase-orders/${po.purchase_order_number}`)
const cap = (poDetail.data?.lines ?? []).reduce(
  (s, l) => s + (l.received_quantity ?? 0) * (l.unit_price ?? 0), 0
)

// 1. 采购发票创建 201/PI/DRAFT
const inv = call('POST', '/purchase/supplier-invoices', {
  purchase_order_number: po.purchase_order_number,
  amount: Math.round(cap * 0.8 * 100) / 100,
})
check(
  '1.采购发票创建 201/DRAFT/PI 前缀',
  inv.status === 201 && inv.data?.status === 'DRAFT' && inv.data?.invoice_number?.startsWith('PI-'),
  `status=${inv.status} data=${JSON.stringify(inv.data).slice(0, 150)}`
)
const pi = inv.data?.invoice_number
const confirm = call('POST', `/purchase/supplier-invoices/${pi}/confirm`)
check('前置：发票确认 CONFIRMED', confirm.status === 200 && confirm.data?.status === 'CONFIRMED')

// 2. 付款创建 + 核销 → PAID
const pay = call('POST', '/purchase/payments', {
  supplier_id: po.supplier_id, amount: 400, method: 'TRANSFER',
})
const payDone = pay.status === 201
  ? call('POST', `/purchase/payments/${pay.data.payment_number}/pay`, {
      allocations: [{ invoice_number: pi, allocated_amount: 300 }],
    })
  : { status: 500 }
const payDetail = payDone.status === 200 ? call('GET', `/purchase/payments/${pay.data.payment_number}`) : null
check(
  '2.付款核销→PAID+明细',
  pay.status === 201 && payDone.status === 200 && payDone.data?.status === 'PAID'
    && payDetail?.data?.allocated_amount === 300,
  `pay=${pay.status} done=${payDone.status}`
)

// 3. 核销超发票额 400
const pay2 = call('POST', '/purchase/payments', { supplier_id: po.supplier_id, amount: 5000 })
const over = call('POST', `/purchase/payments/${pay2.data.payment_number}/allocate`, {
  invoice_number: pi, allocated_amount: 99999,
})
check('3.核销超发票额 400', over.status === 400, `status=${over.status}`)

// 4. 收款创建 + 核销（对 mock 种子发票 INV-20251231-0001 部分 1000）
const rc = call('POST', '/sd/receipts', { customer_id: 'FJ002', amount: 1000, method: 'TRANSFER' })
const rcPay = rc.status === 201
  ? call('POST', `/sd/receipts/${rc.data.receipt_number}/pay`, {
      allocations: [{ invoice_number: 'INV-20251231-0001', allocated_amount: 1000 }],
    })
  : { status: 500 }
check(
  '4.收款核销→PAID+发票部分核销',
  rc.status === 201 && rcPay.status === 200 && rcPay.data?.status === 'PAID',
  `rc=${rc.status} pay=${rcPay.status} data=${JSON.stringify(rcPay.data).slice(0, 150)}`
)
const seededInv = call('GET', '/sd/invoices/INV-20251231-0001')
check(
  '5.种子发票 received_amount 冲减+PARTIALLY_PAID',
  seededInv.status === 200 && seededInv.data?.status === 'PARTIALLY_PAID'
    && seededInv.data?.received_amount === 1000,
  `status=${seededInv.status} data=${JSON.stringify(seededInv.data).slice(0, 150)}`
)

// 6. 超收核销 400 + ap-view 新口径字段
const rc2 = call('POST', '/sd/receipts', { customer_id: 'FJ002', amount: 100 })
const overRc = call('POST', `/sd/receipts/${rc2.data.receipt_number}/pay`, {
  allocations: [{ invoice_number: 'INV-20251231-0001', allocated_amount: 99999 }],
})
const ap = call('GET', '/purchase/ap-view')
const apHasNewFields = (ap.data?.items ?? []).every(
  (x) => 'confirmed_invoice_amount' in x && 'uninvoiced_receipt_amount' in x
)
check(
  '6.超收核销 400 + ap-view 新口径',
  overRc.status === 400 && ap.status === 200 && apHasNewFields,
  `over=${overRc.status} ap=${ap.status}`
)

await rm(workDir, { recursive: true, force: true })

const passed = CHECKS.filter(([, ok]) => ok).length
console.log(`\n===== mock 资金域探针：${passed}/${CHECKS.length} 通过 =====`)
process.exit(passed === CHECKS.length && CHECKS.length >= 6 ? 0 : 1)
