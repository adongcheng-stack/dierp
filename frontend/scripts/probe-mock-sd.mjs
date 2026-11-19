/**
 * 一次性行为探针：mock 销售域（T108）——发货/发票/应收与后端同构。
 *
 * 用 esbuild 把 src/mock/handlers.ts 打成临时 ESM，在 Node 里直接调用
 * handleMockRequest，6 断言。不依赖浏览器、不写 localStorage。
 *
 * 用法：node scripts/probe-mock-sd.mjs
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

const workDir = await mkdtemp(path.join(tmpdir(), 'mock-sd-probe-'))
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
const H = { method: 'GET', query: {}, user: admin, body: null }
const call = (method, p, body = null) => {
  try {
    const r = handleMockRequest({ ...H, method, path: p, body })
    return { status: r.status, data: r.data }
  } catch (e) {
    return { status: e.status ?? 500, data: e.response?.data ?? null }
  }
}

// 1. 种子发货单：2 张（1 DRAFT / 1 SHIPPED）
const list = call('GET', '/sd/deliveries')
const seeded = list.data?.items ?? []
check(
  '1.种子发货单 2 张（1 DRAFT/1 SHIPPED）',
  list.status === 200 &&
    seeded.length === 2 &&
    seeded.filter((d) => d.status === 'DRAFT').length === 1 &&
    seeded.filter((d) => d.status === 'SHIPPED').length === 1,
  `status=${list.status} items=${seeded.length}`
)

// 2. 创建发货单 201 + DK 前缀（订单 SO-20251231-0001 余量 500-50=450，发 20）
const created = call('POST', '/sd/deliveries', {
  sales_order_number: 'SO-20251231-0001',
  quantity: 20,
  remarks: 'mock 探针',
})
check(
  '2.创建发货单 201/DK/DRAFT',
  created.status === 201 &&
    created.data?.delivery_number?.startsWith('DK-') &&
    created.data?.status === 'DRAFT',
  `status=${created.status} data=${JSON.stringify(created.data).slice(0, 200)}`
)
const dk = created.data?.delivery_number

// 3. 超发 400（发 500 > 余量 430）
const over = call('POST', '/sd/deliveries', {
  sales_order_number: 'SO-20251231-0001',
  quantity: 500,
})
check('3.超发校验 400', over.status === 400, `status=${over.status}`)

// 4. ship → SALES_ISSUE 流水可查（GET /api/mm/transactions）
const shipped = call('POST', `/sd/deliveries/${dk}/ship`)
const txns = call('GET', '/mm/transactions')
const txn = (txns.data?.items ?? txns.data ?? []).find?.(
  (t) => t.reference_number === dk && t.transaction_type === 'SALES_ISSUE'
)
check(
  '4.ship 扣库存+SALES_ISSUE 流水',
  shipped.status === 200 && shipped.data?.status === 'SHIPPED' && Boolean(txn),
  `ship=${shipped.status} txn=${JSON.stringify(txn ?? null).slice(0, 150)}`
)

// 5. 发票 issue → ISSUED + receivables 聚合出现该客户
const inv = call('POST', '/sd/invoices', {
  sales_order_number: 'SO-20251231-0001',
  delivery_number: dk,
  amount: 1000,
})
const issued = inv.status === 201 ? call('POST', `/sd/invoices/${inv.data.invoice_number}/issue`) : { status: 500 }
const recv = call('GET', '/sd/receivables')
const fj002 = (recv.data?.items ?? []).find((r) => r.customer_id === 'FJ002')
check(
  '5.issue→ISSUED+应收聚合',
  inv.status === 201 && issued.status === 200 && issued.data?.status === 'ISSUED' &&
    fj002 && fj002.invoiced_amount >= 6300,
  `inv=${inv.status} issue=${issued.status} recv=${JSON.stringify(fj002 ?? null).slice(0, 200)}`
)

// 6. 超开 400（上限=已发货×单价，再开 5000 超限）
const overInv = call('POST', '/sd/invoices', {
  sales_order_number: 'SO-20251231-0001',
  amount: 5000,
})
check('6.超开校验 400', overInv.status === 400, `status=${overInv.status} data=${JSON.stringify(overInv.data)}`)

await rm(workDir, { recursive: true, force: true })

const passed = CHECKS.filter(([, ok]) => ok).length
console.log(`\n===== mock 销售域探针：${passed}/${CHECKS.length} 通过 =====`)
process.exit(passed === CHECKS.length && CHECKS.length === 6 ? 0 : 1)
