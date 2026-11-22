"""驾驶舱预警引擎：本体 DashboardRule → 规则求值 → 预警列表。

规则由 ontology/model/dashboard.yaml 生成模型，种子落库后可在
「系统参数/本体规则」层调整阈值，无需改看板代码。
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.common.models.dashboard import AlertLevel, AlertOperator, DashboardRule, DashboardScope

LEVEL_ORDER = {AlertLevel.INFO.value: 0, AlertLevel.WARNING.value: 1, AlertLevel.CRITICAL.value: 2}

DEFAULT_RULES = [
    ("R-HOME-OEE", "全局设备效率预警", "HOME", "equipment.oee", "LT", 0.70, "WARNING",
     "综合 OEE {value:.0%} 低于 {threshold:.0%}，建议优先安排设备维护", "ALL"),
    ("R-MGMT-OEE", "设备效率预警", "MANAGEMENT", "equipment.oee", "LT", 0.70, "WARNING",
     "综合 OEE {value:.0%} 低于 {threshold:.0%}，建议优先安排设备维护", "ALL"),
    ("R-MGMT-FPY", "一次合格率预警", "MANAGEMENT", "quality.first_pass_rate", "LT", 0.95, "WARNING",
     "一次合格率 {value:.1%} 低于 {threshold:.0%}，需排查关键工序质量", "ALL"),
    ("R-MGMT-DELAY", "交期风险提示", "MANAGEMENT", "delivery.delayed_sales_orders", "GT", 0, "INFO",
     "有 {value:.0f} 张销售订单已过承诺交期，需跟进交付", "ALL"),
    ("R-PROD-RATE", "工单完成率预警", "PRODUCTION", "production.completion_rate", "LT", 0.80, "WARNING",
     "工单完成率 {value:.0%} 低于 {threshold:.0%}，关注在制积压", "LAST90"),
    ("R-PROD-DELAY", "工单逾期预警", "PRODUCTION", "production.delayed_orders", "GT", 0, "CRITICAL",
     "{value:.0f} 张工单已过计划完工日，需要重排或插单评估", "LAST90"),
    ("R-PROG-RATE", "工序进度预警", "PROGRESS", "progress.avg_completion_rate", "LT", 0.60, "WARNING",
     "工序平均完成率 {value:.0%} 偏低，建议核对报工与排程", "ALL"),
    ("R-FIN-COLLECT", "回款率预警", "FINANCE", "finance.collection_rate", "LT", 0.60, "WARNING",
     "回款率 {value:.0%} 低于 {threshold:.0%}，应收催收需加强", "LAST365"),
    ("R-FIN-PAYABLE", "应付余额提示", "FINANCE", "finance.payable_open", "GT", 100000, "INFO",
     "应付余额 {value:,.0f} 元，注意资金安排", "ALL"),
    ("R-SALES-OPEN", "未交订单提示", "SALES", "sales.open_orders", "GT", 0, "INFO",
     "未交订单 {value:.0f} 张，关注产能与物料匹配", "ALL"),
    ("R-SALES-AMOUNT", "在手订单金额提示", "SALES", "sales.amount_open", "LT", 1000, "INFO",
     "在手订单金额 {value:,.0f} 元偏低，需拓展商机", "ALL"),
]


def seed_dashboard_rules(db: Session) -> None:
    """幂等写入默认预警规则。"""
    for code, name, scope, metric, operator, threshold, level, message, window in DEFAULT_RULES:
        rule = db.query(DashboardRule).filter(DashboardRule.code == code).first()
        if rule is None:
            rule = DashboardRule(code=code)
            db.add(rule)
        rule.name = name
        rule.scope = DashboardScope(scope)
        rule.metric = metric
        rule.operator = AlertOperator(operator)
        rule.threshold = Decimal(str(threshold))
        rule.level = AlertLevel(level)
        rule.message = message
        rule.default_window = window
        rule.enabled = True
    db.flush()


def _resolve(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _compare(actual: float, threshold: float, operator: AlertOperator) -> bool:
    if operator == AlertOperator.LT:
        return actual < threshold
    if operator == AlertOperator.LTE:
        return actual <= threshold
    if operator == AlertOperator.GT:
        return actual > threshold
    return actual >= threshold


def build_alerts(db: Session, scope: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """按本体规则求值；HOME 规则始终生效，同 code 去重。"""
    rules = (
        db.query(DashboardRule)
        .filter(DashboardRule.is_deleted.is_(False), DashboardRule.enabled.is_(True))
        .all()
    )
    alerts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in rules:
        if rule.scope.value not in (scope, DashboardScope.HOME.value):
            continue
        if rule.code in seen:
            continue
        actual = _resolve(data, rule.metric)
        if actual is None:
            continue
        try:
            actual_number = float(actual)
            threshold = float(rule.threshold)
        except (TypeError, ValueError):
            continue
        if not _compare(actual_number, threshold, rule.operator):
            continue
        seen.add(rule.code)
        message = rule.message or f"{rule.name}：实际 {actual_number}，阈值 {threshold}"
        try:
            message = message.format(value=actual_number, threshold=threshold)
        except (KeyError, ValueError, IndexError):
            pass
        alerts.append({
            "code": rule.code,
            "name": rule.name,
            "level": rule.level.value,
            "scope": rule.scope.value,
            "metric": rule.metric,
            "actual": round(actual_number, 4),
            "threshold": threshold,
            "message": message,
        })
    alerts.sort(key=lambda item: LEVEL_ORDER.get(item["level"], 0), reverse=True)
    return alerts
