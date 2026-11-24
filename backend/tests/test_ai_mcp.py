"""W2.1 MCP 只读工具层验收：鉴权、工具清单、读写边界、执行与审计。"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.common.database.base import get_db
from backend.services.ai.config import get_settings
from backend.services.ai.intents import INTENT_REGISTRY

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from ai_demo_dataset import seed_ai_demo_dataset  # noqa: E402

TOKEN = "ut-mcp-token"


@pytest.fixture(autouse=True)
def _fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(session_factory):
    Session = session_factory

    def _override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def mcp_enabled(monkeypatch):
    monkeypatch.setenv("AI_MCP_TOKEN", TOKEN)
    get_settings.cache_clear()
    return {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture()
def dataset(session_factory):
    session = session_factory()
    try:
        seed_ai_demo_dataset(session)
        session.commit()
    finally:
        session.close()


def _post(client: TestClient, payload: dict, headers: dict | None = None):
    return client.post("/api/ai/mcp", json=payload, headers=headers or {})


def test_token_missing_or_wrong_is_401(client, monkeypatch):
    monkeypatch.setenv("AI_MCP_TOKEN", TOKEN)
    get_settings.cache_clear()
    resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert resp.status_code == 401

    resp = _post(
        client,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_unconfigured_token_is_fail_closed(client, monkeypatch):
    monkeypatch.setenv("AI_MCP_TOKEN", "")
    get_settings.cache_clear()
    resp = _post(
        client,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 401


def test_initialize_and_tools_list_match_read_only_intents(client, mcp_enabled):
    resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, mcp_enabled)
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "dierp-erp-mcp"

    resp = _post(client, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, mcp_enabled)
    assert resp.status_code == 200
    tools = resp.json()["result"]["tools"]
    expected = {
        code for code, spec in INTENT_REGISTRY.items() if spec.source_system == "ERP"
    }
    assert {tool["name"] for tool in tools} == expected
    assert len(tools) == 7
    for tool in tools:
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["destructiveHint"] is False
        assert tool["inputSchema"]["type"] == "object"


def test_mes_tool_hidden_until_enabled(client, mcp_enabled, monkeypatch):
    resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, mcp_enabled)
    names = {tool["name"] for tool in resp.json()["result"]["tools"]}
    assert "mes_work_order_progress" not in names

    monkeypatch.setenv("MES_QUERY_ENABLED", "true")
    monkeypatch.setenv("MES_DB_USER", "ut-mes")
    monkeypatch.setenv("MES_DB_PASSWORD", "ut-mes-secret")
    get_settings.cache_clear()
    resp = _post(client, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, mcp_enabled)
    names = {tool["name"] for tool in resp.json()["result"]["tools"]}
    assert "mes_work_order_progress" in names
    assert len(names) == 8


def test_write_tools_are_not_exposed(client, mcp_enabled):
    assert all(spec.read_only for spec in INTENT_REGISTRY.values())
    resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, mcp_enabled)
    names = {tool["name"] for tool in resp.json()["result"]["tools"]}
    assert not names & {"create", "update", "delete", "write", "post"}


def test_tool_call_returns_structured_result_and_audit(
    client, mcp_enabled, dataset, monkeypatch
):
    from backend.services.ai import pipeline as pipeline_module

    captured: list[dict] = []
    monkeypatch.setattr(
        pipeline_module, "write_ai_query_log", lambda **kwargs: captured.append(kwargs)
    )

    resp = _post(
        client,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "kitting_shortage", "arguments": {"limit": 5}},
        },
        mcp_enabled,
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["isError"] is False
    payload = result["structuredContent"]
    assert payload["tool"] == "kitting_shortage"
    assert payload["data"]["columns"]
    assert payload["provenance"]
    assert "SHORT" not in payload["answer"]

    assert captured
    audit = captured[-1]
    assert audit["username"].startswith("mcp:")
    assert audit["intent_code"] == "kitting_shortage"
    assert audit["status"] == "OK"


def test_unknown_tool_returns_tool_error(client, mcp_enabled):
    resp = _post(
        client,
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "drop_database", "arguments": {}},
        },
        mcp_enabled,
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["isError"] is True
    assert result["_meta"]["code"] == "AI_INTENT_UNKNOWN"


def test_role_boundary_filters_tools_and_blocks_calls(client, monkeypatch, dataset):
    monkeypatch.setenv("AI_MCP_TOKEN", TOKEN)
    monkeypatch.setenv("AI_MCP_ROLE", "SALES")
    get_settings.cache_clear()
    headers = {"Authorization": f"Bearer {TOKEN}"}

    resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers)
    names = {tool["name"] for tool in resp.json()["result"]["tools"]}
    assert "kitting_shortage" not in names

    resp = _post(
        client,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "kitting_shortage", "arguments": {"limit": 5}},
        },
        headers,
    )
    result = resp.json()["result"]
    assert result["isError"] is True
    assert result["_meta"]["code"] == "AI_PERMISSION_DENIED"


def test_unknown_method_returns_jsonrpc_error(client, mcp_enabled):
    resp = _post(client, {"jsonrpc": "2.0", "id": 9, "method": "resources/list"}, mcp_enabled)
    body = resp.json()
    assert body["error"]["code"] == -32601
