"""W2.3 ERP↔MES 语义映射 v1 验收：本体锚点、枚举合法性、未匹配显式化、只读接口。"""
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
from backend.api.routers.auth import pwd_context
from backend.common.database.base import get_db
from backend.common.models.user import User, UserRole
from backend.services.ai import semantics as semantics_mod
from backend.services.ai.config import get_settings
from backend.services.ai.ontology_service import get_ontology_service
from backend.services.ai.semantics import build_mes_mapping

PASSWORD = "admin123"


@pytest.fixture(autouse=True)
def _fresh_settings():
    get_settings.cache_clear()
    semantics_mod.invalidate_cache()
    yield
    get_settings.cache_clear()
    semantics_mod.invalidate_cache()


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
                username=f"sem_{role.value.lower()}",
                email=f"sem_{role.value.lower()}@ut.local",
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
    monkeypatch.setenv("AI_ENABLED", "true")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _login(client: TestClient, username: str) -> str:
    resp = client.post("/api/auth/login", data={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text[:200]
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_mapping_anchors_existing_ontology_and_enums():
    report = build_mes_mapping()
    assert report["problems"] == []
    assert report["items"]
    assert report["unmapped"] == ["ScrapRecord"]
    assert report["coverage"] == pytest.approx(6 / 7, abs=1e-4)

    ontology = get_ontology_service()
    enumerations = ontology.mappings["enumerations"]
    for item in report["items"]:
        described = ontology.describe(item["ontology_class"])
        properties = {prop["name"] for prop in described["properties"]}
        for field in item["fields"]:
            assert field["ontology_property"] in properties
            if field["enum"]:
                assert field["enum"] in enumerations
                assert set(field["value_map"].values()) <= set(enumerations[field["enum"]])


def test_mes_semantics_endpoint_is_read_only_and_role_gated(client):
    token = _login(client, "sem_general_manager")
    resp = client.get("/api/ai/semantics/mes", headers=_auth(token))
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body["source_system"] == "MES"
    assert body["items"]
    assert body["unmapped"] == ["ScrapRecord"]

    # 只读：接口不接受写方法
    resp = client.post("/api/ai/semantics/mes", headers=_auth(token), json={})
    assert resp.status_code in (404, 405)
