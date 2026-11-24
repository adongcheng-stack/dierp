"""意图 5：客户信用占用（设计 §7.2 #5、§7.2.1 #5）。

取数口径（评审 I4）：
- 应收余额 = SUM(receivable_entries.amount)，流水按带符号金额记账（INVOICE 正、RECEIPT 负、
  RECEIPT_REVERSE 正、INVOICE_REVERSE 负、ADJUST 按录入符号），查询侧不再按类型二次拼符号；
- 未完成订单 = sales_orders.status IN (APPROVED, IN_PRODUCTION) 的 total_amount 之和；
- 占用比 = (ar_balance + open_order_amount) / credit_limit，credit_limit <= 0 时返回 None。
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.common.models.planning import ReceivableEntry
from backend.common.models.sd import Customer, SalesOrder, SalesOrderStatus
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "customer_credit_status"

ALLOWED_ROLES = frozenset({"SALES_MANAGER", "FINANCE", "GENERAL_MANAGER", "ADMIN"})

ALL_COLUMNS = [
    "customer_id", "customer_name", "credit_limit",
    "ar_balance", "open_order_amount", "open_order_count", "credit_usage_ratio",
]
# 金额类列默认裁剪（评审 I10）：财务/销售经理/总经理/管理员可见全列
SAFE_COLUMNS = ["customer_id", "customer_name", "open_order_count"]

_OPEN_STATUSES = (SalesOrderStatus.APPROVED, SalesOrderStatus.IN_PRODUCTION)


class CustomerCreditStatusParams(BoundIntent):
    customer_id: str


def run(db: Session, p: CustomerCreditStatusParams, role: str) -> QueryResult:
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == p.customer_id)
        .limit(1)
        .first()
    )
    if customer is None:
        return QueryResult(
            columns=list(ALL_COLUMNS), rows=[], sources=[], reason="customer_not_found",
        )

    ar_balance = db.query(
        func.coalesce(func.sum(ReceivableEntry.amount), 0)
    ).filter(ReceivableEntry.customer_id == p.customer_id).scalar()
    open_amount, open_count = db.query(
        func.coalesce(func.sum(SalesOrder.total_amount), 0),
        func.count(SalesOrder.id),
    ).filter(
        SalesOrder.customer_id == p.customer_id,
        SalesOrder.status.in_(list(_OPEN_STATUSES)),
    ).one()

    credit_limit = float(customer.credit_limit or 0)
    ar_balance = float(ar_balance or 0)
    open_amount = float(open_amount or 0)
    ratio = round((ar_balance + open_amount) / credit_limit, 4) if credit_limit > 0 else None

    row = {
        "customer_id": customer.customer_id,
        "customer_name": customer.legal_name,
        "credit_limit": credit_limit,
        "ar_balance": ar_balance,
        "open_order_amount": open_amount,
        "open_order_count": int(open_count or 0),
        "credit_usage_ratio": ratio,
    }
    return QueryResult(
        columns=list(ALL_COLUMNS),
        rows=[row],
        sources=[Provenance(
            table="customers", record_key=customer.customer_id,
            ontology_iri=NS + "Customer",
        )],
    )


SPEC = IntentSpec(
    code=CODE,
    label="客户信用占用",
    description="按客户汇总应收余额与未完成订单金额，计算信用占用比。",
    entities=["Customer", "SalesOrder", "ReceivableEntry"],
    primary_entity="Customer",
    params_model=CustomerCreditStatusParams,
    defaults={},
    domains=["sd", "finance"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={
        "*": SAFE_COLUMNS,
        "SALES_MANAGER": list(ALL_COLUMNS),
        "FINANCE": list(ALL_COLUMNS),
        "GENERAL_MANAGER": list(ALL_COLUMNS),
        "ADMIN": list(ALL_COLUMNS),
    },
    record_key=["customer_id"],
    downlink="/sd/customers",
    shacl_coverage="none",
    provenance_kind="aggregate",
    formula="ar_balance = SUM(receivable_entries.amount)（带符号）；"
            "open_order_amount = SUM(sales_orders.total_amount) WHERE status IN (APPROVED, IN_PRODUCTION)；"
            "credit_usage_ratio = (ar_balance + open_order_amount) / NULLIF(credit_limit, 0)，"
            "credit_limit<=0 时比值为 null",
    handler=run,
)
