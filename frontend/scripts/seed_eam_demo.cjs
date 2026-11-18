// EAM 设备管理快照预置脚本：为 snapshot 注入维护计划/维护工单/故障记录演示数据，
// 并将 version 升到 6（清理浏览器旧 localStorage）。
// 同时把 RES-DRILL-B-01 置为 MAINTENANCE，与 APS「资源停机」演示联动；
// 并补齐报工的工艺关联与工时，使 OEE 性能率可计算。
const fs = require('fs');
const path = require('path');

const SNAPSHOT = path.join(__dirname, '..', 'src', 'mock', 'snapshot.json');
const s = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'));

const r2 = (v) => Math.round((Number(v) || 0) * 100) / 100;
const pad = (n, w = 2) => String(n).padStart(w, '0');
const nowIso = () => new Date().toISOString().slice(0, 19);
/** 与后端 naive datetime 一致的本地时间字符串 */
const localIso = (date) => {
  const p = (v) => String(v).padStart(2, '0');
  return (
    `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}` +
    `T${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`
  );
};
const dayAt = (offsetDays, hour = 8) => {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  d.setHours(hour, 0, 0, 0);
  return localIso(d);
};

/* ── 0) 版本升级：version 4 -> 6 ─────────────────────────────────── */
s.version = 6;
s.generatedAt = nowIso();

/* ── 1) RES-DRILL-B-01 置为 MAINTENANCE（演示 APS RESOURCE_DOWN 联动） ── */
if (!Array.isArray(s.resources)) s.resources = [];
const drillB = s.resources.find((r) => r.resource_id === 'RES-DRILL-B-01');
if (drillB) {
  drillB.status = 'MAINTENANCE';
  drillB.notes = 'EAM 演示：内层蚀刻线保养中，APS 排程将产生 RESOURCE_DOWN 异常';
}

/* ── 2) 维护计划（6 条，覆盖全部 APS 演示资源） ───────────────────── */
if (!Array.isArray(s.maintenancePlans)) s.maintenancePlans = [];
if (!Array.isArray(s.maintenanceOrders)) s.maintenanceOrders = [];
if (!Array.isArray(s.equipmentFailures)) s.equipmentFailures = [];

let planSeq = s.maintenancePlans.reduce((m, p) => Math.max(m, Number(p.id) || 0), 0);
const addPlan = (spec) => {
  if (s.maintenancePlans.some((p) => p.plan_id === spec.plan_id)) return;
  planSeq += 1;
  s.maintenancePlans.push({
    id: planSeq,
    plan_id: spec.plan_id,
    resource_id: spec.resource_id,
    maintenance_type: spec.maintenance_type,
    cycle_days: spec.cycle_days,
    last_executed_at: spec.last_executed_at ?? null,
    next_due_at: spec.next_due_at,
    responsible: spec.responsible,
    status: 'PLANNED',
    notes: spec.notes || 'EAM 演示维护计划',
    created_by: 'system',
    created_at: nowIso(),
    updated_by: null,
    updated_at: null,
    is_deleted: false,
  });
};

addPlan({ plan_id: 'MP-DRILL-A1-DAILY', resource_id: 'RES-DRILL-A-01', maintenance_type: 'INSPECTION', cycle_days: 7, last_executed_at: dayAt(-7), next_due_at: dayAt(-1), responsible: '王保全' });
addPlan({ plan_id: 'MP-DRILL-A2-WEEKLY', resource_id: 'RES-DRILL-A-02', maintenance_type: 'LUBRICANT', cycle_days: 14, last_executed_at: dayAt(-14), next_due_at: dayAt(3), responsible: '王保全' });
addPlan({ plan_id: 'MP-DRILL-B1-REPAIR', resource_id: 'RES-DRILL-B-01', maintenance_type: 'REPAIR', cycle_days: 30, last_executed_at: dayAt(-20), next_due_at: dayAt(-2), responsible: '李设备' });
addPlan({ plan_id: 'MP-DRILL-C1-MONTHLY', resource_id: 'RES-DRILL-C-01', maintenance_type: 'OVERHAUL', cycle_days: 30, last_executed_at: dayAt(-30), next_due_at: dayAt(10), responsible: '李设备' });
addPlan({ plan_id: 'MP-DRILL-D1-WEEKLY', resource_id: 'RES-DRILL-D-01', maintenance_type: 'INSPECTION', cycle_days: 7, last_executed_at: dayAt(-3), next_due_at: dayAt(4), responsible: '赵测试' });
addPlan({ plan_id: 'MP-OPR-001-MONTHLY', resource_id: 'RES-OPR-001', maintenance_type: 'INSPECTION', cycle_days: 30, last_executed_at: dayAt(-15), next_due_at: dayAt(15), responsible: '张工' });

/* ── 3) 已完工保养单（2 条，关联来源计划） ───────────────────────── */
let orderSeq = s.maintenanceOrders.reduce((m, o) => Math.max(m, Number(o.id) || 0), 0);
let orderNoSeq = s.maintenanceOrders.reduce((max, o) => {
  const n = Number(String(o.order_number || '').split('-').pop());
  return Number.isFinite(n) ? Math.max(max, n) : max;
}, 0);
const addDoneOrder = (spec) => {
  if (s.maintenanceOrders.some((o) => o.plan_id === spec.plan_id && o.status === 'DONE')) return;
  orderSeq += 1;
  orderNoSeq += 1;
  s.maintenanceOrders.push({
    id: orderSeq,
    order_number: `MO-20261118-${pad(orderNoSeq, 4)}`,
    resource_id: spec.resource_id,
    plan_id: spec.plan_id,
    maintenance_type: spec.maintenance_type,
    planned_date: spec.planned_date,
    completed_at: spec.planned_date,
    downtime_hours: spec.downtime_hours,
    executed_by: '李设备',
    result_note: spec.result_note,
    status: 'DONE',
    created_by: 'system',
    created_at: nowIso(),
    updated_by: null,
    updated_at: null,
    is_deleted: false,
  });
};

addDoneOrder({
  plan_id: 'MP-DRILL-A1-DAILY',
  resource_id: 'RES-DRILL-A-01',
  maintenance_type: 'INSPECTION',
  planned_date: dayAt(-7),
  downtime_hours: 1.0,
  result_note: '日点检完成：气压/导轨润滑/主轴异响均正常',
});
addDoneOrder({
  plan_id: 'MP-DRILL-C1-MONTHLY',
  resource_id: 'RES-DRILL-C-01',
  maintenance_type: 'OVERHAUL',
  planned_date: dayAt(-30),
  downtime_hours: 4.5,
  result_note: '月度大保养完成：更换铣刀夹具并校准行程',
});

/* ── 4) OPEN 故障（RES-DRILL-B-01，昨天发生） ─────────────────────── */
if (!s.equipmentFailures.some((f) => !f.is_deleted && f.resource_id === 'RES-DRILL-B-01' && f.status === 'OPEN')) {
  const failSeq = s.equipmentFailures.reduce((m, f) => Math.max(m, Number(f.id) || 0), 0) + 1;
  const failNo = s.equipmentFailures.reduce((max, f) => {
    const n = Number(String(f.failure_number || '').split('-').pop());
    return Number.isFinite(n) ? Math.max(max, n) : max;
  }, 0) + 1;
  s.equipmentFailures.push({
    id: failSeq,
    failure_number: `EF-20261118-${pad(failNo, 4)}`,
    resource_id: 'RES-DRILL-B-01',
    work_center_id: (drillB && drillB.work_center_id) || 'DRILL-B',
    occurred_at: dayAt(-1, 10),
    resolved_at: null,
    severity: 'HIGH',
    description: '蚀刻线传送段电机异响，喷淋压力波动，待更换传动皮带',
    root_cause: null,
    action_taken: null,
    downtime_hours: 2.5,
    status: 'OPEN',
    reported_by: 'system',
    created_by: 'system',
    created_at: nowIso(),
    updated_by: null,
    updated_at: null,
    is_deleted: false,
  });
}

/* ── 5) 报工补齐工艺关联与工时（OEE 性能率可计算） ─────────────────── */
// 后端 OEE 性能率 = 标准工时 / 实际工时：
//   标准工时来自 routing_operation（setup + machine + labor）× 报工数量占比
//   实际工时取报工的 machine_time + labor_time
// 早期快照报工缺 routing_operation_id 与工时，导致性能率恒为 1。
const reportFixtures = {
  'OR-20251217-0001': { operation_no: '0010', setup_time: 15, machine_time: 90, labor_time: 30, good_quantity: 2 },
  'OR-20251217-0001-9390': { operation_no: '0011', setup_time: 20, machine_time: 110, labor_time: 40, good_quantity: 2 },
  'OR-20251218-0001': { operation_no: '0010', setup_time: 12, machine_time: 70, labor_time: 25, good_quantity: 20 },
  'OR-20251218-0001-6025': { operation_no: '0011', setup_time: 15, machine_time: 90, labor_time: 30, good_quantity: 20 },
  'OR-20251230-0001': { operation_no: '0010', setup_time: 20, machine_time: 110, labor_time: 40, good_quantity: 1 },
  'OR-20251230-0001-1313': { operation_no: '0011', setup_time: 12, machine_time: 70, labor_time: 25, good_quantity: 7 },
};
const routingOps = (s.routingOperations && s.routingOperations['RT-PCB-1001']) || [];
const findOp = (operationNo) => routingOps.find((op) => op.operation_no === operationNo);
let reportFixed = 0;
if (Array.isArray(s.operationReports)) {
  for (const report of s.operationReports) {
    const fixture = reportFixtures[report.report_number];
    if (!fixture) continue;
    const op = findOp(fixture.operation_no);
    if (op) report.routing_operation_id = op.id;
    report.good_quantity = fixture.good_quantity;
    report.setup_time = fixture.setup_time;
    report.machine_time = fixture.machine_time;
    report.labor_time = fixture.labor_time;
    reportFixed += 1;
  }
}

fs.writeFileSync(SNAPSHOT, JSON.stringify(s, null, 2) + '\n', 'utf8');
console.log('EAM 演示快照已预置（version=6）');
console.log('维护计划:', s.maintenancePlans.length, '/ 维护工单:', s.maintenanceOrders.length, '/ 故障记录:', s.equipmentFailures.length);
console.log('报工工艺关联修正:', reportFixed, '条');
const due = s.maintenancePlans.filter((p) => p.next_due_at < nowIso());
console.log('到期计划（可演示“生成到期保养单”）:', due.map((p) => p.plan_id).join(', '));
