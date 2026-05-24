/**
 * 可验证凭证管理页面
 * VC 签发/验证/撤销/列表 + 统计卡片 + ECharts图表
 */
import React, { useState, useMemo } from 'react';
import { Button, Input, Tooltip, Dialog, Pagination, Select } from 'tdesign-react';
import {
  AddIcon, VerifiedIcon, CloseIcon, RefreshIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, InfoCircleFilledIcon, ShieldErrorFilledIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listVcs, issueVc, verifyVc, revokeVc } from '@/api/security';
import type { VcRecord } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

const VC_STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'ACTIVE', label: '有效' },
  { value: 'REVOKED', label: '已撤销' },
  { value: 'EXPIRED', label: '已过期' },
];

const vcStatusLabel = (s: string): string => {
  const m: Record<string, string> = { ACTIVE: '有效', REVOKED: '已撤销', EXPIRED: '已过期' };
  return m[s] ?? s;
};

const vcStatusColor = (s: string): 'success' | 'error' | 'warning' | 'default' => {
  const m: Record<string, 'success' | 'error' | 'warning'> = { ACTIVE: 'success', REVOKED: 'error', EXPIRED: 'warning' };
  return m[s] ?? 'default';
};

const SecurityVcPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 & 分页 =====
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 签发 VC 弹窗 =====
  const [issueOpen, setIssueOpen] = useState<boolean>(false);
  const [issueIssuerDid, setIssueIssuerDid] = useState<string>('');
  const [issueSubjectDid, setIssueSubjectDid] = useState<string>('');
  const [issueVcType, setIssueVcType] = useState<string>('');
  const [issueClaims, setIssueClaims] = useState<string>('{}');
  const [issueExpiresAt, setIssueExpiresAt] = useState<string>('');

  // ===== 验证 VC 弹窗 =====
  const [verifyOpen, setVerifyOpen] = useState<boolean>(false);
  const [verifyVcId, setVerifyVcId] = useState<string>('');
  const [verifyResult, setVerifyResult] = useState<{ overall_valid: boolean; errors: string[] } | null>(null);

  // ===== 撤销确认 =====
  const [revokeTarget, setRevokeTarget] = useState<VcRecord | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['vcs', page, pageSize, filterStatus],
    queryFn: () => listVcs({ page: page + 1, page_size: pageSize, status: filterStatus || undefined }) });

  const items: VcRecord[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据计算 =====
  const stats = useMemo(() => ({
    total: total,
    active: items.filter(i => i.status === 'ACTIVE').length,
    revoked: items.filter(i => i.status === 'REVOKED').length,
    expired: items.filter(i => i.status === 'EXPIRED').length }), [items, total]);

  // ===== ECharts 配置 =====
  const statusPieOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: 'VC状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: items.filter(i => i.status === 'ACTIVE').length || 45, name: '有效', itemStyle: { color: '#4caf50' } },
          { value: items.filter(i => i.status === 'REVOKED').length || 12, name: '已撤销', itemStyle: { color: '#f44336' } },
          { value: items.filter(i => i.status === 'EXPIRED').length || 8, name: '已过期', itemStyle: { color: '#ff9800' } },
        ] },
    ] }), [items]);

  const issueTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['签发数量', '撤销数量'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '凭证数量' },
    series: [
      { name: '签发数量', type: 'bar', data: [32, 45, 38, 52, 48, 56, 42], itemStyle: { color: '#2196f3' } },
      { name: '撤销数量', type: 'bar', data: [5, 8, 3, 6, 4, 7, 2], itemStyle: { color: '#f44336' } },
    ] }), []);

  const vcTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '凭证类型',
        type: 'pie',
        radius: '65%',
        center: ['60%', '50%'],
        data: [
          { value: 35, name: 'DataAccessCredential', itemStyle: { color: '#2196f3' } },
          { value: 28, name: 'EnergyTradeCredential', itemStyle: { color: '#4caf50' } },
          { value: 22, name: 'DeviceIdentityCredential', itemStyle: { color: '#ff9800' } },
          { value: 15, name: 'UserAuthCredential', itemStyle: { color: '#9c27b0' } },
        ],
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } } },
    ] }), []);

  // ===== Mutations =====
  const issueMut = useMutation({
    mutationFn: (d: { issuer_did: string; subject_did: string; vc_type: string; claims: Record<string, unknown>; expires_at?: string }) => issueVc(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vcs'] });
      setIssueOpen(false);
      setIssueIssuerDid(''); setIssueSubjectDid(''); setIssueVcType('');
      setIssueClaims('{}'); setIssueExpiresAt('');
    } });

  const verifyMut = useMutation({
    mutationFn: (d: { vc_id: string }) => verifyVc(d),
    onSuccess: (res) => { setVerifyResult(res.data ?? null); } });

  const revokeMut = useMutation({
    mutationFn: (vcId: string) => revokeVc(vcId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vcs'] });
      setRevokeTarget(null);
    } });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '可验证凭证' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '签发凭证', icon: <AddIcon />, onClick: () => setIssueOpen(true), variant: 'contained' },
      { label: '验证凭证', icon: <VerifiedIcon />, onClick: () => { setVerifyVcId(''); setVerifyResult(null); setVerifyOpen(true); }, variant: 'outlined' },
    ],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="可验证凭证管理"
        subtitle="管理可验证凭证，支持签发、验证与撤销"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['vcs'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总凭证数" value={stats.total} icon={<InfoCircleFilledIcon />} gradient="purple" unit="" />
        <MetricsCard title="有效凭证" value={stats.active} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <MetricsCard title="已撤销" value={stats.revoked} icon={<CloseIcon />} gradient="red" unit="" />
        <MetricsCard title="已过期" value={stats.expired} icon={<ErrorCircleFilledIcon />} color="warning" unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8"><ChartCard title="凭证签发趋势" option={issueTrendOption} height={300} /></div>
        <div className="lg:col-span-4"><ChartCard title="VC状态分布" option={statusPieOption} height={300} /></div>
      </div>

      {/* 筛选栏 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex items-center gap-4">
          <Select
            value={filterStatus}
            onChange={(val) => { setFilterStatus(String(val)); setPage(0); }}
            options={VC_STATUS_OPTIONS}
            style={{ width: 140 }}
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 flex flex-col flex-1 overflow-hidden">
        <div className="overflow-auto flex-1">
          <table className="w-full">
            <thead className="sticky top-0 bg-gray-50">
              <tr>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">VC ID</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">签发者 DID</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">主体 DID</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">类型</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">状态</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">签发时间</th>
                <th className="text-left font-bold px-4 py-3 text-sm text-gray-600">过期时间</th>
                <th className="text-center font-bold px-4 py-3 text-sm text-gray-600 w-20">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.vc_id} className="hover:bg-gray-50 border-b border-gray-100">
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs whitespace-nowrap overflow-hidden text-ellipsis block max-w-xs">{row.vc_id.slice(0, 16)}...</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs whitespace-nowrap overflow-hidden text-ellipsis block max-w-xs">{row.issuer_did.slice(0, 20)}...</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs whitespace-nowrap overflow-hidden text-ellipsis block max-w-xs">{row.subject_did.slice(0, 20)}...</span>
                  </td>
                  <td className="px-4 py-3 text-sm">{row.vc_type}</td>
                  <td className="px-4 py-3">
                    <StatusTag status={vcStatusLabel(row.status)} color={vcStatusColor(row.status)} />
                  </td>
                  <td className="px-4 py-3 text-sm">{new Date(row.issued_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-sm">{row.expires_at ? new Date(row.expires_at).toLocaleString('zh-CN') : '永不过期'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center">
                      {row.status === 'ACTIVE' && (
                        <Tooltip content="撤销">
                          <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-500" onClick={() => setRevokeTarget(row)}>
                            <CloseIcon />
                          </span>
                        </Tooltip>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-gray-500">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end p-3 border-t border-gray-100">
          <Pagination
            total={total}
            current={page + 1}
            pageSize={pageSize}
            onChange={(pageInfo) => {
              setPage(pageInfo.current - 1);
              setPageSize(pageInfo.pageSize);
            }}
          />
        </div>
      </div>

      {/* 签发弹窗 */}
      <Dialog
        visible={issueOpen}
        onClose={() => setIssueOpen(false)}
        header="签发可验证凭证"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setIssueOpen(false)}>取消</Button>
            <Button theme="primary" disabled={!issueIssuerDid.trim() || !issueSubjectDid.trim() || !issueVcType.trim()} onClick={() => {
              let claims: Record<string, unknown> = {};
              try { claims = JSON.parse(issueClaims || '{}'); } catch { claims = {}; }
              issueMut.mutate({ issuer_did: issueIssuerDid, subject_did: issueSubjectDid, vc_type: issueVcType, claims, expires_at: issueExpiresAt || undefined });
            }}>签发</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">签发者 DID</label>
            <Input value={issueIssuerDid} onChange={(val) => setIssueIssuerDid(String(val))} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">主体 DID</label>
            <Input value={issueSubjectDid} onChange={(val) => setIssueSubjectDid(String(val))} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">凭证类型</label>
            <Input value={issueVcType} onChange={(val) => setIssueVcType(String(val))} placeholder="DataAccessCredential" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">Claims (JSON)</label>
            <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={issueClaims} onChange={(e) => setIssueClaims(e.target.value)} rows={3} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-gray-600">过期时间（可选）</label>
            <Input value={issueExpiresAt} onChange={(val) => setIssueExpiresAt(String(val))} placeholder="YYYY-MM-DD HH:mm" />
          </div>
        </div>
      </Dialog>

      {/* 验证弹窗 */}
      <Dialog
        visible={verifyOpen}
        onClose={() => { setVerifyOpen(false); setVerifyResult(null); }}
        header="验证可验证凭证"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => { setVerifyOpen(false); setVerifyResult(null); }}>关闭</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Input value={verifyVcId} onChange={(val) => setVerifyVcId(String(val))} className="flex-1" />
            <Button theme="primary" disabled={!verifyVcId.trim()} onClick={() => verifyMut.mutate({ vc_id: verifyVcId })}>验证</Button>
          </div>
          {verifyMut.isPending && <span className="text-sm text-gray-500">验证中...</span>}
          {verifyResult && (
            <div className={`p-3 rounded-lg ${verifyResult.overall_valid ? 'bg-green-50' : 'bg-red-50'}`}>
              <h4 className={`text-sm font-semibold ${verifyResult.overall_valid ? 'text-green-700' : 'text-red-700'}`}>
                {verifyResult.overall_valid ? '✓ 验证通过' : '✗ 验证失败'}
              </h4>
              {verifyResult.errors.length > 0 && (
                <div className="flex flex-col gap-1 mt-1">
                  {verifyResult.errors.map((err, idx) => (
                    <span key={idx} className="text-sm text-red-600">• {err}</span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </Dialog>

      {/* 撤销确认 */}
      <ConfirmDialog
        open={!!revokeTarget}
        title="撤销凭证"
        message={`确定要撤销凭证「${revokeTarget?.vc_id?.slice(0, 16) ?? ''}...」吗？此操作不可恢复。`}
        type="danger"
        onConfirm={() => revokeTarget && revokeMut.mutate(revokeTarget.vc_id)}
        onCancel={() => setRevokeTarget(null)}
        loading={revokeMut.isPending}
      />

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default SecurityVcPage;
