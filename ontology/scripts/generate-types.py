"""Generate frontend enum types from mappings.json (single source of truth)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
mappings = json.loads((ROOT / "src" / "mappings.json").read_text(encoding="utf-8"))
lines = [
    "/**",
    " * GENERATED FILE - DO NOT EDIT BY HAND.",
    f" * Source: ontology/src/mappings.json (namespace {mappings['namespace']})",
    " * Regenerate: python ontology/scripts/generate-types.py",
    " */",
    "",
]
for name, values in mappings["enumerations"].items():
    union = " | ".join(f"'{v}'" for v in values)
    lines.append(f"export type {name} = {union};")
    lines.append("")

out = ROOT / "generated" / "types.ts"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print(f"written {out} ({len(mappings['enumerations'])} enums)")
