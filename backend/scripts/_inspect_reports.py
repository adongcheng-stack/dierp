from backend.common.database.base import SessionLocal
from backend.common.models import eng, mm, pp, sd, user  # noqa: F401
from backend.common.models.pp import OperationReport

db = SessionLocal()
try:
    rows = db.query(OperationReport).all()
    print("backend reports:", len(rows))
    for r in rows[:15]:
        print(
            r.report_number,
            r.production_order_number,
            r.work_center_id,
            "op=", r.operation_no,
            "routing_op=", r.routing_operation_id,
            "qty=", r.reported_quantity,
            "good=", r.good_quantity,
            "machine=", r.machine_time,
            "labor=", r.labor_time,
        )
finally:
    db.close()
