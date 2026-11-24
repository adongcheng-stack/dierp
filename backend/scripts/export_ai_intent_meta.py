"""导出意图元数据给前端 mock（设计 §10、计划 W1.1）。

用法：
  python backend/scripts/export_ai_intent_meta.py --write   # 生成/覆盖导出物
  python backend/scripts/export_ai_intent_meta.py --check   # 漂移校验（不一致退出 1）

导出物只含意图元数据（code/label/角色矩阵/参数摘要/record_key/downlink），不含业务数据。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.ai import intents as _intents  # noqa: E402,F401  触发注册
from backend.services.ai.intent import INTENTS  # noqa: E402

EXPORT_PATH = ROOT / "frontend" / "src" / "mock" / "ai-intents.json"


def _type_name(annotation: Any) -> str:
    name = getattr(annotation, "__name__", None)
    if name:
        return name
    text = str(annotation)
    return text.replace("typing.", "")


def build_document() -> dict[str, Any]:
    items = []
    for code, spec in INTENTS.items():
        params = []
        for name, field in spec.params_model.model_fields.items():
            params.append({
                "name": name,
                "type": _type_name(field.annotation),
                "required": field.is_required(),
                "default": None if field.is_required() else field.default,
            })
        items.append({
            "code": code,
            "label": spec.label,
            "description": spec.description,
            "entities": list(spec.entities),
            "primary_entity": spec.primary_entity,
            "record_key": list(spec.record_key),
            "downlink": spec.downlink,
            "roles": sorted(spec.allowed_roles),
            "domains": list(spec.domains),
            "shacl_coverage": spec.shacl_coverage,
            "params": params,
        })
    return {"version": 1, "intents": items}


def render() -> str:
    return json.dumps(build_document(), ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导出 AI 意图元数据")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="写入导出物")
    group.add_argument("--check", action="store_true", help="校验导出物是否漂移")
    args = parser.parse_args(argv)

    expected = render()
    if args.write:
        EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPORT_PATH.write_text(expected, encoding="utf-8")
        print(f"已写入 {EXPORT_PATH.relative_to(ROOT)}（{len(INTENTS)} 个意图）")
        return 0

    if not EXPORT_PATH.is_file():
        print(f"FAIL 导出物缺失: {EXPORT_PATH.relative_to(ROOT)}")
        return 1
    actual = EXPORT_PATH.read_text(encoding="utf-8")
    if actual != expected:
        print(f"FAIL 导出物漂移: {EXPORT_PATH.relative_to(ROOT)}（请运行 --write）")
        return 1
    print(f"意图元数据导出物一致（{len(INTENTS)} 个意图）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
