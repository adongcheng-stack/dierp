"""Planning API smoke test using FastAPI TestClient."""
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

checks = [
    ("GET", "/api/planning/overview", None),
    ("GET", "/api/planning/mps", None),
    ("GET", "/api/planning/mrp/runs", None),
    ("GET", "/api/planning/planned-orders?limit=5", None),
    ("GET", "/api/planning/exceptions?limit=5", None),
    ("GET", "/api/planning/kitting?limit=5", None),
    ("GET", "/api/planning/policies?limit=5", None),
]

for method, url, payload in checks:
    response = client.request(method, url, headers=headers, json=payload)
    print(f"{method} {url} -> {response.status_code}")
    assert response.status_code == 200, response.text
    data = response.json()
    if isinstance(data, dict):
        preview = {k: data[k] for k in list(data)[:4]}
    else:
        preview = data[:2]
    print("  ", preview)

runs = client.get("/api/planning/mrp/runs", headers=headers).json()["items"]
if runs:
    latest = runs[0]["run_number"]
    detail = client.get(f"/api/planning/mrp/runs/{latest}", headers=headers)
    assert detail.status_code == 200, detail.text
    print("MRP detail:", latest, len(detail.json().get("requirements", [])), "requirements")

plans = client.get(
    "/api/planning/planned-orders?status=PLANNED&limit=50", headers=headers
).json()["items"]
if plans:
    target = plans[0]
    confirm = client.post(
        f"/api/planning/planned-orders/{target['planned_order_number']}/confirm",
        headers=headers,
    )
    print("confirm:", confirm.status_code, confirm.json().get("status"))
    release = client.post(
        f"/api/planning/planned-orders/{target['planned_order_number']}/release",
        headers=headers,
        json={},
    )
    print("release:", release.status_code, release.json())
    assert release.status_code == 200, release.text

policies = client.get("/api/planning/policies?limit=1", headers=headers).json()["items"]
if policies:
    policy = policies[0]
    update = client.put(
        f"/api/planning/policies/{policy['policy_id']}",
        headers=headers,
        json={
            "material_code": policy["material_code"],
            "mrp_type": policy["mrp_type"],
            "procurement_type": policy["procurement_type"],
            "lot_sizing_rule": policy["lot_sizing_rule"],
            "fixed_lot_size": policy["fixed_lot_size"],
            "min_order_qty": policy["min_order_qty"],
            "max_order_qty": policy["max_order_qty"],
            "order_multiple": policy["order_multiple"],
            "eoq": policy["eoq"],
            "lead_time_days": policy["lead_time_days"],
            "safety_time_days": policy["safety_time_days"],
            "safety_stock": policy["safety_stock"],
            "reorder_point": policy["reorder_point"],
            "planner_code": policy["planner_code"],
            "abc_class": policy["abc_class"],
            "is_active": policy["is_active"],
            "remarks": "API smoke update",
        },
    )
    print("policy update:", update.status_code)

print("ALL PLANNING API CHECKS PASSED")
