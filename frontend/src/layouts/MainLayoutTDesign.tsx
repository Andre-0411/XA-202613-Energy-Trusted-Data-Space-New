/**
 * 主布局组件（TDesign React 版）
 * 组合 SidebarMenu + HeaderBar + TabBar + Content
 * 替代原有 MUI 版 MainLayout，保持一致的功能和无障碍支持
 *
 * 功能对照：
 *   - 侧边栏导航（SidebarMenu）
 *   - 顶栏面包屑 + 通知 + 主题切换 + 用户菜单（HeaderBar）
 *   - 多页签栏（TabBar）— 复用 appStore 的 tabs 状态
 *   - skip-to-content 链接
 *   - 屏幕阅读器通知播报
 *   - 页签右键菜单
 *   - 页面内容区
 *   - 底部 Footer
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Button, Tooltip } from 'tdesign-react';
import { CloseIcon } from 'tdesign-icons-react';
import SidebarMenu from '@/components/layout/SidebarMenu';
import HeaderBar from '@/components/layout/HeaderBar';
import { useAppStore } from '@/stores/appStore';

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

/** 侧边栏展开宽度 */
const SIDEBAR_WIDTH = 232;
/** 侧边栏折叠宽度 */
const SIDEBAR_COLLAPSED_WIDTH = 64;

/**
 * TDesign 版主布局组件
 */
const MainLayoutTDesign: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // 侧边栏折叠状态
  const [collapsed, setCollapsed] = useState(false);

  // 页签上下文菜单状态
  const [tabContextMenu, setTabContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    tabKey: string;
  } | null>(null);

  // 屏幕阅读器播报
  const [announcement, setAnnouncement] = useState('');

  // 主内容区 ref（用于 skip-to-content 聚焦）
  const mainContentRef = useRef<HTMLDivElement>(null);

  // 应用状态
  const tabs = useAppStore((s) => s.tabs);
  const activeTabKey = useAppStore((s) => s.activeTabKey);
  const addTab = useAppStore((s) => s.addTab);
  const removeTab = useAppStore((s) => s.removeTab);
  const setActiveTabKey = useAppStore((s) => s.setActiveTabKey);
  const closeOtherTabs = useAppStore((s) => s.closeOtherTabs);
  const closeAllTabs = useAppStore((s) => s.closeAllTabs);

  /** 屏幕阅读器播报 */
  const announce = useCallback((message: string) => {
    setAnnouncement('');
    setTimeout(() => setAnnouncement(message), 50);
  }, []);

  /** 路由变化时自动添加页签 + 播报 */
  useEffect(() => {
    const label = PATH_LABEL_MAP[location.pathname] || location.pathname.split('/').pop() || '未知';
    const key = location.pathname;
    addTab({ key, label, path: location.pathname });
    announce(`已导航到 ${label}`);
  }, [location.pathname, addTab, announce]);

  /** 键盘事件处理 — Escape 关闭弹出菜单 */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && tabContextMenu) {
        setTabContextMenu(null);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [tabContextMenu]);

  /** 跳过导航直达内容 */
  const handleSkipToContent = useCallback(
    (e: React.MouseEvent | React.KeyboardEvent) => {
      e.preventDefault();
      mainContentRef.current?.focus();
      announce('已跳转到主内容区域');
    },
    [announce],
  );

  /** 页签右键菜单 */
  const handleTabContextMenu = useCallback((e: React.MouseEvent, tabKey: string) => {
    e.preventDefault();
    setTabContextMenu({ mouseX: e.clientX - 2, mouseY: e.clientY - 4, tabKey });
  }, []);

  /** 关闭页签上下文菜单 */
  const handleTabContextClose = useCallback(() => {
    setTabContextMenu(null);
  }, []);

  /** 页签点击 */
  const handleTabClick = useCallback(
    (tab: { key: string; path: string }) => {
      setActiveTabKey(tab.key);
      navigate(tab.path);
    },
    [setActiveTabKey, navigate],
  );

  /** 关闭页签 */
  const handleTabClose = useCallback(
    (tabKey: string, tabLabel: string, e: React.MouseEvent) => {
      e.stopPropagation();
      removeTab(tabKey);
      announce(`已关闭 ${tabLabel} 标签`);
    },
    [removeTab, announce],
  );

  /** 计算内容区 margin-left */
  const contentMarginLeft = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f5f7fa' }}>
      {/* Skip-to-content 链接 */}
      <a
        href="#main-content"
        onClick={handleSkipToContent}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleSkipToContent(e);
          }
        }}
        style={{
          position: 'absolute',
          left: '-9999px',
          zIndex: 9999,
          padding: '8px 16px',
          backgroundColor: '#0052d9',
          color: '#fff',
          fontWeight: 600,
          fontSize: '0.875rem',
          borderRadius: '0 0 8px 0',
          textDecoration: 'none',
        }}
        onFocus={(e) => {
          (e.target as HTMLElement).style.left = '0';
          (e.target as HTMLElement).style.top = '0';
        }}
        onBlur={(e) => {
          (e.target as HTMLElement).style.left = '-9999px';
        }}
      >
        跳转到主内容
      </a>

      {/* 屏幕阅读器通知播报区 */}
      <div
        aria-live="polite"
        aria-atomic="true"
        role="status"
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          overflow: 'hidden',
          clip: 'rect(0 0 0 0)',
          border: 0,
        }}
      >
        {announcement}
      </div>

      {/* 侧边栏 */}
      <SidebarMenu collapsed={collapsed} onCollapsedChange={setCollapsed} />

      {/* 主内容区 */}
      <div
        style={{
          marginLeft: `${contentMarginLeft}px`,
          flex: 1,
          transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          minWidth: 0,
        }}
      >
        {/* 顶栏 */}
        <HeaderBar
          collapsed={collapsed}
          onToggleSidebar={() => setCollapsed(!collapsed)}
        />

        {/* 多页签栏 */}
        <nav
          aria-label="多页签导航"
          style={{
            backgroundColor: '#fff',
            borderBottom: '1px solid #E8E8E8',
            display: 'flex',
            alignItems: 'center',
            minHeight: '36px',
            padding: '0 4px',
            flexShrink: 0,
          }}
        >
          {/* 页签列表 */}
          <div
            role="tablist"
            aria-label="已打开的页面标签"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '2px',
              overflow: 'auto',
              flex: 1,
              padding: '4px 0',
              scrollbarWidth: 'thin',
              scrollbarColor: '#e0e0e0 transparent',
            }}
          >
            {tabs.map((tab) => {
              const isActive = tab.key === activeTabKey;
              return (
                <div
                  key={tab.key}
                  role="tab"
                  aria-selected={isActive}
                  aria-label={`${tab.label}${isActive ? '（当前）' : ''}`}
                  tabIndex={isActive ? 0 : -1}
                  onClick={() => handleTabClick(tab)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleTabClick(tab);
                    }
                  }}
                  onContextMenu={(e) => handleTabContextMenu(e, tab.key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 12px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    fontSize: '0.75rem',
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? '#0052d9' : '#8c8c8c',
                    backgroundColor: isActive ? 'rgba(0, 82, 217, 0.08)' : 'transparent',
                    transition: 'all 0.15s ease',
                    border: isActive
                      ? '1px solid rgba(0, 82, 217, 0.2)'
                      : '1px solid transparent',
                    outline: 'none',
                  }}
                >
                  {/* 活跃标记点 */}
                  {isActive && (
                    <span
                      aria-hidden="true"
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        backgroundColor: '#0052d9',
                        flexShrink: 0,
                      }}
                    />
                  )}
                  {tab.label}
                  {/* 关闭按钮 */}
                  {tab.closable !== false && (
                    <span
                      role="button"
                      aria-label={`关闭 ${tab.label} 标签`}
                      tabIndex={-1}
                      onClick={(e) => handleTabClose(tab.key, tab.label, e)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 14,
                        height: 14,
                        opacity: 0,
                        transition: 'opacity 0.15s',
                        cursor: 'pointer',
                        borderRadius: '2px',
                        marginLeft: '2px',
                        flexShrink: 0,
                      }}
                      className="tab-close-btn"
                    >
                      <CloseIcon style={{ fontSize: '12px' }} />
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* 页签操作按钮 */}
          <Tooltip content="关闭所有标签" placement="bottom">
            <Button
              variant="text"
              shape="square"
              size="small"
              icon={<CloseIcon />}
              onClick={() => {
                closeAllTabs();
                announce('已关闭所有标签');
              }}
              aria-label="关闭所有标签"
              style={{ marginLeft: '4px', opacity: 0.5, flexShrink: 0 }}
            />
          </Tooltip>
        </nav>

        {/* 页签右键菜单 */}
        {tabContextMenu && (
          <>
            {/* 遮罩层 */}
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                zIndex: 200,
              }}
              onClick={handleTabContextClose}
              onContextMenu={(e) => e.preventDefault()}
            />
            {/* 菜单 */}
            <div
              role="menu"
              aria-label="标签操作菜单"
              style={{
                position: 'fixed',
                top: tabContextMenu.mouseY,
                left: tabContextMenu.mouseX,
                zIndex: 201,
                backgroundColor: '#fff',
                borderRadius: '8px',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.12)',
                padding: '4px 0',
                minWidth: '120px',
              }}
            >
              <div
                role="menuitem"
                tabIndex={0}
                onClick={() => {
                  closeOtherTabs(tabContextMenu.tabKey);
                  handleTabContextClose();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    closeOtherTabs(tabContextMenu.tabKey);
                    handleTabContextClose();
                  }
                }}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.8125rem',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s',
                  whiteSpace: 'nowrap',
                }}
              >
                关闭其他
              </div>
              <div
                role="menuitem"
                tabIndex={0}
                onClick={() => {
                  closeAllTabs();
                  handleTabContextClose();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    closeAllTabs();
                    handleTabContextClose();
                  }
                }}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.8125rem',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s',
                  whiteSpace: 'nowrap',
                }}
              >
                关闭所有
              </div>
            </div>
          </>
        )}

        {/* 页面内容 */}
        <main
          id="main-content"
          ref={mainContentRef}
          role="main"
          aria-label="主内容区域"
          tabIndex={-1}
          style={{
            flex: 1,
            padding: '24px',
            backgroundColor: '#f5f7fa',
            overflow: 'auto',
            outline: 'none',
          }}
        >
          <Outlet />
        </main>

        {/* 底部 Footer */}
        <footer
          style={{
            padding: '8px 24px',
            textAlign: 'center',
            borderTop: '1px solid #E8E8E8',
            backgroundColor: '#fff',
            flexShrink: 0,
          }}
        >
          <span style={{ color: '#8c8c8c', fontSize: '0.7rem' }}>
            能源可信数据空间 &copy; 2026 &middot; 面向能源行业的可信数据流通基础设施
          </span>
        </footer>
      </div>

      {/* 页签关闭按钮 hover 样式（内联 CSS 无法直接支持 :hover，使用 style 标签） */}
      <style>{`
        .tab-close-btn:hover {
          opacity: 1 !important;
          color: #d32f2f;
        }
        div[role="tab"]:hover .tab-close-btn {
          opacity: 0.6 !important;
        }
        div[role="tab"]:hover {
          background-color: rgba(0, 0, 0, 0.04);
        }
        div[role="tab"][aria-selected="true"]:hover {
          background-color: rgba(0, 82, 217, 0.12);
        }
        div[role="menuitem"]:hover {
          background-color: rgba(0, 0, 0, 0.04);
        }
        div[role="tab"]:focus-visible {
          outline: 2px solid #0052d9;
          outline-offset: 1px;
        }
        div[role="menuitem"]:focus-visible {
          outline: 2px solid #0052d9;
          outline-offset: -2px;
        }
      `}</style>
    </div>
  );
};

export default MainLayoutTDesign;
