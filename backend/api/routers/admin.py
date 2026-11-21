"""管理域：审计日志查询（仅 ADMIN 可读，由本体读权限策略兜底）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.common.models.audit import OperationLog

router = APIRouter()


@router.get("/operation-logs")
async def list_operation_logs(
    username: Optional[str] = Query(None, description="操作人筛选项"),
    method: Optional[str] = Query(None, description="HTTP 方法筛选项"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """返回最近的写操作审计记录（倒序）。"""
    query = db.query(OperationLog)
    if username:
        query = query.filter(OperationLog.username == username)
    if method:
        query = query.filter(OperationLog.method == method.upper())
    rows = query.order_by(OperationLog.created_at.desc(), OperationLog.id.desc()).limit(limit).all()
    return {
        "total": len(rows),
        "items": [
            {
                "id": row.id,
                "request_id": row.request_id,
                "username": row.username,
                "role": row.role,
                "method": row.method,
                "path": row.path,
                "status_code": row.status_code,
                "client_ip": row.client_ip,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


# ── 数据导入导出（JSON / CSV）──────────────────────────────────────────────
import csv
import io
from datetime import date, datetime
from decimal import Decimal

from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect

from backend.common.models import mm, planning, pp, sd

# 白名单：模型 + 自然键。导入时仅创建，不覆盖既有业务单据。
EXPORTABLE: dict[str, tuple[object, str]] = {
    "customers": (sd.Customer, "customer_id"),
    "materials": (mm.Material, "material_code"),
    "suppliers": (planning.Supplier, "supplier_code"),
    "sales-orders": (sd.SalesOrder, "order_number"),
    "production-orders": (pp.ProductionOrder, "order_number"),
    "purchase-orders": (planning.PurchaseOrder, "purchase_order_number"),
}
_BASE_FIELDS = {"id", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"}


class ImportPayload(BaseModel):
    rows: list[dict]


def _serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _model_columns(model) -> list[str]:
    excluded = _BASE_FIELDS | {"password_hash"}
    return [column.name for column in sa_inspect(model).columns if column.name not in excluded]


@router.get("/export/{entity}")
async def export_entities(
    entity: str,
    format: str = "json",
    db: Session = Depends(get_db),
):
    """导出主数据/单据为 JSON 或 CSV（仅 ADMIN）。"""
    if entity not in EXPORTABLE:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"不支持导出实体: {entity}")
    model, _ = EXPORTABLE[entity]
    columns = _model_columns(model)
    rows = db.query(model).filter(model.is_deleted.is_(False)).all()
    records = [
        {name: _serialize(getattr(row, name, None)) for name in columns}
        for row in rows
    ]

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)
        return Response(
            content="\ufeff" + buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{entity}.csv"'},
        )
    return {"entity": entity, "total": len(records), "items": records}


@router.post("/import/{entity}")
async def import_entities(
    entity: str,
    payload: ImportPayload,
    db: Session = Depends(get_db),
):
    """批量导入：仅创建新行，自然键已存在则跳过（幂等，不覆盖业务数据）。"""
    from fastapi import HTTPException

    if entity not in EXPORTABLE:
        raise HTTPException(status_code=404, detail=f"不支持导入实体: {entity}")
    model, natural_key = EXPORTABLE[entity]
    allowed = set(_model_columns(model))
    created = 0
    skipped = 0
    for raw in payload.rows:
        key_value = raw.get(natural_key)
        if not key_value:
            skipped += 1
            continue
        exists = db.query(model).filter(
            getattr(model, natural_key) == key_value,
            model.is_deleted.is_(False),
        ).first()
        if exists is not None:
            skipped += 1
            continue
        db.add(model(**{key: value for key, value in raw.items() if key in allowed}))
        created += 1
    if created:
        db.commit()
    return {"entity": entity, "created": created, "skipped": skipped}
