/**
 * 数据订阅管理页面
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Tag, Tooltip } from 'tdesign-react';
import { BrowseIcon, CheckCircleFilledIcon, CloseIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listDataSubscriptions, approveDataSubscription, rejectDataSubscription } from '@/api/dataSubscription';
import type { DataSubscription } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  approved: 'success',
  pending: 'warning',
  rejected: 'danger',
  expired: 'default',
  cancelled: 'default',
};

export default function DataSubscriptionsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['data-subscriptions', page, pageSize, statusFilter],
    queryFn: () => listDataSubscriptions({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
    }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => approveDataSubscription(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data-subscriptions'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectDataSubscription(id, { review_comment: '不符合订阅条件' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data-subscriptions'] }),
  });

  const columns: Column<DataSubscription>[] = [
    {
      id: 'id',
      label: '订阅ID',
      minWidth: 200,
      render: (row) => (
        <span
          className="text-blue-600 cursor-pointer font-mono text-xs"
          onClick={() => navigate(`/dashboard/tds/subscriptions/${row.id}`)}
        >
          {row.id.slice(0, 8)}...
        </span>
      ),
    },
    {
      id: 'catalog_id',
      label: '目录ID',
      minWidth: 120,
      render: (row) => <span className="font-mono text-xs">{row.catalog_id.slice(0, 8)}...</span>,
    },
    { id: 'reason', label: '申请理由', minWidth: 200 },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={statusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    {
      id: 'expires_at',
      label: '过期时间',
      minWidth: 160,
      render: (row) => row.expires_at ? new Date(row.expires_at).toLocaleString('zh-CN') : '-',
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
        <div className="flex items-center gap-1 justify-center">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
              onClick={() => navigate(`/dashboard/tds/subscriptions/${row.id}`)}
            >
              <BrowseIcon size="16px" />
            </span>
          </Tooltip>
          {row.status === 'pending' && (
            <>
              <Tooltip content="审批通过">
                <span
                  className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-600"
                  onClick={() => approveMutation.mutate(row.id)}
                >
                  <CheckCircleFilledIcon size="16px" />
                </span>
              </Tooltip>
              <Tooltip content="驳回">
                <span
                  className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600"
                  onClick={() => rejectMutation.mutate(row.id)}
                >
                  <CloseIcon size="16px" />
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
        title="数据订阅管理"
        subtitle="管理数据资源的订阅申请和审批"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '数据订阅管理' },
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
                { label: '待审批', value: 'pending' },
                { label: '已通过', value: 'approved' },
                { label: '已驳回', value: 'rejected' },
                { label: '已过期', value: 'expired' },
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
