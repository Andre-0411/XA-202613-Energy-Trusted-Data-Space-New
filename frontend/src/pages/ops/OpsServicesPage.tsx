/**
 * 服务管理页面
 * 服务目录 CRUD + 订阅管理 + 审批
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, Dialog, MessagePlugin, Pagination } from 'tdesign-react';
import {
  AddIcon, EditIcon, RefreshIcon, ServiceIcon, CheckCircleFilledIcon,
  PendingIcon, UsergroupIcon, CloseIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listServices, createService, updateService,
  getSubscriptions, subscribeService, approveSubscription,
} from '@/api/ops';
import type { ServiceCatalog, Subscription } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';


const CATEGORY_OPTIONS = ['数据共享', '计算服务', '存储服务', '安全服务'];
const PRICING_OPTIONS = [
  { value: 'FREE', label: '免费' },
  { value: 'PER_USE', label: '按次计费' },
  { value: 'PER_MONTH', label: '包月' },
];

const serviceStatusLabel = (s: string): string => {
  const m: Record<string, string> = { ACTIVE: '活跃', INACTIVE: '停用', PENDING: '待审核' };
  return m[s] ?? s;
};

const OpsServicesPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const serviceTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增服务', '活跃服务'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增服务', type: 'bar', data: [5, 8, 6, 9, 7, 10, 12], itemStyle: { color: '#667eea' } },
      { name: '活跃服务', type: 'line', smooth: true, data: [30, 32, 35, 36, 38, 40, 42], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const serviceCategoryOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '服务分类',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 18, name: '数据共享', itemStyle: { color: '#667eea' } },
          { value: 12, name: '计算服务', itemStyle: { color: '#43e97b' } },
          { value: 8, name: '存储服务', itemStyle: { color: '#f093fb' } },
          { value: 7, name: '安全服务', itemStyle: { color: '#4facfe' } },
        ],
      },
    ],
  }), []);

  // ===== 筛选 & 分页 =====
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 创建/编辑弹窗 =====
  const [editOpen, setEditOpen] = useState<boolean>(false);
  const [editMode, setEditMode] = useState<boolean>(false);
  const [editId, setEditId] = useState<string>('');
  const [formName, setFormName] = useState<string>('');
  const [formCategory, setFormCategory] = useState<string>('');
  const [formPricingModel, setFormPricingModel] = useState<string>('FREE');
  const [formPricingConfig, setFormPricingConfig] = useState<string>('{}');
  const [formDescription, setFormDescription] = useState<string>('');

  // ===== 订阅弹窗 =====
  const [subOpen, setSubOpen] = useState<boolean>(false);
  const [subServiceId, setSubServiceId] = useState<string>('');
  const [subStartDate, setSubStartDate] = useState<string>('');
  const [subEndDate, setSubEndDate] = useState<string>('');

  // ===== 订阅列表弹窗 =====
  const [subListOpen, setSubListOpen] = useState<boolean>(false);
  const [subListServiceId, setSubListServiceId] = useState<string>('');
  const [subPage, setSubPage] = useState<number>(0);
  const [subPageSize, setSubPageSize] = useState<number>(5);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['services', page, pageSize, filterCategory],
    queryFn: () => listServices({ page: page + 1, page_size: pageSize, category: filterCategory || undefined }),
  });

  const items: ServiceCatalog[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // 订阅列表查询
  const { data: subData } = useQuery({
    queryKey: ['subscriptions', subListServiceId, subPage, subPageSize],
    queryFn: () => getSubscriptions(subListServiceId, { page: subPage + 1, page_size: subPageSize }),
    enabled: subListOpen && !!subListServiceId,
  });

  const subItems: Subscription[] = subData?.data?.items ?? [];
  const subTotal: number = subData?.data?.total ?? 0;

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    totalServices: total,
    activeServices: items.filter(s => s.status === 'active').length,
    pendingServices: items.filter(s => s.status === 'pending').length,
    totalSubscriptions: subTotal,
  }), [items, total, subTotal]);

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<ServiceCatalog>) => createService(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['services'] }); closeEditDialog(); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data: d }: { id: string; data: Partial<ServiceCatalog> }) => updateService(id, d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['services'] }); closeEditDialog(); },
  });

  const subscribeMut = useMutation({
    mutationFn: ({ serviceId, data: d }: { serviceId: string; data: { start_date: string; end_date?: string } }) =>
      subscribeService(serviceId, d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      setSubOpen(false);
    },
  });

  const approveMut = useMutation({
    mutationFn: ({ subId, approved }: { subId: string; approved: boolean }) => approveSubscription(subId, approved),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['subscriptions'] }); },
  });

  // ===== 辅助方法 =====
  const closeEditDialog = useCallback(() => {
    setEditOpen(false); setEditMode(false); setEditId('');
    setFormName(''); setFormCategory(''); setFormPricingModel('FREE');
    setFormPricingConfig('{}'); setFormDescription('');
  }, []);

  const openCreateDialog = useCallback(() => {
    setEditMode(false); setEditId(''); setFormName(''); setFormCategory('');
    setFormPricingModel('FREE'); setFormPricingConfig('{}'); setFormDescription('');
    setEditOpen(true);
  }, []);

  const openEditDialog = useCallback((svc: ServiceCatalog) => {
    setEditMode(true); setEditId(svc.id); setFormName(svc.name);
    setFormCategory(svc.category); setFormPricingModel(svc.pricing_model);
    setFormPricingConfig(JSON.stringify(svc.pricing_config, null, 2));
    setFormDescription(svc.description ?? '');
    setEditOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    let pricingConfig: Record<string, unknown> = {};
    try { pricingConfig = JSON.parse(formPricingConfig || '{}'); } catch { pricingConfig = {}; }
    const payload: Partial<ServiceCatalog> = {
      name: formName, category: formCategory, pricing_model: formPricingModel,
      pricing_config: pricingConfig, description: formDescription || undefined,
    };
    if (editMode) {
      updateMut.mutate({ id: editId, data: payload });
    } else {
      createMut.mutate(payload);
    }
  }, [editMode, editId, formName, formCategory, formPricingModel, formPricingConfig, formDescription, createMut, updateMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '服务管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{ label: '新增服务', icon: <AddIcon />, onClick: openCreateDialog, variant: 'contained' }],
    [openCreateDialog],
  );

  return (
    <PageContainer>
      <PageHeader
        title="服务管理"
        subtitle="管理服务目录、订阅与审批"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['services'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总服务数" value={stats.totalServices} icon={<ServiceIcon />} gradient="purple" unit="" />
        <MetricsCard title="活跃服务" value={stats.activeServices} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="待审核" value={stats.pendingServices} icon={<PendingIcon />} color="warning" unit="" />
        <MetricsCard title="总订阅数" value={stats.totalSubscriptions} icon={<UsergroupIcon />} gradient="red" unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <div className="md:col-span-2"><ChartCard title="服务增长趋势" option={serviceTrendOption} height={300} /></div>
        <ChartCard title="服务分类分布" option={serviceCategoryOption} height={300} />
      </div>

      {/* 搜索过滤栏 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <Select
            value={filterCategory}
            onChange={(val) => { setFilterCategory(String(val)); setPage(0); }}
            options={[{ label: '全部类别', value: '' }, ...CATEGORY_OPTIONS.map(c => ({ label: c, value: c }))]}
            style={{ minWidth: 160 }}
            clearable
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-bold">服务名称</th>
                <th className="px-4 py-3 text-left font-bold">类别</th>
                <th className="px-4 py-3 text-left font-bold">定价模型</th>
                <th className="px-4 py-3 text-left font-bold">状态</th>
                <th className="px-4 py-3 text-left font-bold">创建时间</th>
                <th className="px-4 py-3 text-center font-bold w-[180px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium">{row.name}</td>
                  <td className="px-4 py-3">{row.category}</td>
                  <td className="px-4 py-3">{PRICING_OPTIONS.find((o) => o.value === row.pricing_model)?.label ?? row.pricing_model}</td>
                  <td className="px-4 py-3"><StatusTag status={serviceStatusLabel(row.status)} /></td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex gap-1 justify-center">
                      <Tooltip content="编辑">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => openEditDialog(row)}>
                          <EditIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content="订阅">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-purple-500" onClick={() => { setSubServiceId(row.id); setSubStartDate(''); setSubEndDate(''); setSubOpen(true); }}>
                          <UsergroupIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content="订阅列表">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-cyan-500" onClick={() => { setSubListServiceId(row.id); setSubPage(0); setSubListOpen(true); }}>
                          <ServiceIcon />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end p-3 border-t border-gray-100">
          <Pagination
            total={total}
            current={page + 1}
            pageSize={pageSize}
            onChange={(pageInfo) => {
              setPage(pageInfo.current - 1);
              setPageSize(pageInfo.pageSize);
            }}
          />
        </div>
      </div>

      {/* 创建/编辑弹窗 */}
      <Dialog visible={editOpen} onClose={closeEditDialog} header={editMode ? '编辑服务' : '新增服务'} width="520px">
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">服务名称</label><Input value={formName} onChange={(val) => setFormName(String(val))} /></div>
          <Select
            label="类别"
            value={formCategory}
            onChange={(val) => setFormCategory(String(val))}
            options={CATEGORY_OPTIONS.map(c => ({ label: c, value: c }))}
          />
          <Select
            label="定价模型"
            value={formPricingModel}
            onChange={(val) => setFormPricingModel(String(val))}
            options={PRICING_OPTIONS}
          />
          <Input label="定价配置 (JSON)" value={formPricingConfig} onChange={(val) => setFormPricingConfig(String(val))} />
          <Input label="描述" value={formDescription} onChange={(val) => setFormDescription(String(val))} />
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button onClick={closeEditDialog}>取消</Button>
          <Button theme="primary" disabled={!formName.trim()} onClick={handleSubmit}>{editMode ? '保存' : '创建'}</Button>
        </div>
      </Dialog>

      {/* 订阅弹窗 */}
      <Dialog visible={subOpen} onClose={() => setSubOpen(false)} header="订阅服务" width="400px">
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">开始日期</label><Input placeholder="YYYY-MM-DD" value={subStartDate} onChange={(val) => setSubStartDate(String(val))} /></div>
          <div><label className="block text-sm text-gray-600 mb-1">结束日期（可选）</label><Input type="text" placeholder="YYYY-MM-DD" value={subEndDate} onChange={(val) => setSubEndDate(String(val))} /></div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button onClick={() => setSubOpen(false)}>取消</Button>
          <Button theme="primary" disabled={!subStartDate} onClick={() => subscribeMut.mutate({ serviceId: subServiceId, data: { start_date: subStartDate, end_date: subEndDate || undefined } })}>确认订阅</Button>
        </div>
      </Dialog>

      {/* 订阅列表弹窗 */}
      <Dialog visible={subListOpen} onClose={() => setSubListOpen(false)} header="订阅列表" width="720px">
        {subItems.length === 0 ? (
          <p className="text-gray-400 py-4">暂无订阅记录</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-bold">用户ID</th>
                <th className="px-4 py-3 text-left font-bold">状态</th>
                <th className="px-4 py-3 text-left font-bold">审批状态</th>
                <th className="px-4 py-3 text-left font-bold">开始日期</th>
                <th className="px-4 py-3 text-left font-bold">已用额度</th>
                <th className="px-4 py-3 text-center font-bold w-[120px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {subItems.map((sub) => (
                <tr key={sub.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">{sub.user_id}</td>
                  <td className="px-4 py-3"><StatusTag status={sub.status} /></td>
                  <td className="px-4 py-3"><StatusTag status={sub.approval_status} /></td>
                  <td className="px-4 py-3">{sub.start_date}</td>
                  <td className="px-4 py-3">{sub.quota_used}</td>
                  <td className="px-4 py-3 text-center">
                    {sub.approval_status === 'PENDING' && (
                      <div className="flex gap-1 justify-center">
                        <Tooltip content="批准">
                          <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500" onClick={() => approveMut.mutate({ subId: sub.id, approved: true })}>
                            <CheckCircleFilledIcon />
                          </span>
                        </Tooltip>
                        <Tooltip content="拒绝">
                          <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-500" onClick={() => approveMut.mutate({ subId: sub.id, approved: false })}>
                            <CloseIcon />
                          </span>
                        </Tooltip>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="flex justify-center items-center gap-3 mt-4">
          <Button variant="outline" disabled={subPage === 0} onClick={() => setSubPage((p) => p - 1)}>上一页</Button>
          <span className="text-sm text-gray-400">第 {subPage + 1} 页</span>
          <Button variant="outline" disabled={(subPage + 1) * subPageSize >= subTotal} onClick={() => setSubPage((p) => p + 1)}>下一页</Button>
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default OpsServicesPage;
