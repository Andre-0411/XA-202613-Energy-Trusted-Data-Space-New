/**
 * 仪表盘首页（重写版）
 * 能源可信数据空间 — 现代化运营仪表盘
 *
 * 重构后：主组件负责数据获取、角色配置、布局编排；
 * 子组件：StatsOverview / ChartsGrid / RecentActivity / QuickActions
 * 使用共享 StatCard 替代内联定义。
 */
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button, Tooltip } from 'tdesign-react';
import {
  AddIcon, MemberIcon, ServerIcon, CloudIcon, SettingIcon,
  ChartBarIcon, ErrorCircleIcon,
  ShieldErrorFilledIcon, LinkIcon,
  ComponentSwitchIcon, NotificationIcon, RefreshIcon,
  HistoryIcon,
} from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getKpiDashboard, getAlerts } from '@/api/ops';
import type { KpiDashboard, AlertInfo } from '@/types/api';
import { useAuthStore } from '@/stores/authStore';
import { getDashboardConfig, ROLE_DISPLAY_NAMES, type UserRole, type DashboardWidget } from '@/config/rolePermissions';

/* 子组件 */
import StatsOverview from './components/StatsOverview';
import ChartsGrid from './components/ChartsGrid';
import RecentActivity from './components/RecentActivity';
import QuickActions from './components/QuickActions';

/* ===== 响应式 hook ===== */
function useBreakpoint() {
  const [bp, setBp] = useState(() => {
    const w = window.innerWidth;
    return { isSmall: w < 600, isMobile: w < 900 };
  });
  useEffect(() => {
    const handler = () => {
      const w = window.innerWidth;
      setBp({ isSmall: w < 600, isMobile: w < 900 });
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);
  return bp;
}

/* ============================================================
 * DashboardPage 主组件
 * ============================================================ */
const DashboardPage: React.FC = () => {
  const { isSmall, isMobile } = useBreakpoint();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [refreshing, setRefreshing] = useState(false);

  // 获取用户角色
  const user = useAuthStore((s) => s.user);
  const userRole = (user?.role || 'user') as UserRole;
  const dashboardConfig = getDashboardConfig(userRole);

  const { data: kpiData, isLoading: kpiLoading } = useQuery({
    queryKey: ['kpiDashboard'],
    queryFn: () => getKpiDashboard(),
  });

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['dashboardAlerts'],
    queryFn: () => getAlerts({ limit: 6 }),
  });

  const kpi: KpiDashboard | null = kpiData?.data ?? null;
  const alerts: AlertInfo[] = alertsData?.data?.items ?? [];

  // 刷新数据
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['kpiDashboard'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboardAlerts'] }),
    ]);
    setTimeout(() => setRefreshing(false), 1000);
  }, [queryClient]);

  // 根据角色配置生成统计卡片数据
  const statCards = useMemo(() => {
    const widgetDataMap: Record<string, { value: number; unit: string; icon: React.ReactNode; gradient: string; trend: number }> = {
      total_users: { value: kpi?.active_users ?? 0, unit: '人', icon: <MemberIcon size="20px" />, gradient: 'green', trend: 15.2 },
      total_assets: { value: kpi?.total_assets ?? 0, unit: '项', icon: <ServerIcon size="20px" />, gradient: 'blue', trend: 12.5 },
      active_tasks: { value: kpi?.total_compute_tasks ?? 0, unit: '个', icon: <CloudIcon size="20px" />, gradient: 'purple', trend: 8.3 },
      system_health: { value: kpi?.uptime_percentage ?? 99.9, unit: '%', icon: <SettingIcon size="20px" />, gradient: 'cyan', trend: 0.5 },
      my_assets: { value: kpi?.total_assets ?? 0, unit: '项', icon: <ServerIcon size="20px" />, gradient: 'blue', trend: 12.5 },
      data_quality_score: { value: kpi?.data_quality_avg ?? 92, unit: '分', icon: <ChartBarIcon size="20px" />, gradient: 'green', trend: 2.1 },
      pending_requests: { value: 24, unit: '个', icon: <ErrorCircleIcon size="20px" />, gradient: 'orange', trend: -5.3 },
      data_usage: { value: 1250, unit: 'GB', icon: <ServerIcon size="20px" />, gradient: 'purple', trend: 18.7 },
      my_tasks: { value: 12, unit: '个', icon: <ChartBarIcon size="20px" />, gradient: 'blue', trend: 3.2 },
      available_assets: { value: 856, unit: '项', icon: <ServerIcon size="20px" />, gradient: 'green', trend: 8.5 },
      my_usage: { value: 45, unit: 'GB', icon: <CloudIcon size="20px" />, gradient: 'purple', trend: 12.1 },
      notifications: { value: 5, unit: '条', icon: <NotificationIcon size="20px" />, gradient: 'orange', trend: -2.3 },
      compliance_score: { value: kpi?.compliance_score ?? 88, unit: '分', icon: <ShieldErrorFilledIcon size="20px" />, gradient: 'green', trend: 1.8 },
      security_incidents: { value: 3, unit: '个', icon: <ShieldErrorFilledIcon size="20px" />, gradient: 'red', trend: -15.2 },
      audit_logs: { value: 1250, unit: '条', icon: <HistoryIcon size="20px" />, gradient: 'blue', trend: 22.5 },
      blockchain_txs: { value: kpi?.blockchain_transactions ?? 0, unit: '笔', icon: <LinkIcon size="20px" />, gradient: 'cyan', trend: 23.1 },
      system_uptime: { value: kpi?.uptime_percentage ?? 99.9, unit: '%', icon: <SettingIcon size="20px" />, gradient: 'green', trend: 0.5 },
      active_alerts: { value: 3, unit: '个', icon: <ErrorCircleIcon size="20px" />, gradient: 'red', trend: -10.2 },
      compute_nodes: { value: 8, unit: '个', icon: <ComponentSwitchIcon size="20px" />, gradient: 'purple', trend: 0 },
      resource_usage: { value: 67, unit: '%', icon: <SettingIcon size="20px" />, gradient: 'orange', trend: 5.3 },
    };

    return dashboardConfig
      .filter((widget: DashboardWidget) => widget.type === 'stat_card')
      .map((widget: DashboardWidget) => ({
        title: widget.title,
        ...widgetDataMap[widget.id],
      }))
      .filter((card) => card.value !== undefined);
  }, [kpi, dashboardConfig]);

  // 根据角色配置生成快捷操作
  const quickActions = useMemo(() => {
    const roleActions: Record<UserRole, { title: string; icon: React.ReactNode; color: string; path: string; description: string }[]> = {
      admin: [
        { title: '用户管理', icon: <MemberIcon size="20px" />, color: '#1976d2', path: '/dashboard/ops/users', description: '管理系统用户' },
        { title: '系统监控', icon: <SettingIcon size="20px" />, color: '#2e7d32', path: '/dashboard/ops/monitor', description: '查看系统状态' },
        { title: '安全策略', icon: <ShieldErrorFilledIcon size="20px" />, color: '#c62828', path: '/dashboard/security/policies', description: '配置安全策略' },
        { title: '数据资产', icon: <ServerIcon size="20px" />, color: '#7b1fa2', path: '/dashboard/data/assets', description: '管理数据资产' },
      ],
      data_admin: [
        { title: '创建数据源', icon: <ServerIcon size="20px" />, color: '#1976d2', path: '/dashboard/data/sources', description: '接入新的数据源' },
        { title: '数据质量', icon: <ChartBarIcon size="20px" />, color: '#2e7d32', path: '/dashboard/data/quality', description: '监控数据质量' },
        { title: '数据目录', icon: <ServerIcon size="20px" />, color: '#7b1fa2', path: '/dashboard/data/catalog', description: '浏览数据目录' },
        { title: '服务管理', icon: <CloudIcon size="20px" />, color: '#0097a7', path: '/dashboard/data/market', description: '管理数据服务' },
      ],
      user: [
        { title: '浏览数据', icon: <ServerIcon size="20px" />, color: '#1976d2', path: '/dashboard/data/catalog', description: '浏览数据目录' },
        { title: '创建任务', icon: <ChartBarIcon size="20px" />, color: '#7b1fa2', path: '/dashboard/compute/create', description: '创建计算任务' },
        { title: '我的任务', icon: <HistoryIcon size="20px" />, color: '#2e7d32', path: '/dashboard/compute/tasks', description: '查看我的任务' },
        { title: '个人中心', icon: <MemberIcon size="20px" />, color: '#0097a7', path: '/dashboard/portal/profile', description: '个人信息设置' },
      ],
      auditor: [
        { title: '合规审计', icon: <ShieldErrorFilledIcon size="20px" />, color: '#1976d2', path: '/dashboard/ops/compliance', description: '查看合规报告' },
        { title: '安全监控', icon: <ShieldErrorFilledIcon size="20px" />, color: '#c62828', path: '/dashboard/security/threats', description: '查看安全事件' },
        { title: '区块链存证', icon: <LinkIcon size="20px" />, color: '#0097a7', path: '/dashboard/blockchain/evidence', description: '查看存证记录' },
        { title: '审计日志', icon: <HistoryIcon size="20px" />, color: '#2e7d32', path: '/dashboard/ops/monitor', description: '查看审计日志' },
      ],
      operator: [
        { title: '系统监控', icon: <SettingIcon size="20px" />, color: '#1976d2', path: '/dashboard/ops/monitor', description: '系统性能监控' },
        { title: '计算节点', icon: <ComponentSwitchIcon size="20px" />, color: '#7b1fa2', path: '/dashboard/compute/tasks', description: '管理计算节点' },
        { title: '安全策略', icon: <ShieldErrorFilledIcon size="20px" />, color: '#c62828', path: '/dashboard/security/policies', description: '配置安全策略' },
        { title: '告警管理', icon: <ErrorCircleIcon size="20px" />, color: '#ed6c02', path: '/dashboard/ops/monitor', description: '查看系统告警' },
      ],
    };
    return roleActions[userRole] || roleActions.user;
  }, [userRole]);

  // 根据角色配置生成图表
  const chartWidgets = useMemo(() => {
    const chartConfigs: Record<string, { option: any; title: string; icon: React.ReactNode; chipLabel: string; chipColor: string }> = {
      user_growth_trend: {
        title: '用户增长趋势', icon: <MemberIcon size="18px" />, chipLabel: '近7月', chipColor: 'primary',
        option: { tooltip: { trigger: 'axis' as const }, xAxis: { type: 'category' as const, data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] }, yAxis: { type: 'value' as const }, series: [{ type: 'line' as const, data: [120, 150, 180, 210, 240, 260, 280], smooth: true, areaStyle: { color: 'rgba(25, 118, 210, 0.2)' }, lineStyle: { color: '#1976d2' } }] },
      },
      asset_distribution: {
        title: '资产类型分布', icon: <ServerIcon size="18px" />, chipLabel: '实时', chipColor: 'success',
        option: { tooltip: { trigger: 'item' as const }, series: [{ type: 'pie' as const, radius: ['40%', '70%'], data: [{ value: 580, name: '电力数据' }, { value: 420, name: '油气数据' }, { value: 350, name: '新能源数据' }, { value: 280, name: '气象数据' }, { value: 220, name: '其他' }] }] },
      },
      asset_growth: {
        title: '资产增长趋势', icon: <MemberIcon size="18px" />, chipLabel: '近7月', chipColor: 'primary',
        option: { tooltip: { trigger: 'axis' as const }, xAxis: { type: 'category' as const, data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] }, yAxis: { type: 'value' as const }, series: [{ type: 'line' as const, data: [800, 920, 1050, 1120, 1180, 1220, 1250], smooth: true, areaStyle: { color: 'rgba(25, 118, 210, 0.2)' }, lineStyle: { color: '#1976d2' } }] },
      },
      quality_trend: {
        title: '质量趋势', icon: <ChartBarIcon size="18px" />, chipLabel: '近7月', chipColor: 'success',
        option: { tooltip: { trigger: 'axis' as const }, xAxis: { type: 'category' as const, data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] }, yAxis: { type: 'value' as const, max: 100 }, series: [{ type: 'line' as const, data: [85, 87, 89, 91, 90, 92, 94], smooth: true, areaStyle: { color: 'rgba(46, 125, 50, 0.2)' }, lineStyle: { color: '#2e7d32' } }] },
      },
      task_history: {
        title: '任务历史', icon: <ChartBarIcon size="18px" />, chipLabel: '近7天', chipColor: 'primary',
        option: { tooltip: { trigger: 'axis' as const }, xAxis: { type: 'category' as const, data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] }, yAxis: { type: 'value' as const }, series: [{ type: 'bar' as const, data: [5, 8, 12, 6, 9, 3, 7], itemStyle: { color: '#7b1fa2' } }] },
      },
      data_catalog: {
        title: '数据目录', icon: <ServerIcon size="18px" />, chipLabel: '分类', chipColor: 'success',
        option: { tooltip: { trigger: 'item' as const }, series: [{ type: 'pie' as const, radius: ['40%', '70%'], data: [{ value: 320, name: '电力数据' }, { value: 240, name: '油气数据' }, { value: 180, name: '新能源数据' }, { value: 150, name: '气象数据' }, { value: 120, name: '其他' }] }] },
      },
      compliance_trend: {
        title: '合规趋势', icon: <ShieldErrorFilledIcon size="18px" />, chipLabel: '近7月', chipColor: 'primary',
        option: { tooltip: { trigger: 'axis' as const }, xAxis: { type: 'category' as const, data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] }, yAxis: { type: 'value' as const, max: 100 }, series: [{ type: 'line' as const, data: [82, 84, 86, 88, 87, 89, 91], smooth: true, areaStyle: { color: 'rgba(46, 125, 50, 0.2)' }, lineStyle: { color: '#2e7d32' } }] },
      },
      threat_distribution: {
        title: '威胁分布', icon: <ShieldErrorFilledIcon size="18px" />, chipLabel: '实时', chipColor: 'error',
        option: { tooltip: { trigger: 'item' as const }, series: [{ type: 'pie' as const, radius: ['40%', '70%'], data: [{ value: 45, name: 'DDoS攻击' }, { value: 32, name: 'SQL注入' }, { value: 28, name: 'XSS攻击' }, { value: 18, name: '暴力破解' }, { value: 12, name: '其他' }] }] },
      },
      performance_trend: {
        title: '性能趋势', icon: <SettingIcon size="18px" />, chipLabel: '近7天', chipColor: 'primary',
        option: { tooltip: { trigger: 'axis' as const }, xAxis: { type: 'category' as const, data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] }, yAxis: { type: 'value' as const, max: 100 }, series: [{ type: 'line' as const, data: [95, 97, 96, 98, 97, 99, 98], smooth: true, areaStyle: { color: 'rgba(25, 118, 210, 0.2)' }, lineStyle: { color: '#1976d2' } }] },
      },
      node_status: {
        title: '节点状态', icon: <ComponentSwitchIcon size="18px" />, chipLabel: '实时', chipColor: 'success',
        option: { tooltip: { trigger: 'item' as const }, series: [{ type: 'pie' as const, radius: ['40%', '70%'], data: [{ value: 6, name: '在线' }, { value: 1, name: '离线' }, { value: 1, name: '维护中' }] }] },
      },
    };

    return dashboardConfig
      .filter((widget: DashboardWidget) => widget.type === 'chart')
      .map((widget: DashboardWidget) => ({ ...widget, ...chartConfigs[widget.id] }))
      .filter((chart) => chart.option);
  }, [dashboardConfig]);

  // 系统健康状态
  const systemHealth = useMemo(() => [
    { label: 'API 响应时间', value: 95, color: '#4caf50', status: 'excellent' as const },
    { label: '系统可用率', value: kpi?.uptime_percentage ?? 99.9, color: '#2196f3', status: 'excellent' as const },
    { label: '数据质量评分', value: kpi?.data_quality_avg ?? 92, color: '#ff9800', status: 'good' as const },
    { label: '安全合规评分', value: kpi?.compliance_score ?? 88, color: '#9c27b0', status: 'good' as const },
  ], [kpi]);

  /** 图表自适应高度 */
  const chartHeight = isSmall ? 220 : isMobile ? 260 : 300;

  return (
    <div>
      {/* 顶部欢迎区域 */}
      <div
        className="text-white pt-8 sm:pt-10 pb-12 sm:pb-16 px-4 sm:px-6 md:px-8 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #1976d2 0%, #0d47a1 50%, #1565c0 100%)' }}
      >
        <div className="absolute rounded-full opacity-5" style={{ top: -100, right: -100, width: 400, height: 400, background: 'white' }} />
        <div className="absolute rounded-full opacity-3" style={{ bottom: -150, left: -150, width: 300, height: 300, background: 'white' }} />
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold mb-1 m-0">{ROLE_DISPLAY_NAMES[userRole]}仪表盘</h1>
              <p className="text-sm text-white/70 m-0">能源可信数据空间实时监控中心 — 掌握数据资产、计算任务、安全态势全貌</p>
            </div>
            <div className="flex items-center gap-3">
              <Tooltip content="刷新数据">
                <span
                  className="cursor-pointer inline-flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-white/15 text-white hover:bg-white/25 transition-colors"
                  onClick={handleRefresh}
                >
                  <RefreshIcon size={isSmall ? '18px' : '20px'} className={refreshing ? 'animate-spin' : ''} />
                </span>
              </Tooltip>
              <Button
                theme="primary"
                icon={<HistoryIcon />}
                size={isSmall ? 'small' : 'medium'}
                className="!bg-white/15 !backdrop-blur-sm hover:!bg-white/25 !border-0"
                onClick={() => navigate('/monitor-screen')}
              >
                监管大屏
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="max-w-7xl mx-auto -mt-8 relative z-10 px-3 sm:px-6">
        {/* 统计卡片 */}
        <StatsOverview statCards={statCards} loading={kpiLoading} />

        {/* 图表区域 */}
        <ChartsGrid chartWidgets={chartWidgets} chartHeight={chartHeight} />

        {/* 下方区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 mb-6">
          <QuickActions systemHealth={systemHealth} quickActions={quickActions} />
          <RecentActivity alerts={alerts} loading={alertsLoading} isSmall={isSmall} />
        </div>

        {/* 底部信息栏 */}
        <div className="rounded-xl bg-blue-50 border border-blue-100 shadow-sm p-4 sm:p-5 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-4 sm:gap-6 flex-wrap">
              <span className="text-xs text-gray-500">平台版本: v2.0.0</span>
              <span className="text-xs text-gray-500">API 响应: {kpi?.avg_response_time_ms ?? 45}ms</span>
              <span className="text-xs text-gray-500">系统可用率: {kpi?.uptime_percentage ?? 99.9}%</span>
            </div>
            <span className="text-xs text-gray-500">数据更新时间: {new Date().toLocaleString('zh-CN')}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
