/**
 * 数据产品管理页面
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Tag, Tooltip } from 'tdesign-react';
import { AddIcon, BrowseIcon, DeleteIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listDataProducts, deleteDataProduct } from '@/api/productManage';
import type { DataProduct } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default' | 'primary'> = {
  published: 'success',
  draft: 'default',
  pending_review: 'warning',
  archived: 'primary',
};

export default function ProductManagePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['products-manage', page, pageSize, statusFilter, typeFilter],
    queryFn: () => listDataProducts({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
      product_type: typeFilter || undefined,
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDataProduct,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['products-manage'] }),
  });

  const columns: Column<DataProduct>[] = [
    {
      id: 'name',
      label: '产品名称',
      minWidth: 200,
      render: (row) => (
        <span
          className="text-sm text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/products/${row.id}`)}
        >
          {row.name}
        </span>
      ),
    },
    {
      id: 'product_type',
      label: '类型',
      minWidth: 120,
      render: (row) => <Tag variant="outline">{row.product_type}</Tag>,
    },
    { id: 'version', label: '版本', minWidth: 80 },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={statusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    {
      id: 'created_at',
      label: '创建时间',
      minWidth: 160,
      render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions',
      label: '操作',
      minWidth: 120,
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-2">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
              onClick={() => navigate(`/dashboard/tds/products/${row.id}`)}
            >
              <BrowseIcon />
            </span>
          </Tooltip>
          <Tooltip content="删除">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600"
              onClick={() => {
                if (confirm('确定要删除该产品吗？')) deleteMutation.mutate(row.id);
              }}
            >
              <DeleteIcon />
            </span>
          </Tooltip>
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="数据产品管理"
        subtitle="管理数据产品的开发、验收和生命周期"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '数据产品管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 120,
              options: [
                { label: '全部', value: '' },
                { label: '草稿', value: 'draft' },
                { label: '待审核', value: 'pending_review' },
                { label: '已发布', value: 'published' },
                { label: '已归档', value: 'archived' },
              ],
            },
            {
              name: 'type',
              type: 'select',
              placeholder: '类型',
              width: 120,
              options: [
                { label: '全部', value: '' },
                { label: '数据服务', value: 'data_service' },
                { label: '数据API', value: 'data_api' },
                { label: '数据报告', value: 'data_report' },
                { label: '算法模型', value: 'algorithm_model' },
              ],
            },
          ]}
          values={{ status: statusFilter, type: typeFilter }}
          onChange={(name, value) => {
            if (name === 'status') setStatusFilter(String(value));
            if (name === 'type') setTypeFilter(String(value));
          }}
          onSearch={() => setPage(0)}
          onReset={() => {
            setStatusFilter('');
            setTypeFilter('');
            setPage(0);
          }}
          extra={
            <Button
              theme="primary"
              icon={<AddIcon />}
              onClick={() => navigate('/dashboard/tds/products/new')}
            >
              创建产品
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
