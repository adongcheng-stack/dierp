"""RBAC 写权限门单元测试（TestClient + 真实用户角色）。

判定技巧：放行用例发送「缺字段的无效载荷」——
  - 权限门放行 → 进入 Pydantic 校验 → 422；
  - 权限门拦截 → 403。
全程不产生任何业务数据。
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def _login(username: str, password: str = "admin123") -> str:
    resp = client.post("/api/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text[:200]
    return resp.json()["access_token"]


def test_policy_covers_demo_roles():
    from backend.api.routers.auth import WRITE_ROLE_POLICY, UserRole

    all_roles = {r.value for r in UserRole}
    for domain, allowed in WRITE_ROLE_POLICY.items():
        assert allowed <= all_roles, f"{domain} 策略含未知角色"


def test_planner_cannot_write_sales_domain():
    token = _login("jihuayuan")  # PLANNER
    resp = client.post(
        "/api/sd/customers",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text[:200]
    assert "无权" in resp.json()["detail"]


def test_sales_passes_gate_on_sales_domain():
    """SALES 在销售域放行：无效载荷应到 422（校验层）而不是 403（权限层）。"""
    token = _login("yewuyuan")
    resp = client.post(
        "/api/sd/customers",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text[:200]


def test_admin_passes_gate_on_qms_domain():
    token = _login("admin")
    resp = client.post(
        "/api/qms/inspections",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 400/422 = 已通过权限门、到达业务校验层（该路由自行做字段校验）
    assert resp.status_code in (400, 422), resp.text[:200]


def test_get_remains_open_for_smoke_scripts():
    """只读端点保持无鉴权可用（冒烟脚本契约）。"""
    resp = client.get("/api/traceability/overview")
    assert resp.status_code == 200
    resp = client.get("/api/dashboard/management")
    assert resp.status_code == 200


def test_anonymous_write_rejected():
    """未携带 token 的写操作必须 401（不再裸奔）。"""
    resp = client.post("/api/sd/customers", json={})
    assert resp.status_code == 401
