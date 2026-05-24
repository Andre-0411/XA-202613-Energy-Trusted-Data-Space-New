/**
 * 密钥管理页面
 * 密钥列表 + 生成 + 轮换 + 审计日志 + Shamir 分片
 */
import React, { useState, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tooltip, Pagination } from 'tdesign-react';
import { AddIcon, RefreshIcon, KeyIcon, CheckCircleFilledIcon, RefreshIcon as AutorenewIcon, ErrorCircleFilledIcon, HistoryIcon } from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listKeys, generateKey, rotateKey, getKeyAuditLog, shamirSplit } from '@/api/security';
import type { KeyInfo } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import ConfirmDialog from '@/components/ConfirmDialog';
import LoadingOverlay from '@/components/LoadingOverlay';

const ALGORITHM_OPTIONS = ['SM2', 'SM4', 'SM9', 'ZUC', 'AES', 'RSA'];
const HIERARCHY_OPTIONS = [
  { value: 'MASTER', label: '主密钥' },
  { value: 'DATA', label: '数据密钥' },
  { value: 'SESSION', label: '会话密钥' },
];

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'ACTIVE', label: '活跃' },
  { value: 'INACTIVE', label: '停用' },
  { value: 'COMPROMISED', label: '已泄露' },
  { value: 'ROTATED', label: '已轮换' },
];

const keyStatusLabel = (s: string): string => {
  const m: Record<string, string> = { ACTIVE: '活跃', INACTIVE: '停用', COMPROMISED: '已泄露', ROTATED: '已轮换' };
  return m[s] ?? s;
};

const keyStatusColor = (s: string): 'success' | 'error' | 'info' | 'default' => {
  const m: Record<string, 'success' | 'error' | 'info'> = { ACTIVE: 'success', INACTIVE: 'error', COMPROMISED: 'error', ROTATED: 'info' };
  return m[s] ?? 'default';
};

const SecurityKeysPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== ECharts 配置 =====
  const keyTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增密钥', '轮换密钥'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增密钥', type: 'bar', data: [18, 22, 25, 20, 28, 32, 35], itemStyle: { color: '#667eea' } },
      { name: '轮换密钥', type: 'line', smooth: true, data: [5, 8, 6, 9, 7, 10, 12], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const algorithmDistributionOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '算法类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 85, name: 'SM2', itemStyle: { color: '#667eea' } },
          { value: 68, name: 'SM4', itemStyle: { color: '#43e97b' } },
          { value: 45, name: 'SM9', itemStyle: { color: '#f093fb' } },
          { value: 32, name: 'AES', itemStyle: { color: '#4facfe' } },
          { value: 26, name: 'RSA', itemStyle: { color: '#ff9800' } },
        ],
      },
    ],
  }), []);

  // ===== 筛选 & 分页 =====
  const [filterAlgorithm, setFilterAlgorithm] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 生成密钥弹窗 =====
  const [genOpen, setGenOpen] = useState<boolean>(false);
  const [genAlgorithm, setGenAlgorithm] = useState<string>('SM2');
  const [genHierarchy, setGenHierarchy] = useState<string>('DATA');
  const [genPurpose, setGenPurpose] = useState<string>('');
  const [genParentKeyId, setGenParentKeyId] = useState<string>('');

  // ===== 轮换确认 =====
  const [rotateTarget, setRotateTarget] = useState<KeyInfo | null>(null);

  // ===== 审计日志弹窗 =====
  const [auditOpen, setAuditOpen] = useState<boolean>(false);
  const [auditKeyId, setAuditKeyId] = useState<string>('');
  const [auditPage, setAuditPage] = useState<number>(1);

  // ===== Shamir 分片弹窗 =====
  const [shamirOpen, setShamirOpen] = useState<boolean>(false);
  const [shamirSecret, setShamirSecret] = useState<string>('');
  const [shamirN, setShamirN] = useState<number>(5);
  const [shamirK, setShamirK] = useState<number>(3);
  const [shamirResult, setShamirResult] = useState<Record<string, unknown>[] | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['keys', page, pageSize, filterAlgorithm, filterStatus],
    queryFn: () => listKeys({ page, page_size: pageSize, algorithm: filterAlgorithm || undefined, status: filterStatus || undefined }),
  });

  const { data: auditData } = useQuery({
    queryKey: ['keyAuditLog', auditKeyId, auditPage],
    queryFn: () => getKeyAuditLog(auditKeyId, { page: auditPage, page_size: 5 }),
    enabled: auditOpen && !!auditKeyId,
  });

  const items: KeyInfo[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;
  const auditItems: Record<string, unknown>[] = auditData?.data?.items ?? [];
  const auditTotal: number = auditData?.data?.total ?? 0;

  // ===== 统计数据 - 从API数据推导 =====
  const stats = useMemo(() => ({
    totalKeys: total,
    activeKeys: items.filter(k => k.status === 'active').length,
    rotatedKeys: items.filter(k => k.status === 'rotated').length,
    compromisedKeys: items.filter(k => k.status === 'compromised').length,
  }), [items, total]);

  // ===== Mutations =====
  const genMut = useMutation({
    mutationFn: (d: { algorithm: string; hierarchy_level: string; purpose: string; parent_key_id?: string }) => generateKey(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keys'] });
      setGenOpen(false);
      setGenAlgorithm('SM2'); setGenHierarchy('DATA'); setGenPurpose(''); setGenParentKeyId('');
    },
  });

  const rotateMut = useMutation({
    mutationFn: (keyId: string) => rotateKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keys'] });
      setRotateTarget(null);
    },
  });

  const shamirMut = useMutation({
    mutationFn: (d: { secret: string; n: number; k: number }) => shamirSplit(d),
    onSuccess: (res) => { setShamirResult(res.data?.shares ?? null); },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '密钥管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '生成密钥', icon: <AddIcon />, onClick: () => setGenOpen(true), variant: 'contained' },
      { label: 'Shamir 分片', icon: <KeyIcon />, onClick: () => { setShamirResult(null); setShamirOpen(true); }, variant: 'outlined' },
    ],
    [],
  );

  const algorithmSelectOptions = [
    { value: '', label: '全部' },
    ...ALGORITHM_OPTIONS.map(a => ({ value: a, label: a })),
  ];

  const genAlgorithmOptions = ALGORITHM_OPTIONS.map(a => ({ value: a, label: a }));
  const genHierarchyOptions = HIERARCHY_OPTIONS.map(h => ({ value: h.value, label: h.label }));

  return (
    <PageContainer>
      <PageHeader
        title="密钥管理"
        subtitle="管理密钥生命周期，支持生成、轮换与审计"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['keys'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总密钥数" value={stats.totalKeys} icon={<KeyIcon />} color="primary" />
        <MetricsCard title="活跃密钥" value={stats.activeKeys} icon={<CheckCircleFilledIcon />} color="success" />
        <MetricsCard title="已轮换" value={stats.rotatedKeys} icon={<RefreshIcon />} color="warning" />
        <MetricsCard title="已泄露" value={stats.compromisedKeys} icon={<ErrorCircleFilledIcon />} color="error" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8"><ChartCard title="密钥增长趋势" option={keyTrendOption} height={300} /></div>
        <div className="lg:col-span-4"><ChartCard title="算法类型分布" option={algorithmDistributionOption} height={300} /></div>
      </div>

      {/* 筛选栏 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 whitespace-nowrap">算法</span>
            <Select
              value={filterAlgorithm}
              options={algorithmSelectOptions}
              onChange={(val) => { setFilterAlgorithm(String(val)); setPage(1); }}
              style={{ width: 120 }}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 whitespace-nowrap">状态</span>
            <Select
              value={filterStatus}
              options={STATUS_OPTIONS}
              onChange={(val) => { setFilterStatus(String(val)); setPage(1); }}
              style={{ width: 120 }}
            />
          </div>
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Key ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">算法</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">层级</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">用途</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">状态</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">父密钥</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">创建时间</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row) => (
                <tr key={row.key_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3"><span className="text-xs text-gray-600">{row.key_id.slice(0, 16)}...</span></td>
                  <td className="px-4 py-3">{row.algorithm}</td>
                  <td className="px-4 py-3">{HIERARCHY_OPTIONS.find((h) => h.value === row.hierarchy_level)?.label ?? row.hierarchy_level}</td>
                  <td className="px-4 py-3">{row.purpose}</td>
                  <td className="px-4 py-3"><StatusTag status={keyStatusLabel(row.status)} color={keyStatusColor(row.status)} /></td>
                  <td className="px-4 py-3">{row.parent_key_id ?? '—'}</td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="轮换密钥">
                        <span
                          className={`cursor-pointer rounded p-1 inline-flex items-center ${row.status !== 'ACTIVE' ? 'opacity-40 cursor-not-allowed' : 'hover:bg-gray-100'}`}
                          onClick={() => row.status === 'ACTIVE' && setRotateTarget(row)}
                        >
                          <RefreshIcon className="text-orange-500" size="16px" />
                        </span>
                      </Tooltip>
                      <Tooltip content="审计日志">
                        <span
                          className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
                          onClick={() => { setAuditKeyId(row.key_id); setAuditPage(1); setAuditOpen(true); }}
                        >
                          <HistoryIcon className="text-blue-500" size="16px" />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-end px-4 py-3 border-t border-gray-100">
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            showPageSize
            pageSizeOptions={[10, 20, 50]}
            onChange={(pagInfo) => {
              setPage(pagInfo.current);
              setPageSize(pagInfo.pageSize);
            }}
          />
        </div>
      </div>

      {/* 生成密钥弹窗 */}
      <Dialog
        visible={genOpen}
        onClose={() => setGenOpen(false)}
        header="生成密钥"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setGenOpen(false)}>取消</Button>
            <Button theme="primary" disabled={!genPurpose.trim()} onClick={() => genMut.mutate({ algorithm: genAlgorithm, hierarchy_level: genHierarchy, purpose: genPurpose, parent_key_id: genParentKeyId || undefined })}>生成</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-sm text-gray-600 mb-1 block">算法</span>
            <Select value={genAlgorithm} options={genAlgorithmOptions} onChange={(val) => setGenAlgorithm(String(val))} />
          </div>
          <div>
            <span className="text-sm text-gray-600 mb-1 block">层级</span>
            <Select value={genHierarchy} options={genHierarchyOptions} onChange={(val) => setGenHierarchy(String(val))} />
          </div>
          <Input label="用途" value={genPurpose} onChange={(val) => setGenPurpose(String(val))} placeholder="数据加密 / 签名验证" />
          <Input label="父密钥 ID（可选）" value={genParentKeyId} onChange={(val) => setGenParentKeyId(String(val))} />
        </div>
      </Dialog>

      {/* 轮换确认 */}
      <ConfirmDialog
        open={!!rotateTarget}
        title="轮换密钥"
        message={`确定要轮换密钥「${rotateTarget?.key_id?.slice(0, 16) ?? ''}...」吗？旧密钥将被标记为已轮换。`}
        type="warning"
        onConfirm={() => rotateTarget && rotateMut.mutate(rotateTarget.key_id)}
        onCancel={() => setRotateTarget(null)}
        loading={rotateMut.isPending}
      />

      {/* 审计日志弹窗 */}
      <Dialog
        visible={auditOpen}
        onClose={() => setAuditOpen(false)}
        header="审计日志"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setAuditOpen(false)}>关闭</Button>
          </div>
        }
      >
        {auditItems.length === 0 ? (
          <span className="text-gray-400">暂无审计记录</span>
        ) : (
          <div className="flex flex-col gap-2">
            {auditItems.map((log, idx) => (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3" key={idx}>
                <pre className="text-xs text-gray-600 whitespace-pre-wrap break-all">
                  {JSON.stringify(log, null, 2)}
                </pre>
              </div>
            ))}
            <div className="flex items-center justify-center gap-2 mt-2">
              <Button disabled={auditPage === 1} onClick={() => setAuditPage((p) => p - 1)}>上一页</Button>
              <span className="text-xs text-gray-600">第 {auditPage} 页</span>
              <Button disabled={auditPage * 5 >= auditTotal} onClick={() => setAuditPage((p) => p + 1)}>下一页</Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Shamir 分片弹窗 */}
      <Dialog
        visible={shamirOpen}
        onClose={() => { setShamirOpen(false); setShamirResult(null); }}
        header="Shamir 分片"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => { setShamirOpen(false); setShamirResult(null); }}>关闭</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <Input label="秘密值" value={shamirSecret} onChange={(val) => setShamirSecret(String(val))} />
          <Input label="总分片数 (n)" type="number" value={String(shamirN)} onChange={(val) => setShamirN(parseInt(String(val), 10) || 5)} />
          <Input label="恢复阈值 (k)" type="number" value={String(shamirK)} onChange={(val) => setShamirK(parseInt(String(val), 10) || 3)} />
          <Button theme="primary" disabled={!shamirSecret.trim()} onClick={() => shamirMut.mutate({ secret: shamirSecret, n: shamirN, k: shamirK })}>
            执行分片
          </Button>
          {shamirResult && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">分片结果 ({shamirResult.length} 片)</h4>
              <pre className="text-xs text-gray-600 whitespace-pre-wrap break-all">
                {JSON.stringify(shamirResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default SecurityKeysPage;
