/** @type {import('tailwindcss').Config} */

/**
 * 色板映射说明（与 MES 前端保持同一套设计变量）
 * ----------------------------------------------------------------------------
 * gray / slate / blue 三族不取 Tailwind 内置常量，而是映射到 index.css 的
 * --n-* / --b-* 变量。暗色模式在 .dark 下翻转整阶语义，因此既有的
 * `bg-white dark:bg-gray-800`、`border-gray-200 dark:border-gray-700`
 * 这类组合无需逐处改动即可在两种模式下成立于新色板。
 *
 * 必须使用 `hsl(var(--x) / <alpha-value>)` 形式，否则 `bg-gray-50/60`
 * 这类透明度修饰符会失效。
 */

const neutral = {
  50: 'hsl(var(--n-50) / <alpha-value>)',
  100: 'hsl(var(--n-100) / <alpha-value>)',
  200: 'hsl(var(--n-200) / <alpha-value>)',
  300: 'hsl(var(--n-300) / <alpha-value>)',
  400: 'hsl(var(--n-400) / <alpha-value>)',
  500: 'hsl(var(--n-500) / <alpha-value>)',
  600: 'hsl(var(--n-600) / <alpha-value>)',
  700: 'hsl(var(--n-700) / <alpha-value>)',
  800: 'hsl(var(--n-800) / <alpha-value>)',
  900: 'hsl(var(--n-900) / <alpha-value>)',
  950: 'hsl(var(--n-950) / <alpha-value>)',
}

const brandScale = {
  50: 'hsl(var(--b-50) / <alpha-value>)',
  100: 'hsl(var(--b-100) / <alpha-value>)',
  200: 'hsl(var(--b-200) / <alpha-value>)',
  300: 'hsl(var(--b-300) / <alpha-value>)',
  400: 'hsl(var(--b-400) / <alpha-value>)',
  500: 'hsl(var(--b-500) / <alpha-value>)',
  600: 'hsl(var(--b-600) / <alpha-value>)',
  700: 'hsl(var(--b-700) / <alpha-value>)',
  800: 'hsl(var(--b-800) / <alpha-value>)',
  900: 'hsl(var(--b-900) / <alpha-value>)',
  950: 'hsl(var(--b-950) / <alpha-value>)',
}

module.exports = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border) / <alpha-value>)',
        input: 'hsl(var(--input) / <alpha-value>)',
        ring: 'hsl(var(--ring) / <alpha-value>)',
        background: 'hsl(var(--background) / <alpha-value>)',
        foreground: 'hsl(var(--foreground) / <alpha-value>)',
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary) / <alpha-value>)',
          foreground: 'hsl(var(--secondary-foreground) / <alpha-value>)',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive) / <alpha-value>)',
          foreground: 'hsl(var(--destructive-foreground) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted) / <alpha-value>)',
          foreground: 'hsl(var(--muted-foreground) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent) / <alpha-value>)',
          foreground: 'hsl(var(--accent-foreground) / <alpha-value>)',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover) / <alpha-value>)',
          foreground: 'hsl(var(--popover-foreground) / <alpha-value>)',
        },
        card: {
          DEFAULT: 'hsl(var(--card) / <alpha-value>)',
          foreground: 'hsl(var(--card-foreground) / <alpha-value>)',
        },

        // ── 语义层：新代码优先使用 ──
        surface: {
          DEFAULT: 'hsl(var(--surface) / <alpha-value>)',
          sunken: 'hsl(var(--surface-sunken) / <alpha-value>)',
          raised: 'hsl(var(--surface-raised) / <alpha-value>)',
          hover: 'hsl(var(--surface-hover) / <alpha-value>)',
        },
        field: 'hsl(var(--field-edge) / <alpha-value>)',
        focus: 'hsl(var(--focus-ring) / <alpha-value>)',
        status: {
          success: 'hsl(var(--chart-success) / <alpha-value>)',
          warning: 'hsl(var(--chart-warning) / <alpha-value>)',
          error: 'hsl(var(--chart-danger) / <alpha-value>)',
        },
        line: {
          DEFAULT: 'hsl(var(--line) / <alpha-value>)',
          strong: 'hsl(var(--line-strong) / <alpha-value>)',
        },
        ink: {
          DEFAULT: 'hsl(var(--ink) / <alpha-value>)',
          soft: 'hsl(var(--ink-soft) / <alpha-value>)',
          faint: 'hsl(var(--ink-faint) / <alpha-value>)',
          placeholder: 'hsl(var(--ink-placeholder) / <alpha-value>)',
        },
        brand: {
          DEFAULT: 'hsl(var(--brand) / <alpha-value>)',
          hover: 'hsl(var(--brand-hover) / <alpha-value>)',
          soft: 'hsl(var(--brand-soft) / <alpha-value>)',
          ink: 'hsl(var(--brand-ink) / <alpha-value>)',
        },

        // ── 既有色族映射到变量 ──
        gray: neutral,
        slate: neutral,
        blue: brandScale,
      },
      fontSize: {
        xs: 'var(--text-xs)',
        sm: 'var(--text-sm)',
        md: 'var(--text-md)',
        lg: 'var(--text-lg)',
        xl: 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'var(--radius)',
        sm: 'var(--radius)',
        none: '0',
      },
      fontFamily: {
        sans: ['var(--font-body)'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Consolas', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px 0 hsl(var(--shadow-color) / 0.04), 0 1px 3px 0 hsl(var(--shadow-color) / 0.06)',
        pop: '0 8px 24px -6px hsl(var(--shadow-color) / 0.16), 0 2px 6px -2px hsl(var(--shadow-color) / 0.08)',
        'edge-left': '-4px 0 8px -4px hsl(var(--shadow-color) / 0.10)',
      },
      transitionTimingFunction: {
        ui: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'skeleton-pulse': {
          '0%, 100%': { opacity: '0.55' },
          '50%': { opacity: '0.9' },
        },
      },
      animation: {
        'fade-in': 'fade-in 160ms cubic-bezier(0.22, 1, 0.36, 1)',
        'skeleton-pulse': '1.6s ease-in-out infinite skeleton-pulse',
      },
    },
  },
  plugins: [],
}
