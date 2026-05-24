/**
 * 计算任务管理页面
 * 计算任务列表、创建跳转、启动/停止、查看结果
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tooltip, MessagePlugin, Tag, Progress, Select } from 'tdesign-react';
import {
  AddIcon, PlayIcon, StopIcon, RefreshIcon, ViewModuleIcon,
  AssignmentIcon, PlayCircleIcon, CheckCircleIcon, TrendingUpIcon,
} from 'tdesign-icons-react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTasks, startTask, stopTask, getTaskResult } from '@/api/compute';
import type { ComputeTask } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import ChartCard from '@/components/common/ChartCard';
import StatCard from '@/components/common/StatCard';
import ResponsiveFilterBar from '@/components/responsive/ResponsiveFilterBar';

/** 任务类型选项 */
const TASK_TYPE_OPTIONS = [
  { value: 'MPC', label: 'MPC 安全多方计算' },
  { value: 'FL', label: '联邦学习' },
  { value: 'TEE', label: 'TEE 可信执行' },
  { value: 'HE', label: '同态加密' },
  { value: 'DP', label: '差分隐私' },
  { value: 'SANDBOX', label: '沙箱计算' },
];

/** 状态选项 */
const STATUS_OPTIONS = [
  { value: 'created', label: '已创建' },
  { value: 'pending', label: '待处理' },
  { value: 'running', label: '运行中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'stopped', label: '已停止' },
];

const ComputeTasksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // ===== 状态 =====
  const [keyword, setKeyword] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // 结果弹窗
  const [resultData, setResultData] = useState<Record<string, unknown> | null>(null);
  const [resultOpen, setResultOpen] = useState<boolean>(false);

  // ===== ECharts 配置 =====
  const trendChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['任务创建', '任务完成'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'],
    },
    yAxis: { type: 'value' as const, name: '任务数' },
    series: [
      { name: '任务创建', type: 'bar', data: [120, 132, 101, 134, 90, 230, 210], itemStyle: { color: '#667eea' } },
      { name: '任务完成', type: 'bar', data: [90, 102, 81, 114, 70, 200, 190], itemStyle: { color: '#764ba2' } },
    ],
  }), []);

  const typeChartOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, left: 'left', top: 20 },
    series: [
      {
        name: '任务类型',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 35, name: 'MPC 安全多方计算', itemStyle: { color: '#667eea' } },
          { value: 25, name: '联邦学习', itemStyle: { color: '#764ba2' } },
          { value: 20, name: 'TEE 可信执行', itemStyle: { color: '#f093fb' } },
          { value: 15, name: '同态加密', itemStyle: { color: '#4facfe' } },
          { value: 10, name: '差分隐私', itemStyle: { color: '#43e97b' } },
          { value: 8, name: '沙箱计算', itemStyle: { color: '#fa709a' } },
        ],
      },
    ],
  }), []);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['computeTasks', page, pageSize, filterType, filterStatus],
    queryFn: () =>
      listTasks({
        page: page + 1,
        page_size: pageSize,
        task_type: filterType || undefined,
        status: filterStatus || undefined,
      }),
  });

  const items: ComputeTask[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalTasks: total,
    runningTasks: items.filter(t => t.status === 'running').length,
    completedTasks: items.filter(t => t.status === 'completed').length,
    todayTasks: items.filter(t => {
      const today = new Date().toDateString();
      return new Date(t.created_at).toDateString() === today;
    }).length,
  }), [items, total]);

  // ===== Mutations =====
  const startMut = useMutation({
    mutationFn: (id: string) => startTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['computeTasks'] });
      MessagePlugin.success('任务已启动');
    },
    onError: () => {
      MessagePlugin.error('任务启动失败');
    },
  });

  const stopMut = useMutation({
    mutationFn: (id: string) => stopTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['computeTasks'] });
      MessagePlugin.success('任务已停止');
    },
    onError: () => {
      MessagePlugin.error('任务停止失败');
    },
  });

  const resultMut = useMutation({
    mutationFn: (id: string) => getTaskResult(id),
    onSuccess: (res) => {
      setResultData(res.data ?? null);
      setResultOpen(true);
    },
    onError: () => {
      MessagePlugin.error('获取任务结果失败');
    },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '计算任务' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      {
        label: '创建任务',
        icon: <AddIcon />,
        onClick: () => navigate('/dashboard/compute/create'),
        variant: 'contained',
      },
    ],
    [navigate],
  );

  // ===== 过滤 =====
  const filteredItems = useMemo(() => {
    if (!keyword.trim()) return items;
    const kw = keyword.toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(kw) ||
        item.id.toLowerCase().includes(kw),
    );
  }, [items, keyword]);

  /** 任务类型标签颜色 */
  const typeTagColor = (t: string): string => {
    const map: Record<string, string> = {
      MPC: '#2196f3', FL: '#9c27b0', TEE: '#4caf50', HE: '#ff9800', DP: '#00bcd4', SANDBOX: '#f44336',
    };
    return map[t] ?? '#9e9e9e';
  };

  /** 进度值（模拟） */
  const getProgress = (status: string): number => {
    const map: Record<string, number> = {
      created: 0, pending: 10, running: 50, completed: 100, failed: 100, stopped: 0,
    };
    return map[status] ?? 0;
  };

  return (
    <PageContainer>
      <PageHeader
        title="计算任务"
        subtitle="管理可信计算任务的创建、执行与监控"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['computeTasks'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <StatCard title="总任务数" value={stats.totalTasks} unit="个" icon={<AssignmentIcon size="20px" />} gradient="purple" />
        <StatCard title="运行中" value={stats.runningTasks} unit="个" icon={<PlayCircleIcon size="20px" />} gradient="red" />
        <StatCard title="已完成" value={stats.completedTasks} unit="个" icon={<CheckCircleIcon size="20px" />} gradient="green" />
        <StatCard title="今日任务" value={stats.todayTasks} unit="个" icon={<TrendingUpIcon size="20px" />} gradient="cyan" />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <div className="md:col-span-2"><ChartCard title="任务趋势分析" option={trendChartOption} height={300} /></div>
        <ChartCard title="任务类型分布" option={typeChartOption} height={300} />
      </div>

      {/* 搜索过滤栏 */}
      <ResponsiveFilterBar
        showClear={!!keyword || !!filterType || !!filterStatus}
        onClear={() => { setKeyword(''); setFilterType(''); setFilterStatus(''); setPage(0); }}
      >
        <Input
          value={keyword}
          onChange={setKeyword}
          placeholder="搜索任务名称/ID"
          style={{ minWidth: 200 }}
        />
        <Select
          value={filterType}
          onChange={(val) => { setFilterType(val as string); setPage(0); }}
          options={[{ label: '全部类型', value: '' }, ...TASK_TYPE_OPTIONS]}
          style={{ minWidth: 180 }}
          clearable
        />
        <Select
          value={filterStatus}
          onChange={(val) => { setFilterStatus(val as string); setPage(0); }}
          options={[{ label: '全部状态', value: '' }, ...STATUS_OPTIONS]}
          style={{ minWidth: 140 }}
          clearable
        />
      </ResponsiveFilterBar>

      {/* 数据表格 - 移动端卡片视图 / 桌面端表格视图 */}
      <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
        {/* 移动端卡片视图 */}
        <div className="md:hidden flex-1 overflow-auto p-3">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-gray-400">暂无数据</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {filteredItems.map((row) => (
                <div key={row.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm font-semibold">{row.name}</p>
                    <StatusTag status={row.status} />
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <Tag
                      variant="outline"
                      style={{ borderColor: typeTagColor(row.task_type), color: typeTagColor(row.task_type) }}
                    >
                      {TASK_TYPE_OPTIONS.find((o) => o.value === row.task_type)?.label ?? row.task_type}
                    </Tag>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <Progress
                      theme="line"
                      percentage={getProgress(row.status)}
                      style={{ flex: 1 }}
                      color={row.status === 'failed' ? '#f44336' : row.status === 'completed' ? '#4caf50' : '#2196f3'}
                    />
                    <span className="text-xs text-gray-400">{getProgress(row.status)}%</span>
                  </div>
                  <p className="text-xs text-gray-400 mb-2">创建于 {new Date(row.created_at).toLocaleString('zh-CN')}</p>
                  <div className="flex gap-2 justify-end">
                    {row.status === 'created' || row.status === 'stopped' ? (
                      <Button icon={<PlayIcon />} onClick={() => startMut.mutate(row.id)}>启动</Button>
                    ) : row.status === 'running' ? (
                      <Button icon={<StopIcon />} onClick={() => stopMut.mutate(row.id)}>停止</Button>
                    ) : null}
                    <Button variant="outline" icon={<ViewModuleIcon />} onClick={() => resultMut.mutate(row.id)}>结果</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
        <div className="hidden md:flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-bold">任务名</th>
                  <th className="px-4 py-3 text-left font-bold">类型</th>
                  <th className="px-4 py-3 text-left font-bold">状态</th>
                  <th className="px-4 py-3 text-left font-bold">进度</th>
                  <th className="px-4 py-3 text-left font-bold">创建者</th>
                  <th className="px-4 py-3 text-left font-bold">创建时间</th>
                  <th className="px-4 py-3 text-center font-bold w-[200px]">操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((row) => (
                  <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium">{row.name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <Tag
                        variant="outline"
                        style={{ borderColor: typeTagColor(row.task_type), color: typeTagColor(row.task_type) }}
                      >
                        {TASK_TYPE_OPTIONS.find((o) => o.value === row.task_type)?.label ?? row.task_type}
                      </Tag>
                    </td>
                    <td className="px-4 py-3">
                      <StatusTag status={row.status} />
                    </td>
                    <td className="px-4 py-3 min-w-[120px]">
                      <div className="flex items-center gap-2">
                        <Progress
                          theme="line"
                          percentage={getProgress(row.status)}
                          style={{ flex: 1 }}
                          color={row.status === 'failed' ? '#f44336' : row.status === 'completed' ? '#4caf50' : '#2196f3'}
                        />
                        <span className="text-xs text-gray-400">{getProgress(row.status)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">{row.initiator_id.slice(0, 8)}</td>
                    <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex gap-1 justify-center">
                        {row.status === 'created' || row.status === 'stopped' ? (
                          <Tooltip content="启动">
                            <Button variant="text" theme="success" icon={<PlayIcon />} onClick={() => startMut.mutate(row.id)} />
                          </Tooltip>
                        ) : row.status === 'running' ? (
                          <Tooltip content="停止">
                            <Button variant="text" theme="warning" icon={<StopIcon />} onClick={() => stopMut.mutate(row.id)} />
                          </Tooltip>
                        ) : null}
                        <Tooltip content="查看结果">
                          <Button variant="text" theme="primary" icon={<ViewModuleIcon />} onClick={() => resultMut.mutate(row.id)} />
                        </Tooltip>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredItems.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* 分页 */}
        <div className="px-4 py-3 border-t border-gray-100 flex flex-wrap justify-end items-center gap-3">
          <span className="text-sm text-gray-400">每页</span>
          <Select
            value={pageSize}
            onChange={(val) => { setPageSize(val as number); setPage(0); }}
            options={[10, 20, 50].map(n => ({ label: `${n} 行`, value: n }))}
            style={{ width: 90 }}
          />
          <span className="text-sm text-gray-400">{page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} / {total}</span>
          <Button variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>上一页</Button>
          <Button variant="outline" disabled={(page + 1) * pageSize >= total} onClick={() => setPage((p) => p + 1)}>下一页</Button>
        </div>
      </div>

      {/* 任务结果弹窗 */}
      {resultOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setResultOpen(false)} />
          <div className="relative w-full max-w-2xl mx-4 bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[80vh]">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold">任务结果</h3>
            </div>
            <div className="px-6 py-4 overflow-auto flex-1">
              {resultData ? (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {JSON.stringify(resultData, null, 2)}
                  </pre>
                </div>
              ) : (
                <p className="text-gray-400">暂无结果数据</p>
              )}
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end">
              <Button variant="outline" onClick={() => setResultOpen(false)}>关闭</Button>
            </div>
          </div>
        </div>
      )}

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default ComputeTasksPage;
