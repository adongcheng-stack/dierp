"""语义目录（AI 可访问实体的只读契约）。

输入：
- ``ontology/model/{planning,admin,dashboard}.yaml``：59 个 YAML 托管实体；
- ``ontology/model/ai-projection.yaml``：4 个遗留表投影 + YAML 实体的形状路径覆盖；
- ``ontology/src/*.ttl``：类 / 形状 / 枚举（通过 ontology_service 复用加载结果）。

输出：``EntityMeta``/``FieldMeta`` 只读目录。构建期硬校验（设计 §5.2/§5.3）：
表存在、字段存在、类存在、形状存在、域合法、形状路径未命中数 = 0。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from rdflib import URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

# 导入即填充 Base.metadata（与 migrations/env.py、tests/conftest.py 的导入列表一致）
from backend.common.database.base import Base
from backend.common.models import (  # noqa: F401
    admin as _admin_models,
    ai as _ai_models,
    audit as _audit_models,
    dashboard as _dashboard_models,
    eng as _eng_models,
    mm as _mm_models,
    planning as _planning_models,
    pp as _pp_models,
    sd as _sd_models,
    user as _user_models,
)
from backend.common.utils.security_policy import READ_OPEN_DOMAINS, READ_ROLE_POLICY
from backend.ontology.registry import ROOT
from backend.services.ai.intent import EntityMeta, FieldMeta
from backend.services.ai.ontology_service import NS, SH, get_ontology_service

MODEL_DIR = ROOT / "ontology" / "model"
MODEL_FILES = ("planning.yaml", "admin.yaml", "dashboard.yaml")
PROJECTION_FILE = MODEL_DIR / "ai-projection.yaml"
DOMAIN_BY_FILE = {"planning.yaml": "planning", "admin.yaml": "admin", "dashboard.yaml": "dashboard"}

# 设计 §1.2：9 张"只声明了类、无字段元数据"的表；其中 4 张已进入投影
CLASS_ONLY_TABLES = frozenset({
    "materials", "work_centers", "sales_orders", "production_orders",
    "boms", "bom_items", "routings", "routing_operations", "customers",
})
EXPECTED_DB_TABLES = 88
EXPECTED_ONTOLOGY_ENTITIES = 59
EXPECTED_PROJECTION_ENTITIES = 4
EXPECTED_NOT_EXPOSED = 25

# 非业务表不参与 AI 目录计数：AI 审计表由 W0.6 新增；workflow_* 为遗留手写表。
# 排除后与设计 §1.2 的 88 张业务表 / 25 张未暴露表口径一致，且不随导入顺序漂移。
NON_CATALOG_TABLES = frozenset({
    "ai_query_logs",
    "workflow_nodes",
    "workflows",
    "workflow_instances",
    "workflow_instance_nodes",
})

_TYPE_MAP = {
    "string": "string", "text": "string", "enum": "enum",
    "integer": "int", "int": "int", "bigint": "int",
    "decimal": "decimal", "float": "decimal", "number": "decimal", "numeric": "decimal",
    "boolean": "bool", "bool": "bool",
    "datetime": "datetime", "date": "datetime", "timestamp": "datetime",
}


class CatalogError(RuntimeError):
    """目录契约被破坏时抛出；消息包含源文件与行号。"""


@dataclass(frozen=True)
class _ShapeProp:
    rdf_name: str
    required: bool
    enum: tuple[str, ...] | None
    pattern: str | None
    datatype: str | None
    minimum: float | None = None
    maximum: float | None = None


def camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def snake_to_camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def _line_of(path: Path, needle: str) -> str:
    try:
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if re.search(rf"^\s*{re.escape(needle)}\s*:", line):
                return f"{path.name}:{index}"
    except OSError:
        pass
    return path.name


def _normalize_type(value: str | None) -> str:
    return _TYPE_MAP.get((value or "string").lower(), "string")


def _orm_type(column: Any) -> str:
    return _TYPE_MAP.get(type(column.type).__name__.lower(), "string")


class Catalog:
    """一次构建、按源文件指纹缓存；``build()`` 可重复调用做缓存断言。"""

    def __init__(self) -> None:
        self.entities: dict[str, EntityMeta] = {}
        self.warnings: list[str] = []
        self.not_exposed: dict[str, list[str]] = {"has_class_no_fields": [], "no_class": []}
        self.build_count = 0
        self._fingerprint: tuple[tuple[str, int, int], ...] | None = None

    # ── 构建 ──────────────────────────────────────────────
    def _sources(self) -> list[Path]:
        return [MODEL_DIR / name for name in MODEL_FILES] + [PROJECTION_FILE]

    def _current_fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        stat = []
        for path in self._sources():
            info = path.stat()
            stat.append((str(path), info.st_mtime_ns, info.st_size))
        return tuple(stat)

    def build(self) -> "Catalog":
        fingerprint = self._current_fingerprint()
        if self._fingerprint == fingerprint and self.entities:
            return self

        missing = [str(p) for p in self._sources() if not p.is_file()]
        if missing:
            raise CatalogError("语义源文件缺失: " + ", ".join(missing))

        service = get_ontology_service()
        if service.semantic is None:
            service.load()
        assert service.semantic is not None and service.shapes is not None

        all_tables = set(Base.metadata.tables)
        metadata_tables = all_tables - NON_CATALOG_TABLES
        shapes = self._shape_index(service)
        projection = yaml.safe_load(PROJECTION_FILE.read_text(encoding="utf-8")) or {}
        overrides, domain_overrides = self._load_entity_overrides(projection.get("entity_overrides") or [])

        entities: dict[str, EntityMeta] = {}
        misses: list[str] = []

        # 1) YAML 托管实体
        for filename in MODEL_FILES:
            path = MODEL_DIR / filename
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for key, cfg in (document.get("entities") or {}).items():
                name = cfg.get("ontology_class") or key
                self._check_class(name, service, path)
                shape = shapes.get(name)
                if shape is None:
                    # 4 个行项目实体（MrpRequirement 等）没有 NodeShape：
                    # 目录仍可用，但 shacl_coverage 只能是 none（如实暴露能力边界）。
                    shape = (None, [], False)
                shape_iri, props, has_sparql = shape
                table = cfg.get("table") or ""
                if table not in all_tables:
                    raise CatalogError(f"{_line_of(path, key)}: 表 {table} 不在 Base.metadata 中")
                entity_overrides = overrides.pop(name, {})
                entity = self._build_yaml_entity(
                    name=name, cfg=cfg, table=table, path=path,
                    props=props, shape_iri=shape_iri, has_sparql=has_sparql,
                    domain=domain_overrides.get(name, DOMAIN_BY_FILE[filename]),
                    domain_source="yaml" if name in domain_overrides else "yaml_file",
                    overrides=entity_overrides, service=service, misses=misses,
                )
                self._add(entities, entity, path)

        # 2) 遗留表投影
        for item in projection.get("entities") or []:
            name = item["ontology_class"]
            self._check_class(name, service, PROJECTION_FILE)
            table = item["table"]
            if table not in all_tables:
                raise CatalogError(f"{_line_of(PROJECTION_FILE, name)}: 表 {table} 不在 Base.metadata 中")
            shape_name = item.get("shape")
            if shape_name:
                if shape_name not in {str(s).split("#")[-1] for s in service.shapes.subjects(RDF.type, URIRef(SH + "NodeShape"))}:
                    raise CatalogError(f"{_line_of(PROJECTION_FILE, name)}: 形状 {shape_name} 不存在")
            shape = shapes.get(name)
            entity = self._build_projection_entity(
                item=item, service=service, metadata_table=Base.metadata.tables[table],
                shape=shape, overrides=item.get("rdf_overrides") or {}, misses=misses,
            )
            self._add(entities, entity, PROJECTION_FILE)

        if misses:
            raise CatalogError("形状路径未命中（必须为 0）: " + "; ".join(sorted(misses)))

        leftovers = {name: value for name, value in overrides.items() if value}
        if leftovers:
            raise CatalogError(f"entity_overrides 指向不存在的实体: {sorted(leftovers)}")
        for name in domain_overrides:
            if name not in entities:
                raise CatalogError(f"entity_overrides 的域例外指向不存在的实体: {name}")
            if entities[name].coverage != "ontology":
                raise CatalogError(f"域例外只能用于 YAML 托管实体: {name}")

        # 3) 域与计数
        allowed_domains = set(READ_OPEN_DOMAINS) | set(READ_ROLE_POLICY)
        for entity in entities.values():
            if not entity.domain:
                raise CatalogError(f"实体 {entity.name} 的 domain 为空")
            if entity.domain not in allowed_domains:
                raise CatalogError(f"实体 {entity.name} 的 domain={entity.domain} 未在生成物中声明")

        if "BOM" in entities or any(entity.table == "boms" for entity in entities.values()):
            raise CatalogError("BOM 不得进入 AI 目录（无 YAML、无投影）")

        exposed_tables = {entity.table for entity in entities.values()}
        unexposed = sorted(metadata_tables - exposed_tables)
        self.not_exposed = {
            "has_class_no_fields": [t for t in unexposed if t in CLASS_ONLY_TABLES],
            "no_class": [t for t in unexposed if t not in CLASS_ONLY_TABLES],
        }

        ontology_count = sum(1 for entity in entities.values() if entity.coverage == "ontology")
        projection_count = sum(1 for entity in entities.values() if entity.coverage == "projection")
        expected = {
            "db_tables": (len(metadata_tables), EXPECTED_DB_TABLES),
            "ontology": (ontology_count, EXPECTED_ONTOLOGY_ENTITIES),
            "projection": (projection_count, EXPECTED_PROJECTION_ENTITIES),
            "not_exposed": (len(unexposed), EXPECTED_NOT_EXPOSED),
        }
        for label, (actual, wanted) in expected.items():
            if actual != wanted:
                raise CatalogError(f"目录计数漂移: {label}={actual}，期望 {wanted}")
        if len(self.not_exposed["has_class_no_fields"]) != 5:
            raise CatalogError("not_exposed.has_class_no_fields 期望 5 张表")

        self.entities = entities
        self._fingerprint = fingerprint
        self.build_count += 1
        return self

    # ── 构建辅助 ──────────────────────────────────────────
    @staticmethod
    def _shape_index(service: Any) -> dict[str, tuple[str, list[_ShapeProp], bool]]:
        result: dict[str, tuple[str, list[_ShapeProp], bool]] = {}
        shape_type = URIRef(SH + "NodeShape")
        for shape in service.shapes.subjects(RDF.type, shape_type):
            targets = list(service.shapes.objects(shape, URIRef(SH + "targetClass")))
            if not targets:
                continue
            props: list[_ShapeProp] = []
            has_sparql = bool(list(service.shapes.objects(shape, URIRef(SH + "sparql"))))
            for prop in service.shapes.objects(shape, URIRef(SH + "property")):
                if list(service.shapes.objects(prop, URIRef(SH + "sparql"))):
                    has_sparql = True
                path = service.shapes.value(prop, URIRef(SH + "path"))
                if path is None:
                    continue
                enum_node = service.shapes.value(prop, URIRef(SH + "in"))
                min_count = service.shapes.value(prop, URIRef(SH + "minCount"))
                pattern = service.shapes.value(prop, URIRef(SH + "pattern"))
                datatype = service.shapes.value(prop, URIRef(SH + "datatype"))
                minimum = service.shapes.value(prop, URIRef(SH + "minInclusive"))
                maximum = service.shapes.value(prop, URIRef(SH + "maxInclusive"))
                props.append(_ShapeProp(
                    rdf_name=str(path).split("#")[-1],
                    required=bool(min_count is not None and int(min_count) > 0),
                    enum=tuple(str(v) for v in Collection(service.shapes, enum_node))
                    if enum_node is not None else None,
                    pattern=str(pattern) if pattern is not None else None,
                    datatype=str(datatype).split("#")[-1] if datatype is not None else None,
                    minimum=float(minimum) if minimum is not None else None,
                    maximum=float(maximum) if maximum is not None else None,
                ))
            for target in targets:
                name = str(target).split("#")[-1]
                if name in result:
                    # 同一类可有多个形状（如 MpsEntry + MpsEntryMaterial），合并约束
                    first_iri, first_props, first_sparql = result[name]
                    known = {prop.rdf_name for prop in first_props}
                    merged = first_props + [prop for prop in props if prop.rdf_name not in known]
                    result[name] = (first_iri, merged, first_sparql or has_sparql)
                    continue
                result[name] = (str(shape), props, has_sparql)
        return result

    @staticmethod
    def _load_entity_overrides(items: list[dict]) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
        overrides: dict[str, dict[str, str]] = {}
        domains: dict[str, str] = {}
        for item in items:
            name = item.get("ontology_class")
            if not name:
                raise CatalogError("entity_overrides 缺少 ontology_class")
            overrides.setdefault(name, {}).update(item.get("rdf_overrides") or {})
            if item.get("domain"):
                domains[name] = item["domain"]
        return overrides, domains

    @staticmethod
    def _check_class(name: str, service: Any, path: Path) -> None:
        if (URIRef(NS + name), RDF.type, OWL.Class) not in service.semantic:
            raise CatalogError(f"{_line_of(path, name)}: 本体类 {name} 不存在")

    def _add(self, entities: dict[str, EntityMeta], entity: EntityMeta, path: Path) -> None:
        if entity.name in entities:
            raise CatalogError(f"{_line_of(path, entity.name)}: 实体重复 {entity.name}")
        entities[entity.name] = entity

    def _build_yaml_entity(
        self,
        *,
        name: str,
        cfg: dict,
        table: str,
        path: Path,
        props: list[_ShapeProp],
        shape_iri: str | None,
        has_sparql: bool,
        domain: str,
        domain_source: str,
        overrides: dict[str, str],
        service: Any,
        misses: list[str],
    ) -> EntityMeta:
        yaml_fields: dict[str, dict] = cfg.get("fields") or {}
        inverted = self._invert_overrides(name, overrides, yaml_fields, props, path)

        fields: dict[str, FieldMeta] = {}
        for prop in props:
            column = inverted.get(prop.rdf_name) or camel_to_snake(prop.rdf_name)
            if column not in yaml_fields:
                misses.append(f"{name}.{prop.rdf_name} (列 {column})")
                continue
            spec = yaml_fields[column]
            if column in fields:
                raise CatalogError(
                    f"{_line_of(path, name)}: 形状路径 {prop.rdf_name} 与 "
                    f"{fields[column].rdf_name} 映射到同一列 {column}"
                )
            data_type = "enum" if prop.enum else _normalize_type(spec.get("type"))
            enum = prop.enum or self._yaml_enum(spec, service)
            fields[column] = FieldMeta(
                name=column,
                rdf_name=prop.rdf_name,
                label=spec.get("label") or "",
                data_type=data_type,
                required=prop.required or bool(spec.get("required")),
                enum=enum,
                pattern=prop.pattern or spec.get("pattern"),
                fk=spec.get("fk"),
                minimum=prop.minimum,
                maximum=prop.maximum,
                source="shacl",
            )

        for column, spec in yaml_fields.items():
            if column in fields:
                continue
            fields[column] = FieldMeta(
                name=column,
                rdf_name=snake_to_camel(column),
                label=spec.get("label") or "",
                data_type=_normalize_type(spec.get("type")),
                required=bool(spec.get("required")),
                enum=self._yaml_enum(spec, service),
                pattern=spec.get("pattern"),
                fk=spec.get("fk"),
                source="yaml",
            )

        return EntityMeta(
            name=name,
            table=table,
            label=cfg.get("label") or name,
            top_category=cfg.get("top_category") or "",
            domain=domain,
            domain_source=domain_source,
            ontology_iri=NS + name,
            shape_iri=shape_iri,
            shape_paths=frozenset(NS + prop.rdf_name for prop in props),
            shape_has_sparql=has_sparql,
            coverage="ontology",
            fields=dict(sorted(fields.items())),
        )

    def _build_projection_entity(
        self,
        *,
        item: dict,
        service: Any,
        metadata_table: Any,
        shape: tuple[str, list[_ShapeProp], bool] | None,
        overrides: dict[str, str],
        misses: list[str],
    ) -> EntityMeta:
        name = item["ontology_class"]
        whitelist: list[str] = list(item.get("fields") or [])
        columns = {column.name: column for column in metadata_table.columns}
        inverted = self._invert_overrides(name, overrides, {c: {} for c in whitelist},
                                          shape[1] if shape else [], PROJECTION_FILE)

        prop_by_column: dict[str, _ShapeProp] = {}
        if shape is not None:
            for prop in shape[1]:
                column = inverted.get(prop.rdf_name) or camel_to_snake(prop.rdf_name)
                if column not in whitelist:
                    misses.append(f"{name}.{prop.rdf_name} (投影未声明列 {column})")
                    continue
                if column in prop_by_column:
                    raise CatalogError(
                        f"{_line_of(PROJECTION_FILE, name)}: 形状路径 {prop.rdf_name} 与 "
                        f"{prop_by_column[column].rdf_name} 映射到同一列 {column}"
                    )
                prop_by_column[column] = prop

        fields: dict[str, FieldMeta] = {}
        for column_name in whitelist:
            column = columns.get(column_name)
            if column is None:
                raise CatalogError(
                    f"{_line_of(PROJECTION_FILE, name)}: 投影字段 {column_name} 不在表 {item['table']} 中"
                )
            prop = prop_by_column.get(column_name)
            fields[column_name] = FieldMeta(
                name=column_name,
                rdf_name=prop.rdf_name if prop else snake_to_camel(column_name),
                label="",
                data_type="enum" if (prop and prop.enum) else _orm_type(column),
                required=prop.required if prop else not column.nullable,
                enum=prop.enum if prop else None,
                pattern=prop.pattern if prop else None,
                minimum=prop.minimum if prop else None,
                maximum=prop.maximum if prop else None,
                indexed=bool(column.index),
                source="shacl" if prop else "projection",
            )

        shape_props = shape[1] if shape else []
        return EntityMeta(
            name=name,
            table=item["table"],
            label=item.get("label") or name,
            top_category=item.get("top_category") or self._top_category(name, service),
            domain=item["domain"],
            domain_source="projection",
            ontology_iri=NS + name,
            shape_iri=shape[0] if shape else None,
            shape_paths=frozenset(NS + prop.rdf_name for prop in shape_props),
            shape_has_sparql=shape[2] if shape else False,
            coverage="projection",
            fields=dict(sorted(fields.items())),
        )

    def _invert_overrides(
        self,
        name: str,
        overrides: dict[str, str],
        fields: dict[str, Any],
        props: list[_ShapeProp],
        path: Path,
    ) -> dict[str, str]:
        """形状路径覆盖：列名 → sh:path，反向成 sh:path → 列名并校验合法性。"""
        prop_names = {prop.rdf_name for prop in props}
        used: dict[str, str] = {}
        for column, rdf_name in overrides.items():
            if column not in fields:
                raise CatalogError(f"{_line_of(path, name)}: override 列 {column} 不在实体 {name} 中")
            if rdf_name not in prop_names:
                raise CatalogError(
                    f"{_line_of(path, name)}: override 路径 {rdf_name} 不在 {name} 的形状中"
                )
            if rdf_name in used:
                raise CatalogError(
                    f"{_line_of(path, name)}: 路径 {rdf_name} 被列 {used[rdf_name]} 与 {column} 重复占用"
                )
            used[rdf_name] = column
        return used

    @staticmethod
    def _yaml_enum(spec: dict, service: Any) -> tuple[str, ...] | None:
        enum_name = spec.get("enum")
        if not enum_name:
            return None
        values = service.mappings.get(enum_name)
        if not values:
            return None
        return tuple(str(value) for value in values)

    @staticmethod
    def _top_category(name: str, service: Any) -> str:
        current = URIRef(NS + name)
        seen: set[str] = set()
        while str(current) not in seen:
            seen.add(str(current))
            parents = list(service.semantic.objects(current, RDFS.subClassOf))
            if not parents:
                return str(current).split("#")[-1]
            current = parents[0]
        return name

    # ── 查询 ──────────────────────────────────────────────
    def get(self, name: str) -> EntityMeta:
        self.build()
        try:
            return self.entities[name]
        except KeyError:
            raise KeyError(f"未知实体: {name}") from None

    def summary(self) -> dict[str, Any]:
        self.build()
        ontology_count = sum(1 for e in self.entities.values() if e.coverage == "ontology")
        projection_count = sum(1 for e in self.entities.values() if e.coverage == "projection")
        total_unexposed = sum(len(v) for v in self.not_exposed.values())
        return {
            "total": len(self.entities),
            "coverage": {
                "ontology": ontology_count,
                "projection": projection_count,
                "not_exposed": total_unexposed,
            },
            "not_exposed": {key: len(value) for key, value in self.not_exposed.items()},
            "not_exposed_tables": self.not_exposed,
            "db_tables": len(set(Base.metadata.tables) - NON_CATALOG_TABLES),
            "warnings": list(self.warnings),
            "items": [
                {
                    "name": entity.name,
                    "table": entity.table,
                    "label": entity.label,
                    "top_category": entity.top_category,
                    "domain": entity.domain,
                    "shape": entity.shape_iri,
                    "coverage": entity.coverage,
                    "readonly": True,
                }
                for entity in sorted(self.entities.values(), key=lambda e: e.name)
            ],
        }


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return Catalog().build()


def reload_catalog() -> Catalog:
    """测试/门禁用：清空缓存并重建。"""
    get_catalog.cache_clear()
    return get_catalog()
