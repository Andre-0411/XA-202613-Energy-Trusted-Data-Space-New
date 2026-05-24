/**
 * 数据质量页面
 * 质量概览统计卡片 + 五维雷达图 + 质量报告表格 + ECharts 趋势图 + 触发检查
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Tag, Tooltip, Pagination } from 'tdesign-react';
import {
  RefreshIcon, PlayIcon, ChartIcon, CheckCircleIcon,
  ErrorCircleFilledIcon, TrendingUpIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listQualityReports, runQualityCheck, getQualityReport } from '@/api/data';
import { getQualityStatistics } from '@/api/dataCatalog';
import type { QualityReport } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

const DataQualityPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态 =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);
  const [filterAssetId, setFilterAssetId] = useState<string>('');

  // 检查弹窗
  const [checkAssetId, setCheckAssetId] = useState<string>('');
  const [checkDialogOpen, setCheckDialogOpen] = useState<boolean>(false);

  // 报告详情弹窗
  const [reportDetail, setReportDetail] = useState<QualityReport | null>(null);
  const [reportDetailOpen, setReportDetailOpen] = useState<boolean>(false);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['qualityReports', page, pageSize, filterAssetId],
    queryFn: () =>
      listQualityReports({
        page: page + 1,
        page_size: pageSize,
        asset_id: filterAssetId || undefined,
      }),
  });

  const items: QualityReport[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 质量统计数据查询 =====
  const { data: qualityStats } = useQuery({
    queryKey: ['qualityStatistics'],
    queryFn: () => getQualityStatistics(),
    refetchInterval: 30000,
  });

  const qualityData = qualityStats?.data;

  // ===== 统计数据 =====
  const stats = useMemo(() => {
    const totalChecks = qualityData?.checked_assets ?? items.length;
    const passCount = items.filter((r) => r.overall_score >= 80).length;
    const passRate = totalChecks > 0 ? parseFloat(((passCount / totalChecks) * 100).toFixed(1)) : 0;
    const anomalyCount = items.filter((r) => r.overall_score < 60).length;
    const avgScore = qualityData?.avg_score ? parseFloat(qualityData.avg_score.toFixed(1)) : 0;
    return { totalChecks, passRate, anomalyCount, avgScore };
  }, [items, qualityData]);

  // ===== Mutations =====
  const checkMut = useMutation({
    mutationFn: (assetId: string) => runQualityCheck(assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['qualityReports'] });
      setCheckDialogOpen(false);
      setCheckAssetId('');
    },
  });

  const getReportMut = useMutation({
    mutationFn: (id: string) => getQualityReport(id),
    onSuccess: (res) => {
      setReportDetail(res.data ?? null);
      setReportDetailOpen(true);
    },
  });

  // ===== 质量等级颜色 =====
  const gradeTheme = (grade: string): 'success' | 'primary' | 'warning' | 'danger' | 'default' => {
    const map: Record<string, 'success' | 'primary' | 'warning' | 'danger'> = {
      A: 'success', B: 'primary', C: 'warning', D: 'danger', F: 'danger',
    };
    return map[grade] ?? 'default';
  };

  // ===== 分数颜色 =====
  const scoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据质量' }],
    [],
  );

  // ===== ECharts 趋势图 =====
  const trendChartOption = useMemo(() => {
    const dated = items
      .filter(r => r.generated_at)
      .slice()
      .sort((a, b) => new Date(a.generated_at!).getTime() - new Date(b.generated_at!).getTime());
    const dates = dated.map((r) => new Date(r.generated_at!).toLocaleDateString('zh-CN'));
    const scores = dated.map((r) => r.overall_score);

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['综合评分'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates, boundaryGap: false },
      yAxis: { type: 'value', min: 0, max: 100, name: '分数' },
      series: [
        {
          name: '综合评分',
          type: 'line',
          data: scores,
          smooth: true,
          lineStyle: { width: 3 },
          areaStyle: { opacity: 0.15 },
          itemStyle: { color: '#2196f3' },
        },
      ],
    };
  }, [items]);

  // ===== 五维雷达图 =====
  const radarChartOption = useMemo(() => {
    const dimensionAverages = qualityData?.dimension_averages ?? {};
    const dimensions = ['completeness', 'accuracy', 'consistency', 'timeliness', 'uniqueness'];
    const labels = ['完整性', '准确性', '一致性', '时效性', '唯一性'];

    return {
      tooltip: { trigger: 'item' },
      radar: {
        indicator: labels.map(label => ({ name: label, max: 100 })),
        shape: 'circle',
        splitNumber: 5,
        axisName: { color: '#333' },
        splitLine: { lineStyle: { color: ['#ddd'] } },
        splitArea: { show: true, areaStyle: { color: ['rgba(66,133,244,0.05)', 'rgba(66,133,244,0.1)'] } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: dimensions.map(d => dimensionAverages[d] ?? 0),
          name: '质量评分',
          areaStyle: { color: 'rgba(66,133,244,0.2)' },
          lineStyle: { color: '#4285f4', width: 2 },
          itemStyle: { color: '#4285f4' },
        }],
      }],
    };
  }, [qualityData]);

  return (
    <PageContainer>
      <PageHeader
        title="数据质量"
        subtitle="数据质量检查、报告与趋势分析"
        breadcrumbs={breadcrumbs}
        actions={[
          {
            label: '触发检查',
            icon: <PlayIcon />,
            onClick: () => setCheckDialogOpen(true),
            variant: 'contained',
          },
        ]}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['qualityReports'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总检查数" value={stats.totalChecks} icon={<ChartIcon />} gradient="blue" unit="" />
        <StatCard title="通过率" value={stats.passRate} icon={<CheckCircleIcon />} gradient="green" unit="%" />
        <StatCard title="异常数" value={stats.anomalyCount} icon={<ErrorCircleFilledIcon />} gradient="red" unit="" />
        <StatCard title="平均分" value={stats.avgScore} icon={<TrendingUpIcon />} gradient="orange" unit="" />
      </StatGrid>

      {/* 质量趋势图和雷达图 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PageSection title="质量趋势" titleIcon={<TrendingUpIcon />} className="md:col-span-2">
          <ReactECharts option={trendChartOption} style={{ height: 260 }} />
        </PageSection>
        <PageSection title="五维质量雷达图" titleIcon={<ChartIcon />}>
          <ReactECharts option={radarChartOption} style={{ height: 260 }} />
        </PageSection>
      </div>

      {/* 搜索过滤栏 */}
      <PageSection padding="sm">
        <div className="flex items-center gap-3">
          <Input
            value={filterAssetId}
            onChange={(val) => { setFilterAssetId(String(val)); setPage(0); }}
            placeholder="输入资产 ID 过滤..."
            prefixIcon={<ChartIcon />}
            className="!w-[300px]"
            onEnter={() => setPage(0)}
          />
        </div>
      </PageSection>

      {/* 数据表格 */}
      <PageSection padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">资产 ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">完整性</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">准确性</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">一致性</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">时效性</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">综合分</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">等级</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">检查时间</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <Tag theme="primary" variant="outline" size="small">
                      {row.asset_id.slice(0, 8)}
                    </Tag>
                  </td>
                  <td className={`px-4 py-3 font-semibold ${scoreColor(row.completeness)}`}>
                    {row.completeness.toFixed(1)}
                  </td>
                  <td className={`px-4 py-3 font-semibold ${scoreColor(row.accuracy)}`}>
                    {row.accuracy.toFixed(1)}
                  </td>
                  <td className={`px-4 py-3 font-semibold ${scoreColor(row.consistency)}`}>
                    {row.consistency.toFixed(1)}
                  </td>
                  <td className={`px-4 py-3 font-semibold ${scoreColor(row.timeliness)}`}>
                    {row.timeliness.toFixed(1)}
                  </td>
                  <td className={`px-4 py-3 font-semibold ${scoreColor(row.overall_score)}`}>
                    {row.overall_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <Tag theme={gradeTheme(row.grade)} size="small">{row.grade}</Tag>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {row.generated_at ? new Date(row.generated_at).toLocaleString('zh-CN') : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Tooltip content="查看详情">
                      <span
                        className="cursor-pointer hover:bg-gray-100 rounded p-1.5 inline-flex items-center text-blue-500"
                        onClick={() => getReportMut.mutate(row.id)}
                      >
                        <ChartIcon className="text-sm" />
                      </span>
                    </Tooltip>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {total > 0 && (
          <div className="flex justify-center py-3 border-t border-gray-100">
            <Pagination
              current={page + 1}
              total={total}
              pageSize={pageSize}
              showPageSize
              pageSizeOptions={[10, 20, 50]}
              onChange={(pageInfo) => {
                setPage(pageInfo.current - 1);
                setPageSize(pageInfo.pageSize);
              }}
            />
          </div>
        )}
      </PageSection>

      {/* 触发检查弹窗 */}
      <Dialog
        visible={checkDialogOpen}
        onClose={() => setCheckDialogOpen(false)}
        header="触发质量检查"
        width={480}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => { setCheckDialogOpen(false); setCheckAssetId(''); }}>取消</Button>
            <Button
              theme="primary"
              disabled={!checkAssetId.trim()}
              loading={checkMut.isPending}
              onClick={() => checkMut.mutate(checkAssetId)}
            >
              执行检查
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-600">
            输入要检查的数据资产 ID，系统将执行质量检查并生成报告。
          </p>
          <Input
            value={checkAssetId}
            onChange={(val) => setCheckAssetId(String(val))}
            placeholder="请输入资产 ID"
          />
        </div>
      </Dialog>

      {/* 报告详情弹窗 */}
      <Dialog
        visible={reportDetailOpen}
        onClose={() => setReportDetailOpen(false)}
        header="质量报告详情"
        width={640}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setReportDetailOpen(false)}>关闭</Button>
          </div>
        }
      >
        {reportDetail ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-6">
              <div>
                <p className="text-xs text-gray-500">资产 ID</p>
                <p className="text-sm font-medium text-gray-800">{reportDetail.asset_id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">等级</p>
                <Tag theme={gradeTheme(reportDetail.grade)} size="small">{reportDetail.grade}</Tag>
              </div>
              <div>
                <p className="text-xs text-gray-500">综合分</p>
                <p className={`text-sm font-semibold ${scoreColor(reportDetail.overall_score)}`}>
                  {reportDetail.overall_score.toFixed(1)}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: '完整性', value: reportDetail.completeness },
                { label: '准确性', value: reportDetail.accuracy },
                { label: '一致性', value: reportDetail.consistency },
                { label: '时效性', value: reportDetail.timeliness },
              ].map((dim) => (
                <div key={dim.label} className="text-center">
                  <p className="text-xs text-gray-500">{dim.label}</p>
                  <p className={`text-lg font-semibold ${scoreColor(dim.value)}`}>
                    {dim.value.toFixed(1)}
                  </p>
                </div>
              ))}
            </div>
            {reportDetail.details && (
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
                <p className="text-sm font-semibold text-gray-700 mb-2">详细数据</p>
                <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-48">
                  {JSON.stringify(reportDetail.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500 text-center py-4">暂无报告数据</p>
        )}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default DataQualityPage;
