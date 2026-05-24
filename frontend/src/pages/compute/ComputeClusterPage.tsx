/**
 * 计算集群管理页面
 * 集群节点列表、状态监控、节点注册、任务调度
 */
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Button, Input, Select, Tag, Tooltip, Progress, MessagePlugin } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, DeleteIcon, ServerIcon, CpuIcon, CloudIcon,
  CheckCircleFilledIcon, CloseCircleFilledIcon, InfoCircleFilledIcon,
  ToolsIcon, DashboardIcon, CloseIcon, SearchIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getClusterNodes, getClusterStatus, registerNode, deleteNode,
} from '@/api/compute';
import type { ClusterNode, ClusterStatus, RegisterNodeRequest } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import MetricsCard from '@/components/common/MetricsCard';
import LoadingOverlay from '@/components/LoadingOverlay';
import ConfirmDialog from '@/components/ConfirmDialog';
import FilterBar from '@/components/common/FilterBar';
import type { FilterField } from '@/components/common/FilterBar';
import ChartCard from '@/components/common/ChartCard';
import { getWebSocket } from '@/api/websocket';

/** 节点类型选项 */
const NODE_TYPE_OPTIONS = [
  { value: 'cpu', label: 'CPU 计算节点' },
  { value: 'gpu', label: 'GPU 计算节点' },
  { value: 'tee', label: 'TEE 可信节点' },
  { value: 'fpga', label: 'FPGA 加速节点' },
];

/** 状态选项 */
const STATUS_OPTIONS = [
  { value: 'online', label: '在线' },
  { value: 'offline', label: '离线' },
  { value: 'busy', label: '忙碌' },
  { value: 'maintenance', label: '维护中' },
];

/** 节点状态图标 */
const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  switch (status) {
    case 'online': return <CheckCircleFilledIcon style={{ color: '#4caf50', fontSize: 18 }} />;
    case 'offline': return <CloseCircleFilledIcon style={{ color: '#9e9e9e', fontSize: 18 }} />;
    case 'busy': return <InfoCircleFilledIcon style={{ color: '#ff9800', fontSize: 18 }} />;
    case 'maintenance': return <ToolsIcon style={{ color: '#2196f3', fontSize: 18 }} />;
    default: return <CloseCircleFilledIcon style={{ color: '#9e9e9e', fontSize: 18 }} />;
  }
};

/** 节点类型标签颜色 */
const NODE_TYPE_TAG_COLOR: Record<string, string> = {
  cpu: '#1565c0', gpu: '#7b1fa2', tee: '#2e7d32', fpga: '#e65100',
};

const ComputeClusterPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态 =====
  const [keyword, setKeyword] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  // 注册弹窗
  const [registerOpen, setRegisterOpen] = useState(false);
  const [registerForm, setRegisterForm] = useState<RegisterNodeRequest>({
    name: '', host: '', port: 8080, node_type: 'cpu',
    cpu_cores: 8, gpu_count: 0, gpu_model: '',
    memory_total_gb: 32, max_tasks: 4, tags: [],
  });

  // 节点详情
  const [selectedNode, setSelectedNode] = useState<ClusterNode | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // 心跳状态
  const [heartbeatMap, setHeartbeatMap] = useState<Record<string, string>>({});

  // ===== WebSocket 心跳监听 =====
  useEffect(() => {
    const ws = getWebSocket();
    const unsub = ws.on('cluster_heartbeat', (data: unknown) => {
      const payload = data as { node_id: string; timestamp: string };
      if (payload?.node_id) {
        setHeartbeatMap((prev) => ({ ...prev, [payload.node_id]: payload.timestamp }));
      }
    });
    return () => { unsub(); };
  }, []);

  // ===== 数据查询 =====
  const { data: nodesData, isLoading: nodesLoading } = useQuery({
    queryKey: ['clusterNodes', page, pageSize, filterStatus, filterType],
    queryFn: () => getClusterNodes({
      page: page + 1, page_size: pageSize,
      status: filterStatus || undefined,
      node_type: filterType || undefined,
    }),
  });

  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ['clusterStatus'],
    queryFn: () => getClusterStatus(),
  });

  const nodes: ClusterNode[] = nodesData?.data?.items ?? [];
  const total: number = nodesData?.data?.total ?? 0;
  const clusterStatus: ClusterStatus | undefined = statusData?.data;

  // ===== Mutations =====
  const registerMut = useMutation({
    mutationFn: (data: RegisterNodeRequest) => registerNode(data),
    onSuccess: () => {
      MessagePlugin.success('节点注册成功');
      queryClient.invalidateQueries({ queryKey: ['clusterNodes'] });
      queryClient.invalidateQueries({ queryKey: ['clusterStatus'] });
      setRegisterOpen(false);
      resetRegisterForm();
    },
    onError: () => { MessagePlugin.error('节点注册失败'); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteNode(id),
    onSuccess: () => {
      MessagePlugin.success('节点删除成功');
      queryClient.invalidateQueries({ queryKey: ['clusterNodes'] });
      queryClient.invalidateQueries({ queryKey: ['clusterStatus'] });
    },
    onError: () => { MessagePlugin.error('节点删除失败'); },
  });

  // ===== 辅助函数 =====
  const resetRegisterForm = () => {
    setRegisterForm({
      name: '', host: '', port: 8080, node_type: 'cpu',
      cpu_cores: 8, gpu_count: 0, gpu_model: '',
      memory_total_gb: 32, max_tasks: 4, tags: [],
    });
  };

  const handleRegister = () => { registerMut.mutate(registerForm); };

  const handleViewDetail = (node: ClusterNode) => {
    setSelectedNode(node);
    setDetailOpen(true);
  };

  const handleDelete = (id: string) => { setDeleteTarget(id); };

  // ===== 过滤 =====
  const filteredNodes = useMemo(() => {
    if (!keyword.trim()) return nodes;
    const kw = keyword.toLowerCase();
    return nodes.filter((n) =>
      n.name.toLowerCase().includes(kw) ||
      n.host.toLowerCase().includes(kw) ||
      n.id.toLowerCase().includes(kw),
    );
  }, [nodes, keyword]);

  // ===== 筛选字段 =====
  const filterFields: FilterField[] = useMemo(() => [
    { name: 'keyword', type: 'text', placeholder: '搜索节点名称/主机', width: 200 },
    {
      name: 'status', type: 'select', placeholder: '状态', width: 140,
      options: [{ value: '', label: '全部' }, ...STATUS_OPTIONS],
    },
    {
      name: 'type', type: 'select', placeholder: '节点类型', width: 160,
      options: [{ value: '', label: '全部' }, ...NODE_TYPE_OPTIONS],
    },
  ], []);

  const filterValues = useMemo(() => ({ keyword, status: filterStatus, type: filterType }), [keyword, filterStatus, filterType]);

  const handleFilterChange = (name: string, value: string) => {
    if (name === 'keyword') setKeyword(value);
    if (name === 'status') { setFilterStatus(value); setPage(0); }
    if (name === 'type') { setFilterType(value); setPage(0); }
  };

  // ===== ECharts 图表配置 =====
  const utilizationChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['CPU 使用率', 'GPU 使用率', '内存使用率'], top: 5 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: nodes.slice(0, 10).map((n) => n.name),
      axisLabel: { rotate: 30, fontSize: 11 },
    },
    yAxis: { type: 'value' as const, max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      { name: 'CPU 使用率', type: 'bar', data: nodes.slice(0, 10).map((n) => n.cpu_usage_percent), itemStyle: { color: '#667eea', borderRadius: [4, 4, 0, 0] } },
      { name: 'GPU 使用率', type: 'bar', data: nodes.slice(0, 10).map((n) => n.gpu_usage_percent), itemStyle: { color: '#764ba2', borderRadius: [4, 4, 0, 0] } },
      { name: '内存使用率', type: 'bar', data: nodes.slice(0, 10).map((n) => (n.memory_used_gb / n.memory_total_gb) * 100), itemStyle: { color: '#43e97b', borderRadius: [4, 4, 0, 0] } },
    ],
  }), [nodes]);

  const statusPieOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, right: 10, top: 20 },
    series: [{
      name: '节点状态', type: 'pie', radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: [
        { value: clusterStatus?.online_nodes ?? 0, name: '在线', itemStyle: { color: '#4caf50' } },
        { value: clusterStatus?.offline_nodes ?? 0, name: '离线', itemStyle: { color: '#9e9e9e' } },
        { value: clusterStatus?.busy_nodes ?? 0, name: '忙碌', itemStyle: { color: '#ff9800' } },
        { value: clusterStatus?.maintenance_nodes ?? 0, name: '维护中', itemStyle: { color: '#2196f3' } },
      ],
    }],
  }), [clusterStatus]);

  // ===== 面包屑与操作 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '计算集群' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{
      label: '注册节点',
      icon: <AddIcon />,
      onClick: () => setRegisterOpen(true),
      variant: 'contained',
    }],
    [],
  );

  // ===== 心跳状态判断 =====
  const getHeartbeatStatus = (node: ClusterNode): 'fresh' | 'stale' | 'dead' => {
    const lastHb = heartbeatMap[node.id] ?? node.last_heartbeat;
    if (!lastHb) return 'dead';
    const diff = Date.now() - new Date(lastHb).getTime();
    if (diff < 60000) return 'fresh';
    if (diff < 300000) return 'stale';
    return 'dead';
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <PageContainer>
      <PageHeader
        title="计算集群"
        subtitle="管理计算集群节点的注册、监控与任务调度"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[{
          icon: <RefreshIcon />,
          onClick: () => {
            queryClient.invalidateQueries({ queryKey: ['clusterNodes'] });
            queryClient.invalidateQueries({ queryKey: ['clusterStatus'] });
          },
          tooltip: '刷新',
        }]}
      />

      {/* 概览统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricsCard title="总节点数" value={clusterStatus?.total_nodes ?? 0} icon={<ServerIcon />} color="primary" trend="up" trendValue={`在线 ${clusterStatus?.online_nodes ?? 0}`} />
        <MetricsCard title="CPU 平均使用率" value={`${(clusterStatus?.avg_cpu_usage ?? 0).toFixed(1)}%`} icon={<CpuIcon />} color={clusterStatus && clusterStatus.avg_cpu_usage > 80 ? 'error' : 'success'} trend={clusterStatus && clusterStatus.avg_cpu_usage > 80 ? 'up' : 'stable'} trendValue={clusterStatus && clusterStatus.avg_cpu_usage > 80 ? '偏高' : '正常'} />
        <MetricsCard title="GPU 平均使用率" value={`${(clusterStatus?.avg_gpu_usage ?? 0).toFixed(1)}%`} icon={<DashboardIcon />} color={clusterStatus && clusterStatus.avg_gpu_usage > 80 ? 'warning' : 'info'} trend={clusterStatus && clusterStatus.avg_gpu_usage > 80 ? 'up' : 'stable'} trendValue={clusterStatus && clusterStatus.avg_gpu_usage > 80 ? '偏高' : '正常'} />
        <MetricsCard title="运行中任务" value={clusterStatus?.total_running_tasks ?? 0} unit={`/ ${clusterStatus?.total_max_tasks ?? 0}`} icon={<CloudIcon />} color="secondary" trend="stable" trendValue={`总容量 ${clusterStatus?.total_cpu_cores ?? 0} 核`} />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="节点资源利用率" option={utilizationChartOption} className="lg:col-span-2" />
        <ChartCard title="节点状态分布" option={statusPieOption} />
      </div>

      {/* 搜索过滤栏 */}
      <FilterBar
        fields={filterFields}
        values={filterValues}
        onChange={handleFilterChange}
      />

      {/* 节点表格 */}
      <div className="rounded-xl bg-white border border-gray-200 flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50 z-10">
              <tr className="border-b border-gray-200">
                <th className="text-left px-4 py-3 font-bold text-gray-600">节点名称</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">主机</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">类型</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">状态</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">CPU</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">GPU</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">内存</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">任务</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">心跳</th>
                <th className="text-center px-4 py-3 font-bold text-gray-600 w-[120px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredNodes.map((row) => {
                const hbStatus = getHeartbeatStatus(row);
                return (
                  <tr key={row.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{row.name}</p>
                      <p className="text-xs text-gray-400">{row.id.slice(0, 8)}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{row.host}:{row.port}</td>
                    <td className="px-4 py-3">
                      <Tag variant="outline" style={{ borderColor: NODE_TYPE_TAG_COLOR[row.node_type], color: NODE_TYPE_TAG_COLOR[row.node_type] }}>
                        {NODE_TYPE_OPTIONS.find((o) => o.value === row.node_type)?.label ?? row.node_type}
                      </Tag>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <StatusIcon status={row.status} />
                        <StatusTag status={row.status} showDot={false} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 min-w-[80px]">
                        <Progress theme="line" percentage={row.cpu_usage_percent} style={{ flex: 1 }} color={row.cpu_usage_percent > 80 ? '#f44336' : row.cpu_usage_percent > 60 ? '#ff9800' : '#2196f3'} />
                        <span className="text-xs text-gray-500 w-8">{row.cpu_usage_percent}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {row.gpu_count > 0 ? `${row.gpu_usage_percent}%` : '-'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {row.memory_used_gb}/{row.memory_total_gb}GB
                    </td>
                    <td className="px-4 py-3">
                      <Tag variant="outline" theme={row.running_tasks >= row.max_tasks ? 'danger' : 'default'}>
                        {row.running_tasks}/{row.max_tasks}
                      </Tag>
                    </td>
                    <td className="px-4 py-3">
                      <Tooltip content={hbStatus === 'fresh' ? '正常' : hbStatus === 'stale' ? '延迟' : '超时'}>
                        <span className={`inline-block w-2.5 h-2.5 rounded-full ${hbStatus === 'fresh' ? 'bg-green-500' : hbStatus === 'stale' ? 'bg-orange-500' : 'bg-red-500'}`} />
                      </Tooltip>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Tooltip content="查看详情">
                          <Button variant="text" icon={<SearchIcon />} onClick={() => handleViewDetail(row)} />
                        </Tooltip>
                        <Tooltip content="删除节点">
                          <Button variant="text" theme="danger" icon={<DeleteIcon />} onClick={() => handleDelete(row.id)} />
                        </Tooltip>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredNodes.length === 0 && (
                <tr><td colSpan={10} className="text-center py-12 text-gray-400">暂无节点数据</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {/* 分页 */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 text-sm text-gray-500">
          <span>共 {total} 条</span>
          <div className="flex items-center gap-2">
            <Button variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>上一页</Button>
            <span>{page + 1} / {totalPages || 1}</span>
            <Button variant="outline" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>下一页</Button>
          </div>
        </div>
      </div>

      {/* 注册节点弹窗 */}
      {registerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setRegisterOpen(false)} />
          <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">注册计算节点</h3>
              <Button variant="text" icon={<CloseIcon />} onClick={() => setRegisterOpen(false)} />
            </div>
            <div className="flex-1 overflow-auto px-6 py-4 flex flex-col gap-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">节点名称 *</label>
                <Input value={registerForm.name} onChange={(val) => setRegisterForm({ ...registerForm, name: val })} />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-sm text-gray-600 mb-1">主机地址 *</label>
                  <Input value={registerForm.host} onChange={(val) => setRegisterForm({ ...registerForm, host: val })} />
                </div>
                <div className="w-[120px]">
                  <label className="block text-sm text-gray-600 mb-1">端口</label>
                  <Input type="number" value={String(registerForm.port)} onChange={(val) => setRegisterForm({ ...registerForm, port: parseInt(val, 10) || 8080 })} />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">节点类型</label>
                <Select value={registerForm.node_type} onChange={(val) => setRegisterForm({ ...registerForm, node_type: val as RegisterNodeRequest['node_type'] })} options={NODE_TYPE_OPTIONS} style={{ width: '100%' }} />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-sm text-gray-600 mb-1">CPU 核数</label>
                  <Input type="number" value={String(registerForm.cpu_cores)} onChange={(val) => setRegisterForm({ ...registerForm, cpu_cores: parseInt(val, 10) || 1 })} />
                </div>
                <div className="flex-1">
                  <label className="block text-sm text-gray-600 mb-1">内存 (GB)</label>
                  <Input type="number" value={String(registerForm.memory_total_gb)} onChange={(val) => setRegisterForm({ ...registerForm, memory_total_gb: parseInt(val, 10) || 1 })} />
                </div>
              </div>
              {registerForm.node_type === 'gpu' && (
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="block text-sm text-gray-600 mb-1">GPU 数量</label>
                    <Input type="number" value={String(registerForm.gpu_count)} onChange={(val) => setRegisterForm({ ...registerForm, gpu_count: parseInt(val, 10) || 0 })} />
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm text-gray-600 mb-1">GPU 型号</label>
                    <Input value={registerForm.gpu_model ?? ''} onChange={(val) => setRegisterForm({ ...registerForm, gpu_model: val })} />
                  </div>
                </div>
              )}
              <div>
                <label className="block text-sm text-gray-600 mb-1">最大并发任务</label>
                <Input type="number" value={String(registerForm.max_tasks)} onChange={(val) => setRegisterForm({ ...registerForm, max_tasks: parseInt(val, 10) || 1 })} />
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
              <Button variant="outline" onClick={() => setRegisterOpen(false)}>取消</Button>
              <Button theme="primary" onClick={handleRegister} disabled={!registerForm.name || !registerForm.host} loading={registerMut.isPending}>
                {registerMut.isPending ? '注册中...' : '注册'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 节点详情抽屉 */}
      {detailOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setDetailOpen(false)} />
          <div className="relative w-full max-w-[420px] bg-white shadow-2xl flex flex-col overflow-hidden">
            {selectedNode && (
              <>
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold">节点详情</h3>
                  <Button variant="text" icon={<CloseIcon />} onClick={() => setDetailOpen(false)} />
                </div>
                <div className="flex-1 overflow-auto px-6 py-4 flex flex-col gap-4">
                  {/* 基本信息 */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-400 mb-3">基本信息</p>
                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between"><span className="text-sm text-gray-600">名称</span><span className="text-sm font-semibold">{selectedNode.name}</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">主机</span><span className="text-sm">{selectedNode.host}:{selectedNode.port}</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">类型</span><Tag variant="outline">{selectedNode.node_type.toUpperCase()}</Tag></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">状态</span><div className="flex items-center gap-1"><StatusIcon status={selectedNode.status} /><StatusTag status={selectedNode.status} showDot={false} /></div></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">注册时间</span><span className="text-sm">{new Date(selectedNode.registered_at).toLocaleString('zh-CN')}</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">最后心跳</span><span className="text-sm">{new Date(selectedNode.last_heartbeat).toLocaleString('zh-CN')}</span></div>
                    </div>
                  </div>

                  {/* 硬件配置 */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-400 mb-3">硬件配置</p>
                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between"><span className="text-sm text-gray-600">CPU</span><span className="text-sm font-semibold">{selectedNode.cpu_cores} 核</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">GPU</span><span className="text-sm font-semibold">{selectedNode.gpu_count > 0 ? `${selectedNode.gpu_count}x ${selectedNode.gpu_model ?? 'N/A'}` : '无'}</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">内存</span><span className="text-sm font-semibold">{selectedNode.memory_total_gb} GB</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">最大任务</span><span className="text-sm font-semibold">{selectedNode.max_tasks}</span></div>
                    </div>
                  </div>

                  {/* 实时资源 */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-400 mb-3">实时资源</p>
                    <div className="flex flex-col gap-3">
                      {[
                        { label: 'CPU', value: selectedNode.cpu_usage_percent },
                        { label: 'GPU', value: selectedNode.gpu_usage_percent },
                        { label: '内存', value: (selectedNode.memory_used_gb / selectedNode.memory_total_gb) * 100 },
                        { label: '磁盘', value: selectedNode.disk_usage_percent },
                      ].map((item) => (
                        <div key={item.label}>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-gray-600">{item.label}</span>
                            <span className="text-sm font-semibold">{item.value.toFixed(1)}%</span>
                          </div>
                          <Progress theme="line" percentage={item.value} color={item.value > 80 ? '#f44336' : item.value > 60 ? '#ff9800' : '#2196f3'} />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 网络 */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-400 mb-3">网络</p>
                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between"><span className="text-sm text-gray-600">入站流量</span><span className="text-sm font-semibold">{selectedNode.network_in_mbps.toFixed(1)} Mbps</span></div>
                      <div className="flex justify-between"><span className="text-sm text-gray-600">出站流量</span><span className="text-sm font-semibold">{selectedNode.network_out_mbps.toFixed(1)} Mbps</span></div>
                    </div>
                  </div>

                  {/* 标签 */}
                  {selectedNode.tags.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-400 mb-2">标签</p>
                      <div className="flex flex-wrap gap-1">
                        {selectedNode.tags.map((tag) => (
                          <Tag key={tag} variant="outline">{tag}</Tag>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 删除确认 */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除节点"
        message="确认删除该节点？删除后不可恢复。"
        type="danger"
        onConfirm={() => { if (deleteTarget) { deleteMut.mutate(deleteTarget); setDeleteTarget(null); } }}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteMut.isPending}
      />

      <LoadingOverlay open={nodesLoading && nodes.length === 0} />
    </PageContainer>
  );
};

export default ComputeClusterPage;
