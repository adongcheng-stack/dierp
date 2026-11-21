import { defineConfig } from '@playwright/test'

/**
 * 前端 E2E。
 * 默认复用本机 Chrome 与 3010 端口的 dev 服务；CI 上通过环境变量覆盖：
 *   E2E_BASE_URL —— dev 服务地址
 *   CHROME_PATH  —— 浏览器可执行文件（留空则用 Playwright 自带 Chromium）
 */
const chromePath = process.env.CHROME_PATH || undefined

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 8_000 },
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:3010',
    headless: true,
    ...(chromePath ? { launchOptions: { executablePath: chromePath } } : {}),
    trace: 'retain-on-failure',
  },
})
