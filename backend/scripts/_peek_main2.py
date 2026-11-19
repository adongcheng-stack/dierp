"""检查 upgrade_planning.py 头部导入。"""
import io

s = io.open("backend/upgrade_planning.py", encoding="utf-8").read()
print(s[:1400])
