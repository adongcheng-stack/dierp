"""Aggregated quality gate for DIERP.

Runs every deterministic gate in dependency order and prints a compact report.
Database-mutating smoke scripts and browser E2E are opt-in (see flags), because
they require a live PostgreSQL / dev server.

Usage (from repository root):
  python backend/scripts/gate.py                 # default: hermetic gates only
  python backend/scripts/gate.py --with-db       # + smoke/probe scripts (needs DB)
  python backend/scripts/gate.py --with-e2e      # + Playwright (needs dev server)
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
ONTOLOGY = ROOT / "ontology"

HERMETIC: list[tuple[str, list[str], Path]] = [
    ("本体/类型同步", [sys.executable, "scripts/validate-type-sync.js"], ONTOLOGY),
    ("本体/一致性", [sys.executable, "scripts/validate-consistency.py"], ONTOLOGY),
    ("本体/安全策略漂移", [sys.executable, "backend/ontology/generate_security.py", "--check"], ROOT),
    ("后端/pytest", [sys.executable, "-m", "pytest", "-q"], BACKEND),
    ("后端/alembic check", [sys.executable, "-m", "alembic", "check"], BACKEND),
    ("后端/demo parity", [sys.executable, "scripts/check_demo_parity.py"], BACKEND),
    ("后端/RBAC parity", [sys.executable, "scripts/check_rbac_parity.py"], BACKEND),
    ("前端/tsc", ["npx", "tsc", "--noEmit"], FRONTEND),
    ("前端/eslint", ["npx", "eslint", ".", "--ext", "ts,tsx", "--max-warnings", "0"], FRONTEND),
    ("前端/vitest", ["npx", "vitest", "run"], FRONTEND),
    ("前端/mock RBAC", ["node", "scripts/check-mock-rbac.mjs"], FRONTEND),
    ("前端/mock handlers", ["npx", "tsx", "mock-tests/handlers.spec.ts"], FRONTEND),
    # 构建产物放系统临时目录，避免触发 dev 服务热重载
    ("前端/build", ["npx", "vite", "build", "--outDir", str(Path(tempfile.gettempdir()) / "dierp-gate-build"), "--emptyOutDir"], FRONTEND),
]

DB_SCRIPTS = sorted(
    p.name for p in (BACKEND / "scripts").glob("smoke_*.py")
) + sorted(p.name for p in (BACKEND / "scripts").glob("probe_*.py"))


def run(name: str, command: list[str], cwd: Path) -> bool:
    started = time.time()
    print(f"\n=== {name} ===")
    # node 脚本用 node 运行，validate-type-sync.js 需要 node
    if command[1].endswith(".js") and command[0] == sys.executable:
        command = ["node", *command[1:]]
    import subprocess

    # Windows 上 npx 是 .cmd 脚本，CreateProcess 无法直接解析，需要 shell=True
    result = subprocess.run(command, cwd=str(cwd), text=True, shell=(sys.platform == "win32"))
    elapsed = time.time() - started
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"--- {name}: {status} ({elapsed:.1f}s) ---")
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="DIERP 聚合门禁")
    parser.add_argument("--with-db", action="store_true", help="追加数据库冒烟/探针（需要 PostgreSQL）")
    parser.add_argument("--with-e2e", action="store_true", help="追加 Playwright E2E（需要 dev server）")
    args = parser.parse_args()

    gates = list(HERMETIC)
    if args.with_db:
        gates += [
            (f"后端/{name}", [sys.executable, f"scripts/{name}"], BACKEND)
            for name in DB_SCRIPTS
        ]
    if args.with_e2e:
        gates += [
            ("前端/E2E", ["npx", "playwright", "test"], FRONTEND),
        ]

    results = [(name, run(name, command, cwd)) for name, command, cwd in gates]
    failed = [name for name, ok in results if not ok]
    print("\n" + "=" * 60)
    print(f"门禁总计 {len(results)} 项，失败 {len(failed)} 项")
    for name in failed:
        print(f"  FAIL {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
