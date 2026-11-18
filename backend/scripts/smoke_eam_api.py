"""EAM 设备管理 API 冒烟测试（FastAPI TestClient）。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    import io

    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402

client = TestClient(app)
login = client.post(
    "/api/auth/login",
    data={"username": "admin", "password": "admin123"},
)
assert login.status_code == 200, login.text
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("== 1) 概览与列表 ==")
response = client.get("/api/planning/eam/overview", headers=headers)
print(f"GET /api/planning/eam/overview -> {response.status_code}")
assert response.status_code == 200, response.text
overview = response.json()
print(
    "   overview:",
    {k: overview[k] for k in ("plans", "due_plans", "orders", "orders_done", "failures", "open_failures")},
)
assert overview["plans"] >= 6, "维护计划种子缺失"
assert overview["failures"] >= 1, "故障记录种子缺失"

for url in (
    "/api/planning/eam/plans",
    "/api/planning/eam/orders",
    "/api/planning/eam/failures",
    "/api/planning/eam/oee",
):
    response = client.get(url, headers=headers)
    print(f"GET {url} -> {response.status_code}")
    assert response.status_code == 200, response.text

print("== 2) 到期保养自动生成 ==")
response = client.post("/api/planning/eam/generate-due-orders", headers=headers, json={})
print(f"POST /api/planning/eam/generate-due-orders -> {response.status_code}")
assert response.status_code == 200, response.text
generated = response.json()
print(f"   生成 {generated['generated']} 张维护工单")
for order in generated["items"]:
    print(f"   {order['order_number']} {order['resource_id']} {order['maintenance_type']}")
response = client.post("/api/planning/eam/generate-due-orders", headers=headers, json={})
assert response.status_code == 200
assert response.json()["generated"] == 0, "generate-due-orders 不幂等"
print("   幂等校验通过（重复执行生成 0 张）")

print("== 3) 新建 / 更新维护计划 ==")
response = client.post(
    "/api/planning/eam/plans",
    headers=headers,
    json={
        "resource_id": "RES-DRILL-D-01",
        "maintenance_type": "LUBRICANT",
        "cycle_days": 14,
        "next_due_at": (datetime.now() + timedelta(days=5)).isoformat(),
        "responsible": "冒烟测试",
        "notes": "API 冒烟新建维护计划",
    },
)
print(f"POST /api/planning/eam/plans -> {response.status_code}")
assert response.status_code == 201, response.text
plan = response.json()
plan_id = plan["plan_id"]
print(f"   新建计划 {plan_id} {plan['resource_id']} {plan['maintenance_type']} 周期 {plan['cycle_days']} 天")

response = client.put(
    f"/api/planning/eam/plans/{plan_id}",
    headers=headers,
    json={"cycle_days": 21, "responsible": "冒烟测试-改"},
)
print(f"PUT /api/planning/eam/plans/{plan_id} -> {response.status_code}")
assert response.status_code == 200, response.text
assert response.json()["cycle_days"] == 21, "维护计划更新未生效"

print("== 4) 完成维护工单 ==")
orders = client.get("/api/planning/eam/orders", headers=headers, params={"status": "PLANNED"}).json()
if not orders["items"]:
    # 保证脚本可重复运行：把一条计划拨到过去，生成一张 PLANNED 工单（避开历史工单日期，绕过幂等）
    plans = client.get("/api/planning/eam/plans", headers=headers, params={"limit": 50}).json()
    assert plans["items"], "没有维护计划可拨动（先运行 backend/upgrade_planning.py）"
    seed_plan = plans["items"][0]
    plan_orders = client.get(
        "/api/planning/eam/orders",
        headers=headers,
        params={"plan_id": seed_plan["plan_id"], "limit": 200},
    ).json()
    taken = {str(o["planned_date"])[:10] for o in plan_orders["items"]}
    due = datetime.now() - timedelta(days=1)
    while due.strftime("%Y-%m-%d") in taken:
        due -= timedelta(days=1)
    response = client.put(
        f"/api/planning/eam/plans/{seed_plan['plan_id']}",
        headers=headers,
        json={"next_due_at": due.strftime("%Y-%m-%dT08:00:00")},
    )
    assert response.status_code == 200, response.text
    response = client.post("/api/planning/eam/generate-due-orders", headers=headers, json={})
    assert response.status_code == 200, response.text
    print(f"   拨动计划 {seed_plan['plan_id']} 至 {due:%m-%d} 并生成 {response.json()['generated']} 张工单")
    orders = client.get("/api/planning/eam/orders", headers=headers, params={"status": "PLANNED"}).json()
assert orders["items"], "没有 PLANNED 状态维护工单可完成"
target = orders["items"][0]
response = client.post(
    f"/api/planning/eam/orders/{target['order_number']}/complete",
    headers=headers,
    json={"downtime_hours": 1.0, "result_note": "API 冒烟：完成保养"},
)
print(f"POST /api/planning/eam/orders/{target['order_number']}/complete -> {response.status_code}")
assert response.status_code == 200, response.text
assert response.json()["status"] == "DONE", "维护工单完成状态未生效"

print("== 5) 故障上报与解决 ==")
response = client.post(
    "/api/planning/eam/failures",
    headers=headers,
    json={
        "resource_id": "RES-DRILL-C-01",
        "severity": "MEDIUM",
        "description": "API 冒烟：外形铣床冷却泵异响",
        "downtime_hours": 0.8,
    },
)
print(f"POST /api/planning/eam/failures -> {response.status_code}")
assert response.status_code == 201, response.text
failure = response.json()
failure_number = failure["failure_number"]
print(f"   上报 {failure_number} @ {failure['work_center_id']} 状态={failure['status']}")
assert failure["work_center_id"] == "DRILL-C", "故障未冗余工作中心"

response = client.post(
    f"/api/planning/eam/failures/{failure_number}/resolve",
    headers=headers,
    json={"root_cause": "冷却泵轴承磨损", "action_taken": "更换轴承", "downtime_hours": 0.8},
)
print(f"POST resolve -> {response.status_code}")
assert response.status_code == 200, response.text
assert response.json()["status"] == "CLOSED", "故障未关闭"

print("== 6) OEE 快照 ==")
oee = client.get("/api/planning/eam/oee", headers=headers).json()
print(f"   全厂 OEE={oee['summary']['oee']} (A={oee['summary']['availability']} P={oee['summary']['performance']} Q={oee['summary']['quality']})")
drill_b = next((r for r in oee["work_centers"] if r["work_center_id"] == "DRILL-B"), None)
assert drill_b is not None and drill_b["downtime_hours"] > 0, "DRILL-B 停机未计入 OEE"
print(f"   DRILL-B: OEE={drill_b['oee']} 停机={drill_b['downtime_hours']}h 停机资源={drill_b['down_resources']}")

print()
print("EAM API 冒烟通过")
