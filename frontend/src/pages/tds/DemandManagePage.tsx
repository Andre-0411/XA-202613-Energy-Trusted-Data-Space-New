/**
 * 需求管理页面
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Input, Select, Tag, Tooltip, Dialog, Textarea } from 'tdesign-react';
import { AddIcon, BrowseIcon, DeleteIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listDemands, createDemand, deleteDemand } from '@/api/demandManage';
import type { Demand } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'default' | 'warning' | 'danger'> = {
  open: 'success',
  claimed: 'default',
  closed: 'default',
  expired: 'danger',
};

export default function DemandManagePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newDemand, setNewDemand] = useState({
    title: '',
    demand_type: 'data_acquisition',
    description: '',
    budget_range: '',
    deadline: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['demands-manage', page, pageSize, statusFilter, typeFilter],
    queryFn: () => listDemands({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
      demand_type: typeFilter || undefined,
    }),
  });

  const createMutation = useMutation({
    mutationFn: createDemand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demands-manage'] });
      setCreateDialogOpen(false);
      setNewDemand({ title: '', demand_type: 'data_acquisition', description: '', budget_range: '', deadline: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDemand,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['demands-manage'] }),
  });

  const columns: Column<Demand>[] = [
    {
      id: 'title',
      label: '需求标题',
      minWidth: 250,
      render: (row) => (
        <span
          className="text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/demands/${row.id}`)}
        >
          {row.title}
        </span>
      ),
    },
    {
      id: 'demand_type',
      label: '类型',
      minWidth: 120,
      render: (row) => <Tag variant="outline">{row.demand_type}</Tag>,
    },
    {
      id: 'budget_range',
      label: '预算范围',
      minWidth: 120,
      render: (row) => row.budget_range || '-',
    },
    {
      id: 'deadline',
      label: '截止日期',
      minWidth: 120,
      render: (row) => row.deadline ? new Date(row.deadline).toLocaleDateString('zh-CN') : '-',
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={statusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    {
      id: 'created_at',
      label: '发布时间',
      minWidth: 160,
      render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions',
      label: '操作',
      minWidth: 120,
      align: 'center',
      render: (row) => (
        <div className="flex items-center gap-1 justify-center">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
              onClick={() => navigate(`/dashboard/tds/demands/${row.id}`)}
            >
              <BrowseIcon size="16px" />
            </span>
          </Tooltip>
          <Tooltip content="删除">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600"
              onClick={() => {
                if (confirm('确定要删除该需求吗？')) deleteMutation.mutate(row.id);
              }}
            >
              <DeleteIcon size="16px" />
            </span>
          </Tooltip>
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="需求管理"
        subtitle="发布和管理数据需求，对接数据供给方"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '需求管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            { name: 'keyword', type: 'text', placeholder: '搜索需求标题', width: 240 },
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 120,
              options: [
                { label: '全部', value: '' },
                { label: '开放', value: 'open' },
                { label: '已认领', value: 'claimed' },
                { label: '已关闭', value: 'closed' },
              ],
            },
            {
              name: 'type',
              type: 'select',
              placeholder: '类型',
              width: 120,
              options: [
                { label: '全部', value: '' },
                { label: '数据采集', value: 'data_acquisition' },
                { label: '数据分析', value: 'data_analysis' },
                { label: '算法需求', value: 'algorithm' },
                { label: '定制需求', value: 'custom' },
              ],
            },
          ]}
          values={{ keyword: '', status: statusFilter, type: typeFilter }}
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
            <Button theme="primary" icon={<AddIcon />} onClick={() => setCreateDialogOpen(true)}>
              发布需求
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

      <Dialog
        visible={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        header="发布需求"
        width="480px"
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={() => createMutation.mutate(newDemand)}
              disabled={!newDemand.title || !newDemand.description || createMutation.isPending}
            >
              {createMutation.isPending ? '发布中...' : '发布'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <p className="mb-1 text-sm">需求标题</p>
            <Input
              value={newDemand.title}
              onChange={(val) => setNewDemand({ ...newDemand, title: String(val) })}
            />
          </div>
          <div>
            <p className="mb-1 text-sm">需求类型</p>
            <Select
              value={newDemand.demand_type}
              onChange={(val) => setNewDemand({ ...newDemand, demand_type: String(val) })}
              options={[
                { label: '数据采集', value: 'data_acquisition' },
                { label: '数据分析', value: 'data_analysis' },
                { label: '算法需求', value: 'algorithm' },
                { label: '定制需求', value: 'custom' },
              ]}
            />
          </div>
          <div>
            <p className="mb-1 text-sm">需求描述</p>
            <Textarea
              value={newDemand.description}
              onChange={(val) => setNewDemand({ ...newDemand, description: val })}
              rows={4}
            />
          </div>
          <div>
            <p className="mb-1 text-sm">预算范围</p>
            <Input
              value={newDemand.budget_range}
              onChange={(val) => setNewDemand({ ...newDemand, budget_range: String(val) })}
            />
          </div>
          <div>
            <p className="mb-1 text-sm">截止日期</p>
            <Input
              placeholder="YYYY-MM-DD"
              value={newDemand.deadline}
              onChange={(val) => setNewDemand({ ...newDemand, deadline: String(val) })}
            />
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
}
