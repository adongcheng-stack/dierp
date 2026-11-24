"""
GENERATED FILE - DO NOT EDIT BY HAND.
Source: ontology/src/security.ttl (security overlay)
Regenerate: python backend/ontology/generate_security.py
"""

from __future__ import annotations

# 角色全集（须与 mappings.json 的 UserRole 一致，由本体门禁校验）
ROLES = frozenset({"ADMIN", "ENGINEER", "FINANCE", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "SALES", "SALES_MANAGER", "WAREHOUSE"})

# 写权限：域 -> 允许写操作的角色集合；未列出的域一律拒绝（fail-closed）
WRITE_ROLE_POLICY: dict[str, frozenset[str]] = {
    "admin": frozenset({"ADMIN"}),
    "ai": frozenset(),
    "auth": frozenset(),
    "dashboard": frozenset(),
    "eng": frozenset({"ADMIN", "ENGINEER", "GENERAL_MANAGER"}),
    "finance": frozenset({"ADMIN", "FINANCE", "GENERAL_MANAGER"}),
    "mm": frozenset({"ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "WAREHOUSE"}),
    "planning": frozenset({"ADMIN", "GENERAL_MANAGER", "PLANNER"}),
    "pp": frozenset({"ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION"}),
    "purchase": frozenset({"ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "WAREHOUSE"}),
    "qms": frozenset({"ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION"}),
    "sd": frozenset({"ADMIN", "GENERAL_MANAGER", "SALES", "SALES_MANAGER"}),
    "system": frozenset({"ADMIN"}),
    "traceability": frozenset(),
    "users": frozenset({"ADMIN"}),
}

# 只读策略：允许匿名 GET 的域
READ_OPEN_DOMAINS = frozenset({"auth", "dashboard", "eng", "finance", "mm", "planning", "pp", "purchase", "qms", "sd", "traceability"})

# 只读策略：必须登录且限定角色的域（如 users）
READ_ROLE_POLICY: dict[str, frozenset[str]] = {
    "admin": frozenset({"ADMIN"}),
    "ai": frozenset({"ADMIN", "ENGINEER", "FINANCE", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "SALES", "SALES_MANAGER", "WAREHOUSE"}),
    "system": frozenset({"ADMIN"}),
    "users": frozenset({"ADMIN"}),
}

# 域元信息（用于报错文案）
DOMAIN_META: dict[str, str] = {
    "admin": "EventRecord",
    "ai": "EventRecord",
    "auth": "Agent",
    "dashboard": "EventRecord",
    "eng": "Document",
    "finance": "Document",
    "mm": "Document",
    "planning": "Document",
    "pp": "Document",
    "purchase": "Document",
    "qms": "Document",
    "sd": "Document",
    "system": "NormativeRule",
    "traceability": "EventRecord",
    "users": "Agent",
}

WRITE_METHODS = frozenset({"DELETE", "PATCH", "POST", "PUT"})

JWT_SECRET_KEY_ENV = "SECRET_KEY"
JWT_ALGORITHM = "HS256"
JWT_TOKEN_EXPIRE_MINUTES = 480
JWT_REFRESH_THRESHOLD_MINUTES = 60
JWT_INSECURE_PLACEHOLDER = "your-secret-key-change-in-production"
