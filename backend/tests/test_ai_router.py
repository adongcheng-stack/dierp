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
from backend.common.models.user import User, UserRole

PASSWORD = "admin123"


@pytest.fixture()
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
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
