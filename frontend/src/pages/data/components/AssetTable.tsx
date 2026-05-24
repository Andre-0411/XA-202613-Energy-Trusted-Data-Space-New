/**
 * AssetTable - 数据资产表格组件
 * 搜索过滤栏 + 数据表格 + 分页
 */
import React from 'react';
import { Button, Input, Select, Tag, Tooltip } from 'tdesign-react';
import {
  BrowseIcon, FolderOpenIcon, CheckCircleFilledIcon, DeleteIcon,
} from 'tdesign-icons-react';
import type { DataAsset } from '@/types/api';
import StatusTag from '@/components/StatusTag';
import { PageSection } from '@/components/common';
import { CATEGORY_OPTIONS, SENSITIVITY_OPTIONS } from './AssetStats';

/** 分类选择选项 */
const CATEGORY_SELECT_OPTIONS = CATEGORY_OPTIONS.map((opt) => ({
  value: opt.value,
  label: `${opt.icon} ${opt.label}`,
}));

/** 敏感级别选择选项 */
const SENSITIVITY_SELECT_OPTIONS = [
  { value: '', label: '全部' },
  ...SENSITIVITY_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label })),
];

interface AssetTableProps {
  keyword: string;
  onKeywordChange: (val: string) => void;
  filterCategory: string;
  onCategoryChange: (val: string) => void;
  filterSensitivity: string;
  onSensitivityChange: (val: string) => void;
  onReset: () => void;
  items: DataAsset[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onViewDetail: (item: DataAsset) => void;
  onClassify: (id: string) => void;
  onPublish: (item: DataAsset) => void;
}

/** 获取分类图标 */
const getCategoryIcon = (category: string) => {
  const cat = CATEGORY_OPTIONS.find((c) => c.value === category);
  return cat?.icon || '📊';
};

/** 获取分类颜色 */
const getCategoryColor = (category: string) => {
  const cat = CATEGORY_OPTIONS.find((c) => c.value === category);
  return cat?.color || '#6b7280';
};

/** 敏感级别颜色映射 - 四级安全等级 */
const sensitivityColor = (level: string): 'success' | 'info' | 'warning' | 'error' | 'default' => {
  const map: Record<string, 'success' | 'info' | 'warning' | 'error'> = {
    '1': 'error',     // 核心
    '2': 'warning',   // 重要
    '3': 'info',      // 一般
    '4': 'success',   // 公开
    // 兼容旧值
    public: 'success',
    internal: 'info',
    confidential: 'warning',
    secret: 'error',
  };
  return map[level] ?? 'default';
};

/** AssetTable 组件 */
const AssetTable: React.FC<AssetTableProps> = ({
  keyword,
  onKeywordChange,
  filterCategory,
  onCategoryChange,
  filterSensitivity,
  onSensitivityChange,
  onReset,
  items,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  onViewDetail,
  onClassify,
  onPublish,
}) => {
  const hasFilters = keyword || filterCategory || filterSensitivity;

  return (
    <>
      {/* 搜索过滤栏 */}
      <PageSection padding="sm">
        <div className="flex flex-wrap gap-3 items-center">
          <Input
            placeholder="搜索名称/编码"
            value={keyword}
            onChange={(val) => onKeywordChange(String(val))}
            className="!w-full sm:!w-52"
          />
          <Select
            value={filterCategory}
            options={[{ value: '', label: '全部分类' }, ...CATEGORY_SELECT_OPTIONS]}
            onChange={(val) => onCategoryChange(String(val))}
            className="!w-full sm:!w-36"
          />
          <Select
            value={filterSensitivity}
            options={SENSITIVITY_SELECT_OPTIONS}
            onChange={(val) => onSensitivityChange(String(val))}
            className="!w-full sm:!w-36"
          />
          {hasFilters && (
            <Button variant="outline" onClick={onReset}>
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
                <th className="px-4 py-3 text-left font-bold">资产名称</th>
                <th className="px-4 py-3 text-left font-bold">编码</th>
                <th className="px-4 py-3 text-left font-bold">分类</th>
                <th className="px-4 py-3 text-left font-bold">敏感级别</th>
                <th className="px-4 py-3 text-left font-bold">发布状态</th>
                <th className="px-4 py-3 text-left font-bold">更新时间</th>
                <th className="px-4 py-3 text-center font-bold w-48">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{getCategoryIcon(row.category)}</span>
                      <span className="font-medium">{row.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs">{row.asset_code}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Tag
                      variant="light"
                      style={{
                        backgroundColor: getCategoryColor(row.category) + '20',
                        color: getCategoryColor(row.category),
                      }}
                    >
                      {CATEGORY_OPTIONS.find((o) => o.value === row.category)?.label ?? row.category}
                    </Tag>
                  </td>
                  <td className="px-4 py-3">
                    <StatusTag
                      status={SENSITIVITY_OPTIONS.find((o) => o.value === row.sensitivity_level)?.label ?? row.sensitivity_level}
                      color={sensitivityColor(row.sensitivity_level)}
                    />
                  </td>
                  <td className="px-4 py-3"><StatusTag status={row.status} /></td>
                  <td className="px-4 py-3">{new Date(row.updated_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="查看详情">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-blue-50 text-blue-500 cursor-pointer transition-colors"
                          onClick={() => onViewDetail(row)}
                        >
                          <BrowseIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="分类标注">
                        <span
                          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-blue-50 text-blue-500 cursor-pointer transition-colors"
                          onClick={() => onClassify(row.id)}
                        >
                          <FolderOpenIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="发布到目录">
                        <span
                          className={`inline-flex items-center justify-center w-8 h-8 rounded-full transition-colors ${row.status === 'published' ? 'text-gray-300 cursor-not-allowed' : 'hover:bg-green-50 text-green-500 cursor-pointer'}`}
                          onClick={() => row.status !== 'published' && onPublish(row)}
                        >
                          <CheckCircleFilledIcon size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="删除">
                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-red-50 text-red-500 cursor-pointer transition-colors">
                          <DeleteIcon size="16px" />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-end px-4 py-3 border-t border-gray-100 flex-wrap gap-2">
          <span className="text-sm text-gray-500">每页</span>
          <Select
            value={String(pageSize)}
            options={[{ value: '10', label: '10' }, { value: '20', label: '20' }, { value: '50', label: '50' }]}
            onChange={(val) => onPageSizeChange(Number(val))}
            className="!w-20"
          />
          <span className="text-sm text-gray-500">
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} / {total}
          </span>
          <Button variant="text" size="small" disabled={page === 0} onClick={() => onPageChange(page - 1)}>上一页</Button>
          <Button variant="text" size="small" disabled={(page + 1) * pageSize >= total} onClick={() => onPageChange(page + 1)}>下一页</Button>
        </div>
      </PageSection>
    </>
  );
};

export default AssetTable;
