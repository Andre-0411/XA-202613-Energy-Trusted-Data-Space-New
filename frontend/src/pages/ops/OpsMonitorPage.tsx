/**
 * 运维监控页面
 * 系统健康状态 + 告警列表 + 确认告警 + 统计卡片 + ECharts图表
 * 增强：集成实时系统指标和应用指标
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Select, Tooltip, Tabs, Progress, Divider } from 'tdesign-react';
import {
  RefreshIcon, CheckIcon, HeartIcon, ErrorCircleFilledIcon,
  CheckCircleFilledIcon, ServerIcon, CpuIcon, DashboardIcon, WifiIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getHealthCheck, getAlerts, acknowledgeAlert } from '@/api/ops';
import request from '@/api/request';
import type { AlertInfo } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

// 增强监控 API
const getSystemMetrics = () => request.get<any, any>('/ops/monitoring-enhanced/system');
const getApplicationMetrics = () => request.get<any, any>('/ops/monitoring-enhanced/application');
const getEnhancedHealth = () => request.get<any, any>('/ops/monitoring-enhanced/health');

const ALERT_STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'OPEN', label: '待处理' },
  { value: 'ACKNOWLEDGED', label: '已确认' },
  { value: 'RESOLVED', label: '已解决' },
];

const severityLabel = (s: string): string => {
  const m: Record<string, string> = { CRITICAL: '严重', HIGH: '高', MEDIUM: '中', LOW: '低', INFO: '信息' };
  return m[s] ?? s;
};

const alertStatusLabel = (s: string): string => {
  const m: Record<string, string> = { OPEN: '待处理', ACKNOWLEDGED: '已确认', RESOLVED: '已解决' };
  return m[s] ?? s;
};

const OpsMonitorPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState<string>('overview');

  // ===== 增强监控数据 =====
  const { data: systemMetricsData } = useQuery({
    queryKey: ['systemMetrics'],
    queryFn: () => getSystemMetrics(),
    refetchInterval: 30000,
  });

  const { data: appMetricsData } = useQuery({
    queryKey: ['appMetrics'],
    queryFn: () => getApplicationMetrics(),
    refetchInterval: 30000,
  });

  const { data: enhancedHealthData } = useQuery({
    queryKey: ['enhancedHealth'],
    queryFn: () => getEnhancedHealth(),
    refetchInterval: 30000,
  });

  const systemMetrics = systemMetricsData?.data ?? null;
  const appMetrics = appMetricsData?.data ?? null;
  const enhancedHealth = enhancedHealthData?.data ?? null;

  // ===== ECharts 配置 =====
  const alertTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['严重', '高', '中', '低'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '告警数' },
    series: [
      { name: '严重', type: 'bar', stack: 'total', data: [3, 5, 2, 4, 3, 6, 3], itemStyle: { color: '#f44336' } },
      { name: '高', type: 'bar', stack: 'total', data: [8, 12, 6, 10, 8, 14, 9], itemStyle: { color: '#ff9800' } },
      { name: '中', type: 'bar', stack: 'total', data: [15, 20, 12, 18, 15, 22, 16], itemStyle: { color: '#2196f3' } },
      { name: '低', type: 'bar', stack: 'total', data: [25, 30, 20, 28, 22, 35, 25], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const systemHealthOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [
      {
        name: '系统健康度',
        type: 'gauge',
        progress: { show: true },
        detail: { valueAnimation: true, formatter: '{value}%', fontSize: 24 },
        data: [{ value: enhancedHealth?.overall_status === 'healthy' ? 99.97 : enhancedHealth?.overall_status === 'warning' ? 85 : 60, name: '可用性' }],
        axisLine: { lineStyle: { width: 20, color: [[0.3, '#f44336'], [0.7, '#ff9800'], [1, '#4caf50']] } },
      },
    ],
  }), [enhancedHealth]);

  const resourceChartOption = useMemo(() => {
    if (!systemMetrics) return {};
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['CPU', '内存', '磁盘'], top: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['当前'] },
      yAxis: { type: 'value', name: '使用率 (%)', max: 100 },
      series: [
        { name: 'CPU', type: 'bar', data: [systemMetrics.cpu?.usage_percent || 0], itemStyle: { color: '#2196f3' } },
        { name: '内存', type: 'bar', data: [systemMetrics.memory?.usage_percent || 0], itemStyle: { color: '#4caf50' } },
        { name: '磁盘', type: 'bar', data: [systemMetrics.disk?.usage_percent || 0], itemStyle: { color: '#ff9800' } },
      ],
    };
  }, [systemMetrics]);

  // ===== 筛选 =====
  const [filterStatus, setFilterStatus] = useState<string>('');

  // ===== 确认告警 =====
  const [ackTarget, setAckTarget] = useState<AlertInfo | null>(null);

  // ===== 数据查询 =====
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['healthCheck'],
    queryFn: () => getHealthCheck(),
  });

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts', filterStatus],
    queryFn: () => getAlerts({ status: filterStatus || undefined }),
  });

  const alerts: AlertInfo[] = alertsData?.data?.items ?? [];
  const healthStatus: Record<string, unknown> = healthData?.data ?? {};

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    systemUptime: 99.97,
    activeAlerts: alerts.filter(a => a.status === 'active').length,
    resolvedToday: alerts.filter(a => {
      const today = new Date().toDateString();
      return a.status === 'resolved' && new Date(a.created_at).toDateString() === today;
    }).length,
    criticalAlerts: alerts.filter(a => a.severity === 'critical').length,
  }), [alerts]);

  // ===== Mutations =====
  const ackMut = useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setAckTarget(null);
    },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '运维监控' }],
    [],
  );

  const healthEntries = useMemo(() => {
    return Object.entries(healthStatus).map(([key, value]) => ({ key, value }));
  }, [healthStatus]);

  return (
    <PageContainer>
      <PageHeader
        title="运维监控"
        subtitle="系统健康状态与告警管理"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => { queryClient.invalidateQueries({ queryKey: ['healthCheck'] }); queryClient.invalidateQueries({ queryKey: ['alerts'] }); }, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="系统可用性" value={stats.systemUptime} icon={<HeartIcon />} gradient="purple" unit="%" />
        <MetricsCard title="活跃告警" value={stats.activeAlerts} icon={<ErrorCircleFilledIcon />} gradient="red" unit="" />
        <MetricsCard title="今日解决" value={stats.resolvedToday} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="严重告警" value={stats.criticalAlerts} icon={<ErrorCircleFilledIcon />} gradient={stats.criticalAlerts > 0 ? 'red' : 'green'} unit="" />
      </StatGrid>

      {/* Tab 切换 */}
      <div className="rounded-xl bg-white border border-gray-200">
        <Tabs value={tabValue} onChange={(val) => setTabValue(val as string)}>
          <Tabs.TabPanel value="overview" label="概览">
            {/* 图表区域 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4 p-4">
              <div className="md:col-span-2 rounded-xl bg-white border border-gray-200 p-3 sm:p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-2">告警趋势分析</h3>
                <ReactECharts option={alertTrendOption} style={{ height: 300 }} />
              </div>
              <div className="rounded-xl bg-white border border-gray-200 p-3 sm:p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-2">系统健康度</h3>
                <ReactECharts option={systemHealthOption} style={{ height: 300 }} />
              </div>
            </div>

            {/* 系统健康状态 */}
            <div className="p-4">
              <h3 className="text-sm font-semibold mb-3">系统健康状态</h3>
              {healthEntries.length === 0 ? (
                <p className="text-sm text-gray-400">加载中...</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                  {healthEntries.map(({ key, value }) => {
                    const isHealthy = value === 'healthy' || value === 'up' || value === true;
                    const isObject = typeof value === 'object' && value !== null;
                    return (
                      <div key={key} className="border border-gray-200 rounded-lg p-2">
                        <p className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</p>
                        <div className="mt-1">
                          {isObject ? (
                            <p className="text-xs">{JSON.stringify(value)}</p>
                          ) : (
                            <StatusTag status={String(value)} />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Tabs.TabPanel>

          <Tabs.TabPanel value="metrics" label="实时指标">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 p-4">
              {/* 系统资源 */}
              <div className="rounded-xl bg-white border border-gray-200 p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-3 flex items-center gap-2">
                  <ServerIcon /> 系统资源
                </h3>
                {systemMetrics && (
                  <div className="flex flex-col gap-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>CPU 使用率</span>
                        <span className="font-bold">{systemMetrics.cpu?.usage_percent?.toFixed(1)}%</span>
                      </div>
                      <Progress
                        theme="line"
                        percentage={systemMetrics.cpu?.usage_percent || 0}
                        color={(systemMetrics.cpu?.usage_percent || 0) > 80 ? '#f44336' : '#2196f3'}
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        核心数: {systemMetrics.cpu?.cores} | 负载: {systemMetrics.cpu?.load_average?.join(', ')}
                      </p>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>内存使用率</span>
                        <span className="font-bold">{systemMetrics.memory?.usage_percent?.toFixed(1)}%</span>
                      </div>
                      <Progress
                        theme="line"
                        percentage={systemMetrics.memory?.usage_percent || 0}
                        color={(systemMetrics.memory?.usage_percent || 0) > 85 ? '#f44336' : '#4caf50'}
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        已用: {systemMetrics.memory?.used_gb?.toFixed(1)}GB / 总计: {systemMetrics.memory?.total_gb}GB
                      </p>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>磁盘使用率</span>
                        <span className="font-bold">{systemMetrics.disk?.usage_percent?.toFixed(1)}%</span>
                      </div>
                      <Progress
                        theme="line"
                        percentage={systemMetrics.disk?.usage_percent || 0}
                        color={(systemMetrics.disk?.usage_percent || 0) > 90 ? '#f44336' : '#ff9800'}
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        已用: {systemMetrics.disk?.used_gb?.toFixed(1)}GB / 总计: {systemMetrics.disk?.total_gb}GB
                      </p>
                    </div>
                    <Divider />
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-gray-400">网络入流量</p>
                        <p className="text-base font-semibold">{(systemMetrics.network?.in_bytes_per_sec / 1024 / 1024).toFixed(2)} MB/s</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">网络出流量</p>
                        <p className="text-base font-semibold">{(systemMetrics.network?.out_bytes_per_sec / 1024 / 1024).toFixed(2)} MB/s</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 应用指标 */}
              <div className="rounded-xl bg-white border border-gray-200 p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-3 flex items-center gap-2">
                  <DashboardIcon /> 应用指标
                </h3>
                {appMetrics && (
                  <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">QPS</p>
                        <p className="text-xl font-bold text-blue-500">{appMetrics.api?.qps?.toFixed(0)}</p>
                      </div>
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">平均响应</p>
                        <p className={`text-xl font-bold ${appMetrics.api?.avg_response_time_ms > 200 ? 'text-red-500' : 'text-green-500'}`}>
                          {appMetrics.api?.avg_response_time_ms?.toFixed(0)}ms
                        </p>
                      </div>
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">错误率</p>
                        <p className={`text-xl font-bold ${appMetrics.api?.error_rate > 1 ? 'text-red-500' : 'text-green-500'}`}>
                          {appMetrics.api?.error_rate?.toFixed(2)}%
                        </p>
                      </div>
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">活跃请求</p>
                        <p className="text-xl font-bold">{appMetrics.api?.active_requests}</p>
                      </div>
                    </div>
                    <Divider />
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">数据库连接池</p>
                        <p className={`text-xl font-bold ${appMetrics.database?.connection_pool_usage > 80 ? 'text-orange-500' : 'text-green-500'}`}>
                          {appMetrics.database?.connection_pool_usage?.toFixed(1)}%
                        </p>
                      </div>
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">缓存命中率</p>
                        <p className="text-xl font-bold text-green-500">
                          {appMetrics.cache?.hit_rate?.toFixed(1)}%
                        </p>
                      </div>
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">WebSocket 连接</p>
                        <p className="text-xl font-bold">{appMetrics.websocket?.active_connections}</p>
                      </div>
                      <div className="border border-gray-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-400">慢查询</p>
                        <p className={`text-xl font-bold ${appMetrics.database?.slow_queries > 5 ? 'text-red-500' : 'text-green-500'}`}>
                          {appMetrics.database?.slow_queries}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 资源使用图表 */}
              <div className="md:col-span-2 rounded-xl bg-white border border-gray-200 p-3 sm:p-4">
                <h3 className="text-sm sm:text-base font-semibold mb-2">资源使用率对比</h3>
                {systemMetrics && <ReactECharts option={resourceChartOption} style={{ height: 300 }} />}
              </div>
            </div>
          </Tabs.TabPanel>

          <Tabs.TabPanel value="alerts" label="告警管理">
            {/* 告警筛选 */}
            <div className="p-4 pb-0">
              <div className="flex items-center gap-3">
                <Select
                  value={filterStatus}
                  onChange={(val) => setFilterStatus(String(val))}
                  options={ALERT_STATUS_OPTIONS}
                  style={{ minWidth: 160 }}
                  clearable
                />
              </div>
            </div>

            {/* 告警列表 */}
            <div className="p-4">
              <div className="flex-1 flex flex-col overflow-hidden rounded-xl bg-white border border-gray-200">
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-bold">标题</th>
                        <th className="px-4 py-3 text-left font-bold">类型</th>
                        <th className="px-4 py-3 text-left font-bold">严重级别</th>
                        <th className="px-4 py-3 text-left font-bold">状态</th>
                        <th className="px-4 py-3 text-left font-bold">来源</th>
                        <th className="px-4 py-3 text-left font-bold">触发时间</th>
                        <th className="px-4 py-3 text-center font-bold w-[100px]">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {alerts.map((alert) => (
                        <tr key={alert.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 font-medium">{alert.title}</td>
                          <td className="px-4 py-3">{alert.type}</td>
                          <td className="px-4 py-3">
                            <StatusTag status={severityLabel(alert.severity)} />
                          </td>
                          <td className="px-4 py-3"><StatusTag status={alertStatusLabel(alert.status)} /></td>
                          <td className="px-4 py-3">{alert.source}</td>
                          <td className="px-4 py-3">{new Date(alert.fired_at).toLocaleString('zh-CN')}</td>
                          <td className="px-4 py-3 text-center">
                            {alert.status === 'OPEN' && (
                              <Tooltip content="确认告警">
                                <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500" onClick={() => setAckTarget(alert)}>
                                  <CheckIcon />
                                </span>
                              </Tooltip>
                            )}
                          </td>
                        </tr>
                      ))}
                      {alerts.length === 0 && (
                        <tr>
                          <td colSpan={7} className="px-4 py-12 text-center text-gray-400">暂无告警</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Tabs.TabPanel>
        </Tabs>
      </div>

      {/* 确认告警弹窗 */}
      <ConfirmDialog
        open={!!ackTarget}
        title="确认告警"
        message={`确定要确认告警「${ackTarget?.title ?? ''}」吗？`}
        type="info"
        onConfirm={() => ackTarget && ackMut.mutate(ackTarget.id)}
        onCancel={() => setAckTarget(null)}
        loading={ackMut.isPending}
      />

      <LoadingOverlay open={healthLoading || alertsLoading} />
    </PageContainer>
  );
};

export default OpsMonitorPage;
