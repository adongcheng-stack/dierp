"""意图 7：未关闭不合格品（设计 §7.2 #7、§7.2.1 #7）。"""
from __future__ import annotations

from pydantic import Field
from sqlalchemy.orm import Session

from backend.common.models.planning import NcrSeverity, NcrStatus, NonConformanceReport
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "open_nonconformance"

ALLOWED_ROLES = frozenset({"ENGINEER", "PRODUCTION", "GENERAL_MANAGER"})

ALL_COLUMNS = [
    "ncr_number", "material_code", "source_ref", "severity",
    "status", "quantity", "disposition", "created_at",
]

_DEFAULT_STATUSES = (NcrStatus.OPEN, NcrStatus.UNDER_REVIEW, NcrStatus.DISPOSITIONED)


class OpenNonConformanceParams(BoundIntent):
    status: str | None = None       # 显式给出时按单值过滤
    severity: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


def _value(enum_value: object) -> str | None:
    if enum_value is None:
        return None
    return enum_value.value if hasattr(enum_value, "value") else str(enum_value)


def run(db: Session, p: OpenNonConformanceParams, role: str) -> QueryResult:
    query = db.query(NonConformanceReport)
    if p.status:
        query = query.filter(NonConformanceReport.status == NcrStatus(p.status))
    else:
        query = query.filter(NonConformanceReport.status.in_(list(_DEFAULT_STATUSES)))
    if p.severity:
        query = query.filter(NonConformanceReport.severity == NcrSeverity(p.severity))
    rows = query.order_by(NonConformanceReport.id.desc()).limit(p.limit).all()

    data = []
    sources = []
    for item in rows:
        data.append({
            "ncr_number": item.ncr_number,
            "material_code": item.material_code,
            "source_ref": item.source_ref,
            "severity": _value(item.severity),
            "status": _value(item.status),
            "quantity": float(item.quantity or 0),
            "disposition": _value(item.disposition),
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
        sources.append(Provenance(
            table="non_conformance_reports", record_key=item.ncr_number,
            ontology_iri=NS + "NonConformanceReport",
        ))
    return QueryResult(columns=list(ALL_COLUMNS), rows=data, sources=sources)


SPEC = IntentSpec(
    code=CODE,
    label="未关闭不合格品",
    description="列出未关闭的 NCR（OPEN/UNDER_REVIEW/DISPOSITIONED），可按严重度过滤。",
    entities=["NonConformanceReport"],
    primary_entity="NonConformanceReport",
    params_model=OpenNonConformanceParams,
    defaults={"limit": 50},
    domains=["planning"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={"*": list(ALL_COLUMNS)},
    record_key=["ncr_number"],
    downlink="/qms/ncrs",
    shacl_coverage="full",
    provenance_kind="event",
    formula="默认 status IN (OPEN, UNDER_REVIEW, DISPOSITIONED)；显式给 status 时按单值；"
            "severity 可选",
    handler=run,
)
