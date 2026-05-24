/**
 * 运营管理中心状态管理（Zustand）
 * selectedUser / monitorTimeRange / alertFilter
 */
import { create } from 'zustand';
import type { User } from '@/types/api';

/** 监控时间范围选项 */
type MonitorTimeRange = '1h' | '6h' | '24h' | '7d';

interface OpsState {
  /** 当前选中的用户 */
  selectedUser: User | null;
  /** 监控面板时间范围 */
  monitorTimeRange: MonitorTimeRange;
  /** 告警筛选关键词 */
  alertFilter: string;

  /** 设置选中用户 */
  setSelectedUser: (user: User | null) => void;
  /** 设置监控时间范围 */
  setMonitorTimeRange: (range: MonitorTimeRange) => void;
  /** 设置告警筛选关键词 */
  setAlertFilter: (filter: string) => void;
}

export const useOpsStore = create<OpsState>()((set) => ({
  selectedUser: null,
  monitorTimeRange: '24h',
  alertFilter: '',

  setSelectedUser: (user: User | null) => {
    set({ selectedUser: user });
  },

  setMonitorTimeRange: (range: MonitorTimeRange) => {
    set({ monitorTimeRange: range });
  },

  setAlertFilter: (filter: string) => {
    set({ alertFilter: filter });
  },
}));
