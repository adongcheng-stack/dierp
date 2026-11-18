"""向 mock snapshot.json 注入 QMS 演示数据（幂等，不修改其他集合）。

运行时从 repo 根执行：python backend/scripts/seed_qms_snapshot.py
注入后请同步递增 snapshot.version，否则老用户浏览器不会刷新。
"""
import io
import json
from datetime import datetime

path = "frontend/src/mock/snapshot.json"
with io.open(path, encoding="utf-8") as f:
    db = json.load(f)

db["version"] = 8
now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

# 1) 一张带报废的报工单（供「由报工生成 NCR」下拉）
reports = db.setdefault("operationReports", [])
max_rep_id = max((r.get("id") or 0) for r in reports) if reports else 0
if not any(r.get("report_number") == "OR-QMS-2026-REPORT-0001" for r in reports):
    reports.append(
        {
            "id": max_rep_id + 1,
            "report_number": "OR-QMS-2026-REPORT-0001",
            "production_order_number": "PO-APS-02",
            "work_center_id": "DRILL-A",
            "operation_no": "0010",
            "operation_name": "钻孔",
            "reported_quantity": 112,
            "good_quantity": 100,
            "scrap_quantity": 12,
            "setup_time": 10,
            "machine_time": 120,
            "labor_time": 25,
            "routing_operation_id": None,
            "lot_number": "LOT-20251230-0002",
            "status": "COMPLETED",
            "reported_by": "system",
            "reported_at": now,
            "remarks": "QMS 演示：带报废的报工单",
            "created_by": "system",
            "created_at": now,
            "updated_by": None,
            "updated_at": None,
            "is_deleted": False,
        }
    )

# 2) 检验单集合
db["inspectionOrders"] = [
    {
        "id": 1,
        "inspection_number": "IQC-20261118-0001",
        "inspection_type": "INCOMING",
        "material_code": "HF1004ENIGAB01",
        "lot_number": None,
        "purchase_order_number": None,
        "report_number": None,
        "quantity_inspected": 300,
        "quantity_ok": 300,
        "quantity_rejected": 0,
        "inspector": "李质检",
        "inspected_at": now,
        "result": "PASS",
        "status": "COMPLETED",
        "remarks": "QMS 演示：来料检验 PASS",
        "created_by": "system",
        "created_at": now,
        "updated_by": "system",
        "updated_at": now,
        "is_deleted": False,
    },
    {
        "id": 2,
        "inspection_number": "IPQC-20261118-0001",
        "inspection_type": "IN_PROCESS",
        "material_code": "HF1004ENIGAB02",
        "lot_number": "LOT-20251230-0003",
        "purchase_order_number": None,
        "report_number": None,
        "quantity_inspected": 200,
        "quantity_ok": 188,
        "quantity_rejected": 12,
        "inspector": "王质检",
        "inspected_at": now,
        "result": "FAIL",
        "status": "COMPLETED",
        "remarks": "蚀刻线宽偏移 12 PCS 不合格",
        "created_by": "system",
        "created_at": now,
        "updated_by": "system",
        "updated_at": now,
        "is_deleted": False,
    },
    {
        "id": 3,
        "inspection_number": "FQC-20261118-0001",
        "inspection_type": "FINAL",
        "material_code": "HF1004ENIGAB01",
        "lot_number": "LOT-20251230-0001",
        "purchase_order_number": None,
        "report_number": None,
        "quantity_inspected": 188,
        "quantity_ok": 188,
        "quantity_rejected": 0,
        "inspector": "赵终检",
        "inspected_at": now,
        "result": "PASS",
        "status": "COMPLETED",
        "remarks": "QMS 演示：终检 PASS",
        "created_by": "system",
        "created_at": now,
        "updated_by": "system",
        "updated_at": now,
        "is_deleted": False,
    },
]

# 3) 不合格品记录集合（含 检验来源 OPEN + 设备原因 OPEN）
db["nonConformanceReports"] = [
    {
        "id": 1,
        "ncr_number": "NCR-20261118-0001",
        "source_type": "INSPECTION",
        "source_ref": "IPQC-20261118-0001",
        "inspection_number": "IPQC-20261118-0001",
        "report_number": None,
        "lot_number": "LOT-20251230-0003",
        "material_code": "HF1004ENIGAB02",
        "quantity": 12,
        "defect_code": "ETCH-OFFSET",
        "defect_desc": "蚀刻线宽偏移 12 PCS",
        "severity": "MAJOR",
        "disposition": "REWORK",
        "disposition_note": "蚀刻参数复核后返工重做",
        "root_cause": "蚀刻线速参数漂移",
        "equipment_cause": False,
        "failure_number": None,
        "status": "CLOSED",
        "reviewed_by": "system",
        "reviewed_at": now,
        "closed_by": "system",
        "closed_at": now,
        "created_by": "system",
        "created_at": now,
        "updated_by": None,
        "updated_at": None,
        "is_deleted": False,
    },
    {
        "id": 2,
        "ncr_number": "NCR-20261118-0002",
        "source_type": "LOT_CARD",
        "source_ref": "LOT-20251230-0003",
        "inspection_number": None,
        "report_number": None,
        "lot_number": "LOT-20251230-0003",
        "material_code": "HF1004ENIGAB02",
        "quantity": 12,
        "defect_code": "DRILL-OFFSET",
        "defect_desc": "钻孔位置偏移，判定为设备原因",
        "severity": "MAJOR",
        "disposition": None,
        "disposition_note": None,
        "root_cause": "钻轴轴向间隙过大导致定位偏移",
        "equipment_cause": True,
        "failure_number": "EF-20261118-0002",
        "status": "UNDER_REVIEW",
        "reviewed_by": "system",
        "reviewed_at": now,
        "closed_by": None,
        "closed_at": None,
        "created_by": "system",
        "created_at": now,
        "updated_by": "system",
        "updated_at": now,
        "is_deleted": False,
    },
]

# 4) 联动生成的 EAM 故障（NCR-…-0002 → EF-…-0002）
failures = db.setdefault("equipmentFailures", [])
if not any(f.get("failure_number") == "EF-20261118-0002" for f in failures):
    failures.append(
        {
            "id": 2,
            "failure_number": "EF-20261118-0002",
            "resource_id": "RES-DRILL-B-01",
            "work_center_id": "DRILL-B",
            "occurred_at": now,
            "resolved_at": None,
            "severity": "MEDIUM",
            "description": "QMS 联动：钻孔定位偏移，疑似主轴间隙",
            "root_cause": None,
            "action_taken": None,
            "downtime_hours": 0,
            "status": "OPEN",
            "reported_by": "system",
            "created_by": "system",
            "created_at": now,
            "updated_by": None,
            "updated_at": None,
            "is_deleted": False,
        }
    )

with io.open(path, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("OK: version ->", db["version"])
print("inspectionOrders ->", len(db["inspectionOrders"]))
print("nonConformanceReports ->", len(db["nonConformanceReports"]))
print("equipmentFailures ->", len(db["equipmentFailures"]))
print("operationReports ->", len(db["operationReports"]))