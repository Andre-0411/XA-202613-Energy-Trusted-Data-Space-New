/**
 * 存证管理页面
 * 存证列表 + 提交存证 + 溯源追踪
 * 已对接真实API，无模拟数据
 */
import React, { useState } from 'react';
import { Button, Input, Select, Tag, Dialog, MessagePlugin, Card, Statistic } from 'tdesign-react';
import { AddIcon, RefreshIcon, BrowseIcon, SearchIcon } from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryEvidenceRange, submitEvidence, getEvidenceDetail, traceEvidence } from '@/api/blockchain';
import type { Evidence } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';

/** 存证类型选项 */
const EVIDENCE_TYPE_OPTIONS = [
  { value: 'DATA_HASH', label: '数据哈希' },
  { value: 'COMPUTE_RESULT', label: '计算结果' },
  { value: 'CONTRACT_EXEC', label: '合约执行' },
  { value: 'AUDIT_LOG', label: '审计日志' },
];

/** 存证状态映射 */
const EVIDENCE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  VERIFIED: { label: '已验证', theme: 'success' },
  PENDING: { label: '待验证', theme: 'warning' },
  FAILED: { label: '验证失败', theme: 'danger' },
};

const BcEvidencePage: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);
  const [filterType, setFilterType] = useState<string>('');

  // 弹窗状态
  const [submitOpen, setSubmitOpen] = useState<boolean>(false);
  const [submitHash, setSubmitHash] = useState<string>('');
  const [submitType, setSubmitType] = useState<string>('DATA_HASH');
  const [submitDesc, setSubmitDesc] = useState<string>('');
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<Evidence | null>(null);
  const [traceOpen, setTraceOpen] = useState<boolean>(false);
  const [traceHash, setTraceHash] = useState<string>('');
  const [traceResults, setTraceResults] = useState<Evidence[]>([]);

  // 查询存证列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['evidences', page, pageSize, filterType],
    queryFn: () => queryEvidenceRange({ page: page + 1, page_size: pageSize, evidence_type: filterType || undefined }),
  });

  const items: Evidence[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // 统计
  const stats = {
    total: total,
    verified: items.filter(i => i.status === 'VERIFIED').length,
    pending: items.filter(i => i.status === 'PENDING').length,
  };

  // 提交存证
  const submitMutation = useMutation({
    mutationFn: submitEvidence,
    onSuccess: () => {
      MessagePlugin.success('存证提交成功');
      setSubmitOpen(false);
      setSubmitHash('');
      setSubmitDesc('');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('提交失败: ' + (error?.message || '未知错误'));
    },
  });

  // 溯源查询
  const handleTrace = async () => {
    if (!traceHash.trim()) {
      MessagePlugin.warning('请输入哈希值');
      return;
    }
    try {
      const res = await traceEvidence(traceHash);
      setTraceResults(res?.data ?? []);
      if ((res?.data ?? []).length === 0) {
        MessagePlugin.info('未找到溯源记录');
      }
    } catch (error: any) {
      MessagePlugin.error('溯源失败: ' + (error?.message || '未知错误'));
    }
  };

  // 表格列定义
  const columns: Column[] = [
    { title: '存证哈希', colKey: 'evidence_hash', width: 200, ellipsis: true },
    {
      title: '类型', colKey: 'evidence_type', width: 120,
      cell: ({ row }) => {
        const typeMap: Record<string, string> = { DATA_HASH: '数据哈希', COMPUTE_RESULT: '计算结果', CONTRACT_EXEC: '合约执行', AUDIT_LOG: '审计日志' };
        return <Tag theme="primary" variant="light">{typeMap[row.evidence_type] || row.evidence_type}</Tag>;
      },
    },
    { title: '交易哈希', colKey: 'tx_hash', width: 200, ellipsis: true },
    { title: '区块号', colKey: 'block_number', width: 120 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }) => {
        const status = EVIDENCE_STATUS_MAP[row.status] || { label: row.status, theme: 'default' as const };
        return <Tag theme={status.theme} variant="light">{status.label}</Tag>;
      },
    },
    { title: '创建时间', colKey: 'created_at', width: 180 },
    {
      title: '操作', colKey: 'actions', width: 150,
      cell: ({ row }) => (
        <Button size="small" variant="text" icon={<BrowseIcon />}
          onClick={() => { setDetailData(row); setDetailOpen(true); }}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="存证管理" breadcrumbs={[homeBreadcrumb, { label: '区块链' }, { label: '存证管理' }]} />

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card><Statistic title="存证总数" value={stats.total} /></Card>
        <Card><Statistic title="已验证" value={stats.verified} /></Card>
        <Card><Statistic title="待验证" value={stats.pending} /></Card>
      </div>

      {/* 操作栏 */}
      <div className="flex justify-between mb-4">
        <div className="flex gap-2">
          <Button icon={<AddIcon />} onClick={() => setSubmitOpen(true)}>提交存证</Button>
          <Button icon={<SearchIcon />} variant="outline" onClick={() => setTraceOpen(true)}>溯源查询</Button>
          <Button icon={<RefreshIcon />} variant="outline" onClick={() => refetch()}>刷新</Button>
        </div>
        <Select value={filterType} onChange={setFilterType} options={EVIDENCE_TYPE_OPTIONS} placeholder="筛选类型" clearable style={{ width: 150 }} />
      </div>

      {/* 数据表格 */}
      <DataTable columns={columns} rows={items} page={page} pageSize={pageSize} total={total}
        onPageChange={setPage} loading={isLoading} />

      {/* 提交存证弹窗 */}
      <Dialog header="提交存证" visible={submitOpen} onClose={() => setSubmitOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setSubmitOpen(false)}>取消</Button>
            <Button loading={submitMutation.isPending}
              onClick={() => submitMutation.mutate({ evidence_hash: submitHash, evidence_type: submitType, description: submitDesc })}>
              确认提交
            </Button>
          </div>
        }>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">存证哈希 *</label>
            <Input value={submitHash} onChange={setSubmitHash} placeholder="0x..." />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">存证类型 *</label>
            <Select value={submitType} onChange={setSubmitType} options={EVIDENCE_TYPE_OPTIONS} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">描述</label>
            <Input value={submitDesc} onChange={setSubmitDesc} placeholder="存证描述" />
          </div>
        </div>
      </Dialog>

      {/* 溯源查询弹窗 */}
      <Dialog header="溯源查询" visible={traceOpen} onClose={() => setTraceOpen(false)}
        footer={<Button onClick={() => setTraceOpen(false)}>关闭</Button>}>
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input value={traceHash} onChange={setTraceHash} placeholder="输入哈希值" className="flex-1" />
            <Button icon={<SearchIcon />} onClick={handleTrace}>查询</Button>
          </div>
          {traceResults.length > 0 && (
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {traceResults.map((item, idx) => (
                <Card key={idx} className="p-3">
                  <div className="text-sm">
                    <div><strong>哈希:</strong> {item.evidence_hash}</div>
                    <div><strong>类型:</strong> {item.evidence_type}</div>
                    <div><strong>时间:</strong> {item.created_at}</div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog header="存证详情" visible={detailOpen} onClose={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {detailData && (
          <div className="space-y-3">
            <div><strong>存证ID:</strong> {detailData.id}</div>
            <div><strong>存证哈希:</strong> {detailData.evidence_hash}</div>
            <div><strong>类型:</strong> {detailData.evidence_type}</div>
            <div><strong>交易哈希:</strong> {detailData.tx_hash}</div>
            <div><strong>区块号:</strong> {detailData.block_number}</div>
            <div><strong>上传者DID:</strong> {detailData.uploader_did}</div>
            <div><strong>描述:</strong> {detailData.description || '无'}</div>
            <div><strong>状态:</strong> {EVIDENCE_STATUS_MAP[detailData.status]?.label || detailData.status}</div>
            <div><strong>创建时间:</strong> {detailData.created_at}</div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default BcEvidencePage;
