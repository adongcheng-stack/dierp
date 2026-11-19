import { getDb, saveDb, clone, type MockDb, type MockUser } from './db'
import { applyEquals, nextId, nextNumber, nowIso, paginate, round, safeDecode, searchText, toNumber } from './utils'

export class MockApiError extends Error {
  status: number
  response: any
  isAxiosError = true
  code = 'ERR_BAD_REQUEST'

  constructor(status: number, detail: unknown, config?: any) {
    super(typeof detail === 'string' ? detail : '请求处理失败')
    this.name = 'MockApiError'
    this.status = status
    this.response = {
      status,
      statusText: status === 404 ? 'Not Found' : 'Bad Request',
      data: { detail },
      headers: {},
      config,
    }
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      response: this.response,
    }
  }
}

export interface MockContext {
  method: string
  path: string
  query: Record<string, any>
  body: any
  user: MockUser | null
  config: any
}

interface MockResult {
  status: number
  data: any
}

type Handler = (ctx: MockContext, params: Record<string, string>) => MockResult

const routes: Array<{ method: string; segments: string[]; handler: Handler }> = []

function route(method: string, pattern: string, handler: Handler) {
  routes.push({ method: method.toUpperCase(), segments: pattern.split('/').filter(Boolean), handler })
}

function ok(data: any, status = 200): MockResult {
  return { status, data }
}

function fail(status: number, detail: string): never {
  throw new MockApiError(status, detail)
}

function requireUser(ctx: MockContext): MockUser {
  if (!ctx.user) fail(401, '登录已过期，请重新登录')
  return ctx.user
}

function findItem(items: any[], field: string, value: string | number | undefined) {
  return items.find((item) => String(item?.[field]) === String(value))
}

function requireItem(items: any[], field: string, value: string | number | undefined, label: string) {
  const item = findItem(items, field, value)
  if (!item) fail(404, `${label}不存在: ${value}`)
  return item
}

function listOf(db: MockDb, key: string): any[] {
  if (!Array.isArray(db[key])) db[key] = []
  return db[key]
}

function stampNew<T extends Record<string, any>>(item: T, user?: MockUser | null): T {
  const now = nowIso()
  const value: Record<string, any> = item
  if (value.created_at === undefined) value.created_at = now
  if (value.updated_at === undefined) value.updated_at = now
  if (value.created_by === undefined) value.created_by = user?.username ?? null
  return value as T
}

function customerPayload(body: Record<string, any>): Record<string, any> {
  return {
    ...body,
    addresses: body.addresses ?? body.customer_addresses ?? [],
    contacts: body.contacts ?? body.customer_contacts ?? [],
    partner_functions: body.partner_functions ?? [],
    sales_data: body.sales_data ?? [],
  }
}

function syncQuotationApproval(db: MockDb, quotation: any) {
  if (!db.quotationApprovals) db.quotationApprovals = {}
  const record = db.quotationApprovals[quotation.quotation_number] ?? {
    quotation_number: quotation.quotation_number,
    status: quotation.status,
    workflow_enabled: false,
    approval_history: [],
  }
  record.status = quotation.status
  record.approval_history = record.approval_history ?? []
  db.quotationApprovals[quotation.quotation_number] = record
  return record
}

function pushQuotationHistory(
  db: MockDb,
  quotation: any,
  nodeName: string,
  status: 'APPROVED' | 'REJECTED',
  user: MockUser,
  comment?: string
) {
  const record = syncQuotationApproval(db, quotation)
  record.approval_history.unshift({
    node_name: nodeName,
    status,
    approver: user.username,
    approved_at: nowIso(),
    comment: comment || null,
  })
  record.status = quotation.status
  return record
}

/** 销售订单评审节点（与后端工作流配置一致） */
const REVIEW_NODES = [
  { node_id: 'SALES_REVIEW', node_name: '销售部评审', order: 1, role: 'SALES_MANAGER' },
  { node_id: 'ENGINEERING_REVIEW', node_name: '工程部评审', order: 2, role: 'ENGINEER' },
  { node_id: 'MATERIAL_REVIEW', node_name: '物料部评审', order: 3, role: 'WAREHOUSE' },
  { node_id: 'FINANCE_REVIEW', node_name: '财务部评审', order: 4, role: 'FINANCE' },
]

function ensureReview(db: MockDb, order: any) {
  if (!db.salesOrderReviews) db.salesOrderReviews = {}
  let record = db.salesOrderReviews[order.order_number]
  if (!record || !record.workflow_status) {
    record = {
      has_workflow: false,
      order_status: order.status,
      workflow_status: {
        instance_id: `SALES_ORDER_REVIEW-${order.order_number}-${nowIso().replace(/[-:T]/g, '')}`,
        status: 'PENDING',
        current_node: null,
        nodes: REVIEW_NODES.map((node) => ({
          node_id: node.node_id,
          node_name: node.node_name,
          status: 'PENDING',
          approver: null,
          approved_at: null,
          comment: null,
          order: node.order,
        })),
      },
      review_history: [],
      can_approve: false,
      current_user_role: 'ADMIN',
    }
    db.salesOrderReviews[order.order_number] = record
  }
  record.order_status = order.status
  return record
}

function reviewStatusResponse(db: MockDb, order: any, user: MockUser | null) {
  const record = ensureReview(db, order)
  const pending = order.status === 'PENDING_REVIEW' || order.status === 'REVIEWING'
  return {
    has_workflow: true,
    order_status: order.status,
    workflow_status: record.workflow_status,
    review_history: record.review_history ?? [],
    can_approve: pending,
    current_user_role: user?.role ?? 'ADMIN',
    debug_info: {
      current_user_role: user?.role ?? 'ADMIN',
      current_node_id: record.workflow_status?.current_node ?? null,
      node_approver_role: null,
      can_approve: pending,
      status_data_exists: true,
      has_current_node: Boolean(record.workflow_status?.current_node),
      user_role_str: user?.role ?? 'ADMIN',
      node_role_str: '',
      role_match: true,
    },
  }
}

function syncSalesOrderStatus(db: MockDb, salesOrderNumber: string) {
  const order = findItem(listOf(db, 'salesOrders'), 'order_number', salesOrderNumber)
  if (!order) return
  const productionOrders = listOf(db, 'productionOrders').filter(
    (item) => item.sales_order_number === salesOrderNumber
  )
  if (productionOrders.length === 0) return
  const statuses = productionOrders.map((item) => item.status)
  const allDone = statuses.every((status) => status === 'COMPLETED' || status === 'CLOSED')
  if (allDone) {
    order.status = 'COMPLETED'
    return
  }
  if (statuses.includes('IN_PRODUCTION') && order.status === 'APPROVED') {
    order.status = 'IN_PRODUCTION'
  }
}

function inventoryMaterial(db: MockDb, materialCode: string) {
  const material = findItem(listOf(db, 'materials'), 'material_code', materialCode)
  if (!material) fail(404, `物料不存在: ${materialCode}`)
  return material
}

/** 库存流水账本：领料/到货/退货等每笔库存变动都落一条事务记录。 */
function appendTransaction(
  db: MockDb,
  input: {
    material_code: string
    transaction_type: string
    quantity: number
    unit?: string
    reference_number: string
    reference_type: string
    warehouse?: string | null
    operator?: string | null
    remarks?: string | null
  }
) {
  const rows = listOf(db, 'materialTransactions')
  rows.unshift({
    id: nextId(rows),
    transaction_number: nextNumber(rows, 'transaction_number', 'TR'),
    material_code: input.material_code,
    transaction_type: input.transaction_type,
    quantity: round(input.quantity, 3),
    unit: input.unit ?? 'PCS',
    reference_number: input.reference_number,
    reference_type: input.reference_type,
    warehouse: input.warehouse ?? null,
    transaction_date: nowIso(),
    operator: input.operator ?? null,
    remarks: input.remarks ?? null,
    created_by: input.operator ?? null,
    created_at: nowIso(),
    is_deleted: false,
  })
}

function buildCalculation(body: Record<string, any>, quotation?: any) {
  const orderQuantity = toNumber(body.order_quantity, 1) || 1
  const length = toNumber(body.delivery_length, 0)
  const width = toNumber(body.delivery_width, 0)
  const deliveryArea = round((length * width * orderQuantity) / 1_000_000, 4)
  const actualPInput = Math.max(1, Math.floor(orderQuantity))

  const layers = toNumber(quotation?.layers, 1) || 1
  const layerMultiplier = 1 + (layers - 1) * 0.15
  let costPerM2 = 1000 * layerMultiplier
  let surcharge = toNumber(body.additional_surcharge_per_m2, 0)

  const regular = body.regular_surcharges
  if (regular && typeof regular === 'object') {
    for (const value of Object.values(regular)) {
      if (value) surcharge += 50
    }
  }
  const special = body.special_surcharges
  if (special && typeof special === 'object') {
    for (const value of Object.values(special)) {
      if (value === true) surcharge += 100
      else if (typeof value === 'number' && value > 0) surcharge += value * 10
    }
  }
  costPerM2 += surcharge

  const costPerPcs = deliveryArea > 0 ? costPerM2 * ((length * width) / 1_000_000) : 0
  const engineeringFee = layers > 6 ? 250 : layers > 4 ? 200 : 150
  const boardMaterialFee = deliveryArea > 0 ? costPerM2 * deliveryArea : 0
  const testFixture = toNumber(body.test_points, 0) > 0 ? 500 : 0
  const otherCosts = toNumber(body.min_customer_consumption, 0)
  const finalTotal = round(engineeringFee + boardMaterialFee + testFixture + otherCosts, 2)

  const processDetails = [
    { process_order: 1, process_name: '开料', p_cost_calculation_info: '基础开料成本', process_cost_share: 10 },
    { process_order: 2, process_name: '钻孔', p_cost_calculation_info: `SET孔数: ${toNumber(body.set_hole_count, 0)}`, process_cost_share: 15 },
    { process_order: 3, process_name: '电镀', p_cost_calculation_info: `层数: ${layers}`, process_cost_share: 20 },
    { process_order: 4, process_name: '线路', p_cost_calculation_info: `线宽线距: ${quotation?.min_line_width_spacing ?? 'N/A'}`, process_cost_share: 25 },
    { process_order: 5, process_name: '阻焊', p_cost_calculation_info: `阻焊颜色: ${body.solder_mask_color_detail ?? 'N/A'}`, process_cost_share: 15 },
  ].map((item) => ({
    ...item,
    p_price: round(costPerM2 * (item.process_cost_share / 100), 2),
    delivery_area: deliveryArea,
  }))

  return {
    order_quantity: orderQuantity,
    actual_p_input: actualPInput,
    delivery_area: deliveryArea,
    cost_per_pcs: round(costPerPcs, 2),
    cost_per_m2: round(costPerM2, 2),
    quote_price_per_pcs: round(costPerPcs * 1.3, 2),
    quote_price_per_m2: round(costPerM2 * 1.3, 2),
    engineering_fee: round(engineeringFee, 2),
    board_material_fee: round(boardMaterialFee, 2),
    test_fixture: round(testFixture, 2),
    other_costs: round(otherCosts, 2),
    final_total_price: finalTotal,
    process_details: processDetails,
  }
}

/* ------------------------------- 认证 ------------------------------- */

route('POST', '/auth/login', (ctx) => {
  const db = getDb()
  const username = String(ctx.body?.username ?? '').trim()
  const password = String(ctx.body?.password ?? '')
  const user = findItem(listOf(db, 'users'), 'username', username)
  if (!user || user.is_deleted) {
    fail(400, '用户名或密码错误（演示账号：admin / admin123）')
  }
  if (password !== 'admin123') {
    fail(400, '密码错误（演示环境统一密码：admin123）')
  }
  return ok({ access_token: `mock.${user.username}`, token_type: 'bearer' })
})

route('GET', '/auth/me', (ctx) => {
  const user = requireUser(ctx)
  return ok({
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    department: user.department,
  })
})

/* ------------------------------- 角色/用户 ------------------------------- */

route('GET', '/roles', () => ok(clone(listOf(getDb(), 'roles'))))

route('GET', '/users/me', (ctx) => ok(clone(requireUser(ctx))))

route('GET', '/users', (ctx) => {
  const db = getDb()
  let users = listOf(db, 'users').filter((user) => !user.is_deleted)
  users = applyEquals(users, ctx.query, ['role'])
  if (ctx.query.is_active !== undefined && ctx.query.is_active !== '') {
    const active = String(ctx.query.is_active) === 'true'
    users = users.filter((user) => Boolean(user.is_active) === active)
  }
  return ok(clone(paginate(users, ctx.query)))
})

route('GET', '/users/:id', (_ctx, params) => {
  const db = getDb()
  return ok(clone(requireItem(listOf(db, 'users'), 'id', params.id, '用户')))
})

route('POST', '/users', (ctx) => {
  const db = getDb()
  const users = listOf(db, 'users')
  const user = requireUser(ctx)
  if (!ctx.body?.username) fail(400, '用户名不能为空')
  if (findItem(users, 'username', ctx.body.username)) fail(400, `用户名已存在: ${ctx.body.username}`)
  const item = stampNew(
    {
      id: nextId(users),
      username: ctx.body.username,
      email: ctx.body.email ?? '',
      full_name: ctx.body.full_name ?? '',
      role: ctx.body.role ?? 'SALES',
      department: ctx.body.department ?? '',
      phone: ctx.body.phone ?? null,
      is_active: ctx.body.is_active ?? true,
      created_by: user.username,
      updated_by: null,
    },
    user
  )
  users.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/users/:id', (ctx, params) => {
  const db = getDb()
  const item = requireItem(listOf(db, 'users'), 'id', params.id, '用户')
  const { password: _password, ...rest } = ctx.body ?? {}
  Object.assign(item, rest, { updated_by: requireUser(ctx).username, updated_at: nowIso() })
  saveDb()
  return ok(clone(item))
})

route('DELETE', '/users/:id', (ctx, params) => {
  const db = getDb()
  const user = requireUser(ctx)
  const item = requireItem(listOf(db, 'users'), 'id', params.id, '用户')
  if (item.username === user.username) fail(400, '不能删除自己的账户')
  item.is_deleted = true
  item.is_active = false
  item.updated_by = user.username
  saveDb()
  return { status: 204, data: null }
})

/* ------------------------------- 客户 ------------------------------- */

route('GET', '/sd/customers', (ctx) => {
  const db = getDb()
  let customers = applyEquals(listOf(db, 'customers'), ctx.query, ['customer_status', 'status'])
  customers = searchText(customers, ctx.query, ['customer_id', 'legal_name', 'trade_name'])
  return ok(clone(paginate(customers, ctx.query)))
})

route('GET', '/sd/customers/:id', (_ctx, params) => {
  const customers = listOf(getDb(), 'customers')
  const customer = findItem(customers, 'customer_id', params.id) ?? findItem(customers, 'id', params.id)
  if (!customer) fail(404, `客户不存在: ${params.id}`)
  return ok(clone(customer))
})

route('POST', '/sd/customers', (ctx) => {
  const db = getDb()
  const customers = listOf(db, 'customers')
  const user = requireUser(ctx)
  if (!ctx.body?.customer_id) fail(400, '客户编号不能为空')
  if (findItem(customers, 'customer_id', ctx.body.customer_id)) {
    fail(400, `客户编号已存在: ${ctx.body.customer_id}`)
  }
  const item = stampNew(
    {
      id: nextId(customers),
      customer_status: 'DRAFT',
      ...customerPayload(ctx.body),
    },
    user
  )
  customers.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/sd/customers/:id', (ctx, params) => {
  const db = getDb()
  const customers = listOf(db, 'customers')
  const customer =
    findItem(customers, 'customer_id', params.id) ?? findItem(customers, 'id', params.id)
  if (!customer) fail(404, `客户不存在: ${params.id}`)
  const payload = customerPayload(ctx.body ?? {})
  delete payload.customer_status
  Object.assign(customer, payload, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(customer))
})

route('POST', '/sd/customers/:id/submit', (ctx, params) => {
  const db = getDb()
  const customers = listOf(db, 'customers')
  const customer =
    findItem(customers, 'customer_id', params.id) ?? findItem(customers, 'id', params.id)
  if (!customer) fail(404, `客户不存在: ${params.id}`)
  if (!['DRAFT', 'REJECTED', 'INACTIVE'].includes(customer.customer_status)) {
    fail(400, `当前状态不允许提交审核: ${customer.customer_status}`)
  }
  customer.customer_status = 'PENDING_SALES_MANAGER'
  customer.updated_by = requireUser(ctx).username
  customer.updated_at = nowIso()
  saveDb()
  return ok({ message: '客户已提交审核', status: customer.customer_status })
})

route('POST', '/sd/customers/:id/approve', (ctx, params) => {
  const db = getDb()
  const customers = listOf(db, 'customers')
  const customer =
    findItem(customers, 'customer_id', params.id) ?? findItem(customers, 'id', params.id)
  if (!customer) fail(404, `客户不存在: ${params.id}`)
  if (customer.customer_status === 'PENDING_SALES_MANAGER') {
    customer.customer_status = 'PENDING_GENERAL_MANAGER'
  } else if (customer.customer_status === 'PENDING_GENERAL_MANAGER') {
    customer.customer_status = 'FROZEN'
  } else {
    fail(400, `当前状态不允许审批: ${customer.customer_status}`)
  }
  customer.updated_by = requireUser(ctx).username
  customer.updated_at = nowIso()
  saveDb()
  return ok({ message: '客户已审批通过', status: customer.customer_status })
})

route('POST', '/sd/customers/:id/activate', (ctx, params) => {
  const db = getDb()
  const customers = listOf(db, 'customers')
  const customer =
    findItem(customers, 'customer_id', params.id) ?? findItem(customers, 'id', params.id)
  if (!customer) fail(404, `客户不存在: ${params.id}`)
  if (!['FROZEN', 'PENDING_GENERAL_MANAGER', 'INACTIVE'].includes(customer.customer_status)) {
    fail(400, `当前状态不允许激活: ${customer.customer_status}`)
  }
  customer.customer_status = 'ACTIVE'
  customer.updated_by = requireUser(ctx).username
  customer.updated_at = nowIso()
  saveDb()
  return ok({ message: '客户已激活', status: customer.customer_status })
})

route('POST', '/sd/customers/:id/reject', (ctx, params) => {
  const db = getDb()
  const customers = listOf(db, 'customers')
  const customer =
    findItem(customers, 'customer_id', params.id) ?? findItem(customers, 'id', params.id)
  if (!customer) fail(404, `客户不存在: ${params.id}`)
  customer.customer_status = 'INACTIVE'
  customer.updated_by = requireUser(ctx).username
  customer.updated_at = nowIso()
  saveDb()
  return ok({ message: '客户已拒绝', status: customer.customer_status })
})

/* ------------------------------- 报价单 ------------------------------- */

route('GET', '/sd/quotations/pending-approval', () => {
  const pending = listOf(getDb(), 'quotations').filter((item) =>
    ['PENDING_SALES', 'PENDING_FINANCE', 'PENDING_GENERAL_MANAGER'].includes(item.status)
  )
  return ok(clone(pending))
})

route('POST', '/sd/quotations/calculate-details', (ctx) =>
  ok(buildCalculation(ctx.body ?? {}))
)

route('GET', '/sd/quotations', (ctx) => {
  const db = getDb()
  let quotations = applyEquals(listOf(db, 'quotations'), ctx.query, ['status', 'customer_id'])
  quotations = searchText(quotations, ctx.query, ['quotation_number', 'product_number', 'customer_id'])
  return ok(clone(paginate(quotations, ctx.query)))
})

route('GET', '/sd/quotations/:number', (_ctx, params) => {
  const quotation = findItem(listOf(getDb(), 'quotations'), 'quotation_number', params.number)
  if (!quotation) fail(404, `报价单不存在: ${params.number}`)
  return ok(clone(quotation))
})

route('POST', '/sd/quotations', (ctx) => {
  const db = getDb()
  const quotations = listOf(db, 'quotations')
  const user = requireUser(ctx)
  const quantity = toNumber(ctx.body?.quantity)
  const unitPrice = toNumber(ctx.body?.unit_price)
  const item = stampNew(
    {
      id: nextId(quotations),
      quotation_number: nextNumber(quotations, 'quotation_number', 'QT'),
      status: 'DRAFT',
      total_amount: round(quantity * unitPrice),
      ...ctx.body,
      quantity,
      unit_price: unitPrice,
    },
    user
  )
  item.total_amount = round(quantity * unitPrice)
  quotations.unshift(item)
  syncQuotationApproval(db, item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/sd/quotations/:number', (ctx, params) => {
  const db = getDb()
  const quotation = requireItem(listOf(db, 'quotations'), 'quotation_number', params.number, '报价单')
  Object.assign(quotation, ctx.body ?? {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  quotation.total_amount = round(toNumber(quotation.quantity) * toNumber(quotation.unit_price))
  syncQuotationApproval(db, quotation)
  saveDb()
  return ok(clone(quotation))
})

route('POST', '/sd/quotations/:number/submit', (ctx, params) => {
  const db = getDb()
  const quotation = requireItem(listOf(db, 'quotations'), 'quotation_number', params.number, '报价单')
  if (!['DRAFT', 'REJECTED', 'CUSTOMER_CONFIRMED'].includes(quotation.status)) {
    fail(400, `当前状态不允许提交: ${quotation.status}`)
  }
  quotation.status = 'PENDING_SALES'
  quotation.updated_by = requireUser(ctx).username
  pushQuotationHistory(db, quotation, '提交审核', 'APPROVED', requireUser(ctx), '提交报价审批')
  saveDb()
  return ok({ message: '报价单已提交', status: quotation.status })
})

route('POST', '/sd/quotations/:number/approve', (ctx, params) => {
  const db = getDb()
  const quotation = requireItem(listOf(db, 'quotations'), 'quotation_number', params.number, '报价单')
  const user = requireUser(ctx)
  let nodeName = ''
  if (quotation.status === 'PENDING_SALES') {
    quotation.status = 'PENDING_GENERAL_MANAGER'
    quotation.sales_approver = user.username
    quotation.sales_approved_at = nowIso()
    nodeName = '销售经理审批'
  } else if (quotation.status === 'PENDING_GENERAL_MANAGER') {
    quotation.status = 'APPROVED'
    quotation.general_manager_approver = user.username
    quotation.general_manager_approved_at = nowIso()
    nodeName = '总经理审批'
  } else {
    fail(400, `当前状态不允许审核通过: ${quotation.status}`)
  }
  quotation.updated_by = user.username
  pushQuotationHistory(db, quotation, nodeName, 'APPROVED', user, ctx.body?.comment)
  saveDb()
  return ok({ message: '报价单审核通过', status: quotation.status })
})

route('POST', '/sd/quotations/:number/reject', (ctx, params) => {
  const db = getDb()
  const quotation = requireItem(listOf(db, 'quotations'), 'quotation_number', params.number, '报价单')
  const user = requireUser(ctx)
  if (!ctx.body?.comment) fail(400, '拒绝审核必须填写拒绝原因')
  if (!['PENDING_SALES', 'PENDING_FINANCE', 'PENDING_GENERAL_MANAGER'].includes(quotation.status)) {
    fail(400, `当前状态不允许拒绝: ${quotation.status}`)
  }
  quotation.status = 'REJECTED'
  quotation.updated_by = user.username
  pushQuotationHistory(db, quotation, '审批拒绝', 'REJECTED', user, ctx.body.comment)
  saveDb()
  return ok({ message: '报价单已拒绝', status: quotation.status })
})

route('GET', '/sd/quotations/:number/approval-status', (_ctx, params) => {
  const db = getDb()
  const quotation = requireItem(listOf(db, 'quotations'), 'quotation_number', params.number, '报价单')
  return ok(clone(syncQuotationApproval(db, quotation)))
})

route('POST', '/sd/quotations/:number/calculate-details', (ctx, params) => {
  const quotation = findItem(listOf(getDb(), 'quotations'), 'quotation_number', params.number)
  return ok(buildCalculation(ctx.body ?? {}, quotation))
})

/* ------------------------------- 销售订单 ------------------------------- */

route('GET', '/sd/sales-orders', (ctx) => {
  const db = getDb()
  const orders = applyEquals(listOf(db, 'salesOrders'), ctx.query, ['status', 'customer_id'])
  return ok(clone(paginate(orders, ctx.query)))
})

route('GET', '/sd/sales-orders/:number', (_ctx, params) => {
  const order = findItem(listOf(getDb(), 'salesOrders'), 'order_number', params.number)
  if (!order) fail(404, `销售订单不存在: ${params.number}`)
  return ok(clone(order))
})

route('POST', '/sd/sales-orders', (ctx) => {
  const db = getDb()
  const orders = listOf(db, 'salesOrders')
  const user = requireUser(ctx)
  const quantity = toNumber(ctx.body?.quantity)
  const unitPrice = toNumber(ctx.body?.unit_price)
  const isReturn = Boolean(ctx.body?.is_return_order)
  // 从工厂产品映射解析生产版本（与后端 SalesOrderService 行为一致）
  let productionVersionId = ctx.body?.production_version_id ?? undefined
  if (!productionVersionId && ctx.body?.customer_id && ctx.body?.product_number) {
    const mapping = listOf(db, 'mappings').find(
      (item) =>
        item.customer_id === ctx.body.customer_id &&
        item.factory_product_number === ctx.body.product_number &&
        item.production_version_id
    )
    if (mapping) productionVersionId = mapping.production_version_id
  }
  const item = stampNew(
    {
      id: nextId(orders),
      order_number: nextNumber(orders, 'order_number', 'SO'),
      status: isReturn ? 'PENDING_REVIEW' : 'DRAFT',
      review_status: isReturn ? 'PENDING' : null,
      total_amount: round(quantity * unitPrice),
      currency: 'CNY',
      ...ctx.body,
      quantity,
      unit_price: unitPrice,
      material_code: ctx.body?.material_code || ctx.body?.product_number,
      production_version_id: productionVersionId ?? null,
    },
    user
  )
  orders.unshift(item)
  if (item.quotation_number) {
    const quotation = findItem(listOf(db, 'quotations'), 'quotation_number', item.quotation_number)
    if (quotation) {
      quotation.status = 'LINKED'
      syncQuotationApproval(db, quotation)
    }
  }
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/sd/sales-orders/:number', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  Object.assign(order, ctx.body ?? {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  order.total_amount = round(toNumber(order.quantity) * toNumber(order.unit_price))
  saveDb()
  return ok(clone(order))
})

route('POST', '/sd/sales-orders/:number/submit', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  if (!['DRAFT', 'REJECTED'].includes(order.status)) {
    fail(400, `当前状态不允许提交评审: ${order.status}`)
  }
  const user = requireUser(ctx)
  order.status = 'PENDING_REVIEW'
  order.review_status = 'PENDING'
  order.updated_by = user.username
  const review = ensureReview(db, order)
  review.has_workflow = true
  review.review_history = []
  review.workflow_status.nodes = REVIEW_NODES.map((node) => ({
    node_id: node.node_id,
    node_name: node.node_name,
    status: 'PENDING',
    approver: null,
    approved_at: null,
    comment: null,
    order: node.order,
  }))
  review.workflow_status.status = 'IN_PROGRESS'
  review.workflow_status.current_node = REVIEW_NODES[0].node_id
  saveDb()
  return ok({ message: '销售订单已提交评审', status: order.status })
})

route('POST', '/sd/sales-orders/:number/approve', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  const user = requireUser(ctx)
  if (!['PENDING_REVIEW', 'REVIEWING'].includes(order.status)) {
    fail(400, `订单状态不允许审批，当前状态: ${order.status}`)
  }
  const review = ensureReview(db, order)
  const workflow = review.workflow_status
  const pending = (workflow.nodes as any[]).find((node) => node.status === 'PENDING')
  if (!pending) fail(400, '没有待审批的评审节点')

  pending.status = 'APPROVED'
  pending.approver = user.username
  pending.approved_at = nowIso()
  pending.comment = ctx.body?.comment ?? null

  review.review_history.unshift({
    reviewer_role: user.role,
    reviewer: user.username,
    review_result: 'APPROVED',
    review_comment: ctx.body?.comment ?? null,
    reviewed_at: nowIso(),
  })

  const nextPending = (workflow.nodes as any[]).find((node) => node.status === 'PENDING')
  if (nextPending) {
    workflow.current_node = nextPending.node_id
    workflow.status = 'IN_PROGRESS'
    order.status = 'REVIEWING'
    order.review_status = 'REVIEWING'
  } else {
    workflow.current_node = pending.node_id
    workflow.status = 'COMPLETED'
    order.status = 'APPROVED'
    order.review_status = 'APPROVED'
    if (order.quotation_number) {
      const quotation = findItem(listOf(db, 'quotations'), 'quotation_number', order.quotation_number)
      if (quotation) {
        quotation.status = 'LINKED'
        syncQuotationApproval(db, quotation)
      }
    }
  }
  order.updated_by = user.username
  review.order_status = order.status
  saveDb()
  return ok(clone(order))
})

route('POST', '/sd/sales-orders/:number/reject', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  const user = requireUser(ctx)
  if (!ctx.body?.comment) fail(400, '拒绝审核必须填写拒绝原因')
  if (!['PENDING_REVIEW', 'REVIEWING'].includes(order.status)) {
    fail(400, `订单状态不允许拒绝，当前状态: ${order.status}`)
  }
  const review = ensureReview(db, order)
  const workflow = review.workflow_status
  const pending = (workflow.nodes as any[]).find((node) => node.status === 'PENDING')
  if (pending) {
    pending.status = 'REJECTED'
    pending.approver = user.username
    pending.approved_at = nowIso()
    pending.comment = ctx.body.comment
  }
  workflow.status = 'REJECTED'
  review.review_history.unshift({
    reviewer_role: user.role,
    reviewer: user.username,
    review_result: 'REJECTED',
    review_comment: ctx.body.comment,
    reviewed_at: nowIso(),
  })
  order.status = 'REJECTED'
  order.review_status = 'REJECTED'
  order.updated_by = user.username
  review.order_status = order.status
  saveDb()
  return ok(clone(order))
})

route('GET', '/sd/sales-orders/:number/review-status', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  return ok(clone(reviewStatusResponse(db, order, ctx.user)))
})

function transitionSalesOrder(
  ctx: MockContext,
  params: Record<string, string>,
  from: string[],
  to: string,
  label: string
) {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  if (!from.includes(order.status)) {
    fail(400, `订单状态不允许${label}，当前状态: ${order.status}，需要状态: ${from.join(' / ')}`)
  }
  order.status = to
  order.updated_by = requireUser(ctx).username
  order.updated_at = nowIso()
  saveDb()
  return ok(clone(order))
}

route('POST', '/sd/sales-orders/:number/ship', (ctx, params) =>
  transitionSalesOrder(ctx, params, ['COMPLETED', 'IN_PRODUCTION'], 'SHIPPED', '发货')
)
route('POST', '/sd/sales-orders/:number/deliver', (ctx, params) =>
  transitionSalesOrder(ctx, params, ['SHIPPED'], 'DELIVERED', '签收')
)
route('POST', '/sd/sales-orders/:number/reconcile', (ctx, params) =>
  transitionSalesOrder(ctx, params, ['DELIVERED'], 'RECONCILED', '对账')
)

route('POST', '/sd/sales-orders/:number/close', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'salesOrders'), 'order_number', params.number, '销售订单')
  if (order.status !== 'RECONCILED') {
    fail(400, `订单状态不允许关闭，当前状态: ${order.status}，需要状态: RECONCILED`)
  }
  const user = requireUser(ctx)
  order.status = 'CLOSED'
  order.updated_by = user.username
  order.updated_at = nowIso()
  for (const po of listOf(db, 'productionOrders')) {
    if (po.sales_order_number === order.order_number && !['CLOSED', 'CANCELLED'].includes(po.status)) {
      po.status = 'CLOSED'
      po.actual_finish_date = po.actual_finish_date ?? nowIso()
      po.updated_by = user.username
    }
  }
  saveDb()
  return ok(clone(order))
})

/* ------------------------------- 工厂产品映射 ------------------------------- */

route('GET', '/sd/factory-product-mappings/by-id/:id', (_ctx, params) => {
  const mapping = requireItem(listOf(getDb(), 'mappings'), 'id', params.id, '产品映射')
  return ok(clone(mapping))
})

route('GET', '/sd/factory-product-mappings/:customer/:product', (_ctx, params) => {
  const mapping = listOf(getDb(), 'mappings').find(
    (item) =>
      item.customer_id === params.customer && item.factory_product_number === params.product
  )
  if (!mapping) fail(404, `未找到产品映射: ${params.customer} / ${params.product}`)
  return ok(clone(mapping))
})

route('GET', '/sd/factory-product-mappings', (ctx) => {
  const db = getDb()
  const mappings = applyEquals(listOf(db, 'mappings'), ctx.query, [
    'customer_id',
    'factory_product_number',
    'material_code',
  ])
  return ok(clone(paginate(mappings, ctx.query)))
})

route('POST', '/sd/factory-product-mappings', (ctx) => {
  const db = getDb()
  const mappings = listOf(db, 'mappings')
  const user = requireUser(ctx)
  const duplicated = mappings.find(
    (item) =>
      item.customer_id === ctx.body?.customer_id &&
      item.factory_product_number === ctx.body?.factory_product_number
  )
  if (duplicated) fail(400, '该客户下的工厂产品编号已存在映射')
  const item = stampNew(
    {
      id: nextId(mappings),
      material_code: ctx.body?.material_code || ctx.body?.factory_product_number,
      production_version_id: ctx.body?.production_version_id ?? null,
      is_default: Boolean(ctx.body?.is_default),
      expiry_date: ctx.body?.expiry_date ?? null,
      ...ctx.body,
    },
    user
  )
  mappings.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/sd/factory-product-mappings/:id', (ctx, params) => {
  const db = getDb()
  const mapping = requireItem(listOf(db, 'mappings'), 'id', params.id, '产品映射')
  Object.assign(mapping, ctx.body ?? {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(mapping))
})

route('DELETE', '/sd/factory-product-mappings/:id', (_ctx, params) => {
  const db = getDb()
  const mappings = listOf(db, 'mappings')
  const index = mappings.findIndex((item) => String(item.id) === String(params.id))
  if (index < 0) fail(404, `产品映射不存在: ${params.id}`)
  mappings.splice(index, 1)
  saveDb()
  return { status: 204, data: null }
})

/* ------------------------------- 物料 ------------------------------- */

route('GET', '/mm/materials', (ctx) => {
  const db = getDb()
  let materials = applyEquals(listOf(db, 'materials'), ctx.query, ['status', 'material_type', 'category'])
  materials = searchText(materials, ctx.query, ['material_code', 'material_name'])
  return ok(clone(paginate(materials, ctx.query)))
})

route('GET', '/mm/inventory', (ctx) => {
  const db = getDb()
  let materials = listOf(db, 'materials').filter((m: any) => !m.is_deleted)
  const code = String(ctx.query?.material_code ?? '').trim()
  if (code) materials = materials.filter((m: any) => String(m.material_code).includes(code))

  // 在途：开放采购单行余量按物料汇总（与后端同口径）
  const onOrder: Record<string, number> = {}
  for (const line of listOf(db, 'purchaseOrderLines')) {
    if (line.is_deleted) continue
    const po = listOf(db, 'purchaseOrders').find(
      (o: any) => !o.is_deleted && o.purchase_order_number === line.purchase_order_number
    )
    if (!po || !['RELEASED', 'PARTIALLY_RECEIVED'].includes(String(po.status))) continue
    const outstanding = toNumber(line.quantity) - toNumber(line.received_quantity)
    if (outstanding > 0) {
      onOrder[line.material_code] = (onOrder[line.material_code] ?? 0) + outstanding
    }
  }

  // 已分配：开放工单（RELEASED/IN_PRODUCTION）BOM 组件需求 − 该工单已领料
  const issued: Record<string, number> = {}
  for (const issue of listOf(db, 'materialIssues')) {
    if (issue.is_deleted) continue
    const key = `${issue.production_order_number}|${issue.material_code}`
    issued[key] = (issued[key] ?? 0) + toNumber(issue.quantity)
  }
  const allocated: Record<string, number> = {}
  for (const order of listOf(db, 'productionOrders')) {
    if (order.is_deleted || !['RELEASED', 'IN_PRODUCTION'].includes(String(order.status))) continue
    const bom = listOf(db, 'boms').find(
      (b: any) => !b.is_deleted && b.parent_material_code === order.material_code
    )
    if (!bom || !Array.isArray(bom.items)) continue
    const base = toNumber(bom.base_quantity, 1) || 1
    for (const item of bom.items) {
      const required =
        (toNumber(order.quantity) / base) *
        toNumber(item.quantity) *
        (1 + toNumber(item.scrap_rate) / 100)
      if (required <= 0) continue
      const alreadyIssued = issued[`${order.order_number}|${item.material_code}`] ?? 0
      const net = Math.max(required - alreadyIssued, 0)
      allocated[item.material_code] = (allocated[item.material_code] ?? 0) + net
    }
  }

  return ok(
    materials.map((m: any) => {
      const current = toNumber(m.current_stock)
      const safety = toNumber(m.safety_stock)
      const onOrderQty = round(onOrder[m.material_code] ?? 0, 2)
      const allocatedQty = round(allocated[m.material_code] ?? 0, 2)
      return {
        material_code: m.material_code,
        material_name: m.material_name,
        category: m.category,
        unit: m.unit,
        current_stock: current,
        safety_stock: safety,
        on_order_qty: onOrderQty,
        allocated_qty: allocatedQty,
        available_qty: round(current + onOrderQty - allocatedQty, 2),
        stock_status: current >= safety ? '充足' : '不足',
      }
    })
  )
})

route('GET', '/mm/transactions', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'materialTransactions').filter((t: any) => !t.is_deleted)
  if (ctx.query?.material_code) {
    rows = rows.filter((t: any) => String(t.material_code).includes(String(ctx.query.material_code)))
  }
  if (ctx.query?.transaction_type) {
    rows = rows.filter((t: any) => t.transaction_type === ctx.query.transaction_type)
  }
  if (ctx.query?.reference_type) {
    rows = rows.filter((t: any) => t.reference_type === ctx.query.reference_type)
  }
  rows = rows.sort((a: any, b: any) => String(b.transaction_date).localeCompare(String(a.transaction_date)))
  const withName = rows.map((t: any) => {
    const material = listOf(db, 'materials').find(
      (m: any) => m.material_code === t.material_code
    )
    return { ...clone(t), material_name: material?.material_name ?? null }
  })
  return ok({ total: withName.length, items: clone(paginate(withName, ctx.query)) })
})

route('GET', '/mm/materials/:code', (_ctx, params) => {
  const material = findItem(listOf(getDb(), 'materials'), 'material_code', params.code)
  if (!material) fail(404, `物料不存在: ${params.code}`)
  return ok(clone(material))
})

route('POST', '/mm/materials', (ctx) => {
  const db = getDb()
  const materials = listOf(db, 'materials')
  const user = requireUser(ctx)
  if (!ctx.body?.material_code) fail(400, '物料编码不能为空')
  if (findItem(materials, 'material_code', ctx.body.material_code)) {
    fail(400, `物料编码已存在: ${ctx.body.material_code}`)
  }
  const item = stampNew(
    {
      id: nextId(materials),
      status: 'ACTIVE',
      current_stock: 0,
      safety_stock: 0,
      base_unit: ctx.body?.unit ?? 'PCS',
      production_unit: ctx.body?.unit ?? 'PCS',
      conversion_factor: 1,
      ...ctx.body,
    },
    user
  )
  materials.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/mm/materials/:code', (ctx, params) => {
  const db = getDb()
  const material = requireItem(listOf(db, 'materials'), 'material_code', params.code, '物料')
  Object.assign(material, ctx.body ?? {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(material))
})

/* ------------------------------- 生产领料 ------------------------------- */

route('GET', '/mm/material-issues', (ctx) => {
  const db = getDb()
  const issues = applyEquals(listOf(db, 'materialIssues'), ctx.query, ['production_order_number'])
  return ok(clone(paginate(issues, ctx.query)))
})

route('POST', '/mm/material-issues', (ctx) => {
  const db = getDb()
  const issues = listOf(db, 'materialIssues')
  const user = requireUser(ctx)
  const orderNumber = ctx.body?.production_order_number
  if (!orderNumber) fail(400, '请选择生产订单')
  const order = requireItem(listOf(db, 'productionOrders'), 'order_number', orderNumber, '生产订单')
  const material = inventoryMaterial(db, ctx.body?.material_code)
  const quantity = toNumber(ctx.body?.quantity)
  if (quantity <= 0) fail(400, '领料数量必须大于 0')
  if (quantity > toNumber(material.current_stock)) {
    fail(400, `库存不足: 当前库存 ${material.current_stock} ${material.unit}，需要 ${quantity}`)
  }
  material.current_stock = round(toNumber(material.current_stock) - quantity, 3)
  material.updated_at = nowIso()
  const item = stampNew(
    {
      id: nextId(issues),
      issue_number: nextNumber(issues, 'issue_number', 'MI'),
      production_order_number: order.order_number,
      material_code: material.material_code,
      quantity,
      unit: ctx.body?.unit ?? material.unit,
      issued_by: user.username,
      remarks: ctx.body?.remarks ?? null,
    },
    user
  )
  issues.unshift(item)
  // 库存流水账本：领料即记 ISSUE 出库
  appendTransaction(db, {
    material_code: material.material_code,
    transaction_type: 'ISSUE',
    quantity: -quantity,
    unit: item.unit,
    reference_number: item.issue_number,
    reference_type: 'MATERIAL_ISSUE',
    warehouse: ctx.body?.warehouse ?? null,
    operator: user.username,
    remarks: `生产领料: ${order.order_number}`,
  })
  saveDb()
  return ok(clone(item), 201)
})

/* ------------------------------- BOM ------------------------------- */

route('GET', '/eng/boms', (ctx) => {
  const db = getDb()
  const boms = applyEquals(listOf(db, 'boms'), ctx.query, ['material_code', 'status', 'bom_type'])
  return ok(clone(paginate(boms, ctx.query)))
})

route('GET', '/eng/boms/:number', (_ctx, params) => {
  const bom = findItem(listOf(getDb(), 'boms'), 'bom_number', params.number)
  if (!bom) fail(404, `BOM不存在: ${params.number}`)
  return ok(clone(bom))
})

route('POST', '/eng/boms', (ctx) => {
  const db = getDb()
  const boms = listOf(db, 'boms')
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  if (!body.parent_material_code) fail(400, '请选择父项物料')
  const bomNumber =
    body.bom_number || `BOM-${body.parent_material_code}-${body.version ?? 'A.0'}`
  if (findItem(boms, 'bom_number', bomNumber)) fail(400, `BOM编号已存在: ${bomNumber}`)
  const items = (body.items ?? []).map((item: any, index: number) => ({
    ...item,
    id: index + 1,
    line_number: item.line_number ?? (index + 1) * 10,
  }))
  const item = stampNew(
    {
      id: nextId(boms),
      status: 'NEW',
      plant_id: null,
      base_quantity: 1,
      base_uom: 'PNL',
      description: null,
      effective_date: null,
      expiry_date: null,
      ...body,
      bom_number: bomNumber,
      items,
    },
    user
  )
  boms.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/eng/boms/:number', (ctx, params) => {
  const db = getDb()
  const bom = requireItem(listOf(db, 'boms'), 'bom_number', params.number, 'BOM')
  const body = ctx.body ?? {}
  const items = (body.items ?? []).map((item: any, index: number) => ({
    ...item,
    id: item.id ?? index + 1,
    line_number: item.line_number ?? (index + 1) * 10,
  }))
  Object.assign(bom, body, items.length ? { items } : {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(bom))
})

/* ------------------------------- 工艺路线 ------------------------------- */

route('GET', '/eng/routings', (ctx) => {
  const db = getDb()
  const routings = applyEquals(listOf(db, 'routings'), ctx.query, ['material_code', 'status'])
  return ok(clone(paginate(routings, ctx.query)))
})

route('GET', '/eng/routings/:id/operations', (_ctx, params) => {
  const db = getDb()
  const routing = requireItem(listOf(db, 'routings'), 'routing_id', params.id, '工艺路线')
  return ok(clone(db.routingOperations?.[routing.routing_id] ?? []))
})

route('GET', '/eng/routings/:id', (_ctx, params) => {
  const routing = findItem(listOf(getDb(), 'routings'), 'routing_id', params.id)
  if (!routing) fail(404, `工艺路线不存在: ${params.id}`)
  return ok(clone(routing))
})

route('POST', '/eng/routings', (ctx) => {
  const db = getDb()
  const routings = listOf(db, 'routings')
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  const routingId = body.routing_id || `RT-${body.material_code}-${body.version ?? 'A01'}`
  if (findItem(routings, 'routing_id', routingId)) fail(400, `工艺路线编号已存在: ${routingId}`)
  const operations = (body.operations ?? []).map((operation: any, index: number) => ({
    ...operation,
    id: index + 1,
    routing_id: routingId,
    operation_no: operation.operation_no ?? String((index + 1) * 10).padStart(4, '0'),
  }))
  const item = stampNew(
    {
      id: nextId(routings),
      status: 'DRAFT',
      base_unit: 'PNL',
      base_quantity: 1,
      ...body,
      routing_id: routingId,
    },
    user
  )
  delete item.operations
  routings.unshift(item)
  if (!db.routingOperations) db.routingOperations = {}
  db.routingOperations[routingId] = operations
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/eng/routings/:id', (ctx, params) => {
  const db = getDb()
  const routing = requireItem(listOf(db, 'routings'), 'routing_id', params.id, '工艺路线')
  const body = { ...(ctx.body ?? {}) }
  if (body.operations) {
    if (!db.routingOperations) db.routingOperations = {}
    db.routingOperations[routing.routing_id] = body.operations.map(
      (operation: any, index: number) => ({
        ...operation,
        id: operation.id ?? index + 1,
        routing_id: routing.routing_id,
        operation_no: operation.operation_no ?? String((index + 1) * 10).padStart(4, '0'),
      })
    )
    delete body.operations
  }
  Object.assign(routing, body, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(routing))
})

route('POST', '/eng/routings/:id/submit', (ctx, params) => {
  const db = getDb()
  const routing = requireItem(listOf(db, 'routings'), 'routing_id', params.id, '工艺路线')
  if (!['DRAFT', 'REJECTED'].includes(routing.status)) {
    fail(400, `当前状态不允许提交: ${routing.status}`)
  }
  routing.status = 'RELEASED'
  routing.updated_by = requireUser(ctx).username
  routing.updated_at = nowIso()
  saveDb()
  return ok({ message: '工艺路线已提交', status: routing.status })
})

route('POST', '/eng/routings/:id/reject', (ctx, params) => {
  const db = getDb()
  const routing = requireItem(listOf(db, 'routings'), 'routing_id', params.id, '工艺路线')
  routing.status = 'DRAFT'
  routing.updated_by = requireUser(ctx).username
  saveDb()
  return ok({ message: '工艺路线已退回', status: routing.status })
})

route('POST', '/eng/routings/:id/obsolete', (ctx, params) => {
  const db = getDb()
  const routing = requireItem(listOf(db, 'routings'), 'routing_id', params.id, '工艺路线')
  if (routing.status !== 'RELEASED') {
    fail(400, `只有已发布的工艺路线可以作废，当前状态: ${routing.status}`)
  }
  routing.status = 'OBSOLETE'
  routing.updated_by = requireUser(ctx).username
  routing.updated_at = nowIso()
  saveDb()
  return ok({ message: '工艺路线已作废', status: routing.status })
})

/* ------------------------------- MI ------------------------------- */

route('GET', '/eng/mis', (ctx) => {
  const db = getDb()
  const mis = applyEquals(listOf(db, 'mis'), ctx.query, ['material_code', 'status'])
  return ok(clone(paginate(mis, ctx.query)))
})

route('GET', '/eng/mis/:number', (_ctx, params) => {
  const mi = findItem(listOf(getDb(), 'mis'), 'mi_number', params.number)
  if (!mi) fail(404, `MI不存在: ${params.number}`)
  return ok(clone(mi))
})

route('POST', '/eng/mis', (ctx) => {
  const db = getDb()
  const mis = listOf(db, 'mis')
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  const miNumber = body.mi_number || `MI-${body.material_code}-${body.version ?? 'V1.0'}`
  if (findItem(mis, 'mi_number', miNumber)) fail(400, `MI编号已存在: ${miNumber}`)
  const instructions = (body.instructions ?? []).map((item: any, index: number) => ({
    ...item,
    id: index + 1,
    mi_number: miNumber,
    sequence: item.sequence ?? index + 1,
  }))
  const item = stampNew(
    {
      id: nextId(mis),
      status: 'DRAFT',
      description: null,
      effective_date: null,
      expiry_date: null,
      ...body,
      mi_number: miNumber,
      instructions,
    },
    user
  )
  mis.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/eng/mis/:number', (ctx, params) => {
  const db = getDb()
  const mi = requireItem(listOf(db, 'mis'), 'mi_number', params.number, 'MI')
  const body = { ...(ctx.body ?? {}) }
  if (body.instructions) {
    body.instructions = body.instructions.map((item: any, index: number) => ({
      ...item,
      id: item.id ?? index + 1,
      mi_number: mi.mi_number,
      sequence: item.sequence ?? index + 1,
    }))
  }
  Object.assign(mi, body, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(mi))
})

route('POST', '/eng/mis/:number/submit', (ctx, params) => {
  const db = getDb()
  const mi = requireItem(listOf(db, 'mis'), 'mi_number', params.number, 'MI')
  if (!['DRAFT', 'REJECTED'].includes(mi.status)) {
    fail(400, `当前状态不允许提交: ${mi.status}`)
  }
  mi.status = 'REVIEWING'
  mi.updated_by = requireUser(ctx).username
  saveDb()
  return ok({ message: 'MI已提交审核', status: mi.status })
})

route('POST', '/eng/mis/:number/approve', (ctx, params) => {
  const db = getDb()
  const mi = requireItem(listOf(db, 'mis'), 'mi_number', params.number, 'MI')
  if (mi.status !== 'REVIEWING') fail(400, `当前状态不允许审批: ${mi.status}`)
  mi.status = 'APPROVED'
  mi.approved_by = requireUser(ctx).username
  mi.approved_at = nowIso()
  mi.approval_comment = ctx.body?.comment ?? null
  saveDb()
  return ok({ message: 'MI已审批通过', status: mi.status })
})

route('POST', '/eng/mis/:number/reject', (ctx, params) => {
  const db = getDb()
  const mi = requireItem(listOf(db, 'mis'), 'mi_number', params.number, 'MI')
  if (mi.status !== 'REVIEWING') fail(400, `当前状态不允许驳回: ${mi.status}`)
  mi.status = 'DRAFT'
  mi.approval_comment = ctx.body?.comment ?? null
  saveDb()
  return ok({ message: 'MI已驳回', status: mi.status })
})

/* ------------------------------- 生产版本 ------------------------------- */

route('GET', '/eng/production-versions', (ctx) => {
  const db = getDb()
  const versions = applyEquals(listOf(db, 'productionVersions'), ctx.query, ['material_code', 'status'])
  return ok(clone(paginate(versions, ctx.query)))
})

route('GET', '/eng/production-versions/:id', (_ctx, params) => {
  const version = findItem(
    listOf(getDb(), 'productionVersions'),
    'production_version_id',
    params.id
  )
  if (!version) fail(404, `生产版本不存在: ${params.id}`)
  return ok(clone(version))
})

route('POST', '/eng/production-versions', (ctx) => {
  const db = getDb()
  const versions = listOf(db, 'productionVersions')
  const body = ctx.body ?? {}
  const versionId =
    body.production_version_id || `PV-${body.material_code}-${body.version ?? 'V1.0'}`
  if (findItem(versions, 'production_version_id', versionId)) {
    fail(400, `生产版本已存在: ${versionId}`)
  }
  const material = findItem(listOf(db, 'materials'), 'material_code', body.material_code) ?? null
  const item = stampNew(
    {
      id: nextId(versions),
      status: 'DRAFT',
      is_deleted: false,
      description: null,
      mi_number: null,
      expiry_date: null,
      ...body,
      production_version_id: versionId,
      material,
    },
    requireUser(ctx)
  )
  versions.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/eng/production-versions/:id', (ctx, params) => {
  const db = getDb()
  const version = requireItem(
    listOf(db, 'productionVersions'),
    'production_version_id',
    params.id,
    '生产版本'
  )
  const body = ctx.body ?? {}
  const material =
    findItem(listOf(db, 'materials'), 'material_code', body.material_code ?? version.material_code) ??
    version.material
  Object.assign(version, body, {
    material,
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(version))
})

route('POST', '/eng/production-versions/:id/release', (ctx, params) => {
  const db = getDb()
  const version = requireItem(
    listOf(db, 'productionVersions'),
    'production_version_id',
    params.id,
    '生产版本'
  )
  if (!version.mi_number) fail(400, '发布生产版本时MI必选，请先关联MI')
  const mi = findItem(listOf(db, 'mis'), 'mi_number', version.mi_number)
  if (!mi) fail(404, `MI不存在: ${version.mi_number}`)
  if (mi.status !== 'APPROVED') {
    fail(400, `MI必须已批准才能发布，当前MI状态: ${mi.status}`)
  }
  version.status = 'RELEASED'
  version.updated_by = requireUser(ctx).username
  version.updated_at = nowIso()
  saveDb()
  return ok({
    message: '生产版本发布成功',
    production_version_id: version.production_version_id,
    status: version.status,
  })
})

/* ------------------------------- 工作中心 ------------------------------- */

route('GET', '/pp/work-centers', (ctx) => {
  const db = getDb()
  const centers = applyEquals(listOf(db, 'workCenters'), ctx.query, ['status', 'work_center_type', 'plant_id'])
  return ok(clone(paginate(centers, ctx.query)))
})

route('GET', '/pp/work-centers/:id', (_ctx, params) => {
  const center = findItem(listOf(getDb(), 'workCenters'), 'work_center_id', params.id)
  if (!center) fail(404, `工作中心不存在: ${params.id}`)
  return ok(clone(center))
})

route('POST', '/pp/work-centers', (ctx) => {
  const db = getDb()
  const centers = listOf(db, 'workCenters')
  const body = ctx.body ?? {}
  if (!body.work_center_id) fail(400, '工作中心编号不能为空')
  if (findItem(centers, 'work_center_id', body.work_center_id)) {
    fail(400, `工作中心编号已存在: ${body.work_center_id}`)
  }
  const item = stampNew(
    {
      id: nextId(centers),
      status: 'ACTIVE',
      plant_id: 'SZ-01',
      hierarchy_level: 1,
      capacity_utilization: 100,
      number_of_capacities: 1,
      activity_types: [],
      technical_attributes: [],
      ...body,
    },
    requireUser(ctx)
  )
  centers.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/pp/work-centers/:id', (ctx, params) => {
  const db = getDb()
  const center = requireItem(listOf(db, 'workCenters'), 'work_center_id', params.id, '工作中心')
  Object.assign(center, ctx.body ?? {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(center))
})

/* ------------------------------- 生产订单 ------------------------------- */

route('GET', '/pp/production-orders', (ctx) => {
  const db = getDb()
  const orders = applyEquals(listOf(db, 'productionOrders'), ctx.query, [
    'sales_order_number',
    'status',
  ])
  return ok(clone(paginate(orders, ctx.query)))
})

route('GET', '/pp/production-orders/:number/operations', (_ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'productionOrders'), 'order_number', params.number, '生产订单')
  const operations = db.productionOrderOperations?.[order.order_number] ?? []
  return ok(clone(operations))
})

route('GET', '/pp/production-orders/:number', (_ctx, params) => {
  const order = findItem(listOf(getDb(), 'productionOrders'), 'order_number', params.number)
  if (!order) fail(404, `生产订单不存在: ${params.number}`)
  return ok(clone(order))
})

route('POST', '/pp/production-orders', (ctx) => {
  const db = getDb()
  const orders = listOf(db, 'productionOrders')
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  const salesOrder = requireItem(
    listOf(db, 'salesOrders'),
    'order_number',
    body.sales_order_number,
    '销售订单'
  )
  if (salesOrder.status !== 'APPROVED') {
    fail(400, '销售订单必须已审批才能创建生产订单')
  }
  const versionId = salesOrder.production_version_id || body.production_version_id
  if (!versionId) fail(400, '销售订单缺少生产版本，请先完善销售订单信息')
  const version = requireItem(
    listOf(db, 'productionVersions'),
    'production_version_id',
    versionId,
    '生产版本'
  )
  const quantity = toNumber(body.quantity ?? salesOrder.quantity)
  const unit =
    body.unit ?? version.material?.production_unit ?? salesOrder.production_unit ?? 'PCS'
  const item: any = stampNew(
    {
      id: nextId(orders),
      order_number: nextNumber(orders, 'order_number', 'PO'),
      sales_order_number: salesOrder.order_number,
      status: 'DRAFT',
      sales_quantity: toNumber(salesOrder.quantity),
      sales_unit: salesOrder.sales_unit ?? unit,
      conversion_factor: toNumber(salesOrder.conversion_factor, 1) || 1,
      production_version_id: versionId,
      material_code: body.material_code ?? salesOrder.material_code ?? salesOrder.product_number,
      quantity,
      unit,
      planned_start_date: body.planned_start_date ?? null,
      planned_finish_date: body.planned_finish_date ?? null,
      remarks: body.remarks ?? null,
    },
    user
  )

  const lotCards = listOf(db, 'lotCards')
  const mi = version.mi_number
    ? findItem(listOf(db, 'mis'), 'mi_number', version.mi_number)
    : null
  const instructions = (mi?.instructions ?? []).map((instruction: any, index: number) => ({
    id: index + 1,
    lot_number: '',
    sequence: instruction.sequence ?? index + 1,
    operation_code: instruction.operation_code ?? null,
    operation_name: instruction.operation_name ?? null,
    instruction_type: instruction.instruction_type ?? '',
    instruction_content: instruction.instruction_content ?? '',
    description: instruction.description ?? '',
  }))
  const lotCard = {
    id: nextId(lotCards),
    lot_number: nextNumber(lotCards, 'lot_number', 'LOT'),
    production_order_number: item.order_number,
    mi_number: version.mi_number ?? null,
    material_code: item.material_code,
    quantity,
    unit,
    status: 'ACTIVE',
    created_at: nowIso(),
    completed_at: null,
    remarks: null,
    instructions: instructions.map((instruction: any) => ({
      ...instruction,
      lot_number: '',
    })),
  }
  lotCard.instructions = lotCard.instructions.map((instruction: any) => ({
    ...instruction,
    lot_number: lotCard.lot_number,
  }))
  lotCards.unshift(lotCard)
  item.lot_number = lotCard.lot_number

  const routingOperations = db.routingOperations?.[version.routing_id] ?? []
  if (!db.productionOrderOperations) db.productionOrderOperations = {}
  db.productionOrderOperations[item.order_number] = routingOperations.map(
    (operation: any, index: number) => ({
      ...operation,
      id: index + 1,
      needs_reporting: operation.needs_reporting ?? true,
      auto_deduct_material: operation.auto_deduct_material ?? false,
      trigger_quality_check: operation.trigger_quality_check ?? false,
    })
  )

  orders.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/pp/production-orders/:number', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'productionOrders'), 'order_number', params.number, '生产订单')
  Object.assign(order, ctx.body ?? {}, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(order))
})

function transitionProductionOrder(
  ctx: MockContext,
  params: Record<string, string>,
  from: string[],
  to: string,
  message: string
) {
  const db = getDb()
  const order = requireItem(listOf(db, 'productionOrders'), 'order_number', params.number, '生产订单')
  if (!from.includes(order.status)) {
    fail(400, `生产订单状态不允许该操作，当前状态: ${order.status}`)
  }

  // N4 成品入库口径：报工良品合计；无报工按工单数量。
  // 与后端同构：短报工完工必须拒绝（否则余量永久无法入库）。
  let receiptQty = 0
  if (to === 'COMPLETED') {
    const reports = listOf(db, 'operationReports').filter(
      (r) => !r.is_deleted && r.production_order_number === order.order_number
    )
    const goodQty = reports.reduce((sum, r) => sum + toNumber(r.good_quantity), 0)
    const orderQty = toNumber(order.quantity)
    receiptQty = goodQty > 0 ? goodQty : orderQty
    if (goodQty > 0 && orderQty > 0 && goodQty < orderQty) {
      fail(
        400,
        `报工良品合计 ${goodQty} 小于工单数量 ${orderQty}：请先补齐报工或删除错误报工，再执行完工`
      )
    }
  }

  order.status = to
  order.updated_by = requireUser(ctx).username
  if (to === 'IN_PRODUCTION') order.actual_start_date = nowIso()
  if (to === 'COMPLETED' || to === 'CLOSED') order.actual_finish_date = nowIso()
  if (to === 'COMPLETED' && receiptQty > 0) {
    const material = listOf(db, 'materials').find(
      (m) => !m.is_deleted && m.material_code === order.material_code
    )
    if (material) {
      material.current_stock = toNumber(material.current_stock) + receiptQty
    }
  }
  syncSalesOrderStatus(db, order.sales_order_number)
  saveDb()
  return ok({ message, status: order.status })
}

route('POST', '/pp/production-orders/:number/release', (ctx, params) =>
  transitionProductionOrder(ctx, params, ['DRAFT'], 'RELEASED', '生产订单已下达')
)
route('POST', '/pp/production-orders/:number/start', (ctx, params) =>
  transitionProductionOrder(ctx, params, ['RELEASED'], 'IN_PRODUCTION', '生产订单已开始生产')
)
route('POST', '/pp/production-orders/:number/complete', (ctx, params) =>
  transitionProductionOrder(ctx, params, ['IN_PRODUCTION'], 'COMPLETED', '生产订单已完成')
)
route('POST', '/pp/production-orders/:number/close', (ctx, params) =>
  transitionProductionOrder(ctx, params, ['COMPLETED'], 'CLOSED', '生产订单已关闭')
)

/* ------------------------------- LOT 卡 ------------------------------- */

route('GET', '/pp/lot-cards', (ctx) => {
  const db = getDb()
  const cards = applyEquals(listOf(db, 'lotCards'), ctx.query, [
    'production_order_number',
    'mi_number',
    'status',
  ])
  return ok(clone(paginate(cards, ctx.query)))
})

route('GET', '/pp/lot-cards/by-lot-number/:lot', (_ctx, params) => {
  const card = findItem(listOf(getDb(), 'lotCards'), 'lot_number', params.lot)
  if (!card) fail(404, `LOT卡不存在: ${params.lot}`)
  return ok(clone(card))
})

route('GET', '/pp/lot-cards/:orderNumber', (_ctx, params) => {
  const card = findItem(
    listOf(getDb(), 'lotCards'),
    'production_order_number',
    params.orderNumber
  )
  if (!card) fail(404, `生产订单 ${params.orderNumber} 没有关联的 LOT 卡`)
  return ok(clone(card))
})

route('PUT', '/pp/lot-cards/:lot', (ctx, params) => {
  const db = getDb()
  const card = requireItem(listOf(db, 'lotCards'), 'lot_number', params.lot, 'LOT卡')
  if (ctx.body?.remarks !== undefined) card.remarks = ctx.body.remarks
  if (Array.isArray(ctx.body?.instructions)) {
    card.instructions = ctx.body.instructions.map((instruction: any, index: number) => ({
      ...instruction,
      id: instruction.id ?? index + 1,
      lot_number: card.lot_number,
      sequence: instruction.sequence ?? index + 1,
    }))
  }
  card.updated_by = requireUser(ctx).username
  card.updated_at = nowIso()
  saveDb()
  return ok(clone(card))
})

/* ------------------------------- 工序报工 ------------------------------- */

route('GET', '/pp/operation-reports', (ctx) => {
  const db = getDb()
  const reports = applyEquals(listOf(db, 'operationReports'), ctx.query, [
    'production_order_number',
    'work_center_id',
  ])
  return ok(clone(paginate(reports, ctx.query)))
})

route('POST', '/pp/operation-reports', (ctx) => {
  const db = getDb()
  const reports = listOf(db, 'operationReports')
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  const order = requireItem(
    listOf(db, 'productionOrders'),
    'order_number',
    body.production_order_number,
    '生产订单'
  )
  if (order.status !== 'IN_PRODUCTION') {
    fail(400, `生产订单状态不允许报工: 当前状态为 ${order.status}，只有生产中的订单才能报工`)
  }
  const lotCard = listOf(db, 'lotCards').find(
    (card) => card.production_order_number === order.order_number
  )
  if (!lotCard) fail(400, `生产订单 ${order.order_number} 没有关联的 LOT 卡，无法报工`)
  requireItem(listOf(db, 'workCenters'), 'work_center_id', body.work_center_id, '工作中心')
  const reportedQuantity = toNumber(body.reported_quantity)
  const suffix = order.order_number.slice(-4)
  let reportNumber = `OR-${nowIso().slice(0, 10).replace(/-/g, '')}-${suffix}`
  if (findItem(reports, 'report_number', reportNumber)) {
    reportNumber = `${reportNumber}-${Math.floor(1000 + Math.random() * 9000)}`
  }
  const item = stampNew(
    {
      id: nextId(reports),
      report_number: reportNumber,
      production_order_number: order.order_number,
      lot_number: lotCard.lot_number,
      routing_operation_id: body.routing_operation_id ?? null,
      work_center_id: body.work_center_id,
      operation_no: body.operation_no,
      operation_name: body.operation_name ?? null,
      reported_quantity: reportedQuantity,
      good_quantity: body.good_quantity ?? reportedQuantity,
      scrap_quantity: toNumber(body.scrap_quantity),
      setup_time: toNumber(body.setup_time),
      machine_time: toNumber(body.machine_time),
      labor_time: toNumber(body.labor_time),
      status: 'PENDING',
      reported_by: user.username,
      reported_at: nowIso(),
      remarks: body.remarks ?? null,
    },
    user
  )
  reports.unshift(item)
  saveDb()
  return ok(clone(item), 201)
})

/* ------------------------------- 计划管理 ------------------------------- */

const PLANNING_DATE = (value: any): string => String(value ?? '').slice(0, 10)

function planningAddDays(value: any, days: number): string {
  const date = new Date(`${PLANNING_DATE(value) || nowIso().slice(0, 10)}T00:00:00`)
  date.setDate(date.getDate() + days)
  const pad = (input: number) => String(input).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    'T00:00:00'
  )
}

function planningWeekStart(value: any): string {
  const date = new Date(`${PLANNING_DATE(value)}T00:00:00`)
  const day = date.getDay()
  const offset = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + offset)
  const pad = (input: number) => String(input).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T00:00:00`
}

function planningPolicyFor(db: MockDb, materialCode: string): any | null {
  return (
    listOf(db, 'planningPolicies').find(
      (item) => item.material_code === materialCode && !item.is_deleted
    ) ?? null
  )
}

function planningActiveBom(db: MockDb, materialCode: string): any | null {
  return (
    listOf(db, 'boms').find(
      (bom) =>
        bom.parent_material_code === materialCode &&
        ['RELEASED', 'ACTIVE'].includes(bom.status)
    ) ?? null
  )
}

function planningMaterial(db: MockDb, materialCode: string): any | null {
  return listOf(db, 'materials').find((item) => item.material_code === materialCode) ?? null
}

function planningUnit(material: any): string {
  return material?.base_unit ?? material?.unit ?? 'PCS'
}

function planningLotSize(shortage: number, policy: any | null): number {
  let quantity = Math.max(0, shortage)
  if (!policy) return round(quantity, 2)
  const rule = policy.lot_sizing_rule ?? 'LOT_FOR_LOT'
  if (rule === 'FIXED_LOT' && toNumber(policy.fixed_lot_size) > 0) {
    const fixed = toNumber(policy.fixed_lot_size)
    quantity = Math.ceil(quantity / fixed) * fixed
  } else if (rule === 'EOQ' && toNumber(policy.eoq) > 0) {
    const eoq = toNumber(policy.eoq)
    quantity = Math.ceil(quantity / eoq) * eoq
  }
  quantity = Math.max(quantity, toNumber(policy.min_order_qty))
  const multiple = toNumber(policy.order_multiple, 1)
  if (multiple > 1) quantity = Math.ceil(quantity / multiple) * multiple
  const maxOrder = toNumber(policy.max_order_qty)
  if (maxOrder > 0) quantity = Math.min(quantity, maxOrder)
  return round(quantity, 2)
}

function planningSummaryMps(plan: any) {
  return {
    id: plan.id,
    mps_number: plan.mps_number,
    version: plan.version,
    plan_name: plan.plan_name,
    plant_id: plan.plant_id,
    horizon_start: plan.horizon_start,
    horizon_end: plan.horizon_end,
    bucket_type: plan.bucket_type,
    status: plan.status,
    demand_source: plan.demand_source,
    total_gross: plan.total_gross,
    total_planned: plan.total_planned,
    generated_by: plan.generated_by,
    generated_at: plan.generated_at,
    created_at: plan.created_at,
  }
}

route('GET', '/planning/overview', () => {
  const db = getDb()
  const runs = listOf(db, 'mrpRuns')
  const latestRun = runs.reduce(
    (latest: any, item: any) => (!latest || Number(item.id) > Number(latest.id) ? item : latest),
    null
  )
  const exceptions = listOf(db, 'mrpExceptions').filter(
    (item) => !item.is_deleted && item.resolution_status === 'OPEN'
  )
  const shortKits = listOf(db, 'kittingResults').filter(
    (item) => !item.is_deleted && ['SHORT', 'PARTIAL'].includes(item.kit_status)
  )
  return ok({
    latest_run: latestRun ?? null,
    mps_draft: listOf(db, 'mpsPlans').filter(
      (item) => !item.is_deleted && item.status === 'DRAFT'
    ).length,
    mps_released: listOf(db, 'mpsPlans').filter(
      (item) => !item.is_deleted && item.status === 'RELEASED'
    ).length,
    open_exceptions: exceptions.length,
    critical_exceptions: exceptions.filter((item) => item.severity === 'CRITICAL').length,
    short_kits: shortKits.length,
    planned_orders_open: listOf(db, 'plannedOrders').filter(
      (item) => !item.is_deleted && ['PLANNED', 'FIRMED'].includes(item.status)
    ).length,
    forecasts: listOf(db, 'forecasts').filter((item) => !item.is_deleted).length,
    policies: listOf(db, 'planningPolicies').filter(
      (item) => !item.is_deleted && item.is_active
    ).length,
  })
})

route('POST', '/planning/mps/generate', (ctx) => {
  const db = getDb()
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  if (!body.horizon_start || !body.horizon_end) fail(400, '计划区间不能为空')
  const start = PLANNING_DATE(body.horizon_start)
  const end = PLANNING_DATE(body.horizon_end)
  const plans = listOf(db, 'mpsPlans')
  const entries = listOf(db, 'mpsEntries')
  const mpsNumber = nextNumber(plans, 'mps_number', 'MPS')
  const includeForecast = body.include_forecast !== false
  const demandSource = body.demand_source ?? 'MIXED'
  const buckets = new Map<string, any>()

  const ensureBucket = (materialCode: string, bucketDate: string) => {
    const key = `${materialCode}|${bucketDate}`
    if (!buckets.has(key)) {
      buckets.set(key, {
        material_code: materialCode,
        bucket_date: bucketDate,
        sales_demand: 0,
        forecast_demand: 0,
      })
    }
    return buckets.get(key)
  }

  if (demandSource !== 'FORECAST') {
    for (const order of listOf(db, 'salesOrders')) {
      if (order.is_deleted) continue
      if (!['APPROVED', 'IN_PRODUCTION'].includes(order.status)) continue
      const due = PLANNING_DATE(order.delivery_date)
      if (!due || due < start || due > end) continue
      if (!order.material_code) continue
      const bucket = ensureBucket(order.material_code, planningWeekStart(order.delivery_date))
      bucket.sales_demand += toNumber(order.quantity)
    }
  }

  if (includeForecast && demandSource !== 'SALES' && demandSource !== 'MPS') {
    for (const forecast of listOf(db, 'forecasts')) {
      if (forecast.is_deleted) continue
      if (!['RELEASED', 'DRAFT', 'CONFIRMED'].includes(forecast.status)) continue
      const due = PLANNING_DATE(forecast.due_date)
      if (!due || due < start || due > end) continue
      const openQty = Math.max(
        0,
        toNumber(forecast.quantity) - toNumber(forecast.consumed_quantity)
      )
      if (!openQty) continue
      const bucket = ensureBucket(forecast.material_code, planningWeekStart(forecast.due_date))
      bucket.forecast_demand += openQty
    }
  }

  if (body.include_safety_stock !== false) {
    for (const policy of listOf(db, 'planningPolicies')) {
      if (policy.is_deleted || !policy.is_active) continue
      const safetyStock = toNumber(policy.safety_stock)
      if (safetyStock <= 0) continue
      const material = planningMaterial(db, policy.material_code)
      if (!material || material.material_type === 'RAW') continue
      const bucket = ensureBucket(policy.material_code, planningWeekStart(start))
      bucket.safety_demand = safetyStock
    }
  }

  if (buckets.size === 0) fail(400, '计划区间内没有可纳入的需求，请检查销售订单、预测与计划区间')

  const materialCodes = [...new Set([...buckets.values()].map((item) => item.material_code))]
  const openingByMaterial = new Map<string, number>()
  for (const materialCode of materialCodes) {
    const material = planningMaterial(db, materialCode)
    openingByMaterial.set(materialCode, toNumber(material?.current_stock))
  }

  const rows: any[] = []
  let totalGross = 0
  let totalPlanned = 0
  let lineNumber = 0
  for (const materialCode of materialCodes) {
    const materialBuckets = [...buckets.values()]
      .filter((item) => item.material_code === materialCode)
      .sort((a, b) => String(a.bucket_date).localeCompare(String(b.bucket_date)))
    const policy = planningPolicyFor(db, materialCode)
    const safety = toNumber(policy?.safety_stock)
    let opening = openingByMaterial.get(materialCode) ?? 0
    for (const bucket of materialBuckets) {
      const gross = round(bucket.sales_demand + bucket.forecast_demand, 2)
      const projectedBefore = round(opening - gross, 2)
      const net = round(Math.max(0, safety - projectedBefore), 2)
      const projected = round(projectedBefore + net, 2)
      lineNumber += 1
      rows.push({
        id: nextId(entries) + rows.length,
        mps_number: mpsNumber,
        line_number: lineNumber,
        material_code: materialCode,
        bucket_date: bucket.bucket_date,
        opening_stock: opening,
        gross_requirement: gross,
        sales_demand: round(bucket.sales_demand, 2),
        forecast_demand: round(bucket.forecast_demand, 2),
        scheduled_receipt: 0,
        projected_available: projected,
        net_requirement: net,
        planned_receipt: net,
        planner_action: net > 0 ? 'RELEASE' : 'NONE',
      })
      totalGross += gross
      totalPlanned += net
      opening = projected
    }
  }

  const plan = {
    id: nextId(plans),
    mps_number: mpsNumber,
    version: '1',
    plan_name: body.plan_name ?? `MPS ${start}`,
    plant_id: body.plant_id ?? null,
    horizon_start: `${start}T00:00:00`,
    horizon_end: `${end}T00:00:00`,
    bucket_type: 'WEEK',
    status: 'DRAFT',
    demand_source: demandSource,
    total_gross: round(totalGross, 2),
    total_planned: round(totalPlanned, 2),
    generated_by: user.username,
    generated_at: nowIso(),
    created_at: nowIso(),
    is_deleted: false,
  }
  plans.unshift(plan)
  entries.push(...rows)
  saveDb()
  return ok(planningSummaryMps(plan), 201)
})

route('GET', '/planning/mps', (ctx) => {
  const db = getDb()
  let plans = applyEquals(listOf(db, 'mpsPlans'), ctx.query, ['status'])
  plans = plans.filter((item) => !item.is_deleted)
  plans.sort((a, b) => String(b.horizon_start).localeCompare(String(a.horizon_start)))
  return ok({ total: plans.length, items: clone(paginate(plans, ctx.query)) })
})

route('GET', '/planning/mps/:mpsNumber', (_ctx, params) => {
  const db = getDb()
  const plan = requireItem(listOf(db, 'mpsPlans'), 'mps_number', params.mpsNumber, 'MPS 计划')
  const entries = listOf(db, 'mpsEntries')
    .filter((item) => item.mps_number === plan.mps_number && !item.is_deleted)
    .sort((a, b) =>
      `${a.material_code}-${a.bucket_date}`.localeCompare(`${b.material_code}-${b.bucket_date}`)
    )
  return ok({ ...planningSummaryMps(plan), entries: clone(entries) })
})

route('POST', '/planning/mps/:mpsNumber/release', (ctx, params) => {
  const db = getDb()
  const plan = requireItem(listOf(db, 'mpsPlans'), 'mps_number', params.mpsNumber, 'MPS 计划')
  if (plan.status !== 'DRAFT') fail(400, `当前状态不允许下达: ${plan.status}`)
  plan.status = 'RELEASED'
  plan.released_by = requireUser(ctx).username
  plan.released_at = nowIso()
  saveDb()
  return ok(planningSummaryMps(plan))
})

route('POST', '/planning/mps/:mpsNumber/close', (ctx, params) => {
  const db = getDb()
  const plan = requireItem(listOf(db, 'mpsPlans'), 'mps_number', params.mpsNumber, 'MPS 计划')
  plan.status = 'CLOSED'
  plan.updated_by = requireUser(ctx).username
  saveDb()
  return ok(planningSummaryMps(plan))
})

route('POST', '/planning/mrp/run', (ctx) => {
  const db = getDb()
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  if (!body.horizon_start || !body.horizon_end) fail(400, '计划区间不能为空')
  const start = PLANNING_DATE(body.horizon_start)
  const end = PLANNING_DATE(body.horizon_end)
  const runs = listOf(db, 'mrpRuns')
  const requirements = listOf(db, 'mrpRequirements')
  const exceptions = listOf(db, 'mrpExceptions')
  const plannedOrders = listOf(db, 'plannedOrders')
  const pegging = listOf(db, 'peggingLinks')
  const runNumber = nextNumber(runs, 'run_number', 'MRP')
  const startedAt = nowIso()

  let resolvedSource = body.demand_source ?? 'AUTO'
  let mpsNumber: string | null = null
  const independent: any[] = []

  const mpsPlans = listOf(db, 'mpsPlans').filter((item) => !item.is_deleted)
  let mps: any | null = null
  if (resolvedSource === 'AUTO' || resolvedSource === 'MPS') {
    if (body.mps_number) {
      mps = mpsPlans.find((item) => item.mps_number === body.mps_number) ?? null
      if (!mps) fail(404, `MPS 计划不存在: ${body.mps_number}`)
    } else {
      mps =
        mpsPlans
          .filter((item) => item.status === 'RELEASED')
          .sort((a, b) => String(b.horizon_start).localeCompare(String(a.horizon_start)))[0] ??
        null
    }
    if (mps) {
      resolvedSource = 'MPS'
      mpsNumber = mps.mps_number
      for (const entry of listOf(db, 'mpsEntries')) {
        if (entry.mps_number !== mps.mps_number || entry.is_deleted) continue
        if (toNumber(entry.net_requirement) <= 0) continue
        const due = PLANNING_DATE(entry.bucket_date)
        if (due < start || due > end) continue
        independent.push({
          material_code: entry.material_code,
          quantity: toNumber(entry.net_requirement),
          due_date: entry.bucket_date,
          demand_type: 'MPS',
          demand_ref: mps.mps_number,
          level: 0,
          independent: true,
        })
      }
    }
  }

  if (independent.length === 0) {
    resolvedSource = resolvedSource === 'FORECAST' ? 'FORECAST' : 'SALES'
    if (resolvedSource !== 'FORECAST') {
      for (const order of listOf(db, 'salesOrders')) {
        if (order.is_deleted) continue
        if (!['APPROVED', 'IN_PRODUCTION'].includes(order.status)) continue
        const due = PLANNING_DATE(order.delivery_date)
        if (due < start || due > end) continue
        independent.push({
          material_code: order.material_code,
          quantity: toNumber(order.quantity),
          due_date: order.delivery_date,
          demand_type: 'SALES_ORDER',
          demand_ref: order.order_number,
          level: 0,
          independent: true,
        })
      }
    }
    if (resolvedSource === 'FORECAST' || (body.include_forecast !== false && independent.length === 0)) {
      for (const forecast of listOf(db, 'forecasts')) {
        if (forecast.is_deleted || forecast.status !== 'RELEASED') continue
        const due = PLANNING_DATE(forecast.due_date)
        if (due < start || due > end) continue
        independent.push({
          material_code: forecast.material_code,
          quantity: Math.max(
            0,
            toNumber(forecast.quantity) - toNumber(forecast.consumed_quantity)
          ),
          due_date: forecast.due_date,
          demand_type: 'FORECAST',
          demand_ref: forecast.forecast_number,
          level: 0,
          independent: true,
        })
      }
    }
  }

  if (body.include_safety_stock !== false) {
    for (const policy of listOf(db, 'planningPolicies')) {
      if (policy.is_deleted || !policy.is_active) continue
      const safetyStock = toNumber(policy.safety_stock)
      if (safetyStock <= 0) continue
      if (independent.some((item) => item.material_code === policy.material_code)) continue
      independent.push({
        material_code: policy.material_code,
        quantity: safetyStock,
        due_date: `${start}T00:00:00`,
        demand_type: 'SAFETY_STOCK',
        demand_ref: `SAFETY-${policy.material_code}`,
        level: 0,
        independent: true,
      })
    }
  }

  if (independent.length === 0) {
    fail(400, '没有可运算的独立需求，请先生成并下达 MPS，或检查销售订单/预测日期')
  }

  const available = new Map<string, number>()
  for (const material of listOf(db, 'materials')) {
    available.set(material.material_code, toNumber(material.current_stock))
  }

  let lineNumber = 0
  const newPlannedOrders: any[] = []
  const exceptionKeys = new Set<string>()
  let shortageCount = 0
  let totalDemandLines = 0

  const addException = (payload: any) => {
    const key = `${payload.exception_type}|${payload.material_code}|${payload.planned_order_number ?? ''}|${payload.shortage_qty}`
    if (exceptionKeys.has(key)) return
    exceptionKeys.add(key)
    exceptions.push({
      id: nextId(exceptions) + exceptionKeys.size,
      run_number: runNumber,
      resolution_status: 'OPEN',
      resolved_by: null,
      resolved_at: null,
      created_at: nowIso(),
      shortage_qty: 0,
      shortage_date: null,
      requirement_ref: null,
      planned_order_number: null,
      ...payload,
    })
    if (toNumber(payload.shortage_qty) > 0) shortageCount += 1
  }

  const processDemand = (demand: any) => {
    if (demand.level > 8) return
    totalDemandLines += 1
    lineNumber += 1
    const policy = planningPolicyFor(db, demand.material_code)
    const material = planningMaterial(db, demand.material_code)
    if (!policy) {
      addException({
        exception_type: 'NO_POLICY',
        severity: 'WARNING',
        material_code: demand.material_code,
        requirement_ref: demand.demand_ref,
        suggestion: '缺少计划参数，已按逐批规则与 0 天提前期处理，请补充物料计划参数',
      })
    }

    const stock = demand.independent ? 0 : available.get(demand.material_code) ?? 0
    const covered = round(Math.min(stock, demand.quantity), 2)
    const shortage = round(Math.max(0, demand.quantity - covered), 2)
    const remaining = round(stock - covered, 2)
    available.set(demand.material_code, remaining)

    const requirement: any = {
      id: nextId(requirements) + totalDemandLines,
      run_number: runNumber,
      line_number: lineNumber,
      material_code: demand.material_code,
      requirement_level: demand.level,
      demand_type: demand.demand_type,
      demand_ref: demand.demand_ref,
      parent_planned_order: demand.parent_planned_order ?? null,
      quantity: round(demand.quantity, 2),
      covered_qty: covered,
      shortage_qty: shortage,
      due_date: demand.due_date,
      status: shortage > 0 ? 'PLANNED' : 'COVERED',
    }
    requirements.push(requirement)

    if (covered > 0) {
      pegging.push({
        id: nextId(pegging),
        run_number: runNumber,
        planned_order_number: demand.parent_planned_order ?? null,
        demand_type: demand.demand_type,
        demand_ref: demand.demand_ref,
        supply_type: 'ON_HAND',
        supply_ref: demand.material_code,
        pegged_qty: covered,
      })
    }

    if (shortage <= 0) return

    const orderType = policy?.procurement_type === 'BUY' ? 'PURCHASE' : 'PRODUCTION'
    const quantity = planningLotSize(shortage, policy)
    const leadTime = toNumber(policy?.lead_time_days)
    const startDate = planningAddDays(demand.due_date, -leadTime)
    const plannedOrderNumber = nextNumber(
      [...plannedOrders, ...newPlannedOrders],
      'planned_order_number',
      'PLO'
    )
    const plannedOrder: any = {
      id: nextId(plannedOrders) + newPlannedOrders.length,
      planned_order_number: plannedOrderNumber,
      run_number: runNumber,
      order_type: orderType,
      material_code: demand.material_code,
      quantity,
      unit: planningUnit(material),
      start_date: startDate,
      due_date: demand.due_date,
      status: 'PLANNED',
      procurement_type: policy?.procurement_type ?? 'MAKE',
      supplier_id: null,
      lot_sizing_rule: policy?.lot_sizing_rule ?? 'LOT_FOR_LOT',
      lead_time_days: leadTime,
      demand_type: demand.demand_type,
      demand_ref: demand.demand_ref,
      parent_planned_order: demand.parent_planned_order ?? null,
      conversion_order_number: null,
      confirmed_by: null,
      confirmed_at: null,
      created_at: nowIso(),
      is_deleted: false,
    }
    newPlannedOrders.push(plannedOrder)

    pegging.push({
      id: nextId(pegging) + newPlannedOrders.length,
      run_number: runNumber,
      planned_order_number: plannedOrderNumber,
      demand_type: demand.demand_type,
      demand_ref: demand.demand_ref,
      supply_type: 'PLANNED_ORDER',
      supply_ref: plannedOrderNumber,
      pegged_qty: quantity,
    })

    addException({
      exception_type: 'SHORTAGE',
      severity: demand.level === 0 || demand.independent ? 'CRITICAL' : 'WARNING',
      material_code: demand.material_code,
      requirement_ref: demand.demand_ref,
      planned_order_number: plannedOrderNumber,
      shortage_qty: shortage,
      shortage_date: demand.due_date,
      suggestion: `需求 ${demand.demand_ref} 短缺 ${round(shortage, 2)}，已生成计划${
        orderType === 'PURCHASE' ? '采购' : '生产'
      }订单 ${plannedOrderNumber}`,
    })

    if (orderType === 'PRODUCTION') {
      const bom = planningActiveBom(db, demand.material_code)
      if (!bom) {
        addException({
          exception_type: 'NO_BOM',
          severity: 'WARNING',
          material_code: demand.material_code,
          requirement_ref: demand.demand_ref,
          planned_order_number: plannedOrderNumber,
          suggestion: '自制物料缺少已发布 BOM，无法展开下层需求，请维护并发布 BOM',
        })
        return
      }
      const baseQuantity = toNumber(bom.base_quantity, 1) || 1
      for (const item of bom.items ?? []) {
        const componentQty = round((quantity * toNumber(item.quantity)) / baseQuantity, 2)
        if (componentQty <= 0) continue
        processDemand({
          material_code: item.material_code,
          quantity: componentQty,
          due_date: startDate,
          demand_type: 'DEPENDENT',
          demand_ref: plannedOrderNumber,
          parent_planned_order: plannedOrderNumber,
          level: demand.level + 1,
          independent: false,
        })
      }
    }
  }

  independent
    .sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)))
    .forEach(processDemand)

  plannedOrders.push(...newPlannedOrders)

  const productionCount = newPlannedOrders.filter(
    (item) => item.order_type === 'PRODUCTION'
  ).length
  const purchaseCount = newPlannedOrders.length - productionCount
  const run = {
    id: nextId(runs),
    run_number: runNumber,
    run_type: body.run_type ?? 'REGENERATIVE',
    status: 'COMPLETED',
    horizon_start: `${start}T00:00:00`,
    horizon_end: `${end}T00:00:00`,
    demand_source: resolvedSource,
    mps_number: mpsNumber,
    plant_id: body.plant_id ?? null,
    total_demands: independent.length,
    total_requirements: totalDemandLines,
    planned_production_count: productionCount,
    planned_purchase_count: purchaseCount,
    exception_count: exceptions.filter((item) => item.run_number === runNumber).length,
    shortage_count: shortageCount,
    started_at: startedAt,
    finished_at: nowIso(),
    run_by: user.username,
    log_text:
      `独立需求 ${independent.length} 条；需求行 ${totalDemandLines} 条；` +
      `计划生产 ${productionCount} 张；计划采购 ${purchaseCount} 张；` +
      `异常 ${exceptions.filter((item) => item.run_number === runNumber).length} 条，其中短缺 ${shortageCount} 条。`,
    is_deleted: false,
  }
  runs.unshift(run)
  saveDb()
  return ok(run, 201)
})

route('GET', '/planning/mrp/runs', (ctx) => {
  const db = getDb()
  let runs = applyEquals(listOf(db, 'mrpRuns'), ctx.query, ['status'])
  runs = runs.filter((item) => !item.is_deleted)
  runs.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: runs.length, items: clone(paginate(runs, ctx.query)) })
})

route('GET', '/planning/mrp/runs/:runNumber/pegging', (_ctx, params) => {
  const db = getDb()
  return ok(
    clone(
      listOf(db, 'peggingLinks').filter(
        (item) => item.run_number === params.runNumber && !item.is_deleted
      )
    )
  )
})

route('GET', '/planning/mrp/runs/:runNumber', (_ctx, params) => {
  const db = getDb()
  const run = requireItem(listOf(db, 'mrpRuns'), 'run_number', params.runNumber, 'MRP 批次')
  return ok({
    ...clone(run),
    requirements: clone(
      listOf(db, 'mrpRequirements')
        .filter((item) => item.run_number === run.run_number && !item.is_deleted)
        .sort((a, b) => a.requirement_level - b.requirement_level || a.line_number - b.line_number)
    ),
    planned_orders: clone(
      listOf(db, 'plannedOrders').filter(
        (item) => item.run_number === run.run_number && !item.is_deleted
      )
    ),
    exceptions: clone(
      listOf(db, 'mrpExceptions').filter(
        (item) => item.run_number === run.run_number && !item.is_deleted
      )
    ),
  })
})

route('GET', '/planning/planned-orders', (ctx) => {
  const db = getDb()
  let orders = listOf(db, 'plannedOrders').filter((item) => !item.is_deleted)
  orders = applyEquals(orders, ctx.query, ['run_number', 'status', 'order_type', 'material_code'])
  if (!ctx.query.status && ctx.query.include_cancelled !== 'true') {
    orders = orders.filter((item) => item.status !== 'CANCELLED')
  }
  orders.sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)))
  return ok({ total: orders.length, items: clone(paginate(orders, ctx.query)) })
})

route('GET', '/planning/planned-orders/:plannedOrderNumber', (_ctx, params) => {
  const db = getDb()
  const order = requireItem(
    listOf(db, 'plannedOrders'),
    'planned_order_number',
    params.plannedOrderNumber,
    '计划订单'
  )
  return ok({
    ...clone(order),
    pegging: clone(
      listOf(db, 'peggingLinks').filter(
        (item) => item.planned_order_number === order.planned_order_number && !item.is_deleted
      )
    ),
  })
})

route('POST', '/planning/planned-orders/:plannedOrderNumber/confirm', (ctx, params) => {
  const db = getDb()
  const order = requireItem(
    listOf(db, 'plannedOrders'),
    'planned_order_number',
    params.plannedOrderNumber,
    '计划订单'
  )
  if (!['PLANNED', 'FIRMED'].includes(order.status)) {
    fail(400, `当前状态不允许确认: ${order.status}`)
  }
  order.status = 'FIRMED'
  order.confirmed_by = requireUser(ctx).username
  order.confirmed_at = nowIso()
  saveDb()
  return ok(clone(order))
})

route('POST', '/planning/planned-orders/:plannedOrderNumber/release', (ctx, params) => {
  const db = getDb()
  const order = requireItem(
    listOf(db, 'plannedOrders'),
    'planned_order_number',
    params.plannedOrderNumber,
    '计划订单'
  )
  if (!['PLANNED', 'FIRMED'].includes(order.status)) {
    fail(400, `当前状态不允许下达: ${order.status}`)
  }
  const user = requireUser(ctx)
  let conversionNumber = ''

  if (order.order_type === 'PRODUCTION') {
    const orders = listOf(db, 'productionOrders')
    const salesOrder =
      listOf(db, 'salesOrders').find(
        (item) =>
          item.order_number === order.demand_ref &&
          ['APPROVED', 'IN_PRODUCTION'].includes(item.status)
      ) ??
      listOf(db, 'salesOrders').find((item) =>
        ['APPROVED', 'IN_PRODUCTION'].includes(item.status)
      ) ??
      null
    const productionOrder = stampNew(
      {
        id: nextId(orders),
        order_number: nextNumber(orders, 'order_number', 'PO'),
        sales_order_number: salesOrder?.order_number ?? null,
        material_code: order.material_code,
        production_version_id: salesOrder?.production_version_id ?? null,
        quantity: order.quantity,
        unit: order.unit,
        planned_start_date: order.start_date,
        planned_finish_date: order.due_date,
        status: 'DRAFT',
        remarks: `由计划订单 ${order.planned_order_number} 自动转换（MRP ${order.run_number}）`,
      },
      user
    )
    orders.unshift(productionOrder)
    conversionNumber = productionOrder.order_number
  } else {
    const purchaseOrders = listOf(db, 'purchaseOrders')
    const lines = listOf(db, 'purchaseOrderLines')
    const material = planningMaterial(db, order.material_code)
    const unitPrice = toNumber(material?.standard_price)
    const purchaseOrder = stampNew(
      {
        id: nextId(purchaseOrders),
        purchase_order_number: nextNumber(
          purchaseOrders,
          'purchase_order_number',
          'PUR'
        ),
        supplier_id: ctx.body?.supplier_id ?? null,
        supplier_name: ctx.body?.supplier_name ?? null,
        status: 'RELEASED',
        order_date: nowIso(),
        expected_date: order.due_date,
        total_amount: round(toNumber(order.quantity) * unitPrice, 2),
        source_planned_order: order.planned_order_number,
        remarks: `由计划订单 ${order.planned_order_number} 自动转换（MRP ${order.run_number}）`,
      },
      user
    )
    purchaseOrders.unshift(purchaseOrder)
    lines.unshift({
      id: nextId(lines),
      purchase_order_number: purchaseOrder.purchase_order_number,
      line_number: 1,
      material_code: order.material_code,
      quantity: order.quantity,
      received_quantity: 0,
      unit: order.unit,
      unit_price: unitPrice,
      expected_date: order.due_date,
      status: 'OPEN',
    })
    conversionNumber = purchaseOrder.purchase_order_number
  }

  order.status = 'RELEASED'
  order.conversion_order_number = conversionNumber
  order.confirmed_by = user.username
  order.confirmed_at = nowIso()
  saveDb()
  return ok({ ...clone(order), created_order_number: conversionNumber })
})

route('GET', '/planning/exceptions', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'mrpExceptions').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, [
    'run_number',
    'severity',
    'exception_type',
    'resolution_status',
  ])
  const weight: Record<string, number> = { CRITICAL: 3, WARNING: 2, INFO: 1 }
  rows.sort((a, b) => (weight[b.severity] ?? 0) - (weight[a.severity] ?? 0) || b.id - a.id)
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/exceptions/:exceptionId/resolve', (ctx, params) => {
  const db = getDb()
  const row = listOf(db, 'mrpExceptions').find(
    (item) => String(item.id) === String(params.exceptionId) && !item.is_deleted
  )
  if (!row) fail(404, `MRP 异常不存在: ${params.exceptionId}`)
  const status = ctx.body?.resolution_status ?? 'RESOLVED'
  if (!['OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'IGNORED'].includes(status)) {
    fail(400, `无效的处理状态: ${status}`)
  }
  row.resolution_status = status
  row.resolved_by = requireUser(ctx).username
  row.resolved_at = nowIso()
  if (ctx.body?.remarks) row.remarks = ctx.body.remarks
  saveDb()
  return ok(clone(row))
})

function planningKittingResult(
  db: MockDb,
  sourceType: string,
  sourceRef: string,
  user: MockUser
) {
  const source =
    sourceType === 'PLANNED_ORDER'
      ? listOf(db, 'plannedOrders').find(
          (item) => item.planned_order_number === sourceRef && !item.is_deleted
        )
      : listOf(db, 'productionOrders').find((item) => item.order_number === sourceRef)
  if (!source) fail(404, `${sourceType === 'PLANNED_ORDER' ? '计划订单' : '生产订单'}不存在: ${sourceRef}`)
  const bom = planningActiveBom(db, source.material_code)
  if (!bom) fail(400, `物料 ${source.material_code} 缺少已发布 BOM，无法做齐套分析`)
  const baseQuantity = toNumber(bom.base_quantity, 1) || 1
  const neededDate =
    PLANNING_DATE(source.planned_start_date ?? source.start_date ?? source.due_date) ||
    nowIso().slice(0, 10)
  const details = (bom.items ?? []).map((item: any) => {
    const material = planningMaterial(db, item.material_code)
    const required = round(
      (toNumber(source.quantity) * toNumber(item.quantity)) / baseQuantity,
      2
    )
    const availableQty = toNumber(material?.current_stock)
    return {
      material_code: item.material_code,
      material_name: material?.material_name ?? item.material_code,
      unit: item.unit ?? planningUnit(material),
      required_qty: required,
      available_qty: availableQty,
      shortage_qty: round(Math.max(0, required - availableQty), 2),
      needed_date: neededDate,
    }
  })
  const shortageQty = round(
    details.reduce((sum: number, item: any) => sum + item.shortage_qty, 0),
    2
  )
  const kitStatus =
    shortageQty <= 0 ? 'FULL' : details.every((item: any) => item.available_qty <= 0) ? 'SHORT' : 'PARTIAL'
  const results = listOf(db, 'kittingResults')
  let result = results.find(
    (item) =>
      item.source_type === sourceType && item.source_ref === sourceRef && !item.is_deleted
  )
  if (!result) {
    result = {
      id: nextId(results),
      result_number: nextNumber(results, 'result_number', 'KIT'),
      source_type: sourceType,
      source_ref: sourceRef,
      is_deleted: false,
    }
    results.unshift(result)
  }
  Object.assign(result, {
    material_code: source.material_code,
    kit_status: kitStatus,
    required_qty: round(toNumber(source.quantity), 2),
    available_qty: round(
      details.reduce(
        (sum: number, item: any) => sum + Math.min(item.required_qty, item.available_qty),
        0
      ),
      2
    ),
    shortage_qty: shortageQty,
    shortage_details: details.filter((item: any) => item.shortage_qty > 0),
    checked_at: nowIso(),
    checked_by: user.username,
    remarks:
      shortageQty > 0
        ? `${details.filter((item: any) => item.shortage_qty > 0).length} 项组件部分缺料`
        : '全部组件齐套',
  })
  return result
}

route('GET', '/planning/kitting', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'kittingResults').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['source_type', 'kit_status'])
  rows.sort((a, b) => String(b.checked_at).localeCompare(String(a.checked_at)))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('GET', '/planning/kitting/by-source/:sourceType/:sourceRef', (_ctx, params) => {
  const db = getDb()
  const row = listOf(db, 'kittingResults').find(
    (item) =>
      item.source_type === params.sourceType &&
      item.source_ref === params.sourceRef &&
      !item.is_deleted
  )
  if (!row) fail(404, '齐套分析结果不存在')
  return ok(clone(row))
})

route('POST', '/planning/kitting/production-orders/:orderNumber', (ctx, params) => {
  const result = planningKittingResult(
    getDb(),
    'PRODUCTION_ORDER',
    params.orderNumber,
    requireUser(ctx)
  )
  saveDb()
  return ok(clone(result))
})

route('POST', '/planning/kitting/planned-orders/:plannedOrderNumber', (ctx, params) => {
  const result = planningKittingResult(
    getDb(),
    'PLANNED_ORDER',
    params.plannedOrderNumber,
    requireUser(ctx)
  )
  saveDb()
  return ok(clone(result))
})

route('GET', '/planning/kitting/:resultNumber', (_ctx, params) => {
  const row = requireItem(
    listOf(getDb(), 'kittingResults'),
    'result_number',
    params.resultNumber,
    '齐套分析结果'
  )
  return ok(clone(row))
})

route('GET', '/planning/policies', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'planningPolicies').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['material_code'])
  if (ctx.query.is_active !== undefined && ctx.query.is_active !== '') {
    const active = ctx.query.is_active === true || ctx.query.is_active === 'true'
    rows = rows.filter((item) => Boolean(item.is_active) === active)
  }
  rows.sort((a, b) => String(a.material_code).localeCompare(String(b.material_code)))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/policies', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.material_code) fail(400, '物料不能为空')
  if (!planningMaterial(db, body.material_code)) {
    fail(404, `物料不存在: ${body.material_code}`)
  }
  const policies = listOf(db, 'planningPolicies')
  if (
    policies.some(
      (item) => item.material_code === body.material_code && !item.is_deleted
    )
  ) {
    fail(400, '该物料已存在计划参数，请使用更新接口')
  }
  const item = stampNew(
    {
      id: nextId(policies),
      policy_id: nextNumber(policies, 'policy_id', 'PLP'),
      is_deleted: false,
      ...body,
    },
    requireUser(ctx)
  )
  policies.push(item)
  saveDb()
  return ok(clone(item), 201)
})

route('PUT', '/planning/policies/:policyId', (ctx, params) => {
  const db = getDb()
  const item = requireItem(
    listOf(db, 'planningPolicies'),
    'policy_id',
    params.policyId,
    '计划参数'
  )
  const body = ctx.body ?? {}
  if (body.material_code && body.material_code !== item.material_code) {
    fail(400, '不允许修改物料编码，请新建策略')
  }
  Object.assign(item, body, {
    updated_by: requireUser(ctx).username,
    updated_at: nowIso(),
  })
  saveDb()
  return ok(clone(item))
})

route('DELETE', '/planning/policies/:policyId', (ctx, params) => {
  const db = getDb()
  const item = requireItem(
    listOf(db, 'planningPolicies'),
    'policy_id',
    params.policyId,
    '计划参数'
  )
  item.is_deleted = true
  item.is_active = false
  item.updated_by = requireUser(ctx).username
  item.updated_at = nowIso()
  saveDb()
  return ok({ message: '计划参数已删除' })
})

/* ------------------------------- 成本引擎（P1） ------------------------------- */

function costWorkCenters(db: MockDb): any[] {
  return listOf(db, 'workCenters')
}

function costRateFor(db: MockDb, workCenterId: string, rateType: string): any | null {
  return (
    listOf(db, 'costRates').find(
      (item) =>
        item.work_center_id === workCenterId &&
        item.rate_type === rateType &&
        !item.is_deleted
    ) ?? null
  )
}

function costRateValue(db: MockDb, workCenterId: string, rateType: string): number {
  const rate = costRateFor(db, workCenterId, rateType)
  return toNumber(rate?.rate_per_hour)
}

function costChildStandard(db: MockDb, materialCode: string): number {
  const rows = listOf(db, 'standardCosts')
    .filter((item) => item.material_code === materialCode && !item.is_deleted)
    .sort((a, b) => Number(b.id) - Number(a.id))
  if (rows.length) return toNumber(rows[0].total_cost)
  const material = planningMaterial(db, materialCode)
  return toNumber(material?.standard_price)
}

function costOperationStandard(db: MockDb, op: any) {
  const hours = (toNumber(op.setup_time) + toNumber(op.machine_time) + toNumber(op.labor_time)) / 60
  const labor = hours * costRateValue(db, op.work_center_id, 'LABOR')
  const machine = hours * costRateValue(db, op.work_center_id, 'MACHINE')
  const overhead = hours * costRateValue(db, op.work_center_id, 'OVERHEAD')
  return { labor: round(labor, 2), machine: round(machine, 2), overhead: round(overhead, 2) }
}

function costRoutingFor(db: MockDb, materialCode: string): any | null {
  const routing = listOf(db, 'routings').find(
    (item) => item.material_code === materialCode && item.status === 'RELEASED' && !item.is_deleted
  )
  if (!routing) return null
  const ops = (db.routingOperations?.[routing.routing_id] ?? []) as any[]
  return { routing, ops: [...ops].sort((a, b) => String(a.operation_no).localeCompare(String(b.operation_no))) }
}

function costComputeStandard(db: MockDb, materialCode: string, user: MockUser) {
  const material = planningMaterial(db, materialCode)
  if (!material) return null
  const rows = listOf(db, 'standardCosts')
  let row = rows.find(
    (item) => item.material_code === materialCode && item.version === '1' && !item.is_deleted
  )
  let materialCost = 0
  let laborCost = 0
  let overheadCost = 0

  const bom = planningActiveBom(db, materialCode)
  if (bom) {
    const base = toNumber(bom.base_quantity, 1) || 1
    for (const item of bom.items ?? []) {
      const qty = (toNumber(item.quantity) / base) * (1 + toNumber(item.scrap_rate) / 100)
      materialCost += qty * costChildStandard(db, item.material_code)
    }
  } else if (['RAW', 'PACKAGING'].includes(material.material_type) || toNumber(material.standard_price) > 0) {
    materialCost = toNumber(material.standard_price)
  }

  const rt = costRoutingFor(db, materialCode)
  if (rt) {
    for (const op of rt.ops) {
      const c = costOperationStandard(db, op)
      laborCost += c.labor
      overheadCost += c.machine + c.overhead
    }
  }
  if (materialCost <= 0 && ['RAW', 'PACKAGING'].includes(material.material_type)) {
    materialCost = toNumber(material.standard_price)
  }

  const total = round(materialCost + laborCost + overheadCost, 2)
  if (!row) {
    row = stampNew(
      {
        id: nextId(rows),
        cost_id: nextNumber(rows, 'cost_id', 'STD'),
        material_code: materialCode,
        version: '1',
        is_deleted: false,
      },
      user
    )
    rows.push(row)
  }
  Object.assign(row, {
    cost_date: nowIso(),
    material_cost: round(materialCost, 2),
    labor_cost: round(laborCost, 2),
    overhead_cost: round(overheadCost, 2),
    total_cost: total,
    unit_cost: total,
    currency: 'CNY',
    status: 'ACTIVE',
    rolled_up_at: nowIso(),
    cost_method: 'STANDARD',
    updated_by: user.username,
    updated_at: nowIso(),
  })
  return row
}

function costRollup(db: MockDb, materialCodes: string[], rollDeep: boolean, user: MockUser) {
  const done = new Set<string>()
  const visit = (code: string, seen: Set<string>) => {
    if (done.has(code) || seen.has(code)) return
    seen = new Set(seen).add(code)
    const bom = planningActiveBom(db, code)
    if (bom && rollDeep) {
      for (const item of bom.items ?? []) visit(item.material_code, seen)
    }
    costComputeStandard(db, code, user)
    done.add(code)
  }
  for (const code of materialCodes) visit(code, new Set())
  return done.size
}

function costCollectProduction(db: MockDb, orderNumber: string, user: MockUser): any {
  const order = listOf(db, 'productionOrders').find((item) => item.order_number === orderNumber)
  if (!order) fail(404, `生产订单不存在: ${orderNumber}`)
  const qty = toNumber(order.quantity) || 1
  let materialActual = 0
  for (const issue of listOf(db, 'materialIssues')) {
    if (issue.production_order_number !== orderNumber || issue.is_deleted) continue
    const mat = planningMaterial(db, issue.material_code)
    materialActual += toNumber(issue.quantity) * toNumber(mat?.standard_price)
  }
  let laborActual = 0
  let overheadActual = 0
  const reports = listOf(db, 'operationReports').filter(
    (item) => item.production_order_number === orderNumber && !item.is_deleted
  )
  for (const report of reports) {
    const hours = (toNumber(report.setup_time) + toNumber(report.machine_time) + toNumber(report.labor_time)) / 60
    laborActual += hours * costRateValue(db, report.work_center_id, 'LABOR')
    overheadActual +=
      hours * costRateValue(db, report.work_center_id, 'MACHINE') +
      hours * costRateValue(db, report.work_center_id, 'OVERHEAD')
  }
  const totalActual = round(materialActual + laborActual + overheadActual, 2)
  const standardCost = round(costChildStandard(db, order.material_code) * qty, 2)

  const rows = listOf(db, 'productionCosts')
  let row = rows.find((item) => item.production_order_number === orderNumber)
  if (!row) {
    row = stampNew(
      {
        id: nextId(rows),
        cost_id: nextNumber(rows, 'cost_id', 'PRC'),
        production_order_number: orderNumber,
        material_code: order.material_code,
        quantity: qty,
        is_deleted: false,
      },
      user
    )
    rows.push(row)
  }
  Object.assign(row, {
    material_cost_actual: round(materialActual, 2),
    labor_cost_actual: round(laborActual, 2),
    overhead_actual: round(overheadActual, 2),
    total_actual: totalActual,
    standard_cost: standardCost,
    wip_value: totalActual,
    status: 'COLLECTED',
    collected_at: nowIso(),
    updated_by: user.username,
    updated_at: nowIso(),
  })
  return row
}

route('GET', '/planning/cost/overview', () => {
  const db = getDb()
  const notDeleted = (arr: any[]) => arr.filter((item) => !item.is_deleted)
  const std = notDeleted(listOf(db, 'standardCosts'))
  const prod = notDeleted(listOf(db, 'productionCosts'))
  const variances = notDeleted(listOf(db, 'costVariances'))
  const settlements = notDeleted(listOf(db, 'costSettlements'))
  return ok({
    standard_costs: std.length,
    production_costs: prod.length,
    open_costs: prod.filter((item) => ['OPEN', 'COLLECTED'].includes(item.status)).length,
    settled_costs: prod.filter((item) => item.status === 'SETTLED').length,
    variances: variances.length,
    adverse_variances: variances.filter((item) => toNumber(item.variance_amount) > 0).length,
    settlements: settlements.length,
    rates: notDeleted(listOf(db, 'costRates')).filter((item) => item.status === 'ACTIVE').length,
    cost_centers: notDeleted(costWorkCenters(db)).length,
  })
})

route('GET', '/planning/cost/rates', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'costRates').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['work_center_id', 'rate_type'])
  rows.sort((a, b) => String(a.work_center_id).localeCompare(String(b.work_center_id)))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('PUT', '/planning/cost/rates/:rateId', (ctx, params) => {
  const db = getDb()
  const row = requireItem(listOf(db, 'costRates'), 'rate_id', params.rateId, '成本费率')
  const body = ctx.body ?? {}
  if (body.rate_per_hour !== undefined) row.rate_per_hour = body.rate_per_hour
  if (body.currency !== undefined) row.currency = body.currency
  if (body.status !== undefined) row.status = body.status
  row.updated_by = requireUser(ctx).username
  row.updated_at = nowIso()
  saveDb()
  return ok(clone(row))
})

route('POST', '/planning/cost/standard/rollup', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  const codes = body.material_codes ?? []
  if (!codes.length) fail(400, 'material_codes 不能为空')
  const rollDeep = body.roll_deep !== false
  const done = costRollup(db, codes, rollDeep, requireUser(ctx))
  saveDb()
  return ok({ rolled_up: done, material_codes: codes })
})

route('GET', '/planning/cost/standard', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'standardCosts').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['material_code'])
  rows.sort((a, b) => String(a.material_code).localeCompare(String(b.material_code)))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('GET', '/planning/cost/standard/:materialCode', (_ctx, params) => {
  const row = requireItem(
    listOf(getDb(), 'standardCosts'),
    'material_code',
    params.materialCode,
    '标准成本'
  )
  return ok(clone(row))
})

route('GET', '/planning/cost/production', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'productionCosts').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['status'])
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/cost/production/collect', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.production_order_number) fail(400, 'production_order_number 不能为空')
  const row = costCollectProduction(db, body.production_order_number, requireUser(ctx))
  saveDb()
  return ok(clone(row))
})

route('GET', '/planning/cost/production/:orderNumber', (_ctx, params) => {
  const row = requireItem(
    listOf(getDb(), 'productionCosts'),
    'production_order_number',
    params.orderNumber,
    '工单成本'
  )
  return ok(clone(row))
})

function costAnalyzeVariances(db: MockDb, orderNumber: string, user: MockUser): any[] {
  const prod = costCollectProduction(db, orderNumber, user)
  const std = costChildStandard(db, prod.material_code)
  const qty = toNumber(prod.quantity) || 1
  const standard = round(std * qty, 2)
  const defs: Array<[string, number, number]> = [
    ['MATERIAL_PRICE', standard, prod.material_cost_actual],
    ['MATERIAL_USAGE', standard, prod.material_cost_actual],
    ['LABOR_RATE', standard, prod.labor_cost_actual],
    ['LABOR_EFFICIENCY', standard, prod.labor_cost_actual],
    ['OVERHEAD', standard, prod.overhead_actual],
  ]
  const existing = listOf(db, 'costVariances')
  for (const item of existing) {
    if (item.production_order_number === orderNumber) item.is_deleted = true
  }
  const created: any[] = []
  defs.forEach(([vtype, stdAmount, actualAmount], index) => {
    const varianceAmount = round(actualAmount - stdAmount, 2)
    const pct = stdAmount !== 0 ? round((varianceAmount / stdAmount) * 100, 2) : 0
    const row = stampNew(
      {
        id: nextId(existing),
        variance_number: `${nextNumber(existing, 'variance_number', 'VAR')}-${index + 1}`,
        production_order_number: orderNumber,
        variance_type: vtype,
        standard_amount: round(stdAmount, 2),
        actual_amount: round(actualAmount, 2),
        variance_amount: varianceAmount,
        variance_pct: pct,
        analyzed_at: nowIso(),
        remarks: `${vtype} 差异分析（标准 ${round(stdAmount, 2)} / 实际 ${round(actualAmount, 2)}）`,
        is_deleted: false,
      },
      user
    )
    existing.push(row)
    created.push(row)
  })
  return created
}

route('POST', '/planning/cost/variances/analyze', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.production_order_number) fail(400, 'production_order_number 不能为空')
  const created = costAnalyzeVariances(db, body.production_order_number, requireUser(ctx))
  saveDb()
  return ok({ items: clone(created) })
})

route('GET', '/planning/cost/variances', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'costVariances').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['production_order_number'])
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/cost/settlement/settle', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.production_order_number) fail(400, 'production_order_number 不能为空')
  const user = requireUser(ctx)
  const prod = costCollectProduction(db, body.production_order_number, user)
  const settlements = listOf(db, 'costSettlements')
  let row = settlements.find((item) => item.production_order_number === body.production_order_number)
  if (!row) {
    row = stampNew(
      {
        id: nextId(settlements),
        settlement_number: nextNumber(settlements, 'settlement_number', 'STL'),
        production_order_number: body.production_order_number,
        is_deleted: false,
      },
      user
    )
    settlements.push(row)
  }
  Object.assign(row, {
    total_cost: prod.total_actual,
    wip_value: prod.wip_value,
    settlement_status: 'SETTLED',
    settled_at: nowIso(),
    updated_by: user.username,
    updated_at: nowIso(),
  })
  prod.status = 'SETTLED'
  prod.settled_at = row.settled_at
  saveDb()
  return ok(clone(row))
})

route('GET', '/planning/cost/settlements', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'costSettlements').filter((item) => !item.is_deleted)
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

/* ------------------------------- APS 有限产能排程（P1） ------------------------------- */

/** 与后端 naive datetime 一致的本地时间字符串（不含 Z） */
function apsLocalIso(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

// 工作中心日历：按班次/工作日计算每日可用工时，记录已占用时段
function apsCalendarFor(db: MockDb, workCenterId: string, _start: string, end: string) {
  const cal = listOf(db, 'workCalendars').find(
    (item) => item.work_center_id === workCenterId && !item.is_deleted
  )
  const wc = listOf(db, 'workCenters').find((item) => item.work_center_id === workCenterId)
  const machines = Math.max(1, Number(wc?.number_of_capacities) || 1)
  const shiftStart = Number((cal?.shift_start || '08:00').split(':')[0])
  const shiftEnd = Number((cal?.shift_end || '20:00').split(':')[0])
  const breakHours = Number(cal?.break_hours) || 1
  const utilization = Number(cal?.utilization) || 100
  const workdays = new Set(
    String(cal?.workdays || '1,2,3,4,5,6')
      .split(',')
      .map((x) => Number(x.trim()))
      .filter((x) => Number.isFinite(x))
  )
  return {
    workCenterId,
    machines,
    shiftStart,
    shiftEnd,
    breakHours,
    utilization,
    workdays,
    hoursPerDay: Math.max(0, shiftEnd - shiftStart) - breakHours,
    busy: Array.from({ length: machines }, () => [] as Array<[string, string]>),
    effective(minutes: number) {
      if (utilization <= 0) return Number.MAX_SAFE_INTEGER
      return (minutes * 100) / utilization
    },
    isWorkday(date: Date) {
      const day = date.getDay()
      return workdays.has(day === 0 ? 7 : day)
    },
    findSlot(durationMinutes: number, earliest: Date) {
      const need = this.effective(durationMinutes)
      let cursor = new Date(earliest)
      for (let m = 0; m < this.machines; m += 1) {
        cursor = new Date(earliest)
        while (cursor < new Date(end)) {
          if (!this.isWorkday(cursor)) {
            cursor = new Date(cursor)
            cursor.setDate(cursor.getDate() + 1)
            cursor.setHours(this.shiftStart, 0, 0, 0)
            continue
          }
          const dayOpen = new Date(cursor)
          dayOpen.setHours(this.shiftStart, 0, 0, 0)
          const dayClose = new Date(cursor)
          dayClose.setHours(this.shiftEnd, 0, 0, 0)
          if (cursor < dayOpen) cursor = dayOpen
          if (cursor >= dayClose) {
            cursor = new Date(cursor)
            cursor.setDate(cursor.getDate() + 1)
            cursor.setHours(this.shiftStart, 0, 0, 0)
            continue
          }
          const busy = this.busy[m]
            .filter(([bs, be]) => new Date(be) > cursor && new Date(bs) < dayClose)            .sort((a, b) => (a[0] < b[0] ? -1 : 1))
          let freeStart = cursor
          for (const [bs, be] of busy) {
            const bsD = new Date(bs)
            const beD = new Date(be)
            if (bsD > freeStart) {
              const freeMin = (bsD.getTime() - freeStart.getTime()) / 60000
              if (freeMin >= need) {
                const s = freeStart
                const e = new Date(s.getTime() + need * 60000)
                return { machine: m, start: s, end: e }
              }
            }
            if (beD > freeStart) freeStart = beD
          }
          if (freeStart < dayClose) {
            const freeMin = (dayClose.getTime() - freeStart.getTime()) / 60000
            if (freeMin >= need) {
              const s = freeStart
              const e = new Date(s.getTime() + need * 60000)
              return { machine: m, start: s, end: e }
            }
          }
          cursor = new Date(cursor)
          cursor.setDate(cursor.getDate() + 1)
          cursor.setHours(this.shiftStart, 0, 0, 0)
        }
      }
      return null
    },
  }
}

function apsRoutingFor(db: MockDb, materialCode: string): any | null {
  const routing = listOf(db, 'routings').find(
    (item) => item.material_code === materialCode && item.status === 'RELEASED' && !item.is_deleted
  )
  if (!routing) return null
  return { routing, ops: (db.routingOperations?.[routing.routing_id] || []).slice().sort((a: any, b: any) => String(a.operation_no).localeCompare(String(b.operation_no))) }
}

function apsOrdersForSource(db: MockDb, sourceType: string) {
  if (sourceType === 'PLANNED_ORDER') {
    return listOf(db, 'plannedOrders')
      .filter(
        (item) => !item.is_deleted && item.order_type === 'PRODUCTION' && ['PLANNED', 'FIRMED', 'RELEASED'].includes(item.status)
      )
      .sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)))
      .map((row) => ({
        order_number: row.planned_order_number,
        material_code: row.material_code,
        quantity: toNumber(row.quantity),
        planned_start_date: row.start_date || row.due_date,
        planned_finish_date: row.due_date,
      }))
  }
  return listOf(db, 'productionOrders')
    .filter((item) => !item.is_deleted && ['RELEASED', 'IN_PRODUCTION'].includes(item.status))
    .sort((a, b) => String(a.planned_start_date || '').localeCompare(String(b.planned_start_date || '')))
    .map((row) => ({
      order_number: row.order_number,
      material_code: row.material_code,
      quantity: toNumber(row.quantity),
      planned_start_date: row.planned_start_date,
      planned_finish_date: row.planned_finish_date,
    }))
}

function apsKittingStatus(db: MockDb, orderNumber: string): string | null {
  const row = listOf(db, 'kittingResults')
    .filter(
      (item) => !item.is_deleted && item.source_type === 'PRODUCTION_ORDER' && item.source_ref === orderNumber
    )
    .sort((a, b) => Number(b.id) - Number(a.id))[0]
  return row ? row.kit_status : null
}

function apsRun(db: MockDb, body: any, user: MockUser) {
  const start = body.horizon_start || `${PLANNING_DATE(nowIso())}T00:00:00`
  const end = body.horizon_end || planningAddDays(start, 42)
  const algorithm = body.algorithm || 'FORWARD'
  const sourceType = body.source_type || 'PRODUCTION_ORDER'
  const runs = listOf(db, 'scheduleRuns')
  let run = runs.find(
    (item) => item.source_type === sourceType && ['DRAFT', 'RUNNING'].includes(item.status) && !item.is_deleted
  )
  if (!run) {
    run = stampNew({
      id: nextId(runs),
      run_number: nextNumber(runs, 'run_number', 'APS'),
      run_name: body.run_name || 'APS 有限产能排程',
      algorithm,
      status: 'RUNNING',
      horizon_start: start,
      horizon_end: end,
      source_type: sourceType,
      generated_by: user.username,
      generated_at: nowIso(),
      operation_count: 0,
      exception_count: 0,
      notes: null,
      is_deleted: false,
    }, user)
    runs.push(run)
  } else {
    Object.assign(run, {
      run_name: body.run_name || run.run_name,
      algorithm,
      horizon_start: start,
      horizon_end: end,
      status: 'RUNNING',
      generated_at: nowIso(),
    })
  }

  // 清空本批次旧的工序/异常
  const ops = listOf(db, 'scheduledOperations')
  const exceptions = listOf(db, 'scheduleExceptions')
  for (const item of ops) if (item.run_number === run.run_number) item.is_deleted = true
  for (const item of exceptions) if (item.run_number === run.run_number) item.is_deleted = true

  const orders = apsOrdersForSource(db, sourceType)
  const calendars = new Map<string, any>()
  for (const wc of listOf(db, 'workCenters')) {
    if (!wc.is_deleted) calendars.set(wc.work_center_id, apsCalendarFor(db, wc.work_center_id, start, end))
  }
  let opCount = 0
  let excCount = 0

  const addException = (payload: any) => {
    exceptions.push(stampNew({
      id: nextId(exceptions),
      exception_id: nextNumber(exceptions, 'exception_id', 'APSEX'),
      run_number: run.run_number,
      severity: 'WARNING',
      created_at: nowIso(),
      ...payload,
      is_deleted: false,
    }, user))
    excCount += 1
  }

  for (const order of orders) {
    let sequence = 0
    let plannedAt = new Date(order.planned_start_date || start)
    if (plannedAt < new Date(start)) plannedAt = new Date(start)
    if (algorithm === 'BACKWARD' || algorithm === 'MIXED') {
      plannedAt = new Date(order.planned_finish_date || order.planned_start_date || end)
    }
    const rt = apsRoutingFor(db, order.material_code)
    if (!rt) {
      addException({
        exception_type: 'CAPACITY_OVERLOAD',
        production_order_number: order.order_number,
        message: `工单 ${order.order_number} 缺少已发布工艺路线，无法排程`,
        suggested_action: '维护并发布工艺路线后重新排程',
      })
      continue
    }
    const kitStatus = apsKittingStatus(db, order.order_number)
    for (const op of rt.ops) {
      sequence += 1
      let duration = toNumber(op.setup_time) + toNumber(op.machine_time) + toNumber(op.labor_time)
      if (!duration) duration = 30
      const calendar = calendars.get(op.work_center_id)
      let slot: any = null
      if (calendar) {
        const earliest = algorithm === 'BACKWARD' || algorithm === 'MIXED'
          ? Math.max(plannedAt.getTime(), new Date(start).getTime())
          : plannedAt.getTime()
        slot = calendar.findSlot(duration, new Date(earliest))
      }
      if (!slot) {
        addException({
          exception_type: 'CAPACITY_OVERLOAD',
          production_order_number: order.order_number,
          work_center_id: op.work_center_id,
          message: `工单 ${order.order_number} 工序 ${op.operation_no} 在 ${op.work_center_id} 找不到可用产能`,
          suggested_action: '调整班次/利用率或增加资源后重新排程',
        })
        plannedAt = new Date(plannedAt.getTime() + duration * 60000)
        continue
      }
      if (calendar) calendar.busy[slot.machine].push([apsLocalIso(slot.start), apsLocalIso(slot.end)])
      plannedAt = new Date(slot.end)
      ops.push(stampNew({
        id: nextId(ops),
        op_id: nextNumber(ops, 'op_id', 'OP'),
        run_number: run.run_number,
        production_order_number: order.order_number,
        material_code: order.material_code,
        operation_no: op.operation_no,
        operation_name: op.operation_name,
        work_center_id: op.work_center_id,
        resource_id: null,
        sequence,
        planned_qty: order.quantity,
        setup_minutes: toNumber(op.setup_time),
        run_minutes: toNumber(op.machine_time) + toNumber(op.labor_time),
        planned_start: apsLocalIso(slot.start),
        planned_end: apsLocalIso(slot.end),
        status: 'PLANNED',
        is_deleted: false,
      }, user))
      opCount += 1
    }
    const due = new Date(order.planned_finish_date || end)
    const lastEnd = ops
      .filter((item) => item.run_number === run.run_number && item.production_order_number === order.order_number)
      .reduce((maxEnd: any, item: any) => (item.planned_end > maxEnd ? item.planned_end : maxEnd), null)
    if (lastEnd && new Date(lastEnd) > due) {
      addException({
        exception_type: 'DUE_DATE_RISK',
        production_order_number: order.order_number,
        message: `工单 ${order.order_number} 排程可能无法满足交期`,
        suggested_action: '评估提前开始 / 加班 / 委外',
      })
    }
    if (kitStatus === 'SHORT' || kitStatus === 'PARTIAL') {
      const critical = kitStatus === 'SHORT'
      addException({
        exception_type: 'MATERIAL_SHORTAGE',
        production_order_number: order.order_number,
        severity: critical ? 'CRITICAL' : 'WARNING',
        message: `工单 ${order.order_number} ${critical ? '物料缺料，不宜下达排程' : '物料部分缺料，排程存在风险'}`,
        suggested_action: critical ? '补料齐套后再排程' : '确认缺料补货计划，必要时调整排程顺序',
      })
    }
  }

  Object.assign(run, {
    operation_count: opCount,
    exception_count: exceptions.filter((item) => item.run_number === run.run_number && !item.is_deleted).length,
    status: 'COMPLETED',
    finished_at: nowIso(),
  })
  return run
}

route('POST', '/planning/aps/run', (ctx) => {
  const db = getDb()
  const run = apsRun(db, ctx.body ?? {}, requireUser(ctx))
  saveDb()
  return ok(clone(run), 201)
})

route('GET', '/planning/aps/overview', () => {
  const db = getDb()
  const runs = listOf(db, 'scheduleRuns').filter((item) => !item.is_deleted)
  const operations = listOf(db, 'scheduledOperations').filter((item) => !item.is_deleted)
  const exceptions = listOf(db, 'scheduleExceptions').filter((item) => !item.is_deleted)
  const resources = listOf(db, 'resources').filter((item) => !item.is_deleted)
  const latest = runs.slice().sort((a, b) => Number(b.id) - Number(a.id))[0]
  return ok({
    runs: runs.length,
    published_runs: runs.filter((item) => item.status === 'PUBLISHED').length,
    operations: operations.length,
    exceptions: exceptions.length,
    critical_exceptions: exceptions.filter((item) => item.severity === 'CRITICAL').length,
    scenarios: listOf(db, 'scenarioSimulations').filter((item) => !item.is_deleted).length,
    resources: resources.length,
    active_resources: resources.filter((item) => item.status === 'ACTIVE').length,
    skills: listOf(db, 'skillMatrices').filter((item) => !item.is_deleted).length,
    changeovers: listOf(db, 'changeoverMatrices').filter((item) => !item.is_deleted).length,
    work_centers: listOf(db, 'workCenters').filter((item) => !item.is_deleted).length,
    latest_run: latest ? clone(latest) : null,
  })
})

route('GET', '/planning/aps/runs', (ctx) => {
  const db = getDb()
  let runs = listOf(db, 'scheduleRuns').filter((item) => !item.is_deleted)
  runs = applyEquals(runs, ctx.query, ['status', 'source_type'])
  runs.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: runs.length, items: clone(paginate(runs, ctx.query)) })
})

route('GET', '/planning/aps/runs/:runNumber', (_ctx, params) => {
  const db = getDb()
  const run = requireItem(listOf(db, 'scheduleRuns'), 'run_number', params.runNumber, '排程批次')
  const ops = listOf(db, 'scheduledOperations').filter(
    (item) => item.run_number === run.run_number && !item.is_deleted
  )
  const exceptions = listOf(db, 'scheduleExceptions').filter(
    (item) => item.run_number === run.run_number && !item.is_deleted
  )
  return ok({ ...clone(run), operations: clone(ops), exceptions: clone(exceptions) })
})

route('GET', '/planning/aps/runs/:runNumber/gantt', (_ctx, params) => {
  const db = getDb()
  const run = requireItem(listOf(db, 'scheduleRuns'), 'run_number', params.runNumber, '排程批次')
  const ops = listOf(db, 'scheduledOperations').filter(
    (item) => item.run_number === run.run_number && !item.is_deleted
  )
  const workCenters = listOf(db, 'workCenters').filter((item) => !item.is_deleted)
  const rows = workCenters.map((wc) => ({
    work_center_id: wc.work_center_id,
    description: wc.description,
    operations: ops
      .filter((op) => op.work_center_id === wc.work_center_id)
      .sort((a, b) => String(a.planned_start).localeCompare(String(b.planned_start)))
      .map((op) => ({
        ...clone(op),
        title: `${op.production_order_number} · ${op.operation_name}`,
      })),
  }))
  return ok({ run: clone(run), gantt: rows, range: { start: run.horizon_start, end: run.horizon_end } })
})

route('POST', '/planning/aps/runs/:runNumber/publish', (ctx, params) => {
  const db = getDb()
  const run = requireItem(listOf(db, 'scheduleRuns'), 'run_number', params.runNumber, '排程批次')
  for (const item of listOf(db, 'scheduledOperations')) {
    if (item.run_number === run.run_number && !item.is_deleted) item.status = 'PUBLISHED'
  }
  run.status = 'PUBLISHED'
  run.published_at = nowIso()
  run.updated_by = requireUser(ctx).username
  saveDb()
  return ok(clone(run))
})

route('POST', '/planning/aps/simulate', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.run_number) fail(400, 'run_number 不能为空')
  const user = requireUser(ctx)
  const scenarios = listOf(db, 'scenarioSimulations')
  const impacts = listOf(db, 'scenarioImpacts')
  const scenario = stampNew({
    id: nextId(scenarios),
    scenario_id: nextNumber(scenarios, 'scenario_id', 'SCN'),
    run_number: body.run_number,
    scenario_type: body.scenario_type || 'INSERT_ORDER',
    description: body.description || '插单/扰动模拟',
    reference_ref: body.reference_ref || null,
    created_by: user.username,
    created_at: nowIso(),
    impact_summary: null as string | null,
    status: 'DRAFT',
    is_deleted: false,
  }, user)
  scenarios.push(scenario)

  const ops = listOf(db, 'scheduledOperations').filter(
    (item) => item.run_number === body.run_number && !item.is_deleted
  )
  const created: any[] = []
  const sType = scenario.scenario_type
  const addImpact = (payload: any) => {
    const impact = stampNew({
      id: nextId(impacts),
      impact_id: nextNumber(impacts, 'impact_id', 'IMP'),
      scenario_id: scenario.scenario_id,
      delay_days: 0,
      impact_level: 'LOW',
      ...payload,
      is_deleted: false,
    }, user)
    impacts.push(impact)
    created.push(impact)
  }

  if (sType === 'INSERT_ORDER') {
    const burden = 2
    for (const op of ops) {
      if (body.reference_ref && op.production_order_number === body.reference_ref) continue
      addImpact({
        production_order_number: op.production_order_number,
        material_code: op.material_code,
        affected_days: burden,
        original_due_date: op.planned_end,
        new_due_date: planningAddDays(op.planned_end, burden),
        delay_days: burden,
        impact_level: 'MEDIUM',
      })
    }
    scenario.impact_summary = `${created.length} 道工序受影响，平均延期 ${burden} 天`
  } else if (sType === 'EQUIPMENT_DOWN') {
    let affected = 0
    for (const op of ops) {
      if (op.work_center_id === body.reference_ref) {
        addImpact({
          production_order_number: op.production_order_number,
          material_code: op.material_code,
          affected_days: 1,
          original_due_date: op.planned_end,
          new_due_date: planningAddDays(op.planned_end, 1),
          delay_days: 1,
          impact_level: 'HIGH',
        })
        affected += 1
      }
    }
    scenario.impact_summary = `设备 ${body.reference_ref} 停机影响 ${affected} 道工序`
  } else if (sType === 'MATERIAL_DELAY') {
    for (const op of ops) {
      addImpact({
        production_order_number: op.production_order_number,
        material_code: op.material_code,
        affected_days: 1.5,
        original_due_date: op.planned_end,
        new_due_date: planningAddDays(op.planned_end, 1) + 'T12:00:00',
        delay_days: 1.5,
        impact_level: 'MEDIUM',
      })
    }
    scenario.impact_summary = `${created.length} 道工序受影响，物料延期 1.5 天`
  }
  scenario.status = 'COMPLETED'
  saveDb()
  return ok({ ...clone(scenario), impacts: clone(created) }, 201)
})

route('GET', '/planning/aps/scenarios', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'scenarioSimulations').filter((item) => !item.is_deleted)
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('GET', '/planning/aps/scenarios/:scenarioId', (_ctx, params) => {
  const db = getDb()
  const scenario = requireItem(listOf(db, 'scenarioSimulations'), 'scenario_id', params.scenarioId, '模拟场景')
  return ok({
    ...clone(scenario),
    impacts: clone(
      listOf(db, 'scenarioImpacts').filter(
        (item) => item.scenario_id === scenario.scenario_id && !item.is_deleted
      )
    ),
  })
})

route('GET', '/planning/aps/exceptions', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'scheduleExceptions').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['run_number', 'exception_type', 'severity'])
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

/* ═════════════════════════ P1 轻量 EAM 设备管理 ═════════════════════════ */

const EAM_FAILURE_SEVERITY = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

/** 按工作中心聚合故障停机时长（小时） */
function eamDowntimeByCenter(db: MockDb): Record<string, number> {
  const result: Record<string, number> = {}
  for (const failure of listOf(db, 'equipmentFailures')) {
    if (failure.is_deleted) continue
    const center = failure.work_center_id || ''
    result[center] = (result[center] ?? 0) + toNumber(failure.downtime_hours)
  }
  return result
}

/** EAM 简化 OEE：可用率 = 1 - 故障停机/班次时长；性能率 = 标准工时/实际工时；良品率 = 良品/报工 */
function eamPerformance(db: MockDb, centerReports: any[]) {
  const opIndex = new Map<number, any>()
  for (const ops of Object.values(db.routingOperations ?? {})) {
    for (const op of ops as any[]) opIndex.set(Number(op.id), op)
  }
  const orders = listOf(db, 'productionOrders')
  let standard = 0
  let actual = 0
  for (const report of centerReports) {
    const op = report.routing_operation_id ? opIndex.get(Number(report.routing_operation_id)) : null
    const order = orders.find((item) => item.order_number === report.production_order_number)
    const orderQty = toNumber(order?.quantity)
    const reportedQty = toNumber(report.reported_quantity)
    if (op && orderQty > 0) {
      const ratio = Math.min(reportedQty / orderQty, 1)
      standard +=
        (toNumber(op.setup_time) + toNumber(op.machine_time) + toNumber(op.labor_time)) * ratio
    }
    actual += toNumber(report.machine_time) + toNumber(report.labor_time)
  }
  if (standard <= 0 || actual <= 0) return 1
  return round(Math.max(0, Math.min(1, standard / actual)), 4)
}

function eamOeeSnapshot(db: MockDb, workCenterId?: string | null) {
  const centers = listOf(db, 'workCenters').filter(
    (item) => !item.is_deleted && (!workCenterId || item.work_center_id === workCenterId)
  )
  const calendars = listOf(db, 'workCalendars').filter((item) => !item.is_deleted)
  const resources = listOf(db, 'resources').filter((item) => !item.is_deleted)
  const downtime = eamDowntimeByCenter(db)
  const reports = listOf(db, 'operationReports').filter((item) => !item.is_deleted)

  const rows = centers.map((wc) => {
    const centerId = wc.work_center_id
    const calendar = calendars.find((c) => c.work_center_id === centerId)
    const shiftHours = toNumber(calendar?.capacity_hours, 0) > 0 ? toNumber(calendar?.capacity_hours) : 10
    const downtimeHours = round(downtime[centerId] ?? 0, 2)
    const availability = round(Math.max(0, Math.min(1, 1 - downtimeHours / shiftHours)), 4)
    const centerReports = reports.filter((r) => r.work_center_id === centerId)
    const reportedQty = centerReports.reduce((sum, r) => sum + toNumber(r.reported_quantity), 0)
    const goodQty = centerReports.reduce((sum, r) => sum + toNumber(r.good_quantity ?? r.reported_quantity), 0)
    const quality = reportedQty > 0 ? round(Math.max(0, Math.min(1, goodQty / reportedQty)), 4) : 1
    const performance = eamPerformance(db, centerReports)
    const centerResources = resources.filter((r) => r.work_center_id === centerId)
    return {
      work_center_id: centerId,
      description: wc.description,
      shift_hours: shiftHours,
      downtime_hours: downtimeHours,
      availability,
      performance,
      quality,
      oee: round(availability * performance * quality, 4),
      report_count: centerReports.length,
      reported_qty: round(reportedQty, 2),
      good_qty: round(goodQty, 2),
      resource_count: centerResources.length,
      down_resources: centerResources
        .filter((r) => r.status !== 'ACTIVE')
        .map((r) => r.resource_id),
    }
  })

  const avg = (values: number[]) =>
    values.length ? round(values.reduce((s, v) => s + v, 0) / values.length, 4) : 0
  const availability = avg(rows.map((r) => r.availability))
  const performance = avg(rows.map((r) => r.performance))
  const quality = avg(rows.map((r) => r.quality))
  const summary = {
    availability,
    performance,
    quality,
    oee: round(availability * performance * quality, 4),
  }
  return { generated_at: nowIso(), summary, work_centers: rows }
}

route('GET', '/planning/eam/overview', () => {
  const db = getDb()
  const plans = listOf(db, 'maintenancePlans').filter((item) => !item.is_deleted)
  const orders = listOf(db, 'maintenanceOrders').filter((item) => !item.is_deleted)
  const failures = listOf(db, 'equipmentFailures').filter((item) => !item.is_deleted)
  const resources = listOf(db, 'resources').filter((item) => !item.is_deleted)
  const now = nowIso()
  const duePlans = plans
    .filter((item) => item.status === 'PLANNED' && item.next_due_at && item.next_due_at <= now)
    .sort((a, b) => String(a.next_due_at).localeCompare(String(b.next_due_at)))
    .slice(0, 20)
  const openFailures = failures
    .filter((item) => item.status !== 'CLOSED')
    .sort((a, b) => String(b.occurred_at).localeCompare(String(a.occurred_at)))
    .slice(0, 20)
  return ok({
    plans: plans.length,
    due_plans: duePlans.length,
    orders: orders.length,
    orders_planned: orders.filter((item) => item.status === 'PLANNED').length,
    orders_done: orders.filter((item) => item.status === 'DONE').length,
    failures: failures.length,
    open_failures: openFailures.length,
    critical_failures: openFailures.filter((item) => item.severity === 'CRITICAL').length,
    resources: resources.length,
    resources_down: resources.filter((item) => item.status !== 'ACTIVE').length,
    due_plan_items: clone(duePlans),
    open_failure_items: clone(openFailures),
  })
})

route('GET', '/planning/eam/plans', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'maintenancePlans').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['resource_id', 'status', 'maintenance_type'])
  rows.sort((a, b) => String(a.next_due_at ?? '').localeCompare(String(b.next_due_at ?? '')))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/eam/plans', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.resource_id) fail(400, 'resource_id 不能为空')
  const user = requireUser(ctx)
  const resources = listOf(db, 'resources').filter((item) => !item.is_deleted)
  if (!resources.some((item) => item.resource_id === body.resource_id)) {
    fail(404, `设备资源不存在: ${body.resource_id}`)
  }
  const plans = listOf(db, 'maintenancePlans')
  const plan = stampNew(
    {
      id: nextId(plans),
      plan_id: nextNumber(plans, 'plan_id', 'MP'),
      resource_id: body.resource_id,
      maintenance_type: body.maintenance_type || 'INSPECTION',
      cycle_days: Number(body.cycle_days) || 30,
      last_executed_at: null,
      next_due_at: body.next_due_at || nowIso(),
      responsible: body.responsible || null,
      status: body.status || 'PLANNED',
      notes: body.notes || null,
      is_deleted: false,
    },
    user
  )
  plans.push(plan)
  saveDb()
  return ok(clone(plan), 201)
})

route('PUT', '/planning/eam/plans/:planId', (ctx, params) => {
  const db = getDb()
  const plan = requireItem(listOf(db, 'maintenancePlans'), 'plan_id', params.planId, '维护计划')
  const body = ctx.body ?? {}
  if (body.maintenance_type) plan.maintenance_type = body.maintenance_type
  if (body.cycle_days != null) plan.cycle_days = Number(body.cycle_days)
  if (body.next_due_at) plan.next_due_at = body.next_due_at
  if (body.responsible !== undefined) plan.responsible = body.responsible
  if (body.status) plan.status = body.status
  if (body.notes !== undefined) plan.notes = body.notes
  plan.updated_by = requireUser(ctx).username
  plan.updated_at = nowIso()
  saveDb()
  return ok(clone(plan))
})

route('GET', '/planning/eam/orders', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'maintenanceOrders').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['resource_id', 'status', 'plan_id'])
  rows.sort((a, b) => String(b.planned_date ?? '').localeCompare(String(a.planned_date ?? '')))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/eam/orders/:orderNumber/complete', (ctx, params) => {
  const db = getDb()
  const order = requireItem(listOf(db, 'maintenanceOrders'), 'order_number', params.orderNumber, '维护工单')
  if (order.status === 'DONE') fail(400, `维护工单已完成，不能重复完成: ${params.orderNumber}`)
  const body = ctx.body ?? {}
  const user = requireUser(ctx)
  order.status = 'DONE'
  order.completed_at = nowIso()
  order.executed_by = body.executed_by || user.username
  if (body.downtime_hours != null) order.downtime_hours = toNumber(body.downtime_hours)
  if (body.result_note) order.result_note = body.result_note
  order.updated_by = user.username
  // 回写来源维护计划
  if (order.plan_id) {
    const plan = listOf(db, 'maintenancePlans').find((item) => item.plan_id === order.plan_id)
    if (plan) {
      plan.last_executed_at = order.completed_at
      const base = new Date((order.completed_at || '').slice(0, 10) + 'T08:00:00')
      base.setDate(base.getDate() + (Number(plan.cycle_days) || 30))
      plan.next_due_at = base.toISOString().slice(0, 19)
      plan.updated_at = nowIso()
    }
  }
  saveDb()
  return ok(clone(order))
})

route('GET', '/planning/eam/failures', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'equipmentFailures').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['resource_id', 'work_center_id', 'status', 'severity'])
  rows.sort((a, b) => String(b.occurred_at ?? '').localeCompare(String(a.occurred_at ?? '')))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/planning/eam/failures', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!body.resource_id) fail(400, 'resource_id 不能为空')
  const user = requireUser(ctx)
  const resource = listOf(db, 'resources').find(
    (item) => !item.is_deleted && item.resource_id === body.resource_id
  )
  if (!resource) fail(404, `设备资源不存在: ${body.resource_id}`)
  const failures = listOf(db, 'equipmentFailures')
  const failure = stampNew(
    {
      id: nextId(failures),
      failure_number: nextNumber(failures, 'failure_number', 'EF'),
      resource_id: body.resource_id,
      work_center_id: resource.work_center_id || null,
      occurred_at: body.occurred_at || nowIso(),
      resolved_at: null,
      severity: EAM_FAILURE_SEVERITY.includes(body.severity) ? body.severity : 'MEDIUM',
      description: body.description || null,
      root_cause: null,
      action_taken: null,
      downtime_hours: toNumber(body.downtime_hours),
      status: 'OPEN',
      reported_by: user.username,
      is_deleted: false,
    },
    user
  )
  failures.push(failure)
  saveDb()
  return ok(clone(failure), 201)
})

route('POST', '/planning/eam/failures/:failureNumber/resolve', (ctx, params) => {
  const db = getDb()
  const failure = requireItem(
    listOf(db, 'equipmentFailures'),
    'failure_number',
    params.failureNumber,
    '设备故障'
  )
  if (failure.status === 'CLOSED') fail(400, `设备故障已关闭: ${params.failureNumber}`)
  const body = ctx.body ?? {}
  failure.status = 'CLOSED'
  failure.resolved_at = nowIso()
  if (body.root_cause) failure.root_cause = body.root_cause
  if (body.action_taken) failure.action_taken = body.action_taken
  if (body.downtime_hours != null) failure.downtime_hours = toNumber(body.downtime_hours)
  failure.updated_by = requireUser(ctx).username
  failure.updated_at = nowIso()
  saveDb()
  return ok(clone(failure))
})

route('GET', '/planning/eam/oee', (ctx) => {
  const db = getDb()
  return ok(eamOeeSnapshot(db, ctx.query.work_center_id))
})

route('POST', '/planning/eam/generate-due-orders', (ctx) => {
  const db = getDb()
  const user = requireUser(ctx)
  const body = ctx.body ?? {}
  const asOf = body.as_of || nowIso()
  const plans = listOf(db, 'maintenancePlans')
  const orders = listOf(db, 'maintenanceOrders')
  const created: any[] = []
  for (const plan of plans) {
    if (plan.is_deleted || plan.status !== 'PLANNED') continue
    if (!plan.next_due_at || String(plan.next_due_at) > String(asOf)) continue
    const exists = orders.some(
      (item) =>
        !item.is_deleted && item.plan_id === plan.plan_id && item.planned_date === plan.next_due_at
    )
    if (exists) {
      const base = new Date(String(plan.next_due_at).slice(0, 10) + 'T08:00:00')
      base.setDate(base.getDate() + (Number(plan.cycle_days) || 30))
      plan.next_due_at = base.toISOString().slice(0, 19)
      continue
    }
    const order = stampNew(
      {
        id: nextId(orders),
        order_number: nextNumber(orders, 'order_number', 'MO'),
        resource_id: plan.resource_id,
        plan_id: plan.plan_id,
        maintenance_type: plan.maintenance_type || 'INSPECTION',
        planned_date: plan.next_due_at,
        completed_at: null,
        downtime_hours: 0,
        executed_by: null,
        result_note: null,
        status: 'PLANNED',
        is_deleted: false,
      },
      user
    )
    orders.push(order)
    const base = new Date(String(plan.next_due_at).slice(0, 10) + 'T08:00:00')
    base.setDate(base.getDate() + (Number(plan.cycle_days) || 30))
    plan.next_due_at = base.toISOString().slice(0, 19)
    created.push(order)
  }
  saveDb()
  return ok({ generated: created.length, items: clone(created) })
})

/* ------------------------------- QMS 质量管理 ------------------------------- */

const INSPECTION_TYPE_KEYS = ['INCOMING', 'IN_PROCESS', 'FINAL']
const INSPECTION_RESULT_KEYS = ['PASS', 'FAIL', 'HOLD']
const NCR_SOURCE_KEYS = ['INSPECTION', 'REPORT', 'LOT_CARD', 'MANUAL']
const NCR_SEVERITY_KEYS = ['MINOR', 'MAJOR', 'CRITICAL']
const NCR_DISPOSITION_KEYS = ['REWORK', 'SCRAP', 'USE_AS_IS', 'RETURN', 'REVIEW']
const DEMO_RESOURCES = ['RES-DRILL-A-01', 'RES-DRILL-B-01', 'RES-DRILL-C-01', 'RES-DRILL-D-01']

function inspectionPrefix(type: string): string {
  return type === 'INCOMING' ? 'IQC' : type === 'IN_PROCESS' ? 'IPQC' : 'FQC'
}

route('GET', '/qms/overview', () => {
  const db = getDb()
  const inspections = listOf(db, 'inspectionOrders').filter((item) => !item.is_deleted)
  const ncrs = listOf(db, 'nonConformanceReports').filter((item) => !item.is_deleted)
  const byType: Record<string, number> = {}
  for (const t of INSPECTION_TYPE_KEYS) byType[t] = inspections.filter((i) => i.inspection_type === t).length
  const recentFail = inspections
    .filter((i) => i.result === 'FAIL')
    .sort((a, b) => String(b.inspected_at ?? '').localeCompare(String(a.inspected_at ?? '')))
    .slice(0, 20)
  const openNcrs = ncrs
    .filter((n) => n.status === 'OPEN' || n.status === 'UNDER_REVIEW')
    .sort((a, b) => Number(b.id) - Number(a.id))
    .slice(0, 20)
  return ok({
    inspections: inspections.length,
    inspections_completed: inspections.filter((i) => i.status === 'COMPLETED').length,
    inspections_fail: inspections.filter((i) => i.result === 'FAIL').length,
    incoming: byType['INCOMING'],
    in_process: byType['IN_PROCESS'],
    final: byType['FINAL'],
    ncrs: ncrs.length,
    ncrs_open: ncrs.filter((n) => n.status === 'OPEN' || n.status === 'UNDER_REVIEW').length,
    ncrs_closed: ncrs.filter((n) => n.status === 'CLOSED').length,
    ncrs_critical: ncrs.filter((n) => n.severity === 'CRITICAL').length,
    ncrs_equipment: ncrs.filter((n) => n.equipment_cause).length,
    recent_fail_inspections: clone(recentFail),
    open_ncr_items: clone(openNcrs),
    as_of: nowIso(),
  })
})

route('GET', '/qms/inspections', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'inspectionOrders').filter((item) => !item.is_deleted)
  if (ctx.query.type) rows = rows.filter((r) => r.inspection_type === ctx.query.type)
  if (ctx.query.result) rows = rows.filter((r) => r.result === ctx.query.result)
  if (ctx.query.material_code) rows = rows.filter((r) => r.material_code === ctx.query.material_code)
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/qms/inspections', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  if (!INSPECTION_TYPE_KEYS.includes(body.inspection_type)) fail(400, 'inspection_type 无效')
  if (!body.material_code) fail(400, 'material_code 不能为空')
  const user = requireUser(ctx)
  const inspections = listOf(db, 'inspectionOrders')
  const inspection = stampNew(
    {
      id: nextId(inspections),
      inspection_number: nextNumber(inspections, 'inspection_number', inspectionPrefix(body.inspection_type)),
      inspection_type: body.inspection_type,
      material_code: body.material_code,
      lot_number: body.lot_number || null,
      purchase_order_number: body.purchase_order_number || null,
      report_number: body.report_number || null,
      quantity_inspected: toNumber(body.quantity_inspected),
      quantity_ok: 0,
      quantity_rejected: 0,
      inspector: body.inspector || user.username,
      inspected_at: null,
      result: null,
      status: 'DRAFT',
      remarks: body.remarks || null,
      is_deleted: false,
    },
    user
  )
  inspections.push(inspection)
  saveDb()
  return ok(clone(inspection), 201)
})

route('POST', '/qms/inspections/:inspectionNumber/complete', (ctx, params) => {
  const db = getDb()
  const inspection = requireItem(
    listOf(db, 'inspectionOrders'),
    'inspection_number',
    params.inspectionNumber,
    '检验单'
  )
  if (inspection.status === 'COMPLETED') fail(400, `检验单已完成: ${params.inspectionNumber}`)
  const body = ctx.body ?? {}
  const rejected = toNumber(body.quantity_rejected ?? 0)
  const okQty = toNumber(body.quantity_ok ?? 0)
  inspection.quantity_ok = okQty
  inspection.quantity_rejected = rejected
  inspection.inspector = body.inspector || inspection.inspector
  inspection.inspected_at = nowIso()
  inspection.result = INSPECTION_RESULT_KEYS.includes(body.result)
    ? body.result
    : rejected > 0
      ? 'FAIL'
      : 'PASS'
  inspection.status = 'COMPLETED'
  inspection.updated_by = requireUser(ctx).username
  inspection.updated_at = nowIso()
  if (inspection.result === 'FAIL' && body.auto_create_ncr !== false) {
    const ncrs = listOf(db, 'nonConformanceReports')
    const ncr = stampNew(
      {
        id: nextId(ncrs),
        ncr_number: nextNumber(ncrs, 'ncr_number', 'NCR'),
        source_type: 'INSPECTION',
        source_ref: inspection.inspection_number,
        inspection_number: inspection.inspection_number,
        report_number: inspection.report_number || null,
        lot_number: inspection.lot_number || null,
        material_code: inspection.material_code,
        quantity: rejected,
        defect_code: body.defect_code || null,
        defect_desc: body.defect_desc || null,
        severity: 'MAJOR',
        disposition: null,
        disposition_note: null,
        root_cause: null,
        equipment_cause: false,
        failure_number: null,
        status: 'OPEN',
        reviewed_by: null,
        reviewed_at: null,
        closed_by: null,
        closed_at: null,
        is_deleted: false,
      },
      requireUser(ctx)
    )
    ncrs.push(ncr)
  }
  saveDb()
  return ok(clone(inspection))
})

route('GET', '/qms/ncrs', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'nonConformanceReports').filter((item) => !item.is_deleted)
  rows = applyEquals(rows, ctx.query, ['status', 'source_type', 'material_code', 'severity'])
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(paginate(rows, ctx.query)) })
})

route('POST', '/qms/ncrs', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  const user = requireUser(ctx)
  const ncrs = listOf(db, 'nonConformanceReports')
  let quantity = toNumber(body.quantity)
  let lot = body.lot_number || null
  let material = body.material_code || null
  // 报工单来源：自动取报废数量与批次
  if (body.source_type === 'REPORT' && body.report_number) {
    const report = listOf(db, 'operationReports').find(
      (r) => !r.is_deleted && r.report_number === body.report_number
    )
    if (!report) fail(404, `报工单不存在: ${body.report_number}`)
    lot = lot || report.lot_number || null
    if (!material) {
      const order = listOf(db, 'productionOrders').find(
        (o) => o.order_number === report.production_order_number
      )
      material = order?.material_code || null
    }
    if (body.quantity == null) quantity = toNumber(report.scrap_quantity)
  }
  if (!material) fail(400, 'material_code 不能为空')
  const ncr = stampNew(
    {
      id: nextId(ncrs),
      ncr_number: nextNumber(ncrs, 'ncr_number', 'NCR'),
      source_type: NCR_SOURCE_KEYS.includes(body.source_type) ? body.source_type : 'INSPECTION',
      source_ref: body.source_ref || body.report_number || null,
      inspection_number: body.inspection_number || null,
      report_number: body.report_number || null,
      lot_number: lot,
      material_code: material,
      quantity,
      defect_code: body.defect_code || null,
      defect_desc: body.defect_desc || null,
      severity: NCR_SEVERITY_KEYS.includes(body.severity) ? body.severity : 'MAJOR',
      disposition: null,
      disposition_note: null,
      root_cause: null,
      equipment_cause: false,
      failure_number: null,
      status: 'OPEN',
      reviewed_by: null,
      reviewed_at: null,
      closed_by: null,
      closed_at: null,
      is_deleted: false,
    },
    user
  )
  ncrs.push(ncr)
  saveDb()
  return ok(clone(ncr), 201)
})

route('POST', '/qms/ncrs/:ncrNumber/review', (ctx, params) => {
  const db = getDb()
  const ncr = requireItem(
    listOf(db, 'nonConformanceReports'),
    'ncr_number',
    params.ncrNumber,
    '不合格品记录'
  )
  if (ncr.status === 'CLOSED') fail(400, `不合格品记录已关闭: ${params.ncrNumber}`)
  const body = ctx.body ?? {}
  if (NCR_SEVERITY_KEYS.includes(body.severity)) ncr.severity = body.severity
  if (body.root_cause) ncr.root_cause = body.root_cause
  if (body.equipment_cause != null) ncr.equipment_cause = Boolean(body.equipment_cause)
  ncr.reviewed_by = requireUser(ctx).username
  ncr.reviewed_at = nowIso()
  if (ncr.status === 'OPEN') ncr.status = 'UNDER_REVIEW'
  ncr.updated_at = nowIso()
  // 设备原因 → 联动 EAM 故障
  if (ncr.equipment_cause && !ncr.failure_number) {
    const resourceId = DEMO_RESOURCES.includes(body.resource_id) ? body.resource_id : DEMO_RESOURCES[0]
    const failures = listOf(db, 'equipmentFailures')
    const failure = stampNew(
      {
        id: nextId(failures),
        failure_number: nextNumber(failures, 'failure_number', 'EF'),
        resource_id: resourceId,
        work_center_id: null,
        occurred_at: nowIso(),
        resolved_at: null,
        severity: ncr.severity === 'CRITICAL' ? 'HIGH' : 'MEDIUM',
        description: body.failure_desc || `[QMS联动] NCR ${ncr.ncr_number}：${ncr.defect_desc || ''}`,
        root_cause: null,
        action_taken: null,
        downtime_hours: 0,
        status: 'OPEN',
        reported_by: ncr.reviewed_by,
        is_deleted: false,
      },
      requireUser(ctx)
    )
    failures.push(failure)
    ncr.failure_number = failure.failure_number
  }
  saveDb()
  return ok(clone(ncr))
})

route('POST', '/qms/ncrs/:ncrNumber/disposition', (ctx, params) => {
  const db = getDb()
  const ncr = requireItem(
    listOf(db, 'nonConformanceReports'),
    'ncr_number',
    params.ncrNumber,
    '不合格品记录'
  )
  if (ncr.status === 'CLOSED') fail(400, `不合格品记录已关闭: ${params.ncrNumber}`)
  const body = ctx.body ?? {}
  if (!NCR_DISPOSITION_KEYS.includes(body.disposition)) fail(400, 'disposition 无效')
  ncr.disposition = body.disposition
  if (body.disposition_note != null) ncr.disposition_note = body.disposition_note
  if (body.equipment_cause != null) ncr.equipment_cause = Boolean(body.equipment_cause)
  ncr.status = 'DISPOSITIONED'
  ncr.updated_by = requireUser(ctx).username
  ncr.updated_at = nowIso()
  if (ncr.equipment_cause && !ncr.failure_number) {
    const resourceId = DEMO_RESOURCES.includes(body.resource_id) ? body.resource_id : DEMO_RESOURCES[0]
    const failures = listOf(db, 'equipmentFailures')
    const failure = stampNew(
      {
        id: nextId(failures),
        failure_number: nextNumber(failures, 'failure_number', 'EF'),
        resource_id: resourceId,
        work_center_id: null,
        occurred_at: nowIso(),
        resolved_at: null,
        severity: ncr.severity === 'CRITICAL' ? 'HIGH' : 'MEDIUM',
        description: body.failure_desc || `[QMS联动] NCR ${ncr.ncr_number}：${ncr.defect_desc || ''}`,
        root_cause: null,
        action_taken: null,
        downtime_hours: 0,
        status: 'OPEN',
        reported_by: ncr.updated_by,
        is_deleted: false,
      },
      requireUser(ctx)
    )
    failures.push(failure)
    ncr.failure_number = failure.failure_number
  }
  saveDb()
  return ok(clone(ncr))
})

route('POST', '/qms/ncrs/:ncrNumber/close', (ctx, params) => {
  const db = getDb()
  const ncr = requireItem(
    listOf(db, 'nonConformanceReports'),
    'ncr_number',
    params.ncrNumber,
    '不合格品记录'
  )
  if (ncr.status === 'CLOSED') fail(400, `不合格品记录已关闭: ${params.ncrNumber}`)
  const body = ctx.body ?? {}
  if (!ncr.disposition) {
    if (!NCR_DISPOSITION_KEYS.includes(body.disposition)) fail(400, 'NCR 未处置，关闭前请先指定处置方式')
    ncr.disposition = body.disposition
  }
  if (body.disposition_note != null) ncr.disposition_note = body.disposition_note
  ncr.status = 'CLOSED'
  ncr.closed_by = requireUser(ctx).username
  ncr.closed_at = nowIso()
  ncr.updated_at = nowIso()
  saveDb()
  return ok(clone(ncr))
})

route('GET', '/qms/operation-reports/scrap', (ctx) => {
  const db = getDb()
  const rows = listOf(db, 'operationReports')
    .filter((r) => !r.is_deleted && toNumber(r.scrap_quantity) > 0)
    .sort((a, b) => Number(b.id) - Number(a.id))
    .slice(0, Number(ctx.query.limit) || 200)
  return ok({
    items: rows.map((r) => {
      const order = listOf(db, 'productionOrders').find(
        (o) => o.order_number === r.production_order_number
      )
      return {
        report_number: r.report_number,
        production_order_number: r.production_order_number,
        lot_number: r.lot_number || null,
        material_code: order?.material_code || null,
        work_center_id: r.work_center_id,
        operation_no: r.operation_no,
        reported_quantity: toNumber(r.reported_quantity),
        scrap_quantity: toNumber(r.scrap_quantity),
      }
    }),
  })
})

/* ------------------------------- 双向追溯（与 traceability_engine 同构） ------------------------------- */

const TRACE_MAX = 50

function traceNewGraph(): { nodes: any[]; edges: any[]; truncated: boolean } {
  return { nodes: [], edges: [], truncated: false }
}

function traceAddNode(g: ReturnType<typeof traceNewGraph>, type: string, key: string, title: string, extra: any = {}): string {
  const nodeKey = `${type}:${key}`
  if (!g.nodes.some((n) => n.key === nodeKey)) {
    g.nodes.push({ key: nodeKey, type, id: key, title, status: null, quantity: null, time: null, meta: {}, ...extra })
  }
  return nodeKey
}

function traceAddEdge(g: ReturnType<typeof traceNewGraph>, from: string, to: string, label: string): void {
  if (!g.edges.some((e) => e.from === from && e.to === to && e.label === label)) {
    g.edges.push({ from, to, label })
  }
}

function traceExpandOrder(db: any, g: ReturnType<typeof traceNewGraph>, order: any): string {
  const orderKey = traceAddNode(g, 'PRODUCTION_ORDER', order.order_number, `生产订单 ${order.order_number}`, {
    status: order.status,
    quantity: toNumber(order.quantity),
    time: order.planned_start_date || null,
    meta: { material_code: order.material_code, sales_order_number: order.sales_order_number },
  })

  // 生产订单 → 销售订单 → 客户
  const salesOrder = order.sales_order_number
    ? listOf(db, 'salesOrders').find((s) => !s.is_deleted && s.order_number === order.sales_order_number)
    : null
  if (salesOrder) {
    const soKey = traceAddNode(g, 'SALES_ORDER', salesOrder.order_number, `销售订单 ${salesOrder.order_number}`, {
      status: salesOrder.status,
      quantity: toNumber(salesOrder.quantity),
      time: salesOrder.delivery_date || null,
      meta: { material_code: salesOrder.material_code },
    })
    traceAddEdge(g, orderKey, soKey, '来自销售订单')
    const customer = listOf(db, 'customers').find(
      (c) => !c.is_deleted && c.customer_id === salesOrder.customer_id
    )
    if (customer) {
      const custKey = traceAddNode(g, 'CUSTOMER', customer.customer_id, customer.legal_name || customer.customer_id, {
        meta: { industry: customer.customer_industry },
      })
      traceAddEdge(g, soKey, custKey, '客户')
    }
  }

  // 生产订单 → LOT 卡
  const lots = listOf(db, 'lotCards')
    .filter((l) => !l.is_deleted && l.production_order_number === order.order_number)
    .slice(0, TRACE_MAX)
  const lotNumbers: string[] = []
  for (const lot of lots) {
    lotNumbers.push(lot.lot_number)
    const lotKey = traceAddNode(g, 'LOT', lot.lot_number, `批次 ${lot.lot_number}`, {
      status: lot.status,
      quantity: toNumber(lot.quantity),
      time: lot.completed_at || null,
      meta: { material_code: lot.material_code },
    })
    traceAddEdge(g, lotKey, orderKey, '批次归属工单')
  }

  // 生产订单 → 领料
  const issues = listOf(db, 'materialIssues')
    .filter((i) => !i.is_deleted && i.production_order_number === order.order_number)
    .slice(0, TRACE_MAX)
  for (const issue of issues) {
    const issueKey = traceAddNode(g, 'MATERIAL_ISSUE', issue.issue_number, `领料 ${issue.issue_number}`, {
      quantity: toNumber(issue.quantity),
      time: issue.issued_at || null,
      meta: { material_code: issue.material_code, warehouse: issue.warehouse },
    })
    traceAddEdge(g, issueKey, orderKey, '领料')
  }

  // 生产订单 → 报工（工单匹配 OR 批次匹配，与后端一致）
  const reports = listOf(db, 'operationReports')
    .filter(
      (r) =>
        !r.is_deleted &&
        (r.production_order_number === order.order_number ||
          (lotNumbers.length > 0 && lotNumbers.includes(r.lot_number)))
    )
    .slice(0, TRACE_MAX)
  const reportNumbers: string[] = []
  for (const report of reports) {
    reportNumbers.push(report.report_number)
    const reportKey = traceAddNode(g, 'OPERATION_REPORT', report.report_number, `报工 ${report.report_number}`, {
      status: report.status,
      quantity: toNumber(report.reported_quantity),
      time: report.reported_at || null,
      meta: {
        lot_number: report.lot_number,
        operation_name: report.operation_name,
        good_quantity: toNumber(report.good_quantity),
        scrap_quantity: toNumber(report.scrap_quantity),
      },
    })
    traceAddEdge(g, reportKey, orderKey, '报工')
  }

  // 检验：按批次优先，无批次回落物料
  const inspections = listOf(db, 'inspectionOrders')
    .filter(
      (i) =>
        !i.is_deleted &&
        i.material_code === order.material_code &&
        (lotNumbers.length > 0 ? lotNumbers.includes(i.lot_number) || !i.lot_number : true)
    )
    .slice(0, TRACE_MAX)
  const inspectionNumbers: string[] = []
  for (const inspection of inspections) {
    inspectionNumbers.push(inspection.inspection_number)
    const inspKey = traceAddNode(
      g,
      'INSPECTION',
      inspection.inspection_number,
      `检验 ${inspection.inspection_number}`,
      {
        status: inspection.status,
        quantity: toNumber(inspection.quantity_inspected),
        time: inspection.inspected_at || null,
        meta: {
          type: inspection.inspection_type,
          result: inspection.result,
          lot_number: inspection.lot_number,
          quantity_rejected: toNumber(inspection.quantity_rejected),
        },
      }
    )
    traceAddEdge(g, inspKey, orderKey, '检验')
  }

  // NCR：批次 / 检验单 / 报工单 关联
  const ncrs = listOf(db, 'nonConformanceReports')
    .filter(
      (n) =>
        !n.is_deleted &&
        (lotNumbers.length > 0
          ? lotNumbers.includes(n.lot_number) ||
            inspectionNumbers.includes(n.inspection_number) ||
            reportNumbers.includes(n.report_number)
          : n.material_code === order.material_code)
    )
    .slice(0, TRACE_MAX)
  const failureNumbers: string[] = []
  for (const ncr of ncrs) {
    const ncrKey = traceAddNode(g, 'NCR', ncr.ncr_number, `不合格品 ${ncr.ncr_number}`, {
      status: ncr.status,
      quantity: toNumber(ncr.quantity),
      time: ncr.created_at || null,
      meta: {
        severity: ncr.severity,
        disposition: ncr.disposition,
        defect_desc: ncr.defect_desc,
        equipment_cause: ncr.equipment_cause,
      },
    })
    traceAddEdge(g, ncrKey, orderKey, '不合格')
    if (ncr.failure_number) failureNumbers.push(ncr.failure_number)
  }

  // NCR → EAM 设备故障
  if (failureNumbers.length > 0) {
    const failures = listOf(db, 'equipmentFailures')
      .filter((f) => !f.is_deleted && failureNumbers.includes(f.failure_number))
      .slice(0, TRACE_MAX)
    for (const failure of failures) {
      const failKey = traceAddNode(g, 'EQUIPMENT_FAILURE', failure.failure_number, `设备故障 ${failure.failure_number}`, {
        status: failure.status,
        time: failure.occurred_at || null,
        meta: {
          resource_id: failure.resource_id,
          severity: failure.severity,
          description: failure.description,
        },
      })
      traceAddEdge(g, failKey, orderKey, '设备原因')
    }
  }
  return orderKey
}

route('GET', '/traceability/overview', () => {
  const db = getDb()
  const live = (name: string) => listOf(db, name).filter((x) => !x.is_deleted).length
  return ok({
    lots: live('lotCards'),
    production_orders: live('productionOrders'),
    sales_orders: live('salesOrders'),
    materials: live('materials'),
    material_issues: live('materialIssues'),
    operation_reports: live('operationReports'),
    inspections: live('inspectionOrders'),
    ncrs: live('nonConformanceReports'),
    equipment_failures: live('equipmentFailures'),
    purchase_orders: live('purchaseOrders'),
    customers: live('customers'),
  })
})

route('GET', '/traceability/search', (ctx) => {
  const db = getDb()
  const q = String(ctx.query.q ?? '').trim()
  if (!q) return ok({ items: [] })
  const match = (value: unknown) => String(value ?? '').includes(q)
  const items: any[] = []
  for (const lot of listOf(db, 'lotCards').filter((x) => !x.is_deleted && match(x.lot_number)).slice(0, 20)) {
    items.push({ type: 'LOT', id: lot.lot_number, title: `批次 ${lot.lot_number}`, meta: { material_code: lot.material_code } })
  }
  for (const order of listOf(db, 'productionOrders').filter((x) => !x.is_deleted && match(x.order_number)).slice(0, 20)) {
    items.push({ type: 'PRODUCTION_ORDER', id: order.order_number, title: `生产订单 ${order.order_number}`, meta: { material_code: order.material_code } })
  }
  for (const so of listOf(db, 'salesOrders').filter((x) => !x.is_deleted && match(x.order_number)).slice(0, 20)) {
    items.push({ type: 'SALES_ORDER', id: so.order_number, title: `销售订单 ${so.order_number}`, meta: { material_code: so.material_code } })
  }
  for (const material of listOf(db, 'materials')
    .filter((x) => !x.is_deleted && (match(x.material_code) || match(x.material_name)))
    .slice(0, 20)) {
    items.push({ type: 'MATERIAL', id: material.material_code, title: `${material.material_code} ${material.material_name ?? ''}`.trim(), meta: {} })
  }
  for (const ncr of listOf(db, 'nonConformanceReports').filter((x) => !x.is_deleted && match(x.ncr_number)).slice(0, 20)) {
    items.push({
      type: 'NCR',
      id: ncr.ncr_number,
      title: `不合格品 ${ncr.ncr_number}`,
      meta: { trace_lot: ncr.lot_number, trace_material: ncr.material_code, root_id: ncr.lot_number || ncr.material_code },
    })
  }
  return ok({ items: items.slice(0, Number(ctx.query.limit) || 20) })
})

route('GET', '/traceability/lots/:lotNumber', (_ctx, params) => {
  const db = getDb()
  const lotNumber = safeDecode(params.lotNumber)
  const lot = listOf(db, 'lotCards').find((x) => !x.is_deleted && x.lot_number === lotNumber)
  if (!lot) fail(404, `批次不存在: ${lotNumber}`)
  const g = traceNewGraph()
  const lotKey = traceAddNode(g, 'LOT', lot.lot_number, `批次 ${lot.lot_number}`, {
    status: lot.status,
    quantity: toNumber(lot.quantity),
    time: lot.completed_at || null,
    meta: { material_code: lot.material_code, mi_number: lot.mi_number },
  })
  const order = listOf(db, 'productionOrders').find(
    (x) => !x.is_deleted && x.order_number === lot.production_order_number
  )
  if (order) {
    const orderKey = traceExpandOrder(db, g, order)
    traceAddEdge(g, lotKey, orderKey, '生产订单')
  } else {
    const inspections = listOf(db, 'inspectionOrders')
      .filter((x) => !x.is_deleted && x.lot_number === lot.lot_number)
      .slice(0, TRACE_MAX)
    for (const inspection of inspections) {
      const inspKey = traceAddNode(g, 'INSPECTION', inspection.inspection_number, `检验 ${inspection.inspection_number}`, {
        status: inspection.status,
        time: inspection.inspected_at || null,
        meta: { result: inspection.result },
      })
      traceAddEdge(g, inspKey, lotKey, '检验')
    }
  }
  return ok({ root: lotKey, direction: 'FORWARD', ...g })
})

route('GET', '/traceability/materials/:materialCode', (_ctx, params) => {
  const db = getDb()
  const materialCode = safeDecode(params.materialCode)
  const material = listOf(db, 'materials').find((x) => !x.is_deleted && x.material_code === materialCode)
  if (!material) fail(404, `物料不存在: ${materialCode}`)
  const g = traceNewGraph()
  const materialKey = traceAddNode(g, 'MATERIAL', material.material_code, `${material.material_code} ${material.material_name ?? ''}`.trim(), {
    meta: { material_name: material.material_name },
  })

  // 反向：领料 → 工单
  const issues = listOf(db, 'materialIssues')
    .filter((x) => !x.is_deleted && x.material_code === materialCode)
    .slice(0, TRACE_MAX)
  const seenOrders = new Set<string>()
  for (const issue of issues) {
    const issueKey = traceAddNode(g, 'MATERIAL_ISSUE', issue.issue_number, `领料 ${issue.issue_number}`, {
      quantity: toNumber(issue.quantity),
      time: issue.issued_at || null,
      meta: { production_order_number: issue.production_order_number },
    })
    traceAddEdge(g, issueKey, materialKey, '领用')
    if (issue.production_order_number && !seenOrders.has(issue.production_order_number)) {
      const order = listOf(db, 'productionOrders').find(
        (x) => !x.is_deleted && x.order_number === issue.production_order_number
      )
      if (order) {
        seenOrders.add(issue.production_order_number)
        const orderKey = traceExpandOrder(db, g, order)
        traceAddEdge(g, orderKey, issueKey, '领料')
      }
    }
  }

  // 反向：物料级检验 / NCR / 故障
  const inspections = listOf(db, 'inspectionOrders')
    .filter((x) => !x.is_deleted && x.material_code === materialCode)
    .slice(0, TRACE_MAX)
  for (const inspection of inspections) {
    const inspKey = traceAddNode(g, 'INSPECTION', inspection.inspection_number, `检验 ${inspection.inspection_number}`, {
      status: inspection.status,
      time: inspection.inspected_at || null,
      meta: { type: inspection.inspection_type, result: inspection.result },
    })
    traceAddEdge(g, inspKey, materialKey, '检验')
  }
  const ncrs = listOf(db, 'nonConformanceReports')
    .filter((x) => !x.is_deleted && x.material_code === materialCode)
    .slice(0, TRACE_MAX)
  const failureNumbers: string[] = []
  for (const ncr of ncrs) {
    const ncrKey = traceAddNode(g, 'NCR', ncr.ncr_number, `不合格品 ${ncr.ncr_number}`, {
      status: ncr.status,
      quantity: toNumber(ncr.quantity),
      time: ncr.created_at || null,
      meta: { severity: ncr.severity, disposition: ncr.disposition, equipment_cause: ncr.equipment_cause },
    })
    traceAddEdge(g, ncrKey, materialKey, '不合格')
    if (ncr.failure_number) failureNumbers.push(ncr.failure_number)
  }
  if (failureNumbers.length > 0) {
    const failures = listOf(db, 'equipmentFailures')
      .filter((f) => !f.is_deleted && failureNumbers.includes(f.failure_number))
      .slice(0, TRACE_MAX)
    for (const failure of failures) {
      const failKey = traceAddNode(g, 'EQUIPMENT_FAILURE', failure.failure_number, `设备故障 ${failure.failure_number}`, {
        status: failure.status,
        time: failure.occurred_at || null,
        meta: { resource_id: failure.resource_id },
      })
      traceAddEdge(g, failKey, materialKey, '设备原因')
    }
  }

  // 反向：采购来源（演示库可能为空）
  const poLines = listOf(db, 'purchaseOrderLines')
    .filter((x) => !x.is_deleted && x.material_code === materialCode)
    .slice(0, TRACE_MAX)
  for (const line of poLines) {
    const po = listOf(db, 'purchaseOrders').find(
      (x) => !x.is_deleted && x.purchase_order_number === line.purchase_order_number
    )
    const lineKey = traceAddNode(
      g,
      'PURCHASE_ORDER_LINE',
      `${line.purchase_order_number}-${line.line_number}`,
      `采购行 ${line.purchase_order_number}#${line.line_number}`,
      { status: line.status, quantity: toNumber(line.quantity), meta: { received_quantity: toNumber(line.received_quantity) } }
    )
    traceAddEdge(g, lineKey, materialKey, '采购')
    if (po) {
      const poKey = traceAddNode(g, 'PURCHASE_ORDER', po.purchase_order_number, `采购单 ${po.purchase_order_number}`, {
        status: po.status,
        time: po.order_date || null,
        meta: { supplier: po.supplier_name },
      })
      traceAddEdge(g, poKey, lineKey, '采购单')
    }
  }
  return ok({ root: materialKey, direction: 'BACKWARD', ...g })
})

route('GET', '/traceability/orders/:orderNumber', (_ctx, params) => {
  const db = getDb()
  const orderNumber = safeDecode(params.orderNumber)
  const productionOrder = listOf(db, 'productionOrders').find(
    (x) => !x.is_deleted && x.order_number === orderNumber
  )
  const g = traceNewGraph()
  if (productionOrder) {
    const orderKey = traceExpandOrder(db, g, productionOrder)
    return ok({ root: orderKey, direction: 'FORWARD', ...g })
  }
  const salesOrder = listOf(db, 'salesOrders').find((x) => !x.is_deleted && x.order_number === orderNumber)
  if (!salesOrder) fail(404, `订单不存在: ${orderNumber}`)
  const soKey = traceAddNode(g, 'SALES_ORDER', salesOrder.order_number, `销售订单 ${salesOrder.order_number}`, {
    status: salesOrder.status,
    quantity: toNumber(salesOrder.quantity),
    time: salesOrder.delivery_date || null,
    meta: { material_code: salesOrder.material_code },
  })
  const customer = listOf(db, 'customers').find(
    (c) => !c.is_deleted && c.customer_id === salesOrder.customer_id
  )
  if (customer) {
    const custKey = traceAddNode(g, 'CUSTOMER', customer.customer_id, customer.legal_name || customer.customer_id, {
      meta: { industry: customer.customer_industry },
    })
    traceAddEdge(g, soKey, custKey, '客户')
  }
  const orders = listOf(db, 'productionOrders')
    .filter((x) => !x.is_deleted && x.sales_order_number === salesOrder.order_number)
    .slice(0, TRACE_MAX)
  for (const order of orders) {
    const orderKey = traceExpandOrder(db, g, order)
    traceAddEdge(g, orderKey, soKey, '生产订单')
  }
  return ok({ root: soKey, direction: 'FORWARD', ...g })
})

/* ------------------------------- 经营看板（与 management_dashboard 同构） ------------------------------- */

const SALES_OPEN_STATUSES = ['PENDING_APPROVAL', 'APPROVED', 'IN_PRODUCTION', 'PARTIALLY_SHIPPED']
const PRODUCTION_OPEN_STATUSES = ['PLANNED', 'RELEASED', 'IN_PRODUCTION']
const NCR_OPEN_STATUSES = ['OPEN', 'UNDER_REVIEW']

route('GET', '/dashboard/management', () => {
  const db = getDb()
  const live = (name: string) => listOf(db, name).filter((x) => !x.is_deleted)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const dateOf = (value: unknown): Date | null => {
    if (!value) return null
    const d = new Date(String(value))
    return Number.isNaN(d.getTime()) ? null : d
  }

  // 销售
  const salesOrders = live('salesOrders')
  const salesOpen = salesOrders.filter((s) => SALES_OPEN_STATUSES.includes(String(s.status)))
  const sales = {
    orders: salesOrders.length,
    open_orders: salesOpen.length,
    amount_total: round(salesOrders.reduce((sum, x) => sum + toNumber(x.total_amount), 0), 2),
    amount_open: round(salesOpen.reduce((sum, x) => sum + toNumber(x.total_amount), 0), 2),
  }

  // 生产
  const productionOrders = live('productionOrders')
  const byStatus: Record<string, number> = {}
  for (const order of productionOrders) {
    const key = String(order.status)
    byStatus[key] = (byStatus[key] ?? 0) + 1
  }
  const productionOpen = productionOrders.filter((o) => PRODUCTION_OPEN_STATUSES.includes(String(o.status)))
  const productionDelayed = productionOpen.filter((o) => {
    const d = dateOf(o.planned_finish_date)
    return d !== null && d < today
  })
  const finished = productionOrders.filter((o) => ['COMPLETED', 'CLOSED'].includes(String(o.status)))
  const production = {
    orders: productionOrders.length,
    open_orders: productionOpen.length,
    by_status: byStatus,
    completion_rate: productionOrders.length > 0 ? round(finished.length / productionOrders.length, 4) : 0,
    delayed_orders: productionDelayed.length,
  }

  // 质量
  const inspections = live('inspectionOrders')
  const completedInsp = inspections.filter((i) => i.result)
  const inspectedQty = completedInsp.reduce((sum, i) => sum + toNumber(i.quantity_inspected), 0)
  const rejectedQty = completedInsp.reduce((sum, i) => sum + toNumber(i.quantity_rejected), 0)
  const ncrs = live('nonConformanceReports')
  const quality = {
    inspections: inspections.length,
    fail_inspections: completedInsp.filter((i) => i.result === 'FAIL').length,
    first_pass_rate: inspectedQty > 0 ? round(1 - rejectedQty / inspectedQty, 4) : 1,
    ncrs: ncrs.length,
    ncrs_open: ncrs.filter((n) => NCR_OPEN_STATUSES.includes(String(n.status))).length,
    ncrs_equipment: ncrs.filter((n) => n.equipment_cause).length,
  }

  // 设备（复用 eamOeeSnapshot 同一口径）
  const oee = eamOeeSnapshot(db)
  const failures = live('equipmentFailures')
  const equipment = {
    oee: oee.summary.oee,
    availability: oee.summary.availability,
    performance: oee.summary.performance,
    quality: oee.summary.quality,
    open_failures: failures.filter((f) => f.status === 'OPEN').length,
    downtime_hours: round(failures.reduce((sum, f) => sum + toNumber(f.downtime_hours), 0), 2),
    work_centers: oee.work_centers.map((wc: any) => ({
      work_center_id: wc.work_center_id,
      oee: wc.oee,
      downtime_hours: wc.downtime_hours,
    })),
  }

  // 成本
  const variances = live('costVariances')
  const varianceByType: Record<string, number> = {}
  for (const variance of variances) {
    const key = String(variance.variance_type ?? 'UNKNOWN')
    varianceByType[key] = round((varianceByType[key] ?? 0) + toNumber(variance.variance_amount), 2)
  }
  const cost = {
    variance_total: round(variances.reduce((sum, v) => sum + toNumber(v.variance_amount), 0), 2),
    variance_by_type: varianceByType,
    settlements: live('costSettlements').length,
  }

  // 交期
  const salesDelayed = salesOpen.filter((s) => {
    const d = dateOf(s.delivery_date)
    return d !== null && d < today
  })
  const dueMaintenance = live('maintenancePlans').filter((p) => {
    const d = dateOf(p.next_due_at)
    return d !== null && d <= today
  }).length
  const delivery = {
    delayed_sales_orders: salesDelayed.length,
    delayed_production_orders: productionDelayed.length,
    due_maintenance_plans: dueMaintenance,
  }

  // 自动点评（与 ManagementDashboard.insights 同规则）
  const insights: string[] = []
  if (equipment.oee < 0.7) {
    const worst = equipment.work_centers.reduce(
      (min: any, wc: any) => (min == null || wc.oee < min.oee ? wc : min),
      null as any
    )
    if (worst) {
      insights.push(
        `设备综合 OEE ${Math.round(equipment.oee * 100)}% 低于 70%，${worst.work_center_id} 仅 ${Math.round(
          worst.oee * 100
        )}%（停机 ${worst.downtime_hours}h），建议优先排维`
      )
    }
  }
  if (quality.ncrs_open > 0) {
    insights.push(`未关闭不合格品 ${quality.ncrs_open} 张，其中设备原因 ${quality.ncrs_equipment} 张待追溯`)
  }
  if (production.delayed_orders > 0) {
    insights.push(`${production.delayed_orders} 张在制工单已过计划完工日，需要重排或插单评估`)
  }
  if (delivery.delayed_sales_orders > 0) {
    insights.push(`${delivery.delayed_sales_orders} 张销售订单已过承诺交期，交付风险需跟进`)
  }
  if (cost.variance_total !== 0) {
    const worstType = Object.keys(varianceByType).sort(
      (a, b) => Math.abs(varianceByType[b]) - Math.abs(varianceByType[a])
    )[0]
    insights.push(
      `成本差异合计 ${cost.variance_total.toLocaleString()} 元，${worstType ?? '-'} 贡献最大`
    )
  }
  if (insights.length === 0) insights.push('各项经营指标均在正常区间')

  return ok({
    sales,
    production,
    quality,
    equipment,
    cost,
    delivery,
    insights,
    generated_at: nowIso(),
  })
})

/* ------------------------------- 采购闭环（与 api/routers/purchase.py 同构） ------------------------------- */

const PURCHASE_RECEIVABLE = ['RELEASED', 'PARTIALLY_RECEIVED']

function purchaseLineDict(line: any) {
  return {
    line_number: line.line_number,
    material_code: line.material_code,
    quantity: toNumber(line.quantity),
    received_quantity: toNumber(line.received_quantity),
    outstanding_quantity: toNumber(line.quantity) - toNumber(line.received_quantity),
    unit: line.unit,
    unit_price: toNumber(line.unit_price),
    expected_date: line.expected_date || null,
    status: line.status,
    remarks: line.remarks,
  }
}

function purchaseOrderDict(db: any, po: any) {
  const lines = listOf(db, 'purchaseOrderLines')
    .filter((l) => !l.is_deleted && l.purchase_order_number === po.purchase_order_number)
    .sort((a, b) => a.line_number - b.line_number)
    .map((l) => purchaseLineDict(l))
  return {
    purchase_order_number: po.purchase_order_number,
    supplier_id: po.supplier_id,
    supplier_name: po.supplier_name,
    status: po.status,
    order_date: po.order_date || null,
    expected_date: po.expected_date || null,
    currency: po.currency,
    total_amount: toNumber(po.total_amount),
    source_planned_order: po.source_planned_order,
    remarks: po.remarks,
    created_at: po.created_at || null,
    lines,
  }
}

route('GET', '/purchase/purchase-orders', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'purchaseOrders').filter((x) => !x.is_deleted)
  if (ctx.query.status) rows = rows.filter((x) => x.status === ctx.query.status)
  if (ctx.query.supplier_id) rows = rows.filter((x) => x.supplier_id === ctx.query.supplier_id)
  if (ctx.query.material_code) {
    const hit = new Set(
      listOf(db, 'purchaseOrderLines')
        .filter((l) => !l.is_deleted && l.material_code === ctx.query.material_code)
        .map((l) => l.purchase_order_number)
    )
    rows = rows.filter((x) => hit.has(x.purchase_order_number))
  }
  rows.sort((a, b) => Number(b.id) - Number(a.id))
  return ok({ total: rows.length, items: clone(rows.map((po) => purchaseOrderDict(db, po))) })
})

route('GET', '/purchase/purchase-orders/:purchaseOrderNumber', (_ctx, params) => {
  const db = getDb()
  const po = listOf(db, 'purchaseOrders').find(
    (x) => !x.is_deleted && x.purchase_order_number === safeDecode(params.purchaseOrderNumber)
  )
  if (!po) fail(404, `采购单不存在: ${params.purchaseOrderNumber}`)
  return ok(purchaseOrderDict(db, po))
})

route('POST', '/purchase/purchase-orders/:purchaseOrderNumber/receive', (ctx, params) => {
  const db = getDb()
  const number = safeDecode(params.purchaseOrderNumber)
  const po = listOf(db, 'purchaseOrders').find(
    (x) => !x.is_deleted && x.purchase_order_number === number
  )
  if (!po) fail(404, `采购单不存在: ${number}`)
  if (!PURCHASE_RECEIVABLE.includes(String(po.status))) {
    fail(400, `采购单状态为 ${po.status}，不允许收货`)
  }
  const body = ctx.body ?? {}
  const lines = listOf(db, 'purchaseOrderLines')
    .filter((l) => !l.is_deleted && l.purchase_order_number === number)
    .sort((a, b) => a.line_number - b.line_number)
  const lineMap = new Map(lines.map((l) => [l.line_number, l]))
  const targets: Array<{ line_number: number; quantity: number | null }> = body.lines?.length
    ? body.lines
    : lines.map((l) => ({ line_number: l.line_number, quantity: null }))
  if (!targets.length) fail(400, '收货行为空')

  let receivedAny = false
  for (const item of targets) {
    const line = lineMap.get(item.line_number)
    if (!line) fail(404, `采购行不存在: ${number}#${item.line_number}`)
    const outstanding = toNumber(line.quantity) - toNumber(line.received_quantity)
    let quantity: number
    if (item.quantity != null) {
      if (toNumber(item.quantity) > outstanding) {
        fail(400, `行 ${item.line_number} 收货超量：余量 ${outstanding}，请求 ${toNumber(item.quantity)}`)
      }
      quantity = toNumber(item.quantity)
    } else {
      quantity = outstanding
    }
    if (quantity <= 0) continue

    // 库存回冲（原料入库）
    const material = listOf(db, 'materials').find(
      (m) => !m.is_deleted && m.material_code === line.material_code
    )
    if (material) {
      material.current_stock = toNumber(material.current_stock) + quantity
    }
    // 库存流水账本：到货即记 RECEIPT 入库
    appendTransaction(db, {
      material_code: line.material_code,
      transaction_type: 'RECEIPT',
      quantity,
      unit: line.unit,
      reference_number: number,
      reference_type: 'PURCHASE_ORDER',
      operator: ctx.user?.username ?? null,
      remarks: `采购到货: ${number}`,
    })
    line.received_quantity = toNumber(line.received_quantity) + quantity
    line.status = toNumber(line.received_quantity) >= toNumber(line.quantity) ? 'RECEIVED' : 'PARTIAL'
    if (body.remarks) line.remarks = body.remarks
    receivedAny = true
  }

  if (receivedAny) {
    const allFull = lines.every((l) => toNumber(l.received_quantity) >= toNumber(l.quantity))
    po.status = allFull ? 'RECEIVED' : 'PARTIALLY_RECEIVED'
    if (body.remarks) po.remarks = body.remarks
    po.updated_at = nowIso()
  }

  // 到货自动来料检验（IQC）：每个收货行生成一张 DRAFT 检验单（与后端同构）
  const autoIqcNumbers: string[] = []
  if (body.auto_iqc) {
    for (const item of targets) {
      const line = lineMap.get(item.line_number)
      if (!line) continue
      const quantity =
        item.quantity != null ? toNumber(item.quantity) : toNumber(line.quantity) - toNumber(line.received_quantity)
      if (quantity <= 0) continue
      const inspections = listOf(db, 'inspectionOrders')
      inspections.unshift({
        id: nextId(inspections),
        inspection_number: nextNumber(inspections, 'inspection_number', 'IQC'),
        inspection_type: 'INCOMING',
        material_code: line.material_code,
        lot_number: null,
        purchase_order_number: number,
        report_number: null,
        quantity_inspected: quantity,
        quantity_ok: null,
        quantity_rejected: null,
        inspector: body.received_by || 'system',
        inspected_at: null,
        result: null,
        status: 'DRAFT',
        remarks: `收货自动生成: ${number}#${line.line_number}`,
        created_by: ctx.user?.username ?? null,
        created_at: nowIso(),
        updated_by: null,
        updated_at: nowIso(),
        is_deleted: false,
      })
      autoIqcNumbers.push(listOf(db, 'inspectionOrders')[0].inspection_number)
    }
  }

  saveDb()
  const result: any = purchaseOrderDict(db, po)
  if (autoIqcNumbers.length) result.auto_iqc_inspections = autoIqcNumbers
  return ok(result)
})

route('POST', '/purchase/purchase-orders/:purchaseOrderNumber/close', (_ctx, params) => {
  const db = getDb()
  const number = safeDecode(params.purchaseOrderNumber)
  const po = listOf(db, 'purchaseOrders').find(
    (x) => !x.is_deleted && x.purchase_order_number === number
  )
  if (!po) fail(404, `采购单不存在: ${number}`)
  if (po.status === 'CLOSED') fail(400, `采购单已关闭: ${number}`)
  if (po.status === 'CANCELLED') fail(400, `采购单已作废: ${number}`)
  po.status = 'CLOSED'
  po.updated_at = nowIso()
  saveDb()
  return ok(purchaseOrderDict(db, po))
})

/* ------------------------------- 供应商 + 应付账款 ------------------------------- */

function supplierDict(s: any) {
  return { ...clone(s) }
}

route('GET', '/purchase/suppliers', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'suppliers').filter((s: any) => !s.is_deleted)
  const kw = String(ctx.query?.keyword ?? '').trim()
  if (kw) {
    rows = rows.filter(
      (s: any) => String(s.supplier_code).includes(kw) || String(s.supplier_name).includes(kw)
    )
  }
  return ok({ total: rows.length, items: rows.map(supplierDict) })
})

route('GET', '/purchase/suppliers/refs', () => {
  const db = getDb()
  const rows = listOf(db, 'suppliers').filter(
    (s: any) => !s.is_deleted && s.status === 'ACTIVE'
  )
  return ok(rows.map((s: any) => ({ supplier_code: s.supplier_code, supplier_name: s.supplier_name })))
})

// 供应商绩效（双指标：到货及时率 / 来料合格率；注意必须注册在 :code 之前）
route('GET', '/purchase/suppliers/performance', () => {
  const db = getDb()
  const suppliers = listOf(db, 'suppliers').filter((s: any) => !s.is_deleted)
  const orders = listOf(db, 'purchaseOrders')
  const lines = listOf(db, 'purchaseOrderLines').filter((l: any) => !l.is_deleted)

  const receivedAmount: Record<string, number> = {}
  const receivedPos: Record<string, Set<string>> = {}
  for (const line of lines) {
    const po = orders.find((o: any) => !o.is_deleted && o.purchase_order_number === line.purchase_order_number)
    if (!po || !po.supplier_id) continue
    const sid = po.supplier_id
    receivedAmount[sid] = (receivedAmount[sid] ?? 0) + toNumber(line.received_quantity) * toNumber(line.unit_price)
    if (toNumber(line.received_quantity) > 0) {
      ;(receivedPos[sid] ??= new Set()).add(po.purchase_order_number)
    }
  }

  // 及时率：RECEIPT 流水首到日期 vs 单据期望日期
  const firstReceipt: Record<string, string> = {}
  for (const tx of listOf(db, 'materialTransactions')) {
    if (tx.is_deleted || tx.reference_type !== 'PURCHASE_ORDER' || tx.transaction_type !== 'RECEIPT') continue
    const prev = firstReceipt[tx.reference_number]
    if (!prev || String(tx.transaction_date) < prev) {
      firstReceipt[tx.reference_number] = String(tx.transaction_date)
    }
  }
  const onTime: Record<string, number> = {}
  const counted: Record<string, number> = {}
  for (const [poNumber, firstDate] of Object.entries(firstReceipt)) {
    const po = orders.find((o: any) => !o.is_deleted && o.purchase_order_number === poNumber)
    if (!po || !po.supplier_id) continue
    const sid = po.supplier_id
    counted[sid] = (counted[sid] ?? 0) + 1
    if (!po.expected_date || firstDate <= String(po.expected_date)) {
      onTime[sid] = (onTime[sid] ?? 0) + 1
    }
  }

  // 来料合格率：INCOMING + COMPLETED 检验单，经采购单归属供应商
  const iqcTotal: Record<string, number> = {}
  const iqcOk: Record<string, number> = {}
  const iqcCount: Record<string, number> = {}
  for (const insp of listOf(db, 'inspectionOrders')) {
    if (insp.is_deleted || insp.inspection_type !== 'INCOMING' || insp.status !== 'COMPLETED') continue
    const po = orders.find((o: any) => !o.is_deleted && o.purchase_order_number === insp.purchase_order_number)
    if (!po || !po.supplier_id) continue
    const inspected = toNumber(insp.quantity_inspected)
    if (inspected <= 0) continue
    const sid = po.supplier_id
    iqcCount[sid] = (iqcCount[sid] ?? 0) + 1
    iqcTotal[sid] = (iqcTotal[sid] ?? 0) + inspected
    iqcOk[sid] = (iqcOk[sid] ?? 0) + toNumber(insp.quantity_ok)
  }

  return ok({
    items: suppliers.map((s: any) => {
      const sid = s.supplier_code
      const countedN = counted[sid] ?? 0
      const onTimeN = onTime[sid] ?? 0
      const inspectedTotal = iqcTotal[sid] ?? 0
      return {
        supplier_id: sid,
        supplier_name: s.supplier_name,
        rating: s.rating ?? 3,
        po_received_count: receivedPos[sid]?.size ?? 0,
        on_time_count: onTimeN,
        on_time_total: countedN,
        on_time_rate: countedN ? round(onTimeN / countedN, 4) : null,
        iqc_count: iqcCount[sid] ?? 0,
        iqc_pass_rate: inspectedTotal > 0 ? round((iqcOk[sid] ?? 0) / inspectedTotal, 4) : null,
        received_amount: round(receivedAmount[sid] ?? 0, 2),
      }
    }),
  })
})

route('GET', '/purchase/suppliers/:code', (_ctx, params) => {
  const s = listOf(getDb(), 'suppliers').find(
    (x: any) => !x.is_deleted && x.supplier_code === params.code
  )
  if (!s) fail(404, `供应商不存在: ${params.code}`)
  return ok(supplierDict(s))
})

route('POST', '/purchase/suppliers', (ctx) => {
  const db = getDb()
  const rows = listOf(db, 'suppliers')
  const body = ctx.body ?? {}
  if (!body?.supplier_name) fail(400, '供应商名称不能为空')
  const nextId = rows.length ? Math.max(...rows.map((r: any) => r.id)) + 1 : 1
  const item = {
    id: nextId,
    supplier_code: `SUP-${String(nextId).padStart(4, '0')}`,
    supplier_name: body.supplier_name,
    short_name: body.short_name ?? null,
    supplier_type: body.supplier_type ?? 'MATERIAL',
    status: body.status ?? 'ACTIVE',
    contact_person: body.contact_person ?? null,
    contact_phone: body.contact_phone ?? null,
    email: body.email ?? null,
    address: body.address ?? null,
    tax_number: body.tax_number ?? null,
    bank_account: body.bank_account ?? null,
    payment_terms: body.payment_terms ?? null,
    lead_time_days: body.lead_time_days ?? 0,
    default_currency: body.default_currency ?? 'CNY',
    rating: body.rating ?? 3,
    remarks: body.remarks ?? null,
    created_at: nowIso(),
    is_deleted: false,
  }
  rows.push(item)
  saveDb()
  return ok(supplierDict(item), 201)
})

route('PUT', '/purchase/suppliers/:code', (ctx, params) => {
  const db = getDb()
  const s = listOf(db, 'suppliers').find(
    (x: any) => !x.is_deleted && x.supplier_code === params.code
  )
  if (!s) fail(404, `供应商不存在: ${params.code}`)
  Object.assign(s, ctx.body ?? {}, { updated_at: nowIso() })
  saveDb()
  return ok(supplierDict(s))
})

route('POST', '/purchase/suppliers/:code/toggle', (_ctx, params) => {
  const db = getDb()
  const s = listOf(db, 'suppliers').find(
    (x: any) => !x.is_deleted && x.supplier_code === params.code
  )
  if (!s) fail(404, `供应商不存在: ${params.code}`)
  s.status = s.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  s.updated_at = nowIso()
  saveDb()
  return ok(supplierDict(s))
})

route('GET', '/purchase/ap-view', () => {
  const db = getDb()
  const orders = listOf(db, 'purchaseOrders')
  const lines: any[] = []
  for (const po of orders) {
    if (!po.is_deleted) {
      const polines = listOf(db, 'purchaseOrderLines').filter(
        (l: any) => !l.is_deleted && l.purchase_order_number === po.purchase_order_number
      )
      lines.push(...polines)
    }
  }
  const buckets: Record<string, any> = {}
  for (const line of lines) {
    const po = orders.find((o: any) => o.purchase_order_number === line.purchase_order_number)
    if (!po) continue
    const sid = po.supplier_id || '未指定'
    const bucket = buckets[sid] ?? {
      supplier_id: sid,
      supplier_name: po.supplier_name || sid,
      received_amount: 0,
      returned_amount: 0,
      closed_amount: 0,
    }
    const receivedQty = toNumber(line.received_quantity)
    const amount = receivedQty * toNumber(line.unit_price)
    bucket.received_amount += amount
    if (po.status === 'CLOSED') bucket.closed_amount += amount
    buckets[sid] = bucket
  }
  // 审批通过的退货（RETURN）冲减净到货与应付；来源采购单已关闭的，同冲减已结金额
  for (const ret of listOf(db, 'purchaseReturns')) {
    if (ret.is_deleted || ret.return_type !== 'RETURN') continue
    if (!['APPROVED', 'CLOSED'].includes(ret.status)) continue
    const sid = ret.supplier_id || '未指定'
    const po = orders.find((o: any) => o.purchase_order_number === ret.purchase_order_number)
    const bucket = buckets[sid] ?? {
      supplier_id: sid,
      supplier_name: (po?.supplier_name as string) || sid,
      received_amount: 0,
      returned_amount: 0,
      closed_amount: 0,
    }
    const amount = toNumber(ret.total_amount)
    bucket.returned_amount += amount
    bucket.received_amount -= amount
    bucket.closed_amount -= amount
    buckets[sid] = bucket
  }
  const items = Object.values(buckets).map((b: any) => {
    const received = round(b.received_amount, 2)
    const closed = round(Math.max(b.closed_amount, 0), 2)
    return {
      supplier_id: b.supplier_id,
      supplier_name: b.supplier_name,
      received_amount: received,
      returned_amount: round(b.returned_amount ?? 0, 2),
      closed_amount: closed,
      payable_amount: round(received - closed, 2),
    }
  })
  return ok({
    total_payable: round(items.reduce((s: number, x: any) => s + x.payable_amount, 0), 2),
    total_received: round(items.reduce((s: number, x: any) => s + x.received_amount, 0), 2),
    items,
  })
})

/* ------------------------------- 采购申请（PR） ------------------------------- */

function purchaseRequestDict(db: any, pr: any) {
  const lines = listOf(db, 'purchaseRequestLines')
    .filter((l) => !l.is_deleted && l.purchase_request_number === pr.purchase_request_number)
    .sort((a, b) => a.line_number - b.line_number)
    .map((l) => ({ ...clone(l) }))
  return { ...clone(pr), lines }
}

function loadMockPr(db: any, number: string) {
  const pr = listOf(db, 'purchaseRequests').find(
    (x) => !x.is_deleted && x.purchase_request_number === number
  )
  if (!pr) fail(404, `采购申请不存在: ${number}`)
  return pr
}

route('GET', '/purchase/purchase-requests', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'purchaseRequests').filter((x) => !x.is_deleted)
  if (ctx.query.status) rows = rows.filter((x) => x.status === ctx.query.status)
  if (ctx.query.supplier_id) rows = rows.filter((x) => x.supplier_id === ctx.query.supplier_id)
  return ok({ total: rows.length, items: rows.map((p) => purchaseRequestDict(db, p)) })
})

route('GET', '/purchase/purchase-requests/:number', (_ctx, params) => {
  const db = getDb()
  return ok(purchaseRequestDict(db, loadMockPr(db, safeDecode(params.number))))
})

route('POST', '/purchase/purchase-requests', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  const lines = Array.isArray(body.lines) ? body.lines : []
  if (lines.length === 0) fail(400, '采购申请至少需要一行')
  const materials = listOf(db, 'materials')
  const resolved = lines.map((line: any, index: number) => {
    const material = materials.find(
      (m) => !m.is_deleted && m.material_code === line?.material_code
    )
    if (!material) fail(404, `物料不存在: ${line?.material_code}`)
    const quantity = toNumber(line.quantity)
    if (quantity <= 0) fail(400, `行 ${index + 1} 数量必须大于 0`)
    return {
      line_number: index + 1,
      material_code: material.material_code,
      quantity,
      unit: line.unit || material.unit,
      unit_price: toNumber(line.unit_price),
      expected_date: body.expected_date ?? null,
      status: 'OPEN',
      remarks: line.remarks ?? null,
    }
  })
  const prs = listOf(db, 'purchaseRequests')
  const item = stampNew(
    {
      id: nextId(prs),
      purchase_request_number: nextNumber(prs, 'purchase_request_number', 'PRQ'),
      supplier_id: body.supplier_id ?? null,
      supplier_name: body.supplier_name ?? null,
      status: 'DRAFT',
      request_date: nowIso(),
      expected_date: body.expected_date ?? null,
      currency: 'CNY',
      total_amount: round(
        resolved.reduce((sum: number, l: any) => sum + l.quantity * l.unit_price, 0),
        2
      ),
      source_planned_order: body.source_planned_order ?? null,
      requested_by: body.requested_by ?? null,
      converted_po_number: null,
      remarks: body.remarks ?? null,
    },
    ctx.user
  )
  prs.unshift(item)
  for (const line of resolved) {
    listOf(db, 'purchaseRequestLines').unshift({
      id: nextId(listOf(db, 'purchaseRequestLines')),
      purchase_request_number: item.purchase_request_number,
      ...line,
      created_by: ctx.user?.username ?? null,
      created_at: nowIso(),
      is_deleted: false,
    })
  }
  saveDb()
  return ok(purchaseRequestDict(db, item), 201)
})

route('POST', '/purchase/purchase-requests/:number/release', (_ctx, params) => {
  const db = getDb()
  const pr = loadMockPr(db, safeDecode(params.number))
  if (pr.status !== 'DRAFT') fail(400, `采购申请状态为 ${pr.status}，不允许下达`)
  pr.status = 'RELEASED'
  pr.updated_at = nowIso()
  saveDb()
  return ok(purchaseRequestDict(db, pr))
})

route('POST', '/purchase/purchase-requests/:number/cancel', (_ctx, params) => {
  const db = getDb()
  const pr = loadMockPr(db, safeDecode(params.number))
  if (!['DRAFT', 'RELEASED'].includes(pr.status)) {
    fail(400, `采购申请状态为 ${pr.status}，不允许作废`)
  }
  pr.status = 'CANCELLED'
  pr.updated_at = nowIso()
  saveDb()
  return ok(purchaseRequestDict(db, pr))
})

route('POST', '/purchase/purchase-requests/:number/convert', (ctx, params) => {
  const db = getDb()
  const pr = loadMockPr(db, safeDecode(params.number))
  if (pr.status !== 'RELEASED') {
    fail(400, `采购申请状态为 ${pr.status}，仅已下达(RELEASED)申请可转采购单`)
  }
  const lines = listOf(db, 'purchaseRequestLines').filter(
    (l) => !l.is_deleted && l.purchase_request_number === pr.purchase_request_number && l.status === 'OPEN'
  )
  if (lines.length === 0) fail(400, `采购申请无可转换行: ${pr.purchase_request_number}`)

  const orders = listOf(db, 'purchaseOrders')
  const poNumber = nextNumber(orders, 'purchase_order_number', 'PUR')
  orders.unshift({
    id: nextId(orders),
    purchase_order_number: poNumber,
    supplier_id: pr.supplier_id,
    supplier_name: pr.supplier_name,
    status: 'RELEASED',
    order_date: nowIso(),
    expected_date: pr.expected_date,
    currency: pr.currency || 'CNY',
    total_amount: round(lines.reduce((s: number, l: any) => s + toNumber(l.quantity) * toNumber(l.unit_price), 0), 2),
    source_planned_order: pr.source_planned_order,
    remarks: `来源采购申请: ${pr.purchase_request_number}`,
    created_by: ctx.user?.username ?? null,
    created_at: nowIso(),
    is_deleted: false,
  })
  for (const line of lines) {
    listOf(db, 'purchaseOrderLines').unshift({
      id: nextId(listOf(db, 'purchaseOrderLines')),
      purchase_order_number: poNumber,
      line_number: line.line_number,
      material_code: line.material_code,
      quantity: line.quantity,
      received_quantity: 0,
      unit: line.unit,
      unit_price: line.unit_price,
      expected_date: line.expected_date || pr.expected_date,
      status: 'OPEN',
      remarks: null,
      created_by: ctx.user?.username ?? null,
      created_at: nowIso(),
      is_deleted: false,
    })
    line.status = 'CONVERTED'
  }
  pr.status = 'CONVERTED'
  pr.converted_po_number = poNumber
  pr.updated_at = nowIso()
  saveDb()
  return ok(purchaseRequestDict(db, pr))
})

/* ------------------------------- 退货 / 索赔 ------------------------------- */

function purchaseReturnDict(db: any, ret: any) {
  const lines = listOf(db, 'purchaseReturnLines')
    .filter((l) => !l.is_deleted && l.return_number === ret.return_number)
    .sort((a, b) => a.line_number - b.line_number)
    .map((l) => ({ ...clone(l) }))
  return { ...clone(ret), lines }
}

function loadMockReturn(db: any, number: string) {
  const ret = listOf(db, 'purchaseReturns').find(
    (x) => !x.is_deleted && x.return_number === number
  )
  if (!ret) fail(404, `退货索赔单不存在: ${number}`)
  return ret
}

function mockReturnedQtyByLine(db: any, poNumber: string): Record<number, number> {
  const totals: Record<number, number> = {}
  for (const ret of listOf(db, 'purchaseReturns')) {
    if (ret.is_deleted || ret.purchase_order_number !== poNumber) continue
    if (ret.return_type !== 'RETURN' || ret.status === 'REJECTED') continue
    for (const line of listOf(db, 'purchaseReturnLines')) {
      if (line.is_deleted || line.return_number !== ret.return_number) continue
      const key = toNumber(line.purchase_order_line_number)
      totals[key] = (totals[key] ?? 0) + toNumber(line.quantity)
    }
  }
  return totals
}

route('GET', '/purchase/purchase-returns', (ctx) => {
  const db = getDb()
  let rows = listOf(db, 'purchaseReturns').filter((x) => !x.is_deleted)
  if (ctx.query.status) rows = rows.filter((x) => x.status === ctx.query.status)
  if (ctx.query.return_type) rows = rows.filter((x) => x.return_type === ctx.query.return_type)
  if (ctx.query.purchase_order_number) {
    rows = rows.filter((x) => x.purchase_order_number === ctx.query.purchase_order_number)
  }
  return ok({ total: rows.length, items: rows.map((r) => purchaseReturnDict(db, r)) })
})

route('GET', '/purchase/purchase-returns/:number', (_ctx, params) => {
  const db = getDb()
  return ok(purchaseReturnDict(db, loadMockReturn(db, safeDecode(params.number))))
})

route('POST', '/purchase/purchase-returns', (ctx) => {
  const db = getDb()
  const body = ctx.body ?? {}
  const returnType = body.return_type ?? 'RETURN'
  if (!['RETURN', 'CLAIM'].includes(returnType)) fail(400, `return_type 必须为 RETURN/CLAIM，收到: ${returnType}`)
  const po = listOf(db, 'purchaseOrders').find(
    (x) => !x.is_deleted && x.purchase_order_number === body?.purchase_order_number
  )
  if (!po) fail(404, `采购单不存在: ${body?.purchase_order_number}`)
  if (!['PARTIALLY_RECEIVED', 'RECEIVED', 'CLOSED'].includes(po.status)) {
    fail(400, `采购单状态为 ${po.status}，无已到货数量可退/可索赔`)
  }
  const poLines = listOf(db, 'purchaseOrderLines').filter(
    (l) => !l.is_deleted && l.purchase_order_number === po.purchase_order_number
  )
  const returnedTotals = returnType === 'RETURN' ? mockReturnedQtyByLine(db, po.purchase_order_number) : {}

  const rawLines = Array.isArray(body.lines) ? body.lines : []
  if (rawLines.length === 0) fail(400, '退货索赔单至少需要一行')
  const resolved = rawLines.map((line: any, index: number) => {
    const poLine = poLines.find((l) => l.line_number === toNumber(line?.purchase_order_line_number))
    if (!poLine) fail(404, `采购行不存在: ${po.purchase_order_number}#${line?.purchase_order_line_number}`)
    const quantity = toNumber(line.quantity)
    if (quantity <= 0) fail(400, `行 ${index + 1} 数量必须大于 0`)
    if (returnType === 'RETURN') {
      const received = toNumber(poLine.received_quantity)
      const available = received - (returnedTotals[poLine.line_number] ?? 0)
      if (quantity > available) {
        fail(400, `行 ${poLine.line_number} 退货超量：已收 ${received}，已占用退货 ${returnedTotals[poLine.line_number] ?? 0}，可退 ${round(available, 2)}，请求 ${quantity}`)
      }
    }
    return {
      line_number: index + 1,
      purchase_order_line_number: poLine.line_number,
      material_code: poLine.material_code,
      quantity,
      unit: poLine.unit,
      unit_price: toNumber(poLine.unit_price),
      remarks: line.remarks ?? null,
    }
  })

  const rets = listOf(db, 'purchaseReturns')
  const item = stampNew(
    {
      id: nextId(rets),
      return_number: nextNumber(rets, 'return_number', 'RTN'),
      purchase_order_number: po.purchase_order_number,
      supplier_id: po.supplier_id,
      supplier_name: po.supplier_name,
      return_type: returnType,
      status: 'DRAFT',
      return_date: nowIso(),
      total_amount: round(resolved.reduce((s: number, l: any) => s + l.quantity * l.unit_price, 0), 2),
      reason: body.reason ?? null,
      remarks: body.remarks ?? null,
    },
    ctx.user
  )
  rets.unshift(item)
  for (const line of resolved) {
    listOf(db, 'purchaseReturnLines').unshift({
      id: nextId(listOf(db, 'purchaseReturnLines')),
      return_number: item.return_number,
      ...line,
      created_by: ctx.user?.username ?? null,
      created_at: nowIso(),
      is_deleted: false,
    })
  }
  saveDb()
  return ok(purchaseReturnDict(db, item), 201)
})

route('POST', '/purchase/purchase-returns/:number/approve', (ctx, params) => {
  const db = getDb()
  const ret = loadMockReturn(db, safeDecode(params.number))
  if (ret.status !== 'DRAFT') fail(400, `退货索赔单状态为 ${ret.status}，仅草稿(DRAFT)可审批`)
  if (ret.return_type === 'RETURN') {
    const lines = listOf(db, 'purchaseReturnLines').filter(
      (l) => !l.is_deleted && l.return_number === ret.return_number
    )
    // 两阶段：先校验库存充足，再扣减
    for (const line of lines) {
      const material = listOf(db, 'materials').find(
        (m) => !m.is_deleted && m.material_code === line.material_code
      )
      const need = lines
        .filter((l) => l.material_code === line.material_code)
        .reduce((s: number, l: any) => s + toNumber(l.quantity), 0)
      const have = material ? toNumber(material.current_stock) : 0
      if (have < need) fail(400, `库存不足，无法退货: ${line.material_code} 当前 ${have}，需退 ${need}`)
    }
    for (const line of lines) {
      const material = listOf(db, 'materials').find(
        (m) => !m.is_deleted && m.material_code === line.material_code
      )
      if (material) {
        material.current_stock = round(toNumber(material.current_stock) - toNumber(line.quantity), 3)
        material.updated_at = nowIso()
      }
      // 库存流水账本：退货出库记 RETURN
      appendTransaction(db, {
        material_code: line.material_code,
        transaction_type: 'RETURN',
        quantity: -toNumber(line.quantity),
        unit: line.unit,
        reference_number: ret.return_number,
        reference_type: 'PURCHASE_RETURN',
        operator: ctx.user?.username ?? null,
        remarks: `采购退货: ${ret.purchase_order_number}`,
      })
    }
  }
  ret.status = 'APPROVED'
  ret.updated_at = nowIso()
  saveDb()
  return ok(purchaseReturnDict(db, ret))
})

route('POST', '/purchase/purchase-returns/:number/reject', (_ctx, params) => {
  const db = getDb()
  const ret = loadMockReturn(db, safeDecode(params.number))
  if (ret.status !== 'DRAFT') fail(400, `退货索赔单状态为 ${ret.status}，仅草稿(DRAFT)可驳回`)
  ret.status = 'REJECTED'
  ret.updated_at = nowIso()
  saveDb()
  return ok(purchaseReturnDict(db, ret))
})

route('POST', '/purchase/purchase-returns/:number/close', (_ctx, params) => {
  const db = getDb()
  const ret = loadMockReturn(db, safeDecode(params.number))
  if (ret.status !== 'APPROVED') fail(400, `退货索赔单状态为 ${ret.status}，仅已审批(APPROVED)可关闭`)
  ret.status = 'CLOSED'
  ret.updated_at = nowIso()
  saveDb()
  return ok(purchaseReturnDict(db, ret))
})

/* ------------------------------- 路由入口 ------------------------------- */

/* ------------------- 写操作权限门（与 backend/api/routers/auth.py 同构） ------------------- */

const WRITE_ROLE_POLICY: Record<string, string[]> = {
  sd: ['SALES', 'SALES_MANAGER', 'GENERAL_MANAGER', 'ADMIN'],
  eng: ['ENGINEER', 'GENERAL_MANAGER', 'ADMIN'],
  pp: ['PRODUCTION', 'PLANNER', 'GENERAL_MANAGER', 'ADMIN'],
  mm: ['WAREHOUSE', 'PRODUCTION', 'PLANNER', 'GENERAL_MANAGER', 'ADMIN'],
  planning: ['PLANNER', 'GENERAL_MANAGER', 'ADMIN'],
  qms: ['PRODUCTION', 'PLANNER', 'GENERAL_MANAGER', 'ADMIN'],
  purchase: ['WAREHOUSE', 'PRODUCTION', 'PLANNER', 'GENERAL_MANAGER', 'ADMIN'],
  users: ['ADMIN'],
}

const WRITE_METHODS = new Set(['POST', 'PUT', 'DELETE', 'PATCH'])

/** 写方法按域校验角色；只读请求（含 CORS 预检）匿名放行。 */
function enforceWritePermission(ctx: MockContext) {
  if (!WRITE_METHODS.has(ctx.method)) return
  const domain = ctx.path.split('/').filter(Boolean)[0] ?? ''
  const allowed = WRITE_ROLE_POLICY[domain]
  if (!allowed) return
  const user = requireUser(ctx)
  if (user.role === 'ADMIN') return
  if (!allowed.includes(user.role)) {
    fail(403, `当前角色(${user.role})无权在「${domain}」域执行写操作`)
  }
}

export function handleMockRequest(ctx: MockContext): MockResult {
  enforceWritePermission(ctx)

  const pathSegments = ctx.path.split('/').filter(Boolean)
  for (const candidate of routes) {
    if (candidate.method !== ctx.method) continue
    if (candidate.segments.length !== pathSegments.length) continue
    const params: Record<string, string> = {}
    let matched = true
    for (let index = 0; index < candidate.segments.length; index += 1) {
      const segment = candidate.segments[index]
      if (segment.startsWith(':')) {
        params[segment.slice(1)] = decodeURIComponent(pathSegments[index])
      } else if (segment !== pathSegments[index]) {
        matched = false
        break
      }
    }
    if (!matched) continue
    return candidate.handler(ctx, params)
  }
  throw new MockApiError(404, `演示接口未实现: ${ctx.method} ${ctx.path}`, ctx.config)
}
