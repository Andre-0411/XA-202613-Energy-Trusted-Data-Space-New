/**
 * 顶栏组件（TDesign React 版）
 * 从 MainLayout.tsx 提取顶栏功能，使用 tdesign-react 组件
 * 包含：折叠按钮、面包屑导航、通知、主题切换、用户菜单
 */
import React, { useMemo, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button, Badge, Dropdown, Avatar, Breadcrumb, Tooltip } from 'tdesign-react';
import {
  SearchIcon,
  NotificationIcon,
  UserIcon,
  MenuFoldIcon,
  MenuUnfoldIcon,
  ModeDarkIcon,
  ModeLightIcon,
  LogoutIcon,
  UserIcon as PersonIcon,
} from 'tdesign-icons-react';
import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';
import { ROLE_DISPLAY_NAMES, type UserRole } from '@/config/rolePermissions';
import type { DropdownOption } from 'tdesign-react/es/dropdown/type';

/** 路径→标签映射 — 与 MainLayout.tsx 保持一致 */
const PATH_LABEL_MAP: Record<string, string> = {
  '/dashboard': '控制台',
  '/dashboard/data/sources': '数据源管理',
  '/dashboard/data/assets': '数据资产',
  '/dashboard/data/catalog': '数据目录',
  '/dashboard/data/market': '数据服务市场',
  '/dashboard/data/requests': '服务申请管理',
  '/dashboard/data/application': '服务申请审批',
  '/dashboard/data/metadata': '元数据管理',
  '/dashboard/data/lineage': '数据血缘',
  '/dashboard/data/quality': '数据质量',
  '/dashboard/compute/tasks': '计算任务',
  '/dashboard/compute/create': '创建任务',
  '/dashboard/compute/dag': 'DAG 画布',
  '/dashboard/compute/sandbox': '计算沙箱',
  '/dashboard/compute/agents': '计算代理',
  '/dashboard/compute/benchmark': '性能基准',
  '/dashboard/compute/cluster': '计算集群',
  '/dashboard/compute/privacy': '隐私计算',
  '/dashboard/blockchain/assets': '链上资产',
  '/dashboard/blockchain/evidence': '存证管理',
  '/dashboard/blockchain/contracts': '智能合约',
  '/dashboard/blockchain/settlement': '链上结算',
  '/dashboard/blockchain/query': '链上查询',
  '/dashboard/ops/users': '用户管理',
  '/dashboard/ops/organizations': '组织管理',
  '/dashboard/ops/services': '服务管理',
  '/dashboard/ops/billing': '计费管理',
  '/dashboard/ops/monitor': '运维监控',
  '/dashboard/ops/compliance': '合规审计',
  '/dashboard/ops/kpi': '运营指标',
  '/dashboard/ops/agent-manage': 'AI Agent 管理',
  '/dashboard/ops/notifications': '通知中心',
  '/dashboard/ops/system-config': '系统配置',
  '/dashboard/ops/audit-logs': '操作日志',
  '/dashboard/security/policies': '安全策略',
  '/dashboard/security/did': 'DID 身份',
  '/dashboard/security/vc': '可验证凭证',
  '/dashboard/security/keys': '密钥管理',
  '/dashboard/security/threats': '威胁监测',
  '/dashboard/security/crypto': '国密算法',
  '/dashboard/security/zkp': '零知识证明',
  '/dashboard/security/levels': '安全等级',
  '/dashboard/portal/profile': '个人中心',
  '/dashboard/portal/announcements': '公告通知',
  '/dashboard/tds/organizations': '机构管理',
  '/dashboard/tds/connectors': '连接器管理',
  '/dashboard/tds/catalog': '数据目录管理',
  '/dashboard/tds/subscriptions': '数据订阅',
  '/dashboard/tds/products': '数据产品管理',
  '/dashboard/tds/product-publish': '产品上架',
  '/dashboard/tds/market': '产品市场',
  '/dashboard/tds/demands': '需求管理',
  '/dashboard/tds/contracts': '合约管理',
  '/dashboard/tds/files': '连接器文件库',
  '/dashboard/tds/workflows': '审批工作流',
  '/dashboard/tds/approvals': '审批记录',
  '/monitor-screen': '监管大屏',
};

/** 面包屑映射 — 与 MainLayout.tsx 保持一致 */
const BREADCRUMB_MAP: Record<string, string> = {
  '': '控制台',
  dashboard: '控制台',
  data: '数据中心',
  compute: '计算中心',
  blockchain: '区块链中心',
  ops: '运营中心',
  security: '安全中心',
  portal: '门户功能',
  tds: '可信数据空间',
  sources: '数据源管理',
  assets: '数据资产',
  catalog: '数据目录',
  market: '数据服务市场',
  requests: '服务申请管理',
  application: '服务申请',
  metadata: '元数据管理',
  lineage: '数据血缘',
  quality: '数据质量',
  tasks: '计算任务',
  create: '创建任务',
  dag: 'DAG 画布',
  sandbox: '计算沙箱',
  agents: '计算代理',
  benchmark: '性能基准',
  cluster: '计算集群',
  privacy: '隐私计算',
  evidence: '存证管理',
  contracts: '智能合约',
  settlement: '链上结算',
  query: '链上查询',
  users: '用户管理',
  organizations: '组织管理',
  services: '服务管理',
  billing: '计费管理',
  monitor: '运维监控',
  compliance: '合规审计',
  kpi: '运营指标',
  'agent-manage': 'AI Agent 管理',
  notifications: '通知中心',
  'system-config': '系统配置',
  'audit-logs': '操作日志',
  policies: '安全策略',
  did: 'DID 身份',
  vc: '可验证凭证',
  keys: '密钥管理',
  threats: '威胁监测',
  crypto: '国密算法',
  zkp: '零知识证明',
  levels: '安全等级',
  announcements: '公告通知',
  profile: '个人中心',
  /* TDS 面包屑用路径前缀区分，避免与 ops 段名冲突 */
  'tds/organizations': '机构管理',
  'tds/connectors': '连接器管理',
  'tds/catalog': '数据目录管理',
  'tds/subscriptions': '数据订阅',
  'tds/products': '数据产品管理',
  'tds/product-publish': '产品上架',
  'tds/market': '产品市场',
  'tds/demands': '需求管理',
  'tds/contracts': '合约管理',
  'tds/files': '连接器文件库',
  'tds/workflows': '审批工作流',
  'tds/approvals': '审批记录',
};

/** 用户角色颜色 */
const ROLE_COLOR_MAP: Record<string, string> = {
  admin: '#d32f2f',
  data_admin: '#1976d2',
  compute_admin: '#2e7d32',
  security_admin: '#ed6c02',
  user: '#7b1fa2',
};

/** 组件 Props */
interface HeaderBarProps {
  /** 侧边栏是否折叠 */
  collapsed: boolean;
  /** 切换侧边栏折叠 */
  onToggleSidebar: () => void;
}

/**
 * 顶栏组件
 * 包含面包屑导航、通知、主题切换、用户菜单
 */
const HeaderBar: React.FC<HeaderBarProps> = ({ collapsed, onToggleSidebar }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // 应用状态
  const themeMode = useAppStore((s) => s.themeMode);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const notifications = useAppStore((s) => s.notifications);

  // 认证状态
  const user = useAuthStore((s) => s.user);
  const userRole = (user?.role || 'user') as UserRole;
  const unreadCount = notifications.filter((n) => !n.read).length;

  /** 面包屑数据生成 — 优先匹配路径前缀，回退到段名 */
  const breadcrumbs = useMemo(() => {
    const segments = location.pathname.split('/').filter(Boolean);
    if (segments.length === 0 || (segments.length === 1 && segments[0] === 'dashboard')) {
      return [{ label: '控制台', path: '/dashboard' }];
    }
    const filtered = segments.filter((seg) => seg !== 'dashboard');
    return [
      { label: '控制台', path: '/dashboard' },
      ...filtered.map((seg, idx) => {
        const pathKey = filtered.slice(0, idx + 1).join('/');
        return {
          label: BREADCRUMB_MAP[pathKey] || BREADCRUMB_MAP[seg] || seg,
          path: '/dashboard/' + pathKey,
        };
      }),
    ];
  }, [location.pathname]);

  /** 面包屑点击 */
  const handleBreadcrumbClick = useCallback(
    (path: string, e: React.MouseEvent) => {
      e.preventDefault();
      navigate(path);
    },
    [navigate],
  );

  /** 通知按钮点击 */
  const handleNotificationClick = useCallback(() => {
    navigate('/dashboard/ops/notifications');
  }, [navigate]);

  /** 退出登录 */
  const handleLogout = useCallback(() => {
    localStorage.removeItem('eds_token');
    localStorage.removeItem('eds_refresh_token');
    localStorage.removeItem('eds-auth-storage');
    navigate('/login');
  }, [navigate]);

  /** 用户菜单点击 */
  const handleUserMenuClick = useCallback(
    (dropdownItem: DropdownOption) => {
      const val = dropdownItem.value as string;
      if (val === 'profile') {
        navigate('/dashboard/portal/profile');
      } else if (val === 'logout') {
        handleLogout();
      }
    },
    [navigate, handleLogout],
  );

  /** 用户下拉菜单选项 */
  const userMenuOptions: DropdownOption[] = [
    {
      content: '个人信息',
      value: 'profile',
      prefixIcon: <PersonIcon />,
    },
    {
      content: '退出登录',
      value: 'logout',
      prefixIcon: <LogoutIcon />,
      theme: 'error' as const,
      divider: true,
    },
  ];

  /** 面包屑渲染 — 转换为 TDesign Breadcrumb 格式 */
  const breadcrumbItems = breadcrumbs.map((crumb, idx) => {
    const isLast = idx === breadcrumbs.length - 1;
    return (
      <Breadcrumb.BreadcrumbItem
        key={crumb.path}
        maxItemWidth="160px"
        onClick={!isLast ? (e: React.MouseEvent) => handleBreadcrumbClick(crumb.path, e) : undefined}
        style={{
          cursor: isLast ? 'default' : 'pointer',
          fontWeight: isLast ? 600 : 400,
          color: isLast ? '#1a1a1a' : '#8c8c8c',
          fontSize: '0.8125rem',
        }}
      >
        {crumb.label}
      </Breadcrumb.BreadcrumbItem>
    );
  });

  return (
    <header
      aria-label="顶部导航栏"
      style={{
        height: '52px',
        backgroundColor: '#FFFFFF',
        borderBottom: '1px solid #E8E8E8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 99,
        flexShrink: 0,
      }}
    >
      {/* 左侧：折叠按钮 + 面包屑 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
        <Tooltip content={collapsed ? '展开侧边栏' : '收起侧边栏'} placement="bottom">
          <Button
            variant="text"
            shape="square"
            icon={collapsed ? <MenuUnfoldIcon /> : <MenuFoldIcon />}
            onClick={onToggleSidebar}
            aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
            style={{ flexShrink: 0 }}
          />
        </Tooltip>
        <Breadcrumb separator="/" maxItemWidth="120px" style={{ flex: 1, minWidth: 0 }}>
          {breadcrumbItems}
        </Breadcrumb>
      </div>

      {/* 右侧：搜索、通知、主题切换、用户菜单 */}
      <nav aria-label="工具栏" style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
        {/* 搜索按钮 */}
        <Tooltip content="搜索" placement="bottom">
          <Button
            variant="text"
            shape="square"
            icon={<SearchIcon />}
            aria-label="搜索"
          />
        </Tooltip>

        {/* 通知按钮 */}
        <Tooltip content={`通知，${unreadCount} 条未读`} placement="bottom">
          <Button
            variant="text"
            shape="square"
            onClick={handleNotificationClick}
            aria-label={`通知，${unreadCount} 条未读`}
          >
            <Badge count={String(unreadCount)} maxCount={99} size="small">
              <NotificationIcon style={{ fontSize: '18px' }} />
            </Badge>
          </Button>
        </Tooltip>

        {/* 主题切换 */}
        <Tooltip
          content={themeMode === 'dark' ? '切换浅色主题' : '切换深色主题'}
          placement="bottom"
        >
          <Button
            variant="text"
            shape="square"
            icon={themeMode === 'dark' ? <ModeLightIcon /> : <ModeDarkIcon />}
            onClick={toggleTheme}
            aria-label={
              themeMode === 'dark'
                ? '当前深色主题，点击切换到浅色'
                : '当前浅色主题，点击切换到深色'
            }
          />
        </Tooltip>

        {/* 用户菜单 */}
        <Dropdown
          options={userMenuOptions}
          onClick={handleUserMenuClick}
          trigger="click"
          placement="bottom-right"
          minColumnWidth={160}
        >
          <div
            role="button"
            tabIndex={0}
            aria-label={`用户菜单: ${user?.username || '用户'}`}
            aria-haspopup="true"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginLeft: '8px',
              padding: '4px 8px',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <Avatar
              size="32px"
              style={{
                backgroundColor: ROLE_COLOR_MAP[userRole] || '#7b1fa2',
                fontSize: '0.8rem',
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              {(user?.username || 'U').charAt(0).toUpperCase()}
            </Avatar>
            <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
              <span
                style={{
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  lineHeight: 1.2,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '80px',
                }}
              >
                {user?.username || '用户'}
              </span>
              <span
                style={{
                  color: '#8c8c8c',
                  fontSize: '0.65rem',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {ROLE_DISPLAY_NAMES[userRole] || '普通用户'}
              </span>
            </div>
          </div>
        </Dropdown>
      </nav>
    </header>
  );
};

export default HeaderBar;
