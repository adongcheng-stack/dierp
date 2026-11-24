"""控制层闸门测试（W0.5）：模式闸 422、SHACL 正反例、跳过语义、规模断言。"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from rdflib.namespace import XSD

from backend.services.ai.catalog import get_catalog
from backend.services.ai.errors import AIException
from backend.services.ai.gates import bind_params, build_param_graph, shacl_check
from backend.services.ai.intent import BoundIntent
from backend.services.ai.ontology_service import NS, get_ontology_service


class MaterialParams(BoundIntent):
    material_type: Literal["FG", "SEMI", "RAW", "PACKAGING", "SERVICE"] | None = None
    material_code: str | None = None
    status: str | None = None


@pytest.fixture(scope="module")
def shapes():
    service = get_ontology_service()
    service.load()
    return service.shapes


def test_schema_gate_rejects_extra_param():
    with pytest.raises(AIException) as excinfo:
        bind_params(MaterialParams, {"material_type": "FG", "bogus": 1})
    assert excinfo.value.code == "AI_PARAM_INVALID"
    assert "bogus" in excinfo.value.message


def test_schema_gate_rejects_bad_literal():
    with pytest.raises(AIException) as excinfo:
        bind_params(MaterialParams, {"material_type": "NOT_A_VALUE"})
    assert excinfo.value.code == "AI_PARAM_INVALID"
    assert "material_type" in excinfo.value.message


def test_shacl_enum_violation_fails(shapes):
    entity = get_catalog().get("Material")
    violations, status = shacl_check(entity, {"material_type": "FOO"}, shapes)
    assert status == "failed"
    assert violations
    assert violations[0]["path"] == "materialType"
    assert violations[0]["component"] == "InConstraintComponent"


def test_min_count_skipped_for_absent_path(shapes):
    entity = get_catalog().get("Material")
    violations, status = shacl_check(entity, {"material_type": "FG"}, shapes)
    assert violations == []
    assert status == "passed"


def test_uncovered_path_is_skipped(shapes):
    entity = get_catalog().get("Material")
    violations, status = shacl_check(entity, {"status": "ACTIVE"}, shapes)
    assert violations == []
    assert status == "skipped"


def test_partial_coverage(shapes):
    entity = get_catalog().get("Material")
    violations, status = shacl_check(
        entity, {"material_type": "FG", "status": "ACTIVE"}, shapes
    )
    assert violations == []
    assert status == "partial"


def test_entity_without_shape_is_skipped(shapes):
    entity = get_catalog().get("Customer")
    assert entity.shape_iri is None
    assert shacl_check(entity, {"credit_limit": 1000}, shapes) == ([], "skipped")


def test_entity_with_sparql_shape_is_skipped(shapes):
    entity = get_catalog().get("PlannedOrder")
    assert entity.shape_has_sparql is True
    assert shacl_check(entity, {"planned_order_number": "PO-1"}, shapes) == ([], "skipped")


def test_param_graph_is_minimal_and_uses_xsd_string():
    entity = get_catalog().get("Material")
    graph, provided = build_param_graph(entity, {"material_type": "FG"})
    assert len(graph) <= 1 + 1  # rdf:type + 1 个参数
    path = next(iter(provided))
    assert str(path).startswith(NS)
    value = graph.value(next(graph.subjects(predicate=path)), path)
    # 仓库 sh:in 用 simple literal；RDF 1.1 语义等价 xsd:string
    assert str(value) == "FG"
    assert value.datatype is None or value.datatype == XSD.string

    wide, _ = build_param_graph(entity, {
        "material_type": "FG", "material_code": "FG-001", "status": "ACTIVE",
    })
    assert len(wide) <= 1 + 3


# §6 P0 出口：SHACL 闸正反例各 ≥6 组（覆盖 passed/partial/skipped/failed）
POSITIVE_CASES = [
    ("Material", {"material_code": "FG-001", "material_type": "FG", "procurement_type": "MAKE"}, "passed"),
    ("Material", {"material_type": "FG", "status": "ACTIVE"}, "partial"),
    ("Material", {"status": "ACTIVE"}, "skipped"),
    ("Customer", {"credit_limit": 1000}, "skipped"),
    ("PlannedOrder", {"planned_order_number": "PO-1"}, "skipped"),
    ("Supplier", {"supplier_code": "SUP-AB", "status": "ACTIVE", "supplier_type": "MATERIAL"}, "passed"),
    ("InventoryValuation", {"material_code": "FG-001", "qty": 10, "amount": 100}, "passed"),
    ("Forecast", {"forecast_number": "FC-20260101-0001", "quantity": 1,
                  "due_date": datetime(2026, 1, 1)}, "passed"),
]

NEGATIVE_CASES = [
    ("Material", {"material_type": "FOO"}, "InConstraintComponent", "materialType"),
    ("Material", {"material_code": "bad"}, "PatternConstraintComponent", "materialCode"),
    ("Material", {"procurement_type": "WHATEVER"}, "InConstraintComponent", "procurementType"),
    ("Supplier", {"supplier_code": "SUP-1"}, "PatternConstraintComponent", "supplierId"),
    ("Supplier", {"status": "UNKNOWN"}, "InConstraintComponent", "status"),
    ("InventoryValuation", {"qty": -1}, "MinInclusiveConstraintComponent", "qty"),
    ("Forecast", {"quantity": 0}, "MinExclusiveConstraintComponent", "quantity"),
]


@pytest.mark.parametrize("name,params,expected_status", POSITIVE_CASES)
def test_shacl_positive_cases(shapes, name, params, expected_status):
    entity = get_catalog().get(name)
    violations, status = shacl_check(entity, params, shapes)
    assert violations == []
    assert status == expected_status


@pytest.mark.parametrize("name,params,component,path", NEGATIVE_CASES)
def test_shacl_negative_cases(shapes, name, params, component, path):
    entity = get_catalog().get(name)
    violations, status = shacl_check(entity, params, shapes)
    assert status == "failed"
    assert any(v["component"] == component and v["path"] == path for v in violations), violations
