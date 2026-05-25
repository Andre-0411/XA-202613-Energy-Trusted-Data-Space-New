/**
 * DAG 编排页面
 * 可视化 DAG 编辑器 + DAG 列表 + 执行监控
 * 使用 ReactFlow 绘制 DAG 画布
 */
import React, { useState, useCallback, useMemo, useRef, DragEvent } from 'react';
import { Button, Input, Tooltip, MessagePlugin, Tag, Divider, Textarea, Select } from 'tdesign-react';
import {
  SaveIcon, PlayIcon, FolderOpenIcon, DeleteIcon, RefreshIcon,
  ZoomInIcon, ZoomOutIcon, CenterFocusStrongIcon,
  AddIcon, ViewModuleIcon, CheckCircleIcon, TimeIcon,
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
  type NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';

// ==================== 类型 ====================

interface OperatorDef {
  type: string;
  label: string;
  color: string;
  icon: string;
}

interface MockDag {
  id: string;
  name: string;
  description: string;
  nodeCount: number;
  edgeCount: number;
  status: string;
  lastRun: string;
  createdBy: string;
}

interface ExecutionLog {
  nodeId: string;
  nodeName: string;
  status: 'pending' | 'running' | 'done' | 'error';
  startTime: string;
  duration: string;
  message: string;
}

// ==================== 常量 ====================

const OPERATORS: OperatorDef[] = [
  { type: 'MPC', label: 'MPC 计算', color: '#2196f3', icon: '🔐' },
  { type: 'FL', label: '联邦学习', color: '#9c27b0', icon: '🧠' },
  { type: 'TEE', label: 'TEE 执行', color: '#4caf50', icon: '🛡️' },
  { type: 'HE', label: '同态加密', color: '#ff9800', icon: '🔑' },
  { type: 'DP', label: '差分隐私', color: '#00bcd4', icon: '🔇' },
  { type: 'DATASOURCE', label: '数据源', color: '#607d8b', icon: '💾' },
  { type: 'OUTPUT', label: '输出节点', color: '#795548', icon: '📤' },
  { type: 'TRANSFORM', label: '数据转换', color: '#e91e63', icon: '🔄' },
  { type: 'FILTER', label: '数据过滤', color: '#3f51b5', icon: '🔍' },
  { type: 'MERGE', label: '数据合并', color: '#009688', icon: '🔗' },
];

const MOCK_DAGS: MockDag[] = [
  { id: 'dag-001', name: '电力负荷联合预测流程', description: '数据采集→联邦学习训练→模型评估→结果输出', nodeCount: 6, edgeCount: 5, status: 'active', lastRun: '2026-05-25 09:30', createdBy: '张工' },
  { id: 'dag-002', name: '碳排放安全审计', description: '数据源→同态加密→安全计算→解密输出', nodeCount: 5, edgeCount: 4, status: 'active', lastRun: '2026-05-24 14:00', createdBy: '王工' },
  { id: 'dag-003', name: '电价协商MPC流程', description: '多方数据→秘密分享→MPC计算→聚合结果', nodeCount: 7, edgeCount: 6, status: 'draft', lastRun: '-', createdBy: '李工' },
  { id: 'dag-004', name: '新能源发电预测', description: '多源数据→差分隐私→联邦学习→预测输出', nodeCount: 8, edgeCount: 7, status: 'active', lastRun: '2026-05-23 09:00', createdBy: '张工' },
  { id: 'dag-005', name: '敏感数据分析TEE流程', description: '加密数据→TEE解密→安全计算→加密输出', nodeCount: 4, edgeCount: 3, status: 'active', lastRun: '2026-05-24 16:00', createdBy: '赵工' },
];

// ==================== 自定义节点 ====================

const DagCustomNode: React.FC<{
  data: { label: string; nodeType: string; config: Record<string, unknown>; execStatus?: string };
  selected?: boolean;
}> = ({ data, selected }) => {
  const opDef = OPERATORS.find((o) => o.type === data.nodeType);
  const bgColor = opDef?.color ?? '#9e9e9e';
  const statusColor = data.execStatus === 'done' ? '#4caf50' : data.execStatus === 'running' ? '#ff9800' : data.execStatus === 'error' ? '#f44336' : bgColor;

  return (
    <div
      className="px-2 py-1.5 rounded-lg bg-white border-2 transition-all duration-300 min-w-[140px]"
      style={{
        borderColor: selected ? '#1565c0' : statusColor,
        boxShadow: selected
          ? '0 4px 12px rgba(0,0,0,0.15)'
          : data.execStatus === 'running'
            ? `0 0 12px ${bgColor}40`
            : '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      <div className="flex flex-col items-center gap-0.5">
        <span className="text-xl">{opDef?.icon ?? '⚙️'}</span>
        <p className="text-xs font-bold truncate">{data.label}</p>
        <div className="flex items-center gap-1">
          <Tag style={{ backgroundColor: bgColor, color: '#fff', height: 18, fontSize: '0.6rem' }}>
            {data.nodeType}
          </Tag>
          {data.execStatus === 'running' && (
            <div className="w-3 h-3 rounded-full border-2 border-orange-400 border-t-transparent animate-spin" />
          )}
          {data.execStatus === 'done' && (
            <CheckCircleIcon style={{ color: '#4caf50', fontSize: 12 }} />
          )}
        </div>
      </div>
    </div>
  );
};

const nodeTypes: NodeTypes = { dagCustom: DagCustomNode };

let nodeIdCounter = 0;
const getNextNodeId = () => `node-${++nodeIdCounter}`;

// ==================== 主组件 ====================

const ComputeDagPage: React.FC = () => {
  const reactFlowRef = useRef<ReactFlowInstance | null>(null);

  // 画布状态
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [dagName, setDagName] = useState('');
  const [dagId, setDagId] = useState<string | null>(null);

  // 属性面板
  const [nodeLabel, setNodeLabel] = useState('');
  const [nodeConfig, setNodeConfig] = useState('{}');

  // UI 状态
  const [showDagList, setShowDagList] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [execLogs, setExecLogs] = useState<ExecutionLog[]>([]);
  const [execStep, setExecStep] = useState(-1);
  const [activeTab, setActiveTab] = useState<'canvas' | 'monitor'>('canvas');

  // 执行计时器
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ===== 连接 =====
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

  // ===== 属性更新 =====
  const applyPropertyChange = useCallback(() => {
    if (!selectedNode) return;
    let config: Record<string, unknown> = {};
    try { config = JSON.parse(nodeConfig || '{}'); } catch { config = {}; }
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

  // ===== 拖拽 =====
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
        data: { label: opDef?.label ?? nodeType, nodeType, config: {} },
      };
      setNodes((prev) => [...prev, newNode]);
    },
    [setNodes],
  );

  // ===== 删除节点 =====
  const handleDeleteNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNode.id));
    setEdges((prev) => prev.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
    setSelectedNode(null);
  }, [selectedNode, setNodes, setEdges]);

  // ===== 加载 DAG =====
  const handleLoadDag = useCallback((dag: MockDag) => {
    setDagId(dag.id);
    setDagName(dag.name);
    setShowDagList(false);

    // 生成示例 DAG
    const dagNodeConfigs: Record<string, { nodes: Array<{ type: string; label: string; x: number; y: number }> }> = {
      'dag-001': {
        nodes: [
          { type: 'DATASOURCE', label: '电力数据源', x: 50, y: 150 },
          { type: 'DATASOURCE', label: '气象数据源', x: 50, y: 300 },
          { type: 'TRANSFORM', label: '数据预处理', x: 280, y: 150 },
          { type: 'FL', label: '联邦学习训练', x: 500, y: 150 },
          { type: 'OUTPUT', label: '模型输出', x: 500, y: 300 },
          { type: 'OUTPUT', label: '预测结果', x: 720, y: 220 },
        ],
      },
      'dag-002': {
        nodes: [
          { type: 'DATASOURCE', label: '排放数据', x: 50, y: 150 },
          { type: 'HE', label: '同态加密', x: 280, y: 150 },
          { type: 'MPC', label: '安全聚合', x: 500, y: 150 },
          { type: 'OUTPUT', label: '审计报告', x: 720, y: 150 },
        ],
      },
    };

    const config = dagNodeConfigs[dag.id] ?? {
      nodes: [
        { type: 'DATASOURCE', label: '数据源', x: 50, y: 150 },
        { type: OPERATORS[0].type, label: OPERATORS[0].label, x: 300, y: 150 },
        { type: 'OUTPUT', label: '输出', x: 550, y: 150 },
      ],
    };

    const loadedNodes: Node[] = config.nodes.map((n, i) => ({
      id: `loaded-${i}`,
      type: 'dagCustom',
      position: { x: n.x, y: n.y },
      data: { label: n.label, nodeType: n.type, config: {} },
    }));

    const loadedEdges: Edge[] = [];
    for (let i = 0; i < loadedNodes.length - 1; i++) {
      // Simple chain, skip some for branching
      if (i === 0 && loadedNodes.length > 3) {
        loadedEdges.push({
          id: `e-loaded-${i}-loaded-${i + 1}`,
          source: `loaded-${i}`,
          target: `loaded-${i + 1}`,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#888', strokeWidth: 2 },
        });
      } else if (i > 0) {
        loadedEdges.push({
          id: `e-loaded-${i}-loaded-${i + 1}`,
          source: `loaded-${i}`,
          target: `loaded-${i + 1}`,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#888', strokeWidth: 2 },
        });
      }
    }

    setNodes(loadedNodes);
    setEdges(loadedEdges);
    setExecLogs([]);
    setExecStep(-1);
    MessagePlugin.success(`已加载: ${dag.name}`);
  }, [setNodes, setEdges]);

  // ===== 执行 DAG =====
  const handleExecute = useCallback(() => {
    if (nodes.length === 0) {
      MessagePlugin.warning('画布为空，请先添加节点');
      return;
    }
    setIsExecuting(true);
    setExecStep(0);
    setExecLogs([]);

    // Reset all node exec status
    setNodes((prev) => prev.map((n) => ({ ...n, data: { ...n.data, execStatus: 'pending' } })));

    const logs: ExecutionLog[] = [];
    let step = 0;

    const runStep = () => {
      if (step >= nodes.length) {
        setIsExecuting(false);
        setExecStep(step);
        setExecLogs([...logs, {
          nodeId: 'system',
          nodeName: '系统',
          status: 'done',
          startTime: new Date().toLocaleTimeString('zh-CN'),
          duration: '-',
          message: 'DAG 执行完成 ✓',
        }]);
        MessagePlugin.success('DAG 执行完成');
        return;
      }

      const node = nodes[step];
      const now = new Date().toLocaleTimeString('zh-CN');

      // Mark current node as running
      setNodes((prev) => prev.map((n) => ({
        ...n,
        data: { ...n.data, execStatus: n.id === node.id ? 'running' : n.data.execStatus },
      })));

      logs.push({
        nodeId: node.id,
        nodeName: node.data.label,
        status: 'running',
        startTime: now,
        duration: '-',
        message: `正在执行 ${node.data.label}...`,
      });
      setExecLogs([...logs]);
      setExecStep(step);

      timerRef.current = setTimeout(() => {
        const duration = `${(Math.random() * 3 + 0.5).toFixed(1)}s`;
        logs[logs.length - 1] = {
          ...logs[logs.length - 1],
          status: 'done',
          duration,
          message: `${node.data.label} 执行完成 (${duration})`,
        };

        setNodes((prev) => prev.map((n) => ({
          ...n,
          data: { ...n.data, execStatus: n.id === node.id ? 'done' : n.data.execStatus },
        })));

        setExecLogs([...logs]);
        step++;
        runStep();
      }, 800 + Math.random() * 1200);
    };

    runStep();
  }, [nodes, setNodes]);

  // ===== 保存 =====
  const handleSave = useCallback(() => {
    MessagePlugin.success(`DAG "${dagName || '未命名'}" 已保存`);
  }, [dagName]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: 'DAG 编排' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="DAG 编排"
        subtitle="可视化编排可信计算 DAG 工作流"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '保存', icon: <SaveIcon />, onClick: handleSave, variant: 'contained' },
          {
            label: isExecuting ? '执行中...' : '执行',
            icon: <PlayIcon />,
            onClick: handleExecute,
            variant: 'contained',
            color: 'success' as const,
            disabled: isExecuting || nodes.length === 0,
          },
          { label: 'DAG 列表', icon: <FolderOpenIcon />, onClick: () => setShowDagList(true), variant: 'outlined' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => { setNodes([]); setEdges([]); setDagName(''); setDagId(null); setExecLogs([]); setExecStep(-1); }, tooltip: '清空画布' },
        ]}
      />

      {/* 标签切换 */}
      <div className="flex gap-2 mb-4">
        <Button
          variant={activeTab === 'canvas' ? 'base' : 'outline'}
          theme={activeTab === 'canvas' ? 'primary' : 'default'}
          onClick={() => setActiveTab('canvas')}
          size="small"
        >
          画布编辑
        </Button>
        <Button
          variant={activeTab === 'monitor' ? 'base' : 'outline'}
          theme={activeTab === 'monitor' ? 'primary' : 'default'}
          onClick={() => setActiveTab('monitor')}
          size="small"
        >
          执行监控
        </Button>
      </div>

      {activeTab === 'canvas' ? (
        <div className="flex gap-4 flex-1 overflow-hidden" style={{ minHeight: 550 }}>
          {/* 左侧算子面板 */}
          <div className="w-[200px] p-3 overflow-auto flex-shrink-0 rounded-xl bg-white border border-gray-200">
            <p className="text-xs font-bold mb-2">算子面板</p>
            <Divider style={{ margin: '8px 0' }} />
            <div className="flex flex-col gap-1.5 mt-2">
              {OPERATORS.map((op) => (
                <div
                  key={op.type}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('application/reactflow-type', op.type);
                    e.dataTransfer.effectAllowed = 'move';
                  }}
                  className="p-2 cursor-grab rounded-md border-l-3 hover:bg-gray-50 active:cursor-grabbing transition-colors"
                  style={{ borderLeftColor: op.color, borderLeftWidth: 3 }}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm">{op.icon}</span>
                    <span className="text-xs font-medium">{op.label}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 中间画布 */}
          <div className="flex-1 overflow-hidden rounded-xl bg-white border border-gray-200" style={{ height: "calc(100vh - 280px)", minHeight: "500px" }}>
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
                <div className="flex items-center gap-2 bg-white rounded-lg shadow-sm border border-gray-200 p-2">
                  <Input
                    label="DAG 名称"
                    value={dagName}
                    onChange={setDagName}
                    style={{ width: 200 }}
                    size="small"
                  />
                  {dagId && <Tag size="small" theme="success">已保存</Tag>}
                </div>
              </Panel>
              <Panel position="top-right">
                <div className="flex gap-1 bg-white rounded-lg shadow-sm border border-gray-200 p-1">
                  <Tooltip content="放大"><Button variant="text" size="small" icon={<ZoomInIcon />} onClick={() => reactFlowRef.current?.zoomIn()} /></Tooltip>
                  <Tooltip content="缩小"><Button variant="text" size="small" icon={<ZoomOutIcon />} onClick={() => reactFlowRef.current?.zoomOut()} /></Tooltip>
                  <Tooltip content="居中"><Button variant="text" size="small" icon={<CenterFocusStrongIcon />} onClick={() => reactFlowRef.current?.fitView({ padding: 0.2 })} /></Tooltip>
                </div>
              </Panel>
            </ReactFlow>
          </div>

          {/* 右侧属性面板 */}
          <div className="w-[260px] p-3 overflow-auto flex-shrink-0 rounded-xl bg-white border border-gray-200">
            <p className="text-xs font-bold mb-2">属性面板</p>
            <Divider style={{ margin: '8px 0' }} />
            {selectedNode ? (
              <div className="flex flex-col gap-3 mt-2">
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
                  <Input value={nodeLabel} onChange={setNodeLabel} size="small" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">参数配置 (JSON)</p>
                  <Textarea
                    rows={5}
                    value={nodeConfig}
                    onChange={setNodeConfig}
                    placeholder='{"key": "value"}'
                    style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                  />
                </div>
                <div className="flex gap-2">
                  <Button theme="primary" size="small" onClick={applyPropertyChange} style={{ flex: 1 }}>应用</Button>
                  <Button theme="danger" variant="text" size="small" icon={<DeleteIcon />} onClick={handleDeleteNode} />
                </div>
                <div className="p-2 rounded bg-gray-50">
                  <p className="text-xs text-gray-400">节点 ID: {selectedNode.id}</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-gray-300">
                <InfoCircleIcon size="32px" style={{ opacity: 0.4 }} />
                <p className="text-xs mt-2">点击画布中的节点查看和编辑属性</p>
              </div>
            )}

            {/* 节点统计 */}
            {nodes.length > 0 && (
              <div className="mt-4 p-2 rounded bg-gray-50">
                <p className="text-xs font-bold mb-1">画布统计</p>
                <p className="text-xs text-gray-500">节点: {nodes.length} | 连线: {edges.length}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* 执行监控 */
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {/* 节点状态 */}
          <div className="md:col-span-4 rounded-xl bg-white border border-gray-200 p-4">
            <p className="text-xs font-bold mb-3">节点执行状态</p>
            {nodes.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">暂无节点</p>
            ) : (
              <div className="flex flex-col gap-2">
                {nodes.map((node, i) => {
                  const status = node.data.execStatus || 'pending';
                  return (
                    <div
                      key={node.id}
                      className="flex items-center gap-2 p-2 rounded-lg"
                      style={{
                        background: status === 'running' ? '#fff3e0' : status === 'done' ? '#e8f5e9' : '#fafafa',
                        borderLeft: `3px solid ${status === 'running' ? '#ff9800' : status === 'done' ? '#4caf50' : '#e0e0e0'}`,
                      }}
                    >
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center text-xs"
                        style={{
                          background: status === 'done' ? '#4caf50' : status === 'running' ? '#ff9800' : '#e0e0e0',
                          color: status !== 'pending' ? '#fff' : '#999',
                        }}
                      >
                        {status === 'done' ? <CheckCircleIcon size="12px" /> : i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate">{node.data.label}</p>
                        <p className="text-xs text-gray-400">{node.data.nodeType}</p>
                      </div>
                      <Tag
                        size="small"
                        theme={status === 'done' ? 'success' : status === 'running' ? 'warning' : 'default'}
                        variant="light"
                      >
                        {status === 'done' ? '完成' : status === 'running' ? '运行中' : '待执行'}
                      </Tag>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 执行日志 */}
          <div className="md:col-span-8 rounded-xl bg-white border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-bold">执行日志</p>
              {isExecuting && (
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
                  <span className="text-xs text-gray-500">执行中...</span>
                </div>
              )}
            </div>
            {execLogs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-300">
                <TimeIcon size="48px" style={{ opacity: 0.3 }} />
                <p className="text-sm mt-2">执行 DAG 后查看日志</p>
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-gray-900 text-green-400 text-xs font-mono" style={{ maxHeight: 400, overflow: 'auto' }}>
                {execLogs.map((log, i) => (
                  <div key={i} className="py-1 flex items-start gap-2">
                    <span className="text-gray-500">[{log.startTime}]</span>
                    <span style={{ color: log.status === 'done' ? '#4caf50' : log.status === 'running' ? '#ff9800' : '#999' }}>
                      {log.message}
                    </span>
                    {log.duration !== '-' && <span className="text-blue-400">({log.duration})</span>}
                  </div>
                ))}
              </div>
            )}

            {/* 执行统计 */}
            {execLogs.length > 0 && (
              <div className="mt-3 grid grid-cols-3 gap-3">
                <div className="text-center p-2 rounded bg-green-50">
                  <p className="text-lg font-bold text-green-600">{execLogs.filter((l) => l.status === 'done').length}</p>
                  <p className="text-xs text-gray-500">已完成</p>
                </div>
                <div className="text-center p-2 rounded bg-orange-50">
                  <p className="text-lg font-bold text-orange-600">{execLogs.filter((l) => l.status === 'running').length}</p>
                  <p className="text-xs text-gray-500">执行中</p>
                </div>
                <div className="text-center p-2 rounded bg-gray-50">
                  <p className="text-lg font-bold text-gray-600">{nodes.length - execLogs.filter((l) => l.status === 'done').length - execLogs.filter((l) => l.status === 'running').length}</p>
                  <p className="text-xs text-gray-500">待执行</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* DAG 列表弹窗 */}
      {showDagList && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowDagList(false)} />
          <div className="relative w-full max-w-lg mx-4 bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-base font-semibold">DAG 列表</h3>
              <Button variant="text" icon={<DeleteIcon />} onClick={() => setShowDagList(false)} />
            </div>
            <div className="px-6 py-4 max-h-[450px] overflow-auto">
              <div className="flex flex-col gap-2">
                {MOCK_DAGS.map((dag) => (
                  <div
                    key={dag.id}
                    className="p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-blue-50 hover:border-blue-200 transition-colors"
                    onClick={() => handleLoadDag(dag)}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-semibold">{dag.name}</p>
                      <StatusTag status={dag.status} />
                    </div>
                    <p className="text-xs text-gray-500 mb-1">{dag.description}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span>节点: {dag.nodeCount}</span>
                      <span>连线: {dag.edgeCount}</span>
                      <span>创建者: {dag.createdBy}</span>
                      {dag.lastRun !== '-' && <span>最后运行: {dag.lastRun}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end">
              <Button variant="outline" onClick={() => setShowDagList(false)}>关闭</Button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default ComputeDagPage;
