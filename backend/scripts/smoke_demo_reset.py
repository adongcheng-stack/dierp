"""演示数据一键重置 API 冒烟测试（FastAPI TestClient，无需启动服务）。

覆盖：
1) 管理员登录 -> POST /api/planning/demo/reset
2) 返回清理统计、资源复位、种子数量、已发布排程批次与插单场景
3) 连续执行两次结果稳定（幂等）
4) 非管理员被 403 拒绝
"""
from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.api.routers.auth import get_current_user  # noqa: E402
from backend.common.models.user import User, UserRole  # noqa: E402

client = TestClient(app)
login = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
assert login.status_code == 200, login.text
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("== 1) 管理员重置演示数据 ==")
response = client.post("/api/planning/demo/reset", headers=headers, json={})
print(f"POST /api/planning/demo/reset -> {response.status_code}")
assert response.status_code == 200, response.text
result = response.json()
cleared = result["cleared"]
seeded = result["seeded"]
print("   cleared:", cleared)
print("   seeded :", seeded)

assert cleared["schedule_runs"] >= 1, "应清理历史排程批次"
assert seeded["maintenance_plans"] >= 6, "维护计划种子缺失"
assert seeded["maintenance_orders"] >= 1, "维护工单种子缺失"
assert seeded["equipment_failures"] >= 1, "故障记录种子缺失"
assert seeded.get("run_number"), "未重建排程批次"
assert seeded.get("operations", 0) > 0, "排程工序为空"
assert seeded.get("scenario_id"), "未生成插单场景"

print("== 2) 重置后各页面接口可用 ==")
run_number = seeded["run_number"]
for url in (
    "/api/planning/aps/overview",
    "/api/planning/aps/runs",
    f"/api/planning/aps/runs/{run_number}/gantt",
    "/api/planning/aps/scenarios",
    "/api/planning/eam/overview",
    "/api/planning/eam/oee",
):
    response = client.get(url, headers=headers)
    print(f"GET {url} -> {response.status_code}")
    assert response.status_code == 200, response.text

detail = client.get(f"/api/planning/aps/runs/{run_number}", headers=headers).json()
print("   排程状态:", detail.get("status"), "· 工序:", len(detail.get("operations", [])))
assert detail.get("status") == "PUBLISHED", "重建的排程应已发布"

print("== 3) 幂等：再执行一次 ==")
response = client.post("/api/planning/demo/reset", headers=headers, json={})
assert response.status_code == 200, response.text
second = response.json()["seeded"]
print("   seeded :", second)
assert second["maintenance_plans"] == seeded["maintenance_plans"]
assert second["operations"] > 0 and second.get("scenario_id")

print("== 4) 非管理员被拒绝 ==")
fake = User(
    id=99999,
    username="smoke_planner",
    full_name="冒烟计划员",
    email="smoke_planner@example.com",
    password_hash="x",
    role=UserRole.PLANNER,
    is_active=True,
)


def _override_user() -> User:
    return fake


app.dependency_overrides[get_current_user] = _override_user
try:
    response = client.post("/api/planning/demo/reset", json={})
    print(f"POST /api/planning/demo/reset (PLANNER) -> {response.status_code}")
    assert response.status_code == 403, response.text
finally:
    app.dependency_overrides.pop(get_current_user, None)

print("\n[OK] 演示数据重置 API 冒烟通过")
