import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * 将 node_modules 按依赖层次拆成稳定的 vendor chunk，避免单文件接近 2MB。
 *
 * 分层原则（只允许上层依赖下层，避免 chunk 循环初始化）：
 *   react-vendor  ← 无第三方依赖
 *   vendor        ← 其余叶子库（clsx / tailwind-merge / @babel/runtime …）
 *   rc            ← rc-* 与 @rc-component/*（组件底层，不依赖 antd）
 *   antd-cssinjs  ← @ant-design/cssinjs 等样式引擎
 *   antd-icons    ← @ant-design/icons（图标定义）
 *   antd          ← antd 组件库
 */
function manualChunks(id: string): string | undefined {
  // CJS 互操作助手由 Rollup 生成，必须固定放在最底层 chunk，否则会被塞进 antd 造成循环
  if (id.includes('commonjsHelpers')) return 'vendor'
  if (!id.includes('node_modules')) return undefined
  const path = id.replace(/\\/g, '/')

  if (
    /node_modules\/(react|react-dom|react-router|react-router-dom|scheduler|react-is|use-sync-external-store|@remix-run\/router)\//.test(
      path
    )
  ) {
    return 'react-vendor'
  }
  if (
    path.includes('node_modules/@ant-design/icons') ||
    path.includes('node_modules/@ant-design/icons-svg')
  ) {
    return 'antd-icons'
  }
  // cssinjs 与 rc-util 互相引用，必须与 rc 同块，否则会产生 chunk 循环
  if (
    path.includes('node_modules/@ant-design/cssinjs') ||
    path.includes('node_modules/@ant-design/colors') ||
    path.includes('node_modules/@ant-design/fast-color')
  ) {
    return 'rc'
  }
  if (/node_modules\/(rc-[^/]+|@rc-component\/[^/]+)\//.test(path)) return 'rc'
  // 表格是唯一「只被页面引用、不被 antd 其他组件反向引用」的大组件，可单独成块
  if (/node_modules\/(antd\/es\/(table|pagination)|rc-table)\//.test(path)) return 'antd-table'
  if (path.includes('node_modules/antd/')) return 'antd'
  if (path.includes('node_modules/@ant-design/')) return 'antd'
  if (path.includes('node_modules/lucide-react')) return 'icons'
  if (path.includes('node_modules/dayjs')) return 'dayjs'
  if (path.includes('node_modules/axios')) return 'axios'
  if (path.includes('node_modules/@dnd-kit') || path.includes('node_modules/array-move')) {
    return 'dnd'
  }
  if (path.includes('node_modules/zustand')) return 'state'
  return 'vendor'
}

export default defineConfig(({ mode }) => {
  const isMock = mode === 'mock'
  const isOffline = mode === 'offline'
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    // 演示版：独立产物目录 + 相对 base（hash 路由下可直接以静态文件打开）
    base: isMock || isOffline ? './' : '/',
    build: {
      outDir: isOffline ? 'dist-offline' : isMock ? 'dist-demo' : 'dist',
      rollupOptions: isOffline
        ? { output: { inlineDynamicImports: true } } // 单文件离线版：Rollup 阶段内联全部动态 import
        : { output: { manualChunks } },
    },
  }
})
