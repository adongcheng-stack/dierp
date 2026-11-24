"""意图 8：MES 工单进度（跨库只读，默认关闭）。

给定 MES 工单号，返回该工单的工序任务与报工记录。数据来自 MES ``mesdb``，
不写入任何 ERP 表；未启用或未配置 MES 时由客户端抛 ``AI_MES_UNAVAILABLE``。

SHACL 说明：MES 工单号是独立业务编号（如 ``GD-20260914-00001``），不满足
ERP ``ProductionOrderShape`` 的 ``^PO-YYYYMMDD-XXXX$``。因此本意图显式绑定
本体中的 ``MesWorkOrderShape``（工单号/状态/数量/计划时间），并通过
``shacl_params`` 把参数映射到形状属性；工序与报工结果在执行器侧按
``MesProcessTaskShape`` / ``MesProcessReportShape`` 校验。所有约束只来自
``ontology/src``，此处仅声明绑定关系。
"""
from __future__ import annotations

from pydantic import Field
from sqlalchemy.orm import Session

from backend.services.ai.intent import BoundIntent, IntentSpec, QueryResult
from backend.services.ai.mes_client import COLUMNS, fetch_work_order_progress

CODE = "mes_work_order_progress"

ALLOWED_ROLES = frozenset({"PLANNER", "PRODUCTION", "GENERAL_MANAGER", "ADMIN"})

ALL_COLUMNS = list(COLUMNS)


class MesWorkOrderProgressParams(BoundIntent):
    work_order_no: str = Field(min_length=1, max_length=50)
    limit: int = Field(default=200, ge=1, le=200)


def run(db: Session, p: MesWorkOrderProgressParams, role: str) -> QueryResult:
    # db 仅用于保持与 ERP 意图一致的 handler 签名；MES 查询走独立只读连接
    return fetch_work_order_progress(p.work_order_no, limit=p.limit)


SPEC = IntentSpec(
    code=CODE,
    label="MES 工单进度",
    description="按 MES 工单号查询该工单的工序任务与报工记录（跨库只读，默认关闭）。",
    entities=["ProductionOrder", "ScheduledOperation"],
    primary_entity="ProductionOrder",
    params_model=MesWorkOrderProgressParams,
    defaults={"limit": 200},
    domains=["pp"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={"*": list(ALL_COLUMNS)},
    output_enums={
        "order_status": "MesWorkOrderStatus",
        "task_status": "MesProcessTaskStatus",
    },
    record_key=["row_key"],
    downlink="/pp/production-orders",
    shacl_coverage="full",
    shacl_shape="MesWorkOrderShape",
    shacl_params={"work_order_no": "mesWorkOrderNo"},
    provenance_kind="aggregate",
    formula="按 prd_work_order.work_order_no 定位工单；"
            "prd_process_task / prd_process_report 按 work_order_id 关联；"
            "每条报工一行，无报工的工序单独一行，工单无工序时返回工单汇总行",
    handler=run,
    source_system="MES",
)
