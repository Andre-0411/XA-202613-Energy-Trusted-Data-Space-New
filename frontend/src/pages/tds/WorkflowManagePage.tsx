/**
 * 工作流管理页面
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
import { listWorkflows, deleteWorkflow } from '@/api/workflowManage';
import type { ApprovalWorkflow } from '@/types/api';

const workflowTypeMap: Record<string, string> = {
  certification: '认证审核',
  subscription: '订阅审批',
  product_publish: '产品上架',
  product_unpublish: '产品下架',
  demand_claim: '需求认领',
  contract: '合约审批',
};

export default function WorkflowManagePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['workflows-manage', page, pageSize, typeFilter, statusFilter],
    queryFn: () => listWorkflows({
      page: page + 1,
      page_size: pageSize,
      workflow_type: typeFilter || undefined,
      status: statusFilter || undefined,
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWorkflow,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows-manage'] }),
  });

  const columns: Column<ApprovalWorkflow>[] = [
    {
      id: 'name',
      label: '工作流名称',
      minWidth: 200,
      render: (row) => (
        <span
          className="text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/workflows/${row.id}`)}
        >
          {row.name}
        </span>
      ),
    },
    {
      id: 'workflow_type',
      label: '类型',
      minWidth: 120,
      render: (row) => (
        <Tag variant="outline" theme="default">
          {workflowTypeMap[row.workflow_type] || row.workflow_type}
        </Tag>
      ),
    },
    {
      id: 'steps',
      label: '步骤数',
      minWidth: 80,
      render: (row) => <span className="text-sm">{row.steps?.length || 0} 步</span>,
    },
    {
      id: 'is_system',
      label: '系统预设',
      minWidth: 100,
      render: (row) => <Tag variant="outline" theme={row.is_system ? 'primary' : 'default'}>{row.is_system ? '是' : '否'}</Tag>,
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 80,
      render: (row) => <Tag theme={row.status === 'active' ? 'success' : 'default'}>{row.status}</Tag>,
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
      minWidth: 100,
      align: 'center',
      render: (row) => (
        <div className="flex items-center gap-1 justify-center">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
              onClick={() => navigate(`/dashboard/tds/workflows/${row.id}`)}
            >
              <BrowseIcon size="16px" />
            </span>
          </Tooltip>
          {!row.is_system && (
            <Tooltip content="删除">
              <span
                className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600"
                onClick={() => {
                  if (confirm('确定要删除该工作流吗？')) deleteMutation.mutate(row.id);
                }}
              >
                <DeleteIcon size="16px" />
              </span>
            </Tooltip>
          )}
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="工作流管理"
        subtitle="管理审批工作流模板和审批记录"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '工作流管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            { name: 'keyword', type: 'text', placeholder: '搜索工作流名称', width: 240 },
            {
              name: 'type',
              type: 'select',
              placeholder: '类型',
              width: 140,
              options: [
                { label: '全部', value: '' },
                { label: '认证审核', value: 'certification' },
                { label: '订阅审批', value: 'subscription' },
                { label: '产品上架', value: 'product_publish' },
                { label: '产品下架', value: 'product_unpublish' },
                { label: '需求认领', value: 'demand_claim' },
                { label: '合约审批', value: 'contract' },
              ],
            },
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 100,
              options: [
                { label: '全部', value: '' },
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ],
            },
          ]}
          values={{ keyword: '', type: typeFilter, status: statusFilter }}
          onChange={(name, value) => {
            if (name === 'type') setTypeFilter(String(value));
            if (name === 'status') setStatusFilter(String(value));
          }}
          onSearch={() => setPage(0)}
          onReset={() => {
            setTypeFilter('');
            setStatusFilter('');
            setPage(0);
          }}
          extra={
            <Button theme="primary" icon={<AddIcon />} onClick={() => navigate('/dashboard/tds/workflows/new')}>
              创建工作流
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
