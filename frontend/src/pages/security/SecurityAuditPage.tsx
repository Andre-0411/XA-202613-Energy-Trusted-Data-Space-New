/**
 * 增强审计页面
 * 全链路操作日志、异常行为检测、审计报告
 */
import React, { useState, useMemo } from 'react';
import { Button, Dialog, Tag, Tooltip } from 'tdesign-react';
import {
  RefreshIcon, AddIcon, TimeIcon,
  CheckCircleFilledIcon, ShieldErrorFilledIcon, ErrorCircleFilledIcon,
} from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import request from '@/api/request';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable, { type Column } from '@/components/common/DataTable';
import FilterBar, { type FilterField } from '@/components/common/FilterBar';

// ===== 类型定义 =====
interface AuditLog {
  log_id: string;
  trace_id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: string;
  ip_address: string;
  user_agent: string;
  status: string;
  timestamp: string;
  risk_level: string;
}

interface Anomaly {
  anomaly_id: string;
  user_id: string;
  type: string;
  risk_level: string;
  description: string;
  log_id: string;
  detected_at: string;
}

interface AuditStatistics {
  total_logs: number;
  total_anomalies: number;
  last_24h_logs: number;
  last_24h_anomalies: number;
  total_reports: number;
  risk_distribution: { low: number; medium: number; high: number; critical: number };
}

// ===== API 函数 =====
const getAuditLogs = (params: any) => request.get<any, any>('/security/audit/logs', { params });
const getAnomalies = (params: any) => request.get<any, any>('/security/audit/anomalies', { params });
const getAuditStatistics = () => request.get<any, any>('/security/audit/statistics');
const getTraceLogs = (traceId: string) => request.get<any, any>(`/security/audit/trace/${traceId}`);
const generateAuditReport = (startDate: string, endDate: string, title?: string) =>
  request.post<any, any>('/security/audit/reports', null, { params: { period_start: startDate, period_end: endDate, title } });

// ===== 面包屑 =====
const breadcrumbs: BreadcrumbItem[] = [
  homeBreadcrumb,
  { label: '安全管控' },
  { label: '增强审计' },
];

// ===== 映射表 =====
const RISK_COLORS: Record<string, string> = { low: '#4caf50', medium: '#ff9800', high: '#f44336', critical: '#9c27b0' };
const RISK_LABELS: Record<string, string> = { low: '低', medium: '中', high: '高', critical: '严重' };
const ANOMALY_TYPE_LABELS: Record<string, string> = {
  unusual_time: '异常时间', high_frequency: '高频操作', brute_force: '暴力破解', ip_change: 'IP 变化',
};

// ===== 主组件 =====
const SecurityAuditPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [filters, setFilters] = useState({ user_id: '', action: '', resource_type: '', risk_level: '' });
  const [traceDialogOpen, setTraceDialogOpen] = useState(false);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [reportForm, setReportForm] = useState({ startDate: '', endDate: '', title: '' });

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['auditLogs', filters],
    queryFn: () => getAuditLogs({ ...filters, limit: 100 }),
  });
  const { data: anomaliesData } = useQuery({ queryKey: ['auditAnomalies'], queryFn: () => getAnomalies({ limit: 50 }) });
  const { data: statsData } = useQuery({ queryKey: ['auditStatistics'], queryFn: () => getAuditStatistics() });
  const { data: traceData } = useQuery({
    queryKey: ['traceLogs', selectedTraceId],
    queryFn: () => getTraceLogs(selectedTraceId!),
    enabled: !!selectedTraceId,
  });

  const logs: AuditLog[] = logsData?.data?.items ?? [];
  const anomalies: Anomaly[] = anomaliesData?.data?.anomalies ?? [];
  const stats: AuditStatistics | null = statsData?.data ?? null;
  const traceLogs: AuditLog[] = traceData?.data?.logs ?? [];

  const riskChartOption = useMemo(() => {
    if (!stats) return {};
    return {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        data: [
          { value: stats.risk_distribution.low, name: '低风险', itemStyle: { color: '#4caf50' } },
          { value: stats.risk_distribution.medium, name: '中风险', itemStyle: { color: '#ff9800' } },
          { value: stats.risk_distribution.high, name: '高风险', itemStyle: { color: '#f44336' } },
          { value: stats.risk_distribution.critical, name: '严重', itemStyle: { color: '#9c27b0' } },
        ].filter(d => d.value > 0),
      }],
    };
  }, [stats]);

  const anomalyChartOption = useMemo(() => {
    if (!anomalies.length) return {};
    const typeCounts: Record<string, number> = {};
    anomalies.forEach(a => { typeCounts[a.type] = (typeCounts[a.type] || 0) + 1; });
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: Object.keys(typeCounts).map(k => ANOMALY_TYPE_LABELS[k] || k) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: Object.values(typeCounts), itemStyle: { color: '#ff9800', borderRadius: [4, 4, 0, 0] } }],
    };
  }, [anomalies]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['auditLogs'] });
    queryClient.invalidateQueries({ queryKey: ['auditAnomalies'] });
    queryClient.invalidateQueries({ queryKey: ['auditStatistics'] });
  };

  const handleGenerateReport = async () => {
    if (!reportForm.startDate || !reportForm.endDate) return;
    try {
      await generateAuditReport(reportForm.startDate, reportForm.endDate, reportForm.title);
      setReportDialogOpen(false);
    } catch (error) { console.error('Failed to generate audit report:', error); }
  };

  const filterFields: FilterField[] = [
    { name: 'user_id', type: 'text', placeholder: '用户 ID', width: 140 },
    { name: 'action', type: 'text', placeholder: '操作类型', width: 140 },
    { name: 'risk_level', type: 'select', placeholder: '风险等级', width: 120, options: [
      { value: '', label: '全部' }, { value: 'low', label: '低' }, { value: 'medium', label: '中' },
      { value: 'high', label: '高' }, { value: 'critical', label: '严重' },
    ]},
  ];

  const logColumns: Column<AuditLog>[] = [
    { id: 'timestamp', label: '时间', render: (row) => <span className="text-xs text-gray-600">{new Date(row.timestamp).toLocaleString()}</span> },
    { id: 'user_id', label: '用户' },
    { id: 'action', label: '操作' },
    { id: 'resource_type', label: '资源类型' },
    { id: 'status', label: '状态', render: (row) => <Tag theme={row.status === 'success' ? 'success' : 'danger'} variant="light">{row.status}</Tag> },
    { id: 'risk_level', label: '风险', render: (row) => <Tag style={{ backgroundColor: RISK_COLORS[row.risk_level] || '#999', color: '#fff', border: 'none' }}>{RISK_LABELS[row.risk_level] || row.risk_level}</Tag> },
    { id: 'ip_address', label: 'IP', render: (row) => <span className="text-xs text-gray-600">{row.ip_address}</span> },
    { id: 'trace_id', label: '追踪', render: (row) => (
      <Tooltip content="查看全链路">
        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => { setSelectedTraceId(row.trace_id); setTraceDialogOpen(true); }}>
          <TimeIcon style={{ fontSize: 16 }} />
        </span>
      </Tooltip>
    )},
  ];

  const anomalyColumns: Column<Anomaly>[] = [
    { id: 'detected_at', label: '时间', render: (row) => <span className="text-xs text-gray-600">{new Date(row.detected_at).toLocaleString()}</span> },
    { id: 'user_id', label: '用户' },
    { id: 'type', label: '类型', render: (row) => <Tag theme="warning" variant="light">{ANOMALY_TYPE_LABELS[row.type] || row.type}</Tag> },
    { id: 'risk_level', label: '风险等级', render: (row) => <Tag style={{ backgroundColor: RISK_COLORS[row.risk_level] || '#999', color: '#fff', border: 'none' }}>{RISK_LABELS[row.risk_level] || row.risk_level}</Tag> },
    { id: 'description', label: '描述' },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="增强审计"
        subtitle="全链路操作日志追踪与异常行为检测"
        breadcrumbs={breadcrumbs}
        iconActions={[{ icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新数据' }]}
        actions={[{ label: '生成报告', icon: <AddIcon />, onClick: () => setReportDialogOpen(true), variant: 'contained' }]}
      />

      {stats && (
        <StatGrid columns={4}>
          <MetricsCard title="总日志数" value={stats.total_logs} icon={<ShieldErrorFilledIcon />} color="primary" />
          <MetricsCard title="24h 日志" value={stats.last_24h_logs} icon={<TimeIcon />} color="info" />
          <MetricsCard title="异常行为" value={stats.total_anomalies} icon={<ErrorCircleFilledIcon />} color="warning" />
          <MetricsCard title="审计报告" value={stats.total_reports} icon={<CheckCircleFilledIcon />} color="success" />
        </StatGrid>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="风险等级分布" option={riskChartOption} height={250} loading={!stats} />
        <ChartCard title="异常类型分布" option={anomalyChartOption} height={250} loading={!anomalies.length} />
      </div>

      <FilterBar fields={filterFields} values={filters} onChange={(name, value) => setFilters({ ...filters, [name]: value })} onSearch={() => queryClient.invalidateQueries({ queryKey: ['auditLogs'] })} />

      <PageSection>
        <div className="flex border-b border-gray-200 mb-4">
          <button className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${tabValue === 0 ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`} onClick={() => setTabValue(0)}>操作日志</button>
          <button className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${tabValue === 1 ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`} onClick={() => setTabValue(1)}>
            <span className="relative">异常行为{anomalies.length > 0 && <span className="absolute -top-2 -right-4 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[18px] text-center">{anomalies.length}</span>}</span>
          </button>
        </div>
        {tabValue === 0 && <DataTable columns={logColumns} data={logs} loading={logsLoading} emptyMessage="暂无审计日志" />}
        {tabValue === 1 && (
          anomalies.length === 0 ? (
            <div className="rounded-lg bg-green-50 border border-green-200 p-4 flex items-center gap-2 text-green-700">
              <CheckCircleFilledIcon /><span className="text-sm">未检测到异常行为</span>
            </div>
          ) : <DataTable columns={anomalyColumns} data={anomalies} emptyMessage="暂无异常行为" />
        )}
      </PageSection>

      <Dialog visible={traceDialogOpen} onClose={() => setTraceDialogOpen(false)} header={`全链路追踪 - ${selectedTraceId}`} destroyOnClose footer={<div className="flex justify-end"><Button onClick={() => setTraceDialogOpen(false)}>关闭</Button></div>}>
        <DataTable
          columns={[
            { id: 'timestamp', label: '时间', render: (row: AuditLog) => new Date(row.timestamp).toLocaleString() },
            { id: 'user_id', label: '用户' }, { id: 'action', label: '操作' },
            { id: 'resource_type', label: '资源' },
            { id: 'status', label: '状态', render: (row: AuditLog) => <Tag theme={row.status === 'success' ? 'success' : 'danger'} variant="light">{row.status}</Tag> },
            { id: 'ip_address', label: 'IP' },
          ]}
          data={traceLogs}
        />
      </Dialog>

      <Dialog visible={reportDialogOpen} onClose={() => setReportDialogOpen(false)} header="生成审计报告" destroyOnClose footer={<div className="flex justify-end gap-2"><Button onClick={() => setReportDialogOpen(false)}>取消</Button><Button theme="primary" onClick={handleGenerateReport}>生成</Button></div>}>
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">报告标题</label><input className="w-full rounded border border-gray-300 px-3 py-2 text-sm" value={reportForm.title} onChange={(e) => setReportForm({ ...reportForm, title: e.target.value })} placeholder="请输入报告标题" /></div>
          <div><label className="block text-sm text-gray-600 mb-1">开始时间</label><input className="w-full rounded border border-gray-300 px-3 py-2 text-sm" value={reportForm.startDate} onChange={(e) => setReportForm({ ...reportForm, startDate: e.target.value })} placeholder="YYYY-MM-DD HH:mm" /></div>
          <div><label className="block text-sm text-gray-600 mb-1">结束时间</label><input className="w-full rounded border border-gray-300 px-3 py-2 text-sm" value={reportForm.endDate} onChange={(e) => setReportForm({ ...reportForm, endDate: e.target.value })} placeholder="YYYY-MM-DD HH:mm" /></div>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default SecurityAuditPage;
