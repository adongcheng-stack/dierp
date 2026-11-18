"""经营看板 router：六域 KPI 只读汇总（ADR-20261118-01 同类派生查询）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.services.planning.management_dashboard import ManagementDashboard

router = APIRouter()


@router.get("/management")
def management_overview(db: Session = Depends(get_db)):
    """销售/生产/质量/设备/成本/交期 六域 KPI + 自动点评。"""
    data = ManagementDashboard.overview(db)
    data["insights"] = ManagementDashboard.insights(data)
    return data
