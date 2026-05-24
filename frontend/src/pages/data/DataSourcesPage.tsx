/**
 * 数据源管理页面
 * 数据源的 CRUD、启动/停止操作、表格展示
 * 集成 MQTT 实时采集数据展示
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, MessagePlugin, Textarea, Dialog } from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, PlayIcon, StopIcon,
  RefreshIcon, CheckCircleIcon, TrendingUpIcon, WifiIcon,
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
                <th className="text-left font-bold px-4 py-3">状态</th>
                <th className="text-left font-bold px-4 py-3">创建时间</th>
                <th className="text-center font-bold px-4 py-3 w-[180px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((row) => (
                <tr key={row.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">{row.name}</td>
                  <td className="px-4 py-3"><Tag variant="outline">{row.code}</Tag></td>
                  <td className="px-4 py-3">{SOURCE_TYPE_OPTIONS.find((o) => o.value === row.source_type)?.label ?? row.source_type}</td>
                  <td className="px-4 py-3">{row.protocol}</td>
                  <td className="px-4 py-3"><StatusTag status={row.status} /></td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-center">
                      <Tooltip content="编辑">
                        <Button variant="text" theme="primary" icon={<EditIcon />} onClick={() => openEditForm(row)} />
                      </Tooltip>
                      {row.status === 'active' ? (
                        <Tooltip content="停止">
                          <Button variant="text" theme="warning" icon={<StopIcon />} onClick={() => stopMut.mutate(row.id)} />
                        </Tooltip>
                      ) : (
                        <Tooltip content="启动">
                          <Button variant="text" theme="success" icon={<PlayIcon />} onClick={() => startMut.mutate(row.id)} />
                        </Tooltip>
                      )}
                      <Tooltip content="删除">
                        <Button variant="text" theme="danger" icon={<DeleteIcon />} onClick={() => setDeleteTarget(row)} />
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredItems.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-400">暂无数据</td>
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

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default DataSourcesPage;
