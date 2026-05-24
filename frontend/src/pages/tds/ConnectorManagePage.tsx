/**
 * 连接器管理页面
 * 展示连接器列表、支持筛选、注册、状态监控
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button, Input, Select, Tag, Tooltip, Dialog,
} from 'tdesign-react';
import {
  AddIcon, DeleteIcon, BrowseIcon, RefreshIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import { listManagedConnectors, registerConnector, deregisterConnector } from '@/api/connectorManage';
import type { Connector } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  online: 'success',
  offline: 'danger',
  connecting: 'warning',
  maintenance: 'default',
};

export default function ConnectorManagePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newConnector, setNewConnector] = useState({
    name: '',
    connector_type: 'database',
    version: '1.0.0',
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['connectors-manage', page, pageSize, keyword, statusFilter, typeFilter],
    queryFn: () => listManagedConnectors({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
      connector_type: typeFilter || undefined,
    }),
  });

  const createMutation = useMutation({
    mutationFn: registerConnector,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors-manage'] });
      setCreateDialogOpen(false);
      setNewConnector({ name: '', connector_type: 'database', version: '1.0.0' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deregisterConnector,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors-manage'] });
    },
  });

  const columns: Column<Connector>[] = [
    {
      id: 'name',
      label: '连接器名称',
      minWidth: 200,
      render: (row) => (
        <span
          className="text-sm text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/connectors/${row.id}`)}
        >
          {row.name}
        </span>
      ),
    },
    {
      id: 'connector_type',
      label: '类型',
      minWidth: 120,
      render: (row) => <Tag variant="outline">{row.connector_type}</Tag>,
    },
    { id: 'version', label: '版本', minWidth: 80 },
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
      id: 'last_heartbeat_at',
      label: '最后心跳',
      minWidth: 160,
      render: (row) => row.last_heartbeat_at
        ? new Date(row.last_heartbeat_at).toLocaleString('zh-CN')
        : '-',
    },
    {
      id: 'created_at',
      label: '注册时间',
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
              onClick={() => navigate(`/dashboard/tds/connectors/${row.id}`)}
            >
              <BrowseIcon size="16px" />
            </span>
          </Tooltip>
          <Tooltip content="删除">
            <span
              className="cursor-pointer hover:bg-red-50 rounded p-1 text-red-500"
              onClick={() => {
                if (confirm('确定要注销该连接器吗？')) {
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
        title="连接器管理"
        subtitle="管理数据空间连接器的注册、状态和配置"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '连接器管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            { name: 'keyword', type: 'text', placeholder: '搜索连接器名称', width: 240 },
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 120,
              options: [
                { value: '', label: '全部' },
                { value: 'online', label: '在线' },
                { value: 'offline', label: '离线' },
                { value: 'connecting', label: '连接中' },
                { value: 'maintenance', label: '维护中' },
              ],
            },
            {
              name: 'type',
              type: 'select',
              placeholder: '类型',
              width: 120,
              options: [
                { value: '', label: '全部' },
                { value: 'database', label: '数据库' },
                { value: 'api', label: 'API' },
                { value: 'file', label: '文件' },
                { value: 'mqtt', label: 'MQTT' },
              ],
            },
          ]}
          values={{ keyword, status: statusFilter, type: typeFilter }}
          onChange={(name, value) => {
            if (name === 'keyword') setKeyword(String(value));
            if (name === 'status') setStatusFilter(String(value));
            if (name === 'type') setTypeFilter(String(value));
          }}
          onSearch={() => setPage(0)}
          onReset={() => {
            setKeyword('');
            setStatusFilter('');
            setTypeFilter('');
            setPage(0);
          }}
          extra={
            <div className="flex items-center gap-2">
              <Button icon={<RefreshIcon />} onClick={() => refetch()}>
                刷新
              </Button>
              <Button
                theme="primary"
                icon={<AddIcon />}
                onClick={() => setCreateDialogOpen(true)}
              >
                注册连接器
              </Button>
            </div>
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
        header="注册连接器"
        visible={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        width="480px"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateDialogOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={() => createMutation.mutate(newConnector)}
              disabled={!newConnector.name || createMutation.isPending}
            >
              {createMutation.isPending ? '注册中...' : '注册'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="连接器名称"
            value={newConnector.name}
            onChange={(val) => setNewConnector({ ...newConnector, name: String(val) })}
          />
          <Select
            label="连接器类型"
            value={newConnector.connector_type}
            onChange={(val) => setNewConnector({ ...newConnector, connector_type: String(val) })}
            options={[
              { value: 'database', label: '数据库' },
              { value: 'api', label: 'API' },
              { value: 'file', label: '文件' },
              { value: 'mqtt', label: 'MQTT' },
            ]}
          />
          <Input
            label="版本"
            value={newConnector.version}
            onChange={(val) => setNewConnector({ ...newConnector, version: String(val) })}
          />
        </div>
      </Dialog>
    </PageContainer>
  );
}
