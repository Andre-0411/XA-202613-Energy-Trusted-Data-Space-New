/**
 * 数据资源中心状态管理（Zustand）
 * selectedDataSource / dataFilters / catalogViewMode
 */
import { create } from 'zustand';
import type { DataSource } from '@/types/api';

/** 数据目录筛选条件 */
interface DataFilters {
  /** 关键词搜索 */
  keyword: string;
  /** 数据类型筛选 */
  type: string;
  /** 敏感等级筛选 */
  level: string;
}

interface DataState {
  /** 当前选中的数据源 */
  selectedDataSource: DataSource | null;
  /** 数据目录筛选条件 */
  dataFilters: DataFilters;
  /** 目录视图模式 */
  catalogViewMode: 'card' | 'list';

  /** 设置选中数据源 */
  setSelectedDataSource: (ds: DataSource | null) => void;
  /** 合并筛选条件（支持部分更新） */
  setDataFilters: (filters: Partial<DataFilters>) => void;
  /** 切换目录视图模式 */
  setCatalogViewMode: (mode: 'card' | 'list') => void;
  /** 重置筛选条件到默认值 */
  resetFilters: () => void;
}

/** 筛选条件默认值 */
const defaultFilters: DataFilters = {
  keyword: '',
  type: '',
  level: '',
};

export const useDataStore = create<DataState>()((set) => ({
  selectedDataSource: null,
  dataFilters: { ...defaultFilters },
  catalogViewMode: 'card',

  setSelectedDataSource: (ds: DataSource | null) => {
    set({ selectedDataSource: ds });
  },

  setDataFilters: (filters: Partial<DataFilters>) => {
    set((state) => ({
      dataFilters: { ...state.dataFilters, ...filters },
    }));
  },

  setCatalogViewMode: (mode: 'card' | 'list') => {
    set({ catalogViewMode: mode });
  },

  resetFilters: () => {
    set({ dataFilters: { ...defaultFilters } });
  },
}));
