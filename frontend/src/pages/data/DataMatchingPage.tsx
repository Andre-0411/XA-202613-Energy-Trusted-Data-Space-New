/**
 * 供需撮合管理页面
 * 基于可信数据空间标准体系，实现数据供需智能撮合
 * 包含：需求发布、供需匹配、撮合记录、效果评估
 */
import React, { useState, useMemo } from 'react';
import { Button, Tag, Tabs, Dialog, Input, Select, Tooltip, MessagePlugin, Textarea } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, EditIcon, SearchIcon,
  CheckCircleFilledIcon, TrendingUpIcon, TimeIcon, ChartIcon,
  ErrorCircleIcon, LinkIcon, DataBaseIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import StatusTag from '@/components/StatusTag';

/* ========== 类型定义 ========== */
interface DataDemand {
  id: string;
  title: string;
  category: string;
  description: string;
  capability_req: string;
  budget_range: string;
  publisher: string;
  status: string;
  created_at: string;
  deadline: string;
  match_count: number;
}

interface MatchResult {
  id: string;
  demand_title: string;
  supply_name: string;
  supply_org: string;
  match_score: number;
  status: string;
  matched_at: string;
  confirmed_at: string;
  data_quality: number;
}

interface MatchRecord {
  id: string;
  demand_id: string;
  demand_title: string;
  supply_name: string;
  provider: string;
  consumer: string;
  match_score: number;
  result: string;
  matched_at: string;
  satisfaction: number;
}

/* ========== 模拟数据 - 需求发布 ========== */
const MOCK_DEMANDS: DataDemand[] = [
  { id: 'dem-001', title: '全省光伏发电实时出力数据', category: '新能源', description: '需要全省范围内分布式光伏电站的实时出力监测数据，时间分辨率15分钟', capability_req: '实时数据接口、数据质量报告、历史数据回溯', budget_range: '¥50,000 - ¥80,000/年', publisher: '电力交易中心', status: 'published', created_at: '2025-05-01T09:00:00Z', deadline: '2025-06-30', match_count: 5 },
  { id: 'dem-002', title: '工商业用户负荷曲线数据', category: '电网运行', description: '大型工商业用户的24小时负荷曲线数据，用于负荷预测模型训练', capability_req: '至少1000户、连续12个月数据、数据脱敏', budget_range: '¥120,000 - ¥180,000', publisher: 'AI预测平台', status: 'published', created_at: '2025-05-10T10:00:00Z', deadline: '2025-07-31', match_count: 3 },
  { id: 'dem-003', title: '碳排放因子数据库', category: '双碳管理', description: '各行业碳排放因子数据，用于碳足迹计算', capability_req: '符合国标、年度更新、覆盖主要行业', budget_range: '¥30,000 - ¥50,000', publisher: '双碳管理平台', status: 'matching', created_at: '2025-05-15T08:00:00Z', deadline: '2025-06-15', match_count: 2 },
  { id: 'dem-004', title: '充电桩位置及运营状态数据', category: '电动汽车', description: '公共充电桩的地理位置、功率、使用率等运营数据', capability_req: '覆盖主城区、每日更新、API接口', budget_range: '¥20,000 - ¥40,000/年', publisher: '电动汽车公司', status: 'published', created_at: '2025-05-18T14:00:00Z', deadline: '2025-06-30', match_count: 4 },
  { id: 'dem-005', title: '风电场气象监测数据', category: '新能源', description: '沿海风电场区域的风速、风向、气温等气象数据', capability_req: '分钟级数据、至少3年历史、质量控制', budget_range: '¥60,000 - ¥100,000', publisher: '新能源研究院', status: 'closed', created_at: '2025-04-20T09:00:00Z', deadline: '2025-05-31', match_count: 6 },
  { id: 'dem-006', title: '电力市场交易价格数据', category: '电力交易', description: '各省电力市场日前、实时交易价格数据', capability_req: '覆盖主要省份、T+1更新、历史5年数据', budget_range: '¥80,000 - ¥150,000', publisher: '综合能源服务商', status: 'matching', created_at: '2025-05-20T10:00:00Z', deadline: '2025-07-31', match_count: 3 },
];

/* ========== 模拟数据 - 匹配结果 ========== */
const MOCK_MATCHES: MatchResult[] = [
  { id: 'match-001', demand_title: '全省光伏发电实时出力数据', supply_name: '光伏电站监测数据集', supply_org: '光伏运营商A', match_score: 95, status: 'confirmed', matched_at: '2025-05-20T10:00:00Z', confirmed_at: '2025-05-21T14:00:00Z', data_quality: 96.5 },
  { id: 'match-002', demand_title: '全省光伏发电实时出力数据', supply_name: '新能源出力监测数据', supply_org: '新能源管理平台', match_score: 88, status: 'pending', matched_at: '2025-05-20T10:00:00Z', confirmed_at: '', data_quality: 92.3 },
  { id: 'match-003', demand_title: '工商业用户负荷曲线数据', supply_name: '大用户用电数据集', supply_org: '营销系统', match_score: 92, status: 'confirmed', matched_at: '2025-05-18T09:00:00Z', confirmed_at: '2025-05-19T16:00:00Z', data_quality: 94.8 },
  { id: 'match-004', demand_title: '碳排放因子数据库', supply_name: '行业碳排放因子库', supply_org: '碳管理平台', match_score: 90, status: 'pending', matched_at: '2025-05-22T11:00:00Z', confirmed_at: '', data_quality: 91.2 },
  { id: 'match-005', demand_title: '充电桩位置及运营状态数据', supply_name: '充电桩运营数据集', supply_org: '充电服务平台', match_score: 97, status: 'confirmed', matched_at: '2025-05-19T14:00:00Z', confirmed_at: '2025-05-20T09:00:00Z', data_quality: 98.1 },
  { id: 'match-006', demand_title: '电力市场交易价格数据', supply_name: '电力交易历史价格', supply_org: '交易中心', match_score: 85, status: 'pending', matched_at: '2025-05-23T08:00:00Z', confirmed_at: '', data_quality: 89.5 },
];

/* ========== 模拟数据 - 撮合记录 ========== */
const MOCK_RECORDS: MatchRecord[] = [
  { id: 'rec-001', demand_id: 'dem-005', demand_title: '风电场气象监测数据', supply_name: '沿海气象站数据集', provider: '气象局', consumer: '新能源研究院', match_score: 93, result: 'success', matched_at: '2025-05-10T10:00:00Z', satisfaction: 4.8 },
  { id: 'rec-002', demand_id: 'dem-005', demand_title: '风电场气象监测数据', supply_name: '风电场运行数据', provider: '风电运营商', consumer: '新能源研究院', match_score: 87, result: 'success', matched_at: '2025-05-12T14:00:00Z', satisfaction: 4.5 },
  { id: 'rec-003', demand_id: 'dem-001', demand_title: '全省光伏发电实时出力数据', supply_name: '光伏电站监测数据集', provider: '光伏运营商A', consumer: '电力交易中心', match_score: 95, result: 'success', matched_at: '2025-05-20T10:00:00Z', satisfaction: 4.9 },
  { id: 'rec-004', demand_id: 'dem-002', demand_title: '工商业用户负荷曲线数据', supply_name: '大用户用电数据集', provider: '营销系统', consumer: 'AI预测平台', match_score: 92, result: 'success', matched_at: '2025-05-18T09:00:00Z', satisfaction: 4.7 },
  { id: 'rec-005', demand_id: 'dem-004', demand_title: '充电桩位置及运营状态数据', supply_name: '充电桩运营数据集', provider: '充电服务平台', consumer: '电动汽车公司', match_score: 97, result: 'success', matched_at: '2025-05-19T14:00:00Z', satisfaction: 5.0 },
];

const DEMAND_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  published: { label: '已发布', theme: 'success' },
  matching: { label: '匹配中', theme: 'primary' },
  closed: { label: '已关闭', theme: 'default' },
};

const MATCH_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  confirmed: { label: '已确认', theme: 'success' },
  pending: { label: '待确认', theme: 'warning' },
  rejected: { label: '已拒绝', theme: 'danger' },
};

const DataMatchingPage: React.FC = () => {
  // ===== 状态 =====
  const [activeTab, setActiveTab] = useState<string>('demands');
  const [publishOpen, setPublishOpen] = useState<boolean>(false);
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedDemand, setSelectedDemand] = useState<DataDemand | null>(null);

  // ===== 统计数据 =====
  const stats = useMemo(() => {
    const totalDemands = MOCK_DEMANDS.length;
    const activeDemands = MOCK_DEMANDS.filter(d => d.status !== 'closed').length;
    const totalMatches = MOCK_MATCHES.length;
    const confirmedMatches = MOCK_MATCHES.filter(m => m.status === 'confirmed').length;
    const successRate = MOCK_RECORDS.length > 0 ? parseFloat(((MOCK_RECORDS.filter(r => r.result === 'success').length / MOCK_RECORDS.length) * 100).toFixed(1)) : 0;
    const avgSatisfaction = MOCK_RECORDS.length > 0 ? parseFloat((MOCK_RECORDS.reduce((s, r) => s + r.satisfaction, 0) / MOCK_RECORDS.length).toFixed(1)) : 0;
    const avgMatchScore = MOCK_MATCHES.length > 0 ? parseFloat((MOCK_MATCHES.reduce((s, m) => s + m.match_score, 0) / MOCK_MATCHES.length).toFixed(1)) : 0;
    return { totalDemands, activeDemands, totalMatches, confirmedMatches, successRate, avgSatisfaction, avgMatchScore };
  }, []);

  // ===== ECharts - 匹配成功率趋势 =====
  const successTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['撮合次数', '成功次数', '成功率'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: [
      { type: 'value', name: '次数' },
      { type: 'value', name: '成功率 (%)', min: 0, max: 100 },
    ],
    series: [
      { name: '撮合次数', type: 'bar', data: [12, 18, 15, 22, 28], itemStyle: { color: '#2196f3' } },
      { name: '成功次数', type: 'bar', data: [10, 15, 13, 19, 25], itemStyle: { color: '#4caf50' } },
      { name: '成功率', type: 'line', yAxisIndex: 1, data: [83.3, 83.3, 86.7, 86.4, 89.3], smooth: true, itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  // ===== ECharts - 需求分类分布 =====
  const categoryDistOption = useMemo(() => {
    const cats: Record<string, number> = {};
    MOCK_DEMANDS.forEach(d => { cats[d.category] = (cats[d.category] || 0) + 1; });
    const colors = ['#2196f3', '#4caf50', '#ff9800', '#9c27b0', '#00bcd4', '#e91e63'];
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 'middle' },
      series: [{
        name: '需求分类', type: 'pie', radius: ['40%', '70%'], center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: Object.entries(cats).map(([name, value], i) => ({
          value, name, itemStyle: { color: colors[i % colors.length] },
        })),
      }],
    };
  }, []);

  // ===== ECharts - 匹配分数分布 =====
  const matchScoreDistOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['80-85', '85-90', '90-95', '95-100'] },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: [
        { value: 1, itemStyle: { color: '#ff9800' } },
        { value: 2, itemStyle: { color: '#2196f3' } },
        { value: 2, itemStyle: { color: '#4caf50' } },
        { value: 1, itemStyle: { color: '#9c27b0' } },
      ],
      barWidth: '50%',
      label: { show: true, position: 'top' },
    }],
  }), []);

  // ===== ECharts - 用户满意度 =====
  const satisfactionOption = useMemo(() => ({
    tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].axisValue}<br/>满意度: ${params[0].value}/5.0` },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: MOCK_RECORDS.map(r => r.demand_title.slice(0, 6) + '...') },
    yAxis: { type: 'value', name: '满意度', min: 4, max: 5 },
    series: [{
      type: 'bar',
      data: MOCK_RECORDS.map(r => ({
        value: r.satisfaction,
        itemStyle: { color: r.satisfaction >= 4.8 ? '#4caf50' : r.satisfaction >= 4.5 ? '#2196f3' : '#ff9800' },
      })),
      barWidth: '50%',
      label: { show: true, position: 'top', formatter: '{c}' },
    }],
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '供需撮合' }],
    [],
  );

  // ===== 需求列表列定义 =====
  const demandColumns: Column<DataDemand>[] = useMemo(() => [
    { id: 'title', label: '需求标题', minWidth: 200, render: (row) => <span className="text-sm font-medium">{row.title}</span> },
    { id: 'category', label: '分类', minWidth: 90, render: (row) => <Tag variant="outline" size="small">{row.category}</Tag> },
    { id: 'publisher', label: '发布方', minWidth: 120 },
    { id: 'budget_range', label: '预算范围', minWidth: 140, render: (row) => <span className="text-sm text-green-600">{row.budget_range}</span> },
    { id: 'match_count', label: '匹配数', minWidth: 80, render: (row) => <span className="text-sm font-semibold text-blue-600">{row.match_count}</span> },
    { id: 'status', label: '状态', minWidth: 90, render: (row) => { const s = DEMAND_STATUS_MAP[row.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'deadline', label: '截止日期', minWidth: 110 },
    {
      id: 'actions', label: '操作', minWidth: 100, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情"><span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => { setSelectedDemand(row); setDetailOpen(true); }}><BrowseIcon /></span></Tooltip>
          <Tooltip content="编辑"><span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500"><EditIcon /></span></Tooltip>
        </div>
      ),
    },
  ], []);

  // ===== 匹配结果列定义 =====
  const matchColumns: Column<MatchResult>[] = useMemo(() => [
    { id: 'demand_title', label: '需求', minWidth: 180, render: (row) => <span className="text-sm font-medium">{row.demand_title}</span> },
    { id: 'supply_name', label: '供给', minWidth: 160, render: (row) => <span className="text-sm">{row.supply_name}</span> },
    { id: 'supply_org', label: '供给方', minWidth: 120 },
    { id: 'match_score', label: '匹配分数', minWidth: 100, render: (row) => <span className={`text-sm font-semibold ${row.match_score >= 90 ? 'text-green-600' : row.match_score >= 80 ? 'text-blue-600' : 'text-orange-600'}`}>{row.match_score}分</span> },
    { id: 'data_quality', label: '数据质量', minWidth: 100, render: (row) => <span className={`text-sm font-semibold ${row.data_quality >= 90 ? 'text-green-600' : 'text-orange-600'}`}>{row.data_quality}%</span> },
    { id: 'status', label: '状态', minWidth: 90, render: (row) => { const s = MATCH_STATUS_MAP[row.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'matched_at', label: '匹配时间', minWidth: 140, render: (row) => new Date(row.matched_at).toLocaleString('zh-CN') },
    {
      id: 'actions', label: '操作', minWidth: 80, align: 'center',
      render: (row) => row.status === 'pending' ? (
        <Button size="small" theme="primary" variant="outline" onClick={() => MessagePlugin.success('已确认匹配')}>确认</Button>
      ) : <Tag theme="success" size="small">已完成</Tag>,
    },
  ], []);

  // ===== 撮合记录列定义 =====
  const recordColumns: Column<MatchRecord>[] = useMemo(() => [
    { id: 'demand_title', label: '需求', minWidth: 180, render: (row) => <span className="text-sm font-medium">{row.demand_title}</span> },
    { id: 'supply_name', label: '供给', minWidth: 160 },
    { id: 'provider', label: '提供方', minWidth: 100 },
    { id: 'consumer', label: '使用方', minWidth: 100 },
    { id: 'match_score', label: '匹配分', minWidth: 80, render: (row) => <span className="text-sm font-semibold text-blue-600">{row.match_score}</span> },
    { id: 'result', label: '结果', minWidth: 80, render: (row) => <Tag theme={row.result === 'success' ? 'success' : 'danger'} size="small">{row.result === 'success' ? '成功' : '失败'}</Tag> },
    { id: 'satisfaction', label: '满意度', minWidth: 100, render: (row) => (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map(i => (
          <svg key={i} width="14" height="14" viewBox="0 0 24 24" fill={i <= Math.floor(row.satisfaction) ? '#ff9800' : '#e0e0e0'}>
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ))}
        <span className="text-xs text-gray-500 ml-1">{row.satisfaction}</span>
      </div>
    ) },
    { id: 'matched_at', label: '撮合时间', minWidth: 140, render: (row) => new Date(row.matched_at).toLocaleString('zh-CN') },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="供需撮合"
        subtitle="基于智能匹配算法，实现数据供需高效对接"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '发布需求', icon: <AddIcon />, onClick: () => setPublishOpen(true), variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('数据已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="需求总数" value={stats.totalDemands} icon={<SearchIcon />} gradient="blue" unit="条" />
        <StatCard title="匹配总数" value={stats.totalMatches} icon={<LinkIcon />} gradient="green" unit="次" />
        <StatCard title="成功率" value={stats.successRate} icon={<CheckCircleFilledIcon />} gradient="purple" unit="%" />
        <StatCard title="平均满意度" value={stats.avgSatisfaction} icon={<TrendingUpIcon />} gradient="orange" unit="/5" />
      </StatGrid>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="demands" label="需求发布">
          <PageSection padding="none" className="mt-4">
            <DataTable columns={demandColumns} rows={MOCK_DEMANDS} page={0} pageSize={20} total={MOCK_DEMANDS.length} />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="matching" label="供需匹配">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={matchColumns} rows={MOCK_MATCHES} page={0} pageSize={20} total={MOCK_MATCHES.length} />
              </PageSection>
            </div>
            <ChartCard title="匹配分数分布" option={matchScoreDistOption} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="records" label="撮合记录">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={recordColumns} rows={MOCK_RECORDS} page={0} pageSize={20} total={MOCK_RECORDS.length} />
              </PageSection>
            </div>
            <ChartCard title="用户满意度" option={satisfactionOption} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="evaluation" label="效果评估">
          <StatGrid columns={3} gap="md" className="mt-4 mb-4">
            <StatCard title="平均匹配分" value={stats.avgMatchScore} icon={<ChartIcon />} gradient="blue" unit="分" />
            <StatCard title="已确认匹配" value={stats.confirmedMatches} icon={<CheckCircleFilledIcon />} gradient="green" unit="次" />
            <StatCard title="活跃需求" value={stats.activeDemands} icon={<DataBaseIcon />} gradient="orange" unit="条" />
          </StatGrid>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="撮合成功率趋势" option={successTrendOption} height={320} />
            <ChartCard title="需求分类分布" option={categoryDistOption} height={320} />
          </div>

          {/* 效果评估详情 */}
          <PageSection title="评估指标详情" titleIcon={<ChartIcon />} className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: '平均响应时间', value: '2.3小时', desc: '从需求发布到首次匹配', trend: '-15%', good: true },
                { label: '匹配精准度', value: '91.2%', desc: '匹配结果符合需求比例', trend: '+3.5%', good: true },
                { label: '数据交付率', value: '96.8%', desc: '匹配成功后数据交付比例', trend: '+1.2%', good: true },
                { label: '用户复用率', value: '78.5%', desc: '用户再次使用撮合服务比例', trend: '+8.3%', good: true },
              ].map((metric) => (
                <div key={metric.label} className="p-4 rounded-lg border border-gray-200 bg-white">
                  <p className="text-xs text-gray-500">{metric.label}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{metric.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{metric.desc}</p>
                  <div className="flex items-center gap-1 mt-2">
                    <span className={`text-xs font-semibold ${metric.good ? 'text-green-600' : 'text-red-600'}`}>{metric.trend}</span>
                    <span className="text-xs text-gray-400">较上月</span>
                  </div>
                </div>
              ))}
            </div>
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 需求详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="需求详情" width={640} footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {selectedDemand && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div><span className="text-xs text-gray-500">需求标题</span><p className="text-sm font-semibold">{selectedDemand.title}</p></div>
              <div><span className="text-xs text-gray-500">分类</span><Tag variant="outline" size="small">{selectedDemand.category}</Tag></div>
              <div><span className="text-xs text-gray-500">发布方</span><p className="text-sm">{selectedDemand.publisher}</p></div>
              <div><span className="text-xs text-gray-500">预算范围</span><p className="text-sm text-green-600">{selectedDemand.budget_range}</p></div>
              <div><span className="text-xs text-gray-500">截止日期</span><p className="text-sm">{selectedDemand.deadline}</p></div>
              <div><span className="text-xs text-gray-500">匹配数</span><p className="text-sm font-semibold text-blue-600">{selectedDemand.match_count}个</p></div>
            </div>
            <div><span className="text-xs text-gray-500">需求描述</span><p className="text-sm text-gray-700 mt-1 p-3 bg-gray-50 rounded-lg">{selectedDemand.description}</p></div>
            <div><span className="text-xs text-gray-500">能力要求</span><p className="text-sm text-gray-700 mt-1 p-3 bg-gray-50 rounded-lg">{selectedDemand.capability_req}</p></div>
          </div>
        )}
      </Dialog>

      {/* 发布需求弹窗 */}
      <Dialog visible={publishOpen} onClose={() => setPublishOpen(false)} header="发布数据需求" width={560} footer={
        <div className="flex justify-end gap-2">
          <Button onClick={() => setPublishOpen(false)}>取消</Button>
          <Button theme="primary" onClick={() => { MessagePlugin.success('需求已发布'); setPublishOpen(false); }}>发布</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">需求标题</label><Input placeholder="请输入需求标题" /></div>
          <div><label className="block text-sm text-gray-600 mb-1">分类</label><Select options={[{ value: '新能源', label: '新能源' }, { value: '电网运行', label: '电网运行' }, { value: '双碳管理', label: '双碳管理' }, { value: '电动汽车', label: '电动汽车' }, { value: '电力交易', label: '电力交易' }]} placeholder="选择分类" /></div>
          <div><label className="block text-sm text-gray-600 mb-1">需求描述</label><Textarea placeholder="详细描述您的数据需求..." rows={3} /></div>
          <div><label className="block text-sm text-gray-600 mb-1">能力要求</label><Textarea placeholder="描述对数据的能力要求..." rows={2} /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm text-gray-600 mb-1">预算范围</label><Input placeholder="如：¥50,000 - ¥100,000" /></div>
            <div><label className="block text-sm text-gray-600 mb-1">截止日期</label><Input placeholder="如：2025-06-30" /></div>
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default DataMatchingPage;
