/**
 * 合约管理页面
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Input, Select, Tag, Tooltip, Dialog, Textarea } from 'tdesign-react';
import {
  AddIcon, BrowseIcon, DeleteIcon,
  SendIcon as SubmitIcon,
  CheckCircleFilledIcon as ActivateIcon,
  CloseCircleFilledIcon as TerminateIcon,
  LinkIcon as ChainIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import FilterBar from '@/components/common/FilterBar';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import {
  listContracts, createContract, deleteContract,
  submitContractForReview, activateContract, terminateContract,
  anchorContractOnChain,
} from '@/api/contractManage';
import type { Contract } from '@/types/api';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default' | 'primary'> = {
  draft: 'default',
  pending_review: 'warning',
  active: 'success',
  expired: 'danger',
  terminated: 'danger',
};

const contractTypeMap: Record<string, string> = {
  data_subscription: '数据订阅',
  product_subscription: '产品订阅',
  joint_compute: '联合计算',
  custom: '自定义',
};

export default function ContractManagePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newContract, setNewContract] = useState({
    title: '',
    contract_type: 'data_subscription',
    party_a_org_id: '',
    party_b_org_id: '',
    content: '',
    effective_date: '',
    expiration_date: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['contracts-manage', page, pageSize, statusFilter, typeFilter],
    queryFn: () => listContracts({
      page: page + 1,
      page_size: pageSize,
      status: statusFilter || undefined,
      contract_type: typeFilter || undefined,
    }),
  });

  const createMutation = useMutation({
    mutationFn: createContract,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts-manage'] });
      setCreateDialogOpen(false);
      setNewContract({ title: '', contract_type: 'data_subscription', party_a_org_id: '', party_b_org_id: '', content: '', effective_date: '', expiration_date: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteContract,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contracts-manage'] }),
  });

  const submitMutation = useMutation({
    mutationFn: submitContractForReview,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contracts-manage'] }),
  });

  const activateMutation = useMutation({
    mutationFn: activateContract,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contracts-manage'] }),
  });

  const terminateMutation = useMutation({
    mutationFn: (id: string) => terminateContract(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contracts-manage'] }),
  });

  const anchorMutation = useMutation({
    mutationFn: anchorContractOnChain,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contracts-manage'] }),
  });

  const columns: Column<Contract>[] = [
    {
      id: 'contract_no',
      label: '合约编号',
      minWidth: 160,
      render: (row) => (
        <span
          className="text-sm text-blue-600 cursor-pointer hover:underline"
          onClick={() => navigate(`/dashboard/tds/contracts/${row.id}`)}
        >
          {row.contract_no}
        </span>
      ),
    },
    { id: 'title', label: '合约标题', minWidth: 200 },
    {
      id: 'contract_type',
      label: '合约类型',
      minWidth: 120,
      render: (row) => <Tag variant="outline">{contractTypeMap[row.contract_type] || row.contract_type}</Tag>,
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 100,
      render: (row) => <Tag theme={statusThemeMap[row.status] || 'default'}>{row.status}</Tag>,
    },
    {
      id: 'blockchain_tx_hash',
      label: '链上存证',
      minWidth: 100,
      render: (row) => row.blockchain_tx_hash
        ? <Tag theme="success" variant="outline">已存证</Tag>
        : <Tag variant="outline">未存证</Tag>,
    },
    {
      id: 'effective_date',
      label: '生效日期',
      minWidth: 120,
      render: (row) => row.effective_date ? new Date(row.effective_date).toLocaleDateString('zh-CN') : '-',
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
      minWidth: 200,
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => navigate(`/dashboard/tds/contracts/${row.id}`)}>
              <BrowseIcon />
            </span>
          </Tooltip>
          {row.status === 'draft' && (
            <>
              <Tooltip content="提交审核">
                <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => submitMutation.mutate(row.id)}>
                  <SubmitIcon />
                </span>
              </Tooltip>
              <Tooltip content="删除">
                <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-600" onClick={() => {
                  if (confirm('确定要删除该合约吗？')) deleteMutation.mutate(row.id);
                }}>
                  <DeleteIcon />
                </span>
              </Tooltip>
            </>
          )}
          {row.status === 'pending_review' && (
            <>
              <Tooltip content="激活">
                <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-600" onClick={() => activateMutation.mutate(row.id)}>
                  <ActivateIcon />
                </span>
              </Tooltip>
              <Tooltip content="终止">
                <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-orange-600" onClick={() => {
                  if (confirm('确定要终止该合约吗？')) terminateMutation.mutate(row.id);
                }}>
                  <TerminateIcon />
                </span>
              </Tooltip>
            </>
          )}
          {row.status === 'active' && !row.blockchain_tx_hash && (
            <Tooltip content="上链存证">
              <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-600" onClick={() => anchorMutation.mutate(row.id)}>
                <ChainIcon />
              </span>
            </Tooltip>
          )}
        </div>
      ),
    },
  ];

  const contractTypeOptions = [
    { label: '数据订阅', value: 'data_subscription' },
    { label: '产品订阅', value: 'product_subscription' },
    { label: '联合计算', value: 'joint_compute' },
    { label: '自定义', value: 'custom' },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="合约管理"
        subtitle="创建和管理数据合约，支持区块链存证"
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '合约管理' },
        ]}
      />

      <PageSection>
        <FilterBar
          fields={[
            { name: 'keyword', type: 'text', placeholder: '搜索合约编号/标题', width: 240 },
            {
              name: 'status',
              type: 'select',
              placeholder: '状态',
              width: 120,
              options: [
                { label: '全部', value: '' },
                { label: '草稿', value: 'draft' },
                { label: '待审核', value: 'pending_review' },
                { label: '生效', value: 'active' },
                { label: '已过期', value: 'expired' },
                { label: '已终止', value: 'terminated' },
              ],
            },
            {
              name: 'type',
              type: 'select',
              placeholder: '合约类型',
              width: 120,
              options: [
                { label: '全部', value: '' },
                ...contractTypeOptions,
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
            <Button
              theme="primary"
              icon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              创建合约
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
        header="创建合约"
        visible={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        width="480px"
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">合约标题</label>
            <Input
              value={newContract.title}
              onChange={(val) => setNewContract({ ...newContract, title: String(val) })}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">合约类型</label>
            <Select
              value={newContract.contract_type}
              onChange={(val) => setNewContract({ ...newContract, contract_type: String(val) })}
              options={contractTypeOptions}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">甲方机构ID</label>
            <Input
              value={newContract.party_a_org_id}
              onChange={(val) => setNewContract({ ...newContract, party_a_org_id: String(val) })}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">乙方机构ID</label>
            <Input
              value={newContract.party_b_org_id}
              onChange={(val) => setNewContract({ ...newContract, party_b_org_id: String(val) })}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">合约内容</label>
            <Textarea
              value={newContract.content}
              onChange={(val) => setNewContract({ ...newContract, content: val })}
              rows={4}
            />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm text-gray-600 mb-1">生效日期</label>
              <Input
                placeholder="YYYY-MM-DD"
                value={newContract.effective_date}
                onChange={(val) => setNewContract({ ...newContract, effective_date: String(val) })}
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm text-gray-600 mb-1">到期日期</label>
              <Input
                placeholder="YYYY-MM-DD"
                value={newContract.expiration_date}
                onChange={(val) => setNewContract({ ...newContract, expiration_date: String(val) })}
              />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={() => setCreateDialogOpen(false)}>取消</Button>
          <Button
            theme="primary"
            onClick={() => createMutation.mutate(newContract)}
            disabled={!newContract.title || !newContract.content || createMutation.isPending}
          >
            {createMutation.isPending ? '创建中...' : '创建'}
          </Button>
        </div>
      </Dialog>
    </PageContainer>
  );
}
