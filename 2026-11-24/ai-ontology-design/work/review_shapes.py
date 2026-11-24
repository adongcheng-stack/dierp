"""列出使用抽象路径 documentNumber/dueDate 的 NodeShape 及其 targetClass。"""
from __future__ import annotations

from pathlib import Path

import rdflib
import yaml
from rdflib import RDF, Namespace

ROOT = Path(__file__).resolve().parents[3]
NS = Namespace("https://dierp.local/ontology/erp/v1#")
SH = Namespace("http://www.w3.org/ns/shacl#")

g = rdflib.Graph()
g.parse(ROOT / "ontology" / "src" / "shapes.ttl", format="turtle")

# YAML 实体：类名 -> (table, fields)
yamls = {}
for p in (ROOT / "ontology" / "model").glob("*.yaml"):
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    for name, spec in (data.get("entities") or {}).items():
        yamls[spec["ontology_class"]] = (spec["table"], set(spec["fields"]))

rows = []
for shape in g.subjects(RDF.type, SH.NodeShape):
    targets = list(g.objects(shape, SH.targetClass))
    for t in targets:
        short = str(t).replace(str(NS), "")
        tbl = yamls.get(short)
        paths = set()
        for pnode in g.objects(shape, SH.property):
            path = g.value(pnode, SH.path)
            if path is None:
                continue
            paths.add(str(path).replace(str(NS), ""))
        abstract = paths & {"documentNumber", "dueDate", "documentDate"}
        if abstract:
            rows.append((short, tbl[0] if tbl else "(未在YAML)", sorted(abstract),
                         "document_number" in (tbl[1] if tbl else set())))

print(f"shapes with abstract paths: {len(rows)}")
for r in sorted(rows):
    print(r)

print("\nYAML 实体数:", len(yamls))
