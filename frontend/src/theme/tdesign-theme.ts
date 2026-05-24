/**
 * TDesign 主题配置 — CSS Variables
 * 参照 TDesign React Starter 设计风格
 */

// TDesign 设计 Token
export const designTokens = {
  // 品牌色
  brandColor: '#0052D9',
  brandColorHover: '#266FE8',
  brandColorActive: '#0044B8',
  brandColorLight: '#E8F1FF',

  // 侧边栏
  sidebarBg: '#18181D',
  sidebarWidth: '232px',
  sidebarCollapsedWidth: '64px',
  sidebarTextColor: 'rgba(255,255,255,0.85)',
  sidebarTextHover: '#FFFFFF',
  sidebarActiveBg: '#0052D9',

  // 顶栏
  headerBg: '#FFFFFF',
  headerHeight: '64px',
  headerBorder: '#E8E8E8',

  // 卡片
  cardBg: '#FFFFFF',
  cardBorder: 'none',
  cardRadius: '8px',
  cardShadow: '0 2px 8px rgba(0,0,0,0.08)',
  cardShadowHover: '0 4px 16px rgba(0,0,0,0.12)',

  // 表格
  tableHeaderBg: '#F5F5F5',
  tableBorderColor: '#E8E8E8',
  tableRowHover: '#F5F5F5',

  // 文字
  textPrimary: 'rgba(0,0,0,0.9)',
  textSecondary: 'rgba(0,0,0,0.6)',
  textPlaceholder: 'rgba(0,0,0,0.35)',
  textDisabled: 'rgba(0,0,0,0.25)',

  // 背景
  bgPage: '#F5F5F5',
  bgContainer: '#FFFFFF',
  bgHover: '#F5F5F5',

  // 间距
  spacingXs: '4px',
  spacingSm: '8px',
  spacingMd: '16px',
  spacingLg: '24px',
  spacingXl: '32px',

  // 字号
  fontSizeXs: '12px',
  fontSizeSm: '12px',
  fontSizeBase: '14px',
  fontSizeMd: '14px',
  fontSizeLg: '16px',
  fontSizeXl: '20px',
  fontSizeXxl: '24px',
} as const;

/**
 * 注入 TDesign 亮色主题 CSS Variables 到 :root
 */
export function applyTDesignTheme() {
  const root = document.documentElement;
  Object.entries({
    // 品牌色
    '--td-brand-color': designTokens.brandColor,
    '--td-brand-color-hover': designTokens.brandColorHover,
    '--td-brand-color-active': designTokens.brandColorActive,
    '--td-brand-color-light': designTokens.brandColorLight,
    // 侧边栏
    '--td-sidebar-bg': designTokens.sidebarBg,
    '--td-sidebar-width': designTokens.sidebarWidth,
    '--td-sidebar-collapsed-width': designTokens.sidebarCollapsedWidth,
    '--td-sidebar-text-color': designTokens.sidebarTextColor,
    '--td-sidebar-text-hover': designTokens.sidebarTextHover,
    '--td-sidebar-active-bg': designTokens.sidebarActiveBg,
    // 顶栏
    '--td-header-bg': designTokens.headerBg,
    '--td-header-height': designTokens.headerHeight,
    '--td-header-border': designTokens.headerBorder,
    // 卡片
    '--td-card-bg': designTokens.cardBg,
    '--td-card-border': designTokens.cardBorder,
    '--td-card-radius': designTokens.cardRadius,
    '--td-card-shadow': designTokens.cardShadow,
    '--td-card-shadow-hover': designTokens.cardShadowHover,
    // 表格
    '--td-table-header-bg': designTokens.tableHeaderBg,
    '--td-table-border-color': designTokens.tableBorderColor,
    '--td-table-row-hover': designTokens.tableRowHover,
    // 文字
    '--td-text-primary': designTokens.textPrimary,
    '--td-text-secondary': designTokens.textSecondary,
    '--td-text-placeholder': designTokens.textPlaceholder,
    '--td-text-disabled': designTokens.textDisabled,
    // 背景
    '--td-page-bg': designTokens.bgPage,
    '--td-container-bg': designTokens.bgContainer,
    '--td-bg-hover': designTokens.bgHover,
    // 间距
    '--td-spacing-xs': designTokens.spacingXs,
    '--td-spacing-sm': designTokens.spacingSm,
    '--td-spacing-md': designTokens.spacingMd,
    '--td-spacing-lg': designTokens.spacingLg,
    '--td-spacing-xl': designTokens.spacingXl,
    // 字号
    '--td-font-size-xs': designTokens.fontSizeXs,
    '--td-font-size-sm': designTokens.fontSizeSm,
    '--td-font-size-base': designTokens.fontSizeBase,
    '--td-font-size-md': designTokens.fontSizeMd,
    '--td-font-size-lg': designTokens.fontSizeLg,
    '--td-font-size-xl': designTokens.fontSizeXl,
    '--td-font-size-xxl': designTokens.fontSizeXxl,
  }).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
}

/** 暗色主题设计 Token */
const darkDesignTokens = {
  brandColor: '#4083FF',
  brandColorHover: '#69A1FF',
  brandColorActive: '#266FE8',
  brandColorLight: 'rgba(64, 131, 255, 0.15)',

  sidebarBg: '#1A1A20',
  sidebarTextColor: 'rgba(255,255,255,0.85)',
  sidebarTextHover: '#FFFFFF',
  sidebarActiveBg: '#4083FF',

  headerBg: '#242428',
  headerBorder: 'rgba(255,255,255,0.08)',

  cardBg: '#2C2C32',
  cardBorder: 'none',
  cardRadius: '8px',
  cardShadow: '0 2px 8px rgba(0,0,0,0.25)',
  cardShadowHover: '0 4px 16px rgba(0,0,0,0.35)',

  tableHeaderBg: '#2C2C32',
  tableBorderColor: 'rgba(255,255,255,0.08)',
  tableRowHover: 'rgba(255,255,255,0.04)',

  textPrimary: 'rgba(255,255,255,0.9)',
  textSecondary: 'rgba(255,255,255,0.55)',
  textPlaceholder: 'rgba(255,255,255,0.3)',
  textDisabled: 'rgba(255,255,255,0.2)',

  bgPage: '#18181D',
  bgContainer: '#242428',
  bgHover: 'rgba(255,255,255,0.06)',
} as const;

/**
 * 注入 TDesign 暗色主题 CSS Variables 到 :root
 */
export function applyTDesignDarkTheme() {
  const root = document.documentElement;
  Object.entries({
    // 品牌色
    '--td-brand-color': darkDesignTokens.brandColor,
    '--td-brand-color-hover': darkDesignTokens.brandColorHover,
    '--td-brand-color-active': darkDesignTokens.brandColorActive,
    '--td-brand-color-light': darkDesignTokens.brandColorLight,
    // 侧边栏
    '--td-sidebar-bg': darkDesignTokens.sidebarBg,
    '--td-sidebar-text-color': darkDesignTokens.sidebarTextColor,
    '--td-sidebar-text-hover': darkDesignTokens.sidebarTextHover,
    '--td-sidebar-active-bg': darkDesignTokens.sidebarActiveBg,
    // 顶栏
    '--td-header-bg': darkDesignTokens.headerBg,
    '--td-header-border': darkDesignTokens.headerBorder,
    // 卡片
    '--td-card-bg': darkDesignTokens.cardBg,
    '--td-card-border': darkDesignTokens.cardBorder,
    '--td-card-radius': darkDesignTokens.cardRadius,
    '--td-card-shadow': darkDesignTokens.cardShadow,
    '--td-card-shadow-hover': darkDesignTokens.cardShadowHover,
    // 表格
    '--td-table-header-bg': darkDesignTokens.tableHeaderBg,
    '--td-table-border-color': darkDesignTokens.tableBorderColor,
    '--td-table-row-hover': darkDesignTokens.tableRowHover,
    // 文字
    '--td-text-primary': darkDesignTokens.textPrimary,
    '--td-text-secondary': darkDesignTokens.textSecondary,
    '--td-text-placeholder': darkDesignTokens.textPlaceholder,
    '--td-text-disabled': darkDesignTokens.textDisabled,
    // 背景
    '--td-page-bg': darkDesignTokens.bgPage,
    '--td-container-bg': darkDesignTokens.bgContainer,
    '--td-bg-hover': darkDesignTokens.bgHover,
  }).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
}
