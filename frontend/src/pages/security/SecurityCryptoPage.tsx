/**
 * 国密算法工具页面
 * SM2/SM3/SM4/SM9/ZUC 操作 + 统计卡片 + ECharts图表
 */
import React, { useState, useMemo } from 'react';
import { Button, Input } from 'tdesign-react';
import { RefreshIcon, LockOnIcon, KeyIcon, CheckCircleFilledIcon } from 'tdesign-icons-react';
import { useMutation } from '@tanstack/react-query';
import { sm2Sign, sm2Verify, sm2Encrypt, sm2Decrypt, sm3Hash, sm4Encrypt, sm4Decrypt, sm9Sign, sm9Verify, zucEncrypt } from '@/api/security';
import type { CryptoResult } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import ReactECharts from 'echarts-for-react';

/** 渲染结果卡片 */
const ResultCard: React.FC<{ title: string; result: CryptoResult | null }> = ({ title, result }) => {
  if (!result) return null;
  return (
    <div className="rounded-xl bg-white border border-gray-200 shadow-sm mt-3">
      <div className="p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">{title}</h4>
        <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
          <pre className="text-xs text-gray-600 whitespace-pre-wrap break-all">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};

const TAB_LABELS = ['SM2 签名/验签', 'SM2 加密/解密', 'SM3 哈希', 'SM4 加密/解密', 'SM9 签名/验签', 'ZUC 加密'];

const SecurityCryptoPage: React.FC = () => {
  const [tabValue, setTabValue] = useState<number>(0);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalOperations: 8520,
    encryption: 3200,
    signing: 2800,
    hashing: 2520,
  }), []);

  // ===== ECharts 配置 =====
  const operationTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['加密', '签名', '哈希'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '操作次数' },
    series: [
      { name: '加密', type: 'line', smooth: true, data: [320, 380, 420, 480, 450, 520, 460], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#2196f3' } },
      { name: '签名', type: 'line', smooth: true, data: [280, 320, 350, 400, 380, 420, 390], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#4caf50' } },
      { name: '哈希', type: 'line', smooth: true, data: [250, 290, 310, 350, 330, 380, 340], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  const algoDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '国密算法',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 2800, name: 'SM2', itemStyle: { color: '#2196f3' } },
          { value: 2520, name: 'SM3', itemStyle: { color: '#4caf50' } },
          { value: 1800, name: 'SM4', itemStyle: { color: '#ff9800' } },
          { value: 900, name: 'SM9', itemStyle: { color: '#9c27b0' } },
          { value: 500, name: 'ZUC', itemStyle: { color: '#f44336' } },
        ],
      },
    ],
  }), []);

  // SM2 签名
  const [sm2sPrivKey, setSm2sPrivKey] = useState('');
  const [sm2sPubKey, setSm2sPubKey] = useState('');
  const [sm2sData, setSm2sData] = useState('');
  const [sm2sResult, setSm2sResult] = useState<CryptoResult | null>(null);

  // SM2 验签
  const [sm2vPubKey, setSm2vPubKey] = useState('');
  const [sm2vData, setSm2vData] = useState('');
  const [sm2vSig, setSm2vSig] = useState('');
  const [sm2vResult, setSm2vResult] = useState<CryptoResult | null>(null);

  // SM2 加密
  const [sm2ePubKey, setSm2ePubKey] = useState('');
  const [sm2ePlain, setSm2ePlain] = useState('');
  const [sm2eResult, setSm2eResult] = useState<CryptoResult | null>(null);

  // SM2 解密
  const [sm2dPrivKey, setSm2dPrivKey] = useState('');
  const [sm2dPubKey, setSm2dPubKey] = useState('');
  const [sm2dCipher, setSm2dCipher] = useState('');
  const [sm2dResult, setSm2dResult] = useState<CryptoResult | null>(null);

  // SM3
  const [sm3Data, setSm3Data] = useState('');
  const [sm3Result, setSm3Result] = useState<CryptoResult | null>(null);

  // SM4 加密
  const [sm4eKey, setSm4eKey] = useState('');
  const [sm4ePlain, setSm4ePlain] = useState('');
  const [sm4eResult, setSm4eResult] = useState<CryptoResult | null>(null);

  // SM4 解密
  const [sm4dKey, setSm4dKey] = useState('');
  const [sm4dCipher, setSm4dCipher] = useState('');
  const [sm4dResult, setSm4dResult] = useState<CryptoResult | null>(null);

  // SM9 签名
  const [sm9sMasterPriv, setSm9sMasterPriv] = useState('');
  const [sm9sData, setSm9sData] = useState('');
  const [sm9sResult, setSm9sResult] = useState<CryptoResult | null>(null);

  // SM9 验签
  const [sm9vMasterPub, setSm9vMasterPub] = useState('');
  const [sm9vData, setSm9vData] = useState('');
  const [sm9vSig, setSm9vSig] = useState('');
  const [sm9vResult, setSm9vResult] = useState<CryptoResult | null>(null);

  // ZUC
  const [zucKey, setZucKey] = useState('');
  const [zucIv, setZucIv] = useState('');
  const [zucPlain, setZucPlain] = useState('');
  const [zucResult, setZucResult] = useState<CryptoResult | null>(null);

  // Mutations
  const sm2SignMut = useMutation({ mutationFn: sm2Sign, onSuccess: (r) => setSm2sResult(r.data ?? null) });
  const sm2VerifyMut = useMutation({ mutationFn: sm2Verify, onSuccess: (r) => setSm2vResult(r.data ?? null) });
  const sm2EncryptMut = useMutation({ mutationFn: sm2Encrypt, onSuccess: (r) => setSm2eResult(r.data ?? null) });
  const sm2DecryptMut = useMutation({ mutationFn: sm2Decrypt, onSuccess: (r) => setSm2dResult(r.data ?? null) });
  const sm3Mut = useMutation({ mutationFn: sm3Hash, onSuccess: (r) => setSm3Result(r.data ?? null) });
  const sm4EncryptMut = useMutation({ mutationFn: sm4Encrypt, onSuccess: (r) => setSm4eResult(r.data ?? null) });
  const sm4DecryptMut = useMutation({ mutationFn: sm4Decrypt, onSuccess: (r) => setSm4dResult(r.data ?? null) });
  const sm9SignMut = useMutation({ mutationFn: sm9Sign, onSuccess: (r) => setSm9sResult(r.data ?? null) });
  const sm9VerifyMut = useMutation({ mutationFn: sm9Verify, onSuccess: (r) => setSm9vResult(r.data ?? null) });
  const zucMut = useMutation({ mutationFn: zucEncrypt, onSuccess: (r) => setZucResult(r.data ?? null) });

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '安全中心' }, { label: '国密算法' }],
    [],
  );

  const inputField = (label: string, value: string, onChange: (v: string) => void, placeholder?: string, multiline?: boolean) => {
    if (multiline) {
      return (
        <div className="flex flex-col gap-1">
          <span className="text-sm text-gray-600">{label}</span>
          <textarea
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
            rows={3}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
          />
        </div>
      );
    }
    return (
      <Input
        label={label}
        value={value}
        onChange={(val) => onChange(String(val))}
        placeholder={placeholder}
      />
    );
  };

  return (
    <PageContainer>
      <PageHeader
        title="国密算法工具"
        subtitle="国密算法操作工具，支持 SM2/SM3/SM4/SM9/ZUC"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => {}, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        <MetricsCard title="总操作数" value={stats.totalOperations} icon={<LockOnIcon />} color="primary" />
        <MetricsCard title="加密操作" value={stats.encryption} icon={<KeyIcon />} color="success" />
        <MetricsCard title="签名操作" value={stats.signing} icon={<CheckCircleFilledIcon />} color="warning" />
        <MetricsCard title="哈希操作" value={stats.hashing} icon={<CheckCircleFilledIcon />} color="secondary" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8">
          <ChartCard title="国密算法使用趋势" option={operationTrendOption} height={300} />
        </div>
        <div className="lg:col-span-4">
          <ChartCard title="算法类型分布" option={algoDistOption} height={300} />
        </div>
      </div>

      {/* 标签页 + 操作区域 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm">
        {/* 自定义 Tab 栏 */}
        <div className="flex border-b border-gray-200 overflow-x-auto">
          {TAB_LABELS.map((label, idx) => (
            <button
              key={label}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                tabValue === idx
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setTabValue(idx)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {/* SM2 签名/验签 */}
          {tabValue === 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM2 签名</h4>
                <div className="flex flex-col gap-3">
                  {inputField('私钥', sm2sPrivKey, setSm2sPrivKey, 'Base64 编码私钥')}
                  {inputField('公钥', sm2sPubKey, setSm2sPubKey, 'Base64 编码公钥')}
                  {inputField('待签名数据', sm2sData, setSm2sData, '原始数据', true)}
                  <Button theme="primary" disabled={!sm2sPrivKey || !sm2sPubKey || !sm2sData} onClick={() => sm2SignMut.mutate({ private_key: sm2sPrivKey, public_key: sm2sPubKey, data: sm2sData })}>签名</Button>
                </div>
                <ResultCard title="签名结果" result={sm2sResult} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM2 验签</h4>
                <div className="flex flex-col gap-3">
                  {inputField('公钥', sm2vPubKey, setSm2vPubKey, 'Base64 编码公钥')}
                  {inputField('原始数据', sm2vData, setSm2vData, '原始数据', true)}
                  {inputField('签名', sm2vSig, setSm2vSig, 'Base64 编码签名')}
                  <Button theme="primary" disabled={!sm2vPubKey || !sm2vData || !sm2vSig} onClick={() => sm2VerifyMut.mutate({ public_key: sm2vPubKey, data: sm2vData, signature: sm2vSig })}>验签</Button>
                </div>
                <ResultCard title="验签结果" result={sm2vResult} />
              </div>
            </div>
          )}

          {/* SM2 加密/解密 */}
          {tabValue === 1 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM2 加密</h4>
                <div className="flex flex-col gap-3">
                  {inputField('公钥', sm2ePubKey, setSm2ePubKey, 'Base64 编码公钥')}
                  {inputField('明文', sm2ePlain, setSm2ePlain, '待加密数据', true)}
                  <Button theme="primary" disabled={!sm2ePubKey || !sm2ePlain} onClick={() => sm2EncryptMut.mutate({ public_key: sm2ePubKey, plaintext: sm2ePlain })}>加密</Button>
                </div>
                <ResultCard title="加密结果" result={sm2eResult} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM2 解密</h4>
                <div className="flex flex-col gap-3">
                  {inputField('私钥', sm2dPrivKey, setSm2dPrivKey, 'Base64 编码私钥')}
                  {inputField('公钥', sm2dPubKey, setSm2dPubKey, 'Base64 编码公钥')}
                  {inputField('密文', sm2dCipher, setSm2dCipher, 'Base64 编码密文', true)}
                  <Button theme="primary" disabled={!sm2dPrivKey || !sm2dPubKey || !sm2dCipher} onClick={() => sm2DecryptMut.mutate({ private_key: sm2dPrivKey, public_key: sm2dPubKey, ciphertext: sm2dCipher })}>解密</Button>
                </div>
                <ResultCard title="解密结果" result={sm2dResult} />
              </div>
            </div>
          )}

          {/* SM3 哈希 */}
          {tabValue === 2 && (
            <div className="max-w-xl">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">SM3 哈希</h4>
              <div className="flex flex-col gap-3">
                {inputField('待哈希数据', sm3Data, setSm3Data, '输入数据', true)}
                <Button theme="primary" disabled={!sm3Data} onClick={() => sm3Mut.mutate({ data: sm3Data })}>计算哈希</Button>
              </div>
              <ResultCard title="哈希结果" result={sm3Result} />
            </div>
          )}

          {/* SM4 加密/解密 */}
          {tabValue === 3 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM4 加密</h4>
                <div className="flex flex-col gap-3">
                  {inputField('密钥 (Hex)', sm4eKey, setSm4eKey, '16字节 Hex 密钥')}
                  {inputField('明文', sm4ePlain, setSm4ePlain, '待加密数据', true)}
                  <Button theme="primary" disabled={!sm4eKey || !sm4ePlain} onClick={() => sm4EncryptMut.mutate({ key: sm4eKey, plaintext: sm4ePlain })}>加密</Button>
                </div>
                <ResultCard title="加密结果" result={sm4eResult} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM4 解密</h4>
                <div className="flex flex-col gap-3">
                  {inputField('密钥 (Hex)', sm4dKey, setSm4dKey, '16字节 Hex 密钥')}
                  {inputField('密文', sm4dCipher, setSm4dCipher, 'Base64/Hex 编码密文', true)}
                  <Button theme="primary" disabled={!sm4dKey || !sm4dCipher} onClick={() => sm4DecryptMut.mutate({ key: sm4dKey, ciphertext: sm4dCipher })}>解密</Button>
                </div>
                <ResultCard title="解密结果" result={sm4dResult} />
              </div>
            </div>
          )}

          {/* SM9 签名/验签 */}
          {tabValue === 4 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM9 签名</h4>
                <div className="flex flex-col gap-3">
                  {inputField('主私钥', sm9sMasterPriv, setSm9sMasterPriv, 'Base64 编码主私钥')}
                  {inputField('待签名数据', sm9sData, setSm9sData, '原始数据', true)}
                  <Button theme="primary" disabled={!sm9sMasterPriv || !sm9sData} onClick={() => sm9SignMut.mutate({ master_private_key: sm9sMasterPriv, data: sm9sData })}>签名</Button>
                </div>
                <ResultCard title="签名结果" result={sm9sResult} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">SM9 验签</h4>
                <div className="flex flex-col gap-3">
                  {inputField('主公钥', sm9vMasterPub, setSm9vMasterPub, 'Base64 编码主公钥')}
                  {inputField('原始数据', sm9vData, setSm9vData, '原始数据', true)}
                  {inputField('签名', sm9vSig, setSm9vSig, 'Base64 编码签名')}
                  <Button theme="primary" disabled={!sm9vMasterPub || !sm9vData || !sm9vSig} onClick={() => sm9VerifyMut.mutate({ master_public_key: sm9vMasterPub, data: sm9vData, signature: sm9vSig })}>验签</Button>
                </div>
                <ResultCard title="验签结果" result={sm9vResult} />
              </div>
            </div>
          )}

          {/* ZUC 加密 */}
          {tabValue === 5 && (
            <div className="max-w-xl">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">ZUC 加密</h4>
              <div className="flex flex-col gap-3">
                {inputField('密钥 (Hex)', zucKey, setZucKey, '16字节 Hex 密钥')}
                {inputField('IV (Hex)', zucIv, setZucIv, '16字节 Hex 初始向量')}
                {inputField('明文', zucPlain, setZucPlain, '待加密数据', true)}
                <Button theme="primary" disabled={!zucKey || !zucIv || !zucPlain} onClick={() => zucMut.mutate({ key: zucKey, iv: zucIv, plaintext: zucPlain })}>加密</Button>
              </div>
              <ResultCard title="加密结果" result={zucResult} />
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
};

export default SecurityCryptoPage;
