/**
 * 数据资产管理页面（增强版）
 * 数据资产的 CRUD、分类标注、发布操作、统计图表、资产详情
 * 拆分为 AssetStats + AssetTable + AssetDetailPanel 子组件
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button } from 'tdesign-react';
import {
  AddIcon, RefreshIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listDataAssets, createDataAsset, classifyAsset, publishAsset,
} from '@/api/data';
import type { DataAsset } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import LoadingOverlay from '@/components/LoadingOverlay';
import AssetStats from './components/AssetStats';
import AssetTable from './components/AssetTable';
import AssetDetailPanel, { INITIAL_FORM, type AssetFormData } from './components/AssetDetailPanel';

const DataAssetsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 & 分页 =====
  const [keyword, setKeyword] = useState<string>('');
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [filterSensitivity, setFilterSensitivity] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 弹窗 =====
  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<AssetFormData>(INITIAL_FORM);
  const [publishTarget, setPublishTarget] = useState<DataAsset | null>(null);
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailItem, setDetailItem] = useState<DataAsset | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['dataAssets', page, pageSize, filterCategory, filterSensitivity],
    queryFn: () =>
      listDataAssets({
        page: page + 1,
        page_size: pageSize,
        category: filterCategory || undefined,
        sensitivity_level: filterSensitivity || undefined,
      }),
  });

  const items: DataAsset[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    totalAssets: total,
    published: items.filter(i => i.status === 'published').length,
    classified: items.filter(i => i.status === 'classified').length,
    sensitive: items.filter(i => i.classification_level === 1 || i.classification_level === 2).length,
    byCategory: {
      '发电': items.filter(i => i.category === '发电').length,
      '用电': items.filter(i => i.category === '用电').length,
      '调度': items.filter(i => i.category === '调度').length,
      '市场': items.filter(i => i.category === '市场').length,
      '设备状态': items.filter(i => i.category === '设备状态').length,
      '地理信息': items.filter(i => i.category === '地理信息').length,
    },
    bySensitivity: {
      '1': items.filter(i => i.classification_level === 1).length,
      '2': items.filter(i => i.classification_level === 2).length,
      '3': items.filter(i => i.classification_level === 3).length,
      '4': items.filter(i => i.classification_level === 4).length,
    },
  }), [items, total]);

  // ===== Mutations =====
  const createMut = useMutation({
    mutationFn: (d: Partial<DataAsset>) => createDataAsset(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataAssets'] });
      closeForm();
    },
  });

  const classifyMut = useMutation({
    mutationFn: (id: string) => classifyAsset(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dataAssets'] }),
  });

  const publishMut = useMutation({
    mutationFn: (id: string) => publishAsset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataAssets'] });
      setPublishTarget(null);
    },
  });

  // ===== 表单操作 =====
  const openCreateForm = useCallback(() => {
    setEditingId(null);
    setFormData(INITIAL_FORM);
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => {
    setFormOpen(false);
    setEditingId(null);
    setFormData(INITIAL_FORM);
  }, []);

  const handleSubmit = useCallback(() => {
    const payload: Partial<DataAsset> = {
      name: formData.name,
      asset_code: formData.asset_code,
      asset_type: formData.asset_type,
      category: formData.category,
      sensitivity_level: formData.sensitivity_level,
      description: formData.description || null,
    };
    createMut.mutate(payload);
  }, [formData, createMut]);

  const handleFieldChange = useCallback(
    (field: keyof AssetFormData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据资产' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{ label: '新建资产', icon: <AddIcon />, onClick: openCreateForm, variant: 'contained' }],
    [openCreateForm],
  );

  // ===== 过滤 =====
  const filteredItems = useMemo(() => {
    if (!keyword.trim()) return items;
    const kw = keyword.toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(kw) ||
        item.asset_code.toLowerCase().includes(kw),
    );
  }, [items, keyword]);

  return (
    <div className="flex flex-col gap-3 sm:gap-4 h-full overflow-auto">
      <PageHeader
        title="数据资产"
        subtitle="管理数据资产的分类、敏感级别与发布状态"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['dataAssets'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 + 图表 */}
      <AssetStats stats={stats} />

      {/* 表格区域 */}
      <AssetTable
        keyword={keyword}
        onKeywordChange={setKeyword}
        filterCategory={filterCategory}
        onCategoryChange={(val) => { setFilterCategory(val); setPage(0); }}
        filterSensitivity={filterSensitivity}
        onSensitivityChange={(val) => { setFilterSensitivity(val); setPage(0); }}
        onReset={() => { setKeyword(''); setFilterCategory(''); setFilterSensitivity(''); setPage(0); }}
        items={filteredItems}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
        onViewDetail={(item) => { setDetailItem(item); setDetailOpen(true); }}
        onClassify={(id) => classifyMut.mutate(id)}
        onPublish={(item) => setPublishTarget(item)}
      />

      {/* 详情面板（新建/详情/发布确认弹窗） */}
      <AssetDetailPanel
        formOpen={formOpen}
        formData={formData}
        onFormClose={closeForm}
        onFormSubmit={handleSubmit}
        onFieldChange={handleFieldChange}
        createPending={createMut.isPending}
        detailOpen={detailOpen}
        detailItem={detailItem}
        onDetailClose={() => setDetailOpen(false)}
        onPublishFromDetail={(item) => setPublishTarget(item)}
        publishTarget={publishTarget}
        onPublishConfirm={() => publishTarget && publishMut.mutate(publishTarget.id)}
        onPublishCancel={() => setPublishTarget(null)}
        publishPending={publishMut.isPending}
      />

      <LoadingOverlay open={isLoading} />
    </div>
  );
};

export default DataAssetsPage;
