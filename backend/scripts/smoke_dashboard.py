"""经营看板冒烟测试：引擎 KPI + TestClient API（只读，不产生数据）。

Run: python backend/scripts/smoke_dashboard.py
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
from backend.common.database.base import SessionLocal  # noqa: E402
from backend.common.models import eng, mm, pp, sd, planning  # noqa: E402,F401
from backend.services.planning.management_dashboard import ManagementDashboard  # noqa: E402

client = TestClient(app)


def main() -> int:
    print("[1] 引擎 KPI（六域）")
    db = SessionLocal()
    try:
        data = ManagementDashboard.overview(db)
    finally:
        db.close()

    assert set(data) >= {"sales", "production", "quality", "equipment", "cost", "delivery", "generated_at"}
    assert data["sales"]["orders"] >= 5, "销售订单数异常"
    assert data["production"]["orders"] >= 9, "生产订单数异常"
    assert 0 <= data["quality"]["first_pass_rate"] <= 1, "一次合格率越界"
    assert 0 <= data["equipment"]["oee"] <= 1, "OEE 越界"
    assert data["equipment"]["open_failures"] >= 1, "未关闭故障应存在"
    assert "MATERIAL_PRICE" in data["cost"]["variance_by_type"], "缺材料价格差异"
    print(f"    销售: {data['sales']}")
    print(f"    生产: 完成率 {data['production']['completion_rate']:.0%}，逾期 {data['production']['delayed_orders']}")
    print(f"    质量: 一次合格率 {data['quality']['first_pass_rate']:.1%}，OPEN NCR {data['quality']['ncrs_open']}")
    print(f"    设备: OEE {data['equipment']['oee']:.1%}，停机 {data['equipment']['downtime_hours']}h")
    print(f"    成本: 差异合计 {data['cost']['variance_total']:,.2f}")
    print(f"    交期: {data['delivery']}")

    print("[2] 自动点评")
    insights = ManagementDashboard.insights(data)
    assert isinstance(insights, list) and len(insights) >= 1
    for line in insights:
        print("    -", line)

    print("[3] API（TestClient）")
    resp = client.get("/api/dashboard/management")
    assert resp.status_code == 200, resp.text[:200]
    payload = resp.json()
    assert payload["sales"]["orders"] == data["sales"]["orders"]
    assert isinstance(payload["insights"], list) and payload["insights"]
    print("    GET /api/dashboard/management -> 200，KPI 与引擎一致，insights 非空")

    print("\n经营看板冒烟通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
