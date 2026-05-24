/**
 * 角色权限配置
 * 定义不同角色可以访问的菜单项和路由
 */

export type UserRole = 'admin' | 'data_admin' | 'user' | 'auditor' | 'operator';

export interface NavItemConfig {
  key: string;
  label: string;
  icon: string;
  path: string;
  children?: { label: string; path: string }[];
}

/**
 * 角色-菜单映射配置
 * 每个角色可以访问的菜单项 key 列表
 */
export const ROLE_MENU_ACCESS: Record<UserRole, string[]> = {
  // 系统管理员：可以访问所有菜单
  admin: [
    'dashboard',
    'data',
    'compute',
    'blockchain',
    'ops',
    'security',
    'portal',
  ],
  
  // 数据管理员：数据中心 + 计算中心 + 门户功能
  data_admin: [
    'dashboard',
    'data',
    'compute',
    'portal',
  ],
  
  // 普通用户：数据中心（只读）+ 计算中心（基础）+ 门户功能
  user: [
    'dashboard',
    'data',
    'compute',
    'portal',
  ],
  
  // 审计员：运营中心 + 安全中心 + 区块链中心 + 门户功能
  auditor: [
    'dashboard',
    'ops',
    'security',
    'blockchain',
    'portal',
  ],
  
  // 运维人员：运维中心 + 安全中心 + 计算中心 + 门户功能
  operator: [
    'dashboard',
    'ops',
    'security',
    'compute',
    'portal',
  ],
};

/**
 * 角色-路由权限映射
 * 定义每个角色可以访问的具体路由路径
 */
export const ROLE_ROUTE_ACCESS: Record<UserRole, string[]> = {
  admin: ['*'], // 管理员可以访问所有路由

  data_admin: [
    '/dashboard',
    '/dashboard/data/*',
    '/dashboard/compute/*',
    '/dashboard/portal/*',
  ],

  user: [
    '/dashboard',
    '/dashboard/data/sources',
    '/dashboard/data/assets',
    '/dashboard/data/catalog',
    '/dashboard/data/market',
    '/dashboard/data/application',
    '/dashboard/data/requests',
    '/dashboard/data/metadata',
    '/dashboard/data/lineage',
    '/dashboard/data/quality',
    '/dashboard/compute/tasks',
    '/dashboard/compute/create',
    '/dashboard/compute/dag',
    '/dashboard/compute/sandbox',
    '/dashboard/compute/agents',
    '/dashboard/compute/benchmark',
    '/dashboard/compute/cluster',
    '/dashboard/portal/*',
  ],

  auditor: [
    '/dashboard',
    '/dashboard/ops/*',
    '/dashboard/security/*',
    '/dashboard/blockchain/*',
    '/dashboard/portal/*',
  ],

  operator: [
    '/dashboard',
    '/dashboard/ops/*',
    '/dashboard/security/*',
    '/dashboard/compute/*',
    '/dashboard/portal/*',
  ],
};

/**
 * 角色特定仪表板配置
 * 定义每个角色仪表板显示的统计卡片和图表
 */
export interface DashboardWidget {
  id: string;
  title: string;
  type: 'stat_card' | 'chart' | 'table' | 'alert';
  size: 'small' | 'medium' | 'large';
  priority: number;
}

export const ROLE_DASHBOARD_CONFIG: Record<UserRole, DashboardWidget[]> = {
  admin: [
    { id: 'total_users', title: '总用户数', type: 'stat_card', size: 'small', priority: 1 },
    { id: 'total_assets', title: '数据资产总数', type: 'stat_card', size: 'small', priority: 2 },
    { id: 'active_tasks', title: '活跃计算任务', type: 'stat_card', size: 'small', priority: 3 },
    { id: 'system_health', title: '系统健康度', type: 'stat_card', size: 'small', priority: 4 },
    { id: 'user_growth_trend', title: '用户增长趋势', type: 'chart', size: 'medium', priority: 5 },
    { id: 'asset_distribution', title: '资产类型分布', type: 'chart', size: 'medium', priority: 6 },
    { id: 'recent_alerts', title: '最近告警', type: 'alert', size: 'large', priority: 7 },
    { id: 'system_performance', title: '系统性能监控', type: 'chart', size: 'large', priority: 8 },
  ],
  
  data_admin: [
    { id: 'my_assets', title: '我管理的资产', type: 'stat_card', size: 'small', priority: 1 },
    { id: 'data_quality_score', title: '数据质量评分', type: 'stat_card', size: 'small', priority: 2 },
    { id: 'pending_requests', title: '待处理申请', type: 'stat_card', size: 'small', priority: 3 },
    { id: 'data_usage', title: '数据使用量', type: 'stat_card', size: 'small', priority: 4 },
    { id: 'asset_growth', title: '资产增长趋势', type: 'chart', size: 'medium', priority: 5 },
    { id: 'quality_trend', title: '质量趋势', type: 'chart', size: 'medium', priority: 6 },
    { id: 'recent_activities', title: '最近操作', type: 'table', size: 'large', priority: 7 },
  ],
  
  user: [
    { id: 'my_tasks', title: '我的任务', type: 'stat_card', size: 'small', priority: 1 },
    { id: 'available_assets', title: '可用资产', type: 'stat_card', size: 'small', priority: 2 },
    { id: 'my_usage', title: '我的使用量', type: 'stat_card', size: 'small', priority: 3 },
    { id: 'notifications', title: '未读通知', type: 'stat_card', size: 'small', priority: 4 },
    { id: 'task_history', title: '任务历史', type: 'chart', size: 'medium', priority: 5 },
    { id: 'data_catalog', title: '数据目录', type: 'chart', size: 'medium', priority: 6 },
  ],
  
  auditor: [
    { id: 'compliance_score', title: '合规评分', type: 'stat_card', size: 'small', priority: 1 },
    { id: 'security_incidents', title: '安全事件', type: 'stat_card', size: 'small', priority: 2 },
    { id: 'audit_logs', title: '审计日志', type: 'stat_card', size: 'small', priority: 3 },
    { id: 'blockchain_txs', title: '区块链交易', type: 'stat_card', size: 'small', priority: 4 },
    { id: 'compliance_trend', title: '合规趋势', type: 'chart', size: 'medium', priority: 5 },
    { id: 'threat_distribution', title: '威胁分布', type: 'chart', size: 'medium', priority: 6 },
    { id: 'recent_audits', title: '最近审计', type: 'table', size: 'large', priority: 7 },
  ],
  
  operator: [
    { id: 'system_uptime', title: '系统运行时间', type: 'stat_card', size: 'small', priority: 1 },
    { id: 'active_alerts', title: '活跃告警', type: 'stat_card', size: 'small', priority: 2 },
    { id: 'compute_nodes', title: '计算节点', type: 'stat_card', size: 'small', priority: 3 },
    { id: 'resource_usage', title: '资源使用率', type: 'stat_card', size: 'small', priority: 4 },
    { id: 'performance_trend', title: '性能趋势', type: 'chart', size: 'medium', priority: 5 },
    { id: 'node_status', title: '节点状态', type: 'chart', size: 'medium', priority: 6 },
    { id: 'recent_operations', title: '最近操作', type: 'table', size: 'large', priority: 7 },
  ],
};

/**
 * 角色显示名称映射
 */
export const ROLE_DISPLAY_NAMES: Record<UserRole, string> = {
  admin: '系统管理员',
  data_admin: '数据管理员',
  user: '普通用户',
  auditor: '审计员',
  operator: '运维人员',
};

/**
 * 角色描述
 */
export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: '拥有系统所有功能的完全访问权限',
  data_admin: '负责数据资产管理、数据质量监控和数据服务管理',
  user: '可以浏览数据目录、提交计算任务和查看个人使用情况',
  auditor: '负责合规审计、安全监控和区块链存证验证',
  operator: '负责系统运维、性能监控和安全管理',
};

/**
 * 检查角色是否有权访问指定菜单
 */
export function hasMenuAccess(role: UserRole, menuKey: string): boolean {
  const allowedMenus = ROLE_MENU_ACCESS[role];
  return allowedMenus.includes(menuKey);
}

/**
 * 检查角色是否有权访问指定路由
 */
export function hasRouteAccess(role: UserRole, routePath: string): boolean {
  const allowedRoutes = ROLE_ROUTE_ACCESS[role];

  // 防御性检查：角色不在映射中则拒绝访问
  if (!allowedRoutes) return false;

  // 管理员可以访问所有路由
  if (allowedRoutes.includes('*')) {
    return true;
  }
  
  // 检查精确匹配或通配符匹配
  return allowedRoutes.some(pattern => {
    if (pattern.endsWith('/*')) {
      const prefix = pattern.slice(0, -2);
      return routePath.startsWith(prefix);
    }
    return routePath === pattern;
  });
}

/**
 * 获取角色可访问的菜单项
 */
export function getFilteredNavItems(role: UserRole, navItems: any[]): any[] {
  return navItems.filter(item => hasMenuAccess(role, item.key));
}

/**
 * 获取角色特定的仪表板配置
 */
export function getDashboardConfig(role: UserRole): DashboardWidget[] {
  return ROLE_DASHBOARD_CONFIG[role] || ROLE_DASHBOARD_CONFIG.user;
}