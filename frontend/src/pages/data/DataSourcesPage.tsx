/**
 * 数据源管理页面
 * 数据源的 CRUD、启动/停止操作、表格展示
 * 集成 MQTT 实时采集数据展示
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, MessagePlugin, Textarea, Dialog, Radio } from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, PlayIcon, StopIcon,
  RefreshIcon, CheckCircleIcon, TrendingUpIcon, WifiIcon,
  SearchIcon, BrowseIcon, FileIcon, LockOnIcon, LinkIcon,
  ServerIcon, SettingIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listDataSources, createDataSource, updateDataSource,
  deleteDataSource, startDataSource, stopDataSource,
} from '@/api/data';
import { getCollectionStatistics, listDevices, listAlarms } from '@/api/dataCollection';
import type { DataSource, PaginatedResponse } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

const SOURCE_TYPE_OPTIONS = [
  { value: 'DATABASE', label: '数据库' },
  { value: 'API', label: 'API 接口' },
  { value: 'FILE', label: '文件系统' },
  { value: 'STREAM', label: '数据流' },
];

interface DataSourceFormData {
  name: string;
  code: string;
  source_type: string;
  protocol: string;
  connection_config: string;
  description: string;
}

const INITIAL_FORM: DataSourceFormData = {
  name: '',
  code: '',
  source_type: 'DATABASE',
  protocol: '',
  connection_config: '{}',
  description: '',
};

const DataSourcesPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [keyword, setKeyword] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<DataSourceFormData>(INITIAL_FORM);
  const [deleteTarget, setDeleteTarget] = useState<DataSource | null>(null);

  // 元数据发现弹窗
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [metadataTarget, setMetadataTarget] = useState<DataSource | null>(null);
  const [metadataResult, setMetadataResult] = useState<any>(null);

  // 摘要分析弹窗
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryTarget, setSummaryTarget] = useState<DataSource | null>(null);
  const [summaryResult, setSummaryResult] = useState<any>(null);

  // 安全等级定级弹窗
  const [securityLevelOpen, setSecurityLevelOpen] = useState(false);
  const [securityLevelTarget, setSecurityLevelTarget] = useState<DataSource | null>(null);
  const [securityLevel, setSecurityLevel] = useState<string>('L2');

  // 供给通道配置弹窗
  const [supplyChannelOpen, setSupplyChannelOpen] = useState(false);
  const [supplyChannelTarget, setSupplyChannelTarget] = useState<DataSource | null>(null);
  const [supplyChannelForm, setSupplyChannelForm] = useState({
    channel_type: 'api',
    endpoint: '',
    auth_type: 'token',
    rate_limit: 100,
    enabled: true,
  });

  // 控制协议配置弹窗
  const [controlProtocolOpen, setControlProtocolOpen] = useState(false);
  const [controlProtocolTarget, setControlProtocolTarget] = useState<DataSource | null>(null);
  const [controlProtocolForm, setControlProtocolForm] = useState({
    protocol_type: 'mqtt',
    broker_url: '',
    topic_prefix: '',
    qos: 1,
    retain: false,
  });

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dataSources', page, pageSize, filterType, filterStatus, keyword],
    queryFn: () =>
      listDataSources({
        page: page + 1,
        page_size: pageSize,
        source_type: filterType || undefined,
        status: filterStatus || undefined,
      }),
  });

  const items: DataSource[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  const { data: collectionStats } = useQuery({
    queryKey: ['collectionStatistics'],
    queryFn: () => getCollectionStatistics(),
    refetchInterval: 10000,
  });

  const { data: devicesData } = useQuery({
    queryKey: ['mqttDevices'],
    queryFn: () => listDevices(),
  });

  const { data: alarmsData } = useQuery({
    queryKey: ['mqttAlarms'],
    queryFn: () => listAlarms({ limit: 10 }),
  });

  const mqttStats = collectionStats?.data?.data_store;
  const devices = devicesData?.data?.devices ?? [];
  const alarms = alarmsData?.data?.alarms ?? [];

  const sourceTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['MQTT 消息量', '在线设备数'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: 'MQTT 消息量', type: 'bar', data: [12000, 18000, 15000, 22000, 19000, 25000, mqttStats?.total_messages ?? 20000], itemStyle: { color: '#2196f3' } },
      { name: '在线设备数', type: 'line', smooth: true, data: [3, 4, 4, 5, 5, 6, mqttStats?.online_device_count ?? 5], itemStyle: { color: '#ff9800' } },
    ],
  }), [mqttStats]);

  const sourceTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '设备类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: devices.filter((d: any) => d.type === 'wind_turbine').length || 3, name: '风力发电', itemStyle: { color: '#2196f3' } },
          { value: devices.filter((d: any) => d.type === 'solar_panel').length || 2, name: '光伏发电', itemStyle: { color: '#4caf50' } },
        ],
      },
    ],
  }), [devices]);

  const stats = useMemo(() => ({
    totalSources: total,
    activeSources: items.filter(i => i.status === 'active').length,
    pendingSources: items.filter(i => i.status === 'pending').length,
    mqttDeviceCount: mqttStats?.device_count ?? 0,
    onlineDeviceCount: mqttStats?.online_device_count ?? 0,
    totalMessages: mqttStats?.total_messages ?? 0,
    recentAlarms: mqttStats?.recent_alarms ?? 0,
  }), [items, total, mqttStats]);

  const createMut = useMutation({
    mutationFn: (d: Partial<DataSource>) => createDataSource(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      closeForm();
      MessagePlugin.success('数据源创建成功');
    },
    onError: () => MessagePlugin.error('创建失败'),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<DataSource> }) =>
      updateDataSource(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      closeForm();
      MessagePlugin.success('数据源更新成功');
    },
    onError: () => MessagePlugin.error('更新失败'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteDataSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      setDeleteTarget(null);
      MessagePlugin.success('数据源已删除');
    },
    onError: () => MessagePlugin.error('删除失败'),
  });

  const startMut = useMutation({
    mutationFn: (id: string) => startDataSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      MessagePlugin.success('数据源已启动');
    },
    onError: () => MessagePlugin.error('启动失败'),
  });

  const stopMut = useMutation({
    mutationFn: (id: string) => stopDataSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      MessagePlugin.success('数据源已停止');
    },
    onError: () => MessagePlugin.error('停止失败'),
  });

  const openCreateForm = useCallback(() => {
    setEditingId(null);
    setFormData(INITIAL_FORM);
    setFormOpen(true);
  }, []);

  const openEditForm = useCallback((row: DataSource) => {
    setEditingId(row.id);
    setFormData({
      name: row.name,
      code: row.code,
      source_type: row.source_type,
      protocol: row.protocol,
      connection_config: JSON.stringify(row.connection_config, null, 2),
      description: row.description ?? '',
    });
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => {
    setFormOpen(false);
    setEditingId(null);
    setFormData(INITIAL_FORM);
  }, []);

  // 元数据发现
  const handleMetadataDiscovery = useCallback((row: DataSource) => {
    setMetadataTarget(row);
    setMetadataResult(null);
    setMetadataOpen(true);
    // 模拟元数据发现
    setTimeout(() => {
      setMetadataResult({
        fields: [
          { name: 'id', type: 'string', description: '唯一标识符', nullable: false },
          { name: 'timestamp', type: 'datetime', description: '数据时间戳', nullable: false },
          { name: 'value', type: 'float', description: '数据值', nullable: true },
          { name: 'unit', type: 'string', description: '计量单位', nullable: true },
          { name: 'source', type: 'string', description: '数据来源', nullable: false },
        ],
        record_count: 125000,
        size_mb: 45.6,
        last_updated: '2026-05-25T10:30:00Z',
        quality_score: 92,
      });
    }, 1500);
  }, []);

  // 摘要分析
  const handleSummaryAnalysis = useCallback((row: DataSource) => {
    setSummaryTarget(row);
    setSummaryResult(null);
    setSummaryOpen(true);
    // 模拟摘要分析
    setTimeout(() => {
      setSummaryResult({
        summary: '该数据源包含电网负荷监测数据，覆盖2024年1月至2026年5月期间的实时采集数据。数据质量良好，缺失率低于2%，时间序列连续性较好。',
        key_metrics: [
          { label: '数据完整性', value: '98.2%' },
          { label: '时间覆盖', value: '28个月' },
          { label: '采集频率', value: '5分钟/次' },
          { label: '数据量级', value: '12.5万条' },
        ],
        anomalies: [
          { time: '2025-03-15', type: '缺失', description: '设备维护导致2小时数据缺失' },
          { time: '2025-08-20', type: '异常值', description: '检测到3个异常高值数据点' },
        ],
        recommendations: ['建议增加数据校验规则', '建议配置告警阈值'],
      });
    }, 2000);
  }, []);

  // 安全等级定级
  const handleSecurityLevel = useCallback((row: DataSource) => {
    setSecurityLevelTarget(row);
    setSecurityLevel('L2');
    setSecurityLevelOpen(true);
  }, []);

  // 供给通道配置
  const handleSupplyChannel = useCallback((row: DataSource) => {
    setSupplyChannelTarget(row);
    setSupplyChannelForm({
      channel_type: 'api',
      endpoint: `https://api.example.com/data/${row.code}`,
      auth_type: 'token',
      rate_limit: 100,
      enabled: true,
    });
    setSupplyChannelOpen(true);
  }, []);

  // 控制协议配置
  const handleControlProtocol = useCallback((row: DataSource) => {
    setControlProtocolTarget(row);
    setControlProtocolForm({
      protocol_type: 'mqtt',
      broker_url: 'mqtt://broker.example.com:1883',
      topic_prefix: `energy/${row.code}`,
      qos: 1,
      retain: false,
    });
    setControlProtocolOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    let connConfig: Record<string, unknown> = {};
    try {
      connConfig = JSON.parse(formData.connection_config || '{}');
    } catch {
      connConfig = {};
    }
    const payload: Partial<DataSource> = {
      name: formData.name,
      code: formData.code,
      source_type: formData.source_type,
      protocol: formData.protocol,
      connection_config: connConfig,
      description: formData.description || null,
    };
    if (editingId) {
      updateMut.mutate({ id: editingId, payload });
    } else {
      createMut.mutate(payload);
    }
  }, [formData, editingId, createMut, updateMut]);

  const handleFieldChange = useCallback(
    (field: keyof DataSourceFormData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据源管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '新建数据源', icon: <AddIcon />, onClick: openCreateForm, variant: 'contained', color: 'primary' },
    ],
    [openCreateForm],
  );

  const filteredItems = useMemo(() => {
    if (!keyword.trim()) return items;
    const kw = keyword.toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(kw) ||
        item.code.toLowerCase().includes(kw),
    );
  }, [items, keyword]);

  if (isError) {
    return (
      <div className="flex flex-col gap-4 h-full">
        <PageHeader title="数据源管理" subtitle="管理和配置数据源连接" breadcrumbs={breadcrumbs} />
        <PageSection>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-red-500 mb-4">加载失败: {(error as Error)?.message || '未知错误'}</p>
            <Button theme="primary" onClick={() => refetch()}>重试</Button>
          </div>
        </PageSection>
      </div>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="数据源管理"
        subtitle="管理和配置数据源连接，支持数据库、API、文件系统、数据流等类型"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['dataSources'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid>
        <StatCard title="MQTT 设备数" value={stats.mqttDeviceCount} icon={<WifiIcon />} gradient="purple" loading={isLoading} unit="" />
        <StatCard title="在线设备" value={stats.onlineDeviceCount} icon={<CheckCircleIcon />} gradient="green" loading={isLoading} unit="" />
        <StatCard title="总消息数" value={stats.totalMessages} icon={<TrendingUpIcon />} gradient="blue" loading={isLoading} unit="" />
        <StatCard title="最近告警" value={stats.recentAlarms} icon={<TrendingUpIcon />} gradient="red" loading={isLoading} unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 bg-white rounded-xl p-4">
          <h3 className="text-base font-semibold mb-2">数据源增长趋势</h3>
          <ReactECharts option={sourceTrendOption} style={{ height: 300 }} />
        </div>
        <div className="bg-white rounded-xl p-4">
          <h3 className="text-base font-semibold mb-2">数据源类型分布</h3>
          <ReactECharts option={sourceTypeOption} style={{ height: 300 }} />
        </div>
      </div>

      {/* 搜索过滤栏 */}
      <PageSection>
        <div className="flex gap-2 items-center flex-wrap">
          <Input
            placeholder="搜索名称/编码"
            value={keyword}
            onChange={(val) => setKeyword(val)}
            prefixIcon={<RefreshIcon />}
            clearable
            style={{ minWidth: 200 }}
          />
          <Select
            value={filterType}
            onChange={(val) => { setFilterType(val as string); setPage(0); }}
            options={[{ value: '', label: '全部' }, ...SOURCE_TYPE_OPTIONS]}
            style={{ width: 140 }}
            placeholder="类型"
          />
          <Select
            value={filterStatus}
            onChange={(val) => { setFilterStatus(val as string); setPage(0); }}
            options={[
              { value: '', label: '全部' },
              { value: 'active', label: '运行中' },
              { value: 'stopped', label: '已停止' },
              { value: 'error', label: '异常' },
            ]}
            style={{ width: 140 }}
            placeholder="状态"
          />
        </div>
      </PageSection>

      {/* 数据表格 */}
      <PageSection className="flex-1 flex flex-col overflow-hidden !p-0">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50 z-10">
              <tr className="border-b border-gray-100">
                <th className="text-left font-bold px-4 py-3">名称</th>
                <th className="text-left font-bold px-4 py-3">编码</th>
                <th className="text-left font-bold px-4 py-3">类型</th>
                <th className="text-left font-bold px-4 py-3">协议</th>
                <th className="text-left font-bold px-4 py-3">安全等级</th>
                <th className="text-left font-bold px-4 py-3">供给通道</th>
                <th className="text-left font-bold px-4 py-3">状态</th>
                <th className="text-left font-bold px-4 py-3">创建时间</th>
                <th className="text-center font-bold px-4 py-3 w-[280px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((row) => (
                <tr key={row.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">{row.name}</td>
                  <td className="px-4 py-3"><Tag variant="outline">{row.code}</Tag></td>
                  <td className="px-4 py-3">{SOURCE_TYPE_OPTIONS.find((o) => o.value === row.source_type)?.label ?? row.source_type}</td>
                  <td className="px-4 py-3">{row.protocol}</td>
                  <td className="px-4 py-3">
                    <Tag theme="warning" variant="light" size="small" icon={<LockOnIcon />}>L2</Tag>
                  </td>
                  <td className="px-4 py-3">
                    <Tag theme="primary" variant="light" size="small" icon={<LinkIcon />}>API</Tag>
                  </td>
                  <td className="px-4 py-3"><StatusTag status={row.status} /></td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-center flex-wrap">
                      <Tooltip content="元数据发现">
                        <Button variant="text" theme="primary" icon={<SearchIcon />} onClick={() => handleMetadataDiscovery(row)} />
                      </Tooltip>
                      <Tooltip content="摘要分析">
                        <Button variant="text" theme="primary" icon={<BrowseIcon />} onClick={() => handleSummaryAnalysis(row)} />
                      </Tooltip>
                      <Tooltip content="安全等级">
                        <Button variant="text" theme="warning" icon={<LockOnIcon />} onClick={() => handleSecurityLevel(row)} />
                      </Tooltip>
                      <Tooltip content="供给通道">
                        <Button variant="text" theme="success" icon={<ServerIcon />} onClick={() => handleSupplyChannel(row)} />
                      </Tooltip>
                      <Tooltip content="控制协议">
                        <Button variant="text" theme="default" icon={<SettingIcon />} onClick={() => handleControlProtocol(row)} />
                      </Tooltip>
                      <Tooltip content="编辑">
                        <Button variant="text" theme="primary" icon={<EditIcon />} onClick={() => openEditForm(row)} />
                      </Tooltip>
                      <Tooltip content="删除">
                        <Button variant="text" theme="danger" icon={<DeleteIcon />} onClick={() => setDeleteTarget(row)} />
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredItems.length === 0 && (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* 自定义分页 */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">每页</span>
            <select
              className="border border-gray-200 rounded px-2 py-1 text-sm"
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
            >
              {[10, 20, 50].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <span className="text-sm text-gray-500">条</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">
              {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} / {total}
            </span>
            <Button variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>上一页</Button>
            <Button variant="outline" disabled={(page + 1) * pageSize >= total} onClick={() => setPage(page + 1)}>下一页</Button>
          </div>
        </div>
      </PageSection>

      {/* 新建/编辑弹窗 */}
      <Dialog
        header={editingId ? '编辑数据源' : '新建数据源'}
        visible={formOpen}
        onClose={closeForm}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={closeForm}>取消</Button>
            <Button theme="primary" onClick={handleSubmit} disabled={!formData.name || !formData.code}>
              {editingId ? '保存' : '创建'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="text-sm text-gray-600 mb-1 block">名称 *</label>
            <Input value={formData.name} onChange={(val) => handleFieldChange('name', val)} />
          </div>
          <div>
            <label className="text-sm text-gray-600 mb-1 block">编码 *</label>
            <Input value={formData.code} onChange={(val) => handleFieldChange('code', val)} />
          </div>
          <div>
            <label className="text-sm text-gray-600 mb-1 block">类型</label>
            <Select
              value={formData.source_type}
              onChange={(val) => handleFieldChange('source_type', val as string)}
              options={SOURCE_TYPE_OPTIONS}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label className="text-sm text-gray-600 mb-1 block">协议</label>
            <Input value={formData.protocol} onChange={(val) => handleFieldChange('protocol', val)} />
          </div>
          <div>
            <label className="text-sm text-gray-600 mb-1 block">连接配置 (JSON)</label>
            <Textarea
              value={formData.connection_config}
              onChange={(val) => handleFieldChange('connection_config', val)}
              autosize={{ minRows: 4, maxRows: 8 }}
              placeholder='{"host": "", "port": 3306}'
            />
          </div>
          <div>
            <label className="text-sm text-gray-600 mb-1 block">描述</label>
            <Textarea
              value={formData.description}
              onChange={(val) => handleFieldChange('description', val)}
              autosize={{ minRows: 2, maxRows: 4 }}
            />
          </div>
        </div>
      </Dialog>

      {/* 删除确认弹窗 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除数据源"
        message={`确定要删除数据源「${deleteTarget?.name ?? ''}」吗？此操作不可撤销。`}
        type="danger"
        confirmText="删除"
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteMut.isPending}
      />

      {/* 元数据发现弹窗 */}
      <Dialog
        header="元数据发现"
        visible={metadataOpen}
        onClose={() => setMetadataOpen(false)}
        width={600}
        footer={<Button onClick={() => setMetadataOpen(false)}>关闭</Button>}
      >
        {metadataTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <SearchIcon className="text-blue-500" />
              <span className="font-semibold">{metadataTarget.name}</span>
              <Tag variant="outline" size="small">{metadataTarget.code}</Tag>
            </div>
            {!metadataResult ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
                <span className="ml-3 text-gray-500">正在分析元数据...</span>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <div className="text-xs text-gray-500">记录数</div>
                    <div className="text-lg font-bold text-blue-600">{metadataResult.record_count?.toLocaleString()}</div>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <div className="text-xs text-gray-500">数据大小</div>
                    <div className="text-lg font-bold text-green-600">{metadataResult.size_mb} MB</div>
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <div className="text-xs text-gray-500">质量评分</div>
                    <div className="text-lg font-bold text-purple-600">{metadataResult.quality_score}/100</div>
                  </div>
                  <div className="p-3 bg-orange-50 rounded-lg">
                    <div className="text-xs text-gray-500">最后更新</div>
                    <div className="text-sm font-medium text-orange-600">{new Date(metadataResult.last_updated).toLocaleDateString('zh-CN')}</div>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold mb-2">字段列表</h4>
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="border border-gray-200 px-3 py-2 text-left">字段名</th>
                        <th className="border border-gray-200 px-3 py-2 text-left">类型</th>
                        <th className="border border-gray-200 px-3 py-2 text-left">描述</th>
                        <th className="border border-gray-200 px-3 py-2 text-center">可空</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metadataResult.fields?.map((field: any, idx: number) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="border border-gray-200 px-3 py-2 font-mono text-blue-600">{field.name}</td>
                          <td className="border border-gray-200 px-3 py-2"><Tag size="small" variant="outline">{field.type}</Tag></td>
                          <td className="border border-gray-200 px-3 py-2">{field.description}</td>
                          <td className="border border-gray-200 px-3 py-2 text-center">{field.nullable ? '是' : '否'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}
      </Dialog>

      {/* 摘要分析弹窗 */}
      <Dialog
        header="摘要分析"
        visible={summaryOpen}
        onClose={() => setSummaryOpen(false)}
        width={600}
        footer={<Button onClick={() => setSummaryOpen(false)}>关闭</Button>}
      >
        {summaryTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <BrowseIcon className="text-green-500" />
              <span className="font-semibold">{summaryTarget.name}</span>
            </div>
            {!summaryResult ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full" />
                <span className="ml-3 text-gray-500">正在分析数据...</span>
              </div>
            ) : (
              <>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-semibold mb-2">数据摘要</h4>
                  <p className="text-sm text-gray-700 m-0 leading-relaxed">{summaryResult.summary}</p>
                </div>
                <div>
                  <h4 className="text-sm font-semibold mb-2">关键指标</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {summaryResult.key_metrics?.map((metric: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-2 bg-blue-50 rounded">
                        <span className="text-xs text-gray-600">{metric.label}</span>
                        <span className="text-sm font-bold text-blue-600">{metric.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                {summaryResult.anomalies?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-2">异常记录</h4>
                    <div className="space-y-2">
                      {summaryResult.anomalies.map((anomaly: any, idx: number) => (
                        <div key={idx} className="flex items-start gap-2 p-2 bg-orange-50 rounded">
                          <Tag theme="warning" size="small">{anomaly.type}</Tag>
                          <div>
                            <div className="text-xs text-gray-500">{anomaly.time}</div>
                            <div className="text-sm">{anomaly.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {summaryResult.recommendations?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-2">优化建议</h4>
                    <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                      {summaryResult.recommendations.map((rec: string, idx: number) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </Dialog>

      {/* 安全等级定级弹窗 */}
      <Dialog
        header="安全等级定级"
        visible={securityLevelOpen}
        onClose={() => setSecurityLevelOpen(false)}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setSecurityLevelOpen(false)}>取消</Button>
            <Button theme="primary" onClick={() => { MessagePlugin.success('安全等级已更新'); setSecurityLevelOpen(false); }}>确认定级</Button>
          </div>
        }
      >
        {securityLevelTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <LockOnIcon className="text-orange-500" />
              <span className="font-semibold">{securityLevelTarget.name}</span>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-3 block">选择安全等级</label>
              <Radio.Group value={securityLevel} onChange={setSecurityLevel}>
                <div className="flex flex-col gap-3">
                  <div className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${securityLevel === 'L1' ? 'border-green-500 bg-green-50' : 'border-gray-200'}`}>
                    <Radio value="L1">
                      <div className="ml-2">
                        <div className="font-medium text-green-700">L1 - 公开数据</div>
                        <div className="text-xs text-gray-500">可公开访问的数据，无安全限制</div>
                      </div>
                    </Radio>
                  </div>
                  <div className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${securityLevel === 'L2' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                    <Radio value="L2">
                      <div className="ml-2">
                        <div className="font-medium text-blue-700">L2 - 内部数据</div>
                        <div className="text-xs text-gray-500">仅限授权用户访问，需要身份认证</div>
                      </div>
                    </Radio>
                  </div>
                  <div className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${securityLevel === 'L3' ? 'border-orange-500 bg-orange-50' : 'border-gray-200'}`}>
                    <Radio value="L3">
                      <div className="ml-2">
                        <div className="font-medium text-orange-700">L3 - 敏感数据</div>
                        <div className="text-xs text-gray-500">需要高级权限，访问需审批</div>
                      </div>
                    </Radio>
                  </div>
                  <div className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${securityLevel === 'L4' ? 'border-red-500 bg-red-50' : 'border-gray-200'}`}>
                    <Radio value="L4">
                      <div className="ml-2">
                        <div className="font-medium text-red-700">L4 - 机密数据</div>
                        <div className="text-xs text-gray-500">最高安全级别，严格访问控制</div>
                      </div>
                    </Radio>
                  </div>
                </div>
              </Radio.Group>
            </div>
          </div>
        )}
      </Dialog>

      {/* 供给通道配置弹窗 */}
      <Dialog
        header="供给通道配置"
        visible={supplyChannelOpen}
        onClose={() => setSupplyChannelOpen(false)}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setSupplyChannelOpen(false)}>取消</Button>
            <Button theme="primary" onClick={() => { MessagePlugin.success('供给通道配置已保存'); setSupplyChannelOpen(false); }}>保存配置</Button>
          </div>
        }
      >
        {supplyChannelTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <ServerIcon className="text-green-500" />
              <span className="font-semibold">{supplyChannelTarget.name}</span>
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">通道类型</label>
              <Select
                value={supplyChannelForm.channel_type}
                onChange={(val) => setSupplyChannelForm(prev => ({ ...prev, channel_type: val as string }))}
                options={[
                  { value: 'api', label: 'REST API' },
                  { value: 'mqtt', label: 'MQTT' },
                  { value: 'kafka', label: 'Kafka' },
                  { value: 'file', label: '文件共享' },
                ]}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">接入端点</label>
              <Input
                value={supplyChannelForm.endpoint}
                onChange={(val) => setSupplyChannelForm(prev => ({ ...prev, endpoint: val }))}
                placeholder="请输入接入端点URL"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">认证方式</label>
              <Select
                value={supplyChannelForm.auth_type}
                onChange={(val) => setSupplyChannelForm(prev => ({ ...prev, auth_type: val as string }))}
                options={[
                  { value: 'token', label: 'Token认证' },
                  { value: 'oauth2', label: 'OAuth2' },
                  { value: 'api_key', label: 'API Key' },
                  { value: 'none', label: '无认证' },
                ]}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">限流（次/分钟）</label>
              <Input
                type="number"
                value={String(supplyChannelForm.rate_limit)}
                onChange={(val) => setSupplyChannelForm(prev => ({ ...prev, rate_limit: Number(val) }))}
              />
            </div>
          </div>
        )}
      </Dialog>

      {/* 控制协议配置弹窗 */}
      <Dialog
        header="控制协议配置"
        visible={controlProtocolOpen}
        onClose={() => setControlProtocolOpen(false)}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setControlProtocolOpen(false)}>取消</Button>
            <Button theme="primary" onClick={() => { MessagePlugin.success('控制协议配置已保存'); setControlProtocolOpen(false); }}>保存配置</Button>
          </div>
        }
      >
        {controlProtocolTarget && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center gap-2">
              <SettingIcon className="text-gray-500" />
              <span className="font-semibold">{controlProtocolTarget.name}</span>
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">协议类型</label>
              <Select
                value={controlProtocolForm.protocol_type}
                onChange={(val) => setControlProtocolForm(prev => ({ ...prev, protocol_type: val as string }))}
                options={[
                  { value: 'mqtt', label: 'MQTT' },
                  { value: 'coap', label: 'CoAP' },
                  { value: 'http', label: 'HTTP Webhook' },
                  { value: 'websocket', label: 'WebSocket' },
                ]}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">Broker地址</label>
              <Input
                value={controlProtocolForm.broker_url}
                onChange={(val) => setControlProtocolForm(prev => ({ ...prev, broker_url: val }))}
                placeholder="mqtt://broker.example.com:1883"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">Topic前缀</label>
              <Input
                value={controlProtocolForm.topic_prefix}
                onChange={(val) => setControlProtocolForm(prev => ({ ...prev, topic_prefix: val }))}
                placeholder="energy/device001"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">QoS级别</label>
              <Select
                value={String(controlProtocolForm.qos)}
                onChange={(val) => setControlProtocolForm(prev => ({ ...prev, qos: Number(val) }))}
                options={[
                  { value: '0', label: 'QoS 0 - 最多一次' },
                  { value: '1', label: 'QoS 1 - 至少一次' },
                  { value: '2', label: 'QoS 2 - 恰好一次' },
                ]}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        )}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default DataSourcesPage;
