import { lazy } from 'react';
import type { RouteObject } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import MainLayout from '@/layouts/MainLayoutTDesign';
import AuthLayout from '@/layouts/AuthLayout';
import FullScreenLayout from '@/layouts/FullScreenLayout';
import ProtectedRoute from './ProtectedRoute';
import LazyLoad from './LazyLoad';

/* ========== 门户首页（公开） ========== */
const LandingPage = lazy(() => import('@/pages/portal/LandingPage'));

/* ========== 认证页面 ========== */
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const SSOCallbackPage = lazy(() => import('@/pages/auth/SSOCallbackPage'));
const MfaSetupPage = lazy(() => import('@/pages/auth/MfaSetupPage'));

/* ========== 仪表盘 ========== */
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));

/* ========== 数据中心 ========== */
const DataSourcesPage = lazy(() => import('@/pages/data/DataSourcesPage'));
const DataAssetsPage = lazy(() => import('@/pages/data/DataAssetsPage'));
const DataCatalogPage = lazy(() => import('@/pages/data/DataCatalogPage'));
const DataMarketPage = lazy(() => import('@/pages/data/DataMarketPage'));
const DataApplicationPage = lazy(() => import('@/pages/data/DataApplicationPage'));
const ServiceRequestPage = lazy(() => import('@/pages/data/ServiceRequestPage'));
const MetadataPage = lazy(() => import('@/pages/data/MetadataPage'));
const DataLineagePage = lazy(() => import('@/pages/data/DataLineagePage'));
const DataQualityPage = lazy(() => import('@/pages/data/DataQualityPage'));
const DataLifecyclePage = lazy(() => import('@/pages/data/DataLifecyclePage'));
const DataMatchingPage = lazy(() => import('@/pages/data/DataMatchingPage'));
const ConnectorManageDataPage = lazy(() => import('@/pages/data/ConnectorManagePage'));
const DataSubscriptionPage = lazy(() => import('@/pages/data/DataSubscriptionPage'));
const ProductManageDataPage = lazy(() => import('@/pages/data/ProductManagePage'));
const DemandHallPage = lazy(() => import('@/pages/data/DemandHallPage'));

/* ========== 计算中心 ========== */
const ComputeTasksPage = lazy(() => import('@/pages/compute/ComputeTasksPage'));
const ComputeCreatePage = lazy(() => import('@/pages/compute/ComputeCreatePage'));
const ComputeDagPage = lazy(() => import('@/pages/compute/ComputeDagPage'));
const ComputeSandboxPage = lazy(() => import('@/pages/compute/ComputeSandboxPage'));
const ComputeAgentsPage = lazy(() => import('@/pages/compute/ComputeAgentsPage'));
const ComputeBenchmarkPage = lazy(() => import('@/pages/compute/ComputeBenchmarkPage'));
const ComputeClusterPage = lazy(() => import('@/pages/compute/ComputeClusterPage'));
const PrivacyComputePage = lazy(() => import('@/pages/compute/PrivacyComputePage'));
const DataSandboxPage = lazy(() => import('@/pages/compute/DataSandboxPage'));

/* ========== 区块链中心 ========== */
const BcAssetsPage = lazy(() => import('@/pages/blockchain/BcAssetsPage'));
const BcEvidencePage = lazy(() => import('@/pages/blockchain/BcEvidencePage'));
const BcContractsPage = lazy(() => import('@/pages/blockchain/BcContractsPage'));
const BcSettlementPage = lazy(() => import('@/pages/blockchain/BcSettlementPage'));
const BcQueryPage = lazy(() => import('@/pages/blockchain/BcQueryPage'));

/* ========== 运营中心 ========== */
const OpsUsersPage = lazy(() => import('@/pages/ops/OpsUsersPage'));
const OpsServicesPage = lazy(() => import('@/pages/ops/OpsServicesPage'));
const OpsBillingPage = lazy(() => import('@/pages/ops/OpsBillingPage'));
const OpsMonitorPage = lazy(() => import('@/pages/ops/OpsMonitorPage'));
const OpsCompliancePage = lazy(() => import('@/pages/ops/OpsCompliancePage'));
const OpsKpiPage = lazy(() => import('@/pages/ops/OpsKpiPage'));
const OpsOrgPage = lazy(() => import('@/pages/ops/OpsOrgPage'));
const OpsRevenuePage = lazy(() => import('@/pages/ops/OpsRevenuePage'));
const ApprovalCenterPage = lazy(() => import('@/pages/ops/ApprovalCenterPage'));

/* ========== AI Agent 管理 ========== */
const AgentManagePage = lazy(() => import('@/pages/ops/AgentManagePage'));

/* ========== 系统管理 ========== */
const NotificationCenterPage = lazy(() => import('@/pages/ops/NotificationCenterPage'));
const SystemConfigPage = lazy(() => import('@/pages/ops/SystemConfigPage'));
const AuditLogPage = lazy(() => import('@/pages/ops/AuditLogPage'));

/* ========== 安全中心 ========== */
const SecurityPoliciesPage = lazy(() => import('@/pages/security/SecurityPoliciesPage'));
const SecurityDidPage = lazy(() => import('@/pages/security/SecurityDidPage'));
const SecurityVcPage = lazy(() => import('@/pages/security/SecurityVcPage'));
const SecurityKeysPage = lazy(() => import('@/pages/security/SecurityKeysPage'));
const SecurityThreatsPage = lazy(() => import('@/pages/security/SecurityThreatsPage'));
const SecurityCryptoPage = lazy(() => import('@/pages/security/SecurityCryptoPage'));
const SecurityZkpPage = lazy(() => import('@/pages/security/SecurityZkpPage'));
const SecurityLevelsPage = lazy(() => import('@/pages/security/SecurityLevelsPage'));

/* ========== 业务场景 ========== */
const PowerDispatchPage = lazy(() => import('@/pages/portal/PowerDispatchPage'));
const RenewableEnergyPage = lazy(() => import('@/pages/portal/RenewableEnergyPage'));
const VirtualPowerPlantPage = lazy(() => import('@/pages/portal/VirtualPowerPlantPage'));
const PowerTradingPage = lazy(() => import('@/pages/portal/PowerTradingPage'));

/* ========== AI Agent ========== */
const AgentChatNewPage = lazy(() => import('@/pages/agent/AgentChatPage'));

/* ========== 联邦学习 ========== */
const FederatedLearningPage = lazy(() => import('@/pages/compute/FederatedLearningPage'));

/* ========== 跨链互操作 ========== */
const CrossChainPage = lazy(() => import('@/pages/blockchain/CrossChainPage'));

/* ========== 门户功能 ========== */
const AnnouncementsPage = lazy(() => import('@/pages/portal/AnnouncementsPage'));
const PortalProfilePage = lazy(() => import('@/pages/portal/PortalProfilePage'));
const AgentChatPage = lazy(() => import('@/pages/portal/AgentChatPage'));
const OrgCertificationPage = lazy(() => import('@/pages/portal/OrgCertificationPage'));

/* ========== 可信数据空间 - 机构管理 ========== */
const OrganizationsPage = lazy(() => import('@/pages/tds/OrganizationsPage'));
const OrganizationDetailPage = lazy(() => import('@/pages/tds/OrganizationDetailPage'));

/* ========== 可信数据空间 - 连接器管理 ========== */
const ConnectorManagePage = lazy(() => import('@/pages/tds/ConnectorManagePage'));
const ConnectorDetailPage = lazy(() => import('@/pages/tds/ConnectorDetailPage'));

/* ========== 可信数据空间 - 数据目录管理 ========== */
const CatalogManagePage = lazy(() => import('@/pages/tds/CatalogManagePage'));
const CatalogDetailPage = lazy(() => import('@/pages/tds/CatalogDetailPage'));

/* ========== 可信数据空间 - 数据订阅 ========== */
const DataSubscriptionsPage = lazy(() => import('@/pages/tds/DataSubscriptionsPage'));
const SubscriptionDetailPage = lazy(() => import('@/pages/tds/SubscriptionDetailPage'));

/* ========== 可信数据空间 - 数据产品管理 ========== */
const ProductManagePage = lazy(() => import('@/pages/tds/ProductManagePage'));
const ProductDetailPage = lazy(() => import('@/pages/tds/ProductDetailPage'));

/* ========== 可信数据空间 - 产品上架 ========== */
const ProductPublishPage = lazy(() => import('@/pages/tds/ProductPublishPage'));

/* ========== 可信数据空间 - 产品市场 ========== */
const ProductMarketPage = lazy(() => import('@/pages/tds/ProductMarketPage'));
const ProductMarketDetailPage = lazy(() => import('@/pages/tds/ProductMarketDetailPage'));

/* ========== 可信数据空间 - 需求管理 ========== */
const DemandManagePage = lazy(() => import('@/pages/tds/DemandManagePage'));
const DemandDetailPage = lazy(() => import('@/pages/tds/DemandDetailPage'));

/* ========== 可信数据空间 - 合约管理 ========== */
const ContractManagePage = lazy(() => import('@/pages/tds/ContractManagePage'));
const ContractDetailPage = lazy(() => import('@/pages/tds/ContractDetailPage'));

/* ========== 可信数据空间 - 连接器文件库 ========== */
const ConnectorFilesPage = lazy(() => import('@/pages/tds/ConnectorFilesPage'));

/* ========== 可信数据空间 - 审批工作流 ========== */
const WorkflowManagePage = lazy(() => import('@/pages/tds/WorkflowManagePage'));
const WorkflowDetailPage = lazy(() => import('@/pages/tds/WorkflowDetailPage'));
const ApprovalRecordsPage = lazy(() => import('@/pages/tds/ApprovalRecordsPage'));

/* ========== 监管大屏 ========== */
const MonitorScreenPage = lazy(() => import('@/pages/monitor-screen/MonitorScreenPage'));

/**
 * 完整路由配置
 * 所有业务页面均懒加载，认证页面使用 AuthLayout，业务页面使用 MainLayout
 */
export const routes: RouteObject[] = [
  /* ========== 公开页面（无需登录） ========== */
  {
    path: '/',
    element: (
      <LazyLoad>
        <LandingPage />
      </LazyLoad>
    ),
  },
  {
    path: '/login',
    element: (
      <AuthLayout>
        <LazyLoad>
          <LoginPage />
        </LazyLoad>
      </AuthLayout>
    ),
  },
  /* ========== 受保护页面（需登录） ========== */
  {
    path: '/dashboard',
    element: <ProtectedRoute />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { index: true, element: <LazyLoad><DashboardPage /></LazyLoad> },
          /* ---- 数据中心 ---- */
          { path: 'data/sources', element: <LazyLoad><DataSourcesPage /></LazyLoad> },
          { path: 'data/assets', element: <LazyLoad><DataAssetsPage /></LazyLoad> },
          { path: 'data/catalog', element: <LazyLoad><DataCatalogPage /></LazyLoad> },
          { path: 'data/market', element: <LazyLoad><DataMarketPage /></LazyLoad> },
          { path: 'data/application', element: <LazyLoad><DataApplicationPage /></LazyLoad> },
          { path: 'data/requests', element: <LazyLoad><ServiceRequestPage /></LazyLoad> },
          { path: 'data/metadata', element: <LazyLoad><MetadataPage /></LazyLoad> },
          { path: 'data/lineage', element: <LazyLoad><DataLineagePage /></LazyLoad> },
          { path: 'data/quality', element: <LazyLoad><DataQualityPage /></LazyLoad> },
          { path: 'data/lifecycle', element: <LazyLoad><DataLifecyclePage /></LazyLoad> },
          { path: 'data/matching', element: <LazyLoad><DataMatchingPage /></LazyLoad> },
          { path: 'data/connectors', element: <LazyLoad><ConnectorManageDataPage /></LazyLoad> },
          { path: 'data/subscription', element: <LazyLoad><DataSubscriptionPage /></LazyLoad> },
          { path: 'data/products', element: <LazyLoad><ProductManageDataPage /></LazyLoad> },
          { path: 'data/demands', element: <LazyLoad><DemandHallPage /></LazyLoad> },
          /* ---- 计算中心 ---- */
          { path: 'compute/tasks', element: <LazyLoad><ComputeTasksPage /></LazyLoad> },
          { path: 'compute/create', element: <LazyLoad><ComputeCreatePage /></LazyLoad> },
          { path: 'compute/dag', element: <LazyLoad><ComputeDagPage /></LazyLoad> },
          { path: 'compute/sandbox', element: <LazyLoad><ComputeSandboxPage /></LazyLoad> },
          { path: 'compute/agents', element: <LazyLoad><ComputeAgentsPage /></LazyLoad> },
          { path: 'compute/benchmark', element: <LazyLoad><ComputeBenchmarkPage /></LazyLoad> },
          { path: 'compute/cluster', element: <LazyLoad><ComputeClusterPage /></LazyLoad> },
          { path: 'compute/privacy', element: <LazyLoad><PrivacyComputePage /></LazyLoad> },
          { path: 'compute/data-sandbox', element: <LazyLoad><DataSandboxPage /></LazyLoad> },
          /* ---- 区块链中心 ---- */
          { path: 'blockchain/assets', element: <LazyLoad><BcAssetsPage /></LazyLoad> },
          { path: 'blockchain/evidence', element: <LazyLoad><BcEvidencePage /></LazyLoad> },
          { path: 'blockchain/contracts', element: <LazyLoad><BcContractsPage /></LazyLoad> },
          { path: 'blockchain/settlement', element: <LazyLoad><BcSettlementPage /></LazyLoad> },
          { path: 'blockchain/query', element: <LazyLoad><BcQueryPage /></LazyLoad> },
          /* ---- 运营中心 ---- */
          { path: 'ops/users', element: <LazyLoad><OpsUsersPage /></LazyLoad> },
          { path: 'ops/services', element: <LazyLoad><OpsServicesPage /></LazyLoad> },
          { path: 'ops/billing', element: <LazyLoad><OpsBillingPage /></LazyLoad> },
          { path: 'ops/monitor', element: <LazyLoad><OpsMonitorPage /></LazyLoad> },
          { path: 'ops/compliance', element: <LazyLoad><OpsCompliancePage /></LazyLoad> },
          { path: 'ops/kpi', element: <LazyLoad><OpsKpiPage /></LazyLoad> },
          { path: 'ops/organizations', element: <LazyLoad><OpsOrgPage /></LazyLoad> },
          { path: 'ops/agent-manage', element: <LazyLoad><AgentManagePage /></LazyLoad> },
          { path: 'ops/notifications', element: <LazyLoad><NotificationCenterPage /></LazyLoad> },
          { path: 'ops/system-config', element: <LazyLoad><SystemConfigPage /></LazyLoad> },
          { path: 'ops/audit-logs', element: <LazyLoad><AuditLogPage /></LazyLoad> },
          { path: 'ops/revenue', element: <LazyLoad><OpsRevenuePage /></LazyLoad> },
          { path: 'ops/approval-center', element: <LazyLoad><ApprovalCenterPage /></LazyLoad> },
          /* ---- 安全中心 ---- */
          { path: 'security/policies', element: <LazyLoad><SecurityPoliciesPage /></LazyLoad> },
          { path: 'security/did', element: <LazyLoad><SecurityDidPage /></LazyLoad> },
          { path: 'security/vc', element: <LazyLoad><SecurityVcPage /></LazyLoad> },
          { path: 'security/keys', element: <LazyLoad><SecurityKeysPage /></LazyLoad> },
          { path: 'security/threats', element: <LazyLoad><SecurityThreatsPage /></LazyLoad> },
          { path: 'security/crypto', element: <LazyLoad><SecurityCryptoPage /></LazyLoad> },
          { path: 'security/zkp', element: <LazyLoad><SecurityZkpPage /></LazyLoad> },
          { path: 'security/levels', element: <LazyLoad><SecurityLevelsPage /></LazyLoad> },
          /* ---- 业务场景 ---- */
          { path: 'scenario/power-dispatch', element: <LazyLoad><PowerDispatchPage /></LazyLoad> },
          { path: 'scenario/renewable-energy', element: <LazyLoad><RenewableEnergyPage /></LazyLoad> },
          { path: 'scenario/virtual-power-plant', element: <LazyLoad><VirtualPowerPlantPage /></LazyLoad> },
          { path: 'scenario/power-trading', element: <LazyLoad><PowerTradingPage /></LazyLoad> },
          /* ---- 门户功能 ---- */
          { path: 'portal/announcements', element: <LazyLoad><AnnouncementsPage /></LazyLoad> },
          { path: 'portal/profile', element: <LazyLoad><PortalProfilePage /></LazyLoad> },
          { path: 'portal/agent-chat', element: <LazyLoad><AgentChatPage /></LazyLoad> },
          { path: 'portal/org-certification', element: <LazyLoad><OrgCertificationPage /></LazyLoad> },
          /* ---- 业务场景 ---- */
          { path: 'scene/power-dispatch', element: <LazyLoad><PowerDispatchPage /></LazyLoad> },
          { path: 'scene/renewable-energy', element: <LazyLoad><RenewableEnergyPage /></LazyLoad> },
          { path: 'scene/virtual-power-plant', element: <LazyLoad><VirtualPowerPlantPage /></LazyLoad> },
          { path: 'scene/power-trading', element: <LazyLoad><PowerTradingPage /></LazyLoad> },
          /* ---- 可信数据空间 - 机构管理 ---- */
          { path: 'tds/organizations', element: <LazyLoad><OrganizationsPage /></LazyLoad> },
          { path: 'tds/organizations/:id', element: <LazyLoad><OrganizationDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 连接器管理 ---- */
          { path: 'tds/connectors', element: <LazyLoad><ConnectorManagePage /></LazyLoad> },
          { path: 'tds/connectors/:id', element: <LazyLoad><ConnectorDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 数据目录管理 ---- */
          { path: 'tds/catalog', element: <LazyLoad><CatalogManagePage /></LazyLoad> },
          { path: 'tds/catalog/:id', element: <LazyLoad><CatalogDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 数据订阅 ---- */
          { path: 'tds/subscriptions', element: <LazyLoad><DataSubscriptionsPage /></LazyLoad> },
          { path: 'tds/subscriptions/:id', element: <LazyLoad><SubscriptionDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 数据产品管理 ---- */
          { path: 'tds/products', element: <LazyLoad><ProductManagePage /></LazyLoad> },
          { path: 'tds/products/:id', element: <LazyLoad><ProductDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 产品上架 ---- */
          { path: 'tds/product-publish', element: <LazyLoad><ProductPublishPage /></LazyLoad> },
          /* ---- 可信数据空间 - 产品市场 ---- */
          { path: 'tds/market', element: <LazyLoad><ProductMarketPage /></LazyLoad> },
          { path: 'tds/market/:id', element: <LazyLoad><ProductMarketDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 需求管理 ---- */
          { path: 'tds/demands', element: <LazyLoad><DemandManagePage /></LazyLoad> },
          { path: 'tds/demands/:id', element: <LazyLoad><DemandDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 合约管理 ---- */
          { path: 'tds/contracts', element: <LazyLoad><ContractManagePage /></LazyLoad> },
          { path: 'tds/contracts/:id', element: <LazyLoad><ContractDetailPage /></LazyLoad> },
          /* ---- 可信数据空间 - 连接器文件库 ---- */
          { path: 'tds/files', element: <LazyLoad><ConnectorFilesPage /></LazyLoad> },
          /* ---- 可信数据空间 - 审批工作流 ---- */
          { path: 'tds/workflows', element: <LazyLoad><WorkflowManagePage /></LazyLoad> },
          { path: 'tds/workflows/:id', element: <LazyLoad><WorkflowDetailPage /></LazyLoad> },
          { path: 'tds/approvals', element: <LazyLoad><ApprovalRecordsPage /></LazyLoad> },
        ],
      },
    ],
  },
  {
    path: '/monitor-screen',
    element: (
      <FullScreenLayout>
        <LazyLoad>
          <MonitorScreenPage />
        </LazyLoad>
      </FullScreenLayout>
    ),
  },
  /* ========== SSO 回调（公开） ========== */
  {
    path: '/sso-callback',
    element: (
      <LazyLoad>
        <SSOCallbackPage />
      </LazyLoad>
    ),
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },

  /* ========== MFA 设置（需认证） ========== */
  {
    path: '/auth/mfa-setup',
    element: (
      <ProtectedRoute>
        <LazyLoad>
          <MfaSetupPage />
        </LazyLoad>
      </ProtectedRoute>
    ),
  },

  /* ========== AI Agent 智能助手 ========== */
  {
    path: '/agent/chat',
    element: <LazyLoad><AgentChatNewPage /></LazyLoad>,
  },
  /* ========== 联邦学习 ========== */
  {
    path: '/compute/federated-learning',
    element: <LazyLoad><FederatedLearningPage /></LazyLoad>,
  },
  /* ========== 跨链互操作 ========== */
  {
    path: '/blockchain/cross-chain',
    element: <LazyLoad><CrossChainPage /></LazyLoad>,
  },
];
