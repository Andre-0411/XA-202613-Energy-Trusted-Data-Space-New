/**
 * AssetStats - 数据资产统计面板组件
 * 统计卡片 + 分类/敏感级别图表
 */
import React from 'react';
import { Tag } from 'tdesign-react';
import {
  FolderOpenIcon, CheckCircleFilledIcon, ShieldErrorFilledIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { StatGrid, StatCard, PageSection } from '@/components/common';

/** 分类选项 */
const CATEGORY_OPTIONS = [
  { value: 'electricity', label: '电力数据', icon: '⚡', color: '#f59e0b' },
  { value: 'gas', label: '燃气数据', icon: '🔥', color: '#ef4444' },
  { value: 'renewable', label: '新能源数据', icon: '🌱', color: '#22c55e' },
  { value: 'market', label: '市场数据', icon: '📈', color: '#3b82f6' },
  { value: 'device', label: '设备数据', icon: '🔧', color: '#8b5cf6' },
  { value: 'geographic', label: '地理信息', icon: '🗺️', color: '#06b6d4' },
];

/** 敏感级别选项 */
const SENSITIVITY_OPTIONS = [
  { value: 'public', label: '公开', color: '#22c55e' },
  { value: 'internal', label: '内部', color: '#3b82f6' },
  { value: 'confidential', label: '机密', color: '#f59e0b' },
  { value: 'secret', label: '绝密', color: '#ef4444' },
];

interface AssetStatsProps {
  stats: {
    totalAssets: number;
    published: number;
    classified: number;
    sensitive: number;
    byCategory: Record<string, number>;
    bySensitivity: Record<string, number>;
  };
}

/** AssetStats 组件 */
const AssetStats: React.FC<AssetStatsProps> = ({ stats }) => {
  // ===== 图表配置 =====
  const categoryPieOption = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie' as const,
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' as const },
      },
      data: CATEGORY_OPTIONS.map((cat) => ({
        value: stats.byCategory[cat.value] || 0,
        name: cat.label,
        itemStyle: { color: cat.color },
      })),
    }],
  };

  const sensitivityBarOption = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: SENSITIVITY_OPTIONS.map((s) => s.label),
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: 'value' as const, name: '数量' },
    series: [{
      type: 'bar' as const,
      barWidth: '60%',
      data: SENSITIVITY_OPTIONS.map((s) => ({
        value: stats.bySensitivity[s.value] || 0,
        itemStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: s.color },
              { offset: 1, color: s.color + '80' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
      })),
    }],
  };

  return (
    <>
      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="资产总数" value={stats.totalAssets} icon={<FolderOpenIcon />} gradient="purple" unit="" />
        <StatCard title="已发布" value={stats.published} icon={<CheckCircleFilledIcon />} gradient="green" unit="" />
        <StatCard title="已分类" value={stats.classified} icon={<FolderOpenIcon />} gradient="blue" unit="" />
        <StatCard title="敏感资产" value={stats.sensitive} icon={<ShieldErrorFilledIcon />} gradient="red" unit="" />
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
        <PageSection title="数据分类分布">
          <ReactECharts option={categoryPieOption} style={{ height: 250 }} />
        </PageSection>
        <PageSection title="敏感级别统计">
          <ReactECharts option={sensitivityBarOption} style={{ height: 250 }} />
        </PageSection>
      </div>
    </>
  );
};

export default AssetStats;
export { CATEGORY_OPTIONS, SENSITIVITY_OPTIONS };
