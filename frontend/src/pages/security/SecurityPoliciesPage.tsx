/**
 * 安全策略管理页面
 * 策略 CRUD + 权限评估
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Dialog, MessagePlugin, Tag, Tooltip, Textarea } from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, RefreshIcon,
  ShieldErrorFilledIcon, CheckCircleFilledIcon, ErrorCircleFilledIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listPolicies, createPolicy, updatePolicy, deletePolicy, evaluatePermission } from '@/api/security';
import type { SecurityPolicy } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';

const POLICY_TYPE_OPTIONS = [
  { value: 'ACCESS_CONTROL', label: '访问控制' },
  { value: 'DATA_MASKING', label: '数据脱敏' },
  { value: 'AUDIT', label: '审计策略' },
  { value: 'ENCRYPTION', label: '加密策略' },
];

const policyStatusLabel = (s: string): string => {
  const m: Record<string, string> = { ACTIVE: '生效中', DRAFT: '草稿', ARCHIVED: '已归档' };
  return m[s] ?? s;
};

const policyStatusColor = (s: string): 'success' | 'warning' | 'info' | 'default' => {
  const m: Record<string, 'success' | 'warning' | 'info'> = { ACTIVE: 'success', DRAFT: 'warning', ARCHIVED: 'info' };
  return m[s] ?? 'default';
};

const SecurityPoliciesPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const policyTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增策略', '活跃策略'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增策略', type: 'bar', data: [12, 15, 18, 14, 20, 22, 25], itemStyle: { color: '#667eea' } },
      { name: '活跃策略', type: 'line', smooth: true, data: [85, 88, 90, 92, 95, 96, 98], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const policyTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '策略类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 52, name: '访问控制', itemStyle: { color: '#667eea' } },
          { value: 35, name: '数据脱敏', itemStyle: { color: '#43e97b' } },
          { value: 25, name: '审计策略', itemStyle: { color: '#f093fb' } },
          { value: 16, name: '加密策略', itemStyle: { color: '#4facfe' } },
        ],
      },
    ],
  }), []);

  // ===== 筛选 =====
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // ===== 创建/编辑弹窗 =====
  const [editOpen, setEditOpen] = useState<boolean>(false);
  const [editMode, setEditMode] = useState<boolean>(false);
  const [editId, setEditId] = useState<string>('');
  const [formName, setFormName] = useState<string>('');
  const [formType, setFormType] = useState<string>('ACCESS_CONTROL');
  const [formRules, setFormRules] = useState<string>('{}');
  const [formPriority, setFormPriority] = useState<number>(1);
  const [formStatus, setFormStatus] = useState<string>('DRAFT');

  // ===== 权限评估弹窗 =====
  const [evalOpen, setEvalOpen] = useState<boolean>(false);
  const [evalSubjectDid, setEvalSubjectDid] = useState<string>('');
  const [evalResourceType, setEvalResourceType] = useState<string>('');
  const [evalResourceId, setEvalResourceId] = useState<string>('');
  const [evalAction, setEvalAction] = useState<string>('');
  const [evalResult, setEvalResult] = useState<{ allowed: boolean; deny_reason?: string } | null>(null);

  // ===== 删除确认 =====
  const [deleteTarget, setDeleteTarget] = useState<SecurityPolicy | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['policies', filterType, filterStatus],
    queryFn: () => listPolicies({ policy_type: filterType || undefined, status: filterStatus || undefined }),
  });

  const items: SecurityPolicy[] = (data?.data as unknown as SecurityPolicy[] | undefined) ?? [];

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    totalPolicies: items.length,
    activePolicies: items.filter(p => p.status === 'active').length,
    draftPolicies: items.filter(p => p.status === 'draft').length,
    archivedPolicies: items.filter(p => p.status === 'archived').length,
  }), [items]);

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<SecurityPolicy>) => createPolicy(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['policies'] }); closeEditDialog(); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data: d }: { id: string; data: Partial<SecurityPolicy> }) => updatePolicy(id, d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['policies'] }); closeEditDialog(); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deletePolicy(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['policies'] }); setDeleteTarget(null); },
  });

  const evalMut = useMutation({
    mutationFn: (d: { subject_did: string; resource_type: string; resource_id: string; action: string }) => evaluatePermission(d),
    onSuccess: (res) => { setEvalResult(res.data ?? null); },
  });

  // ===== 辅助方法 =====
  const closeEditDialog = useCallback(() => {
    setEditOpen(false); setEditMode(false); setEditId('');
    setFormName(''); setFormType('ACCESS_CONTROL'); setFormRules('{}');
    setFormPriority(1); setFormStatus('DRAFT');
  }, []);

  const openCreateDialog = useCallback(() => {
    setEditMode(false); setEditId(''); setFormName(''); setFormType('ACCESS_CONTROL');
    setFormRules('{}'); setFormPriority(1); setFormStatus('DRAFT');
    setEditOpen(true);
  }, []);

  const openEditDialog = useCallback((policy: SecurityPolicy) => {
    setEditMode(true); setEditId(policy.id); setFormName(policy.name);
    setFormType(policy.policy_type); setFormRules(JSON.stringify(policy.rules, null, 2));
    setFormPriority(policy.priority); setFormStatus(policy.status);
    setEditOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    let rules: Record<string, unknown> = {};
    try { rules = JSON.parse(formRules || '{}'); } catch { rules = {}; }
    const payload: Partial<SecurityPolicy> = {
      name: formName, policy_type: formType, rules, priority: formPriority, status: formStatus,
    };
    if (editMode) {
      updateMut.mutate({ id: editId, data: payload });
    } else {
      createMut.mutate(payload);
    }
  }, [editMode, editId, formName, formType, formRules, formPriority, formStatus, createMut, updateMut]);

  const handleEvaluate = useCallback(() => {
    evalMut.mutate({
      subject_did: evalSubjectDid, resource_type: evalResourceType,
      resource_id: evalResourceId, action: evalAction,
    });
  }, [evalSubjectDid, evalResourceType, evalResourceId, evalAction, evalMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '安全策略' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '新增策略', icon: <AddIcon />, onClick: openCreateDialog, variant: 'contained' },
      { label: '权限评估', icon: <ShieldErrorFilledIcon />, onClick: () => { setEvalResult(null); setEvalOpen(true); }, variant: 'outlined' },
    ],
    [openCreateDialog],
  );

  return (
    <PageContainer>
      <PageHeader
        title="安全策略管理"
        subtitle="管理安全策略与权限评估"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['policies'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总策略数" value={stats.totalPolicies} icon={<ShieldErrorFilledIcon />} gradient="purple" unit="" />
        <MetricsCard title="生效中" value={stats.activePolicies} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="草稿" value={stats.draftPolicies} icon={<ErrorCircleFilledIcon />} color="warning" unit="" />
        <MetricsCard title="已归档" value={stats.archivedPolicies} icon={<ShieldErrorFilledIcon />} gradient="red" unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        <div className="md:col-span-8"><ChartCard title="策略增长趋势" option={policyTrendOption} height={300} /></div>
        <div className="md:col-span-4"><ChartCard title="策略类型分布" option={policyTypeOption} height={300} /></div>
      </div>

      {/* 筛选栏 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <div className="flex items-center gap-4">
          <Select
            value={filterType}
            onChange={(val) => setFilterType(String(val))}
            options={[{ value: '', label: '全部' }, ...POLICY_TYPE_OPTIONS]}
            placeholder="策略类型"
            style={{ minWidth: 140 }}
          />
          <Select
            value={filterStatus}
            onChange={(val) => setFilterStatus(String(val))}
            options={[
              { value: '', label: '全部' },
              { value: 'ACTIVE', label: '生效中' },
              { value: 'DRAFT', label: '草稿' },
              { value: 'ARCHIVED', label: '已归档' },
            ]}
            placeholder="状态"
            style={{ minWidth: 140 }}
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">策略名称</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">策略类型</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">优先级</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">状态</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">创建时间</th>
                <th className="px-4 py-3 text-center font-bold text-sm text-gray-700 w-[140px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 border-t border-gray-100">
                  <td className="px-4 py-3 font-medium text-sm">{row.name}</td>
                  <td className="px-4 py-3 text-sm">{POLICY_TYPE_OPTIONS.find((o) => o.value === row.policy_type)?.label ?? row.policy_type}</td>
                  <td className="px-4 py-3 text-sm">{row.priority}</td>
                  <td className="px-4 py-3"><StatusTag status={policyStatusLabel(row.status)} color={policyStatusColor(row.status)} /></td>
                  <td className="px-4 py-3 text-sm">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="编辑">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => openEditDialog(row)}>
                          <EditIcon style={{ fontSize: 16 }} />
                        </span>
                      </Tooltip>
                      <Tooltip content="删除">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600" onClick={() => setDeleteTarget(row)}>
                          <DeleteIcon style={{ fontSize: 16 }} />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-500">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 创建/编辑弹窗 */}
      <Dialog
        visible={editOpen}
        onClose={closeEditDialog}
        header={editMode ? '编辑策略' : '新增策略'}
        destroyOnClose
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={closeEditDialog}>取消</Button>
            <Button theme="primary" disabled={!formName.trim()} onClick={handleSubmit}>{editMode ? '保存' : '创建'}</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">策略名称</label>
            <Input value={formName} onChange={(val) => setFormName(String(val))} placeholder="请输入策略名称" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">策略类型</label>
            <Select
              value={formType}
              onChange={(val) => setFormType(String(val))}
              options={POLICY_TYPE_OPTIONS}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">规则 (JSON)</label>
            <Textarea value={formRules} onChange={(val) => setFormRules(String(val))} rows={4} />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">优先级</label>
            <Input value={String(formPriority)} onChange={(val) => setFormPriority(parseInt(String(val), 10) || 1)} type="number" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">状态</label>
            <Select
              value={formStatus}
              onChange={(val) => setFormStatus(String(val))}
              options={[
                { value: 'DRAFT', label: '草稿' },
                { value: 'ACTIVE', label: '生效' },
                { value: 'ARCHIVED', label: '归档' },
              ]}
            />
          </div>
        </div>
      </Dialog>

      {/* 权限评估弹窗 */}
      <Dialog
        visible={evalOpen}
        onClose={() => { setEvalOpen(false); setEvalResult(null); }}
        header="权限评估"
        destroyOnClose
        footer={
          <div className="flex justify-end">
            <Button onClick={() => { setEvalOpen(false); setEvalResult(null); }}>关闭</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">主体 DID</label>
            <Input value={evalSubjectDid} onChange={(val) => setEvalSubjectDid(String(val))} placeholder="请输入主体 DID" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">资源类型</label>
            <Input value={evalResourceType} onChange={(val) => setEvalResourceType(String(val))} placeholder="data_asset" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">资源 ID</label>
            <Input value={evalResourceId} onChange={(val) => setEvalResourceId(String(val))} placeholder="请输入资源 ID" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">操作</label>
            <Input value={evalAction} onChange={(val) => setEvalAction(String(val))} placeholder="read / write / delete" />
          </div>
          <Button
            theme="primary"
            disabled={!evalSubjectDid.trim() || !evalResourceType.trim() || !evalResourceId.trim() || !evalAction.trim()}
            onClick={handleEvaluate}
          >
            执行评估
          </Button>
          {evalResult && (
            <div className={`rounded-lg p-4 ${evalResult.allowed ? 'bg-green-50' : 'bg-red-50'}`}>
              <h4 className={`font-semibold ${evalResult.allowed ? 'text-green-700' : 'text-red-700'}`}>
                {evalResult.allowed ? '✓ 允许访问' : '✗ 拒绝访问'}
              </h4>
              {evalResult.deny_reason && (
                <span className="text-sm text-gray-600 mt-1 block">
                  原因: {evalResult.deny_reason}
                </span>
              )}
            </div>
          )}
        </div>
      </Dialog>

      {/* 删除确认 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除策略"
        message={`确定要删除策略「${deleteTarget?.name ?? ''}」吗？此操作不可恢复。`}
        type="danger"
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteMut.isPending}
      />

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default SecurityPoliciesPage;
