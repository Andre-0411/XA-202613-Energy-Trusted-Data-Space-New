/**
 * QuickActions - 系统健康状态 + 快捷操作区域
 * 包含 SystemStatusIndicator 和 QuickActionCard 子组件
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SettingIcon, ComponentSwitchIcon,
} from 'tdesign-icons-react';

/* ===== SystemStatusIndicator 子组件 ===== */
interface SystemStatusProps {
  label: string;
  value: number;
  color: string;
  status: 'excellent' | 'good' | 'warning' | 'critical';
}

const SystemStatusIndicator: React.FC<SystemStatusProps> = ({ label, value, color, status }) => {
  const statusColors = {
    excellent: '#4caf50',
    good: '#8bc34a',
    warning: '#ff9800',
    critical: '#f44336',
  };

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-600">{label}</span>
        <div className="flex items-center gap-1">
          <div
            className={`w-2 h-2 rounded-full ${status === 'critical' ? 'animate-pulse' : ''}`}
            style={{ backgroundColor: statusColors[status] }}
          />
          <span className="text-xs text-gray-600">{value}%</span>
        </div>
      </div>
      <div className="w-full h-1.5 rounded-full" style={{ backgroundColor: `${color}26` }}>
        <div
          className="h-full rounded-full"
          style={{ width: `${value}%`, background: `linear-gradient(90deg, ${color}, ${color}b3)` }}
        />
      </div>
    </div>
  );
};

/* ===== QuickActionCard 子组件 ===== */
interface QuickActionProps {
  title: string;
  icon: React.ReactNode;
  color: string;
  path: string;
  description: string;
}

const QuickActionCard: React.FC<QuickActionProps> = ({ title, icon, color, path, description }) => {
  const navigate = useNavigate();

  return (
    <div
      className="rounded-xl bg-white border border-gray-200 cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg group"
      onClick={() => navigate(path)}
    >
      <div className="p-4 sm:p-5">
        <div className="flex items-center gap-3 sm:gap-4">
          <div
            className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center transition-all duration-300 group-hover:bg-white group-hover:text-white shrink-0"
            style={{ backgroundColor: `${color}1a`, color }}
          >
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate m-0">{title}</p>
            <p className="text-xs text-gray-500 truncate m-0 hidden sm:block">{description}</p>
          </div>
          <span className="text-gray-400 text-lg hidden sm:block">&rarr;</span>
        </div>
      </div>
    </div>
  );
};

/* ===== Props ===== */
interface QuickActionsProps {
  systemHealth: { label: string; value: number; color: string; status: 'excellent' | 'good' | 'warning' | 'critical' }[];
  quickActions: { title: string; icon: React.ReactNode; color: string; path: string; description: string }[];
}

/* ============================================================
 * QuickActions 主组件
 * ============================================================ */
const QuickActions: React.FC<QuickActionsProps> = ({ systemHealth, quickActions }) => {
  return (
    <div className="lg:col-span-4 flex flex-col gap-4 sm:gap-6">
      {/* 系统健康状态 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 sm:p-6">
        <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2 mb-4 m-0">
          <SettingIcon size="18px" />
          系统健康状态
        </h3>
        {systemHealth.map((item, index) => (
          <SystemStatusIndicator key={index} {...item} />
        ))}
      </div>

      {/* 快捷操作 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 sm:p-6">
        <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2 mb-4 m-0">
          <ComponentSwitchIcon size="18px" />
          快捷操作
        </h3>
        <div className="flex flex-col gap-3">
          {quickActions.map((action, index) => (
            <QuickActionCard key={index} {...action} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default QuickActions;
