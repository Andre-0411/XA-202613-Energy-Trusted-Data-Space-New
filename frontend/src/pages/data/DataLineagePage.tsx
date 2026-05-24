/**
 * 数据血缘页面
 * 使用 ReactFlow 绘制血缘关系图，支持缩放、居中、导出图片
 * 连接数据血缘 API 获取真实血缘数据
 */
import React, { useState, useCallback, useMemo, useRef } from 'react';
import { Button, Drawer, Input, Select, Tag, Tooltip } from 'tdesign-react';
import {
  RefreshIcon, FolderOpenIcon, CheckCircleIcon, TimeIcon,
  TrendingUpIcon, ZoomInIcon, ZoomOutIcon, FullscreenIcon,
  ScreenshotIcon, CloseCircleIcon,
} from 'tdesign-icons-react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type ReactFlowInstance,
  BackgroundVariant,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useQuery } from '@tanstack/react-query';
import { getLineage as getLineageLegacy } from '@/api/data';
import { getDataLineage } from '@/api/dataCatalog';
import type { DataLineageGraph, DataLineageNode, DataLineageEdge } from '@/api/dataCatalog';
import type { DataSource, DataAsset } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

/** 节点类型颜色 */
const NODE_COLORS: Record<string, string> = {
  datasource: '#2196f3',
  asset: '#4caf50',
  task: '#ff9800',
  default: '#9e9e9e',
};

/** 自定义节点组件 */
const CustomNode: React.FC<{
  data: { label: string; nodeType: string; status: string; description: string };
}> = ({ data }) => {
  const bgColor = NODE_COLORS[data.nodeType] ?? NODE_COLORS.default;
  return (
    <div
      className="px-3 py-2 rounded-lg bg-white border-2 min-w-[160px] shadow-md"
      style={{ borderColor: bgColor }}
    >
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: bgColor }}
          />
          <span className="text-sm font-bold truncate">
            {data.label}
          </span>
        </div>
        <span className="text-xs text-gray-500">
          类型: {data.nodeType}
        </span>
        <StatusTag status={data.status} showDot={false} />
      </div>
    </div>
  );
};

/** 节点类型映射 */
const nodeTypes = { custom: CustomNode };

/** 示例资产ID（5大发电企业相关） */
const SAMPLE_ASSETS = [
  { id: 'asset-hn-001', name: '华能风电数据集' },
  { id: 'asset-dt-002', name: '大唐火电数据集' },
  { id: 'asset-hd-003', name: '华电水电数据集' },
  { id: 'asset-gjny-004', name: '国家能源光伏数据集' },
  { id: 'asset-gdp-005', name: '国电投综合能源' },
];

/** 默认血缘数据（API无数据时展示） */
const DEFAULT_NODES: Node[] = [
  { id: 'ds-1', type: 'custom', position: { x: 50, y: 100 }, data: { label: '华能SCADA', nodeType: 'datasource', status: 'active', description: '华能风电SCADA实时数据' } },
  { id: 'ds-2', type: 'custom', position: { x: 50, y: 300 }, data: { label: '大唐DCS', nodeType: 'datasource', status: 'active', description: '大唐火电DCS系统' } },
  { id: 'ds-3', type: 'custom', position: { x: 50, y: 500 }, data: { label: 'MQTT采集器', nodeType: 'datasource', status: 'active', description: 'MQTT实时采集数据' } },
  { id: 'asset-1', type: 'custom', position: { x: 400, y: 100 }, data: { label: '华能风电资产', nodeType: 'asset', status: 'published', description: '华能风电数据资产' } },
  { id: 'asset-2', type: 'custom', position: { x: 400, y: 300 }, data: { label: '大唐火电资产', nodeType: 'asset', status: 'published', description: '大唐火电数据资产' } },
  { id: 'asset-3', type: 'custom', position: { x: 400, y: 500 }, data: { label: '实时采集资产', nodeType: 'asset', status: 'draft', description: 'MQTT采集实时数据' } },
  { id: 'task-1', type: 'custom', position: { x: 750, y: 200 }, data: { label: 'MPC 联合统计', nodeType: 'task', status: 'completed', description: '多企业隐私统计' } },
  { id: 'task-2', type: 'custom', position: { x: 750, y: 450 }, data: { label: '数据质量评估', nodeType: 'task', status: 'running', description: '五维质量评估任务' } },
];

const DEFAULT_EDGES: Edge[] = [
  { id: 'e-ds1-a1', source: 'ds-1', target: 'asset-1', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#2196f3', strokeWidth: 2 } },
  { id: 'e-ds2-a2', source: 'ds-2', target: 'asset-2', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#2196f3', strokeWidth: 2 } },
  { id: 'e-ds3-a3', source: 'ds-3', target: 'asset-3', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#2196f3', strokeWidth: 2 } },
  { id: 'e-a1-t1', source: 'asset-1', target: 'task-1', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ff9800', strokeWidth: 2 } },
  { id: 'e-a2-t1', source: 'asset-2', target: 'task-1', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ff9800', strokeWidth: 2 } },
  { id: 'e-a2-t2', source: 'asset-2', target: 'task-2', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ff9800', strokeWidth: 2 } },
  { id: 'e-a3-t2', source: 'asset-3', target: 'task-2', markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ff9800', strokeWidth: 2 } },
];

/** 将API返回的血缘图转换为ReactFlow格式 */
function convertLineageToReactFlow(graph: DataLineageGraph): { rfNodes: Node[]; rfEdges: Edge[] } {
  const rfNodes: Node[] = graph.nodes.map((n: DataLineageNode, idx: number) => ({
    id: n.id,
    type: 'custom',
    position: {
      x: n.type === 'datasource' ? 50 : n.type === 'asset' ? 400 : 750,
      y: 100 + (idx % 5) * 150,
    },
    data: {
      label: n.name,
      nodeType: n.type,
      status: (n.metadata?.status as string) || 'active',
      description: (n.metadata?.description as string) || '',
    },
  }));

  const rfEdges: Edge[] = graph.edges.map((e: DataLineageEdge, idx: number) => ({
    id: `e-${e.source}-${e.target}-${idx}`,
    source: e.source,
    target: e.target,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: {
      stroke: e.label?.includes('transform') ? '#ff9800' : '#2196f3',
      strokeWidth: 2,
    },
    label: e.label || undefined,
  }));

  return { rfNodes, rfEdges };
}

const DataLineagePage: React.FC = () => {
  const reactFlowRef = useRef<ReactFlowInstance | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string>(SAMPLE_ASSETS[0].id);

  // ===== 数据查询 - 尝试从API获取 =====
  const { data: lineageData, isLoading, refetch } = useQuery({
    queryKey: ['dataLineage', selectedAssetId],
    queryFn: async () => {
      try {
        const res = await getDataLineage(selectedAssetId);
        if (res?.data?.nodes?.length > 0) {
          return convertLineageToReactFlow(res.data);
        }
      } catch (err) {
        console.warn('Enhanced lineage API failed, using default', err);
      }
      // 使用默认数据
      return { rfNodes: DEFAULT_NODES, rfEdges: DEFAULT_EDGES };
    },
  });

  const initialNodes = lineageData?.rfNodes ?? DEFAULT_NODES;
  const initialEdges = lineageData?.rfEdges ?? DEFAULT_EDGES;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalNodes: initialNodes.length,
    totalEdges: initialEdges.length,
    activeLineages: initialNodes.filter((n: Node) => n.data.status === 'active').length,
    todayTraces: 45,
  }), [initialNodes, initialEdges]);

  // ===== ECharts 配置 =====
  const lineageTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增节点', '新增关系'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增节点', type: 'bar', data: [12, 18, 15, 22, 19, 25, 20], itemStyle: { color: '#2196f3' } },
      { name: '新增关系', type: 'line', smooth: true, data: [18, 25, 22, 30, 28, 35, 32], itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  const nodeTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '节点类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 68, name: '数据源', itemStyle: { color: '#2196f3' } },
          { value: 52, name: '数据资产', itemStyle: { color: '#4caf50' } },
          { value: 36, name: '计算任务', itemStyle: { color: '#ff9800' } },
        ],
      },
    ],
  }), []);

  // ===== 状态 =====
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [filterType, setFilterType] = useState<string>('');

  // ===== 节点点击 =====
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    setDrawerOpen(true);
  }, []);

  // ===== 画布操作 =====
  const handleZoomIn = useCallback(() => {
    reactFlowRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    reactFlowRef.current?.zoomOut();
  }, []);

  const handleFitView = useCallback(() => {
    reactFlowRef.current?.fitView({ padding: 0.2 });
  }, []);

  const handleExportImage = useCallback(() => {
    const flowEl = document.querySelector('.react-flow');
    if (!flowEl) return;
    const svgEl = flowEl.querySelector('svg');
    if (svgEl) {
      const svgData = new XMLSerializer().serializeToString(svgEl);
      const blob = new Blob([svgData], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'data-lineage.svg';
      a.click();
      URL.revokeObjectURL(url);
    }
  }, []);

  // ===== 按类型过滤节点 =====
  const handleFilterChange = useCallback((nodeType: string) => {
    setFilterType(nodeType);
    if (!nodeType) {
      setNodes(initialNodes);
      setEdges(initialEdges);
    } else {
      const filteredNodeIds = new Set(
        initialNodes.filter((n: Node) => n.data.nodeType === nodeType).map((n: Node) => n.id),
      );
      const connectedNodeIds = new Set(filteredNodeIds);
      initialEdges.forEach((edge: Edge) => {
        if (filteredNodeIds.has(edge.source) || filteredNodeIds.has(edge.target)) {
          connectedNodeIds.add(edge.source);
          connectedNodeIds.add(edge.target);
        }
      });
      setNodes(initialNodes.filter((n: Node) => connectedNodeIds.has(n.id)));
      setEdges(initialEdges.filter((e: Edge) => connectedNodeIds.has(e.source) && connectedNodeIds.has(e.target)));
    }
  }, [setNodes, setEdges, initialNodes, initialEdges]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据血缘' }],
    [],
  );

  const assetOptions = SAMPLE_ASSETS.map((a) => ({ label: a.name, value: a.id }));
  const filterOptions = [
    { label: '全部', value: '' },
    { label: '数据源', value: 'datasource' },
    { label: '数据资产', value: 'asset' },
    { label: '计算任务', value: 'task' },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="数据血缘"
        subtitle="可视化展示数据源、数据资产、计算任务之间的血缘关系"
        breadcrumbs={breadcrumbs}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => handleFilterChange(filterType),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总节点数" value={stats.totalNodes} icon={<FolderOpenIcon />} gradient="blue" unit="" />
        <StatCard title="总关系数" value={stats.totalEdges} icon={<CheckCircleIcon />} gradient="green" unit="" />
        <StatCard title="活跃血缘" value={stats.activeLineages} icon={<TimeIcon />} gradient="purple" unit="" />
        <StatCard title="今日溯源" value={stats.todayTraces} icon={<TrendingUpIcon />} gradient="orange" unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PageSection title="血缘增长趋势" titleIcon={<TrendingUpIcon />} className="md:col-span-2">
          <ReactECharts option={lineageTrendOption} style={{ height: 300 }} />
        </PageSection>
        <PageSection title="节点类型分布" titleIcon={<FolderOpenIcon />}>
          <ReactECharts option={nodeTypeOption} style={{ height: 300 }} />
        </PageSection>
      </div>

      {/* 工具栏 */}
      <PageSection padding="sm">
        <div className="flex items-center gap-2 flex-wrap">
          <Select
            value={selectedAssetId}
            options={assetOptions}
            onChange={(val) => {
              setSelectedAssetId(String(val));
              setFilterType('');
              refetch();
            }}
            style={{ width: 200 }}
            size="small"
          />
          <Select
            value={filterType}
            options={filterOptions}
            onChange={(val) => handleFilterChange(String(val))}
            style={{ width: 140 }}
            size="small"
          />
          <div className="flex-1" />
          <Tooltip content="刷新">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => { setFilterType(''); refetch(); }}>
              <RefreshIcon />
            </span>
          </Tooltip>
          <Tooltip content="放大">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={handleZoomIn}>
              <ZoomInIcon />
            </span>
          </Tooltip>
          <Tooltip content="缩小">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={handleZoomOut}>
              <ZoomOutIcon />
            </span>
          </Tooltip>
          <Tooltip content="居中适配">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={handleFitView}>
              <FullscreenIcon />
            </span>
          </Tooltip>
          <Tooltip content="导出图片">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={handleExportImage}>
              <ScreenshotIcon />
            </span>
          </Tooltip>
        </div>
      </PageSection>

      {/* 画布 */}
      <PageSection padding="none" className="overflow-hidden" style={{ height: 500 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onInit={(instance) => { reactFlowRef.current = instance; }}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={2}
          attributionPosition="bottom-left"
        >
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={(node) => NODE_COLORS[node.data?.nodeType as string] ?? '#9e9e9e'}
            maskColor="rgba(0,0,0,0.1)"
            style={{ width: 160, height: 120 }}
          />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Panel position="top-right">
            <div className="flex gap-1">
              <Tag>数据源</Tag>
              <Tag>数据资产</Tag>
              <Tag>计算任务</Tag>
            </div>
          </Panel>
        </ReactFlow>
      </PageSection>

      {/* 侧边栏 - 选中节点详情 */}
      <Drawer
        visible={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        header="节点详情"
        size="400px"
        destroyOnClose
      >
        {selectedNode ? (
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">名称</p>
              <p className="text-sm text-gray-700">{selectedNode.data.label}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">类型</p>
              <Tag>{selectedNode.data.nodeType}</Tag>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">状态</p>
              <StatusTag status={selectedNode.data.status} />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">描述</p>
              <p className="text-sm text-gray-600">{selectedNode.data.description || '暂无描述'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">节点 ID</p>
              <p className="text-sm text-gray-600 font-mono">{selectedNode.id}</p>
            </div>
            <hr className="border-gray-200" />
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">上游节点</p>
              <div className="flex flex-wrap gap-1">
                {edges
                  .filter((e) => e.target === selectedNode.id)
                  .map((e) => (
                    <Tag key={e.id}>{nodes.find((n) => n.id === e.source)?.data.label ?? e.source}</Tag>
                  ))}
                {edges.filter((e) => e.target === selectedNode.id).length === 0 && (
                  <span className="text-xs text-gray-400">无上游</span>
                )}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">下游节点</p>
              <div className="flex flex-wrap gap-1">
                {edges
                  .filter((e) => e.source === selectedNode.id)
                  .map((e) => (
                    <Tag key={e.id}>{nodes.find((n) => n.id === e.target)?.data.label ?? e.target}</Tag>
                  ))}
                {edges.filter((e) => e.source === selectedNode.id).length === 0 && (
                  <span className="text-xs text-gray-400">无下游</span>
                )}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-400">请选择节点查看详情</p>
        )}
      </Drawer>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default DataLineagePage;
