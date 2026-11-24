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
from rdflib.collection import Collection  # noqa: E402
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
from backend.services.ai.gates import shape_property_paths  # noqa: E402
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


# 跨库 MES 意图的角色契约：显式固定，防止默认放开或悄悄扩权
MES_ROLE_CONTRACT = frozenset({"ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION"})

# MES 形状最小契约：防止形状被删空或关键约束被悄悄移除
MES_SHAPE_CONTRACT: dict[str, tuple[str, frozenset[str]]] = {
    "MesWorkOrderShape": (
        "MesWorkOrder",
        frozenset({
            "mesWorkOrderNo", "mesOrderStatus", "mesOrderQuantity",
            "mesOrderCompletedQuantity", "mesOrderQualifiedQuantity",
            "mesOrderScrappedQuantity", "mesPlannedStart", "mesPlannedEnd",
        }),
    ),
    "MesProcessTaskShape": (
        "MesProcessTask",
        frozenset({
            "mesTaskId", "belongsToMesWorkOrder", "mesTaskSequence", "mesTaskStatus",
            "mesTaskCompletedQuantity", "mesTaskQualifiedQuantity", "mesTaskScrappedQuantity",
        }),
    ),
    "MesProcessReportShape": (
        "MesProcessReport",
        frozenset({
            "mesReportId", "reportsMesTask", "mesReportTime", "mesReportCompletedQuantity",
            "mesReportQualifiedQuantity", "mesReportScrappedQuantity",
        }),
    ),
}

# 形状枚举必须与 mappings.json 完全一致（生成物 types.ts 由双栈校验兜底）
MES_ENUM_CONTRACT: tuple[tuple[str, str, str], ...] = (
    ("MesWorkOrderShape", "mesOrderStatus", "MesWorkOrderStatus"),
    ("MesProcessTaskShape", "mesTaskStatus", "MesProcessTaskStatus"),
)


def _shape_in_values(
    shapes_graph: Any, shape_iri: URIRef, path: URIRef
) -> list[str] | None:
    for prop in shapes_graph.objects(shape_iri, URIRef(SH + "property")):
        if shapes_graph.value(prop, URIRef(SH + "path")) != path:
            continue
        list_node = shapes_graph.value(prop, URIRef(SH + "in"))
        if list_node is None:
            return None
        return [str(value) for value in Collection(shapes_graph, list_node)]
    return None


def check_mes_shapes() -> None:
    """MES 侧形状与 mappings.json 枚举一致性（形状唯一事实源在 ontology/src）。"""
    service = get_ontology_service()
    service.ensure_loaded()
    shapes_graph = service.shapes
    for shape_name, (target, required) in MES_SHAPE_CONTRACT.items():
        shape_iri = URIRef(NS + shape_name)
        if (shape_iri, RDF.type, URIRef(SH + "NodeShape")) not in shapes_graph:
            fail(f"MES 形状缺失: {shape_name}")
            continue
        targets = set(shapes_graph.objects(shape_iri, URIRef(SH + "targetClass")))
        if URIRef(NS + target) not in targets:
            fail(f"{shape_name}: sh:targetClass 不是 {target}")
        paths = shape_property_paths(shapes_graph, shape_iri)
        missing = {URIRef(NS + name) for name in required} - paths
        if missing:
            fail(
                f"{shape_name}: 缺失关键属性路径 "
                + ", ".join(sorted(str(path).replace(NS, "") for path in missing))
            )

    for shape_name, prop_name, enum_name in MES_ENUM_CONTRACT:
        values = _shape_in_values(
            shapes_graph, URIRef(NS + shape_name), URIRef(NS + prop_name)
        )
        codes = (service.mappings.get("enumerations") or {}).get(enum_name) or []
        if values is None:
            fail(f"{shape_name}.{prop_name}: 缺少 sh:in 枚举约束")
        elif set(values) != set(codes):
            fail(
                f"{shape_name}.{prop_name}: sh:in={sorted(set(values))}，"
                f"mappings.json[{enum_name}]={sorted(set(codes))}"
            )
        labels = service.enum_labels.get(enum_name)
        if not codes or labels is None or set(labels) != set(codes):
            fail(f"枚举 {enum_name}: mappings.json 码值或 labels 不完整")

    shape_iri = URIRef(NS + "MesWorkOrderShape")
    no_path = URIRef(NS + "mesWorkOrderNo")
    patterns = [
        shapes_graph.value(prop, URIRef(SH + "pattern"))
        for prop in shapes_graph.objects(shape_iri, URIRef(SH + "property"))
        if shapes_graph.value(prop, URIRef(SH + "path")) == no_path
    ]
    if not any(pattern is not None for pattern in patterns):
        fail("MesWorkOrderShape.mesWorkOrderNo: 缺少 sh:pattern（不得放宽为任意字符串）")


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
        if spec.source_system == "MES" and frozenset(spec.allowed_roles) != MES_ROLE_CONTRACT:
            fail(
                f"意图 {code}: MES 角色契约={sorted(MES_ROLE_CONTRACT)}，"
                f"实际={sorted(spec.allowed_roles)}"
            )
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
        output_columns = set().union(*spec.output_fields.values()) if spec.output_fields else set()
        for key in spec.record_key:
            if spec.source_system == "ERP":
                if key not in columns:
                    fail(f"意图 {code}: record_key={key} 不是 {primary.table} 的真实列")
            elif key not in output_columns:
                # 外部来源的行键不在 ERP 表中，但必须出现在输出里，供溯源使用
                fail(f"意图 {code}: 外部来源 record_key={key} 不在输出字段中")

        # 输出枚举：列→枚举名必须在 mappings.json 中，且 labels 覆盖全部码值
        service = get_ontology_service()
        service.ensure_loaded()
        for column, enum_name in spec.output_enums.items():
            if column not in output_columns:
                fail(f"意图 {code}: output_enums 列 {column} 不在输出字段中")
            codes = (service.mappings.get("enumerations") or {}).get(enum_name)
            labels = service.enum_labels.get(enum_name)
            if not codes:
                fail(f"意图 {code}: output_enums[{column}] 的枚举 {enum_name} 不在 mappings.json")
            elif labels is None or set(labels) != set(codes):
                fail(f"意图 {code}: 枚举 {enum_name} 的 labels 未覆盖全部码值")
        for column in output_columns:
            field = primary.fields.get(column)
            if field is not None and field.enum and column not in spec.output_enums:
                fail(f"意图 {code}: 枚举输出列 {column} 未声明 output_enums")

        covered = 0
        mapped_params = 0
        if spec.shacl_shape:
            # 外部数据源：按显式绑定的本体形状计算覆盖率
            service = get_ontology_service()
            service.ensure_loaded()
            shape_iri = URIRef(NS + spec.shacl_shape)
            if (shape_iri, RDF.type, URIRef(SH + "NodeShape")) not in service.shapes:
                fail(f"意图 {code}: shacl_shape={spec.shacl_shape} 不在 ontology/src/shapes.ttl")
                continue
            shape_paths = shape_property_paths(service.shapes, shape_iri)
            unknown_params = set(spec.shacl_params) - set(spec.params_model.model_fields)
            if unknown_params:
                fail(f"意图 {code}: shacl_params 含未知参数 {sorted(unknown_params)}")
            for param_name, prop_name in spec.shacl_params.items():
                mapped_params += 1
                if URIRef(NS + prop_name) not in shape_paths:
                    fail(
                        f"意图 {code}: shacl_params[{param_name}]={prop_name} "
                        f"不是形状 {spec.shacl_shape} 的属性路径"
                    )
                else:
                    covered += 1
        else:
            for param_name in spec.params_model.model_fields:
                field = _match_field(primary, param_name)
                if field is None:
                    continue
                mapped_params += 1
                if NS + field.rdf_name in primary.shape_paths:
                    covered += 1
        if mapped_params == 0 or covered == 0:
            expected_coverage = "none"
        elif covered == mapped_params:
            expected_coverage = "full"
        else:
            expected_coverage = "partial"
        if spec.shacl_coverage != expected_coverage:
            fail(
                f"意图 {code}: shacl_coverage={spec.shacl_coverage}，"
                f"按形状计算应为 {expected_coverage}"
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
                "output_enums": dict(spec.output_enums),
            }
            for key, value in expected.items():
                if item.get(key) != value:
                    fail(f"ai-intents.json[{code}].{key}={item.get(key)!r}，期望 {value!r}")
    elif INTENTS:
        fail("frontend/src/mock/ai-intents.json 缺失（注册表非空时必须提交导出物）")


# ── 7. 覆盖率与未暴露清单 ────────────────────────────────
def check_mcp() -> None:
    """MCP 工具清单与读写边界必须来自 security.ttl，且不开放写操作。"""
    from backend.services.ai.mcp.tools import boundary_problems, security_boundary, tool_specs

    try:
        boundary = security_boundary()
    except Exception as exc:  # noqa: BLE001 - 边界读取失败即门禁失败
        fail(f"MCP 安全边界读取失败: {type(exc).__name__}: {exc}")
        return
    if not boundary["write_methods"]:
        fail("security.ttl 未声明写方法，无法证明写操作默认关闭")
    for problem in boundary_problems():
        fail(f"MCP: {problem}")
    tools = tool_specs("GENERAL_MANAGER")
    for tool in tools:
        if not tool["annotations"].get("readOnlyHint"):
            fail(f"MCP 工具 {tool['name']} 未标记 readOnlyHint")
    print(f"MCP 只读工具: {len(tools)} 个；security.ttl 写方法: {boundary['write_methods']}")


def check_mes_semantics() -> None:
    """ERP↔MES 语义映射：锚点必须存在、枚举码必须合法、未匹配显式列出。"""
    from backend.services.ai.semantics import build_mes_mapping

    try:
        report = build_mes_mapping()
    except Exception as exc:  # noqa: BLE001 - 源缺失即门禁失败
        fail(f"MES 语义映射读取失败: {type(exc).__name__}: {exc}")
        return
    for problem in report["problems"]:
        fail(f"MES 语义映射: {problem}")
    if not report["items"]:
        fail("MES 语义映射为空")
    print(
        f"MES 语义映射: {len(report['items'])} 个实体，覆盖率 {report['coverage']:.2%}，"
        f"未匹配 {report['unmapped']}"
    )


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
    check_mes_shapes()
    check_projection(catalog)
    check_intents(catalog)
    check_mcp()
    check_mes_semantics()
    print_coverage(catalog)

    if failures:
        print(f"\nAI 语义目录门禁失败 {len(failures)} 项")
        return 1
    print("\nAI 语义目录门禁通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
