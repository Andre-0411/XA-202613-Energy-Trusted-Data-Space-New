/**
 * 计算沙箱页面
 * 沙箱实例的创建、删除、上传算法、执行、导出审计日志 + 统计卡片 + ECharts图表
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tooltip, MessagePlugin, Tag, Textarea, Select } from 'tdesign-react';
import {
  AddIcon, DeleteIcon, RefreshIcon, PlayIcon, UploadIcon, DownloadIcon,
  ShieldErrorIcon, ServerIcon, DesktopIcon, CheckCircleIcon, TimeIcon, TrendingUpIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listSandboxes, createSandbox, deleteSandbox,
  scanSandboxAlgorithm, exportSandboxAudit,
} from '@/api/compute';
import type { Sandbox } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import ChartCard from '@/components/common/ChartCard';
import StatCard from '@/components/common/StatCard';

/** 沙箱表单数据 */
interface SandboxFormData {
  name: string;
  algorithm: string;
  config_json: string;
}

const INITIAL_FORM: SandboxFormData = {
  name: '',
  algorithm: '',
  config_json: '{}',
};

const ComputeSandboxPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const sandboxTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['创建', '完成', '运行中'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '沙箱数' },
    series: [
      { name: '创建', type: 'bar', data: [8, 12, 10, 15, 13, 18, 14], itemStyle: { color: '#2196f3' } },
      { name: '完成', type: 'bar', data: [6, 10, 8, 12, 11, 15, 12], itemStyle: { color: '#4caf50' } },
      { name: '运行中', type: 'line', smooth: true, data: [5, 7, 9, 12, 14, 17, 12], itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  const statusDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '沙箱状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 12, name: '运行中', itemStyle: { color: '#4caf50' } },
          { value: 32, name: '已完成', itemStyle: { color: '#2196f3' } },
          { value: 4, name: '失败', itemStyle: { color: '#f44336' } },
        ],
      },
    ],
  }), []);

  // ===== 状态 =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(12);

  // 弹窗
  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [formData, setFormData] = useState<SandboxFormData>(INITIAL_FORM);
  const [deleteTarget, setDeleteTarget] = useState<Sandbox | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['sandboxes', page, pageSize],
    queryFn: () => listSandboxes({ page: page + 1, page_size: pageSize }),
  });

  const items: Sandbox[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    totalSandboxes: total,
    running: items.filter(i => i.status === 'running').length,
    completed: items.filter(i => i.status === 'completed').length,
    todayTasks: items.filter(i => {
      const today = new Date().toDateString();
      return new Date(i.created_at).toDateString() === today;
    }).length,
  }), [items, total]);

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<Sandbox>) => createSandbox(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandboxes'] });
      closeForm();
      MessagePlugin.success('沙箱创建成功');
    },
    onError: () => {
      MessagePlugin.error('沙箱创建失败');
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteSandbox(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandboxes'] });
      setDeleteTarget(null);
      MessagePlugin.success('沙箱已删除');
    },
    onError: () => {
      MessagePlugin.error('沙箱删除失败');
    },
  });

  const scanMut = useMutation({
    mutationFn: (id: string) => scanSandboxAlgorithm(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sandboxes'] });
      MessagePlugin.success('安全扫描已启动');
    },
    onError: () => {
      MessagePlugin.error('安全扫描失败');
    },
  });

  const exportMut = useMutation({
    mutationFn: (id: string) => exportSandboxAudit(id),
    onSuccess: (res) => {
      const auditData = JSON.stringify(res.data, null, 2);
      const blob = new Blob([auditData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sandbox-audit-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      MessagePlugin.success('审计日志已导出');
    },
    onError: () => {
      MessagePlugin.error('审计日志导出失败');
    },
  });

  // ===== 表单操作 =====
  const openCreateForm = useCallback(() => {
    setFormData(INITIAL_FORM);
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => {
    setFormOpen(false);
    setFormData(INITIAL_FORM);
  }, []);

  const handleSubmit = useCallback(() => {
    let config: Record<string, unknown> = {};
    try {
      config = JSON.parse(formData.config_json || '{}');
    } catch {
      config = {};
    }
    createMut.mutate({
      name: formData.name,
      algorithm: formData.algorithm,
      config,
    });
  }, [formData, createMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '计算沙箱' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{ label: '创建沙箱', icon: <AddIcon />, onClick: openCreateForm, variant: 'contained' }],
    [openCreateForm],
  );

  /** 状态颜色 */
  const statusColor = (status: string): string => {
    const map: Record<string, string> = {
      active: '#4caf50', running: '#2196f3', stopped: '#9e9e9e', error: '#f44336', created: '#ff9800',
    };
    return map[status] ?? '#9e9e9e';
  };

  return (
    <PageContainer>
      <PageHeader
        title="计算沙箱"
        subtitle="在隔离的安全沙箱环境中执行不可信算法，支持安全扫描与审计导出"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['sandboxes'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总沙箱数" value={stats.totalSandboxes} unit="个" icon={<DesktopIcon size="20px" />} gradient="purple" />
        <StatCard title="运行中" value={stats.running} unit="个" icon={<PlayIcon size="20px" />} gradient="green" />
        <StatCard title="已完成" value={stats.completed} unit="个" icon={<CheckCircleIcon size="20px" />} gradient="cyan" />
        <StatCard title="今日任务" value={stats.todayTasks} unit="个" icon={<TrendingUpIcon size="20px" />} gradient="orange" />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2"><ChartCard title="沙箱运行趋势" option={sandboxTrendOption} height={300} /></div>
        <ChartCard title="沙箱状态分布" option={statusDistOption} height={300} />
      </div>

      {/* 沙箱卡片列表 */}
      <div className="flex-1 overflow-auto">
        {items.length === 0 ? (
          <div className="rounded-xl bg-white border border-gray-200 p-12 text-center">
            <p className="text-gray-400">暂无沙箱实例</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {items.map((sandbox) => (
              <div key={sandbox.id} className="rounded-xl bg-white border border-gray-200 overflow-hidden">
                {/* 卡片头部 */}
                <div className="px-4 py-3 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-white" style={{ backgroundColor: statusColor(sandbox.status) }}>
                    <ServerIcon size="16px" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold">{sandbox.name}</p>
                      <StatusTag status={sandbox.status} />
                    </div>
                    <p className="text-xs text-gray-400">创建于 {new Date(sandbox.created_at).toLocaleString('zh-CN')}</p>
                  </div>
                </div>
                {/* 卡片内容 */}
                <div className="px-4 pb-2">
                  <div className="flex gap-6">
                    <div>
                      <p className="text-xs text-gray-400">算法</p>
                      <p className="text-sm">{sandbox.algorithm || '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">ID</p>
                      <Tag variant="outline">{sandbox.id.slice(0, 8)}</Tag>
                    </div>
                    {sandbox.result && (
                      <div>
                        <p className="text-xs text-gray-400">结果</p>
                        <p className="text-sm font-medium text-green-600">已生成</p>
                      </div>
                    )}
                  </div>
                </div>
                {/* 卡片操作 */}
                <div className="px-4 py-2 border-t border-gray-100 flex gap-2">
                  <Button variant="outline" icon={<ShieldErrorIcon />} onClick={() => scanMut.mutate(sandbox.id)}>
                    安全扫描
                  </Button>
                  <Button variant="outline" icon={<UploadIcon />} disabled={sandbox.status !== 'active'}>
                    上传算法
                  </Button>
                  <Button variant="outline" theme="success" icon={<PlayIcon />} disabled={sandbox.status !== 'active'}>
                    执行
                  </Button>
                  <Button variant="outline" theme="primary" icon={<DownloadIcon />} onClick={() => exportMut.mutate(sandbox.id)}>
                    导出审计
                  </Button>
                  <div className="flex-1" />
                  <Button variant="text" theme="danger" icon={<DeleteIcon />} onClick={() => setDeleteTarget(sandbox)} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 分页 */}
      <div className="rounded-xl bg-white border border-gray-200 p-3">
        <div className="flex justify-between items-center">
          <p className="text-sm text-gray-400">共 {total} 个沙箱实例</p>
          <div className="flex gap-2 items-center">
            <Button variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              上一页
            </Button>
            <span className="text-sm">第 {page + 1} 页</span>
            <Button variant="outline" disabled={(page + 1) * pageSize >= total} onClick={() => setPage((p) => p + 1)}>
              下一页
            </Button>
          </div>
        </div>
      </div>

      {/* 创建弹窗 */}
      {formOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={closeForm} />
          <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold">创建沙箱</h3>
            </div>
            <div className="px-6 py-4 flex flex-col gap-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">沙箱名称 <span className="text-red-500">*</span></p>
                <Input
                  value={formData.name}
                  onChange={(val) => setFormData((prev) => ({ ...prev, name: val }))}
                />
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">算法名称</p>
                <Input
                  value={formData.algorithm}
                  onChange={(val) => setFormData((prev) => ({ ...prev, algorithm: val }))}
                  placeholder="例如: linear_regression.py"
                />
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">配置 (JSON)</p>
                <Textarea
                  rows={4}
                  value={formData.config_json}
                  onChange={(val) => setFormData((prev) => ({ ...prev, config_json: val }))}
                  placeholder='{"timeout": 300, "memory": "2G"}'
                />
              </div>
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2">
              <Button variant="outline" onClick={closeForm}>取消</Button>
              <Button theme="primary" onClick={handleSubmit} disabled={!formData.name}>创建</Button>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除沙箱"
        message={`确定要删除沙箱「${deleteTarget?.name ?? ''}」吗？此操作不可撤销，所有数据将被清除。`}
        type="danger"
        confirmText="删除"
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteMut.isPending}
      />

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default ComputeSandboxPage;
