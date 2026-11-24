"""意图 3：低于安全库存的物料（设计 §7.2 #3、§7.2.1 #3）。"""
from __future__ import annotations

from pydantic import Field
from sqlalchemy.orm import Session

from backend.common.models.mm import Material
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "material_below_safety"

ALLOWED_ROLES = frozenset({"WAREHOUSE", "PLANNER", "PRODUCTION", "GENERAL_MANAGER"})

ALL_COLUMNS = [
    "material_code", "material_name", "material_type",
    "current_stock", "safety_stock", "shortage",
]


class MaterialBelowSafetyParams(BoundIntent):
    material_type: str | None = None          # 由 MaterialShape 的 sh:in 闭包校验
    limit: int = Field(default=50, ge=1, le=200)


def run(db: Session, p: MaterialBelowSafetyParams, role: str) -> QueryResult:
    query = db.query(Material).filter(Material.current_stock < Material.safety_stock)
    if p.material_type:
        query = query.filter(Material.material_type == p.material_type)
    rows = (
        query.order_by((Material.safety_stock - Material.current_stock).desc())
        .limit(p.limit)
        .all()
    )
    data = []
    sources = []
    for m in rows:
        current = float(m.current_stock or 0)
        safety = float(m.safety_stock or 0)
        data.append({
            "material_code": m.material_code,
            "material_name": m.material_name,
            "material_type": m.material_type,
            "current_stock": current,
            "safety_stock": safety,
            "shortage": safety - current,
        })
        sources.append(Provenance(
            table="materials", record_key=m.material_code, ontology_iri=NS + "Material",
        ))
    return QueryResult(columns=list(ALL_COLUMNS), rows=data, sources=sources)


SPEC = IntentSpec(
    code=CODE,
    label="物料低于安全库存",
    description="列出当前库存低于安全库存的物料，按缺口排序。",
    entities=["Material"],
    primary_entity="Material",
    params_model=MaterialBelowSafetyParams,
    defaults={"limit": 50},
    domains=["mm"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={"*": list(ALL_COLUMNS)},
    record_key=["material_code"],
    downlink="/mm/materials",
    shacl_coverage="full",
    provenance_kind="aggregate",
    formula="current_stock < safety_stock；缺额 = safety_stock - current_stock；"
            "按缺口降序（safety_stock<=0 的行仍返回）",
    handler=run,
)
