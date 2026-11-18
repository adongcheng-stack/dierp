"""Standard / actual manufacturing cost engine.

Pipeline:
  1. StandardCost.rollup   — multi-level BOM cost roll-up per material (used as the
                             cost basis that MRP/kitting/APS all share).
  2. ProductionCost.collect — accumulate actual material issue + operation labour /
                             machine / overhead from operation reports and cost rates.
  3. CostVariance.analyze   — standard-vs-actual variance by type (price/usage/labor/overhead).
  4. CostSettlement.settle  — close a work order and write the settlement record.

The four layers intentionally follow the ontology: StandardCost / ProductionCost /
CostVariance / CostSettlement are already modelled and generated.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common.models.eng import Routing, RoutingOperation, RoutingStatus
from backend.common.models.mm import Material, MaterialIssue
from backend.common.models.planning import (
    CostRate,
    CostRateType,
    CostSettlement,
    CostStatus,
    CostVariance,
    ProductionCost,
    StandardCost,
    VarianceType,
)
from backend.common.models.pp import OperationReport, OperationReportStatus, ProductionOrder
from backend.common.utils.number_generator import NumberGenerator
from backend.services.planning.common import (
    ZERO,
    bom_components,
    dec,
    get_bom,
    get_material,
    get_routing,
    routing_operations,
)

CURRENCY = "CNY"
Q2 = Decimal("0.01")


def _q(value) -> Decimal:
    return dec(value).quantize(Q2, rounding=ROUND_HALF_UP)


class CostEngine:
    """Factory-style static service that mirrors the four cost entities."""

    # ── Standard cost roll-up ───────────────────────────────────────────
    @staticmethod
    def rollup_standard_cost(
        db: Session,
        material_code: str,
        *,
        version: str = "1",
        cost_date: Optional[datetime] = None,
        roll_deep: bool = False,
        created_by: Optional[str] = None,
    ) -> StandardCost:
        """Single-level roll-up for one material. When ``roll_deep`` is set the
        component standard costs are (re)computed first so a top FG cost is fully
        aggregated from raw materials."""
        cost_date = cost_date or datetime.now()
        material = get_material(db, material_code)
        if material is None:
            raise ValueError(f"物料不存在: {material_code}")

        if roll_deep:
            CostEngine._roll_components(db, material_code, cost_date, created_by)

        return CostEngine._compute_standard(db, material, version, cost_date, created_by)

    @staticmethod
    def rollup_many(
        db: Session,
        material_codes: list[str],
        *,
        version: str = "1",
        created_by: Optional[str] = None,
    ) -> int:
        """Roll up a set of materials, sorting by BOM dependency so parents are
        computed after their children when possible."""
        cost_date = datetime.now()
        done = set()

        def visit(code: str, seen: set[str]) -> None:
            if code in done or code in seen:
                return
            seen = seen | {code}
            bom = get_bom(db, code, cost_date)
            if bom is not None:
                for item in bom_components(db, bom):
                    visit(item.material_code, seen)
            CostEngine._compute_standard(db, get_material(db, code), version, cost_date, created_by)
            done.add(code)

        for code in material_codes:
            visit(code, set())
        return len(done)

    @staticmethod
    def _roll_components(
        db: Session, material_code: str, cost_date: datetime, created_by: Optional[str]
    ) -> None:
        bom = get_bom(db, material_code, cost_date)
        if bom is None:
            return
        for item in bom_components(db, bom):
            child = get_material(db, item.material_code)
            if child is None:
                continue
            CostEngine._compute_standard(db, child, "1", cost_date, created_by)

    @staticmethod
    def _compute_standard(
        db: Session,
        material: Material,
        version: str,
        cost_date: datetime,
        created_by: Optional[str],
    ) -> StandardCost:
        row = (
            db.query(StandardCost)
            .filter(
                StandardCost.material_code == material.material_code,
                StandardCost.version == version,
                StandardCost.is_deleted == False,
            )
            .first()
        )
        if row is None:
            row = StandardCost(
                cost_id=NumberGenerator.generate_document_number(
                    db, StandardCost, "cost_id", "STD", 4
                ),
                material_code=material.material_code,
                version=version,
                created_by=created_by,
            )
            db.add(row)

        # ── material content from BOM ────────────────────────────────
        material_cost = ZERO
        labor_cost = ZERO
        overhead_cost = ZERO

        bom = get_bom(db, material.material_code, cost_date)
        if bom is not None:
            base_qty = dec(bom.base_quantity) or Decimal("1")
            for item in bom_components(db, bom):
                child = get_material(db, item.material_code)
                if child is None:
                    continue
                qty = dec(item.quantity) / base_qty * (
                    Decimal("1") + dec(item.scrap_rate) / Decimal("100")
                )
                child_cost = CostEngine._child_standard(db, child.material_code)
                material_cost += qty * child_cost
            # Raw / buy material without a BOM: value at its own standard price.
        elif material.material_type in ("RAW", "PACKAGING") or dec(material.standard_price) > ZERO:
            material_cost = dec(material.standard_price)

        # ── routing labour + machine + overhead ──────────────────────
        routing = get_routing(db, material.material_code, cost_date)
        if routing is not None:
            for op in routing_operations(db, routing):
                l_cost, m_cost, o_cost = CostEngine._operation_standard(db, op)
                labor_cost += l_cost
                overhead_cost += m_cost + o_cost

        # fallback: buy material valued by its standard price
        if material_cost <= ZERO and material.material_type in ("RAW", "PACKAGING"):
            material_cost = dec(material.standard_price)

        row.material_cost = _q(material_cost)
        row.labor_cost = _q(labor_cost)
        row.overhead_cost = _q(overhead_cost)
        row.total_cost = _q(material_cost + labor_cost + overhead_cost)
        row.unit_cost = row.total_cost  # total per 1 base quantity
        row.currency = CURRENCY
        row.cost_date = cost_date
        row.rolled_up_at = datetime.now()
        row.cost_method = "STANDARD"
        row.status = "ACTIVE"
        row.updated_by = created_by
        db.flush()
        return row

    @staticmethod
    def _child_standard(db: Session, material_code: str) -> Decimal:
        row = (
            db.query(StandardCost)
            .filter(
                StandardCost.material_code == material_code,
                StandardCost.is_deleted == False,
            )
            .order_by(StandardCost.id.desc())
            .first()
        )
        if row is not None:
            return dec(row.total_cost)
        material = get_material(db, material_code)
        return dec(material.standard_price) if material else ZERO

    @staticmethod
    def _operation_standard(
        db: Session, op: RoutingOperation
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Return (labor, machine, overhead) standard per base quantity for an op."""
        minutes = dec(op.setup_time) + dec(op.machine_time) + dec(op.labor_time)
        hours = minutes / Decimal("60")
        labor = ZERO
        machine = ZERO
        overhead = ZERO
        rates = (
            db.query(CostRate)
            .filter(
                CostRate.work_center_id == op.work_center_id,
                CostRate.is_deleted == False,
                CostRate.status == "ACTIVE",
            )
            .all()
        )
        rate_map = {str(r.rate_type.value if hasattr(r.rate_type, "value") else r.rate_type): dec(r.rate_per_hour) for r in rates}
        labor = hours * rate_map.get(CostRateType.LABOR.value, ZERO)
        machine = hours * rate_map.get(CostRateType.MACHINE.value, ZERO)
        overhead = hours * rate_map.get(CostRateType.OVERHEAD.value, ZERO)
        return _q(labor), _q(machine), _q(overhead)

    # ── Actual production cost collection ────────────────────────────
    @staticmethod
    def collect_production_cost(
        db: Session,
        order_number: str,
        *,
        created_by: Optional[str] = None,
    ) -> ProductionCost:
        order = (
            db.query(ProductionOrder)
            .filter(
                ProductionOrder.order_number == order_number,
                ProductionOrder.is_deleted == False,
            )
            .first()
        )
        if order is None:
            raise ValueError(f"生产订单不存在: {order_number}")

        row = (
            db.query(ProductionCost)
            .filter(ProductionCost.production_order_number == order_number)
            .first()
        )
        if row is None:
            row = ProductionCost(
                cost_id=NumberGenerator.generate_document_number(
                    db, ProductionCost, "cost_id", "PRC", 4
                ),
                production_order_number=order_number,
                material_code=order.material_code,
                quantity=dec(order.quantity),
                created_by=created_by,
            )
            db.add(row)

        qty = dec(order.quantity) or Decimal("1")

        # ── actual material: issues valued at standard price ─────────
        material_cost_actual = ZERO
        issues = (
            db.query(MaterialIssue)
            .filter(
                MaterialIssue.production_order_number == order_number,
                MaterialIssue.is_deleted == False,
            )
            .all()
        )
        for issue in issues:
            mat = get_material(db, issue.material_code)
            unit_cost = dec(mat.standard_price) if mat else ZERO
            material_cost_actual += dec(issue.quantity) * unit_cost

        # ── actual labour / machine / overhead from operation reports ─
        labor_actual = ZERO
        overhead_actual = ZERO
        reports = (
            db.query(OperationReport)
            .filter(
                OperationReport.production_order_number == order_number,
                OperationReport.is_deleted == False,
            )
            .all()
        )
        for report in reports:
            l_cost, m_cost, o_cost = CostEngine._report_actual(db, report)
            labor_actual += l_cost
            overhead_actual += m_cost + o_cost

        total_actual = material_cost_actual + labor_actual + overhead_actual

        std = CostEngine._child_standard(db, order.material_code)
        standard_cost = _q(std * qty)

        row.material_cost_actual = _q(material_cost_actual)
        row.labor_cost_actual = _q(labor_actual)
        row.overhead_actual = _q(overhead_actual)
        row.total_actual = _q(total_actual)
        row.standard_cost = standard_cost
        row.wip_value = _q(total_actual)  # WIP = accumulated actual before settlement
        row.status = CostStatus.COLLECTED
        row.collected_at = datetime.now()
        row.updated_by = created_by
        db.flush()
        return row

    @staticmethod
    def _report_actual(
        db: Session, report: OperationReport
    ) -> tuple[Decimal, Decimal, Decimal]:
        hours = (
            dec(report.setup_time) + dec(report.machine_time) + dec(report.labor_time)
        ) / Decimal("60")
        rates = (
            db.query(CostRate)
            .filter(
                CostRate.work_center_id == report.work_center_id,
                CostRate.is_deleted == False,
                CostRate.status == "ACTIVE",
            )
            .all()
        )
        rate_map = {
            str(r.rate_type.value if hasattr(r.rate_type, "value") else r.rate_type): dec(
                r.rate_per_hour
            )
            for r in rates
        }
        labor = hours * rate_map.get(CostRateType.LABOR.value, ZERO)
        machine = hours * rate_map.get(CostRateType.MACHINE.value, ZERO)
        overhead = hours * rate_map.get(CostRateType.OVERHEAD.value, ZERO)
        return _q(labor), _q(machine), _q(overhead)

    # ── Variance analysis ─────────────────────────────────────────────
    @staticmethod
    def analyze_variances(
        db: Session,
        order_number: str,
        *,
        created_by: Optional[str] = None,
    ) -> list[CostVariance]:
        prod = CostEngine.collect_production_cost(db, order_number, created_by=created_by)
        db.flush()
        std = CostEngine._child_standard(db, prod.material_code)
        qty = dec(prod.quantity) or Decimal("1")

        entries = [
            (
                VarianceType.MATERIAL_PRICE,
                prod.standard_cost,
                prod.material_cost_actual,
            ),
            (
                VarianceType.MATERIAL_USAGE,
                prod.standard_cost,
                prod.material_cost_actual,
            ),
            (VarianceType.LABOR_RATE, prod.standard_cost, prod.labor_cost_actual),
            (
                VarianceType.LABOR_EFFICIENCY,
                prod.standard_cost,
                prod.labor_cost_actual,
            ),
            (VarianceType.OVERHEAD, prod.standard_cost, prod.overhead_actual),
        ]

        db.query(CostVariance).filter(
            CostVariance.production_order_number == order_number,
            CostVariance.is_deleted == False,
        ).delete(synchronize_session=False)
        db.flush()

        result: list[CostVariance] = []
        for idx, (vtype, standard_amount, actual_amount) in enumerate(entries):
            standard_amount = _q(standard_amount)
            actual_amount = _q(actual_amount)
            variance_amount = _q(actual_amount - standard_amount)
            pct = ZERO
            if standard_amount != ZERO:
                pct = (variance_amount / standard_amount * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            row = CostVariance(
                variance_number=NumberGenerator.generate_document_number(
                    db, CostVariance, "variance_number", "VAR", 4
                )
                + f"-{idx + 1}",
                production_order_number=order_number,
                variance_type=vtype,
                standard_amount=standard_amount,
                actual_amount=actual_amount,
                variance_amount=variance_amount,
                variance_pct=pct,
                analyzed_at=datetime.now(),
                remarks=f"{vtype.value} 差异分析（标准 {standard_amount} / 实际 {actual_amount}）",
                created_by=created_by,
            )
            db.add(row)
            result.append(row)
        db.flush()
        return result

    # ── Settlement ────────────────────────────────────────────────────
    @staticmethod
    def settle(
        db: Session,
        order_number: str,
        *,
        created_by: Optional[str] = None,
    ) -> CostSettlement:
        prod = CostEngine.collect_production_cost(db, order_number, created_by=created_by)
        db.flush()
        settlement = (
            db.query(CostSettlement)
            .filter(CostSettlement.production_order_number == order_number)
            .first()
        )
        if settlement is None:
            settlement = CostSettlement(
                settlement_number=NumberGenerator.generate_document_number(
                    db, CostSettlement, "settlement_number", "STL", 4
                ),
                production_order_number=order_number,
                created_by=created_by,
            )
            db.add(settlement)
        settlement.total_cost = _q(prod.total_actual)
        settlement.wip_value = _q(prod.wip_value)
        settlement.settlement_status = CostStatus.SETTLED
        settlement.settled_at = datetime.now()
        settlement.updated_by = created_by

        prod.status = CostStatus.SETTLED
        prod.settled_at = settlement.settled_at
        db.flush()
        return settlement

    # ── Cost rates CRUD ───────────────────────────────────────────────
    @staticmethod
    def upsert_rate(
        db: Session,
        work_center_id: str,
        rate_type: str,
        rate_per_hour: Decimal,
        *,
        created_by: Optional[str] = None,
    ) -> CostRate:
        row = (
            db.query(CostRate)
            .filter(
                CostRate.work_center_id == work_center_id,
                CostRate.rate_type == rate_type,
                CostRate.is_deleted == False,
            )
            .first()
        )
        if row is None:
            row = CostRate(
                rate_id=NumberGenerator.generate_document_number(
                    db, CostRate, "rate_id", "CR", 4
                ),
                work_center_id=work_center_id,
                rate_type=rate_type,
                created_by=created_by,
            )
            db.add(row)
        row.rate_per_hour = rate_per_hour
        row.status = "ACTIVE"
        row.updated_by = created_by
        db.flush()
        return row