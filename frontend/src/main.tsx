import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import { ConfirmProvider } from './components/common/ConfirmProvider'
import { useThemeStore } from './stores/themeStore'
import { getAntdTheme } from './theme/antdTheme'
import { setupMockApi } from './mock'
import './index.css'

/** 演示数据模式：在请求层接管 /api，不连接后端 */
setupMockApi()

/** 主题订阅放在最外层：亮/暗切换时 ConfigProvider 会重算 antd 令牌 */
function Root() {
  const theme = useThemeStore((state) => state.theme)

  return (
    <ConfigProvider locale={zhCN} theme={getAntdTheme(theme)}>
      <AntdApp>
        <ConfirmProvider>
          <App />
        </ConfirmProvider>
      </AntdApp>
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
)
