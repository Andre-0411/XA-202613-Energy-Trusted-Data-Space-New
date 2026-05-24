/**
 * 产品上架管理页面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Tag, Tooltip } from 'tdesign-react';
import {
  CheckCircleFilledIcon as ApproveIcon,
  CloseIcon as RejectIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listPublishRequests, approvePublishRequest, rejectPublishRequest } from '@/api/productPublish';
import type { ProductPublishRequest } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  approved: 'success',
  pending: 'warning',
  rejected: 'danger',
};

export default function ProductPublishPage() {
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['publish-requests', page, pageSize, statusFilter],
    queryFn: () => listPublishRequests({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
    }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => approvePublishRequest(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['publish-requests'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectPublishRequest(id, { review_comment: '不符合上架要求' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['publish-requests'] }),
  });

  const columns: Column<ProductPublishRequest>[] = [
    {
      id: 'product_id',
      label: '产品ID',
      minWidth: 200,
      render: (row) => <span className="text-xs font-mono text-gray-700">{row.product_id.slice(0, 8)}...</span>,
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={statusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    {
      id: 'review_deadline',
      label: '审核截止',
      minWidth: 160,
      render: (row) => row.review_deadline ? new Date(row.review_deadline).toLocaleString('zh-CN') : '-',
    },
    {
      id: 'created_at',
      label: '申请时间',
      minWidth: 160,
      render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions',
      label: '操作',
      minWidth: 150,
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-2">
          {row.status === 'pending' && (
            <>
              <Tooltip content="审批通过">
                <span
                  className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-600"
                  onClick={() => approveMutation.mutate(row.id)}
                >
                  <ApproveIcon />
                </span>
              </Tooltip>
              <Tooltip content="驳回">
                <span
                  className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600"
                  onClick={() => rejectMutation.mutate(row.id)}
                >
                  <RejectIcon />
                </span>
              </Tooltip>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="产品上架管理"
        subtitle="审核数据产品的上架申请"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '产品上架管理' },
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
                { label: '待审核', value: 'pending' },
                { label: '已通过', value: 'approved' },
                { label: '已驳回', value: 'rejected' },
              ],
            },
          ]}
          values={{ status: statusFilter }}
          onChange={(name, value) => {
            if (name === 'status') setStatusFilter(String(value));
          }}
          onSearch={() => setPage(0)}
          onReset={() => {
            setStatusFilter('');
            setPage(0);
          }}
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
