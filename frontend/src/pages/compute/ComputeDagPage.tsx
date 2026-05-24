/**
 * DAG 画布页面
 * 使用 ReactFlow 绘制 DAG 编排画布
 * 左侧算子面板 + 中间画布 + 右侧属性面板
 */
import React, { useState, useCallback, useMemo, useRef, DragEvent } from 'react';
import { Button, Input, Tooltip, MessagePlugin, Tag, Divider, Textarea } from 'tdesign-react';
import {
  SaveIcon, PlayIcon, FolderOpenIcon, DeleteIcon, RefreshIcon,
  ZoomInIcon, ZoomOutIcon, CenterFocusStrongIcon,
} from 'tdesign-icons-react';
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type Connection,
  type ReactFlowInstance,
  BackgroundVariant,
  MarkerType,
  Panel,
  type XYPosition,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDags, createDag, updateDag, executeDag } from '@/api/compute';
import type { DagDefinition, DagNode as DagNodeType, DagEdge as DagEdgeType } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

/** 算子定义 */
interface OperatorDef {
  type: string;
  label: string;
  color: string;
  icon: string;
}

/** 可用算子列表 */
const OPERATORS: OperatorDef[] = [
  { type: 'MPC', label: 'MPC 计算', color: '#2196f3', icon: '🔐' },
  { type: 'FL', label: '联邦学习', color: '#9c27b0', icon: '🧠' },
  { type: 'TEE', label: 'TEE 执行', color: '#4caf50', icon: '🛡️' },
  { type: 'HE', label: '同态加密', color: '#ff9800', icon: '🔑' },
  { type: 'DP', label: '差分隐私', color: '#00bcd4', icon: '🔇' },
  { type: 'DATASOURCE', label: '数据源', color: '#607d8b', icon: '💾' },
  { type: 'OUTPUT', label: '输出节点', color: '#795548', icon: '📤' },
];

/** 自定义 DAG 节点组件 */
const DagCustomNode: React.FC<{
  data: { label: string; nodeType: string; config: Record<string, unknown> };
  selected?: boolean;
}> = ({ data, selected }) => {
  const opDef = OPERATORS.find((o) => o.type === data.nodeType);
  const bgColor = opDef?.color ?? '#9e9e9e';
  return (
    <div
      className="px-2 py-1.5 rounded-lg bg-white border-2 transition-shadow min-w-[140px]"
      style={{
        borderColor: selected ? '#1565c0' : bgColor,
        boxShadow: selected ? '0 4px 12px rgba(0,0,0,0.15)' : '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      <div className="flex flex-col items-center gap-0.5">
        <span className="text-xl">{opDef?.icon ?? '⚙️'}</span>
        <p className="text-xs font-bold truncate">{data.label}</p>
        <Tag
          style={{ backgroundColor: bgColor, color: '#fff', height: 20, fontSize: '0.65rem' }}
        >
          {data.nodeType}
        </Tag>
      </div>
    </div>
  );
};

const nodeTypes = { dagCustom: DagCustomNode } as any;

let nodeIdCounter = 0;
const getNextNodeId = () => `node-${++nodeIdCounter}`;

const ComputeDagPage: React.FC = () => {
  const queryClient = useQueryClient();
  const reactFlowRef = useRef<ReactFlowInstance | null>(null);

  // ===== DAG 列表查询 =====
  const { data: dagListData, isLoading } = useQuery({
    queryKey: ['dags'],
    queryFn: () => listDags({ page: 1, page_size: 50 }),
  });

  // ===== 画布状态 =====
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [dagName, setDagName] = useState<string>('');
  const [dagId, setDagId] = useState<string | null>(null);

  // 属性面板
  const [nodeLabel, setNodeLabel] = useState<string>('');
  const [nodeConfig, setNodeConfig] = useState<string>('{}');

  // 加载弹窗
  const [loadDialogOpen, setLoadDialogOpen] = useState<boolean>(false);

  // ===== Mutations =====
  const saveMut = useMutation({
    mutationFn: (data: Partial<DagDefinition>) => {
      if (dagId) return updateDag(dagId, data);
      return createDag(data);
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['dags'] });
      if (!dagId && res.data?.id) setDagId(res.data.id);
      MessagePlugin.success('DAG 保存成功');
    },
    onError: () => {
      MessagePlugin.error('DAG 保存失败');
    },
  });

  const executeMut = useMutation({
    mutationFn: (id: string) => executeDag(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dags'] });
      MessagePlugin.success('DAG 执行已启动');
    },
    onError: () => {
      MessagePlugin.error('DAG 执行失败');
    },
  });

  // ===== 连接边 =====
  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge: Edge = {
        id: `e-${connection.source}-${connection.target}`,
        source: connection.source ?? '',
        target: connection.target ?? '',
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#888', strokeWidth: 2 },
      };
      setEdges((prev) => addEdge(newEdge, prev));
    },
    [setEdges],
  );

  // ===== 节点选择 =====
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    setNodeLabel(node.data.label ?? '');
    setNodeConfig(JSON.stringify(node.data.config ?? {}, null, 2));
  }, []);

  // ===== 属性面板更新 =====
  const applyPropertyChange = useCallback(() => {
    if (!selectedNode) return;
    let config: Record<string, unknown> = {};
    try {
      config = JSON.parse(nodeConfig || '{}');
    } catch {
      config = {};
    }
    setNodes((prev) =>
      prev.map((n) =>
        n.id === selectedNode.id
          ? { ...n, data: { ...n.data, label: nodeLabel, config } }
          : n,
      ),
    );
    setSelectedNode((prev) =>
      prev ? { ...prev, data: { ...prev.data, label: nodeLabel, config } } : null,
    );
  }, [selectedNode, nodeLabel, nodeConfig, setNodes]);

  // ===== 拖拽添加节点 =====
  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData('application/reactflow-type');
      if (!nodeType) return;

      const position = reactFlowRef.current?.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      if (!position) return;

      const opDef = OPERATORS.find((o) => o.type === nodeType);
      const newNode: Node = {
        id: getNextNodeId(),
        type: 'dagCustom',
        position: position as XYPosition,
        data: {
          label: opDef?.label ?? nodeType,
          nodeType,
          config: {},
        },
      };
      setNodes((prev) => [...prev, newNode]);
    },
    [setNodes],
  );

  // ===== 保存 DAG =====
  const handleSave = useCallback(() => {
    const dagNodes: DagNodeType[] = nodes.map((n) => ({
      id: n.id,
      name: n.data.label ?? '',
      task_type: n.data.nodeType ?? '',
      config: n.data.config ?? {},
    }));
    const dagEdges: DagEdgeType[] = edges.map((e) => ({
      source: e.source,
      target: e.target,
      data_type: 'default',
    }));
    saveMut.mutate({
      name: dagName || '未命名 DAG',
      nodes: dagNodes,
      edges: dagEdges,
    });
  }, [nodes, edges, dagName, saveMut]);

  // ===== 加载 DAG =====
  const handleLoadDag = useCallback((dag: DagDefinition) => {
    setDagId(dag.id);
    setDagName(dag.name);
    const loadedNodes: Node[] = dag.nodes.map((n, idx) => ({
      id: n.id,
      type: 'dagCustom',
      position: { x: 100 + idx * 250, y: 100 + (idx % 3) * 150 },
      data: { label: n.name, nodeType: n.task_type, config: n.config },
    }));
    const loadedEdges: Edge[] = dag.edges.map((e) => ({
      id: `e-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: '#888', strokeWidth: 2 },
    }));
    setNodes(loadedNodes);
    setEdges(loadedEdges);
    setLoadDialogOpen(false);
  }, [setNodes, setEdges]);

  // ===== 删除选中节点 =====
  const handleDeleteNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNode.id));
    setEdges((prev) => prev.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
    setSelectedNode(null);
  }, [selectedNode, setNodes, setEdges]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: 'DAG 画布' }],
    [],
  );

  const dagList: DagDefinition[] = dagListData?.data?.items ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="DAG 画布"
        subtitle="可视化编排可信计算 DAG 工作流"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '保存', icon: <SaveIcon />, onClick: handleSave, variant: 'contained' },
          {
            label: '执行',
            icon: <PlayIcon />,
            onClick: () => dagId && executeMut.mutate(dagId),
            variant: 'contained',
            color: 'success' as const,
            disabled: !dagId,
          },
          { label: '加载', icon: <FolderOpenIcon />, onClick: () => setLoadDialogOpen(true), variant: 'outlined' },
        ]}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['dags'] }),
            tooltip: '刷新',
          },
        ]}
      />

      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* 左侧算子面板 */}
        <div className="w-[220px] p-4 overflow-auto flex-shrink-0 rounded-xl bg-white border border-gray-200">
          <p className="text-xs font-bold mb-2">算子面板</p>
          <Divider />
          <div className="flex flex-col gap-2 mt-2">
            {OPERATORS.map((op) => (
              <div
                key={op.type}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/reactflow-type', op.type);
                  e.dataTransfer.effectAllowed = 'move';
                }}
                className="p-3 cursor-grab rounded-md border-l-4 hover:bg-gray-50 active:cursor-grabbing transition-colors"
                style={{ borderLeftColor: op.color }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{op.icon}</span>
                  <span className="text-sm font-medium">{op.label}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 中间画布 */}
        <div className="flex-1 overflow-hidden rounded-xl bg-white border border-gray-200">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onInit={(instance) => { reactFlowRef.current = instance; }}
            onDragOver={onDragOver}
            onDrop={onDrop}
            nodeTypes={nodeTypes}
            fitView
            deleteKeyCode="Delete"
            minZoom={0.2}
            maxZoom={2}
          >
            <Controls showInteractive={false} />
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
            <Panel position="top-left">
              <Input
                label="DAG 名称"
                value={dagName}
                onChange={setDagName}
                style={{ width: 200, backgroundColor: '#fff', borderRadius: 4 }}
              />
            </Panel>
            <Panel position="top-right">
              <div className="flex gap-1">
                <Tooltip content="放大">
                  <Button variant="text" icon={<ZoomInIcon />} onClick={() => reactFlowRef.current?.zoomIn()} />
                </Tooltip>
                <Tooltip content="缩小">
                  <Button variant="text" icon={<ZoomOutIcon />} onClick={() => reactFlowRef.current?.zoomOut()} />
                </Tooltip>
                <Tooltip content="居中">
                  <Button variant="text" icon={<CenterFocusStrongIcon />} onClick={() => reactFlowRef.current?.fitView({ padding: 0.2 })} />
                </Tooltip>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* 右侧属性面板 */}
        <div className="w-[280px] p-4 overflow-auto flex-shrink-0 rounded-xl bg-white border border-gray-200">
          <p className="text-xs font-bold mb-2">属性面板</p>
          <Divider />
          {selectedNode ? (
            <div className="flex flex-col gap-4 mt-3">
              <div>
                <p className="text-xs text-gray-500 mb-1">节点类型</p>
                <Tag
                  style={{
                    backgroundColor: OPERATORS.find((o) => o.type === selectedNode.data.nodeType)?.color ?? '#9e9e9e',
                    color: '#fff',
                  }}
                >
                  {selectedNode.data.nodeType}
                </Tag>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">节点名称</p>
                <Input
                  value={nodeLabel}
                  onChange={setNodeLabel}
                />
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">参数配置 (JSON)</p>
                <Textarea
                  rows={6}
                  value={nodeConfig}
                  onChange={setNodeConfig}
                  placeholder='{"key": "value"}'
                  style={{ fontFamily: 'monospace' }}
                />
              </div>
              <div className="flex gap-2">
                <Button theme="primary" onClick={applyPropertyChange} style={{ flex: 1 }}>
                  应用更改
                </Button>
                <Button theme="danger" variant="text" icon={<DeleteIcon />} onClick={handleDeleteNode} />
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400 mt-3">点击画布中的节点查看和编辑属性</p>
          )}
        </div>
      </div>

      {/* 加载 DAG 弹窗 */}
      {loadDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setLoadDialogOpen(false)} />
          <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold">加载已有 DAG</h3>
            </div>
            <div className="px-6 py-4 max-h-[400px] overflow-auto">
              {dagList.length === 0 ? (
                <p className="text-sm text-gray-400">暂无可加载的 DAG</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {dagList.map((dag) => (
                    <div
                      key={dag.id}
                      className="p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => handleLoadDag(dag)}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-sm font-semibold">{dag.name}</p>
                          <p className="text-xs text-gray-400">
                            节点: {dag.nodes.length} | 边: {dag.edges.length}
                          </p>
                        </div>
                        <StatusTag status={dag.status} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end">
              <Button variant="outline" onClick={() => setLoadDialogOpen(false)}>取消</Button>
            </div>
          </div>
        </div>
      )}

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default ComputeDagPage;
