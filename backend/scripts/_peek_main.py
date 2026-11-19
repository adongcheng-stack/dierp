"""查看 upgrade_planning.py main() 真实文本（一次性辅助）。"""
import io

s = io.open("backend/upgrade_planning.py", encoding="utf-8").read()
i = s.find("def main(")
print(s[i : i + 1400])
