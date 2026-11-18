"""刷新演示用计划数据，并把结果导出到前端 mock 快照。

流程：清理旧计划单据 -> 生成 MPS -> 下达 -> 运行 MRP -> 写入 snapshot.json
用法：python backend/scripts/refresh_planning_demo.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
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

from backend.api.routers.planning import (  # noqa: E402
    _exception,
    _kitting,
    _mps_entry,
    _mps_summary,
    _planned_order,
    _policy,
    _requirement,
    _run_summary,
)
from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models.eng import BOM, BOMItem  # noqa: E402
from backend.common.models.planning import (  # noqa: E402
    Forecast,
    KittingResult,
    MpsEntry,
    MpsPlan,
    MrpException,
    MrpRequirement,
    MrpRun,
    PeggingLink,
    PlannedOrder,
    PlanningPolicy,
    PurchaseOrder,
    PurchaseOrderLine,
)
from backend.services.planning import MpsEngine, MrpEngine  # noqa: E402

SNAPSHOT = project_root / "frontend" / "src" / "mock" / "snapshot.json"


def clean(db) -> None:
    db.query(PeggingLink).delete(synchronize_session=False)
    db.query(MrpRequirement).delete(synchronize_session=False)
    db.query(MrpException).delete(synchronize_session=False)
    db.query(PlannedOrder).delete(synchronize_session=False)
    db.query(KittingResult).delete(synchronize_session=False)
    db.query(MpsEntry).delete(synchronize_session=False)
    db.query(MrpRun).delete(synchronize_session=False)
    db.query(MpsPlan).delete(synchronize_session=False)

    generated_pos = {
        row[0]
        for row in db.query(PurchaseOrder.purchase_order_number)
        .filter(PurchaseOrder.source_planned_order.isnot(None))
        .all()
    }
    if generated_pos:
        db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.purchase_order_number.in_(generated_pos)
        ).delete(synchronize_session=False)
        db.query(PurchaseOrder).filter(
            PurchaseOrder.purchase_order_number.in_(generated_pos)
        ).delete(synchronize_session=False)
    db.commit()
    print("[OK] 旧计划单据已清理")


def generate(db) -> None:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today + timedelta(days=1)
    end = today + timedelta(days=56)

    mps = MpsEngine.generate(
        db,
        horizon_start=start,
        horizon_end=end,
        plan_name="演示 MPS · 未来 8 周",
        demand_source="MIXED",
        include_forecast=True,
        include_safety_stock=True,
        created_by="planning",
    )
    db.flush()
    MpsEngine.release(db, mps.mps_number, released_by="planning")

    run = MrpEngine.run(
        db,
        horizon_start=start,
        horizon_end=end,
        run_type="REGENERATIVE",
        demand_source="MPS",
        mps_number=mps.mps_number,
        include_forecast=True,
        include_safety_stock=True,
        run_by="planning",
    )
    db.commit()
    print(f"[OK] 已生成 {mps.mps_number} / {run.run_number}")


def export(db) -> None:
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    data["mpsPlans"] = [_mps_summary(row) for row in db.query(MpsPlan).all()]
    data["mpsEntries"] = [_mps_entry(row) for row in db.query(MpsEntry).all()]
    data["mrpRuns"] = [_run_summary(row) for row in db.query(MrpRun).all()]
    data["mrpRequirements"] = [_requirement(row) for row in db.query(MrpRequirement).all()]
    data["mrpExceptions"] = [_exception(row) for row in db.query(MrpException).all()]
    data["plannedOrders"] = [_planned_order(row) for row in db.query(PlannedOrder).all()]
    data["kittingResults"] = [_kitting(row) for row in db.query(KittingResult).all()]
    data["planningPolicies"] = [_policy(row) for row in db.query(PlanningPolicy).all()]

    data["boms"] = [
        {
            "id": bom.id,
            "bom_number": bom.bom_number,
            "version": bom.version,
            "parent_material_code": bom.parent_material_code,
            "plant_id": bom.plant_id,
            "bom_type": bom.bom_type,
            "base_quantity": float(bom.base_quantity or 1),
            "base_uom": bom.base_uom,
            "status": bom.status.value if hasattr(bom.status, "value") else bom.status,
            "description": bom.description,
            "effective_date": bom.effective_date.isoformat() if bom.effective_date else None,
            "expiry_date": bom.expiry_date.isoformat() if bom.expiry_date else None,
            "items": [
                {
                    "id": item.id,
                    "line_number": item.line_number,
                    "material_code": item.material_code,
                    "item_category": item.item_category,
                    "quantity": float(item.quantity or 0),
                    "unit": item.unit,
                    "scrap_rate": float(item.scrap_rate) if item.scrap_rate is not None else None,
                    "calculation_formula": item.calculation_formula,
                    "layer_code": item.layer_code,
                    "material_type": item.material_type,
                    "process_step": item.process_step,
                    "remarks": item.remarks,
                }
                for item in db.query(BOMItem)
                .filter(BOMItem.bom_number == bom.bom_number, BOMItem.is_deleted == False)
                .order_by(BOMItem.line_number)
                .all()
            ],
            "created_by": bom.created_by,
            "created_at": bom.created_at.isoformat() if bom.created_at else None,
            "updated_by": bom.updated_by,
            "updated_at": bom.updated_at.isoformat() if bom.updated_at else None,
        }
        for bom in db.query(BOM).filter(BOM.is_deleted == False).all()
    ]

    data["peggingLinks"] = [
        {
            "id": row.id,
            "run_number": row.run_number,
            "planned_order_number": row.planned_order_number,
            "demand_type": row.demand_type.value if hasattr(row.demand_type, "value") else row.demand_type,
            "demand_ref": row.demand_ref,
            "supply_type": row.supply_type.value if hasattr(row.supply_type, "value") else row.supply_type,
            "supply_ref": row.supply_ref,
            "pegged_qty": float(row.pegged_qty or 0),
        }
        for row in db.query(PeggingLink).all()
    ]
    data["forecasts"] = [
        {
            "id": row.id,
            "forecast_number": row.forecast_number,
            "version": row.version,
            "material_code": row.material_code,
            "quantity": float(row.quantity or 0),
            "consumed_quantity": float(row.consumed_quantity or 0),
            "unit": row.unit,
            "due_date": row.due_date.isoformat() if row.due_date else None,
            "bucket_type": row.bucket_type,
            "status": row.status,
            "remarks": row.remarks,
        }
        for row in db.query(Forecast).all()
    ]
    data.setdefault("purchaseOrders", [])
    data.setdefault("purchaseOrderLines", [])
    data["generatedAt"] = datetime.now().isoformat()

    SNAPSHOT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        "[OK] snapshot 已更新: "
        f"MPS={len(data['mpsPlans'])} 计划订单={len(data['plannedOrders'])} "
        f"异常={len(data['mrpExceptions'])} 齐套={len(data['kittingResults'])}"
    )


def main() -> None:
    db = SessionLocal()
    try:
        clean(db)
        generate(db)
        export(db)
    except Exception as exc:
        db.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
