/**
 * 操作日志审计页面
 * 提供操作日志查询、筛选、导出和统计功能
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tag, Tooltip, Pagination, MessagePlugin } from 'tdesign-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getAuditLogs, getActionTypes, getResourceTypes, getModules,
  getAuditLogStatistics, exportAuditLogs, type AuditLog, type AuditLogStatistics,
} from '@/api/system';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import {
  AddIcon, BrowseIcon, CheckCircleFilledIcon, CloudDownloadIcon, CloudUploadIcon,
  DashboardIcon, DeleteIcon, EditIcon, ErrorCircleFilledIcon, ErrorIcon,
  FolderOpenIcon, InfoCircleFilledIcon, LoginIcon, LogoutIcon,
  RefreshIcon, SearchIcon, SettingIcon, ShieldErrorFilledIcon, TimeIcon, UserIcon,
} from 'tdesign-icons-react';

/** 操作类型配置 */
const ACTION_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  login: { icon: <LoginIcon />, color: '#4caf50', label: '登录' },
  logout: { icon: <LogoutIcon />, color: '#9e9e9e', label: '登出' },
  create: { icon: <AddIcon />, color: '#2196f3', label: '创建' },
  update: { icon: <EditIcon />, color: '#ff9800', label: '更新' },
  delete: { icon: <DeleteIcon />, color: '#f44336', label: '删除' },
  query: { icon: <SearchIcon />, color: '#9c27b0', label: '查询' },
  download: { icon: <CloudDownloadIcon />, color: '#00bcd4', label: '下载' },
  upload: { icon: <CloudUploadIcon />, color: '#795548', label: '上传' },
  submit: { icon: <CheckCircleFilledIcon />, color: '#4caf50', label: '提交' },
  approve: { icon: <ShieldErrorFilledIcon />, color: '#4caf50', label: '审批' },
  reject: { icon: <ErrorIcon />, color: '#f44336', label: '拒绝' },
  export: { icon: <FolderOpenIcon />, color: '#2196f3', label: '导出' },
  deploy: { icon: <SettingIcon />, color: '#ff9800', label: '部署' },
  apply: { icon: <UserIcon />, color: '#9c27b0', label: '申请' },
};

/** 状态配置 */
const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  success: { color: '#4caf50', label: '成功' },
  failed: { color: '#f44336', label: '失败' },
  pending: { color: '#ff9800', label: '待处理' },
};

const ACTION_TYPE_OPTIONS = [
  { value: 'all', label: '全部操作' },
];
const MODULE_OPTIONS = [
  { value: 'all', label: '全部模块' },
];
const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'pending', label: '待处理' },
];

const AuditLogPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态管理 =====
  const [page, setPage] = useState<number>(0);
  const [rowsPerPage, setRowsPerPage] = useState<number>(20);
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [filterAction, setFilterAction] = useState<string>('all');
  const [filterModule, setFilterModule] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  // ===== 数据查询 =====
  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['auditLogs', page, rowsPerPage, filterAction, filterModule, filterStatus, searchKeyword],
    queryFn: () => getAuditLogs({
      page: page + 1,
      page_size: rowsPerPage,
      action: filterAction !== 'all' ? filterAction : undefined,
      module: filterModule !== 'all' ? filterModule : undefined,
      status: filterStatus !== 'all' ? filterStatus : undefined,
      keyword: searchKeyword || undefined,
    }),
  });

  const { data: statisticsData } = useQuery({
    queryKey: ['auditLogStatistics'],
    queryFn: getAuditLogStatistics,
  });

  const { data: actionsData } = useQuery({
    queryKey: ['actionTypes'],
    queryFn: getActionTypes,
  });

  const { data: modulesData } = useQuery({
    queryKey: ['modules'],
    queryFn: getModules,
  });

  const logs: AuditLog[] = logsData?.data?.data?.items ?? [];
  const totalCount: number = logsData?.data?.data?.total ?? 0;
  const statistics: AuditLogStatistics | null = statisticsData?.data?.data ?? null;
  const actionTypes: { value: string; label: string }[] = actionsData?.data?.data ?? [];
  const modules: { value: string; label: string }[] = modulesData?.data?.data ?? [];

  // 构建动态选项
  const actionOptions = useMemo(() => [
    { value: 'all', label: '全部操作' },
    ...actionTypes.map(a => ({ value: a.value, label: a.label })),
  ], [actionTypes]);

  const moduleOptions = useMemo(() => [
    { value: 'all', label: '全部模块' },
    ...modules.map(m => ({ value: m.value, label: m.label })),
  ], [modules]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalLogs: statistics?.total_logs ?? 0,
    todayCount: statistics?.today_count ?? 0,
    successRate: statistics?.status_stats?.success
      ? Math.round((statistics.status_stats.success / statistics.total_logs) * 100)
      : 0,
    topAction: statistics?.action_stats
      ? Object.entries(statistics.action_stats).sort(([,a], [,b]) => b - a)[0]?.[0] || '-'
      : '-',
  }), [statistics]);

  // ===== ECharts配置 =====
  const actionChartOption = useMemo(() => {
    if (!statistics?.action_stats) return {};
    const data = Object.entries(statistics.action_stats).map(([key, value]) => ({
      name: ACTION_CONFIG[key]?.label || key,
      value,
      itemStyle: { color: ACTION_CONFIG[key]?.color || '#667eea' },
    }));
    return {
      tooltip: { trigger: 'item' as const },
      legend: { orient: 'vertical' as const, right: 10, top: 20 },
      series: [{
        name: '操作类型',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
        labelLine: { show: false },
        data,
      }],
    };
  }, [statistics]);

  const moduleChartOption = useMemo(() => {
    if (!statistics?.module_stats) return {};
    const categories = Object.keys(statistics.module_stats);
    const values = Object.values(statistics.module_stats);
    return {
      tooltip: { trigger: 'axis' as const },
      xAxis: { type: 'category' as const, data: categories },
      yAxis: { type: 'value' as const },
      series: [{
        type: 'bar',
        data: values.map((value, index) => ({
          value,
          itemStyle: { color: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#ff6b6b'][index % 7] },
        })),
        barWidth: '40%',
      }],
    };
  }, [statistics]);

  // ===== 事件处理 =====
  const handleRefresh = useCallback(() => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['auditLogStatistics'] });
  }, [refetch, queryClient]);

  const handleViewDetail = useCallback((log: AuditLog) => {
    setSelectedLog(log);
    setDetailOpen(true);
  }, []);

  const handleExport = useCallback(() => {
    exportAuditLogs({
      format: 'csv',
      action: filterAction !== 'all' ? filterAction : undefined,
      module: filterModule !== 'all' ? filterModule : undefined,
    }).then((data: any) => {
      MessagePlugin.success(`导出成功，共 ${data.data?.data?.count} 条记录`);
    });
  }, [filterAction, filterModule]);

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  return (
    <PageContainer>
      <PageHeader
        title="操作日志"
        subtitle="系统操作审计日志查询与分析"
        breadcrumbs={[homeBreadcrumb]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
          { icon: <FolderOpenIcon />, onClick: handleExport, tooltip: '导出日志' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总日志数" value={stats.totalLogs} icon={<TimeIcon />} color="primary" />
        <MetricsCard title="今日操作" value={stats.todayCount} icon={<DashboardIcon />} color="warning" />
        <MetricsCard title="成功率" value={stats.successRate} icon={<CheckCircleFilledIcon />} color="success" unit="%" />
        <MetricsCard title="最频繁操作" value={0} icon={<ShieldErrorFilledIcon />} color="secondary" unit="" />
      </StatGrid>

      {/* ECharts图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="操作类型分布" option={actionChartOption} height={300} />
        <ChartCard title="模块操作统计" option={moduleChartOption} height={300} />
      </div>

      {/* 筛选区域 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <div className="flex flex-wrap items-center gap-4">
          <Input
            placeholder="搜索操作日志..."
            value={searchKeyword}
            onChange={(val) => setSearchKeyword(String(val))}
            prefixIcon={<SearchIcon />}
            style={{ width: 240 }}
          />
          <Select
            value={filterAction}
            options={actionOptions}
            onChange={(val) => { setFilterAction(String(val)); setPage(0); }}
            style={{ width: 140 }}
          />
          <Select
            value={filterModule}
            options={moduleOptions}
            onChange={(val) => { setFilterModule(String(val)); setPage(0); }}
            style={{ width: 140 }}
          />
          <Select
            value={filterStatus}
            options={STATUS_OPTIONS}
            onChange={(val) => { setFilterStatus(String(val)); setPage(0); }}
            style={{ width: 140 }}
          />
          <Button
            variant="outline"
            icon={<FolderOpenIcon />}
            onClick={handleExport}
          >
            导出日志
          </Button>
        </div>
      </div>

      {/* 日志表格 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">时间</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">用户</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">操作</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">资源</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">模块</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">状态</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">IP地址</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">详情</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {logs.map((log) => {
                    const actionConfig = ACTION_CONFIG[log.action] || { icon: <InfoCircleFilledIcon />, color: '#9e9e9e', label: log.action };
                    const statusConfig = STATUS_CONFIG[log.status] || STATUS_CONFIG.pending;

                    return (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {formatTime(log.timestamp)}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium">
                              {log.username.charAt(0)}
                            </div>
                            <span className="text-sm">{log.username}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Tag
                            icon={actionConfig.icon as React.ReactElement}
                            style={{ backgroundColor: `${actionConfig.color}20`, color: actionConfig.color }}
                          >
                            {actionConfig.label}
                          </Tag>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {log.resource_name || log.resource_type}
                        </td>
                        <td className="px-4 py-3">
                          <Tag variant="outline">{log.module}</Tag>
                        </td>
                        <td className="px-4 py-3">
                          <Tag style={{ backgroundColor: `${statusConfig.color}20`, color: statusConfig.color }}>
                            {statusConfig.label}
                          </Tag>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {log.ip_address}
                        </td>
                        <td className="px-4 py-3">
                          <Tooltip content="查看详情">
                            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => handleViewDetail(log)}>
                              <BrowseIcon />
                            </span>
                          </Tooltip>
                        </td>
                      </tr>
                    );
                  })}
                  {logs.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-gray-500">暂无数据</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex justify-end p-4 border-t border-gray-100">
              <Pagination
                current={page + 1}
                total={totalCount}
                pageSize={rowsPerPage}
                onCurrentChange={(current) => setPage(current - 1)}
                onPageSizeChange={(size) => { setRowsPerPage(size); setPage(0); }}
                showPageSize
                pageSizeOptions={[10, 20, 50, 100]}
              />
            </div>
          </>
        )}
      </div>

      {/* 日志详情对话框 */}
      <Dialog
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        header="操作详情"
        footer={
          <Button onClick={() => setDetailOpen(false)}>关闭</Button>
        }
      >
        {selectedLog && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ backgroundColor: `${ACTION_CONFIG[selectedLog.action]?.color || '#9e9e9e'}20`, color: ACTION_CONFIG[selectedLog.action]?.color || '#9e9e9e' }}
              >
                {ACTION_CONFIG[selectedLog.action]?.icon || <InfoCircleFilledIcon />}
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-800">操作详情</h3>
                <span className="text-xs text-gray-500">
                  {formatTime(selectedLog.timestamp)}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-gray-500">操作用户</span>
                <p className="text-sm text-gray-700">{selectedLog.username} ({selectedLog.user_id})</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">操作类型</span>
                <div className="mt-1">
                  <Tag
                    icon={ACTION_CONFIG[selectedLog.action]?.icon as React.ReactElement}
                    style={{ backgroundColor: `${ACTION_CONFIG[selectedLog.action]?.color || '#9e9e9e'}20`, color: ACTION_CONFIG[selectedLog.action]?.color || '#9e9e9e' }}
                  >
                    {ACTION_CONFIG[selectedLog.action]?.label || selectedLog.action}
                  </Tag>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">资源类型</span>
                <p className="text-sm text-gray-700">{selectedLog.resource_type}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">资源ID</span>
                <p className="text-sm text-gray-700">{selectedLog.resource_id || '-'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">资源名称</span>
                <p className="text-sm text-gray-700">{selectedLog.resource_name || '-'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">所属模块</span>
                <div className="mt-1">
                  <Tag variant="outline">{selectedLog.module}</Tag>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">IP地址</span>
                <p className="text-sm text-gray-700">{selectedLog.ip_address}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">状态</span>
                <div className="mt-1">
                  <Tag style={{ backgroundColor: `${STATUS_CONFIG[selectedLog.status]?.color || '#9e9e9e'}20`, color: STATUS_CONFIG[selectedLog.status]?.color || '#9e9e9e' }}>
                    {STATUS_CONFIG[selectedLog.status]?.label || selectedLog.status}
                  </Tag>
                </div>
              </div>
            </div>

            <hr className="border-gray-200 my-2" />

            <div>
              <span className="text-xs text-gray-500">操作详情</span>
              <div className="mt-1 rounded-lg bg-gray-50 border border-gray-200 p-3">
                <span className="text-xs text-gray-600">{selectedLog.details || '无详细信息'}</span>
              </div>
            </div>

            {selectedLog.user_agent && (
              <div>
                <span className="text-xs text-gray-500">用户代理</span>
                <div className="mt-1 rounded-lg bg-gray-50 border border-gray-200 p-3">
                  <span className="text-xs text-gray-600">{selectedLog.user_agent}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default AuditLogPage;
