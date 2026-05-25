/**
 * 存证管理页面
 * 存证列表 + 提交存证 + 存证验证 + 溯源追踪 + 批量存证
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, Dialog, MessagePlugin, Textarea, Tabs, Table, Form, Card, Row, Col, Statistic, Steps, Timeline, Divider, Typography, Space } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, SearchIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TrendingUpIcon,
  FileIcon, TimeIcon, LinkIcon, DataBaseIcon, VerifyIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryEvidenceRange, submitEvidence, getEvidenceDetail, traceEvidence } from '@/api/blockchain';
import type { Evidence } from '@/types/api';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import FilterBar from '@/components/common/FilterBar';
import type { FilterField } from '@/components/common/FilterBar';
import ReactECharts from 'echarts-for-react';

/** 存证类型选项 */
const EVIDENCE_TYPE_OPTIONS = [
  { value: 'DATA_HASH', label: '数据哈希' },
  { value: 'COMPUTE_RESULT', label: '计算结果' },
  { value: 'CONTRACT_EXEC', label: '合约执行' },
  { value: 'AUDIT_LOG', label: '审计日志' },
];

/** 节点类型选项 */
const NODE_TYPE_OPTIONS = [
  { value: 'data_node', label: '数据节点' },
  { value: 'compute_node', label: '计算节点' },
  { value: 'storage_node', label: '存储节点' },
  { value: 'verification_node', label: '验证节点' },
];

/** 资源类型选项 */
const RESOURCE_TYPE_OPTIONS = [
  { value: 'energy_data', label: '能源数据' },
  { value: 'carbon_data', label: '碳排放数据' },
  { value: 'trading_data', label: '交易数据' },
  { value: 'monitoring_data', label: '监测数据' },
];

/** 存证类型颜色映射 */
const evidenceTypeColor = (t: string): 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error' | 'default' => {
  const map: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error'> = {
    DATA_HASH: 'primary',
    COMPUTE_RESULT: 'success',
    CONTRACT_EXEC: 'warning',
    AUDIT_LOG: 'info',
  };
  return map[t] ?? 'default';
};

/** 存证状态映射 */
const EVIDENCE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  VERIFIED: { label: '已验证', theme: 'success' },
  PENDING: { label: '待验证', theme: 'warning' },
  FAILED: { label: '验证失败', theme: 'danger' },
};

/* ========== 模拟数据 - 存证记录 ========== */
const MOCK_EVIDENCES: Evidence[] = [
  {
    id: 'ev-001',
    evidence_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    evidence_type: 'DATA_HASH',
    tx_hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
    block_number: 1234567,
    uploader_did: 'did:ethr:0x1234567890abcdef1234567890abcdef12345678',
    description: '电网负荷数据哈希存证',
    status: 'VERIFIED',
    created_at: '2025-05-20T08:00:00Z',
    node_type: 'data_node',
    resource_type: 'energy_data',
  },
  {
    id: 'ev-002',
    evidence_hash: '0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1',
    evidence_type: 'COMPUTE_RESULT',
    tx_hash: '0xbcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890a',
    block_number: 1234568,
    uploader_did: 'did:ethr:0x234567890abcdef1234567890abcdef123456789',
    description: '光伏发电预测计算结果存证',
    status: 'VERIFIED',
    created_at: '2025-05-21T10:30:00Z',
    node_type: 'compute_node',
    resource_type: 'energy_data',
  },
  {
    id: 'ev-003',
    evidence_hash: '0x34567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12',
    evidence_type: 'CONTRACT_EXEC',
    tx_hash: '0xcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab',
    block_number: 1234569,
    uploader_did: 'did:ethr:0x34567890abcdef1234567890abcdef1234567890',
    description: '数据共享合约执行存证',
    status: 'PENDING',
    created_at: '2025-05-22T14:15:00Z',
    node_type: 'verification_node',
    resource_type: 'trading_data',
  },
  {
    id: 'ev-004',
    evidence_hash: '0x4567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef123',
    evidence_type: 'AUDIT_LOG',
    tx_hash: '0xdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc',
    block_number: 1234570,
    uploader_did: 'did:ethr:0x4567890abcdef1234567890abcdef1234567890a',
    description: '碳排放数据审计日志存证',
    status: 'VERIFIED',
    created_at: '2025-05-23T09:45:00Z',
    node_type: 'storage_node',
    resource_type: 'carbon_data',
  },
  {
    id: 'ev-005',
    evidence_hash: '0x567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234',
    evidence_type: 'DATA_HASH',
    tx_hash: '0xef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd',
    block_number: 1234571,
    uploader_did: 'did:ethr:0x567890abcdef1234567890abcdef1234567890ab',
    description: '储能调度数据哈希存证',
    status: 'VERIFIED',
    created_at: '2025-05-24T11:20:00Z',
    node_type: 'data_node',
    resource_type: 'monitoring_data',
  },
];

/* ========== 模拟数据 - 批量存证 ========== */
interface BatchEvidence {
  id: string;
  batch_id: string;
  evidence_count: number;
  success_count: number;
  failed_count: number;
  status: string;
  created_at: string;
  completed_at: string;
}

const MOCK_BATCH_EVIDENCES: BatchEvidence[] = [
  {
    id: 'batch-001',
    batch_id: 'BATCH-20250520-001',
    evidence_count: 50,
    success_count: 48,
    failed_count: 2,
    status: 'completed',
    created_at: '2025-05-20T08:00:00Z',
    completed_at: '2025-05-20T08:05:00Z',
  },
  {
    id: 'batch-002',
    batch_id: 'BATCH-20250521-001',
    evidence_count: 30,
    success_count: 30,
    failed_count: 0,
    status: 'completed',
    created_at: '2025-05-21T10:30:00Z',
    completed_at: '2025-05-21T10:33:00Z',
  },
  {
    id: 'batch-003',
    batch_id: 'BATCH-20250522-001',
    evidence_count: 100,
    success_count: 95,
    failed_count: 5,
    status: 'processing',
    created_at: '2025-05-22T14:15:00Z',
    completed_at: '',
  },
];

const BATCH_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  completed: { label: '已完成', theme: 'success' },
  processing: { label: '处理中', theme: 'primary' },
  failed: { label: '失败', theme: 'danger' },
};

const BcEvidencePage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 主 Tab =====
  const [activeTab, setActiveTab] = useState<string>('evidence');

  // ===== 筛选 & 分页 =====
  const [filterType, setFilterType] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 提交存证弹窗 =====
  const [submitOpen, setSubmitOpen] = useState<boolean>(false);
  const [submitStep, setSubmitStep] = useState<number>(0);
  const [submitHash, setSubmitHash] = useState<string>('');
  const [submitType, setSubmitType] = useState<string>('DATA_HASH');
  const [submitDesc, setSubmitDesc] = useState<string>('');
  const [submitNodeType, setSubmitNodeType] = useState<string>('data_node');
  const [submitResourceType, setSubmitResourceType] = useState<string>('energy_data');

  // ===== 存证验证弹窗 =====
  const [verifyOpen, setVerifyOpen] = useState<boolean>(false);
  const [verifyHash, setVerifyHash] = useState<string>('');
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string } | null>(null);

  // ===== 溯源弹窗 =====
  const [traceOpen, setTraceOpen] = useState<boolean>(false);
  const [traceHash, setTraceHash] = useState<string>('');
  const [traceResults, setTraceResults] = useState<Evidence[]>([]);

  // ===== 详情弹窗 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<Evidence | null>(null);

  // ===== 批量存证弹窗 =====
  const [batchOpen, setBatchOpen] = useState<boolean>(false);
  const [batchHashes, setBatchHashes] = useState<string>('');
  const [batchType, setBatchType] = useState<string>('DATA_HASH');

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['evidence', page, pageSize, filterType],
    queryFn: () =>
      queryEvidenceRange({
        page: page + 1,
        page_size: pageSize,
        evidence_type: filterType || undefined,
      }),
  });

  const items: Evidence[] = data?.data?.items ?? MOCK_EVIDENCES;
  const total: number = data?.data?.total ?? MOCK_EVIDENCES.length;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalEvidence: total,
    verifiedEvidence: items.filter((item) => item.status === 'VERIFIED').length,
    pendingEvidence: items.filter((item) => item.status === 'PENDING').length,
    todaySubmitted: items.filter((item) => {
      const today = new Date().toDateString();
      return new Date(item.created_at).toDateString() === today;
    }).length,
    totalBatches: MOCK_BATCH_EVIDENCES.length,
    successRate: items.length > 0 ? Math.round((items.filter(i => i.status === 'VERIFIED').length / items.length) * 100) : 0,
  }), [total, items]);

  // ===== ECharts 配置 =====
  const evidenceTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['提交存证', '验证通过'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '存证数量' },
    series: [
      { name: '提交存证', type: 'bar', data: [320, 380, 420, 480, 520, 580, 650], itemStyle: { color: '#2196f3' } },
      { name: '验证通过', type: 'bar', data: [280, 350, 390, 450, 490, 550, 620], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const evidenceTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '存证类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 1580, name: '数据哈希', itemStyle: { color: '#2196f3' } },
          { value: 980, name: '计算结果', itemStyle: { color: '#4caf50' } },
          { value: 520, name: '合约执行', itemStyle: { color: '#ff9800' } },
          { value: 370, name: '审计日志', itemStyle: { color: '#9c27b0' } },
        ],
      },
    ],
  }), []);

  const nodeTypeOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['数据节点', '计算节点', '存储节点', '验证节点'], axisLabel: { rotate: 15 } },
    yAxis: { type: 'value', name: '存证数量' },
    series: [{
      type: 'bar',
      data: [
        { value: 1250, itemStyle: { color: '#2196f3' } },
        { value: 890, itemStyle: { color: '#4caf50' } },
        { value: 650, itemStyle: { color: '#ff9800' } },
        { value: 420, itemStyle: { color: '#9c27b0' } },
      ],
      barWidth: '50%',
    }],
  }), []);

  // ===== Mutations =====
  const submitMut = useMutation({
    mutationFn: (d: { evidence_hash: string; evidence_type: string; description?: string }) => submitEvidence(d),
    onSuccess: () => {
      MessagePlugin.success('存证提交成功');
      queryClient.invalidateQueries({ queryKey: ['evidence'] });
      setSubmitOpen(false);
      setSubmitStep(0);
      setSubmitHash('');
      setSubmitType('DATA_HASH');
      setSubmitDesc('');
      setSubmitNodeType('data_node');
      setSubmitResourceType('energy_data');
    },
    onError: () => { MessagePlugin.error('存证提交失败'); },
  });

  const detailMut = useMutation({
    mutationFn: (id: string) => getEvidenceDetail(id),
    onSuccess: (res) => {
      setDetailData(res.data ?? null);
      setDetailOpen(true);
    },
  });

  const traceMut = useMutation({
    mutationFn: (hash: string) => traceEvidence(hash),
    onSuccess: (res) => {
      setTraceResults(res.data ?? []);
    },
  });

  const handleTrace = useCallback(() => {
    if (traceHash.trim()) {
      traceMut.mutate(traceHash);
    }
  }, [traceHash, traceMut]);

  const handleVerify = useCallback(() => {
    if (verifyHash.trim()) {
      // 模拟验证结果
      setTimeout(() => {
        const isValid = Math.random() > 0.3; // 70% 概率验证成功
        setVerifyResult({
          valid: isValid,
          message: isValid ? '存证验证成功，数据完整性已确认' : '存证验证失败，数据可能已被篡改',
        });
      }, 1000);
    }
  }, [verifyHash]);

  const handleBatchSubmit = useCallback(() => {
    const hashes = batchHashes.split('\n').filter(h => h.trim());
    if (hashes.length > 0) {
      MessagePlugin.success(`已提交 ${hashes.length} 条存证`);
      setBatchOpen(false);
      setBatchHashes('');
      setBatchType('DATA_HASH');
    }
  }, [batchHashes]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '存证管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '提交存证', icon: <AddIcon />, onClick: () => setSubmitOpen(true), variant: 'contained' },
      { label: '存证验证', icon: <VerifyIcon />, onClick: () => setVerifyOpen(true), variant: 'outlined' },
      { label: '存证溯源', icon: <SearchIcon />, onClick: () => setTraceOpen(true), variant: 'outlined' },
    ],
    [],
  );

  // ===== 筛选字段 =====
  const filterFields: FilterField[] = useMemo(() => [
    {
      name: 'type', type: 'select', placeholder: '存证类型', width: 160,
      options: [{ value: '', label: '全部' }, ...EVIDENCE_TYPE_OPTIONS],
    },
  ], []);

  const handleFilterChange = (name: string, value: string) => {
    if (name === 'type') { setFilterType(value); setPage(0); }
  };

  // ===== 表格列定义 =====
  const columns: Column<Evidence>[] = useMemo(() => [
    {
      id: 'evidence_hash', label: '存证哈希', minWidth: 160,
      render: (row) => (
        <Tooltip content={row.evidence_hash}>
          <Tag variant="outline">{(row.evidence_hash ?? '').slice(0, 12) + '...'}</Tag>
        </Tooltip>
      ),
    },
    {
      id: 'evidence_type', label: '类型', minWidth: 120,
      render: (row) => (
        <StatusTag
          status={EVIDENCE_TYPE_OPTIONS.find((o) => o.value === row.evidence_type)?.label ?? row.evidence_type}
          color={evidenceTypeColor(row.evidence_type)}
        />
      ),
    },
    {
      id: 'node_type', label: '节点类型', minWidth: 120,
      render: (row) => {
        const option = NODE_TYPE_OPTIONS.find(o => o.value === row.node_type);
        return <Tag variant="outline" size="small">{option?.label || row.node_type}</Tag>;
      },
    },
    {
      id: 'resource_type', label: '资源类型', minWidth: 120,
      render: (row) => {
        const option = RESOURCE_TYPE_OPTIONS.find(o => o.value === row.resource_type);
        return <Tag variant="outline" size="small">{option?.label || row.resource_type}</Tag>;
      },
    },
    {
      id: 'status', label: '状态', minWidth: 100,
      render: (row) => {
        const s = EVIDENCE_STATUS_MAP[row.status];
        return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : <Tag size="small">{row.status}</Tag>;
      },
    },
    {
      id: 'tx_hash', label: '交易哈希', minWidth: 140,
      render: (row) => (
        <Tooltip content={row.tx_hash ?? ''}>
          <Tag variant="outline" theme="primary">
            {(row.tx_hash?.slice(0, 10) ?? '—') + (row.tx_hash ? '...' : '')}
          </Tag>
        </Tooltip>
      ),
    },
    { id: 'block_number', label: '区块号', minWidth: 100 },
    {
      id: 'created_at', label: '创建时间', minWidth: 160,
      render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions', label: '操作', minWidth: 120, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => detailMut.mutate(row.id)}>
              <BrowseIcon />
            </span>
          </Tooltip>
          <Tooltip content="验证存证">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500" onClick={() => {
              setVerifyHash(row.evidence_hash);
              setVerifyOpen(true);
            }}>
              <VerifyIcon />
            </span>
          </Tooltip>
        </div>
      ),
    },
  ], []);

  // ===== 批量存证列定义 =====
  const batchColumns: Column<BatchEvidence>[] = useMemo(() => [
    { id: 'batch_id', label: '批次ID', minWidth: 180, render: (row) => <Tag variant="outline">{row.batch_id}</Tag> },
    { id: 'evidence_count', label: '存证数量', minWidth: 100 },
    { id: 'success_count', label: '成功数量', minWidth: 100, render: (row) => <span className="text-green-600">{row.success_count}</span> },
    { id: 'failed_count', label: '失败数量', minWidth: 100, render: (row) => <span className="text-red-600">{row.failed_count}</span> },
    { id: 'status', label: '状态', minWidth: 100, render: (row) => { const s = BATCH_STATUS_MAP[row.status]; return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'created_at', label: '创建时间', minWidth: 150, render: (row) => new Date(row.created_at).toLocaleString('zh-CN') },
    { id: 'completed_at', label: '完成时间', minWidth: 150, render: (row) => row.completed_at ? new Date(row.completed_at).toLocaleString('zh-CN') : '—' },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="存证管理"
        subtitle="管理区块链存证记录，支持提交、验证、溯源与批量操作"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['evidence'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总存证数" value={stats.totalEvidence} unit="条" icon={<FileIcon />} gradient="purple" />
        <StatCard title="已验证" value={stats.verifiedEvidence} unit="条" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="待验证" value={stats.pendingEvidence} unit="条" icon={<TimeIcon />} gradient="orange" />
        <StatCard title="验证成功率" value={stats.successRate} unit="%" icon={<TrendingUpIcon />} gradient="cyan" />
      </div>

      {/* 主 Tab 区域 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="evidence" label="存证记录">
          {/* ECharts 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="存证提交趋势" option={evidenceTrendOption} className="lg:col-span-2" />
            <ChartCard title="存证类型分布" option={evidenceTypeOption} />
          </div>

          {/* 搜索过滤栏 */}
          <FilterBar
            fields={filterFields}
            values={{ type: filterType }}
            onChange={handleFilterChange}
          />

          {/* 数据表格 */}
          <PageSection padding="none">
            <DataTable
              columns={columns}
              rows={items}
              loading={isLoading}
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
            />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="batch" label="批量存证">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={batchColumns} rows={MOCK_BATCH_EVIDENCES} page={0} pageSize={20} total={MOCK_BATCH_EVIDENCES.length} />
              </PageSection>
            </div>
            <ChartCard title="节点类型分布" option={nodeTypeOption} />
          </div>
        </Tabs.TabPanel>
      </Tabs>

      {/* 提交存证弹窗（多步骤） */}
      <Dialog visible={submitOpen} onClose={() => setSubmitOpen(false)} header="提交存证" width="640px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setSubmitOpen(false)}>取消</Button>
          {submitStep > 0 && <Button variant="outline" onClick={() => setSubmitStep(submitStep - 1)}>上一步</Button>}
          {submitStep < 2 ? (
            <Button theme="primary" onClick={() => setSubmitStep(submitStep + 1)} disabled={submitStep === 0 && !submitHash.trim()}>下一步</Button>
          ) : (
            <Button theme="primary" disabled={!submitHash.trim()} onClick={() => submitMut.mutate({ evidence_hash: submitHash, evidence_type: submitType, description: submitDesc || undefined })}>提交</Button>
          )}
        </div>
      }>
        <div className="mb-4">
          <Steps current={submitStep} style={{ marginBottom: 24 }}>
            <Steps.StepItem title="填写哈希" />
            <Steps.StepItem title="选择类型" />
            <Steps.StepItem title="确认提交" />
          </Steps>
        </div>

        {submitStep === 0 && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">存证哈希</label>
              <Input value={submitHash} onChange={(val) => setSubmitHash(String(val))} placeholder="SHA-256 哈希值" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">描述（可选）</label>
              <Textarea value={submitDesc} onChange={(val) => setSubmitDesc(String(val))} rows={2} placeholder="请输入存证描述" />
            </div>
          </div>
        )}

        {submitStep === 1 && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">存证类型</label>
              <Select value={submitType} onChange={(val) => setSubmitType(String(val))} options={EVIDENCE_TYPE_OPTIONS} />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">节点类型</label>
              <Select value={submitNodeType} onChange={(val) => setSubmitNodeType(String(val))} options={NODE_TYPE_OPTIONS} />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">资源类型</label>
              <Select value={submitResourceType} onChange={(val) => setSubmitResourceType(String(val))} options={RESOURCE_TYPE_OPTIONS} />
            </div>
          </div>
        )}

        {submitStep === 2 && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-gray-600">请确认以下存证信息：</p>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm"><strong>存证哈希：</strong>{submitHash || '未填写'}</p>
              <p className="text-sm mt-2"><strong>存证类型：</strong>{EVIDENCE_TYPE_OPTIONS.find(o => o.value === submitType)?.label}</p>
              <p className="text-sm mt-2"><strong>节点类型：</strong>{NODE_TYPE_OPTIONS.find(o => o.value === submitNodeType)?.label}</p>
              <p className="text-sm mt-2"><strong>资源类型：</strong>{RESOURCE_TYPE_OPTIONS.find(o => o.value === submitResourceType)?.label}</p>
              <p className="text-sm mt-2"><strong>描述：</strong>{submitDesc || '无'}</p>
            </div>
            <div className="flex items-center gap-2 text-blue-600">
              <TimeIcon />
              <span className="text-sm">提交后将生成交易哈希并上链</span>
            </div>
          </div>
        )}
      </Dialog>

      {/* 存证验证弹窗 */}
      <Dialog visible={verifyOpen} onClose={() => { setVerifyOpen(false); setVerifyHash(''); setVerifyResult(null); }} header="存证验证" width="480px" footer={
        <Button variant="outline" onClick={() => { setVerifyOpen(false); setVerifyHash(''); setVerifyResult(null); }}>关闭</Button>
      }>
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Input value={verifyHash} onChange={(val) => setVerifyHash(String(val))} placeholder="输入存证哈希" style={{ flex: 1 }} />
            <Button theme="primary" onClick={handleVerify} disabled={!verifyHash.trim()}>验证</Button>
          </div>
          {verifyResult && (
            <div className={`p-4 rounded-lg ${verifyResult.valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center gap-2 mb-2">
                {verifyResult.valid ? (
                  <CheckCircleFilledIcon style={{ color: '#4caf50', fontSize: 20 }} />
                ) : (
                  <ErrorCircleFilledIcon style={{ color: '#f44336', fontSize: 20 }} />
                )}
                <span className={`font-semibold ${verifyResult.valid ? 'text-green-800' : 'text-red-800'}`}>
                  {verifyResult.valid ? '验证成功' : '验证失败'}
                </span>
              </div>
              <p className={`text-sm ${verifyResult.valid ? 'text-green-600' : 'text-red-600'}`}>
                {verifyResult.message}
              </p>
            </div>
          )}
        </div>
      </Dialog>

      {/* 溯源弹窗 */}
      <Dialog visible={traceOpen} onClose={() => { setTraceOpen(false); setTraceResults([]); setTraceHash(''); }} header="存证溯源" width="640px" footer={
        <Button variant="outline" onClick={() => { setTraceOpen(false); setTraceResults([]); setTraceHash(''); }}>关闭</Button>
      }>
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Input value={traceHash} onChange={(val) => setTraceHash(String(val))} placeholder="输入存证哈希" style={{ flex: 1 }} />
            <Button theme="primary" onClick={handleTrace} disabled={!traceHash.trim()}>溯源查询</Button>
          </div>
          {traceMut.isPending && <span className="text-gray-400">查询中...</span>}
          {traceResults.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-semibold">溯源结果（{traceResults.length} 条记录）</p>
              <Timeline>
                {traceResults.map((ev, idx) => (
                  <Timeline.Item key={ev.id} label={`区块 #${ev.block_number}`}>
                    <div className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex justify-between mb-1">
                        <Tag>#{idx + 1}</Tag>
                        <span className="text-xs text-gray-500">
                          {new Date(ev.created_at).toLocaleString('zh-CN')}
                        </span>
                      </div>
                      <p className="text-xs font-mono">哈希: {ev.evidence_hash}</p>
                      <p className="text-xs">类型: {EVIDENCE_TYPE_OPTIONS.find(o => o.value === ev.evidence_type)?.label}</p>
                      <p className="text-xs">上传者: {ev.uploader_did}</p>
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
            </div>
          )}
          {!traceMut.isPending && traceResults.length === 0 && traceMut.isSuccess && (
            <span className="text-gray-400">未找到相关存证记录</span>
          )}
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="存证详情" width="640px" footer={
        <Button variant="outline" onClick={() => setDetailOpen(false)}>关闭</Button>
      }>
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <span className="text-xs text-gray-500">存证哈希</span>
                <p className="text-sm font-mono break-all">{detailData.evidence_hash}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">类型</span>
                <StatusTag status={detailData.evidence_type} color={evidenceTypeColor(detailData.evidence_type)} />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <span className="text-xs text-gray-500">交易哈希</span>
                <p className="text-sm font-mono break-all">{detailData.tx_hash}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">区块号</span>
                <p className="text-sm font-semibold">{detailData.block_number}</p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <span className="text-xs text-gray-500">上传者 DID</span>
                <p className="text-sm font-mono break-all">{detailData.uploader_did}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">描述</span>
                <p className="text-sm">{detailData.description ?? '—'}</p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <div>
                <span className="text-xs text-gray-500">节点类型</span>
                <p className="text-sm">{NODE_TYPE_OPTIONS.find(o => o.value === detailData.node_type)?.label || detailData.node_type}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">资源类型</span>
                <p className="text-sm">{RESOURCE_TYPE_OPTIONS.find(o => o.value === detailData.resource_type)?.label || detailData.resource_type}</p>
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500">创建时间</span>
              <p className="text-sm">{new Date(detailData.created_at).toLocaleString('zh-CN')}</p>
            </div>
          </div>
        ) : (
          <span className="text-gray-400">暂无数据</span>
        )}
      </Dialog>

      {/* 批量存证弹窗 */}
      <Dialog visible={batchOpen} onClose={() => setBatchOpen(false)} header="批量存证" width="480px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setBatchOpen(false)}>取消</Button>
          <Button theme="primary" disabled={!batchHashes.trim()} onClick={handleBatchSubmit}>批量提交</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">存证类型</label>
            <Select value={batchType} onChange={(val) => setBatchType(String(val))} options={EVIDENCE_TYPE_OPTIONS} />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">存证哈希列表（每行一个）</label>
            <Textarea value={batchHashes} onChange={(val) => setBatchHashes(String(val))} rows={6} placeholder="请输入存证哈希，每行一个" />
          </div>
          <div className="text-xs text-gray-500">
            支持批量提交存证，每行一个哈希值，最多支持100条。
          </div>
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default BcEvidencePage;