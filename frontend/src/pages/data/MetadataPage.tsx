/**
 * 元数据管理页面
 * 元数据的 CRUD、版本历史查看、血缘关系查看
 * 增强：分类规则查看、数据质量评估集成
 * 拆分为 MetadataEditor + MetadataDetails 子组件
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tag, Tooltip } from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, RefreshIcon, FileIcon,
  CheckCircleFilledIcon, TimeFilledIcon, TrendingUpIcon,
  HistoryIcon, LinkIcon, FilterIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import {
  listMetadata, createMetadata, updateMetadata, getVersions, getLineage,
} from '@/api/data';
import { getMetadataVersions, getClassificationRules } from '@/api/dataCatalog';
import type { MetadataRecord } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import MetadataEditor, { INITIAL_FORM, type MetadataFormData, STANDARD_OPTIONS } from './components/MetadataEditor';
import MetadataDetails from './components/MetadataDetails';

const MetadataPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态 =====
  const [keyword, setKeyword] = useState<string>('');
  const [filterAssetId, setFilterAssetId] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 弹窗 =====
  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<MetadataFormData>(INITIAL_FORM);
  const [deleteTarget, setDeleteTarget] = useState<MetadataRecord | null>(null);

  // 版本历史弹窗
  const [versionsOpen, setVersionsOpen] = useState<boolean>(false);
  const [versionsData, setVersionsData] = useState<MetadataRecord[]>([]);
  const [versionsLoading, setVersionsLoading] = useState<boolean>(false);

  // 血缘关系弹窗
  const [lineageOpen, setLineageOpen] = useState<boolean>(false);
  const [lineageData, setLineageData] = useState<Record<string, unknown> | null>(null);
  const [lineageLoading, setLineageLoading] = useState<boolean>(false);

  // 分类规则弹窗
  const [rulesOpen, setRulesOpen] = useState<boolean>(false);

  // ===== ECharts 配置 =====
  const trendChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['元数据数量', '更新次数'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'],
    },
    yAxis: { type: 'value' as const, name: '数量' },
    series: [
      {
        name: '元数据数量',
        type: 'line',
        smooth: true,
        data: [120, 132, 101, 134, 90, 230, 210],
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.05)' },
            ],
          },
        },
        itemStyle: { color: '#667eea' },
      },
      {
        name: '更新次数',
        type: 'line',
        smooth: true,
        data: [90, 102, 81, 114, 70, 200, 190],
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(118, 75, 162, 0.5)' },
              { offset: 1, color: 'rgba(118, 75, 162, 0.05)' },
            ],
          },
        },
        itemStyle: { color: '#764ba2' },
      },
    ],
  }), []);

  const standardChartOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, left: 'left', top: 20 },
    series: [
      {
        name: '标准类型',
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
          { value: 45, name: '能源国标', itemStyle: { color: '#667eea' } },
          { value: 30, name: 'Dublin Core', itemStyle: { color: '#764ba2' } },
          { value: 25, name: '自定义', itemStyle: { color: '#f093fb' } },
        ],
      },
    ],
  }), []);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['metadata', page, pageSize, filterAssetId],
    queryFn: () =>
      listMetadata({
        page: page + 1,
        page_size: pageSize,
        asset_id: filterAssetId || undefined,
      }),
  });

  const items: MetadataRecord[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalMetadata: total,
    activeMetadata: items.filter(item => item.status === 'active').length,
    pendingMetadata: items.filter(item => item.status === 'pending').length,
    todayUpdates: items.filter(item => {
      const today = new Date().toDateString();
      return new Date(item.updated_at).toDateString() === today;
    }).length,
  }), [items, total]);

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<MetadataRecord>) => createMetadata(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metadata'] });
      closeForm();
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<MetadataRecord> }) =>
      updateMetadata(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metadata'] });
      closeForm();
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => createMetadata({ asset_id: id } as Partial<MetadataRecord>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metadata'] });
      setDeleteTarget(null);
    },
  });

  // ===== 版本历史 =====
  const handleViewVersions = useCallback(async (id: string) => {
    setVersionsOpen(true);
    setVersionsLoading(true);
    try {
      const res = await getVersions(id);
      setVersionsData(res.data ?? []);
    } catch {
      setVersionsData([]);
    } finally {
      setVersionsLoading(false);
    }
  }, []);

  // ===== 血缘关系 =====
  const handleViewLineage = useCallback(async (id: string) => {
    setLineageOpen(true);
    setLineageLoading(true);
    try {
      const res = await getLineage(id);
      setLineageData(res.data ?? null);
    } catch {
      setLineageData(null);
    } finally {
      setLineageLoading(false);
    }
  }, []);

  // ===== 分类规则 =====
  const { data: classificationRules } = useQuery({
    queryKey: ['classificationRules'],
    queryFn: async () => {
      try {
        const res = await getClassificationRules();
        return res?.data ?? [];
      } catch {
        return [];
      }
    },
    enabled: rulesOpen,
  });

  // ===== 表单操作 =====
  const openCreateForm = useCallback(() => {
    setEditingId(null);
    setFormData(INITIAL_FORM);
    setFormOpen(true);
  }, []);

  const openEditForm = useCallback((row: MetadataRecord) => {
    setEditingId(row.id);
    setFormData({
      asset_id: row.asset_id,
      standard: row.standard,
      schema_version: row.schema_version,
      fields_json: JSON.stringify(row.fields, null, 2),
    });
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => {
    setFormOpen(false);
    setEditingId(null);
    setFormData(INITIAL_FORM);
  }, []);

  const handleSubmit = useCallback(() => {
    let fields: Record<string, unknown>[] = [];
    try {
      fields = JSON.parse(formData.fields_json || '[]');
    } catch {
      fields = [];
    }
    const payload: Partial<MetadataRecord> = {
      asset_id: formData.asset_id,
      standard: formData.standard,
      schema_version: formData.schema_version,
      fields,
    };
    if (editingId) {
      updateMut.mutate({ id: editingId, payload });
    } else {
      createMut.mutate(payload);
    }
  }, [formData, editingId, createMut, updateMut]);

  const handleFieldChange = useCallback(
    (field: keyof MetadataFormData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '元数据管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '新建元数据', icon: <AddIcon />, onClick: openCreateForm, variant: 'contained' },
      { label: '分类规则', icon: <FilterIcon />, onClick: () => setRulesOpen(true), variant: 'outlined' },
    ],
    [openCreateForm],
  );

  // ===== 过滤 =====
  const filteredItems = useMemo(() => {
    if (!keyword.trim()) return items;
    const kw = keyword.toLowerCase();
    return items.filter(
      (item) =>
        item.asset_id.toLowerCase().includes(kw) ||
        item.standard.toLowerCase().includes(kw) ||
        item.schema_version.toLowerCase().includes(kw),
    );
  }, [items, keyword]);

  const isMutPending = createMut.isPending || updateMut.isPending;

  return (
    <PageContainer>
      <PageHeader
        title="元数据管理"
        subtitle="管理数据资产的元数据定义、版本历史与血缘关系"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['metadata'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总元数据" value={stats.totalMetadata} icon={<FileIcon />} gradient="blue" unit="" />
        <StatCard title="活跃元数据" value={stats.activeMetadata} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <StatCard title="待审核" value={stats.pendingMetadata} icon={<TimeFilledIcon />} gradient="orange" unit="" />
        <StatCard title="今日更新" value={stats.todayUpdates} icon={<TrendingUpIcon />} gradient="purple" unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
        <PageSection title="元数据增长趋势" titleIcon={<TrendingUpIcon />}>
          <ReactECharts option={trendChartOption} style={{ height: 250 }} />
        </PageSection>
        <PageSection title="标准类型分布" titleIcon={<FilterIcon />}>
          <ReactECharts option={standardChartOption} style={{ height: 250 }} />
        </PageSection>
      </div>

      {/* 搜索过滤栏 */}
      <PageSection padding="sm">
        <div className="flex flex-wrap gap-3 items-center">
          <Input
            placeholder="搜索标准/版本/资产ID"
            value={keyword}
            onChange={(val) => setKeyword(String(val))}
            className="!w-full sm:!w-52"
          />
          <Input
            placeholder="资产 ID"
            value={filterAssetId}
            onChange={(val) => { setFilterAssetId(String(val)); setPage(0); }}
            className="!w-full sm:!w-40"
          />
          {(keyword || filterAssetId) && (
            <Button
              variant="outline"
              onClick={() => { setKeyword(''); setFilterAssetId(''); setPage(0); }}
            >
              重置
            </Button>
          )}
        </div>
      </PageSection>

      {/* 数据表格 */}
      <PageSection padding="none" className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left font-bold">资产 ID</th>
                <th className="px-4 py-3 text-left font-bold">标准</th>
                <th className="px-4 py-3 text-left font-bold">Schema 版本</th>
                <th className="px-4 py-3 text-left font-bold">字段数</th>
                <th className="px-4 py-3 text-left font-bold">前一版本</th>
                <th className="px-4 py-3 text-left font-bold">更新时间</th>
                <th className="px-4 py-3 text-center font-bold w-48">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <Tag variant="outline" size="small">{row.asset_id}</Tag>
                  </td>
                  <td className="px-4 py-3">
                    {STANDARD_OPTIONS.find((o) => o.value === row.standard)?.label ?? row.standard}
                  </td>
                  <td className="px-4 py-3">{row.schema_version}</td>
                  <td className="px-4 py-3">{row.fields?.length ?? 0}</td>
                  <td className="px-4 py-3">
                    {row.previous_version_id ? (
                      <Tag size="small">{row.previous_version_id.slice(0, 8)}</Tag>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{new Date(row.updated_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="编辑">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-blue-50 text-blue-500 cursor-pointer transition-colors"
                          onClick={() => openEditForm(row)}
                        >
                          <EditIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="版本历史">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-purple-50 text-purple-500 cursor-pointer transition-colors"
                          onClick={() => handleViewVersions(row.id)}
                        >
                          <HistoryIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="血缘关系">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-green-50 text-green-500 cursor-pointer transition-colors"
                          onClick={() => handleViewLineage(row.id)}
                        >
                          <LinkIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="删除">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-red-50 text-red-500 cursor-pointer transition-colors"
                          onClick={() => setDeleteTarget(row)}
                        >
                          <DeleteIcon size="16px" />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredItems.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-end px-4 py-3 border-t border-gray-100 flex-wrap gap-2">
          <span className="text-sm text-gray-500">每页</span>
          <select
            className="border border-gray-300 rounded px-2 py-1 text-sm"
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
          >
            {[10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <span className="text-sm text-gray-500">
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} / {total}
          </span>
          <Button variant="text" size="small" disabled={page === 0} onClick={() => setPage(page - 1)}>上一页</Button>
          <Button variant="text" size="small" disabled={(page + 1) * pageSize >= total} onClick={() => setPage(page + 1)}>下一页</Button>
        </div>
      </PageSection>

      {/* 元数据编辑器弹窗 */}
      <MetadataEditor
        formOpen={formOpen}
        editingId={editingId}
        formData={formData}
        onClose={closeForm}
        onSubmit={handleSubmit}
        onFieldChange={handleFieldChange}
        submitPending={isMutPending}
      />

      {/* 详情对话框（版本历史、血缘、分类规则） */}
      <MetadataDetails
        versionsOpen={versionsOpen}
        versionsData={versionsData}
        versionsLoading={versionsLoading}
        onVersionsClose={() => setVersionsOpen(false)}
        lineageOpen={lineageOpen}
        lineageData={lineageData}
        lineageLoading={lineageLoading}
        onLineageClose={() => setLineageOpen(false)}
        rulesOpen={rulesOpen}
        classificationRules={(classificationRules as any[]) ?? []}
        onRulesClose={() => setRulesOpen(false)}
      />

      {/* 删除确认 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除元数据"
        message="确定要删除该元数据记录吗？此操作不可撤销。"
        type="danger"
        confirmText="删除"
        onConfirm={() => { if (deleteTarget) deleteMut.mutate(deleteTarget.id); }}
        onCancel={() => setDeleteTarget(null)}
      />

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default MetadataPage;
