/**
 * 门禁：mock 写权限门行为验证（与后端 RBAC 同构）。
 *
 * 用 esbuild 把 `src/mock/handlers.ts` 打成临时 ESM，在 Node 里直接调用
 * handleMockRequest，逐条断言状态码。不依赖浏览器、不写 localStorage。
 *
 * 用法：npm run check:mock-rbac
 */
import { build } from 'esbuild'
import { pathToFileURL } from 'node:url'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'

// handlers.ts 不直接访问 window，但它引入的 db.ts 在 getDb() 时会读 localStorage
globalThis.window = {
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  setTimeout,
  clearTimeout,
}

const workDir = await mkdtemp(path.join(tmpdir(), 'mock-rbac-'))
const outfile = path.join(workDir, 'handlers.mjs')

await build({
  entryPoints: [path.resolve('src/mock/handlers.ts')],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile,
  logLevel: 'silent',
})

const { handleMockRequest, MockApiError } = await import(pathToFileURL(outfile).href)

const users = {
  admin: { username: 'admin', role: 'ADMIN', full_name: '系统管理员' },
  planner: { username: 'jihuayuan', role: 'PLANNER', full_name: '计划员' },
  sales: { username: 'yewuyuan', role: 'SALES', full_name: '销业务' },
  warehouse: { username: 'cangkuyuan', role: 'WAREHOUSE', full_name: '仓库员' },
  finance: { username: 'caiwuyuan', role: 'FINANCE', full_name: '财务员' },
}

function call({ method, path: requestPath, user = null, body = null }) {
  try {
    return handleMockRequest({
      method,
      path: requestPath,
      query: {},
      body,
      user,
      config: {},
    })
  } catch (error) {
    if (error instanceof MockApiError) return { status: error.status, data: error.response?.data }
    throw error
  }
}

const cases = [
  ['匿名 GET /sd/customers', { method: 'GET', path: '/sd/customers' }, 200],
  ['匿名 GET /planning/planned-orders', { method: 'GET', path: '/planning/planned-orders' }, 200],
  ['匿名 POST /sd/customers', { method: 'POST', path: '/sd/customers', body: {} }, 401],
  ['匿名 DELETE /pp/production-orders/PO-APS-01', { method: 'DELETE', path: '/pp/production-orders/PO-APS-01' }, 401],
  ['PLANNER POST /sd/customers', { method: 'POST', path: '/sd/customers', user: users.planner, body: {} }, 403],
  ['WAREHOUSE POST /planning/planned-orders/X/release', { method: 'POST', path: '/planning/planned-orders/X/release', user: users.warehouse }, 403],
  ['SALES POST /sd/customers（放行到业务层）', { method: 'POST', path: '/sd/customers', user: users.sales, body: {} }, 'not-403'],
  ['ADMIN POST /sd/customers（恒通过）', { method: 'POST', path: '/sd/customers', user: users.admin, body: {} }, 'not-403'],
  // P0 安全：finance 写门 + users 读门
  ['WAREHOUSE POST /finance/periods/X/close（拒绝）', { method: 'POST', path: '/finance/periods/2026-11/close', user: users.warehouse }, 403],
  ['FINANCE POST /finance/periods/X/close（放行）', { method: 'POST', path: '/finance/periods/2026-11/close', user: users.finance }, 'not-403'],
  ['匿名 GET /users（401）', { method: 'GET', path: '/users' }, 401],
  ['WAREHOUSE GET /users（403）', { method: 'GET', path: '/users', user: users.warehouse }, 403],
  ['ADMIN GET /users（200）', { method: 'GET', path: '/users', user: users.admin }, 200],
]

let failed = 0
for (const [name, request, expected] of cases) {
  const result = call(request)
  const ok =
    expected === 'not-403'
      ? result.status !== 403 && result.status !== 401
      : result.status === expected
  if (!ok) failed += 1
  const detail =
    expected === 'not-403' ? `期望非 403，实际 ${result.status}` : `期望 ${expected}，实际 ${result.status}`
  console.log(`  [${ok ? 'OK ' : 'FAIL'}] ${name}：${ok ? result.status : detail}`)
}

await rm(workDir, { recursive: true, force: true })

if (failed > 0) {
  console.error(`\nmock 写权限门存在 ${failed} 处偏差`)
  process.exit(1)
}
console.log('\nmock 写权限门行为符合预期')
