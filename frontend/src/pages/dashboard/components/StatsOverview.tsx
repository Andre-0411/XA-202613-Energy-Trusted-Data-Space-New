/**
 * StatsOverview - 仪表盘统计卡片区域
 * 使用共享 StatCard 组件替代内联定义
 */
import React from 'react';
import { StatCard } from '@/components/common';

/* ===== Props ===== */
interface StatCardData {
  title: string;
  value: number;
  unit: string;
  icon: React.ReactNode;
  gradient: string;
  trend?: number;
}

interface StatsOverviewProps {
  statCards: StatCardData[];
  loading: boolean;
}

/* ============================================================
 * StatsOverview 主组件
 * ============================================================ */
const StatsOverview: React.FC<StatsOverviewProps> = ({ statCards, loading }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6">
      {statCards.map((card, index) => (
        <StatCard key={index} {...card} loading={loading} />
      ))}
    </div>
  );
};

export default StatsOverview;
