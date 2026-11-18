"""QMS 质量管理引擎冒烟测试（三环节检验 + 不合格品闭环 + 双向联动）。

Run: python backend/scripts/smoke_qms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    EquipmentFailure,
    InspectionOrder,
    InspectionResult,
    InspectionStatus,
    InspectionType,
    NcrDisposition,
    NcrSeverity,
    NcrSourceType,
    NcrStatus,
    NonConformanceReport,
)
from backend.services.planning.qms_engine import QmsEngine  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        print("[1] 检验单创建与完成（create_inspection / complete_inspection）")
        inspection = QmsEngine.create_inspection(
            db,
            inspection_type=InspectionType.IN_PROCESS,
            material_code="HF1004ENIGAB01",
            lot_number="LOT-20251230-0001",
            quantity_inspected="100",
            inspector="冒烟质检",
            remarks="冒烟测试：过程检验",
            created_by="smoke",
        )
        db.commit()
        assert inspection.status == InspectionStatus.DRAFT
        print(f"    创建 {inspection.inspection_number} 状态={inspection.status.value}")

        completed = QmsEngine.complete_inspection(
            db,
            inspection.inspection_number,
            quantity_ok="95",
            quantity_rejected="5",
            result=InspectionResult.FAIL,
            remarks="冒烟测试：不合格 5 PCS",
            auto_create_ncr=True,
            updated_by="smoke",
        )
        db.commit()
        assert completed.status == InspectionStatus.COMPLETED
        assert completed.result == InspectionResult.FAIL
        print(f"    完成 {completed.inspection_number} 结论={completed.result.value} 不合格={completed.quantity_rejected}")

        ncr_from_inspection = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.source_type == NcrSourceType.INSPECTION,
                NonConformanceReport.inspection_number == completed.inspection_number,
                NonConformanceReport.is_deleted == False,
            )
            .first()
        )
        assert ncr_from_inspection is not None, "检验 FAIL 未自动生成 NCR"
        print(f"    检验不合格自动生成 NCR {ncr_from_inspection.ncr_number} 状态={ncr_from_inspection.status.value}")

        print("\n[2] 报工 → NCR（create_ncr source_type=REPORT）")
        report_ncr = QmsEngine.create_ncr(
            db,
            source_type=NcrSourceType.REPORT,
            report_number="OR-QMS-2026-REPORT-0001",
            defect_code="SCRAP-DEMO",
            defect_desc="冒烟测试：由报工报废自动生成 NCR",
            created_by="smoke",
        )
        db.commit()
        print(f"    由报工单生成 {report_ncr.ncr_number} 数量={report_ncr.quantity} 批次={report_ncr.lot_number}")

        print("\n[3] NCR 评审 → 设备联动 EAM（review_ncr equipment_cause=True）")
        device_ncr = QmsEngine.create_ncr(
            db,
            source_type=NcrSourceType.LOT_CARD,
            source_ref="LOT-20251230-0003",
            lot_number="LOT-20251230-0003",
            material_code="HF1004ENIGAB02",
            quantity="8",
            defect_code="DRILL-OFFSET",
            defect_desc="冒烟测试：设备原因不合格",
            severity=NcrSeverity.MAJOR,
            created_by="smoke",
        )
        db.commit()
        reviewed = QmsEngine.review_ncr(
            db,
            device_ncr.ncr_number,
            severity=NcrSeverity.MAJOR,
            root_cause="主轴间隙",
            equipment_cause=True,
            resource_id="RES-DRILL-B-01",
            failure_desc="冒烟测试：联动 EAM 故障",
            reviewed_by="smoke",
        )
        db.commit()
        assert reviewed.failure_number is not None, "设备原因 NCR 未联动生成 EAM 故障"
        failure = (
            db.query(EquipmentFailure)
            .filter(EquipmentFailure.failure_number == reviewed.failure_number)
            .first()
        )
        assert failure is not None, f"EAM 故障不存在: {reviewed.failure_number}"
        print(
            f"    评审 {reviewed.ncr_number} → 联动 EAM 故障 {reviewed.failure_number} "
            f"({failure.resource_id}, status={failure.status.value})"
        )

        print("\n[4] 处置与关闭（disposition_ncr / close_ncr）")
        disposed = QmsEngine.disposition_ncr(
            db,
            report_ncr.ncr_number,
            disposition=NcrDisposition.REWORK,
            disposition_note="冒烟测试：返工重钻",
            dispositioned_by="smoke",
        )
        db.commit()
        assert disposed.status == NcrStatus.DISPOSITIONED
        closed = QmsEngine.close_ncr(
            db,
            report_ncr.ncr_number,
            closed_by="smoke",
        )
        db.commit()
        assert closed.status == NcrStatus.CLOSED
        print(f"    处置 {disposed.ncr_number}={disposed.disposition.value} → 关闭 {closed.ncr_number}")

        print("\n[5] 概览（overview）")
        overview = QmsEngine.overview(db)
        print(
            f"    检验单={overview['inspections']}（完成 {overview['inspections_completed']}，不合格 {overview['inspections_fail']}）"
            f" NCR={overview['ncrs']}（打开 {overview['ncrs_open']}，设备原因 {overview['ncrs_equipment']}）"
        )

        counts = {
            "检验单": db.query(InspectionOrder).filter(InspectionOrder.is_deleted == False).count(),
            "不合格品": db.query(NonConformanceReport).filter(NonConformanceReport.is_deleted == False).count(),
        }
        print(f"\n[6] 数据量: {counts}")
        print("\nQMS 质量管理冒烟通过")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())