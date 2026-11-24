"""Generate frontend enum types from mappings.json (single source of truth)."""
import argparse
import json
import sys
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

labels = mappings.get("labels", {})
if labels:
    lines.append("export const ENUM_LABELS = {")
    for name, mapping in labels.items():
        lines.append(f"  {name}: {{")
        for code, label in mapping.items():
            lines.append(f"    {code}: '{label}',")
        lines.append("  },")
    lines.append("} as const;")
    lines.append("")
out = ROOT / "generated" / "types.ts"
expected = "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="从 mappings.json 生成 TS 枚举类型")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只比对生成物与当前文件，不写入；发现漂移返回 1（供 CI 门禁使用）",
    )
    args = parser.parse_args()

    if args.check:
        actual = out.read_text(encoding="utf-8") if out.exists() else None
        if actual != expected:
            print(f"DRIFT {out}: regenerate with `python ontology/scripts/generate-types.py`")
            return 1
        print("generated types.ts in sync")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(expected, encoding="utf-8")
    print(f"written {out} ({len(mappings['enumerations'])} enums)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
