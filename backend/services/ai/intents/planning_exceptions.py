"""意图 4：未处理计划异常（设计 §7.2 #4、§7.2.1 #4）。"""
from __future__ import annotations

from pydantic import Field
from sqlalchemy.orm import Session

from backend.common.models.planning import MrpException, ResolutionStatus
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "open_mrp_exceptions"

ALLOWED_ROLES = frozenset({"PLANNER", "GENERAL_MANAGER", "ADMIN"})

ALL_COLUMNS = [
    "id", "run_number", "exception_type", "severity", "material_code",
    "shortage_qty", "shortage_date", "suggestion", "resolution_status",
]


class OpenMrpExceptionsParams(BoundIntent):
    severity: str | None = None
    exception_type: str | None = None
    resolution_status: str = "OPEN"
    limit: int = Field(default=50, ge=1, le=200)


def _value(enum_value: object) -> str | None:
    if enum_value is None:
        return None
    return enum_value.value if hasattr(enum_value, "value") else str(enum_value)


def run(db: Session, p: OpenMrpExceptionsParams, role: str) -> QueryResult:
    query = db.query(MrpException).filter(
        MrpException.resolution_status == ResolutionStatus(p.resolution_status)
    )
    if p.severity:
        query = query.filter(MrpException.severity == p.severity)
    if p.exception_type:
        query = query.filter(MrpException.exception_type == p.exception_type)
    rows = (
        query.order_by(MrpException.shortage_qty.desc())
        .limit(p.limit)
        .all()
    )
    data = []
    sources = []
    for item in rows:
        data.append({
            "id": item.id,
            "run_number": item.run_number,
            "exception_type": _value(item.exception_type),
            "severity": _value(item.severity),
            "material_code": item.material_code,
            "shortage_qty": float(item.shortage_qty or 0),
            "shortage_date": item.shortage_date.isoformat() if item.shortage_date else None,
            "suggestion": item.suggestion,
            "resolution_status": _value(item.resolution_status),
        })
        sources.append(Provenance(
            table="mrp_exceptions", record_key=str(item.id),
            ontology_iri=NS + "MrpException",
        ))
    return QueryResult(columns=list(ALL_COLUMNS), rows=data, sources=sources)


SPEC = IntentSpec(
    code=CODE,
    label="未处理计划异常",
    description="列出 MRP 运行产生的未处理异常，可按严重度与异常类型过滤。",
    entities=["MrpException"],
    primary_entity="MrpException",
    params_model=OpenMrpExceptionsParams,
    defaults={"resolution_status": "OPEN", "limit": 50},
    domains=["planning"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={"*": list(ALL_COLUMNS)},
    output_enums={
        "exception_type": "MrpExceptionType",
        "severity": "ExceptionSeverity",
        "resolution_status": "ResolutionStatus",
    },
    record_key=["id"],
    downlink=None,          # 事件表无业务单号，只能定位到 MRP 运行批次
    shacl_coverage="full",
    provenance_kind="event",
    formula="resolution_status = 'OPEN'（默认）；severity/exception_type 可选；按 shortage_qty 降序；"
            "run_number 允许为空，溯源用主键 id",
    handler=run,
)
