/**
 * 生成离线 mock 单文件演示包：dist-demo → 一个自包含 DIERP-demo.html。
 *
 * 关键点（历史 bug）：
 * - 不能用 String.replace(regex, '<script>' + js + '</script>')：
 *   js 中的 `$&` 会被当成 replacement 模式插回原始标签，导致浏览器把 JS 当文本渲染。
 * - 内联脚本中的 `</script` 必须转义为 `<\/script`，否则提前闭合脚本标签。
 *
 * 用法：node scripts/build-offline-demo.mjs
 */
import { build } from 'esbuild'
import { readFile, writeFile, readdir } from 'node:fs/promises'
import path from 'node:path'

const root = path.resolve(import.meta.dirname ?? path.dirname(new URL(import.meta.url).pathname), '..')
const demoDir = path.join(root, 'dist-demo')
const outFile = path.join(root, '..', 'DIERP-demo.html')

const indexHtml = await readFile(path.join(demoDir, 'index.html'), 'utf8')
const entryMatch = indexHtml.match(/<script[^>]*src="\.\/assets\/([^"]+\.js)"/)
if (!entryMatch) throw new Error('dist-demo/index.html 中未找到入口 JS')
const entry = path.join(demoDir, 'assets', entryMatch[1])

// 把入口 + 所有动态 chunk 打成一个 iife（无需服务器、无 ESM import）
const result = await build({
  entryPoints: [entry],
  bundle: true,
  write: false,
  format: 'esm',
  platform: 'browser',
  target: ['es2020'],
  minify: true,
  legalComments: 'none',
  loader: { '.js': 'js' },
})
// Vite 的 __vite__mapDeps 会按 chunk 名生成 modulepreload 链接；单文件版全部已内联，
// 置空即可避免 file:// 下产生无意义的 CORS 报错（不影响真正的懒加载 import）。
const js = result.outputFiles[0].text
  .replace(/__vite__mapDeps\(\[[^\]]*\]\)/g, '[]')
  .replace(/t\.f=\[[^\]]*\]/g, 't.f=[]')
  .replace(/<\/script/gi, '<\\/script')

// 内联所有 CSS（dist-demo 通常只有一个入口样式）
const assets = await readdir(path.join(demoDir, 'assets'))
const cssFiles = assets.filter((f) => f.endsWith('.css'))
let css = ''
for (const file of cssFiles) {
  css += await readFile(path.join(demoDir, 'assets', file), 'utf8') + '\n'
}

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>DIERP ERP 管理系统 · Demo（离线版）</title>
<style>${css}</style>
</head>
<body>
<div id="root"></div>
<script type="module">${js}</script>
</body>
</html>`

await writeFile(outFile, html, 'utf8')
console.log(`generated ${outFile} (${(Buffer.byteLength(html) / 1048576).toFixed(2)} MB, chunks inlined: ${assets.filter((f) => f.endsWith('.js')).length})`)
