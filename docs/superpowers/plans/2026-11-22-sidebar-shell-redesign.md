# DIERP 侧栏与外壳视觉重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将侧栏、顶栏、页签条统一为「轻盈档案」细线语言，保留全部菜单文案、顺序与业务行为。

**Architecture:** 新增只读的分区映射模块，不改动 `menuConfig.tsx` 的菜单数据；Sidebar 按映射渲染三个分区标题，顶栏与页签条只调整 class，不改任何处理函数；全部颜色沿用 `tokens.css`，验证以 build/lint/test 与 Hallmark sweep 为准。

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind + Antd + Vitest + Hallmark sloplint。

**Commit policy:** 本工作区不自动提交；下列任务不含 git commit 步骤，除非用户明确要求提交。

---

### Task 1: 分区映射与契约测试

**Files:**
- Create: `frontend/src/components/layout/navSections.ts`
- Test: `frontend/src/components/layout/navSections.test.ts`

- [ ] **Step 1: 写失败测试**

```ts
import { describe, expect, it } from 'vitest'
import { NAV_ITEMS } from './menuConfig'
import { NAV_SECTIONS } from './navSections'

describe('NAV_SECTIONS', () => {
  it('covers every top-level item exactly once in original order', () => {
    expect(NAV_SECTIONS.flatMap((section) => section.keys)).toEqual(
      NAV_ITEMS.map((item) => item.key)
    )
  })

  it('uses the three approved section titles in order', () => {
    expect(NAV_SECTIONS.map((section) => section.title)).toEqual([
      '工作台',
      '业务域',
      '系统',
    ])
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd d:/project/erp/frontend && npm test -- src/components/layout/navSections.test.ts`
Expected: 失败，提示 `Cannot find module './navSections'`。

- [ ] **Step 3: 实现映射模块**

```ts
import { NAV_ITEMS } from './menuConfig'

export interface NavSection {
  title: string
  keys: string[]
}

export const NAV_SECTIONS: NavSection[] = [
  { title: '工作台', keys: ['/', 'kpi'] },
  {
    title: '业务域',
    keys: ['sd', 'pp', 'purchase', 'inventory', 'finance', 'eng', 'cost', 'qms', 'eam', 'aps'],
  },
  { title: '系统', keys: ['admin'] },
]

const allKeys = NAV_SECTIONS.flatMap((section) => section.keys)

if (allKeys.length !== NAV_ITEMS.length || allKeys.some((key, index) => key !== NAV_ITEMS[index].key)) {
  throw new Error('NAV_SECTIONS must preserve menuConfig order and cover every top-level item')
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd d:/project/erp/frontend && npm test -- src/components/layout/navSections.test.ts`
Expected: 2 个用例全部通过。

---

### Task 2: Sidebar 视觉重构

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx:1-160`

- [ ] **Step 1: 替换导入与基础类**

把文件开头的导入和 `NAV_BASE` 替换为：

```tsx
import { useEffect, useMemo, useState } from 'react'
/* Hallmark · dropped onClick={() => { if (hasChildren) toggleExpand(item.key) else if (item.path) navigate(item.path) }} · mobile drawer also closes after navigation; both effects kept */
import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronRight, Factory } from 'lucide-react'
import { cn } from '../../lib/utils'
import { NAV_ITEMS, type NavItem } from './menuConfig'
import { NAV_SECTIONS } from './navSections'

const SIDEBAR_WIDTH = 240

const NAV_BASE =
  'group flex w-full min-h-11 items-center gap-2.5 border-s-2 border-transparent text-sm transition-colors duration-150'
```

- [ ] **Step 2: 替换激活态 class 分支**

把 `renderItem` 中按钮的 `className={cn(...)}` 整段替换为：

```tsx
          className={cn(
            NAV_BASE,
            level > 0 ? 'ps-9 pe-3' : 'px-3',
            active && !hasChildren
              ? 'border-brand bg-brand-soft font-semibold text-brand-ink'
              : parentActive
                ? 'border-brand bg-brand-soft font-semibold text-brand-ink'
                : level === 0 && hasChildren && expanded
                  ? 'font-medium text-ink hover:bg-surface-hover'
                  : 'text-ink-soft hover:bg-surface-hover hover:text-ink'
          )}
```

- [ ] **Step 3: 给按钮补轨道态可访问名称**

在同一个 `<button>` 上，紧跟 `aria-expanded={...}` 之后插入：

```tsx
          aria-label={item.label}
          title={item.label}
```

不要改动 `onClick` 的表达式，保持 Hallmark 记录中的处理函数逐字保留。

- [ ] **Step 4: 替换品牌块**

把 `{/* Logo 区域 */}` 整段替换为：

```tsx
      {/* Logo 区域 */}
      <div className="flex h-14 shrink-0 items-center border-b border-line px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-line text-brand">
            <Factory className="h-5 w-5" />
          </div>
          <div className="overflow-hidden">
            <h1 className="sidebar-label truncate text-sm font-semibold tracking-tight text-ink">DIERP</h1>
            <p className="sidebar-label truncate text-xs text-ink-soft">ERP 管理系统</p>
          </div>
        </div>
      </div>
```

- [ ] **Step 5: 按分区渲染菜单**

把菜单区域里这一行：

```tsx
          <div className="space-y-0.5">{NAV_ITEMS.map((item) => renderItem(item))}</div>
```

替换为：

```tsx
          <div className="space-y-0.5">
            {NAV_SECTIONS.map((section, sectionIndex) => (
              <div key={section.title}>
                {sectionIndex > 0 && <div className="mx-3 my-2 border-t border-line" />}
                <div className="sidebar-label px-3 pb-1 pt-2 text-xs text-ink-soft">
                  {section.title}
                </div>
                {section.keys.map((key) => {
                  const item = NAV_ITEMS.find((candidate) => candidate.key === key)
                  return item ? <div key={item.key}>{renderItem(item)}</div> : null
                })}
              </div>
            ))}
          </div>
```

- [ ] **Step 6: 运行定向检查**

Run: `cd d:/project/erp/frontend && npm run build && npm run lint`
Expected: 构建成功，lint 无输出。

---

### Task 3: Header 细线化

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx:142-233`

- [ ] **Step 1: 顶栏容器与面包屑字号**

把：

```tsx
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-surface px-4">
      {/* 左侧：折叠 + 刷新 + 面包屑 */}
      <nav className="flex min-w-0 items-center gap-2 text-sm">
```

替换为：

```tsx
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-surface px-4">
      {/* 左侧：折叠 + 刷新 + 面包屑 */}
      <nav className="flex min-w-0 items-center gap-2 text-[13px]">
```

- [ ] **Step 2: 四个工具按钮的圆角与命中区**

把四处 `className="inline-flex h-8 w-8 items-center justify-center rounded-md` 批量替换为 `className="inline-flex h-11 w-11 items-center justify-center rounded-none`，只改 class，不改 `onClick`。四处分别是折叠按钮、刷新按钮、主题按钮、全屏按钮。

- [ ] **Step 3: 用户菜单按钮与头像**

把 Dropdown 内的触发按钮替换为：

```tsx
          <button
            type="button"
            className="flex items-center gap-2 rounded-none px-2 py-1.5 transition-colors hover:bg-surface-hover"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full border border-line bg-surface text-xs font-medium text-brand-ink">
              {(user?.full_name || user?.username || 'U').charAt(0)}
            </div>
            <span className="hidden max-w-[140px] truncate text-[13px] text-ink sm:block">
              {user?.full_name || user?.username || '用户'}
            </span>
            <ChevronDown className="h-4 w-4 text-ink-faint" />
          </button>
```

窄屏同时把用户菜单前的竖线改为 `mx-1 hidden h-5 w-px bg-line sm:block`，避免 375px 下顶栏被裁切；用户名在窄屏隐藏，但完整姓名仍在下拉菜单中可见。

- [ ] **Step 4: 运行定向检查**

Run: `cd d:/project/erp/frontend && npm run build && npm run lint`
Expected: 构建成功，lint 无输出。

---

### Task 4: PageTabs 细线化

**Files:**
- Modify: `frontend/src/components/layout/PageTabs.tsx:120-199`

- [ ] **Step 1: 容器与滚动按钮**

把：

```tsx
    <div className="app-tabstrip relative flex h-9 items-center gap-2 border-b border-line bg-surface px-4">
```

替换为：

```tsx
    <div className="app-tabstrip relative flex h-9 items-center gap-2 border-b border-line bg-surface px-3">
```

两个滚动按钮的 `rounded-none` 保持不变，不改 `onClick`。

- [ ] **Step 2: 标签按钮**

把标签按钮的 `className={cn(...)}` 整段替换为：

```tsx
            className={cn(
              'flex min-h-8 shrink-0 items-center border-b-2 px-3 py-1.5 text-[13px] leading-none transition-colors',
              activeKey === tab.key
                ? 'border-brand font-medium text-brand-ink'
                : 'border-transparent text-ink-soft hover:text-ink'
            )}
```

把标签文本的类改为：

```tsx
            <span className="max-w-[160px] truncate text-[13px]">{tab.label}</span>
```

- [ ] **Step 3: 关闭图标**

把关闭 span 的 className 改为：

```tsx
                className="relative rounded-none p-1 text-ink-faint hover:bg-surface-hover hover:text-ink after:absolute after:-inset-1 after:content-['']"
```

不要改动 `onClick` / `onKeyDown`。

- [ ] **Step 4: 运行定向检查**

Run: `cd d:/project/erp/frontend && npm run build && npm run lint`
Expected: 构建成功，lint 无输出。

---

### Task 5: 设计规则同步

**Files:**
- Modify: `frontend/design.md:12`

- [ ] **Step 1: 更新动效规则**

把：

```md
-motion: 只动 transform/opacity；无宽度/高度动画，无 `transition-all`；尊重 reduced-motion
```

替换为：

```md
-motion: 过渡只改 color / background-color / opacity；仅抽屉位移可用 transform；无宽度/高度动画，无 `transition-all`；尊重 reduced-motion
```

- [ ] **Step 2: 增加外壳分区规则**

在 `-structure:` 行之后插入：

```md
-shell: 侧栏分「工作台 / 业务域 / 系统」三段，hairline 分隔；顶栏与页签条沿用同一套 hairline 与 13px 文字
```

- [ ] **Step 3: 确认文档无冲突**

Run: `cd d:/project/erp && git --no-pager diff -- frontend/design.md`
Expected: 只出现上述两处变化。

---

### Task 6: 全量验证

**Files:** 无新增，验证上述所有改动。

- [ ] **Step 1: 单元测试、构建与 lint**

Run: `cd d:/project/erp/frontend && npm test && npm run build && npm run lint`
Expected: 测试文件数与用例数不低于当前基线（4 files / 19 tests，加上新增 2 个用例后为 21），build 成功，lint 无输出。

- [ ] **Step 2: Hallmark sweep**

Run:

```
cd d:/project/erp
$env:HALLMARK_PUPPETEER='d:/project/erp/.hallmark/tools'
node 'C:/Users/che99/.codebuddy/skills/hallmark/scripts/sloplint.mjs' 'd:/project/erp/frontend/src' --genre modern-minimal --scope app --render --kept --url 'http://localhost:3101/#/login' --url 'http://localhost:3101/#/' --url 'http://localhost:3101/#/sd/customers' --url 'http://localhost:3101/#/eng/boms' --url 'http://localhost:3101/#/sd/quotations/new' --url 'http://localhost:3101/#/aps/workbench' --url 'http://localhost:3101/#/dashboard/management'
```

Expected: kept 保持 links 2/2、fields 349/349、handlers 378/381（3 dropped on record，上一轮重构已登记）、headings 8/8；Floor FAIL 不高于 1；Reflex 不高于 3。

- [ ] **Step 3: 截图复核**

查看 `.hallmark/shots/` 中 `1440x900`、`1280x800`、`375` 三档：侧栏三段标题可见，轨道态图标不溢出，移动抽屉不遮挡内容，顶栏与页签条无横向滚动。

- [ ] **Step 4: 预览确认**

打开 `http://localhost:3101/#/`，人工确认侧栏、顶栏、页签条的细线语言一致，点击菜单、折叠、页签关闭均正常。
