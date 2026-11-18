"""双向追溯 API 冒烟（TestClient，不影响运行中的服务）。

Run: python backend/scripts/smoke_traceability_api.py
"""
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


def main() -> int:
    checks = []

    resp = client.get("/api/traceability/overview")
    checks.append(("GET /overview", resp.status_code, resp.json().get("lots") if resp.status_code == 200 else resp.text[:120]))
    assert resp.status_code == 200 and resp.json()["lots"] >= 4

    resp = client.get("/api/traceability/lots/LOT-20251230-0003")
    data = resp.json()
    keys = [n["key"] for n in data["nodes"]]
    checks.append(("GET /lots/LOT-20251230-0003", resp.status_code, f"{len(keys)} nodes"))
    assert resp.status_code == 200
    # 动态编号（种子按当天日期生成）用前缀断言
    assert any(k.startswith("NCR:") for k in keys), "正向链缺 NCR"
    assert any(k.startswith("EQUIPMENT_FAILURE:") for k in keys), "正向链缺设备故障"

    resp = client.get("/api/traceability/materials/HF1004ENIGAB02")
    keys = [n["key"] for n in resp.json()["nodes"]]
    checks.append(("GET /materials/HF1004ENIGAB02", resp.status_code, f"{len(keys)} nodes"))
    assert resp.status_code == 200 and "CUSTOMER:FJ001" in keys

    resp = client.get("/api/traceability/orders/SO-20251231-0001")
    keys = [n["key"] for n in resp.json()["nodes"]]
    checks.append(("GET /orders/SO-20251231-0001", resp.status_code, f"{len(keys)} nodes"))
    assert resp.status_code == 200 and "PRODUCTION_ORDER:PO-APS-02" in keys

    resp = client.get("/api/traceability/search", params={"q": "NCR-"})
    checks.append(("GET /search?q=NCR-", resp.status_code, len(resp.json()["items"])))
    assert resp.status_code == 200 and len(resp.json()["items"]) >= 2

    resp = client.get("/api/traceability/lots/NOPE-404")
    checks.append(("GET /lots/NOPE-404", resp.status_code, resp.json().get("detail")))
    assert resp.status_code == 404

    for name, code, info in checks:
        print(f"    {name} -> {code} {info}")
    print("\n双向追溯 API 冒烟通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
