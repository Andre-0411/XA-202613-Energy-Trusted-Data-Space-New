/**
 * 连接器文件库页面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button, Input, Select, Tag, Tooltip, Dialog, Textarea, Tabs,
} from 'tdesign-react';
import {
  AddIcon, DeleteIcon, SearchIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import {
  listFileSets, createFileSet, deleteFileSet,
  listFiles, deleteFile,
  listApiProxies, createApiProxy, deleteApiProxy, testApiProxy,
} from '@/api/connectorFileManage';
import type { ConnectorFile, FileSet, ApiProxy } from '@/types/api';

const { TabPanel } = Tabs;

const fileTypeThemeMap: Record<string, 'success' | 'warning' | 'primary' | 'default'> = {
  csv: 'success',
  json: 'primary',
  xml: 'warning',
  pdf: 'default',
  parquet: 'success',
  xlsx: 'primary',
};

export default function ConnectorFilesPage() {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);

  // File sets
  const [fileSetPage, setFileSetPage] = useState(0);
  const [createSetDialogOpen, setCreateSetDialogOpen] = useState(false);
  const [newFileSet, setNewFileSet] = useState({ name: '', description: '' });

  const { data: fileSetsData, isLoading: loadingSets } = useQuery({
    queryKey: ['file-sets', fileSetPage],
    queryFn: () => listFileSets({ page: fileSetPage + 1, page_size: 20 }),
  });

  const createSetMutation = useMutation({
    mutationFn: createFileSet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['file-sets'] });
      setCreateSetDialogOpen(false);
      setNewFileSet({ name: '', description: '' });
    },
  });

  const deleteSetMutation = useMutation({
    mutationFn: deleteFileSet,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['file-sets'] }),
  });

  // Files
  const [filePage, setFilePage] = useState(0);
  const [fileTypeFilter, setFileTypeFilter] = useState('');

  const { data: filesData, isLoading: loadingFiles } = useQuery({
    queryKey: ['connector-files', filePage, fileTypeFilter],
    queryFn: () => listFiles({ page: filePage + 1, page_size: 20, file_type: fileTypeFilter || undefined }),
  });

  const deleteFileMutation = useMutation({
    mutationFn: deleteFile,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connector-files'] }),
  });

  // API Proxies
  const [proxyPage, setProxyPage] = useState(0);
  const [createProxyDialogOpen, setCreateProxyDialogOpen] = useState(false);
  const [newProxy, setNewProxy] = useState({
    connector_id: '',
    name: '',
    target_url: '',
    http_method: 'GET' as 'GET' | 'POST' | 'PUT' | 'DELETE',
    description: '',
  });

  const { data: proxiesData, isLoading: loadingProxies } = useQuery({
    queryKey: ['api-proxies', proxyPage],
    queryFn: () => listApiProxies({ page: proxyPage + 1, page_size: 20 }),
  });

  const createProxyMutation = useMutation({
    mutationFn: createApiProxy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-proxies'] });
      setCreateProxyDialogOpen(false);
      setNewProxy({ connector_id: '', name: '', target_url: '', http_method: 'GET', description: '' });
    },
  });

  const deleteProxyMutation = useMutation({
    mutationFn: deleteApiProxy,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-proxies'] }),
  });

  const testProxyMutation = useMutation({
    mutationFn: testApiProxy,
  });

  const fileSetColumns: Column<FileSet>[] = [
    { id: 'name', label: '文件集名称', minWidth: 200 },
    { id: 'description', label: '描述', minWidth: 250, render: (row) => row.description || '-' },
    { id: 'status', label: '状态', minWidth: 100, render: (row) => <Tag>{row.status}</Tag> },
    { id: 'created_at', label: '创建时间', minWidth: 160, render: (row) => new Date(row.created_at).toLocaleString('zh-CN') },
    {
      id: 'actions',
      label: '操作',
      minWidth: 80,
      align: 'center',
      render: (row) => (
        <Tooltip content="删除">
          <span
            className="cursor-pointer hover:bg-red-50 rounded p-1 text-red-500"
            onClick={() => {
              if (confirm('确定要删除该文件集吗？')) deleteSetMutation.mutate(row.id);
            }}
          >
            <DeleteIcon size="16px" />
          </span>
        </Tooltip>
      ),
    },
  ];

  const fileColumns: Column<ConnectorFile>[] = [
    { id: 'file_name', label: '文件名', minWidth: 200 },
    {
      id: 'file_type',
      label: '类型',
      minWidth: 80,
      render: (row) => <Tag variant="outline" theme={fileTypeThemeMap[row.file_type] || 'default'}>{row.file_type}</Tag>,
    },
    {
      id: 'file_size_bytes',
      label: '大小',
      minWidth: 100,
      render: (row) => {
        const kb = row.file_size_bytes / 1024;
        return kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(1)} KB`;
      },
    },
    { id: 'row_count', label: '行数', minWidth: 80, render: (row) => row.row_count ?? '-' },
    { id: 'status', label: '状态', minWidth: 80, render: (row) => <Tag>{row.status}</Tag> },
    { id: 'created_at', label: '上传时间', minWidth: 160, render: (row) => new Date(row.created_at).toLocaleString('zh-CN') },
    {
      id: 'actions',
      label: '操作',
      minWidth: 100,
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="删除">
            <span
              className="cursor-pointer hover:bg-red-50 rounded p-1 text-red-500"
              onClick={() => {
                if (confirm('确定要删除该文件吗？')) deleteFileMutation.mutate(row.id);
              }}
            >
              <DeleteIcon size="16px" />
            </span>
          </Tooltip>
        </div>
      ),
    },
  ];

  const proxyColumns: Column<ApiProxy>[] = [
    { id: 'name', label: '代理名称', minWidth: 180 },
    { id: 'http_method', label: '方法', minWidth: 80, render: (row) => <Tag variant="outline">{row.http_method}</Tag> },
    { id: 'target_url', label: '目标URL', minWidth: 250, render: (row) => <span className="text-xs text-gray-700 truncate block max-w-[250px]">{row.target_url}</span> },
    { id: 'is_enabled', label: '启用', minWidth: 80, render: (row) => <Tag theme={row.is_enabled ? 'success' : 'default'}>{row.is_enabled ? '是' : '否'}</Tag> },
    { id: 'status', label: '状态', minWidth: 80, render: (row) => <Tag>{row.status}</Tag> },
    {
      id: 'actions',
      label: '操作',
      minWidth: 120,
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="测试">
            <span
              className="cursor-pointer hover:bg-blue-50 rounded p-1 text-blue-500"
              onClick={() => testProxyMutation.mutate(row.id)}
            >
              <SearchIcon size="16px" />
            </span>
          </Tooltip>
          <Tooltip content="删除">
            <span
              className="cursor-pointer hover:bg-red-50 rounded p-1 text-red-500"
              onClick={() => {
                if (confirm('确定要删除该API代理吗？')) deleteProxyMutation.mutate(row.id);
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
        title="连接器文件库"
        subtitle="管理文件集、文件和API代理"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '连接器文件库' },
        ]}
      />

      <Tabs value={tabValue} onChange={(val) => setTabValue(val as number)}>
        <TabPanel value={0} label="文件集">
          <PageSection className="mt-2">
            <div className="flex justify-end mb-4">
              <Button theme="primary" icon={<AddIcon />} onClick={() => setCreateSetDialogOpen(true)}>
                创建文件集
              </Button>
            </div>
            <DataTable
              columns={fileSetColumns}
              rows={fileSetsData?.data?.items || []}
              loading={loadingSets}
              page={fileSetPage}
              pageSize={20}
              total={fileSetsData?.data?.total || 0}
              onPageChange={setFileSetPage}
              onPageSizeChange={() => {}}
            />
          </PageSection>
        </TabPanel>

        <TabPanel value={1} label="文件">
          <PageSection className="mt-2">
            <div className="mb-4">
              <FilterBar
                fields={[
                  {
                    name: 'fileType',
                    type: 'select',
                    placeholder: '文件类型',
                    width: 120,
                    options: [
                      { value: '', label: '全部' },
                      { value: 'csv', label: 'CSV' },
                      { value: 'json', label: 'JSON' },
                      { value: 'xml', label: 'XML' },
                      { value: 'pdf', label: 'PDF' },
                      { value: 'parquet', label: 'Parquet' },
                      { value: 'xlsx', label: 'XLSX' },
                    ],
                  },
                ]}
                values={{ fileType: fileTypeFilter }}
                onChange={(name, value) => {
                  if (name === 'fileType') setFileTypeFilter(String(value));
                }}
                onSearch={() => setFilePage(0)}
                onReset={() => {
                  setFileTypeFilter('');
                  setFilePage(0);
                }}
              />
            </div>
            <DataTable
              columns={fileColumns}
              rows={filesData?.data?.items || []}
              loading={loadingFiles}
              page={filePage}
              pageSize={20}
              total={filesData?.data?.total || 0}
              onPageChange={setFilePage}
              onPageSizeChange={() => {}}
            />
          </PageSection>
        </TabPanel>

        <TabPanel value={2} label="API代理">
          <PageSection className="mt-2">
            <div className="flex justify-end mb-4">
              <Button theme="primary" icon={<AddIcon />} onClick={() => setCreateProxyDialogOpen(true)}>
                创建API代理
              </Button>
            </div>
            <DataTable
              columns={proxyColumns}
              rows={proxiesData?.data?.items || []}
              loading={loadingProxies}
              page={proxyPage}
              pageSize={20}
              total={proxiesData?.data?.total || 0}
              onPageChange={setProxyPage}
              onPageSizeChange={() => {}}
            />
          </PageSection>
        </TabPanel>
      </Tabs>

      {/* 创建文件集对话框 */}
      <Dialog
        header="创建文件集"
        visible={createSetDialogOpen}
        onClose={() => setCreateSetDialogOpen(false)}
        width="480px"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateSetDialogOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={() => createSetMutation.mutate(newFileSet)}
              disabled={!newFileSet.name || createSetMutation.isPending}
            >
              {createSetMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="文件集名称"
            value={newFileSet.name}
            onChange={(val) => setNewFileSet({ ...newFileSet, name: String(val) })}
          />
          <div>
            <span className="text-xs text-gray-500 block mb-1">描述</span>
            <Textarea
              value={newFileSet.description}
              onChange={(val) => setNewFileSet({ ...newFileSet, description: val })}
              rows={3}
            />
          </div>
        </div>
      </Dialog>

      {/* 创建API代理对话框 */}
      <Dialog
        header="创建API代理"
        visible={createProxyDialogOpen}
        onClose={() => setCreateProxyDialogOpen(false)}
        width="480px"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateProxyDialogOpen(false)}>取消</Button>
            <Button
              theme="primary"
              onClick={() => createProxyMutation.mutate(newProxy)}
              disabled={!newProxy.connector_id || !newProxy.name || !newProxy.target_url || createProxyMutation.isPending}
            >
              {createProxyMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="连接器ID"
            value={newProxy.connector_id}
            onChange={(val) => setNewProxy({ ...newProxy, connector_id: String(val) })}
          />
          <Input
            label="代理名称"
            value={newProxy.name}
            onChange={(val) => setNewProxy({ ...newProxy, name: String(val) })}
          />
          <Input
            label="目标URL"
            value={newProxy.target_url}
            onChange={(val) => setNewProxy({ ...newProxy, target_url: String(val) })}
          />
          <Select
            label="HTTP方法"
            value={newProxy.http_method}
            onChange={(val) => setNewProxy({ ...newProxy, http_method: val as 'GET' | 'POST' | 'PUT' | 'DELETE' })}
            options={[
              { value: 'GET', label: 'GET' },
              { value: 'POST', label: 'POST' },
              { value: 'PUT', label: 'PUT' },
              { value: 'DELETE', label: 'DELETE' },
            ]}
          />
          <div>
            <span className="text-xs text-gray-500 block mb-1">描述</span>
            <Textarea
              value={newProxy.description}
              onChange={(val) => setNewProxy({ ...newProxy, description: val })}
              rows={2}
            />
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
}
