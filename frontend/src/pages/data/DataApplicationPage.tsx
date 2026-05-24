/**
 * 服务申请审批页面
 * 我的申请 / 待我审批 / 全部申请
 * 支持提交申请、审批通过、审批拒绝、查看详情
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, MessagePlugin, Textarea, Dialog } from 'tdesign-react';
import { SearchIcon, RefreshIcon, BrowseIcon, CheckCircleIcon, CloseCircleIcon, ViewListIcon, TimeIcon } from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getApplications, getApplicationStats, getApplicationDetail,
  approveApplication, rejectApplication,
  type DataApplication, type ApplicationStats, type ApplicationScope,
} from '@/api/dataApplication';
import type { PaginatedRequest } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';

/** 申请状态选项 */
const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'pending', label: '待审批' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' },
];

/** 状态主题映射 (TDesign Tag theme) */
const STATUS_THEME_MAP: Record<string, 'warning' | 'success' | 'danger' | 'default'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
};

/** 状态标签映射 */
const STATUS_LABEL_MAP: Record<string, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
};

const DataApplicationPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== Tab 状态 =====
  const [tabValue, setTabValue] = useState<number>(0);

  // ===== 搜索与筛选状态 =====
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // ===== 分页状态 =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 详情对话框状态 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedApplication, setSelectedApplication] = useState<DataApplication | null>(null);

  // ===== 审批对话框状态 =====
  const [approveOpen, setApproveOpen] = useState<boolean>(false);
  const [rejectOpen, setRejectOpen] = useState<boolean>(false);
  const [approveComment, setApproveComment] = useState<string>('');
  const [rejectReason, setRejectReason] = useState<string>('');
  const [rejectComment, setRejectComment] = useState<string>('');

  // ===== 当前 Tab 对应的 scope =====
  const currentScope: ApplicationScope = useMemo(() => {
    switch (tabValue) {
      case 0: return 'mine';
      case 1: return 'pending_approval';
      case 2: return 'all';
      default: return 'mine';
    }
  }, [tabValue]);

  // ===== ECharts 配置 =====
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
          label: { show: true, fontSize: 18, fontWeight: 'bold' },
        },
        labelLine: { show: false },
        data: [
          { value: 0, name: '待审批', itemStyle: { color: '#ff9800' } },
          { value: 0, name: '已通过', itemStyle: { color: '#4caf50' } },
          { value: 0, name: '已拒绝', itemStyle: { color: '#f44336' } },
        ],
      },
    ],
  }), []);

  const trendChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['申请数量', '审批数量'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'],
    },
    yAxis: { type: 'value' as const, name: '数量' },
    series: [
      {
        name: '申请数量',
        type: 'line',
        smooth: true,
        data: [15, 22, 18, 25, 30, 28, 35],
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.05)' },
            ],
          },
        },
        itemStyle: { color: '#667eea' },
      },
      {
        name: '审批数量',
        type: 'line',
        smooth: true,
        data: [12, 20, 15, 22, 28, 25, 32],
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(76, 175, 80, 0.5)' },
              { offset: 1, color: 'rgba(76, 175, 80, 0.05)' },
            ],
          },
        },
        itemStyle: { color: '#4caf50' },
      },
    ],
  }), []);

  // ===== 查询参数 =====
  const queryParams = useMemo(() => ({
    page: page + 1,
    page_size: pageSize,
    scope: currentScope,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    keyword: searchKeyword.trim() || undefined,
  }), [page, pageSize, currentScope, statusFilter, searchKeyword]);

  // ===== 数据查询 =====
  const { data: applicationsData, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dataApplications', queryParams],
    queryFn: () => getApplications(queryParams),
  });

  const { data: statsData } = useQuery({
    queryKey: ['applicationStats'],
    queryFn: getApplicationStats,
  });

  const applications: DataApplication[] = applicationsData?.data?.items ?? [];
  const totalCount: number = applicationsData?.data?.total ?? 0;
  const rawStats = statsData?.data ?? {};
  const stats = {
    total_applications: rawStats.total ?? rawStats.total_applications ?? 0,
    pending_count: rawStats.pending ?? rawStats.pending_count ?? 0,
    approved_count: rawStats.approved ?? rawStats.approved_count ?? 0,
    rejected_count: rawStats.rejected ?? rawStats.rejected_count ?? 0,
  };

  // ===== 更新图表数据 =====
  const statusChartWithData = useMemo(() => ({
    ...statusChartOption,
    series: [{
      ...statusChartOption.series[0],
      data: [
        { value: stats.pending_count, name: '待审批', itemStyle: { color: '#ff9800' } },
        { value: stats.approved_count, name: '已通过', itemStyle: { color: '#4caf50' } },
        { value: stats.rejected_count, name: '已拒绝', itemStyle: { color: '#f44336' } },
      ],
    }],
  }), [statusChartOption, stats]);

  // ===== Mutations =====
  const approveMut = useMutation({
    mutationFn: (data: { id: string; comment?: string }) =>
      approveApplication(data.id, { comment: data.comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataApplications'] });
      queryClient.invalidateQueries({ queryKey: ['applicationStats'] });
      setApproveOpen(false);
      setApproveComment('');
      MessagePlugin.success('审批通过成功');
    },
    onError: () => {
      MessagePlugin.error('审批操作失败');
    },
  });

  const rejectMut = useMutation({
    mutationFn: (data: { id: string; reason: string; comment?: string }) =>
      rejectApplication(data.id, { reason: data.reason, comment: data.comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataApplications'] });
      queryClient.invalidateQueries({ queryKey: ['applicationStats'] });
      setRejectOpen(false);
      setRejectReason('');
      setRejectComment('');
      MessagePlugin.success('审批拒绝成功');
    },
    onError: () => {
      MessagePlugin.error('审批操作失败');
    },
  });

  // ===== 事件处理 =====
  const handleRefresh = useCallback(() => {
    setSearchKeyword('');
    setStatusFilter('all');
    setPage(0);
    queryClient.invalidateQueries({ queryKey: ['dataApplications'] });
    queryClient.invalidateQueries({ queryKey: ['applicationStats'] });
  }, [queryClient]);

  const handleSearch = useCallback(() => {
    setPage(0);
    refetch();
  }, [refetch]);

  const handleViewDetail = useCallback((app: DataApplication) => {
    setSelectedApplication(app);
    setDetailOpen(true);
  }, []);

  const handleApprove = useCallback((app: DataApplication) => {
    setSelectedApplication(app);
    setApproveComment('');
    setApproveOpen(true);
  }, []);

  const handleReject = useCallback((app: DataApplication) => {
    setSelectedApplication(app);
    setRejectReason('');
    setRejectComment('');
    setRejectOpen(true);
  }, []);

  const handleSubmitApprove = useCallback(() => {
    if (!selectedApplication) return;
    approveMut.mutate({ id: selectedApplication.id, comment: approveComment || undefined });
  }, [selectedApplication, approveComment, approveMut]);

  const handleSubmitReject = useCallback(() => {
    if (!selectedApplication || !rejectReason.trim()) return;
    rejectMut.mutate({
      id: selectedApplication.id,
      reason: rejectReason,
      comment: rejectComment || undefined,
    });
  }, [selectedApplication, rejectReason, rejectComment, rejectMut]);

  return (
    <PageContainer>
      <PageHeader
        title="服务申请审批"
        subtitle="管理数据资产使用申请和审批流程"
        breadcrumbs={[homeBreadcrumb]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid>
        <StatCard title="总申请数" value={stats.total_applications} icon={<ViewListIcon />} gradient="blue" unit="" />
        <StatCard title="待审批" value={stats.pending_count} icon={<TimeIcon />} gradient="orange" unit="" />
        <StatCard title="已通过" value={stats.approved_count} icon={<CheckCircleIcon />} gradient="green" unit="" />
        <StatCard title="已拒绝" value={stats.rejected_count} icon={<CloseCircleIcon />} gradient="red" unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <PageSection title="申请趋势">
            <ReactECharts option={trendChartOption} style={{ height: 280 }} />
          </PageSection>
        </div>
        <div>
          <PageSection title="申请状态分布">
            <ReactECharts option={statusChartWithData} style={{ height: 280 }} />
          </PageSection>
        </div>
      </div>

      {/* Tab 切换 + 搜索 + 表格 */}
      <PageSection>
        {/* Tab buttons */}
        <div className="flex border-b border-gray-200 mb-4">
          {[
            { label: '我的申请', icon: <ViewListIcon /> },
            { label: '待我审批', icon: <CheckCircleIcon /> },
            { label: '全部申请', icon: <ViewListIcon /> },
          ].map((tab, idx) => (
            <button
              key={idx}
              className={`px-4 py-2 text-sm font-medium flex items-center gap-1.5 transition-colors ${
                tabValue === idx
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => { setTabValue(idx); setPage(0); }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* 搜索与筛选 */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <Input
            value={searchKeyword}
            onChange={(val) => setSearchKeyword(String(val))}
            placeholder="搜索申请..."
            prefixIcon={<SearchIcon />}
            className="!w-[280px]"
            onEnter={handleSearch}
          />
          <Select
            value={statusFilter}
            onChange={(val) => { setStatusFilter(String(val)); setPage(0); }}
            options={STATUS_OPTIONS}
            style={{ width: 120 }}
          />
          <Button theme="primary" icon={<SearchIcon />} onClick={handleSearch}>
            搜索
          </Button>
        </div>

        {/* 错误状态 */}
        {isError && (
          <div className="text-center py-8">
            <p className="text-red-500 mb-2">加载失败: {(error as Error)?.message || '未知错误'}</p>
            <Button theme="primary" onClick={() => refetch()}>重试</Button>
          </div>
        )}

        {/* 表格 */}
        {!isError && (
          <LoadingOverlay open={isLoading}>
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 text-left text-sm text-gray-500">
                  <th className="px-4 py-3 font-medium">申请编号</th>
                  <th className="px-4 py-3 font-medium">资产名称</th>
                  <th className="px-4 py-3 font-medium">申请人</th>
                  <th className="px-4 py-3 font-medium">申请用途</th>
                  <th className="px-4 py-3 font-medium">状态</th>
                  <th className="px-4 py-3 font-medium">申请时间</th>
                  <th className="px-4 py-3 font-medium text-center">操作</th>
                </tr>
              </thead>
              <tbody>
                {applications.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                      暂无申请记录
                    </td>
                  </tr>
                ) : (
                  applications.map((app) => (
                    <tr key={app.id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono">{app.application_no}</td>
                      <td className="px-4 py-3 text-sm font-medium">{app.asset_name}</td>
                      <td className="px-4 py-3 text-sm">{app.applicant_name}</td>
                      <td className="px-4 py-3 text-sm max-w-[200px] truncate">{app.purpose}</td>
                      <td className="px-4 py-3">
                        <Tag theme={STATUS_THEME_MAP[app.status] || 'default'} variant="light">
                          {STATUS_LABEL_MAP[app.status] || app.status}
                        </Tag>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(app.created_at).toLocaleDateString('zh-CN')}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Tooltip content="查看详情">
                            <Button variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(app)} />
                          </Tooltip>
                          {tabValue === 1 && app.status === 'pending' && (
                            <>
                              <Tooltip content="审批通过">
                                <Button variant="text" theme="success" icon={<CheckCircleIcon />} onClick={() => handleApprove(app)} />
                              </Tooltip>
                              <Tooltip content="审批拒绝">
                                <Button variant="text" theme="danger" icon={<CloseCircleIcon />} onClick={() => handleReject(app)} />
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
          </LoadingOverlay>
        )}

        {/* 分页 */}
        {totalCount > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 mt-2">
            <span className="text-sm text-gray-500">共 {totalCount} 条</span>
            <div className="flex items-center gap-2">
              <select
                className="border border-gray-300 rounded px-2 py-1 text-sm"
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
              >
                {[10, 20, 50].map((n) => <option key={n} value={n}>{n} 条/页</option>)}
              </select>
              <Button variant="text" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                上一页
              </Button>
              <span className="text-sm text-gray-500">第 {page + 1} 页</span>
              <Button variant="text" disabled={(page + 1) * pageSize >= totalCount} onClick={() => setPage((p) => p + 1)}>
                下一页
              </Button>
            </div>
          </div>
        )}
      </PageSection>

      {/* 详情对话框 */}
      <Dialog
        header="申请详情"
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={680}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setDetailOpen(false)}>关闭</Button>
            {selectedApplication && tabValue === 1 && selectedApplication.status === 'pending' && (
              <>
                <Button theme="success" icon={<CheckCircleIcon />} onClick={() => { setDetailOpen(false); handleApprove(selectedApplication); }}>
                  审批通过
                </Button>
                <Button theme="danger" icon={<CloseCircleIcon />} onClick={() => { setDetailOpen(false); handleReject(selectedApplication); }}>
                  审批拒绝
                </Button>
              </>
            )}
          </div>
        }
      >
        {selectedApplication && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">申请编号</p>
              <p className="text-sm font-mono">{selectedApplication.application_no}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">资产名称</p>
              <p className="text-sm font-medium">{selectedApplication.asset_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">申请人</p>
              <p className="text-sm">{selectedApplication.applicant_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">申请用途</p>
              <p className="text-sm">{selectedApplication.purpose}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">使用天数</p>
              <p className="text-sm">{selectedApplication.duration_days} 天</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">有效期</p>
              <p className="text-sm">
                {selectedApplication.validity_start && selectedApplication.validity_end
                  ? `${selectedApplication.validity_start} 至 ${selectedApplication.validity_end}`
                  : '未设置'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">状态</p>
              <Tag theme={STATUS_THEME_MAP[selectedApplication.status] || 'default'} variant="light">
                {STATUS_LABEL_MAP[selectedApplication.status] || selectedApplication.status}
              </Tag>
            </div>
            <div>
              <p className="text-sm text-gray-500">审批人</p>
              <p className="text-sm">{selectedApplication.reviewer_name || '-'}</p>
            </div>
            <div className="col-span-2">
              <p className="text-sm text-gray-500">审批意见</p>
              <p className="text-sm">{selectedApplication.review_comment || '-'}</p>
            </div>
            {selectedApplication.reject_reason && (
              <div className="col-span-2">
                <p className="text-sm text-gray-500">拒绝原因</p>
                <p className="text-sm text-red-500">{selectedApplication.reject_reason}</p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-500">申请时间</p>
              <p className="text-sm">{new Date(selectedApplication.created_at).toLocaleString('zh-CN')}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">更新时间</p>
              <p className="text-sm">{new Date(selectedApplication.updated_at).toLocaleString('zh-CN')}</p>
            </div>
          </div>
        )}
      </Dialog>

      {/* 审批通过对话框 */}
      <Dialog
        header="审批通过"
        visible={approveOpen}
        onClose={() => setApproveOpen(false)}
        width={480}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setApproveOpen(false)}>取消</Button>
            <Button theme="success" loading={approveMut.isPending} onClick={handleSubmitApprove}>
              {approveMut.isPending ? '处理中...' : '确认通过'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
            确认通过该申请？通过后申请人将获得数据资产的访问权限。
          </div>
          <p className="text-base font-semibold">{selectedApplication?.asset_name}</p>
          <p className="text-sm text-gray-500">申请人：{selectedApplication?.applicant_name}</p>
          <Textarea
            value={approveComment}
            onChange={(val) => setApproveComment(String(val))}
            placeholder="请输入审批意见..."
            rows={3}
          />
        </div>
      </Dialog>

      {/* 审批拒绝对话框 */}
      <Dialog
        header="审批拒绝"
        visible={rejectOpen}
        onClose={() => setRejectOpen(false)}
        width={480}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setRejectOpen(false)}>取消</Button>
            <Button theme="danger" loading={rejectMut.isPending} disabled={!rejectReason.trim()} onClick={handleSubmitReject}>
              {rejectMut.isPending ? '处理中...' : '确认拒绝'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-sm text-orange-700">
            拒绝该申请后，申请人将收到拒绝通知。
          </div>
          <p className="text-base font-semibold">{selectedApplication?.asset_name}</p>
          <p className="text-sm text-gray-500">申请人：{selectedApplication?.applicant_name}</p>
          <div>
            <p className="text-sm text-gray-600 mb-1">拒绝原因 *</p>
            <Textarea
              value={rejectReason}
              onChange={(val) => setRejectReason(String(val))}
              placeholder="请说明拒绝原因..."
              rows={2}
            />
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">补充说明（可选）</p>
            <Textarea
              value={rejectComment}
              onChange={(val) => setRejectComment(String(val))}
              placeholder="可选补充说明..."
              rows={2}
            />
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default DataApplicationPage;
