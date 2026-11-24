"""问题解析器：确定性规则（默认）+ LLM 提议（仅走 schema 闸，不直连模型）。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §7.1、§7.1.1、§7.1.2。
- 只做规则表内的显式抽取（单号/客户/同义词/状态词/时间词/前 N 条），不做语义猜测；
- 意图匹配前先做 schema/写操作前置分类，命中即拒绝；
- ``LLMProposer`` 最多调用 2 次，非法 JSON 直接拒绝，合法 JSON 交给模式闸校验。
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.services.ai.catalog import get_catalog
from backend.services.ai.errors import AIException
from backend.services.ai.intent import INTENTS
from backend.services.ai.llm import LLMClient


class ProposedIntent(BaseModel):
    intent: str
    params: dict[str, Any] = Field(default_factory=dict)
    source: Literal["rule", "llm"] = "rule"
    confidence: float = 1.0


# ── 前置分类 ────────────────────────────────────────────────
_SCHEMA_TOKENS = (
    "建表", "删表", "表结构", "所有表", "数据库结构", "数据库表", "ddl", "schema",
    "列名", "字段名", "information_schema", "忽略之前", "忽略上述", "忽略以上",
    "system prompt", "ai_query_logs",
)
_WRITE_TOKENS = (
    "删除", "修改", "更新", "新增", "创建", "写入", "插入", "导入", "导出",
    "改成", "覆盖", "清空",
)

# ── 意图关键词（按优先级从上到下）────────────────────────────
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    # MES 工单进度：关键词专属于跨库工序/报工查询，放在最前避免被"工单"类问法截走
    ("mes_work_order_progress", ("工序", "报工")),
    ("kitting_shortage", ("缺料", "齐套")),
    ("customer_credit_status", ("信用",)),
    ("open_nonconformance", ("不合格", "ncr")),
    ("open_mrp_exceptions", ("计划异常",)),
    ("ar_overdue", ("应收", "未收款")),
    ("material_below_safety", ("安全库存",)),
    ("order_delay_risk", ("延期", "交付", "未完工")),
)

_ORDER_NO_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2,4})-([A-Z0-9]{4,}(?:-[A-Z0-9]+)*)")
_CUSTOMER_ID_RE = re.compile(r"客户\s*([A-Za-z0-9][A-Za-z0-9_\-]{1,19})")
_CUSTOMER_NAME_RE = re.compile(r"客户\s*([\u4e00-\u9fa5]{2,6}?)(?=的|有|信用|$|\s)")
_WITHIN_RE = re.compile(r"(\d+)\s*天内")
_OVERDUE_RE = re.compile(r"(\d+)\s*天以上")
_TOP_N_RE = re.compile(r"前\s*(\d+)\s*条")
_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
_SEVERITY_RE = re.compile(r"\b(CRITICAL|WARNING|INFO|MAJOR|MINOR)\b")
_MATERIAL_TYPE_RE = re.compile(
    r"(?:物料类型|材料类型|类型)\s*(?:是|为|写为|写成|写|[:=])?\s*['\"“]?([A-Za-z][A-Za-z0-9_]{1,19})"
)
_MATERIAL_SYNONYMS = (
    ("半成品", "SEMI"),
    ("原材料", "RAW"),
    ("成品", "FG"),
    ("包装", "PACKAGING"),
    ("服务", "SERVICE"),
)
_IGNORED_PREFIXES = {"INV", "NCR", "SO"}


def normalize(question: str, max_chars: int) -> str:
    text = unicodedata.normalize("NFKC", question or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def preclassify(text: str) -> None:
    """schema/DDL 与写操作在意图匹配前拒绝（设计 §7.1.2）。"""
    lowered = text.lower()
    for token in _SCHEMA_TOKENS:
        if token in lowered:
            raise AIException(
                "AI_INTENT_UNKNOWN",
                "该问题涉及库表结构或规则覆盖，AI 仅支持受控业务查询",
                reject_reason="SCHEMA_REJECTED",
            )
    for token in _WRITE_TOKENS:
        if token in text:
            raise AIException(
                "AI_INTENT_UNKNOWN",
                "AI 只提供只读查询，不支持任何写操作",
            )


def _customer(text: str) -> str | None:
    match = _CUSTOMER_ID_RE.search(text) or _CUSTOMER_NAME_RE.search(text)
    return match.group(1) if match else None


def _material_type(text: str) -> str | None:
    for word, code in _MATERIAL_SYNONYMS:
        if word in text:
            return code
    match = _MATERIAL_TYPE_RE.search(text)
    return match.group(1).upper() if match else None


def _order_number(text: str) -> tuple[str, str] | None:
    match = _ORDER_NO_RE.search(text)
    return (match.group(1), match.group(0)) if match else None


class RuleBasedProposer:
    """只按设计 §7.1.1 的规则表抽取意图与参数。"""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def propose(self, question: str) -> ProposedIntent:
        text = question.lower()
        intent = next(
            (code for code, words in _RULES if any(word in text for word in words)),
            None,
        )
        if intent is None:
            raise AIException("AI_INTENT_UNKNOWN")

        params = self._params(intent, question.lower(), question)
        return ProposedIntent(intent=intent, params=params, source="rule")

    def _params(self, intent: str, lowered: str, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        order = _order_number(text)
        severity = _SEVERITY_RE.search(text)
        top_n = _TOP_N_RE.search(text)

        if intent == "kitting_shortage":
            params["kit_status"] = "SHORT"
            if order and order[0] not in _IGNORED_PREFIXES:
                params["source_ref"] = order[1]
        elif intent == "mes_work_order_progress":
            # MES 工单号即完整业务编号（如 GD-20260914-00001）
            if order:
                params["work_order_no"] = order[1]
        elif intent == "order_delay_risk":
            within = _WITHIN_RE.search(text)
            if within:
                params["within_days"] = int(within.group(1))
            customer_id = _customer(text)
            if customer_id:
                params["customer_id"] = customer_id
            elif order and order[0] == "SO" and self.db is not None:
                params.update(self._customer_from_order(order[1]))
        elif intent == "material_below_safety":
            material_type = _material_type(text)
            if material_type:
                params["material_type"] = material_type
        elif intent == "open_mrp_exceptions":
            if severity:
                params["severity"] = severity.group(1)
        elif intent == "customer_credit_status":
            customer_id = _customer(text)
            if customer_id:
                params["customer_id"] = customer_id
        elif intent == "ar_overdue":
            overdue = _OVERDUE_RE.search(text)
            if overdue:
                params["days_overdue"] = int(overdue.group(1))
            customer_id = _customer(text)
            if customer_id:
                params["customer_id"] = customer_id
            if order and order[0] == "INV":
                params["invoice_number"] = order[1]
        elif intent == "open_nonconformance":
            if severity:
                params["severity"] = severity.group(1)

        if top_n and "limit" in INTENTS[intent].params_model.model_fields:
            params["limit"] = int(top_n.group(1))
        return params

    def _customer_from_order(self, order_number: str) -> dict[str, Any]:
        """设计 §7.1.1：SO 单号 → 查单取客户（只读）。"""
        from backend.common.models.sd import SalesOrder

        order = (
            self.db.query(SalesOrder)
            .filter(SalesOrder.order_number == order_number)
            .limit(1)
            .first()
        )
        return {"customer_id": order.customer_id} if order else {}


def _loads_object(raw: str) -> dict[str, Any]:
    """解析模型返回的 JSON；容忍整体被 ```json 代码块包裹（真实模型常见）。

    仅剥离围栏，不做字段修补；结构校验仍由模式闸与 SHACL 闸负责。
    """
    text = (raw or "").strip()
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("LLM 返回不是 JSON 对象")
    return data


def _schema_type(field: Any) -> str:
    """把 pydantic 字段注解收敛成 JSON 友好类型名（仅类型，不含取值）。"""
    annotation = field.annotation
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(args) == 1:
        annotation = args[0]
    if annotation is int:
        return "integer"
    if annotation is bool:
        return "boolean"
    if annotation is float:
        return "number"
    return "string"


def _field_bounds(field: Any) -> tuple[Any, Any]:
    minimum = maximum = None
    for meta in field.metadata:
        if minimum is None:
            minimum = getattr(meta, "ge", None)
        if maximum is None:
            maximum = getattr(meta, "le", None)
    return minimum, maximum


def _param_schema(spec: Any) -> list[dict[str, Any]]:
    """构造单个意图的参数契约：名称/类型/枚举/上下限/默认值。

    枚举来自语义目录（与 SHACL ``sh:in`` 同源），只是 schema 信息，不含任何业务数据。
    """
    entity = get_catalog().entities.get(spec.primary_entity)
    schema: list[dict[str, Any]] = []
    for name, field in spec.params_model.model_fields.items():
        meta = entity.fields.get(name) if entity else None
        item: dict[str, Any] = {"name": name}
        if meta is not None and meta.enum:
            item["type"] = "string"
            item["enum"] = list(meta.enum)
        else:
            item["type"] = _schema_type(field)

        minimum, maximum = _field_bounds(field)
        if meta is not None:
            minimum = meta.minimum if meta.minimum is not None else minimum
            maximum = meta.maximum if meta.maximum is not None else maximum
        if minimum is not None:
            item["minimum"] = minimum
        if maximum is not None:
            item["maximum"] = maximum

        item["required"] = field.is_required()
        if name in spec.defaults:
            item["default"] = spec.defaults[name]
        elif not field.is_required():
            item["default"] = field.default
        schema.append(item)
    return schema


class LLMProposer:
    """LLM 提议：只输出 ``{intent, params}``；任何结构问题最多重试 1 次。"""

    MAX_CALLS = 2

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def propose(self, question: str) -> ProposedIntent:
        payload = {
            "task": "intent_proposal",
            "instruction": (
                '只返回一个 JSON 对象，形如 {"intent": "<意图码>", "params": {...}}；'
                "intent 必须取自 allowed_intents，params 的键与取值必须满足各意图的 "
                "params 契约。硬约束：用户在问题里以字面量形式给出的参数值（如引号/代码样式的 "
                "物料类型、单号、客户号、天数、条数）必须原样填入 params，不得省略、不得改写、"
                "不得替换成近似值；即使该字面量不在 enum 内也必须原样输出，交由下游校验拒绝。"
                "自然语言业务词（如“原材料”“半成品”“严重”）应按 enum 语义映射为对应枚举码，"
                "这属于正常映射、不算改写字面量。只有在无法判断意图、或需要推断的取值无法映射到"
                '允许值时才返回 {"intent": "unknown", "params": {}}；不得通过丢弃参数来执行更宽的查询。'
                "不要输出 Markdown 代码块、解释或额外字段。"
            ),
            "question": question,
            "allowed_intents": list(INTENTS),
            "intents": [
                {
                    "code": code,
                    "label": spec.label,
                    "description": spec.description,
                    "params": _param_schema(spec),
                }
                for code, spec in INTENTS.items()
            ],
        }
        for _ in range(self.MAX_CALLS):
            try:
                raw = self.client.complete(payload, response_format="json_object")
                data = _loads_object(raw)
                intent = data.get("intent")
                params = data.get("params", {})
                if not isinstance(intent, str) or not isinstance(params, dict):
                    continue
                if intent.strip().lower() == "unknown":
                    # 模型显式声明无法映射：走既有 unknown 拒绝路径，且给出可被用户看到的原因
                    raise AIException(
                        "AI_INTENT_UNKNOWN",
                        "问题中的参数值无法映射到允许值，已拒绝执行以免返回宽泛结果",
                    )
                return ProposedIntent(intent=intent, params=params, source="llm")
            except AIException:
                raise
            except Exception:  # noqa: BLE001 - 非法 JSON/网络错误统一重试一次
                continue
        raise AIException("AI_INTENT_UNKNOWN", "LLM 返回结构不合法")
