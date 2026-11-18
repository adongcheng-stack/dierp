from backend.common.database.base import SessionLocal
from backend.common.models import eng, mm, pp, sd, user  # noqa: F401
from backend.common.models.eng import ProductionVersion, Routing, RoutingOperation
from backend.common.models.pp import ProductionOrder

db = SessionLocal()
try:
    for r in db.query(Routing).all():
        ops = db.query(RoutingOperation).filter(RoutingOperation.routing_id == r.routing_id).all()
        print("ROUTING", r.routing_id, r.material_code, "ops", [(o.id, o.operation_no, o.work_center_id, o.setup_time, o.machine_time, o.labor_time) for o in ops])
    print("--- versions ---")
    for v in db.query(ProductionVersion).all():
        print("PV", v.production_version_id, v.material_code, v.routing_id)
    print("--- orders ---")
    for o in db.query(ProductionOrder).all():
        print("PO", o.order_number, o.material_code, o.quantity)
finally:
    db.close()
