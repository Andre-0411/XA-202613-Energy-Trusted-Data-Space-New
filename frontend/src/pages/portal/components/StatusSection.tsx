/**
 * StatusSection - 平台状态与Live Demo区域
 * 包含：实时平台运行状态 + Live Demo图表 + 五大核心能力中心导航
 */
import React, { useMemo } from 'react';
import { Button, Tag } from 'tdesign-react';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import {
  HardDiskStorageIcon, CloudIcon, LinkIcon,
  UsergroupIcon, LockOnIcon, ForwardIcon,
} from 'tdesign-icons-react';

/* ===== 五中心数据 ===== */
const CENTERS = [
  {
    icon: <HardDiskStorageIcon />,
    title: '数据资源中心',
    desc: '数据采集接入、分类分级、元数据管理、数据质量控制、数据目录发布',
    color: '#1976d2',
    path: '/dashboard/data/sources',
  },
  {
    icon: <CloudIcon />,
    title: '可信计算中心',
    desc: '联邦学习、安全多方计算、可信执行环境、同态加密、差分隐私',
    color: '#2e7d32',
    path: '/dashboard/compute/tasks',
  },
  {
    icon: <LinkIcon />,
    title: '区块链存证中心',
    desc: '数据资产确权、全流程操作存证、智能合约结算、链上溯源',
    color: '#ed6c02',
    path: '/dashboard/blockchain/assets',
  },
  {
    icon: <UsergroupIcon />,
    title: '运营管理中心',
    desc: '用户管理、服务目录、计费管理、合规审计、运营监控',
    color: '#7b1fa2',
    path: '/dashboard/ops/users',
  },
  {
    icon: <LockOnIcon />,
    title: '安全管控中心',
    desc: 'DID身份认证、VC凭证管理、密钥管理、零知识证明、国密算法',
    color: '#d32f2f',
    path: '/dashboard/security/policies',
  },
];

/* ===== Props ===== */
interface PlatformMetric {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
}

interface StatusSectionProps {
  platformMetrics: PlatformMetric[];
  dashboardLoading: boolean;
}

/* ============================================================
 * StatusSection 主组件
 * ============================================================ */
const StatusSection: React.FC<StatusSectionProps> = ({ platformMetrics, dashboardLoading }) => {
  const navigate = useNavigate();

  /* ===== Live Demo 图表配置 ===== */
  const liveDemoChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['光伏发电', '风电发电', '电网负荷', '储能充放'], top: 5 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    },
    yAxis: { type: 'value' as const, name: 'MW' },
    series: [
      {
        name: '光伏发电',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.15 },
        lineStyle: { width: 2 },
        itemStyle: { color: '#f57c00' },
        data: [0, 0, 0, 0, 0, 5, 45, 120, 210, 280, 310, 320, 315, 300, 260, 180, 80, 15, 0, 0, 0, 0, 0, 0],
      },
      {
        name: '风电发电',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.15 },
        lineStyle: { width: 2 },
        itemStyle: { color: '#0288d1' },
        data: [180, 170, 165, 160, 155, 150, 140, 130, 120, 110, 100, 95, 100, 110, 125, 140, 155, 170, 180, 185, 190, 185, 180, 175],
      },
      {
        name: '电网负荷',
        type: 'line',
        smooth: true,
        lineStyle: { width: 2, type: 'dashed' as const },
        itemStyle: { color: '#d32f2f' },
        data: [320, 290, 270, 260, 265, 300, 420, 550, 580, 560, 540, 520, 510, 490, 480, 500, 550, 600, 580, 520, 460, 420, 380, 340],
      },
      {
        name: '储能充放',
        type: 'bar',
        itemStyle: { color: '#7b1fa2', opacity: 0.7 },
        data: [50, 50, 50, 50, 50, 30, -20, -40, -30, -10, 10, 20, 30, 40, 50, 30, -20, -40, -30, 0, 20, 40, 50, 50],
      },
    ],
  }), []);

  /* ===== 实时数据流图表配置 ===== */
  const realtimeFlowOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, right: 10, top: 20 },
    series: [
      {
        name: '数据流通量',
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['40%', '50%'],
        roseType: 'area',
        itemStyle: { borderRadius: 8 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: [
          { value: 42, name: '电网运行', itemStyle: { color: '#1976d2' } },
          { value: 28, name: '新能源', itemStyle: { color: '#2e7d32' } },
          { value: 18, name: '气象环境', itemStyle: { color: '#0288d1' } },
          { value: 25, name: '设备状态', itemStyle: { color: '#ed6c02' } },
          { value: 15, name: '电力市场', itemStyle: { color: '#7b1fa2' } },
          { value: 21, name: '碳管理', itemStyle: { color: '#00897b' } },
        ],
      },
    ],
  }), []);

  return (
    <>
      {/* ===== 平台状态 ===== */}
      <section id="status" className="py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-10">
            <Tag>平台状态</Tag>
            <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">实时平台运行状态</h3>
            <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
              实时监控平台核心指标，保障数据空间安全稳定运行
            </p>
          </div>

          {dashboardLoading ? (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {platformMetrics.map((m) => (
                <div
                  key={m.label}
                  className="rounded-xl bg-white border border-gray-200 p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-md group cursor-default"
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-lg mb-3 transition-all duration-300"
                    style={{ backgroundColor: `${m.color}15`, color: m.color }}
                  >
                    {m.icon}
                  </div>
                  <span className="text-3xl font-extrabold text-gray-900 block">{m.value}</span>
                  <span className="text-xs text-gray-600">{m.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ===== Live Demo ===== */}
      <section id="demo" className="py-12 md:py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-10">
            <Tag>Live Demo</Tag>
            <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">能源数据实时流动</h3>
            <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
              可视化展示能源数据空间中数据资产的实时流通与计算调度
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            <div className="md:col-span-8">
              <div className="rounded-xl bg-white border border-gray-200 p-4">
                <h3 className="text-base font-semibold text-gray-800 mb-1">24小时能源发电与负荷曲线</h3>
                <span className="text-xs text-gray-600 block mb-2">融合光伏、风电、电网负荷、储能充放多维数据</span>
                <ReactECharts option={liveDemoChartOption} style={{ height: 350 }} />
              </div>
            </div>
            <div className="md:col-span-4">
              <div className="rounded-xl bg-white border border-gray-200 p-4">
                <h3 className="text-base font-semibold text-gray-800 mb-1">数据流通量分布</h3>
                <span className="text-xs text-gray-600 block mb-2">各类数据资产实时接入占比</span>
                <ReactECharts option={realtimeFlowOption} style={{ height: 350 }} />
              </div>
            </div>
          </div>

          {/* 五中心导航卡片 */}
          <div className="mt-10">
            <h2 className="text-xl font-semibold text-gray-800 mb-4 text-center">五大核心能力中心</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
              {CENTERS.map((c) => (
                <div
                  key={c.title}
                  className="rounded-xl bg-white border-2 border-gray-200 p-4 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-md group"
                  style={{ borderColor: `${c.color}26` }}
                  onClick={() => navigate(c.path)}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-lg mb-3"
                    style={{ backgroundColor: `${c.color}15`, color: c.color }}
                  >
                    {c.icon}
                  </div>
                  <span className="font-bold text-gray-800 block mb-1">{c.title}</span>
                  <span className="text-xs text-gray-600 block mb-3 line-clamp-2">{c.desc}</span>
                  <Button variant="text" icon={<ForwardIcon />} className="text-blue-600">进入</Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default StatusSection;
