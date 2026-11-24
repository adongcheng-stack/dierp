"""检查抽象形状路径对应的 YAML 实体首列（用于评审证据）。"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
targets = {"Forecast", "MpsPlan", "MrpRun", "PlannedOrder", "PurchaseOrder", "ScheduleRun"}
for p in (ROOT / "ontology" / "model").glob("*.yaml"):
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    for name, spec in (data.get("entities") or {}).items():
        if spec.get("ontology_class") in targets:
            fields = list(spec["fields"])
            print(f"{spec['ontology_class']:14s} table={spec['table']:22s} first_fields={fields[:4]}")
