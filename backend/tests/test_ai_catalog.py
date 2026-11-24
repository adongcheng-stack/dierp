"""语义目录（W0.4）测试：计数/形状路径/枚举/域/投影覆盖/失败定位/缓存。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.common.database.base import Base
from backend.services.ai import catalog as mod
from backend.services.ai.catalog import Catalog, CatalogError, get_catalog, reload_catalog


@pytest.fixture()
def built():
    return reload_catalog()


def _copy_model_dir(tmp_path: Path) -> Path:
    target = tmp_path / "model"
    shutil.copytree(mod.MODEL_DIR, target)
    return target


def _use_tmp(monkeypatch, directory: Path) -> None:
    monkeypatch.setattr(mod, "MODEL_DIR", directory)
    monkeypatch.setattr(mod, "PROJECTION_FILE", directory / "ai-projection.yaml")


def test_counts_and_tables(built):
    summary = built.summary()
    assert summary["total"] == 63
    assert summary["coverage"] == {"ontology": 59, "projection": 4, "not_exposed": 25}
    assert summary["not_exposed"] == {"has_class_no_fields": 5, "no_class": 20}
    assert summary["db_tables"] == 88
    assert len(summary["items"]) == 63
    for entity in built.entities.values():
        assert entity.table in Base.metadata.tables
        assert entity.domain
        assert entity.coverage in {"ontology", "projection"}


def test_shape_paths_and_enums(built):
    material = built.get("Material")
    assert material.fields["material_type"].enum == ("FG", "SEMI", "RAW", "PACKAGING", "SERVICE")
    assert material.fields["material_type"].required is True
    assert material.fields["material_code"].pattern == "^[A-Z0-9][A-Z0-9._-]{2,49}$"
    assert material.fields["material_code"].required is True

    # 全部投影/托管实体的形状路径都必须可解释（build 内已断言未命中 = 0）
    assert built.get("SalesOrder").fields["order_number"].rdf_name == "documentNumber"
    assert built.get("SalesOrder").fields["delivery_date"].rdf_name == "dueDate"
    assert built.get("MrpRun").fields["run_number"].rdf_name == "documentNumber"
    assert built.get("ScheduleRun").fields["algorithm"].rdf_name == "scheduleAlgorithm"
    assert built.get("Supplier").fields["supplier_code"].rdf_name == "supplierId"


def test_domains_and_bom_exclusion(built):
    assert built.get("SalesInvoice").domain == "finance"
    assert built.get("ReceivableEntry").domain == "finance"
    assert built.get("Material").domain == "mm"
    assert built.get("SalesOrder").domain == "sd"
    assert "BOM" not in built.entities
    assert "boms" not in {entity.table for entity in built.entities.values()}


def test_build_is_cached(built):
    before = built.build_count
    built.build()
    assert built.build_count == before


def test_wrong_class_fails_with_line(monkeypatch, tmp_path):
    directory = _copy_model_dir(tmp_path)
    path = directory / "planning.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("ontology_class: Supplier\n", "ontology_class: SupplierTypo\n", 1),
        encoding="utf-8",
    )
    _use_tmp(monkeypatch, directory)
    with pytest.raises(CatalogError) as excinfo:
        Catalog().build()
    message = str(excinfo.value)
    assert "本体类 SupplierTypo 不存在" in message
    assert "planning.yaml:" in message


def test_wrong_projection_field_fails(monkeypatch, tmp_path):
    directory = _copy_model_dir(tmp_path)
    path = directory / "ai-projection.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "fields: [material_code, material_name,",
            "fields: [material_code, not_a_column, material_name,",
            1,
        ),
        encoding="utf-8",
    )
    _use_tmp(monkeypatch, directory)
    with pytest.raises(CatalogError) as excinfo:
        Catalog().build()
    assert "投影字段 not_a_column" in str(excinfo.value)


def test_invalid_override_path_fails(monkeypatch, tmp_path):
    directory = _copy_model_dir(tmp_path)
    path = directory / "ai-projection.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("order_number: documentNumber, delivery_date: dueDate",
                     "order_number: notAPath, delivery_date: dueDate", 1),
        encoding="utf-8",
    )
    _use_tmp(monkeypatch, directory)
    with pytest.raises(CatalogError) as excinfo:
        Catalog().build()
    assert "notAPath" in str(excinfo.value)


def test_invalid_domain_fails(monkeypatch, tmp_path):
    directory = _copy_model_dir(tmp_path)
    path = directory / "ai-projection.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("    domain: mm\n", "    domain: unknown_domain\n", 1), encoding="utf-8")
    _use_tmp(monkeypatch, directory)
    with pytest.raises(CatalogError) as excinfo:
        Catalog().build()
    assert "unknown_domain" in str(excinfo.value)
