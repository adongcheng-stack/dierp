/**
 * 生成离线 mock 单文件演示包：dist-offline（Rollup inlineDynamicImports）→ DIERP-demo.html。
 *
 * 关键点（历史 bug）：
 * - 不能用 esbuild 事后合并 Vite 的拆分 chunk：会产生 TDZ（Cannot access 'x' before initialization）。
 *   必须在 Vite/Rollup 构建阶段用 inlineDynamicImports 内联（见 vite.config.ts 的 offline 模式）。
 * - 不能用 String.replace(regex, '<script>' + js + '</script>')：js 中的 `$&` 会被当成替换模式。
 * - 内联脚本中的 `</script` 必须转义为 `<\/script`，否则提前闭合脚本标签。
 *
 * 用法：node scripts/build-offline-demo.mjs（在 npm run build --mode offline 之后）
 */
import { readFile, writeFile, readdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const offlineDir = path.join(root, 'dist-offline')
const outFile = path.join(root, '..', 'DIERP-demo.html')

const indexHtml = await readFile(path.join(offlineDir, 'index.html'), 'utf8')
const entryMatch = indexHtml.match(/<script[^>]*src="\.\/assets\/([^"]+\.js)"/)
if (!entryMatch) throw new Error('dist-offline/index.html 中未找到入口 JS')
const jsPath = path.join(offlineDir, 'assets', entryMatch[1])
const assets = await readdir(path.join(offlineDir, 'assets'))
const jsChunks = assets.filter((f) => f.endsWith('.js'))
if (jsChunks.length !== 1) {
  throw new Error(`离线版应只有 1 个 JS chunk，实际 ${jsChunks.length}；请检查 vite offline 配置`)
}

// 用函数式替换拼接，避免 `$&` 等替换模式被解释
let js = await readFile(jsPath, 'utf8')
js = js.replace(/<\/script/gi, () => '<\\/script')

let css = ''
for (const file of assets.filter((f) => f.endsWith('.css'))) {
  css += await readFile(path.join(offlineDir, 'assets', file), 'utf8') + '\n'
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
console.log(`generated ${outFile} (${(Buffer.byteLength(html) / 1048576).toFixed(2)} MB, single chunk: ${entryMatch[1]})`)
