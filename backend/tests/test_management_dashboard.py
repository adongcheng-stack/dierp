"""经营看板 insights 规则与追溯图容器的单元测试（纯函数）。"""
from __future__ import annotations

from backend.services.planning.management_dashboard import ManagementDashboard
from backend.services.planning.traceability_engine import _Graph


class TestInsights:
    def base(self, **overrides):
        data = {
            "sales": {"orders": 5, "open_orders": 3, "amount_total": 100.0, "amount_open": 60.0},
            "production": {"orders": 9, "open_orders": 6, "by_status": {}, "completion_rate": 0.33, "delayed_orders": 0},
            "quality": {"inspections": 3, "fail_inspections": 1, "first_pass_rate": 0.98, "ncrs": 2, "ncrs_open": 0, "ncrs_equipment": 0},
            "equipment": {"oee": 0.9, "availability": 0.95, "performance": 0.9, "quality": 0.98,
                          "open_failures": 0, "downtime_hours": 0.0,
                          "work_centers": [{"work_center_id": "DRILL-A", "oee": 0.9, "downtime_hours": 0.0}]},
            "cost": {"variance_total": 0.0, "variance_by_type": {}, "settlements": 1},
            "delivery": {"delayed_sales_orders": 0, "delayed_production_orders": 0, "due_maintenance_plans": 0},
        }
        data.update(overrides)
        return data

    def test_all_normal(self):
        insights = ManagementDashboard.insights(self.base())
        assert insights == ["各项经营指标均在正常区间"]

    def test_low_oee_points_to_worst_center(self):
        data = self.base(equipment={
            "oee": 0.66, "availability": 0.8, "performance": 0.8, "quality": 0.98,
            "open_failures": 1, "downtime_hours": 2.5,
            "work_centers": [
                {"work_center_id": "DRILL-A", "oee": 0.8, "downtime_hours": 0.0},
                {"work_center_id": "DRILL-B", "oee": 0.31, "downtime_hours": 2.5},
            ],
        })
        insights = ManagementDashboard.insights(data)
        assert any("DRILL-B" in line and "31%" in line for line in insights)

    def test_open_ncr_and_delay(self):
        data = self.base(quality={"inspections": 3, "fail_inspections": 1, "first_pass_rate": 0.98,
                                  "ncrs": 2, "ncrs_open": 1, "ncrs_equipment": 1},
                         delivery={"delayed_sales_orders": 3, "delayed_production_orders": 2,
                                   "due_maintenance_plans": 2})
        insights = ManagementDashboard.insights(data)
        assert any("不合格品" in line for line in insights)
        assert any("销售订单" in line for line in insights)

    def test_cost_variance_names_biggest_type(self):
        data = self.base(cost={"variance_total": -1000.0,
                               "variance_by_type": {"MATERIAL_PRICE": -800.0, "LABOR_RATE": -200.0},
                               "settlements": 0})
        insights = ManagementDashboard.insights(data)
        assert any("MATERIAL_PRICE" in line for line in insights)


class TestTraceGraph:
    def test_node_dedupe_and_shape(self):
        g = _Graph()
        key1 = g.add_node("LOT", "L1", "批次 L1", status="ACTIVE", quantity=1.0)
        key2 = g.add_node("LOT", "L1", "批次 L1-重复")  # 同 key 去重，首见优先
        assert key1 == key2
        assert len(g.nodes) == 1
        node = g.nodes[key1]
        assert node["key"] == "LOT:L1" and node["title"] == "批次 L1"
        assert g.to_dict(key1, "FORWARD")["root"] == key1

    def test_edge_dedupe(self):
        g = _Graph()
        a = g.add_node("LOT", "L1", "批次 L1")
        b = g.add_node("PRODUCTION_ORDER", "P1", "工单 P1")
        g.add_edge(a, b, "生产订单")
        g.add_edge(a, b, "生产订单")
        assert len(g.edges) == 1

    def test_truncated_flag_default_false(self):
        g = _Graph()
        assert g.truncated is False
