# Alembic 迁移使用说明（N4 基线）

## 现状

- 2026-11-19 起数据库纳入 Alembic 版本管理，基线版本 `a1b2c3d4e5f6`（空迁移 + stamp head）。
- 基线之前的表由 `create_all` + 手写脚本创建，**部分 MVP 手写表存在历史漂移**
  （索引命名、列注释、遗留列如 `lot_cards.mi_content`）。
- 已在 `env.py` 用 `LEGACY_UNMANAGED_TABLES` 划定托管范围：
  `factory_product_mappings`、`lot_card_instructions`、`lot_cards`、`mi_instructions`
  这四张表由手写脚本管理，**不参与 Alembic 比对**。其余表完整比对。
- 因此 `python -m alembic check` 现在 **EXIT=0**，可作为门禁；但它绿的含义是
  「**托管范围内**零漂移」，不等于「全库零漂移」。

## 纪律（重要）

1. `alembic check` / autogenerate 只在托管范围内作答。要改上述四张遗留表的结构，
   先做一次「收养迁移」：用迁移把实库对齐到模型，再从 `LEGACY_UNMANAGED_TABLES`
   中移除该表，之后它才受版本管理。
2. **autogenerate 产物必须人工审查**后再 `upgrade head`。真实踩过的坑：
   自动生成的「对齐迁移」会删除库里已有的表/列注释，并补出可直接失败的唯一约束。
3. `include_object` 的规则：
   - 表：必须在 `Base.metadata` 登记且不在遗留集合；
   - 索引/约束/列：库里存在、元数据中没有（`reflected=True and compare_to is None`）
     一律忽略，避免 `drop_index idx_sales_order_production_version` 这类破坏性脚本。
4. 新增/修改模型字段后：
   ```powershell
   cd backend
   python -m alembic revision --autogenerate -m "描述"
   # 人工检查 versions/ 下生成的脚本，删除误报的 drop 类操作
   python -m alembic upgrade head
   python -m alembic check      # 应输出 No new upgrade operations detected.
   ```
5. 演示库回滚：`reset_demo.py` 只重置数据，不动结构；结构回滚用
   `python -m alembic downgrade -1`（慎用，先确认迁移可逆）。
