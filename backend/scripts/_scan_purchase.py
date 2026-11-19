"""定位采购转单端点上下文（一次性辅助脚本）。"""
import io
import re

s = io.open("backend/api/routers/planning.py", encoding="utf-8").read()
lines = s.splitlines()

# L746 所属路由装饰器
for i in range(745, 600, -1):
    if lines[i].strip().startswith("@router."):
        print("路由装饰器:", lines[i].strip())
        print("函数签名:", lines[i + 1].strip()[:100])
        break

# 全部 GET 端点路径（planned/purchase 相关）
for m in re.finditer(r'@router\.(get|post|put|delete)\("([^"]+)"\)', s):
    path = m.group(2)
    if "purchase" in path or "planned" in path:
        print(m.group(1).upper(), path)
