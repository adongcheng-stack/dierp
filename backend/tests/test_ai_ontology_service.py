"""本体检索服务（A1）测试：描述/检索/规则/受限 SPARQL/单例/缺源降级。"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from rdflib import URIRef

from backend.services.ai import ontology_service as mod
from backend.services.ai.ontology_service import (
    NS,
    OntologyService,
    OntologySourceError,
    get_ontology_service,
    reset_ontology_service,
)


@pytest.fixture(autouse=True)
def _fresh_singleton():
    reset_ontology_service()
    yield
    reset_ontology_service()


def test_describe_material():
    detail = get_ontology_service().describe("Material")
    assert detail["label"] == "物料"
    assert detail["top_category"] == "PhysicalObject"
    assert detail["shape"].endswith("#MaterialShape")
    assert detail["ontology_iri"] == NS
    names = {prop["name"] for prop in detail["properties"]}
    assert {"materialCode", "materialType", "procurementType"} <= names
    material_type = next(prop for prop in detail["properties"] if prop["name"] == "materialType")
    assert material_type["enum"] == ["FG", "SEMI", "RAW", "PACKAGING", "SERVICE"]


def test_search_material_and_inventory():
    service = get_ontology_service()
    material_hits = service.search("物料", limit=20)
    assert any(item["name"] == "Material" and item["kind"] == "class" for item in material_hits)
    assert len(material_hits) <= 20

    inventory_hits = service.search("库存", limit=20)
    assert inventory_hits
    assert any(item["name"] == "InventoryValuation" for item in inventory_hits)


def test_rules_metadata_and_degrade():
    rules = get_ontology_service().rules()
    ids = [rule["id"] for rule in rules]
    assert "R1" in ids and "R3" in ids
    assert all(rule["label"] for rule in rules)

    broken = OntologyService()
    broken.semantic = SimpleNamespace(subjects=None)  # 触发异常分支
    assert broken.rules() == []


def test_sparql_guardrails_and_schema_graph():
    service = get_ontology_service()
    service.load()  # validate_sparql 是纯函数，这里显式加载以检查 schema 图
    auto = service.validate_sparql("SELECT * WHERE { ?s ?p ?o }", 200)
    assert auto.rstrip().endswith("LIMIT 200")

    kept = service.validate_sparql("SELECT * WHERE { ?s ?p ?o } LIMIT 50", 200)
    assert kept.rstrip().endswith("LIMIT 50")

    for bad in (
        "SELECT * WHERE { ?s ?p ?o } LIMIT 600",
        "INSERT DATA { <urn:a> <urn:b> <urn:c> }",
        "SELECT * WHERE { SERVICE <http://evil.example/sparql> { ?s ?p ?o } }",
        "SELECT * FROM <http://evil.example/data> WHERE { ?s ?p ?o }",
        "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
    ):
        with pytest.raises(ValueError):
            service.validate_sparql(bad, 200)

    # 语义图含 JwtConfig，schema 图必须剔除
    jwt = URIRef(NS + "JwtConfig")
    assert list(service.semantic.triples((jwt, None, None)))
    leaked = service.sparql(
        f"SELECT ?p ?o WHERE {{ <{jwt}> ?p ?o }}"
    )
    assert leaked == []

    classes = service.sparql("SELECT ?s WHERE { ?s a owl:Class } LIMIT 5")
    assert classes and all(set(row) == {"s", "p", "o"} for row in classes)


def test_singleton_loads_once():
    first = get_ontology_service().describe("Material")
    second = get_ontology_service().describe("Material")
    assert first["name"] == second["name"] == "Material"
    assert get_ontology_service().load_count == 1


def test_missing_ontology_sources_raise_clear_error(monkeypatch, tmp_path):
    missing = tmp_path / "not-there"
    for attr in ("ERP_TTL", "SHAPES_TTL", "SECURITY_TTL", "RULES_SWRL", "MAPPINGS_JSON"):
        monkeypatch.setattr(mod, attr, missing / f"{attr}.ttl")
    with pytest.raises(OntologySourceError) as excinfo:
        OntologyService().load()
    assert "本体源文件缺失" in str(excinfo.value)
    assert "not-there" in str(excinfo.value)
