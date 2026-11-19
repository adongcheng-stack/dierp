"""门禁：mock 与真实后端的写权限矩阵必须逐域一致。

背景：前端 mock（`frontend/src/mock/handlers.ts`）为演示模式提供同构行为，
    其中写权限表是 Python 侧的副本。两份策略一旦漂移，演示与真机的
    「谁能写」就会分叉，且不会触发任何类型错误。

用法：python backend/scripts/check_rbac_parity.py
"""
from __future__ import annotations

import ast
import io
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BACKEND_AUTH = PROJECT_ROOT / "backend" / "api" / "routers" / "auth.py"
MOCK_HANDLERS = PROJECT_ROOT / "frontend" / "src" / "mock" / "handlers.ts"


def _extract_block(text: str, marker: str) -> str:
    """从 marker 后第一个 '{' 起，按大括号配对截出对象字面量（含外层括号）。"""
    start = text.index(marker)
    start = text.index("{", start)
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError(f"未找到配对的右括号: {marker}")


def load_backend_policy() -> tuple[dict[str, set[str]], set[str]]:
    text = io.open(BACKEND_AUTH, encoding="utf-8").read()
    policy_block = _extract_block(text, "WRITE_ROLE_POLICY: dict[str, set[str]] =")
    policy = ast.literal_eval(policy_block)
    methods_block = _extract_block(text, "WRITE_METHODS =")
    methods = set(ast.literal_eval(methods_block))
    return policy, methods


def load_mock_policy() -> tuple[dict[str, set[str]], set[str]]:
    text = io.open(MOCK_HANDLERS, encoding="utf-8").read()
    policy_block = _extract_block(
        text, "const WRITE_ROLE_POLICY: Record<string, string[]> ="
    )
    policy: dict[str, set[str]] = {}
    for match in re.finditer(r"(\w+)\s*:\s*\[([^\]]*)\]", policy_block):
        domain = match.group(1)
        roles = {item.strip().strip("'\"") for item in match.group(2).split(",") if item.strip()}
        policy[domain] = roles
    methods_match = re.search(r"new Set\(\[([^\]]*)\]\)", text)
    if not methods_match:
        raise ValueError("mock 中未找到 WRITE_METHODS 定义")
    methods = {
        item.strip().strip("'\"")
        for item in methods_match.group(1).split(",")
        if item.strip()
    }
    return policy, methods


def main() -> int:
    backend_policy, backend_methods = load_backend_policy()
    mock_policy, mock_methods = load_mock_policy()

    problems: list[str] = []

    if backend_methods != mock_methods:
        problems.append(
            f"写方法集合不一致: backend={sorted(backend_methods)} mock={sorted(mock_methods)}"
        )

    for domain in sorted(set(backend_policy) | set(mock_policy)):
        backend_roles = backend_policy.get(domain)
        mock_roles = mock_policy.get(domain)
        if backend_roles is None:
            problems.append(f"域 '{domain}' 只存在于 mock（后端无此策略）")
        elif mock_roles is None:
            problems.append(f"域 '{domain}' 只存在于后端（mock 缺策略）")
        elif backend_roles != mock_roles:
            problems.append(
                f"域 '{domain}' 角色不一致: backend 多 {sorted(backend_roles - mock_roles)}"
                f" / mock 多 {sorted(mock_roles - backend_roles)}"
            )

    print(f"后端策略: {len(backend_policy)} 域 / mock 策略: {len(mock_policy)} 域")
    for domain in sorted(backend_policy):
        print(f"  {domain:<10} {'/'.join(sorted(backend_policy[domain]))}")

    if problems:
        print("\n写权限矩阵不一致：")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\n写权限矩阵双栈一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
