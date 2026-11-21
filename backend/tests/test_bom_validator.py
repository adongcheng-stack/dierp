"""BOM 深层循环引用检查（validate_bom_hierarchy TODO）单元测试。"""
from datetime import datetime
from decimal import Decimal

from backend.common.models.eng import BOM, BOMItem
from backend.common.models.mm import Material
from backend.common.utils.validators import BOMValidator


def _setup(db, graph):
    for code in {n for edge in graph for n in edge}:
        db.add(Material(material_code=code, material_name=code, category="RAW",
                        unit="PCS", status="ACTIVE"))
    db.flush()
    for parent, children in graph.items():
        number = f"BOM-{parent}"
        db.add(BOM(bom_number=number, version="A.0", parent_material_code=parent,
                   effective_date=datetime(2026, 1, 1), base_quantity=1, status="NEW"))
        db.flush()
        for line, child in enumerate(children, start=1):
            db.add(BOMItem(bom_number=number, line_number=line,
                           material_code=child, quantity=Decimal("1"), unit="PCS"))
    db.flush()


def test_direct_cycle_is_rejected(db):
    _setup(db, {"A": ["A"]})
    result = BOMValidator.validate_bom_hierarchy(
        {"parent_material_code": "A", "items": [{"material_code": "A"}]}, db)
    assert result.is_valid is False
    assert any("循环引用" in e for e in result.errors)


def test_deep_cycle_is_rejected(db):
    # 库中已有 B→C→A，现在保存 A→B，构成 A→B→C→A
    _setup(db, {"B": ["C"], "C": ["A"]})
    result = BOMValidator.validate_bom_hierarchy(
        {"parent_material_code": "A", "items": [{"material_code": "B"}]}, db)
    assert result.is_valid is False
    assert any("B" in e and "A" in e for e in result.errors), result.errors


def test_acyclic_hierarchy_passes(db):
    _setup(db, {"B": ["C"], "C": ["D"]})
    result = BOMValidator.validate_bom_hierarchy(
        {"parent_material_code": "A", "items": [{"material_code": "B"}]}, db)
    assert result.is_valid is True
    assert result.errors == []
