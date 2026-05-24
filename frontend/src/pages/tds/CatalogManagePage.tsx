/**
 * 数据目录管理页面
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button, Tag, Tooltip,
} from 'tdesign-react';
import {
  AddIcon, BrowseIcon, SendIcon, CloseIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listCatalogs, publishCatalog, unpublishCatalog } from '@/api/catalogManage';
import type { CatalogRegistration } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'default'> = {
  published: 'success',
  draft: 'default',
  pending: 'warning',
  unpublished: 'default',
};

const sensitivityThemeMap: Record<string, 'danger' | 'warning' | 'primary' | 'default'> = {
  high: 'danger',
  medium: 'warning',
  low: 'primary',
  public: 'default',
};

export default function CatalogManagePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['catalog-manage', page, pageSize, keyword, statusFilter, categoryFilter],
    queryFn: () => listCatalogs({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
      category: categoryFilter || undefined,
    }),
  });

  const publishMutation = useMutation({
    mutationFn: publishCatalog,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['catalog-manage'] }),
  });

  const unpublishMutation = useMutation({
    mutationFn: unpublishCatalog,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['catalog-manage'] }),
  });

  const columns: Column<CatalogRegistration>[] = [
    {
      id: 'name',
      label: '目录名称',
      minWidth: 200,
      render: (row) => (
        <span
          className="text-sm text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/catalog/${row.id}`)}
        >
          {row.name}
        </span>
      ),
    },
    {
      id: 'category',
      label: '分类',
      minWidth: 120,
      render: (row) => <Tag variant="outline">{row.category}</Tag>,
    },
    {
      id: 'sensitivity_level',
      label: '敏感等级',
      minWidth: 100,
      render: (row) => (
        <Tag theme={sensitivityThemeMap[row.sensitivity_level] || 'default'}>
          {row.sensitivity_level}
        </Tag>
      ),
    },
    {
      id: 'tags',
      label: '标签',
      minWidth: 200,
      render: (row) => (
        <div className="flex items-center gap-1 flex-wrap">
          {row.tags?.slice(0, 3).map((tag, i) => (
            <Tag key={i} size="small">{tag}</Tag>
          ))}
          {row.tags && row.tags.length > 3 && (
            <span className="text-xs text-gray-400">+{row.tags.length - 3}</span>
          )}
        </div>
      ),
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => (
        <Tag theme={statusThemeMap[row.status] || 'default'}>
          {row.status}
        </Tag>
      ),
    },
    {
      id: 'published_at',
      label: '发布时间',
      minWidth: 160,
      render: (row) => row.published_at ? new Date(row.published_at).toLocaleString('zh-CN') : '-',
    },
    {
      id: 'actions',
      label: '操作',
      minWidth: 150,
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1"
              onClick={() => navigate(`/dashboard/tds/catalog/${row.id}`)}
            >
              <BrowseIcon size="16px" />
            </span>
          </Tooltip>
          {row.status === 'draft' ? (
            <Tooltip content="发布">
              <span
                className="cursor-pointer hover:bg-green-50 rounded p-1 text-green-600"
                onClick={() => publishMutation.mutate(row.id)}
              >
                <SendIcon size="16px" />
              </span>
            </Tooltip>
          ) : row.status === 'published' ? (
            <Tooltip content="下架">
              <span
                className="cursor-pointer hover:bg-yellow-50 rounded p-1 text-yellow-600"
                onClick={() => unpublishMutation.mutate(row.id)}
              >
                <CloseIcon size="16px" />
              </span>
            </Tooltip>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="数据目录管理"
        subtitle="管理数据资源的注册、发布和访问控制"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '数据目录管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            { name: 'keyword', type: 'text', placeholder: '搜索目录名称', width: 240 },
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 120,
              options: [
                { value: '', label: '全部' },
                { value: 'draft', label: '草稿' },
                { value: 'published', label: '已发布' },
                { value: 'unpublished', label: '已下架' },
              ],
            },
            {
              name: 'category',
              type: 'select',
              placeholder: '分类',
              width: 120,
              options: [
                { value: '', label: '全部' },
                { value: 'energy', label: '能源数据' },
                { value: 'grid', label: '电网数据' },
                { value: 'market', label: '市场数据' },
                { value: 'weather', label: '气象数据' },
              ],
            },
          ]}
          values={{ keyword, status: statusFilter, category: categoryFilter }}
          onChange={(name, value) => {
            if (name === 'keyword') setKeyword(String(value));
            if (name === 'status') setStatusFilter(String(value));
            if (name === 'category') setCategoryFilter(String(value));
          }}
          onSearch={() => setPage(0)}
          onReset={() => {
            setKeyword('');
            setStatusFilter('');
            setCategoryFilter('');
            setPage(0);
          }}
          extra={
            <Button
              theme="primary"
              icon={<AddIcon />}
              onClick={() => navigate('/dashboard/tds/catalog/new')}
            >
              注册目录
            </Button>
          }
        />

        <div className="mt-4">
          <DataTable
            columns={columns}
            rows={data?.data?.items || []}
            loading={isLoading}
            page={page}
            pageSize={pageSize}
            total={data?.data?.total || 0}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </div>
      </PageSection>
    </PageContainer>
  );
}
