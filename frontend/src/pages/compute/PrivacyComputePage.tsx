/**
 * 隐私计算演示页面
 * 四种隐私计算技术完整演示：联邦学习 / MPC安全计算 / 同态加密 / TEE可信执行环境
 * 包含交互式演示、动画效果、ECharts图表
 */
import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { Button, Input, Tag, Select, Slider, Progress, Divider, Textarea } from 'tdesign-react';
import {
  RefreshIcon, PlayIcon, SaveIcon, LockOnIcon, LockOffIcon,
  CheckCircleIcon, CloseCircleIcon, InfoCircleIcon,
  CloudIcon, ServerIcon, DataBaseIcon, FileIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

// ==================== 类型定义 ====================

type TechType = 'FL' | 'MPC' | 'HE' | 'TEE';

interface TechCard {
  type: TechType;
  name: string;
  icon: React.ReactNode;
  description: string;
  scenarios: string[];
  color: string;
  gradient: string;
}

interface FlParty {
  id: string;
  name: string;
  dataCount: number;
  dataSize: string;
  status: 'idle' | 'training' | 'done';
}

interface MpcParty {
  id: string;
  name: string;
  privateValue: number;
  share: number[];
  color: string;
}

interface TrainingRound {
  round: number;
  loss: number;
  accuracy: number;
  valLoss: number;
  valAccuracy: number;
}

interface TeeStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'done';
  description: string;
}

// ==================== 常量 ====================

const TECH_CARDS: TechCard[] = [
  {
    type: 'FL',
    name: '联邦学习',
    icon: <CloudIcon size="28px" />,
    description: '多方数据不出域，模型参数聚合训练',
    scenarios: ['负荷预测', '需求响应', '设备故障诊断'],
    color: '#667eea',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  {
    type: 'MPC',
    name: '安全多方计算',
    icon: <LockOnIcon size="28px" />,
    description: '多方秘密分享，不泄露各方私有数据',
    scenarios: ['电价协商', '联合统计', '安全结算'],
    color: '#f093fb',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  },
  {
    type: 'HE',
    name: '同态加密',
    icon: <LockOnIcon size="28px" />,
    description: '密文直接计算，结果解密后与明文一致',
    scenarios: ['隐私查询', '安全审计', '数据聚合'],
    color: '#4facfe',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  },
  {
    type: 'TEE',
    name: '可信执行环境',
    icon: <ServerIcon size="28px" />,
    description: '硬件安全隔离，数据在可信环境中处理',
    scenarios: ['碳排放核算', '调度优化', '敏感数据分析'],
    color: '#43e97b',
    gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  },
];

const FL_DATASETS = [
  { value: 'electricity', label: '电力负荷数据集 (12,480条)' },
  { value: 'weather', label: '气象数据集 (8,320条)' },
  { value: 'price', label: '电价数据集 (6,144条)' },
  { value: 'carbon', label: '碳排放数据集 (4,096条)' },
];

const FL_ALGORITHMS = [
  { value: 'fedavg', label: 'FedAvg (联邦平均)' },
  { value: 'fedprox', label: 'FedProx (近端优化)' },
  { value: 'fednova', label: 'FedNova (异步聚合)' },
  { value: 'scaffold', label: 'SCAFFOLD (控制变量)' },
];

const MPC_PROTOCOLS = [
  { value: 'secret_sharing', label: '秘密分享 (SS)' },
  { value: 'garbled_circuit', label: '混淆电路 (GC)' },
  { value: 'homomorphic', label: '同态加密 (HE)' },
  { value: 'ot', label: '不经意传输 (OT)' },
];

const MPC_OPERATIONS = [
  { value: 'sum', label: '安全求和' },
  { value: 'avg', label: '安全求平均' },
  { value: 'max', label: '安全求最大值' },
  { value: 'compare', label: '安全比较' },
  { value: 'rank', label: '安全排序' },
];

const HE_SCHEMES = [
  { value: 'bfv', label: 'BFV (整数运算)' },
  { value: 'bgv', label: 'BGV (整数运算)' },
  { value: 'ckks', label: 'CKKS (近似浮点)' },
  { value: 'tfhe', label: 'TFHE (布尔电路)' },
];

const HE_OPERATIONS = [
  { value: 'add', label: '密文加法' },
  { value: 'multiply', label: '密文乘法' },
  { value: 'dot_product', label: '内积运算' },
  { value: 'polynomial', label: '多项式求值' },
];

const TEE_RUNTIMES = [
  { value: 'sgx', label: 'Intel SGX' },
  { value: 'sev', label: 'AMD SEV' },
  { value: 'trustzone', label: 'ARM TrustZone' },
  { value: 'nitro', label: 'AWS Nitro Enclaves' },
];

// ==================== 工具函数 ====================

const generateTrainingData = (rounds: number): TrainingRound[] => {
  const data: TrainingRound[] = [];
  let loss = 2.5;
  let acc = 0.15;
  let valLoss = 2.8;
  let valAcc = 0.12;
  for (let i = 1; i <= rounds; i++) {
    const decay = Math.exp(-i / (rounds * 0.35));
    loss = loss * (0.92 + Math.random() * 0.06) + 0.01 * decay;
    acc = Math.min(0.98, acc + (1 - acc) * (0.08 + Math.random() * 0.04) * decay);
    valLoss = loss + 0.1 + Math.random() * 0.15;
    valAcc = Math.min(0.95, acc - 0.02 - Math.random() * 0.04);
    data.push({
      round: i,
      loss: Math.max(0.02, loss),
      accuracy: Math.min(0.99, acc),
      valLoss: Math.max(0.05, valLoss),
      valAccuracy: Math.min(0.97, valAcc),
    });
  }
  return data;
};

const generateMockShares = (value: number, parties: number): number[] => {
  const shares: number[] = [];
  let remaining = value;
  for (let i = 0; i < parties - 1; i++) {
    const share = Math.round((Math.random() - 0.5) * value * 2);
    shares.push(share);
    remaining -= share;
  }
  shares.push(remaining);
  return shares;
};

// ==================== 主组件 ====================

const PrivacyComputePage: React.FC = () => {
  const [activeTech, setActiveTech] = useState<TechType>('FL');
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '隐私计算' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="隐私计算中心"
        subtitle="支持联邦学习、安全多方计算、同态加密、可信执行环境四种隐私计算技术"
        breadcrumbs={breadcrumbs}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => window.location.reload(),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 技术选择卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-6">
        {TECH_CARDS.map((card) => (
          <TechSelectionCard
            key={card.type}
            card={card}
            active={activeTech === card.type}
            onClick={() => setActiveTech(card.type)}
          />
        ))}
      </div>

      {/* 技术演示区域 */}
      {activeTech === 'FL' && <FlDemo />}
      {activeTech === 'MPC' && <MpcDemo />}
      {activeTech === 'HE' && <HeDemo />}
      {activeTech === 'TEE' && <TeeDemo />}

      {/* 性能基准对比 */}
      <PerformanceBenchmark />
    </PageContainer>
  );
};

// ==================== 技术选择卡片 ====================

const TechSelectionCard: React.FC<{
  card: TechCard;
  active: boolean;
  onClick: () => void;
}> = ({ card, active, onClick }) => (
  <div
    className="relative overflow-hidden rounded-xl p-4 cursor-pointer transition-all duration-300 hover:-translate-y-1"
    style={{
      background: active ? card.gradient : '#fff',
      border: active ? 'none' : '1px solid #e5e7eb',
      boxShadow: active ? '0 8px 25px rgba(0,0,0,0.15)' : '0 1px 3px rgba(0,0,0,0.04)',
      color: active ? '#fff' : '#333',
    }}
    onClick={onClick}
  >
    <div
      className="absolute rounded-full"
      style={{
        top: -30, right: -30, width: 100, height: 100,
        background: active ? 'rgba(255,255,255,0.1)' : 'transparent',
      }}
    />
    <div className="relative z-10">
      <div className="flex items-center gap-2 mb-2">
        <div
          className="flex items-center justify-center rounded-lg"
          style={{
            width: 40, height: 40,
            background: active ? 'rgba(255,255,255,0.2)' : `${card.color}15`,
            color: active ? '#fff' : card.color,
          }}
        >
          {card.icon}
        </div>
        <span className="text-sm font-bold">{card.name}</span>
      </div>
      <p className="text-xs mb-2" style={{ opacity: active ? 0.9 : 0.6, lineHeight: 1.5 }}>
        {card.description}
      </p>
      <div className="flex flex-wrap gap-1">
        {card.scenarios.map((s) => (
          <Tag
            key={s}
            size="small"
            variant="outline"
            style={{
              borderColor: active ? 'rgba(255,255,255,0.4)' : card.color,
              color: active ? '#fff' : card.color,
              fontSize: '0.65rem',
            }}
          >
            {s}
          </Tag>
        ))}
      </div>
    </div>
  </div>
);

// ==================== 联邦学习演示 ====================

const FlDemo: React.FC = () => {
  const [algorithm, setAlgorithm] = useState('fedavg');
  const [dataset, setDataset] = useState('electricity');
  const [rounds, setRounds] = useState(20);
  const [lr, setLr] = useState('0.01');
  const [batchSize, setBatchSize] = useState('32');
  const [isTraining, setIsTraining] = useState(false);
  const [currentRound, setCurrentRound] = useState(0);
  const [trainingData, setTrainingData] = useState<TrainingRound[]>([]);
  const [parties, setParties] = useState<FlParty[]>([
    { id: 'p1', name: '国网供电公司', dataCount: 4200, dataSize: '156MB', status: 'idle' },
    { id: 'p2', name: '南方电网数据中心', dataCount: 3800, dataSize: '142MB', status: 'idle' },
    { id: 'p3', name: '华能新能源', dataCount: 2600, dataSize: '98MB', status: 'idle' },
    { id: 'p4', name: '三峡能源', dataCount: 1880, dataSize: '71MB', status: 'idle' },
  ]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startTraining = useCallback(() => {
    setIsTraining(true);
    setCurrentRound(0);
    setTrainingData([]);
    setParties((prev) => prev.map((p) => ({ ...p, status: 'training' as const })));

    const data = generateTrainingData(rounds);
    let round = 0;

    timerRef.current = setInterval(() => {
      round++;
      setCurrentRound(round);
      setTrainingData((prev) => [...prev, data[round - 1]]);

      if (round >= rounds) {
        if (timerRef.current) clearInterval(timerRef.current);
        setIsTraining(false);
        setParties((prev) => prev.map((p) => ({ ...p, status: 'done' as const })));
      }
    }, 200);
  }, [rounds]);

  const stopTraining = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setIsTraining(false);
    setParties((prev) => prev.map((p) => ({ ...p, status: p.status === 'done' ? 'done' : 'idle' })));
  }, []);

  // 训练曲线图表
  const lossChartOption = useMemo(() => {
    if (trainingData.length === 0) return {};
    return {
      tooltip: { trigger: 'axis' as const },
      legend: { data: ['训练损失', '验证损失'], top: 0, right: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category' as const, data: trainingData.map((d) => `R${d.round}`), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value' as const, name: 'Loss', nameTextStyle: { fontSize: 10 } },
      series: [
        { name: '训练损失', type: 'line', data: trainingData.map((d) => +d.loss.toFixed(4)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: '#667eea' }, showSymbol: false },
        { name: '验证损失', type: 'line', data: trainingData.map((d) => +d.valLoss.toFixed(4)), smooth: true, lineStyle: { width: 2, type: 'dashed' }, itemStyle: { color: '#f5576c' }, showSymbol: false },
      ],
    };
  }, [trainingData]);

  const accChartOption = useMemo(() => {
    if (trainingData.length === 0) return {};
    return {
      tooltip: { trigger: 'axis' as const, formatter: (params: any) => params.map((p: any) => `${p.seriesName}: ${(p.value * 100).toFixed(1)}%`).join('<br/>') },
      legend: { data: ['训练准确率', '验证准确率'], top: 0, right: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category' as const, data: trainingData.map((d) => `R${d.round}`), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value' as const, name: 'Accuracy', min: 0, max: 1, nameTextStyle: { fontSize: 10 }, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
      series: [
        { name: '训练准确率', type: 'line', data: trainingData.map((d) => +d.accuracy.toFixed(4)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: '#43e97b' }, showSymbol: false, areaStyle: { color: 'rgba(67,233,123,0.1)' } },
        { name: '验证准确率', type: 'line', data: trainingData.map((d) => +d.valAccuracy.toFixed(4)), smooth: true, lineStyle: { width: 2, type: 'dashed' }, itemStyle: { color: '#38f9d7' }, showSymbol: false },
      ],
    };
  }, [trainingData]);

  // 最终混淆矩阵
  const confusionMatrixOption = useMemo(() => {
    if (!trainingData.length || currentRound < rounds) return {};
    const labels = ['低负荷', '中负荷', '高负荷', '尖峰'];
    const matrix = [
      [285, 12, 3, 0],
      [8, 312, 15, 2],
      [1, 10, 298, 8],
      [0, 1, 6, 340],
    ];
    const data: [number, number, number][] = [];
    matrix.forEach((row, i) => row.forEach((val, j) => data.push([j, i, val])));
    return {
      tooltip: { position: 'top' as const, formatter: (p: any) => `实际: ${labels[p.data[1]]}<br/>预测: ${labels[p.data[0]]}<br/>数量: ${p.data[2]}` },
      grid: { left: '15%', right: '10%', bottom: '15%', top: '5%' },
      xAxis: { type: 'category' as const, data: labels, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'category' as const, data: labels, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
      visualMap: { min: 0, max: 350, calculable: false, orient: 'horizontal' as const, left: 'center', bottom: '0%', inRange: { color: ['#f5f5f5', '#667eea'] } },
      series: [{ name: '混淆矩阵', type: 'heatmap', data, label: { show: true, fontSize: 11 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }],
    };
  }, [trainingData, currentRound, rounds]);

  // 特征重要性
  const featureImportanceOption = useMemo(() => {
    if (!trainingData.length || currentRound < rounds) return {};
    const features = ['历史负荷', '温度', '湿度', '风速', '日期类型', '电价', '日照时长', '气压'];
    const importance = [0.32, 0.22, 0.15, 0.11, 0.08, 0.06, 0.04, 0.02];
    return {
      tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' as const } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
      yAxis: { type: 'category' as const, data: features.reverse() },
      series: [{ type: 'bar', data: importance.reverse().map((v) => ({ value: v, itemStyle: { color: `rgba(102,126,234,${0.4 + v * 1.5})`, borderRadius: [0, 4, 4, 0] } })), barWidth: 18 }],
    };
  }, [trainingData, currentRound, rounds]);

  const finalAcc = trainingData.length > 0 ? trainingData[trainingData.length - 1].accuracy : 0;
  const finalLoss = trainingData.length > 0 ? trainingData[trainingData.length - 1].loss : 0;
  const isComplete = currentRound >= rounds;

  return (
    <div className="flex flex-col gap-4">
      {/* 训练配置 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">联邦学习训练配置</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">聚合算法</p>
            <Select value={algorithm} onChange={(v) => setAlgorithm(v as string)} options={FL_ALGORITHMS} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">数据集</p>
            <Select value={dataset} onChange={(v) => setDataset(v as string)} options={FL_DATASETS} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">学习率</p>
            <Input value={lr} onChange={setLr} placeholder="0.01" />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">批次大小</p>
            <Input value={batchSize} onChange={setBatchSize} placeholder="32" />
          </div>
        </div>
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-1">训练轮次: {rounds}</p>
          <Slider value={rounds} onChange={(v) => setRounds(v as number)} min={5} max={50} />
        </div>
        <div className="mt-3 flex gap-2">
          {!isTraining ? (
            <Button theme="primary" icon={<PlayIcon />} onClick={startTraining}>开始训练</Button>
          ) : (
            <Button theme="warning" icon={<CloseCircleIcon />} onClick={stopTraining}>停止训练</Button>
          )}
          {isComplete && (
            <Tag theme="success" size="large" icon={<CheckCircleIcon />}>训练完成</Tag>
          )}
        </div>
      </div>

      {/* 参与方管理 & 训练进度 */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* 参与方列表 */}
        <div className="md:col-span-4 rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">参与方管理</p>
          <div className="flex flex-col gap-2">
            {parties.map((p) => (
              <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-100">
                <div>
                  <p className="text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-gray-400">{p.dataCount.toLocaleString()} 条 / {p.dataSize}</p>
                </div>
                <Tag
                  size="small"
                  theme={p.status === 'done' ? 'success' : p.status === 'training' ? 'warning' : 'default'}
                  variant="light"
                >
                  {p.status === 'done' ? '已完成' : p.status === 'training' ? '训练中' : '就绪'}
                </Tag>
              </div>
            ))}
          </div>
          {/* 数据分布饼图 */}
          <div className="mt-3">
            <ReactECharts
              option={{
                tooltip: { trigger: 'item' as const },
                series: [{
                  type: 'pie', radius: ['40%', '65%'],
                  label: { show: true, fontSize: 10, formatter: '{b}\n{d}%' },
                  data: parties.map((p) => ({ name: p.name, value: p.dataCount })),
                  itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
                }],
              }}
              style={{ height: 180 }}
            />
          </div>
        </div>

        {/* 训练进度 */}
        <div className="md:col-span-8 rounded-xl bg-white border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold">训练过程监控</p>
            {isTraining && (
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs text-gray-500">轮次 {currentRound}/{rounds}</span>
              </div>
            )}
          </div>
          {isTraining && (
            <div className="mb-3">
              <Progress
                theme="line"
                percentage={Math.round((currentRound / rounds) * 100)}
                color={{ '0%': '#667eea', '100%': '#764ba2' }}
              />
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div style={{ minHeight: 250 }}>
              {trainingData.length > 0 ? (
                <ReactECharts option={lossChartOption} style={{ height: 250 }} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-300 text-sm">点击"开始训练"查看损失曲线</div>
              )}
            </div>
            <div style={{ minHeight: 250 }}>
              {trainingData.length > 0 ? (
                <ReactECharts option={accChartOption} style={{ height: 250 }} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-300 text-sm">点击"开始训练"查看准确率曲线</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 模型性能指标 */}
      {isComplete && (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {/* 性能指标 */}
          <div className="md:col-span-4 rounded-xl bg-white border border-gray-200 p-4">
            <p className="text-xs font-bold mb-3">模型性能指标</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center p-3 rounded-lg bg-blue-50">
                <p className="text-2xl font-bold text-blue-600">{(finalAcc * 100).toFixed(1)}%</p>
                <p className="text-xs text-gray-500">准确率</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-purple-50">
                <p className="text-2xl font-bold text-purple-600">{finalLoss.toFixed(4)}</p>
                <p className="text-xs text-gray-500">损失值</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-green-50">
                <p className="text-2xl font-bold text-green-600">96.2%</p>
                <p className="text-xs text-gray-500">精确率</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-orange-50">
                <p className="text-2xl font-bold text-orange-600">95.8%</p>
                <p className="text-xs text-gray-500">召回率</p>
              </div>
            </div>
            <div className="mt-3 p-3 rounded-lg bg-gray-50">
              <p className="text-xs text-gray-500 mb-1">F1 Score</p>
              <p className="text-lg font-bold">96.0%</p>
              <p className="text-xs text-gray-500 mt-1">AUC-ROC: 0.9847</p>
            </div>
          </div>
          {/* 混淆矩阵 */}
          <div className="md:col-span-4 rounded-xl bg-white border border-gray-200 p-4">
            <p className="text-xs font-bold mb-1">混淆矩阵</p>
            <p className="text-xs text-gray-400 mb-2">实际类别 vs 预测类别</p>
            <ReactECharts option={confusionMatrixOption} style={{ height: 280 }} />
          </div>
          {/* 特征重要性 */}
          <div className="md:col-span-4 rounded-xl bg-white border border-gray-200 p-4">
            <p className="text-xs font-bold mb-1">特征重要性</p>
            <p className="text-xs text-gray-400 mb-2">各特征对模型预测的贡献度</p>
            <ReactECharts option={featureImportanceOption} style={{ height: 280 }} />
          </div>
        </div>
      )}
    </div>
  );
};

// ==================== MPC 安全计算演示 ====================

const MpcDemo: React.FC = () => {
  const [protocol, setProtocol] = useState('secret_sharing');
  const [operation, setOperation] = useState('sum');
  const [isComputing, setIsComputing] = useState(false);
  const [step, setStep] = useState(0);
  const [parties, setParties] = useState<MpcParty[]>([
    { id: 'p1', name: '国网北京', privateValue: 8520, share: [], color: '#667eea' },
    { id: 'p2', name: '国网上海', privateValue: 6340, share: [], color: '#f093fb' },
    { id: 'p3', name: '国网广州', privateValue: 7180, share: [], color: '#4facfe' },
    { id: 'p4', name: '国网深圳', privateValue: 5960, share: [], color: '#43e97b' },
  ]);
  const [result, setResult] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const startCompute = useCallback(() => {
    setIsComputing(true);
    setStep(0);
    setResult(null);

    // Step 1: 秘密分享
    timerRef.current = setTimeout(() => {
      setStep(1);
      setParties((prev) =>
        prev.map((p) => ({
          ...p,
          share: generateMockShares(p.privateValue, parties.length),
        }))
      );
    }, 800);

    // Step 2: 安全传输
    timerRef.current = setTimeout(() => setStep(2), 2000);

    // Step 3: 安全计算
    timerRef.current = setTimeout(() => setStep(3), 3200);

    // Step 4: 结果聚合
    timerRef.current = setTimeout(() => {
      setStep(4);
      const values = parties.map((p) => p.privateValue);
      let r: number;
      switch (operation) {
        case 'sum': r = values.reduce((a, b) => a + b, 0); break;
        case 'avg': r = values.reduce((a, b) => a + b, 0) / values.length; break;
        case 'max': r = Math.max(...values); break;
        default: r = values.reduce((a, b) => a + b, 0);
      }
      setResult(r);
      setIsComputing(false);
    }, 4500);
  }, [operation, parties]);

  const steps = [
    { label: '输入数据', icon: <DataBaseIcon size="16px" /> },
    { label: '秘密分享', icon: <LockOnIcon size="16px" /> },
    { label: '安全传输', icon: <CloudIcon size="16px" /> },
    { label: '安全计算', icon: <ServerIcon size="16px" /> },
    { label: '结果聚合', icon: <CheckCircleIcon size="16px" /> },
  ];

  const totalShares = parties.reduce((acc, p) => acc + p.share.length, 0);

  return (
    <div className="flex flex-col gap-4">
      {/* 计算配置 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">MPC 安全计算配置</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">安全协议</p>
            <Select value={protocol} onChange={(v) => setProtocol(v as string)} options={MPC_PROTOCOLS} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">计算操作</p>
            <Select value={operation} onChange={(v) => setOperation(v as string)} options={MPC_OPERATIONS} />
          </div>
          <div className="flex items-end">
            <Button theme="primary" icon={<PlayIcon />} onClick={startCompute} disabled={isComputing} block>
              {isComputing ? '计算中...' : '开始安全计算'}
            </Button>
          </div>
        </div>
      </div>

      {/* 计算流程步骤 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">计算流程</p>
        <div className="flex items-center justify-between">
          {steps.map((s, i) => (
            <React.Fragment key={i}>
              <div className="flex flex-col items-center gap-1">
                <div
                  className="flex items-center justify-center rounded-full transition-all duration-500"
                  style={{
                    width: 40, height: 40,
                    background: step >= i ? (step === i && isComputing ? 'linear-gradient(135deg, #667eea, #764ba2)' : '#4caf50') : '#e0e0e0',
                    color: step >= i ? '#fff' : '#9e9e9e',
                  }}
                >
                  {step > i ? <CheckCircleIcon size="18px" /> : s.icon}
                </div>
                <span className="text-xs" style={{ color: step >= i ? '#333' : '#999' }}>{s.label}</span>
              </div>
              {i < steps.length - 1 && (
                <div
                  className="flex-1 h-0.5 mx-2 transition-all duration-500"
                  style={{ background: step > i ? '#4caf50' : '#e0e0e0' }}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* 参与方数据 & 秘密分享 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">参与方私有数据</p>
          <p className="text-xs text-gray-400 mb-3">各方私有数据对外不可见，仅参与方自己可见</p>
          <div className="flex flex-col gap-2">
            {parties.map((p) => (
              <div key={p.id} className="flex items-center justify-between p-3 rounded-lg" style={{ borderLeft: `3px solid ${p.color}`, background: `${p.color}08` }}>
                <div>
                  <p className="text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-gray-400">私有数据</p>
                </div>
                <div className="text-right">
                  {step >= 1 ? (
                    <div className="flex flex-wrap gap-1 justify-end">
                      {p.share.map((s, i) => (
                        <Tag key={i} size="small" variant="outline" style={{ borderColor: p.color, color: p.color, fontSize: '0.65rem' }}>
                          S{i + 1}:{s}
                        </Tag>
                      ))}
                    </div>
                  ) : (
                    <Tag size="small" variant="outline" style={{ borderColor: '#ccc', color: '#ccc' }}>
                      ****** kWh
                    </Tag>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 计算过程可视化 */}
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">安全计算过程</p>
          <div className="flex flex-col gap-3">
            {/* 流程图 */}
            <div className="relative p-4 rounded-lg bg-gray-50" style={{ minHeight: 200 }}>
              {/* 节点：各方输入 */}
              <div className="flex justify-around mb-6">
                {parties.map((p, i) => (
                  <div key={p.id} className="flex flex-col items-center">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white text-xs font-bold"
                      style={{ background: p.color, opacity: step >= 1 ? 1 : 0.4 }}
                    >
                      P{i + 1}
                    </div>
                    <span className="text-xs mt-1 text-gray-500">{p.name.slice(2)}</span>
                  </div>
                ))}
              </div>

              {/* 箭头指向计算节点 */}
              <div className="flex justify-center mb-2">
                <svg width="300" height="30" className="overflow-visible">
                  {[60, 120, 180, 240].map((x, i) => (
                    <line key={i} x1={x} y1="0" x2="150" y2="25" stroke={step >= 2 ? parties[i].color : '#ddd'} strokeWidth="2" strokeDasharray={step >= 2 ? '0' : '4'} />
                  ))}
                </svg>
              </div>

              {/* 安全计算节点 */}
              <div className="flex justify-center mb-2">
                <div
                  className="px-6 py-2 rounded-lg text-white text-sm font-bold transition-all duration-500"
                  style={{
                    background: step >= 3 ? 'linear-gradient(135deg, #667eea, #764ba2)' : '#e0e0e0',
                    boxShadow: step >= 3 ? '0 4px 12px rgba(102,126,234,0.3)' : 'none',
                  }}
                >
                  {step >= 3 ? '安全计算中...' : '安全计算节点'}
                </div>
              </div>

              {/* 箭头指向结果 */}
              <div className="flex justify-center mb-2">
                <svg width="10" height="25">
                  <line x1="5" y1="0" x2="5" y2="25" stroke={step >= 4 ? '#4caf50' : '#ddd'} strokeWidth="2" />
                  <polygon points="0,20 10,20 5,28" fill={step >= 4 ? '#4caf50' : '#ddd'} />
                </svg>
              </div>

              {/* 结果节点 */}
              <div className="flex justify-center">
                <div
                  className="px-6 py-2 rounded-lg text-sm font-bold transition-all duration-500"
                  style={{
                    background: step >= 4 ? '#e8f5e9' : '#f5f5f5',
                    color: step >= 4 ? '#2e7d32' : '#999',
                    border: step >= 4 ? '2px solid #4caf50' : '2px solid #e0e0e0',
                  }}
                >
                  {step >= 4 ? `聚合结果: ${result?.toLocaleString()}` : '等待结果'}
                </div>
              </div>
            </div>

              {/* 步骤日志 */}
              <div className="p-3 rounded-lg bg-gray-900 text-green-400 text-xs font-mono" style={{ maxHeight: 150, overflow: 'auto' }}>
                <div className={step >= 0 ? 'opacity-100' : 'opacity-30'}>{'>'} 初始化 MPC 计算任务...</div>
                {step >= 1 && <div>{'>'} 各方生成秘密分享 ({totalShares} 个分片)</div>}
                {step >= 2 && <div>{'>'} 通过安全通道传输分享分片...</div>}
                {step >= 3 && <div>{'>'} 在密文上执行 {MPC_OPERATIONS.find((o) => o.value === operation)?.label}...</div>}
                {step >= 4 && <div className="text-yellow-400">{'>'} 计算完成，聚合结果: {result?.toLocaleString()}</div>}
                {step >= 4 && <div className="text-blue-400">{'>'} 各方私有数据未泄露 ✓</div>}
              </div>
          </div>
        </div>
      </div>

      {/* 结果展示 */}
      {result !== null && (
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">计算结果</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 rounded-lg bg-green-50">
              <p className="text-3xl font-bold text-green-600">{result.toLocaleString()}</p>
              <p className="text-sm text-gray-500 mt-1">
                {operation === 'sum' ? '总用电量 (kWh)' : operation === 'avg' ? '平均用电量 (kWh)' : '最大用电量 (kWh)'}
              </p>
            </div>
            <div className="text-center p-4 rounded-lg bg-blue-50">
              <p className="text-3xl font-bold text-blue-600">{parties.length}</p>
              <p className="text-sm text-gray-500 mt-1">参与方数量</p>
            </div>
            <div className="text-center p-4 rounded-lg bg-purple-50">
              <p className="text-3xl font-bold text-purple-600">0</p>
              <p className="text-sm text-gray-500 mt-1">数据泄露量</p>
            </div>
          </div>
          <div className="mt-3 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <p className="text-xs text-yellow-800">
              <strong>安全保障：</strong>整个计算过程中，各方的私有数据通过秘密分享技术进行保护，任何一方都无法获取其他方的原始数据。仅聚合结果对所有参与方可见。
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

// ==================== 同态加密演示 ====================

const HeDemo: React.FC = () => {
  const [scheme, setScheme] = useState('ckks');
  const [operation, setOperation] = useState('add');
  const [plaintext1, setPlaintext1] = useState('12345');
  const [plaintext2, setPlaintext2] = useState('67890');
  const [step, setStep] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [publicKey, setPublicKey] = useState('');
  const [ciphertext1, setCiphertext1] = useState('');
  const [ciphertext2, setCiphertext2] = useState('');
  const [encryptedResult, setEncryptedResult] = useState('');
  const [decryptedResult, setDecryptedResult] = useState<number | null>(null);
  const [expectedResult, setExpectedResult] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const generateKey = () => {
    const chars = '0123456789abcdef';
    const gen = (len: number) => Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
    setPublicKey(`pk_${gen(64)}`);
    return gen(64);
  };

  const startProcess = useCallback(() => {
    setIsProcessing(true);
    setStep(0);
    setDecryptedResult(null);

    // Step 1: 密钥生成
    timerRef.current = setTimeout(() => {
      setStep(1);
      generateKey();
    }, 600);

    // Step 2: 加密数据
    timerRef.current = setTimeout(() => {
      setStep(2);
      const chars = '0123456789abcdef';
      const gen = (len: number) => Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
      setCiphertext1(`ct_${gen(96)}`);
      setCiphertext2(`ct_${gen(96)}`);
    }, 1800);

    // Step 3: 密文计算
    timerRef.current = setTimeout(() => {
      setStep(3);
      const chars = '0123456789abcdef';
      const gen = (len: number) => Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
      setEncryptedResult(`ct_${gen(128)}`);
    }, 3200);

    // Step 4: 解密结果
    timerRef.current = setTimeout(() => {
      setStep(4);
      const a = parseFloat(plaintext1) || 0;
      const b = parseFloat(plaintext2) || 0;
      let expected: number;
      let decrypted: number;
      switch (operation) {
        case 'add': expected = a + b; decrypted = expected; break;
        case 'multiply': expected = a * b; decrypted = expected; break;
        case 'dot_product': expected = a * b + a; decrypted = expected; break;
        default: expected = a + b; decrypted = expected;
      }
      setExpectedResult(expected);
      // CKKS 近似运算会有微小误差
      if (scheme === 'ckks') {
        setDecryptedResult(decrypted + (Math.random() - 0.5) * 0.01);
      } else {
        setDecryptedResult(decrypted);
      }
      setIsProcessing(false);
    }, 4500);
  }, [plaintext1, plaintext2, operation, scheme]);

  const heSteps = [
    { label: '密钥生成', icon: <LockOnIcon size="16px" /> },
    { label: '数据加密', icon: <LockOnIcon size="16px" /> },
    { label: '密文计算', icon: <ServerIcon size="16px" /> },
    { label: '结果解密', icon: <LockOffIcon size="16px" /> },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* 配置 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">同态加密配置</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">加密方案</p>
            <Select value={scheme} onChange={(v) => setScheme(v as string)} options={HE_SCHEMES} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">运算类型</p>
            <Select value={operation} onChange={(v) => setOperation(v as string)} options={HE_OPERATIONS} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">明文数据 A</p>
            <Input value={plaintext1} onChange={setPlaintext1} type="number" placeholder="输入数值" />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">明文数据 B</p>
            <Input value={plaintext2} onChange={setPlaintext2} type="number" placeholder="输入数值" />
          </div>
        </div>
        <div className="mt-3">
          <Button theme="primary" icon={<PlayIcon />} onClick={startProcess} disabled={isProcessing}>
            {isProcessing ? '处理中...' : '开始同态加密演示'}
          </Button>
        </div>
      </div>

      {/* 流程步骤 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">加密计算流程</p>
        <div className="flex items-center justify-between">
          {heSteps.map((s, i) => (
            <React.Fragment key={i}>
              <div className="flex flex-col items-center gap-1">
                <div
                  className="flex items-center justify-center rounded-full transition-all duration-500"
                  style={{
                    width: 48, height: 48,
                    background: step >= i ? (step === i && isProcessing ? 'linear-gradient(135deg, #4facfe, #00f2fe)' : '#4caf50') : '#e0e0e0',
                    color: step >= i ? '#fff' : '#9e9e9e',
                  }}
                >
                  {step > i ? <CheckCircleIcon size="20px" /> : s.icon}
                </div>
                <span className="text-xs" style={{ color: step >= i ? '#333' : '#999' }}>{s.label}</span>
              </div>
              {i < heSteps.length - 1 && (
                <div className="flex-1 h-1 mx-3 rounded transition-all duration-500" style={{ background: step > i ? '#4caf50' : '#e0e0e0' }} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* 加密过程展示 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 左侧：加密过程 */}
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">加密过程</p>
          <div className="flex flex-col gap-3">
            {/* 公钥 */}
            <div className="p-3 rounded-lg bg-gray-50">
              <p className="text-xs text-gray-500 mb-1">公钥 (Public Key)</p>
              <div className="text-xs font-mono text-blue-600 break-all">
                {step >= 1 ? publicKey : <span className="text-gray-300">等待密钥生成...</span>}
              </div>
            </div>

            {/* 明文 → 密文 */}
            <div className="flex items-center gap-2">
              <div className="flex-1 p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                <p className="text-xs text-gray-500">明文 A</p>
                <p className="text-lg font-bold text-green-700">{plaintext1}</p>
              </div>
              <span className="text-gray-400 text-lg">→</span>
              <div className="flex-1 p-3 rounded-lg bg-red-50 border border-red-200 text-center">
                <p className="text-xs text-gray-500">密文 A</p>
                <p className="text-xs font-mono text-red-600 truncate">
                  {step >= 2 ? ciphertext1 : '...'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex-1 p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                <p className="text-xs text-gray-500">明文 B</p>
                <p className="text-lg font-bold text-green-700">{plaintext2}</p>
              </div>
              <span className="text-gray-400 text-lg">→</span>
              <div className="flex-1 p-3 rounded-lg bg-red-50 border border-red-200 text-center">
                <p className="text-xs text-gray-500">密文 B</p>
                <p className="text-xs font-mono text-red-600 truncate">
                  {step >= 2 ? ciphertext2 : '...'}
                </p>
              </div>
            </div>

            {/* 密文计算 */}
            <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
              <p className="text-xs text-gray-500 mb-1">密文计算结果</p>
              <p className="text-xs font-mono text-purple-600 break-all">
                {step >= 3 ? encryptedResult : <span className="text-gray-300">等待密文计算...</span>}
              </p>
              <p className="text-xs text-purple-500 mt-1">
                操作: Enc(A) {operation === 'add' ? '⊕' : operation === 'multiply' ? '⊗' : '⊙'} Enc(B) = Enc(Result)
              </p>
            </div>
          </div>
        </div>

        {/* 右侧：结果对比 */}
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">解密结果对比</p>
          {step >= 4 && decryptedResult !== null && expectedResult !== null ? (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-4 rounded-lg bg-blue-50">
                  <p className="text-xs text-gray-500 mb-1">同态加密计算</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {scheme === 'ckks' ? decryptedResult.toFixed(2) : decryptedResult.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">密文解密结果</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-green-50">
                  <p className="text-xs text-gray-500 mb-1">明文直接计算</p>
                  <p className="text-2xl font-bold text-green-600">
                    {expectedResult.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">明文运算结果</p>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-green-50 border border-green-200 flex items-center gap-2">
                <CheckCircleIcon style={{ color: '#4caf50' }} />
                <div>
                  <p className="text-sm font-medium text-green-800">结果一致性验证通过</p>
                  <p className="text-xs text-green-600">
                    {scheme === 'ckks'
                      ? `CKKS 近似运算误差: ${Math.abs(decryptedResult - expectedResult).toFixed(6)} (在允许范围内)`
                      : '密文计算结果与明文计算结果完全一致'}
                  </p>
                </div>
              </div>

              {/* 安全属性 */}
              <div className="p-3 rounded-lg bg-gray-50">
                <p className="text-xs font-bold mb-2">安全属性</p>
                <div className="flex flex-col gap-1">
                  {[
                    { label: '数据机密性', value: '原始数据全程加密，计算节点无法获取明文' },
                    { label: '计算正确性', value: '密文运算结果与明文运算结果一致' },
                    { label: '方案安全性', value: `${HE_SCHEMES.find((s) => s.value === scheme)?.label} - 基于 RLWE 困难问题` },
                  ].map((item) => (
                    <div key={item.label} className="flex items-start gap-2">
                      <CheckCircleIcon style={{ color: '#4caf50', fontSize: 14, marginTop: 2 }} />
                      <div>
                        <span className="text-xs font-medium">{item.label}: </span>
                        <span className="text-xs text-gray-500">{item.value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-gray-300">
              <LockOffIcon size="48px" style={{ opacity: 0.4 }} />
              <p className="text-sm mt-2">点击"开始同态加密演示"查看结果</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== TEE 可信执行环境演示 ====================

const TeeDemo: React.FC = () => {
  const [runtime, setRuntime] = useState('sgx');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [attestationResult, setAttestationResult] = useState('');
  const [computeResult, setComputeResult] = useState<Record<string, number> | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [steps, setSteps] = useState<TeeStep[]>([
    { id: 'init', label: '初始化 TEE', status: 'pending', description: '创建安全飞地，分配受保护内存' },
    { id: 'attest', label: '远程证明', status: 'pending', description: '生成证明报告，验证 TEE 环境完整性' },
    { id: 'input', label: '安全传入数据', status: 'pending', description: '通过加密通道将数据传入 TEE' },
    { id: 'compute', label: '安全计算', status: 'pending', description: '在 TEE 内执行计算，数据不离开安全区域' },
    { id: 'output', label: '安全输出结果', status: 'pending', description: '加密输出计算结果，验证完整性' },
  ]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const startTee = useCallback(() => {
    setIsRunning(true);
    setCurrentStep(0);
    setComputeResult(null);
    setAttestationResult('');
    setSteps((prev) => prev.map((s) => ({ ...s, status: 'pending' as const })));

    const runStep = (index: number) => {
      if (index >= steps.length) {
        setIsRunning(false);
        return;
      }

      setCurrentStep(index);
      setSteps((prev) => prev.map((s, i) => ({
        ...s,
        status: i < index ? 'done' : i === index ? 'active' : 'pending',
      })));

      timerRef.current = setTimeout(() => {
        if (index === 1) {
          const chars = '0123456789abcdef';
          const gen = (len: number) => Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
          setAttestationResult(`SGX_QUOTE_${gen(64)}`);
        }
        if (index === 4) {
          setComputeResult({
            totalEmission: 125680.5,
            avgIntensity: 0.5823,
            peakHour: 14,
            reductionPotential: 12.5,
          });
        }
        setSteps((prev) => prev.map((s, i) => ({
          ...s,
          status: i <= index ? 'done' : i === index + 1 ? 'active' : 'pending',
        })));
        runStep(index + 1);
      }, 1200);
    };

    runStep(0);
  }, [steps.length]);

  const architectureOption = useMemo(() => ({
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'none',
      symbolSize: 60,
      roam: false,
      label: { show: true, fontSize: 11 },
      edgeSymbol: ['circle', 'arrow'],
      edgeSymbolSize: [4, 12],
      data: [
        { name: '外部应用', x: 50, y: 50, itemStyle: { color: '#4facfe' } },
        { name: 'TEE\n安全边界', x: 300, y: 200, itemStyle: { color: '#43e97b', borderColor: '#2e7d32', borderWidth: 3 } },
        { name: '加密数据', x: 50, y: 350, itemStyle: { color: '#f093fb' } },
        { name: '安全计算', x: 300, y: 100, itemStyle: { color: '#667eea' } },
        { name: '加密结果', x: 550, y: 350, itemStyle: { color: '#f5576c' } },
        { name: '远程证明', x: 550, y: 50, itemStyle: { color: '#ff9800' } },
      ],
      links: [
        { source: '外部应用', target: 'TEE\n安全边界', lineStyle: { color: '#aaa' } },
        { source: '加密数据', target: 'TEE\n安全边界', lineStyle: { color: '#aaa' } },
        { source: 'TEE\n安全边界', target: '安全计算', lineStyle: { color: '#aaa' } },
        { source: 'TEE\n安全边界', target: '加密结果', lineStyle: { color: '#aaa' } },
        { source: 'TEE\n安全边界', target: '远程证明', lineStyle: { color: '#aaa' } },
      ],
      lineStyle: { opacity: 0.8, curveness: 0.1 },
    }],
  }), []);

  return (
    <div className="flex flex-col gap-4">
      {/* 配置 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">TEE 环境配置</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">TEE 运行时</p>
            <Select value={runtime} onChange={(v) => setRuntime(v as string)} options={TEE_RUNTIMES} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">计算任务</p>
            <Input value="碳排放核算分析" disabled />
          </div>
          <div className="flex items-end">
            <Button theme="primary" icon={<PlayIcon />} onClick={startTee} disabled={isRunning} block>
              {isRunning ? '执行中...' : '启动 TEE 安全计算'}
            </Button>
          </div>
        </div>
      </div>

      {/* TEE 执行步骤 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <p className="text-xs font-bold mb-3">TEE 执行流程</p>
        <div className="flex flex-col gap-2">
          {steps.map((s, i) => (
            <div
              key={s.id}
              className="flex items-center gap-3 p-3 rounded-lg transition-all duration-300"
              style={{
                background: s.status === 'active' ? '#e8f5e9' : s.status === 'done' ? '#f1f8e9' : '#fafafa',
                borderLeft: `3px solid ${s.status === 'active' ? '#4caf50' : s.status === 'done' ? '#8bc34a' : '#e0e0e0'}`,
              }}
            >
              <div
                className="flex items-center justify-center rounded-full"
                style={{
                  width: 32, height: 32,
                  background: s.status === 'done' ? '#4caf50' : s.status === 'active' ? '#667eea' : '#e0e0e0',
                  color: s.status !== 'pending' ? '#fff' : '#999',
                }}
              >
                {s.status === 'done' ? <CheckCircleIcon size="16px" /> : <span className="text-xs font-bold">{i + 1}</span>}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium" style={{ color: s.status !== 'pending' ? '#333' : '#999' }}>{s.label}</p>
                <p className="text-xs text-gray-400">{s.description}</p>
              </div>
              {s.status === 'active' && (
                <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
              )}
            </div>
          ))}
        </div>

        {/* 远程证明结果 */}
        {attestationResult && (
          <div className="mt-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
            <p className="text-xs font-bold text-blue-800 mb-1">远程证明报告</p>
            <p className="text-xs font-mono text-blue-600 break-all">{attestationResult}</p>
            <p className="text-xs text-blue-500 mt-1">证明状态: 通过 | TEE 环境完整性: 已验证 | 安全级别: Level 3</p>
          </div>
        )}
      </div>

      {/* TEE 架构图 & 结果 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-1">TEE 工作原理</p>
          <p className="text-xs text-gray-400 mb-2">数据在硬件安全隔离环境中处理，外部无法访问</p>
          <ReactECharts option={architectureOption} style={{ height: 300 }} />
          <div className="mt-2 p-2 rounded bg-gray-50">
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-center">
                <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ background: '#43e97b' }} />
                <span className="text-gray-500">安全区域</span>
              </div>
              <div className="text-center">
                <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ background: '#4facfe' }} />
                <span className="text-gray-500">外部组件</span>
              </div>
              <div className="text-center">
                <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ background: '#f093fb' }} />
                <span className="text-gray-500">加密数据</span>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs font-bold mb-3">计算结果</p>
          {computeResult ? (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 rounded-lg bg-green-50">
                  <p className="text-xl font-bold text-green-600">{computeResult.totalEmission.toLocaleString()}</p>
                  <p className="text-xs text-gray-500">总碳排放量 (tCO₂)</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-blue-50">
                  <p className="text-xl font-bold text-blue-600">{computeResult.avgIntensity.toFixed(4)}</p>
                  <p className="text-xs text-gray-500">平均排放强度</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-orange-50">
                  <p className="text-xl font-bold text-orange-600">{computeResult.peakHour}:00</p>
                  <p className="text-xs text-gray-500">排放高峰时段</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-purple-50">
                  <p className="text-xl font-bold text-purple-600">{computeResult.reductionPotential}%</p>
                  <p className="text-xs text-gray-500">减排潜力</p>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-green-50 border border-green-200 flex items-start gap-2">
                <CheckCircleIcon style={{ color: '#4caf50', marginTop: 2 }} />
                <div>
                  <p className="text-sm font-medium text-green-800">安全计算完成</p>
                  <p className="text-xs text-green-600">
                    数据在 {TEE_RUNTIMES.find((r) => r.value === runtime)?.label} 安全环境中处理，原始数据未离开 TEE 安全边界。计算结果已通过完整性验证。
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-gray-300">
              <ServerIcon size="48px" style={{ opacity: 0.4 }} />
              <p className="text-sm mt-2">启动 TEE 安全计算查看结果</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== 性能基准对比 ====================

const PerformanceBenchmark: React.FC = () => {
  const radarOption = useMemo(() => ({
    tooltip: {},
    legend: { data: ['联邦学习', 'MPC', '同态加密', 'TEE'], bottom: 0 },
    radar: {
      indicator: [
        { name: '计算速度', max: 100 },
        { name: '通信开销', max: 100 },
        { name: '安全性', max: 100 },
        { name: '准确性', max: 100 },
        { name: '可扩展性', max: 100 },
        { name: '易用性', max: 100 },
      ],
      radius: '60%',
    },
    series: [{
      type: 'radar',
      data: [
        { value: [75, 60, 85, 90, 80, 85], name: '联邦学习', lineStyle: { color: '#667eea' }, itemStyle: { color: '#667eea' }, areaStyle: { color: 'rgba(102,126,234,0.1)' } },
        { value: [40, 30, 95, 99, 50, 60], name: 'MPC', lineStyle: { color: '#f093fb' }, itemStyle: { color: '#f093fb' }, areaStyle: { color: 'rgba(240,147,251,0.1)' } },
        { value: [30, 20, 90, 95, 35, 50], name: '同态加密', lineStyle: { color: '#4facfe' }, itemStyle: { color: '#4facfe' }, areaStyle: { color: 'rgba(79,172,254,0.1)' } },
        { value: [90, 85, 88, 99, 70, 75], name: 'TEE', lineStyle: { color: '#43e97b' }, itemStyle: { color: '#43e97b' }, areaStyle: { color: 'rgba(67,233,123,0.1)' } },
      ],
    }],
  }), []);

  const barOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' as const } },
    legend: { data: ['计算时间 (ms)', '通信开销 (KB)', '内存占用 (MB)'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category' as const, data: ['联邦学习', 'MPC', '同态加密', 'TEE'] },
    yAxis: { type: 'value' as const },
    series: [
      { name: '计算时间 (ms)', type: 'bar', data: [1200, 3500, 8500, 450], itemStyle: { color: '#667eea', borderRadius: [4, 4, 0, 0] } },
      { name: '通信开销 (KB)', type: 'bar', data: [850, 2400, 1200, 320], itemStyle: { color: '#f093fb', borderRadius: [4, 4, 0, 0] } },
      { name: '内存占用 (MB)', type: 'bar', data: [512, 1024, 2048, 256], itemStyle: { color: '#4facfe', borderRadius: [4, 4, 0, 0] } },
    ],
  }), []);

  return (
    <div className="rounded-xl bg-white border border-gray-200 p-4">
      <p className="text-xs font-bold mb-3">四种隐私计算技术性能对比</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-gray-500 mb-2">综合能力雷达图</p>
          <ReactECharts option={radarOption} style={{ height: 350 }} />
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-2">性能指标对比 (标准化)</p>
          <ReactECharts option={barOption} style={{ height: 350 }} />
        </div>
      </div>

      {/* 对比表格 */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-3 py-2 text-left font-bold text-xs">技术</th>
              <th className="px-3 py-2 text-left font-bold text-xs">计算速度</th>
              <th className="px-3 py-2 text-left font-bold text-xs">通信开销</th>
              <th className="px-3 py-2 text-left font-bold text-xs">安全性</th>
              <th className="px-3 py-2 text-left font-bold text-xs">适用场景</th>
            </tr>
          </thead>
          <tbody>
            {[
              { name: '联邦学习', speed: '快', comm: '中', sec: '高', scene: '多方联合建模、预测' },
              { name: 'MPC', speed: '慢', comm: '高', sec: '极高', scene: '安全统计、隐私查询' },
              { name: '同态加密', speed: '极慢', comm: '低', sec: '极高', scene: '密文计算、安全审计' },
              { name: 'TEE', speed: '极快', comm: '低', sec: '高', scene: '复杂计算、敏感分析' },
            ].map((row, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="px-3 py-2 font-medium">{row.name}</td>
                <td className="px-3 py-2">{row.speed}</td>
                <td className="px-3 py-2">{row.comm}</td>
                <td className="px-3 py-2">{row.sec}</td>
                <td className="px-3 py-2 text-gray-500">{row.scene}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PrivacyComputePage;
