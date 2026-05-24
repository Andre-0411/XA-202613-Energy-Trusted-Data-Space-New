/**
 * 可信数据空间核心业务状态管理（Zustand）
 * 管理机构、连接器、目录、订阅、产品、需求、合约、工作流的 UI 状态
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  Organization, Connector, CatalogRegistration,
  DataSubscription, DataProduct, Demand, Contract,
  ApprovalWorkflow, ApprovalRecord,
} from '@/types/api';

// ==================== 机构管理状态 ====================

interface OrgFilters {
  keyword: string;
  status: string;
  level: number | null;
}

// ==================== 连接器管理状态 ====================

interface ConnectorFilters {
  keyword: string;
  status: string;
  connector_type: string;
}

// ==================== 数据目录状态 ====================

interface CatalogFilters {
  keyword: string;
  category: string;
  sensitivity_level: string;
  status: string;
}

// ==================== 订阅管理状态 ====================

interface SubscriptionFilters {
  keyword: string;
  status: string;
  catalog_id: string;
}

// ==================== 产品管理状态 ====================

interface ProductFilters {
  keyword: string;
  product_type: string;
  status: string;
  project_id: string;
}

// ==================== 需求管理状态 ====================

interface DemandFilters {
  keyword: string;
  demand_type: string;
  status: string;
}

// ==================== 合约管理状态 ====================

interface ContractFilters {
  keyword: string;
  contract_type: string;
  status: string;
}

// ==================== 工作流状态 ====================

interface WorkflowFilters {
  keyword: string;
  workflow_type: string;
  status: string;
}

// ==================== 主状态接口 ====================

interface TdsState {
  // 选中项
  selectedOrganization: Organization | null;
  selectedConnector: Connector | null;
  selectedCatalog: CatalogRegistration | null;
  selectedSubscription: DataSubscription | null;
  selectedProduct: DataProduct | null;
  selectedDemand: Demand | null;
  selectedContract: Contract | null;
  selectedWorkflow: ApprovalWorkflow | null;
  selectedApprovalRecord: ApprovalRecord | null;

  // 筛选条件
  orgFilters: OrgFilters;
  connectorFilters: ConnectorFilters;
  catalogFilters: CatalogFilters;
  subscriptionFilters: SubscriptionFilters;
  productFilters: ProductFilters;
  demandFilters: DemandFilters;
  contractFilters: ContractFilters;
  workflowFilters: WorkflowFilters;

  // 视图模式
  catalogViewMode: 'card' | 'list';
  productViewMode: 'card' | 'list';
  demandViewMode: 'card' | 'list';

  // 设置选中项
  setSelectedOrganization: (org: Organization | null) => void;
  setSelectedConnector: (connector: Connector | null) => void;
  setSelectedCatalog: (catalog: CatalogRegistration | null) => void;
  setSelectedSubscription: (sub: DataSubscription | null) => void;
  setSelectedProduct: (product: DataProduct | null) => void;
  setSelectedDemand: (demand: Demand | null) => void;
  setSelectedContract: (contract: Contract | null) => void;
  setSelectedWorkflow: (workflow: ApprovalWorkflow | null) => void;
  setSelectedApprovalRecord: (record: ApprovalRecord | null) => void;

  // 设置筛选条件
  setOrgFilters: (filters: Partial<OrgFilters>) => void;
  setConnectorFilters: (filters: Partial<ConnectorFilters>) => void;
  setCatalogFilters: (filters: Partial<CatalogFilters>) => void;
  setSubscriptionFilters: (filters: Partial<SubscriptionFilters>) => void;
  setProductFilters: (filters: Partial<ProductFilters>) => void;
  setDemandFilters: (filters: Partial<DemandFilters>) => void;
  setContractFilters: (filters: Partial<ContractFilters>) => void;
  setWorkflowFilters: (filters: Partial<WorkflowFilters>) => void;

  // 设置视图模式
  setCatalogViewMode: (mode: 'card' | 'list') => void;
  setProductViewMode: (mode: 'card' | 'list') => void;
  setDemandViewMode: (mode: 'card' | 'list') => void;

  // 重置筛选条件
  resetOrgFilters: () => void;
  resetConnectorFilters: () => void;
  resetCatalogFilters: () => void;
  resetSubscriptionFilters: () => void;
  resetProductFilters: () => void;
  resetDemandFilters: () => void;
  resetContractFilters: () => void;
  resetWorkflowFilters: () => void;

  // 重置所有状态
  resetAll: () => void;
}

// ==================== 默认值 ====================

const defaultOrgFilters: OrgFilters = { keyword: '', status: '', level: null };
const defaultConnectorFilters: ConnectorFilters = { keyword: '', status: '', connector_type: '' };
const defaultCatalogFilters: CatalogFilters = { keyword: '', category: '', sensitivity_level: '', status: '' };
const defaultSubscriptionFilters: SubscriptionFilters = { keyword: '', status: '', catalog_id: '' };
const defaultProductFilters: ProductFilters = { keyword: '', product_type: '', status: '', project_id: '' };
const defaultDemandFilters: DemandFilters = { keyword: '', demand_type: '', status: '' };
const defaultContractFilters: ContractFilters = { keyword: '', contract_type: '', status: '' };
const defaultWorkflowFilters: WorkflowFilters = { keyword: '', workflow_type: '', status: '' };

// ==================== Store 实现 ====================

export const useTdsStore = create<TdsState>()(
  persist(
    (set) => ({
      // 初始选中项
      selectedOrganization: null,
      selectedConnector: null,
      selectedCatalog: null,
      selectedSubscription: null,
      selectedProduct: null,
      selectedDemand: null,
      selectedContract: null,
      selectedWorkflow: null,
      selectedApprovalRecord: null,

      // 初始筛选条件
      orgFilters: { ...defaultOrgFilters },
      connectorFilters: { ...defaultConnectorFilters },
      catalogFilters: { ...defaultCatalogFilters },
      subscriptionFilters: { ...defaultSubscriptionFilters },
      productFilters: { ...defaultProductFilters },
      demandFilters: { ...defaultDemandFilters },
      contractFilters: { ...defaultContractFilters },
      workflowFilters: { ...defaultWorkflowFilters },

      // 初始视图模式
      catalogViewMode: 'card',
      productViewMode: 'card',
      demandViewMode: 'card',

      // 设置选中项
      setSelectedOrganization: (org) => set({ selectedOrganization: org }),
      setSelectedConnector: (connector) => set({ selectedConnector: connector }),
      setSelectedCatalog: (catalog) => set({ selectedCatalog: catalog }),
      setSelectedSubscription: (sub) => set({ selectedSubscription: sub }),
      setSelectedProduct: (product) => set({ selectedProduct: product }),
      setSelectedDemand: (demand) => set({ selectedDemand: demand }),
      setSelectedContract: (contract) => set({ selectedContract: contract }),
      setSelectedWorkflow: (workflow) => set({ selectedWorkflow: workflow }),
      setSelectedApprovalRecord: (record) => set({ selectedApprovalRecord: record }),

      // 设置筛选条件
      setOrgFilters: (filters) => set((state) => ({
        orgFilters: { ...state.orgFilters, ...filters },
      })),
      setConnectorFilters: (filters) => set((state) => ({
        connectorFilters: { ...state.connectorFilters, ...filters },
      })),
      setCatalogFilters: (filters) => set((state) => ({
        catalogFilters: { ...state.catalogFilters, ...filters },
      })),
      setSubscriptionFilters: (filters) => set((state) => ({
        subscriptionFilters: { ...state.subscriptionFilters, ...filters },
      })),
      setProductFilters: (filters) => set((state) => ({
        productFilters: { ...state.productFilters, ...filters },
      })),
      setDemandFilters: (filters) => set((state) => ({
        demandFilters: { ...state.demandFilters, ...filters },
      })),
      setContractFilters: (filters) => set((state) => ({
        contractFilters: { ...state.contractFilters, ...filters },
      })),
      setWorkflowFilters: (filters) => set((state) => ({
        workflowFilters: { ...state.workflowFilters, ...filters },
      })),

      // 设置视图模式
      setCatalogViewMode: (mode) => set({ catalogViewMode: mode }),
      setProductViewMode: (mode) => set({ productViewMode: mode }),
      setDemandViewMode: (mode) => set({ demandViewMode: mode }),

      // 重置筛选条件
      resetOrgFilters: () => set({ orgFilters: { ...defaultOrgFilters } }),
      resetConnectorFilters: () => set({ connectorFilters: { ...defaultConnectorFilters } }),
      resetCatalogFilters: () => set({ catalogFilters: { ...defaultCatalogFilters } }),
      resetSubscriptionFilters: () => set({ subscriptionFilters: { ...defaultSubscriptionFilters } }),
      resetProductFilters: () => set({ productFilters: { ...defaultProductFilters } }),
      resetDemandFilters: () => set({ demandFilters: { ...defaultDemandFilters } }),
      resetContractFilters: () => set({ contractFilters: { ...defaultContractFilters } }),
      resetWorkflowFilters: () => set({ workflowFilters: { ...defaultWorkflowFilters } }),

      // 重置所有状态
      resetAll: () => set({
        selectedOrganization: null,
        selectedConnector: null,
        selectedCatalog: null,
        selectedSubscription: null,
        selectedProduct: null,
        selectedDemand: null,
        selectedContract: null,
        selectedWorkflow: null,
        selectedApprovalRecord: null,
        orgFilters: { ...defaultOrgFilters },
        connectorFilters: { ...defaultConnectorFilters },
        catalogFilters: { ...defaultCatalogFilters },
        subscriptionFilters: { ...defaultSubscriptionFilters },
        productFilters: { ...defaultProductFilters },
        demandFilters: { ...defaultDemandFilters },
        contractFilters: { ...defaultContractFilters },
        workflowFilters: { ...defaultWorkflowFilters },
        catalogViewMode: 'card',
        productViewMode: 'card',
        demandViewMode: 'card',
      }),
    }),
    {
      name: 'eds-tds-storage',
      partialize: (state) => ({
        catalogViewMode: state.catalogViewMode,
        productViewMode: state.productViewMode,
        demandViewMode: state.demandViewMode,
      }),
    }
  )
);
