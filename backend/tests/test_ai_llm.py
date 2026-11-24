"""W1.2 LLM 层验收：均以本地桩/模拟实现驱动，不依赖真实网络。

覆盖：OpenAI 兼容客户端（URL 归一化、chat/completions、models、重试与降级、
密钥不泄漏）、提议结构、重试上限、模式闸与出域字段白名单。
"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy.orm import sessionmaker

from backend.common.models.ai import AiQueryLog
from backend.services.ai import audit as audit_mod
from backend.services.ai import intents as _intents_module  # noqa: F401 - 触发意图注册
from backend.services.ai import pipeline as pipeline_mod
from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.intent import INTENTS, Provenance, QueryResult
from backend.services.ai.llm import (
    LLMError,
    OpenAICompatibleClient,
    build_narration_payload,
    get_llm_client,
)
from backend.services.ai.ontology_service import NS
from backend.services.ai.proposer import LLMProposer

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from ai_demo_dataset import CUSTOMER_ID, seed_ai_demo_dataset  # noqa: E402

PLANNER = SimpleNamespace(username="planner1", role="PLANNER")


class StubClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete(self, payload: dict, *, response_format: str | None = None) -> str:
        self.calls.append(payload)
        return self.responses.pop(0) if self.responses else ""


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch):
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.fixture()
def sessions(engine, monkeypatch):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(audit_mod, "SessionLocal", Session)
    return Session


@pytest.fixture()
def dataset(db):
    seed_ai_demo_dataset(db)
    db.commit()
    return db


def test_invalid_json_rejected_after_two_calls():
    client = StubClient(["not-json", "still-not-json"])
    proposer = LLMProposer(client)
    with pytest.raises(AIException) as excinfo:
        proposer.propose("随便问问")
    assert excinfo.value.code == "AI_INTENT_UNKNOWN"
    assert len(client.calls) == LLMProposer.MAX_CALLS == 2


def test_out_of_domain_intent_rejected_by_schema_gate(dataset, sessions):
    client = StubClient(['{"intent": "schema_dump", "params": {}}'])
    proposer = LLMProposer(client)
    with pytest.raises(AIException) as excinfo:
        pipeline_mod.ask("你是谁？", PLANNER, dataset, proposer=proposer)
    assert excinfo.value.code == "AI_INTENT_UNKNOWN"

    row = sessions().query(AiQueryLog).filter_by(trace_id=excinfo.value.trace_id).one()
    assert row.status == "REJECTED_SCHEMA"


def test_extra_params_from_llm_rejected_by_schema_gate(dataset, sessions):
    client = StubClient([
        '{"intent": "material_below_safety", "params": {"material_type": "RAW", "x": 1}}'
    ])
    with pytest.raises(AIException) as excinfo:
        pipeline_mod.ask("哪些原材料低于安全库存？", PLANNER, dataset,
                         proposer=LLMProposer(client))
    assert excinfo.value.code == "AI_PARAM_INVALID"

    row = sessions().query(AiQueryLog).filter_by(trace_id=excinfo.value.trace_id).one()
    assert row.status == "REJECTED_PARAM"


def test_narration_payload_excludes_row_details_by_default():
    result = QueryResult(
        columns=[
            "customer_id", "customer_name", "credit_limit", "ar_balance",
            "open_order_amount", "open_order_count", "credit_usage_ratio",
        ],
        rows=[{
            "customer_id": CUSTOMER_ID, "customer_name": "示例客户一",
            "credit_limit": 100000.0, "ar_balance": 600.0,
            "open_order_amount": 3500.0, "open_order_count": 3,
            "credit_usage_ratio": 0.041,
        }],
        sources=[Provenance(table="customers", record_key=CUSTOMER_ID,
                            ontology_iri=NS + "Customer")],
    )
    payload = build_narration_payload(result, result.columns, allow_external_data=False)
    text = str(payload)

    assert payload["row_count"] == 1
    assert CUSTOMER_ID not in text
    assert "示例客户一" not in text
    assert "credit_limit" not in payload["aggregate"]
    assert "ar_balance" not in payload["aggregate"]
    assert "amount" not in payload["aggregate"]
    assert set(payload["aggregate"]) == {"open_order_count"}


def test_narration_payload_includes_rows_when_allowed():
    result = QueryResult(
        columns=["customer_id", "open_order_count"],
        rows=[{"customer_id": CUSTOMER_ID, "open_order_count": 3}],
        sources=[Provenance(table="customers", record_key=CUSTOMER_ID,
                            ontology_iri=NS + "Customer")],
    )
    payload = build_narration_payload(result, result.columns, allow_external_data=True)
    assert payload["rows"][0]["customer_id"] == CUSTOMER_ID


# ── OpenAI 兼容客户端（标准库 urllib，全部用桩替换 urlopen）─────────
class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info) -> bool:
        return False


def _install_fake_urlopen(monkeypatch, responses: list) -> list[dict]:
    """按顺序返回预设响应；元素为 Exception 时抛出。返回调用记录。"""
    calls: list[dict] = []

    def fake_urlopen(request, timeout=None):
        calls.append({
            "url": request.full_url,
            "method": request.get_method(),
            "headers": {key.lower(): value for key, value in request.header_items()},
            "body": request.data,
            "timeout": timeout,
        })
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return calls


def test_base_url_normalized_to_v1():
    client = OpenAICompatibleClient("http://127.0.0.1:3001", "demo")
    assert client.base_url == "http://127.0.0.1:3001/v1"
    assert OpenAICompatibleClient("http://127.0.0.1:3001/v1/", "demo").base_url == (
        "http://127.0.0.1:3001/v1"
    )
    with pytest.raises(LLMError):
        OpenAICompatibleClient("", "demo")
    with pytest.raises(LLMError):
        OpenAICompatibleClient("http://127.0.0.1:3001", "  ")


def test_complete_posts_chat_completions(monkeypatch):
    calls = _install_fake_urlopen(monkeypatch, [
        json.dumps({"choices": [{"message": {"content": "  按要求回答  "}}]}),
    ])
    client = OpenAICompatibleClient("http://127.0.0.1:3001", "demo", api_key="sk-local")
    assert client.complete({"task": "narration"}) == "按要求回答"

    call = calls[0]
    assert call["url"] == "http://127.0.0.1:3001/v1/chat/completions"
    assert call["method"] == "POST"
    assert call["timeout"] == 20.0
    assert call["headers"]["authorization"] == "Bearer sk-local"
    body = json.loads(call["body"])
    assert body["model"] == "demo"
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert json.loads(body["messages"][-1]["content"]) == {"task": "narration"}


def test_complete_without_api_key_sends_no_authorization(monkeypatch):
    calls = _install_fake_urlopen(monkeypatch, [
        json.dumps({"choices": [{"message": {"content": "ok"}}]}),
    ])
    OpenAICompatibleClient("http://127.0.0.1:3001", "demo").complete({"task": "x"})
    assert "authorization" not in calls[0]["headers"]


def test_list_models_parses_ids(monkeypatch):
    calls = _install_fake_urlopen(monkeypatch, [
        json.dumps({"data": [{"id": "a"}, {"id": "b"}, {"missing": 1}]}),
    ])
    client = OpenAICompatibleClient("http://127.0.0.1:3001/v1", "demo")
    assert client.list_models() == ["a", "b"]
    assert calls[0]["url"] == "http://127.0.0.1:3001/v1/models"
    assert calls[0]["method"] == "GET"


def test_network_error_retried_twice_then_raises_without_key(monkeypatch):
    calls = _install_fake_urlopen(monkeypatch, [
        urllib.error.URLError("boom"),
        TimeoutError("slow"),
    ])
    client = OpenAICompatibleClient(
        "http://127.0.0.1:3001", "demo", api_key="sk-secret", timeout=1,
        backoff_seconds=0,
    )
    with pytest.raises(LLMError) as excinfo:
        client.complete({"task": "x"})
    assert len(calls) == client.MAX_ATTEMPTS == 2
    assert "sk-secret" not in str(excinfo.value)


def test_client_error_is_not_retried(monkeypatch):
    error = urllib.error.HTTPError(
        "http://127.0.0.1:3001/v1/chat/completions",
        401,
        "Unauthorized",
        {},
        io.BytesIO(b'{"error":"bad key"}'),
    )
    calls = _install_fake_urlopen(monkeypatch, [error, json.dumps({})])
    client = OpenAICompatibleClient("http://127.0.0.1:3001", "demo", api_key="sk-secret")
    with pytest.raises(LLMError) as excinfo:
        client.complete({"task": "x"})
    assert len(calls) == 1
    assert "sk-secret" not in str(excinfo.value)


def test_unparsable_body_degrades(monkeypatch):
    _install_fake_urlopen(monkeypatch, ["<html>gateway</html>", "still-not-json"])
    client = OpenAICompatibleClient("http://127.0.0.1:3001", "demo", backoff_seconds=0)
    with pytest.raises(LLMError):
        client.complete({"task": "x"})


def test_missing_choices_degrades(monkeypatch):
    malformed = json.dumps({"object": "chat.completion"})
    _install_fake_urlopen(monkeypatch, [malformed, malformed])
    client = OpenAICompatibleClient("http://127.0.0.1:3001", "demo", backoff_seconds=0)
    with pytest.raises(LLMError):
        client.complete({"task": "x"})


def test_get_llm_client_returns_none_when_disabled(monkeypatch):
    monkeypatch.setenv("AI_LLM_ENABLED", "false")
    assert get_llm_client() is None


def test_get_llm_client_builds_from_env(monkeypatch):
    monkeypatch.setenv("AI_LLM_ENABLED", "true")
    monkeypatch.setenv("AI_LLM_BASE_URL", "http://127.0.0.1:3001")
    monkeypatch.setenv("AI_LLM_MODEL", "demo-model")
    monkeypatch.setenv("AI_LLM_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("AI_LLM_API_KEY", "sk-demo")

    client = get_llm_client()
    assert isinstance(client, OpenAICompatibleClient)
    assert client.base_url == "http://127.0.0.1:3001/v1"
    assert client.model == "demo-model"
    assert client.timeout == 7.0
    assert client.complete.__self__._api_key == "sk-demo"


def test_fenced_json_from_real_model_is_accepted():
    """真实模型常把 JSON 包进 ```json 代码块：剥离围栏后仍走同一套模式闸。"""
    client = StubClient(['```json\n{"intent": "ar_overdue", "params": {"days_overdue": 30}}\n```'])
    proposal = LLMProposer(client).propose("30 天以上未收款的应收有哪些？")
    assert proposal.intent == "ar_overdue"
    assert proposal.params == {"days_overdue": 30}
    assert proposal.source == "llm"


def test_complete_sends_json_object_response_format(monkeypatch):
    calls = _install_fake_urlopen(monkeypatch, [
        json.dumps({"choices": [{"message": {"content": "{}"}}]}),
    ])
    OpenAICompatibleClient("http://127.0.0.1:3001", "demo").complete(
        {"task": "intent_proposal"}, response_format="json_object"
    )
    assert json.loads(calls[0]["body"])["response_format"] == {"type": "json_object"}


def test_429_falls_back_to_next_model_and_records_it(monkeypatch):
    quota = urllib.error.HTTPError(
        "http://127.0.0.1:3001/v1/chat/completions", 429, "Too Many Requests", {},
        io.BytesIO(b'{"error":"quota exhausted"}'),
    )
    calls = _install_fake_urlopen(monkeypatch, [
        quota,
        json.dumps({"choices": [{"message": {"content": '{"intent": "ar_overdue"}'}}]}),
    ])
    client = OpenAICompatibleClient(
        "http://127.0.0.1:3001", "primary-model",
        fallback_models=["backup-model"], backoff_seconds=0,
    )
    assert client.complete({"task": "intent_proposal"}) == '{"intent": "ar_overdue"}'
    assert len(calls) == 2
    assert json.loads(calls[0]["body"])["model"] == "primary-model"
    assert json.loads(calls[1]["body"])["model"] == "backup-model"
    assert client.last_model == "backup-model"


def test_400_on_response_format_retried_without_it(monkeypatch):
    unsupported = urllib.error.HTTPError(
        "http://127.0.0.1:3001/v1/chat/completions", 400, "Bad Request", {},
        io.BytesIO(b'{"error":"unknown field response_format"}'),
    )
    calls = _install_fake_urlopen(monkeypatch, [
        unsupported,
        json.dumps({"choices": [{"message": {"content": "{}"}}]}),
    ])
    client = OpenAICompatibleClient("http://127.0.0.1:3001", "demo", backoff_seconds=0)
    assert client.complete({"task": "x"}, response_format="json_object") == "{}"
    assert len(calls) == 2
    assert "response_format" in json.loads(calls[0]["body"])
    assert "response_format" not in json.loads(calls[1]["body"])
    assert client.last_model == "demo"


def test_fallback_models_discovered_from_models_endpoint(monkeypatch):
    quota = urllib.error.HTTPError(
        "http://127.0.0.1:3001/v1/chat/completions", 429, "Too Many Requests", {},
        io.BytesIO(b'{"error":"quota"}'),
    )
    calls = _install_fake_urlopen(monkeypatch, [
        json.dumps({"data": [
            {"id": "primary-model", "available": True},
            {"id": "primary-model-lite", "available": True},
            {"id": "other-model", "available": True},
            {"id": "auto", "available": True},
            {"id": "claude-sonnet-x", "available": True},
            {"id": "dead-model", "available": False},
        ]}),
        quota,
        json.dumps({"choices": [{"message": {"content": "ok"}}]}),
    ])
    client = OpenAICompatibleClient(
        "http://127.0.0.1:3001", "primary-model",
        discover_fallbacks=True, backoff_seconds=0,
    )
    assert client.complete({"task": "x"}) == "ok"
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"].endswith("/v1/models")
    assert json.loads(calls[1]["body"])["model"] == "primary-model"
    assert json.loads(calls[2]["body"])["model"] == "other-model"
    assert client.last_model == "other-model"


def test_proposal_payload_carries_schema_without_business_data():
    client = StubClient(['{"intent": "material_below_safety", "params": {"material_type": "RAW"}}'])
    proposal = LLMProposer(client).propose("哪些原材料低于安全库存？")
    payload = client.calls[0]

    assert proposal.intent == "material_below_safety"
    assert payload["allowed_intents"] == list(INTENTS)
    material = next(i for i in payload["intents"] if i["code"] == "material_below_safety")
    material_type = next(p for p in material["params"] if p["name"] == "material_type")
    assert material_type["enum"] == ["FG", "SEMI", "RAW", "PACKAGING", "SERVICE"]
    assert material_type["type"] == "string"
    limit = next(p for p in material["params"] if p["name"] == "limit")
    assert limit["type"] == "integer"
    assert (limit["minimum"], limit["maximum"]) == (1, 200)

    text = json.dumps(payload, ensure_ascii=False)
    assert CUSTOMER_ID not in text
    assert "示例客户" not in text
    assert "rows" not in payload and "aggregate" not in payload
    assert "原样填入" in payload["instruction"]
    assert "不得省略" in payload["instruction"]


def test_explicit_unknown_intent_is_rejected_with_visible_message():
    client = StubClient(['{"intent": "unknown", "params": {}}'])
    with pytest.raises(AIException) as excinfo:
        LLMProposer(client).propose('低于安全库存的物料类型写 "FOO"')
    assert excinfo.value.code == "AI_INTENT_UNKNOWN"
    assert excinfo.value.http_status == 422
    assert "无法映射" in excinfo.value.message
    assert len(client.calls) == 1  # 模型已明确拒绝，不再重试


def test_unknown_proposal_never_returns_silent_200(dataset, sessions):
    """拒绝必须抛给上层（路由序列化为 422），不能静默执行宽查询。"""
    warehouse = SimpleNamespace(username="demo_wh", role="WAREHOUSE")
    client = StubClient(['{"intent": "unknown", "params": {}}'])
    with pytest.raises(AIException) as excinfo:
        pipeline_mod.ask(
            '低于安全库存的物料类型写 "FOO"', warehouse, dataset,
            proposer=LLMProposer(client),
        )
    assert excinfo.value.code == "AI_INTENT_UNKNOWN"
    assert "无法映射" in excinfo.value.message

    row = sessions().query(AiQueryLog).filter_by(trace_id=excinfo.value.trace_id).one()
    assert row.status == "REJECTED_INTENT"


def test_rule_failure_falls_back_to_llm(monkeypatch, dataset, sessions):
    """确定性规则未命中时才走 LLM 兜底；叙述与提议共用同一客户端。"""
    client = StubClient([
        '{"intent": "customer_credit_status", "params": {"customer_id": "C001"}}',
    ])
    sales = SimpleNamespace(username="sales_mgr1", role="SALES_MANAGER")
    outcome = pipeline_mod.ask("那家客户的额度情况？", sales, dataset, llm_client=client)
    assert outcome["intent"]["code"] == "customer_credit_status"
    # 提议来自 LLM 时应如实标注模型（桩客户端无 last_model，回落到配置值）
    assert outcome["model"] == (get_settings().ai_llm_model or "llm")
    assert client.calls[0]["task"] == "intent_proposal"
