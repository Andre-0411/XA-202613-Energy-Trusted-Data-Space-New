/**
 * StatusSection - 平台状态统计区域
 * 4个大数字卡片（接入后端 /portal/stats 真实数据）+ 系统健康状态
 */
import React, { useState, useEffect } from 'react';

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

function formatNumber(num: number): string {
  return num.toLocaleString();
}

/* ============================================================
 * StatusSection 主组件
 * ============================================================ */
interface PlatformStats {
  data_assets_total: number;
  transactions_total: number;
  organizations_total: number;
  evidences_total: number;
  system_uptime: number;
}

interface HealthStatus {
  status: string;
  database: { status: string };
  redis: { status: string };
  blockchain: { status: string };
  uptime: number;
}

const StatusSection: React.FC<{ platformMetrics?: any[]; dashboardLoading?: boolean }> = () => {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    // 获取平台统计数据（无需认证）
    fetch('/api/v1/portal/stats')
      .then(r => r.json())
      .then(d => setStats(d))
      .catch(() => {});

    // 获取系统健康状态
    fetch('/api/v1/health')
      .then(r => r.json())
      .then(d => setHealth(d))
      .catch(() => {});
  }, []);

  const statItems = [
    { icon: '📊', value: stats?.data_assets_total ?? 0, label: '数据资产', subLabel: '实时统计', color: '#165DFF', suffix: '+' },
    { icon: '💰', value: stats?.transactions_total ?? 0, label: '交易笔数', subLabel: '累计统计', color: '#00B42A', suffix: '' },
    { icon: '🏢', value: stats?.organizations_total ?? 0, label: '接入机构', subLabel: '活跃机构', color: '#0FC6C2', suffix: '+' },
    { icon: '🔗', value: stats?.evidences_total ?? 0, label: '存证数量', subLabel: '链上存证', color: '#722ED1', suffix: '+' },
  ];

  const healthItems = [
    { label: '数据库', status: health?.database?.status, icon: '🗄️' },
    { label: 'Redis缓存', status: health?.redis?.status, icon: '⚡' },
    { label: '区块链节点', status: health?.blockchain?.status, icon: '🔗' },
    { label: '系统可用率', status: health?.status, icon: '📈', value: `${stats?.system_uptime ?? 99.97}%` },
  ];

  return (
    <section id="status" className="py-16 md:py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="section-title">平台运行数据</h2>
          <p className="section-subtitle">实时监控平台核心指标，保障数据空间安全稳定运行</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statItems.map((stat) => (
            <StatCard key={stat.label} {...stat} />
          ))}
        </div>

        {/* 系统健康状态 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {healthItems.map((item) => {
            const isHealthy = item.status === 'healthy' || item.status === 'degraded';
            return (
              <div key={item.label} className="bg-white rounded-lg p-4 flex items-center gap-3 shadow-sm">
                <span className="text-xl">{item.icon}</span>
                <div>
                  <div className="text-sm font-medium text-gray-800">{item.label}</div>
                  <div className="flex items-center gap-1">
                    <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className={`text-xs ${isHealthy ? 'text-green-600' : 'text-red-600'}`}>
                      {item.value || (isHealthy ? '正常' : '异常')}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

/* ===== 统计卡片组件 ===== */
const StatCard: React.FC<{ icon: string; value: number; label: string; subLabel: string; color: string; suffix: string }> = ({ icon, value, label, subLabel, color, suffix }) => {
  const count = useCountUp(value);
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-300" style={{ borderLeft: `4px solid ${color}` }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-3xl">{icon}</span>
        <span className="text-sm font-medium px-2 py-1 rounded-full" style={{ backgroundColor: `${color}15`, color }}>{subLabel}</span>
      </div>
      <div className="stat-number" style={{ color }}>{formatNumber(count)}{suffix}</div>
      <div className="text-gray-600 text-sm mt-1">{label}</div>
    </div>
  );
};

export default StatusSection;
