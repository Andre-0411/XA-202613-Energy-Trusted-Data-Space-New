/**
 * 隐私计算页面
 * 联邦学习 / MPC / HE / TEE 任务管理
 * 已对接真实API，无Demo组件
 */
import React, { useState } from 'react';
import { Button, Input, Select, Tag, Dialog, MessagePlugin, Card, Statistic, Tabs } from 'tdesign-react';
import { AddIcon, RefreshIcon, PlayIcon, BrowseIcon, StopIcon } from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTasks, createTask, startTask, stopTask, getTaskResult } from '@/api/compute';
import type { ComputeTask } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';

/** 任务类型选项 */
const TASK_TYPE_OPTIONS = [
  { value: 'FL', label: '联邦学习' },
  { value: 'MPC', label: '安全多方计算' },
  { value: 'HE', label: '同态加密' },
  { value: 'TEE', label: '可信执行环境' },
];

/** 任务状态映射 */
const TASK_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  COMPLETED: { label: '已完成', theme: 'success' },
  RUNNING: { label: '运行中', theme: 'primary' },
  PENDING: { label: '待执行', theme: 'warning' },
  FAILED: { label: '失败', theme: 'danger' },
  STOPPED: { label: '已停止', theme: 'default' },
};

const PrivacyComputePage: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);
  const [filterType, setFilterType] = useState<string>('');

  // 弹窗状态
  const [createOpen, setCreateOpen] = useState<boolean>(false);
  const [newTaskName, setNewTaskName] = useState<string>('');
  const [newTaskType, setNewTaskType] = useState<string>('FL');
  const [newTaskDesc, setNewTaskDesc] = useState<string>('');
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<ComputeTask | null>(null);
  const [resultOpen, setResultOpen] = useState<boolean>(false);
  const [resultData, setResultData] = useState<any>(null);

  // 查询任务列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['compute-tasks', page, pageSize, filterType],
    queryFn: () => listTasks({ page: page + 1, page_size: pageSize, task_type: filterType || undefined }),
  });

  const items: ComputeTask[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // 统计
  const stats = {
    total: total,
    running: items.filter(i => i.status === 'RUNNING').length,
    completed: items.filter(i => i.status === 'COMPLETED').length,
  };

  // 创建任务
  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      MessagePlugin.success('任务创建成功');
      setCreateOpen(false);
      setNewTaskName('');
      setNewTaskDesc('');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('创建失败: ' + (error?.message || '未知错误'));
    },
  });

  // 启动任务
  const startMutation = useMutation({
    mutationFn: startTask,
    onSuccess: () => {
      MessagePlugin.success('任务已启动');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('启动失败: ' + (error?.message || '未知错误'));
    },
  });

  // 停止任务
  const stopMutation = useMutation({
    mutationFn: stopTask,
    onSuccess: () => {
      MessagePlugin.success('任务已停止');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('停止失败: ' + (error?.message || '未知错误'));
    },
  });

  // 获取结果
  const handleGetResult = async (taskId: string) => {
    try {
      const res = await getTaskResult(taskId);
      setResultData(res?.data);
      setResultOpen(true);
    } catch (error: any) {
      MessagePlugin.error('获取结果失败: ' + (error?.message || '未知错误'));
    }
  };

  // 表格列定义
  const columns: Column[] = [
    { title: '任务名称', colKey: 'name', width: 200 },
    {
      title: '类型', colKey: 'task_type', width: 120,
      cell: ({ row }) => {
        const typeMap: Record<string, string> = { FL: '联邦学习', MPC: '安全多方计算', HE: '同态加密', TEE: '可信执行环境' };
        return <Tag theme="primary" variant="light">{typeMap[row.task_type] || row.task_type}</Tag>;
      },
    },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }) => {
        const status = TASK_STATUS_MAP[row.status] || { label: row.status, theme: 'default' as const };
        return <Tag theme={status.theme} variant="light">{status.label}</Tag>;
      },
    },
    { title: '创建时间', colKey: 'created_at', width: 180 },
    {
      title: '操作', colKey: 'actions', width: 250,
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />}
            onClick={() => { setDetailData(row); setDetailOpen(true); }}>
            详情
          </Button>
          {row.status === 'PENDING' && (
            <Button size="small" variant="text" theme="success" icon={<PlayIcon />}
              onClick={() => startMutation.mutate(row.id)}>
              启动
            </Button>
          )}
          {row.status === 'RUNNING' && (
            <Button size="small" variant="text" theme="danger" icon={<StopIcon />}
              onClick={() => stopMutation.mutate(row.id)}>
              停止
            </Button>
          )}
          {row.status === 'COMPLETED' && (
            <Button size="small" variant="text" theme="primary"
              onClick={() => handleGetResult(row.id)}>
              查看结果
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="隐私计算" breadcrumbs={[homeBreadcrumb, { label: '计算中心' }, { label: '隐私计算' }]} />

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card><Statistic title="任务总数" value={stats.total} /></Card>
        <Card><Statistic title="运行中" value={stats.running} /></Card>
        <Card><Statistic title="已完成" value={stats.completed} /></Card>
      </div>

      {/* 操作栏 */}
      <div className="flex justify-between mb-4">
        <div className="flex gap-2">
          <Button icon={<AddIcon />} onClick={() => setCreateOpen(true)}>创建任务</Button>
          <Button icon={<RefreshIcon />} variant="outline" onClick={() => refetch()}>刷新</Button>
        </div>
        <Select value={filterType} onChange={setFilterType} options={TASK_TYPE_OPTIONS} placeholder="筛选类型" clearable style={{ width: 150 }} />
      </div>

      {/* 数据表格 */}
      <DataTable columns={columns} rows={items} page={page} pageSize={pageSize} total={total}
        onPageChange={setPage} loading={isLoading} />

      {/* 创建任务弹窗 */}
      <Dialog header="创建计算任务" visible={createOpen} onClose={() => setCreateOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button loading={createMutation.isPending}
              onClick={() => createMutation.mutate({ name: newTaskName, task_type: newTaskType, description: newTaskDesc })}>
              确认创建
            </Button>
          </div>
        }>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">任务名称 *</label>
            <Input value={newTaskName} onChange={setNewTaskName} placeholder="输入任务名称" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">计算类型 *</label>
            <Select value={newTaskType} onChange={setNewTaskType} options={TASK_TYPE_OPTIONS} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">描述</label>
            <Input value={newTaskDesc} onChange={setNewTaskDesc} placeholder="任务描述" />
          </div>
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog header="任务详情" visible={detailOpen} onClose={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {detailData && (
          <div className="space-y-3">
            <div><strong>任务ID:</strong> {detailData.id}</div>
            <div><strong>任务名称:</strong> {detailData.name}</div>
            <div><strong>类型:</strong> {detailData.task_type}</div>
            <div><strong>状态:</strong> {TASK_STATUS_MAP[detailData.status]?.label || detailData.status}</div>
            <div><strong>描述:</strong> {detailData.description || '无'}</div>
            <div><strong>创建时间:</strong> {detailData.created_at}</div>
          </div>
        )}
      </Dialog>

      {/* 结果弹窗 */}
      <Dialog header="计算结果" visible={resultOpen} onClose={() => setResultOpen(false)}
        footer={<Button onClick={() => setResultOpen(false)}>关闭</Button>}>
        <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-80">
          {resultData ? JSON.stringify(resultData, null, 2) : '暂无结果'}
        </pre>
      </Dialog>
    </PageContainer>
  );
};

export default PrivacyComputePage;
