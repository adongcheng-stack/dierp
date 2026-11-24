"""回答模板：字段白名单裁剪 + 模板叙述 + 数字回查（设计 §7.3 第 10 步、评审 I10）。

- 金额列按 ``IntentSpec.output_fields[role]`` 裁剪，缺省用 ``"*"``；
- 叙述中的数字必须来自结果集（行内数值或由行汇总得到的统计量），否则退回通用文案。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.services.ai.intent import IntentSpec, QueryResult

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class AnswerResult:
    text: str
    columns: list[str]
    rows: list[dict[str, Any]]
    trimmed: bool


def allowed_columns(spec: IntentSpec, role: str, columns: list[str]) -> list[str]:
    if role in spec.output_fields:
        allowed = set(spec.output_fields[role])
    else:
        allowed = set(spec.output_fields.get("*", columns))
    return [column for column in columns if column in allowed]


def allowed_numbers(rows: list[dict[str, Any]], extra: set[float] | None = None) -> set[float]:
    values: set[float] = set(extra or set())
    for row in rows:
        for value in row.values():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.add(round(float(value), 4))
    return values


def numbers_subset(text: str, allowed: set[float]) -> bool:
    found = {round(float(match), 4) for match in _NUMBER_RE.findall(text)}
    return found <= allowed


def _sum(rows: list[dict[str, Any]], column: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(column)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total += float(value)
    return round(total, 4)


def build_answer(
    spec: IntentSpec, result: QueryResult, role: str, truncated: bool = False
) -> AnswerResult:
    columns = allowed_columns(spec, role, result.columns)
    rows = [{column: row.get(column) for column in columns} for row in result.rows]
    trimmed = len(columns) < len(result.columns)

    count = len(rows)
    if count == 0:
        if result.reason == "customer_not_found":
            return AnswerResult("未找到该客户，无法计算信用占用。", columns, rows, trimmed)
        if result.reason == "work_order_not_found":
            return AnswerResult(
                "未找到该工单，请确认工单号是否正确，或该工单尚未同步到 MES。",
                columns, rows, trimmed,
            )
        return AnswerResult("未找到符合条件的结果。", columns, rows, trimmed)

    if result.reason == "work_order_no_tasks":
        order_no = rows[0].get("work_order_no")
        if order_no:
            text = f"工单 {order_no} 存在，但当前没有工序任务或报工记录。"
        else:
            text = "该工单存在，但当前没有工序任务或报工记录。"
        return AnswerResult(text, columns, rows, trimmed)

    extras: set[float] = {float(count)}
    parts = [f"共 {count} 条结果"]

    if spec.code in {"kitting_shortage", "material_below_safety"} and "shortage_qty" in columns:
        total = _sum(rows, "shortage_qty")
        extras.add(total)
        parts.append(f"缺料数量合计 {total}")
    elif spec.code == "material_below_safety" and "shortage" in columns:
        total = _sum(rows, "shortage")
        extras.add(total)
        parts.append(f"缺口合计 {total}")
    elif spec.code == "ar_overdue" and "outstanding" in columns:
        total = _sum(rows, "outstanding")
        extras.add(total)
        parts.append(f"未收金额合计 {total}")
    elif spec.code == "customer_credit_status" and "credit_usage_ratio" in columns:
        ratio = rows[0].get("credit_usage_ratio")
        if ratio is not None:
            parts.append(f"信用占用比 {ratio}")
    elif spec.code == "mes_work_order_progress":
        no_report = len({
            row.get("process_task_id")
            for row in rows
            if row.get("process_task_id") is not None and row.get("report_id") is None
        })
        if no_report:
            extras.add(float(no_report))
            parts.append(f"其中 {no_report} 道工序尚无报工记录")

    text = "，".join(parts) + "。"
    if truncated:
        text += "（结果已按上限截断）"

    if not numbers_subset(text, allowed_numbers(rows, extras)):
        return AnswerResult("查询完成，已返回结构化结果。", columns, rows, trimmed)
    return AnswerResult(text, columns, rows, trimmed)
