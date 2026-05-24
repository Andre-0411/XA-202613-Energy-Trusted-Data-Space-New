/**
 * 安全等级管理页面
 * 安全等级概览 + 安全仪表盘 + ECharts + 统计卡片
 */
import React, { useMemo } from 'react';
import { Button } from 'tdesign-react';
import {
  RefreshIcon, ShieldErrorFilledIcon, VerifiedIcon,
  ErrorCircleFilledIcon, CheckCircleFilledIcon,
} from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getSecurityDashboard } from '@/api/security';
import { getKpiDashboard } from '@/api/ops';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import ReactECharts from 'echarts-for-react';
import { useNavigate } from 'react-router-dom';

const LEVEL_CARDS = [
  {
    level: 'Public',
    label: '公开',
    description: '公开数据，无安全限制，可自由共享',
    color: '#4caf50',
    bgGradient: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
    assetsPlaceholder: 120,
    policiesPlaceholder: 5,
  },
  {
    level: 'Internal',
    label: '内部',
    description: '内部使用数据，仅组织内部可访问',
    color: '#2196f3',
    bgGradient: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
    assetsPlaceholder: 340,
    policiesPlaceholder: 18,
  },
  {
    level: 'Confidential',
    label: '机密',
    description: '机密数据，需授权访问，受数据脱敏策略保护',
    color: '#ff9800',
    bgGradient: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
    assetsPlaceholder: 210,
    policiesPlaceholder: 32,
  },
  {
    level: 'TopSecret',
    label: '绝密',
    description: '最高安全等级，端到端加密，严格审计',
    color: '#f44336',
    bgGradient: 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)',
    assetsPlaceholder: 56,
    policiesPlaceholder: 48,
  },
];

const SecurityLevelsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: dashboardData } = useQuery({
    queryKey: ['securityDashboard'],
    queryFn: () => getSecurityDashboard(),
  });

  const { data: kpiData } = useQuery({
    queryKey: ['kpiDashboard'],
    queryFn: () => getKpiDashboard(),
  });

  const dashboardInfo: Record<string, unknown> = dashboardData?.data ?? {};

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    overallScore: (dashboardInfo.overall_score as number) ?? 85,
    totalAssets: (dashboardInfo.total_assets as number) ?? 726,
    activePolicies: (dashboardInfo.active_policies as number) ?? 103,
    securityIncidents: kpiData?.data?.security_incidents ?? 0,
  }), [dashboardInfo, kpiData]);

  // ===== ECharts 配置 =====
  const radarOption = useMemo(() => ({
    tooltip: {},
    radar: {
      indicator: [
        { name: '访问控制', max: 100 },
        { name: '数据加密', max: 100 },
        { name: '审计合规', max: 100 },
        { name: '身份认证', max: 100 },
        { name: '威胁防护', max: 100 },
        { name: '密钥管理', max: 100 },
      ],
    },
    series: [{
      type: 'radar' as const,
      data: [{
        value: [85, 92, 78, 88, 72, 90],
        name: '安全评分',
        areaStyle: { opacity: 0.2, color: '#2196f3' },
        lineStyle: { color: '#2196f3' },
        itemStyle: { color: '#2196f3' },
      }, {
        value: [78, 85, 82, 80, 68, 85],
        name: '行业平均',
        areaStyle: { opacity: 0.1, color: '#ff9800' },
        lineStyle: { color: '#ff9800', type: 'dashed' },
        itemStyle: { color: '#ff9800' },
      }],
    }],
  }), []);

  const levelDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '安全等级',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 120, name: '公开', itemStyle: { color: '#4caf50' } },
          { value: 340, name: '内部', itemStyle: { color: '#2196f3' } },
          { value: 210, name: '机密', itemStyle: { color: '#ff9800' } },
          { value: 56, name: '绝密', itemStyle: { color: '#f44336' } },
        ],
      },
    ],
  }), []);

  const scoreTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['安全评分', '合规评分'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '评分', min: 60, max: 100 },
    series: [
      { name: '安全评分', type: 'line', smooth: true, data: [78, 80, 82, 85, 83, 86, 85], itemStyle: { color: '#2196f3' } },
      { name: '合规评分', type: 'line', smooth: true, data: [82, 85, 88, 90, 87, 92, 91], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '安全等级' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="安全等级管理"
        subtitle="数据安全等级概览与安全仪表盘"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => { queryClient.invalidateQueries({ queryKey: ['securityDashboard'] }); queryClient.invalidateQueries({ queryKey: ['kpiDashboard'] }); }, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="综合安全评分" value={stats.overallScore} icon={<ShieldErrorFilledIcon />} gradient="purple" unit="分" />
        <MetricsCard title="数据资产总数" value={stats.totalAssets} icon={<ShieldErrorFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="活跃安全策略" value={stats.activePolicies} icon={<VerifiedIcon />} gradient="cyan" unit="" />
        <MetricsCard title="安全事件" value={stats.securityIncidents} icon={stats.securityIncidents > 0 ? <ErrorCircleFilledIcon /> : <CheckCircleFilledIcon />} gradient={stats.securityIncidents > 0 ? 'red' : 'green'} unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        <div className="md:col-span-8"><ChartCard title="安全评分趋势" option={scoreTrendOption} height={300} /></div>
        <div className="md:col-span-4"><ChartCard title="数据资产等级分布" option={levelDistOption} height={300} /></div>
      </div>

      {/* 安全仪表盘 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">安全评分仪表盘</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <ReactECharts option={radarOption} style={{ height: 300 }} />
          </div>
          <div className="flex flex-col gap-4 pt-2">
            <div>
              <span className="text-xs text-gray-600">安全事件数</span>
              <h2 className="text-2xl font-bold" style={{ color: kpiData?.data?.security_incidents ?? 0 > 0 ? '#f44336' : '#4caf50' }}>
                {kpiData?.data?.security_incidents ?? 0}
              </h2>
            </div>
            <div>
              <span className="text-xs text-gray-600">合规评分</span>
              <h2 className="text-2xl font-bold" style={{ color: '#2196f3' }}>
                {kpiData?.data?.compliance_score ?? '—'}
              </h2>
            </div>
            <div>
              <span className="text-xs text-gray-600">仪表盘原始数据</span>
              <div className="rounded bg-gray-50 border border-gray-200 p-2 mt-1">
                <pre className="text-xs font-mono whitespace-pre-wrap max-h-[150px] overflow-auto">
                  {JSON.stringify(dashboardInfo, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 安全等级卡片 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-4">数据安全等级</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {LEVEL_CARDS.map((card) => (
            <div key={card.level} className="rounded-xl border-2 h-full" style={{ background: card.bgGradient, borderColor: card.color }}>
              <div className="p-4">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <ShieldErrorFilledIcon style={{ color: card.color }} />
                    <h4 className="text-base font-bold" style={{ color: card.color }}>{card.label}</h4>
                  </div>
                  <span className="text-xs text-gray-600">{card.level}</span>
                  <span className="text-sm">{card.description}</span>
                  <div className="flex gap-4 mt-2">
                    <div>
                      <span className="text-xs text-gray-600">数据资产</span>
                      <h4 className="text-base font-semibold" style={{ color: card.color }}>{card.assetsPlaceholder}</h4>
                    </div>
                    <div>
                      <span className="text-xs text-gray-600">安全策略</span>
                      <h4 className="text-base font-semibold" style={{ color: card.color }}>{card.policiesPlaceholder}</h4>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 安全策略快速链接 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">安全策略快速链接</h3>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => navigate('/dashboard/security/policies')}>安全策略管理</Button>
          <Button variant="outline" onClick={() => navigate('/dashboard/security/did')}>DID 身份管理</Button>
          <Button variant="outline" onClick={() => navigate('/dashboard/security/vc')}>可验证凭证</Button>
          <Button variant="outline" onClick={() => navigate('/dashboard/security/keys')}>密钥管理</Button>
          <Button variant="outline" onClick={() => navigate('/dashboard/security/threats')}>威胁检测</Button>
          <Button variant="outline" onClick={() => navigate('/dashboard/security/crypto')}>国密算法</Button>
          <Button variant="outline" onClick={() => navigate('/dashboard/security/zkp')}>零知识证明</Button>
        </div>
      </div>
    </PageContainer>
  );
};

export default SecurityLevelsPage;
