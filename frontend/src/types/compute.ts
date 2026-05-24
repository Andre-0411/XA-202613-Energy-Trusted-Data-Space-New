/**
 * 可信计算相关 UI 类型定义
 * 扩展 api.ts 中的基础类型，补充前端 DAG 编辑器所需的布局/可视化字段
 */
import type { DagNode as BaseDagNode, DagEdge as BaseDagEdge } from '@/types/api';

/** DAG 节点（UI 扩展：增加画布坐标与标签） */
export interface DagNodeUI extends BaseDagNode {
  /** 画布坐标 */
  position: { x: number; y: number };
  /** 节点显示标签 */
  label: string;
  /** 节点附加数据（供自定义组件渲染） */
  data: Record<string, unknown>;
}

/** DAG 连线（UI 扩展：增加 id 和可选标签） */
export interface DagEdgeUI extends BaseDagEdge {
  /** 连线唯一标识 */
  id: string;
  /** 连线可选标签 */
  label?: string;
}

/** 沙箱状态枚举 */
export type SandboxRunStatus = 'idle' | 'running' | 'stopped' | 'error';
