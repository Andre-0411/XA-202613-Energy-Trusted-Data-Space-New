/**
 * 区块链存证中心状态管理（Zustand）
 * selectedEvidence / chainStatus / queryHistory
 */
import { create } from 'zustand';
import type { Evidence } from '@/types/api';

/** 区块链连接状态 */
type ChainStatus = 'connected' | 'disconnected';

interface BlockchainState {
  /** 当前选中的存证记录 */
  selectedEvidence: Evidence | null;
  /** 链连接状态 */
  chainStatus: ChainStatus;
  /** 历史查询列表（最近 50 条） */
  queryHistory: string[];

  /** 设置选中存证 */
  setSelectedEvidence: (evidence: Evidence | null) => void;
  /** 设置链连接状态 */
  setChainStatus: (status: ChainStatus) => void;
  /** 添加查询历史（自动去重，保留最近 50 条） */
  addQueryHistory: (query: string) => void;
  /** 清空查询历史 */
  clearQueryHistory: () => void;
}

const MAX_HISTORY_SIZE = 50;

export const useBlockchainStore = create<BlockchainState>()((set) => ({
  selectedEvidence: null,
  chainStatus: 'disconnected',
  queryHistory: [],

  setSelectedEvidence: (evidence: Evidence | null) => {
    set({ selectedEvidence: evidence });
  },

  setChainStatus: (status: ChainStatus) => {
    set({ chainStatus: status });
  },

  addQueryHistory: (query: string) => {
    set((state) => {
      // 去重：若已存在则移到最前面
      const filtered = state.queryHistory.filter((q) => q !== query);
      const updated = [query, ...filtered].slice(0, MAX_HISTORY_SIZE);
      return { queryHistory: updated };
    });
  },

  clearQueryHistory: () => {
    set({ queryHistory: [] });
  },
}));
