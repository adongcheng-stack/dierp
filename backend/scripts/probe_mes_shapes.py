"""真实 MES 形状抽样校验（只读，凭据只来自环境变量）。

对 MES 库全部工单执行最小只读链路，并用本体形状校验结果行：
- 退出 0：真实数据全部通过形状；
- 退出 1：打印违规工单、row_key、形状路径与原因（不迁就形状）；
- MES 未启用时打印 SKIP 并退出 0（可在无 MES 环境重复执行）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.ai.config import get_settings  # noqa: E402
from backend.services.ai.mes_client import (  # noqa: E402
    _connect,
    _fetch_all,
    fetch_work_order_progress,
)
from backend.services.ai.mes_shapes import validate_mes_result  # noqa: E402


def main() -> int:
    settings = get_settings()
    if not settings.mes_ready:
        print("SKIP MES 未启用或未配置（MES_QUERY_ENABLED / MES_DB_*）")
        return 0

    connection = _connect(settings)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("START TRANSACTION READ ONLY")
            orders = _fetch_all(
                cursor,
                "SELECT work_order_no FROM prd_work_order ORDER BY work_order_no",
                (),
            )
    finally:
        connection.close()

    violations: list[dict[str, str]] = []
    checked_orders = 0
    checked_rows = 0
    empty_orders = 0
    for item in orders:
        order_no = str(item["work_order_no"])
        result = fetch_work_order_progress(order_no, limit=settings.mes_query_max_rows)
        checked_orders += 1
        checked_rows += len(result.rows)
        if not result.rows:
            empty_orders += 1
        for violation in validate_mes_result(result.rows):
            violation["work_order_no"] = order_no
            violations.append(violation)

    print(
        f"检查工单 {checked_orders} 张、结果行 {checked_rows} 行"
        f"（空结果 {empty_orders} 张）；违规 {len(violations)} 条"
    )
    if violations:
        for violation in violations[:100]:
            print(
                "VIOLATION "
                f"work_order_no={violation['work_order_no']} "
                f"row_key={violation['row_key']} "
                f"focus={violation['focus']} "
                f"path={violation['path']} "
                f"component={violation['component']} "
                f"message={violation['message']}"
            )
        return 1
    print("MES 真实数据形状校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
