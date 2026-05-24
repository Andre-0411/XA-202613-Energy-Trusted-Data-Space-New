/**
 * 数据服务市场页面
 * 展示可申请使用的数据资产目录，支持搜索、筛选、预览元数据、申请使用、评价反馈
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tag, Textarea } from 'tdesign-react';
import {
  SearchIcon, RefreshIcon, DataBaseIcon, TrendingUpIcon,
  ShieldErrorFilledIcon, UsergroupIcon, FilterIcon,
  FolderOpenIcon, TimeIcon, StarIcon, BrowseIcon, UserAddIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  browseCatalog, searchCatalog, applyForAccess, submitFeedback, previewCatalogItem,
} from '@/api/data';
import type { DataCatalogItem } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

/** 数据分类选项 */
const DATA_CATEGORIES = [
  { value: 'all', label: '全部分类' },
  { value: 'electricity', label: '电力数据' },
  { value: 'gas', label: '燃气数据' },
  { value: 'renewable', label: '新能源数据' },
  { value: 'market', label: '市场数据' },
  { value: 'device', label: '设备数据' },
  { value: 'geographic', label: '地理信息' },
];

/** 敏感级别选项 */
const SENSITIVITY_LEVELS = [
  { value: 'all', label: '全部级别' },
  { value: 'public', label: '公开' },
  { value: 'internal', label: '内部' },
  { value: 'confidential', label: '机密' },
  { value: 'secret', label: '绝密' },
];

/** 排序选项 */
const SORT_OPTIONS = [
  { value: 'updated_at', label: '最近更新' },
  { value: 'rating', label: '评分最高' },
  { value: 'usage_count', label: '使用最多' },
  { value: 'name', label: '名称排序' },
];

const DataMarketPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 搜索与筛选状态 =====
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSensitivity, setSelectedSensitivity] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('updated_at');

  // ===== 分页状态 =====
  const [page, setPage] = useState<number>(0);
  const [pageSize] = useState<number>(12);

  // ===== 预览对话框状态 =====
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null);
  const [previewItem, setPreviewItem] = useState<DataCatalogItem | null>(null);

  // ===== 申请对话框状态 =====
  const [applyOpen, setApplyOpen] = useState<boolean>(false);
  const [applyItem, setApplyItem] = useState<DataCatalogItem | null>(null);
  const [applyReason, setApplyReason] = useState<string>('');

  // ===== 评价对话框状态 =====
  const [feedbackOpen, setFeedbackOpen] = useState<boolean>(false);
  const [feedbackItem, setFeedbackItem] = useState<DataCatalogItem | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackComment, setFeedbackComment] = useState<string>('');

  // ===== 查询参数 =====
  const queryParams = useMemo(() => ({
    page: page + 1,
    page_size: pageSize,
    category: selectedCategory !== 'all' ? selectedCategory : undefined,
    sensitivity_level: selectedSensitivity !== 'all' ? selectedSensitivity : undefined,
    sort_by: sortBy,
    sort_order: 'desc' as const,
  }), [page, pageSize, selectedCategory, selectedSensitivity, sortBy]);

  // ===== 数据查询 =====
  const { data: catalogData, isLoading, refetch } = useQuery({
    queryKey: ['dataMarket', queryParams],
    queryFn: () => searchKeyword.trim()
      ? searchCatalog(searchKeyword, queryParams)
      : browseCatalog(queryParams),
  });

  const catalogItems: DataCatalogItem[] = catalogData?.data?.items ?? [];
  const totalCount: number = catalogData?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalAssets: totalCount,
    activeAssets: catalogItems.filter(item => item.status === 'active').length,
    publicAssets: catalogItems.filter(item => item.sensitivity_level === 'public').length,
    totalUsage: catalogItems.reduce((sum, item) => sum + (item.usage_count ?? 0), 0),
  }), [catalogItems, totalCount]);

  // ===== ECharts 配置 =====
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#ff9800', '#9c27b0'];

  const categoryChartOption = useMemo(() => {
    const catMap: Record<string, number> = {};
    catalogItems.forEach((item) => {
      const label = DATA_CATEGORIES.find((c) => c.value === item.category)?.label ?? item.category;
      catMap[label] = (catMap[label] ?? 0) + 1;
    });
    const entries = Object.entries(catMap).sort((a, b) => b[1] - a[1]);
    return {
      tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical' as const, left: 'left', top: 20 },
      series: [
        {
          name: '数据分类',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
          label: { show: false, position: 'center' },
          emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
          labelLine: { show: false },
          data: entries.map(([name, value], i) => ({
            value, name, itemStyle: { color: COLORS[i % COLORS.length] },
          })),
        },
      ],
    };
  }, [catalogItems]);

  /** 敏感级别分布图 */
  const sensitivityChartOption = useMemo(() => {
    const levelMap: Record<string, number> = {};
    catalogItems.forEach((item) => {
      const label = SENSITIVITY_LEVELS.find((l) => l.value === item.sensitivity_level)?.label ?? item.sensitivity_level;
      levelMap[label] = (levelMap[label] ?? 0) + 1;
    });
    const entries = Object.entries(levelMap).sort((a, b) => b[1] - a[1]);
    return {
      tooltip: { trigger: 'item' as const },
      legend: { orient: 'vertical' as const, left: 'left', top: 20 },
      series: [
        {
          name: '敏感级别',
          type: 'pie',
          radius: '65%',
          center: ['60%', '50%'],
          data: entries.map(([name, value], i) => ({
            value, name, itemStyle: { color: COLORS[i % COLORS.length] },
          })),
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
        },
      ],
    };
  }, [catalogItems]);

  // ===== Mutations =====
  const applyMut = useMutation({
    mutationFn: (data: { id: string; reason: string }) => applyForAccess(data.id, data.reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataMarket'] });
      setApplyOpen(false);
      setApplyReason('');
    },
  });

  const feedbackMut = useMutation({
    mutationFn: (data: { id: string; rating: number; comment: string }) =>
      submitFeedback(data.id, data.rating, data.comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataMarket'] });
      setFeedbackOpen(false);
      setFeedbackRating(0);
      setFeedbackComment('');
    },
  });

  const previewMut = useMutation({
    mutationFn: (id: string) => previewCatalogItem(id),
    onSuccess: (res) => {
      setPreviewData(res.data);
    },
  });

  // ===== 事件处理 =====
  const handleSearch = useCallback(() => {
    setPage(0);
    refetch();
  }, [refetch]);

  const handleRefresh = useCallback(() => {
    setSearchKeyword('');
    setSelectedCategory('all');
    setSelectedSensitivity('all');
    setSortBy('updated_at');
    setPage(0);
    queryClient.invalidateQueries({ queryKey: ['dataMarket'] });
  }, [queryClient]);

  const handlePreview = useCallback((item: DataCatalogItem) => {
    setPreviewItem(item);
    setPreviewData(null);
    setPreviewOpen(true);
    previewMut.mutate(item.id);
  }, [previewMut]);

  const handleApply = useCallback((item: DataCatalogItem) => {
    setApplyItem(item);
    setApplyReason('');
    setApplyOpen(true);
  }, []);

  const handleSubmitApply = useCallback(() => {
    if (!applyItem || !applyReason.trim()) return;
    applyMut.mutate({ id: applyItem.id, reason: applyReason });
  }, [applyItem, applyReason, applyMut]);

  const handleFeedback = useCallback((item: DataCatalogItem) => {
    setFeedbackItem(item);
    setFeedbackRating(0);
    setFeedbackComment('');
    setFeedbackOpen(true);
  }, []);

  const handleSubmitFeedback = useCallback(() => {
    if (!feedbackItem || !feedbackRating) return;
    feedbackMut.mutate({ id: feedbackItem.id, rating: feedbackRating, comment: feedbackComment });
  }, [feedbackItem, feedbackRating, feedbackComment, feedbackMut]);

  // ===== 获取敏感级别颜色 =====
  const getSensitivityTheme = (level: string): 'success' | 'primary' | 'warning' | 'danger' | 'default' => {
    switch (level) {
      case 'public': return 'success';
      case 'internal': return 'primary';
      case 'confidential': return 'warning';
      case 'secret': return 'danger';
      default: return 'default';
    }
  };

  // ===== 获取数据分类图标 =====
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'electricity': return '⚡';
      case 'gas': return '🔥';
      case 'renewable': return '🌱';
      case 'market': return '📈';
      case 'device': return '🔧';
      case 'geographic': return '🗺️';
      default: return '📊';
    }
  };

  // ===== 渲染星级评分 =====
  const renderStars = (rating: number, size: 'sm' | 'md' = 'sm') => {
    const full = Math.floor(rating);
    const hasHalf = rating - full >= 0.5;
    const iconSize = size === 'sm' ? 'text-sm' : 'text-base';
    return (
      <span className="flex items-center gap-0.5">
        {Array.from({ length: 5 }, (_, i) => (
          <StarIcon
            key={i}
            className={`${iconSize} ${
              i < full ? 'text-yellow-400' : i === full && hasHalf ? 'text-yellow-300' : 'text-gray-300'
            }`}
          />
        ))}
      </span>
    );
  };

  return (
    <PageContainer>
      <PageHeader
        title="数据服务市场"
        subtitle="浏览和申请使用能源数据资产"
        breadcrumbs={[homeBreadcrumb, { label: '数据中心' }, { label: '数据服务市场' }]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总数据资产" value={stats.totalAssets} icon={<DataBaseIcon />} gradient="blue" unit="" />
        <StatCard title="活跃资产" value={stats.activeAssets} icon={<TrendingUpIcon />} gradient="green" unit="" />
        <StatCard title="公开资产" value={stats.publicAssets} icon={<ShieldErrorFilledIcon />} gradient="purple" unit="" />
        <StatCard title="总使用次数" value={stats.totalUsage} icon={<UsergroupIcon />} gradient="orange" unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PageSection title="数据分类分布" titleIcon={<FilterIcon />}>
          {catalogItems.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">暂无数据</p>
          ) : (
            <ReactECharts option={categoryChartOption} style={{ height: 300 }} />
          )}
        </PageSection>
        <PageSection title="敏感级别分布" titleIcon={<ShieldErrorFilledIcon />}>
          {catalogItems.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">暂无数据</p>
          ) : (
            <ReactECharts option={sensitivityChartOption} style={{ height: 300 }} />
          )}
        </PageSection>
      </div>

      {/* 搜索与筛选区域 */}
      <PageSection padding="sm">
        <div className="flex flex-wrap items-center gap-3">
          <Input
            placeholder="搜索数据资产..."
            value={searchKeyword}
            onChange={(val) => setSearchKeyword(String(val))}
            prefixIcon={<SearchIcon />}
            className="!w-[280px]"
            onEnter={handleSearch}
          />
          <Select
            value={selectedCategory}
            onChange={(val) => { setSelectedCategory(String(val)); setPage(0); }}
            options={DATA_CATEGORIES}
            style={{ width: 140 }}
          />
          <Select
            value={selectedSensitivity}
            onChange={(val) => { setSelectedSensitivity(String(val)); setPage(0); }}
            options={SENSITIVITY_LEVELS}
            style={{ width: 140 }}
          />
          <Select
            value={sortBy}
            onChange={(val) => { setSortBy(String(val)); setPage(0); }}
            options={SORT_OPTIONS}
            style={{ width: 140 }}
          />
          <Button theme="primary" icon={<SearchIcon />} onClick={handleSearch}>
            搜索
          </Button>
        </div>
      </PageSection>

      {/* 数据资产卡片网格 */}
      <LoadingOverlay open={isLoading}>
        {catalogItems.length === 0 ? (
          <PageSection>
            <div className="text-center py-8">
              <h3 className="text-base font-semibold text-gray-800">暂无数据资产</h3>
              <p className="text-xs text-gray-600 mt-1">请尝试调整搜索条件或筛选器</p>
            </div>
          </PageSection>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {catalogItems.map((item) => (
              <div key={item.id} className="rounded-xl bg-white border border-gray-200 shadow-sm flex flex-col">
                <div className="p-4 flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xl">{getCategoryIcon(item.category)}</span>
                    <h3 className="text-sm font-semibold text-gray-800 truncate">{item.name}</h3>
                  </div>

                  <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                    {item.description || '暂无描述'}
                  </p>

                  <div className="flex flex-wrap gap-1.5 mb-3">
                    <Tag
                      icon={<FilterIcon />}
                      theme="primary"
                      variant="outline"
                      size="small"
                    >
                      {DATA_CATEGORIES.find(c => c.value === item.category)?.label || item.category}
                    </Tag>
                    <Tag
                      theme={getSensitivityTheme(item.sensitivity_level)}
                      variant="outline"
                      size="small"
                    >
                      {SENSITIVITY_LEVELS.find(l => l.value === item.sensitivity_level)?.label || item.sensitivity_level}
                    </Tag>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <FolderOpenIcon className="text-sm" />
                      {item.usage_count ?? 0} 次使用
                    </span>
                    <span className="flex items-center gap-1">
                      <TimeIcon className="text-sm" />
                      {item.updated_at ? new Date(item.updated_at).toLocaleDateString('zh-CN') : '-'}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 mt-2">
                    {renderStars(item.rating ?? 0)}
                    <span className="text-xs text-gray-500 ml-1">({item.rating_count ?? 0})</span>
                  </div>
                </div>

                <div className="flex gap-2 p-3 border-t border-gray-100">
                  <Button
                    size="small"
                    icon={<BrowseIcon />}
                    onClick={() => handlePreview(item)}
                  >
                    预览
                  </Button>
                  <Button
                    size="small"
                    theme="primary"
                    icon={<UserAddIcon />}
                    onClick={() => handleApply(item)}
                  >
                    申请使用
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </LoadingOverlay>

      {/* 分页控件 */}
      {totalCount > 0 && (
        <PageSection padding="sm">
          <div className="flex items-center justify-center gap-4">
            <span className="text-xs text-gray-600">共 {totalCount} 项</span>
            <Button
              size="small"
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
            >
              上一页
            </Button>
            <span className="text-xs text-gray-600">第 {page + 1} 页</span>
            <Button
              size="small"
              disabled={(page + 1) * pageSize >= totalCount}
              onClick={() => setPage(p => p + 1)}
            >
              下一页
            </Button>
          </div>
        </PageSection>
      )}

      {/* 预览对话框 */}
      <Dialog
        visible={previewOpen}
        onClose={() => setPreviewOpen(false)}
        header={`数据预览 - ${previewItem?.name ?? ''}`}
        width={640}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setPreviewOpen(false)}>关闭</Button>
            {previewItem && (
              <Button
                theme="primary"
                onClick={() => {
                  setPreviewOpen(false);
                  handleApply(previewItem);
                }}
              >
                申请使用
              </Button>
            )}
          </div>
        }
      >
        {previewMut.isPending ? (
          <div className="text-center py-8">
            <p className="text-gray-500">加载预览数据中...</p>
          </div>
        ) : previewData ? (
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(previewData).slice(0, 10).map(([key, value]) => (
                <tr key={key} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-medium text-gray-600 whitespace-nowrap">{key}</td>
                  <td className="py-2 text-gray-800">{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-gray-500 text-center py-4">暂无预览数据</p>
        )}
      </Dialog>

      {/* 申请使用对话框 */}
      <Dialog
        visible={applyOpen}
        onClose={() => setApplyOpen(false)}
        header="申请使用数据资产"
        width={520}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setApplyOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={handleSubmitApply}
              disabled={!applyReason.trim() || applyMut.isPending}
              loading={applyMut.isPending}
            >
              {applyMut.isPending ? '提交中...' : '提交申请'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="text-base font-semibold text-gray-800">{applyItem?.name}</p>
          <p className="text-sm text-gray-600">{applyItem?.description}</p>
          <div>
            <p className="text-sm text-gray-600 mb-1">申请理由</p>
            <Textarea
              value={applyReason}
              onChange={(val) => setApplyReason(String(val))}
              placeholder="请说明您申请使用此数据资产的目的和用途..."
              rows={4}
            />
          </div>
        </div>
      </Dialog>

      {/* 评价反馈对话框 */}
      <Dialog
        visible={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        header="评价数据资产"
        width={520}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setFeedbackOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={handleSubmitFeedback}
              disabled={!feedbackRating || feedbackMut.isPending}
              loading={feedbackMut.isPending}
            >
              {feedbackMut.isPending ? '提交中...' : '提交评价'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="text-base font-semibold text-gray-800">{feedbackItem?.name}</p>
          <div>
            <p className="text-sm text-gray-600 mb-1">评分</p>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <StarIcon
                  key={star}
                  className={`text-2xl cursor-pointer transition-colors ${
                    star <= feedbackRating ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-200'
                  }`}
                  onClick={() => setFeedbackRating(star)}
                />
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">评价内容</p>
            <Textarea
              value={feedbackComment}
              onChange={(val) => setFeedbackComment(String(val))}
              placeholder="请分享您对此数据资产的使用体验..."
              rows={3}
            />
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default DataMarketPage;
