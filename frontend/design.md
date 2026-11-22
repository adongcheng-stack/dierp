# DIERP 设计系统（Hallmark v2.0.0 · app screen）

-theme/lineage: Grid（deal 1/3），品牌锁定 DIERP 工业蓝与冷中性；Radio Canada 与瑞士红不放行
-copy/voice: 逐字保留现有中文文案；点号只拆成列线与 hairline，不增删词
-structure: 外壳为「左侧轨道 / 顶栏 / 页签条 / 内容画布」四区；60rem 以下侧栏变抽屉
-shell: 侧栏分「工作台 / 业务域 / 系统」三段，hairline 分隔；顶栏与页签条沿用同一套 hairline 与 13px 文字
-signature: 首页第一对象是「待我审批的报价单」；KPI 是列线账本，不是磁贴墙
-layout primitives: hairline (`--rule-hair`), column rule, ledger row, no card-in-card
-color: `tokens.css` 是唯一色源；UI 色一律 `hsl(var(--token))` 或 `var(--color-*)`，状态色只标真实状态
-type: `--font-body` 系统无衬线；字阶 12/13/14/16/18/21.6/25.9px；正文 14px，最小 12px
-space: 2/4/8/12/16/24/40/64/96/144px；半径 2px；阴影只用于浮层，不叠加 hairline
-controls: 32–40px 控件高度，主操作 36px；外壳轨道按钮与顶栏工具按钮取 44px 命中区；焦点环 `var(--color-focus)` 2px 不透明，字段内嵌
-motion: 过渡只改 color / background-color / opacity；仅抽屉位移可用 transform；无宽度/高度动画，无 `transition-all`；尊重 reduced-motion
-data: 表格优先；第一列与操作列窄屏固定；骨架 / 空 / 错 / 满四态齐全；筛选与分页写入 URL
-waive 63: 个别业务文本中的短横仅作空值占位，不改
-never: 紫蓝渐变、发光、emoji 当图标、彩色边条磁贴、悬停抬升、成功提示覆盖可见结果
