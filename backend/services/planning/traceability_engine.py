"""双向追溯引擎（只读派生查询）。

ADR-20261118-01：追溯是「派生视图」而非存储事实——图完全由既有单据链接
（LOT↔工单↔销售订单↔客户↔领料/报工↔检验↔NCR↔设备故障）推导，因此不新增
本体实体、不写库。原料批次级追溯由 MaterialIssue.batch_number /
purchase_order_number 两个派生字段提供：领料 → 原料批次 → 采购单 → 供应商。

图结构契约（与 frontend/src/mock/handlers.ts 同构）：
    node = {key, type, title, status, quantity, time, meta}
    edge = {from, to, label}          # key 形如 "LOT:LOT-20251230-0003"
    响应 = {root, direction, nodes, edges, truncated}
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.common.models.mm import Material, MaterialIssue
from backend.common.models.pp import LotCard, OperationReport, ProductionOrder
from backend.common.models.sd import Customer, SalesOrder
from backend.common.models.planning import (
    EquipmentFailure,
    InspectionOrder,
    NonConformanceReport,
    PurchaseOrder,
    PurchaseOrderLine,
)

MAX_NODES_PER_HOP = 50


class _Graph:
    """去重节点 + 有向边的轻量图容器。"""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, str]] = []
        self.truncated = False

    def add_node(
        self,
        ntype: str,
        key: str,
        title: str,
        *,
        status: Optional[str] = None,
        quantity: Optional[float] = None,
        time: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        node_key = f"{ntype}:{key}"
        if node_key not in self.nodes:
            self.nodes[node_key] = {
                "key": node_key,
                "type": ntype,
                "id": key,
                "title": title,
                "status": status,
                "quantity": quantity,
                "time": time,
                "meta": meta or {},
            }
        return node_key

    def add_edge(self, src: str, dst: str, label: str) -> None:
        edge = {"from": src, "to": dst, "label": label}
        if edge not in self.edges:
            self.edges.append(edge)

    def to_dict(self, root: str, direction: str) -> Dict[str, Any]:
        return {
            "root": root,
            "direction": direction,
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "truncated": self.truncated,
        }


def _num(value: Any) -> Optional[float]:
    return float(value) if value is not None else None


def _iso(value: Any) -> Optional[str]:
    return value.isoformat(timespec="seconds") if value is not None else None


def _label_of(value: Any) -> Optional[str]:
    return value.value if value is not None else None


def _add_batch_source(db: Session, g: _Graph, issue: MaterialIssue, from_key: str) -> None:
    """把领料单上的原料批次挂到图上：领料 → 原料批次 → 采购单 → 供应商。

    领料单无批次号时静默跳过，保持旧数据可用。
    """
    if not issue.batch_number:
        return

    supplier = None
    po = None
    if issue.purchase_order_number:
        po = (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.purchase_order_number == issue.purchase_order_number,
                PurchaseOrder.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if po is not None:
            supplier = po.supplier_name

    batch_key = g.add_node(
        "MATERIAL_BATCH",
        issue.batch_number,
        f"原料批次 {issue.batch_number}",
        meta={
            "batch_number": issue.batch_number,
            "material_code": issue.material_code,
            "purchase_order_number": issue.purchase_order_number,
            "supplier": supplier,
        },
    )
    g.add_edge(from_key, batch_key, "领用批次")

    if po is not None:
        po_key = g.add_node(
            "PURCHASE_ORDER",
            po.purchase_order_number,
            f"采购单 {po.purchase_order_number}",
            status=_label_of(po.status),
            time=_iso(po.order_date),
            meta={"supplier": po.supplier_name},
        )
        g.add_edge(batch_key, po_key, "批次来源")


class TraceEngine:
    """双向追溯：正向（LOT→…→客户/质量/设备）与反向（物料→…→客户）。"""

    # ── 共享展开：生产订单及其下游 ─────────────────────────────────────
    @staticmethod
    def _expand_production_order(db: Session, g: _Graph, order: ProductionOrder) -> str:
        order_key = g.add_node(
            "PRODUCTION_ORDER",
            order.order_number,
            f"生产订单 {order.order_number}",
            status=order.status,
            quantity=_num(order.quantity),
            time=_iso(order.planned_start_date),
            meta={"material_code": order.material_code, "sales_order_number": order.sales_order_number},
        )

        # 生产订单 → 销售订单 → 客户
        sales_order = None
        if order.sales_order_number:
            sales_order = (
                db.query(SalesOrder)
                .filter(SalesOrder.order_number == order.sales_order_number, SalesOrder.is_deleted == False)
                .first()
            )
        if sales_order is not None:
            so_key = g.add_node(
                "SALES_ORDER",
                sales_order.order_number,
                f"销售订单 {sales_order.order_number}",
                status=sales_order.status,
                quantity=_num(sales_order.quantity),
                time=_iso(sales_order.delivery_date),
                meta={"material_code": sales_order.material_code},
            )
            g.add_edge(order_key, so_key, "来自销售订单")
            customer = (
                db.query(Customer)
                .filter(Customer.customer_id == sales_order.customer_id, Customer.is_deleted == False)
                .first()
            )
            if customer is not None:
                cust_key = g.add_node(
                    "CUSTOMER",
                    customer.customer_id,
                    customer.legal_name or customer.customer_id,
                    meta={"industry": customer.customer_industry},
                )
                g.add_edge(so_key, cust_key, "客户")

        # 生产订单 → LOT 卡
        lots = (
            db.query(LotCard)
            .filter(
                LotCard.production_order_number == order.order_number,
                LotCard.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        lot_numbers: List[str] = []
        for lot in lots:
            lot_numbers.append(lot.lot_number)
            lot_key = g.add_node(
                "LOT",
                lot.lot_number,
                f"批次 {lot.lot_number}",
                status=lot.status,
                quantity=_num(lot.quantity),
                time=_iso(lot.completed_at),
                meta={"material_code": lot.material_code},
            )
            g.add_edge(lot_key, order_key, "批次归属工单")

        # 生产订单 → 领料
        issues = (
            db.query(MaterialIssue)
            .filter(
                MaterialIssue.production_order_number == order.order_number,
                MaterialIssue.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        for issue in issues:
            issue_key = g.add_node(
                "MATERIAL_ISSUE",
                issue.issue_number,
                f"领料 {issue.issue_number}",
                quantity=_num(issue.quantity),
                time=_iso(issue.issued_at),
                meta={"material_code": issue.material_code, "warehouse": issue.warehouse},
            )
            g.add_edge(issue_key, order_key, "领料")
            _add_batch_source(db, g, issue, issue_key)

        # 生产订单 → 报工（按工单匹配；批次卡上的报工即使登记在别的工单名下也一并纳入）
        report_query = db.query(OperationReport).filter(OperationReport.is_deleted == False)
        if lot_numbers:
            from sqlalchemy import or_

            report_query = report_query.filter(
                or_(
                    OperationReport.production_order_number == order.order_number,
                    OperationReport.lot_number.in_(lot_numbers),
                )
            )
        else:
            report_query = report_query.filter(
                OperationReport.production_order_number == order.order_number
            )
        reports = report_query.limit(MAX_NODES_PER_HOP).all()
        report_numbers: List[str] = []
        for report in reports:
            report_numbers.append(report.report_number)
            report_key = g.add_node(
                "OPERATION_REPORT",
                report.report_number,
                f"报工 {report.report_number}",
                status=report.status,
                quantity=_num(report.reported_quantity),
                time=_iso(report.reported_at),
                meta={
                    "lot_number": report.lot_number,
                    "operation_name": report.operation_name,
                    "good_quantity": _num(report.good_quantity),
                    "scrap_quantity": _num(report.scrap_quantity),
                },
            )
            g.add_edge(report_key, order_key, "报工")

        # 检验：优先按批次精确匹配；工单无批次卡时回落到按物料（覆盖 IQC 等无批次检验）
        insp_query = db.query(InspectionOrder).filter(
            InspectionOrder.is_deleted == False,
            InspectionOrder.material_code == order.material_code,
        )
        if lot_numbers:
            insp_query = insp_query.filter(
                (InspectionOrder.lot_number.in_(lot_numbers))
                | (InspectionOrder.lot_number.is_(None))
            )
        inspections = insp_query.limit(MAX_NODES_PER_HOP).all()
        inspection_numbers: List[str] = []
        for inspection in inspections:
            inspection_numbers.append(inspection.inspection_number)
            insp_key = g.add_node(
                "INSPECTION",
                inspection.inspection_number,
                f"检验 {inspection.inspection_number}",
                status=_label_of(inspection.status),
                quantity=_num(inspection.quantity_inspected),
                time=_iso(inspection.inspected_at),
                meta={
                    "type": _label_of(inspection.inspection_type),
                    "result": _label_of(inspection.result),
                    "lot_number": inspection.lot_number,
                    "quantity_rejected": _num(inspection.quantity_rejected),
                },
            )
            g.add_edge(insp_key, order_key, "检验")

        # NCR：按批次 / 检验单 / 报工单 关联
        ncr_query = db.query(NonConformanceReport).filter(NonConformanceReport.is_deleted == False)
        if lot_numbers:
            ncr_query = ncr_query.filter(
                (NonConformanceReport.lot_number.in_(lot_numbers))
                | (NonConformanceReport.inspection_number.in_(inspection_numbers or ["∅"]))
                | (NonConformanceReport.report_number.in_(report_numbers or ["∅"]))
            )
        else:
            ncr_query = ncr_query.filter(NonConformanceReport.material_code == order.material_code)
        ncrs = ncr_query.limit(MAX_NODES_PER_HOP).all()
        failure_numbers: List[str] = []
        for ncr in ncrs:
            ncr_key = g.add_node(
                "NCR",
                ncr.ncr_number,
                f"不合格品 {ncr.ncr_number}",
                status=_label_of(ncr.status),
                quantity=_num(ncr.quantity),
                time=_iso(ncr.created_at),
                meta={
                    "severity": _label_of(ncr.severity),
                    "disposition": _label_of(ncr.disposition),
                    "defect_desc": ncr.defect_desc,
                    "equipment_cause": ncr.equipment_cause,
                },
            )
            g.add_edge(ncr_key, order_key, "不合格")
            if ncr.failure_number:
                failure_numbers.append(ncr.failure_number)

        # NCR → EAM 设备故障
        if failure_numbers:
            failures = (
                db.query(EquipmentFailure)
                .filter(
                    EquipmentFailure.failure_number.in_(failure_numbers),
                    EquipmentFailure.is_deleted == False,
                )
                .limit(MAX_NODES_PER_HOP)
                .all()
            )
            for failure in failures:
                fail_key = g.add_node(
                    "EQUIPMENT_FAILURE",
                    failure.failure_number,
                    f"设备故障 {failure.failure_number}",
                    status=_label_of(failure.status),
                    time=_iso(failure.occurred_at),
                    meta={
                        "resource_id": failure.resource_id,
                        "severity": _label_of(failure.severity),
                        "description": failure.description,
                    },
                )
                g.add_edge(fail_key, order_key, "设备原因")
        return order_key

    # ── 正向：从 LOT 出发 ─────────────────────────────────────────────
    @staticmethod
    def trace_lot(db: Session, lot_number: str) -> Dict[str, Any]:
        g = _Graph()
        lots = (
            db.query(LotCard)
            .filter(LotCard.lot_number == lot_number, LotCard.is_deleted == False)
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        if not lots:
            raise ValueError(f"批次不存在: {lot_number}")
        lot = lots[0]
        lot_key = g.add_node(
            "LOT",
            lot.lot_number,
            f"批次 {lot.lot_number}",
            status=lot.status,
            quantity=_num(lot.quantity),
            time=_iso(lot.completed_at),
            meta={"material_code": lot.material_code, "mi_number": lot.mi_number},
        )
        order = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.order_number == lot.production_order_number,
                ProductionOrder.is_deleted == False,
            )
            .first()
        )
        if order is not None:
            order_key = TraceEngine._expand_production_order(db, g, order)
            g.add_edge(lot_key, order_key, "生产订单")
        else:
            # 孤批次也要能追到物料与质量记录
            g.add_edge(lot_key, lot_key, "")
            insp = (
                db.query(InspectionOrder)
                .filter(
                    InspectionOrder.lot_number == lot.lot_number,
                    InspectionOrder.is_deleted == False,
                )
                .limit(MAX_NODES_PER_HOP)
                .all()
            )
            for inspection in insp:
                insp_key = g.add_node(
                    "INSPECTION",
                    inspection.inspection_number,
                    f"检验 {inspection.inspection_number}",
                    status=_label_of(inspection.status),
                    time=_iso(inspection.inspected_at),
                    meta={"result": _label_of(inspection.result)},
                )
                g.add_edge(insp_key, lot_key, "检验")
        return g.to_dict(lot_key, "FORWARD")

    # ── 反向：从物料出发 ─────────────────────────────────────────────
    @staticmethod
    def trace_material(db: Session, material_code: str) -> Dict[str, Any]:
        g = _Graph()
        material = (
            db.query(Material)
            .filter(Material.material_code == material_code, Material.is_deleted == False)
            .first()
        )
        if material is None:
            raise ValueError(f"物料不存在: {material_code}")
        material_key = g.add_node(
            "MATERIAL",
            material.material_code,
            f"{material.material_code} {material.material_name or ''}".strip(),
            meta={"material_name": material.material_name},
        )

        # 反向：领料 → 工单（复用生产订单展开）
        issues = (
            db.query(MaterialIssue)
            .filter(
                MaterialIssue.material_code == material_code,
                MaterialIssue.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        seen_orders = set()
        for issue in issues:
            issue_key = g.add_node(
                "MATERIAL_ISSUE",
                issue.issue_number,
                f"领料 {issue.issue_number}",
                quantity=_num(issue.quantity),
                time=_iso(issue.issued_at),
                meta={"production_order_number": issue.production_order_number},
            )
            g.add_edge(issue_key, material_key, "领用")
            _add_batch_source(db, g, issue, issue_key)
            if issue.production_order_number and issue.production_order_number not in seen_orders:
                order = (
                    db.query(ProductionOrder)
                    .filter(
                        ProductionOrder.order_number == issue.production_order_number,
                        ProductionOrder.is_deleted == False,
                    )
                    .first()
                )
                if order is not None:
                    seen_orders.add(issue.production_order_number)
                    order_key = TraceEngine._expand_production_order(db, g, order)
                    g.add_edge(order_key, issue_key, "领料")

        # 反向：直接挂在物料上的检验/NCR（来料检验、物料级 NCR）
        inspections = (
            db.query(InspectionOrder)
            .filter(
                InspectionOrder.material_code == material_code,
                InspectionOrder.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        for inspection in inspections:
            insp_key = g.add_node(
                "INSPECTION",
                inspection.inspection_number,
                f"检验 {inspection.inspection_number}",
                status=_label_of(inspection.status),
                time=_iso(inspection.inspected_at),
                meta={
                    "type": _label_of(inspection.inspection_type),
                    "result": _label_of(inspection.result),
                },
            )
            g.add_edge(insp_key, material_key, "检验")

        ncrs = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.material_code == material_code,
                NonConformanceReport.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        failure_numbers: List[str] = []
        for ncr in ncrs:
            ncr_key = g.add_node(
                "NCR",
                ncr.ncr_number,
                f"不合格品 {ncr.ncr_number}",
                status=_label_of(ncr.status),
                quantity=_num(ncr.quantity),
                time=_iso(ncr.created_at),
                meta={
                    "severity": _label_of(ncr.severity),
                    "disposition": _label_of(ncr.disposition),
                    "equipment_cause": ncr.equipment_cause,
                },
            )
            g.add_edge(ncr_key, material_key, "不合格")
            if ncr.failure_number:
                failure_numbers.append(ncr.failure_number)
        if failure_numbers:
            failures = (
                db.query(EquipmentFailure)
                .filter(
                    EquipmentFailure.failure_number.in_(failure_numbers),
                    EquipmentFailure.is_deleted == False,
                )
                .limit(MAX_NODES_PER_HOP)
                .all()
            )
            for failure in failures:
                fail_key = g.add_node(
                    "EQUIPMENT_FAILURE",
                    failure.failure_number,
                    f"设备故障 {failure.failure_number}",
                    status=_label_of(failure.status),
                    time=_iso(failure.occurred_at),
                    meta={"resource_id": failure.resource_id},
                )
                g.add_edge(fail_key, material_key, "设备原因")

        # 反向：采购来源（当前演示库可能为空，优雅缺省）
        po_lines = (
            db.query(PurchaseOrderLine)
            .filter(
                PurchaseOrderLine.material_code == material_code,
                PurchaseOrderLine.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        for line in po_lines:
            po = (
                db.query(PurchaseOrder)
                .filter(
                    PurchaseOrder.purchase_order_number == line.purchase_order_number,
                    PurchaseOrder.is_deleted == False,
                )
                .first()
            )
            line_key = g.add_node(
                "PURCHASE_ORDER_LINE",
                f"{line.purchase_order_number}-{line.line_number}",
                f"采购行 {line.purchase_order_number}/#{line.line_number}",
                status=line.status,
                quantity=_num(line.quantity),
                meta={"received_quantity": _num(line.received_quantity)},
            )
            g.add_edge(line_key, material_key, "采购")
            if po is not None:
                po_key = g.add_node(
                    "PURCHASE_ORDER",
                    po.purchase_order_number,
                    f"采购单 {po.purchase_order_number}",
                    status=po.status,
                    time=_iso(po.order_date),
                    meta={"supplier": po.supplier_name},
                )
                g.add_edge(po_key, line_key, "采购单")
        return g.to_dict(material_key, "BACKWARD")

    # ── 从订单出发（自动识别生产/销售订单） ──────────────────────────
    @staticmethod
    def trace_order(db: Session, order_number: str) -> Dict[str, Any]:
        order = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.order_number == order_number,
                ProductionOrder.is_deleted == False,
            )
            .first()
        )
        if order is not None:
            g = _Graph()
            order_key = TraceEngine._expand_production_order(db, g, order)
            return g.to_dict(order_key, "FORWARD")

        sales_order = (
            db.query(SalesOrder)
            .filter(SalesOrder.order_number == order_number, SalesOrder.is_deleted == False)
            .first()
        )
        if sales_order is None:
            raise ValueError(f"订单不存在: {order_number}")

        g = _Graph()
        so_key = g.add_node(
            "SALES_ORDER",
            sales_order.order_number,
            f"销售订单 {sales_order.order_number}",
            status=sales_order.status,
            quantity=_num(sales_order.quantity),
            time=_iso(sales_order.delivery_date),
            meta={"material_code": sales_order.material_code},
        )
        customer = (
            db.query(Customer)
            .filter(
                Customer.customer_id == sales_order.customer_id,
                Customer.is_deleted == False,
            )
            .first()
        )
        if customer is not None:
            cust_key = g.add_node(
                "CUSTOMER",
                customer.customer_id,
                customer.legal_name or customer.customer_id,
                meta={"industry": customer.customer_industry},
            )
            g.add_edge(so_key, cust_key, "客户")
        orders = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.sales_order_number == sales_order.order_number,
                ProductionOrder.is_deleted == False,
            )
            .limit(MAX_NODES_PER_HOP)
            .all()
        )
        for order in orders:
            order_key = TraceEngine._expand_production_order(db, g, order)
            g.add_edge(order_key, so_key, "生产订单")
        return g.to_dict(so_key, "FORWARD")

    # ── 根节点搜索 ────────────────────────────────────────────────────
    @staticmethod
    def search(db: Session, q: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = (q or "").strip()
        if not q:
            return []
        like = f"%{q}%"
        out: List[Dict[str, Any]] = []

        lots = (
            db.query(LotCard)
            .filter(LotCard.lot_number.ilike(like), LotCard.is_deleted == False)
            .limit(limit)
            .all()
        )
        for lot in lots:
            out.append({"type": "LOT", "id": lot.lot_number, "title": f"批次 {lot.lot_number}", "meta": {"material_code": lot.material_code}})

        orders = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.order_number.ilike(like),
                ProductionOrder.is_deleted == False,
            )
            .limit(limit)
            .all()
        )
        for order in orders:
            out.append({"type": "PRODUCTION_ORDER", "id": order.order_number, "title": f"生产订单 {order.order_number}", "meta": {"material_code": order.material_code}})

        sales = (
            db.query(SalesOrder)
            .filter(SalesOrder.order_number.ilike(like), SalesOrder.is_deleted == False)
            .limit(limit)
            .all()
        )
        for so in sales:
            out.append({"type": "SALES_ORDER", "id": so.order_number, "title": f"销售订单 {so.order_number}", "meta": {"material_code": so.material_code}})

        materials = (
            db.query(Material)
            .filter(
                (Material.material_code.ilike(like)) | (Material.material_name.ilike(like)),
                Material.is_deleted == False,
            )
            .limit(limit)
            .all()
        )
        for material in materials:
            out.append({"type": "MATERIAL", "id": material.material_code, "title": f"{material.material_code} {material.material_name or ''}".strip(), "meta": {}})

        ncrs = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.ncr_number.ilike(like),
                NonConformanceReport.is_deleted == False,
            )
            .limit(limit)
            .all()
        )
        for ncr in ncrs:
            root_id = ncr.lot_number or ncr.material_code
            out.append({
                "type": "NCR",
                "id": ncr.ncr_number,
                "title": f"不合格品 {ncr.ncr_number}",
                "meta": {"trace_lot": ncr.lot_number, "trace_material": ncr.material_code, "root_id": root_id},
            })
        return out[:limit]

    # ── 概览 ─────────────────────────────────────────────────────────
    @staticmethod
    def overview(db: Session) -> Dict[str, Any]:
        def count(model, *filters):  # noqa: ANN002
            query = db.query(model)
            for f in filters:
                query = query.filter(f)
            return query.filter(model.is_deleted == False).count()  # noqa: E712

        return {
            "lots": count(LotCard),
            "production_orders": count(ProductionOrder),
            "sales_orders": count(SalesOrder),
            "materials": count(Material),
            "material_issues": count(MaterialIssue),
            "operation_reports": count(OperationReport),
            "inspections": count(InspectionOrder),
            "ncrs": count(NonConformanceReport),
            "equipment_failures": count(EquipmentFailure),
            "purchase_orders": count(PurchaseOrder),
            "customers": count(Customer),
        }
