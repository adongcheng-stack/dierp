"""Generate SQLAlchemy models and TypeScript contracts from the ERP operational model.

Source of truth:
  - ontology/model/planning.yaml   (entities, fields, relations)
  - ontology/src/mappings.json     (enumerations)

Generated:
  - backend/common/models/planning.py
  - frontend/src/types/planning.generated.ts

Run from repository root:
  python backend/ontology/generate_models.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = ROOT / "ontology"
MAPPINGS_FILE = ONTOLOGY_DIR / "src" / "mappings.json"

# 每份运营模型 → 独立生成物。新增领域只需在此追加一条配置。
MODEL_CONFIGS: list[tuple[str, str, str]] = [
    (
        "model/planning.yaml",
        "backend/common/models/planning.py",
        "frontend/src/types/planning.generated.ts",
    ),
    (
        "model/admin.yaml",
        "backend/common/models/admin.py",
        "frontend/src/types/admin.generated.ts",
    ),
    (
        "model/dashboard.yaml",
        "backend/common/models/dashboard.py",
        "frontend/src/types/dashboard.generated.ts",
    ),
]

PY_TYPE_IMPORTS = {
    "string": "String",
    "text": "Text",
    "integer": "Integer",
    "decimal": "Numeric",
    "boolean": "Boolean",
    "datetime": "DateTime",
    "date": "Date",
}


def py_default(field: dict[str, Any]) -> str | None:
    if "default" not in field:
        return None
    value = field["default"]
    ftype = field["type"]
    if ftype == "enum":
        return f"{field['enum']}.{value}"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(value, ensure_ascii=False)


def render_py_column(name: str, field: dict[str, Any]) -> str:
    ftype = field["type"]
    args: list[str] = []

    if ftype == "string":
        args.append(f"String({field.get('length', 50)})")
    elif ftype == "text":
        args.append("Text")
    elif ftype == "integer":
        args.append("Integer")
    elif ftype == "decimal":
        args.append(f"Numeric({field.get('precision', 15)}, {field.get('scale', 4)})")
    elif ftype == "boolean":
        args.append("Boolean")
    elif ftype == "datetime":
        args.append("DateTime")
    elif ftype == "date":
        args.append("Date")
    elif ftype == "enum":
        args.append(f"SQLEnum({field['enum']})")
    else:
        raise ValueError(f"Unsupported field type {ftype!r} for {name}")

    if field.get("fk"):
        args.append(f'ForeignKey("{field["fk"]}")')
    if field.get("required"):
        args.append("nullable=False")
    if field.get("unique"):
        args.append("unique=True")
    if field.get("index"):
        args.append("index=True")
    default = py_default(field)
    if default is not None:
        args.append(f"default={default}")
    if field.get("comment"):
        args.append(f"comment={json.dumps(field['comment'], ensure_ascii=False)}")

    return f"    {name} = Column({', '.join(args)})"


def render_models(model: dict[str, Any], mappings: dict[str, Any]) -> str:
    entities: dict[str, Any] = model["entities"]

    used_types = set()
    used_enums = set()
    for entity in entities.values():
        for field in entity.get("fields", {}).values():
            used_types.add(field["type"])
            if field["type"] == "enum":
                used_enums.add(field["enum"])

    imported = sorted(PY_TYPE_IMPORTS[t] for t in used_types if t in PY_TYPE_IMPORTS)
    imports = [
        f"from sqlalchemy import Column, ForeignKey, {', '.join(imported)}",
        "from sqlalchemy import Enum as SQLEnum",
        "from enum import Enum",
        "from backend.common.models.base import BaseModel",
    ]

    lines: list[str] = [
        '"""',
        "GENERATED FILE - DO NOT EDIT BY HAND.",
        f"Source: {model.get('_source', 'ontology/model/planning.yaml')} (version {model.get('version', '1.0.0')})",
        f"Ontology: {model.get('namespace', '')}",
        "Regenerate: python backend/ontology/generate_models.py",
        '"""',
        "",
        *imports,
        "",
        "",
        "# " + "=" * 70,
        "# 枚举（来自 ontology/src/mappings.json，唯一事实源）",
        "# " + "=" * 70,
    ]

    for enum_name, values in mappings["enumerations"].items():
        if enum_name not in used_enums:
            continue
        lines.append("")
        lines.append(f"class {enum_name}(str, Enum):")
        lines.append(f'    """{enum_name}"""')
        for value in values:
            lines.append(f'    {value} = "{value}"')

    for entity_name, entity in entities.items():
        lines.append("")
        lines.append("")
        lines.append(f"class {entity_name}(BaseModel):")
        lines.append(f'    """{entity.get("label", entity_name)}"""')
        lines.append(f'    __tablename__ = "{entity["table"]}"')
        lines.append("")
        for field_name, field in entity.get("fields", {}).items():
            lines.append(render_py_column(field_name, field))
            lines.append("")

    lines.append("")
    return "\n".join(lines)


def ts_type(field: dict[str, Any]) -> str:
    ftype = field["type"]
    if ftype in ("integer", "decimal"):
        return "number"
    if ftype == "boolean":
        return "boolean"
    if ftype == "enum":
        return field["enum"]
    return "string"


def render_ts(model: dict[str, Any], mappings: dict[str, Any]) -> str:
    entities: dict[str, Any] = model["entities"]
    lines: list[str] = [
        "/**",
        " * GENERATED FILE - DO NOT EDIT BY HAND.",
        f" * Source: {model.get('_source', 'ontology/model/planning.yaml')} (version {model.get('version', '1.0.0')})",
        " * Regenerate: python backend/ontology/generate_models.py",
        " */",
        "",
        "/* eslint-disable */",
        "",
    ]
    # Enum types are imported from the ontology enum mirror.
    lines.append("import type {")
    for enum_name in mappings["enumerations"]:
        lines.append(f"  {enum_name},")
    lines.append("} from '../../../ontology/generated/types'")
    lines.append("")
    lines.append("export type {")
    for enum_name in mappings["enumerations"]:
        lines.append(f"  {enum_name},")
    lines.append("}")
    lines.append("")

    for entity_name, entity in entities.items():
        lines.append(f"/** {entity.get('label', entity_name)} */")
        lines.append(f"export interface {entity_name} {{")
        emitted: set[str] = set()
        for field_name, field in entity.get("fields", {}).items():
            if field_name in emitted:
                continue  # base fields (id/created_at/updated_at) are appended below
            emitted.add(field_name)
            optional = "" if field.get("required") else "?"
            lines.append(f"  {field_name}{optional}: {ts_type(field)}")
        if "id" not in emitted:
            lines.append("  id?: number")
        if "created_at" not in emitted:
            lines.append("  created_at?: string")
        if "updated_at" not in emitted:
            lines.append("  updated_at?: string")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="从运营模型生成后端模型与前端契约")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只比对生成物与当前文件，不写入；发现漂移返回 1（供 CI 门禁使用）",
    )
    args = parser.parse_args()

    mappings = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
    drifted: list[str] = []
    for model_rel, backend_rel, frontend_rel in MODEL_CONFIGS:
        model = yaml.safe_load((ONTOLOGY_DIR / model_rel).read_text(encoding="utf-8"))
        model["_source"] = f"ontology/{model_rel}"
        backend_out = ROOT / backend_rel
        frontend_out = ROOT / frontend_rel

        py = render_models(model, mappings)
        ts = render_ts(model, mappings)

        if args.check:
            for rel, expected in ((backend_rel, py), (frontend_rel, ts)):
                out = ROOT / rel
                actual = out.read_text(encoding="utf-8") if out.exists() else None
                if actual != expected:
                    drifted.append(rel)
                    print(f"DRIFT {rel}: regenerate with `python backend/ontology/generate_models.py`")
        else:
            backend_out.parent.mkdir(parents=True, exist_ok=True)
            backend_out.write_text(py, encoding="utf-8")
            frontend_out.parent.mkdir(parents=True, exist_ok=True)
            frontend_out.write_text(ts, encoding="utf-8")
            print(f"generated {backend_rel} ({len(model['entities'])} entities)")
            print(f"generated {frontend_rel}")

    if args.check:
        if drifted:
            print(f"generated-file drift detected in {len(drifted)} file(s)")
            return 1
        print(f"all generated files in sync ({len(MODEL_CONFIGS)} models)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
