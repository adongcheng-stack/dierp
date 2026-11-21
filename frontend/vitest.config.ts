import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

/** 前端组件/工具单元测试（jsdom 环境），与 E2E（Playwright）互补。 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
    clearMocks: true,
  },
})
