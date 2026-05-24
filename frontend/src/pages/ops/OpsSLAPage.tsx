/**
 * SLA 管理页面
 * SLA 配置管理、指标监控、报告生成、仪表盘
 */
import React, { useState, useMemo } from 'react';
import { Button, Dialog, Input, Tag, Tooltip, Tabs, Progress } from 'tdesign-react';
import {
  RefreshIcon, AnalyticsIcon, CheckCircleFilledIcon, ErrorCircleFilledIcon,
  TrendingUpIcon, TrendingDownIcon,
} from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import request from '@/api/request';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import LoadingOverlay from '@/components/LoadingOverlay';

// ===== 类型定义 =====
interface SLATarget {
  metric_name: string;
  target_value: number;
  unit: string;
  operator: string;
  description?: string;
}

interface SLAConfig {
  sla_id: string;
  name: string;
  service_id: string;
  service_name?: string;
  targets: SLATarget[];
  enabled: boolean;
  created_at: string;
  updated_at?: string;
}

interface SLAMetricData {
  metric_name: string;
  current_value: number;
  target_value: number;
  unit: string;
  status: 'met' | 'at_risk' | 'breached';
  compliance_percent: number;
  trend?: string;
  last_measured_at: string;
}

interface SLADashboard {
  total_slas: number;
  met_count: number;
  at_risk_count: number;
  breached_count: number;
  overall_compliance: number;
  metrics: SLAMetricData[];
  recent_breaches: unknown[];
  period: string;
}

// ===== API 函数 =====
const getSlaConfigs = () => request.get<unknown, { configs: SLAConfig[] }>('/ops/sla/configs');
const getSlaDashboard = (period: string = '30d') => request.get<unknown, SLADashboard>('/ops/sla/dashboard', { params: { period } });
const getSlaMetrics = (slaId: string) => request.get<unknown, unknown>(`/ops/sla/metrics/${slaId}`);
const generateSlaReport = (slaId: string, startDate: string, endDate: string) =>
  request.post<unknown, unknown>('/ops/sla/reports', null, { params: { sla_id: slaId, period_start: startDate, period_end: endDate } });

// ===== 状态颜色映射 =====
const STATUS_COLORS: Record<string, string> = {
  met: '#4caf50',
  at_risk: '#ff9800',
  breached: '#f44336',
};

const STATUS_LABELS: Record<string, string> = {
  met: '达标',
  at_risk: '风险',
  breached: '违规',
};

// ===== 主组件 =====
const OpsSLAPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState<string>('dashboard');
  const [selectedSla, setSelectedSla] = useState<string | null>(null);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [reportForm, setReportForm] = useState({ startDate: '', endDate: '' });

  // 获取 SLA 配置
  const { data: configsData, isLoading: configsLoading } = useQuery({
    queryKey: ['slaConfigs'],
    queryFn: () => getSlaConfigs(),
  });

  // 获取 SLA 仪表盘
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['slaDashboard'],
    queryFn: () => getSlaDashboard(),
  });

  const configs: SLAConfig[] = configsData?.configs ?? [];
  const dashboard: SLADashboard | null = dashboardData ?? null;

  // SLA 达标率图表选项
  const complianceChartOption = useMemo(() => {
    if (!dashboard) return {};
    return {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
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
          { value: dashboard.met_count, name: '达标', itemStyle: { color: '#4caf50' } },
          { value: dashboard.at_risk_count, name: '风险', itemStyle: { color: '#ff9800' } },
          { value: dashboard.breached_count, name: '违规', itemStyle: { color: '#f44336' } },
        ],
      }],
    };
  }, [dashboard]);

  // 指标达标率图表选项
  const metricsChartOption = useMemo(() => {
    if (!dashboard?.metrics?.length) return {};
    const metrics = dashboard.metrics.slice(0, 8);
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: metrics.map(m => m.metric_name.replace(/_/g, ' ')),
        axisLabel: { rotate: 30, fontSize: 11 },
      },
      yAxis: { type: 'value', name: '达标率 (%)', max: 100 },
      series: [{
        type: 'bar',
        data: metrics.map(m => ({
          value: m.compliance_percent,
          itemStyle: {
            color: STATUS_COLORS[m.status] || '#999',
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barWidth: '60%',
      }],
    };
  }, [dashboard]);

  // 面包屑
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: 'SLA 管理' }],
    [],
  );

  // 刷新数据
  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['slaConfigs'] });
    queryClient.invalidateQueries({ queryKey: ['slaDashboard'] });
  };

  // 生成报告
  const handleGenerateReport = async () => {
    if (!selectedSla || !reportForm.startDate || !reportForm.endDate) return;
    try {
      await generateSlaReport(selectedSla, reportForm.startDate, reportForm.endDate);
      setReportDialogOpen(false);
    } catch (error) {
      console.error('Failed to generate report:', error);
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title="SLA 管理"
        subtitle="服务等级协议监控与管理"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新数据' },
        ]}
        actions={[
          {
            label: '生成报告',
            icon: <AnalyticsIcon />,
            onClick: () => setReportDialogOpen(true),
            variant: 'contained',
            disabled: !selectedSla,
          },
        ]}
      />

      {/* 统计卡片 */}
      {dashboard && (
        <StatGrid columns={4}>
          <MetricsCard title="SLA 总数" value={dashboard.total_slas} icon={<CheckCircleFilledIcon />} color="primary" />
          <MetricsCard title="达标数量" value={dashboard.met_count} icon={<CheckCircleFilledIcon />} color="success" />
          <MetricsCard title="风险数量" value={dashboard.at_risk_count} icon={<ErrorCircleFilledIcon />} color="warning" />
          <MetricsCard title="总体达标率" value={Math.round(dashboard.overall_compliance)} icon={<CheckCircleFilledIcon />} color="info" unit="%" />
        </StatGrid>
      )}

      {/* Tab 切换 */}
      <div className="rounded-xl bg-white border border-gray-200">
        <Tabs value={tabValue} onChange={(val) => setTabValue(val as string)}>
          <Tabs.TabPanel value="dashboard" label="仪表盘">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 p-4">
              <div className="rounded-xl bg-white border border-gray-200 p-3 sm:p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-2">SLA 达标分布</h3>
                {dashboard && <ReactECharts option={complianceChartOption} style={{ height: 300 }} />}
              </div>
              <div className="rounded-xl bg-white border border-gray-200 p-3 sm:p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-2">指标达标率</h3>
                {dashboard && <ReactECharts option={metricsChartOption} style={{ height: 300 }} />}
              </div>
            </div>
          </Tabs.TabPanel>

          <Tabs.TabPanel value="configs" label="SLA 配置">
            <div className="p-4">
              <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-bold">名称</th>
                        <th className="px-4 py-3 text-left font-bold">服务</th>
                        <th className="px-4 py-3 text-left font-bold">指标数</th>
                        <th className="px-4 py-3 text-left font-bold">状态</th>
                        <th className="px-4 py-3 text-left font-bold">创建时间</th>
                        <th className="px-4 py-3 text-center font-bold">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {configs.map((config) => (
                        <tr key={config.sla_id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 font-medium">{config.name}</td>
                          <td className="px-4 py-3">{config.service_name || config.service_id}</td>
                          <td className="px-4 py-3">{config.targets.length}</td>
                          <td className="px-4 py-3">
                            <Tag theme={config.enabled ? 'success' : 'default'} variant="light">
                              {config.enabled ? '启用' : '禁用'}
                            </Tag>
                          </td>
                          <td className="px-4 py-3">{new Date(config.created_at).toLocaleDateString('zh-CN')}</td>
                          <td className="px-4 py-3 text-center">
                            <Button
                              size="small"
                              theme={selectedSla === config.sla_id ? 'primary' : 'default'}
                              variant={selectedSla === config.sla_id ? 'base' : 'outline'}
                              onClick={() => setSelectedSla(config.sla_id)}
                            >
                              选择
                            </Button>
                          </td>
                        </tr>
                      ))}
                      {configs.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无 SLA 配置</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Tabs.TabPanel>

          <Tabs.TabPanel value="metrics" label="指标详情">
            <div className="p-4">
              {dashboard?.metrics && dashboard.metrics.length > 0 ? (
                <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
                  <div className="flex-1 overflow-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left font-bold">指标</th>
                          <th className="px-4 py-3 text-left font-bold">当前值</th>
                          <th className="px-4 py-3 text-left font-bold">目标值</th>
                          <th className="px-4 py-3 text-left font-bold">达标率</th>
                          <th className="px-4 py-3 text-left font-bold">状态</th>
                          <th className="px-4 py-3 text-left font-bold">趋势</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashboard.metrics.map((metric, index) => (
                          <tr key={index} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3">
                              <span className="text-xs text-gray-600">{metric.metric_name.replace(/_/g, ' ')}</span>
                            </td>
                            <td className="px-4 py-3">{metric.current_value} {metric.unit}</td>
                            <td className="px-4 py-3">{metric.target_value} {metric.unit}</td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <Progress
                                  theme="line"
                                  percentage={Math.min(metric.compliance_percent, 100)}
                                  style={{ width: 100 }}
                                  color={STATUS_COLORS[metric.status]}
                                />
                                <span className="text-xs text-gray-600">{metric.compliance_percent.toFixed(1)}%</span>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                {metric.status === 'met' && <CheckCircleFilledIcon className="text-green-500" />}
                                {metric.status === 'breached' && <ErrorCircleFilledIcon className="text-red-500" />}
                                {metric.status === 'at_risk' && <ErrorCircleFilledIcon className="text-orange-500" />}
                                <Tag theme={metric.status === 'met' ? 'success' : metric.status === 'breached' ? 'danger' : 'warning'} variant="light">
                                  {STATUS_LABELS[metric.status]}
                                </Tag>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              {metric.trend === 'up' && <TrendingUpIcon className="text-green-500" />}
                              {metric.trend === 'down' && <TrendingDownIcon className="text-red-500" />}
                              {metric.trend === 'stable' && <span className="text-xs text-gray-400">—</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <p className="text-gray-400 text-center py-8">暂无指标数据</p>
              )}
            </div>
          </Tabs.TabPanel>
        </Tabs>
      </div>

      {/* 生成报告对话框 */}
      <Dialog visible={reportDialogOpen} onClose={() => setReportDialogOpen(false)} header="生成 SLA 报告" width="440px">
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">开始日期</label>
            <Input
              type="text"
              placeholder="YYYY-MM-DD"
              value={reportForm.startDate}
              onChange={(val) => setReportForm({ ...reportForm, startDate: String(val) })}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">结束日期</label>
            <Input
              type="text"
              placeholder="YYYY-MM-DD"
              value={reportForm.endDate}
              onChange={(val) => setReportForm({ ...reportForm, endDate: String(val) })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button onClick={() => setReportDialogOpen(false)}>取消</Button>
          <Button theme="primary" onClick={handleGenerateReport}>生成</Button>
        </div>
      </Dialog>

      <LoadingOverlay open={configsLoading || dashboardLoading} />
    </PageContainer>
  );
};

export default OpsSLAPage;
