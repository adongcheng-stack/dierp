#!/usr/bin/env python3
"""
Ontology Consistency Validator (SHACL + OWL-RL + SWRL) —— 通用模板 (business-ontology skill)

四段语义校验 (补充 validate-type-sync.js 的结构校验):
  1. Syntax  - 每个 TTL 解析为 Turtle; rules.swrl 解析为 N3
  2. SHACL   - shapes.ttl 校验 ontology + 全部数据实例 (业务铁律权威, inference=none)
  3. OWL     - OWL-RL 推理一致: 无 owl:Nothing; 无个体落入 2+ 互斥顶层范畴;
               无跨范畴 domain 泄漏 (共享属性残留 rdfs:domain 被反推进别的类)
  4. SWRL    - 每个 head/body atom 带 swrl:arguments; 派生类禁 owl:equivalentClass

新项目使用: 复制到 ontology/scripts/, 只改 CONFIG 区, 然后:
  python scripts/validate-consistency.py
Exit: 0 一致 / 1 失败
依赖: pip install rdflib pyshacl owlrl
"""

import sys
from pathlib import Path

# Windows GBK 控制台无法输出 ✓/✗ 等符号
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

import owlrl
import rdflib
from pyshacl import validate

ROOT = Path(__file__).resolve().parent.parent

# ═══════════════ CONFIG —— 新项目只改这里 ═══════════════
NS = "https://dierp.local/ontology/erp/v1#"

ONTOLOGY_TTL = ROOT / "src" / "erp-ontology.ttl"
SHAPES_TTL = ROOT / "src" / "shapes.ttl"
SWRL_FILE = ROOT / "src" / "rules.swrl"
DATA_TTLS = [
    ROOT / "src" / "security.ttl",
    ROOT / "data" / "demo.ttl",
]

TOP_CATEGORIES = [
    "Agent", "PhysicalObject", "Document", "DocumentLine",
    "NormativeRule", "EventRecord",
]

# domain 泄漏守卫对: (被误推源类, 被误推目标类)。
# 共享属性（materialCode/status/quantity 等）已全部不声明 rdfs:domain。
LEAK_GUARDS = [
    ("SalesOrder", "PurchaseOrder"),
    ("PlannedOrder", "ProductionOrder"),
]
# 泄漏守卫报错文案模板 (fail 时展示)
LEAK_HINT = "被推理成 :PurchaseOrder/:ProductionOrder (某共享属性仍带 rdfs:domain, 需去 domain 改用 SHACL 约束)"

# 运营模型（YAML）→ 本体的覆盖守卫 (Check5)
MODEL_FILES = ["model/planning.yaml", "model/admin.yaml", "model/dashboard.yaml"]
# 行项目作为父单据的嵌套对象校验（hasRequirement / hasPurchaseLine 等），不单独建 NodeShape。
# 若要改为独立校验，请移除对应豁免并在 shapes.ttl 补形状。
SHAPE_EXEMPT = {
    "MrpRequirement", "PurchaseOrderLine", "PurchaseRequestLine", "PurchaseReturnLine",
}
# ═══════════════ CONFIG 结束 ═══════════════

failures = 0


def ok(msg: str) -> None:
    print(f"  \N{CHECK MARK} {msg}")


def fail(msg: str) -> None:
    global failures
    failures += 1
    print(f"  \N{BALLOT X} {msg}")


TTL_FILES = [ONTOLOGY_TTL, SHAPES_TTL, *DATA_TTLS]

print("\n[1] TTL / N3 syntax")
data = rdflib.Graph()  # ontology + shapes + instances (SHACL data graph, OWL facts)
for f in TTL_FILES:
    try:
        g = rdflib.Graph()
        g.parse(f, format="turtle")
        data += g
        ok(f"{f.relative_to(ROOT)}: {len(g)} triples")
    except Exception as e:
        fail(f"{f.relative_to(ROOT)}: {type(e).__name__}: {str(e).splitlines()[0]}")

rules = rdflib.Graph()
try:
    rules.parse(SWRL_FILE, format="n3")
    ok(f"{SWRL_FILE.relative_to(ROOT)}: {len(rules)} triples (N3)")
except Exception as e:
    fail(f"{SWRL_FILE.relative_to(ROOT)}: {type(e).__name__}: {str(e).splitlines()[0]}")

if failures == 0:
    print("\n[2] SHACL validation (shapes.ttl × ontology + data)")
    shapes = rdflib.Graph()
    shapes.parse(SHAPES_TTL, format="turtle")
    conforms, results_graph, _ = validate(
        data, shacl_graph=shapes, inference="none", advanced=False
    )
    if conforms:
        ok("all shapes conform")
    else:
        SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
        seen = set()
        for res in results_graph.subjects(rdflib.RDF.type, SH.ValidationResult):
            msg = (
                results_graph.value(res, SH.resultMessage)
                or results_graph.value(res, SH.message)
                or "(no message)"
            )
            focus = str(results_graph.value(res, SH.focusNode)).replace(NS, ":")
            path = str(results_graph.value(res, SH.resultPath) or "").replace(NS, ":")
            key = (focus, path, str(msg))
            if key in seen:
                continue
            seen.add(key)
            fail(f"{focus} [{path}]: {msg}")

    print("\n[3] OWL consistency (OWL-RL reasoning)")
    reasoned = rdflib.Graph()
    reasoned += data
    try:
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(reasoned)
        nothing = [s for s in reasoned.subjects(rdflib.RDF.type, rdflib.OWL.Nothing)
                   if isinstance(s, rdflib.URIRef) and str(s).startswith(NS)]
        if nothing:
            for s in nothing:
                fail(f"owl:Nothing entailed for {str(s).replace(NS, ':')}")
        else:
            ok("no owl:Nothing instances")

        tops = {t: rdflib.URIRef(NS + t) for t in TOP_CATEGORIES}
        conflicts = 0
        for s in set(reasoned.subjects(rdflib.RDF.type, None)):
            if not isinstance(s, rdflib.URIRef) or not str(s).startswith(NS):
                continue
            cats = sorted(t for t, uri in tops.items() if (s, rdflib.RDF.type, uri) in reasoned)
            if len(cats) > 1:
                conflicts += 1
                fail(f"{str(s).replace(NS, ':')} is in disjoint categories {cats}")
        if conflicts == 0:
            ok(f"no disjoint top-category conflicts ({len(TOP_CATEGORIES)} categories)")

        for src_cls, dst_cls in LEAK_GUARDS:
            SRC = rdflib.URIRef(NS + src_cls)
            DST = rdflib.URIRef(NS + dst_cls)
            leaked = sorted(
                str(s).replace(NS, ":")
                for s in set(reasoned.subjects(rdflib.RDF.type, SRC))
                if s != SRC and (s, rdflib.RDF.type, DST) in reasoned
            )
            if leaked:
                for name in leaked:
                    fail(f"domain 泄漏: {name} {LEAK_HINT}")
            else:
                ok(f"no {src_cls}->{dst_cls} domain leakage")
    except Exception as e:
        fail(f"reasoner crashed: {type(e).__name__}: {str(e).splitlines()[0]}")

    print("\n[4] SWRL structure")
    SWRL = rdflib.Namespace("http://www.w3.org/2003/11/swrl#")
    imps = list(rules.subjects(rdflib.RDF.type, SWRL.Imp))
    ok(f"{len(imps)} swrl:Imp rules loaded")
    bad_atoms = 0
    for imp in imps:
        for role in (SWRL.body, SWRL.head):
            node = rules.value(imp, role)
            if node is None:
                fail(f"{imp}: missing {role}")
                bad_atoms += 1
                continue
            for atom in rules.items(node):
                if not list(rules.objects(atom, SWRL.arguments)):
                    fail(f"{imp}: atom without swrl:arguments")
                    bad_atoms += 1
    if bad_atoms == 0:
        ok("every head/body atom carries swrl:arguments")

    # 建模约定: 派生类禁止 owl:equivalentClass (只用 rdfs:subClassOf)
    eq_classes = list(rules.triples((None, rdflib.OWL.equivalentClass, None)))
    if eq_classes:
        for cls, _, _obj in eq_classes:
            fail(
                f"{str(cls).replace(NS, ':')} uses owl:equivalentClass - "
                f"derived classes must use rdfs:subClassOf"
            )
    else:
        ok("no owl:equivalentClass on derived classes")

    # ─── Check 5: 运营模型 (model/*.yaml) → 本体覆盖 ──────────────────────
    # 前述 4 段只校验 TTL/SHACL/SWRL 自身，无法发现"YAML 有实体、本体没类"。
    print("\n[5] Operational model ↔ ontology coverage (model/*.yaml)")
    try:
        import yaml
    except ImportError:
        fail("PyYAML not installed; cannot validate model/*.yaml coverage")
    else:
        SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
        declared_classes = set(data.subjects(rdflib.RDF.type, rdflib.OWL.Class))
        shape_targets = {
            str(t)
            for s in data.subjects(rdflib.RDF.type, SH.NodeShape)
            for t in data.objects(s, SH.targetClass)
        }
        before = failures
        total = 0
        for rel in MODEL_FILES:
            path = ROOT / rel
            if not path.exists():
                fail(f"{rel}: file not found")
                continue
            try:
                model = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as e:
                fail(f"{rel}: {type(e).__name__}: {str(e).splitlines()[0]}")
                continue
            for name, entity in (model.get("entities") or {}).items():
                total += 1
                cls = entity.get("ontology_class") or name
                top = entity.get("top_category")
                uri = rdflib.URIRef(NS + cls)
                if uri not in declared_classes:
                    fail(f"{rel}:{name} -> :{cls} 未声明为 owl:Class (本体与运营模型不一致)")
                    continue
                if top and (uri, rdflib.RDFS.subClassOf, rdflib.URIRef(NS + top)) not in data:
                    fail(f"{rel}:{name} -> :{cls} 未声明 rdfs:subClassOf :{top}")
                if cls not in SHAPE_EXEMPT and str(uri) not in shape_targets:
                    fail(f"{rel}:{name} -> :{cls} 缺少 SHACL NodeShape (或显式加入 SHAPE_EXEMPT)")
        if failures == before:
            ok(f"所有 {total} 个 YAML 实体的本体类 / 顶层范畴 / 形状标注一致 ({len(SHAPE_EXEMPT)} 项显式豁免)")

print("\n" + "━" * 40)
if failures:
    print(f"\n\N{CROSS MARK} Consistency validation FAILED ({failures} issue(s)).\n")
    sys.exit(1)
print("\n\N{WHITE HEAVY CHECK MARK} All consistency checks passed.\n")
