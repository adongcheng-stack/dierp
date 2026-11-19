"""RBAC 写权限门单元测试（SQLite 内存库隔离，不依赖 PostgreSQL）。

隔离方式：覆盖 FastAPI 的 get_db 依赖，指向 conftest 的内存库；
权限判定只看「是否到达业务校验层」，因此全程零业务数据写入。

判定技巧：放行用例发送「缺字段的无效载荷」——
  - 权限门放行 → 进入业务校验 → 400/422；
  - 权限门拦截 → 403；
  - 未登录 → 401。
"""
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

DEMO_ACCOUNTS = [
    ("admin", UserRole.ADMIN),
    ("jihuayuan", UserRole.PLANNER),
    ("yewuyuan", UserRole.SALES),
    ("cangkuyuan", UserRole.WAREHOUSE),
]


@pytest.fixture()
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    seed = Session()
    for username, role in DEMO_ACCOUNTS:
        seed.add(
            User(
                username=username,
                email=f"{username}@ut.local",
                full_name=username,
                password_hash=pwd_context.hash("admin123"),
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


def _login(client: TestClient, username: str, password: str = "admin123") -> str:
    resp = client.post("/api/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text[:200]
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_policy_covers_demo_roles():
    from backend.api.routers.auth import WRITE_ROLE_POLICY

    all_roles = {r.value for r in UserRole}
    for domain, allowed in WRITE_ROLE_POLICY.items():
        assert allowed <= all_roles, f"{domain} 策略含未知角色"


def test_anonymous_write_rejected(client):
    """未携带 token 的写操作必须 401（不再裸奔）。"""
    for path in ["/api/sd/customers", "/api/qms/inspections", "/api/purchase/purchase-orders/x/receive"]:
        resp = client.post(path, json={})
        assert resp.status_code == 401, f"{path} 期望 401，实际 {resp.status_code}"


def test_planner_cannot_write_sales_domain(client):
    token = _login(client, "jihuayuan")  # PLANNER
    resp = client.post("/api/sd/customers", json={}, headers=_auth(token))
    assert resp.status_code == 403, resp.text[:200]
    assert "无权" in resp.json()["detail"]


def test_warehouse_cannot_write_planning_domain(client):
    token = _login(client, "cangkuyuan")  # WAREHOUSE
    resp = client.post("/api/planning/planned-orders/X/release", json={}, headers=_auth(token))
    assert resp.status_code == 403, resp.text[:200]


def test_sales_passes_gate_on_sales_domain(client):
    """SALES 在销售域放行：无效载荷应到校验层（4xx）而不是 403。"""
    token = _login(client, "yewuyuan")
    resp = client.post("/api/sd/customers", json={}, headers=_auth(token))
    assert resp.status_code in (400, 422), resp.text[:200]


def test_admin_passes_gate_on_qms_domain(client):
    token = _login(client, "admin")
    resp = client.post("/api/qms/inspections", json={}, headers=_auth(token))
    # 400/422 = 已通过权限门、到达业务校验层（该路由自行做字段校验）
    assert resp.status_code in (400, 422), resp.text[:200]


def test_get_remains_open_for_smoke_scripts(client):
    """只读端点保持无鉴权可用（既有 API 契约 + 冒烟脚本契约）。

    回归背景：写权限门若依赖 get_current_user（auto_error=True），
    匿名 GET 会被连带 401。因此必须逐个域断言，不能只测新路由。
    """
    for path in [
        "/api/sd/customers",
        "/api/pp/production-orders",
        "/api/mm/materials",
        "/api/eng/boms",
        "/api/planning/planned-orders",
        "/api/qms/inspections",
        "/api/purchase/purchase-orders",
        "/api/traceability/overview",
        "/api/dashboard/management",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 匿名 GET 应放行，实际 {resp.status_code}"


def test_cors_preflight_is_anonymous(client):
    """浏览器 CORS 预检（OPTIONS）不能要求 token，否则前端写操作全挂。"""
    resp = client.options(
        "/api/sd/customers",
        headers={
            "Origin": "http://localhost:3200",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert resp.status_code in (200, 204), resp.text[:200]


def test_login_requires_existing_user(client):
    resp = client.post("/api/auth/login", data={"username": "nobody", "password": "x"})
    assert resp.status_code == 401
