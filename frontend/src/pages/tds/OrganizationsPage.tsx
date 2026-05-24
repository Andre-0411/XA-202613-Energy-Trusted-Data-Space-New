/**
 * 机构管理页面
 * 展示机构列表、支持筛选、创建、编辑操作
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button, Input, Select, Tag, Tooltip, Dialog,
} from 'tdesign-react';
import {
  AddIcon, EditIcon, DeleteIcon, BrowseIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listOrganizations, createOrganization, deleteOrganization } from '@/api/orgManagement';
import type { Organization } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  active: 'success',
  pending: 'warning',
  disabled: 'danger',
};

export default function OrganizationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newOrg, setNewOrg] = useState({ name: '', code: '', level: 1 });

  const { data, isLoading } = useQuery({
    queryKey: ['organizations', page, pageSize, keyword, statusFilter],
    queryFn: () => listOrganizations({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
    }),
  });

  const createMutation = useMutation({
    mutationFn: createOrganization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      setCreateDialogOpen(false);
      setNewOrg({ name: '', code: '', level: 1 });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteOrganization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
    },
  });

  const columns: Column<Organization>[] = [
    {
      id: 'name',
      label: '机构名称',
      minWidth: 200,
      render: (row) => (
        <span
          className="text-sm text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/organizations/${row.id}`)}
        >
          {row.name}
        </span>
      ),
    },
    { id: 'code', label: '机构编码', minWidth: 120 },
    {
      id: 'level',
      label: '层级',
      minWidth: 80,
      render: (row) => <Tag variant="outline">{`L${row.level}`}</Tag>,
    },
    {
      id: 'did',
      label: 'DID',
      minWidth: 200,
      render: (row) => (
        <span className="text-xs font-mono text-gray-600">
          {row.did || '-'}
        </span>
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
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1"
              onClick={() => navigate(`/dashboard/tds/organizations/${row.id}`)}
            >
              <BrowseIcon size="16px" />
            </span>
          </Tooltip>
          <Tooltip content="编辑">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1"
              onClick={() => navigate(`/dashboard/tds/organizations/${row.id}?edit=true`)}
            >
              <EditIcon size="16px" />
            </span>
          </Tooltip>
          <Tooltip content="删除">
            <span
              className="cursor-pointer hover:bg-red-50 rounded p-1 text-red-500"
              onClick={() => {
                if (confirm('确定要删除该机构吗？')) {
                  deleteMutation.mutate(row.id);
                }
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
        title="机构管理"
        subtitle="管理可信数据空间中的参与机构"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '机构管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            { name: 'keyword', type: 'text', placeholder: '搜索机构名称或编码', width: 280 },
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 120,
              options: [
                { value: '', label: '全部' },
                { value: 'active', label: '活跃' },
                { value: 'pending', label: '待审核' },
                { value: 'disabled', label: '已禁用' },
              ],
            },
          ]}
          values={{ keyword, status: statusFilter }}
          onChange={(name, value) => {
            if (name === 'keyword') setKeyword(String(value));
            if (name === 'status') setStatusFilter(String(value));
          }}
          onSearch={() => setPage(0)}
          onReset={() => {
            setKeyword('');
            setStatusFilter('');
            setPage(0);
          }}
          extra={
            <Button
              theme="primary"
              icon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              新建机构
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
        header="新建机构"
        visible={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        width="480px"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateDialogOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={() => createMutation.mutate(newOrg)}
              disabled={!newOrg.name || !newOrg.code || createMutation.isPending}
            >
              {createMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="机构名称"
            value={newOrg.name}
            onChange={(val) => setNewOrg({ ...newOrg, name: String(val) })}
          />
          <Input
            label="机构编码"
            value={newOrg.code}
            onChange={(val) => setNewOrg({ ...newOrg, code: String(val) })}
          />
          <Select
            label="层级"
            value={newOrg.level}
            onChange={(val) => setNewOrg({ ...newOrg, level: Number(val) })}
            options={[
              { value: 1, label: 'L1 - 省级' },
              { value: 2, label: 'L2 - 市级' },
              { value: 3, label: 'L3 - 区县级' },
            ]}
          />
        </div>
      </Dialog>
    </PageContainer>
  );
}
