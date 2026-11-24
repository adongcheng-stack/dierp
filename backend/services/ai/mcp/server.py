"""MCP JSON-RPC 子集服务端：``initialize`` / ``ping`` / ``tools/list`` / ``tools/call``。

- 鉴权：``Authorization: Bearer <AI_MCP_TOKEN>``；token 未配置时 fail-closed；
- 执行：复用 ``pipeline.run_intent``（同一套 SHACL/权限/执行/审计闸），只读；
- 审计：``username = mcp:<sha256(token)[:12]>``，token 本身不落库。
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from backend.services.ai.config import get_settings
from backend.services.ai.errors import AIException
from backend.services.ai.mcp.tools import tool_specs
from backend.services.ai.pipeline import run_intent

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "dierp-erp-mcp", "version": "1.0.0"}


class MCPAuthError(Exception):
    """鉴权失败；路由层转为 HTTP 401。"""


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    parts = authorization.strip().split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def authenticate(authorization: str | None) -> tuple[str, str]:
    """返回 (审计用 username, 角色)；未配置 token 或 token 不匹配时抛错。"""
    settings = get_settings()
    expected = settings.ai_mcp_token
    if not expected:
        raise MCPAuthError("MCP 未启用：未配置 AI_MCP_TOKEN")
    token = _bearer_token(authorization)
    if not token or not hmac.compare_digest(token, expected):
        raise MCPAuthError("MCP token 无效")
    return f"mcp:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:12]}", settings.ai_mcp_role.upper()


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(
    payload: Any,
    username: str,
    role: str,
    db: Any,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _error(None, -32600, "invalid request")

    method = payload.get("method")
    request_id_value = payload.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id_value,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id_value, "result": {}}
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id_value,
            "result": {"tools": tool_specs(role)},
        }
    if method == "tools/call":
        params = payload.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not name:
            return _error(request_id_value, -32602, "params.name 必须是非空字符串")
        if not isinstance(arguments, dict):
            return _error(request_id_value, -32602, "params.arguments 必须是对象")
        try:
            result = run_intent(
                name,
                arguments,
                _MCPUser(username=username, role=role),
                db,
                request_id=request_id,
            )
        except AIException as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id_value,
                "result": {
                    "content": [{"type": "text", "text": exc.message}],
                    "isError": True,
                    "_meta": {"code": exc.code, "trace_id": exc.trace_id},
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": request_id_value,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "structuredContent": result,
                "isError": False,
            },
        }

    return _error(request_id_value, -32601, f"method not found: {method}")


class _MCPUser:
    """MCP 调用的身份载体：只暴露审计与权限需要的两个属性。"""

    def __init__(self, username: str, role: str) -> None:
        self.username = username
        self.role = role
