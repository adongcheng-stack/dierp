"""MCP 只读工具层（W2.1）：工具清单与读写边界从 security.ttl 派生。"""
from backend.services.ai.mcp.server import MCPAuthError, authenticate, handle
from backend.services.ai.mcp.tools import boundary_problems, tool_specs

__all__ = ["MCPAuthError", "authenticate", "handle", "boundary_problems", "tool_specs"]
