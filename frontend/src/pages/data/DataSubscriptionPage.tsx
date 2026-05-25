/**
 * 数据资源订阅页面（增强版）
 * 数据搜索、数据详情（脱敏预览）、订阅申请、审批流程、合约签署、交付管理
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Button, Dialog, Input, Select, Tag, Tabs, Steps, Form, Textarea,
  Table, Tooltip, MessagePlugin, Descriptions, Timeline, Rate,
} from 'tdesign-react';
import {
  SearchIcon, RefreshIcon, BrowseIcon, StarIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TimeIcon,
  FileIcon, LinkIcon, ChartIcon, TrendingUpIcon,
  EditIcon, ShieldErrorIcon, UserIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid } from '@/components/common';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/* ========== 模拟数据资源 ========== */
interface DataResource {
  id: string;
  name: string;
  category: string;
  security_level: 'public' | 'internal' | 'confidential' | 'secret';
  provider: string;
  description: string;
  fields: string[];
  update_freq: string;
  record_count: number;
  rating: number;
  rating_count: number;
  price: number;
  status: 'available' | 'applying' | 'subscribed';
  created_at: string;
  sample_data: Record<string, unknown>[];
}

const MOCK_RESOURCES: DataResource[] = [
  {
    id: 'res-001', name: '光伏发电实时出力数据', category: '新能源', security_level: 'internal',
    provider: '华能新能源', description: '包含光伏逆变器实时功率、辐照度、温度等数据，分钟级更新',
    fields: ['电站ID', '逆变器编号', '有功功率(kW)', '辐照度(W/m²)', '组件温度(℃)', '时间戳'],
    update_freq: '分钟级', record_count: 12500000, rating: 4.6, rating_count: 89, price: 500,
    status: 'available', created_at: '2025-03-15',
    sample_data: [
      { '电站ID': 'PV-001', '逆变器编号': 'INV-001', '有功功率(kW)': '***', '辐照度(W/m²)': 856, '组件温度(℃)': 42.3, '时间戳': '2025-05-23 10:30:00' },
      { '电站ID': 'PV-001', '逆变器编号': 'INV-002', '有功功率(kW)': '***', '辐照度(W/m²)': 845, '组件温度(℃)': 41.8, '时间戳': '2025-05-23 10:30:00' },
    ],
  },
  {
    id: 'res-002', name: '电力用户负荷曲线', category: '电力数据', security_level: 'confidential',
    provider: '国网营销部', description: '大工业用户96点负荷曲线数据，含行业分类、用电特征',
    fields: ['用户编号', '行业类型', '电压等级', '有功功率(MW)', '无功功率(MVar)', '时间点'],
    update_freq: '日级', record_count: 8500000, rating: 4.8, rating_count: 156, price: 1200,
    status: 'available', created_at: '2025-02-20',
    sample_data: [
      { '用户编号': '***', '行业类型': '钢铁', '电压等级': '110kV', '有功功率(MW)': '***', '无功功率(MVar)': '***', '时间点': '00:00' },
      { '用户编号': '***', '行业类型': '化工', '电压等级': '35kV', '有功功率(MW)': '***', '无功功率(MVar)': '***', '时间点': '00:00' },
    ],
  },
  {
    id: 'res-003', name: '碳排放监测数据', category: '环保数据', security_level: 'public',
    provider: '生态环境局', description: '重点排放企业碳排放监测数据，含排放因子、排放量',
    fields: ['企业编号', '行业', '排放源类型', 'CO2排放量(吨)', '排放因子', '监测时间'],
    update_freq: '月级', record_count: 320000, rating: 4.2, rating_count: 45, price: 800,
    status: 'available', created_at: '2025-04-10',
    sample_data: [
      { '企业编号': 'ENT-001', '行业': '电力', '排放源类型': '燃煤锅炉', 'CO2排放量(吨)': 12500, '排放因子': 2.66, '监测时间': '2025-04' },
    ],
  },
  {
    id: 'res-004', name: '储能电站运行数据', category: '储能数据', security_level: 'internal',
    provider: '宁德时代', description: '储能电站BMS、PCS运行数据，含SOC、SOH、充放电状态',
    fields: ['电站ID', '电池簇编号', 'SOC(%)', 'SOH(%)', '充放电状态', '功率(kW)', '温度(℃)'],
    update_freq: '秒级', record_count: 45000000, rating: 4.5, rating_count: 67, price: 600,
    status: 'available', created_at: '2025-05-01',
    sample_data: [
      { '电站ID': 'ESS-001', '电池簇编号': 'BC-01', 'SOC(%)': '***', 'SOH(%)': 98.5, '充放电状态': '充电', '功率(kW)': '***', '温度(℃)': 28.3 },
    ],
  },
  {
    id: 'res-005', name: '配电网络拓扑数据', category: '电网数据', security_level: 'secret',
    provider: '国网运检部', description: '配电网拓扑结构、设备参数、运行状态数据',
    fields: ['线路编号', '设备类型', '额定容量(kVA)', '运行状态', '投运日期', '地理位置'],
    update_freq: '周级', record_count: 1800000, rating: 4.0, rating_count: 23, price: 2000,
    status: 'available', created_at: '2025-01-15',
    sample_data: [
      { '线路编号': '***', '设备类型': '变压器', '额定容量(kVA)': '***', '运行状态': '正常', '投运日期': '2020-06-15', '地理位置': '***' },
    ],
  },
  {
    id: 'res-006', name: '气象预报数据', category: '气象数据', security_level: 'public',
    provider: '气象局', description: '未来7天逐小时气象预报，含温度、风速、辐照度等',
    fields: ['站点编号', '经度', '纬度', '温度(℃)', '风速(m/s)', '辐照度(W/m²)', '预报时间'],
    update_freq: '小时级', record_count: 5600000, rating: 4.3, rating_count: 112, price: 300,
    status: 'available', created_at: '2025-03-20',
    sample_data: [
      { '站点编号': 'WX-001', '经度': 116.4, '纬度': 39.9, '温度(℃)': 28.5, '风速(m/s)': 3.2, '辐照度(W/m²)': 856, '预报时间': '2025-05-24 10:00' },
    ],
  },
];

/* ========== 模拟订阅记录 ========== */
interface Subscription {
  id: string;
  resource_id: string;
  resource_name: string;
  applicant: string;
  purpose: string;
  duration: string;
  status: 'pending' | 'first_approved' | 'approved' | 'rejected' | 'signed' | 'delivering' | 'completed';
  apply_time: string;
  first_approver: string;
  second_approver: string;
  contract_template: string;
  token: string;
  api_endpoint: string;
  usage_count: number;
}

const MOCK_SUBSCRIPTIONS: Subscription[] = [
  { id: 'sub-001', resource_id: 'res-001', resource_name: '光伏发电实时出力数据', applicant: '华电研究院', purpose: '光伏出力预测模型训练', duration: '12个月', status: 'completed', apply_time: '2025-04-01', first_approver: '张主任', second_approver: '李总监', contract_template: '标准数据使用协议', token: 'tk-8f3a2b1c', api_endpoint: '/api/v1/data/pv-realtime', usage_count: 15420 },
  { id: 'sub-002', resource_id: 'res-002', resource_name: '电力用户负荷曲线', applicant: '清华能源互联网研究院', purpose: '负荷特性分析研究', duration: '6个月', status: 'signed', apply_time: '2025-04-15', first_approver: '张主任', second_approver: '李总监', contract_template: '学术研究数据协议', token: '', api_endpoint: '', usage_count: 0 },
  { id: 'sub-003', resource_id: 'res-003', resource_name: '碳排放监测数据', applicant: '碳交易中心', purpose: '碳配额核算', duration: '24个月', status: 'delivering', apply_time: '2025-05-01', first_approver: '王经理', second_approver: '李总监', contract_template: '标准数据使用协议', token: 'tk-9e4b3c2d', api_endpoint: '/api/v1/data/carbon', usage_count: 3200 },
  { id: 'sub-004', resource_id: 'res-004', resource_name: '储能电站运行数据', applicant: '比亚迪储能', purpose: '储能系统优化', duration: '12个月', status: 'pending', apply_time: '2025-05-20', first_approver: '', second_approver: '', contract_template: '', token: '', api_endpoint: '', usage_count: 0 },
  { id: 'sub-005', resource_id: 'res-006', resource_name: '气象预报数据', applicant: '金风科技', purpose: '风电功率预测', duration: '12个月', status: 'first_approved', apply_time: '2025-05-18', first_approver: '张主任', second_approver: '', contract_template: '', token: '', api_endpoint: '', usage_count: 0 },
  { id: 'sub-006', resource_id: 'res-005', resource_name: '配电网络拓扑数据', applicant: '某民营配电网公司', purpose: '配电网规划', duration: '6个月', status: 'rejected', apply_time: '2025-05-10', first_approver: '张主任', second_approver: '', contract_template: '', token: '', api_endpoint: '', usage_count: 0 },
];

const SECURITY_MAP: Record<string, { label: string; theme: 'success' | 'primary' | 'warning' | 'danger' | 'default'; color: string }> = {
  public: { label: '公开', theme: 'success', color: '#52c41a' },
  internal: { label: '内部', theme: 'primary', color: '#1890ff' },
  confidential: { label: '机密', theme: 'warning', color: '#faad14' },
  secret: { label: '绝密', theme: 'danger', color: '#f5222d' },
};

const SUB_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' | 'primary'; step: number }> = {
  pending: { label: '待审批', theme: 'warning', step: 0 },
  first_approved: { label: '一级审批通过', theme: 'primary', step: 1 },
  approved: { label: '审批通过', theme: 'success', step: 2 },
  rejected: { label: '已拒绝', theme: 'danger', step: -1 },
  signed: { label: '已签约', theme: 'success', step: 3 },
  delivering: { label: '交付中', theme: 'primary', step: 4 },
  completed: { label: '已完成', theme: 'success', step: 5 },
};

const CATEGORIES = [
  { value: '', label: '全部分类' },
  { value: '新能源', label: '新能源' },
  { value: '电力数据', label: '电力数据' },
  { value: '环保数据', label: '环保数据' },
  { value: '储能数据', label: '储能数据' },
  { value: '电网数据', label: '电网数据' },
  { value: '气象数据', label: '气象数据' },
];

const DataSubscriptionPage: React.FC = () => {
  // ===== Tab状态 =====
  const [activeTab, setActiveTab] = useState<string>('search');

  // ===== 搜索筛选 =====
  const [keyword, setKeyword] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [securityFilter, setSecurityFilter] = useState('');

  // ===== 订阅申请 =====
  const [applyOpen, setApplyOpen] = useState(false);
  const [applyStep, setApplyStep] = useState(0);
  const [applyResource, setApplyResource] = useState<DataResource | null>(null);
  const [applyForm, setApplyForm] = useState({ purpose: '', duration: '12', contact: '', phone: '' });

  // ===== 详情 =====
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailResource, setDetailResource] = useState<DataResource | null>(null);

  // ===== 审批详情 =====
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [approvalItem, setApprovalItem] = useState<Subscription | null>(null);

  // ===== 合约签署 =====
  const [contractOpen, setContractOpen] = useState(false);
  const [contractItem, setContractItem] = useState<Subscription | null>(null);
  const [contractTemplate, setContractTemplate] = useState('standard');
  const [contractTerms, setContractTerms] = useState('');

  // ===== 过滤数据 =====
  const filteredResources = useMemo(() => {
    return MOCK_RESOURCES.filter(r => {
      if (keyword && !r.name.includes(keyword) && !r.description.includes(keyword)) return false;
      if (categoryFilter && r.category !== categoryFilter) return false;
      if (securityFilter && r.security_level !== securityFilter) return false;
      return true;
    });
  }, [keyword, categoryFilter, securityFilter]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalResources: MOCK_RESOURCES.length,
    totalSubscriptions: MOCK_SUBSCRIPTIONS.length,
    activeSubscriptions: MOCK_SUBSCRIPTIONS.filter(s => ['signed', 'delivering', 'completed'].includes(s.status)).length,
    pendingApproval: MOCK_SUBSCRIPTIONS.filter(s => ['pending', 'first_approved'].includes(s.status)).length,
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据资源订阅' }],
    [],
  );

  // ===== ECharts配置 =====
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];

  const categoryChartOption = useMemo(() => {
    const catMap: Record<string, number> = {};
    MOCK_RESOURCES.forEach(r => { catMap[r.category] = (catMap[r.category] ?? 0) + 1; });
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 20 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: Object.entries(catMap).map(([name, value], i) => ({ value, name, itemStyle: { color: COLORS[i % COLORS.length] } })),
      }],
    };
  }, []);

  const subscriptionTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['申请数', '通过数', '拒绝数'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '申请数', type: 'bar', data: [12, 18, 15, 22, 28], itemStyle: { color: '#667eea' } },
      { name: '通过数', type: 'bar', data: [10, 15, 12, 18, 20], itemStyle: { color: '#52c41a' } },
      { name: '拒绝数', type: 'bar', data: [2, 3, 3, 4, 8], itemStyle: { color: '#f5222d' } },
    ],
  }), []);

  const securityChartOption = useMemo(() => {
    const secMap: Record<string, number> = {};
    MOCK_RESOURCES.forEach(r => { secMap[SECURITY_MAP[r.security_level].label] = (secMap[SECURITY_MAP[r.security_level].label] ?? 0) + 1; });
    return {
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: '65%',
        data: Object.entries(secMap).map(([name, value]) => ({ value, name, itemStyle: { color: SECURITY_MAP[Object.keys(SECURITY_MAP).find(k => SECURITY_MAP[k].label === name) || 'public'].color } })),
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
      }],
    };
  }, []);

  const ratingChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: MOCK_RESOURCES.map(r => r.name.substring(0, 6)), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '评分', min: 3, max: 5 },
    series: [{
      type: 'bar',
      data: MOCK_RESOURCES.map((r, i) => ({ value: r.rating, itemStyle: { color: COLORS[i % COLORS.length] } })),
      barWidth: '40%',
    }],
  }), []);

  // ===== 操作处理 =====
  const handleViewDetail = useCallback((resource: DataResource) => {
    setDetailResource(resource);
    setDetailOpen(true);
  }, []);

  const handleApply = useCallback((resource: DataResource) => {
    setApplyResource(resource);
    setApplyForm({ purpose: '', duration: '12', contact: '', phone: '' });
    setApplyStep(0);
    setApplyOpen(true);
  }, []);

  const handleApplyNext = useCallback(() => {
    if (applyStep < 2) setApplyStep(applyStep + 1);
  }, [applyStep]);

  const handleApplySubmit = useCallback(() => {
    MessagePlugin.success('订阅申请已提交，请等待审批');
    setApplyOpen(false);
  }, [applyStep]);

  const handleViewApproval = useCallback((item: Subscription) => {
    setApprovalItem(item);
    setApprovalOpen(true);
  }, []);

  const handleSignContract = useCallback((item: Subscription) => {
    setContractItem(item);
    setContractTemplate('standard');
    setContractTerms('');
    setContractOpen(true);
  }, []);

  const handleSignSubmit = useCallback(() => {
    MessagePlugin.success('合约签署成功');
    setContractOpen(false);
  }, []);

  // ===== 资源列表列定义 =====
  const resourceColumns = [
    {
      title: '资源名称', colKey: 'name', width: 220,
      cell: ({ row }: { row: DataResource }) => (
        <span className="text-blue-600 cursor-pointer hover:underline font-medium" onClick={() => handleViewDetail(row)}>
          {row.name}
        </span>
      ),
    },
    { title: '分类', colKey: 'category', width: 100, cell: ({ row }: { row: DataResource }) => <Tag variant="outline">{row.category}</Tag> },
    {
      title: '安全等级', colKey: 'security_level', width: 100,
      cell: ({ row }: { row: DataResource }) => (
        <Tag theme={SECURITY_MAP[row.security_level].theme} variant="light">
          {SECURITY_MAP[row.security_level].label}
        </Tag>
      ),
    },
    { title: '提供方', colKey: 'provider', width: 140 },
    {
      title: '评分', colKey: 'rating', width: 140,
      cell: ({ row }: { row: DataResource }) => (
        <div className="flex items-center gap-1">
          <span className="text-yellow-500 font-semibold">{row.rating}</span>
          <span className="text-xs text-gray-400">({row.rating_count}人)</span>
        </div>
      ),
    },
    { title: '记录数', colKey: 'record_count', width: 120, cell: ({ row }: { row: DataResource }) => <span className="font-mono">{(row.record_count / 10000).toFixed(0)}万</span> },
    { title: '更新频率', colKey: 'update_freq', width: 100 },
    { title: '价格(元/月)', colKey: 'price', width: 110, cell: ({ row }: { row: DataResource }) => <span className="text-orange-600 font-semibold">¥{row.price}</span> },
    {
      title: '操作', colKey: 'action', width: 180, fixed: 'right' as const,
      cell: ({ row }: { row: DataResource }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)}>详情</Button>
          <Button size="small" variant="contained" onClick={() => handleApply(row)}>申请订阅</Button>
        </div>
      ),
    },
  ];

  // ===== 订阅记录列定义 =====
  const subscriptionColumns = [
    { title: '订阅ID', colKey: 'id', width: 120, cell: ({ row }: { row: Subscription }) => <span className="font-mono text-xs">{row.id}</span> },
    { title: '数据资源', colKey: 'resource_name', width: 200 },
    { title: '申请方', colKey: 'applicant', width: 160 },
    { title: '用途', colKey: 'purpose', width: 150 },
    { title: '时长', colKey: 'duration', width: 80 },
    {
      title: '状态', colKey: 'status', width: 120,
      cell: ({ row }: { row: Subscription }) => (
        <Tag theme={SUB_STATUS_MAP[row.status].theme} variant="light">
          {SUB_STATUS_MAP[row.status].label}
        </Tag>
      ),
    },
    { title: '申请时间', colKey: 'apply_time', width: 120 },
    {
      title: '操作', colKey: 'action', width: 200, fixed: 'right' as const,
      cell: ({ row }: { row: Subscription }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" onClick={() => handleViewApproval(row)}>查看</Button>
          {row.status === 'approved' && <Button size="small" variant="contained" onClick={() => handleSignContract(row)}>签约</Button>}
          {row.status === 'signed' && <Button size="small" variant="contained" theme="success">交付</Button>}
        </div>
      ),
    },
  ];

  // ===== 渲染星级评分 =====
  const renderStars = (rating: number) => {
    const full = Math.floor(rating);
    const hasHalf = rating - full >= 0.5;
    return (
      <span className="flex items-center gap-0.5">
        {Array.from({ length: 5 }, (_, i) => (
          <StarIcon key={i} className={`text-sm ${i < full ? 'text-yellow-400' : i === full && hasHalf ? 'text-yellow-300' : 'text-gray-300'}`} />
        ))}
      </span>
    );
  };

  // ===== 渲染申请步骤内容 =====
  const renderApplyStepContent = () => {
    switch (applyStep) {
      case 0:
        return (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <div className="font-semibold text-blue-800">{applyResource?.name}</div>
              <div className="text-sm text-blue-600 mt-1">{applyResource?.description}</div>
            </div>
            <Form labelWidth={100}>
              <Form.FormItem label="订阅用途" required>
                <Textarea value={applyForm.purpose} onChange={(v) => setApplyForm({ ...applyForm, purpose: v })} placeholder="请详细说明数据使用目的" />
              </Form.FormItem>
              <Form.FormItem label="订阅时长" required>
                <Select value={applyForm.duration} onChange={(v) => setApplyForm({ ...applyForm, duration: v })} options={[{ value: '3', label: '3个月' }, { value: '6', label: '6个月' }, { value: '12', label: '12个月' }, { value: '24', label: '24个月' }]} />
              </Form.FormItem>
              <Form.FormItem label="联系人" required>
                <Input value={applyForm.contact} onChange={(v) => setApplyForm({ ...applyForm, contact: v })} placeholder="请输入联系人姓名" />
              </Form.FormItem>
              <Form.FormItem label="联系电话" required>
                <Input value={applyForm.phone} onChange={(v) => setApplyForm({ ...applyForm, phone: v })} placeholder="请输入联系电话" />
              </Form.FormItem>
            </Form>
          </div>
        );
      case 1:
        return (
          <div className="space-y-4">
            <div className="text-center py-4">
              <ShieldErrorIcon className="text-5xl text-blue-500 mb-2" />
              <div className="text-lg font-semibold">安全评估中...</div>
            </div>
            <Timeline>
              <Timeline.Item dotColor="green">申请信息完整性校验 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">申请人资质审核 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">数据安全等级匹配检查 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">使用目的合规性评估 - 通过</Timeline.Item>
            </Timeline>
          </div>
        );
      case 2:
        return (
          <div className="space-y-4">
            <Descriptions title="申请信息确认" bordered column={2}>
              <Descriptions.Item label="数据资源">{applyResource?.name}</Descriptions.Item>
              <Descriptions.Item label="安全等级"><Tag theme={SECURITY_MAP[applyResource?.security_level || 'public'].theme}>{SECURITY_MAP[applyResource?.security_level || 'public'].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="订阅用途">{applyForm.purpose || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="订阅时长">{applyForm.duration}个月</Descriptions.Item>
              <Descriptions.Item label="联系人">{applyForm.contact || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="联系电话">{applyForm.phone || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="月费用" span={2}><span className="text-orange-600 font-semibold text-lg">¥{applyResource?.price}/月</span></Descriptions.Item>
            </Descriptions>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title="数据资源订阅"
        subtitle="搜索、预览、申请订阅数据资源，全流程管理订阅生命周期"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="数据资源总数" value={stats.totalResources} icon={<DataBaseIcon />} gradient="blue" />
        <StatCard title="订阅总数" value={stats.totalSubscriptions} icon={<FileIcon />} gradient="purple" />
        <StatCard title="活跃订阅" value={stats.activeSubscriptions} icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="待审批" value={stats.pendingApproval} icon={<TimeIcon />} gradient="orange" />
      </StatGrid>

      {/* 主内容 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="search" label="数据搜索">
          {/* 搜索筛选 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索数据资源名称或描述"
                style={{ width: 300 }}
                clearable
              />
              <Select
                value={categoryFilter}
                onChange={setCategoryFilter}
                options={CATEGORIES}
                style={{ width: 150 }}
                clearable
              />
              <Select
                value={securityFilter}
                onChange={setSecurityFilter}
                options={[
                  { value: '', label: '全部等级' },
                  { value: 'public', label: '公开' },
                  { value: 'internal', label: '内部' },
                  { value: 'confidential', label: '机密' },
                  { value: 'secret', label: '绝密' },
                ]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setCategoryFilter(''); setSecurityFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 资源表格 */}
          <PageSection className="mt-4">
            <Table data={filteredResources} columns={resourceColumns} rowKey="id" bordered hover />
          </PageSection>

          {/* 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="数据资源分类分布" option={categoryChartOption} height={300} />
            <ChartCard title="资源评分对比" option={ratingChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="subscriptions" label="我的订阅">
          <PageSection className="mt-4">
            <Table data={MOCK_SUBSCRIPTIONS} columns={subscriptionColumns} rowKey="id" bordered hover />
          </PageSection>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="订阅申请趋势" option={subscriptionTrendOption} height={300} />
            <ChartCard title="安全等级分布" option={securityChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="approval" label="审批流程">
          <PageSection title="待审批列表" titleIcon={<TimeIcon />} className="mt-4">
            <div className="space-y-3">
              {MOCK_SUBSCRIPTIONS.filter(s => ['pending', 'first_approved'].includes(s.status)).map(item => (
                <div key={item.id} className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 bg-white hover:shadow-sm transition-shadow">
                  <div className="flex-1">
                    <div className="font-semibold">{item.resource_name}</div>
                    <div className="text-sm text-gray-500 mt-1">申请方：{item.applicant} | 用途：{item.purpose} | 时长：{item.duration}</div>
                  </div>
                  <Tag theme={SUB_STATUS_MAP[item.status].theme} variant="light">{SUB_STATUS_MAP[item.status].label}</Tag>
                  <div className="flex gap-2">
                    <Button size="small" variant="contained" theme="success" onClick={() => MessagePlugin.success('审批通过')}>通过</Button>
                    <Button size="small" variant="contained" theme="danger" onClick={() => MessagePlugin.warning('已拒绝')}>拒绝</Button>
                  </div>
                </div>
              ))}
              {MOCK_SUBSCRIPTIONS.filter(s => ['pending', 'first_approved'].includes(s.status)).length === 0 && (
                <div className="text-center py-8 text-gray-400">暂无待审批事项</div>
              )}
            </div>
          </PageSection>

          <PageSection title="审批流程说明" titleIcon={<ChartIcon />} className="mt-4">
            <Steps current={2} style={{ padding: '20px 0' }}>
              <Steps.StepItem title="提交申请" content="用户填写订阅申请" />
              <Steps.StepItem title="一级审批" content="部门负责人审批" />
              <Steps.StepItem title="二级审批" content="数据安全官审批" />
              <Steps.StepItem title="合约签署" content="双方签署数据使用协议" />
              <Steps.StepItem title="数据交付" content="生成Token和API接口" />
            </Steps>
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 数据详情弹窗 */}
      <Dialog header="数据资源详情" visible={detailOpen} onClose={() => setDetailOpen(false)} width={800}>
        {detailResource && (
          <div className="space-y-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="资源名称">{detailResource.name}</Descriptions.Item>
              <Descriptions.Item label="分类"><Tag variant="outline">{detailResource.category}</Tag></Descriptions.Item>
              <Descriptions.Item label="安全等级"><Tag theme={SECURITY_MAP[detailResource.security_level].theme}>{SECURITY_MAP[detailResource.security_level].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="提供方">{detailResource.provider}</Descriptions.Item>
              <Descriptions.Item label="评分"><div className="flex items-center gap-2">{renderStars(detailResource.rating)}<span>{detailResource.rating}</span></div></Descriptions.Item>
              <Descriptions.Item label="记录数">{(detailResource.record_count / 10000).toFixed(0)}万条</Descriptions.Item>
              <Descriptions.Item label="更新频率">{detailResource.update_freq}</Descriptions.Item>
              <Descriptions.Item label="价格"><span className="text-orange-600 font-semibold">¥{detailResource.price}/月</span></Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{detailResource.description}</Descriptions.Item>
              <Descriptions.Item label="数据字段" span={2}>
                <div className="flex flex-wrap gap-1">
                  {detailResource.fields.map(f => <Tag key={f} size="small" variant="outline">{f}</Tag>)}
                </div>
              </Descriptions.Item>
            </Descriptions>

            <PageSection title="数据预览（脱敏）" titleIcon={<BrowseIcon />}>
              <Table
                data={detailResource.sample_data}
                columns={detailResource.fields.map(f => ({ title: f, colKey: f, width: 120 }))}
                rowKey={(_, i) => String(i)}
                bordered
                size="small"
              />
            </PageSection>

            <div className="flex justify-end">
              <Button variant="contained" onClick={() => { setDetailOpen(false); handleApply(detailResource); }}>申请订阅</Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* 订阅申请弹窗 */}
      <Dialog header="订阅申请" visible={applyOpen} onClose={() => setApplyOpen(false)} width={700}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setApplyOpen(false)}>取消</Button>
            {applyStep > 0 && <Button onClick={() => setApplyStep(applyStep - 1)}>上一步</Button>}
            {applyStep < 2 ? (
              <Button variant="contained" onClick={handleApplyNext}>下一步</Button>
            ) : (
              <Button variant="contained" theme="success" onClick={handleApplySubmit}>提交申请</Button>
            )}
          </div>
        }
      >
        <Steps current={applyStep} style={{ marginBottom: 24 }}>
          <Steps.StepItem title="填写用途" />
          <Steps.StepItem title="安全评估" />
          <Steps.StepItem title="确认提交" />
        </Steps>
        {renderApplyStepContent()}
      </Dialog>

      {/* 审批详情弹窗 */}
      <Dialog header="审批详情" visible={approvalOpen} onClose={() => setApprovalOpen(false)} width={700}>
        {approvalItem && (
          <div className="space-y-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="订阅ID">{approvalItem.id}</Descriptions.Item>
              <Descriptions.Item label="数据资源">{approvalItem.resource_name}</Descriptions.Item>
              <Descriptions.Item label="申请方">{approvalItem.applicant}</Descriptions.Item>
              <Descriptions.Item label="用途">{approvalItem.purpose}</Descriptions.Item>
              <Descriptions.Item label="时长">{approvalItem.duration}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag theme={SUB_STATUS_MAP[approvalItem.status].theme}>{SUB_STATUS_MAP[approvalItem.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="申请时间">{approvalItem.apply_time}</Descriptions.Item>
              <Descriptions.Item label="一级审批人">{approvalItem.first_approver || '待分配'}</Descriptions.Item>
              <Descriptions.Item label="二级审批人">{approvalItem.second_approver || '待分配'}</Descriptions.Item>
              {approvalItem.token && <Descriptions.Item label="Token"><span className="font-mono text-sm">{approvalItem.token}</span></Descriptions.Item>}
              {approvalItem.api_endpoint && <Descriptions.Item label="API接口"><span className="font-mono text-sm">{approvalItem.api_endpoint}</span></Descriptions.Item>}
            </Descriptions>

            <PageSection title="审批流程" titleIcon={<ChartIcon />}>
              <Timeline>
                <Timeline.Item dotColor="green">提交申请 - {approvalItem.apply_time}</Timeline.Item>
                <Timeline.Item dotColor={approvalItem.first_approver ? 'green' : 'gray'}>
                  一级审批 - {approvalItem.first_approver ? `已通过 (${approvalItem.first_approver})` : '待审批'}
                </Timeline.Item>
                <Timeline.Item dotColor={approvalItem.second_approver ? 'green' : 'gray'}>
                  二级审批 - {approvalItem.second_approver ? `已通过 (${approvalItem.second_approver})` : '待审批'}
                </Timeline.Item>
                <Timeline.Item dotColor={['signed', 'delivering', 'completed'].includes(approvalItem.status) ? 'green' : 'gray'}>
                  合约签署 - {['signed', 'delivering', 'completed'].includes(approvalItem.status) ? '已签署' : '待签署'}
                </Timeline.Item>
                <Timeline.Item dotColor={['delivering', 'completed'].includes(approvalItem.status) ? 'green' : 'gray'}>
                  数据交付 - {['delivering', 'completed'].includes(approvalItem.status) ? '交付中' : '待交付'}
                </Timeline.Item>
              </Timeline>
            </PageSection>
          </div>
        )}
      </Dialog>

      {/* 合约签署弹窗 */}
      <Dialog header="合约签署" visible={contractOpen} onClose={() => setContractOpen(false)} width={600}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setContractOpen(false)}>取消</Button>
            <Button variant="contained" theme="success" onClick={handleSignSubmit}>确认签署</Button>
          </div>
        }
      >
        {contractItem && (
          <div className="space-y-4">
            <Form labelWidth={100}>
              <Form.FormItem label="数据资源">
                <span className="font-medium">{contractItem.resource_name}</span>
              </Form.FormItem>
              <Form.FormItem label="合约模板">
                <Select value={contractTemplate} onChange={setContractTemplate} options={[{ value: 'standard', label: '标准数据使用协议' }, { value: 'academic', label: '学术研究数据协议' }, { value: 'commercial', label: '商业数据授权协议' }]} />
              </Form.FormItem>
              <Form.FormItem label="特殊条款">
                <Textarea value={contractTerms} onChange={setContractTerms} placeholder="如有特殊条款请在此填写" />
              </Form.FormItem>
            </Form>
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <div className="font-semibold mb-2">合约摘要</div>
              <div className="text-sm text-gray-600 space-y-1">
                <div>• 数据使用范围：仅限{contractItem.purpose}</div>
                <div>• 订阅期限：{contractItem.duration}</div>
                <div>• 数据不得转让给第三方</div>
                <div>• 使用结束后需销毁本地副本</div>
                <div>• 违约将承担相应法律责任</div>
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default DataSubscriptionPage;
