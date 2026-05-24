/**
 * 合规管理页面
 * 合规报告列表 + 生成报告 + 查看报告 + 合规检查清单
 */
import React, { useState, useMemo } from 'react';
import { Button, Input, Select, Tooltip, Dialog, Pagination } from 'tdesign-react';
import { AddIcon, BrowseIcon, ViewListIcon, RefreshIcon, ChartBarIcon, CheckCircleFilledIcon, TimeIcon } from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listComplianceReports, generateComplianceReport, getComplianceReport, getComplianceChecklist,
} from '@/api/ops';
import type { ComplianceReport } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

const REPORT_TYPE_OPTIONS = [
  { value: 'DATA_SHARING', label: '数据共享' },
  { value: 'PRIVACY', label: '隐私保护' },
  { value: 'SECURITY', label: '安全审计' },
];

const reportStatusLabel = (s: string): string => {
  const m: Record<string, string> = { DRAFT: '草稿', GENERATING: '生成中', COMPLETED: '已完成', FAILED: '失败' };
  return m[s] ?? s;
};

const reportStatusColor = (s: string): 'info' | 'warning' | 'success' | 'error' | 'default' => {
  const m: Record<string, 'info' | 'warning' | 'success' | 'error'> = {
    DRAFT: 'info', GENERATING: 'warning', COMPLETED: 'success', FAILED: 'error',
  };
  return m[s] ?? 'default';
};

const scoreColor = (score: number): string => {
  if (score >= 80) return '#4caf50';
  if (score >= 60) return '#ff9800';
  return '#f44336';
};

const OpsCompliancePage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const reportTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['生成报告', '通过报告'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '生成报告', type: 'bar', data: [18, 22, 25, 20, 28, 32, 35], itemStyle: { color: '#667eea' } },
      { name: '通过报告', type: 'bar', data: [15, 19, 22, 18, 25, 29, 32], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const reportTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '报告类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 68, name: '数据共享', itemStyle: { color: '#667eea' } },
          { value: 52, name: '隐私保护', itemStyle: { color: '#43e97b' } },
          { value: 36, name: '安全审计', itemStyle: { color: '#f093fb' } },
        ],
      },
    ],
  }), []);

  // ===== 筛选 & 分页 =====
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 生成报告弹窗 =====
  const [genOpen, setGenOpen] = useState<boolean>(false);
  const [genOrgId, setGenOrgId] = useState<string>('');
  const [genType, setGenType] = useState<string>('DATA_SHARING');
  const [genPeriod, setGenPeriod] = useState<string>('');

  // ===== 详情弹窗 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<ComplianceReport | null>(null);

  // ===== 检查清单弹窗 =====
  const [checklistOpen, setChecklistOpen] = useState<boolean>(false);
  const [checklistType, setChecklistType] = useState<string>('');

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['complianceReports', page, pageSize, filterType, filterStatus],
    queryFn: () => listComplianceReports({
      page: page + 1, page_size: pageSize,
      report_type: filterType || undefined,
      status: filterStatus || undefined,
    }),
  });

  const { data: checklistData, isLoading: checklistLoading } = useQuery({
    queryKey: ['complianceChecklist', checklistType],
    queryFn: () => getComplianceChecklist(checklistType || undefined),
    enabled: checklistOpen,
  });

  const items: ComplianceReport[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalReports: total,
    completedReports: items.filter(r => r.status === 'completed').length,
    pendingReports: items.filter(r => r.status === 'pending').length,
    averageScore: items.length > 0
      ? Number((items.reduce((sum, r) => sum + (r.compliance_score ?? 0), 0) / items.length).toFixed(1))
      : 0,
  }), [items, total]);

  // ===== Mutations =====
  const genMut = useMutation({
    mutationFn: (d: { organization_id: string; report_type: string; period: string }) => generateComplianceReport(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['complianceReports'] });
      setGenOpen(false);
      setGenOrgId(''); setGenType('DATA_SHARING'); setGenPeriod('');
    },
  });

  const detailMut = useMutation({
    mutationFn: (id: string) => getComplianceReport(id),
    onSuccess: (res) => {
      setDetailData(res.data ?? null);
      setDetailOpen(true);
    },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '合规管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '生成报告', icon: <AddIcon />, onClick: () => setGenOpen(true), variant: 'contained' },
      { label: '检查清单', icon: <ViewListIcon />, onClick: () => setChecklistOpen(true), variant: 'outlined' },
    ],
    [],
  );

  const typeFilterOptions = useMemo(() => [
    { label: '全部', value: '' },
    ...REPORT_TYPE_OPTIONS,
  ], []);

  const statusFilterOptions = useMemo(() => [
    { label: '全部', value: '' },
    { label: '草稿', value: 'DRAFT' },
    { label: '生成中', value: 'GENERATING' },
    { label: '已完成', value: 'COMPLETED' },
    { label: '失败', value: 'FAILED' },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="合规管理"
        subtitle="管理合规报告、生成报告与查看检查清单"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['complianceReports'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总报告数" value={stats.totalReports} icon={<ChartBarIcon />} gradient="purple" unit="" />
        <MetricsCard title="已完成" value={stats.completedReports} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="待生成" value={stats.pendingReports} icon={<TimeIcon />} color="warning" unit="" />
        <MetricsCard title="平均评分" value={stats.averageScore} icon={<ChartBarIcon />} gradient="red" unit="分" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2"><ChartCard title="报告生成趋势" option={reportTrendOption} height={300} /></div>
        <ChartCard title="报告类型分布" option={reportTypeOption} height={300} />
      </div>

      {/* 搜索过滤 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <div className="flex items-center gap-4">
          <Select
            value={filterType}
            onChange={(val) => { setFilterType(String(val)); setPage(0); }}
            options={typeFilterOptions}
            style={{ minWidth: 140 }}
            placeholder="报告类型"
          />
          <Select
            value={filterStatus}
            onChange={(val) => { setFilterStatus(String(val)); setPage(0); }}
            options={statusFilterOptions}
            style={{ minWidth: 140 }}
            placeholder="状态"
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm flex-1 flex flex-col overflow-hidden">
        <div className="overflow-auto flex-1">
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">组织 ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">报告类型</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">周期</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">状态</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">总体评分</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">生成时间</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 w-20">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 border-t border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-600">{row.organization_id}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{REPORT_TYPE_OPTIONS.find((o) => o.value === row.report_type)?.label ?? row.report_type}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{row.period}</td>
                  <td className="px-4 py-3">
                    <StatusTag status={reportStatusLabel(row.status)} color={reportStatusColor(row.status)} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm font-semibold" style={{ color: scoreColor(row.overall_score) }}>
                      {row.overall_score}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{row.generated_at ? new Date(row.generated_at).toLocaleString('zh-CN') : '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <Tooltip content="查看详情">
                      <span
                        className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500"
                        onClick={() => detailMut.mutate(row.id)}
                      >
                        <BrowseIcon size="16px" />
                      </span>
                    </Tooltip>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="border-t border-gray-200 px-4 py-3">
          <Pagination
            current={page + 1}
            total={total}
            pageSize={pageSize}
            pageSizeOptions={[10, 20, 50]}
            onChange={(pageInfo) => {
              setPage(pageInfo.current - 1);
            }}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(0);
            }}
            showJumper
            showPageSize
          />
        </div>
      </div>

      {/* 生成报告弹窗 */}
      <Dialog
        visible={genOpen}
        onClose={() => setGenOpen(false)}
        header="生成合规报告"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setGenOpen(false)}>取消</Button>
            <Button
              theme="primary"
              disabled={!genOrgId.trim() || !genPeriod.trim()}
              onClick={() => genMut.mutate({ organization_id: genOrgId, report_type: genType, period: genPeriod })}
            >
              生成
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">组织 ID</label>
            <Input value={genOrgId} onChange={setGenOrgId} placeholder="请输入组织 ID" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">报告类型</label>
            <Select value={genType} onChange={(val) => setGenType(String(val))} options={REPORT_TYPE_OPTIONS} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">周期</label>
            <Input value={genPeriod} onChange={setGenPeriod} placeholder="2024-Q1" />
          </div>
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        header="合规报告详情"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setDetailOpen(false)}>关闭</Button>
          </div>
        }
      >
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex gap-8">
              <div>
                <span className="text-xs text-gray-500">组织</span>
                <p className="text-sm">{detailData.organization_id}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">类型</span>
                <p className="text-sm">{REPORT_TYPE_OPTIONS.find((o) => o.value === detailData.report_type)?.label ?? detailData.report_type}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">状态</span>
                <StatusTag status={reportStatusLabel(detailData.status)} color={reportStatusColor(detailData.status)} />
              </div>
            </div>
            <div className="flex gap-8">
              <div>
                <span className="text-xs text-gray-500">总体评分</span>
                <h2 className="text-xl font-semibold" style={{ color: scoreColor(detailData.overall_score) }}>{detailData.overall_score}</h2>
              </div>
              <div>
                <span className="text-xs text-gray-500">周期</span>
                <p className="text-sm">{detailData.period}</p>
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500">发现项</span>
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 mt-1">
                <pre className="text-xs font-mono whitespace-pre-wrap max-h-[300px] overflow-auto">
                  {JSON.stringify(detailData.findings, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        ) : (
          <span className="text-sm text-gray-400">暂无数据</span>
        )}
      </Dialog>

      {/* 检查清单弹窗 */}
      <Dialog
        visible={checklistOpen}
        onClose={() => setChecklistOpen(false)}
        header="合规检查清单"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setChecklistOpen(false)}>关闭</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">报告类型</label>
            <Select
              value={checklistType}
              onChange={(val) => setChecklistType(String(val))}
              options={[{ label: '全部', value: '' }, ...REPORT_TYPE_OPTIONS]}
            />
          </div>
          {checklistLoading ? (
            <span className="text-sm text-gray-400">加载中...</span>
          ) : checklistData?.data ? (
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
              <pre className="text-xs font-mono whitespace-pre-wrap max-h-[400px] overflow-auto">
                {JSON.stringify(checklistData.data, null, 2)}
              </pre>
            </div>
          ) : (
            <span className="text-sm text-gray-400">暂无检查清单数据</span>
          )}
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default OpsCompliancePage;
