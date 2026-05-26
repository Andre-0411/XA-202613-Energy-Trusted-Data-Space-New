// @ts-nocheck
/**
 * 侧边栏菜单组件（TDesign React 版）
 * 从 MainLayout.tsx 提取菜单配置，使用 tdesign-react Menu 组件
 * 支持折叠/展开、路由联动、角色权限过滤、高对比度模式
 */
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, Tooltip } from 'tdesign-react';
import {
  DashboardIcon,
  DataBaseIcon,
  CalculationIcon,
  LinkIcon,
  SystemSettingIcon,
  SecuredIcon,
  NotificationIcon,
  FullscreenIcon,
  ContrastIcon,
  InternetIcon,
  FlashlightIcon,
  ChartBarIcon,
} from 'tdesign-icons-react';
import { useAuthStore } from '@/stores/authStore';
import { getFilteredNavItems, type UserRole } from '@/config/rolePermissions';

/** 导航菜单项类型 */
interface NavChild {
  label: string;
  path: string;
}

interface NavItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  children?: NavChild[];
}

/** 导航菜单配置 — 与 MainLayout.tsx 保持一致 */
const NAV_ITEMS: NavItem[] = [
  {
    key: 'dashboard',
    label: '控制台',
    icon: <DashboardIcon />,
    path: '/dashboard',
  },
  {
    key: 'data',
    label: '数据中心',
    icon: <DataBaseIcon />,
    path: '/dashboard/data/sources',
    children: [
      { label: '数据源管理', path: '/dashboard/data/sources' },
      { label: '数据资产', path: '/dashboard/data/assets' },
      { label: '数据目录', path: '/dashboard/data/catalog' },
      { label: '数据服务市场', path: '/dashboard/data/market' },
      { label: '服务申请审批', path: '/dashboard/data/application' },
      { label: '元数据管理', path: '/dashboard/data/metadata' },
      { label: '数据血缘', path: '/dashboard/data/lineage' },
      { label: '数据质量', path: '/dashboard/data/quality' },
      { label: '数据生命周期', path: '/dashboard/data/lifecycle' },
      { label: '供需撮合', path: '/dashboard/data/matching' },
    ],
  },
  {
    key: 'compute',
    label: '计算中心',
    icon: <CalculationIcon />,
    path: '/dashboard/compute/tasks',
    children: [
      { label: '计算任务', path: '/dashboard/compute/tasks' },
      { label: '创建任务', path: '/dashboard/compute/create' },
      { label: 'DAG 画布', path: '/dashboard/compute/dag' },
      { label: '计算沙箱', path: '/dashboard/compute/sandbox' },
      { label: '计算代理', path: '/dashboard/compute/agents' },
      { label: '性能基准', path: '/dashboard/compute/benchmark' },
      { label: '计算集群', path: '/dashboard/compute/cluster' },
      { label: '隐私计算', path: '/dashboard/compute/privacy' },
    ],
  },
  {
    key: 'blockchain',
    label: '区块链中心',
    icon: <LinkIcon />,
    path: '/dashboard/blockchain/assets',
    children: [
      { label: '链上资产', path: '/dashboard/blockchain/assets' },
      { label: '存证管理', path: '/dashboard/blockchain/evidence' },
      { label: '智能合约', path: '/dashboard/blockchain/contracts' },
      { label: '链上结算', path: '/dashboard/blockchain/settlement' },
      { label: '链上查询', path: '/dashboard/blockchain/query' },
    ],
  },
  {
    key: 'ops',
    label: '运营中心',
    icon: <SystemSettingIcon />,
    path: '/dashboard/ops/users',
    children: [
      { label: '用户管理', path: '/dashboard/ops/users' },
      { label: '组织管理', path: '/dashboard/ops/organizations' },
      { label: '服务管理', path: '/dashboard/ops/services' },
      { label: '计费管理', path: '/dashboard/ops/billing' },
      { label: '收益分配', path: '/dashboard/ops/revenue' },
      { label: '运维监控', path: '/dashboard/ops/monitor' },
      { label: '合规审计', path: '/dashboard/ops/compliance' },
      { label: '运营指标', path: '/dashboard/ops/kpi' },
      { label: 'AI Agent 管理', path: '/dashboard/ops/agent-manage' },
      { label: '通知中心', path: '/dashboard/ops/notifications' },
      { label: '系统配置', path: '/dashboard/ops/system-config' },
      { label: '操作日志', path: '/dashboard/ops/audit-logs' },
    ],
  },
  {
    key: 'security',
    label: '安全中心',
    icon: <SecuredIcon />,
    path: '/dashboard/security/policies',
    children: [
      { label: '安全设置', path: '/security/settings' },
      { label: '安全策略', path: '/dashboard/security/policies' },
      { label: 'DID 身份', path: '/dashboard/security/did' },
      { label: '可验证凭证', path: '/dashboard/security/vc' },
      { label: '密钥管理', path: '/dashboard/security/keys' },
      { label: '威胁监测', path: '/dashboard/security/threats' },
      { label: '国密算法', path: '/dashboard/security/crypto' },
      { label: '零知识证明', path: '/dashboard/security/zkp' },
      { label: '安全等级', path: '/dashboard/security/levels' },
    ],
  },
  {
    key: 'tds',
    label: '可信数据空间',
    icon: <InternetIcon />,
    path: '/dashboard/tds/organizations',
    children: [
      { label: '机构管理', path: '/dashboard/tds/organizations' },
      { label: '连接器管理', path: '/dashboard/tds/connectors' },
      { label: '数据目录管理', path: '/dashboard/tds/catalog' },
      { label: '数据订阅', path: '/dashboard/tds/subscriptions' },
      { label: '数据产品管理', path: '/dashboard/tds/products' },
      { label: '产品上架', path: '/dashboard/tds/product-publish' },
      { label: '产品市场', path: '/dashboard/tds/market' },
      { label: '需求管理', path: '/dashboard/tds/demands' },
      { label: '合约管理', path: '/dashboard/tds/contracts' },
      { label: '连接器文件库', path: '/dashboard/tds/files' },
      { label: '审批工作流', path: '/dashboard/tds/workflows' },
      { label: '审批记录', path: '/dashboard/tds/approvals' },
    ],
  },
  {
    key: 'scenario',
    label: '业务场景',
    icon: <FlashlightIcon />,
    path: '/dashboard/scenario/power-dispatch',
    children: [
      { label: 'AI智能助手', path: '/dashboard/portal/agent-chat' },
      { label: '电网调度优化', path: '/dashboard/scenario/power-dispatch' },
      { label: '新能源消纳管理', path: '/dashboard/scenario/renewable-energy' },
      { label: '虚拟电厂运营', path: '/dashboard/scenario/virtual-power-plant' },
      { label: '电力市场交易', path: '/dashboard/scenario/power-trading' },
    ],
  },
  {
    key: 'portal',
    label: '门户功能',
    icon: <NotificationIcon />,
    path: '/dashboard/portal/announcements',
    children: [
      { label: '机构认证', path: '/dashboard/portal/org-certification' },
      { label: '个人中心', path: '/dashboard/portal/profile' },
      { label: '公告通知', path: '/dashboard/portal/announcements' },
    ],
  },
  {
    key: 'scenario',
    label: '业务场景',
    icon: <ChartBarIcon />,
    path: '/dashboard/scene/power-dispatch',
    children: [
      { label: '电网调度优化', path: '/dashboard/scene/power-dispatch' },
      { label: '新能源消纳管理', path: '/dashboard/scene/renewable-energy' },
      { label: '虚拟电厂运营', path: '/dashboard/scene/virtual-power-plant' },
      { label: '电力市场交易', path: '/dashboard/scene/power-trading' },
    ],
  },
];

/** 路径→菜单项反向索引（用于从路径推导 activeKey） */
function buildPathMenuMap(items: NavItem[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of items) {
    if (item.children) {
      for (const child of item.children) {
        map.set(child.path, child.path);
      }
    }
    map.set(item.path, item.key);
  }
  return map;
}

/** 根据当前路径推导 activeMenu value 和需要展开的 SubMenu key */
function deriveActiveState(
  pathname: string,
  items: NavItem[],
): { activeValue: string; expandedKeys: string[] } {
  // 优先精确匹配子菜单路径
  for (const item of items) {
    if (item.children) {
      for (const child of item.children) {
        if (pathname === child.path) {
          return { activeValue: child.path, expandedKeys: [item.key] };
        }
      }
    }
  }
  // 其次匹配父菜单
  for (const item of items) {
    if (pathname === item.path || pathname.startsWith(item.path + '/')) {
      return { activeValue: item.key, expandedKeys: [] };
    }
  }
  return { activeValue: 'dashboard', expandedKeys: [] };
}

/** 组件 Props */
interface SidebarMenuProps {
  /** 侧边栏是否折叠 */
  collapsed: boolean;
  /** 折叠状态变更回调 */
  onCollapsedChange: (collapsed: boolean) => void;
}

/**
 * 侧边栏菜单组件
 * 使用 tdesign-react Menu 实现多级导航
 */
const SidebarMenu: React.FC<SidebarMenuProps> = ({ collapsed, onCollapsedChange }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // 认证 store — 获取用户角色做菜单过滤
  const user = useAuthStore((s) => s.user);
  const userRole = (user?.role || 'user') as UserRole;

  // 高对比度模式状态
  const [highContrast, setHighContrast] = useState(false);

  // 高对比度模式切换
  useEffect(() => {
    if (highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
  }, [highContrast]);

  // 角色过滤后的菜单项
  const filteredNavItems = useMemo(
    () => getFilteredNavItems(userRole, NAV_ITEMS),
    [userRole],
  );

  // 根据当前路径推导 active 值和展开的 SubMenu
  const { activeValue, expandedKeys: initialExpanded } = useMemo(
    () => deriveActiveState(location.pathname, filteredNavItems),
    [location.pathname, filteredNavItems],
  );

  // 受控展开状态
  const [expanded, setExpanded] = useState<string[]>(initialExpanded);

  // 路径变化时同步展开状态
  useEffect(() => {
    const { expandedKeys } = deriveActiveState(location.pathname, filteredNavItems);
    setExpanded((prev) => {
      const merged = new Set([...prev, ...expandedKeys]);
      return Array.from(merged);
    });
  }, [location.pathname, filteredNavItems]);

  /** 菜单项点击处理 */
  const handleChange = useCallback(
    (value: string | number) => {
      const val = String(value);
      // 检查是否是路径（以 / 开头）
      if (val.startsWith('/')) {
        navigate(val);
      } else {
        // 是父菜单 key，导航到其默认路径
        const item = filteredNavItems.find((i) => i.key === val);
        if (item?.path) {
          navigate(item.path);
        }
      }
    },
    [navigate, filteredNavItems],
  );

  /** 展开状态变更 */
  const handleExpand = useCallback((keys: (string | number)[]) => {
    setExpanded(keys.map(String));
  }, []);

  /** 渲染菜单项 — 递归处理嵌套结构 */
  const renderMenuItems = useCallback(
    (items: NavItem[]) => {
      return items.map((item) => {
        const hasChildren = item.children && item.children.length > 0;
        if (hasChildren) {
          return (
            <Menu.SubMenu
              key={item.key}
              value={item.key}
              title={item.label}
              icon={item.icon}
            >
              {item.children!.map((child) => (
                <Menu.MenuItem key={child.path} value={child.path}>
                  {child.label}
                </Menu.MenuItem>
              ))}
            </Menu.SubMenu>
          );
        }
        return (
          <Menu.MenuItem key={item.key} value={item.key} icon={item.icon}>
            {item.label}
          </Menu.MenuItem>
        );
      });
    },
    [],
  );

  /** Logo 区域内容 */
  const logoContent = (
    <div
      style={{
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        padding: collapsed ? '0' : '0 20px',
        gap: '12px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        flexShrink: 0,
      }}
    >
      {/* Logo 图标 */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #0052d9 0%, #2b82e8 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontWeight: 800,
          fontSize: '1.1rem',
          boxShadow: '0 4px 12px rgba(0, 82, 217, 0.3)',
          flexShrink: 0,
        }}
      >
        E
      </div>
      {!collapsed && (
        <div style={{ overflow: 'hidden', flex: 1 }}>
          <div
            style={{
              color: '#fff',
              fontWeight: 700,
              fontSize: '0.95rem',
              lineHeight: 1.3,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            能源可信数据空间
          </div>
          <div
            style={{
              color: 'rgba(255, 255, 255, 0.5)',
              fontSize: '0.7rem',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            Energy Trusted Data Space
          </div>
        </div>
      )}
    </div>
  );

  /** 无障碍设置区域 */
  const accessibilitySection = (
    <div style={{ padding: collapsed ? '8px 0' : '8px 12px', flexShrink: 0 }}>
      <Tooltip content="切换高对比度模式" placement="right" showArrow>
        <div
          role="switch"
          aria-checked={highContrast}
          aria-label="切换高对比度模式"
          tabIndex={0}
          onClick={() => setHighContrast(!highContrast)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setHighContrast(!highContrast);
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: '8px',
            padding: '8px 12px',
            borderRadius: '6px',
            cursor: 'pointer',
            color: 'rgba(255, 255, 255, 0.55)',
            fontSize: '0.75rem',
            transition: 'all 0.2s',
          }}
        >
          <ContrastIcon style={{ fontSize: '16px' }} />
          {!collapsed && <span>高对比度</span>}
        </div>
      </Tooltip>
    </div>
  );

  /** 监管大屏入口 */
  const monitorScreenEntry = (
    <div style={{ padding: collapsed ? '0 0 8px' : '0 12px 8px', flexShrink: 0 }}>
      <Tooltip content="打开监管大屏" placement="right" showArrow>
        <div
          role="button"
          tabIndex={0}
          aria-label="打开监管大屏"
          onClick={() => navigate('/monitor-screen')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              navigate('/monitor-screen');
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: '10px',
            padding: collapsed ? '10px 0' : '10px 16px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #0052d9 0%, #7b1fa2 100%)',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.875rem',
            transition: 'all 0.2s',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          <FullscreenIcon style={{ fontSize: '18px', flexShrink: 0 }} />
          {!collapsed && <span>监管大屏</span>}
        </div>
      </Tooltip>
    </div>
  );

  /** 折叠按钮 */
  const collapseButton = (
    <div
      style={{
        position: 'absolute',
        bottom: '16px',
        left: 0,
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        zIndex: 10,
      }}
    >
      <Tooltip content={collapsed ? '展开侧边栏' : '收起侧边栏'} placement="right" showArrow>
        <div
          role="button"
          tabIndex={0}
          aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
          onClick={() => onCollapsedChange(!collapsed)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onCollapsedChange(!collapsed);
            }
          }}
          style={{
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '6px',
            cursor: 'pointer',
            color: 'rgba(255, 255, 255, 0.4)',
            transition: 'all 0.2s',
            fontSize: '14px',
          }}
        >
          {collapsed ? '>' : '<'}
        </div>
      </Tooltip>
    </div>
  );

  return (
    <aside
      aria-label="导航侧边栏"
      style={{
        width: collapsed ? '64px' : '232px',
        height: '100vh',
        backgroundColor: '#18181D',
        transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '2px 0 8px rgba(0, 0, 0, 0.08)',
        overflow: 'hidden',
      }}
    >
      {/* Logo 区域 */}
      {logoContent}

      {/* 导航菜单 */}
      <div style={{ flex: 1, overflow: 'auto', paddingTop: '8px' }}>
        <Menu
          value={activeValue}
          expanded={expanded}
          onChange={handleChange}
          onExpand={handleExpand}
          collapsed={collapsed}
          theme="dark"
          width={collapsed ? '64px' : '232px'}
          style={{ backgroundColor: 'transparent', borderRight: 'none' }}
        >
          {renderMenuItems(filteredNavItems)}
        </Menu>
      </div>

      {/* 无障碍设置 + 监管大屏 + 折叠按钮区域 */}
      <div style={{ position: 'relative', flexShrink: 0 }}>
        {accessibilitySection}
        {monitorScreenEntry}
        {collapseButton}
      </div>
    </aside>
  );
};

export default SidebarMenu;
