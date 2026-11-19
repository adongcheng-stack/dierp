"""查看 planned-orders 列表端点签名（一次性辅助）。"""
import io

s = io.open("backend/api/routers/planning.py", encoding="utf-8").read()
i = s.find('@router.get("/planned-orders")')
print(s[i : i + 900])
