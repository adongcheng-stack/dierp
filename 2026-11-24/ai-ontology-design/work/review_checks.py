"""评审用一次性核查脚本（不进入交付物）。"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "ontology" / "model"

tables = collections.Counter()
classes = collections.Counter()
entity_count = 0
for path in sorted(MODEL.glob("*.yaml")):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for name, spec in (data.get("entities") or {}).items():
        entity_count += 1
        tables[spec.get("table")] += 1
        classes[spec.get("ontology_class")] += 1

print("yaml files:", [p.name for p in sorted(MODEL.glob("*.yaml"))])
print("entity_count:", entity_count)
print("duplicate tables:", {k: v for k, v in tables.items() if v > 1})
print("duplicate ontology_class:", {k: v for k, v in classes.items() if v > 1})

mappings = json.loads((ROOT / "ontology" / "src" / "mappings.json").read_text(encoding="utf-8"))
print("enums:", len(mappings["enumerations"]))
print("AccessDomain:", mappings["enumerations"]["AccessDomain"])
