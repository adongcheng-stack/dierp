"""增量升级脚本：创建计划/成本域数据表并写入演示基础参数。

可重复执行：create_all 只创建缺失的表，种子数据按业务主键幂等判断。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

if sys.platform == "win32":
    import io

    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session  # noqa: E402

from backend.common.database.base import Base, SessionLocal, engine  # noqa: E402
from backend.common.models import eng, mm, pp, sd, user  # noqa: E402
from backend.common.models.eng import BOM, BOMItem, BOMStatus  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    ChangeoverMatrix,
    CostRate,
    CostRateType,
    EquipmentFailure,
    FailureSeverity,
    FailureStatus,
    Forecast,
    InspectionOrder,
    InspectionResult,
    InspectionStatus,
    InspectionType,
    KittingResult,
    MaintenanceOrder,
    MaintenancePlan,
    MaintenanceStatus,
    MaintenanceType,
    NcrDisposition,
    NcrSeverity,
    NcrSourceType,
    NcrStatus,
    NonConformanceReport,
    PlanningPolicy,
    ProcurementType,
    PurchaseOrder,
    PurchaseOrderLine,
    Resource,
    ResourceStatus,
    SkillMatrix,
    Supplier,
    WorkCalendar,
)
from backend.common.utils.number_generator import NumberGenerator  # noqa: E402
from backend.services.planning.common import ZERO, dec, material_unit  # noqa: E402
from backend.services.planning.qms_engine import QmsEngine  # noqa: E402


def create_tables() -> None:
    print("正在创建计划/成本域数据表 ...")
    Base.metadata.create_all(bind=engine)
    print("[OK] 数据表已就绪")


def seed_policies(db: Session) -> int:
    created = 0
    materials = (
        db.query(mm.Material)
        .filter(mm.Material.is_deleted == False)
        .order_by(mm.Material.material_code)
        .all()
    )
    for material in materials:
        exists = (
            db.query(PlanningPolicy)
            .filter(PlanningPolicy.material_code == material.material_code)
            .first()
        )
        if exists:
            continue
        procurement = material.procurement_type
        if material.material_type in ("RAW", "PACKAGING"):
            procurement = "BUY" if procurement != "SUB" else "SUB"
        procurement = procurement or "MAKE"
        db.add(
            PlanningPolicy(
                policy_id=NumberGenerator.generate_document_number(
                    db, PlanningPolicy, "policy_id", "PLP", 4
                ),
                material_code=material.material_code,
                mrp_type="MRP",
                procurement_type=procurement,
                lot_sizing_rule="LOT_FOR_LOT",
                fixed_lot_size=0,
                min_order_qty=material.min_order_quantity or 0,
                max_order_qty=material.max_lot_size,
                order_multiple=material.order_multiple or 1,
                lead_time_days=material.lead_time_days or 0,
                safety_time_days=0,
                safety_stock=material.safety_stock or 0,
                reorder_point=0,
                planner_code=material.mrp_controller,
                abc_class=material.abc_class,
                is_active=True,
                remarks="升级脚本按物料主数据自动生成",
                created_by="system",
            )
        )
        db.flush()
        created += 1
    return created


def fix_policy_procurement(db: Session) -> int:
    """原材料/包材默认按采购计划，避免生成无 BOM 的自制计划订单。"""
    updated = 0
    rows = (
        db.query(PlanningPolicy, mm.Material)
        .join(mm.Material, mm.Material.material_code == PlanningPolicy.material_code)
        .filter(PlanningPolicy.is_deleted == False)
        .all()
    )
    for policy, material in rows:
        if material.material_type in ("RAW", "PACKAGING") and policy.procurement_type != ProcurementType.BUY:
            policy.procurement_type = ProcurementType.BUY
            updated += 1
    return updated


def _released_bom(db: Session, material_code: str) -> BOM | None:
    return (
        db.query(BOM)
        .filter(
            BOM.parent_material_code == material_code,
            BOM.status == BOMStatus.RELEASED,
            BOM.is_deleted == False,
        )
        .first()
    )


def seed_boms(db: Session) -> int:
    """确保演示用的成品拥有已发布 BOM，MRP 才能展开组件需求。"""
    created = 0
    today = datetime.now()
    effective = today - timedelta(days=60)

    materials = {
        material.material_code: material
        for material in db.query(mm.Material).filter(mm.Material.is_deleted == False).all()
    }
    raw_codes = [code for code in ("RM-FR4-150", "RM-PP1080", "RM-CU-FOIL") if code in materials]

    recipes = {
        "HF1004ENIGAB01": [("RM-FR4-150", 1), ("RM-PP1080", 2), ("RM-CU-FOIL", 1)],
        "HF1004ENIGAB02": [("RM-FR4-150", 1), ("RM-PP1080", 2), ("RM-CU-FOIL", 1)],
        "HF1004ENIGAB03": [("RM-FR4-150", 1), ("RM-PP1080", 2), ("RM-CU-FOIL", 1)],
        "HF1004ENIGAB04": [("RM-FR4-150", 2), ("RM-PP1080", 3), ("RM-CU-FOIL", 2)],
    }

    for material_code, items in recipes.items():
        if material_code not in materials or _released_bom(db, material_code):
            continue
        bom_number = f"BOM-{material_code[-2:]}-R1"
        if db.query(BOM).filter(BOM.bom_number == bom_number).first():
            continue
        bom = BOM(
            bom_number=bom_number,
            version="R1",
            parent_material_code=material_code,
            plant_id="P01",
            bom_type="PRODUCTION",
            base_quantity=1,
            base_uom=materials[material_code].production_unit or "PNL",
            effective_date=effective,
            status=BOMStatus.RELEASED,
            description="计划模块演示 BOM（升级脚本生成）",
            created_by="system",
        )
        db.add(bom)
        db.flush()
        for line_number, (component_code, quantity) in enumerate(items, start=1):
            if component_code not in materials:
                continue
            material = materials[component_code]
            db.add(
                BOMItem(
                    bom_number=bom_number,
                    line_number=line_number,
                    material_code=component_code,
                    item_category="STOCK_ITEM",
                    quantity=quantity,
                    unit=material.base_unit or material.unit or "PCS",
                    scrap_rate=2 if component_code == "RM-CU-FOIL" else 0,
                    created_by="system",
                )
            )
        created += 1
    return created


def seed_work_calendars(db: Session) -> int:
    created = 0
    for index, work_center in enumerate(
        db.query(pp.WorkCenter).filter(pp.WorkCenter.is_deleted == False).all(), start=1
    ):
        exists = (
            db.query(WorkCalendar)
            .filter(WorkCalendar.work_center_id == work_center.work_center_id)
            .first()
        )
        if exists:
            continue
        db.add(
            WorkCalendar(
                calendar_id=f"CAL-{index:04d}",
                work_center_id=work_center.work_center_id,
                shift_start=work_center.shift_start_time or "08:00",
                shift_end=work_center.shift_finish_time or "20:00",
                break_hours=work_center.break_time or 1,
                capacity_hours=10,
                utilization=work_center.capacity_utilization or 100,
                workdays="1,2,3,4,5,6",
                status="ACTIVE",
                created_by="system",
            )
        )
        created += 1
    return created


def seed_cost_rates(db: Session) -> int:
    created = 0
    defaults = {
        CostRateType.LABOR: Decimal("85"),
        CostRateType.MACHINE: Decimal("120"),
        CostRateType.OVERHEAD: Decimal("45"),
    }
    for work_center in db.query(pp.WorkCenter).filter(pp.WorkCenter.is_deleted == False).all():
        for rate_type, rate in defaults.items():
            exists = (
                db.query(CostRate)
                .filter(
                    CostRate.work_center_id == work_center.work_center_id,
                    CostRate.rate_type == rate_type,
                )
                .first()
            )
            if exists:
                continue
            db.add(
                CostRate(
                    rate_id=NumberGenerator.generate_document_number(
                        db, CostRate, "rate_id", "CR", 4
                    ),
                    work_center_id=work_center.work_center_id,
                    rate_type=rate_type,
                    rate_per_hour=rate,
                    currency="CNY",
                    effective_from=datetime.now() - timedelta(days=90),
                    status="ACTIVE",
                    created_by="system",
                )
            )
            db.flush()
            created += 1
    return created


def seed_material_prices(db: Session) -> int:
    """为演示物料写入标准单价（人民币/单位），成本引擎需要价格才有非零结果。"""
    prices = {
        "RM-FR4-150": Decimal("38.50"),
        "RM-PP1080": Decimal("16.80"),
        "RM-CU-FOIL": Decimal("42.20"),
        "RM-DRY-FILM": Decimal("9.60"),
        "RM-SOLDER-MASK": Decimal("15.30"),
        "RM-ENIG-CHEM": Decimal("88.00"),
    }
    updated = 0
    for material in db.query(mm.Material).filter(mm.Material.is_deleted == False).all():
        if material.material_code in prices and (
            material.standard_price is None or material.standard_price == 0
        ):
            material.standard_price = prices[material.material_code]
            material.currency = "CNY"
            material.valuation_method = material.valuation_method or "STANDARD"
            material.last_cost_update = datetime.now()
            updated += 1
    return updated


def seed_forecasts(db: Session) -> int:
    if db.query(Forecast).filter(Forecast.is_deleted == False).count() > 0:
        return 0

    materials = (
        db.query(mm.Material)
        .filter(
            mm.Material.is_deleted == False,
            mm.Material.material_type.in_(["FG", "SEMI"]),
        )
        .order_by(mm.Material.material_code)
        .limit(4)
        .all()
    )
    created = 0
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for idx, material in enumerate(materials):
        for weeks_ahead, quantity in ((2, 60), (4, 40)):
            due = today + timedelta(days=7 * weeks_ahead)
            db.add(
                Forecast(
                    forecast_number=NumberGenerator.generate_document_number(
                        db, Forecast, "forecast_number", "FC", 4
                    ),
                    version="1",
                    material_code=material.material_code,
                    quantity=quantity + idx * 5,
                    unit=material_unit(material),
                    due_date=due,
                    bucket_type="WEEK",
                    status="RELEASED",
                    consumed_quantity=0,
                    remarks="计划模块演示预测",
                    created_by="system",
                )
            )
            db.flush()
            created += 1
    return created


def seed_aps_demo_data(db: Session) -> int:
    """APS 演示数据：为成品物料补发布工艺路线，并建立今天开工的演示工单（幂等）。"""
    from backend.common.models.pp import ProductionOrder, ProductionOrderStatus
    from backend.common.models.sd import SalesOrder, SalesOrderStatus

    created = 0
    base_routing = (
        db.query(eng.Routing)
        .filter(eng.Routing.status == eng.RoutingStatus.RELEASED, eng.Routing.is_deleted == False)
        .order_by(eng.Routing.id)
        .first()
    )
    if base_routing is None:
        return 0
    base_ops = (
        db.query(eng.RoutingOperation)
        .filter(eng.RoutingOperation.routing_id == base_routing.routing_id)
        .order_by(eng.RoutingOperation.operation_no)
        .all()
    )

    fg_materials = ["HF1004ENIGAB01", "HF1004ENIGAB02", "HF1004ENIGAB03", "HF1004ENIGAB04"]
    time_specs = {
        "HF1004ENIGAB01": (Decimal("15"), Decimal("150"), Decimal("30")),
        "HF1004ENIGAB02": (Decimal("10"), Decimal("120"), Decimal("25")),
        "HF1004ENIGAB03": (Decimal("20"), Decimal("200"), Decimal("35")),
        "HF1004ENIGAB04": (Decimal("25"), Decimal("240"), Decimal("40")),
    }

    routing_by_material: dict[str, str] = {}
    for index, material_code in enumerate(fg_materials, start=1):
        routing_id = f"RT-PCB-{index:04d}"
        routing_by_material[material_code] = routing_id
        exists = db.query(eng.Routing).filter(eng.Routing.routing_id == routing_id).first()
        if exists is None:
            routing = eng.Routing(
                routing_id=routing_id,
                version="A01",
                material_code=material_code,
                description=f"APS 演示工艺路线 {material_code}",
                plant_id=base_routing.plant_id,
                base_unit=base_routing.base_unit,
                base_quantity=base_routing.base_quantity,
                units_per_panel=base_routing.units_per_panel,
                effective_date=datetime.now() - timedelta(days=365),
                status=eng.RoutingStatus.RELEASED,
                created_by="system",
            )
            db.add(routing)
            db.flush()
            created += 1
            setup, machine, labor = time_specs.get(material_code, (Decimal("10"), Decimal("120"), Decimal("25")))
            for op_index, base_op in enumerate(base_ops):
                db.add(
                    eng.RoutingOperation(
                        routing_id=routing_id,
                        operation_no=base_op.operation_no,
                        operation_code=base_op.operation_code,
                        operation_name=base_op.operation_name,
                        operation_type=base_op.operation_type,
                        work_center_id=base_op.work_center_id,
                        setup_time=setup,
                        machine_time=machine if op_index == 0 else (machine * Decimal("0.6")).quantize(Decimal("0.01")),
                        labor_time=labor if op_index == 0 else (labor * Decimal("0.7")).quantize(Decimal("0.01")),
                        queue_time=base_op.queue_time,
                        cost_relevant=True,
                        scheduling_relevant=True,
                        needs_reporting=True,
                        created_by="system",
                    )
                )
            created += len(base_ops)

    # 演示工单：今天开工、7 天交期，关联一张已审批销售订单
    sales_order = (
        db.query(SalesOrder)
        .filter(SalesOrder.status == SalesOrderStatus.APPROVED, SalesOrder.is_deleted == False)
        .order_by(SalesOrder.id)
        .first()
    )
    if sales_order is None:
        return created

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for index, material_code in enumerate(fg_materials, start=1):
        order_number = f"PO-APS-{index:02d}"
        # PO-APS-04 为交期紧张工单：交期仅 1 天，排程必然超出 → 演示交期风险异常
        finish_days = 1 if index == 4 else 8
        exists = db.query(ProductionOrder).filter(ProductionOrder.order_number == order_number).first()
        if exists is not None:
            target_finish = today + timedelta(days=finish_days)
            if exists.planned_finish_date is None or exists.planned_finish_date > target_finish:
                exists.planned_finish_date = target_finish
            continue
        version = (
            db.query(eng.ProductionVersion)
            .filter(eng.ProductionVersion.material_code == material_code)
            .order_by(eng.ProductionVersion.id)
            .first()
        )
        # PO-APS-04 为交期紧张工单：交期仅 1 天，排程必然超出 → 演示交期风险异常
        db.add(
            ProductionOrder(
                order_number=order_number,
                sales_order_number=sales_order.order_number,
                material_code=material_code,
                production_version_id=version.production_version_id if version else None,
                quantity=Decimal("20"),
                unit="PCS",
                planned_start_date=today + timedelta(days=1),
                planned_finish_date=today + timedelta(days=finish_days),
                status=ProductionOrderStatus.RELEASED,
                remarks="APS 演示工单",
                sales_quantity=Decimal("20"),
                sales_unit="PCS",
                conversion_factor=Decimal("1"),
                created_by="system",
            )
        )
        created += 1
    return created


def seed_aps_kitting(db: Session) -> int:
    """为 APS 演示工单生成齐套快照（缺料工单 → 演示排程缺料异常）"""
    from backend.common.models.pp import ProductionOrder
    from backend.services.planning.kitting_service import KittingService

    created = 0
    for order_number in ("PO-APS-01", "PO-APS-04"):
        exists = (
            db.query(KittingResult)
            .filter(
                KittingResult.source_type == "PRODUCTION_ORDER",
                KittingResult.source_ref == order_number,
                KittingResult.is_deleted == False,
            )
            .first()
        )
        if exists is not None:
            continue
        order = (
            db.query(ProductionOrder)
            .filter(ProductionOrder.order_number == order_number)
            .first()
        )
        if order is None:
            continue
        KittingService.analyze_production_order(db, order_number, checked_by="system")
        created += 1
    return created


def fix_routing_operation_codes(db: Session) -> int:
    """按工序语义修正工序编码前缀，使能力码与资源技能码一致（幂等）。"""
    prefix_by_keyword = (
        ("蚀刻", "ETC"),
        ("钻孔", "DRL"),
        ("铣", "MIL"),
        ("测试", "TST"),
        ("AOI", "AOI"),
    )
    fixed = 0
    rows = (
        db.query(eng.RoutingOperation)
        .filter(eng.RoutingOperation.is_deleted == False)
        .all()
    )
    for row in rows:
        name = str(row.operation_name or "")
        code = str(row.operation_code or "").upper()
        prefix = code.split("-")[0][:3] if code else ""
        for keyword, target in prefix_by_keyword:
            if keyword in name and prefix != target:
                suffix = code.split("-")[1] if "-" in code else row.operation_no or "001"
                row.operation_code = f"{target}-{suffix}"
                fixed += 1
                break
    return fixed


def seed_aps_master_data(db: Session) -> int:
    """APS 主数据种子：设备资源 / 人员技能矩阵 / 换产矩阵（幂等）"""
    created = 0

    resource_specs = [
        ("RES-DRILL-A-01", "CNC钻孔机 A1", "DRILL-A", "MACHINE", "DRL,PCB"),
        ("RES-DRILL-A-02", "CNC钻孔机 A2", "DRILL-A", "MACHINE", "DRL,PCB"),
        ("RES-DRILL-B-01", "内层蚀刻线 B1", "DRILL-B", "MACHINE", "ETC,AOI"),
        ("RES-DRILL-C-01", "外形铣床 C1", "DRILL-C", "MACHINE", "MIL"),
        ("RES-DRILL-D-01", "测试台 D1", "DRILL-D", "MACHINE", "TST"),
        ("RES-OPR-001", "主操机员 · 张工", "DRILL-A", "LABOR", "SETUP,DRL"),
    ]
    for resource_id, resource_name, work_center_id, resource_type, tags in resource_specs:
        exists = db.query(Resource).filter(Resource.resource_id == resource_id).first()
        if exists:
            if exists.skill_tags != tags:
                exists.skill_tags = tags
            continue
        db.add(
            Resource(
                resource_id=resource_id,
                resource_name=resource_name,
                work_center_id=work_center_id,
                resource_type=resource_type,
                capacity_per_shift=Decimal("11"),
                shift_start="08:00",
                shift_end="20:00",
                workdays="1,2,3,4,5,6",
                status=ResourceStatus.ACTIVE,
                skill_tags=tags,
                created_by="system",
            )
        )
        created += 1

    skill_specs = [
        ("SK-001", "RES-OPR-001", "SETUP", "换线与调机", Decimal("1.00")),
        ("SK-002", "RES-OPR-001", "DRL", "钻孔编程与操作", Decimal("0.80")),
        ("SK-003", "RES-DRILL-B-01", "AOI", "AOI 缺陷判读", Decimal("0.90")),
        ("SK-004", "RES-DRILL-D-01", "TST", "电测试", Decimal("1.00")),
    ]
    for skill_id, resource_id, skill_code, skill_name, proficiency in skill_specs:
        exists = db.query(SkillMatrix).filter(SkillMatrix.skill_id == skill_id).first()
        if exists:
            if exists.skill_code != skill_code:
                exists.skill_code = skill_code
            continue
        db.add(
            SkillMatrix(
                skill_id=skill_id,
                resource_id=resource_id,
                skill_code=skill_code,
                skill_name=skill_name,
                proficiency=proficiency,
                status="ACTIVE",
                created_by="system",
            )
        )
        created += 1

    changeover_specs = [
        ("CO-001", "DRILL-A", "0010", "0020", Decimal("45")),
        ("CO-002", "DRILL-A", "0010", "0010", Decimal("20")),
        ("CO-003", "DRILL-B", "0011", "0011", Decimal("25")),
        ("CO-004", "DRILL-B", "0011", "0021", Decimal("40")),
    ]
    for changeover_id, work_center_id, from_op, to_op, minutes in changeover_specs:
        exists = db.query(ChangeoverMatrix).filter(ChangeoverMatrix.changeover_id == changeover_id).first()
        if exists:
            continue
        db.add(
            ChangeoverMatrix(
                changeover_id=changeover_id,
                work_center_id=work_center_id,
                from_operation=from_op,
                to_operation=to_op,
                changeover_minutes=minutes,
                status="ACTIVE",
                created_by="system",
            )
        )
        created += 1

    return created


def seed_eam_demo_data(db: Session) -> int:
    """EAM 演示数据：6 条维护计划 + 2 条已完工保养单 + 1 条 OPEN 故障（幂等）。

    RES-DRILL-B-01 置为 MAINTENANCE 且带 OPEN 故障，用于演示：
    - APS 排程 RESOURCE_DOWN 异常联动；
    - OEE 可用率因故障停机下降。
    """
    created = 0
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 1) 设备资源置为保养状态（演示 APS 联动） ─────────────────────
    drill_b = db.query(Resource).filter(Resource.resource_id == "RES-DRILL-B-01").first()
    if drill_b is not None and drill_b.status != ResourceStatus.MAINTENANCE:
        drill_b.status = ResourceStatus.MAINTENANCE
        drill_b.notes = "EAM 演示：内层蚀刻线保养中，APS 排程将产生 RESOURCE_DOWN 异常"
        created += 1

    # ── 2) 6 条维护计划（覆盖全部 APS 演示资源，周期/类型各异） ────────
    plan_specs = [
        # (plan_key, resource_id, type, cycle_days, last_offset_days, due_offset_days, responsible)
        ("MP-DRILL-A1-DAILY", "RES-DRILL-A-01", MaintenanceType.INSPECTION, 7, -7, -1, "王保全"),
        ("MP-DRILL-A2-WEEKLY", "RES-DRILL-A-02", MaintenanceType.LUBRICANT, 14, -14, 3, "王保全"),
        ("MP-DRILL-B1-REPAIR", "RES-DRILL-B-01", MaintenanceType.REPAIR, 30, -20, -2, "李设备"),
        ("MP-DRILL-C1-MONTHLY", "RES-DRILL-C-01", MaintenanceType.OVERHAUL, 30, -30, 10, "李设备"),
        ("MP-DRILL-D1-WEEKLY", "RES-DRILL-D-01", MaintenanceType.INSPECTION, 7, -3, 4, "赵测试"),
        ("MP-OPR-001-MONTHLY", "RES-OPR-001", MaintenanceType.INSPECTION, 30, -15, 15, "张工"),
    ]
    for plan_key, resource_id, m_type, cycle_days, last_offset, due_offset, responsible in plan_specs:
        exists = db.query(MaintenancePlan).filter(MaintenancePlan.plan_id == plan_key).first()
        if exists is not None:
            continue
        db.add(
            MaintenancePlan(
                plan_id=plan_key,
                resource_id=resource_id,
                maintenance_type=m_type,
                cycle_days=cycle_days,
                last_executed_at=today + timedelta(days=last_offset) if last_offset else None,
                next_due_at=today + timedelta(days=due_offset),
                responsible=responsible,
                status=MaintenanceStatus.PLANNED,
                notes="EAM 演示维护计划（升级脚本生成）",
                created_by="system",
            )
        )
        db.flush()  # 先落库计划，维护工单外键依赖 plan_id
        created += 1

    # ── 3) 2 条已完工保养单（回写计划执行时间） ────────────────────────
    done_specs = [
        (
            "MP-DRILL-A1-DAILY",
            "RES-DRILL-A-01",
            MaintenanceType.INSPECTION,
            today - timedelta(days=7),
            Decimal("1.0"),
            "日点检完成：气压/导轨润滑/主轴异响均正常",
        ),
        (
            "MP-DRILL-C1-MONTHLY",
            "RES-DRILL-C-01",
            MaintenanceType.OVERHAUL,
            today - timedelta(days=30),
            Decimal("4.5"),
            "月度大保养完成：更换铣刀夹具并校准行程",
        ),
    ]
    for plan_key, resource_id, m_type, done_at, downtime, note in done_specs:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.plan_id == plan_key).first()
        exists = (
            db.query(MaintenanceOrder)
            .filter(
                MaintenanceOrder.plan_id == plan_key,
                MaintenanceOrder.status == MaintenanceStatus.DONE,
                MaintenanceOrder.is_deleted == False,
            )
            .first()
        )
        if exists is not None:
            continue
        db.add(
            MaintenanceOrder(
                order_number=NumberGenerator.generate_document_number(
                    db, MaintenanceOrder, "order_number", "MO", 4
                ),
                resource_id=resource_id,
                plan_id=plan_key,
                maintenance_type=m_type,
                planned_date=done_at,
                completed_at=done_at,
                downtime_hours=downtime,
                executed_by="system",
                result_note=note,
                status=MaintenanceStatus.DONE,
                created_by="system",
            )
        )
        db.flush()  # 立即落库，确保下一次编号生成能查询到已有记录
        if plan is not None and (plan.last_executed_at is None or plan.last_executed_at < done_at):
            plan.last_executed_at = done_at
        created += 1

    # ── 4) 1 条 OPEN 故障（RES-DRILL-B-01，昨天发生） ──────────────────
    exists_failure = (
        db.query(EquipmentFailure)
        .filter(
            EquipmentFailure.resource_id == "RES-DRILL-B-01",
            EquipmentFailure.status == FailureStatus.OPEN,
            EquipmentFailure.is_deleted == False,
        )
        .first()
    )
    if exists_failure is None and drill_b is not None:
        db.add(
            EquipmentFailure(
                failure_number=NumberGenerator.generate_document_number(
                    db, EquipmentFailure, "failure_number", "EF", 4
                ),
                resource_id="RES-DRILL-B-01",
                work_center_id=drill_b.work_center_id,
                occurred_at=today - timedelta(days=1),
                severity=FailureSeverity.HIGH,
                description="蚀刻线传送段电机异响，喷淋压力波动，待更换传动皮带",
                downtime_hours=Decimal("2.5"),
                status=FailureStatus.OPEN,
                reported_by="system",
                created_by="system",
            )
        )
        db.flush()  # 立即落库，确保编号唯一
        created += 1

    return created


def seed_operation_report_routing(db: Session) -> int:
    """补齐演示报工与工艺路线工序的关联及实际工时。

    背景：EAM 的 OEE 性能率 = 标准工时 / 实际工时，需要报工同时具备
    `routing_operation_id`（标准工时来源）与 machine_time/labor_time（实际工时）。
    早期 MVP 的 RT-PCB-1001 工序工时为空、报工也缺工艺关联，导致性能率恒为 1。

    幂等：工序工时与报工字段均写入固定演示值，可重复执行。
    """
    # 1) RT-PCB-1001 两条工序的工时（与前端快照保持一致）
    routing = (
        db.query(eng.Routing)
        .filter(eng.Routing.routing_id == "RT-PCB-1001")
        .first()
    )
    fixed_ops = 0
    op_map: dict[str, eng.RoutingOperation] = {}
    if routing is not None:
        fixtures = {
            "0010": (Decimal("10"), Decimal("120"), Decimal("25")),
            "0011": (Decimal("10"), Decimal("70"), Decimal("18")),
        }
        for op in db.query(eng.RoutingOperation).filter(
            eng.RoutingOperation.routing_id == routing.routing_id
        ):
            op_map[op.operation_no] = op
            if op.operation_no in fixtures:
                setup, machine, labor = fixtures[op.operation_no]
                if (dec(op.setup_time), dec(op.machine_time), dec(op.labor_time)) != (
                    setup,
                    machine,
                    labor,
                ):
                    op.setup_time = setup
                    op.machine_time = machine
                    op.labor_time = labor
                    fixed_ops += 1
        db.flush()

    # 2) 六条演示报工：关联工艺工序 + 良品数 + 实际工时
    report_fixtures = {
        "OR-20251217-0001": ("0010", Decimal("15"), Decimal("90"), Decimal("30"), Decimal("2")),
        "OR-20251217-0001-9390": ("0011", Decimal("20"), Decimal("110"), Decimal("40"), Decimal("2")),
        "OR-20251218-0001": ("0010", Decimal("12"), Decimal("70"), Decimal("25"), Decimal("20")),
        "OR-20251218-0001-6025": ("0011", Decimal("15"), Decimal("90"), Decimal("30"), Decimal("20")),
        "OR-20251230-0001": ("0010", Decimal("20"), Decimal("110"), Decimal("40"), Decimal("1")),
        "OR-20251230-0001-1313": ("0011", Decimal("12"), Decimal("70"), Decimal("25"), Decimal("7")),
    }
    updated = 0
    for report_number, (op_no, setup, machine, labor, good) in report_fixtures.items():
        report = (
            db.query(pp.OperationReport)
            .filter(pp.OperationReport.report_number == report_number)
            .first()
        )
        if report is None:
            continue
        op = op_map.get(op_no)
        changed = False
        if op is not None and report.routing_operation_id != op.id:
            report.routing_operation_id = op.id
            changed = True
        if dec(report.good_quantity) != good:
            report.good_quantity = good
            changed = True
        if (dec(report.setup_time), dec(report.machine_time), dec(report.labor_time)) != (
            setup,
            machine,
            labor,
        ):
            report.setup_time = setup
            report.machine_time = machine
            report.labor_time = labor
            changed = True
        if changed:
            updated += 1

    return fixed_ops + updated


def seed_qms_demo_data(db: Session) -> int:
    """QMS 演示数据：三环节检验单 + 不合格品（NCR）闭环，含双向联动（幂等）。

    生成内容：
    - 来料检验 PASS（HF1004ENIGAB01）
    - 过程检验 FAIL（对 LOT-20251230-0003），完成时自动生成一张来源为本检验单的 NCR；
    - 终检 PASS（HF1004ENIGAB01）；
    - 一张 scrap>0 报工单（PO-APS-02 首工序，报废 12 PCS），供前端「由报工生成 NCR」下拉；
    - 一条 OPEN 的 NCR：来源为 LOT_CARD、评审判定为设备原因（equipment_cause=True），
      自动联动 EAM 生成一条 OPEN 故障（RES-DRILL-B-01），并回写 NCR.failure_number。

    幂等：均按业务主键判断存在则跳过，可重复执行。
    """
    created = 0
    today = datetime.now()

    # ── 1) 来料检验 PASS ────────────────────────────────────────────────
    mat_incoming = db.query(mm.Material).filter(mm.Material.material_code == "HF1004ENIGAB01").first()
    if mat_incoming is None:
        return 0  # 依赖的演示物料不存在，跳过
    existing_iqc = (
        db.query(InspectionOrder)
        .filter(
            InspectionOrder.inspection_type == InspectionType.INCOMING,
            InspectionOrder.result == InspectionResult.PASS,
            InspectionOrder.is_deleted == False,
        )
        .first()
    )
    if existing_iqc is None:
        iqc = QmsEngine.create_inspection(
            db,
            inspection_type=InspectionType.INCOMING,
            material_code="HF1004ENIGAB01",
            quantity_inspected=Decimal("300"),
            inspector="李质检",
            inspected_at=today,
            remarks="QMS 演示：来料检验 PASS",
            created_by="system",
        )
        QmsEngine.complete_inspection(
            db,
            iqc.inspection_number,
            quantity_ok=Decimal("300"),
            quantity_rejected=Decimal("0"),
            inspector="李质检",
            result=InspectionResult.PASS,
            remarks="QMS 演示：来料检验 PASS",
            auto_create_ncr=False,
            updated_by="system",
        )
        created += 1

    # ── 2) 过程检验 FAIL → 自动 NCR ─────────────────────────────────────
    existing_ipqc = (
        db.query(InspectionOrder)
        .filter(
            InspectionOrder.inspection_type == InspectionType.IN_PROCESS,
            InspectionOrder.result == InspectionResult.FAIL,
            InspectionOrder.is_deleted == False,
        )
        .first()
    )
    if existing_ipqc is None:
        ipqc = QmsEngine.create_inspection(
            db,
            inspection_type=InspectionType.IN_PROCESS,
            material_code="HF1004ENIGAB02",
            lot_number="LOT-20251230-0003",
            quantity_inspected=Decimal("200"),
            inspector="王质检",
            inspected_at=today,
            remarks="QMS 演示：过程检验 FAIL，触发不合格品闭环",
            created_by="system",
        )
        QmsEngine.complete_inspection(
            db,
            ipqc.inspection_number,
            quantity_ok=Decimal("188"),
            quantity_rejected=Decimal("12"),
            inspector="王质检",
            result=InspectionResult.FAIL,
            remarks="蚀刻线宽偏移 12 PCS 不合格",
            auto_create_ncr=True,
            updated_by="system",
        )
        # 过程检验自动开立的 NCR 立即走完闭环，作为「已关闭」演示样本
        auto_ncr = (
            db.query(NonConformanceReport)
            .filter(
                NonConformanceReport.source_type == NcrSourceType.INSPECTION,
                NonConformanceReport.status == NcrStatus.OPEN,
                NonConformanceReport.is_deleted == False,
            )
            .order_by(NonConformanceReport.id.desc())
            .first()
        )
        if auto_ncr is not None:
            QmsEngine.disposition_ncr(
                db,
                auto_ncr.ncr_number,
                disposition=NcrDisposition.REWORK,
                disposition_note="蚀刻参数复核后返工重做",
                dispositioned_by="system",
            )
            QmsEngine.close_ncr(
                db,
                auto_ncr.ncr_number,
                disposition_note="返工后复检合格，关闭",
                closed_by="system",
            )
        created += 1

    # ── 3) 终检 PASS ────────────────────────────────────────────────────
    existing_fqc = (
        db.query(InspectionOrder)
        .filter(
            InspectionOrder.inspection_type == InspectionType.FINAL,
            InspectionOrder.result == InspectionResult.PASS,
            InspectionOrder.is_deleted == False,
        )
        .first()
    )
    if existing_fqc is None:
        fqc = QmsEngine.create_inspection(
            db,
            inspection_type=InspectionType.FINAL,
            material_code="HF1004ENIGAB01",
            lot_number="LOT-20251230-0001",
            quantity_inspected=Decimal("188"),
            inspector="赵终检",
            inspected_at=today,
            remarks="QMS 演示：终检 PASS",
            created_by="system",
        )
        QmsEngine.complete_inspection(
            db,
            fqc.inspection_number,
            quantity_ok=Decimal("188"),
            quantity_rejected=Decimal("0"),
            inspector="赵终检",
            result=InspectionResult.PASS,
            remarks="QMS 演示：终检 PASS",
            auto_create_ncr=False,
            updated_by="system",
        )
        created += 1

    # ── 4) 一张 scrap>0 报工单（供「由报工生成 NCR」演示） ──────────────
    report_fixture = (
        db.query(pp.OperationReport)
        .filter(
            pp.OperationReport.report_number == "OR-QMS-2026-REPORT-0001",
            pp.OperationReport.is_deleted == False,
        )
        .first()
    )
    if report_fixture is None:
        po_aps2 = (
            db.query(pp.ProductionOrder)
            .filter(pp.ProductionOrder.order_number == "PO-APS-02")
            .first()
        )
        if po_aps2 is not None:
            report_fixture = pp.OperationReport(
                report_number="OR-QMS-2026-REPORT-0001",
                production_order_number="PO-APS-02",
                lot_number="LOT-20251230-0002",
                work_center_id="DRILL-A",
                operation_no="0010",
                operation_name="钻孔",
                reported_quantity=Decimal("112"),
                good_quantity=Decimal("100"),
                scrap_quantity=Decimal("12"),
                setup_time=Decimal("10"),
                machine_time=Decimal("120"),
                labor_time=Decimal("25"),
                status=pp.OperationReportStatus.COMPLETED,
                reported_by="system",
                reported_at=today,
                remarks="QMS 演示：带报废的报工单",
                created_by="system",
            )
            db.add(report_fixture)
            db.flush()
            created += 1

    # ── 5) 设备原因 NCR（LOT_CARD 来源）→ 联动 EAM 故障 ─────────────────
    existing_device_ncr = (
        db.query(NonConformanceReport)
        .filter(
            NonConformanceReport.source_type == NcrSourceType.LOT_CARD,
            NonConformanceReport.equipment_cause == True,
            NonConformanceReport.is_deleted == False,
        )
        .first()
    )
    if existing_device_ncr is None:
        device_ncr = QmsEngine.create_ncr(
            db,
            source_type=NcrSourceType.LOT_CARD,
            source_ref="LOT-20251230-0003",
            lot_number="LOT-20251230-0003",
            material_code="HF1004ENIGAB02",
            quantity=Decimal("12"),
            defect_code="DRILL-OFFSET",
            defect_desc="钻孔位置偏移，判定为设备原因",
            severity=NcrSeverity.MAJOR,
            created_by="system",
        )
        QmsEngine.review_ncr(
            db,
            device_ncr.ncr_number,
            severity=NcrSeverity.MAJOR,
            root_cause="钻轴轴向间隙过大导致定位偏移",
            equipment_cause=True,
            resource_id="RES-DRILL-B-01",
            failure_desc="QMS 联动：钻孔定位偏移，疑似主轴间隙",
            reviewed_by="system",
        )
        created += 1

    db.flush()
    return created


def seed_purchase_demo_data(db: Session) -> int:
    """N3 采购闭环演示数据：两张 RELEASED 采购单（幂等）。

    - PUR-…：RM-FR4-150 ×100（单行）——演示「整单到货」；
    - PUR-…：RM-PP1080 ×200 + RM-CU-FOIL ×50（两行）——演示「分批到货 / 部分收货」。
    收货动作不在种子里做（留给演示现场），库存回冲由到货端点实时完成。
    """
    from backend.common.models.planning import (
        PurchaseOrder,
        PurchaseOrderLine,
        PurchaseOrderStatus,
    )

    created = 0
    today = datetime.now()

    def _has_demo_order(marker: str) -> bool:
        """按演示备注标记判重。

        不能用「物料出现过」判重：MRP release 自动生成的采购单可能恰好含同一物料，
        会导致演示单被静默跳过。
        """
        return (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.remarks.like(f"%{marker}%"),
                PurchaseOrder.is_deleted == False,  # noqa: E712
            )
            .first()
            is not None
        )

    def _next_number() -> str:
        return NumberGenerator.generate_document_number(
            db, PurchaseOrder, "purchase_order_number", "PUR", 4
        )

    # ── 1) FR-4 覆铜板 100 张 ────────────────────────────────────────────
    if not _has_demo_order("采购闭环演示：整单到货"):
        number = _next_number()
        db.add(
            PurchaseOrder(
                purchase_order_number=number,
                supplier_id="SUP-HQ",
                supplier_name="华强覆铜板贸易",
                status=PurchaseOrderStatus.RELEASED,
                order_date=today,
                expected_date=today + timedelta(days=5),
                currency="CNY",
                total_amount=Decimal("3850.00"),
                remarks="N3 采购闭环演示：整单到货（RM-FR4-150 ×100）",
                created_by="system",
            )
        )
        db.flush()
        db.add(
            PurchaseOrderLine(
                purchase_order_number=number,
                line_number=1,
                material_code="RM-FR4-150",
                quantity=Decimal("100"),
                received_quantity=Decimal("0"),
                unit="张",
                unit_price=Decimal("38.50"),
                expected_date=today + timedelta(days=5),
                status="OPEN",
                created_by="system",
            )
        )
        created += 1

    # ── 2) 半固化片 + 铜箔 两行 ─────────────────────────────────────────
    if not _has_demo_order("采购闭环演示：分批到货"):
        number = _next_number()
        db.add(
            PurchaseOrder(
                purchase_order_number=number,
                supplier_id="SUP-HQ",
                supplier_name="华强覆铜板贸易",
                status=PurchaseOrderStatus.RELEASED,
                order_date=today,
                expected_date=today + timedelta(days=7),
                currency="CNY",
                total_amount=Decimal("6700.00"),
                remarks="N3 采购闭环演示：分批到货（RM-PP1080 ×200 / RM-CU-FOIL ×50）",
                created_by="system",
            )
        )
        db.flush()
        db.add(
            PurchaseOrderLine(
                purchase_order_number=number,
                line_number=1,
                material_code="RM-PP1080",
                quantity=Decimal("200"),
                received_quantity=Decimal("0"),
                unit="张",
                unit_price=Decimal("12.00"),
                expected_date=today + timedelta(days=7),
                status="OPEN",
                created_by="system",
            )
        )
        db.add(
            PurchaseOrderLine(
                purchase_order_number=number,
                line_number=2,
                material_code="RM-CU-FOIL",
                quantity=Decimal("50"),
                received_quantity=Decimal("0"),
                unit="卷",
                unit_price=Decimal("86.00"),
                expected_date=today + timedelta(days=7),
                status="OPEN",
                created_by="system",
            )
        )
        created += 1

    db.flush()
    return created


def seed_sales_delivery_demo(db: Session) -> int:
    """销售发货/发票/应收演示种子（幂等，按固定单号判重）。

    三线自洽：SHIPPED 发货单在种子时同步扣成品库存并写 SALES_ISSUE 流水；
    已开票发票金额 = 已发货量×单价（恰好达可开票上限），并生成 AR 应收流水。
    """
    from backend.common.models.mm import Material, MaterialTransaction
    from backend.common.models.planning import (
        DeliveryStatus,
        InvoiceStatus,
        ReceivableEntry,
        ReceivableEntryType,
        SalesDelivery,
        SalesInvoice,
    )
    from backend.common.models.sd import SalesOrder

    created = 0
    order = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_number == "SO-20251231-0001", SalesOrder.is_deleted.is_(False))
        .first()
    )
    if order is None:
        return 0
    if db.query(SalesDelivery).filter(SalesDelivery.delivery_number == "DK-20251231-0001").first():
        return 0

    material = (
        db.query(Material).filter(Material.material_code == order.material_code).first()
    )
    unit_price = float(order.unit_price or 0)

    # ── 1) DRAFT 发货单（演示发货动作） ─────────────────────────────
    db.add(SalesDelivery(
        delivery_number="DK-20251231-0001",
        sales_order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=order.customer.legal_name if order.customer else None,
        material_code=order.material_code,
        quantity=Decimal("30"),
        unit=order.sales_unit or "PCS",
        unit_price=Decimal(str(unit_price)),
        status=DeliveryStatus.DRAFT,
        remarks="销售发货演示：待发货（DRAFT）",
        created_by="system",
    ))
    created += 1

    # ── 2) SHIPPED 发货单（同步扣库存 + SALES_ISSUE 流水，保证 reset 后自洽） ──
    db.add(SalesDelivery(
        delivery_number="DK-20251231-0002",
        sales_order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=order.customer.legal_name if order.customer else None,
        material_code=order.material_code,
        quantity=Decimal("20"),
        unit=order.sales_unit or "PCS",
        unit_price=Decimal(str(unit_price)),
        status=DeliveryStatus.SHIPPED,
        ship_date=datetime(2025, 12, 31, 10, 0, 0),
        remarks="销售发货演示：已发货（SHIPPED，种子已扣库存）",
        created_by="system",
    ))
    from backend.services.inventory.valuation import InventoryValuationService
    InventoryValuationService.post(
        db, material_code=order.material_code, qty_delta=-20,
        source_type="SALES_ISSUE", source_ref="DK-20251231-0002", operator="system",
    )
    db.add(MaterialTransaction(
        transaction_number="TXN-SD-SEED-0001",
        material_code=order.material_code,
        transaction_type="SALES_ISSUE",
        quantity=Decimal("-20"),
        unit=order.sales_unit or "PCS",
        reference_number="DK-20251231-0002",
        reference_type="SALES_DELIVERY",
        transaction_date=datetime(2025, 12, 31, 10, 0, 0),
        operator="system",
        remarks="销售发货演示：出库扣减（种子）",
        created_by="system",
    ))
    created += 1
    db.flush()

    # ── 3) 已开票发票（金额=已发货量×单价）+ AR 应收流水 ────────────
    amount = Decimal("20") * Decimal(str(unit_price))
    db.add(SalesInvoice(
        invoice_number="INV-20251231-0001",
        sales_order_number=order.order_number,
        delivery_number="DK-20251231-0002",
        customer_id=order.customer_id,
        customer_name=order.customer.legal_name if order.customer else None,
        amount=amount,
        currency=order.currency or "CNY",
        status=InvoiceStatus.ISSUED,
        invoice_date=datetime(2025, 12, 31, 11, 0, 0),
        due_date=order.delivery_date,
        received_amount=Decimal("0"),
        remarks="销售发票演示：已开票（ISSUED，生成应收）",
        created_by="system",
    ))
    db.flush()  # 发票先落库，避免 receivable_entries FK 乱序
    db.add(ReceivableEntry(
        entry_number="AR-20251231-0001",
        invoice_number="INV-20251231-0001",
        customer_id=order.customer_id,
        entry_type=ReceivableEntryType.INVOICE,
        amount=amount,
        entry_date=datetime(2025, 12, 31, 11, 0, 0),
        reference_number="INV-20251231-0001",
        remarks="应收流水演示：开票应收（种子）",
        created_by="system",
    ))
    created += 1
    db.commit()
    return created


def seed_inventory_opening(db: Session) -> int:
    """移动加权期初建账：按基线数量×标准成本建估值行和 OPENING 流水（幂等）。

    口径（用户确认按方案默认）：期初科目 4001、发票额不含税、标准成本作期初单价。
    """
    from backend.common.models.mm import Material
    from backend.common.models.planning import InventoryValuation, StandardCost, ValuationMove
    from backend.services.inventory.valuation import InventoryValuationService
    from backend.services.planning.demo_reset import MATERIAL_STOCK_BASELINE

    created = 0
    for code, qty in MATERIAL_STOCK_BASELINE.items():
        if not qty or float(qty) <= 0:
            continue
        if db.query(InventoryValuation).filter(InventoryValuation.material_code == code).first():
            continue
        std = (
            db.query(StandardCost)
            .filter(StandardCost.material_code == code)
            .order_by(StandardCost.id.desc())
            .first()
        )
        material = db.query(Material).filter(Material.material_code == code).first()
        cost = float(std.material_cost or 0) if std else float(material.standard_price or 0) if material else 0.0
        if cost <= 0:
            continue
        try:
            InventoryValuationService.post(
                db, material_code=code, qty_delta=qty, unit_cost=cost,
                source_type="OPENING", source_ref=f"OPENING-{datetime.now().strftime('%Y-%m')}",
                operator="system",
            )
            created += 1
        except Exception as exc:
            print(f"[VALUATION] 期初建账跳过 {code}: {exc}")
    db.commit()
    # 期初 GL 分录（按用户默认：借 1405 库存商品 / 贷 4001 实收资本）
    total = sum(
        float(v.amount or 0) for v in db.query(InventoryValuation).all()
    )
    if total > 0:
        from backend.services.finance.gl_engine import GlEngineError
        from backend.services.finance.gl_engine import post as gl_post
        try:
            gl_post(
                db, "OPENING", f"OPENING-{datetime.now().strftime('%Y-%m')}",
                amount=total,
                lines=[
                    ("1405", total, 0, "期初库存建账"),
                    ("4001", 0, total, "期初库存建账"),
                ],
                summary="移动加权期初建账", operator="system",
            )
            db.commit()
        except GlEngineError as exc:
            print(f"[GL] 期初分录跳过（可能已存在）: {exc}")
    return created


def seed_gl_accounts(db: Session) -> int:
    """总账科目 + 当月会计期间种子（幂等，按编码判重）。P2 demo：8 个一级明细科目。"""
    from backend.common.models.planning import Account, FiscalPeriod, PeriodStatus
    from backend.services.finance.gl_rules import GL_ACCOUNTS

    created = 0
    for code, name, account_type in GL_ACCOUNTS:
        if db.query(Account).filter(Account.account_code == code).first():
            continue
        db.add(Account(
            account_code=code,
            account_name=name,
            account_type=account_type,
            parent_code=None,
            is_leaf=True,
            created_by="system",
        ))
        created += 1

    # PG 原生枚举 ALTER TYPE（create_all 不会扩展已有 ENUM 值）
    from sqlalchemy import text
    try:
        db.execute(text("ALTER TYPE glsourcetype ADD VALUE IF NOT EXISTS 'PERIOD_CLOSE'"))
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[GL] 枚举扩展跳过（可能已存在）: {exc}")

    now = datetime.now()
    period_code = now.strftime("%Y-%m")
    if db.query(FiscalPeriod).filter(FiscalPeriod.period_code == period_code).first() is None:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1, month=1) if now.month == 12 else start.replace(month=start.month + 1)
        db.add(FiscalPeriod(
            period_code=period_code, start_date=start, end_date=end,
            status=PeriodStatus.OPEN, created_by="system",
        ))
        created += 1
    db.commit()
    return created


def seed_suppliers(db: Session) -> int:
    """供应商主数据演示种子（幂等）。

    与采购单 seed_purchase_demo_data 硬编码的 SUP-HQ 对齐：
    - 华强覆铜板贸易（SUP-HQ）——现有演示采购单的供应商；
    - 苏州瑞银电子、铜陵金泰铜业——补充供应商下拉可选。
    """
    from backend.common.models.planning import Supplier

    demo_suppliers = [
        {
            "supplier_code": "SUP-HQ",
            "supplier_name": "华强覆铜板贸易",
            "short_name": "华强",
            "supplier_type": "MATERIAL",
            "contact_person": "王经理",
            "contact_phone": "0755-88886666",
            "email": "sales@huaqiang-fr4.com",
            "address": "广东省深圳市宝安区",
            "payment_terms": "月结30天",
            "lead_time_days": 5,
            "default_currency": "CNY",
            "rating": 5,
        },
        {
            "supplier_code": "SUP-RY",
            "supplier_name": "苏州瑞银电子材料",
            "short_name": "瑞银电子",
            "supplier_type": "MATERIAL",
            "contact_person": "李主管",
            "contact_phone": "0512-66889900",
            "email": "sales@ruiyin-pp.com",
            "address": "江苏省苏州市工业园区",
            "payment_terms": "月结45天",
            "lead_time_days": 7,
            "default_currency": "CNY",
            "rating": 4,
        },
        {
            "supplier_code": "SUP-JT",
            "supplier_name": "铜陵金泰铜业",
            "short_name": "金泰铜业",
            "supplier_type": "MATERIAL",
            "contact_person": "周工",
            "contact_phone": "0562-55667788",
            "email": "sales@jintai-cu.com",
            "address": "安徽省铜陵市经济技术开发区",
            "payment_terms": "预付30%",
            "lead_time_days": 3,
            "default_currency": "CNY",
            "rating": 4,
        },
    ]
    created = 0
    for item in demo_suppliers:
        exists = (
            db.query(Supplier)
            .filter(
                Supplier.supplier_code == item["supplier_code"],
                Supplier.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if exists is not None:
            continue
        db.add(Supplier(**item, created_by="system"))
        created += 1
    db.flush()
    return created


def seed_purchase_requests(db: Session) -> int:
    """采购申请演示种子（幂等，按备注标记判重）。

    - PRQ-…（DRAFT，两行）：演示「下达 → 整单转采购单」；
    - PRQ-…（RELEASED，单行）：可直接演示「转采购单」。
    转换动作不在种子里做（留给演示现场），PO 由 convert 端点实时生成。
    """
    from backend.common.models.planning import (
        PurchaseRequest,
        PurchaseRequestLine,
        PurchaseRequestStatus,
    )

    created = 0
    today = datetime.now()

    def _has_demo_request(marker: str) -> bool:
        return (
            db.query(PurchaseRequest)
            .filter(
                PurchaseRequest.remarks.like(f"%{marker}%"),
                PurchaseRequest.is_deleted == False,  # noqa: E712
            )
            .first()
            is not None
        )

    def _next_number() -> str:
        return NumberGenerator.generate_document_number(
            db, PurchaseRequest, "purchase_request_number", "PRQ", 4
        )

    # ── 1) DRAFT：FR-4 + 半固化片（演示下达→转换全流程） ────────────────
    if not _has_demo_request("采购申请演示：草稿待下达"):
        number = _next_number()
        pr = PurchaseRequest(
            purchase_request_number=number,
            supplier_id="SUP-RY",
            supplier_name="苏州瑞银电子材料",
            status=PurchaseRequestStatus.DRAFT,
            request_date=today,
            expected_date=today + timedelta(days=10),
            currency="CNY",
            total_amount=Decimal("5800.00"),
            requested_by="jihuayuan",
            remarks="N3+ 采购申请演示：草稿待下达（RM-FR4-150 ×100 / RM-PP1080 ×200）",
            created_by="system",
        )
        db.add(pr)
        db.flush()
        db.add(
            PurchaseRequestLine(
                purchase_request_number=number,
                line_number=1,
                material_code="RM-FR4-150",
                quantity=Decimal("100"),
                unit="张",
                unit_price=Decimal("38.50"),
                expected_date=today + timedelta(days=10),
                status="OPEN",
                created_by="system",
            )
        )
        db.add(
            PurchaseRequestLine(
                purchase_request_number=number,
                line_number=2,
                material_code="RM-PP1080",
                quantity=Decimal("200"),
                unit="张",
                unit_price=Decimal("12.00"),
                expected_date=today + timedelta(days=10),
                status="OPEN",
                created_by="system",
            )
        )
        created += 1

    # ── 2) RELEASED：铜箔（演示一键转采购单） ────────────────────────────
    if not _has_demo_request("采购申请演示：已下达待转换"):
        number = _next_number()
        pr = PurchaseRequest(
            purchase_request_number=number,
            supplier_id="SUP-JT",
            supplier_name="铜陵金泰铜业",
            status=PurchaseRequestStatus.RELEASED,
            request_date=today,
            expected_date=today + timedelta(days=7),
            currency="CNY",
            total_amount=Decimal("4300.00"),
            requested_by="jihuayuan",
            remarks="N3+ 采购申请演示：已下达待转换（RM-CU-FOIL ×50）",
            created_by="system",
        )
        db.add(pr)
        db.flush()
        db.add(
            PurchaseRequestLine(
                purchase_request_number=number,
                line_number=1,
                material_code="RM-CU-FOIL",
                quantity=Decimal("50"),
                unit="卷",
                unit_price=Decimal("86.00"),
                expected_date=today + timedelta(days=7),
                status="OPEN",
                created_by="system",
            )
        )
        created += 1

    db.flush()
    return created


def seed_material_batches(db: Session) -> int:
    """原料批次追溯基线（幂等）：回填领料单批次号/来源采购单，并给来料检验挂采购单。

    追溯引擎据此可把「领料批次 → 采购单 → 供应商」串起来；仅补空值，不覆盖用户录入。
    """
    from backend.common.models.mm import MaterialIssue

    count = 0
    first_po = db.query(PurchaseOrder).filter(PurchaseOrder.is_deleted == False).first()  # noqa: E712

    issues = db.query(MaterialIssue).filter(MaterialIssue.is_deleted == False).all()  # noqa: E712
    for issue in issues:
        if issue.batch_number:
            continue
        day = issue.issued_at.strftime("%Y%m%d") if issue.issued_at else "20261120"
        issue.batch_number = f"BATCH-{issue.material_code}-{day}"
        line = (
            db.query(PurchaseOrderLine)
            .filter(
                PurchaseOrderLine.material_code == issue.material_code,
                PurchaseOrderLine.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        po = line.purchase_order_number if line else (first_po.purchase_order_number if first_po else None)
        if po:
            issue.purchase_order_number = po
        count += 1

    # 来料检验单挂采购单（演示库中原字段恒空）
    iqc_rows = (
        db.query(InspectionOrder)
        .filter(
            InspectionOrder.inspection_type == InspectionType.INCOMING,
            InspectionOrder.purchase_order_number.is_(None),
            InspectionOrder.is_deleted == False,  # noqa: E712
        )
        .all()
    )
    for row in iqc_rows:
        line = (
            db.query(PurchaseOrderLine)
            .filter(
                PurchaseOrderLine.material_code == row.material_code,
                PurchaseOrderLine.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        po = line.purchase_order_number if line else (first_po.purchase_order_number if first_po else None)
        if po:
            row.purchase_order_number = po
            count += 1

    return count


def seed_material_transactions(db: Session) -> int:
    """库存流水基线种子（幂等）：按现存领料单补 ISSUE 流水。

    流水表是账本——reset 清空后依据未删除的领料单重建基线，
    保证「库存流水」演示页 reset 后不为空；此后领料/到货/退货实时追加。
    """
    from backend.common.models.mm import MaterialIssue, MaterialTransaction

    created = 0
    issues = db.query(MaterialIssue).filter(MaterialIssue.is_deleted == False).all()  # noqa: E712
    for issue in issues:
        exists = (
            db.query(MaterialTransaction)
            .filter(
                MaterialTransaction.reference_type == "MATERIAL_ISSUE",
                MaterialTransaction.reference_number == issue.issue_number,
                MaterialTransaction.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if exists is not None:
            continue
        db.add(
            MaterialTransaction(
                transaction_number=NumberGenerator.generate_document_number(
                    db, MaterialTransaction, "transaction_number", "TR", 4
                ),
                material_code=issue.material_code,
                transaction_type="ISSUE",
                quantity=-(issue.quantity or 0),
                unit=issue.unit or "PCS",
                reference_number=issue.issue_number,
                reference_type="MATERIAL_ISSUE",
                warehouse=issue.warehouse,
                transaction_date=issue.issued_at or datetime.now(),
                operator=issue.issued_by or "system",
                remarks=f"生产领料: {issue.production_order_number}",
                created_by="system",
            )
        )
        # 同事务连续生成单号：flush 让下一条 generate 能看到刚插入的序号
        db.flush()
        created += 1
    db.flush()
    return created


def main() -> None:
    print("=" * 56)
    print("DIERP 计划与控制系统 - 增量升级")
    print("=" * 56)
    create_tables()

    db = SessionLocal()
    try:
        print(f"[OK] 计划参数新增 {seed_policies(db)} 条")
        print(f"[OK] 原材料采购类型修正 {fix_policy_procurement(db)} 条")
        print(f"[OK] 已发布演示 BOM 新增 {seed_boms(db)} 套")
        print(f"[OK] 工作中心日历新增 {seed_work_calendars(db)} 条")
        print(f"[OK] 成本费率新增 {seed_cost_rates(db)} 条")
        print(f"[OK] 物料标准单价写入 {seed_material_prices(db)} 个")
        print(f"[OK] 需求预测新增 {seed_forecasts(db)} 条")
        print(f"[OK] APS 主数据新增 {seed_aps_master_data(db)} 条")
        print(f"[OK] 工序能力码修正 {fix_routing_operation_codes(db)} 条")
        print(f"[OK] APS 演示数据新增 {seed_aps_demo_data(db)} 条")
        print(f"[OK] APS 齐套快照新增 {seed_aps_kitting(db)} 条")
        print(f"[OK] EAM 演示数据新增 {seed_eam_demo_data(db)} 条")
        print(f"[OK] 报工工艺关联与工时修正 {seed_operation_report_routing(db)} 条")
        print(f"[OK] QMS 演示数据新增 {seed_qms_demo_data(db)} 条")
        print(f"[OK] 采购演示单据新增 {seed_purchase_demo_data(db)} 张")
        print(f"[OK] 采购申请演示新增 {seed_purchase_requests(db)} 张")
        print(f"[OK] 供应商主数据新增 {seed_suppliers(db)} 家")
        print(f"[OK] 原料批次追溯基线新增 {seed_material_batches(db)} 条")
        print(f"[OK] 库存流水基线新增 {seed_material_transactions(db)} 条")
        print(f"[OK] 库存估值期初新增 {seed_inventory_opening(db)} 条")
        print(f"[OK] 销售发货演示新增 {seed_sales_delivery_demo(db)} 张")
        print(f"[OK] 总账科目/期间新增 {seed_gl_accounts(db)} 条")
        db.commit()

        print("-" * 56)
        print(f"计划参数: {db.query(PlanningPolicy).count()}")
        print(f"工作日历: {db.query(WorkCalendar).count()}")
        print(f"成本费率: {db.query(CostRate).count()}")
        print(f"需求预测: {db.query(Forecast).count()}")
        print(f"APS 资源: {db.query(Resource).count()} / 技能: {db.query(SkillMatrix).count()} / 换产: {db.query(ChangeoverMatrix).count()}")
        print(f"EAM 维护计划: {db.query(MaintenancePlan).count()} / 维护工单: {db.query(MaintenanceOrder).count()} / 故障记录: {db.query(EquipmentFailure).count()}")
        print(f"QMS 检验单: {db.query(InspectionOrder).count()} / 不合格品记录: {db.query(NonConformanceReport).count()}")
        print("=" * 56)
        print("升级完成")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] 升级失败: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
