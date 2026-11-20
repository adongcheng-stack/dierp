import { expect, test, type Page } from '@playwright/test'
import { execSync } from 'node:child_process'

/** 登录：清本地状态 → 滑块验证 → 账号密码 → 进主界面 */
async function login(page: Page) {
  await page.goto('/login')
  await page.evaluate(() => localStorage.clear())
  await page.reload()

  const slider = page.getByRole('slider', { name: '安全验证滑块' })
  const box = await slider.boundingBox()
  expect(box, '滑块应可见').not.toBeNull()
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2)
  await page.mouse.down()
  await page.mouse.move(box!.x + box!.width / 2 + 600, box!.y + box!.height / 2, { steps: 14 })
  await page.mouse.up()
  await expect(page.getByText('验证通过')).toBeVisible()

  await page.locator('#login_username').fill('admin')
  await page.locator('#login_password').fill('admin123')
  await page.getByRole('button', { name: /登.*录/ }).click()
  await expect(page).toHaveURL('http://127.0.0.1:3010/')
  await expect(page.getByText('经营看板', { exact: true }).first()).toBeVisible()
}

/** 侧栏分组默认折叠：先展开分组，再点子菜单 */
async function openMenu(page: Page, group: string, item: string) {
  const nav = page.getByRole('complementary').getByRole('navigation')
  await nav.getByRole('button', { name: group, exact: true }).click()
  await nav.getByRole('button', { name: item, exact: true }).click()
}

test.describe('核心链路 E2E', () => {
  test('1. 登录（滑块 + 账号密码）', async ({ page }) => {
    await login(page)
    await expect(page.getByText('仪表盘', { exact: true }).first()).toBeVisible()
  })

  test('2. 页签右键菜单：关闭其他', async ({ page }) => {
    await login(page)
    // 打开两个页面形成多页签
    await openMenu(page, '财务管理', '会计科目')
    await expect(page).toHaveURL(/\/finance\/accounts/)
    // 等 AppLayout 的路由 effect 把页签写入，再导航下一页（避免两次快速导航被合并）
    await expect(page.locator('[data-tab-key]')).toHaveCount(2)
    await page.getByRole('complementary').getByRole('button', { name: '余额表', exact: true }).click()
    await expect(page).toHaveURL(/\/finance\/trial-balance/)

    const tabs = page.locator('[data-tab-key]')
    await expect(tabs).toHaveCount(3)
    await tabs.nth(1).click({ button: 'right' })
    await expect(page.getByText('关闭其他', { exact: true })).toBeVisible()
    await expect(page.getByText('关闭右侧', { exact: true })).toBeVisible()
    await page.getByText('关闭其他', { exact: true }).click()
    await expect(tabs).toHaveCount(2) // 首页 + 当前页
  })

  test('3. 月结确认弹窗有内边距（文字/按钮不顶边）', async ({ page }) => {
    await login(page)
    await page.goto('/finance/periods')
    await page.locator('main').getByRole('button', { name: /月结$/ }).click()
    const content = page.locator('.ant-modal-confirm .ant-modal-content')
    await expect(content).toBeVisible()
    const padding = await content.evaluate((el) => getComputedStyle(el).paddingLeft)
    expect(parseFloat(padding)).toBeGreaterThanOrEqual(20)
    await page.keyboard.press('Escape')
  })

  test('4. 菜单按业务价值链排序 + 期间月结可达', async ({ page }) => {
    await login(page)
    const labels = await page.locator('nav button').allTextContents()
    const expected = ['仪表盘', '经营看板', '销售管理', '生产计划', '采购管理', '库存管理', '财务管理']
    const positions = expected.map((label) => labels.indexOf(label)).filter((i) => i >= 0)
    expect(positions.length).toBe(expected.length)
    expect(positions).toEqual([...positions].sort((a, b) => a - b))

    await openMenu(page, '财务管理', '期间与月结')
    await expect(page).toHaveURL(/\/finance\/periods/)
    await expect(page.getByText('月结预览')).toBeVisible()
  })

  test('5. PR 行级部分转换界面', async ({ page }) => {
    // 该用例会真实生成采购单，先复位演示库保证种子 PR 可转
    execSync('python ../backend/scripts/reset_demo.py', { stdio: 'ignore' })
    await login(page)
    await openMenu(page, '采购管理', '采购申请')
    await expect(page).toHaveURL(/\/mm\/purchase-requests/)
    const row = page.locator('tbody tr').filter({ hasText: 'PRQ-' }).first()
    await row.getByRole('button', { name: '部分转换' }).click()
    const modal = page.locator('.ant-modal').filter({ hasText: '部分转换' })
    await expect(modal).toBeVisible()
    await modal.getByRole('button', { name: '生成采购单' }).click()
    await expect(page.getByText(/已生成采购单/)).toBeVisible()
  })
})
