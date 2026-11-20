/** mock PR 行级部分转换探针（T903）。用法：node scripts/probe-mock-pr.mjs */
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
  setTimeout, clearTimeout,
}
const workDir = await mkdtemp(path.join(tmpdir(), 'mock-pr-probe-'))
const outfile = path.join(workDir, 'handlers.mjs')
await build({ entryPoints: [path.join(frontendRoot, 'src/mock/handlers.ts')],
  bundle: true, format: 'esm', platform: 'node', outfile, logLevel: 'silent' })
const { handleMockRequest } = await import(pathToFileURL(outfile).href)

const CHECKS = []
const check = (name, cond, detail = '') => {
  CHECKS.push([name, Boolean(cond)])
  console.log(`[${cond ? 'PASS' : 'FAIL'}] ${name} ${cond ? '' : detail}`)
}
const admin = { username: 'admin', role: 'ADMIN', full_name: '系统管理员' }
const call = (method, p, body = null, query = {}) => {
  try {
    const r = handleMockRequest({ method, path: p, query, body, user: admin, config: null })
    return { status: r.status, data: r.data }
  } catch (e) { return { status: e.status ?? 500, data: e.response?.data ?? null } }
}

// 1. 建 3 行申请单
const created = call('POST', '/purchase/purchase-requests', {
  supplier_id: 'SUP-RY', supplier_name: ' Supplier', remarks: 'mock 部分转换探针',
  lines: [
    { material_code: 'RM-FR4-150', quantity: 100, unit: '张', unit_price: 10 },
    { material_code: 'RM-FR4-150', quantity: 50, unit: '张', unit_price: 10 },
    { material_code: 'RM-FR4-150', quantity: 20, unit: '张', unit_price: 10 },
  ],
})
check('1.创建 3 行申请单', created.status === 201 && created.data?.lines?.length === 3,
  JSON.stringify(created.data).slice(0, 150))
const pr = created.data?.purchase_request_number

// 2. 下达
const released = call('POST', `/purchase/purchase-requests/${pr}/release`)
check('2.下达 RELEASED', released.status === 200 && released.data?.status === 'RELEASED')

// 3. 部分转换 30
const partial = call('POST', `/purchase/purchase-requests/${pr}/convert-lines`, {
  lines: [{ line_number: 1, quantity: 30 }],
})
const line1 = (partial.data?.lines ?? []).find((l) => l.line_number === 1)
check('3.部分转换→PARTIALLY_CONVERTED',
  partial.status === 200 && partial.data?.status === 'PARTIALLY_CONVERTED'
    && line1?.converted_quantity === 30 && line1?.remaining_quantity === 70,
  JSON.stringify(line1))
const po1 = partial.data?.new_po_number

// 4. PO 数量正确
const po = call('GET', `/purchase/purchase-orders/${po1}`)
check('4.PO 数量=30', po.status === 200
  && (po.data?.lines ?? []).some((l) => l.quantity === 30))

// 5. 重复行 400
const dup = call('POST', `/purchase/purchase-requests/${pr}/convert-lines`, {
  lines: [{ line_number: 2, quantity: 1 }, { line_number: 2, quantity: 2 }],
})
check('5.重复行 400', dup.status === 400)

// 6. 转满全单→CONVERTED + 多 PO 单号累计
call('POST', `/purchase/purchase-requests/${pr}/convert-lines`, { lines: [{ line_number: 1, quantity: 70 }] })
const done = call('POST', `/purchase/purchase-requests/${pr}/convert-lines`, {
  lines: [{ line_number: 2 }, { line_number: 3 }],
})
const numbers = (done.data?.converted_po_numbers ?? '').split(',').filter(Boolean)
check('6.全转完→CONVERTED+3 张 PO',
  done.status === 200 && done.data?.status === 'CONVERTED' && numbers.length === 3,
  `status=${done.data?.status} po=${numbers.length}`)

await rm(workDir, { recursive: true, force: true })
const passed = CHECKS.filter(([, ok]) => ok).length
console.log(`\n===== mock PR 部分转换探针：${passed}/${CHECKS.length} 通过 =====`)
process.exit(passed === CHECKS.length && CHECKS.length >= 6 ? 0 : 1)
