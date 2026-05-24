/**
 * 可信计算中心状态管理（Zustand）
 * selectedTask / dagNodes / dagEdges / sandboxStatus
 */
import { create } from 'zustand';
import type { ComputeTask } from '@/types/api';
import type { DagNodeUI, DagEdgeUI, SandboxRunStatus } from '@/types/compute';

interface ComputeState {
  /** 当前选中的计算任务 */
  selectedTask: ComputeTask | null;
  /** DAG 节点列表 */
  dagNodes: DagNodeUI[];
  /** DAG 连线列表 */
  dagEdges: DagEdgeUI[];
  /** 沙箱运行状态 */
  sandboxStatus: SandboxRunStatus;

  /** 设置选中任务 */
  setSelectedTask: (task: ComputeTask | null) => void;
  /** 设置全部 DAG 节点 */
  setDagNodes: (nodes: DagNodeUI[]) => void;
  /** 设置全部 DAG 连线 */
  setDagEdges: (edges: DagEdgeUI[]) => void;
  /** 添加单个 DAG 节点 */
  addDagNode: (node: DagNodeUI) => void;
  /** 移除指定 DAG 节点（同时移除相关连线） */
  removeDagNode: (id: string) => void;
  /** 设置沙箱状态 */
  setSandboxStatus: (status: SandboxRunStatus) => void;
}

export const useComputeStore = create<ComputeState>()((set) => ({
  selectedTask: null,
  dagNodes: [],
  dagEdges: [],
  sandboxStatus: 'idle',

  setSelectedTask: (task: ComputeTask | null) => {
    set({ selectedTask: task });
  },

  setDagNodes: (nodes: DagNodeUI[]) => {
    set({ dagNodes: nodes });
  },

  setDagEdges: (edges: DagEdgeUI[]) => {
    set({ dagEdges: edges });
  },

  addDagNode: (node: DagNodeUI) => {
    set((state) => ({
      dagNodes: [...state.dagNodes, node],
    }));
  },

  removeDagNode: (id: string) => {
    set((state) => ({
      dagNodes: state.dagNodes.filter((n) => n.id !== id),
      dagEdges: state.dagEdges.filter((e) => e.source !== id && e.target !== id),
    }));
  },

  setSandboxStatus: (status: SandboxRunStatus) => {
    set({ sandboxStatus: status });
  },
}));
