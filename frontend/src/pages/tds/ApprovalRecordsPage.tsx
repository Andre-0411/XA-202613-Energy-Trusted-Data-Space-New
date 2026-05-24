/**
 * 审批记录页面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Input, Select, Tag, Tooltip, Dialog, Tabs, Textarea } from 'tdesign-react';
import { CheckCircleFilledIcon, CloseIcon, CloseCircleFilledIcon, SearchIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import {
  listApprovalRecords, listMyPendingApprovals, listMyApplications,
  approveRecord, rejectRecord, cancelRecord,
} from '@/api/workflowManage';
import type { ApprovalRecord } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  pending: 'warning',
  in_progress: 'default',
  approved: 'success',
  rejected: 'danger',
  cancelled: 'default',
};

const businessTypeMap: Record<string, string> = {
  certification: '机构认证',
  subscription: '数据订阅',
  product_publish: '产品上架',
  product_unpublish: '产品下架',
  demand_claim: '需求认领',
  contract: '合约审批',
};

export default function ApprovalRecordsPage() {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState('0');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const { data: allData, isLoading: loadingAll } = useQuery({
    queryKey: ['approval-records', page, pageSize, statusFilter, typeFilter],
    queryFn: () => listApprovalRecords({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
      business_type: typeFilter || undefined,
    }),
    enabled: tabValue === '0',
  });

  const { data: pendingData, isLoading: loadingPending } = useQuery({
    queryKey: ['my-pending-approvals', page, pageSize],
    queryFn: () => listMyPendingApprovals({ page: page + 1, page_size: pageSize }),
    enabled: tabValue === '1',
  });

  const { data: appsData, isLoading: loadingApps } = useQuery({
    queryKey: ['my-applications', page, pageSize, statusFilter],
    queryFn: () => listMyApplications({ page: page + 1, page_size: pageSize, status: statusFilter || undefined }),
    enabled: tabValue === '2',
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => approveRecord(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-records'] });
      queryClient.invalidateQueries({ queryKey: ['my-pending-approvals'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => rejectRecord(id, { reject_reason: reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-records'] });
      queryClient.invalidateQueries({ queryKey: ['my-pending-approvals'] });
      setRejectDialogOpen(false);
      setRejectTarget(null);
      setRejectReason('');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelRecord,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-records'] });
      queryClient.invalidateQueries({ queryKey: ['my-applications'] });
    },
  });

  const currentData = tabValue === '0' ? allData : tabValue === '1' ? pendingData : appsData;
  const currentLoading = tabValue === '0' ? loadingAll : tabValue === '1' ? loadingPending : loadingApps;

  const columns: Column<ApprovalRecord>[] = [
    {
      id: 'business_type',
      label: '业务类型',
      minWidth: 120,
      render: (row) => <Tag variant="outline">{businessTypeMap[row.business_type] || row.business_type}</Tag>,
    },
    {
      id: 'business_id',
      label: '业务ID',
      minWidth: 200,
      render: (row) => <span className="text-sm truncate block max-w-[200px]">{row.business_id}</span>,
    },
    {
      id: 'progress',
      label: '审批进度',
      minWidth: 120,
      render: (row) => (
        <div className="flex items-center gap-1">
          <span className="text-sm">{row.current_step}</span>
          <span className="text-sm text-gray-400">/</span>
          <span className="text-sm">{row.total_steps}</span>
        </div>
      ),
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={statusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    {
      id: 'approved_by',
      label: '审批人',
      minWidth: 120,
      render: (row) => row.approved_by || '-',
    },
    {
      id: 'reject_reason',
      label: '驳回原因',
      minWidth: 150,
      render: (row) => row.reject_reason ? (
        <Tooltip content={row.reject_reason}>
          <span className="text-sm text-red-600 truncate block max-w-[150px]">{row.reject_reason}</span>
        </Tooltip>
      ) : '-',
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
      minWidth: 140,
      align: 'center',
      render: (row) => (
        <div className="flex items-center gap-1 justify-center">
          {tabValue === '1' && row.status === 'pending' && (
            <>
              <Tooltip content="通过">
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
                  onClick={() => {
                    setRejectTarget(row.id);
                    setRejectDialogOpen(true);
                  }}
                >
                  <CloseIcon size="16px" />
                </span>
              </Tooltip>
            </>
          )}
          {tabValue === '2' && (row.status === 'pending' || row.status === 'in_progress') && (
            <Tooltip content="撤回">
              <span
                className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-orange-600"
                onClick={() => {
                  if (confirm('确定要撤回该申请吗？')) cancelMutation.mutate(row.id);
                }}
              >
                <CloseCircleFilledIcon size="16px" />
              </span>
            </Tooltip>
          )}
        </div>
      ),
    },
  ];

  const handleTabChange = (val: string) => {
    setTabValue(val);
    setPage(0);
  };

  return (
    <PageContainer>
      <PageHeader
        title="审批记录"
        subtitle="查看和管理所有审批流程"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '审批记录' },
        ]}
      />

      <PageSection padding="none">
        <Tabs
          value={tabValue}
          onChange={(val) => handleTabChange(String(val))}
          className="border-b border-gray-200"
        >
          <Tabs.TabPanel label="全部记录" value="0" />
          <Tabs.TabPanel label="待我审批" value="1" />
          <Tabs.TabPanel label="我的申请" value="2" />
        </Tabs>

        <div className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Input
              placeholder="搜索业务ID"
              prefixIcon={<SearchIcon />}
              style={{ minWidth: 200 }}
            />
            {tabValue !== '1' && (
              <Select
                value={statusFilter}
                onChange={(val) => setStatusFilter(String(val))}
                options={[
                  { label: '全部', value: '' },
                  { label: '待审批', value: 'pending' },
                  { label: '审批中', value: 'in_progress' },
                  { label: '已通过', value: 'approved' },
                  { label: '已驳回', value: 'rejected' },
                  { label: '已撤回', value: 'cancelled' },
                ]}
                style={{ minWidth: 100 }}
              />
            )}
            {tabValue === '0' && (
              <Select
                value={typeFilter}
                onChange={(val) => setTypeFilter(String(val))}
                options={[
                  { label: '全部', value: '' },
                  { label: '机构认证', value: 'certification' },
                  { label: '数据订阅', value: 'subscription' },
                  { label: '产品上架', value: 'product_publish' },
                  { label: '需求认领', value: 'demand_claim' },
                  { label: '合约审批', value: 'contract' },
                ]}
                style={{ minWidth: 120 }}
              />
            )}
          </div>

          <DataTable
            columns={columns}
            rows={currentData?.data?.items || []}
            loading={currentLoading}
            page={page}
            pageSize={pageSize}
            total={currentData?.data?.total || 0}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </div>
      </PageSection>

      <Dialog
        visible={rejectDialogOpen}
        onClose={() => setRejectDialogOpen(false)}
        header="驳回审批"
        width="480px"
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>取消</Button>
            <Button
              theme="danger"
              onClick={() => {
                if (rejectTarget) rejectMutation.mutate({ id: rejectTarget, reason: rejectReason });
              }}
              disabled={!rejectReason || rejectMutation.isPending}
            >
              {rejectMutation.isPending ? '驳回中...' : '确认驳回'}
            </Button>
          </div>
        }
      >
        <div className="mt-1">
          <p className="mb-1 text-sm">驳回原因</p>
          <Textarea
            value={rejectReason}
            onChange={(val) => setRejectReason(val)}
            rows={3}
          />
        </div>
      </Dialog>
    </PageContainer>
  );
}
