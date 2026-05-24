/**
 * CatalogTable - 数据目录表格组件
 * 搜索栏 + 多维过滤 + 数据表格 + 分页
 */
import React from 'react';
import { Button, Input, Select, Tag, Tooltip } from 'tdesign-react';
import {
  SearchIcon, BrowseIcon, CheckCircleIcon,
  FolderOpenIcon, StarIcon, ShieldErrorFilledIcon, FilterIcon,
} from 'tdesign-icons-react';
import type { DataCatalogItem } from '@/types/api';
import type { SearchFacets, SearchSuggestion } from '@/api/dataCatalog';
import StatusTag from '@/components/StatusTag';
import { PageSection } from '@/components/common';

/** 级别选项 */
const LEVEL_OPTIONS = [
  { value: '', label: '全部' },
  { value: '1', label: '1级-核心' },
  { value: '2', label: '2级-重要' },
  { value: '3', label: '3级-敏感' },
  { value: '4', label: '4级-公开' },
];

const SORT_OPTIONS = [
  { value: 'relevance', label: '相关性' },
  { value: 'published_at', label: '发布时间' },
  { value: 'rating', label: '评分' },
  { value: 'record_count', label: '数据量' },
];

interface CatalogTableProps {
  searchKeyword: string;
  onKeywordChange: (val: string) => void;
  onSearch: () => void;
  filterLevel: string;
  onLevelChange: (val: string) => void;
  sortBy: string;
  onSortChange: (val: string) => void;
  facets: SearchFacets | null;
  selectedCategory: string;
  onCategoryTagClick: (cat: string) => void;
  activeFilterCount: number;
  onClearFilters: () => void;
  suggestions: SearchSuggestion[];
  onSuggestionClick: (keyword: string) => void;
  items: any[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onPreview: (id: string) => void;
  onApply: (item: DataCatalogItem) => void;
  onFeedback: (item: DataCatalogItem) => void;
  onClassify: (item: DataCatalogItem) => void;
  onVerify: (item: DataCatalogItem) => void;
}

/** CatalogTable 组件 */
const CatalogTable: React.FC<CatalogTableProps> = ({
  searchKeyword,
  onKeywordChange,
  onSearch,
  filterLevel,
  onLevelChange,
  sortBy,
  onSortChange,
  facets,
  selectedCategory,
  onCategoryTagClick,
  activeFilterCount,
  onClearFilters,
  suggestions,
  onSuggestionClick,
  items,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  onPreview,
  onApply,
  onFeedback,
  onClassify,
  onVerify,
}) => {
  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden">
      {/* 搜索栏 + 多维过滤 */}
      <PageSection padding="sm">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <Input
              value={searchKeyword}
              onChange={(val) => {
                onKeywordChange(String(val));
              }}
              placeholder="搜索数据目录"
              prefixIcon={<SearchIcon />}
              className="flex-1"
              onEnter={onSearch}
            />
            <Button theme="primary" onClick={onSearch}>搜索</Button>
            <div className="relative">
              <Button
                variant="outline"
                icon={<FilterIcon />}
                onClick={onClearFilters}
              >
                重置过滤
              </Button>
              {activeFilterCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-blue-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </div>
          </div>
          {/* 过滤条件行 */}
          <div className="flex items-center gap-3 flex-wrap">
            <Select
              value={filterLevel}
              options={LEVEL_OPTIONS}
              onChange={(val) => onLevelChange(String(val))}
              style={{ width: 140 }}
            />
            <Select
              value={sortBy}
              options={SORT_OPTIONS}
              onChange={(val) => onSortChange(String(val))}
              style={{ width: 140 }}
            />
            {/* Facets标签展示 */}
            {facets && Object.keys(facets.categories).length > 0 && (
              <div className="flex gap-1 flex-wrap flex-1">
                {Object.entries(facets.categories).slice(0, 5).map(([cat, count]) => (
                  <Tag
                    key={cat}
                    variant={selectedCategory === cat ? 'dark' : 'light'}
                    theme={selectedCategory === cat ? 'primary' : 'default'}
                    onClick={() => onCategoryTagClick(selectedCategory === cat ? '' : cat)}
                    className="cursor-pointer"
                  >
                    {cat} ({count as number})
                  </Tag>
                ))}
              </div>
            )}
          </div>
          {/* 搜索建议 */}
          {suggestions.length > 0 && searchKeyword && (
            <div className="border border-gray-200 rounded-lg p-2 max-h-28 overflow-auto">
              <p className="text-xs text-gray-500 mb-1">搜索建议：</p>
              <div className="flex gap-1 flex-wrap">
                {suggestions.map((s) => (
                  <Tag
                    key={s.keyword}
                    variant="light"
                    className="cursor-pointer"
                    onClick={() => onSuggestionClick(s.keyword)}
                  >
                    {s.keyword} ({s.count})
                  </Tag>
                ))}
              </div>
            </div>
          )}
        </div>
      </PageSection>

      {/* 列表 */}
      <PageSection padding="none" className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left font-bold">名称</th>
                <th className="px-4 py-3 text-left font-bold">分类</th>
                <th className="px-4 py-3 text-left font-bold">敏感级别</th>
                <th className="px-4 py-3 text-left font-bold">标签</th>
                <th className="px-4 py-3 text-left font-bold">提供方</th>
                <th className="px-4 py-3 text-left font-bold">数据量</th>
                <th className="px-4 py-3 text-left font-bold">评分</th>
                <th className="px-4 py-3 text-left font-bold">状态</th>
                <th className="px-4 py-3 text-center font-bold w-56">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row: any) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.name}</p>
                    {row.description && (
                      <p className="text-xs text-gray-500 max-w-[200px] truncate">{row.description}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">{row.category}</td>
                  <td className="px-4 py-3"><StatusTag status={row.sensitivity_level} /></td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {row.tags?.slice(0, 3).map((tag: string) => (
                        <Tag key={tag} variant="outline" size="small">{tag}</Tag>
                      ))}
                      {(row.tags?.length || 0) > 3 && (
                        <Tag size="small">+{(row.tags?.length || 0) - 3}</Tag>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">{row.owner_org}</td>
                  <td className="px-4 py-3">{row.record_count ? row.record_count.toLocaleString() : '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <StarIcon size="14px" className="text-amber-400" />
                      <span className="text-sm">{row.avg_rating?.toFixed(1) || '-'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusTag status={row.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="预览数据">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-blue-50 text-blue-500 cursor-pointer transition-colors"
                          onClick={() => onPreview(row.id)}
                        >
                          <BrowseIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="申请访问">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-blue-50 text-blue-600 cursor-pointer transition-colors"
                          onClick={() => onApply(row)}
                        >
                          <CheckCircleIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="评分反馈">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-amber-50 text-amber-500 cursor-pointer transition-colors"
                          onClick={() => onFeedback(row)}
                        >
                          <StarIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="自动分类">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-purple-50 text-purple-500 cursor-pointer transition-colors"
                          onClick={() => onClassify(row)}
                        >
                          <FolderOpenIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="完整性验证">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-green-50 text-green-500 cursor-pointer transition-colors"
                          onClick={() => onVerify(row)}
                        >
                          <ShieldErrorFilledIcon size="16px" />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
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
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
          >
            {[10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <span className="text-sm text-gray-500">
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} / {total}
          </span>
          <Button variant="text" size="small" disabled={page === 0} onClick={() => onPageChange(page - 1)}>上一页</Button>
          <Button variant="text" size="small" disabled={(page + 1) * pageSize >= total} onClick={() => onPageChange(page + 1)}>下一页</Button>
        </div>
      </PageSection>
    </div>
  );
};

export default CatalogTable;
