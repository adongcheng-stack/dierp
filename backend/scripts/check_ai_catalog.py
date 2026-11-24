"""AI 语义目录门禁（设计 §11.1 的 7 类校验）。

在干净仓库退出 0；任一契约被破坏时打印可定位的失败项并退出非 0。
只读：不创建数据库连接，只消费 ``Base.metadata`` 与本体/投影源文件。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rdflib import URIRef  # noqa: E402
from rdflib.namespace import RDF  # noqa: E402

from backend.common.database.base import Base  # noqa: E402
from backend.common.utils.security_policy import (  # noqa: E402
    READ_OPEN_DOMAINS,
    READ_ROLE_POLICY,
    ROLES,
)
from backend.services.ai.catalog import (  # noqa: E402
    EXPECTED_DB_TABLES,
    EXPECTED_NOT_EXPOSED,
    EXPECTED_ONTOLOGY_ENTITIES,
    EXPECTED_PROJECTION_ENTITIES,
    camel_to_snake,
    reload_catalog,
)
from backend.services.ai import intents as _ai_intents  # noqa: E402,F401  触发意图注册
from backend.services.ai.intent import INTENTS, BoundIntent  # noqa: E402
from backend.services.ai.intents import EXPECTED_INTENTS  # noqa: E402
from backend.services.ai.ontology_service import NS, SH, get_ontology_service  # noqa: E402

FRONTEND_INTENTS = ROOT / "frontend" / "src" / "mock" / "ai-intents.json"

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print(f"FAIL {message}")


# ── 1. 目录构建与计数 ─────────────────────────────────────
def check_catalog(catalog: Any) -> None:
    summary = catalog.summary()
    coverage = summary["coverage"]
    expected = {
        "ontology": EXPECTED_ONTOLOGY_ENTITIES,
        "projection": EXPECTED_PROJECTION_ENTITIES,
        "not_exposed": EXPECTED_NOT_EXPOSED,
    }
    for key, wanted in expected.items():
        if coverage[key] != wanted:
            fail(f"目录计数漂移: {key}={coverage[key]}，期望 {wanted}")
    if summary["db_tables"] != EXPECTED_DB_TABLES:
        fail(f"Base.metadata 表数={summary['db_tables']}，期望 {EXPECTED_DB_TABLES}")
    total = len(catalog.entities)
    if total != EXPECTED_ONTOLOGY_ENTITIES + EXPECTED_PROJECTION_ENTITIES:
        fail(f"目录实体数={total}，期望 63")
    if "BOM" in catalog.entities or any(e.table == "boms" for e in catalog.entities.values()):
        fail("BOM 不得进入 AI 目录（无 YAML、无投影）")


# ── 2. 表/字段存在且类型可映射 ────────────────────────────
def check_fields(catalog: Any) -> None:
    tables = Base.metadata.tables
    for entity in catalog.entities.values():
        table = tables.get(entity.table)
        if table is None:
            fail(f"{entity.name}: 表 {entity.table} 不在 Base.metadata 中")
            continue
        columns = set(table.columns.keys())
        for field in entity.fields.values():
            if field.name not in columns:
                fail(f"{entity.name}.{field.name}: 列不在表 {entity.table} 中")
            if field.data_type not in {"string", "int", "decimal", "bool", "datetime", "enum"}:
                fail(f"{entity.name}.{field.name}: 类型 {field.data_type} 不可映射")


# ── 3. domain 合法 ────────────────────────────────────────
def check_domains(catalog: Any) -> None:
    allowed = set(READ_OPEN_DOMAINS) | set(READ_ROLE_POLICY)
    for entity in catalog.entities.values():
        if not entity.domain:
            fail(f"{entity.name}: domain 为空")
        elif entity.domain not in allowed:
            fail(f"{entity.name}: domain={entity.domain} 未在 READ_OPEN_DOMAINS/READ_ROLE_POLICY 中声明")
    for name, domain in (
        ("SalesInvoice", "finance"),
        ("ReceivableEntry", "finance"),
    ):
        entity = catalog.entities.get(name)
        if entity is not None and entity.domain != domain:
            fail(f"{name}: domain={entity.domain}，期望 {domain}")


# ── 4. 形状存在、targetClass 一致、路径 0 遗漏 ────────────
def check_shapes(catalog: Any) -> None:
    service = get_ontology_service()
    if service.shapes is None:
        service.load()
    shapes_graph = service.shapes
    assert shapes_graph is not None
    for entity in catalog.entities.values():
        if entity.shape_iri is None:
            continue
        targets = set(shapes_graph.objects(URIRef(entity.shape_iri), URIRef(SH + "targetClass")))
        if URIRef(entity.ontology_iri) not in targets:
            fail(f"{entity.name}: 形状 {entity.shape_iri} 的 sh:targetClass 与 ontology_iri 不一致")
        if not entity.shape_paths:
            fail(f"{entity.name}: 声明了形状但未解析到任何 sh:path")
        mapped = {NS + field.rdf_name for field in entity.fields.values()}
        missing = entity.shape_paths - mapped
        if missing:
            fail(
                f"{entity.name}: 形状路径未命中 "
                + ", ".join(sorted(str(p).replace(NS, "") for p in missing))
            )


# ── 5. 投影与 entity_overrides 有效 ──────────────────────
def check_projection(catalog: Any) -> None:
    projections = [e for e in catalog.entities.values() if e.coverage == "projection"]
    if len(projections) != EXPECTED_PROJECTION_ENTITIES:
        fail(f"投影实体数={len(projections)}，期望 {EXPECTED_PROJECTION_ENTITIES}")
    names = [e.name for e in projections]
    if len(set(names)) != len(names):
        fail(f"投影实体名重复: {names}")
    tables = [e.table for e in projections]
    if len(set(tables)) != len(tables):
        fail(f"投影表重复: {tables}")
    allowed = set(READ_OPEN_DOMAINS) | set(READ_ROLE_POLICY)
    for entity in projections:
        if entity.domain not in allowed:
            fail(f"投影 {entity.name}: domain={entity.domain} 未声明")
        if entity.shape_iri is not None and not entity.shape_paths:
            fail(f"投影 {entity.name}: 声明了形状但未解析到 sh:path")
    sales_orders = catalog.entities.get("SalesOrder")
    if sales_orders is None:
        fail("投影 SalesOrder 缺失")
    else:
        expected_paths = {"order_number": "documentNumber", "delivery_date": "dueDate"}
        for column, rdf_name in expected_paths.items():
            field = sales_orders.fields.get(column)
            if field is None:
                fail(f"SalesOrder: 缺少投影字段 {column}")
            elif field.rdf_name != rdf_name:
                fail(f"SalesOrder.{column}: rdf_name={field.rdf_name}，期望 {rdf_name}")


# ── 6. 意图注册表 ────────────────────────────────────────
def _match_field(primary: Any, param_name: str) -> Any:
    by_column = primary.fields.get(param_name)
    if by_column is not None:
        return by_column
    snake = camel_to_snake(param_name)
    if snake in primary.fields:
        return primary.fields[snake]
    for field in primary.fields.values():
        if field.rdf_name == param_name:
            return field
    return None


def check_intents(catalog: Any) -> None:
    if len(INTENTS) != EXPECTED_INTENTS:
        fail(f"意图数={len(INTENTS)}，期望 {EXPECTED_INTENTS}")

    allowed_domains = set(READ_OPEN_DOMAINS) | set(READ_ROLE_POLICY)
    for code, spec in INTENTS.items():
        if spec.code != code:
            fail(f"意图 {code}: code 字段={spec.code} 与注册键不一致")
        if not spec.allowed_roles:
            fail(f"意图 {code}: allowed_roles 为空")
        unknown_roles = set(spec.allowed_roles) - set(ROLES)
        if unknown_roles:
            fail(f"意图 {code}: allowed_roles 含未声明角色 {sorted(unknown_roles)}")
        if not spec.domains:
            fail(f"意图 {code}: domains 为空")
        for domain in spec.domains:
            if domain not in allowed_domains:
                fail(f"意图 {code}: domain={domain} 未在策略中声明")
        if not callable(spec.handler):
            fail(f"意图 {code}: handler 不可调用")
        # 必填参数模型无法用默认值实例化，只能做结构断言（评审发现的 P0 门禁缺陷）
        if not (isinstance(spec.params_model, type) and issubclass(spec.params_model, BoundIntent)):
            fail(f"意图 {code}: 参数模型必须继承 BoundIntent")
        elif spec.params_model.model_config.get("extra") != "forbid":
            fail(f"意图 {code}: 参数模型未设置 extra='forbid'")

        for name in spec.entities:
            if name not in catalog.entities:
                fail(f"意图 {code}: 实体 {name} 不在目录中")
        primary = catalog.entities.get(spec.primary_entity)
        if primary is None:
            fail(f"意图 {code}: primary_entity={spec.primary_entity} 不在目录中")
            continue

        table = Base.metadata.tables.get(primary.table)
        columns = set(table.columns.keys()) if table is not None else set()
        for key in spec.record_key:
            if key not in columns:
                fail(f"意图 {code}: record_key={key} 不是 {primary.table} 的真实列")

        covered = 0
        mapped_params = 0
        for param_name in spec.params_model.model_fields:
            field = _match_field(primary, param_name)
            if field is None:
                continue
            mapped_params += 1
            if NS + field.rdf_name in primary.shape_paths:
                covered += 1
        if not primary.shape_paths or mapped_params == 0:
            expected_coverage = "none"
        elif covered == mapped_params:
            expected_coverage = "full"
        elif covered:
            expected_coverage = "partial"
        else:
            expected_coverage = "none"
        if spec.shacl_coverage != expected_coverage:
            fail(
                f"意图 {code}: shacl_coverage={spec.shacl_coverage}，"
                f"按 shape_paths 计算应为 {expected_coverage}"
                f"（覆盖 {covered}/{mapped_params} 参数）"
            )

    if FRONTEND_INTENTS.is_file():
        document = json.loads(FRONTEND_INTENTS.read_text(encoding="utf-8"))
        items = document.get("intents") if isinstance(document, dict) else document
        exported = {item.get("code"): item for item in items or []}
        if set(exported) != set(INTENTS):
            fail(f"ai-intents.json 的 code 集合与注册表不一致: {sorted(set(exported) ^ set(INTENTS))}")
        for code, spec in INTENTS.items():
            item = exported.get(code) or {}
            expected = {
                "label": spec.label,
                "entities": list(spec.entities),
                "primary_entity": spec.primary_entity,
                "record_key": list(spec.record_key),
                "downlink": spec.downlink,
                "roles": sorted(spec.allowed_roles),
                "domains": list(spec.domains),
            }
            for key, value in expected.items():
                if item.get(key) != value:
                    fail(f"ai-intents.json[{code}].{key}={item.get(key)!r}，期望 {value!r}")
    elif INTENTS:
        fail("frontend/src/mock/ai-intents.json 缺失（注册表非空时必须提交导出物）")


# ── 7. 覆盖率与未暴露清单 ────────────────────────────────
def print_coverage(catalog: Any) -> None:
    summary = catalog.summary()
    coverage = summary["coverage"]
    print(f"覆盖率 {{ontology: {coverage['ontology']}, projection: {coverage['projection']}, "
          f"not_exposed: {coverage['not_exposed']}}}")
    print(f"db_tables: {summary['db_tables']}；目录实体: {summary['total']}")
    print("未暴露·有类无字段: " + ", ".join(summary["not_exposed_tables"]["has_class_no_fields"]))
    print("未暴露·无类: " + ", ".join(summary["not_exposed_tables"]["no_class"]))


def main() -> int:
    try:
        catalog = reload_catalog()
    except Exception as exc:  # noqa: BLE001 - 构建失败即门禁失败
        print(f"FAIL 目录构建失败: {type(exc).__name__}: {exc}")
        return 1

    check_catalog(catalog)
    check_fields(catalog)
    check_domains(catalog)
    check_shapes(catalog)
    check_projection(catalog)
    check_intents(catalog)
    print_coverage(catalog)

    if failures:
        print(f"\nAI 语义目录门禁失败 {len(failures)} 项")
        return 1
    print("\nAI 语义目录门禁通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
