"""P1 意图注册表：7 个手写只读意图。

导入本包即把各意图的 ``SPEC`` 注册进 ``backend.services.ai.intent.INTENTS``。
模块顺序与实施计划 W1.1 的清单一致。
"""
from __future__ import annotations

from backend.services.ai.intent import INTENTS, IntentSpec

from . import credit, inventory, kitting, orders, planning_exceptions, quality, receivables

_MODULES = (
    kitting, inventory, orders, planning_exceptions, credit, receivables, quality,
)

EXPECTED_INTENTS = 7

INTENT_REGISTRY: dict[str, IntentSpec] = {module.SPEC.code: module.SPEC for module in _MODULES}

if len(INTENT_REGISTRY) != EXPECTED_INTENTS:
    raise RuntimeError(f"意图注册表必须恰好 {EXPECTED_INTENTS} 个，当前 {len(INTENT_REGISTRY)}")

INTENTS.update(INTENT_REGISTRY)

__all__ = ["EXPECTED_INTENTS", "INTENT_REGISTRY"]
