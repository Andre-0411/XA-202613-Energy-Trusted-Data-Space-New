/**
 * DashboardPageTemplate 仪表盘页面模板
 * 组合 PageHeader + StatsRow + 子内容区，
 * 提供统一的 Dashboard 页布局。
 */
import React from 'react';
import PageHeader, { BreadcrumbItem } from '../PageHeader';
import StatsRow from '../common/StatsRow';
import StatCard, { GradientPreset } from '../common/StatCard';

export interface DashboardPageTemplateProps {
  /** 页面标题 */
  title: string;
  /** 页面副标题 */
  subtitle?: string;
  /** 面包屑导航 */
  breadcrumbs: BreadcrumbItem[];

  /** 顶部统计数据（带趋势） */
  stats: Array<{
    title: string;
    value: number | string;
    icon?: React.ReactNode;
    color?: string;
    trend?: number;
    unit?: string;
    gradient?: string;
  }>;

  /** 图表等内容区域 */
  children: React.ReactNode;
}

/**
 * DashboardPageTemplate 组件
 * 标准仪表盘布局：页头 → 统计卡片行 → 图表内容区
 */
const DashboardPageTemplate: React.FC<DashboardPageTemplateProps> = ({
  title,
  subtitle,
  breadcrumbs,
  stats,
  children,
}) => {
  return (
    <div>
      {/* 页头 */}
      <PageHeader
        title={title}
        subtitle={subtitle}
        breadcrumbs={breadcrumbs}
      />

      {/* 统计卡片行 */}
      <StatsRow columns={Math.min(stats.length, 4)}>
        {stats.map((s, idx) => (
          <StatCard
            key={`dash-stat-${idx}`}
            title={s.title}
            value={typeof s.value === 'number' ? s.value : Number(s.value) || 0}
            unit={s.unit || ''}
            icon={s.icon || <span />}
            gradient={(s.gradient || s.color || 'blue') as GradientPreset | string}
            trend={s.trend}
          />
        ))}
      </StatsRow>

      {/* 图表内容区 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {children}
      </div>
    </div>
  );
};

export default DashboardPageTemplate;
