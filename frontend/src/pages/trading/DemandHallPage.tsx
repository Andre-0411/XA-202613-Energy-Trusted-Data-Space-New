/**
 * 需求大厅页面
 * 需求卡片网格（2列）、发布需求、认领需求
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tag, Textarea, MessagePlugin } from 'tdesign-react';
import { AddIcon, RefreshIcon, SearchIcon, TimeIcon, MoneyIcon, UserIcon } from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import request from '@/api/request';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer from '@/components/common/PageContainer';

// ===== API =====
const listDemands = (params?: any) => request.get('/demand-manage', { params });
const createDemand = (data: any) => request.post('/demand-manage', data);
const claimDemand = (id: string, data: any) => request.post(`/demand-manage/${id}/claims`, data);

// ===== 类型 =====
interface DemandItem {
  id: string;
  title: string;
  description: string;
  demand_type: string;
  status: string;
  budget_range?: string;
  deadline?: string;
  publisher?: string;
  created_at: string;
}

const TYPE_MAP: Record<string, string> = {
  data_collect: '数据采集',
  data_process: '数据处理',
  model_train: '模型训练',
  analysis_report: '分析报告',
  system_dev: '系统开发',
};

const STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' | 'primary' }> = {
  open: { label: '开放中', theme: 'primary' },
  claiming: { label: '认领中', theme: 'warning' },
  in_progress: { label: '进行中', theme: 'primary' },
  completed: { label: '已完成', theme: 'success' },
  closed: { label: '已关闭', theme: 'default' },
  expired: { label: '已过期', theme: 'danger' },
};

const DemandHallPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 =====
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // ===== 发布需求 =====
  const [publishOpen, setPublishOpen] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formType, setFormType] = useState('data_collect');
  const [formDesc, setFormDesc] = useState('');
  const [formBudget, setFormBudget] = useState('');
  const [formDeadline, setFormDeadline] = useState('');

  // ===== 认领 =====
  const [claimOpen, setClaimOpen] = useState(false);
  const [claimTarget, setClaimTarget] = useState<DemandItem | null>(null);
  const [claimProposal, setClaimProposal] = useState('');

  // ===== 数据查询 =====
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['demands', keyword, typeFilter, statusFilter],
    queryFn: () => listDemands({
      keyword: keyword || undefined,
      demand_type: typeFilter || undefined,
      status: statusFilter || undefined,
    }),
  });

  const res = data?.data || data;
  const list: DemandItem[] = res?.items || res?.list || res || [];

  // ===== 发布需求 =====
  const publishMut = useMutation({
    mutationFn: (d: any) => createDemand(d),
    onSuccess: () => {
      MessagePlugin.success('需求发布成功');
      queryClient.invalidateQueries({ queryKey: ['demands'] });
      setPublishOpen(false);
      resetForm();
    },
    onError: () => MessagePlugin.error('发布失败'),
  });

  // ===== 认领需求 =====
  const claimMut = useMutation({
    mutationFn: ({ id, proposal }: { id: string; proposal: string }) => claimDemand(id, { proposal }),
    onSuccess: () => {
      MessagePlugin.success('认领申请已提交');
      queryClient.invalidateQueries({ queryKey: ['demands'] });
      setClaimOpen(false);
      setClaimProposal('');
    },
    onError: () => MessagePlugin.error('认领失败'),
  });

  // ===== 辅助 =====
  const resetForm = useCallback(() => {
    setFormTitle('');
    setFormType('data_collect');
    setFormDesc('');
    setFormBudget('');
    setFormDeadline('');
  }, []);

  const handlePublish = useCallback(() => {
    if (!formTitle.trim()) { MessagePlugin.warning('请输入需求标题'); return; }
    publishMut.mutate({
      title: formTitle,
      demand_type: formType,
      description: formDesc,
      budget_range: formBudget || undefined,
      deadline: formDeadline || undefined,
    });
  }, [formTitle, formType, formDesc, formBudget, formDeadline, publishMut]);

  const handleClaim = useCallback(() => {
    if (!claimTarget) return;
    if (!claimProposal.trim()) { MessagePlugin.warning('请输入承接方案'); return; }
    claimMut.mutate({ id: claimTarget.id, proposal: claimProposal });
  }, [claimTarget, claimProposal, claimMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '交易中心' }, { label: '需求大厅' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="需求大厅"
        subtitle="浏览和发布数据服务需求，寻找合适的承接方"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '发布需求', icon: <AddIcon />, onClick: () => { resetForm(); setPublishOpen(true); }, variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => refetch(), tooltip: '刷新' },
        ]}
      />

      {/* 筛选栏 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <Input
            prefixIcon={<SearchIcon />}
            value={keyword}
            onChange={setKeyword}
            placeholder="搜索需求标题或描述"
            style={{ minWidth: 240 }}
            clearable
          />
          <Select
            value={typeFilter}
            onChange={setTypeFilter}
            options={[
              { value: '', label: '全部类型' },
              ...Object.entries(TYPE_MAP).map(([v, l]) => ({ value: v, label: l })),
            ]}
            style={{ minWidth: 140 }}
            clearable
          />
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: '', label: '全部状态' },
              ...Object.entries(STATUS_MAP).map(([v, l]) => ({ value: v, label: l.label })),
            ]}
            style={{ minWidth: 140 }}
            clearable
          />
          <Button onClick={() => { setKeyword(''); setTypeFilter(''); setStatusFilter(''); }}>重置</Button>
        </div>
      </div>

      {/* 需求卡片网格（2列） */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      ) : list.length === 0 ? (
        <div className="rounded-xl bg-white border border-gray-200 p-12 text-center">
          <p className="text-gray-400">暂无需求数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {list.map((item) => {
            const status = STATUS_MAP[item.status] ?? { label: item.status, theme: 'default' as const };
            return (
              <div key={item.id} className="rounded-xl bg-white border border-gray-200 p-5 flex flex-col hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-base font-semibold text-gray-800 flex-1 mr-2">{item.title}</h3>
                  <Tag theme={status.theme} variant="light">{status.label}</Tag>
                </div>
                <p className="text-sm text-gray-600 mb-3 line-clamp-3 min-h-[60px]">
                  {item.description || '暂无描述'}
                </p>
                <div className="flex flex-wrap gap-2 mb-3">
                  {item.demand_type && (
                    <Tag size="small" variant="outline">{TYPE_MAP[item.demand_type] ?? item.demand_type}</Tag>
                  )}
                  {item.budget_range && (
                    <Tag size="small" theme="warning" variant="light">
                      <MoneyIcon style={{ fontSize: '0.75rem', marginRight: 2 }} />
                      {item.budget_range}
                    </Tag>
                  )}
                </div>
                <div className="flex items-center justify-between text-xs text-gray-400 mt-auto pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-3">
                    {item.publisher && (
                      <span className="flex items-center gap-1">
                        <UserIcon style={{ fontSize: '0.75rem' }} />
                        {item.publisher}
                      </span>
                    )}
                    {item.deadline && (
                      <span className="flex items-center gap-1">
                        <TimeIcon style={{ fontSize: '0.75rem' }} />
                        截止: {item.deadline}
                      </span>
                    )}
                  </div>
                  {item.status === 'open' && (
                    <Button
                      size="small"
                      theme="primary"
                      onClick={() => { setClaimTarget(item); setClaimProposal(''); setClaimOpen(true); }}
                    >
                      认领
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 发布需求 Dialog */}
      <Dialog
        visible={publishOpen}
        onClose={() => setPublishOpen(false)}
        header="发布需求"
        width="560px"
        footer={
          <div className="flex justify-end gap-3">
            <Button onClick={() => setPublishOpen(false)}>取消</Button>
            <Button theme="primary" loading={publishMut.isPending} onClick={handlePublish}>发布</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">需求标题 <span className="text-red-500">*</span></label>
            <Input value={formTitle} onChange={setFormTitle} placeholder="请输入需求标题" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">需求类型</label>
            <Select
              value={formType}
              onChange={setFormType}
              options={Object.entries(TYPE_MAP).map(([v, l]) => ({ value: v, label: l }))}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">需求描述</label>
            <Textarea value={formDesc} onChange={setFormDesc} placeholder="请详细描述需求内容" rows={4} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">预算范围</label>
              <Input value={formBudget} onChange={setFormBudget} placeholder="如: ¥50,000" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">截止日期</label>
              <Input value={formDeadline} onChange={setFormDeadline} placeholder="如: 2025-06-30" />
            </div>
          </div>
        </div>
      </Dialog>

      {/* 认领 Dialog */}
      <Dialog
        visible={claimOpen}
        onClose={() => setClaimOpen(false)}
        header="认领需求"
        width="480px"
        footer={
          <div className="flex justify-end gap-3">
            <Button onClick={() => setClaimOpen(false)}>取消</Button>
            <Button theme="primary" loading={claimMut.isPending} onClick={handleClaim}>提交方案</Button>
          </div>
        }
      >
        {claimTarget && (
          <div className="flex flex-col gap-4">
            <div className="p-3 rounded-lg bg-gray-50 border border-gray-200">
              <div className="font-semibold text-sm">{claimTarget.title}</div>
              {claimTarget.budget_range && (
                <div className="text-xs text-orange-600 mt-1">预算: {claimTarget.budget_range}</div>
              )}
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">承接方案 <span className="text-red-500">*</span></label>
              <Textarea
                value={claimProposal}
                onChange={setClaimProposal}
                placeholder="请描述您的承接方案、团队优势和预计交付时间..."
                rows={5}
              />
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default DemandHallPage;
