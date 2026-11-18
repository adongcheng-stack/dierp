"""QmsEngine 引擎级单元测试：检验闭环 / NCR 闭环 / 双向联动（SQLite 内存库）。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from backend.common.models.planning import (
    EquipmentFailure,
    InspectionOrder,
    InspectionResult,
    InspectionStatus,
    InspectionType,
    NcrDisposition,
    NcrSourceType,
    NcrStatus,
    NonConformanceReport,
    Resource,
    ResourceStatus,
)
from backend.common.models.pp import OperationReport, ProductionOrder
from backend.services.planning.qms_engine import QmsEngine


@pytest.fixture()
def resource(db):
    row = Resource(resource_id="RES-TEST-01", status=ResourceStatus.ACTIVE)
    db.add(row)
    db.flush()
    return row


def test_inspection_closed_loop(db):
    inspection = QmsEngine.create_inspection(
        db,
        inspection_type=InspectionType.IN_PROCESS,
        material_code="M-TEST",
        quantity_inspected=Decimal("100"),
        created_by="ut",
    )
    assert inspection.status == InspectionStatus.DRAFT
    assert inspection.inspection_number.startswith("IPQC-")

    # 未给结论时按不合格数推导
    completed = QmsEngine.complete_inspection(
        db,
        inspection.inspection_number,
        quantity_ok=Decimal("95"),
        quantity_rejected=Decimal("5"),
        updated_by="ut",
    )
    assert completed.status == InspectionStatus.COMPLETED
    assert completed.result == InspectionResult.FAIL

    # FAIL + auto_create_ncr → 自动开立 OPEN NCR
    ncr = (
        db.query(NonConformanceReport)
        .filter(NonConformanceReport.inspection_number == inspection.inspection_number)
        .one()
    )
    assert ncr.source_type == NcrSourceType.INSPECTION
    assert ncr.status == NcrStatus.OPEN
    assert ncr.quantity == Decimal("5")

    # 重复完成应拒绝
    with pytest.raises(ValueError, match="不能重复完成"):
        QmsEngine.complete_inspection(db, inspection.inspection_number)


def test_pass_inspection_no_ncr(db):
    inspection = QmsEngine.create_inspection(
        db, inspection_type=InspectionType.INCOMING, material_code="M-TEST", created_by="ut"
    )
    QmsEngine.complete_inspection(
        db, inspection.inspection_number, quantity_ok=Decimal("10"), quantity_rejected=Decimal("0")
    )
    assert inspection.result == InspectionResult.PASS
    assert db.query(NonConformanceReport).count() == 0


def test_ncr_full_loop_with_equipment_linkage(db, resource):
    reviewed = QmsEngine.create_ncr(
        db,
        source_type=NcrSourceType.LOT_CARD,
        lot_number="LOT-UT-001",
        material_code="M-TEST",
        quantity=Decimal("8"),
        defect_desc="单元测试缺陷",
        created_by="ut",
    )
    assert reviewed.status == NcrStatus.OPEN

    reviewed = QmsEngine.review_ncr(
        db,
        reviewed.ncr_number,
        root_cause="主轴间隙",
        equipment_cause=True,
        resource_id=resource.resource_id,
        reviewed_by="ut",
    )
    assert reviewed.status == NcrStatus.UNDER_REVIEW
    assert reviewed.failure_number is not None

    failure = (
        db.query(EquipmentFailure)
        .filter(EquipmentFailure.failure_number == reviewed.failure_number)
        .one()
    )
    assert failure.resource_id == resource.resource_id
    assert failure.status.value == "OPEN"

    # 幂等：再次评审不应生成第二张故障
    before = db.query(EquipmentFailure).count()
    QmsEngine.review_ncr(db, reviewed.ncr_number, reviewed_by="ut")
    assert db.query(EquipmentFailure).count() == before

    disposed = QmsEngine.disposition_ncr(
        db, reviewed.ncr_number, disposition=NcrDisposition.REWORK, dispositioned_by="ut"
    )
    assert disposed.status == NcrStatus.DISPOSITIONED

    closed = QmsEngine.close_ncr(db, reviewed.ncr_number, closed_by="ut")
    assert closed.status == NcrStatus.CLOSED

    with pytest.raises(ValueError):
        QmsEngine.disposition_ncr(db, closed.ncr_number, disposition=NcrDisposition.SCRAP)


def test_ncr_material_resolved_from_report(db):
    order = ProductionOrder(
        order_number="PO-UT-0001",
        sales_order_number="SO-UT-0001",
        material_code="M-FROM-ORDER",
        quantity=Decimal("50"),
        unit="PCS",
    )
    db.add(order)
    report = OperationReport(
        report_number="OR-UT-0001",
        production_order_number="PO-UT-0001",
        work_center_id="WC-UT",
        operation_no="0010",
        reported_quantity=Decimal("50"),
        good_quantity=Decimal("45"),
        scrap_quantity=Decimal("5"),
        lot_number="LOT-UT-002",
        reported_by="ut",
        reported_at=datetime.now(),
    )
    db.add(report)
    db.flush()

    ncr = QmsEngine.create_ncr(
        db,
        source_type=NcrSourceType.REPORT,
        report_number="OR-UT-0001",
        created_by="ut",
    )
    # 报工表无物料字段：应从生产订单解析物料、取报废数与批次
    assert ncr.material_code == "M-FROM-ORDER"
    assert ncr.quantity == Decimal("5")
    assert ncr.lot_number == "LOT-UT-002"

    # 无物料可解析且未显式传入 → 明确报错而不是落脏数据
    empty_report = OperationReport(
        report_number="OR-UT-0002",
        production_order_number="PO-NOT-EXIST",
        work_center_id="WC-UT",
        operation_no="0010",
        reported_quantity=Decimal("1"),
        good_quantity=Decimal("0"),
        scrap_quantity=Decimal("1"),
        reported_by="ut",
        reported_at=datetime.now(),
    )
    db.add(empty_report)
    db.flush()
    with pytest.raises(ValueError, match="material_code"):
        QmsEngine.create_ncr(db, source_type=NcrSourceType.REPORT, report_number="OR-UT-0002")
