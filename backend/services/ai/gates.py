"""控制层闸门：模式闸（pydantic）+ SHACL 闸（复用既有 NodeShape）。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §5.4。
- 模式闸：``BoundIntent`` 的 ``extra="forbid"`` + 字段类型/范围；失败抛 ``AI_PARAM_INVALID``。
- SHACL 闸：只构造"过滤值节点"，不构造完整实例；``minCount`` 只对未提供路径豁免；
  无形状或含 ``sh:sparql`` 的形状如实返回 ``skipped``，不冒充 ``passed``。
"""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, SH as SHNS, XSD
from pyshacl import validate

from backend.services.ai.errors import AIException
from backend.services.ai.intent import BoundIntent, EntityMeta
from backend.services.ai.ontology_service import NS

# 设计 §5.1 要求枚举值是字面量而不是类 IRI。仓库 shapes.ttl 的 sh:in 使用 simple literal
# （rdflib 中 datatype=None）；显式 xsd:string 会因 rdflib 的严格 term 相等性被判为不在枚举内。
# RDF 1.1 下 simple literal 语义即 xsd:string，因此字符串/枚举使用 simple literal。
_DATATYPE: dict[str, URIRef | None] = {
    "string": None,
    "enum": None,
    "int": XSD.integer,
    "decimal": XSD.decimal,
    "bool": XSD.boolean,
    "datetime": XSD.dateTime,
}

VALID_SHACL_STATUSES = frozenset({"passed", "partial", "skipped", "failed"})


def bind_params(model: type[BoundIntent], params: dict[str, Any]) -> BoundIntent:
    """模式闸：多余参数/类型错误 → ``AI_PARAM_INVALID``（消息含字段名）。"""
    try:
        return model(**params)
    except ValidationError as exc:
        details: list[str] = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc") or ()) or "__root__"
            details.append(f"{location}: {error.get('msg', '')}")
        raise AIException("AI_PARAM_INVALID", "参数校验失败: " + "; ".join(details)) from exc


def build_param_graph(
    entity: EntityMeta, params: dict[str, Any]
) -> tuple[Graph, set[URIRef]]:
    """只把"实体字段参数"构造成 SHACL 校验用的最小图。"""
    graph = Graph()
    node = BNode()
    graph.add((node, RDF.type, URIRef(entity.ontology_iri)))
    provided: set[URIRef] = set()
    for db_name, value in params.items():
        field = entity.fields.get(db_name)
        if field is None or value is None:
            continue
        path = URIRef(NS + field.rdf_name)
        datatype = _DATATYPE[field.data_type]
        graph.add((node, path, Literal(value) if datatype is None else Literal(value, datatype=datatype)))
        provided.add(path)
    return graph, provided


def shacl_check(
    entity: EntityMeta, params: dict[str, Any], shapes_graph: Graph
) -> tuple[list[dict[str, str]], str]:
    """返回 ``(violations, status)``，status ∈ passed/partial/skipped/failed。"""
    if not entity.shape_iri or entity.shape_has_sparql:
        return [], "skipped"

    graph, provided = build_param_graph(entity, params)
    conforms, results_graph, _ = validate(
        graph,
        shacl_graph=shapes_graph,
        inference="none",
        advanced=False,
    )

    violations: list[dict[str, str]] = []
    for result in results_graph.subjects(RDF.type, SHNS.ValidationResult):
        path = results_graph.value(result, SHNS.resultPath)
        component = results_graph.value(result, SHNS.sourceConstraintComponent)
        if component == SHNS.MinCountConstraintComponent and path not in provided:
            continue
        violations.append({
            "path": str(path).replace(NS, "") if path else "",
            "component": str(component).rsplit("#", 1)[-1] if component else "",
            "message": str(results_graph.value(result, SHNS.resultMessage) or ""),
        })

    shape_paths = {URIRef(path) for path in entity.shape_paths}
    matched = provided & shape_paths
    if violations:
        status = "failed"
    elif provided and matched == provided:
        status = "passed"
    elif matched:
        status = "partial"
    else:
        status = "skipped"

    assert status in VALID_SHACL_STATUSES
    return violations, status
