"""MCP 工具清单：只读边界与工具可见性从 ``security.ttl`` 派生。

- 工具 = 意图注册表中 ``read_only=True`` 且其 ``domains`` 对 MCP 角色可读的意图；
- 可读性来自 ``security.ttl`` 的 ``:AccessDomain``（``:anonymousRead`` / ``:readRole``）；
- 写方法清单来自 ``security.ttl`` 的 ``:WriteMethods``，本模块不注册任何写工具。
"""
from __future__ import annotations

from typing import Any

from rdflib import URIRef
from rdflib.namespace import RDF

from backend.services.ai.catalog import get_catalog
from backend.services.ai.config import get_settings
from backend.services.ai.intents import INTENT_REGISTRY
from backend.services.ai.ontology_service import NS, get_ontology_service

_DOMAIN_CLASS = URIRef(NS + "AccessDomain")
_DOMAIN_CODE = URIRef(NS + "domainCode")
_READ_ROLE = URIRef(NS + "readRole")
_ANON_READ = URIRef(NS + "anonymousRead")
_METHOD = URIRef(NS + "method")


def _local(value: Any) -> str:
    text = str(value)
    return text.split("#")[-1] if "#" in text else text.rsplit("/", 1)[-1]


def security_boundary() -> dict[str, Any]:
    """从 security.ttl 读取读策略与写方法；本体缺失时抛 OntologySourceError。"""
    ontology = get_ontology_service()
    ontology.ensure_loaded()
    graph = ontology.semantic
    assert graph is not None

    domains: dict[str, dict[str, Any]] = {}
    for subject in graph.subjects(RDF.type, _DOMAIN_CLASS):
        code = graph.value(subject, _DOMAIN_CODE)
        if code is None:
            continue
        anon = str(graph.value(subject, _ANON_READ) or "false").lower() == "true"
        roles = sorted({_local(role) for role in graph.objects(subject, _READ_ROLE)})
        domains[str(code)] = {"anonymous_read": anon, "read_roles": roles}

    write_methods = sorted({str(method).upper() for method in graph.objects(None, _METHOD)})
    return {"domains": domains, "write_methods": write_methods}


def role_can_read(domain: str, role: str, boundary: dict[str, Any] | None = None) -> bool:
    item = (boundary or security_boundary())["domains"].get(domain)
    if item is None:
        return False
    return role == "ADMIN" or item["anonymous_read"] or role in item["read_roles"]


def _visible(spec: Any, role: str, boundary: dict[str, Any], mes_enabled: bool) -> bool:
    """工具可见性：只读 + 角色 + 域可读 + 外部数据源开关。"""
    if not spec.read_only:
        return False
    if role not in spec.allowed_roles:
        return False
    if not spec.domains or not all(
        role_can_read(domain, role, boundary) for domain in spec.domains
    ):
        return False
    if spec.source_system == "MES" and not mes_enabled:
        return False
    return True


def tool_specs(role: str) -> list[dict[str, Any]]:
    """生成 MCP tools/list 响应；写意图（若未来出现）默认不暴露。"""
    boundary = security_boundary()
    catalog = get_catalog()
    mes_enabled = get_settings().mes_ready
    tools: list[dict[str, Any]] = []
    for spec in INTENT_REGISTRY.values():
        if not _visible(spec, role, boundary, mes_enabled):
            continue
        entity = catalog.entities.get(spec.primary_entity)
        tools.append({
            "name": spec.code,
            "description": spec.description or spec.label,
            "inputSchema": spec.params_model.model_json_schema(),
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
            "_meta": {
                "label": spec.label,
                "domains": list(spec.domains),
                "ontologyClass": entity.ontology_iri if entity is not None else None,
            },
        })
    return sorted(tools, key=lambda item: item["name"])


def boundary_problems(role: str = "GENERAL_MANAGER") -> list[str]:
    """门禁用：检查工具边界是否完全来自 security.ttl，且没有写工具。"""
    boundary = security_boundary()
    problems: list[str] = []
    if not boundary["write_methods"]:
        problems.append("security.ttl 未声明 WriteMethods")
    for code, spec in INTENT_REGISTRY.items():
        if not spec.read_only:
            problems.append(f"意图 {code} 不是只读，禁止进入 MCP")
        for domain in spec.domains:
            if domain not in boundary["domains"]:
                problems.append(f"意图 {code} 的域 {domain} 未在 security.ttl 声明")
    exposed = {tool["name"] for tool in tool_specs(role)}
    mes_enabled = get_settings().mes_ready
    expected = {
        code for code, spec in INTENT_REGISTRY.items()
        if _visible(spec, role, boundary, mes_enabled)
    }
    if exposed != expected:
        problems.append(f"MCP 工具集与只读意图不一致: {sorted(exposed)} != {sorted(expected)}")
    return problems
