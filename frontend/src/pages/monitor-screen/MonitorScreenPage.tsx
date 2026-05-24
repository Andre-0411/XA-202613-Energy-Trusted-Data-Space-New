/**
 * 监管大屏页面（增强版）
 * 能源可信数据空间 — 全屏深色主题数据可视化
 * 拆分为子组件：MonitorMetricCard, MonitorAlertPanel, MonitorStatusPanel
 */
import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { Tag } from 'tdesign-react';
import {
  ArrowLeftIcon, FullscreenIcon, FullscreenExitIcon, RefreshIcon,
  ServerIcon, CloudIcon, UsergroupIcon, LinkIcon,
  ChartLineIcon, ErrorCircleIcon, FlashlightIcon, SwapIcon,
} from 'tdesign-icons-react';
import { useQuery } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { useNavigate } from 'react-router-dom';
import { getKpiDashboard, getAlerts } from '@/api/ops';
import type { KpiDashboard, AlertInfo } from '@/types/api';
import MonitorMetricCard from './components/MonitorMetricCard';
import MonitorAlertPanel from './components/MonitorAlertPanel';
import MonitorStatusPanel, { DataFlowAnimation, CarouselIndicator } from './components/MonitorStatusPanel';

/* ===== 深色主题常量 ===== */
const COLORS = {
  bg: '#0a0f1a',
  cardBg: '#111827',
  cardBorder: '#1f2937',
  text: '#e5e7eb',
  textSecondary: '#9ca3af',
  accent1: '#00e5ff',
  accent2: '#7c4dff',
  accent3: '#00e676',
  accent4: '#ff6e40',
  accent5: '#ffd740',
  gradient1: 'linear-gradient(135deg, #00e5ff 0%, #0091ea 100%)',
  gradient2: 'linear-gradient(135deg, #7c4dff 0%, #536dfe 100%)',
  gradient3: 'linear-gradient(135deg, #00e676 0%, #00c853 100%)',
  gradient4: 'linear-gradient(135deg, #ff6e40 0%, #ff3d00 100%)',
};

/* ===== 告警闪烁动画 keyframes ===== */
const ALERT_FLASH_KEYFRAMES = `
@keyframes alertFlash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
@keyframes alertPulse {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes flowParticle {
  0% { left: -5%; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { left: 105%; opacity: 0; }
}
@keyframes pulseRing {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}
`;

/* ===== 区域分布热力图（ECharts 模拟 geo 地图） ===== */
const useGeoHeatmapOption = () => useMemo(() => {
  const regions = [
    { name: '华北', center: [116.4, 39.9], value: 85, detail: '国网、大唐等' },
    { name: '华东', center: [121.5, 31.2], value: 92, detail: '上海、浙江、江苏' },
    { name: '华南', center: [113.3, 23.1], value: 78, detail: '南方电网、广东' },
    { name: '华中', center: [114.3, 30.6], value: 65, detail: '湖北、湖南' },
    { name: '西南', center: [104.1, 30.7], value: 55, detail: '四川、重庆' },
    { name: '西北', center: [108.9, 34.3], value: 48, detail: '陕西、甘肃' },
    { name: '东北', center: [123.4, 41.8], value: 42, detail: '辽宁、吉林' },
  ];

  return {
    tooltip: {
      trigger: 'item' as const,
      backgroundColor: COLORS.cardBg,
      borderColor: COLORS.cardBorder,
      textStyle: { color: COLORS.text },
      formatter: (params: { name: string; value: number[] }) => {
        const region = regions.find((r) => r.name === params.name);
        return `<strong>${params.name}</strong><br/>数据接入量: ${params.value[2]}<br/>${region?.detail ?? ''}`;
      },
    },
    grid: { left: '5%', right: '5%', top: '5%', bottom: '5%' },
    xAxis: {
      type: 'value' as const, min: 70, max: 135,
      axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false },
    },
    yAxis: {
      type: 'value' as const, min: 15, max: 50,
      axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false },
    },
    series: [{
      type: 'scatter' as const,
      symbolSize: (val: number[]) => Math.max(val[2] * 0.8, 30),
      data: regions.map((r) => ({
        name: r.name,
        value: [r.center[0], r.center[1], r.value],
        itemStyle: {
          color: {
            type: 'radial' as const, x: 0.5, y: 0.5, r: 0.5,
            colorStops: [
              { offset: 0, color: `${COLORS.accent1}CC` },
              { offset: 1, color: `${COLORS.accent1}1A` },
            ],
          },
          shadowBlur: 20, shadowColor: `${COLORS.accent1}66`,
        },
        label: {
          show: true, formatter: '{b}', position: 'inside' as const,
          color: '#fff', fontSize: 11, fontWeight: 'bold' as const,
        },
      })),
    }],
  };
}, []);

/* ===== 主监管大屏组件 ===== */
const MonitorScreenPage: React.FC = () => {
  const navigate = useNavigate();
  const [currentTime, setCurrentTime] = useState<string>('');
  const [currentDate, setCurrentDate] = useState<string>('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [carouselIndex, setCarouselIndex] = useState(0);
  const carouselTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 实时时钟
  useEffect(() => {
    const update = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('zh-CN', { hour12: false }));
      setCurrentDate(now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'long' }));
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  // 全屏切换
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // 数据轮播
  const carouselItems = useMemo(() => [
    { label: '数据资产总量', icon: <ServerIcon /> },
    { label: '今日计算任务', icon: <CloudIcon /> },
    { label: '链上交易笔数', icon: <LinkIcon /> },
    { label: '活跃用户数', icon: <UsergroupIcon /> },
  ], []);

  useEffect(() => {
    carouselTimerRef.current = setInterval(() => {
      setCarouselIndex((prev) => (prev + 1) % carouselItems.length);
    }, 5000);
    return () => {
      if (carouselTimerRef.current) clearInterval(carouselTimerRef.current);
    };
  }, [carouselItems.length]);

  const handleCarouselSwitch = useCallback((index: number) => {
    setCarouselIndex(index);
    if (carouselTimerRef.current) clearInterval(carouselTimerRef.current);
    carouselTimerRef.current = setInterval(() => {
      setCarouselIndex((prev) => (prev + 1) % carouselItems.length);
    }, 5000);
  }, [carouselItems.length]);

  const { data: kpiData, isError: kpiError, error: kpiErr } = useQuery({
    queryKey: ['kpiDashboard'],
    queryFn: () => getKpiDashboard(),
    refetchInterval: 30000,
  });

  const { data: alertsData, isError: alertsError, error: alertsErr } = useQuery({
    queryKey: ['monitorAlerts'],
    queryFn: () => getAlerts({ limit: 8 }),
    refetchInterval: 30000,
  });

  if (kpiError || alertsError) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: COLORS.bg }}>
        <div className="text-center">
          <ErrorCircleIcon className="mb-4 text-5xl text-red-500" />
          <p className="text-lg text-white">数据加载失败</p>
          <p className="mt-2 text-sm text-gray-400">{(kpiErr || alertsErr)?.message || '请稍后重试'}</p>
        </div>
      </div>
    );
  }

  const kpi: KpiDashboard | null = kpiData?.data ?? null;
  const alerts: AlertInfo[] = alertsData?.data?.items ?? [];

  // 核心指标
  const coreMetrics = useMemo(() => [
    { title: '数据资产', value: kpi?.total_assets ?? 1250, unit: '项', icon: <ServerIcon className="text-white" />, gradient: COLORS.gradient1, trend: 12.5, yoy: 28.6, mom: 8.3 },
    { title: '计算任务', value: kpi?.total_compute_tasks ?? 890, unit: '个', icon: <CloudIcon className="text-white" />, gradient: COLORS.gradient2, trend: 8.3, yoy: 35.2, mom: 12.1 },
    { title: '活跃用户', value: kpi?.active_users ?? 280, unit: '人', icon: <UsergroupIcon className="text-white" />, gradient: COLORS.gradient3, trend: 15.2, yoy: 42.8, mom: 6.7 },
    { title: '链上交易', value: kpi?.blockchain_transactions ?? 650, unit: '笔', icon: <LinkIcon className="text-white" />, gradient: COLORS.gradient4, trend: 23.1, yoy: 58.4, mom: 18.9 },
  ], [kpi]);

  const geoHeatmapOption = useGeoHeatmapOption();

  // 数据资产分布饼图
  const assetPieOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const, backgroundColor: COLORS.cardBg, borderColor: COLORS.cardBorder, textStyle: { color: COLORS.text } },
    legend: { orient: 'vertical' as const, right: '5%', top: 'center', textStyle: { color: COLORS.textSecondary, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
    series: [{
      type: 'pie' as const, radius: ['45%', '75%'], center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: COLORS.cardBg, borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold', color: COLORS.text }, itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,0,0,0.5)' } },
      data: [
        { value: 450, name: '电力数据', itemStyle: { color: COLORS.accent1 } },
        { value: 320, name: '碳排放数据', itemStyle: { color: COLORS.accent2 } },
        { value: 280, name: '交易数据', itemStyle: { color: COLORS.accent4 } },
        { value: 200, name: '设备数据', itemStyle: { color: COLORS.accent3 } },
      ],
    }],
  }), []);

  // 组织分布柱状图
  const orgBarOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const, backgroundColor: COLORS.cardBg, borderColor: COLORS.cardBorder, textStyle: { color: COLORS.text } },
    grid: { left: '3%', right: '5%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: { type: 'category' as const, data: ['国网', '南网', '华能', '大唐', '华电', '国电'], axisLabel: { color: COLORS.textSecondary, fontSize: 10 }, axisLine: { lineStyle: { color: COLORS.cardBorder } } },
    yAxis: { type: 'value' as const, axisLabel: { color: COLORS.textSecondary }, splitLine: { lineStyle: { color: `${COLORS.accent1}1A` } } },
    series: [{
      type: 'bar' as const, barWidth: '50%',
      data: [85, 72, 65, 58, 50, 43],
      itemStyle: { borderRadius: [4, 4, 0, 0], color: { type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: COLORS.accent1 }, { offset: 1, color: `${COLORS.accent1}80` }] } },
    }],
  }), []);

  // 安全威胁雷达图
  const radarOption = useMemo(() => ({
    radar: {
      indicator: [
        { name: '数据泄露', max: 100 }, { name: '未授权访问', max: 100 }, { name: 'DDoS攻击', max: 100 },
        { name: '内部威胁', max: 100 }, { name: '合规风险', max: 100 }, { name: '供应链攻击', max: 100 },
      ],
      axisName: { color: COLORS.textSecondary, fontSize: 10 },
      splitArea: { areaStyle: { color: [`${COLORS.accent1}05`, `${COLORS.accent1}0D`] } },
      splitLine: { lineStyle: { color: COLORS.cardBorder } },
      axisLine: { lineStyle: { color: COLORS.cardBorder } },
    },
    series: [{
      type: 'radar' as const,
      data: [{
        value: [75, 60, 45, 80, 55, 40], name: '威胁等级',
        areaStyle: { color: `${COLORS.accent4}33` }, lineStyle: { color: COLORS.accent4, width: 2 },
        itemStyle: { color: COLORS.accent4 }, symbol: 'circle', symbolSize: 6,
      }],
    }],
  }), []);

  // 合规评分仪表盘
  const gaugeOption = useMemo(() => ({
    series: [{
      type: 'gauge' as const, startAngle: 200, endAngle: -20, min: 0, max: 100, radius: '85%',
      progress: { show: true, width: 12, itemStyle: { color: { type: 'linear' as const, x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: COLORS.accent2 }, { offset: 1, color: COLORS.accent1 }] } } },
      axisLine: { lineStyle: { width: 12, color: [[1, `${COLORS.cardBorder}80`]] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      pointer: { show: false }, anchor: { show: false }, title: { show: false },
      detail: { valueAnimation: true, formatter: '{value}%', color: COLORS.text, fontSize: 28, fontWeight: 'bold', offsetCenter: [0, '10%'] },
      data: [{ value: kpi?.compliance_score ?? 85 }],
    }],
  }), [kpi]);

  // 趋势对比图
  const trendCompareOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const, backgroundColor: COLORS.cardBg, borderColor: COLORS.cardBorder, textStyle: { color: COLORS.text } },
    legend: { data: ['本月', '上月（环比）', '去年同期（同比）'], top: 5, textStyle: { color: COLORS.textSecondary, fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
    grid: { left: '3%', right: '5%', bottom: '3%', top: '18%', containLabel: true },
    xAxis: { type: 'category' as const, data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'], axisLabel: { color: COLORS.textSecondary, fontSize: 10 }, axisLine: { lineStyle: { color: COLORS.cardBorder } } },
    yAxis: { type: 'value' as const, axisLabel: { color: COLORS.textSecondary }, splitLine: { lineStyle: { color: `${COLORS.accent1}1A` } } },
    series: [
      { name: '本月', type: 'line' as const, smooth: true, symbol: 'none', data: [820, 932, 901, 1034, 1290, 1130, 1020], lineStyle: { color: COLORS.accent1, width: 2 }, areaStyle: { color: { type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: `${COLORS.accent1}4D` }, { offset: 1, color: `${COLORS.accent1}05` }] } } },
      { name: '上月（环比）', type: 'line' as const, smooth: true, symbol: 'none', data: [720, 810, 780, 910, 1100, 980, 890], lineStyle: { color: COLORS.accent5, width: 1.5, type: 'dashed' as const } },
      { name: '去年同期（同比）', type: 'line' as const, smooth: true, symbol: 'none', data: [580, 650, 620, 750, 880, 790, 720], lineStyle: { color: COLORS.accent2, width: 1.5, type: 'dashed' as const } },
    ],
  }), []);

  // 系统健康状态
  const systemHealth = useMemo(() => [
    { label: 'API 响应时间', value: 95, color: COLORS.accent3 },
    { label: '系统可用率', value: kpi?.uptime_percentage ?? 99.9, color: COLORS.accent1 },
    { label: '数据质量评分', value: kpi?.data_quality_avg ?? 92, color: COLORS.accent5 },
    { label: '安全合规评分', value: kpi?.compliance_score ?? 88, color: COLORS.accent2 },
  ], [kpi]);

  const carouselValues = useMemo(() => [
    kpi?.total_assets ?? 1250,
    kpi?.total_compute_tasks ?? 890,
    kpi?.blockchain_transactions ?? 650,
    kpi?.active_users ?? 280,
  ], [kpi]);

  return (
    <section
      aria-label="监管大屏"
      className="min-h-screen overflow-auto"
      style={{
        background: COLORS.bg, color: COLORS.text,
        scrollbarWidth: 'thin', scrollbarColor: `${COLORS.cardBorder} ${COLORS.bg}`,
      }}
    >
      <style>{ALERT_FLASH_KEYFRAMES}</style>

      {/* 顶部标题栏 */}
      <header
        className="sticky top-0 z-[100] border-b px-6 py-3"
        style={{ background: `linear-gradient(180deg, ${COLORS.bg} 0%, ${COLORS.bg}F5 100%)`, backdropFilter: 'blur(20px)', borderColor: COLORS.cardBorder }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate(-1)} className="transition-colors hover:opacity-80" style={{ color: COLORS.accent1 }} aria-label="返回上一页">
              <ArrowLeftIcon className="text-xl" />
            </button>
            <div className="flex items-center gap-2">
              <FlashlightIcon className="text-2xl" style={{ color: COLORS.accent1 }} />
              <h5 className="text-lg font-bold" style={{ background: COLORS.gradient1, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                能源可信数据空间
              </h5>
              <Tag className="font-semibold" style={{ background: `${COLORS.accent1}26`, color: COLORS.accent1 }}>监管大屏</Tag>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <h5 className="font-bold tracking-wider" style={{ color: COLORS.accent1, fontFamily: 'monospace' }}>{currentTime}</h5>
              <span className="text-xs" style={{ color: COLORS.textSecondary }}>{currentDate}</span>
            </div>
            <div className="flex gap-2">
              <button className="transition-colors hover:opacity-80" style={{ color: COLORS.textSecondary }} aria-label="刷新数据">
                <RefreshIcon className="text-xl" />
              </button>
              <button onClick={toggleFullscreen} className="transition-colors hover:opacity-80" style={{ color: COLORS.textSecondary }} aria-label={isFullscreen ? '退出全屏' : '全屏显示'}>
                {isFullscreen ? <FullscreenExitIcon className="text-xl" /> : <FullscreenIcon className="text-xl" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="p-6">
        {/* 核心指标卡片 */}
        <div className="mb-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {coreMetrics.map((metric, index) => (
              <MonitorMetricCard key={index} {...metric} isHighlighted={index === carouselIndex} />
            ))}
          </div>
          <CarouselIndicator total={carouselItems.length} current={carouselIndex} onSwitch={handleCarouselSwitch} />
        </div>

        {/* 轮播焦点指示条 */}
        <div className="relative mb-6 overflow-hidden rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.accent1}` }}>
          <div className="absolute bottom-0 left-0 top-0 w-1" style={{ background: COLORS.gradient1 }} />
          <div className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-full" style={{ background: COLORS.gradient1 }}>
              {carouselItems[carouselIndex].icon}
            </div>
            <div>
              <span className="text-xs" style={{ color: COLORS.textSecondary }}>当前聚焦</span>
              <p className="text-sm font-bold" style={{ color: COLORS.accent1 }}>
                {carouselItems[carouselIndex].label}: {carouselValues[carouselIndex].toLocaleString()}
              </p>
            </div>
            <div className="flex-1" />
            <SwapIcon style={{ color: `${COLORS.accent1}80` }} />
            <span className="text-xs" style={{ color: COLORS.textSecondary }}>5秒自动切换</span>
          </div>
        </div>

        {/* 数据流动画 */}
        <div className="mb-6 rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
          <div className="mb-2 flex items-center gap-2">
            <ChartLineIcon className="text-sm" style={{ color: COLORS.accent1 }} />
            <span className="text-xs font-semibold" style={{ color: COLORS.accent1 }}>实时数据流</span>
            <Tag style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', fontSize: '0.6rem', height: 18 }}>LIVE</Tag>
          </div>
          <DataFlowAnimation />
        </div>

        {/* 图表区域 */}
        <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* 左侧：数据资产分布 + 组织分布 */}
          <div className="lg:col-span-3">
            <div className="flex flex-col gap-4">
              <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
                <p className="mb-2 text-xs font-semibold" style={{ color: COLORS.accent1 }}>数据资产分布</p>
                <ReactECharts option={assetPieOption} style={{ height: 200 }} />
              </div>
              <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
                <p className="mb-2 text-xs font-semibold" style={{ color: COLORS.accent1 }}>组织分布</p>
                <ReactECharts option={orgBarOption} style={{ height: 180 }} />
              </div>
            </div>
          </div>

          {/* 中间：趋势对比 + 区域热力图 */}
          <div className="lg:col-span-6">
            <div className="flex flex-col gap-4">
              <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold" style={{ color: COLORS.accent1 }}>数据访问趋势（同比/环比对比）</span>
                  <div className="flex gap-2">
                    <Tag style={{ background: `${COLORS.accent1}26`, color: COLORS.accent1, fontSize: '0.6rem', height: 18 }}>本月</Tag>
                    <Tag style={{ background: `${COLORS.accent5}26`, color: COLORS.accent5, fontSize: '0.6rem', height: 18 }}>环比</Tag>
                    <Tag style={{ background: `${COLORS.accent2}26`, color: COLORS.accent2, fontSize: '0.6rem', height: 18 }}>同比</Tag>
                  </div>
                </div>
                <ReactECharts option={trendCompareOption} style={{ height: 200 }} />
              </div>
              <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
                <p className="mb-2 text-xs font-semibold" style={{ color: COLORS.accent1 }}>区域分布热力图</p>
                <ReactECharts option={geoHeatmapOption} style={{ height: 180 }} />
              </div>
            </div>
          </div>

          {/* 右侧：安全威胁 + 合规评分 + 系统状态 */}
          <div className="lg:col-span-3">
            <div className="flex flex-col gap-4">
              <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
                <p className="mb-2 text-xs font-semibold" style={{ color: COLORS.accent1 }}>安全威胁等级</p>
                <ReactECharts option={radarOption} style={{ height: 200 }} />
              </div>
              <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
                <p className="mb-2 text-xs font-semibold" style={{ color: COLORS.accent1 }}>合规评分</p>
                <ReactECharts option={gaugeOption} style={{ height: 180 }} />
              </div>
              <MonitorStatusPanel systemHealth={systemHealth} />
            </div>
          </div>
        </div>

        {/* 底部告警区域 */}
        <MonitorAlertPanel alerts={alerts} />
      </main>
    </section>
  );
};

export default MonitorScreenPage;
