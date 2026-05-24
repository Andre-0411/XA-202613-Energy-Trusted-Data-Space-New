/**
 * 威胁检测页面
 * 威胁列表 + 主动检测 + 详情 + 处置 + 统计卡片 + ECharts图表
 */
import React, { useState, useMemo } from 'react';
import { Button, Input, Select, Dialog, Tag, Tooltip, Textarea } from 'tdesign-react';
import {
  RefreshIcon, AddIcon, SearchIcon,
  ErrorCircleFilledIcon, ShieldErrorFilledIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listThreats, detectThreats, resolveThreat } from '@/api/security';
import type { ThreatEvent } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';
import ResponsiveFilterBar from '@/components/responsive/ResponsiveFilterBar';

const severityLabel = (s: string): string => {
  const m: Record<string, string> = { CRITICAL: '严重', HIGH: '高', MEDIUM: '中', LOW: '低' };
  return m[s] ?? s;
};

const severityColor = (s: string): 'error' | 'warning' | 'info' | 'success' => {
  const m: Record<string, 'error' | 'warning' | 'info' | 'success'> = { CRITICAL: 'error', HIGH: 'warning', MEDIUM: 'info', LOW: 'success' };
  return m[s] ?? 'info';
};

const threatStatusLabel = (s: string): string => {
  const m: Record<string, string> = { OPEN: '待处理', INVESTIGATING: '调查中', RESOLVED: '已解决', FALSE_POSITIVE: '误报' };
  return m[s] ?? s;
};

const threatStatusColor = (s: string): 'error' | 'warning' | 'success' | 'info' => {
  const m: Record<string, 'error' | 'warning' | 'success' | 'info'> = { OPEN: 'error', INVESTIGATING: 'warning', RESOLVED: 'success', FALSE_POSITIVE: 'info' };
  return m[s] ?? 'info';
};

const SecurityThreatsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 & 分页 =====
  const [filterType, setFilterType] = useState<string>('');
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 处置弹窗 =====
  const [resolveOpen, setResolveOpen] = useState<boolean>(false);
  const [resolveId, setResolveId] = useState<string>('');
  const [resolveResolution, setResolveResolution] = useState<string>('');
  const [resolveDesc, setResolveDesc] = useState<string>('');

  // ===== 检测结果 =====
  const [detectResult, setDetectResult] = useState<number | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['threats', page, pageSize, filterType, filterSeverity, filterStatus],
    queryFn: () => listThreats({
      page: page + 1, page_size: pageSize,
      threat_type: filterType || undefined, severity: filterSeverity || undefined, status: filterStatus || undefined,
    }),
  });

  const items: ThreatEvent[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== Mutations =====
  const detectMut = useMutation({
    mutationFn: () => detectThreats(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['threats'] });
      setDetectResult(res.data?.threats_detected ?? 0);
    },
  });

  const resolveMut = useMutation({
    mutationFn: ({ id, data: d }: { id: string; data: { resolution: string; description?: string } }) => resolveThreat(id, d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threats'] });
      setResolveOpen(false);
      setResolveId(''); setResolveResolution(''); setResolveDesc('');
    },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '威胁检测' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '主动检测', icon: <AddIcon />, onClick: () => { setDetectResult(null); detectMut.mutate(); }, variant: 'contained' },
    ],
    [],
  );

  // ===== 统计数据计算 =====
  const stats = useMemo(() => {
    if (!items.length) return { total: 0, critical: 0, high: 0, resolved: 0, open: 0, investigating: 0 };
    return {
      total: items.length,
      critical: items.filter(i => i.severity === 'CRITICAL').length,
      high: items.filter(i => i.severity === 'HIGH').length,
      resolved: items.filter(i => i.status === 'RESOLVED').length,
      open: items.filter(i => i.status === 'OPEN').length,
      investigating: items.filter(i => i.status === 'INVESTIGATING').length,
    };
  }, [items]);

  // ===== ECharts 配置 =====
  const trendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['严重', '高', '中', '低'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '威胁数量' },
    series: [
      { name: '严重', type: 'line', smooth: true, data: [5, 8, 3, 6, 4, 7, 2], itemStyle: { color: '#f44336' } },
      { name: '高', type: 'line', smooth: true, data: [12, 15, 10, 18, 14, 11, 9], itemStyle: { color: '#ff9800' } },
      { name: '中', type: 'line', smooth: true, data: [25, 30, 22, 35, 28, 32, 20], itemStyle: { color: '#2196f3' } },
      { name: '低', type: 'line', smooth: true, data: [40, 45, 38, 50, 42, 48, 35], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const typeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '威胁类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: items.filter(i => i.threat_type === 'INTRUSION').length || 35, name: '入侵', itemStyle: { color: '#f44336' } },
          { value: items.filter(i => i.threat_type === 'MALWARE').length || 28, name: '恶意软件', itemStyle: { color: '#ff9800' } },
          { value: items.filter(i => i.threat_type === 'DATA_LEAK').length || 22, name: '数据泄露', itemStyle: { color: '#2196f3' } },
          { value: items.filter(i => i.threat_type === 'DDOS').length || 15, name: 'DDoS', itemStyle: { color: '#9c27b0' } },
        ],
      },
    ],
  }), [items]);

  return (
    <PageContainer>
      <PageHeader
        title="威胁检测"
        subtitle="安全威胁监控与处置"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['threats'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总威胁数" value={stats.total} icon={<ShieldErrorFilledIcon />} gradient="purple" unit="" />
        <MetricsCard title="严重威胁" value={stats.critical} icon={<ErrorCircleFilledIcon />} gradient="red" unit="" />
        <MetricsCard title="待处理" value={stats.open} icon={<ShieldErrorFilledIcon />} gradient="cyan" unit="" />
        <MetricsCard title="已解决" value={stats.resolved} icon={<ShieldErrorFilledIcon />} gradient="green" unit="" />
      </StatGrid>

      {/* 检测结果提示 */}
      {detectResult !== null && (
        <div className={`rounded-lg p-3 flex items-center justify-between ${detectResult > 0 ? 'bg-yellow-50 border border-yellow-200 text-yellow-800' : 'bg-green-50 border border-green-200 text-green-800'}`}>
          <span className="text-sm">{detectResult > 0 ? `检测到 ${detectResult} 个新威胁` : '未检测到新威胁'}</span>
          <span className="cursor-pointer text-gray-500 hover:text-gray-700" onClick={() => setDetectResult(null)}>✕</span>
        </div>
      )}

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 sm:gap-4">
        <div className="md:col-span-8"><ChartCard title="威胁趋势分析" option={trendOption} height={300} /></div>
        <div className="md:col-span-4"><ChartCard title="威胁类型分布" option={typeOption} height={300} /></div>
      </div>

      {/* 筛选栏 */}
      <ResponsiveFilterBar
        showClear={!!(filterType || filterSeverity || filterStatus)}
        onClear={() => { setFilterType(''); setFilterSeverity(''); setFilterStatus(''); setPage(0); }}
      >
        <Select
          value={filterType}
          onChange={(val) => { setFilterType(String(val)); setPage(0); }}
          options={[
            { value: '', label: '全部' },
            { value: 'INTRUSION', label: '入侵' },
            { value: 'MALWARE', label: '恶意软件' },
            { value: 'DATA_LEAK', label: '数据泄露' },
            { value: 'DDOS', label: 'DDoS' },
          ]}
          placeholder="威胁类型"
          style={{ minWidth: 120 }}
        />
        <Select
          value={filterSeverity}
          onChange={(val) => { setFilterSeverity(String(val)); setPage(0); }}
          options={[
            { value: '', label: '全部' },
            { value: 'CRITICAL', label: '严重' },
            { value: 'HIGH', label: '高' },
            { value: 'MEDIUM', label: '中' },
            { value: 'LOW', label: '低' },
          ]}
          placeholder="严重级别"
          style={{ minWidth: 120 }}
        />
        <Select
          value={filterStatus}
          onChange={(val) => { setFilterStatus(String(val)); setPage(0); }}
          options={[
            { value: '', label: '全部' },
            { value: 'OPEN', label: '待处理' },
            { value: 'INVESTIGATING', label: '调查中' },
            { value: 'RESOLVED', label: '已解决' },
            { value: 'FALSE_POSITIVE', label: '误报' },
          ]}
          placeholder="状态"
          style={{ minWidth: 120 }}
        />
      </ResponsiveFilterBar>

      {/* 数据表格 - 移动端卡片视图 / 桌面端表格视图 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm flex-1 flex flex-col overflow-hidden">
        {/* 移动端卡片视图 */}
        <div className="md:hidden flex-1 overflow-auto p-3">
          {items.length === 0 ? (
            <div className="py-12 text-center text-gray-500">暂无威胁记录</div>
          ) : (
            <div className="flex flex-col gap-3">
              {items.map((row) => (
                <div key={row.id} className="rounded-lg border border-gray-200 p-3 active:bg-gray-50">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold">{row.threat_type}</span>
                      <StatusTag status={severityLabel(row.severity)} color={severityColor(row.severity)} />
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusTag status={threatStatusLabel(row.status)} color={threatStatusColor(row.status)} />
                      {row.source && (
                        <span className="text-xs text-gray-500">来源: {row.source}</span>
                      )}
                    </div>
                    <span className="text-sm text-gray-600">{row.description}</span>
                    <span className="text-xs text-gray-500">
                      {new Date(row.detected_at).toLocaleString('zh-CN')}
                    </span>
                    {(row.status === 'OPEN' || row.status === 'INVESTIGATING') && (
                      <div className="flex justify-end">
                        <Button
                          icon={<SearchIcon />}
                          onClick={() => { setResolveId(row.id); setResolveOpen(true); }}
                          style={{ minHeight: 36 }}
                        >
                          处置
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
        <div className="hidden md:block flex-1 overflow-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">威胁类型</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">严重级别</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">来源</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">描述</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">状态</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">负责人</th>
                <th className="px-4 py-3 text-left font-bold text-sm text-gray-700">检测时间</th>
                <th className="px-4 py-3 text-center font-bold text-sm text-gray-700 w-20">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 border-t border-gray-100">
                  <td className="px-4 py-3 text-sm">{row.threat_type}</td>
                  <td className="px-4 py-3"><StatusTag status={severityLabel(row.severity)} color={severityColor(row.severity)} /></td>
                  <td className="px-4 py-3 text-sm">{row.source ?? '—'}</td>
                  <td className="px-4 py-3 text-sm max-w-[180px] truncate">{row.description}</td>
                  <td className="px-4 py-3"><StatusTag status={threatStatusLabel(row.status)} color={threatStatusColor(row.status)} /></td>
                  <td className="px-4 py-3 text-sm">{row.assigned_to ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">{new Date(row.detected_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-center">
                    {(row.status === 'OPEN' || row.status === 'INVESTIGATING') && (
                      <Tooltip content="处置">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => { setResolveId(row.id); setResolveOpen(true); }}>
                          <SearchIcon style={{ fontSize: 16 }} />
                        </span>
                      </Tooltip>
                    )}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">暂无威胁记录</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        <div className="flex flex-wrap items-center justify-center sm:justify-end gap-2 px-4 py-3 border-t border-gray-100">
          <span className="text-sm text-gray-600">每页行数:</span>
          <Select
            value={String(pageSize)}
            onChange={(val) => { setPageSize(Number(val)); setPage(0); }}
            options={[
              { value: '10', label: '10' },
              { value: '20', label: '20' },
              { value: '50', label: '50' },
            ]}
            style={{ width: 80 }}
          />
          <span className="text-sm text-gray-600">{`${page * pageSize + 1}-${Math.min((page + 1) * pageSize, total)} / ${total}`}</span>
          <div className="flex gap-1">
            <Button variant="outline" size="small" disabled={page === 0} onClick={() => setPage(page - 1)}>上一页</Button>
            <Button variant="outline" size="small" disabled={(page + 1) * pageSize >= total} onClick={() => setPage(page + 1)}>下一页</Button>
          </div>
        </div>
      </div>

      {/* 处置弹窗 */}
      <Dialog
        visible={resolveOpen}
        onClose={() => { setResolveOpen(false); setResolveResolution(''); setResolveDesc(''); }}
        header="威胁处置"
        destroyOnClose
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => { setResolveOpen(false); setResolveResolution(''); setResolveDesc(''); }}>取消</Button>
            <Button theme="primary" disabled={!resolveResolution.trim()} onClick={() => resolveMut.mutate({ id: resolveId, data: { resolution: resolveResolution, description: resolveDesc || undefined } })}>确认处置</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">处置方式</label>
            <Input value={resolveResolution} onChange={(val) => setResolveResolution(String(val))} placeholder="已修复 / 误报标记 / 加固措施" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">详细描述（可选）</label>
            <Textarea value={resolveDesc} onChange={(val) => setResolveDesc(String(val))} rows={3} />
          </div>
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default SecurityThreatsPage;
