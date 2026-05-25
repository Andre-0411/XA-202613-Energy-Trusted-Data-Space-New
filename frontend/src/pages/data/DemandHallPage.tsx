/**
 * 需求大厅页面（增强版）
 * 需求列表、发布需求、需求详情、认领承接、我的需求
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Button, Dialog, Input, Select, Tag, Tabs, Steps, Form, Textarea,
  Table, Tooltip, MessagePlugin, Descriptions, Timeline,
} from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, SearchIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TimeIcon,
  ChartIcon, TrendingUpIcon, FileIcon, UserIcon,
  EditIcon, MoneyIcon, ShieldErrorIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid } from '@/components/common';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/* ========== 模拟需求数据 ========== */
interface DemandItem {
  id: string;
  title: string;
  type: 'data_collect' | 'data_process' | 'model_train' | 'analysis_report' | 'system_dev';
  status: 'open' | 'claiming' | 'in_progress' | 'completed' | 'closed' | 'expired';
  budget: number;
  publisher: string;
  publish_time: string;
  deadline: string;
  description: string;
  requirements: string[];
  claimants: ClaimantItem[];
  security_level: 'low' | 'medium' | 'high';
  tags: string[];
}

interface ClaimantItem {
  id: string;
  name: string;
  submit_time: string;
  proposal: string;
  status: 'pending' | 'selected' | 'rejected';
}

const MOCK_DEMANDS: DemandItem[] = [
  {
    id: 'dem-001', title: '光伏电站运行数据采集与清洗', type: 'data_collect', status: 'open',
    budget: 50000, publisher: '华电研究院', publish_time: '2025-05-20', deadline: '2025-06-20',
    description: '需要采集100座光伏电站的运行数据，包括逆变器出力、辐照度、温度等参数，并进行数据清洗和标准化处理',
    requirements: ['数据采集经验3年以上', '熟悉光伏电站数据接口', '具备数据清洗能力', '有相关案例优先'],
    claimants: [
      { id: 'cl-001', name: '数据科技公司A', submit_time: '2025-05-21', proposal: '我们有丰富的光伏数据采集经验...', status: 'pending' },
      { id: 'cl-002', name: '新能源数据服务B', submit_time: '2025-05-22', proposal: '可以提供完整的数据采集方案...', status: 'pending' },
    ],
    security_level: 'medium', tags: ['光伏', '数据采集', '清洗'],
  },
  {
    id: 'dem-002', title: '电力负荷预测模型训练', type: 'model_train', status: 'claiming',
    budget: 80000, publisher: '国网营销部', publish_time: '2025-05-18', deadline: '2025-07-18',
    description: '基于历史用电数据训练电力负荷预测模型，支持日前和日内预测，精度要求MAPE<5%',
    requirements: ['深度学习建模经验', '电力行业背景', '有负荷预测项目经验', '模型可部署为API'],
    claimants: [
      { id: 'cl-003', name: '清华AI实验室', submit_time: '2025-05-19', proposal: '我们团队在电力负荷预测领域有深入研究...', status: 'selected' },
    ],
    security_level: 'high', tags: ['AI', '负荷预测', '深度学习'],
  },
  {
    id: 'dem-003', title: '碳排放数据分析报告', type: 'analysis_report', status: 'in_progress',
    budget: 30000, publisher: '碳交易中心', publish_time: '2025-05-10', deadline: '2025-06-10',
    description: '对区域碳排放数据进行深度分析，生成碳排放趋势报告和减排建议',
    requirements: ['碳排放分析经验', '熟悉碳交易政策', '报告撰写能力', '数据可视化能力'],
    claimants: [
      { id: 'cl-004', name: '绿色咨询公司', submit_time: '2025-05-12', proposal: '我们是专业的碳咨询机构...', status: 'selected' },
    ],
    security_level: 'low', tags: ['碳排放', '分析报告', '减排'],
  },
  {
    id: 'dem-004', title: '配电网故障诊断系统开发', type: 'system_dev', status: 'open',
    budget: 150000, publisher: '国网运检部', publish_time: '2025-05-15', deadline: '2025-08-15',
    description: '开发配电网故障诊断系统，基于故障录波数据实现故障类型识别和定位',
    requirements: ['电力系统专业背景', '有配电网项目经验', '熟悉故障诊断算法', '系统开发能力'],
    claimants: [],
    security_level: 'high', tags: ['配电网', '故障诊断', '系统开发'],
  },
  {
    id: 'dem-005', title: '储能电站数据治理服务', type: 'data_process', status: 'completed',
    budget: 25000, publisher: '宁德时代', publish_time: '2025-04-01', deadline: '2025-05-01',
    description: '对储能电站历史运行数据进行治理，包括数据清洗、格式标准化、质量评估',
    requirements: ['数据治理经验', '熟悉储能系统', '有数据质量评估工具'],
    claimants: [
      { id: 'cl-005', name: '数据治理公司C', submit_time: '2025-04-05', proposal: '我们有成熟的数据治理平台...', status: 'selected' },
    ],
    security_level: 'medium', tags: ['储能', '数据治理', '质量评估'],
  },
  {
    id: 'dem-006', title: '风电功率预测数据集构建', type: 'data_collect', status: 'expired',
    budget: 40000, publisher: '金风科技', publish_time: '2025-03-01', deadline: '2025-04-01',
    description: '构建风电功率预测训练数据集，包含气象数据、风机运行数据、功率数据',
    requirements: ['风电行业经验', '数据采集能力', '数据标注经验'],
    claimants: [],
    security_level: 'medium', tags: ['风电', '数据集', '功率预测'],
  },
];

const DEMAND_TYPE_MAP: Record<string, { label: string; icon: string; color: string }> = {
  data_collect: { label: '数据采集', icon: '📥', color: '#1890ff' },
  data_process: { label: '数据处理', icon: '⚙️', color: '#52c41a' },
  model_train: { label: '模型训练', icon: '🤖', color: '#722ed1' },
  analysis_report: { label: '分析报告', icon: '📊', color: '#fa541c' },
  system_dev: { label: '系统开发', icon: '💻', color: '#13c2c2' },
};

const DEMAND_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' | 'primary' }> = {
  open: { label: '开放中', theme: 'primary' },
  claiming: { label: '认领中', theme: 'warning' },
  in_progress: { label: '进行中', theme: 'primary' },
  completed: { label: '已完成', theme: 'success' },
  closed: { label: '已关闭', theme: 'default' },
  expired: { label: '已过期', theme: 'danger' },
};

const SECURITY_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' }> = {
  low: { label: '低风险', theme: 'success' },
  medium: { label: '中风险', theme: 'warning' },
  high: { label: '高风险', theme: 'danger' },
};

const DemandHallPage: React.FC = () => {
  // ===== Tab状态 =====
  const [activeTab, setActiveTab] = useState<string>('hall');

  // ===== 筛选 =====
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // ===== 发布需求 =====
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishStep, setPublishStep] = useState(0);
  const [newDemand, setNewDemand] = useState({
    title: '', type: 'data_collect', description: '', budget: '', deadline: '', requirements: '', tags: '',
  });

  // ===== 详情 =====
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailDemand, setDetailDemand] = useState<DemandItem | null>(null);

  // ===== 认领 =====
  const [claimOpen, setClaimOpen] = useState(false);
  const [claimDemand, setClaimDemand] = useState<DemandItem | null>(null);
  const [claimProposal, setClaimProposal] = useState('');

  // ===== 过滤数据 =====
  const filteredDemands = useMemo(() => {
    return MOCK_DEMANDS.filter(d => {
      if (keyword && !d.title.includes(keyword) && !d.description.includes(keyword)) return false;
      if (typeFilter && d.type !== typeFilter) return false;
      if (statusFilter && d.status !== statusFilter) return false;
      return true;
    });
  }, [keyword, typeFilter, statusFilter]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    total: MOCK_DEMANDS.length,
    open: MOCK_DEMANDS.filter(d => d.status === 'open').length,
    inProgress: MOCK_DEMANDS.filter(d => ['claiming', 'in_progress'].includes(d.status)).length,
    completed: MOCK_DEMANDS.filter(d => d.status === 'completed').length,
    totalBudget: MOCK_DEMANDS.reduce((s, d) => s + d.budget, 0),
  }), []);

  // ===== 我的需求 =====
  const myDemands = useMemo(() => {
    return MOCK_DEMANDS.filter(d => d.claimants.some(c => c.status === 'selected'));
  }, []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '需求大厅' }],
    [],
  );

  // ===== ECharts配置 =====
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];

  const typeChartOption = useMemo(() => {
    const typeCount: Record<string, number> = {};
    MOCK_DEMANDS.forEach(d => { typeCount[DEMAND_TYPE_MAP[d.type].label] = (typeCount[DEMAND_TYPE_MAP[d.type].label] ?? 0) + 1; });
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

  const budgetChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: MOCK_DEMANDS.map(d => d.title.substring(0, 8)), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '预算(元)' },
    series: [{
      type: 'bar',
      data: MOCK_DEMANDS.map((d, i) => ({ value: d.budget, itemStyle: { color: COLORS[i % COLORS.length] } })),
      barWidth: '40%',
    }],
  }), []);

  const trendChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['发布数', '完成数'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '发布数', type: 'bar', data: [15, 22, 18, 25, 30], itemStyle: { color: '#667eea' } },
      { name: '完成数', type: 'bar', data: [10, 15, 12, 18, 22], itemStyle: { color: '#52c41a' } },
    ],
  }), []);

  // ===== 操作处理 =====
  const handleViewDetail = useCallback((demand: DemandItem) => {
    setDetailDemand(demand);
    setDetailOpen(true);
  }, []);

  const handleClaim = useCallback((demand: DemandItem) => {
    setClaimDemand(demand);
    setClaimProposal('');
    setClaimOpen(true);
  }, []);

  const handleClaimSubmit = useCallback(() => {
    MessagePlugin.success('方案已提交，请等待需求方确认');
    setClaimOpen(false);
  }, []);

  const handlePublishNext = useCallback(() => {
    if (publishStep < 4) setPublishStep(publishStep + 1);
  }, [publishStep]);

  const handlePublishSubmit = useCallback(() => {
    MessagePlugin.success('需求发布成功！');
    setPublishOpen(false);
    setPublishStep(0);
  }, []);

  // ===== 需求列表列定义 =====
  const demandColumns = [
    {
      title: '需求标题', colKey: 'title', width: 250,
      cell: ({ row }: { row: DemandItem }) => (
        <div>
          <span className="text-blue-600 cursor-pointer hover:underline font-medium" onClick={() => handleViewDetail(row)}>
            {row.title}
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {row.tags.map(tag => <Tag key={tag} size="small" variant="outline">{tag}</Tag>)}
          </div>
        </div>
      ),
    },
    {
      title: '类型', colKey: 'type', width: 120,
      cell: ({ row }: { row: DemandItem }) => (
        <div className="flex items-center gap-1">
          <span>{DEMAND_TYPE_MAP[row.type].icon}</span>
          <span>{DEMAND_TYPE_MAP[row.type].label}</span>
        </div>
      ),
    },
    {
      title: '预算', colKey: 'budget', width: 120,
      cell: ({ row }: { row: DemandItem }) => <span className="text-orange-600 font-semibold">¥{row.budget.toLocaleString()}</span>,
    },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: DemandItem }) => (
        <Tag theme={DEMAND_STATUS_MAP[row.status].theme} variant="light">
          {DEMAND_STATUS_MAP[row.status].label}
        </Tag>
      ),
    },
    { title: '发布方', colKey: 'publisher', width: 120 },
    { title: '发布时间', colKey: 'publish_time', width: 120 },
    { title: '截止日期', colKey: 'deadline', width: 120 },
    {
      title: '安全评估', colKey: 'security_level', width: 100,
      cell: ({ row }: { row: DemandItem }) => (
        <Tag theme={SECURITY_MAP[row.security_level].theme} variant="light">
          {SECURITY_MAP[row.security_level].label}
        </Tag>
      ),
    },
    {
      title: '认领方', colKey: 'claimants', width: 80,
      cell: ({ row }: { row: DemandItem }) => <span className="font-semibold">{row.claimants.length}</span>,
    },
    {
      title: '操作', colKey: 'action', width: 150, fixed: 'right' as const,
      cell: ({ row }: { row: DemandItem }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)}>详情</Button>
          {row.status === 'open' && <Button size="small" variant="contained" onClick={() => handleClaim(row)}>认领</Button>}
        </div>
      ),
    },
  ];

  // ===== 渲染发布步骤内容 =====
  const renderPublishStepContent = () => {
    switch (publishStep) {
      case 0:
        return (
          <div className="space-y-4">
            <div className="text-sm text-gray-500 mb-4">选择需求类型</div>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(DEMAND_TYPE_MAP).map(([key, value]) => (
                <div
                  key={key}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all text-center ${newDemand.type === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                  onClick={() => setNewDemand({ ...newDemand, type: key })}
                >
                  <div className="text-3xl mb-2">{value.icon}</div>
                  <div className="font-semibold text-sm">{value.label}</div>
                </div>
              ))}
            </div>
          </div>
        );
      case 1:
        return (
          <Form labelWidth={100}>
            <Form.FormItem label="需求标题" required>
              <Input value={newDemand.title} onChange={(v) => setNewDemand({ ...newDemand, title: v })} placeholder="请输入需求标题" />
            </Form.FormItem>
            <Form.FormItem label="需求描述" required>
              <Textarea value={newDemand.description} onChange={(v) => setNewDemand({ ...newDemand, description: v })} placeholder="请详细描述需求内容" rows={4} />
            </Form.FormItem>
            <Form.FormItem label="预算(元)" required>
              <Input value={newDemand.budget} onChange={(v) => setNewDemand({ ...newDemand, budget: v })} placeholder="请输入预算金额" />
            </Form.FormItem>
            <Form.FormItem label="截止日期" required>
              <Input value={newDemand.deadline} onChange={(v) => setNewDemand({ ...newDemand, deadline: v })} placeholder="YYYY-MM-DD" />
            </Form.FormItem>
            <Form.FormItem label="具体要求">
              <Textarea value={newDemand.requirements} onChange={(v) => setNewDemand({ ...newDemand, requirements: v })} placeholder="每行一个要求" rows={3} />
            </Form.FormItem>
            <Form.FormItem label="标签">
              <Input value={newDemand.tags} onChange={(v) => setNewDemand({ ...newDemand, tags: v })} placeholder="多个标签用逗号分隔" />
            </Form.FormItem>
          </Form>
        );
      case 2:
        return (
          <div className="space-y-4">
            <div className="text-center py-4">
              <ShieldErrorIcon className="text-5xl text-blue-500 mb-2" />
              <div className="text-lg font-semibold">安全风险评估中...</div>
            </div>
            <Timeline>
              <Timeline.Item dotColor="green">需求内容合规性检查 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">数据安全等级评估 - 中风险</Timeline.Item>
              <Timeline.Item dotColor="green">预算合理性分析 - 合理</Timeline.Item>
              <Timeline.Item dotColor="green">发布方资质验证 - 通过</Timeline.Item>
            </Timeline>
          </div>
        );
      case 3:
        return (
          <Descriptions title="需求信息确认" bordered column={2}>
            <Descriptions.Item label="需求标题">{newDemand.title || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="类型">{DEMAND_TYPE_MAP[newDemand.type].label}</Descriptions.Item>
            <Descriptions.Item label="预算"><span className="text-orange-600 font-semibold">¥{Number(newDemand.budget || 0).toLocaleString()}</span></Descriptions.Item>
            <Descriptions.Item label="截止日期">{newDemand.deadline || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{newDemand.description || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="要求" span={2}>{newDemand.requirements || '无'}</Descriptions.Item>
          </Descriptions>
        );
      default:
        return null;
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title="需求大厅"
        subtitle="发布数据需求、认领承接项目、管理需求生命周期"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '发布需求', icon: <AddIcon />, onClick: () => { setPublishStep(0); setNewDemand({ title: '', type: 'data_collect', description: '', budget: '', deadline: '', requirements: '', tags: '' }); setPublishOpen(true); }, variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="需求总数" value={stats.total} icon={<FileIcon />} gradient="blue" />
        <StatCard title="开放中" value={stats.open} icon={<TimeIcon />} gradient="green" />
        <StatCard title="进行中" value={stats.inProgress} icon={<TrendingUpIcon />} gradient="orange" />
        <StatCard title="总预算" value={stats.totalBudget} icon={<MoneyIcon />} gradient="purple" unit="元" />
      </StatGrid>

      {/* 主内容 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="hall" label="需求大厅">
          {/* 筛选栏 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索需求标题"
                style={{ width: 220 }}
                clearable
              />
              <Select
                value={typeFilter}
                onChange={setTypeFilter}
                options={[{ value: '', label: '全部类型' }, ...Object.entries(DEMAND_TYPE_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                options={[{ value: '', label: '全部状态' }, ...Object.entries(DEMAND_STATUS_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setTypeFilter(''); setStatusFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 需求表格 */}
          <PageSection className="mt-4">
            <Table data={filteredDemands} columns={demandColumns} rowKey="id" bordered hover />
          </PageSection>

          {/* 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="需求类型分布" option={typeChartOption} height={300} />
            <ChartCard title="需求预算对比" option={budgetChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="my" label="我的需求">
          <PageSection title="我发布的" titleIcon={<EditIcon />} className="mt-4">
            <div className="text-center py-8 text-gray-400">暂无发布的需求</div>
          </PageSection>

          <PageSection title="我认领的" titleIcon={<UserIcon />} className="mt-4">
            <div className="space-y-3">
              {myDemands.map(demand => (
                <div key={demand.id} className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 bg-white hover:shadow-sm transition-shadow">
                  <div className="text-3xl">{DEMAND_TYPE_MAP[demand.type].icon}</div>
                  <div className="flex-1">
                    <div className="font-semibold">{demand.title}</div>
                    <div className="text-sm text-gray-500 mt-1">发布方：{demand.publisher} | 预算：¥{demand.budget.toLocaleString()}</div>
                  </div>
                  <Tag theme={DEMAND_STATUS_MAP[demand.status].theme} variant="light">{DEMAND_STATUS_MAP[demand.status].label}</Tag>
                  <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(demand)}>详情</Button>
                </div>
              ))}
              {myDemands.length === 0 && <div className="text-center py-8 text-gray-400">暂无认领的需求</div>}
            </div>
          </PageSection>

          <PageSection title="已完成" titleIcon={<CheckCircleFilledIcon />} className="mt-4">
            <div className="space-y-3">
              {MOCK_DEMANDS.filter(d => d.status === 'completed').map(demand => (
                <div key={demand.id} className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 bg-white">
                  <div className="text-3xl">{DEMAND_TYPE_MAP[demand.type].icon}</div>
                  <div className="flex-1">
                    <div className="font-semibold">{demand.title}</div>
                    <div className="text-sm text-gray-500 mt-1">发布方：{demand.publisher} | 预算：¥{demand.budget.toLocaleString()}</div>
                  </div>
                  <Tag theme="success" variant="light">已完成</Tag>
                </div>
              ))}
            </div>
          </PageSection>

          <ChartCard title="需求趋势" option={trendChartOption} height={300} className="mt-4" />
        </Tabs.TabPanel>
      </Tabs>

      {/* 发布需求弹窗 */}
      <Dialog header="发布需求" visible={publishOpen} onClose={() => setPublishOpen(false)} width={700}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setPublishOpen(false)}>取消</Button>
            {publishStep > 0 && <Button onClick={() => setPublishStep(publishStep - 1)}>上一步</Button>}
            {publishStep < 3 ? (
              <Button variant="contained" onClick={handlePublishNext}>下一步</Button>
            ) : (
              <Button variant="contained" theme="success" onClick={handlePublishSubmit}>确认发布</Button>
            )}
          </div>
        }
      >
        <Steps current={publishStep} style={{ marginBottom: 24 }}>
          <Steps.StepItem title="选择类型" />
          <Steps.StepItem title="填写信息" />
          <Steps.StepItem title="安全评估" />
          <Steps.StepItem title="确认发布" />
        </Steps>
        {renderPublishStepContent()}
      </Dialog>

      {/* 需求详情弹窗 */}
      <Dialog header="需求详情" visible={detailOpen} onClose={() => setDetailOpen(false)} width={800}>
        {detailDemand && (
          <div className="space-y-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="需求标题">{detailDemand.title}</Descriptions.Item>
              <Descriptions.Item label="类型"><div className="flex items-center gap-1"><span>{DEMAND_TYPE_MAP[detailDemand.type].icon}</span><span>{DEMAND_TYPE_MAP[detailDemand.type].label}</span></div></Descriptions.Item>
              <Descriptions.Item label="预算"><span className="text-orange-600 font-semibold">¥{detailDemand.budget.toLocaleString()}</span></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag theme={DEMAND_STATUS_MAP[detailDemand.status].theme}>{DEMAND_STATUS_MAP[detailDemand.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="发布方">{detailDemand.publisher}</Descriptions.Item>
              <Descriptions.Item label="安全评估"><Tag theme={SECURITY_MAP[detailDemand.security_level].theme}>{SECURITY_MAP[detailDemand.security_level].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="发布时间">{detailDemand.publish_time}</Descriptions.Item>
              <Descriptions.Item label="截止日期">{detailDemand.deadline}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{detailDemand.description}</Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                <div className="flex flex-wrap gap-1">
                  {detailDemand.tags.map(tag => <Tag key={tag} variant="outline">{tag}</Tag>)}
                </div>
              </Descriptions.Item>
            </Descriptions>

            {/* 具体要求 */}
            <PageSection title="具体要求" titleIcon={<FileIcon />}>
              <div className="space-y-2">
                {detailDemand.requirements.map((req, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <CheckCircleFilledIcon className="text-green-500 text-sm" />
                    <span>{req}</span>
                  </div>
                ))}
              </div>
            </PageSection>

            {/* 安全风险评估 */}
            <PageSection title="安全风险评估结果" titleIcon={<ShieldErrorIcon />}>
              <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
                <div className="flex items-center gap-2 mb-2">
                  <Tag theme={SECURITY_MAP[detailDemand.security_level].theme}>{SECURITY_MAP[detailDemand.security_level].label}</Tag>
                  <span className="font-semibold">综合风险等级</span>
                </div>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>• 数据安全等级：{detailDemand.security_level === 'high' ? '涉及敏感数据，需严格管控' : detailDemand.security_level === 'medium' ? '涉及内部数据，需适当管控' : '公开数据，风险较低'}</div>
                  <div>• 合规性评估：符合数据安全法规要求</div>
                  <div>• 隐私保护：已进行隐私影响评估</div>
                </div>
              </div>
            </PageSection>

            {/* 认领方列表 */}
            <PageSection title={`认领方列表 (${detailDemand.claimants.length})`} titleIcon={<UserIcon />}>
              {detailDemand.claimants.length > 0 ? (
                <div className="space-y-3">
                  {detailDemand.claimants.map(claimant => (
                    <div key={claimant.id} className="flex items-center gap-4 p-3 rounded-lg border border-gray-200 bg-white">
                      <UserIcon className="text-2xl text-blue-500" />
                      <div className="flex-1">
                        <div className="font-semibold">{claimant.name}</div>
                        <div className="text-sm text-gray-500 mt-1">{claimant.proposal}</div>
                      </div>
                      <div className="text-xs text-gray-400">{claimant.submit_time}</div>
                      <Tag theme={claimant.status === 'selected' ? 'success' : claimant.status === 'rejected' ? 'danger' : 'warning'} variant="light">
                        {claimant.status === 'selected' ? '已选中' : claimant.status === 'rejected' ? '已拒绝' : '待审核'}
                      </Tag>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-400">暂无认领方</div>
              )}
            </PageSection>

            {detailDemand.status === 'open' && (
              <div className="flex justify-end">
                <Button variant="contained" onClick={() => { setDetailOpen(false); handleClaim(detailDemand); }}>提交方案</Button>
              </div>
            )}
          </div>
        )}
      </Dialog>

      {/* 认领弹窗 */}
      <Dialog header="提交认领方案" visible={claimOpen} onClose={() => setClaimOpen(false)} width={600}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setClaimOpen(false)}>取消</Button>
            <Button variant="contained" theme="success" onClick={handleClaimSubmit}>提交方案</Button>
          </div>
        }
      >
        {claimDemand && (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <div className="font-semibold text-blue-800">{claimDemand.title}</div>
              <div className="text-sm text-blue-600 mt-1">预算：¥{claimDemand.budget.toLocaleString()} | 截止：{claimDemand.deadline}</div>
            </div>
            <Form labelWidth={100}>
              <Form.FormItem label="方案描述" required>
                <Textarea
                  value={claimProposal}
                  onChange={setClaimProposal}
                  placeholder="请详细描述您的实施方案、技术路线、团队优势等"
                  rows={6}
                />
              </Form.FormItem>
            </Form>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default DemandHallPage;
