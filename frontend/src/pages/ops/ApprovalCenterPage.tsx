/**
 * 审批中心页面（增强版）
 * 待我审批、我已审批、审批详情、审批统计
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Button, Dialog, Input, Select, Tag, Tabs, Textarea, Form,
  Table, Tooltip, MessagePlugin, Descriptions, Timeline,
} from 'tdesign-react';
import {
  RefreshIcon, BrowseIcon, SearchIcon, CheckCircleFilledIcon,
  ErrorCircleFilledIcon, TimeIcon, ChartIcon, TrendingUpIcon,
  FileIcon, UserIcon, EditIcon, FilterIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid } from '@/components/common';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/* ========== 模拟审批数据 ========== */
interface ApprovalItem {
  id: string;
  title: string;
  type: 'subscription' | 'product_publish' | 'connector_register' | 'data_access' | 'org_certification';
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  applicant: string;
  apply_time: string;
  approver: string;
  approve_time: string;
  comment: string;
  priority: 'low' | 'medium' | 'high';
  content: string;
  details: Record<string, string>;
}

const MOCK_APPROVALS: ApprovalItem[] = [
  {
    id: 'apr-001', title: '光伏出力预测API上架审核', type: 'product_publish', status: 'pending',
    applicant: '华能新能源', apply_time: '2025-05-23 09:00', approver: '', approve_time: '', comment: '',
    priority: 'high', content: '申请将光伏出力预测API上架至数据产品市场',
    details: { '产品名称': '光伏出力预测API', '产品类型': 'API服务', '价格': '¥2000/月', '审核周期': '3个工作日' },
  },
  {
    id: 'apr-002', title: '电力用户负荷曲线订阅申请', type: 'subscription', status: 'pending',
    applicant: '清华能源互联网研究院', apply_time: '2025-05-22 14:30', approver: '', approve_time: '', comment: '',
    priority: 'medium', content: '申请订阅电力用户负荷曲线数据，用于学术研究',
    details: { '数据资源': '电力用户负荷曲线', '订阅时长': '6个月', '用途': '负荷特性分析研究', '安全等级': '机密' },
  },
  {
    id: 'apr-003', title: '储能系统连接器注册申请', type: 'connector_register', status: 'pending',
    applicant: '宁德时代', apply_time: '2025-05-22 10:15', approver: '', approve_time: '', comment: '',
    priority: 'medium', content: '申请注册储能系统数据连接器，接入BMS和PCS数据',
    details: { '连接器名称': '储能系统连接器', '类型': '标准连接器', '数据源': 'BMS、PCS', '协议': 'MQTT' },
  },
  {
    id: 'apr-004', title: '碳排放数据访问申请', type: 'data_access', status: 'pending',
    applicant: '碳交易中心', apply_time: '2025-05-21 16:00', approver: '', approve_time: '', comment: '',
    priority: 'low', content: '申请访问碳排放监测数据，用于碳配额核算',
    details: { '数据类型': '碳排放监测数据', '访问级别': '只读', '有效期': '12个月', '用途': '碳配额核算' },
  },
  {
    id: 'apr-005', title: '华电研究院机构认证申请', type: 'org_certification', status: 'pending',
    applicant: '华电研究院', apply_time: '2025-05-20 11:00', approver: '', approve_time: '', comment: '',
    priority: 'high', content: '申请机构认证，获取数据空间完整访问权限',
    details: { '机构名称': '华电研究院', '机构类型': '科研院所', '统一社会信用代码': '91110000****', '联系人': '张主任' },
  },
  {
    id: 'apr-006', title: '气象预报数据订阅申请', type: 'subscription', status: 'approved',
    applicant: '金风科技', apply_time: '2025-05-18 09:30', approver: '张主任', approve_time: '2025-05-19 10:00', comment: '申请合理，同意订阅',
    priority: 'medium', content: '申请订阅气象预报数据，用于风电功率预测',
    details: { '数据资源': '气象预报数据', '订阅时长': '12个月', '用途': '风电功率预测', '安全等级': '公开' },
  },
  {
    id: 'apr-007', title: '配电网拓扑数据订阅申请', type: 'subscription', status: 'rejected',
    applicant: '某民营配电网公司', apply_time: '2025-05-10 14:00', approver: '张主任', approve_time: '2025-05-12 09:00', comment: '申请方资质不符合要求，数据安全等级过高',
    priority: 'high', content: '申请订阅配电网拓扑数据，用于配电网规划',
    details: { '数据资源': '配电网络拓扑数据', '订阅时长': '6个月', '用途': '配电网规划', '安全等级': '绝密' },
  },
  {
    id: 'apr-008', title: '电力市场分析报告上架审核', type: 'product_publish', status: 'approved',
    applicant: '电力交易中心', apply_time: '2025-05-15 10:00', approver: '李总监', approve_time: '2025-05-18 14:00', comment: '产品内容完整，审核通过',
    priority: 'medium', content: '申请将电力市场分析报告上架至数据产品市场',
    details: { '产品名称': '电力市场分析报告', '产品类型': '分析报告', '价格': '¥500/月', '审核周期': '5个工作日' },
  },
  {
    id: 'apr-009', title: '储能调度优化API上架审核', type: 'product_publish', status: 'pending',
    applicant: '宁德时代', apply_time: '2025-05-23 11:00', approver: '', approve_time: '', comment: '',
    priority: 'medium', content: '申请将储能调度优化API上架至数据产品市场',
    details: { '产品名称': '储能调度优化API', '产品类型': 'API服务', '价格': '¥2500/月', '审核周期': '3个工作日' },
  },
  {
    id: 'apr-010', title: '光伏电站监控连接器注册', type: 'connector_register', status: 'approved',
    applicant: '华能新能源', apply_time: '2025-05-10 09:00', approver: '王经理', approve_time: '2025-05-11 10:00', comment: '连接器配置合理，同意注册',
    priority: 'low', content: '申请注册光伏电站监控连接器',
    details: { '连接器名称': '光伏电站监控连接器', '类型': '轻量连接器', '数据源': '逆变器、汇流箱', '协议': 'HTTPS' },
  },
];

const APPROVAL_TYPE_MAP: Record<string, { label: string; icon: string; color: string }> = {
  subscription: { label: '数据订阅', icon: '📋', color: '#1890ff' },
  product_publish: { label: '产品上架', icon: '📦', color: '#52c41a' },
  connector_register: { label: '连接器注册', icon: '🔗', color: '#722ed1' },
  data_access: { label: '数据访问', icon: '🔑', color: '#fa541c' },
  org_certification: { label: '机构认证', icon: '🏛️', color: '#13c2c2' },
};

const APPROVAL_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' | 'primary' }> = {
  pending: { label: '待审批', theme: 'warning' },
  approved: { label: '已通过', theme: 'success' },
  rejected: { label: '已拒绝', theme: 'danger' },
  cancelled: { label: '已撤回', theme: 'default' },
};

const PRIORITY_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' }> = {
  low: { label: '低', theme: 'default' },
  medium: { label: '中', theme: 'warning' },
  high: { label: '高', theme: 'danger' },
};

const ApprovalCenterPage: React.FC = () => {
  // ===== Tab状态 =====
  const [activeTab, setActiveTab] = useState<string>('pending');

  // ===== 筛选 =====
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  // ===== 审批详情 =====
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<ApprovalItem | null>(null);

  // ===== 审批操作 =====
  const [approveOpen, setApproveOpen] = useState(false);
  const [approveItem, setApproveItem] = useState<ApprovalItem | null>(null);
  const [approveAction, setApproveAction] = useState<'approve' | 'reject'>('approve');
  const [approveComment, setApproveComment] = useState('');

  // ===== 批量审批 =====
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // ===== 过滤数据 =====
  const pendingApprovals = useMemo(() => {
    return MOCK_APPROVALS.filter(a => a.status === 'pending').filter(a => {
      if (keyword && !a.title.includes(keyword) && !a.applicant.includes(keyword)) return false;
      if (typeFilter && a.type !== typeFilter) return false;
      if (priorityFilter && a.priority !== priorityFilter) return false;
      return true;
    });
  }, [keyword, typeFilter, priorityFilter]);

  const completedApprovals = useMemo(() => {
    return MOCK_APPROVALS.filter(a => a.status !== 'pending').filter(a => {
      if (keyword && !a.title.includes(keyword) && !a.applicant.includes(keyword)) return false;
      if (typeFilter && a.type !== typeFilter) return false;
      return true;
    });
  }, [keyword, typeFilter]);

  // 我发起的审批（模拟当前用户发起的）
  const myApplications = useMemo(() => {
    return MOCK_APPROVALS.filter(a => {
      if (keyword && !a.title.includes(keyword)) return false;
      if (typeFilter && a.type !== typeFilter) return false;
      return true;
    });
  }, [keyword, typeFilter]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    pending: MOCK_APPROVALS.filter(a => a.status === 'pending').length,
    approved: MOCK_APPROVALS.filter(a => a.status === 'approved').length,
    rejected: MOCK_APPROVALS.filter(a => a.status === 'rejected').length,
    total: MOCK_APPROVALS.length,
    passRate: parseFloat(((MOCK_APPROVALS.filter(a => a.status === 'approved').length / MOCK_APPROVALS.filter(a => a.status !== 'pending').length) * 100).toFixed(1)),
    avgTime: 1.5, // 天
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '审批中心' }],
    [],
  );

  // ===== ECharts配置 =====
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];

  const typeChartOption = useMemo(() => {
    const typeCount: Record<string, number> = {};
    MOCK_APPROVALS.forEach(a => { typeCount[APPROVAL_TYPE_MAP[a.type].label] = (typeCount[APPROVAL_TYPE_MAP[a.type].label] ?? 0) + 1; });
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 20 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: Object.entries(typeCount).map(([name, value], i) => ({ value, name, itemStyle: { color: COLORS[i % COLORS.length] } })),
      }],
    };
  }, []);

  const statusChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['待审批', '已通过', '已拒绝', '已撤回'] },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: [
        { value: MOCK_APPROVALS.filter(a => a.status === 'pending').length, itemStyle: { color: '#faad14' } },
        { value: MOCK_APPROVALS.filter(a => a.status === 'approved').length, itemStyle: { color: '#52c41a' } },
        { value: MOCK_APPROVALS.filter(a => a.status === 'rejected').length, itemStyle: { color: '#f5222d' } },
        { value: MOCK_APPROVALS.filter(a => a.status === 'cancelled').length, itemStyle: { color: '#d9d9d9' } },
      ],
      barWidth: '40%',
    }],
  }), []);

  const trendChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['申请数', '通过数', '拒绝数'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '申请数', type: 'bar', data: [5, 8, 6, 10, 7], itemStyle: { color: '#667eea' } },
      { name: '通过数', type: 'bar', data: [3, 5, 4, 7, 5], itemStyle: { color: '#52c41a' } },
      { name: '拒绝数', type: 'bar', data: [1, 2, 1, 2, 1], itemStyle: { color: '#f5222d' } },
    ],
  }), []);

  const timeChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['数据订阅', '产品上架', '连接器注册', '数据访问', '机构认证'] },
    yAxis: { type: 'value', name: '平均审批时间(天)' },
    series: [{
      type: 'bar',
      data: [
        { value: 1.5, itemStyle: { color: '#1890ff' } },
        { value: 3.2, itemStyle: { color: '#52c41a' } },
        { value: 1.0, itemStyle: { color: '#722ed1' } },
        { value: 0.8, itemStyle: { color: '#fa541c' } },
        { value: 2.5, itemStyle: { color: '#13c2c2' } },
      ],
      barWidth: '40%',
    }],
  }), []);

  // ===== 操作处理 =====
  const handleViewDetail = useCallback((item: ApprovalItem) => {
    setDetailItem(item);
    setDetailOpen(true);
  }, []);

  const handleApprove = useCallback((item: ApprovalItem, action: 'approve' | 'reject') => {
    setApproveItem(item);
    setApproveAction(action);
    setApproveComment('');
    setApproveOpen(true);
  }, []);

  const handleApproveSubmit = useCallback(() => {
    MessagePlugin.success(approveAction === 'approve' ? '审批已通过' : '审批已拒绝');
    setApproveOpen(false);
  }, [approveAction]);

  const handleBatchApprove = useCallback(() => {
    if (selectedIds.length === 0) {
      MessagePlugin.warning('请先选择要审批的项目');
      return;
    }
    MessagePlugin.success(`已批量审批 ${selectedIds.length} 个项目`);
    setSelectedIds([]);
  }, [selectedIds]);

  // ===== 待审批列表列定义 =====
  const pendingColumns = [
    {
      title: '审批标题', colKey: 'title', width: 250,
      cell: ({ row }: { row: ApprovalItem }) => (
        <div>
          <span className="text-blue-600 cursor-pointer hover:underline font-medium" onClick={() => handleViewDetail(row)}>
            {row.title}
          </span>
          <div className="text-xs text-gray-500 mt-1">{row.applicant}</div>
        </div>
      ),
    },
    {
      title: '类型', colKey: 'type', width: 120,
      cell: ({ row }: { row: ApprovalItem }) => (
        <div className="flex items-center gap-1">
          <span>{APPROVAL_TYPE_MAP[row.type].icon}</span>
          <span>{APPROVAL_TYPE_MAP[row.type].label}</span>
        </div>
      ),
    },
    {
      title: '优先级', colKey: 'priority', width: 80,
      cell: ({ row }: { row: ApprovalItem }) => (
        <Tag theme={PRIORITY_MAP[row.priority].theme} variant="light">
          {PRIORITY_MAP[row.priority].label}
        </Tag>
      ),
    },
    { title: '申请人', colKey: 'applicant', width: 120 },
    { title: '申请时间', colKey: 'apply_time', width: 160 },
    {
      title: '操作', colKey: 'action', width: 200, fixed: 'right' as const,
      cell: ({ row }: { row: ApprovalItem }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)}>详情</Button>
          <Button size="small" variant="contained" theme="success" onClick={() => handleApprove(row, 'approve')}>通过</Button>
          <Button size="small" variant="contained" theme="danger" onClick={() => handleApprove(row, 'reject')}>拒绝</Button>
        </div>
      ),
    },
  ];

  // ===== 已审批列表列定义 =====
  const completedColumns = [
    {
      title: '审批标题', colKey: 'title', width: 250,
      cell: ({ row }: { row: ApprovalItem }) => (
        <span className="text-blue-600 cursor-pointer hover:underline" onClick={() => handleViewDetail(row)}>
          {row.title}
        </span>
      ),
    },
    {
      title: '类型', colKey: 'type', width: 120,
      cell: ({ row }: { row: ApprovalItem }) => (
        <div className="flex items-center gap-1">
          <span>{APPROVAL_TYPE_MAP[row.type].icon}</span>
          <span>{APPROVAL_TYPE_MAP[row.type].label}</span>
        </div>
      ),
    },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: ApprovalItem }) => (
        <Tag theme={APPROVAL_STATUS_MAP[row.status].theme} variant="light">
          {APPROVAL_STATUS_MAP[row.status].label}
        </Tag>
      ),
    },
    { title: '申请人', colKey: 'applicant', width: 120 },
    { title: '审批人', colKey: 'approver', width: 100 },
    { title: '审批时间', colKey: 'approve_time', width: 160 },
    {
      title: '审批意见', colKey: 'comment', width: 200,
      cell: ({ row }: { row: ApprovalItem }) => (
        <Tooltip content={row.comment}>
          <span className="text-sm text-gray-600 truncate block max-w-[180px]">{row.comment}</span>
        </Tooltip>
      ),
    },
    {
      title: '操作', colKey: 'action', width: 100,
      cell: ({ row }: { row: ApprovalItem }) => (
        <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)}>详情</Button>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="审批中心"
        subtitle="统一审批管理：待我审批、审批历史、审批统计"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: `批量审批 (${selectedIds.length})`, icon: <CheckCircleFilledIcon />, onClick: handleBatchApprove, variant: 'contained', disabled: selectedIds.length === 0 },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="待我审批" value={stats.pending} icon={<TimeIcon />} gradient="orange" />
        <StatCard title="已通过" value={stats.approved} icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="已拒绝" value={stats.rejected} icon={<ErrorCircleFilledIcon />} gradient="red" />
        <StatCard title="通过率" value={stats.passRate} icon={<TrendingUpIcon />} gradient="blue" unit="%" />
      </StatGrid>

      {/* 主内容 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="pending" label={`待我审批 (${stats.pending})`}>
          {/* 筛选栏 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索审批标题"
                style={{ width: 220 }}
                clearable
              />
              <Select
                value={typeFilter}
                onChange={setTypeFilter}
                options={[{ value: '', label: '全部类型' }, ...Object.entries(APPROVAL_TYPE_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Select
                value={priorityFilter}
                onChange={setPriorityFilter}
                options={[{ value: '', label: '全部优先级' }, { value: 'high', label: '高' }, { value: 'medium', label: '中' }, { value: 'low', label: '低' }]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setTypeFilter(''); setPriorityFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 待审批表格 */}
          <PageSection className="mt-4">
            <Table
              data={pendingApprovals}
              columns={pendingColumns}
              rowKey="id"
              bordered
              hover
              selectedRowKeys={selectedIds}
              onSelectChange={setSelectedIds}
              rowSelection={{ type: 'checkbox' }}
            />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="completed" label="我已审批">
          {/* 筛选栏 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索审批标题"
                style={{ width: 220 }}
                clearable
              />
              <Select
                value={typeFilter}
                onChange={setTypeFilter}
                options={[{ value: '', label: '全部类型' }, ...Object.entries(APPROVAL_TYPE_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setTypeFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 已审批表格 */}
          <PageSection className="mt-4">
            <Table data={completedApprovals} columns={completedColumns} rowKey="id" bordered hover />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="my-applications" label="我发起的">
          {/* 筛选栏 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索审批标题"
                style={{ width: 220 }}
                clearable
              />
              <Select
                value={typeFilter}
                onChange={setTypeFilter}
                options={[{ value: '', label: '全部类型' }, ...Object.entries(APPROVAL_TYPE_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setTypeFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 我发起的表格 */}
          <PageSection className="mt-4">
            <Table
              data={myApplications}
              columns={[
                {
                  title: '审批标题', colKey: 'title', width: 250,
                  cell: ({ row }: { row: ApprovalItem }) => (
                    <span className="text-blue-600 cursor-pointer hover:underline" onClick={() => handleViewDetail(row)}>
                      {row.title}
                    </span>
                  ),
                },
                {
                  title: '类型', colKey: 'type', width: 120,
                  cell: ({ row }: { row: ApprovalItem }) => (
                    <div className="flex items-center gap-1">
                      <span>{APPROVAL_TYPE_MAP[row.type].icon}</span>
                      <span>{APPROVAL_TYPE_MAP[row.type].label}</span>
                    </div>
                  ),
                },
                {
                  title: '状态', colKey: 'status', width: 100,
                  cell: ({ row }: { row: ApprovalItem }) => (
                    <Tag theme={APPROVAL_STATUS_MAP[row.status].theme} variant="light">
                      {APPROVAL_STATUS_MAP[row.status].label}
                    </Tag>
                  ),
                },
                { title: '申请时间', colKey: 'apply_time', width: 160 },
                { title: '审批人', colKey: 'approver', width: 120, cell: ({ row }: { row: ApprovalItem }) => row.approver || '—' },
                { title: '审批时间', colKey: 'approve_time', width: 160, cell: ({ row }: { row: ApprovalItem }) => row.approve_time || '—' },
                {
                  title: '操作', colKey: 'action', width: 100,
                  cell: ({ row }: { row: ApprovalItem }) => (
                    <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)}>详情</Button>
                  ),
                },
              ]}
              rowKey="id"
              bordered
              hover
            />
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 审批详情弹窗 */}
      <Dialog header="审批详情" visible={detailOpen} onClose={() => setDetailOpen(false)} width={700}>
        {detailItem && (
          <div className="space-y-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="审批编号">{detailItem.id}</Descriptions.Item>
              <Descriptions.Item label="类型"><div className="flex items-center gap-1"><span>{APPROVAL_TYPE_MAP[detailItem.type].icon}</span><span>{APPROVAL_TYPE_MAP[detailItem.type].label}</span></div></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag theme={APPROVAL_STATUS_MAP[detailItem.status].theme}>{APPROVAL_STATUS_MAP[detailItem.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="优先级"><Tag theme={PRIORITY_MAP[detailItem.priority].theme}>{PRIORITY_MAP[detailItem.priority].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="申请人">{detailItem.applicant}</Descriptions.Item>
              <Descriptions.Item label="申请时间">{detailItem.apply_time}</Descriptions.Item>
              {detailItem.approver && <Descriptions.Item label="审批人">{detailItem.approver}</Descriptions.Item>}
              {detailItem.approve_time && <Descriptions.Item label="审批时间">{detailItem.approve_time}</Descriptions.Item>}
              <Descriptions.Item label="内容" span={2}>{detailItem.content}</Descriptions.Item>
              {detailItem.comment && <Descriptions.Item label="审批意见" span={2}>{detailItem.comment}</Descriptions.Item>}
            </Descriptions>

            {/* 详细信息 */}
            <PageSection title="详细信息" titleIcon={<FileIcon />}>
              <Descriptions bordered column={2}>
                {Object.entries(detailItem.details).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key}>{value}</Descriptions.Item>
                ))}
              </Descriptions>
            </PageSection>

            {/* 审批流程 */}
            <PageSection title="审批流程" titleIcon={<ChartIcon />}>
              <Timeline>
                <Timeline.Item dotColor="green">
                  <div className="font-medium">提交申请</div>
                  <div className="text-xs text-gray-500">{detailItem.applicant} - {detailItem.apply_time}</div>
                </Timeline.Item>
                {detailItem.status !== 'pending' && (
                  <Timeline.Item dotColor={detailItem.status === 'approved' ? 'green' : 'red'}>
                    <div className="font-medium">{detailItem.status === 'approved' ? '审批通过' : '审批拒绝'}</div>
                    <div className="text-xs text-gray-500">{detailItem.approver} - {detailItem.approve_time}</div>
                    {detailItem.comment && <div className="text-sm text-gray-600 mt-1">{detailItem.comment}</div>}
                  </Timeline.Item>
                )}
                {detailItem.status === 'pending' && (
                  <Timeline.Item dotColor="gray">
                    <div className="font-medium">待审批</div>
                    <div className="text-xs text-gray-500">等待审批人处理</div>
                  </Timeline.Item>
                )}
              </Timeline>
            </PageSection>

            {/* 审批操作 */}
            {detailItem.status === 'pending' && (
              <div className="flex justify-end gap-2">
                <Button variant="contained" theme="success" onClick={() => { setDetailOpen(false); handleApprove(detailItem, 'approve'); }}>通过</Button>
                <Button variant="contained" theme="danger" onClick={() => { setDetailOpen(false); handleApprove(detailItem, 'reject'); }}>拒绝</Button>
              </div>
            )}
          </div>
        )}
      </Dialog>

      {/* 审批操作弹窗 */}
      <Dialog
        header={approveAction === 'approve' ? '审批通过' : '审批拒绝'}
        visible={approveOpen}
        onClose={() => setApproveOpen(false)}
        width={500}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setApproveOpen(false)}>取消</Button>
            <Button
              variant="contained"
              theme={approveAction === 'approve' ? 'success' : 'danger'}
              onClick={handleApproveSubmit}
            >
              确认{approveAction === 'approve' ? '通过' : '拒绝'}
            </Button>
          </div>
        }
      >
        {approveItem && (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <div className="font-semibold">{approveItem.title}</div>
              <div className="text-sm text-gray-500 mt-1">申请人：{approveItem.applicant}</div>
            </div>
            <Form.FormItem label="审批意见">
              <Textarea
                value={approveComment}
                onChange={setApproveComment}
                placeholder={approveAction === 'approve' ? '请输入通过意见（可选）' : '请输入拒绝原因（必填）'}
                rows={4}
              />
            </Form.FormItem>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default ApprovalCenterPage;
