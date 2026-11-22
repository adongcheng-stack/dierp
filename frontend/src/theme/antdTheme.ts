import { theme as antdTheme, type ThemeConfig } from 'antd'
import type { ThemeMode } from '../stores/themeStore'

/**
 * antd 主题令牌 —— 与 index.css 的设计变量保持同一套取值。
 * 亮色取原始色阶中段，暗色整体提亮一档（与 MES 的 .dark 变量同策略）。
 */
const palette = {
  light: {
    brand: '#2662c9',
    success: '#22774f',
    warning: '#a55e0d',
    error: '#b42222',
    text: '#363f4f',
    textSecondary: '#4d596a',
    border: '#647082',
    borderSecondary: '#e2e6eb',
    bgBase: '#f6f7f9',
    bgLayout: '#eceff3',
    bgContainer: '#f6f7f9',
    bgElevated: '#f6f7f9',
  },
  dark: {
    brand: '#6090dc',
    success: '#43d679',
    warning: '#fba82d',
    error: '#f05151',
    text: '#f6f7f9',
    textSecondary: '#cbd3dd',
    border: '#95a1b1',
    borderSecondary: '#353c48',
    bgBase: '#161920',
    bgLayout: '#101319',
    bgContainer: '#21252e',
    bgElevated: '#353c48',
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
      borderRadius: 2,
      borderRadiusLG: 2,
      borderRadiusSM: 2,
      controlHeight: 36,
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
        headerBg: 'transparent',
        headerColor: c.text,
        headerSplitColor: 'transparent',
        rowHoverBg: mode === 'dark' ? '#353c48' : '#eceff3',
        borderColor: c.borderSecondary,
        cellPaddingBlock: 12,
        cellPaddingInline: 16,
        fontSize: 14,
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
