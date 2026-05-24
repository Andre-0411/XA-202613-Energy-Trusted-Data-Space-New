/**
 * 存证管理页面
 * 存证列表 + 提交存证 + 存证溯源 + 查看详情
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, Dialog, MessagePlugin, Textarea } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, SearchIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TrendingUpIcon,
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

/** 存证类型选项 */
const EVIDENCE_TYPE_OPTIONS = [
  { value: 'DATA_HASH', label: '数据哈希' },
  { value: 'COMPUTE_RESULT', label: '计算结果' },
  { value: 'CONTRACT_EXEC', label: '合约执行' },
  { value: 'AUDIT_LOG', label: '审计日志' },
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

const BcEvidencePage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 & 分页 =====
  const [filterType, setFilterType] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 提交存证弹窗 =====
  const [submitOpen, setSubmitOpen] = useState<boolean>(false);
  const [submitHash, setSubmitHash] = useState<string>('');
  const [submitType, setSubmitType] = useState<string>('DATA_HASH');
  const [submitDesc, setSubmitDesc] = useState<string>('');

  // ===== 溯源弹窗 =====
  const [traceOpen, setTraceOpen] = useState<boolean>(false);
  const [traceHash, setTraceHash] = useState<string>('');
  const [traceResults, setTraceResults] = useState<Evidence[]>([]);

  // ===== 详情弹窗 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<Evidence | null>(null);

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

  const items: Evidence[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalEvidence: total,
    verifiedEvidence: items.filter((item) => item.status === 'VERIFIED').length,
    pendingEvidence: items.filter((item) => item.status === 'PENDING').length,
    todaySubmitted: items.filter((item) => {
      const today = new Date().toDateString();
      return new Date(item.created_at).toDateString() === today;
    }).length,
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

  // ===== Mutations =====
  const submitMut = useMutation({
    mutationFn: (d: { evidence_hash: string; evidence_type: string; description?: string }) => submitEvidence(d),
    onSuccess: () => {
      MessagePlugin.success('存证提交成功');
      queryClient.invalidateQueries({ queryKey: ['evidence'] });
      setSubmitOpen(false);
      setSubmitHash('');
      setSubmitType('DATA_HASH');
      setSubmitDesc('');
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

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '存证管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '提交存证', icon: <AddIcon />, onClick: () => setSubmitOpen(true), variant: 'contained' },
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
      id: 'uploader_did', label: '上传者 DID', minWidth: 180,
      render: (row) => (
        <span className="text-xs text-gray-600 font-mono truncate max-w-[160px] inline-block">
          {(row.uploader_did ?? '').slice(0, 20)}...
        </span>
      ),
    },
    {
      id: 'description', label: '描述', minWidth: 150,
      render: (row) => (
        <span className="text-xs text-gray-600 max-w-[150px] truncate inline-block">
          {row.description ?? '—'}
        </span>
      ),
    },
    {
      id: 'created_at', label: '创建时间', minWidth: 160,
      render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions', label: '操作', minWidth: 80, align: 'center',
      render: (row) => (
        <Tooltip content="查看详情">
          <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => detailMut.mutate(row.id)}>
            <BrowseIcon />
          </span>
        </Tooltip>
      ),
    },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="存证管理"
        subtitle="管理区块链存证记录，支持提交、溯源与详情查看"
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总存证数" value={stats.totalEvidence} unit="条" icon={<CheckCircleFilledIcon />} gradient="purple" />
        <StatCard title="已验证" value={stats.verifiedEvidence} unit="条" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="待验证" value={stats.pendingEvidence} unit="条" icon={<ErrorCircleFilledIcon />} gradient="cyan" />
        <StatCard title="今日提交" value={stats.todaySubmitted} unit="条" icon={<TrendingUpIcon />} gradient="orange" />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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

      {/* 提交存证弹窗 */}
      <Dialog visible={submitOpen} onClose={() => setSubmitOpen(false)} header="提交存证" width="480px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setSubmitOpen(false)}>取消</Button>
          <Button theme="primary" disabled={!submitHash.trim()} onClick={() => submitMut.mutate({ evidence_hash: submitHash, evidence_type: submitType, description: submitDesc || undefined })}>提交</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">存证哈希</label>
            <Input value={submitHash} onChange={(val) => setSubmitHash(String(val))} placeholder="SHA-256 哈希值" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">存证类型</label>
            <Select value={submitType} onChange={(val) => setSubmitType(String(val))} options={EVIDENCE_TYPE_OPTIONS} />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">描述（可选）</label>
            <Textarea value={submitDesc} onChange={(val) => setSubmitDesc(String(val))} rows={2} />
          </div>
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
              {traceResults.map((ev, idx) => (
                <div key={ev.id} className="p-3 border border-gray-200 rounded-lg">
                  <div className="flex justify-between mb-1">
                    <Tag>#{idx + 1}</Tag>
                    <span className="text-xs text-gray-500">
                      区块 #{ev.block_number} | {new Date(ev.created_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  <p className="text-xs font-mono">哈希: {ev.evidence_hash}</p>
                  <p className="text-xs">上传者: {ev.uploader_did}</p>
                </div>
              ))}
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
            <div>
              <span className="text-xs text-gray-500">创建时间</span>
              <p className="text-sm">{new Date(detailData.created_at).toLocaleString('zh-CN')}</p>
            </div>
          </div>
        ) : (
          <span className="text-gray-400">暂无数据</span>
        )}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default BcEvidencePage;
