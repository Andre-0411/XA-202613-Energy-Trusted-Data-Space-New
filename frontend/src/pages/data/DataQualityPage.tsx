/**
 * 数据质量评价页面（增强版）
 * 质量概览 + 质量检查 + 质量报告 + 质量监控
 * 基于可信数据空间标准体系的五维质量评价
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Tag, Tooltip, Pagination, Tabs, Select, MessagePlugin } from 'tdesign-react';
import {
  RefreshIcon, PlayIcon, ChartIcon, CheckCircleIcon,
  ErrorCircleFilledIcon, TrendingUpIcon, TimeIcon,
  BrowseIcon, AddIcon, NotificationIcon, DataBaseIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listQualityReports, runQualityCheck, getQualityReport } from '@/api/data';
import { getQualityStatistics } from '@/api/dataCatalog';
import type { QualityReport } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid } from '@/components/common';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

/* ========== 模拟质量检查规则 ========== */
interface QualityRule {
  id: string;
  name: string;
  dimension: string;
  description: string;
  threshold: number;
  status: string;
  last_run: string;
  pass_rate: number;
}

const MOCK_RULES: QualityRule[] = [
  { id: 'rule-001', name: '非空字段检查', dimension: '完整性', description: '检查必填字段是否存在空值', threshold: 99, status: 'active', last_run: '2025-05-23T10:00:00Z', pass_rate: 99.2 },
  { id: 'rule-002', name: '数值范围校验', dimension: '准确性', description: '验证数值字段是否在合理范围内', threshold: 95, status: 'active', last_run: '2025-05-23T10:00:00Z', pass_rate: 97.8 },
  { id: 'rule-003', name: '数据时效性检查', dimension: '时效性', description: '检查数据更新时间是否在规定延迟内', threshold: 90, status: 'active', last_run: '2025-05-23T10:00:00Z', pass_rate: 94.5 },
  { id: 'rule-004', name: '跨源一致性校验', dimension: '一致性', description: '对比多源数据的一致性', threshold: 85, status: 'active', last_run: '2025-05-23T10:00:00Z', pass_rate: 92.1 },
  { id: 'rule-005', name: '主键唯一性检查', dimension: '唯一性', description: '检查主键字段是否存在重复', threshold: 100, status: 'active', last_run: '2025-05-23T10:00:00Z', pass_rate: 99.8 },
  { id: 'rule-006', name: '格式规范检查', dimension: '准确性', description: '验证数据格式是否符合规范定义', threshold: 95, status: 'active', last_run: '2025-05-22T14:00:00Z', pass_rate: 96.3 },
  { id: 'rule-007', name: '关联完整性检查', dimension: '完整性', description: '检查外键关联数据是否完整', threshold: 98, status: 'warning', last_run: '2025-05-22T14:00:00Z', pass_rate: 88.5 },
  { id: 'rule-008', name: '数据新鲜度监控', dimension: '时效性', description: '监控数据源的更新频率', threshold: 90, status: 'active', last_run: '2025-05-23T08:00:00Z', pass_rate: 91.2 },
];

/* ========== 模拟质量告警 ========== */
interface QualityAlert {
  id: string;
  asset_name: string;
  dimension: string;
  severity: string;
  message: string;
  triggered_at: string;
  status: string;
}

const MOCK_ALERTS: QualityAlert[] = [
  { id: 'alert-001', asset_name: '储能调度数据', dimension: '时效性', severity: 'high', message: '数据更新延迟超过30分钟，当前延迟: 45分钟', triggered_at: '2025-05-23T09:30:00Z', status: 'active' },
  { id: 'alert-002', asset_name: '光伏发电出力数据', dimension: '完整性', severity: 'medium', message: '缺失率达5.2%，超过阈值3%', triggered_at: '2025-05-23T08:15:00Z', status: 'active' },
  { id: 'alert-003', asset_name: '用户用电量统计', dimension: '一致性', severity: 'low', message: '营销系统与计量系统数据偏差0.8%', triggered_at: '2025-05-22T16:00:00Z', status: 'resolved' },
  { id: 'alert-004', asset_name: '碳排放监测数据', dimension: '准确性', severity: 'high', message: '检测到异常值，3个监测点数据超出历史波动范围', triggered_at: '2025-05-23T07:45:00Z', status: 'active' },
];

const ALERT_SEVERITY_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  high: { label: '严重', theme: 'danger' },
  medium: { label: '警告', theme: 'warning' },
  low: { label: '提示', theme: 'primary' },
};

const RULE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  active: { label: '运行中', theme: 'success' },
  warning: { label: '异常', theme: 'warning' },
  disabled: { label: '已禁用', theme: 'default' },
};

const DataQualityPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态 =====
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);
  const [filterAssetId, setFilterAssetId] = useState<string>('');
  const [checkAssetId, setCheckAssetId] = useState<string>('');
  const [checkDialogOpen, setCheckDialogOpen] = useState<boolean>(false);
  const [reportDetail, setReportDetail] = useState<QualityReport | null>(null);
  const [reportDetailOpen, setReportDetailOpen] = useState<boolean>(false);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['qualityReports', page, pageSize, filterAssetId],
    queryFn: () => listQualityReports({ page: page + 1, page_size: pageSize, asset_id: filterAssetId || undefined }),
  });

  const items: QualityReport[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

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
    const activeAlerts = MOCK_ALERTS.filter(a => a.status === 'active').length;
    const ruleCount = MOCK_RULES.length;
    return { totalChecks, passRate, anomalyCount, avgScore, activeAlerts, ruleCount };
  }, [items, qualityData]);

  // ===== Mutations =====
  const checkMut = useMutation({
    mutationFn: (assetId: string) => runQualityCheck(assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['qualityReports'] });
      setCheckDialogOpen(false);
      setCheckAssetId('');
      MessagePlugin.success('质量检查已触发');
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
    const map: Record<string, 'success' | 'primary' | 'warning' | 'danger'> = { A: 'success', B: 'primary', C: 'warning', D: 'danger', F: 'danger' };
    return map[grade] ?? 'default';
  };

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
    const dated = items.filter(r => r.generated_at).slice().sort((a, b) => new Date(a.generated_at!).getTime() - new Date(b.generated_at!).getTime());
    const dates = dated.map((r) => new Date(r.generated_at!).toLocaleDateString('zh-CN'));
    const scores = dated.map((r) => r.overall_score);
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['综合评分'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates, boundaryGap: false },
      yAxis: { type: 'value', min: 0, max: 100, name: '分数' },
      series: [{
        name: '综合评分', type: 'line', data: scores, smooth: true,
        lineStyle: { width: 3 }, areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#2196f3' },
      }],
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
        shape: 'circle', splitNumber: 5,
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

  // ===== 质量维度对比图 =====
  const dimensionCompareOption = useMemo(() => {
    const dimensions = ['完整性', '准确性', '一致性', '时效性', '唯一性'];
    const current = [96.5, 94.2, 92.1, 88.7, 99.1];
    const target = [99, 95, 90, 90, 100];
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['当前得分', '目标值'], top: 10 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dimensions },
      yAxis: { type: 'value', min: 80, max: 100, name: '分数' },
      series: [
        { name: '当前得分', type: 'bar', data: current, itemStyle: { color: '#2196f3' }, barWidth: '30%' },
        { name: '目标值', type: 'line', data: target, itemStyle: { color: '#f44336' }, lineStyle: { type: 'dashed' } },
      ],
    };
  }, []);

  // ===== 告警趋势图 =====
  const alertTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['严重', '警告', '提示'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五'] },
    yAxis: { type: 'value', name: '告警数' },
    series: [
      { name: '严重', type: 'bar', stack: 'total', data: [2, 1, 3, 1, 2], itemStyle: { color: '#f44336' } },
      { name: '警告', type: 'bar', stack: 'total', data: [3, 4, 2, 5, 3], itemStyle: { color: '#ff9800' } },
      { name: '提示', type: 'bar', stack: 'total', data: [5, 3, 4, 2, 4], itemStyle: { color: '#2196f3' } },
    ],
  }), []);

  return (
    <PageContainer>
      <PageHeader
        title="数据质量评价"
        subtitle="基于可信数据空间标准体系的五维数据质量评价与监控"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '触发检查', icon: <PlayIcon />, onClick: () => setCheckDialogOpen(true), variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['qualityReports'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总检查数" value={stats.totalChecks} icon={<ChartIcon />} gradient="blue" unit="" />
        <StatCard title="通过率" value={stats.passRate} icon={<CheckCircleIcon />} gradient="green" unit="%" />
        <StatCard title="异常数" value={stats.anomalyCount} icon={<ErrorCircleFilledIcon />} gradient="red" unit="" />
        <StatCard title="平均分" value={stats.avgScore} icon={<TrendingUpIcon />} gradient="orange" unit="" />
      </StatGrid>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="overview" label="质量概览">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <PageSection title="质量趋势" titleIcon={<TrendingUpIcon />} className="md:col-span-2">
              <ReactECharts option={trendChartOption} style={{ height: 260 }} />
            </PageSection>
            <PageSection title="五维质量雷达图" titleIcon={<ChartIcon />}>
              <ReactECharts option={radarChartOption} style={{ height: 260 }} />
            </PageSection>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="质量维度对比（当前 vs 目标）" option={dimensionCompareOption} height={280} />
            <ChartCard title="本周告警趋势" option={alertTrendOption} height={280} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="check" label="质量检查">
          <PageSection title="质量检查规则" titleIcon={<DataBaseIcon />} className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              {['完整性', '准确性', '一致性', '时效性', '唯一性'].map(dim => {
                const dimRules = MOCK_RULES.filter(r => r.dimension === dim);
                const avgPass = dimRules.length > 0 ? (dimRules.reduce((s, r) => s + r.pass_rate, 0) / dimRules.length).toFixed(1) : '0';
                return (
                  <div key={dim} className="p-3 rounded-lg border border-gray-200 bg-white">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-gray-800">{dim}</span>
                      <Tag size="small" variant="outline">{dimRules.length}条规则</Tag>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${avgPass}%`, backgroundColor: parseFloat(avgPass) >= 90 ? '#4caf50' : parseFloat(avgPass) >= 80 ? '#ff9800' : '#f44336' }} />
                      </div>
                      <span className="text-xs font-semibold text-gray-600">{avgPass}%</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 规则列表 */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">规则名称</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">维度</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">阈值</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">通过率</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">状态</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">上次运行</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {MOCK_RULES.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div>
                          <span className="text-sm font-medium text-gray-900">{rule.name}</span>
                          <p className="text-xs text-gray-500 mt-0.5">{rule.description}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3"><Tag variant="outline" size="small">{rule.dimension}</Tag></td>
                      <td className="px-4 py-3 text-gray-600">{rule.threshold}%</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${rule.pass_rate}%`, backgroundColor: rule.pass_rate >= rule.threshold ? '#4caf50' : '#f44336' }} />
                          </div>
                          <span className={`text-xs font-semibold ${rule.pass_rate >= rule.threshold ? 'text-green-600' : 'text-red-600'}`}>{rule.pass_rate}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">{(() => { const s = RULE_STATUS_MAP[rule.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{rule.status}</Tag>; })()}</td>
                      <td className="px-4 py-3 text-gray-600">{new Date(rule.last_run).toLocaleString('zh-CN')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="reports" label="质量报告">
          {/* 搜索过滤栏 */}
          <div className="mt-4 mb-4 flex items-center gap-3">
            <Input
              value={filterAssetId}
              onChange={(val) => { setFilterAssetId(String(val)); setPage(0); }}
              placeholder="输入资产 ID 过滤..."
              prefixIcon={<ChartIcon />}
              className="!w-[300px]"
              onEnter={() => setPage(0)}
            />
          </div>

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
                      <td className="px-4 py-3"><Tag theme="primary" variant="outline" size="small">{row.asset_id.slice(0, 8)}</Tag></td>
                      <td className={`px-4 py-3 font-semibold ${scoreColor(row.completeness)}`}>{(row.completeness ?? 0).toFixed(1)}</td>
                      <td className={`px-4 py-3 font-semibold ${scoreColor(row.accuracy)}`}>{(row.accuracy ?? 0).toFixed(1)}</td>
                      <td className={`px-4 py-3 font-semibold ${scoreColor(row.consistency)}`}>{(row.consistency ?? 0).toFixed(1)}</td>
                      <td className={`px-4 py-3 font-semibold ${scoreColor(row.timeliness)}`}>{(row.timeliness ?? 0).toFixed(1)}</td>
                      <td className={`px-4 py-3 font-semibold ${scoreColor(row.overall_score)}`}>{(row.overall_score ?? 0).toFixed(1)}</td>
                      <td className="px-4 py-3"><Tag theme={gradeTheme(row.grade)} size="small">{row.grade}</Tag></td>
                      <td className="px-4 py-3 text-gray-600">{row.generated_at ? new Date(row.generated_at).toLocaleString('zh-CN') : '—'}</td>
                      <td className="px-4 py-3 text-center">
                        <Tooltip content="查看详情">
                          <span className="cursor-pointer hover:bg-gray-100 rounded p-1.5 inline-flex items-center text-blue-500" onClick={() => getReportMut.mutate(row.id)}>
                            <BrowseIcon className="text-sm" />
                          </span>
                        </Tooltip>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-500">暂无数据</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {total > 0 && (
              <div className="flex justify-center py-3 border-t border-gray-100">
                <Pagination
                  current={page + 1} total={total} pageSize={pageSize}
                  showPageSize pageSizeOptions={[10, 20, 50]}
                  onChange={(pageInfo) => { setPage(pageInfo.current - 1); setPageSize(pageInfo.pageSize); }}
                />
              </div>
            )}
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="monitor" label="质量监控">
          {/* 实时告警 */}
          <PageSection title="实时质量告警" titleIcon={<NotificationIcon />} className="mt-4" extra={<Tag theme="danger" size="small">{stats.activeAlerts}条活跃告警</Tag>}>
            <div className="space-y-3">
              {MOCK_ALERTS.map((alert) => (
                <div key={alert.id} className={`flex items-start gap-3 p-3 rounded-lg border ${alert.status === 'active' ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-gray-50'}`}>
                  <div className="mt-0.5">
                    {alert.severity === 'high' ? <ErrorCircleFilledIcon className="text-red-500" /> : alert.severity === 'medium' ? <TimeIcon className="text-orange-500" /> : <ChartIcon className="text-blue-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-gray-900">{alert.asset_name}</span>
                      <Tag variant="outline" size="small">{alert.dimension}</Tag>
                      {(() => { const s = ALERT_SEVERITY_MAP[alert.severity]; return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : null; })()}
                      {alert.status === 'resolved' && <Tag theme="success" size="small">已解决</Tag>}
                    </div>
                    <p className="text-sm text-gray-600">{alert.message}</p>
                    <span className="text-xs text-gray-400 mt-1 block">{new Date(alert.triggered_at).toLocaleString('zh-CN')}</span>
                  </div>
                  {alert.status === 'active' && (
                    <Button size="small" variant="outline" onClick={() => MessagePlugin.info('告警已确认处理')}>确认处理</Button>
                  )}
                </div>
              ))}
            </div>
          </PageSection>

          {/* 监控面板 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <PageSection title="质量维度健康度" titleIcon={<ChartIcon />}>
              <div className="space-y-3">
                {[
                  { name: '完整性', score: 96.5, trend: 1.2 },
                  { name: '准确性', score: 94.2, trend: -0.5 },
                  { name: '一致性', score: 92.1, trend: 2.3 },
                  { name: '时效性', score: 88.7, trend: -1.8 },
                  { name: '唯一性', score: 99.1, trend: 0.3 },
                ].map((dim) => (
                  <div key={dim.name} className="flex items-center gap-3">
                    <span className="w-16 text-sm text-gray-700">{dim.name}</span>
                    <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${dim.score}%`, backgroundColor: dim.score >= 90 ? '#4caf50' : dim.score >= 80 ? '#ff9800' : '#f44336' }} />
                    </div>
                    <span className={`w-14 text-sm font-semibold ${dim.score >= 90 ? 'text-green-600' : dim.score >= 80 ? 'text-orange-600' : 'text-red-600'}`}>{dim.score}%</span>
                    <span className={`w-14 text-xs ${dim.trend >= 0 ? 'text-green-500' : 'text-red-500'}`}>{dim.trend >= 0 ? '+' : ''}{dim.trend}%</span>
                  </div>
                ))}
              </div>
            </PageSection>

            <PageSection title="数据源质量排名" titleIcon={<DataBaseIcon />}>
              <div className="space-y-2">
                {[
                  { name: '国网数据中心', score: 97.2, assets: 45 },
                  { name: '营销系统', score: 95.8, assets: 32 },
                  { name: '新能源管理平台', score: 93.5, assets: 28 },
                  { name: '碳管理平台', score: 91.2, assets: 15 },
                  { name: '充电服务平台', score: 89.7, assets: 22 },
                ].map((source, idx) => (
                  <div key={source.name} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${idx < 3 ? 'bg-blue-500' : 'bg-gray-400'}`}>{idx + 1}</span>
                    <span className="flex-1 text-sm text-gray-800">{source.name}</span>
                    <span className="text-xs text-gray-500">{source.assets}个资产</span>
                    <span className={`text-sm font-semibold ${source.score >= 90 ? 'text-green-600' : 'text-orange-600'}`}>{source.score}%</span>
                  </div>
                ))}
              </div>
            </PageSection>
          </div>
        </Tabs.TabPanel>
      </Tabs>

      {/* 触发检查弹窗 */}
      <Dialog visible={checkDialogOpen} onClose={() => setCheckDialogOpen(false)} header="触发质量检查" width={480} footer={
        <div className="flex justify-end gap-2">
          <Button onClick={() => { setCheckDialogOpen(false); setCheckAssetId(''); }}>取消</Button>
          <Button theme="primary" disabled={!checkAssetId.trim()} loading={checkMut.isPending} onClick={() => checkMut.mutate(checkAssetId)}>执行检查</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-600">输入要检查的数据资产 ID，系统将执行质量检查并生成报告。</p>
          <Input value={checkAssetId} onChange={(val) => setCheckAssetId(String(val))} placeholder="请输入资产 ID" />
        </div>
      </Dialog>

      {/* 报告详情弹窗 */}
      <Dialog visible={reportDetailOpen} onClose={() => setReportDetailOpen(false)} header="质量报告详情" width={640} footer={
        <Button onClick={() => setReportDetailOpen(false)}>关闭</Button>
      }>
        {reportDetail ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-6">
              <div><p className="text-xs text-gray-500">资产 ID</p><p className="text-sm font-medium text-gray-800">{reportDetail.asset_id}</p></div>
              <div><p className="text-xs text-gray-500">等级</p><Tag theme={gradeTheme(reportDetail.grade)} size="small">{reportDetail.grade}</Tag></div>
              <div><p className="text-xs text-gray-500">综合分</p><p className={`text-sm font-semibold ${scoreColor(reportDetail.overall_score)}`}>{(reportDetail.overall_score ?? 0).toFixed(1)}</p></div>
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
                  <p className={`text-lg font-semibold ${scoreColor(dim.value)}`}>{(dim.value ?? 0).toFixed(1)}</p>
                </div>
              ))}
            </div>
            {reportDetail.details && (
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
                <p className="text-sm font-semibold text-gray-700 mb-2">详细数据</p>
                <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-48">{JSON.stringify(reportDetail.details, null, 2)}</pre>
              </div>
            )}
          </div>
        ) : <p className="text-sm text-gray-500 text-center py-4">暂无报告数据</p>}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default DataQualityPage;
