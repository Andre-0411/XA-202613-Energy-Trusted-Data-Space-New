import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // 防止与 tdesign-react 样式冲突：设置 important
  important: true,
  theme: {
    extend: {
      colors: {
        // TDesign 主色系
        primary: {
          50: '#E8F1FF',
          100: '#BEDAFF',
          200: '#94BFFF',
          300: '#69A1FF',
          400: '#4083FF',
          500: '#0052D9',  // TDesign 主色
          600: '#0044B8',
          700: '#003597',
          800: '#002876',
          900: '#001C56',
        },
        secondary: {
          50: '#E8F5E9',
          100: '#C8E6C9',
          200: '#A5D6A7',
          300: '#81C784',
          400: '#66BB6A',
          500: '#2E7D32',
          600: '#256628',
          700: '#1B5E20',
          800: '#144D1A',
          900: '#0D3B12',
        },
        warning: {
          50: '#FFF3E0',
          100: '#FFE0B2',
          200: '#FFCC80',
          300: '#FFB74D',
          400: '#FFA726',
          500: '#ED6C02',
          600: '#E65100',
          700: '#BF360C',
        },
        danger: {
          50: '#FFEBEE',
          100: '#FFCDD2',
          200: '#EF9A9A',
          300: '#E57373',
          400: '#EF5350',
          500: '#D32F2F',
          600: '#C62828',
          700: '#B71C1C',
        },
        // TDesign 语义色
        success: { 500: '#00A870' },
        info: { 500: '#0052D9' },
      },
      fontFamily: {
        sans: [
          '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto',
          'PingFang SC', 'Microsoft YaHei', 'sans-serif',
        ],
      },
      spacing: {
        'sidebar': '232px',
        'sidebar-collapsed': '64px',
        'header': '64px',
      },
      borderRadius: {
        'card': '8px',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0,0,0,0.08)',
        'card-hover': '0 4px 16px rgba(0,0,0,0.12)',
      },
    },
  },
  corePlugins: {
    preflight: false,  // 关闭 Tailwind preflight，避免与 tdesign-react 样式冲突
  },
  plugins: [],
};

export default config;
