// APS 演示数据增强脚本：为 snapshot.json 补充各成品的发布工艺路线 + 今天开工的生产订单，
// 让 APS 排程引擎能生成丰富的甘特图与产能冲突场景。
const fs = require('fs');
const path = require('path');

const SNAPSHOT = path.join(__dirname, '..', 'src', 'mock', 'snapshot.json');
const s = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'));

const r2 = (v) => Math.round((Number(v) || 0) * 100) / 100;
const pad = (n, w = 4) => String(n).padStart(w, '0');

// 今日日期（供新建工单参考）
const today = new Date();
const iso = (d) => d.toISOString().slice(0, 10) + 'T00:00:00';

// 1) 四个成品的工艺路线（每套 2 道工序，工时各异以制造产能冲突）
const FG = ['HF1004ENIGAB01', 'HF1004ENIGAB02', 'HF1004ENIGAB03', 'HF1004ENIGAB04'];
const WORK_CENTERS = ['DRILL-A', 'DRILL-B'];
const OP_SETUP = { HF1004ENIGAB01: 15, HF1004ENIGAB02: 10, HF1004ENIGAB03: 20, HF1004ENIGAB04: 25 };
const OP_MACHINE = { HF1004ENIGAB01: 150, HF1004ENIGAB02: 120, HF1004ENIGAB03: 200, HF1004ENIGAB04: 240 };
const OP_LABOR = { HF1004ENIGAB01: 30, HF1004ENIGAB02: 25, HF1004ENIGAB03: 35, HF1004ENIGAB04: 40 };

const materialByCode = Object.fromEntries(s.materials.map((m) => [m.material_code, m]));
const existingRoutings = new Set(s.routings.map((r) => r.routing_id));
const existingOpsKeys = new Set(Object.keys(s.routingOperations));
let routingSeq = 1;
const routingIdByMaterial = {};
for (const code of FG) {
  const rtId = `RT-PCB-${pad(routingSeq)}`;
  routingIdByMaterial[code] = rtId;
  routingSeq += 1;
}

for (const code of FG) {
  const rtId = routingIdByMaterial[code];
  if (existingRoutings.has(rtId)) continue;
  const baseOp = s.routingOperations['RT-PCB-1001'];
  const setup = OP_SETUP[code];
  const machine = OP_MACHINE[code];
  const labor = OP_LABOR[code];
  const routing = {
    id: s.routings.length + routingSeq,
    routing_id: rtId,
    version: 'A01',
    material_code: code,
    description: `APS 演示工艺路线 ${code}`,
    plant_id: 'SZ-01',
    base_unit: 'PNL',
    base_quantity: 1,
    units_per_panel: 1,
    panel_size: null,
    effective_date: iso(new Date(today.getFullYear() - 1, 0, 1)),
    expiry_date: null,
    status: 'RELEASED',
    change_request_no: null,
    created_by: 'system',
    created_at: iso(today),
    updated_by: null,
    updated_at: null,
  };
  s.routings.push(routing);
  const ops = (baseOp || []).map((b, i) => ({
    ...b,
    id: (b.id || 0) + 100 + routingSeq * 10 + i,
    routing_id: rtId,
    operation_no: i === 0 ? '0010' : '0011',
    work_center_id: WORK_CENTERS[i],
    setup_time: setup,
    machine_time: i === 0 ? machine : Math.round(machine * 0.6),
    labor_time: i === 0 ? labor : Math.round(labor * 0.7),
    operation_name: i === 0 ? 'CNC钻孔' : '内层蚀刻与AOI',
  }));
  s.routingOperations[rtId] = ops;
}

// 2) 为四个成品各建一张今天起 RELEASED 生产订单
const prodOrders = s.productionOrders;
const prodOps = s.productionOrderOperations;
const existingOrders = new Set(prodOrders.map((o) => o.order_number));
const versions = {};
for (const pv of s.productionVersions) versions[pv.material_code] = pv.production_version_id;
let newId = Math.max(0, ...prodOrders.map((o) => Number(o.id) || 0)) + 1;
let opId = Math.max(0, ...Object.values(prodOps).flat().map((o) => Number(o.id) || 0)) + 1;
for (const code of FG) {
  const rtId = routingIdByMaterial[code];
  const orderNo = `PO-APS-${code.slice(-2)}`;
  if (existingOrders.has(orderNo)) continue;
  const qty = 20;
  const start = new Date();
  start.setDate(start.getDate() + 1);
  const finish = new Date(start);
  finish.setDate(finish.getDate() + 7);
  prodOrders.push({
    id: newId,
    order_number: orderNo,
    sales_order_number: null,
    material_code: code,
    production_version_id: versions[code] || null,
    quantity: qty,
    unit: 'PCS',
    planned_start_date: iso(start),
    planned_finish_date: iso(finish),
    actual_start_date: null,
    actual_finish_date: null,
    lot_number: null,
    status: 'RELEASED',
    remarks: 'APS 演示工单',
    sales_quantity: null,
    sales_unit: null,
    conversion_factor: 1,
    created_by: 'system',
    created_at: iso(today),
    updated_by: null,
    updated_at: null,
  });
  const rtOps = s.routingOperations[rtId];
  prodOps[orderNo] = rtOps.map((op, i) => ({
    ...op,
    id: opId + i,
    production_order_number: orderNo,
  }));
  opId += rtOps.length;
  newId += 1;
}

// 3) 更新现有 RT-PCB-1001 工序工时（从 0 改非零）
if (s.routingOperations['RT-PCB-1001']) {
  s.routingOperations['RT-PCB-1001'] = s.routingOperations['RT-PCB-1001'].map((op, i) => ({
    ...op,
    setup_time: 10,
    machine_time: i === 0 ? 120 : 70,
    labor_time: i === 0 ? 25 : 18,
  }));
}

fs.writeFileSync(SNAPSHOT, JSON.stringify(s, null, 2) + '\n', 'utf8');
console.log('APS 演示数据已增强');
console.log('routings:', s.routings.length, 'routingOperations keys:', Object.keys(s.routingOperations).length);
console.log('productionOrders:', s.productionOrders.length, 'prodOps keys:', Object.keys(s.productionOrderOperations).length);