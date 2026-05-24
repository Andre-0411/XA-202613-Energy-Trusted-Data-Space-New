/**
 * 主题模块入口
 * 已移除 MUI createTheme，统一使用 TDesign 主题
 */

// ─── TDesign 主题导出 ────────────────────────────────────────────
export { designTokens, applyTDesignTheme, applyTDesignDarkTheme } from './tdesign-theme';
export { useThemeMode } from './useThemeMode';

/** 自定义响应式断点常量 */
export const BREAKPOINTS = {
  xs: 0,
  sm: 600,
  md: 900,
  lg: 1200,
  xl: 1536,
} as const;

/**
 * useIsMobile - 判断当前是否为移动端（md 断点以下）
 * 使用原生 matchMedia，SSR 安全
 */
export const useIsMobile = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia(`(max-width:${BREAKPOINTS.md - 1}px)`).matches;
};

/**
 * useIsSmall - 判断当前是否为小屏设备（sm 断点以下）
 * 使用原生 matchMedia，SSR 安全
 */
export const useIsSmall = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia(`(max-width:${BREAKPOINTS.sm - 1}px)`).matches;
};

/**
 * useBreakpoint - 返回当前命中的断点名称
 * 返回 'xs' | 'sm' | 'md' | 'lg' | 'xl'
 */
export const useBreakpoint = (): 'xs' | 'sm' | 'md' | 'lg' | 'xl' => {
  if (typeof window === 'undefined') return 'md';
  const isXl = window.matchMedia(`(min-width:${BREAKPOINTS.xl}px)`).matches;
  const isLg = window.matchMedia(`(min-width:${BREAKPOINTS.lg}px)`).matches;
  const isMd = window.matchMedia(`(min-width:${BREAKPOINTS.md}px)`).matches;
  const isSm = window.matchMedia(`(min-width:${BREAKPOINTS.sm}px)`).matches;

  if (isXl) return 'xl';
  if (isLg) return 'lg';
  if (isMd) return 'md';
  if (isSm) return 'sm';
  return 'xs';
};
