/**
 * 智能合约全生命周期管理页面
 * 包含：合约列表、合约模板、合约创建、合约执行、合约归档
 * 增强：链状态监控 + 合约部署管理 + 合约模板 + 执行监控
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Dialog, MessagePlugin, Textarea, Tabs, Select, Steps, Table, Form, Card, Row, Col, Statistic, Progress, Badge, Divider, Typography, Space } from 'tdesign-react';
import {
  RefreshIcon, BrowseIcon, CheckCircleFilledIcon, TrendingUpIcon,
  LinkIcon, SearchIcon, AddIcon, FileIcon, TimeIcon, EditIcon,
  ChartIcon, DataBaseIcon, CloudUploadIcon, PlayIcon, PauseIcon, StopIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listContracts, getContractDetail, invokeContract, getContractTransactions,
  getChainStatus, deployContract, deployAllContracts,
} from '@/api/blockchain';
import type { SmartContract } from '@/types/api';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import ReactECharts from 'echarts-for-react';

/* ========== 合约模板类型 ========== */
interface ContractTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  version: string;
  clauses: number;
  usage_count: number;
  status: string;
  created_at: string;
}

/* ========== 合约执行记录类型 ========== */
interface ContractExecution {
  id: string;
  contract_name: string;
  trigger_type: string;
  status: string;
  start_time: string;
  end_time: string;
  result: string;
  participants: string[];
}

/* ========== 合约归档记录类型 ========== */
interface ArchivedContract {
  id: string;
  name: string;
  archive_reason: string;
  archived_at: string;
  original_duration: string;
  participants: string[];
  final_status: string;
}

/* ========== 模拟数据 - 合约模板 ========== */
const MOCK_TEMPLATES: ContractTemplate[] = [
  { id: 'tpl-001', name: '数据共享协议模板', category: '数据共享', description: '适用于数据提供方与使用方之间的数据共享场景，包含数据范围、使用限制、保密条款等', version: '2.1', clauses: 12, usage_count: 45, status: 'active', created_at: '2025-01-10T08:00:00Z' },
  { id: 'tpl-002', name: '数据交易标准合约', category: '数据交易', description: '标准化数据交易合约模板，包含定价机制、交付标准、质量保证、违约责任', version: '1.5', clauses: 18, usage_count: 32, status: 'active', created_at: '2025-02-15T09:00:00Z' },
  { id: 'tpl-003', name: '隐私计算协作合约', category: '隐私计算', description: '多方安全计算协作合约，涵盖数据不出域、计算可验证、结果可追溯', version: '1.0', clauses: 15, usage_count: 18, status: 'active', created_at: '2025-03-01T10:00:00Z' },
  { id: 'tpl-004', name: '能源数据授权合约', category: '数据授权', description: '能源行业专用数据授权模板，符合能源监管要求', version: '1.2', clauses: 14, usage_count: 28, status: 'active', created_at: '2025-03-20T08:00:00Z' },
  { id: 'tpl-005', name: '收益分配合约模板', category: '收益分配', description: '数据资产收益多方分配合约，支持按贡献度、使用量等维度分配', version: '1.0', clauses: 10, usage_count: 12, status: 'active', created_at: '2025-04-05T09:00:00Z' },
  { id: 'tpl-006', name: 'SLA服务等级合约', category: '服务等级', description: '数据服务等级协议模板，定义可用性、响应时间、数据质量等指标', version: '2.0', clauses: 16, usage_count: 22, status: 'draft', created_at: '2025-04-20T10:00:00Z' },
];

/* ========== 模拟数据 - 合约执行记录 ========== */
const MOCK_EXECUTIONS: ContractExecution[] = [
  { id: 'exec-001', contract_name: '电网负荷数据共享合约', trigger_type: '自动触发', status: 'completed', start_time: '2025-05-20T08:00:00Z', end_time: '2025-05-20T08:05:00Z', result: '数据交付成功，质量检查通过', participants: ['国网数据中心', '新能源研究院'] },
  { id: 'exec-002', contract_name: '光伏发电数据交易合约', trigger_type: '手动触发', status: 'running', start_time: '2025-05-23T10:00:00Z', end_time: '', result: '正在执行数据质量验证', participants: ['光伏运营商A', '电力交易中心'] },
  { id: 'exec-003', contract_name: '碳排放数据授权合约', trigger_type: '条件触发', status: 'completed', start_time: '2025-05-22T14:00:00Z', end_time: '2025-05-22T14:30:00Z', result: '授权有效期自动续期', participants: ['双碳管理平台', '环保监测中心'] },
  { id: 'exec-004', contract_name: '储能调度数据共享协议', trigger_type: '定时触发', status: 'failed', start_time: '2025-05-23T06:00:00Z', end_time: '2025-05-23T06:02:00Z', result: '数据源连接超时，执行失败', participants: ['储能电站A', '调度中心'] },
  { id: 'exec-005', contract_name: '充电桩运营数据合约', trigger_type: '自动触发', status: 'completed', start_time: '2025-05-21T00:00:00Z', end_time: '2025-05-21T00:10:00Z', result: '日结数据自动交付完成', participants: ['充电服务平台', '电动汽车公司'] },
  { id: 'exec-006', contract_name: '电价预测数据协作合约', trigger_type: '条件触发', status: 'pending', start_time: '', end_time: '', result: '等待数据提供方确认', participants: ['交易中心', 'AI预测平台'] },
];

/* ========== 模拟数据 - 归档合约 ========== */
const MOCK_ARCHIVED: ArchivedContract[] = [
  { id: 'arch-001', name: '2024年Q1电力交易数据合约', archive_reason: '合约到期', archived_at: '2025-04-01T00:00:00Z', original_duration: '2024-01-01 ~ 2024-03-31', participants: ['交易中心', '发电集团'], final_status: 'completed' },
  { id: 'arch-002', name: '历史气象数据授权协议', archive_reason: '数据已退出', archived_at: '2025-05-10T15:30:00Z', original_duration: '2023-06-01 ~ 2025-05-10', participants: ['气象局', '数据中心'], final_status: 'terminated' },
  { id: 'arch-003', name: '风电场试运行数据共享', archive_reason: '试运行结束', archived_at: '2025-03-15T12:00:00Z', original_duration: '2024-12-01 ~ 2025-03-15', participants: ['风电运营商', '新能源部'], final_status: 'completed' },
  { id: 'arch-004', name: '临时数据接入测试合约', archive_reason: '测试完成', archived_at: '2025-02-28T18:00:00Z', original_duration: '2025-02-01 ~ 2025-02-28', participants: ['技术部', '测试中心'], final_status: 'completed' },
];

const EXECUTION_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  completed: { label: '已完成', theme: 'success' },
  running: { label: '执行中', theme: 'primary' },
  failed: { label: '执行失败', theme: 'danger' },
  pending: { label: '待执行', theme: 'warning' },
};

const TEMPLATE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  active: { label: '已启用', theme: 'success' },
  draft: { label: '草稿', theme: 'warning' },
};

/** 合约状态颜色映射 */
const contractStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
  const map: Record<string, 'success' | 'warning' | 'error'> = {
    active: 'success', DEPLOYED: 'success', inactive: 'warning', PENDING: 'warning',
    upgrading: 'info' as unknown as 'warning', FAILED: 'error',
  };
  return (map[status] as 'success' | 'warning' | 'error' | 'default') ?? 'default';
};

/** 合约状态中文映射 */
const contractStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    active: '已部署', DEPLOYED: '已部署', inactive: '未激活', PENDING: '部署中',
    upgrading: '升级中', FAILED: '部署失败',
  };
  return map[status] ?? status;
};

const BcContractsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 主 Tab =====
  const [activeTab, setActiveTab] = useState<string>('contracts');

  // ===== 分页（客户端分页） =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 弹窗状态 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<SmartContract | null>(null);

  const [invokeOpen, setInvokeOpen] = useState<boolean>(false);
  const [invokeId, setInvokeId] = useState<string>('');
  const [invokeMethod, setInvokeMethod] = useState<string>('');
  const [invokeArgs, setInvokeArgs] = useState<string>('{}');
  const [invokeResult, setInvokeResult] = useState<Record<string, unknown> | null>(null);

  const [txOpen, setTxOpen] = useState<boolean>(false);
  const [txContractId, setTxContractId] = useState<string>('');
  const [txPage, setTxPage] = useState<number>(0);
  const [txPageSize, setTxPageSize] = useState<number>(5);

  // ===== 创建合约弹窗 =====
  const [createOpen, setCreateOpen] = useState<boolean>(false);
  const [createStep, setCreateStep] = useState<number>(0);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [contractName, setContractName] = useState<string>('');
  const [contractParties, setContractParties] = useState<string>('');

  // ===== 合约列表查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: listContracts,
  });

  const items: SmartContract[] = (data?.data as unknown as SmartContract[]) ?? [];

  // ===== 链状态查询（每 10 秒轮询） =====
  const { data: chainData } = useQuery({
    queryKey: ['chainStatus'],
    queryFn: getChainStatus,
    refetchInterval: 10000,
  });

  const chainStatus = chainData?.data ?? {
    connected: false, block_number: 0, peer_count: 0, chain_id: 0, latest_block_time: 0,
  };

  // ===== 客户端分页 =====
  const total: number = items.length;
  const pagedItems: SmartContract[] = items.slice(page * pageSize, (page + 1) * pageSize);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalContracts: items.length,
    deployed: items.filter((item) => item.status === 'active' || item.status === 'DEPLOYED').length,
    blockNumber: chainStatus.block_number,
    peerCount: chainStatus.peer_count,
    chainConnected: chainStatus.connected,
    chainId: chainStatus.chain_id,
    templateCount: MOCK_TEMPLATES.length,
    executionRunning: MOCK_EXECUTIONS.filter(e => e.status === 'running').length,
    archivedCount: MOCK_ARCHIVED.length,
  }), [items, chainStatus]);

  // ===== ECharts 配置 =====
  const contractTypeOption = useMemo(() => {
    const categories: Record<string, number> = {};
    items.forEach((item) => {
      const cat = item.name.includes('NFT') ? '数据资产NFT'
        : (item.name.includes('Evidence') || item.name.includes('Usage')) ? '存证合约'
        : item.name.includes('Settlement') ? '结算合约'
        : item.name.includes('Identity') ? '身份合约'
        : item.name.includes('Access') ? '访问控制'
        : item.name.includes('Compliance') ? '合规审计'
        : '其他';
      categories[cat] = (categories[cat] || 0) + 1;
    });
    const colors = ['#2196f3', '#4caf50', '#ff9800', '#9c27b0', '#00bcd4', '#e91e63'];
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 'middle' },
      series: [{
        name: '合约类型', type: 'pie', radius: ['40%', '70%'], center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: Object.entries(categories).map(([name, value], i) => ({
          value, name, itemStyle: { color: colors[i % colors.length] },
        })),
      }],
    };
  }, [items]);

  const deployTrendOption = useMemo(() => {
    const active = items.filter((i) => i.status === 'active' || i.status === 'DEPLOYED').length;
    const inactive = items.filter((i) => i.status === 'inactive').length;
    const upgrading = items.filter((i) => i.status === 'upgrading').length;
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['已部署', '未激活', '升级中'], top: 10 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['已部署', '未激活', '升级中'] },
      yAxis: { type: 'value', name: '数量' },
      series: [{
        type: 'bar',
        data: [
          { value: active, itemStyle: { color: '#4caf50' } },
          { value: inactive, itemStyle: { color: '#ff9800' } },
          { value: upgrading, itemStyle: { color: '#2196f3' } },
        ],
        barWidth: '40%',
      }],
    };
  }, [items]);

  // ===== 执行状态分布图表 =====
  const executionChartOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{c}次' },
      data: [
        { value: MOCK_EXECUTIONS.filter(e => e.status === 'completed').length, name: '已完成', itemStyle: { color: '#4caf50' } },
        { value: MOCK_EXECUTIONS.filter(e => e.status === 'running').length, name: '执行中', itemStyle: { color: '#2196f3' } },
        { value: MOCK_EXECUTIONS.filter(e => e.status === 'failed').length, name: '失败', itemStyle: { color: '#f44336' } },
        { value: MOCK_EXECUTIONS.filter(e => e.status === 'pending').length, name: '待执行', itemStyle: { color: '#ff9800' } },
      ],
    }],
  }), []);

  // ===== 模板分类图表 =====
  const templateCategoryOption = useMemo(() => {
    const cats: Record<string, number> = {};
    MOCK_TEMPLATES.forEach(t => { cats[t.category] = (cats[t.category] || 0) + 1; });
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: Object.keys(cats), axisLabel: { rotate: 15 } },
      yAxis: { type: 'value', name: '数量' },
      series: [{
        type: 'bar',
        data: Object.values(cats).map((v, i) => ({
          value: v,
          itemStyle: { color: ['#2196f3', '#4caf50', '#ff9800', '#9c27b0', '#00bcd4', '#e91e63'][i % 6] },
        })),
        barWidth: '50%',
      }],
    };
  }, []);

  // ===== 交易记录查询 =====
  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['contractTransactions', txContractId, txPage, txPageSize],
    queryFn: () => getContractTransactions(txContractId, { page: txPage + 1, page_size: txPageSize }),
    enabled: txOpen && !!txContractId,
  });

  const txItems: Record<string, unknown>[] = txData?.data?.items ?? [];
  const txTotal: number = txData?.data?.total ?? 0;

  // ===== Mutations =====
  const detailMut = useMutation({
    mutationFn: (id: string) => getContractDetail(id),
    onSuccess: (res) => { setDetailData(res.data ?? null); setDetailOpen(true); },
  });

  const invokeMut = useMutation({
    mutationFn: ({ id, method, args }: { id: string; method: string; args: Record<string, unknown> }) =>
      invokeContract(id, method, args),
    onSuccess: (res) => { setInvokeResult(res.data ?? null); queryClient.invalidateQueries({ queryKey: ['contracts'] }); },
  });

  const deployMut = useMutation({
    mutationFn: (contractName: string) => deployContract(contractName),
    onSuccess: (res) => {
      MessagePlugin.success(`合约 ${res.data?.name ?? ''} 部署成功`);
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['chainStatus'] });
    },
    onError: (err: unknown) => { MessagePlugin.error(`部署失败: ${err instanceof Error ? err.message : '未知错误'}`); },
  });

  const deployAllMut = useMutation({
    mutationFn: deployAllContracts,
    onSuccess: (res) => {
      MessagePlugin.success(`成功部署 ${Object.keys(res.data?.results ?? {}).length} 个合约`);
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['chainStatus'] });
    },
    onError: (err: unknown) => { MessagePlugin.error(`一键部署失败: ${err instanceof Error ? err.message : '未知错误'}`); },
  });

  // ===== 操作处理 =====
  const openInvoke = useCallback((contract: SmartContract) => {
    setInvokeId(contract.id); setInvokeMethod(''); setInvokeArgs('{}'); setInvokeResult(null); setInvokeOpen(true);
  }, []);

  const openTransactions = useCallback((contractId: string) => {
    setTxContractId(contractId); setTxPage(0); setTxOpen(true);
  }, []);

  const handleInvoke = useCallback(() => {
    let args: Record<string, unknown> = {};
    try { args = JSON.parse(invokeArgs || '{}'); } catch { args = {}; }
    invokeMut.mutate({ id: invokeId, method: invokeMethod, args });
  }, [invokeId, invokeMethod, invokeArgs, invokeMut]);

  const handleCreateSubmit = useCallback(() => {
    MessagePlugin.success('合约创建请求已提交，等待参与方确认');
    setCreateOpen(false);
    setCreateStep(0);
    setSelectedTemplate('');
    setContractName('');
    setContractParties('');
  }, []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '合约管理' }],
    [],
  );

  // ===== 合约列表表格列定义 =====
  const columns: Column<SmartContract>[] = useMemo(() => [
    { id: 'name', label: '合约名称', minWidth: 160, render: (row) => <span className="text-sm font-medium">{row.name}</span> },
    {
      id: 'address', label: '合约地址', minWidth: 180,
      render: (row) => (
        <Tooltip content={row.address || 'N/A'}>
          <Tag variant="outline">{row.address ? (row.address.length > 20 ? row.address.slice(0, 10) + '...' + row.address.slice(-8) : row.address) : 'N/A'}</Tag>
        </Tooltip>
      ),
    },
    { id: 'version', label: '版本', minWidth: 80, render: (row) => `v${row.version}` },
    { id: 'status', label: '状态', minWidth: 100, render: (row) => <StatusTag status={contractStatusLabel(row.status)} color={contractStatusColor(row.status)} /> },
    { id: 'deployed_at', label: '部署时间', minWidth: 160, render: (row) => row.deployed_at ? new Date(row.deployed_at).toLocaleString('zh-CN') : '未部署' },
    {
      id: 'actions', label: '操作', minWidth: 200, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情"><span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => detailMut.mutate(row.id)}><BrowseIcon /></span></Tooltip>
          <Tooltip content="调用合约"><span className={`cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500 ${row.status !== 'active' && row.status !== 'DEPLOYED' ? 'opacity-40 pointer-events-none' : ''}`} onClick={() => openInvoke(row)}><CheckCircleFilledIcon /></span></Tooltip>
          <Tooltip content="交易记录"><span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-purple-500" onClick={() => openTransactions(row.id)}><TrendingUpIcon /></span></Tooltip>
          {row.status !== 'active' && row.status !== 'DEPLOYED' && (
            <Tooltip content="部署此合约"><span className={`cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500 ${deployMut.isPending ? 'opacity-40 pointer-events-none' : ''}`} onClick={() => deployMut.mutate(row.name)}><CheckCircleFilledIcon /></span></Tooltip>
          )}
        </div>
      ),
    },
  ], []);

  // ===== 模板列表列定义 =====
  const templateColumns: Column<ContractTemplate>[] = useMemo(() => [
    { id: 'name', label: '模板名称', minWidth: 180, render: (row) => <span className="text-sm font-medium">{row.name}</span> },
    { id: 'category', label: '分类', minWidth: 100, render: (row) => <Tag variant="outline" size="small">{row.category}</Tag> },
    { id: 'version', label: '版本', minWidth: 80, render: (row) => `v${row.version}` },
    { id: 'clauses', label: '条款数', minWidth: 80 },
    { id: 'usage_count', label: '使用次数', minWidth: 90, render: (row) => <span className="text-blue-600 font-semibold">{row.usage_count}</span> },
    { id: 'status', label: '状态', minWidth: 90, render: (row) => { const s = TEMPLATE_STATUS_MAP[row.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>; } },
    {
      id: 'actions', label: '操作', minWidth: 120, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情"><span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500"><BrowseIcon /></span></Tooltip>
          <Tooltip content="使用此模板"><span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500" onClick={() => { setSelectedTemplate(row.id); setCreateStep(1); setCreateOpen(true); }}><AddIcon /></span></Tooltip>
        </div>
      ),
    },
  ], []);

  // ===== 执行记录列定义 =====
  const executionColumns: Column<ContractExecution>[] = useMemo(() => [
    { id: 'contract_name', label: '合约名称', minWidth: 180, render: (row) => <span className="text-sm font-medium">{row.contract_name}</span> },
    { id: 'trigger_type', label: '触发方式', minWidth: 100, render: (row) => <Tag variant="outline" size="small">{row.trigger_type}</Tag> },
    { id: 'status', label: '执行状态', minWidth: 100, render: (row) => { const s = EXECUTION_STATUS_MAP[row.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'start_time', label: '开始时间', minWidth: 150, render: (row) => row.start_time ? new Date(row.start_time).toLocaleString('zh-CN') : '—' },
    { id: 'end_time', label: '结束时间', minWidth: 150, render: (row) => row.end_time ? new Date(row.end_time).toLocaleString('zh-CN') : '—' },
    { id: 'result', label: '执行结果', minWidth: 200, render: (row) => <span className="text-sm text-gray-600">{row.result}</span> },
    { id: 'participants', label: '参与方', minWidth: 160, render: (row) => <div className="flex flex-wrap gap-1">{row.participants.map((p, i) => <Tag key={i} size="small" variant="outline">{p}</Tag>)}</div> },
  ], []);

  // ===== 归档列表列定义 =====
  const archivedColumns: Column<ArchivedContract>[] = useMemo(() => [
    { id: 'name', label: '合约名称', minWidth: 200, render: (row) => <span className="text-sm font-medium">{row.name}</span> },
    { id: 'archive_reason', label: '归档原因', minWidth: 120 },
    { id: 'original_duration', label: '原始期限', minWidth: 180 },
    { id: 'archived_at', label: '归档时间', minWidth: 150, render: (row) => new Date(row.archived_at).toLocaleString('zh-CN') },
    { id: 'participants', label: '参与方', minWidth: 160, render: (row) => <div className="flex flex-wrap gap-1">{row.participants.map((p, i) => <Tag key={i} size="small" variant="outline">{p}</Tag>)}</div> },
    { id: 'final_status', label: '最终状态', minWidth: 100, render: (row) => <Tag theme={row.final_status === 'completed' ? 'success' : 'danger'} size="small">{row.final_status === 'completed' ? '已完成' : '已终止'}</Tag> },
  ], []);

  const txTotalPages = Math.ceil(txTotal / txPageSize);

  return (
    <PageContainer>
      <PageHeader
        title="合约全生命周期管理"
        subtitle="管理链上智能合约，支持模板管理、合约创建、执行监控与归档"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '创建合约', icon: <AddIcon />, onClick: () => { setCreateStep(0); setCreateOpen(true); }, variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => { queryClient.invalidateQueries({ queryKey: ['contracts'] }); queryClient.invalidateQueries({ queryKey: ['chainStatus'] }); }, tooltip: '刷新' },
          { icon: <CheckCircleFilledIcon />, onClick: () => deployAllMut.mutate(), tooltip: '一键部署全部合约', disabled: deployAllMut.isPending },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="总合约数" value={stats.totalContracts} unit="个" icon={<SearchIcon />} gradient="purple" />
        <StatCard title="已部署" value={stats.deployed} unit="个" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="合约模板" value={stats.templateCount} unit="个" icon={<FileIcon />} gradient="blue" />
        <StatCard title="执行中" value={stats.executionRunning} unit="个" icon={<TimeIcon />} gradient="orange" />
        <StatCard title="已归档" value={stats.archivedCount} unit="个" icon={<DataBaseIcon />} gradient="cyan" />
      </div>

      {/* 主 Tab 区域 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="contracts" label="智能合约">
          {/* 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="合约状态分布" option={deployTrendOption} className="lg:col-span-2" />
            <ChartCard title="合约类型分布" option={contractTypeOption} />
          </div>

          {/* 合约列表 */}
          <PageSection padding="none" className="mt-4">
            <DataTable
              columns={columns}
              rows={pagedItems}
              loading={isLoading}
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
            />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="templates" label="合约模板">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={templateColumns} rows={MOCK_TEMPLATES} page={0} pageSize={20} total={MOCK_TEMPLATES.length} />
              </PageSection>
            </div>
            <ChartCard title="模板分类分布" option={templateCategoryOption} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="execution" label="合约执行">
          {/* 执行统计 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={executionColumns} rows={MOCK_EXECUTIONS} page={0} pageSize={20} total={MOCK_EXECUTIONS.length} />
              </PageSection>
            </div>
            <ChartCard title="执行状态分布" option={executionChartOption} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="archive" label="合约归档">
          <PageSection title="历史归档合约" titleIcon={<DataBaseIcon />} className="mt-4">
            <DataTable columns={archivedColumns} rows={MOCK_ARCHIVED} page={0} pageSize={20} total={MOCK_ARCHIVED.length} />
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 合约详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="合约详情" width="640px" footer={<Button variant="outline" onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex gap-8">
              <div><span className="text-xs text-gray-500">合约名称</span><p className="text-sm font-semibold">{detailData.name}</p></div>
              <div><span className="text-xs text-gray-500">版本</span><p className="text-sm">v{detailData.version}</p></div>
              <div><span className="text-xs text-gray-500">状态</span><StatusTag status={contractStatusLabel(detailData.status)} color={contractStatusColor(detailData.status)} /></div>
            </div>
            <div><span className="text-xs text-gray-500">合约地址</span><p className="text-sm font-mono">{detailData.address}</p></div>
            {detailData.deploy_tx_hash && <div><span className="text-xs text-gray-500">部署交易哈希</span><p className="text-sm font-mono">{detailData.deploy_tx_hash}</p></div>}
            <div><span className="text-xs text-gray-500">ABI 定义</span><div className="mt-1 p-3 bg-gray-50 rounded-lg"><pre className="text-xs font-mono whitespace-pre-wrap max-h-[300px] overflow-auto">{JSON.stringify(detailData.abi, null, 2)}</pre></div></div>
            <div><span className="text-xs text-gray-500">部署时间</span><p className="text-sm">{detailData.deployed_at ? new Date(detailData.deployed_at).toLocaleString('zh-CN') : '未部署'}</p></div>
          </div>
        ) : <span className="text-gray-400">暂无数据</span>}
      </Dialog>

      {/* 调用合约弹窗 */}
      <Dialog visible={invokeOpen} onClose={() => setInvokeOpen(false)} header="调用合约" width="480px" footer={<Button variant="outline" onClick={() => setInvokeOpen(false)}>关闭</Button>}>
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">方法名</label><Input value={invokeMethod} onChange={(val) => setInvokeMethod(String(val))} placeholder="例如: transfer" /></div>
          <div><label className="block text-sm text-gray-600 mb-1">参数 (JSON)</label><Textarea value={invokeArgs} onChange={(val) => setInvokeArgs(String(val))} placeholder='{"to": "0x...", "amount": 100}' rows={4} /></div>
          <Button theme="primary" onClick={handleInvoke} disabled={!invokeMethod.trim()}>执行调用</Button>
          {invokeResult && <div className="p-3 bg-gray-50 rounded-lg"><p className="text-sm font-semibold mb-2">调用结果</p><pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(invokeResult, null, 2)}</pre></div>}
        </div>
      </Dialog>

      {/* 交易记录弹窗 */}
      <Dialog visible={txOpen} onClose={() => setTxOpen(false)} header="交易记录" width="640px" footer={<Button variant="outline" onClick={() => setTxOpen(false)}>关闭</Button>}>
        {txLoading ? <span className="text-gray-400">加载中...</span> : txItems.length === 0 ? <span className="text-gray-400">暂无交易记录</span> : (
          <div className="flex flex-col gap-2">
            {txItems.map((tx, idx) => <div key={idx} className="p-3 border border-gray-200 rounded-lg"><pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(tx, null, 2)}</pre></div>)}
            <div className="flex items-center justify-center gap-2 mt-2">
              <button className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50" disabled={txPage === 0} onClick={() => setTxPage((p) => p - 1)}>上一页</button>
              <span className="text-xs text-gray-500">第 {txPage + 1} 页</span>
              <button className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50" disabled={(txPage + 1) * txPageSize >= txTotal} onClick={() => setTxPage((p) => p + 1)}>下一页</button>
            </div>
          </div>
        )}
      </Dialog>

      {/* 创建合约弹窗（多步骤） */}
      <Dialog visible={createOpen} onClose={() => setCreateOpen(false)} header="创建合约" width="640px" footer={
        <div className="flex justify-end gap-2">
          <Button onClick={() => setCreateOpen(false)}>取消</Button>
          {createStep > 0 && <Button variant="outline" onClick={() => setCreateStep(createStep - 1)}>上一步</Button>}
          {createStep < 3 ? (
            <Button theme="primary" onClick={() => setCreateStep(createStep + 1)} disabled={createStep === 0 && !selectedTemplate}>下一步</Button>
          ) : (
            <Button theme="primary" onClick={handleCreateSubmit}>确认创建</Button>
          )}
        </div>
      }>
        <div className="mb-4">
          <Steps current={createStep} style={{ marginBottom: 24 }}>
            <Steps.StepItem title="选择模板" />
            <Steps.StepItem title="配置条款" />
            <Steps.StepItem title="参与方确认" />
            <Steps.StepItem title="签署" />
          </Steps>
        </div>

        {createStep === 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-gray-600 mb-2">选择一个合约模板开始创建：</p>
            {MOCK_TEMPLATES.filter(t => t.status === 'active').map(t => (
              <div
                key={t.id}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedTemplate === t.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                onClick={() => setSelectedTemplate(t.id)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{t.name}</span>
                  <Tag size="small" variant="outline">{t.category}</Tag>
                </div>
                <p className="text-xs text-gray-500 mt-1">{t.description}</p>
              </div>
            ))}
          </div>
        )}

        {createStep === 1 && (
          <div className="flex flex-col gap-4">
            <div><label className="block text-sm text-gray-600 mb-1">合约名称</label><Input value={contractName} onChange={(val) => setContractName(String(val))} placeholder="请输入合约名称" /></div>
            <div><label className="block text-sm text-gray-600 mb-1">参与方（多个用逗号分隔）</label><Input value={contractParties} onChange={(val) => setContractParties(String(val))} placeholder="如：数据中心, 新能源研究院" /></div>
            <div><label className="block text-sm text-gray-600 mb-1">合约条款描述</label><Textarea placeholder="请输入合约条款描述..." rows={4} /></div>
          </div>
        )}

        {createStep === 2 && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-gray-600">请确认以下合约信息，等待参与方确认：</p>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm"><strong>模板：</strong>{MOCK_TEMPLATES.find(t => t.id === selectedTemplate)?.name || '未选择'}</p>
              <p className="text-sm mt-2"><strong>合约名称：</strong>{contractName || '未填写'}</p>
              <p className="text-sm mt-2"><strong>参与方：</strong>{contractParties || '未填写'}</p>
            </div>
            <div className="flex items-center gap-2 text-orange-600">
              <TimeIcon />
              <span className="text-sm">等待所有参与方确认...</span>
            </div>
          </div>
        )}

        {createStep === 3 && (
          <div className="flex flex-col items-center gap-4 py-4">
            <CheckCircleFilledIcon style={{ fontSize: 48, color: '#4caf50' }} />
            <p className="text-lg font-semibold text-gray-800">合约签署完成</p>
            <p className="text-sm text-gray-500">合约将自动部署到区块链网络</p>
          </div>
        )}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default BcContractsPage;