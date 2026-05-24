/**
 * 数据目录页面
 * 左侧分类树 + 右侧目录项列表 + 搜索 + 申请访问 + 评分反馈
 * 支持多维过滤(分类/级别/组织/标签) + 搜索建议 + Facets
 * 拆分为 CatalogTree + CatalogTable + CatalogDetail 子组件
 */
import React, { useState, useCallback, useMemo } from 'react';
import { MessagePlugin } from 'tdesign-react';
import {
  RefreshIcon, FolderOpenIcon, CheckCircleIcon, TimeIcon, TrendingUpIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  browseCatalog as browseCatalogLegacy, searchCatalog as searchCatalogLegacy,
  applyForAccess, submitFeedback, previewCatalogItem,
} from '@/api/data';
import {
  searchCatalog, getSearchSuggestions, browseCatalog,
  classifyData, verifyIntegrity,
} from '@/api/dataCatalog';
import type { SearchFacets, SearchSuggestion } from '@/api/dataCatalog';
import type { DataCatalogItem } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageSection, StatGrid, StatCard } from '@/components/common';
import LoadingOverlay from '@/components/LoadingOverlay';
import CatalogTree from './components/CatalogTree';
import CatalogTable from './components/CatalogTable';
import CatalogDetail from './components/CatalogDetail';

const DataCatalogPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const catalogTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增目录', '访问量'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增目录', type: 'bar', data: [180, 220, 250, 280, 310, 350, 380], itemStyle: { color: '#2196f3' } },
      { name: '访问量', type: 'line', smooth: true, data: [1200, 1800, 2200, 2600, 2900, 3200, 3450], itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  const categoryDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '目录分类',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 980, name: '能源数据', itemStyle: { color: '#2196f3' } },
          { value: 650, name: '金融数据', itemStyle: { color: '#4caf50' } },
          { value: 450, name: '个人信息', itemStyle: { color: '#ff9800' } },
          { value: 370, name: '运营数据', itemStyle: { color: '#9c27b0' } },
        ],
      },
    ],
  }), []);

  // ===== 状态 =====
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);
  const [filterLevel, setFilterLevel] = useState<string>('');
  const [filterOrg, setFilterOrg] = useState<string>('');
  const [filterTags, setFilterTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<string>('relevance');
  const [facets, setFacets] = useState<SearchFacets | null>(null);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [classifyDialogOpen, setClassifyDialogOpen] = useState<boolean>(false);
  const [classifyResult, setClassifyResult] = useState<any>(null);
  const [verifyDialogOpen, setVerifyDialogOpen] = useState<boolean>(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  // ===== 弹窗 =====
  const [applyTarget, setApplyTarget] = useState<DataCatalogItem | null>(null);
  const [applyReason, setApplyReason] = useState<string>('');
  const [feedbackTarget, setFeedbackTarget] = useState<DataCatalogItem | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackComment, setFeedbackComment] = useState<string>('');
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['dataCatalog', page, pageSize, selectedCategory, searchKeyword, filterLevel, filterOrg, filterTags, sortBy],
    queryFn: async () => {
      const searchParams = {
        keyword: searchKeyword || undefined,
        category: selectedCategory || undefined,
        classification_level: filterLevel ? Number(filterLevel) : undefined,
        organization_id: filterOrg || undefined,
        tags: filterTags.length > 0 ? filterTags : undefined,
        sort_by: sortBy || undefined,
        page: page + 1,
        page_size: pageSize,
      };

      try {
        const res = await searchCatalog(searchParams);
        if (res?.data) {
          if (res.data.facets) {
            setFacets(res.data.facets);
          }
          return {
            data: {
              items: res.data.items || [],
              total: res.data.total || 0,
            },
          };
        }
      } catch (err) {
        console.warn('Enhanced search failed, falling back to legacy API', err);
      }

      if (searchKeyword.trim()) {
        return searchCatalogLegacy(searchKeyword, { page: page + 1, page_size: pageSize });
      }
      return browseCatalogLegacy({
        page: page + 1,
        page_size: pageSize,
        category: selectedCategory || undefined,
      });
    },
  });

  const items: any[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalItems: total,
    publishedItems: items.filter((i: any) => i.status === 'published').length,
    pendingReview: items.filter((i: any) => i.status === 'pending').length,
    todayViews: 3450,
  }), [items, total]);

  // ===== Mutations =====
  const applyMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => applyForAccess(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataCatalog'] });
      setApplyTarget(null);
      setApplyReason('');
      MessagePlugin.success('申请已提交');
    },
  });

  const feedbackMut = useMutation({
    mutationFn: ({ id, rating, comment }: { id: string; rating: number; comment: string }) =>
      submitFeedback(id, rating, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataCatalog'] });
      setFeedbackTarget(null);
      setFeedbackRating(0);
      setFeedbackComment('');
      MessagePlugin.success('反馈已提交');
    },
  });

  const previewMut = useMutation({
    mutationFn: (id: string) => previewCatalogItem(id),
    onSuccess: (res) => {
      setPreviewData(res.data ?? null);
    },
  });

  const classifyMut = useMutation({
    mutationFn: (params: { data_name: string; data_description?: string; data_fields?: string[] }) =>
      classifyData(params),
    onSuccess: (res) => {
      setClassifyResult(res.data ?? null);
    },
  });

  const verifyMut = useMutation({
    mutationFn: (params: { data_name: string; data_fields: string[]; expected_hash: string }) =>
      verifyIntegrity(params),
    onSuccess: (res) => {
      setVerifyResult(res.data ?? null);
    },
  });

  // 搜索建议
  const handleSearchSuggestions = useCallback(async (keyword: string) => {
    if (!keyword || keyword.length < 2) {
      setSuggestions([]);
      return;
    }
    try {
      const res = await getSearchSuggestions(keyword, 8);
      setSuggestions(res?.data ?? []);
    } catch {
      setSuggestions([]);
    }
  }, []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据目录' }],
    [],
  );

  const handleSearch = useCallback(() => {
    setPage(0);
    queryClient.invalidateQueries({ queryKey: ['dataCatalog'] });
  }, [queryClient]);

  const handleClearFilters = useCallback(() => {
    setSelectedCategory('');
    setSearchKeyword('');
    setFilterLevel('');
    setFilterOrg('');
    setFilterTags([]);
    setSortBy('relevance');
    setPage(0);
    queryClient.invalidateQueries({ queryKey: ['dataCatalog'] });
  }, [queryClient]);

  const handleKeywordChange = useCallback((val: string) => {
    setSearchKeyword(val);
    handleSearchSuggestions(val);
  }, [handleSearchSuggestions]);

  const handleCategorySelect = useCallback((id: string) => {
    setSelectedCategory(id);
    setPage(0);
  }, []);

  const handleSuggestionClick = useCallback((keyword: string) => {
    setSearchKeyword(keyword);
    setSuggestions([]);
    handleSearch();
  }, [handleSearch]);

  const activeFilterCount = (filterLevel ? 1 : 0) + (filterOrg ? 1 : 0) + filterTags.length;

  return (
    <div className="flex flex-col gap-4 h-full overflow-auto">
      <PageHeader
        title="数据目录"
        subtitle="浏览和检索数据目录，申请访问和提交反馈"
        breadcrumbs={breadcrumbs}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['dataCatalog'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总目录项" value={stats.totalItems} icon={<FolderOpenIcon />} gradient="blue" unit="" />
        <StatCard title="已发布" value={stats.publishedItems} icon={<CheckCircleIcon />} gradient="green" unit="" />
        <StatCard title="待审核" value={stats.pendingReview} icon={<TimeIcon />} gradient="cyan" unit="" />
        <StatCard title="今日浏览" value={stats.todayViews} icon={<TrendingUpIcon />} gradient="orange" unit="" />
      </StatGrid>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PageSection title="目录增长趋势" titleIcon={<TrendingUpIcon />} className="md:col-span-2">
          <ReactECharts option={catalogTrendOption} style={{ height: 300 }} />
        </PageSection>
        <PageSection title="目录分类分布" titleIcon={<FolderOpenIcon />}>
          <ReactECharts option={categoryDistOption} style={{ height: 300 }} />
        </PageSection>
      </div>

      {/* 主内容区：分类树 + 表格 */}
      <div className="flex gap-4 flex-1 overflow-hidden">
        <CatalogTree
          selectedCategory={selectedCategory}
          onCategorySelect={handleCategorySelect}
        />
        <CatalogTable
          searchKeyword={searchKeyword}
          onKeywordChange={handleKeywordChange}
          onSearch={handleSearch}
          filterLevel={filterLevel}
          onLevelChange={(val) => { setFilterLevel(val); setPage(0); }}
          sortBy={sortBy}
          onSortChange={(val) => { setSortBy(val); setPage(0); }}
          facets={facets}
          selectedCategory={selectedCategory}
          onCategoryTagClick={(cat) => { setSelectedCategory(cat); setPage(0); }}
          activeFilterCount={activeFilterCount}
          onClearFilters={handleClearFilters}
          suggestions={suggestions}
          onSuggestionClick={handleSuggestionClick}
          items={items}
          total={total}
          page={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
          onPreview={(id) => previewMut.mutate(id)}
          onApply={(item) => setApplyTarget(item)}
          onFeedback={(item) => setFeedbackTarget(item)}
          onClassify={(item) => {
            classifyMut.mutate({
              data_name: item.name,
              data_description: item.description,
              data_fields: item.tags || [],
            });
            setClassifyDialogOpen(true);
          }}
          onVerify={(item) => {
            verifyMut.mutate({
              data_name: item.name,
              data_fields: item.tags || [],
              expected_hash: 'auto',
            });
            setVerifyDialogOpen(true);
          }}
        />
      </div>

      {/* 所有对话框 */}
      <CatalogDetail
        applyTarget={applyTarget}
        applyReason={applyReason}
        onApplyReasonChange={setApplyReason}
        onApplySubmit={() => applyTarget && applyMut.mutate({ id: applyTarget.id, reason: applyReason })}
        onApplyClose={() => { setApplyTarget(null); setApplyReason(''); }}
        applyPending={applyMut.isPending}
        feedbackTarget={feedbackTarget}
        feedbackRating={feedbackRating}
        feedbackComment={feedbackComment}
        onFeedbackRatingChange={setFeedbackRating}
        onFeedbackCommentChange={setFeedbackComment}
        onFeedbackSubmit={() => feedbackTarget && feedbackMut.mutate({ id: feedbackTarget.id, rating: feedbackRating, comment: feedbackComment })}
        onFeedbackClose={() => { setFeedbackTarget(null); setFeedbackRating(0); setFeedbackComment(''); }}
        feedbackPending={feedbackMut.isPending}
        previewData={previewData}
        onPreviewClose={() => setPreviewData(null)}
        classifyDialogOpen={classifyDialogOpen}
        classifyResult={classifyResult}
        onClassifyClose={() => { setClassifyDialogOpen(false); setClassifyResult(null); }}
        verifyDialogOpen={verifyDialogOpen}
        verifyResult={verifyResult}
        onVerifyClose={() => { setVerifyDialogOpen(false); setVerifyResult(null); }}
      />

      <LoadingOverlay open={isLoading} />
    </div>
  );
};

export default DataCatalogPage;
