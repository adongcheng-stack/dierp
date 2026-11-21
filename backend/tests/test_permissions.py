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
    ("caiwuyuan", UserRole.FINANCE),
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


# ── P0 安全回归 ────────────────────────────────────────────────────────────

def test_finance_write_requires_finance_role(client):
    """finance 域期间关闭是高危操作：仓库角色必须被写门拦截（原漏洞）。"""
    token = _login(client, "cangkuyuan")  # WAREHOUSE
    resp = client.post(
        "/api/finance/periods/2026-11/close", json={}, headers=_auth(token)
    )
    assert resp.status_code == 403, resp.text[:200]


def test_finance_role_passes_write_gate(client):
    """财务角色可到达业务层（4xx/2xx 均可，关键是不得 403）。"""
    token = _login(client, "caiwuyuan")  # FINANCE
    resp = client.post(
        "/api/finance/periods/2026-11/close", json={}, headers=_auth(token)
    )
    assert resp.status_code != 403, resp.text[:200]


def test_users_read_requires_admin(client):
    """用户列表/角色枚举不再匿名可读（原漏洞）。"""
    assert client.get("/api/users").status_code == 401
    token = _login(client, "cangkuyuan")
    assert client.get("/api/users", headers=_auth(token)).status_code == 403
    token = _login(client, "admin")
    assert client.get("/api/users", headers=_auth(token)).status_code == 200


def test_unlisted_domain_is_fail_closed(client, monkeypatch):
    """本体未声明的域默认拒绝，防止新增域自动裸奔。"""
    from backend.api.routers import auth as auth_module

    monkeypatch.delitem(auth_module.WRITE_ROLE_POLICY, "sd")
    token = _login(client, "yewuyuan")  # SALES，原本在 sd 允许列表
    resp = client.post("/api/sd/customers", json={}, headers=_auth(token))
    assert resp.status_code == 403, resp.text[:200]


def test_secret_key_is_not_public_placeholder():
    """JWT 密钥不得再使用仓库中公开的占位默认值。"""
    from backend.api.routers.auth import JWT_INSECURE_PLACEHOLDER, SECRET_KEY

    assert SECRET_KEY and SECRET_KEY.strip()
    assert SECRET_KEY != JWT_INSECURE_PLACEHOLDER


def test_operation_logs_admin_only(client):
    """审计日志仅 ADMIN 可读（本体 admin 域读策略）。"""
    assert client.get("/api/admin/operation-logs").status_code == 401
    token = _login(client, "cangkuyuan")
    assert client.get("/api/admin/operation-logs", headers=_auth(token)).status_code == 403
    token = _login(client, "admin")
    resp = client.get("/api/admin/operation-logs", headers=_auth(token))
    assert resp.status_code == 200, resp.text[:200]
    assert "items" in resp.json()


def test_audit_log_records_write_operations(client):
    """写操作应落一条审计记录（append-only）。"""
    from backend.common.models.audit import OperationLog

    token = _login(client, "admin")
    before = client.get("/api/admin/operation-logs", headers=_auth(token)).json()["total"]
    client.post("/api/sd/customers", json={}, headers={**_auth(token), "X-Test": "audit"})
    after = client.get("/api/admin/operation-logs", headers=_auth(token)).json()["total"]
    assert after > before, (before, after)


def test_export_requires_admin(client):
    assert client.get("/api/admin/export/customers").status_code == 401
    token = _login(client, "cangkuyuan")
    assert client.get("/api/admin/export/customers", headers=_auth(token)).status_code == 403


def test_export_import_json_roundtrip(client):
    """JSON 导出/导入闭环：导入幂等，重复导入跳过。"""
    from backend.common.models.sd import Customer

    token = _login(client, "admin")
    headers = _auth(token)
    # 直接种子一条客户，避免受其他测试的业务校验影响
    from backend.api.routers.auth import pwd_context

    resp = client.post(
        "/api/admin/import/customers",
        headers=headers,
        json={"rows": [{"customer_id": "C-EXP-1", "legal_name": "导出测试客户", "customer_status": "ACTIVE"}]},
    )
    assert resp.status_code == 200, resp.text[:200]
    assert resp.json()["created"] == 1

    again = client.post(
        "/api/admin/import/customers",
        headers=headers,
        json={"rows": [{"customer_id": "C-EXP-1", "legal_name": "重复"}]},
    )
    assert again.json()["skipped"] == 1

    exported = client.get("/api/admin/export/customers?format=json", headers=headers)
    assert exported.status_code == 200
    ids = [row["customer_id"] for row in exported.json()["items"]]
    assert "C-EXP-1" in ids

    csv_resp = client.get("/api/admin/export/customers?format=csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "customer_id" in csv_resp.text


# ── 组织架构与系统管理 ────────────────────────────────────────────────────

def test_system_domain_admin_only(client):
    assert client.get("/api/system/roles").status_code == 401
    token = _login(client, "cangkuyuan")
    assert client.get("/api/system/roles", headers=_auth(token)).status_code == 403
    token = _login(client, "admin")
    assert client.get("/api/system/roles", headers=_auth(token)).status_code == 200


def test_department_tree_crud(client):
    token = _login(client, "admin")
    headers = _auth(token)
    created = client.post("/api/system/departments", headers=headers, json={
        "code": "D-UT", "name": "单元测试部", "level": 1,
        "department_type": "DEPARTMENT", "status": "ACTIVE", "sort_order": 1,
    })
    assert created.status_code == 200, created.text[:200]
    item_id = created.json()["id"]
    tree = client.get("/api/system/departments/tree", headers=headers).json()
    assert any(node["code"] == "D-UT" for node in tree)
    assert client.delete(f"/api/system/departments/{item_id}", headers=headers).status_code == 200


def test_role_menu_assignment(client):
    token = _login(client, "admin")
    headers = _auth(token)
    menu = client.post("/api/system/menus", headers=headers, json={
        "code": "M-UT", "name": "单测菜单", "menu_type": "MENU", "status": "ACTIVE",
    })
    assert menu.status_code == 200, menu.text[:200]
    menu_id = menu.json()["id"]
    resp = client.post("/api/system/roles/SALES/menus", headers=headers,
                       json={"menu_ids": [menu_id]})
    assert resp.status_code == 200, resp.text[:200]
    assigned = client.get("/api/system/roles/SALES/menus", headers=headers).json()["menu_ids"]
    assert menu_id in assigned


def test_parameter_crud(client):
    from backend.common.models.admin import SystemParameter

    token = _login(client, "admin")
    headers = _auth(token)
    created = client.post("/api/system/parameters", headers=headers, json={
        "param_key": "ut.param", "param_name": "单测参数", "param_value": "42",
        "param_type": "INT", "is_system": False,
    })
    assert created.status_code == 200, created.text[:200]
    item_id = created.json()["id"]
    assert client.get("/api/system/parameters/key/ut.param", headers=headers).json()["param_value"] == "42"
    assert client.delete(f"/api/system/parameters/{item_id}", headers=headers).status_code == 200


def test_login_log_written_on_success(client):
    from backend.common.models.admin import LoginLog, LoginStatus

    _login(client, "admin")
    db = next(client.app.dependency_overrides[get_db]())
    try:
        log = db.query(LoginLog).filter(LoginLog.username == "admin").order_by(LoginLog.id.desc()).first()
        assert log is not None
        assert log.login_status == LoginStatus.SUCCESS
    finally:
        db.close()
