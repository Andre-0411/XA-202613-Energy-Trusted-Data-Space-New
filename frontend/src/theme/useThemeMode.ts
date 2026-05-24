/**
 * 主题模式管理 Hook
 * 同步 appStore.themeMode 与 TDesign CSS Variables / DOM 属性
 */
import { useEffect } from 'react';
import { useAppStore } from '@/stores/appStore';
import { applyTDesignTheme, applyTDesignDarkTheme } from './tdesign-theme';

/**
 * 根据主题模式应用对应的 CSS Variables 和 DOM 属性
 * @param mode - 'light' | 'dark' | 'system'
 */
function applyTheme(mode: 'light' | 'dark' | 'system') {
  const root = document.documentElement;

  if (mode === 'dark') {
    root.setAttribute('theme-mode', 'dark');
    root.classList.add('dark');
    root.classList.remove('light');
    applyTDesignDarkTheme();
  } else if (mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      root.setAttribute('theme-mode', 'dark');
      root.classList.add('dark');
      root.classList.remove('light');
      applyTDesignDarkTheme();
    } else {
      root.removeAttribute('theme-mode');
      root.classList.add('light');
      root.classList.remove('dark');
      applyTDesignTheme();
    }
  } else {
    root.removeAttribute('theme-mode');
    root.classList.add('light');
    root.classList.remove('dark');
    applyTDesignTheme();
  }
}

/**
 * 主题模式管理 Hook
 * - 读取 appStore.themeMode 并同步 TDesign CSS Variables
 * - 监听系统主题变化（themeMode === 'system' 时生效）
 * - 返回当前 themeMode 供组件使用
 */
export function useThemeMode() {
  const themeMode = useAppStore((s) => s.themeMode);

  // 主题模式变更时，应用对应的 CSS Variables
  useEffect(() => {
    applyTheme(themeMode);
  }, [themeMode]);

  // 监听系统主题变化（仅 system 模式有效）
  useEffect(() => {
    if (themeMode !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      const root = document.documentElement;
      if (e.matches) {
        root.setAttribute('theme-mode', 'dark');
        root.classList.add('dark');
        root.classList.remove('light');
        applyTDesignDarkTheme();
      } else {
        root.removeAttribute('theme-mode');
        root.classList.add('light');
        root.classList.remove('dark');
        applyTDesignTheme();
      }
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [themeMode]);

  return { themeMode };
}
