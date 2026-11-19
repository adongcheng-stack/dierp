/**
 * 一次性行为探针：mock 库存补强（T506）——仓库/盘点/调拨与后端同构。
 *
 * 8 断言。用法：node scripts/probe-mock-stock.mjs
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

const workDir = await mkdtemp(path.join(tmpdir(), 'mock-stock-probe-'))
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

const MATERIAL = 'HF1004ENIGAB01'
const rowsOf = (r) => r.data?.items ?? r.data ?? []
const matStock = () => {
  const row = rowsOf(call('GET', '/mm/materials')).find((m) => m.material_code === MATERIAL)
  return Number(row?.current_stock ?? 0)
}
const stock0 = matStock()

// 1. 种子仓库在册（WH-PD01/02）
const wh = call('GET', '/mm/warehouses')
const codes = new Set((wh.data?.items ?? []).map((x) => x.warehouse_code))
check('1.种子仓库 WH-PD01/02 在册', wh.status === 200 && codes.has('WH-PD01') && codes.has('WH-PD02'),
  `status=${wh.status} codes=${[...codes]}`)

// 2. 盘点创建：book 快照 + diff
const inv0 = call('POST', '/mm/stocktakes', { material_code: MATERIAL, counted_qty: Number(stock0) + 5 })
check('2.盘点创建 book 快照+diff',
  inv0.status === 201 && Math.abs(inv0.data?.book_qty - stock0) < 1e-6
    && Math.abs(inv0.data?.diff - 5) < 1e-6 && inv0.data?.stocktake_number?.startsWith('STK-'),
  `status=${inv0.status} data=${JSON.stringify(inv0.data).slice(0, 150)}`)
const stk = inv0.data?.stocktake_number

// 3. 盘盈审批 → 库存 +5 + ADJUSTMENT 流水
call('POST', `/mm/stocktakes/${stk}/approve`)
const txns = rowsOf(call('GET', '/mm/transactions'))
const adj = txns.find((t) => t.transaction_type === 'ADJUSTMENT' && t.reference_number === stk)
const stock1 = matStock()
check('3.盘盈审批→库存校正+ADJUSTMENT 流水',
  Math.abs(stock1 - (Number(stock0) + 5)) < 1e-6 && Boolean(adj) && Math.abs(adj.quantity - 5) < 1e-6,
  `stock=${stock1} adj=${JSON.stringify(adj ?? null).slice(0, 120)}`)

// 4. 盘亏至负 400（并发模拟：stkB 先建单（快照 80，diff −80），stkA 后批（80→50），stkB 再批 → 50−80<0）
const stkB = call('POST', '/mm/stocktakes', { material_code: MATERIAL, counted_qty: 0 })
const stkA = call('POST', '/mm/stocktakes', { material_code: MATERIAL, counted_qty: Number(stock1) - 30 })
call('POST', `/mm/stocktakes/${stkA.data.stocktake_number}/approve`)
const overNeg = call('POST', `/mm/stocktakes/${stkB.data.stocktake_number}/approve`)
check('4.盘亏至负 400', overNeg.status === 400, `status=${overNeg.status}`)

// 5. 调拨创建 201/TRF
const trf = call('POST', '/mm/stock-transfers', {
  from_warehouse_code: 'WH-PD01', to_warehouse_code: 'WH-PD02',
  material_code: MATERIAL, quantity: 10,
})
check('5.调拨创建 201/TRF/DRAFT',
  trf.status === 201 && trf.data?.status === 'DRAFT' && trf.data?.transfer_number?.startsWith('TRF-'),
  `status=${trf.status} data=${JSON.stringify(trf.data).slice(0, 150)}`)

// 6. from=to 400
const badTrf = call('POST', '/mm/stock-transfers', {
  from_warehouse_code: 'WH-PD01', to_warehouse_code: 'WH-PD01',
  material_code: MATERIAL, quantity: 10,
})
check('6.from=to 400', badTrf.status === 400, `status=${badTrf.status}`)

// 7. 确认 → 两笔流水总量不变
const stockBefore = matStock()
call('POST', `/mm/stock-transfers/${trf.data.transfer_number}/confirm`)
const txns2 = rowsOf(call('GET', '/mm/transactions'))
const tOut = txns2.find((t) => t.transaction_type === 'TRANSFER_OUT' && t.reference_number === trf.data.transfer_number)
const tIn = txns2.find((t) => t.transaction_type === 'TRANSFER_IN' && t.reference_number === trf.data.transfer_number)
const stockAfter = matStock()
check('7.调拨确认→两笔流水+总量不变',
  Boolean(tOut) && Math.abs(tOut.quantity + 10) < 1e-6
    && Boolean(tIn) && Math.abs(tIn.quantity - 10) < 1e-6
    && Math.abs(stockAfter - stockBefore) < 1e-6,
  `out=${tOut?.quantity} in=${tIn?.quantity}`)

// 8. 重复确认 400 + finance-kpi 可用
const again = call('POST', `/mm/stock-transfers/${trf.data.transfer_number}/confirm`)
const kpi = call('GET', '/dashboard/finance-kpi')
check('8.重复确认 400 + finance-kpi',
  again.status === 400 && kpi.status === 200 && 'receivable_outstanding' in (kpi.data ?? {}),
  `again=${again.status} kpi=${kpi.status}`)

await rm(workDir, { recursive: true, force: true })

const passed = CHECKS.filter(([, ok]) => ok).length
console.log(`\n===== mock 库存补强探针：${passed}/${CHECKS.length} 通过 =====`)
process.exit(passed === CHECKS.length && CHECKS.length >= 6 ? 0 : 1)
