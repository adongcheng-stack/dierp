"""A4 异常解读：驾驶舱 KPI 规则告警 + MRP 未处理异常 → 结构化告警与解读文本。

只读派生层：
- KPI 阈值与比较完全复用 ``backend.services.dashboard.alerts.build_alerts``，
  数据复用 ``ManagementDashboard.overview`` / ``finance_kpi`` / ``progress_rows``，
  本模块不重算任何指标；
- MRP 角色白名单来自意图注册表 ``open_mrp_exceptions``；
- 解读文本默认走确定性模板；LLM 只负责润色已算好的结论，输出必须通过数字回查，
  失败/配额耗尽时静默退回模板，不影响接口可用性。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.common.models.dashboard import DashboardRule
from backend.common.models.planning import (
    EquipmentFailure,
    FailureStatus,
    InvoiceStatus,
    MrpException,
    NcrStatus,
    NonConformanceReport,
    ResolutionStatus,
    SalesInvoice,
    SupplierInvoice,
    SupplierInvoiceStatus,
)
from backend.common.models.pp import ProductionOrder
from backend.common.models.sd import SalesOrder
from backend.services.ai.answer import numbers_subset
from backend.services.ai.config import get_settings
from backend.services.ai.intents import INTENT_REGISTRY
from backend.services.ai.llm import get_llm_client
from backend.services.ai.ontology_service import get_ontology_service
from backend.services.dashboard.alerts import build_alerts
from backend.services.dashboard.kpi import finance_kpi, progress_rows
from backend.services.planning.management_dashboard import (
    NCR_OPEN_VALUES,
    PRODUCTION_OPEN_VALUES,
    SALES_OPEN_VALUES,
    ManagementDashboard,
)

SEVERITY_ORDER = {"CRITICAL": 2, "WARNING": 1, "INFO": 0}
MAX_EVIDENCE = 5
MAX_MRP_ALERTS = 20
WINDOW_DAYS = {"7d": 7, "30d": 30}
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")

# 指标 → 下钻路径 / 数值类型（ratio 用百分比展示，amount 走金额裁剪，count/qty 为数量）
_METRIC_META: dict[str, dict[str, str]] = {
    "equipment.oee": {"drilldown": "/dashboard/management", "kind": "ratio"},
    "quality.first_pass_rate": {"drilldown": "/dashboard/management", "kind": "ratio"},
    "production.completion_rate": {"drilldown": "/dashboard/production", "kind": "ratio"},
    "production.delayed_orders": {"drilldown": "/dashboard/production-progress", "kind": "count"},
    "progress.avg_completion_rate": {"drilldown": "/dashboard/production-progress", "kind": "ratio"},
    "finance.collection_rate": {"drilldown": "/dashboard/finance", "kind": "ratio"},
    "finance.payable_open": {"drilldown": "/dashboard/finance", "kind": "amount"},
    "sales.open_orders": {"drilldown": "/dashboard/sales", "kind": "count"},
    "sales.amount_open": {"drilldown": "/dashboard/sales", "kind": "amount"},
    "delivery.delayed_sales_orders": {"drilldown": "/dashboard/sales", "kind": "count"},
    "cost.variance_total": {"drilldown": "/dashboard/management", "kind": "amount"},
    "mrp_exception.shortage_qty": {"drilldown": "/pp/planning-exceptions", "kind": "qty"},
}

# 金额类指标在无金额权限角色下的固定建议（不含任何数字）
_MASKED_SUGGESTION = {
    "finance.payable_open": "应付余额超过预警阈值，请注意资金安排",
    "sales.amount_open": "在手订单金额低于预警阈值，需拓展商机",
    "cost.variance_total": "存在成本差异，金额已按角色裁剪",
}


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _label(enum_name: str, code: str | None) -> str:
    """枚举码 → 中文标签；唯一来源是本体的 mappings.json labels。"""
    if code is None:
        return "未知"
    return get_ontology_service().enum_label(enum_name, code)


def _value(value: Any) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _amount_visible_roles() -> frozenset[str]:
    """从意图注册表推导可看金额的角色，避免在解读层硬编码角色名。"""
    spec = INTENT_REGISTRY.get("customer_credit_status")
    if spec is None:
        return frozenset()
    base = set(spec.output_fields.get("*", []))
    roles = {
        role
        for role, columns in spec.output_fields.items()
        if role != "*" and set(columns) != base
    }
    return frozenset(roles & set(spec.allowed_roles))


def _kind(metric: str) -> str:
    return _METRIC_META.get(metric, {}).get("kind", "count")


def _drilldown(metric: str) -> str | None:
    return _METRIC_META.get(metric, {}).get("drilldown")


def _format_value(metric: str, value: float | None) -> str:
    if value is None:
        return "—"
    kind = _kind(metric)
    if kind == "ratio":
        return f"{value:.0%}"
    if kind == "amount":
        return f"{value:.2f}"
    if kind == "qty":
        return f"{value:.2f}"
    return f"{value:.0f}"


def _deviation_text(metric: str, deviation: float | None) -> str:
    if deviation is None:
        return "金额类指标已按角色裁剪"
    kind = _kind(metric)
    if deviation == 0:
        return "与阈值持平"
    direction = "低于" if deviation < 0 else "高于"
    if kind == "ratio":
        return f"{direction}阈值 {abs(deviation) * 100:.1f} 个百分点"
    if kind == "amount":
        return f"{direction}阈值 {abs(deviation):.2f}"
    return f"{direction}阈值 {abs(deviation):.0f}"


def _evidence(table: str, record_ref: Any, label: Any = None) -> dict[str, str]:
    return {
        "table": table,
        "record_ref": str(record_ref),
        "label": str(label if label is not None else record_ref),
    }


def _cap(items: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    return items[:MAX_EVIDENCE], len(items)


def _status_in(value: Any, allowed: set[str]) -> bool:
    return (_value(value) or "") in allowed


def _evidence_for(
    metric: str,
    db: Session,
    overview: dict[str, Any],
    progress: dict[str, Any],
    threshold: float,
    now: datetime,
) -> tuple[list[dict[str, str]], int]:
    """按指标查询关联单据/记录；返回（最多 5 条证据, 证据总数）。"""
    items: list[dict[str, str]] = []

    if metric == "equipment.oee":
        centers = [
            wc for wc in overview["equipment"].get("work_centers", [])
            if _num(wc.get("oee")) < threshold
        ]
        items.extend(_evidence("work_centers", wc["work_center_id"]) for wc in centers)
        failures = (
            db.query(EquipmentFailure)
            .filter(
                EquipmentFailure.is_deleted.is_(False),
                EquipmentFailure.status == FailureStatus.OPEN,
            )
            .order_by(EquipmentFailure.occurred_at.desc())
            .all()
        )
        items.extend(_evidence("equipment_failures", row.failure_number) for row in failures)

    elif metric == "quality.first_pass_rate":
        rows = (
            db.query(NonConformanceReport)
            .filter(NonConformanceReport.is_deleted.is_(False))
            .order_by(NonConformanceReport.id.desc())
            .all()
        )
        items.extend(
            _evidence("non_conformance_reports", row.ncr_number)
            for row in rows
            if _status_in(row.status, NCR_OPEN_VALUES)
        )

    elif metric == "production.completion_rate":
        rows = (
            db.query(ProductionOrder)
            .filter(ProductionOrder.is_deleted.is_(False))
            .order_by(ProductionOrder.order_number)
            .all()
        )
        items.extend(
            _evidence("production_orders", row.order_number)
            for row in rows
            if _status_in(row.status, PRODUCTION_OPEN_VALUES)
        )

    elif metric == "production.delayed_orders":
        rows = (
            db.query(ProductionOrder)
            .filter(ProductionOrder.is_deleted.is_(False))
            .order_by(ProductionOrder.planned_finish_date)
            .all()
        )
        items.extend(
            _evidence("production_orders", row.order_number)
            for row in rows
            if _status_in(row.status, PRODUCTION_OPEN_VALUES)
            and row.planned_finish_date is not None
            and row.planned_finish_date < now
        )

    elif metric == "delivery.delayed_sales_orders":
        rows = (
            db.query(SalesOrder)
            .filter(SalesOrder.is_deleted.is_(False))
            .order_by(SalesOrder.delivery_date)
            .all()
        )
        items.extend(
            _evidence("sales_orders", row.order_number)
            for row in rows
            if _status_in(row.status, SALES_OPEN_VALUES)
            and row.delivery_date is not None
            and row.delivery_date < now
        )

    elif metric in ("sales.open_orders", "sales.amount_open"):
        rows = (
            db.query(SalesOrder)
            .filter(SalesOrder.is_deleted.is_(False))
            .order_by(SalesOrder.order_number)
            .all()
        )
        items.extend(
            _evidence("sales_orders", row.order_number)
            for row in rows
            if _status_in(row.status, SALES_OPEN_VALUES)
        )

    elif metric == "finance.collection_rate":
        rows = (
            db.query(SalesInvoice)
            .filter(
                SalesInvoice.is_deleted.is_(False),
                SalesInvoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
            )
            .order_by(SalesInvoice.due_date)
            .all()
        )
        items.extend(
            _evidence("sales_invoices", row.invoice_number)
            for row in rows
            if _num(row.amount) - _num(row.received_amount) > 0
        )

    elif metric == "finance.payable_open":
        rows = (
            db.query(SupplierInvoice)
            .filter(
                SupplierInvoice.is_deleted.is_(False),
                SupplierInvoice.status == SupplierInvoiceStatus.CONFIRMED,
            )
            .order_by(SupplierInvoice.invoice_date)
            .all()
        )
        items.extend(_evidence("supplier_invoices", row.invoice_number) for row in rows)

    elif metric == "progress.avg_completion_rate":
        items.extend(
            _evidence(
                "production_progress",
                f"{row['production_order_number']}-{row['operation_no']}",
            )
            for row in progress.get("rows", [])
            if _num(row.get("completion_rate")) < threshold
        )

    return _cap(items)


def _attribution(
    metric: str,
    overview: dict[str, Any],
    progress: dict[str, Any],
    evidence_total: int,
) -> str:
    if metric == "equipment.oee":
        centers = overview["equipment"].get("work_centers", [])
        worst = min(centers, key=lambda wc: _num(wc.get("oee")), default=None)
        if worst:
            return (
                f"最差工作中心 {worst['work_center_id']} 的 OEE 为 "
                f"{_num(worst.get('oee')):.0%}，停机 {_num(worst.get('downtime_hours')):.1f}h"
            )
        return "设备效率整体偏低"
    if metric == "quality.first_pass_rate":
        quality = overview["quality"]
        return (
            f"{quality.get('ncrs_open', 0)} 张未关闭不合格品，"
            f"其中 {quality.get('ncrs_equipment', 0)} 张判定为设备原因"
        )
    if metric == "production.completion_rate":
        return f"{overview['production'].get('open_orders', 0)} 张在制工单待完成"
    if metric == "production.delayed_orders":
        return f"{evidence_total} 张工单已过计划完工日"
    if metric == "delivery.delayed_sales_orders":
        return f"{evidence_total} 张销售订单已过承诺交期"
    if metric == "finance.collection_rate":
        return f"{evidence_total} 张销售发票尚未收清"
    if metric == "finance.payable_open":
        return f"{evidence_total} 张已确认采购发票待付款"
    if metric == "progress.avg_completion_rate":
        return f"{evidence_total} 道工序完成率偏低"
    if metric == "sales.open_orders":
        return f"{evidence_total} 张销售订单尚未关闭"
    if metric == "sales.amount_open":
        return f"{evidence_total} 张未关闭销售订单在手"
    if metric == "cost.variance_total":
        variance_by_type = overview["cost"].get("variance_by_type", {})
        if variance_by_type:
            biggest = max(variance_by_type, key=lambda key: abs(variance_by_type[key]))
            return f"{_label('VarianceType', biggest)} 差异贡献最大"
        return "存在成本差异"
    return ""


def _rule_operator(db: Session, codes: set[str]) -> dict[str, str]:
    rules = (
        db.query(DashboardRule)
        .filter(DashboardRule.is_deleted.is_(False), DashboardRule.code.in_(codes))
        .all()
    )
    return {rule.code: _value(rule.operator) or "GT" for rule in rules}


def _scope_alerts(db: Session, scopes: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    seen_metrics: set[str] = set()
    for scope, data in scopes:
        for alert in build_alerts(db, scope, data):
            metric = alert["metric"]
            if metric in seen_metrics:
                continue
            seen_metrics.add(metric)
            alerts.append(alert)
    return alerts


def _enrich(
    db: Session,
    raw_alerts: list[dict[str, Any]],
    overview: dict[str, Any],
    progress: dict[str, Any],
    role: str,
    now: datetime,
) -> list[dict[str, Any]]:
    operators = _rule_operator(db, {alert["code"] for alert in raw_alerts})
    amount_visible = role in _amount_visible_roles()
    enriched: list[dict[str, Any]] = []

    for alert in raw_alerts:
        metric = alert["metric"]
        evidence, evidence_total = _evidence_for(
            metric, db, overview, progress, float(alert["threshold"]), now
        )
        if not evidence:
            # 验收要求：无证据的告警不输出
            continue

        kind = _kind(metric)
        amount_masked = kind == "amount" and not amount_visible
        current = None if amount_masked else round(float(alert["actual"]), 4)
        threshold = None if amount_masked else round(float(alert["threshold"]), 4)
        deviation = None
        if current is not None and threshold is not None:
            deviation = round(current - threshold, 4)

        if amount_masked:
            suggestion = _MASKED_SUGGESTION.get(metric, "金额类指标已按角色裁剪")
        else:
            suggestion = alert.get("message") or ""

        enriched.append({
            "code": alert["code"],
            "title": alert["name"],
            "severity": alert["level"],
            "scope": alert["scope"],
            "metric": metric,
            "value_kind": kind,
            "current_value": current,
            "threshold": threshold,
            "operator": operators.get(alert["code"], "GT"),
            "deviation": deviation,
            "deviation_text": _deviation_text(metric, deviation),
            "evidence": evidence,
            "evidence_total": evidence_total,
            "drilldown": _drilldown(metric),
            "attribution": _attribution(metric, overview, progress, evidence_total),
            "suggestion": suggestion,
            "amount_masked": amount_masked,
        })
    return enriched


def _mrp_alerts(db: Session, window: str, role: str) -> tuple[list[dict[str, Any]], bool]:
    spec = INTENT_REGISTRY.get("open_mrp_exceptions")
    if spec is None or role not in spec.allowed_roles:
        return [], False

    cutoff = datetime.now() - timedelta(days=WINDOW_DAYS[window])
    rows = (
        db.query(MrpException)
        .filter(MrpException.resolution_status == ResolutionStatus.OPEN)
        .order_by(MrpException.shortage_qty.desc())
        .all()
    )
    rows = [
        row for row in rows
        if row.shortage_date is None or row.shortage_date >= cutoff
    ]
    truncated = len(rows) > MAX_MRP_ALERTS
    alerts = []
    for row in rows[:MAX_MRP_ALERTS]:
        severity = _value(row.severity) or "INFO"
        if severity not in SEVERITY_ORDER:
            severity = "INFO"
        exception_type = _value(row.exception_type) or "UNKNOWN"
        exception_label = _label("MrpExceptionType", exception_type)
        quantity = round(_num(row.shortage_qty), 2)
        material = row.material_code or "-"
        alerts.append({
            "code": f"MRP-{row.id}",
            "title": f"MRP 异常：{exception_label}",
            "severity": severity,
            "scope": "PLANNING",
            "metric": "mrp_exception.shortage_qty",
            "value_kind": "qty",
            "current_value": quantity,
            "threshold": 0.0,
            "operator": "GT",
            "deviation": quantity,
            "deviation_text": f"高于阈值 {quantity:.2f}",
            "evidence": [_evidence("mrp_exceptions", row.id, material)],
            "evidence_total": 1,
            "drilldown": "/pp/planning-exceptions",
            "attribution": f"{exception_label} 物料 {material} 缺口 {quantity:.2f}",
            "suggestion": row.suggestion or "请检查 MRP 运行结果并处理缺口",
            "amount_masked": False,
        })
    return alerts, truncated


def _sort_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scope_order = {
        "MANAGEMENT": 0, "PRODUCTION": 1, "PROGRESS": 2,
        "FINANCE": 3, "SALES": 4, "PLANNING": 5, "HOME": 6,
    }
    return sorted(
        alerts,
        key=lambda item: (
            -SEVERITY_ORDER.get(item["severity"], 0),
            scope_order.get(item["scope"], 9),
            item["code"],
        ),
    )


def _summary(alerts: list[dict[str, Any]], truncated: bool) -> dict[str, Any]:
    return {
        "total": len(alerts),
        "critical": sum(1 for item in alerts if item["severity"] == "CRITICAL"),
        "warning": sum(1 for item in alerts if item["severity"] == "WARNING"),
        "info": sum(1 for item in alerts if item["severity"] == "INFO"),
        "truncated": truncated,
    }


def _template_narrative(window: str, alerts: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    days = WINDOW_DAYS[window]
    if not alerts:
        return f"近 {days} 天未发现需要关注的异常。"

    lines = [
        f"近 {days} 天共发现 {summary['total']} 项异常："
        f"严重 {summary['critical']} 项、警告 {summary['warning']} 项、"
        f"提示 {summary['info']} 项。"
    ]
    for alert in alerts:
        line = (
            f"【{_label('ExceptionSeverity', alert['severity'])}】"
            f"{alert['title']}：当前 {_format_value(alert['metric'], alert['current_value'])}，"
            f"阈值 {_format_value(alert['metric'], alert['threshold'])}，"
            f"{alert['deviation_text']}，关联单据 {alert['evidence_total']} 张"
        )
        if alert["attribution"]:
            line += f"；{alert['attribution']}"
        if alert["suggestion"]:
            line += f"；建议：{alert['suggestion']}"
        lines.append(line + "。")
    return "".join(lines)


def _fact_set(alerts: list[dict[str, Any]], summary: dict[str, Any], window: str) -> set[float]:
    """数字回查白名单：全部来自实际查询得到的结构化字段与确定性模板。"""
    facts: set[float] = {0.0, float(WINDOW_DAYS[window]), float(summary["total"])}
    facts.update(float(summary[key]) for key in ("critical", "warning", "info"))
    for alert in alerts:
        facts.add(float(alert["evidence_total"]))
        facts.add(float(len(alert["evidence"])))
        for key in ("current_value", "threshold", "deviation"):
            value = alert[key]
            if value is None:
                continue
            facts.add(round(float(value), 4))
            facts.add(round(float(value), 2))
            facts.add(round(float(value), 0))
            if _kind(alert["metric"]) == "ratio":
                facts.add(round(float(value) * 100, 1))
                facts.add(round(float(value) * 100, 0))
    return facts


def _llm_narrative(
    template: str,
    alerts: list[dict[str, Any]],
    summary: dict[str, Any],
    window: str,
    facts: set[float],
) -> tuple[str, str, str]:
    """返回（文本, 来源, 模型）；失败一律退回模板。"""
    settings = get_settings()
    client = get_llm_client()
    if client is None or not settings.ai_llm_narration_enabled or not alerts:
        return template, "template", "deterministic-v1"

    allow_external = settings.ai_llm_allow_external_data
    payload_alerts = []
    for alert in alerts:
        amount_masked = alert["amount_masked"] or (
            not allow_external and _kind(alert["metric"]) == "amount"
        )
        suggestion = alert["suggestion"]
        if not allow_external and _kind(alert["metric"]) == "amount":
            suggestion = _MASKED_SUGGESTION.get(alert["metric"], "金额类指标已按角色裁剪")
        payload_alerts.append({
            "code": alert["code"],
            "title": alert["title"],
            "severity": _label("ExceptionSeverity", alert["severity"]),
            "metric": alert["metric"],
            "unit": _kind(alert["metric"]),
            "current_value": None if amount_masked else alert["current_value"],
            "threshold": None if amount_masked else alert["threshold"],
            "deviation": None if amount_masked else alert["deviation"],
            "evidence_total": alert["evidence_total"],
            "suggestion": suggestion,
            # 行级标识（工作中心/物料/单号）仅在允许出域时随草稿发送
            "attribution": alert["attribution"] if allow_external else None,
        })
    payload: dict[str, Any] = {
        "task": "insight_narration",
        "window": window,
        "summary": summary,
        "alerts": payload_alerts,
        "instruction": (
            "把已算好的异常结论改写成更自然的中文解读；"
            "不得新增或修改任何数字，不得改变告警判定，只返回正文。"
        ),
    }
    if allow_external:
        payload["draft"] = template

    try:
        text = client.complete(payload)
        text = text.strip() if isinstance(text, str) else ""
        if text and numbers_subset(text, facts):
            model = getattr(client, "last_model", None) or settings.ai_llm_model or "llm"
            return text, "llm", model
    except Exception:  # noqa: BLE001 - 润色失败不影响可用性
        pass
    return template, "template", "deterministic-v1"


def build_dashboard_insights(db: Session, window: str, role: str) -> dict[str, Any]:
    """A4 异常解读：只读聚合六域 KPI 告警 + MRP 异常，返回结构化告警与解读文本。"""
    now = datetime.now()
    overview = ManagementDashboard.overview(db)
    finance = finance_kpi(db)
    progress_rows_all = progress_rows(db, "ALL", None)
    progress = {
        "operations": len(progress_rows_all),
        "avg_completion_rate": (
            round(sum(row["completion_rate"] for row in progress_rows_all) / len(progress_rows_all), 4)
            if progress_rows_all else 0.0
        ),
        "rows": progress_rows_all,
    }

    scopes = [
        ("MANAGEMENT", overview),
        ("PRODUCTION", overview),
        ("PROGRESS", {"progress": progress}),
        ("FINANCE", {"finance": finance}),
        ("SALES", {"sales": overview["sales"]}),
        ("HOME", {**overview, "finance": finance}),
    ]
    raw_alerts = _scope_alerts(db, scopes)
    alerts = _enrich(db, raw_alerts, overview, progress, role, now)

    mrp_alerts, mrp_truncated = _mrp_alerts(db, window, role)
    alerts.extend(mrp_alerts)
    alerts = _sort_alerts(alerts)

    summary = _summary(alerts, mrp_truncated)
    template = _template_narrative(window, alerts, summary)
    facts = _fact_set(alerts, summary, window)
    # 模板中的数字均来自结构化字段，加入白名单以允许 LLM 原样复述
    facts.update(round(float(match), 4) for match in _NUMBER_RE.findall(template))

    narrative, source, model = _llm_narrative(template, alerts, summary, window, facts)

    return {
        "window": window,
        "generated_at": now.isoformat(timespec="seconds"),
        "summary": summary,
        "alerts": alerts,
        "narrative": narrative,
        "narration_source": source,
        "model": model,
    }
