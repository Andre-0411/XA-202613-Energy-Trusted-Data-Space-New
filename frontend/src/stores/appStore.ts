/**
 * 应用状态管理（Zustand）
 * sidebarOpen / currentModule / themeMode / notifications / tabs
 * toggleSidebar / setModule / toggleTheme / addNotification / clearNotifications / tab管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Notification } from '@/types/api';

type ThemeMode = 'light' | 'dark' | 'system';

/** 多页签 */
export interface TabItem {
  key: string;
  label: string;
  path: string;
  closable?: boolean;
}

interface AppState {
  sidebarOpen: boolean;
  currentModule: string;
  themeMode: ThemeMode;
  notifications: Notification[];
  globalLoading: boolean;
  globalError: string | null;
  /** 多页签列表 */
  tabs: TabItem[];
  /** 当前激活页签 key */
  activeTabKey: string;

  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setModule: (module: string) => void;
  toggleTheme: () => void;
  setThemeMode: (mode: ThemeMode) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'read' | 'created_at'>) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  setGlobalLoading: (loading: boolean) => void;
  setGlobalError: (error: string | null) => void;
  /** 添加页签（已存在则激活） */
  addTab: (tab: TabItem) => void;
  /** 关闭页签 */
  removeTab: (key: string) => void;
  /** 设置激活页签 */
  setActiveTabKey: (key: string) => void;
  /** 关闭其他页签 */
  closeOtherTabs: (key: string) => void;
  /** 关闭所有可关闭页签 */
  closeAllTabs: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      currentModule: 'dashboard',
      themeMode: 'light',
      notifications: [],
      globalLoading: false,
      globalError: null,
      tabs: [{ key: 'dashboard', label: '控制台', path: '/dashboard', closable: false }],
      activeTabKey: 'dashboard',

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open });
      },

      setModule: (module: string) => {
        set({ currentModule: module });
      },

      toggleTheme: () => {
        const current = get().themeMode;
        const next: ThemeMode = current === 'light' ? 'dark' : current === 'dark' ? 'system' : 'light';
        set({ themeMode: next });
        applyThemeMode(next);
      },

      setThemeMode: (mode: ThemeMode) => {
        set({ themeMode: mode });
        applyThemeMode(mode);
      },

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          read: false,
          created_at: new Date().toISOString(),
        };
        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50),
        }));
      },

      markNotificationRead: (id: string) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n,
          ),
        }));
      },

      clearNotifications: () => {
        set({ notifications: [] });
      },

      setGlobalLoading: (loading: boolean) => {
        set({ globalLoading: loading });
      },

      setGlobalError: (error: string | null) => {
        set({ globalError: error });
      },

      addTab: (tab: TabItem) => {
        const { tabs } = get();
        const exists = tabs.find((t) => t.key === tab.key);
        if (exists) {
          set({ activeTabKey: tab.key });
        } else {
          set({
            tabs: [...tabs, { ...tab, closable: tab.closable ?? true }],
            activeTabKey: tab.key,
          });
        }
      },

      removeTab: (key: string) => {
        const { tabs, activeTabKey } = get();
        const target = tabs.find((t) => t.key === key);
        if (!target || target.closable === false) return;
        const newTabs = tabs.filter((t) => t.key !== key);
        if (newTabs.length === 0) {
          newTabs.push({ key: 'dashboard', label: '控制台', path: '/dashboard', closable: false });
        }
        let newActive = activeTabKey;
        if (activeTabKey === key) {
          const idx = tabs.findIndex((t) => t.key === key);
          newActive = newTabs[Math.min(idx, newTabs.length - 1)].key;
        }
        set({ tabs: newTabs, activeTabKey: newActive });
      },

      setActiveTabKey: (key: string) => {
        set({ activeTabKey: key });
      },

      closeOtherTabs: (key: string) => {
        const { tabs } = get();
        set({
          tabs: tabs.filter((t) => !t.closable || t.key === key),
          activeTabKey: key,
        });
      },

      closeAllTabs: () => {
        set({
          tabs: [{ key: 'dashboard', label: '控制台', path: '/dashboard', closable: false }],
          activeTabKey: 'dashboard',
        });
      },
    }),
    {
      name: 'eds-app-storage',
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        currentModule: state.currentModule,
        themeMode: state.themeMode,
        tabs: state.tabs,
        activeTabKey: state.activeTabKey,
      }),
    },
  ),
);

/** 应用主题到 DOM */
function applyThemeMode(mode: ThemeMode): void {
  const root = document.documentElement;
  if (mode === 'dark') {
    root.classList.add('dark');
    root.classList.remove('light');
  } else if (mode === 'light') {
    root.classList.add('light');
    root.classList.remove('dark');
  } else {
    // system
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.classList.toggle('dark', prefersDark);
    root.classList.toggle('light', !prefersDark);
  }
}
