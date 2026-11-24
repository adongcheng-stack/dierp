"""意图 6：超期应收（设计 §7.2 #6、§7.2.1 #6）。"""
from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import Field
from sqlalchemy.orm import Session

from backend.common.models.planning import InvoiceStatus, SalesInvoice
from backend.services.ai.intent import BoundIntent, IntentSpec, Provenance, QueryResult
from backend.services.ai.ontology_service import NS

CODE = "ar_overdue"

ALLOWED_ROLES = frozenset({"FINANCE", "GENERAL_MANAGER", "ADMIN"})

ALL_COLUMNS = [
    "invoice_number", "customer_id", "customer_name", "status", "due_date",
    "amount", "received_amount", "outstanding", "days_overdue",
]
# 金额类列默认裁剪（评审 I10）
SAFE_COLUMNS = [
    "invoice_number", "customer_id", "customer_name", "status", "due_date", "days_overdue",
]

_OPEN_STATUSES = (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID)


class ArOverdueParams(BoundIntent):
    days_overdue: int = Field(default=30, ge=1, le=365)
    customer_id: str | None = None
    invoice_number: str | None = None


def _value(enum_value: object) -> str:
    return enum_value.value if hasattr(enum_value, "value") else str(enum_value)


def run(db: Session, p: ArOverdueParams, role: str) -> QueryResult:
    now = datetime.now()
    cutoff = now - timedelta(days=p.days_overdue)
    query = db.query(SalesInvoice).filter(
        # DRAFT/PAID/CANCELLED 不属于未收应收
        SalesInvoice.status.in_(list(_OPEN_STATUSES)),
        SalesInvoice.received_amount < SalesInvoice.amount,
        SalesInvoice.amount > 0,
        SalesInvoice.due_date < cutoff,
    )
    if p.customer_id:
        query = query.filter(SalesInvoice.customer_id == p.customer_id)
    if p.invoice_number:
        query = query.filter(SalesInvoice.invoice_number == p.invoice_number)
    rows = query.order_by(SalesInvoice.due_date.asc()).limit(200).all()

    data = []
    sources = []
    for invoice in rows:
        amount = float(invoice.amount or 0)
        received = float(invoice.received_amount or 0)
        data.append({
            "invoice_number": invoice.invoice_number,
            "customer_id": invoice.customer_id,
            "customer_name": invoice.customer_name,
            "status": _value(invoice.status),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "amount": amount,
            "received_amount": received,
            "outstanding": amount - received,
            "days_overdue": (now - invoice.due_date).days,
        })
        sources.append(Provenance(
            table="sales_invoices", record_key=invoice.invoice_number,
            ontology_iri=NS + "SalesInvoice",
        ))
    return QueryResult(columns=list(ALL_COLUMNS), rows=data, sources=sources)


SPEC = IntentSpec(
    code=CODE,
    label="超期应收",
    description="列出发票已过到期日仍未收足的应收，按到期日排序。",
    entities=["SalesInvoice", "ReceivableEntry"],
    primary_entity="SalesInvoice",
    params_model=ArOverdueParams,
    defaults={"days_overdue": 30},
    domains=["finance"],
    allowed_roles=ALLOWED_ROLES,
    output_fields={
        "*": SAFE_COLUMNS,
        "FINANCE": list(ALL_COLUMNS),
        "GENERAL_MANAGER": list(ALL_COLUMNS),
        "ADMIN": list(ALL_COLUMNS),
    },
    output_enums={"status": "InvoiceStatus"},
    record_key=["invoice_number"],
    downlink="/sd/invoices",
    # 设计 §7.2 写 none，但 SalesInvoiceShape 实际约束了 invoiceNumber（sh:path 存在），
    # 按目录的 shape_paths 计算为 partial（1/2 参数）；以可验证的计算结果为准。
    shacl_coverage="partial",
    provenance_kind="document",
    formula="status IN (ISSUED, PARTIALLY_PAID) 且 received_amount < amount 且 amount > 0 "
            "且 due_date < now - days_overdue；未收 = amount - received_amount",
    handler=run,
)
