/**
 * StatusSection - 平台状态统计区域
 * 4个大数字卡片，带递增动画
 */
import React, { useState, useEffect } from 'react';

/* ===== 统计数据 ===== */
const STATS = [
  {
    icon: '📊',
    value: 12580,
    label: '数据资产',
    subLabel: '+12.5% ↑',
    color: '#165DFF',
    suffix: '+',
  },
  {
    icon: '💰',
    value: 3260,
    label: '交易笔数',
    subLabel: '+8.3% ↑',
    color: '#00B42A',
    suffix: '+',
  },
  {
    icon: '🏢',
    value: 156,
    label: '接入机构',
    subLabel: '+15.2% ↑',
    color: '#0FC6C2',
    suffix: '+',
  },
  {
    icon: '🔗',
    value: 89000,
    label: '存证数量',
    subLabel: '+22.1% ↑',
    color: '#722ED1',
    suffix: '+',
  },
];

/* ===== 动画计数器 Hook ===== */
function useCountUp(end: number, duration: number = 2000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [end, duration]);

  return count;
}

/* ===== 数字格式化 ===== */
function formatNumber(num: number): string {
  return num.toLocaleString();
}

/* ============================================================
 * StatusSection 主组件
 * ============================================================ */
const StatusSection: React.FC = () => {
  return (
    <section id="status" className="py-16 md:py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="section-title">平台运行数据</h2>
          <p className="section-subtitle">实时监控平台核心指标，保障数据空间安全稳定运行</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {STATS.map((stat) => (
            <StatCard key={stat.label} {...stat} />
          ))}
        </div>
      </div>
    </section>
  );
};

/* ===== 统计卡片组件 ===== */
interface StatCardProps {
  icon: string;
  value: number;
  label: string;
  subLabel: string;
  color: string;
  suffix: string;
}

const StatCard: React.FC<StatCardProps> = ({ icon, value, label, subLabel, color, suffix }) => {
  const count = useCountUp(value);

  return (
    <div
      className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-300"
      style={{ borderLeft: `4px solid ${color}` }}
    >
      <div className="flex items-center justify-between mb-4">
        <span className="text-3xl">{icon}</span>
        <span
          className="text-sm font-medium px-2 py-1 rounded-full"
          style={{ backgroundColor: `${color}15`, color }}
        >
          {subLabel}
        </span>
      </div>
      <div className="stat-number" style={{ color }}>
        {formatNumber(count)}{suffix}
      </div>
      <div className="text-gray-600 text-sm mt-1">{label}</div>
    </div>
  );
};

export default StatusSection;