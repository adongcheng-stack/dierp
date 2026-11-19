#!/usr/bin/env node

/**
 * Ontology-Type Sync Validator —— 通用模板 (business-ontology skill)
 *
 * 三角同步: src/mappings.json enumerations <-> generated/types.ts <-> src/shapes.ttl sh:in
 * 外加: 命名空间一致性、必备 NodeShape 清点、TTL/N3 解析、属性声明完整性、
 *       个体类型化、业务数量基线、双类型/单顶层范畴守卫。
 *
 * 新项目使用: 复制本文件到 ontology/scripts/, 只改下方 CONFIG 区, 然后:
 *   node scripts/validate-type-sync.js
 * Exit: 0 全绿 / 1 有问题
 * 依赖: npm i n3 (在 ontology/ 目录)
 */

const fs = require('fs');
const path = require('path');

// Windows 控制台默认 GBK, 输出勾选符号会乱码
if (process.stdout.setEncoding) process.stdout.setEncoding('utf8');

const ROOT = path.resolve(__dirname, '..');

// ═══════════════ CONFIG —— 新项目只改这里 ═══════════════
const CONFIG = {
  // 命名空间 (与 ttl 文件 @prefix : 完全一致, 含 #)
  NS: 'https://dierp.local/ontology/erp/v1#',
  // 陈旧/外域命名空间黑名单 (从参考项目复刻时残留的外域 IRI)
  STALE_NS: ['customplushiesfactory.com', 'clearcustomjewelry.com'],
  // 主本体文件 (类与属性声明所在)
  ONTOLOGY_TTL: 'src/erp-ontology.ttl',
  // 全部数据 TTL (相对 ontology/ 根, 顺序即加载顺序)
  DATA_TTLS: [
    'src/shapes.ttl',
    'data/demo.ttl',
  ],
  // N3/SWRL 规则文件
  SWRL_FILES: ['src/rules.swrl'],
  // 枚举名 -> shapes.ttl 中对应 sh:path 属性名 (Check2)
  // 可选 shape 字段：限定在某个 NodeShape 内匹配，用于同名属性承载不同枚举的场景
  // （如 :severity 在 MrpException 用 ExceptionSeverity、在 EquipmentFailure 用 FailureSeverity）
  KEY_ENUMS: [
    { name: 'MaterialType', prop: 'materialType' },
    { name: 'ProcurementType', prop: 'procurementType' },
    { name: 'LotSizingRule', prop: 'lotSizingRule' },
    { name: 'MrpRunType', prop: 'runType' },
    { name: 'PlannedOrderType', prop: 'orderType' },
    { name: 'PlannerAction', prop: 'plannerAction' },
    { name: 'MrpExceptionType', prop: 'exceptionType' },
    { name: 'ExceptionSeverity', prop: 'severity', shape: 'MrpExceptionShape' },
    { name: 'ResolutionStatus', prop: 'resolutionStatus' },
    { name: 'DemandType', prop: 'demandType' },
    { name: 'SupplyType', prop: 'supplyType' },
    { name: 'KitStatus', prop: 'kitStatus' },
    { name: 'CostRateType', prop: 'rateType' },
    { name: 'VarianceType', prop: 'varianceType' },
    // APS 高级排程
    { name: 'ResourceStatus', prop: 'status', shape: 'ResourceShape' },
    { name: 'ScheduleAlgorithm', prop: 'scheduleAlgorithm', shape: 'ScheduleRunShape' },
    { name: 'ScheduleRunStatus', prop: 'status', shape: 'ScheduleRunShape' },
    { name: 'ScheduleOpStatus', prop: 'status', shape: 'ScheduledOperationShape' },
    { name: 'ScheduleExceptionType', prop: 'exceptionType', shape: 'ScheduleExceptionShape' },
    { name: 'ScenarioType', prop: 'scenarioType', shape: 'ScenarioSimulationShape' },
    // EAM 设备管理
    { name: 'MaintenanceType', prop: 'maintenanceType', shape: 'MaintenancePlanShape' },
    { name: 'MaintenanceStatus', prop: 'status', shape: 'MaintenancePlanShape' },
    { name: 'FailureStatus', prop: 'status', shape: 'EquipmentFailureShape' },
    { name: 'FailureSeverity', prop: 'severity', shape: 'EquipmentFailureShape' },
    // QMS 质量管理
    { name: 'InspectionType', prop: 'inspectionType', shape: 'InspectionOrderShape' },
    { name: 'InspectionResult', prop: 'result', shape: 'InspectionOrderShape' },
    { name: 'InspectionStatus', prop: 'status', shape: 'InspectionOrderShape' },
    { name: 'NcrSourceType', prop: 'sourceType', shape: 'NonConformanceReportShape' },
    { name: 'NcrSeverity', prop: 'severity', shape: 'NonConformanceReportShape' },
    { name: 'NcrDisposition', prop: 'disposition', shape: 'NonConformanceReportShape' },
    { name: 'NcrStatus', prop: 'status', shape: 'NonConformanceReportShape' },
    // 采购域扩展
    { name: 'SupplierStatus', prop: 'status', shape: 'SupplierShape' },
    { name: 'PurchaseRequestStatus', prop: 'status', shape: 'PurchaseRequestShape' },
    { name: 'ReturnType', prop: 'returnType', shape: 'PurchaseReturnShape' },
    { name: 'ReturnStatus', prop: 'status', shape: 'PurchaseReturnShape' },
    // 销售域：发货/发票/应收（三线打通）
    { name: 'DeliveryStatus', prop: 'status', shape: 'SalesDeliveryShape' },
    { name: 'InvoiceStatus', prop: 'status', shape: 'SalesInvoiceShape' },
    { name: 'ReceivableEntryType', prop: 'entryType', shape: 'ReceivableEntryShape' },
    // 资金域：应付/收款（P1 双闭环）
    { name: 'SupplierInvoiceStatus', prop: 'status', shape: 'SupplierInvoiceShape' },
    { name: 'PaymentMethod', prop: 'method', shape: 'SupplierPaymentShape' },
    { name: 'PaymentMethod', prop: 'method', shape: 'ReceiptShape' },
  ],
  // 必须存在的 NodeShape 名 (Check4)
  REQUIRED_SHAPES: [
    'MaterialShape', 'PlanningPolicyShape', 'SalesOrderShape', 'ForecastShape',
    'MpsPlanShape', 'MpsEntryShape', 'MrpRunShape', 'PlannedOrderShape',
    'MrpExceptionShape', 'ProductionOrderShape', 'PurchaseOrderShape',
    'BOMShape', 'BomLineShape', 'RoutingOperationShape', 'CostRateShape',
    'WorkCalendarShape', 'KittingResultShape', 'CostVarianceShape',
    'PeggingLinkShape', 'CostSettlementShape', 'MpsEntryMaterialShape',
    'StandardCostShape', 'ProductionCostShape',
    'ResourceShape', 'SkillMatrixShape', 'ChangeoverMatrixShape',
    'ScheduleRunShape', 'ScheduledOperationShape', 'ScheduleExceptionShape',
    'ScenarioSimulationShape', 'ScenarioImpactShape',
    'MaintenancePlanShape', 'MaintenanceOrderShape', 'EquipmentFailureShape',
    'InspectionOrderShape', 'NonConformanceReportShape',
    'SupplierShape', 'PurchaseRequestShape', 'PurchaseReturnShape',
    'SalesDeliveryShape', 'SalesInvoiceShape', 'ReceivableEntryShape',
    'SupplierInvoiceShape', 'SupplierPaymentShape', 'PaymentAllocationShape',
    'ReceiptShape', 'ReceiptAllocationShape',
  ],
  // 业务数量基线: 类名 -> 期望实例数 (Check8; 0 表示不检查该项可删除)
  BASELINE: {
    Material: 9,
    SalesOrder: 3,
    Forecast: 2,
    MpsPlan: 1,
    MpsEntry: 4,
    MrpRun: 1,
    PlannedOrder: 5,
    MrpException: 3,
    ProductionOrder: 2,
    PurchaseOrder: 1,
    BOM: 3,
    BomLine: 9,
    Routing: 1,
    RoutingOperation: 3,
    PlanningPolicy: 6,
    CostRate: 3,
    WorkCalendar: 3,
    PeggingLink: 3,
    KittingResult: 2,
    CostVariance: 2,
    CostSettlement: 1,
    StandardCost: 1,
    ProductionCost: 1,
    MaintenancePlan: 1,
    MaintenanceOrder: 1,
    EquipmentFailure: 1,
    InspectionOrder: 2,
    NonConformanceReport: 2,
    Supplier: 4,
  },
  // 六个互斥顶层范畴 (一般不改)
  TOP_CATEGORIES: ['Agent', 'PhysicalObject', 'Document', 'DocumentLine', 'NormativeRule', 'EventRecord'],
};
// ═══════════════ CONFIG 结束 ═══════════════

const MAPPINGS = path.join(ROOT, 'src', 'mappings.json');
const TYPES_TS = path.join(ROOT, 'generated', 'types.ts');
const SHAPES_TTL = path.join(ROOT, 'src', 'shapes.ttl');

let hasErrors = false;
function logOk(msg) { console.log(`  \u2713 ${msg}`); }
function logErr(msg) { console.error(`  \u2717 ${msg}`); hasErrors = true; }

console.log(`\n\ud83d\udd0d Ontology-Type Sync Validator (${path.basename(ROOT)})\n`);
console.log('\u2501'.repeat(50));

const mappings = JSON.parse(fs.readFileSync(MAPPINGS, 'utf8'));
const typesContent = fs.readFileSync(TYPES_TS, 'utf8');
const shapesContent = fs.readFileSync(SHAPES_TTL, 'utf8');
const ontoContent = fs.readFileSync(path.join(ROOT, CONFIG.ONTOLOGY_TTL), 'utf8');

// ─── Check 1: mappings.json enumerations ↔ generated/types.ts ──────────
console.log('\n[1] Enum sync: mappings.json <-> generated/types.ts (全量枚举)');

for (const [name, values] of Object.entries(mappings.enumerations || {})) {
  const re = new RegExp(`export type ${name}\\s*=([\\s\\S]*?);`);
  const m = typesContent.match(re);
  if (!m) { logErr(`${name}: not found in generated/types.ts`); continue; }
  const tsValues = [...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1]).sort();
  const mapValues = [...values].sort();
  if (JSON.stringify(tsValues) === JSON.stringify(mapValues)) {
    logOk(`${name}: [${tsValues.length}] values in sync`);
  } else {
    logErr(`${name}: MISMATCH - mappings [${mapValues.join(', ')}] vs types [${tsValues.join(', ')}]`);
  }
}

// ─── Check 2: 关键枚举 ↔ shapes.ttl sh:in ───────────────────────────────
console.log('\n[2] Enum sync: mappings.json <-> shapes.ttl sh:in');

for (const { name, prop, shape } of CONFIG.KEY_ENUMS) {
  // 若指定 shape，则只在该 NodeShape 块内匹配，避免同名属性（如 :status/:severity）串枚举
  let scope = shapesContent;
  if (shape) {
    const blocks = [...shapesContent.matchAll(/^:(\w+Shape) a sh:NodeShape/gm)];
    const idx = blocks.findIndex((b) => b[1] === shape);
    if (idx < 0) { logErr(`${name}: NodeShape :${shape} not found in shapes.ttl`); continue; }
    const start = blocks[idx].index;
    const end = idx + 1 < blocks.length ? blocks[idx + 1].index : shapesContent.length;
    scope = shapesContent.slice(start, end);
  }
  const pathRe = new RegExp(`sh:path :${prop}\\s*;([\\s\\S]{0,400}?)sh:in \\(([^)]*)\\)`);
  const m = scope.match(pathRe);
  if (!m) { logErr(`${name}: no sh:in found for :${prop} in shapes.ttl`); continue; }
  const shapeValues = m[2].trim().split(/\s+/).map((v) => v.replace(/^"|"$/g, '')).sort();
  const mapValues = [...(mappings.enumerations[name] || [])].sort();
  if (JSON.stringify(shapeValues) === JSON.stringify(mapValues)) {
    logOk(`${name} (:${prop}): shapes sh:in = mappings [${mapValues.length}]`);
  } else {
    logErr(`${name} (:${prop}): MISMATCH - shapes [${shapeValues.join(', ')}] vs mappings [${mapValues.join(', ')}]`);
  }
}

// ─── Check 3: Namespace consistency ────────────────────────────────────
console.log('\n[3] Namespace consistency');

if (ontoContent.includes(CONFIG.NS)) logOk(`Ontology namespace: ${CONFIG.NS}`);
else logErr(`Ontology namespace missing expected: ${CONFIG.NS}`);

for (const [file, content] of [['mappings.json', JSON.stringify(mappings)],
  ['shapes.ttl', shapesContent], ['types.ts', typesContent]]) {
  if (content.includes(CONFIG.NS)) logOk(`${file} uses expected namespace`);
  else logErr(`${file} does not reference expected namespace`);
}
for (const bad of CONFIG.STALE_NS) {
  if (ontoContent.includes(bad) || shapesContent.includes(bad)) logErr(`stale/foreign namespace ${bad} present`);
}

// ─── Check 4: SHACL shapes inventory ───────────────────────────────────
console.log('\n[4] SHACL shapes inventory');

const shapeCount = (shapesContent.match(/a sh:NodeShape/g) || []).length;
logOk(`shapes.ttl exists with ${shapeCount} NodeShapes`);
for (const s of CONFIG.REQUIRED_SHAPES) {
  if (shapesContent.includes(s)) logOk(`  ${s} defined`);
  else logErr(`  ${s} MISSING`);
}

// ─── Check 5: TTL / N3 语法解析 ─────────────────────────────────────────
console.log('\n[5] TTL/N3 syntax parsing');

const N3 = require('n3');
const ttlFiles = [CONFIG.ONTOLOGY_TTL, ...CONFIG.DATA_TTLS].map((f) => path.join(ROOT, f));
const n3Files = CONFIG.SWRL_FILES.map((f) => path.join(ROOT, f));

function parseRdf(file, format) {
  return new Promise((resolve, reject) => {
    const parser = new N3.Parser({ format });
    const quads = [];
    parser.parse(fs.readFileSync(file, 'utf8'), (err, quad) => {
      if (err) return reject(err);
      if (quad) quads.push(quad);
      else resolve(quads);
    });
  });
}

const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
const OWL_NS = 'http://www.w3.org/2002/07/owl#';
const SH_NS = 'http://www.w3.org/ns/shacl#';
const NS = CONFIG.NS;
const ontoQuads = [];
const dataQuads = [];
const shapesQuads = [];

(async () => {
  let parseFailed = false;
  for (const file of ttlFiles) {
    if (!fs.existsSync(file)) { logErr(`${path.relative(ROOT, file)} not found`); parseFailed = true; continue; }
    try {
      const quads = await parseRdf(file, 'Turtle');
      logOk(`${path.relative(ROOT, file)}: ${quads.length} triples`);
      if (file.endsWith(CONFIG.ONTOLOGY_TTL.split('/').pop())) ontoQuads.push(...quads);
      else if (file.includes('shapes.ttl')) shapesQuads.push(...quads);
      else dataQuads.push(...quads);
    } catch (e) {
      logErr(`${path.relative(ROOT, file)}: Turtle parse failed - ${String(e.message).split('\n')[0]}`);
      parseFailed = true;
    }
  }
  for (const file of n3Files) {
    try {
      const quads = await parseRdf(file, 'N3');
      logOk(`${path.relative(ROOT, file)}: ${quads.length} triples (N3)`);
    } catch (e) {
      logErr(`${path.relative(ROOT, file)}: N3 parse failed - ${String(e.message).split('\n')[0]}`);
      parseFailed = true;
    }
  }

  // ─── Check 6: 数据/形状中使用的本体属性必须已声明 ──────────────────────
  console.log('\n[6] Ontology property declarations');
  if (!parseFailed) {
    const declared = new Set();
    for (const q of ontoQuads) {
      if (q.predicate.value === RDF_TYPE &&
          (q.object.value === OWL_NS + 'ObjectProperty' || q.object.value === OWL_NS + 'DatatypeProperty')) {
        declared.add(q.subject.value);
      }
    }
    const used = new Set();
    for (const q of dataQuads) {
      if (q.predicate.value.startsWith(NS)) used.add(q.predicate.value);
    }
    for (const q of shapesQuads) {
      if (q.predicate.value === SH_NS + 'path' && q.object.value.startsWith(NS)) {
        used.add(q.object.value);
      }
    }
    const undeclared = [...used].filter((p) => !declared.has(p));
    if (undeclared.length === 0) logOk(`all ${used.size} used ontology properties are declared`);
    else for (const p of undeclared) logErr(`property not declared in ontology ttl: ${p.slice(NS.length)}`);

    // ─── Check 7: 数据中引用的本体个体必须有类型 ────────────────────────
    console.log('\n[7] Typed individuals');
    const typed = new Set();
    for (const q of [...ontoQuads, ...dataQuads, ...shapesQuads]) {
      if (q.predicate.value === RDF_TYPE) typed.add(q.subject.value);
    }
    const referenced = new Set();
    for (const q of dataQuads) {
      for (const t of [q.subject, q.object]) {
        if (t.termType === 'NamedNode' && t.value.startsWith(NS)) referenced.add(t.value);
      }
    }
    const untyped = [...referenced].filter((iri) => !typed.has(iri));
    if (untyped.length === 0) logOk(`all ${referenced.size} referenced individuals are typed`);
    else for (const iri of untyped) logErr(`individual referenced in data but never typed: ${iri.slice(NS.length)}`);
  } else {
    logErr('skipped checks 6/7 due to parse failures');
  }

  // ─── Check 8: 业务数量基线 + 双类型/单顶层范畴守卫 ─────────────────────
  console.log('\n[8] Class-count baseline & double-typed instances');
  if (!parseFailed) {
    const cntClass = (cls) => dataQuads.filter((q) => q.predicate.value === RDF_TYPE && q.object.value === NS + cls).length;
    for (const [cls, want] of Object.entries(CONFIG.BASELINE)) {
      const n = cntClass(cls);
      if (n === want) logOk(`:${cls} typed = ${n}`);
      else logErr(`:${cls} typed = ${n}, 期望 ${want} (业务基线被破坏)`);
    }

    const TOP = CONFIG.TOP_CATEGORIES;
    const typeOf = new Map();
    for (const q of dataQuads) {
      if (q.predicate.value === RDF_TYPE && q.object.value.startsWith(NS)) {
        if (!typeOf.has(q.subject.value)) typeOf.set(q.subject.value, new Set());
        typeOf.get(q.subject.value).add(q.object.value.slice(NS.length));
      }
    }
    let missingTop = 0, multiTop = 0;
    for (const [subj, types] of typeOf) {
      const tops = [...types].filter((t) => TOP.includes(t));
      if (tops.length === 0) { logErr(`${subj.slice(NS.length)} 缺顶层范畴双类型标注`); missingTop++; }
      else if (tops.length > 1) { logErr(`${subj.slice(NS.length)} 命中多个互斥顶层范畴 [${tops.join(', ')}]`); multiTop++; }
    }
    if (missingTop === 0 && multiTop === 0) logOk(`所有数据个体单顶层范畴双类型标注一致 (${typeOf.size} 个)`);
  }

  console.log('\n' + '\u2501'.repeat(50));
  if (hasErrors) {
    console.error('\n\u274c Sync validation FAILED - fix the issues above before merging.\n');
    process.exit(1);
  } else {
    console.log('\n\u2705 All sync checks passed.\n');
    process.exit(0);
  }
})().catch((e) => { console.error('Validator crashed:', e); process.exit(1); });
