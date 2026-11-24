"""进程内滑动窗口限流（设计 §7.3 第 2 步、计划 W1.2 #5）。

只按用户名计数，窗口 60 秒；超限抛 ``AI_RATE_LIMITED``（HTTP 429）。
时钟可注入，测试用 ``reset()`` 清空。
"""
from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException

WINDOW_SECONDS = 60


class SlidingWindowRateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._events: dict[str, deque[float]] = {}

    def reset(self) -> None:
        self._events.clear()

    def check(self, key: str, limit: int | None = None) -> None:
        limit = limit if limit is not None else get_settings().ai_rate_limit_per_minute
        now = self._clock()
        window = self._events.setdefault(key, deque())
        while window and now - window[0] >= WINDOW_SECONDS:
            window.popleft()
        if len(window) >= limit:
            raise AIException(
                "AI_RATE_LIMITED",
                f"请求过于频繁：{WINDOW_SECONDS} 秒内最多 {limit} 次",
            )
        window.append(now)


_LIMITER = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _LIMITER
