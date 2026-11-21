"""Generate the security policy layer from the security ontology.

Single source of truth: ontology/src/security.ttl (id: dierp-security v1).

Generated (DO NOT EDIT BY HAND):
  backend/common/utils/security_policy.py         -- policy data consumed by FastAPI
  frontend/src/types/authorization.generated.ts   -- mirrored policy consumed by the demo mock

Usage (from repository root):
  python backend/ontology/generate_security.py           # write generated files
  python backend/ontology/generate_security.py --check   # fail on drift (CI gate)

The generator is deliberately data-only: authentication logic stays in
backend/api/routers/auth.py and the mock gate stays in frontend/src/mock/handlers.ts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY = ROOT / "ontology" / "src" / "security.ttl"
MAPPINGS = ROOT / "ontology" / "src" / "mappings.json"
BACKEND_OUT = ROOT / "backend" / "common" / "utils" / "security_policy.py"
FRONTEND_OUT = ROOT / "frontend" / "src" / "types" / "authorization.generated.ts"

NS = Namespace("https://dierp.local/ontology/erp/v1#")


def load_ontology() -> dict:
    graph = Graph()
    graph.parse(ONTOLOGY, format="turtle")

    def code(subject, predicate):
        value = graph.value(subject, NS[predicate])
        return str(value) if value is not None else None

    # 角色个体 -> roleCode
    roles = sorted(
        code(subject, "roleCode")
        for subject in graph.subjects(NS["roleCode"], None)
    )

    # 访问域个体
    domains: dict[str, dict] = {}
    for subject in graph.subjects(NS["domainCode"], None):
        domain_code = code(subject, "domainCode")
        allows = sorted(
            code(obj, "roleCode") for obj in graph.objects(subject, NS["allowsRole"])
        )
        read_roles = sorted(
            code(obj, "roleCode") for obj in graph.objects(subject, NS["readRole"])
        )
        anonymous = graph.value(subject, NS["anonymousRead"])
        domains[domain_code] = {
            "allows": allows,
            "anonymous_read": str(anonymous).lower() == "true" if anonymous is not None else True,
            "read_roles": read_roles,
            "top_category": code(subject, "topCategory") or "",
        }

    jwt = graph.value(None, NS["secretKeyEnv"], None)
    jwt_subject = next(graph.subjects(NS["secretKeyEnv"], None), None)
    jwt_config = {
        "secret_key_env": code(jwt_subject, "secretKeyEnv"),
        "algorithm": code(jwt_subject, "algorithm"),
        "token_expire_minutes": int(code(jwt_subject, "tokenExpireMinutes")),
        "refresh_threshold_minutes": int(code(jwt_subject, "refreshThresholdMinutes")),
        "insecure_placeholder": code(jwt_subject, "insecurePlaceholder"),
    }

    methods_subject = next(graph.subjects(NS["method"], None), None)
    write_methods = sorted(str(m) for m in graph.objects(methods_subject, NS["method"]))

    return {
        "roles": roles,
        "domains": dict(sorted(domains.items())),
        "jwt": jwt_config,
        "write_methods": write_methods,
    }


def _py_set(values) -> str:
    if not values:
        return "frozenset()"
    return "frozenset({" + ", ".join(json.dumps(value) for value in values) + "})"


def render_backend(data: dict) -> str:
    lines = [
        '"""',
        "GENERATED FILE - DO NOT EDIT BY HAND.",
        "Source: ontology/src/security.ttl (security overlay)",
        "Regenerate: python backend/ontology/generate_security.py",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# 角色全集（须与 mappings.json 的 UserRole 一致，由本体门禁校验）",
        f"ROLES = {_py_set(data['roles'])}",
        "",
        "# 写权限：域 -> 允许写操作的角色集合；未列出的域一律拒绝（fail-closed）",
        "WRITE_ROLE_POLICY: dict[str, frozenset[str]] = {",
    ]
    for domain, spec in data["domains"].items():
        lines.append(f"    {json.dumps(domain)}: {_py_set(spec['allows'])},")
    lines += [
        "}",
        "",
        "# 只读策略：允许匿名 GET 的域",
        f"READ_OPEN_DOMAINS = {_py_set(d for d, s in data['domains'].items() if s['anonymous_read'])}",
        "",
        "# 只读策略：必须登录且限定角色的域（如 users）",
        "READ_ROLE_POLICY: dict[str, frozenset[str]] = {",
    ]
    for domain, spec in data["domains"].items():
        if not spec["anonymous_read"]:
            lines.append(f"    {json.dumps(domain)}: {_py_set(spec['read_roles'])},")
    lines += [
        "}",
        "",
        "# 域元信息（用于报错文案）",
        "DOMAIN_META: dict[str, str] = {",
    ]
    for domain, spec in data["domains"].items():
        lines.append(f"    {json.dumps(domain)}: {json.dumps(spec['top_category'])},")
    lines += [
        "}",
        "",
        f"WRITE_METHODS = {_py_set(data['write_methods'])}",
        "",
    ]
    jwt = data["jwt"]
    lines += [
        f"JWT_SECRET_KEY_ENV = {json.dumps(jwt['secret_key_env'])}",
        f"JWT_ALGORITHM = {json.dumps(jwt['algorithm'])}",
        f"JWT_TOKEN_EXPIRE_MINUTES = {jwt['token_expire_minutes']}",
        f"JWT_REFRESH_THRESHOLD_MINUTES = {jwt['refresh_threshold_minutes']}",
        f"JWT_INSECURE_PLACEHOLDER = {json.dumps(jwt['insecure_placeholder'])}",
        "",
    ]
    return "\n".join(lines)


def render_frontend(data: dict, mappings: dict) -> str:
    role_values = mappings["enumerations"]["UserRole"]
    lines = [
        "/**",
        " * GENERATED FILE - DO NOT EDIT BY HAND.",
        " * Source: ontology/src/security.ttl (security overlay)",
        " * Regenerate: python backend/ontology/generate_security.py",
        " */",
        "",
        "/* eslint-disable */",
        "",
        "export type UserRole = " + " | ".join(f"'{value}'" for value in role_values),
        "",
        "export const WRITE_ROLE_POLICY: Record<string, string[]> = {",
    ]
    for domain, spec in data["domains"].items():
        lines.append(f"  {json.dumps(domain)}: {json.dumps(spec['allows'])},")
    lines += [
        "}",
        "",
        "export const READ_OPEN_DOMAINS: string[] = "
        + json.dumps([d for d, s in data["domains"].items() if s["anonymous_read"]]),
        "",
        "export const READ_ROLE_POLICY: Record<string, string[]> = {",
    ]
    for domain, spec in data["domains"].items():
        if not spec["anonymous_read"]:
            lines.append(f"  {json.dumps(domain)}: {json.dumps(spec['read_roles'])},")
    lines += [
        "}",
        "",
        "export const WRITE_METHODS: string[] = " + json.dumps(data["write_methods"]),
        "",
        "export const ALL_DOMAINS: string[] = " + json.dumps(list(data["domains"])),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    check_only = "--check" in sys.argv
    data = load_ontology()
    mappings = json.loads(MAPPINGS.read_text(encoding="utf-8"))
    ontology_roles = set(data["roles"])
    mapping_roles = set(mappings["enumerations"]["UserRole"])
    if ontology_roles != mapping_roles:
        print(
            "[FAIL] security.ttl roles differ from mappings.json UserRole: "
            f"only-ttl={sorted(ontology_roles - mapping_roles)}, "
            f"only-json={sorted(mapping_roles - ontology_roles)}",
            file=sys.stderr,
        )
        return 1

    outputs = {
        BACKEND_OUT: render_backend(data),
        FRONTEND_OUT: render_frontend(data, mappings),
    }
    if check_only:
        failed = False
        for path, content in outputs.items():
            actual = path.read_text(encoding="utf-8") if path.exists() else ""
            if actual != content:
                print(f"[FAIL] {path.relative_to(ROOT)} is stale; regenerate.", file=sys.stderr)
                failed = True
        if failed:
            return 1
        print("[OK] security policy generated files are in sync with security.ttl")
        return 0

    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
