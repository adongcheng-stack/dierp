"""NumberGenerator 单元测试（纯函数 + SQLite 会话）。"""
from __future__ import annotations

import pytest

from backend.common.models.planning import NonConformanceReport
from backend.common.utils.number_generator import NumberGenerator


class TestFactoryNumber:
    def test_format_with_suffix(self):
        # 后缀截取前 4 位（生成器规则）
        assert (
            NumberGenerator.generate_factory_number("HS10", "04", 1, "ENIGAB01")
            == "HS10-04-0001-ENIG"
        )

    def test_format_without_suffix(self):
        assert NumberGenerator.generate_factory_number("HS20", "08", 123) == "HS20-08-0123"

    def test_short_prefix_padded(self):
        # 单字符 category 补 0 到 2 位（'4' -> '40'）
        assert NumberGenerator.generate_factory_number("AB", "4", 7) == "ABXX-40-0007"

    def test_parse_roundtrip(self):
        parsed = NumberGenerator.parse_factory_number("HS10-04-0001-ENIG")
        assert parsed == {
            "prefix": "HS10",
            "category": "04",
            "sequence": 1,
            "suffix": "ENIG",
        }

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            NumberGenerator.parse_factory_number("not-a-number")


class TestDocumentNumber:
    def test_first_sequence(self, db):
        number = NumberGenerator.generate_document_number(
            db, NonConformanceReport, "ncr_number", "TST", 4
        )
        assert number.startswith("TST-") and number.endswith("0001")

    def test_increments_within_same_day(self, db):
        db.add(NonConformanceReport(ncr_number="TST-20260101-0007", source_type="INSPECTION",
                                    material_code="M1", quantity=1, status="OPEN"))
        db.flush()
        number = NumberGenerator.generate_document_number(
            db, NonConformanceReport, "ncr_number", "TST", 4, date_part="20260101"
        )
        assert number == "TST-20260101-0008"

    def test_ignores_other_prefixes(self, db):
        db.add(NonConformanceReport(ncr_number="OTH-20260101-0099", source_type="INSPECTION",
                                    material_code="M1", quantity=1, status="OPEN"))
        db.flush()
        number = NumberGenerator.generate_document_number(
            db, NonConformanceReport, "ncr_number", "TST", 4, date_part="20260101"
        )
        assert number == "TST-20260101-0001"
