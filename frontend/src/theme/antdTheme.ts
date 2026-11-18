import { theme as antdTheme, type ThemeConfig } from 'antd'
import type { ThemeMode } from '../stores/themeStore'

/**
 * antd 主题令牌 —— 与 index.css 的设计变量保持同一套取值。
 * 亮色取原始色阶中段，暗色整体提亮一档（与 MES 的 .dark 变量同策略）。
 */
const palette = {
  light: {
    brand: '#2662c9',
    success: '#16a34a',
    warning: '#d97706',
    error: '#dc2626',
    text: '#151f29',
    textSecondary: '#5f6b7a',
    border: '#dfe5ec',
    borderSecondary: '#e8edf3',
    bgBase: '#ffffff',
    bgLayout: '#f6f8fa',
    bgContainer: '#ffffff',
    bgElevated: '#ffffff',
  },
  dark: {
    brand: '#6091dd',
    success: '#4ade80',
    warning: '#fbbf24',
    error: '#f87171',
    text: '#eef2f7',
    textSecondary: '#8d99a8',
    border: '#333d4b',
    borderSecondary: '#2b3441',
    bgBase: '#0f1218',
    bgLayout: '#11151c',
    bgContainer: '#21252c',
    bgElevated: '#272b32',
  },
} as const

export function getAntdTheme(mode: ThemeMode): ThemeConfig {
  const c = palette[mode]

  return {
    algorithm: mode === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: c.brand,
      colorInfo: c.brand,
      colorSuccess: c.success,
      colorWarning: c.warning,
      colorError: c.error,
      colorTextBase: c.text,
      colorText: c.text,
      colorTextSecondary: c.textSecondary,
      colorBorder: c.border,
      colorBorderSecondary: c.borderSecondary,
      colorBgBase: c.bgBase,
      colorBgLayout: c.bgLayout,
      colorBgContainer: c.bgContainer,
      colorBgElevated: c.bgElevated,
      borderRadius: 6,
      borderRadiusLG: 8,
      borderRadiusSM: 4,
      controlHeight: 34,
      fontSize: 14,
      fontFamily:
        "system-ui, -apple-system, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', sans-serif",
      boxShadow: '0 1px 2px 0 rgba(15, 23, 42, 0.04)',
      wireframe: false,
    },
    components: {
      Layout: {
        headerBg: c.bgContainer,
        siderBg: c.bgContainer,
        bodyBg: c.bgLayout,
        headerHeight: 56,
      },
      Menu: {
        itemHeight: 36,
        itemBorderRadius: 6,
        itemSelectedBg: mode === 'dark' ? '#1b2536' : '#eff5ff',
        itemSelectedColor: mode === 'dark' ? '#a9c6f2' : '#1e4f9e',
        itemHoverBg: mode === 'dark' ? '#2b3441' : '#f2f5f9',
        itemColor: mode === 'dark' ? '#8d99a8' : '#5f6b7a',
        itemMarginInline: 8,
        itemMarginBlock: 2,
        iconSize: 16,
        collapsedIconSize: 18,
      },
      Table: {
        headerBg: mode === 'dark' ? '#272b32' : '#eef1f5',
        headerColor: c.textSecondary,
        headerSplitColor: 'transparent',
        rowHoverBg: mode === 'dark' ? '#2b3441' : '#f2f5f9',
        borderColor: c.borderSecondary,
        cellPaddingBlock: 10,
        cellPaddingInline: 14,
        fontSize: 13,
      },
      Card: {
        colorBorderSecondary: c.border,
        paddingLG: 16,
      },
      Button: {
        fontWeight: 500,
        defaultBorderColor: c.border,
        defaultColor: c.text,
        paddingInline: 14,
      },
      Input: {
        activeShadow: `0 0 0 2px ${mode === 'dark' ? 'rgba(96,145,221,0.25)' : 'rgba(38,98,201,0.15)'}`,
      },
      Select: {
        optionSelectedBg: mode === 'dark' ? '#1b2536' : '#eff5ff',
      },
      Tag: {
        defaultBg: mode === 'dark' ? '#2b3441' : '#eef1f5',
        defaultColor: c.textSecondary,
      },
      Modal: {
        paddingContentHorizontalLG: 20,
        titleFontSize: 15,
      },
      Tabs: {
        titleFontSize: 13,
        horizontalItemPadding: '8px 0',
      },
      Descriptions: {
        labelColor: c.textSecondary,
        contentColor: c.text,
      },
      Steps: {
        iconSize: 26,
      },
      Pagination: {
        itemSize: 30,
        fontSize: 12,
      },
    },
  }
}
