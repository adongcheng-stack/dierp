"""QMS 质量管理引擎（来料/过程/终检三环节检验 + 不合格品闭环）。

覆盖：
- 检验单（InspectionOrder）：来料 INCOMING / 过程 IN_PROCESS / 终检 FINAL 三种检验环节，
  完成后计算合格/不合格数量并给出结论（PASS / FAIL / HOLD）。
- 不合格品记录（NonConformanceReport，NCR）：开立 → 评审 → 处置 → 关闭 的闭环状态机，
  并与报工（OperationReport）和 EAM（设备故障）双向联动：

  · 报工 → NCR：由报工单 scrap>0 一键生成 NCR（source_type=REPORT），数量取自报工报废数；
  · NCR → EAM：当处置判定为「设备原因」（equipment_cause=True）时，自动调用
    EamEngine.record_failure 生成一条 OPEN 故障记录，并把故障号回写到 NCR.failure_number。

所有写入均为幂等或可重复执行，供升级种子脚本与冒烟测试直接调用。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from backend.common.models.planning import (
    InspectionOrder,
    InspectionResult,
    InspectionStatus,
    InspectionType,
    NcrDisposition,
    NcrSeverity,
    NcrSourceType,
    NcrStatus,
    NonConformanceReport,
    Resource,
)
from backend.common.models.pp import OperationReport, ProductionOrder
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import ZERO, dec
from backend.services.planning.eam_engine import EamEngine

# 各检验环节的单据号前缀
INSPECTION_PREFIX = {
    InspectionType.INCOMING: "IQC",
    InspectionType.IN_PROCESS: "IPQC",
    InspectionType.FINAL: "FQC",
}


class QmsEngine:
    """质量管理静态方法集合：检验单闭环 / 不合格品闭环 / 与报工&EAM 联动。"""

    # ── 检验单 ─────────────────────────────────────────────────────────
    @staticmethod
    def create_inspection(
        db: Session,
        *,
        inspection_type: InspectionType,
        material_code: str,
        lot_number: Optional[str] = None,
        purchase_order_number: Optional[str] = None,
        report_number: Optional[str] = None,
        quantity_inspected: Optional[Decimal] = None,
        inspector: Optional[str] = None,
        inspected_at: Optional[datetime] = None,
        remarks: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> InspectionOrder:
        """新建一张检验单（DRAFT）。"""
        prefix = INSPECTION_PREFIX[InspectionType(inspection_type)]
        row = InspectionOrder(
            inspection_number=NumberGenerator.generate_document_number(
                db, InspectionOrder, "inspection_number", prefix, 4
            ),
            inspection_type=InspectionType(inspection_type),
            material_code=material_code,
            lot_number=lot_number,
            purchase_order_number=purchase_order_number,
            report_number=report_number,
            quantity_inspected=dec(quantity_inspected),
            inspector=inspector,
            inspected_at=inspected_at,
            status=InspectionStatus.DRAFT,
            remarks=remarks,
            created_by=created_by,
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def complete_inspection(
        db: Session,
        inspection_number: str,
        *,
        quantity_ok: Optional[Decimal] = None,
        quantity_rejected: Optional[Decimal] = None,
        inspector: Optional[str] = None,
        result: Optional[InspectionResult] = None,
        remarks: Optional[str] = None,
        auto_create_ncr: bool = True,
        updated_by: Optional[str] = None,
    ) -> InspectionOrder:
        """完成检验：落数量与结论，状态置 COMPLETED。

        - 未显式给结论时，由合格/不合格数量推导（rejected>0 → FAIL，否则 PASS）；
        - 结论为 FAIL 且 auto_create_ncr 时，自动生成一张来源为本检验单的 NCR。
        """
        row = (
            db.query(InspectionOrder)
            .filter(
                InspectionOrder.inspection_number == inspection_number,
                InspectionOrder.is_deleted == False,
            )
            .first()
        )
        if row is None:
            raise ValueError(f"检验单不存在: {inspection_number}")
        if row.status == InspectionStatus.COMPLETED:
            raise ValueError(f"检验单已完成，不能重复完成: {inspection_number}")

        rejected = dec(quantity_rejected)
        ok = dec(quantity_ok)
        row.quantity_ok = ok
        row.quantity_rejected = rejected
        if quantity_ok is not None or quantity_rejected is not None:
            # 只更新数量，避免覆盖手工填写的检验总数
            pass
        row.inspector = inspector or row.inspector
        row.inspected_at = datetime.now()
        if result is not None:
            row.result = InspectionResult(result)
        elif rejected > ZERO:
            row.result = InspectionResult.FAIL
        else:
            row.result = InspectionResult.PASS
        row.remarks = remarks if remarks is not None else row.remarks
        row.status = InspectionStatus.COMPLETED
        row.updated_by = updated_by
        db.flush()

        if row.result == InspectionResult.FAIL and auto_create_ncr:
            QmsEngine.create_ncr(
                db,
                source_type=NcrSourceType.INSPECTION,
                source_ref=row.inspection_number,
                inspection_number=row.inspection_number,
                report_number=row.report_number,
                lot_number=row.lot_number,
                material_code=row.material_code,
                quantity=rejected,
                created_by=updated_by,
            )
        return row

    @staticmethod
    def overview(db: Session, *, as_of: Optional[datetime] = None) -> dict:
        """QMS 工作台概览统计。"""
        as_of = as_of or datetime.now()
        inspections = db.query(InspectionOrder).filter(InspectionOrder.is_deleted == False)
        ncrs = db.query(NonConformanceReport).filter(NonConformanceReport.is_deleted == False)

        by_type: dict[str, int] = {}
        for it in InspectionType:
            by_type[it.value] = inspections.filter(InspectionOrder.inspection_type == it).count()

        return {
            "inspections": inspections.count(),
            "inspections_completed": inspections.filter(
                InspectionOrder.status == InspectionStatus.COMPLETED
            ).count(),
            "inspections_fail": inspections.filter(InspectionOrder.result == InspectionResult.FAIL).count(),
            "incoming": by_type[InspectionType.INCOMING.value],
            "in_process": by_type[InspectionType.IN_PROCESS.value],
            "final": by_type[InspectionType.FINAL.value],
            "ncrs": ncrs.count(),
            "ncrs_open": ncrs.filter(
                NonConformanceReport.status.in_([NcrStatus.OPEN, NcrStatus.UNDER_REVIEW])
            ).count(),
            "ncrs_closed": ncrs.filter(NonConformanceReport.status == NcrStatus.CLOSED).count(),
            "ncrs_critical": ncrs.filter(
                NonConformanceReport.severity == NcrSeverity.CRITICAL
            ).count(),
            "ncrs_equipment": ncrs.filter(NonConformanceReport.equipment_cause == True).count(),
            "as_of": as_of.isoformat(timespec="seconds"),
        }

    # ── 不合格品闭环 ────────────────────────────────────────────────────
    @staticmethod
    def create_ncr(
        db: Session,
        *,
        source_type: NcrSourceType = NcrSourceType.INSPECTION,
        source_ref: Optional[str] = None,
        inspection_number: Optional[str] = None,
        report_number: Optional[str] = None,
        lot_number: Optional[str] = None,
        material_code: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        defect_code: Optional[str] = None,
        defect_desc: Optional[str] = None,
        severity: NcrSeverity = NcrSeverity.MAJOR,
        created_by: Optional[str] = None,
    ) -> NonConformanceReport:
        """开立一张 NCR（OPEN）。

        当来源为报工单（source_type=REPORT 且传了 report_number）时，自动从
        OperationReport 取 scrap_quantity 作为不合格数量，并回填物料/批次。
        """
        if source_type == NcrSourceType.REPORT and report_number:
            report = (
                db.query(OperationReport)
                .filter(
                    OperationReport.report_number == report_number,
                    OperationReport.is_deleted == False,
                )
                .first()
            )
            if report is None:
                raise ValueError(f"报工单不存在: {report_number}")
            # 报工表本身没有物料字段，按生产订单解析物料
            if material_code is None:
                order = (
                    db.query(ProductionOrder)
                    .filter(ProductionOrder.order_number == report.production_order_number)
                    .first()
                )
                material_code = order.material_code if order else None
            lot_number = lot_number or report.lot_number
            if quantity is None:
                quantity = report.scrap_quantity
            source_ref = source_ref or report_number

        if not material_code:
            raise ValueError(
                "不合格品记录必须关联物料：未能从来源单据解析 material_code，请显式传入"
            )

        ncr = NonConformanceReport(
            ncr_number=NumberGenerator.generate_document_number(
                db, NonConformanceReport, "ncr_number", "NCR", 4
            ),
            source_type=NcrSourceType(source_type),
            source_ref=source_ref,
            inspection_number=inspection_number,
            report_number=report_number,
            lot_number=lot_number,
            material_code=material_code,
            quantity=dec(quantity),
            defect_code=defect_code,
            defect_desc=defect_desc,
            severity=NcrSeverity(severity),
            status=NcrStatus.OPEN,
            created_by=created_by,
        )
        db.add(ncr)
        db.flush()
        return ncr

    @staticmethod
    def review_ncr(
        db: Session,
        ncr_number: str,
        *,
        severity: Optional[NcrSeverity] = None,
        root_cause: Optional[str] = None,
        equipment_cause: Optional[bool] = None,
        resource_id: Optional[str] = None,
        failure_desc: Optional[str] = None,
        reviewed_by: Optional[str] = None,
    ) -> NonConformanceReport:
        """评审 NCR：定严重度/根因/是否设备原因。

        联动：当判定为设备原因（equipment_cause=True）且尚未生成 EAM 故障时，
        自动调用 EamEngine.record_failure 生成 OPEN 故障，并回写 failure_number。
        resource_id 用于指定故障关联设备；缺省时尝试从来源报工的工作中心解析。
        """
        ncr = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.ncr_number == ncr_number,
                NonConformanceReport.is_deleted == False,
            )
            .first()
        )
        if ncr is None:
            raise ValueError(f"不合格品记录不存在: {ncr_number}")
        if ncr.status == NcrStatus.CLOSED:
            raise ValueError(f"不合格品记录已关闭，不能再次评审: {ncr_number}")

        if severity is not None:
            ncr.severity = NcrSeverity(severity)
        if root_cause is not None:
            ncr.root_cause = root_cause
        if equipment_cause is not None:
            ncr.equipment_cause = bool(equipment_cause)
        ncr.reviewed_by = reviewed_by or ncr.reviewed_by
        ncr.reviewed_at = datetime.now()
        if ncr.status == NcrStatus.OPEN:
            ncr.status = NcrStatus.UNDER_REVIEW
        ncr.updated_by = reviewed_by
        db.flush()

        if ncr.equipment_cause and not ncr.failure_number:
            rid = resource_id or QmsEngine._resolve_resource_id(db, ncr)
            if rid is None:
                raise ValueError(
                    "判定为设备原因但无法解析设备资源，请显式传入 resource_id"
                )
            failure = EamEngine.record_failure(
                db,
                resource_id=rid,
                severity="HIGH" if ncr.severity == NcrSeverity.CRITICAL else "MEDIUM",
                description=failure_desc or f"[QMS联动] NCR {ncr.ncr_number}：{ncr.defect_desc or ncr.root_cause or ncr.defect_code or ''}",
                reported_by=reviewed_by,
                downtime_hours=None,
            )
            ncr.failure_number = failure.failure_number
            db.flush()
        return ncr

    @staticmethod
    def disposition_ncr(
        db: Session,
        ncr_number: str,
        *,
        disposition: NcrDisposition,
        disposition_note: Optional[str] = None,
        equipment_cause: Optional[bool] = None,
        resource_id: Optional[str] = None,
        failure_desc: Optional[str] = None,
        dispositioned_by: Optional[str] = None,
    ) -> NonConformanceReport:
        """处置 NCR：落处置方式，状态置 DISPOSITIONED。

        处置为 REVIEW（待设备维修/进一步分析）且判定设备原因时，同样确保
        EAM 故障已联动生成。
        """
        ncr = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.ncr_number == ncr_number,
                NonConformanceReport.is_deleted == False,
            )
            .first()
        )
        if ncr is None:
            raise ValueError(f"不合格品记录不存在: {ncr_number}")
        if ncr.status == NcrStatus.CLOSED:
            raise ValueError(f"不合格品记录已关闭，不能重复处置: {ncr_number}")

        ncr.disposition = NcrDisposition(disposition)
        if disposition_note is not None:
            ncr.disposition_note = disposition_note
        if equipment_cause is not None:
            ncr.equipment_cause = bool(equipment_cause)
        ncr.status = NcrStatus.DISPOSITIONED
        ncr.updated_by = dispositioned_by
        db.flush()

        if ncr.equipment_cause and not ncr.failure_number:
            rid = resource_id or QmsEngine._resolve_resource_id(db, ncr)
            if rid is None:
                raise ValueError(
                    "判定为设备原因但无法解析设备资源，请显式传入 resource_id"
                )
            failure = EamEngine.record_failure(
                db,
                resource_id=rid,
                severity="HIGH" if ncr.severity == NcrSeverity.CRITICAL else "MEDIUM",
                description=failure_desc or f"[QMS联动] NCR {ncr.ncr_number}：{ncr.defect_desc or ncr.root_cause or ncr.defect_code or ''}",
                reported_by=dispositioned_by,
                downtime_hours=None,
            )
            ncr.failure_number = failure.failure_number
            db.flush()
        return ncr

    @staticmethod
    def close_ncr(
        db: Session,
        ncr_number: str,
        *,
        disposition: Optional[NcrDisposition] = None,
        disposition_note: Optional[str] = None,
        closed_by: Optional[str] = None,
    ) -> NonConformanceReport:
        """关闭 NCR：必须已有处置方式，状态置 CLOSED。"""
        ncr = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.ncr_number == ncr_number,
                NonConformanceReport.is_deleted == False,
            )
            .first()
        )
        if ncr is None:
            raise ValueError(f"不合格品记录不存在: {ncr_number}")
        if ncr.status == NcrStatus.CLOSED:
            raise ValueError(f"不合格品记录已关闭，不能重复关闭: {ncr_number}")
        if ncr.disposition is None:
            if disposition is None:
                raise ValueError(f"NCR 未处置，关闭前请先指定处置方式: {ncr_number}")
            ncr.disposition = NcrDisposition(disposition)
        if disposition_note is not None:
            ncr.disposition_note = disposition_note
        ncr.status = NcrStatus.CLOSED
        ncr.closed_by = closed_by or ncr.closed_by
        ncr.closed_at = datetime.now()
        ncr.updated_by = closed_by
        db.flush()
        return ncr

    # ── 内部工具 ────────────────────────────────────────────────────────
    @staticmethod
    def _resolve_resource_id(db: Session, ncr: NonConformanceReport) -> Optional[str]:
        """从来源报工的工作中心解析一个可用设备资源；找不到返回 None。"""
        report = None
        if ncr.report_number:
            report = (
                db.query(OperationReport)
                .filter(
                    OperationReport.report_number == ncr.report_number,
                    OperationReport.is_deleted == False,
                )
                .first()
            )
        work_center_id = report.work_center_id if report else None
        if work_center_id is None:
            return None
        resource = (
            db.query(Resource)
            .filter(
                Resource.work_center_id == work_center_id,
                Resource.is_deleted == False,
            )
            .first()
        )
        return resource.resource_id if resource else None