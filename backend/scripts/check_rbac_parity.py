"""门禁：本体安全策略 → 后端 / 前端 mock 双栈一致。

策略唯一事实源：ontology/src/security.ttl
生成物：
  backend/common/utils/security_policy.py
  frontend/src/types/authorization.generated.ts

本门禁验证：
  1. 生成物与本体同步（调用 generate_security.py --check）
  2. 后端策略与前端 mock 策略逐域一致（写 + 读）
  3. 本体中所有域都在两侧出现（fail-closed 域也必须显式声明）

用法：python backend/scripts/check_rbac_parity.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

GENERATOR = PROJECT_ROOT / "backend" / "ontology" / "generate_security.py"
BACKEND_POLICY = PROJECT_ROOT / "backend" / "common" / "utils" / "security_policy.py"
FRONTEND_POLICY = PROJECT_ROOT / "frontend" / "src" / "types" / "authorization.generated.ts"


def _ts_array(text: str, marker: str) -> dict[str, set[str]]:
    start = text.index(marker)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                block = text[brace : index + 1]
                break
    else:
        raise ValueError(f"未找到配对的右括号: {marker}")
    result: dict[str, set[str]] = {}
    for match in re.finditer(r'"([^"]+)"\s*:\s*\[([^\]]*)\]', block):
        values = {
            item.strip().strip("'\"")
            for item in match.group(2).split(",")
            if item.strip()
        }
        result[match.group(1)] = values
    return result


def _ts_string_array(text: str, marker: str) -> set[str]:
    match = re.search(marker + r"[^=]*=\s*\[([^\]]*)\]", text)
    if not match:
        raise ValueError(f"未找到数组定义: {marker}")
    return {
        item.strip().strip("'\"")
        for item in match.group(1).split(",")
        if item.strip()
    }


def main() -> int:
    # 1. 本体生成物同步门禁
    check = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        print(check.stdout.strip())
        print(check.stderr.strip(), file=sys.stderr)
        print("\n本体策略生成物已漂移，请先运行 python backend/ontology/generate_security.py", file=sys.stderr)
        return 1

    # 2. 读取两侧策略
    from backend.common.utils import security_policy as backend

    frontend_text = FRONTEND_POLICY.read_text(encoding="utf-8")
    frontend_write = _ts_array(frontend_text, "export const WRITE_ROLE_POLICY")
    frontend_read = _ts_array(frontend_text, "export const READ_ROLE_POLICY")
    frontend_open = _ts_string_array(frontend_text, "export const READ_OPEN_DOMAINS")
    frontend_methods = _ts_string_array(frontend_text, "export const WRITE_METHODS")

    backend_write = {domain: set(roles) for domain, roles in backend.WRITE_ROLE_POLICY.items()}
    backend_read = {domain: set(roles) for domain, roles in backend.READ_ROLE_POLICY.items()}
    backend_open = set(backend.READ_OPEN_DOMAINS)
    backend_methods = set(backend.WRITE_METHODS)

    problems: list[str] = []
    if backend_methods != frontend_methods:
        problems.append(
            f"写方法集合不一致: backend={sorted(backend_methods)} mock={sorted(frontend_methods)}"
        )
    if backend_open != frontend_open:
        problems.append(
            f"匿名读域不一致: backend={sorted(backend_open)} mock={sorted(frontend_open)}"
        )

    for domain in sorted(set(backend_write) | set(frontend_write)):
        left, right = backend_write.get(domain), frontend_write.get(domain)
        if left is None or right is None:
            problems.append(f"写策略域 '{domain}' 仅存在一侧")
        elif left != right:
            problems.append(
                f"写策略域 '{domain}' 角色不一致: backend 多 {sorted(left - right)}"
                f" / mock 多 {sorted(right - left)}"
            )

    for domain in sorted(set(backend_read) | set(frontend_read)):
        left, right = backend_read.get(domain), frontend_read.get(domain)
        if left is None or right is None:
            problems.append(f"读策略域 '{domain}' 仅存在一侧")
        elif left != right:
            problems.append(f"读策略域 '{domain}' 角色不一致")

    print(f"本体策略: {len(backend_write)} 域 / 后端: {len(backend_write)} 域 / mock: {len(frontend_write)} 域")
    for domain in sorted(backend_write):
        roles = "/".join(sorted(backend_write[domain])) or "(fail-closed)"
        read = "匿名" if domain in backend_open else "受限"
        print(f"  {domain:<12} 写[{roles}] 读[{read}]")

    if problems:
        print("\n本体/后端/mock 三方策略不一致：")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\n本体 → 后端 → mock 策略三方一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
