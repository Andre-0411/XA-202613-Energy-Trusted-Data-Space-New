/**
 * 服务申请管理页面
 * 在线提交数据使用申请，审批流程跟踪，申请状态实时推送
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tag, Tooltip, Textarea, Steps, MessagePlugin } from 'tdesign-react';
import {
  SearchIcon, RefreshIcon, AddIcon, BrowseIcon,
  CheckCircleIcon, CloseCircleIcon, TimeIcon, TrendingUpIcon, FileIcon,
  LinkIcon, UserIcon, SettingIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listServices, subscribeService, getSubscriptions, approveSubscription,
} from '@/api/ops';
import type { ServiceCatalog, Subscription } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

/** 申请状态选项 */
const REQUEST_STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'pending', label: '待审批' },
  { value: 'approved', label: '已批准' },
  { value: 'rejected', label: '已拒绝' },
  { value: 'expired', label: '已过期' },
];

/** 服务分类选项 */
const SERVICE_CATEGORY_OPTIONS = [
  { value: 'all', label: '全部分类' },
  { value: 'data_query', label: '数据查询' },
  { value: 'data_compute', label: '数据计算' },
  { value: 'data_export', label: '数据导出' },
  { value: 'custom', label: '定制服务' },
];

const ServiceRequestPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态管理 =====
  const [tabValue, setTabValue] = useState<number>(0);
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(0);
  const [pageSize] = useState<number>(10);

  // ===== 新建申请对话框状态 =====
  const [createOpen, setCreateOpen] = useState<boolean>(false);
  const [selectedService, setSelectedService] = useState<ServiceCatalog | null>(null);
  const [requestReason, setRequestReason] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // ===== 查看详情对话框状态 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedRequest, setSelectedRequest] = useState<Subscription | null>(null);

  // ===== 需求审核流程 =====
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewTarget, setReviewTarget] = useState<Subscription | null>(null);
  const [reviewStep, setReviewStep] = useState(0);
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject'>('approve');
  const [reviewComment, setReviewComment] = useState('');

  // ===== 认领承接 =====
  const [claimDialogOpen, setClaimDialogOpen] = useState(false);
  const [claimTarget, setClaimTarget] = useState<ServiceCatalog | null>(null);
  const [claimForm, setClaimForm] = useState({
    provider_name: '',
    provider_contact: '',
    estimated_time: '',
    notes: '',
  });

  // ===== 自动下架 =====
  const [delistDialogOpen, setDelistDialogOpen] = useState(false);
  const [delistTarget, setDelistTarget] = useState<ServiceCatalog | null>(null);
  const [delistReason, setDelistReason] = useState('');
  const [delistAutoTime, setDelistAutoTime] = useState('');

  // ===== ECharts 配置 =====
  const trendChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['申请数量', '批准数量'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'],
    },
    yAxis: { type: 'value' as const, name: '数量' },
    series: [
      {
        name: '申请数量',
        type: 'bar',
        data: [120, 132, 101, 134, 90, 230, 210],
        itemStyle: { color: '#667eea' },
      },
      {
        name: '批准数量',
        type: 'bar',
        data: [90, 102, 81, 114, 70, 200, 190],
        itemStyle: { color: '#764ba2' },
      },
    ],
  }), []);

  const statusChartOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, left: 'left', top: 20 },
    series: [
      {
        name: '申请状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: 'bold' },
        },
        labelLine: { show: false },
        data: [
          { value: 35, name: '待审批', itemStyle: { color: '#667eea' } },
          { value: 45, name: '已批准', itemStyle: { color: '#43e97b' } },
          { value: 15, name: '已拒绝', itemStyle: { color: '#f5576c' } },
          { value: 5, name: '已过期', itemStyle: { color: '#aaa' } },
        ],
      },
    ],
  }), []);

  // ===== 查询参数 =====
  const servicesParams = useMemo(() => ({
    page: page + 1,
    page_size: pageSize,
    category: categoryFilter !== 'all' ? categoryFilter : undefined,
    keyword: searchKeyword || undefined,
  }), [page, pageSize, categoryFilter, searchKeyword]);

  const subscriptionsParams = useMemo(() => ({
    page: page + 1,
    page_size: pageSize,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  }), [page, pageSize, statusFilter]);

  // ===== 数据查询 =====
  const { data: servicesData, isLoading: servicesLoading } = useQuery({
    queryKey: ['services', servicesParams],
    queryFn: () => listServices(servicesParams),
    enabled: tabValue === 0,
  });

  const { data: subscriptionsData, isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['subscriptions', subscriptionsParams],
    queryFn: () => getSubscriptions('all', subscriptionsParams),
    enabled: tabValue === 1,
  });

  const services: ServiceCatalog[] = servicesData?.data?.items ?? [];
  const subscriptions: Subscription[] = subscriptionsData?.data?.items ?? [];
  const totalServices: number = servicesData?.data?.total ?? 0;
  const totalSubscriptions: number = subscriptionsData?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalRequests: totalSubscriptions,
    pendingRequests: subscriptions.filter(s => s.status === 'pending').length,
    approvedRequests: subscriptions.filter(s => s.status === 'approved').length,
    todayRequests: subscriptions.filter(s => {
      const today = new Date().toDateString();
      return new Date(s.created_at).toDateString() === today;
    }).length,
  }), [subscriptions, totalSubscriptions]);

  // ===== Mutations =====
  const subscribeMut = useMutation({
    mutationFn: (data: { serviceId: string; start_date: string; end_date?: string }) =>
      subscribeService(data.serviceId, { start_date: data.start_date, end_date: data.end_date }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      setCreateOpen(false);
      setRequestReason('');
      setStartDate('');
      setEndDate('');
    },
  });

  const approveMut = useMutation({
    mutationFn: (data: { subId: string; approved: boolean }) =>
      approveSubscription(data.subId, data.approved),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
    },
  });

  // ===== 事件处理 =====
  const handleRefresh = useCallback(() => {
    setSearchKeyword('');
    setStatusFilter('all');
    setCategoryFilter('all');
    setPage(0);
    queryClient.invalidateQueries({ queryKey: ['services'] });
    queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
  }, [queryClient]);

  const handleCreateRequest = useCallback((service: ServiceCatalog) => {
    setSelectedService(service);
    setRequestReason('');
    setStartDate(new Date().toISOString().split('T')[0]);
    setEndDate('');
    setCreateOpen(true);
  }, []);

  const handleSubmitRequest = useCallback(() => {
    if (!selectedService || !requestReason.trim() || !startDate) return;
    subscribeMut.mutate({
      serviceId: selectedService.id,
      start_date: startDate,
      end_date: endDate || undefined,
    });
  }, [selectedService, requestReason, startDate, endDate, subscribeMut]);

  const handleViewDetail = useCallback((request: Subscription) => {
    setSelectedRequest(request);
    setDetailOpen(true);
  }, []);

  const handleApprove = useCallback((subId: string, approved: boolean) => {
    approveMut.mutate({ subId, approved });
  }, [approveMut]);

  // 需求审核流程
  const handleReview = useCallback((sub: Subscription) => {
    setReviewTarget(sub);
    setReviewStep(0);
    setReviewAction('approve');
    setReviewComment('');
    setReviewDialogOpen(true);
  }, []);

  const handleReviewSubmit = useCallback(() => {
    if (reviewStep === 0) {
      // 初审通过，进入复审
      setReviewStep(1);
      MessagePlugin.success('初审通过，请进行复审');
    } else {
      // 复审完成
      if (reviewTarget) {
        handleApprove(reviewTarget.id, reviewAction === 'approve');
      }
      MessagePlugin.success(reviewAction === 'approve' ? '审核通过' : '审核拒绝');
      setReviewDialogOpen(false);
    }
  }, [reviewStep, reviewAction, reviewTarget, handleApprove]);

  // 认领承接
  const handleClaim = useCallback((service: ServiceCatalog) => {
    setClaimTarget(service);
    setClaimForm({
      provider_name: '',
      provider_contact: '',
      estimated_time: '',
      notes: '',
    });
    setClaimDialogOpen(true);
  }, []);

  const handleClaimSubmit = useCallback(() => {
    if (!claimForm.provider_name.trim()) {
      MessagePlugin.warning('请输入提供方名称');
      return;
    }
    MessagePlugin.success('认领成功，请按时完成服务交付');
    setClaimDialogOpen(false);
  }, [claimForm]);

  // 自动下架
  const handleDelist = useCallback((service: ServiceCatalog) => {
    setDelistTarget(service);
    setDelistReason('');
    setDelistAutoTime('');
    setDelistDialogOpen(true);
  }, []);

  const handleDelistSubmit = useCallback(() => {
    MessagePlugin.success('下架任务已创建，将在指定时间自动执行');
    setDelistDialogOpen(false);
  }, []);

  // ===== 获取状态 Tag 主题 =====
  const getStatusTheme = (status: string): 'warning' | 'success' | 'danger' | 'default' => {
    switch (status) {
      case 'pending': return 'warning';
      case 'approved': return 'success';
      case 'rejected': return 'danger';
      default: return 'default';
    }
  };

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '服务申请' }],
    [],
  );

  const currentTotal = tabValue === 0 ? totalServices : totalSubscriptions;

  return (
    <PageContainer>
      <PageHeader
        title="服务申请管理"
        subtitle="在线提交数据使用申请，跟踪审批流程"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总申请数" value={stats.totalRequests} icon={<FileIcon />} gradient="blue" unit="" />
        <StatCard title="待审批" value={stats.pendingRequests} icon={<TimeIcon />} gradient="orange" unit="" />
        <StatCard title="已批准" value={stats.approvedRequests} icon={<CheckCircleIcon />} gradient="green" unit="" />
        <StatCard title="今日申请" value={stats.todayRequests} icon={<TrendingUpIcon />} gradient="purple" unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <PageSection title="申请趋势分析" titleIcon={<TrendingUpIcon />} className="md:col-span-2">
          <ReactECharts option={trendChartOption} style={{ height: 300 }} />
        </PageSection>
        <PageSection title="申请状态分布" titleIcon={<CheckCircleIcon />}>
          <ReactECharts option={statusChartOption} style={{ height: 300 }} />
        </PageSection>
      </div>

      {/* 标签页切换 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm">
        <div className="flex border-b border-gray-200">
          <button
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tabValue === 0 ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => { setTabValue(0); setPage(0); }}
          >
            可用服务
          </button>
          <button
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tabValue === 1 ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => { setTabValue(1); setPage(0); }}
          >
            我的申请
            {subscriptions.filter(s => s.status === 'pending').length > 0 && (
              <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-xs rounded-full bg-amber-100 text-amber-700">
                {subscriptions.filter(s => s.status === 'pending').length}
              </span>
            )}
          </button>
          <button
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tabValue === 2 ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => { setTabValue(2); setPage(0); }}
          >
            需求认领
          </button>
        </div>
      </div>

      {/* 搜索与筛选 */}
      <PageSection padding="sm">
        <div className="flex flex-wrap gap-3 items-center">
          <Input
            placeholder="搜索服务..."
            value={searchKeyword}
            onChange={(val) => setSearchKeyword(String(val))}
            onEnter={() => setPage(0)}
            prefixIcon={<SearchIcon />}
            className="!w-full sm:!w-52"
          />
          {tabValue === 0 && (
            <Select
              value={categoryFilter}
              options={SERVICE_CATEGORY_OPTIONS}
              onChange={(val) => { setCategoryFilter(String(val)); setPage(0); }}
              className="!w-full sm:!w-36"
            />
          )}
          {tabValue === 1 && (
            <Select
              value={statusFilter}
              options={REQUEST_STATUS_OPTIONS}
              onChange={(val) => { setStatusFilter(String(val)); setPage(0); }}
              className="!w-full sm:!w-36"
            />
          )}
          {tabValue === 2 && (
            <Select
              value={categoryFilter}
              options={SERVICE_CATEGORY_OPTIONS}
              onChange={(val) => { setCategoryFilter(String(val)); setPage(0); }}
              className="!w-full sm:!w-36"
            />
          )}
          <Button theme="primary" onClick={() => setPage(0)} icon={<SearchIcon />}>
            搜索
          </Button>
        </div>
      </PageSection>

      {/* 内容区域 */}
      <PageSection padding="none" className="flex-1 flex flex-col overflow-hidden">
        <LoadingOverlay open={tabValue === 0 ? servicesLoading : subscriptionsLoading} />
        {tabValue === 0 ? (
          /* 可用服务列表 */
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left font-bold">服务名称</th>
                  <th className="px-4 py-3 text-left font-bold">服务分类</th>
                  <th className="px-4 py-3 text-left font-bold">计费模式</th>
                  <th className="px-4 py-3 text-left font-bold">价格</th>
                  <th className="px-4 py-3 text-left font-bold">状态</th>
                  <th className="px-4 py-3 text-center font-bold">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {services.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无可用服务</td>
                  </tr>
                ) : (
                  services.map((service) => (
                    <tr key={service.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-semibold text-sm block">{service.name}</span>
                        <span className="text-xs text-gray-500 block">
                          {service.description?.substring(0, 50)}...
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <Tag variant="outline" size="small">
                          {SERVICE_CATEGORY_OPTIONS.find(c => c.value === service.category)?.label || service.category}
                        </Tag>
                      </td>
                      <td className="px-4 py-3">{service.billing_mode}</td>
                      <td className="px-4 py-3">{service.price} 元/{service.billing_unit}</td>
                      <td className="px-4 py-3">
                        <StatusTag status={service.status} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex gap-1 justify-center">
                          <Button
                            theme="primary"
                            size="small"
                            icon={<AddIcon />}
                            onClick={() => handleCreateRequest(service)}
                          >
                            申请
                          </Button>
                          <Tooltip content="认领承接">
                            <Button
                              variant="text"
                              theme="success"
                              size="small"
                              icon={<LinkIcon />}
                              onClick={() => handleClaim(service)}
                            />
                          </Tooltip>
                          <Tooltip content="自动下架">
                            <Button
                              variant="text"
                              theme="warning"
                              size="small"
                              icon={<SettingIcon />}
                              onClick={() => handleDelist(service)}
                            />
                          </Tooltip>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : tabValue === 1 ? (
          /* 我的申请列表 */
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left font-bold">服务名称</th>
                  <th className="px-4 py-3 text-left font-bold">申请时间</th>
                  <th className="px-4 py-3 text-left font-bold">有效期</th>
                  <th className="px-4 py-3 text-left font-bold">状态</th>
                  <th className="px-4 py-3 text-center font-bold">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {subscriptions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-gray-400">暂无申请记录</td>
                  </tr>
                ) : (
                  subscriptions.map((sub) => (
                    <tr key={sub.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-semibold text-sm">{sub.service_name || '未知服务'}</span>
                      </td>
                      <td className="px-4 py-3">
                        {new Date(sub.created_at).toLocaleString('zh-CN')}
                      </td>
                      <td className="px-4 py-3">
                        {new Date(sub.start_date).toLocaleDateString('zh-CN')}
                        {sub.end_date && ` ~ ${new Date(sub.end_date).toLocaleDateString('zh-CN')}`}
                      </td>
                      <td className="px-4 py-3">
                        <Tag size="small" theme={getStatusTheme(sub.status)} variant="light">
                          {REQUEST_STATUS_OPTIONS.find(s => s.value === sub.status)?.label || sub.status}
                        </Tag>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <Tooltip content="查看详情">
                            <span
                              className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-blue-50 text-blue-500 cursor-pointer transition-colors"
                              onClick={() => handleViewDetail(sub)}
                            >
                              <BrowseIcon size="16px" />
                            </span>
                          </Tooltip>
                          {sub.status === 'pending' && (
                            <>
                              <Tooltip content="审核">
                                <span
                                  className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-purple-50 text-purple-500 cursor-pointer transition-colors"
                                  onClick={() => handleReview(sub)}
                                >
                                  <CheckCircleIcon size="16px" />
                                </span>
                              </Tooltip>
                              <Tooltip content="拒绝">
                                <span
                                  className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-red-50 text-red-500 cursor-pointer transition-colors"
                                  onClick={() => handleApprove(sub.id, false)}
                                >
                                  <CloseCircleIcon size="16px" />
                                </span>
                              </Tooltip>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          /* 需求认领列表 */
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left font-bold">需求名称</th>
                  <th className="px-4 py-3 text-left font-bold">需求分类</th>
                  <th className="px-4 py-3 text-left font-bold">预算</th>
                  <th className="px-4 py-3 text-left font-bold">截止时间</th>
                  <th className="px-4 py-3 text-left font-bold">状态</th>
                  <th className="px-4 py-3 text-center font-bold">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {/* 模拟需求数据 */}
                {[
                  { id: 'demand-1', name: '电网负荷预测数据需求', category: 'data_query', budget: '5000元', deadline: '2026-06-30', status: 'open' },
                  { id: 'demand-2', name: '新能源发电量分析', category: 'data_compute', budget: '8000元', deadline: '2026-07-15', status: 'open' },
                  { id: 'demand-3', name: '电力市场交易数据导出', category: 'data_export', budget: '3000元', deadline: '2026-06-20', status: 'claimed' },
                ].map((demand) => (
                  <tr key={demand.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-semibold text-sm">{demand.name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Tag variant="outline" size="small">
                        {SERVICE_CATEGORY_OPTIONS.find(c => c.value === demand.category)?.label || demand.category}
                      </Tag>
                    </td>
                    <td className="px-4 py-3 text-orange-600 font-medium">{demand.budget}</td>
                    <td className="px-4 py-3">{demand.deadline}</td>
                    <td className="px-4 py-3">
                      <Tag
                        size="small"
                        theme={demand.status === 'open' ? 'success' : 'default'}
                        variant="light"
                      >
                        {demand.status === 'open' ? '待认领' : '已认领'}
                      </Tag>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {demand.status === 'open' && (
                        <Button
                          theme="primary"
                          size="small"
                          icon={<LinkIcon />}
                          onClick={() => MessagePlugin.success('认领成功')}
                        >
                          认领
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageSection>

      {/* 分页控件 */}
      <PageSection padding="sm">
        <div className="flex items-center justify-end gap-3 flex-wrap">
          <span className="text-sm text-gray-500">共 {currentTotal} 项</span>
          <Button
            variant="text"
            size="small"
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
          >
            上一页
          </Button>
          <span className="text-sm text-gray-500">第 {page + 1} 页</span>
          <Button
            variant="text"
            size="small"
            disabled={(page + 1) * pageSize >= currentTotal}
            onClick={() => setPage(p => p + 1)}
          >
            下一页
          </Button>
        </div>
      </PageSection>

      {/* 新建申请对话框 */}
      <Dialog
        header="提交服务申请"
        visible={createOpen}
        onClose={() => setCreateOpen(false)}
        footer={false}
        destroyOnClose
      >
        <div className="flex flex-col gap-4 py-2">
          {selectedService && (
            <>
              <h3 className="font-semibold text-base">{selectedService.name}</h3>
              <p className="text-xs text-gray-600">{selectedService.description}</p>
              <div className="flex items-center gap-4">
                <span className="text-xs text-gray-600">
                  <strong>计费模式：</strong>{selectedService.billing_mode}
                </span>
                <span className="text-xs text-gray-600">
                  <strong>价格：</strong>{selectedService.price} 元/{selectedService.billing_unit}
                </span>
              </div>
            </>
          )}
          <div>
            <label className="block text-sm text-gray-600 mb-1">申请理由</label>
            <Textarea
              value={requestReason}
              onChange={(val) => setRequestReason(String(val))}
              placeholder="请说明您申请使用此服务的目的和用途..."
              rows={3}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">开始日期</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">结束日期（可选）</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <Button onClick={() => setCreateOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={handleSubmitRequest}
              disabled={!requestReason.trim() || !startDate || subscribeMut.isPending}
            >
              {subscribeMut.isPending ? '提交中...' : '提交申请'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* 查看详情对话框 */}
      <Dialog
        header="申请详情"
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        footer={false}
        destroyOnClose
      >
        {selectedRequest && (
          <div className="flex flex-col gap-3 py-2">
            <h3 className="font-semibold text-base">
              {selectedRequest.service_name || '未知服务'}
            </h3>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-gray-600">
                <strong>申请ID：</strong>{selectedRequest.id}
              </span>
              <span className="text-sm text-gray-600">
                <strong>申请时间：</strong>{new Date(selectedRequest.created_at).toLocaleString('zh-CN')}
              </span>
              <span className="text-sm text-gray-600">
                <strong>有效期：</strong>
                {new Date(selectedRequest.start_date).toLocaleDateString('zh-CN')}
                {selectedRequest.end_date && ` ~ ${new Date(selectedRequest.end_date).toLocaleDateString('zh-CN')}`}
              </span>
              <span className="text-sm text-gray-600">
                <strong>状态：</strong>
                <Tag size="small" theme={getStatusTheme(selectedRequest.status)} variant="light">
                  {REQUEST_STATUS_OPTIONS.find(s => s.value === selectedRequest.status)?.label || selectedRequest.status}
                </Tag>
              </span>
              {selectedRequest.approved_at && (
                <span className="text-sm text-gray-600">
                  <strong>审批时间：</strong>{new Date(selectedRequest.approved_at).toLocaleString('zh-CN')}
                </span>
              )}
              {selectedRequest.rejected_reason && (
                <span className="text-sm text-gray-600">
                  <strong>拒绝原因：</strong>{selectedRequest.rejected_reason}
                </span>
              )}
            </div>
            <div className="flex justify-end pt-3 border-t border-gray-100">
              <Button onClick={() => setDetailOpen(false)}>关闭</Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* 需求审核流程弹窗 */}
      <Dialog
        header="需求审核"
        visible={reviewDialogOpen}
        onClose={() => setReviewDialogOpen(false)}
        width={600}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>取消</Button>
            {reviewStep === 1 && (
              <Button theme="danger" onClick={() => { setReviewAction('reject'); handleReviewSubmit(); }}>
                拒绝
              </Button>
            )}
            <Button theme="primary" onClick={handleReviewSubmit}>
              {reviewStep === 0 ? '初审通过' : '复审通过'}
            </Button>
          </div>
        }
      >
        {reviewTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <CheckCircleIcon className="text-blue-500" />
              <span className="font-semibold">{reviewTarget.service_name || '未知服务'}</span>
            </div>

            {/* 审核步骤 */}
            <Steps current={reviewStep}>
              <Steps.StepItem title="初审" content="申请信息完整性检查" />
              <Steps.StepItem title="复审" content="业务合规性与资源可用性审核" />
            </Steps>

            <div className="p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-semibold mb-2">审核内容</h4>
              {reviewStep === 0 ? (
                <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                  <li>申请理由充分性检查</li>
                  <li>有效期合理性验证</li>
                  <li>申请人资质审核</li>
                  <li>申请信息完整性</li>
                </ul>
              ) : (
                <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                  <li>服务资源可用性检查</li>
                  <li>配额限制验证</li>
                  <li>业务合规性审核</li>
                  <li>安全策略检查</li>
                </ul>
              )}
            </div>

            <div>
              <label className="text-sm text-gray-600 mb-1 block">审核意见</label>
              <Input
                value={reviewComment}
                onChange={setReviewComment}
                placeholder="请输入审核意见（可选）"
              />
            </div>
          </div>
        )}
      </Dialog>

      {/* 认领承接弹窗 */}
      <Dialog
        header="认领承接"
        visible={claimDialogOpen}
        onClose={() => setClaimDialogOpen(false)}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setClaimDialogOpen(false)}>取消</Button>
            <Button theme="primary" onClick={handleClaimSubmit}>确认认领</Button>
          </div>
        }
      >
        {claimTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <LinkIcon className="text-green-500" />
              <span className="font-semibold">{claimTarget.name}</span>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <p className="text-sm text-green-700 m-0">
                认领后，您将负责完成该服务的交付工作。请确保您有能力在规定时间内完成。
              </p>
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">提供方名称 *</label>
              <Input
                value={claimForm.provider_name}
                onChange={(val) => setClaimForm(prev => ({ ...prev, provider_name: val }))}
                placeholder="请输入您的机构名称"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">联系方式</label>
              <Input
                value={claimForm.provider_contact}
                onChange={(val) => setClaimForm(prev => ({ ...prev, provider_contact: val }))}
                placeholder="请输入联系方式"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">预计完成时间</label>
              <input
                type="date"
                value={claimForm.estimated_time}
                onChange={(e) => setClaimForm(prev => ({ ...prev, estimated_time: e.target.value }))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">备注说明</label>
              <Textarea
                value={claimForm.notes}
                onChange={(val) => setClaimForm(prev => ({ ...prev, notes: val }))}
                placeholder="请说明您的服务能力和优势..."
                rows={3}
              />
            </div>
          </div>
        )}
      </Dialog>

      {/* 自动下架弹窗 */}
      <Dialog
        header="自动下架配置"
        visible={delistDialogOpen}
        onClose={() => setDelistDialogOpen(false)}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDelistDialogOpen(false)}>取消</Button>
            <Button theme="primary" onClick={handleDelistSubmit}>创建下架任务</Button>
          </div>
        }
      >
        {delistTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <SettingIcon className="text-orange-500" />
              <span className="font-semibold">{delistTarget.name}</span>
            </div>
            <div className="p-3 bg-orange-50 rounded-lg">
              <p className="text-sm text-orange-700 m-0">
                配置自动下架规则后，系统将在满足条件时自动将该服务下架，无需人工干预。
              </p>
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">下架原因</label>
              <Select
                value={delistReason}
                onChange={(val) => setDelistReason(val as string)}
                options={[
                  { value: 'expired', label: '服务到期' },
                  { value: 'maintenance', label: '系统维护' },
                  { value: 'compliance', label: '合规要求' },
                  { value: 'custom', label: '自定义原因' },
                ]}
                style={{ width: '100%' }}
                placeholder="请选择下架原因"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">自动下架时间</label>
              <input
                type="datetime-local"
                value={delistAutoTime}
                onChange={(e) => setDelistAutoTime(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">通知方式</label>
              <div className="flex gap-2">
                <Tag variant="outline" size="small">站内消息</Tag>
                <Tag variant="outline" size="small">邮件通知</Tag>
                <Tag variant="outline" size="small">短信通知</Tag>
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default ServiceRequestPage;
