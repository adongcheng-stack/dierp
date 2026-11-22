# DIERP 侧栏与外壳视觉重构设计说明

日期：2026-11-22
状态：设计已确认，待实施

## 目标

把左侧菜单、顶栏与页签条统一为「轻盈档案」视觉语言：白底、hairline 分隔、小号分区标题、克制的品牌蓝激活态。提升导航的扫读效率与专业感，不改变任何现有业务行为。

## 非目标

- 不重排 13 个顶层菜单的顺序，不改任何现有菜单名称。
- 不引入新色板、渐变、发光、emoji 图标或圆角磁贴。
- 不改变路由、鉴权、mock 数据、URL 状态与表格行为。
- 不新增依赖。

## 已确认决策

1. 视觉方向：B · 轻盈档案（用户从 A/B/C 视觉方案中点选）。
2. 文案边界：允许新增少量分区标题，具体为「工作台」「业务域」「系统」三个；现有菜单文案与顺序逐字保留。
3. 改动范围：整个外壳（侧栏 + 顶栏 + 页签条）统一为同一套细线语言。

## 视觉语言

- 全部颜色取自 `frontend/src/tokens.css`。侧栏表面用现有 surface/card 色，边线用 `--line`，弱化文字用 `--ink-soft`，激活文字用 `--brand-ink`，激活底色用 `--brand-soft`，激活左线用 `--brand`。
- 侧栏宽 240px，收起轨道 60px；顶栏 56px，页签条 36px，沿用现有尺寸 token，不改布局尺寸。
- 分区标题：12px（与 `frontend/design.md` 的最小字号一致）、不加字距、弱化色但满足 4.5:1；分组之间用 1px hairline 分隔，分区标题上下留白按现有 spacing token 的 8px/16px 刻度。
- 激活项：左侧 2px 品牌蓝线 + `--brand-soft` 底色 + `--brand-ink` 字重 600；不使用圆角胶囊或投影。
- 悬停：仅改背景与文字颜色，150–200ms 过渡；不使用 transform、scale 或 lift。
- 焦点环：保持现有 2px token 化焦点环；品牌蓝实心按钮用纸色内描边。
- 顶栏：面包屑与工具按钮统一 13px，按钮 hover 用 `--surface-hover`；头像保留圆形细线框。
- 页签条：文字 13px，激活项 2px 品牌蓝下划线，关闭图标用弱化色；不用圆角 chip。

## 结构与文案

- 侧栏顶部品牌块：`DIERP` + `ERP 管理系统` 逐字保留；图标沿用现有 Lucide `Factory`；细线方框，不做实心卡片。
- 分区归类：
  - 工作台：首页、经营看板。
  - 业务域：销售管理、生产计划、采购管理、库存管理、财务管理、工程管理、成本管理、质量管理、设备管理、高级排程。
  - 系统：系统管理。
- 13 个顶层项与 75 个子项的名称、顺序、路径全部保留；`menuConfig.tsx` 的导出接口与 `PATH_LABEL_MAP` 生成逻辑不变。
- 新增的三个分区标题只允许出现在侧栏渲染层，不写入 `NAV_ITEMS`，避免影响面包屑与页面标签解析。

## 状态与交互

- 桌面：`AppLayout` 按 `sidebarCollapsed` 切换 240px / 60px 两列；轨道态隐藏 `.sidebar-label`，图标保持 44px 命中区，悬停用 Tooltip 显示原文案。
- 移动（≤60rem）：侧栏仍为覆盖式抽屉、有遮罩；分区标题在抽屉里保留；点击导航后关闭抽屉的行为不变。
- 分组展开/收起：`toggleExpand` 逻辑与 `expandedKeys` 初始化逻辑不变；分区标题只做静态分组，不新增可点击行为。
- 键盘：现有 Enter 激活、aria-current、aria-expanded 保持；轨道态图标按钮补 `aria-label`，文案取对应菜单名称。
- 动效只改 color / background-color / opacity，尊重 `prefers-reduced-motion`。

## 实施边界

涉及文件预计为：

- `frontend/src/components/layout/Sidebar.tsx`：分区标题渲染、品牌块与激活态样式。
- `frontend/src/components/layout/Header.tsx`：顶栏工具区与面包屑的细线化。
- `frontend/src/components/layout/PageTabs.tsx`：页签下划线与关闭图标。
- `frontend/src/base.css`、`frontend/src/tokens.css`：分区标题、细线、轨道态与移动抽屉的样式支撑。
- `frontend/design.md`：补记分区标题与外壳视觉规则。
- 不改动 `menuConfig.tsx` 的菜单数据本体，除非仅为分区渲染新增只读映射。

## 验收标准

1. `npm run build`、`npm run lint`、`npm test` 全部通过。
2. Hallmark app 范围 sweep 对比 7 条代表性路由：`#/login`、`#/`、`#/sd/customers`、`#/eng/boms`、`#/sd/quotations/new`、`#/aps/workbench`、`#/dashboard/management`。
3. kept 检查保持 links 2/2、fields 349/349、handlers 378/381（3 dropped on record，均为上一轮重构已登记的包装改动）、headings 8/8；本次改动不得新增丢失的链接、字段、处理函数、标题或数值。
4. Floor 数量不得从当前 1 FAIL 回升；Reflex 不得从当前 3 增加。
5. 1440、1280、375 三档截图下：侧栏分区可读，轨道态图标不溢出，移动抽屉不遮挡内容，顶栏与页签条不产生横向滚动。
6. 焦点环对比不低于 3:1；正文与分区标题对比不低于 4.5:1；键盘可达且顺序与视觉一致。

## 风险与取舍

- 12 个业务域仍在同一滚动列表内，分区标题提升扫读但不缩短列表长度；这是接受的成本。
- 收起轨道牺牲文字标签换取内容空间，依赖 Tooltip 和 `aria-label` 补偿可理解性。
- 顶栏与页签条改为细线后，与未改动的页面内组件可能存在视觉重量差异；验收时以截图确认不出现明显割裂。
