// APS 排程快照预置脚本：用与 mock 引擎一致的算法，为 snapshot 的可排程工单生成
// scheduleRuns / scheduledOperations / scheduleExceptions，供 APS 甘特图打开即有数据。
const fs = require('fs');
const path = require('path');

const SNAPSHOT = path.join(__dirname, '..', 'src', 'mock', 'snapshot.json');
const s = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'));

const r2 = (v) => Math.round((Number(v) || 0) * 100) / 100;
const pad = (n, w = 4) => String(n).padStart(w, '0');
const nowIso = () => new Date().toISOString().slice(0, 19);
/** 本地 naive 时间字符串（与后端 naive datetime 一致，不含 Z） */
const localIso = (date) => {
  const p = (v) => String(v).padStart(2, '0');
  return (
    `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}` +
    `T${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`
  );
};

/* ── 1) APS 主数据：工作日历 / 设备资源 / 技能矩阵 / 换产矩阵 ───────── */
if (!Array.isArray(s.workCalendars)) s.workCalendars = [];
if (!Array.isArray(s.resources)) s.resources = [];
if (!Array.isArray(s.skillMatrices)) s.skillMatrices = [];
if (!Array.isArray(s.changeoverMatrices)) s.changeoverMatrices = [];

const wcIds = s.workCenters.filter((w) => !w.is_deleted).map((w) => w.work_center_id);
for (const wcId of wcIds) {
  if (!s.workCalendars.some((c) => c.work_center_id === wcId)) {
    s.workCalendars.push({
      id: s.workCalendars.length + 1,
      calendar_id: `CAL-${wcId}`,
      work_center_id: wcId,
      shift_start: '08:00',
      shift_end: '20:00',
      break_hours: 1,
      capacity_hours: 11,
      utilization: 100,
      workdays: '1,2,3,4,5,6',
      status: 'ACTIVE',
      created_by: 'system',
      created_at: nowIso(),
      updated_by: null,
      updated_at: null,
      is_deleted: false,
    });
  }
}

const RESOURCE_SPEC = [
  { resource_id: 'RES-DRILL-A-01', resource_name: 'CNC钻孔机 A1', work_center_id: 'DRILL-A', resource_type: 'MACHINE', capacity_per_shift: 11, skill_tags: ['DRILLING', 'PCB'] },
  { resource_id: 'RES-DRILL-A-02', resource_name: 'CNC钻孔机 A2', work_center_id: 'DRILL-A', resource_type: 'MACHINE', capacity_per_shift: 11, skill_tags: ['DRILLING', 'PCB'] },
  { resource_id: 'RES-DRILL-B-01', resource_name: '内层蚀刻线 B1', work_center_id: 'DRILL-B', resource_type: 'MACHINE', capacity_per_shift: 11, skill_tags: ['ETCHING', 'AOI'] },
  { resource_id: 'RES-DRILL-C-01', resource_name: '外形铣床 C1', work_center_id: 'DRILL-C', resource_type: 'MACHINE', capacity_per_shift: 11, skill_tags: ['MILLING'] },
  { resource_id: 'RES-DRILL-D-01', resource_name: '测试台 D1', work_center_id: 'DRILL-D', resource_type: 'MACHINE', capacity_per_shift: 11, skill_tags: ['TESTING'] },
  { resource_id: 'RES-OPR-001', resource_name: '主操机员 · 张工', work_center_id: 'DRILL-A', resource_type: 'LABOR', capacity_per_shift: 11, skill_tags: ['SETUP', 'DRILLING'] },
];
for (const spec of RESOURCE_SPEC) {
  if (!s.resources.some((r) => r.resource_id === spec.resource_id)) {
    s.resources.push({
      id: s.resources.length + 1,
      ...spec,
      shift_start: '08:00',
      shift_end: '20:00',
      workdays: '1,2,3,4,5,6',
      status: 'ACTIVE',
      notes: null,
      created_by: 'system',
      created_at: nowIso(),
      updated_by: null,
      updated_at: null,
      is_deleted: false,
    });
  }
}

const SKILL_SPEC = [
  { skill_id: 'SK-001', resource_id: 'RES-OPR-001', skill_code: 'SETUP', skill_name: '换线与调机', proficiency: 1.0 },
  { skill_id: 'SK-002', resource_id: 'RES-OPR-001', skill_code: 'DRILLING', skill_name: '钻孔编程与操作', proficiency: 0.8 },
  { skill_id: 'SK-003', resource_id: 'RES-DRILL-B-01', skill_code: 'AOI', skill_name: 'AOI 缺陷判读', proficiency: 0.9 },
  { skill_id: 'SK-004', resource_id: 'RES-DRILL-D-01', skill_code: 'TESTING', skill_name: '电测试', proficiency: 1.0 },
];
for (const spec of SKILL_SPEC) {
  if (!s.skillMatrices.some((m) => m.skill_id === spec.skill_id)) {
    s.skillMatrices.push({
      id: s.skillMatrices.length + 1,
      ...spec,
      status: 'ACTIVE',
      created_by: 'system',
      created_at: nowIso(),
      updated_by: null,
      updated_at: null,
      is_deleted: false,
    });
  }
}

const CHANGEOVER_SPEC = [
  { changeover_id: 'CO-001', work_center_id: 'DRILL-A', from_operation: '0010', to_operation: '0020', changeover_minutes: 45 },
  { changeover_id: 'CO-002', work_center_id: 'DRILL-A', from_operation: '0010', to_operation: '0010', changeover_minutes: 20 },
  { changeover_id: 'CO-003', work_center_id: 'DRILL-B', from_operation: '0011', to_operation: '0011', changeover_minutes: 25 },
  { changeover_id: 'CO-004', work_center_id: 'DRILL-B', from_operation: '0011', to_operation: '0021', changeover_minutes: 40 },
];
for (const spec of CHANGEOVER_SPEC) {
  if (!s.changeoverMatrices.some((m) => m.changeover_id === spec.changeover_id)) {
    s.changeoverMatrices.push({
      id: s.changeoverMatrices.length + 1,
      ...spec,
      status: 'ACTIVE',
      created_by: 'system',
      created_at: nowIso(),
      updated_by: null,
      updated_at: null,
      is_deleted: false,
    });
  }
}

const planningAddDays = (value, days) => {
  const d = new Date((value || '').slice(0, 10) + 'T00:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10) + 'T00:00:00';
};
const startOfToday = () => {
  const d = new Date();
  return d.toISOString().slice(0, 10) + 'T00:00:00';
};

function calendarFor(workCenterId, start, end) {
  const cal = (s.workCalendars || []).find((c) => c.work_center_id === workCenterId && !c.is_deleted);
  const wc = s.workCenters.find((w) => w.work_center_id === workCenterId);
  const machines = Math.max(1, Number(wc?.number_of_capacities) || 1);
  const shiftStart = Number((cal?.shift_start || '08:00').split(':')[0]);
  const shiftEnd = Number((cal?.shift_end || '20:00').split(':')[0]);
  const breakHours = Number(cal?.break_hours) || 1;
  const utilization = Number(cal?.utilization) || 100;
  const workdays = new Set(String(cal?.workdays || '1,2,3,4,5,6').split(',').map((x) => Number(x.trim())).filter(Number.isFinite));
  return {
    machines, shiftStart, shiftEnd, breakHours, utilization, workdays,
    hoursPerDay: Math.max(0, shiftEnd - shiftStart) - breakHours,
    busy: Array.from({ length: machines }, () => []),
    effective(minutes) { return utilization <= 0 ? Number.MAX_SAFE_INTEGER : (minutes * 100) / utilization; },
    isWorkday(date) { const day = date.getDay(); return workdays.has(day === 0 ? 7 : day); },
    findSlot(durationMinutes, earliest) {
      const need = this.effective(durationMinutes);
      let cursor = new Date(earliest);
      for (let m = 0; m < this.machines; m += 1) {
        cursor = new Date(earliest);
        while (cursor < new Date(end)) {
          if (!this.isWorkday(cursor)) {
            cursor = new Date(cursor); cursor.setDate(cursor.getDate() + 1); cursor.setHours(this.shiftStart, 0, 0, 0);
            continue;
          }
          const dayOpen = new Date(cursor); dayOpen.setHours(this.shiftStart, 0, 0, 0);
          const dayClose = new Date(cursor); dayClose.setHours(this.shiftEnd, 0, 0, 0);
          if (cursor < dayOpen) cursor = dayOpen;
          if (cursor >= dayClose) {
            cursor = new Date(cursor); cursor.setDate(cursor.getDate() + 1); cursor.setHours(this.shiftStart, 0, 0, 0);
            continue;
          }
          const busy = this.busy[m]
            .filter(([bs, be]) => new Date(be) > cursor && new Date(bs) < dayClose)
            .sort((a, b) => (a[0] < b[0] ? -1 : 1));
          let freeStart = cursor;
          let ok = false;
          for (const [bs, be] of busy) {
            const bsD = new Date(bs); const beD = new Date(be);
            if (bsD > freeStart) {
              if ((bsD.getTime() - freeStart.getTime()) / 60000 >= need) {
                const st = freeStart; return { machine: m, start: st, end: new Date(st.getTime() + need * 60000) };
              }
            }
            if (beD > freeStart) freeStart = beD;
          }
          if (freeStart < dayClose && (dayClose.getTime() - freeStart.getTime()) / 60000 >= need) {
            return { machine: m, start: freeStart, end: new Date(freeStart.getTime() + need * 60000) };
          }
          cursor = new Date(cursor); cursor.setDate(cursor.getDate() + 1); cursor.setHours(this.shiftStart, 0, 0, 0);
        }
      }
      return null;
    },
  };
}

function routingFor(materialCode) {
  const routing = s.routings.find((r) => r.material_code === materialCode && r.status === 'RELEASED' && !r.is_deleted);
  if (!routing) return null;
  return { routing, ops: (s.routingOperations[routing.routing_id] || []).slice().sort((a, b) => String(a.operation_no).localeCompare(String(b.operation_no))) };
}

function kittingStatus(orderNumber) {
  const row = s.kittingResults
    .filter((k) => !k.is_deleted && k.source_type === 'PRODUCTION_ORDER' && k.source_ref === orderNumber)
    .sort((a, b) => Number(b.id) - Number(a.id))[0];
  return row ? row.kit_status : null;
}

// 运行一次正排
const start = startOfToday();
const end = planningAddDays(start, 30);

/* ── 2) 演示场景注入：PO-APS-04 交期紧张 + 关键工单齐套部分缺料 ───────── */
if (!Array.isArray(s.kittingResults)) s.kittingResults = [];
const nextSeq = () => Math.max(0, ...s.kittingResults.map((k) => Number(k.id) || 0)) + 1;
const nextKitNo = () => {
  const n = Math.max(0, ...s.kittingResults.map((k) => Number(String(k.result_number || '').split('-').pop()) || 0)) + 1;
  return `KIT-20261117-${String(n).padStart(4, '0')}`;
};
const ensureKit = (orderNumber, materialCode) => {
  const exists = s.kittingResults.some(
    (k) => !k.is_deleted && k.source_type === 'PRODUCTION_ORDER' && k.source_ref === orderNumber
  );
  if (exists) return;
  s.kittingResults.push({
    id: nextSeq(),
    result_number: nextKitNo(),
    source_type: 'PRODUCTION_ORDER',
    source_ref: orderNumber,
    material_code: materialCode,
    kit_status: 'PARTIAL',
    required_qty: 281.4,
    available_qty: 65,
    shortage_qty: 216.4,
    shortage_details: [
      { material_code: 'RM-FR4-150', material_name: 'FR-4覆铜板', unit: 'PCS', required_qty: 70, available_qty: 20, shortage_qty: 50, needed_date: start.slice(0, 10) },
      { material_code: 'RM-PP1080', material_name: '1080半固化片', unit: 'PCS', required_qty: 140, available_qty: 15, shortage_qty: 125, needed_date: start.slice(0, 10) },
    ],
    checked_at: nowIso(),
    remarks: '2 项组件部分缺料',
    is_deleted: false,
  });
};
ensureKit('PO-APS-01', 'HF1004ENIGAB01');
ensureKit('PO-APS-04', 'HF1004ENIGAB04');

// PO-APS-04 交期紧张（明天），排程必然超出 → 演示交期风险异常
const tightOrder = s.productionOrders.find((o) => o.order_number === 'PO-APS-04');
if (tightOrder && (tightOrder.planned_finish_date || '') > planningAddDays(start, 1)) {
  tightOrder.planned_finish_date = planningAddDays(start, 1);
}

const orders = s.productionOrders
  .filter((o) => !o.is_deleted && ['RELEASED', 'IN_PRODUCTION'].includes(o.status))
  .sort((a, b) => String(a.planned_start_date || '').localeCompare(String(b.planned_start_date || '')));

const calendars = new Map();
for (const wc of s.workCenters) if (!wc.is_deleted) calendars.set(wc.work_center_id, calendarFor(wc.work_center_id, start, end));

const run = {
  id: 1,
  run_number: `APS-${start.slice(0, 4)}${start.slice(5, 7)}${start.slice(8, 10)}-0001`,
  run_name: '演示 APS · 未来 4 周',
  algorithm: 'FORWARD',
  status: 'COMPLETED',
  horizon_start: start,
  horizon_end: end,
  source_type: 'PRODUCTION_ORDER',
  generated_by: 'planning',
  generated_at: nowIso(),
  published_at: null,
  operation_count: 0,
  exception_count: 0,
  notes: '演示有限产能排程（4 个成品工单争抢 2 个工作中心）',
  created_by: 'system',
  created_at: nowIso(),
  updated_by: null,
  updated_at: null,
  is_deleted: false,
};

const ops = [];
const exceptions = [];
let opSeq = 0;
let excSeq = 0;

for (const order of orders) {
  let sequence = 0;
  let plannedAt = new Date(order.planned_start_date || start);
  if (plannedAt < new Date(start)) plannedAt = new Date(start);
  const rt = routingFor(order.material_code);
  if (!rt) {
    exceptions.push({
      id: ++excSeq,
      exception_id: `APSEX-${String(excSeq).padStart(4, '0')}`,
      run_number: run.run_number,
      exception_type: 'CAPACITY_OVERLOAD',
      production_order_number: order.order_number,
      work_center_id: null,
      resource_id: null,
      severity: 'WARNING',
      message: `工单 ${order.order_number} 缺少已发布工艺路线，无法排程`,
      suggested_action: '维护并发布工艺路线后重新排程',
      created_at: nowIso(),
      is_deleted: false,
    });
    continue;
  }
  const kit = kittingStatus(order.order_number);
  for (const op of rt.ops) {
    sequence += 1;
    let duration = Number(op.setup_time) + Number(op.machine_time) + Number(op.labor_time);
    if (!duration) duration = 30;
    const calendar = calendars.get(op.work_center_id);
    const slot = calendar ? calendar.findSlot(duration, plannedAt) : null;
    if (!slot) {
      exceptions.push({
        id: ++excSeq,
        exception_id: `APSEX-${String(excSeq).padStart(4, '0')}`,
        run_number: run.run_number,
        exception_type: 'CAPACITY_OVERLOAD',
        production_order_number: order.order_number,
        work_center_id: op.work_center_id,
        resource_id: null,
        severity: 'WARNING',
        message: `工单 ${order.order_number} 工序 ${op.operation_no} 在 ${op.work_center_id} 找不到可用产能`,
        suggested_action: '调整班次/利用率或增加资源后重新排程',
        created_at: nowIso(),
        is_deleted: false,
      });
      plannedAt = new Date(plannedAt.getTime() + duration * 60000);
      continue;
    }
    if (calendar) calendar.busy[slot.machine].push([localIso(slot.start), localIso(slot.end)]);
    plannedAt = new Date(slot.end);
    ops.push({
      id: ++opSeq,
      op_id: `OP-${String(opSeq).padStart(4, '0')}`,
      run_number: run.run_number,
      production_order_number: order.order_number,
      material_code: order.material_code,
      operation_no: op.operation_no,
      operation_name: op.operation_name,
      work_center_id: op.work_center_id,
      resource_id: null,
      sequence,
      planned_qty: Number(order.quantity),
      setup_minutes: Number(op.setup_time),
      run_minutes: Number(op.machine_time) + Number(op.labor_time),
      planned_start: localIso(slot.start),
      planned_end: localIso(slot.end),
      status: 'PLANNED',
      created_by: 'system',
      created_at: nowIso(),
      updated_by: null,
      updated_at: null,
      is_deleted: false,
    });
  }
  const due = new Date(order.planned_finish_date || end);
  const lastEnd = ops
    .filter((o) => o.run_number === run.run_number && o.production_order_number === order.order_number)
    .reduce((mx, o) => (o.planned_end > mx ? o.planned_end : mx), null);
  if (lastEnd && new Date(lastEnd) > due) {
    exceptions.push({
      id: ++excSeq,
      exception_id: `APSEX-${String(excSeq).padStart(4, '0')}`,
      run_number: run.run_number,
      exception_type: 'DUE_DATE_RISK',
      production_order_number: order.order_number,
      work_center_id: null,
      resource_id: null,
      severity: 'WARNING',
      message: `工单 ${order.order_number} 排程可能无法满足交期`,
      suggested_action: '评估提前开始 / 加班 / 委外',
      created_at: nowIso(),
      is_deleted: false,
    });
  }
  if (kit === 'SHORT' || kit === 'PARTIAL') {
    const critical = kit === 'SHORT';
    exceptions.push({
      id: ++excSeq,
      exception_id: `APSEX-${String(excSeq).padStart(4, '0')}`,
      run_number: run.run_number,
      exception_type: 'MATERIAL_SHORTAGE',
      production_order_number: order.order_number,
      work_center_id: null,
      resource_id: null,
      severity: critical ? 'CRITICAL' : 'WARNING',
      message: `工单 ${order.order_number} ${critical ? '物料缺料，不宜下达排程' : '物料部分缺料，排程存在风险'}`,
      suggested_action: critical ? '补料齐套后再排程' : '确认缺料补货计划，必要时调整排程顺序',
      created_at: nowIso(),
      is_deleted: false,
    });
  }
}

run.operation_count = ops.length;
run.exception_count = exceptions.length;

s.scheduleRuns = [run];
s.scheduledOperations = ops;
s.scheduleExceptions = exceptions;

/* ── 3) 预置一个插单模拟场景（打开页面即有数据） ─────────────────────── */
if (!Array.isArray(s.scenarioSimulations)) s.scenarioSimulations = [];
if (!Array.isArray(s.scenarioImpacts)) s.scenarioImpacts = [];
if (s.scenarioSimulations.length === 0 && ops.length > 0) {
  const scenario = {
    id: 1,
    scenario_id: 'SCN-0001',
    run_number: run.run_number,
    scenario_type: 'INSERT_ORDER',
    description: '演示：插入紧急订单 PO-EXP-01，评估对现有排程的冲击',
    reference_ref: null,
    created_by: 'planning',
    created_at: nowIso(),
    impact_summary: '',
    status: 'COMPLETED',
    is_deleted: false,
  };
  const impacts = [];
  let impSeq = 0;
  for (const op of ops) {
    impSeq += 1;
    impacts.push({
      id: impSeq,
      impact_id: `IMP-${String(impSeq).padStart(4, '0')}`,
      scenario_id: scenario.scenario_id,
      production_order_number: op.production_order_number,
      material_code: op.material_code,
      affected_days: 2,
      original_due_date: op.planned_end,
      new_due_date: planningAddDays(op.planned_end, 2),
      delay_days: 2,
      impact_level: 'MEDIUM',
      is_deleted: false,
    });
  }
  scenario.impact_summary = `${impacts.length} 道工序受影响，平均延期 2 天`;
  s.scenarioSimulations.push(scenario);
  s.scenarioImpacts.push(...impacts);
}

fs.writeFileSync(SNAPSHOT, JSON.stringify(s, null, 2) + '\n', 'utf8');
console.log('APS 排程快照已预置');
console.log('run:', run.run_number, 'ops:', ops.length, 'exceptions:', exceptions.length);
console.log('工序示例:');
for (const op of ops.slice(0, 8)) console.log(' ', op.production_order_number, op.operation_no, op.operation_name, '@', op.work_center_id, op.planned_start.slice(0, 16).replace('T', ' '));