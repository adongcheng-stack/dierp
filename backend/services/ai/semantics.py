"""ERP ↔ MES 语义映射 v1（W2.3）：映射目录只读，锚点与枚举必须来自本体。

- 映射文件：``ontology/model/mes-mapping.yaml``（语义目录，不是生成源）；
- 每个映射项必须指向既有本体类与既有属性；
- 枚举值必须来自 ``mappings.json`` 的 ``enumerations``；
- 未覆盖的 MES 实体显式进入 ``unmapped``，不做猜测。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.ontology.registry import ROOT
from backend.services.ai.ontology_service import OntologyService, get_ontology_service

MES_MAPPING_YAML = ROOT / "ontology" / "model" / "mes-mapping.yaml"


class SemanticsSourceError(RuntimeError):
    """映射文件缺失或不可解析。"""


@lru_cache(maxsize=1)
def _load_mapping() -> dict[str, Any]:
    if not MES_MAPPING_YAML.is_file():
        raise SemanticsSourceError(f"映射文件缺失: {MES_MAPPING_YAML}")
    try:
        data = yaml.safe_load(MES_MAPPING_YAML.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 - 解析失败按源不可用处理
        raise SemanticsSourceError(f"映射文件解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise SemanticsSourceError("映射文件根节点必须是对象")
    return data


def invalidate_cache() -> None:
    _load_mapping.cache_clear()


def _resolve_entity(ontology: OntologyService, name: str) -> dict[str, Any] | None:
    try:
        return ontology.describe(name)
    except KeyError:
        return None


def build_mes_mapping(ontology: OntologyService | None = None) -> dict[str, Any]:
    data = _load_mapping()
    service = ontology or get_ontology_service()
    service.ensure_loaded()
    enumerations = service.mappings.get("enumerations", {})

    problems: list[str] = []
    items: list[dict[str, Any]] = []
    mapped_entities: set[str] = set()

    for entry in data.get("mappings") or []:
        entity = str(entry.get("mes_entity") or "").strip()
        class_name = str(entry.get("ontology_class") or "").strip()
        if not entity or not class_name:
            problems.append(f"映射项缺少 mes_entity/ontology_class: {entry!r}")
            continue
        mapped_entities.add(entity)

        described = _resolve_entity(service, class_name)
        if described is None:
            problems.append(f"{entity}: 本体类 {class_name} 不存在")
            continue
        properties = {prop["name"]: prop for prop in described["properties"]}

        fields: list[dict[str, Any]] = []
        for field in entry.get("fields") or []:
            mes_field = str(field.get("mes_field") or "")
            prop_name = str(field.get("ontology_property") or "")
            enum_name = field.get("enum")
            value_map = {str(k): str(v) for k, v in (field.get("value_map") or {}).items()}

            if not mes_field or not prop_name:
                problems.append(f"{entity}: 字段缺少 mes_field/ontology_property")
                continue
            if prop_name not in properties:
                problems.append(f"{entity}.{mes_field}: 本体属性 {class_name}.{prop_name} 不存在")

            if enum_name:
                codes = enumerations.get(str(enum_name))
                if not codes:
                    problems.append(f"{entity}.{mes_field}: 枚举 {enum_name} 不在 mappings.json")
                elif not value_map:
                    problems.append(f"{entity}.{mes_field}: 声明了枚举 {enum_name} 但缺少 value_map")
                else:
                    for mes_value, code in value_map.items():
                        if code not in codes:
                            problems.append(
                                f"{entity}.{mes_field}: {mes_value}->{code} 不是 {enum_name} 的合法码值"
                            )

            fields.append({
                "mes_field": mes_field,
                "ontology_property": prop_name,
                "enum": str(enum_name) if enum_name else None,
                "value_map": value_map,
            })

        items.append({
            "mes_entity": entity,
            "mes_table": entry.get("mes_table"),
            "ontology_class": class_name,
            "ontology_label": described.get("label"),
            "fields": fields,
        })

    catalog = [str(name) for name in (data.get("mes_catalog") or {}).get("entities", [])]
    unmapped = [name for name in catalog if name not in mapped_entities]
    coverage = round(len(mapped_entities & set(catalog)) / len(catalog), 4) if catalog else 0.0

    return {
        "version": data.get("version"),
        "source_system": data.get("source_system"),
        "namespace": data.get("namespace"),
        "items": items,
        "unmapped": unmapped,
        "coverage": coverage,
        "problems": problems,
    }
