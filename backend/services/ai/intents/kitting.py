"""意图 1：齐套缺口（设计 §7.2 #1、§7.2.1 #1）。"""
from __future__ import annotations

from pydantic import Field
from sqlalchemy.orm import Session

from backend.common.models.planning import KitStatus, KittingResult
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "kitting_shortage"

ALLOWED_ROLES = frozenset({"PLANNER", "PRODUCTION", "GENERAL_MANAGER", "ADMIN"})

ALL_COLUMNS = [
    "result_number", "source_ref", "material_code",
    "kit_status", "shortage_qty", "checked_at",
]


class KittingShortageParams(BoundIntent):
    kit_status: str = Field(default="SHORT")   # KitStatus 枚举，由形状校验
    source_ref: str | None = None
    limit: int = Field(default=20, ge=1, le=200)


def _value(enum_value: object) -> str:
    return enum_value.value if hasattr(enum_value, "value") else str(enum_value)


def run(db: Session, p: KittingShortageParams, role: str) -> QueryResult:
    query = db.query(KittingResult).filter(
        KittingResult.kit_status == KitStatus(p.kit_status)
    )
    if p.source_ref:
        query = query.filter(KittingResult.source_ref == p.source_ref)
    rows = (
        query.order_by(KittingResult.checked_at.desc())
        .limit(p.limit)
        .all()
    )
    data = []
    sources = []
    for item in rows:
        data.append({
            "result_number": item.result_number,
            "source_ref": item.source_ref,
            "material_code": item.material_code,
            "kit_status": _value(item.kit_status),
            "shortage_qty": float(item.shortage_qty or 0),
            "checked_at": item.checked_at.isoformat() if item.checked_at else None,
        })
        sources.append(Provenance(
            table="kitting_results", record_key=item.result_number,
            ontology_iri=NS + "KittingResult",
        ))
    return QueryResult(columns=list(ALL_COLUMNS), rows=data, sources=sources)


SPEC = IntentSpec(
    code=CODE,
    label="齐套缺口",
    description="列出齐套状态为短缺的齐套结果，可按生产订单/计划订单号精确过滤。",
    entities=["KittingResult"],
    primary_entity="KittingResult",
    params_model=KittingShortageParams,
    defaults={"kit_status": "SHORT", "limit": 20},
    domains=["planning"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={"*": list(ALL_COLUMNS)},
    output_enums={"kit_status": "KitStatus"},
    record_key=["result_number"],
    downlink="/pp/kitting",
    shacl_coverage="partial",
    provenance_kind="event",
    formula="kitting_results.kit_status = 'SHORT'；可选 source_ref 精确匹配；按 checked_at 倒序；"
            "shortage_qty 为空按 0 处理",
    handler=run,
)
