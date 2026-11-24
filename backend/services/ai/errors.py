"""AI 统一异常与错误码（设计 §7.5）。

所有 AI 失败路径都抛 ``AIException``；路由层把它序列化为
``{"code", "message", "trace_id"}`` 并按 ``http_status`` 返回。
"""
from __future__ import annotations

from typing import Final

# 错误码 → HTTP 状态（与设计 §7.5 表逐项对应）
ERROR_HTTP_STATUS: Final[dict[str, int]] = {
    "AI_DISABLED": 503,
    "AI_CHATBI_DISABLED": 503,
    "AI_INTENT_UNKNOWN": 422,
    "AI_PARAM_INVALID": 422,
    "AI_PERMISSION_DENIED": 403,
    "AI_QUERY_TOO_BROAD": 422,
    "AI_EXECUTION_TIMEOUT": 504,
    "AI_LLM_EGRESS_BLOCKED": 503,
    "AI_EXECUTION_FAILED": 500,
    "AI_PROVENANCE_INCOMPLETE": 500,
    "AI_RATE_LIMITED": 429,
}

DEFAULT_MESSAGES: Final[dict[str, str]] = {
    "AI_DISABLED": "AI 功能已关闭",
    "AI_CHATBI_DISABLED": "AI 问答功能已关闭（本体检索仍可用）",
    "AI_INTENT_UNKNOWN": "无法识别该问题对应的查询意图",
    "AI_PARAM_INVALID": "查询参数不合法",
    "AI_PERMISSION_DENIED": "当前角色无权执行该查询",
    "AI_QUERY_TOO_BROAD": "查询范围过大，请补充过滤条件",
    "AI_EXECUTION_TIMEOUT": "查询超时",
    "AI_LLM_EGRESS_BLOCKED": "LLM 数据出域配置不允许该调用",
    "AI_EXECUTION_FAILED": "查询执行失败",
    "AI_PROVENANCE_INCOMPLETE": "溯源信息不完整，回答已拒绝",
    "AI_RATE_LIMITED": "请求过于频繁，请稍后再试",
}

# 审计状态（设计 §9.3），集中定义避免字符串漂移
AUDIT_STATUSES: Final[frozenset[str]] = frozenset({
    "OK",
    "REJECTED_SCHEMA",
    "REJECTED_INTENT",
    "REJECTED_PARAM",
    "REJECTED_SHACL",
    "REJECTED_PERMISSION",
    "REJECTED_TOO_BROAD",
    "REJECTED_TIMEOUT",
    "REJECTED_RATE_LIMIT",
    "FAILED",
})


class AIException(Exception):
    """结构化 AI 异常；``code`` 必须来自 §7.5 的错误码表。"""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        trace_id: str | None = None,
        http_status: int | None = None,
        reject_reason: str | None = None,
    ) -> None:
        if code not in ERROR_HTTP_STATUS:
            raise ValueError(f"未知 AI 错误码: {code}")
        self.code = code
        self.message = message or DEFAULT_MESSAGES[code]
        self.trace_id = trace_id
        self.http_status = http_status or ERROR_HTTP_STATUS[code]
        self.reject_reason = reject_reason
        super().__init__(self.message)

    def to_payload(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "trace_id": self.trace_id}
