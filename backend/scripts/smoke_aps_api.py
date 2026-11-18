"""APS API smoke test using FastAPI TestClient."""
from __future__ import annotations

import sys
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

print("== 1) 主数据与概览 ==")
for url in (
    "/api/planning/aps/overview",
    "/api/planning/aps/resources",
    "/api/planning/aps/skills",
    "/api/planning/aps/changeovers",
    "/api/planning/aps/calendars",
):
    response = client.get(url, headers=headers)
    print(f"GET {url} -> {response.status_code}")
    assert response.status_code == 200, response.text

overview = client.get("/api/planning/aps/overview", headers=headers).json()
print("   overview:", {k: overview[k] for k in ("runs", "operations", "exceptions", "resources", "skills", "changeovers")})
assert overview["resources"] >= 6, "资源主数据缺失"
assert overview["skills"] >= 4, "技能矩阵缺失"

print("== 2) 运行排程 ==")
response = client.post(
    "/api/planning/aps/run",
    headers=headers,
    json={"algorithm": "FORWARD", "source_type": "PRODUCTION_ORDER", "run_name": "API 冒烟正排"},
)
print(f"POST /api/planning/aps/run -> {response.status_code}")
assert response.status_code == 201, response.text
run = response.json()
run_number = run["run_number"]
print("   run:", run_number, "ops:", run["operation_count"], "exceptions:", run["exception_count"])
assert run["operation_count"] > 0, "排程未生成工序"

print("== 3) 批次 / 甘特 / 异常 ==")
detail = client.get(f"/api/planning/aps/runs/{run_number}", headers=headers)
assert detail.status_code == 200, detail.text
print("   detail ops:", len(detail.json()["operations"]))

gantt = client.get(f"/api/planning/aps/runs/{run_number}/gantt", headers=headers)
assert gantt.status_code == 200, gantt.text
gantt_rows = gantt.json()["gantt"]
print("   gantt rows:", [(row["work_center_id"], len(row["operations"])) for row in gantt_rows])
assert len(gantt_rows) > 0, "甘特图无数据"

exceptions = client.get("/api/planning/aps/exceptions", headers=headers, params={"run_number": run_number})
assert exceptions.status_code == 200
print("   exceptions:", [(row["exception_type"], row["severity"]) for row in exceptions.json()["items"]][:6])

print("== 4) 插单模拟 ==")
response = client.post(
    "/api/planning/aps/simulate",
    headers=headers,
    json={"run_number": run_number, "scenario_type": "INSERT_ORDER", "description": "API 冒烟插单模拟"},
)
print(f"POST /api/planning/aps/simulate -> {response.status_code}")
assert response.status_code == 201, response.text
scenario = response.json()
print("   scenario:", scenario["scenario_id"], "|", scenario["impact_summary"])
assert scenario["impacts"], "模拟影响明细为空"

scenarios = client.get("/api/planning/aps/scenarios", headers=headers)
assert scenarios.status_code == 200
scenario_id = scenarios.json()["items"][0]["scenario_id"]
impact_detail = client.get(f"/api/planning/aps/scenarios/{scenario_id}", headers=headers)
assert impact_detail.status_code == 200
print("   scenario detail impacts:", len(impact_detail.json()["impacts"]))

print("== 5) 发布 ==")
response = client.post(f"/api/planning/aps/runs/{run_number}/publish", headers=headers)
print(f"POST publish -> {response.status_code}")
assert response.status_code == 200, response.text
assert response.json()["status"] == "PUBLISHED", response.text

print()
print("APS API 冒烟通过")
