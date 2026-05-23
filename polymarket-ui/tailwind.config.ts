import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Binance Brand Colors
        primary: '#fcd535',
        'primary-active': '#f0b90b',
        'primary-disabled': '#3a3a1f',
        ink: '#181a20',

        // Canvas & Surface
        canvas: '#0b0e11',
        'surface-card': '#1e2329',
        'surface-elevated': '#2b3139',
        'surface-soft-light': '#fafafa',

        // Text Colors
        body: '#eaecef',
        muted: '#707a8a',
        'muted-strong': '#929aa5',

        // Borders
        hairline: '#2b3139',
        'border-strong': '#cdd1d6',

        // Trading Semantics
        'trading-up': '#0ecb81',
        'trading-down': '#f6465d',

        // Info & Focus
        info: '#3b82f6',
        'info-ring': '#3b82f6',

        // On-color overlays
        'on-primary': '#181a20',
        'on-dark': '#ffffff',
      },
      fontFamily: {
        // Binance Nova (display + body) - fallback to Inter
        display: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        body: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        // Binance Plex (numbers) - fallback to IBM Plex Mono
        mono: ['IBM Plex Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Display sizes
        'hero-display': ['64px', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-1px' }],
        'display-lg': ['48px', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-0.5px' }],
        'display-md': ['40px', { lineHeight: '1.15', fontWeight: '600', letterSpacing: '-0.3px' }],
        'display-sm': ['32px', { lineHeight: '1.2', fontWeight: '600' }],

        // Title sizes
        'title-lg': ['24px', { lineHeight: '1.3', fontWeight: '600' }],
        'title-md': ['20px', { lineHeight: '1.35', fontWeight: '600' }],
        'title-sm': ['16px', { lineHeight: '1.4', fontWeight: '600' }],

        // Number sizes (use mono font)
        'number-display': ['40px', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-0.3px' }],
        'number-md': ['16px', { lineHeight: '1.4', fontWeight: '500' }],
        'number-sm': ['14px', { lineHeight: '1.4', fontWeight: '500' }],

        // Body sizes
        'body-md': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'body-sm': ['13px', { lineHeight: '1.5', fontWeight: '400' }],
        caption: ['12px', { lineHeight: '1.4', fontWeight: '500' }],
        button: ['14px', { lineHeight: '1', fontWeight: '600' }],
        'nav-link': ['14px', { lineHeight: '1.4', fontWeight: '500' }],
      },
      spacing: {
        xxs: '4px',
        xs: '8px',
        sm: '12px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        xxl: '48px',
        section: '80px',
      },
      borderRadius: {
        xs: '2px',
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
        pill: '9999px',
      },
    },
  },
  plugins: [],
}

export default config
