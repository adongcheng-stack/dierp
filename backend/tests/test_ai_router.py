"""AI 路由探针（评审 S8）：parity 只防漂移，策略正确性需要行为证据。

覆盖：
- 匿名访问 ``/api/ai/**`` → 401；
- 9 个真实角色（含 ADMIN）登录 → 200；
- 伪造/未知角色 → 403（fail-closed）；
- 生成物断言：``ai`` 域不可写、不可匿名读、读角色为 9 个。
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.api.routers.auth import get_current_user, pwd_context
from backend.common.database.base import get_db
from backend.common.models.ai import AiQueryLog
from backend.common.models.mm import Material
from backend.common.models.planning import (
    KittingResult,
    MrpException,
    NonConformanceReport,
    SalesInvoice,
)
from backend.common.models.sd import SalesOrder
from backend.common.models.user import User, UserRole
from backend.services.ai import audit as audit_mod
from backend.services.ai.config import get_settings

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from ai_demo_dataset import seed_ai_demo_dataset  # noqa: E402

PASSWORD = "admin123"

BUSINESS_TABLES = (
    KittingResult, Material, SalesOrder, SalesInvoice, MrpException, NonConformanceReport,
)


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(session_factory, monkeypatch):
    Session = session_factory
    seed = Session()
    password_hash = pwd_context.hash(PASSWORD)
    for role in UserRole:
        seed.add(
            User(
                username=f"ai_{role.value.lower()}",
                email=f"ai_{role.value.lower()}@ut.local",
                full_name=role.value,
                password_hash=password_hash,
                role=role,
                department="UT",
                is_active=True,
            )
        )
    seed.commit()
    seed.close()

    # 审计走独立 SessionLocal；测试里指向同一内存库，保证 /queries 可查
    monkeypatch.setattr(audit_mod, "SessionLocal", Session)

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
        get_settings.cache_clear()


@pytest.fixture()
def ai_dataset(session_factory):
    session = session_factory()
    try:
        seed_ai_demo_dataset(session)
        session.commit()
    finally:
        session.close()


def _login(client: TestClient, username: str) -> str:
    resp = client.post("/api/auth/login", data={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text[:200]
    return resp.json()["access_token"]


def test_generated_policy_is_read_only_and_login_required():
    from backend.common.utils.security_policy import (
        READ_OPEN_DOMAINS,
        READ_ROLE_POLICY,
        WRITE_ROLE_POLICY,
    )

    assert WRITE_ROLE_POLICY["ai"] == frozenset()
    assert "ai" not in READ_OPEN_DOMAINS
    assert READ_ROLE_POLICY["ai"] == frozenset(role.value for role in UserRole)
    assert len(READ_ROLE_POLICY["ai"]) == 9


def test_anonymous_ai_request_is_rejected(client):
    resp = client.get("/api/ai/ping")
    assert resp.status_code == 401, resp.text[:200]


def test_every_role_can_access_ai(client):
    for role in UserRole:
        token = _login(client, f"ai_{role.value.lower()}")
        resp = client.get("/api/ai/ping", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"{role.value}: {resp.status_code} {resp.text[:200]}"


def test_forged_role_is_forbidden(client):
    """未知角色不能借登录态进入 AI 域（fail-closed）。"""

    def _fake_user():
        return SimpleNamespace(role=SimpleNamespace(value="GUEST"))

    app.dependency_overrides[get_current_user] = _fake_user
    try:
        resp = client.get("/api/ai/ping")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 403, resp.text[:200]


def test_sparql_is_admin_only(client, monkeypatch):
    from backend.services.ai.config import get_settings

    monkeypatch.setenv("AI_SPARQL_ENABLED", "true")
    get_settings.cache_clear()
    try:
        token = _login(client, "ai_planner")
        resp = client.post(
            "/api/ai/ontology/sparql",
            json={"query": "SELECT * WHERE { ?s ?p ?o }"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        get_settings.cache_clear()
    assert resp.status_code == 403, resp.text[:200]


# ── W1.3：对外契约、错误映射与只读约束 ─────────────────────────


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_openapi_contains_all_ai_routes():
    paths = app.openapi()["paths"]
    expected = {
        "/api/ai/ping": "get",
        "/api/ai/chat": "post",
        "/api/ai/queries": "get",
        "/api/ai/queries/{trace_id}/feedback": "post",
        "/api/ai/ontology/entities": "get",
        "/api/ai/ontology/entities/{name}": "get",
        "/api/ai/ontology/search": "get",
        "/api/ai/ontology/rules": "get",
        "/api/ai/ontology/sparql": "post",
        "/api/ai/insights/dashboard": "get",
    }
    for path, method in expected.items():
        assert path in paths, f"缺少路由 {path}"
        assert method in paths[path], f"{path} 缺少 {method.upper()}"


def test_ai_disabled_closes_every_route(client, monkeypatch):
    token = _login(client, "ai_planner")
    monkeypatch.setenv("AI_ENABLED", "false")
    get_settings.cache_clear()
    try:
        cases = [
            client.get("/api/ai/ping", headers=_auth(token)),
            client.get("/api/ai/ontology/entities", headers=_auth(token)),
            client.post("/api/ai/chat", json={"question": "这周哪些工单缺料？"}, headers=_auth(token)),
        ]
    finally:
        get_settings.cache_clear()
    for resp in cases:
        assert resp.status_code == 503, resp.text[:200]
        assert resp.json()["detail"]["code"] == "AI_DISABLED"


def test_chatbi_disabled_keeps_ontology_available(client, monkeypatch):
    token = _login(client, "ai_planner")
    monkeypatch.setenv("AI_CHATBI_ENABLED", "false")
    get_settings.cache_clear()
    try:
        chat = client.post(
            "/api/ai/chat", json={"question": "这周哪些工单缺料？"}, headers=_auth(token)
        )
        entities = client.get("/api/ai/ontology/entities", headers=_auth(token))
    finally:
        get_settings.cache_clear()
    assert chat.status_code == 503, chat.text[:200]
    assert chat.json()["detail"]["code"] == "AI_CHATBI_DISABLED"
    assert entities.status_code == 200, entities.text[:200]


def test_chat_rejects_empty_question(client):
    token = _login(client, "ai_planner")
    resp = client.post("/api/ai/chat", json={"question": "   "}, headers=_auth(token))
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "AI_PARAM_INVALID"


def test_chat_is_read_only_and_returns_provenance(client, ai_dataset, session_factory):
    token = _login(client, "ai_planner")
    before = {}
    session = session_factory()
    try:
        before = {model.__tablename__: session.query(model).count() for model in BUSINESS_TABLES}
    finally:
        session.close()

    resp = client.post(
        "/api/ai/chat", json={"question": "这周哪些工单缺料？"}, headers=_auth(token)
    )
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["intent"]["code"] == "kitting_shortage"
    assert body["data"]["row_count"] == 3
    assert body["answer"].startswith("共 3 条结果")
    assert len(body["provenance"]) == body["data"]["row_count"]
    assert body["limits"]["shacl"] == "passed"
    assert body["model"] == "deterministic-v1"
    assert body["trace_id"]

    session = session_factory()
    try:
        after = {model.__tablename__: session.query(model).count() for model in BUSINESS_TABLES}
        log = session.query(AiQueryLog).filter(AiQueryLog.trace_id == body["trace_id"]).one()
    finally:
        session.close()
    assert after == before
    assert log.status == "OK"
    assert log.provenance_json


def test_queries_are_scoped_to_owner_unless_admin(client, ai_dataset):
    planner = _login(client, "ai_planner")
    finance = _login(client, "ai_finance")
    resp = client.post("/api/ai/chat", json={"question": "这周哪些工单缺料？"}, headers=_auth(planner))
    assert resp.status_code == 200, resp.text[:200]
    resp = client.post(
        "/api/ai/chat", json={"question": "30 天以上未收款的应收有哪些？"}, headers=_auth(finance)
    )
    assert resp.status_code == 200, resp.text[:200]

    own = client.get("/api/ai/queries", headers=_auth(planner))
    assert own.status_code == 200
    assert own.json()["total"] == 1
    assert {item["username"] for item in own.json()["items"]} == {"ai_planner"}

    everything = client.get("/api/ai/queries", headers=_auth(_login(client, "ai_admin")))
    assert everything.status_code == 200
    assert everything.json()["total"] >= 2
    assert {"ai_planner", "ai_finance"} <= {
        item["username"] for item in everything.json()["items"]
    }


def test_feedback_only_owner_or_admin(client, ai_dataset):
    planner = _login(client, "ai_planner")
    finance = _login(client, "ai_finance")
    resp = client.post("/api/ai/chat", json={"question": "这周哪些工单缺料？"}, headers=_auth(planner))
    trace_id = resp.json()["trace_id"]

    denied = client.post(
        f"/api/ai/queries/{trace_id}/feedback", json={"score": 1}, headers=_auth(finance)
    )
    assert denied.status_code == 403, denied.text[:200]

    accepted = client.post(
        f"/api/ai/queries/{trace_id}/feedback",
        json={"score": 1, "comment": "有帮助"},
        headers=_auth(planner),
    )
    assert accepted.status_code == 200, accepted.text[:200]
    assert accepted.json()["feedback_score"] == 1

    admin = _login(client, "ai_admin")
    overridden = client.post(
        f"/api/ai/queries/{trace_id}/feedback", json={"score": -1}, headers=_auth(admin)
    )
    assert overridden.status_code == 200, overridden.text[:200]

    invalid = client.post(
        f"/api/ai/queries/{trace_id}/feedback", json={"score": 5}, headers=_auth(planner)
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "AI_PARAM_INVALID"


@pytest.mark.parametrize(
    "question",
    [
        "这周哪些工单缺料？",
        "哪些订单 7 天内要交付但还没完工？",
        "哪些原材料低于安全库存？",
        "还有哪些 CRITICAL 的计划异常？",
        "客户 CUST001 信用超额了吗？",
        "30 天以上未收款的应收有哪些？",
        "还有哪些 CRITICAL 的不合格品没关闭？",
    ],
)
def test_admin_can_run_every_intent(client, ai_dataset, question):
    token = _login(client, "ai_admin")
    resp = client.post("/api/ai/chat", json={"question": question}, headers=_auth(token))
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["intent"]["code"]
