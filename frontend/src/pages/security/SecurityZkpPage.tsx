/**
 * 零知识证明页面
 * Groth16 / BBS+ / Bulletproofs + 统计卡片 + ECharts图表
 */
import React, { useState, useMemo } from 'react';
import { Button, Input } from 'tdesign-react';
import {
  RefreshIcon, ShieldErrorFilledIcon, VerifiedIcon, CheckCircleFilledIcon,
} from 'tdesign-icons-react';
import { useMutation } from '@tanstack/react-query';
import {
  groth16Prove, groth16Verify, bbsSign, bbsVerify, bulletproofsProve, bulletproofsVerify } from '@/api/security';
import type { ZkpProof } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import ReactECharts from 'echarts-for-react';

/** 渲染结果卡片 */
const ZkpResultCard: React.FC<{ title: string; result: Record<string, unknown> | null }> = ({ title, result }) => {
  if (!result) return null;
  return (
    <div className="rounded-xl bg-white border border-gray-200 mt-4">
      <div className="p-4">
        <h4 className="text-sm font-semibold text-gray-800 mb-2">{title}</h4>
        <div className="p-3 bg-gray-900 rounded-lg">
          <pre className="whitespace-pre-wrap font-mono text-xs text-gray-300 m-0">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};

const TAB_LABELS = ['Groth16', 'BBS+ 签名', 'Bulletproofs'];

const SecurityZkpPage: React.FC = () => {
  const [tabValue, setTabValue] = useState<number>(0);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalProofs: 1256,
    verified: 1180,
    successRate: 94,
    todayProofs: 42 }), []);

  // ===== ECharts 配置 =====
  const proofTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['证明生成', '验证通过'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '次数' },
    series: [
      { name: '证明生成', type: 'bar', data: [120, 150, 180, 200, 165, 190, 145], itemStyle: { color: '#2196f3' } },
      { name: '验证通过', type: 'bar', data: [112, 142, 170, 192, 158, 182, 138], itemStyle: { color: '#4caf50' } },
    ] }), []);

  const algoDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: 'ZKP算法',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 520, name: 'Groth16', itemStyle: { color: '#2196f3' } },
          { value: 380, name: 'BBS+', itemStyle: { color: '#4caf50' } },
          { value: 356, name: 'Bulletproofs', itemStyle: { color: '#ff9800' } },
        ] },
    ] }), []);

  // Groth16
  const [g16CircuitId, setG16CircuitId] = useState('');
  const [g16PrivInput, setG16PrivInput] = useState('{}');
  const [g16PubInput, setG16PubInput] = useState('{}');
  const [g16ProveResult, setG16ProveResult] = useState<ZkpProof | null>(null);

  const [g16vProof, setG16vProof] = useState('{}');
  const [g16vSignals, setG16vSignals] = useState('[]');
  const [g16vResult, setG16vResult] = useState<{ is_valid: boolean } | null>(null);

  // BBS+
  const [bbsPrivKey, setBbsPrivKey] = useState('');
  const [bbsMessages, setBbsMessages] = useState('["message1", "message2"]');
  const [bbsSignResult, setBbsSignResult] = useState<ZkpProof | null>(null);

  const [bbsvPubKey, setBbsvPubKey] = useState('');
  const [bbsvMessages, setBbsvMessages] = useState('["message1", "message2"]');
  const [bbsvSignature, setBbsvSignature] = useState('{}');
  const [bbsvResult, setBbsvResult] = useState<{ is_valid: boolean } | null>(null);

  // Bulletproofs
  const [bpValue, setBpValue] = useState<number>(100);
  const [bpMinVal, setBpMinVal] = useState<number>(0);
  const [bpMaxVal, setBpMaxVal] = useState<number>(1000);
  const [bpProveResult, setBpProveResult] = useState<ZkpProof | null>(null);

  const [bpvProof, setBpvProof] = useState('{}');
  const [bpvMinVal, setBpvMinVal] = useState<number>(0);
  const [bpvMaxVal, setBpvMaxVal] = useState<number>(1000);
  const [bpvResult, setBpvResult] = useState<{ is_valid: boolean } | null>(null);

  // Mutations
  const g16ProveMut = useMutation({ mutationFn: groth16Prove, onSuccess: (r) => setG16ProveResult(r.data ?? null) });
  const g16VerifyMut = useMutation({ mutationFn: groth16Verify, onSuccess: (r) => setG16vResult(r.data ?? null) });
  const bbsSignMut = useMutation({ mutationFn: bbsSign, onSuccess: (r) => setBbsSignResult(r.data ?? null) });
  const bbsVerifyMut = useMutation({ mutationFn: bbsVerify, onSuccess: (r) => setBbsvResult(r.data ?? null) });
  const bpProveMut = useMutation({ mutationFn: bulletproofsProve, onSuccess: (r) => setBpProveResult(r.data ?? null) });
  const bpVerifyMut = useMutation({ mutationFn: bulletproofsVerify, onSuccess: (r) => setBpvResult(r.data ?? null) });

  /** 安全解析 JSON */
  const parseJson = (str: string): Record<string, unknown> => {
    try { return JSON.parse(str || '{}'); } catch { return {}; }
  };
  const parseJsonArr = (str: string): string[] => {
    try { return JSON.parse(str || '[]'); } catch { return []; }
  };

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '零知识证明' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="零知识证明"
        subtitle="ZKP 操作工具：Groth16 / BBS+ / Bulletproofs"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => {}, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总证明数" value={stats.totalProofs} icon={<ShieldErrorFilledIcon />} gradient="purple" unit="" />
        <MetricsCard title="验证通过" value={stats.verified} icon={<VerifiedIcon />} gradient="green" unit="" />
        <MetricsCard title="成功率" value={stats.successRate} icon={<CheckCircleFilledIcon />} gradient="cyan" unit="%" />
        <MetricsCard title="今日证明" value={stats.todayProofs} icon={<CheckCircleFilledIcon />} color="warning" unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8"><ChartCard title="证明生成趋势" option={proofTrendOption} height={300} /></div>
        <div className="lg:col-span-4"><ChartCard title="ZKP算法分布" option={algoDistOption} height={300} /></div>
      </div>

      <div className="rounded-xl bg-white border border-gray-200 p-4 flex-1">
        {/* 自定义 Tab 栏 */}
        <div className="flex border-b border-gray-200 mb-4">
          {TAB_LABELS.map((label, i) => (
            <button
              key={i}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tabValue === i
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setTabValue(i)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Groth16 */}
        {tabValue === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Groth16 证明</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">Circuit ID</label>
                  <Input value={g16CircuitId} onChange={(val) => setG16CircuitId(String(val))} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">私有输入 (JSON)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={g16PrivInput} onChange={(e) => setG16PrivInput(e.target.value)} rows={3} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">公开输入 (JSON)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={g16PubInput} onChange={(e) => setG16PubInput(e.target.value)} rows={3} />
                </div>
                <Button theme="primary" disabled={!g16CircuitId.trim()} onClick={() => g16ProveMut.mutate({ circuit_id: g16CircuitId, private_input: parseJson(g16PrivInput), public_input: parseJson(g16PubInput) })}>
                  生成证明
                </Button>
              </div>
              <ZkpResultCard title="证明结果" result={g16ProveResult as unknown as Record<string, unknown> | null} />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Groth16 验证</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">Proof (JSON)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={g16vProof} onChange={(e) => setG16vProof(e.target.value)} rows={3} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">Public Signals (JSON Array)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={g16vSignals} onChange={(e) => setG16vSignals(e.target.value)} rows={3} />
                </div>
                <Button theme="primary" onClick={() => g16VerifyMut.mutate({ proof: parseJson(g16vProof), public_signals: parseJsonArr(g16vSignals) })}>
                  验证证明
                </Button>
              </div>
              {g16vResult && (
                <div className={`rounded-xl border border-gray-200 mt-4 ${g16vResult.is_valid ? 'bg-green-50' : 'bg-red-50'}`}>
                  <div className="p-4">
                    <h4 className={`text-sm font-semibold ${g16vResult.is_valid ? 'text-green-700' : 'text-red-700'}`}>
                      {g16vResult.is_valid ? '✓ 验证通过' : '✗ 验证失败'}
                    </h4>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* BBS+ */}
        {tabValue === 1 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">BBS+ 签名</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">私钥</label>
                  <Input value={bbsPrivKey} onChange={(val) => setBbsPrivKey(String(val))} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">消息列表 (JSON Array)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={bbsMessages} onChange={(e) => setBbsMessages(e.target.value)} rows={3} />
                </div>
                <Button theme="primary" disabled={!bbsPrivKey.trim()} onClick={() => bbsSignMut.mutate({ private_key: bbsPrivKey, messages: parseJsonArr(bbsMessages) })}>
                  生成签名
                </Button>
              </div>
              <ZkpResultCard title="签名结果" result={bbsSignResult as unknown as Record<string, unknown> | null} />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">BBS+ 验证</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">公钥</label>
                  <Input value={bbsvPubKey} onChange={(val) => setBbsvPubKey(String(val))} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">消息列表 (JSON Array)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={bbsvMessages} onChange={(e) => setBbsvMessages(e.target.value)} rows={3} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">签名 (JSON)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={bbsvSignature} onChange={(e) => setBbsvSignature(e.target.value)} rows={3} />
                </div>
                <Button theme="primary" disabled={!bbsvPubKey.trim()} onClick={() => bbsVerifyMut.mutate({ public_key: bbsvPubKey, messages: parseJsonArr(bbsvMessages), signature: parseJson(bbsvSignature) })}>
                  验证签名
                </Button>
              </div>
              {bbsvResult && (
                <div className={`rounded-xl border border-gray-200 mt-4 ${bbsvResult.is_valid ? 'bg-green-50' : 'bg-red-50'}`}>
                  <div className="p-4">
                    <h4 className={`text-sm font-semibold ${bbsvResult.is_valid ? 'text-green-700' : 'text-red-700'}`}>
                      {bbsvResult.is_valid ? '✓ 验证通过' : '✗ 验证失败'}
                    </h4>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Bulletproofs */}
        {tabValue === 2 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Bulletproofs 范围证明</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">值</label>
                  <Input value={String(bpValue)} onChange={(val) => setBpValue(parseFloat(String(val)) || 0)} type="number" />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">最小值（可选）</label>
                  <Input value={String(bpMinVal)} onChange={(val) => setBpMinVal(parseFloat(String(val)) || 0)} type="number" />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">最大值（可选）</label>
                  <Input value={String(bpMaxVal)} onChange={(val) => setBpMaxVal(parseFloat(String(val)) || 0)} type="number" />
                </div>
                <Button theme="primary" onClick={() => bpProveMut.mutate({ value: bpValue, min_val: bpMinVal || undefined, max_val: bpMaxVal || undefined })}>
                  生成证明
                </Button>
              </div>
              <ZkpResultCard title="证明结果" result={bpProveResult as unknown as Record<string, unknown> | null} />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Bulletproofs 验证</h4>
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">Proof (JSON)</label>
                  <textarea className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none" value={bpvProof} onChange={(e) => setBpvProof(e.target.value)} rows={4} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">最小值（可选）</label>
                  <Input value={String(bpvMinVal)} onChange={(val) => setBpvMinVal(parseFloat(String(val)) || 0)} type="number" />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm text-gray-600">最大值（可选）</label>
                  <Input value={String(bpvMaxVal)} onChange={(val) => setBpvMaxVal(parseFloat(String(val)) || 0)} type="number" />
                </div>
                <Button theme="primary" onClick={() => bpVerifyMut.mutate({ proof: parseJson(bpvProof), min_val: bpvMinVal || undefined, max_val: bpvMaxVal || undefined })}>
                  验证证明
                </Button>
              </div>
              {bpvResult && (
                <div className={`rounded-xl border border-gray-200 mt-4 ${bpvResult.is_valid ? 'bg-green-50' : 'bg-red-50'}`}>
                  <div className="p-4">
                    <h4 className={`text-sm font-semibold ${bpvResult.is_valid ? 'text-green-700' : 'text-red-700'}`}>
                      {bpvResult.is_valid ? '✓ 验证通过' : '✗ 验证失败'}
                    </h4>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
};

export default SecurityZkpPage;
