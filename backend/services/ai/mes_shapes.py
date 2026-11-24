"""MES 外部数据的本体形状校验。

形状唯一事实源：``ontology/src/shapes.ttl`` 的
``MesWorkOrderShape`` / ``MesProcessTaskShape`` / ``MesProcessReportShape``。
本模块只负责把查询结果行映射为 RDF 实例并调用 pyshacl，不定义任何约束。
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable
from urllib.parse import quote

from pyshacl import validate
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SH as SHNS, XSD

from backend.services.ai.ontology_service import NS, get_ontology_service

MES_CLASSES = ("MesWorkOrder", "MesProcessTask", "MesProcessReport")


def _node(*parts: object) -> URIRef:
    return URIRef(NS + "mes/" + "/".join(quote(str(part), safe="") for part in parts))


def _decimal(value: Any) -> Literal:
    try:
        return Literal(Decimal(str(value)), datatype=XSD.decimal)
    except (InvalidOperation, ValueError):
        return Literal(value)


def _integer(value: Any) -> Literal:
    try:
        return Literal(int(value), datatype=XSD.integer)
    except (TypeError, ValueError):
        return Literal(value)


def _date_time(value: Any) -> Literal:
    if isinstance(value, datetime):
        return Literal(value, datatype=XSD.dateTime)
    if isinstance(value, date):
        return Literal(datetime.combine(value, time.min), datatype=XSD.dateTime)
    text = str(value)
    try:
        return Literal(datetime.fromisoformat(text.replace(" ", "T")), datatype=XSD.dateTime)
    except ValueError:
        return Literal(text)


def _text(value: Any) -> Literal:
    return Literal(str(value))


def build_mes_graph(rows: Iterable[dict[str, Any]]) -> tuple[Graph, dict[URIRef, str]]:
    """把 MES 结果行映射为工单/工序/报工三类实例；返回图与焦点→row_key 映射。"""
    graph = Graph()
    focus: dict[URIRef, str] = {}
    seen_orders: set[str] = set()
    seen_tasks: set[str] = set()
    seen_reports: set[str] = set()

    def row_key(row: dict[str, Any]) -> str:
        return str(row.get("row_key") or "")

    for row in rows:
        order_no = row.get("work_order_no")
        order_uri = _node("work-order", order_no)
        focus.setdefault(order_uri, row_key(row))
        key = str(order_no)
        if key not in seen_orders:
            seen_orders.add(key)
            graph.add((order_uri, RDF.type, URIRef(NS + "MesWorkOrder")))
            for column, prop, convert in (
                ("work_order_no", "mesWorkOrderNo", _text),
                ("product_name", "mesProductName", _text),
                ("order_status", "mesOrderStatus", _text),
                ("order_quantity", "mesOrderQuantity", _decimal),
                ("order_completed_quantity", "mesOrderCompletedQuantity", _decimal),
                ("order_qualified_quantity", "mesOrderQualifiedQuantity", _decimal),
                ("order_scrapped_quantity", "mesOrderScrappedQuantity", _decimal),
                ("planned_start_date", "mesPlannedStart", _date_time),
                ("planned_end_date", "mesPlannedEnd", _date_time),
            ):
                value = row.get(column)
                if value is not None:
                    graph.add((order_uri, URIRef(NS + prop), convert(value)))

        task_id = row.get("process_task_id")
        if task_id is None:
            continue
        task_uri = _node("task", task_id)
        focus.setdefault(task_uri, row_key(row))
        task_key = str(task_id)
        if task_key not in seen_tasks:
            seen_tasks.add(task_key)
            graph.add((task_uri, RDF.type, URIRef(NS + "MesProcessTask")))
            graph.add((task_uri, URIRef(NS + "belongsToMesWorkOrder"), order_uri))
            for column, prop, convert in (
                ("process_task_id", "mesTaskId", _integer),
                ("task_sequence", "mesTaskSequence", _integer),
                ("task_status", "mesTaskStatus", _text),
                ("equipment_id", "mesEquipmentId", _integer),
                ("task_completed_quantity", "mesTaskCompletedQuantity", _decimal),
                ("task_qualified_quantity", "mesTaskQualifiedQuantity", _decimal),
                ("task_scrapped_quantity", "mesTaskScrappedQuantity", _decimal),
            ):
                value = row.get(column)
                if value is not None:
                    graph.add((task_uri, URIRef(NS + prop), convert(value)))

        report_id = row.get("report_id")
        if report_id is None:
            continue
        report_uri = _node("report", report_id)
        focus[report_uri] = row_key(row)
        report_key = str(report_id)
        if report_key in seen_reports:
            continue
        seen_reports.add(report_key)
        graph.add((report_uri, RDF.type, URIRef(NS + "MesProcessReport")))
        graph.add((report_uri, URIRef(NS + "reportsMesTask"), task_uri))
        for column, prop, convert in (
            ("report_id", "mesReportId", _integer),
            ("report_time", "mesReportTime", _date_time),
            ("report_completed_quantity", "mesReportCompletedQuantity", _decimal),
            ("report_qualified_quantity", "mesReportQualifiedQuantity", _decimal),
            ("report_scrapped_quantity", "mesReportScrappedQuantity", _decimal),
            ("defect_reason", "mesDefectReason", _text),
            ("actual_hours", "mesActualHours", _decimal),
        ):
            value = row.get(column)
            if value is not None:
                graph.add((report_uri, URIRef(NS + prop), convert(value)))

    return graph, focus


def validate_mes_result(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """按本体形状校验 MES 结果行；返回违规明细（空列表表示通过）。"""
    if not rows:
        return []
    graph, focus = build_mes_graph(rows)
    ontology = get_ontology_service()
    ontology.ensure_loaded()
    conforms, report, _ = validate(
        graph,
        shacl_graph=ontology.shapes,
        inference="none",
        advanced=False,
    )
    if conforms:
        return []

    violations: list[dict[str, str]] = []
    for result in report.subjects(RDF.type, SHNS.ValidationResult):
        node = report.value(result, SHNS.focusNode)
        path = report.value(result, SHNS.resultPath)
        component = report.value(result, SHNS.sourceConstraintComponent)
        violations.append({
            "row_key": focus.get(node, "") if node is not None else "",
            "focus": str(node).replace(NS, "") if node is not None else "",
            "path": str(path).replace(NS, "") if path else "",
            "component": str(component).rsplit("#", 1)[-1] if component else "",
            "message": str(report.value(result, SHNS.resultMessage) or ""),
        })
    violations.sort(key=lambda item: (item["row_key"], item["focus"], item["path"], item["component"]))
    return violations
