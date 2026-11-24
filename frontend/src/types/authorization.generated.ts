/**
 * GENERATED FILE - DO NOT EDIT BY HAND.
 * Source: ontology/src/security.ttl (security overlay)
 * Regenerate: python backend/ontology/generate_security.py
 */

/* eslint-disable */

export type UserRole = 'SALES' | 'SALES_MANAGER' | 'ENGINEER' | 'PLANNER' | 'PRODUCTION' | 'WAREHOUSE' | 'FINANCE' | 'GENERAL_MANAGER' | 'ADMIN'

export const WRITE_ROLE_POLICY: Record<string, string[]> = {
  "admin": ["ADMIN"],
  "ai": [],
  "auth": [],
  "dashboard": [],
  "eng": ["ADMIN", "ENGINEER", "GENERAL_MANAGER"],
  "finance": ["ADMIN", "FINANCE", "GENERAL_MANAGER"],
  "mm": ["ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "WAREHOUSE"],
  "planning": ["ADMIN", "GENERAL_MANAGER", "PLANNER"],
  "pp": ["ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION"],
  "purchase": ["ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "WAREHOUSE"],
  "qms": ["ADMIN", "GENERAL_MANAGER", "PLANNER", "PRODUCTION"],
  "sd": ["ADMIN", "GENERAL_MANAGER", "SALES", "SALES_MANAGER"],
  "system": ["ADMIN"],
  "traceability": [],
  "users": ["ADMIN"],
}

export const READ_OPEN_DOMAINS: string[] = ["auth", "dashboard", "eng", "finance", "mm", "planning", "pp", "purchase", "qms", "sd", "traceability"]

export const READ_ROLE_POLICY: Record<string, string[]> = {
  "admin": ["ADMIN"],
  "ai": ["ADMIN", "ENGINEER", "FINANCE", "GENERAL_MANAGER", "PLANNER", "PRODUCTION", "SALES", "SALES_MANAGER", "WAREHOUSE"],
  "system": ["ADMIN"],
  "users": ["ADMIN"],
}

export const WRITE_METHODS: string[] = ["DELETE", "PATCH", "POST", "PUT"]

export const ALL_DOMAINS: string[] = ["admin", "ai", "auth", "dashboard", "eng", "finance", "mm", "planning", "pp", "purchase", "qms", "sd", "system", "traceability", "users"]
