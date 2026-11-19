# Alembic 迁移使用说明（N4 基线）

## 现状

- 2026-11-19 起数据库纳入 Alembic 版本管理，基线版本 `a1b2c3d4e5f6`（空迁移 + stamp head）。
- 基线之前的表由 `create_all` + 手写脚本创建，**部分 MVP 手写表存在历史漂移**
  （索引命名、列注释、遗留列如 `lot_cards.mi_content`）。`alembic check` 会报告这些差异，属已知问题。

## 纪律（重要）

1. **autogenerate 产物必须人工审查**后再 `upgrade head`——历史漂移会让脚本带上
   「删除索引 / 删除遗留列」等操作，盲目执行会破坏既有数据。
2. 新增/修改模型字段后：
   ```powershell
   cd backend
   python -m alembic revision --autogenerate -m "描述"
   # 人工检查 versions/ 下生成的脚本，删除误报的 drop 类操作
   python -m alembic upgrade head
   ```
3. `env.py` 的 `include_object` 白名单只管理 `Base.metadata` 登记的表；
   历史遗留表（workflows 等）永远不会被 autogenerate 误删。
4. 演示库回滚：`reset_demo.py` 只重置数据，不动结构；结构回滚用
   `python -m alembic downgrade -1`（慎用，先确认迁移可逆）。
