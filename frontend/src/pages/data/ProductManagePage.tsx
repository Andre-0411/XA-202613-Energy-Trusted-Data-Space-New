/**
 * 数据产品管理页面（增强版）
 * 产品列表、创建产品、产品开发、上架审核、产品详情、订阅管理
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Button, Dialog, Input, Select, Tag, Tabs, Steps, Form, Textarea,
  Table, Tooltip, MessagePlugin, Descriptions, Timeline, Progress,
} from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, DeleteIcon, EditIcon,
  SearchIcon, CheckCircleFilledIcon, ErrorCircleFilledIcon, TimeIcon,
  ChartIcon, TrendingUpIcon, FileIcon, ServerIcon, CloudUploadIcon,
  LinkIcon, UserIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid } from '@/components/common';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/* ========== 模拟数据产品 ========== */
interface DataProduct {
  id: string;
  name: string;
  type: 'api' | 'report' | 'application' | 'model' | 'dataset';
  status: 'draft' | 'developing' | 'pending_review' | 'reviewing' | 'published' | 'rejected' | 'archived';
  version: string;
  created_at: string;
  updated_at: string;
  publisher: string;
  description: string;
  subscribers: number;
  rating: number;
  price: number;
  review_cycle: string;
  review_comment: string;
  tags: string[];
}

const MOCK_PRODUCTS: DataProduct[] = [
  { id: 'prod-001', name: '光伏出力预测API', type: 'api', status: 'published', version: 'v2.1.0', created_at: '2025-01-15', updated_at: '2025-05-20', publisher: '华能新能源', description: '基于AI的光伏出力短期预测服务，支持15分钟至72小时预测', subscribers: 45, rating: 4.7, price: 2000, review_cycle: '3个工作日', review_comment: '', tags: ['AI', '光伏', '预测'] },
  { id: 'prod-002', name: '电力市场分析报告', type: 'report', status: 'published', version: 'v1.5.0', created_at: '2025-02-20', updated_at: '2025-05-18', publisher: '电力交易中心', description: '月度电力市场运行分析报告，含价格走势、交易量分析', subscribers: 128, rating: 4.5, price: 500, review_cycle: '5个工作日', review_comment: '', tags: ['市场', '分析', '报告'] },
  { id: 'prod-003', name: '碳足迹计算应用', type: 'application', status: 'published', version: 'v1.0.0', created_at: '2025-03-10', updated_at: '2025-05-15', publisher: '碳科技公司', description: '企业碳足迹计算与可视化工具，支持多种碳排放因子库', subscribers: 32, rating: 4.3, price: 1500, review_cycle: '5个工作日', review_comment: '', tags: ['碳排放', '计算', '可视化'] },
  { id: 'prod-004', name: '负荷预测模型', type: 'model', status: 'pending_review', version: 'v1.0.0', created_at: '2025-04-01', updated_at: '2025-05-22', publisher: '清华研究院', description: '基于深度学习的电力负荷预测模型，支持日前和日内预测', subscribers: 0, rating: 0, price: 3000, review_cycle: '7个工作日', review_comment: '', tags: ['AI', '负荷', '预测'] },
  { id: 'prod-005', name: '配电网故障诊断数据集', type: 'dataset', status: 'developing', version: 'v0.9.0', created_at: '2025-04-15', updated_at: '2025-05-23', publisher: '国网运检部', description: '配电网故障录波数据集，含10种故障类型的标注数据', subscribers: 0, rating: 0, price: 800, review_cycle: '5个工作日', review_comment: '', tags: ['配电网', '故障', '数据集'] },
  { id: 'prod-006', name: '储能调度优化API', type: 'api', status: 'reviewing', version: 'v1.0.0', created_at: '2025-05-01', updated_at: '2025-05-23', publisher: '宁德时代', description: '储能电站充放电策略优化API，支持多种调度目标', subscribers: 0, rating: 0, price: 2500, review_cycle: '3个工作日', review_comment: '', tags: ['储能', '调度', '优化'] },
  { id: 'prod-007', name: '新能源消纳评估报告', type: 'report', status: 'draft', version: 'v0.1.0', created_at: '2025-05-10', updated_at: '2025-05-23', publisher: '能源研究所', description: '区域新能源消纳能力评估报告，含消纳率分析和建议', subscribers: 0, rating: 0, price: 1000, review_cycle: '5个工作日', review_comment: '', tags: ['新能源', '消纳', '评估'] },
  { id: 'prod-008', name: '电力设备健康管理系统', type: 'application', status: 'rejected', version: 'v1.0.0', created_at: '2025-03-20', updated_at: '2025-05-10', publisher: '设备制造商', description: '基于物联网的电力设备健康管理与预测性维护系统', subscribers: 0, rating: 0, price: 5000, review_cycle: '7个工作日', review_comment: '安全评估未通过，需补充数据加密方案', tags: ['设备', '健康', '物联网'] },
];

/* ========== 模拟订阅记录 ========== */
interface ProductSubscription {
  id: string;
  product_id: string;
  product_name: string;
  subscriber: string;
  start_date: string;
  end_date: string;
  status: 'active' | 'expired' | 'cancelled';
  usage_count: number;
  api_calls: number;
}

const MOCK_PRODUCT_SUBS: ProductSubscription[] = [
  { id: 'psub-001', product_id: 'prod-001', product_name: '光伏出力预测API', subscriber: '华电研究院', start_date: '2025-03-01', end_date: '2026-03-01', status: 'active', usage_count: 15420, api_calls: 52300 },
  { id: 'psub-002', product_id: 'prod-001', product_name: '光伏出力预测API', subscriber: '金风科技', start_date: '2025-04-15', end_date: '2026-04-15', status: 'active', usage_count: 8900, api_calls: 31200 },
  { id: 'psub-003', product_id: 'prod-002', product_name: '电力市场分析报告', subscriber: '国电投', start_date: '2025-01-01', end_date: '2025-12-31', status: 'active', usage_count: 12, api_calls: 0 },
  { id: 'psub-004', product_id: 'prod-003', product_name: '碳足迹计算应用', subscriber: '宝钢集团', start_date: '2025-04-01', end_date: '2026-04-01', status: 'active', usage_count: 560, api_calls: 12000 },
  { id: 'psub-005', product_id: 'prod-002', product_name: '电力市场分析报告', subscriber: '华能集团', start_date: '2024-01-01', end_date: '2024-12-31', status: 'expired', usage_count: 12, api_calls: 0 },
];

const PRODUCT_TYPE_MAP: Record<string, { label: string; icon: string; color: string }> = {
  api: { label: 'API服务', icon: '🔗', color: '#1890ff' },
  report: { label: '分析报告', icon: '📊', color: '#52c41a' },
  application: { label: '应用系统', icon: '💻', color: '#722ed1' },
  model: { label: 'AI模型', icon: '🤖', color: '#fa541c' },
  dataset: { label: '数据集', icon: '📁', color: '#13c2c2' },
};

const PRODUCT_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' | 'primary' }> = {
  draft: { label: '草稿', theme: 'default' },
  developing: { label: '开发中', theme: 'primary' },
  pending_review: { label: '待审核', theme: 'warning' },
  reviewing: { label: '审核中', theme: 'warning' },
  published: { label: '已上架', theme: 'success' },
  rejected: { label: '已驳回', theme: 'danger' },
  archived: { label: '已归档', theme: 'default' },
};

const ProductManagePage: React.FC = () => {
  // ===== Tab状态 =====
  const [activeTab, setActiveTab] = useState<string>('list');

  // ===== 筛选 =====
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // ===== 创建产品 =====
  const [createOpen, setCreateOpen] = useState(false);
  const [createStep, setCreateStep] = useState(0);
  const [newProduct, setNewProduct] = useState({
    name: '', type: 'api', description: '', price: '', tags: '',
  });

  // ===== 详情 =====
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailProduct, setDetailProduct] = useState<DataProduct | null>(null);

  // ===== 审核 =====
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewProduct, setReviewProduct] = useState<DataProduct | null>(null);

  // ===== 过滤数据 =====
  const filteredProducts = useMemo(() => {
    return MOCK_PRODUCTS.filter(p => {
      if (keyword && !p.name.includes(keyword) && !p.description.includes(keyword)) return false;
      if (typeFilter && p.type !== typeFilter) return false;
      if (statusFilter && p.status !== statusFilter) return false;
      return true;
    });
  }, [keyword, typeFilter, statusFilter]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    total: MOCK_PRODUCTS.length,
    published: MOCK_PRODUCTS.filter(p => p.status === 'published').length,
    developing: MOCK_PRODUCTS.filter(p => ['developing', 'pending_review', 'reviewing'].includes(p.status)).length,
    totalSubscribers: MOCK_PRODUCTS.reduce((s, p) => s + p.subscribers, 0),
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据产品管理' }],
    [],
  );

  // ===== ECharts配置 =====
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#ff9800'];

  const typeChartOption = useMemo(() => {
    const typeCount: Record<string, number> = {};
    MOCK_PRODUCTS.forEach(p => { typeCount[PRODUCT_TYPE_MAP[p.type].label] = (typeCount[PRODUCT_TYPE_MAP[p.type].label] ?? 0) + 1; });
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

  const statusChartOption = useMemo(() => {
    const statusCount: Record<string, number> = {};
    MOCK_PRODUCTS.forEach(p => { statusCount[PRODUCT_STATUS_MAP[p.status].label] = (statusCount[PRODUCT_STATUS_MAP[p.status].label] ?? 0) + 1; });
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: Object.keys(statusCount) },
      yAxis: { type: 'value', name: '数量' },
      series: [{
        type: 'bar',
        data: Object.entries(statusCount).map(([name, value]) => ({
          value,
          itemStyle: {
            color: name === '已上架' ? '#52c41a' : name === '开发中' ? '#1890ff' : name === '待审核' ? '#faad14' : name === '已驳回' ? '#f5222d' : '#d9d9d9',
          },
        })),
        barWidth: '40%',
      }],
    };
  }, []);

  const subscriberChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增订阅', '续订'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增订阅', type: 'bar', stack: 'total', data: [8, 12, 15, 18, 22], itemStyle: { color: '#667eea' } },
      { name: '续订', type: 'bar', stack: 'total', data: [5, 8, 10, 12, 15], itemStyle: { color: '#43e97b' } },
    ],
  }), []);

  const revenueChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: { type: 'value', name: '收入(万元)' },
    series: [{
      type: 'line', data: [12.5, 18.2, 22.8, 28.5, 35.2], smooth: true,
      lineStyle: { width: 3, color: '#667eea' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(102,126,234,0.3)' }, { offset: 1, color: 'rgba(102,126,234,0.05)' }] } },
      itemStyle: { color: '#667eea' },
    }],
  }), []);

  // ===== 操作处理 =====
  const handleViewDetail = useCallback((product: DataProduct) => {
    setDetailProduct(product);
    setDetailOpen(true);
  }, []);

  const handleSubmitReview = useCallback((product: DataProduct) => {
    setReviewProduct(product);
    setReviewOpen(true);
  }, []);

  const handleCreateNext = useCallback(() => {
    if (createStep < 3) setCreateStep(createStep + 1);
  }, [createStep]);

  const handleCreateSubmit = useCallback(() => {
    MessagePlugin.success('产品创建成功！');
    setCreateOpen(false);
    setCreateStep(0);
  }, []);

  // ===== 产品列表列定义 =====
  const productColumns = [
    {
      title: '产品名称', colKey: 'name', width: 220,
      cell: ({ row }: { row: DataProduct }) => (
        <div>
          <span className="text-blue-600 cursor-pointer hover:underline font-medium" onClick={() => handleViewDetail(row)}>
            {row.name}
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {row.tags.map(tag => <Tag key={tag} size="small" variant="outline">{tag}</Tag>)}
          </div>
        </div>
      ),
    },
    {
      title: '类型', colKey: 'type', width: 120,
      cell: ({ row }: { row: DataProduct }) => (
        <div className="flex items-center gap-1">
          <span>{PRODUCT_TYPE_MAP[row.type].icon}</span>
          <span>{PRODUCT_TYPE_MAP[row.type].label}</span>
        </div>
      ),
    },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: DataProduct }) => (
        <Tag theme={PRODUCT_STATUS_MAP[row.status].theme} variant="light">
          {PRODUCT_STATUS_MAP[row.status].label}
        </Tag>
      ),
    },
    { title: '版本', colKey: 'version', width: 100 },
    { title: '发布方', colKey: 'publisher', width: 120 },
    {
      title: '订阅数', colKey: 'subscribers', width: 80,
      cell: ({ row }: { row: DataProduct }) => <span className="font-semibold">{row.subscribers}</span>,
    },
    {
      title: '评分', colKey: 'rating', width: 80,
      cell: ({ row }: { row: DataProduct }) => row.rating > 0 ? <span className="text-yellow-500">{row.rating}</span> : '-',
    },
    {
      title: '价格(元/月)', colKey: 'price', width: 110,
      cell: ({ row }: { row: DataProduct }) => <span className="text-orange-600">¥{row.price}</span>,
    },
    { title: '审核周期', colKey: 'review_cycle', width: 100 },
    { title: '更新时间', colKey: 'updated_at', width: 120 },
    {
      title: '操作', colKey: 'action', width: 200, fixed: 'right' as const,
      cell: ({ row }: { row: DataProduct }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)}>详情</Button>
          {row.status === 'draft' && <Button size="small" variant="contained" onClick={() => handleSubmitReview(row)}>提交审核</Button>}
          {row.status === 'pending_review' && <Button size="small" variant="contained" theme="warning">审核</Button>}
          {row.status === 'rejected' && <Button size="small" variant="text" icon={<EditIcon />}>修改</Button>}
        </div>
      ),
    },
  ];

  // ===== 订阅记录列定义 =====
  const subColumns = [
    { title: '订阅ID', colKey: 'id', width: 120, cell: ({ row }: { row: ProductSubscription }) => <span className="font-mono text-xs">{row.id}</span> },
    { title: '产品名称', colKey: 'product_name', width: 200 },
    { title: '订阅方', colKey: 'subscriber', width: 140 },
    { title: '开始日期', colKey: 'start_date', width: 120 },
    { title: '结束日期', colKey: 'end_date', width: 120 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: ProductSubscription }) => (
        <Tag theme={row.status === 'active' ? 'success' : row.status === 'expired' ? 'default' : 'danger'} variant="light">
          {row.status === 'active' ? '有效' : row.status === 'expired' ? '已过期' : '已取消'}
        </Tag>
      ),
    },
    { title: '使用次数', colKey: 'usage_count', width: 100, cell: ({ row }: { row: ProductSubscription }) => <span className="font-mono">{row.usage_count.toLocaleString()}</span> },
    { title: 'API调用', colKey: 'api_calls', width: 100, cell: ({ row }: { row: ProductSubscription }) => <span className="font-mono">{row.api_calls.toLocaleString()}</span> },
  ];

  // ===== 渲染创建步骤内容 =====
  const renderCreateStepContent = () => {
    switch (createStep) {
      case 0:
        return (
          <div className="space-y-4">
            <div className="text-sm text-gray-500 mb-4">选择产品类型</div>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(PRODUCT_TYPE_MAP).map(([key, value]) => (
                <div
                  key={key}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all text-center ${newProduct.type === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                  onClick={() => setNewProduct({ ...newProduct, type: key })}
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
            <Form.FormItem label="产品名称" required>
              <Input value={newProduct.name} onChange={(v) => setNewProduct({ ...newProduct, name: v })} placeholder="请输入产品名称" />
            </Form.FormItem>
            <Form.FormItem label="产品描述" required>
              <Textarea value={newProduct.description} onChange={(v) => setNewProduct({ ...newProduct, description: v })} placeholder="请输入产品描述" />
            </Form.FormItem>
            <Form.FormItem label="价格(元/月)" required>
              <Input value={newProduct.price} onChange={(v) => setNewProduct({ ...newProduct, price: v })} placeholder="请输入价格" />
            </Form.FormItem>
            <Form.FormItem label="标签">
              <Input value={newProduct.tags} onChange={(v) => setNewProduct({ ...newProduct, tags: v })} placeholder="多个标签用逗号分隔" />
            </Form.FormItem>
          </Form>
        );
      case 2:
        return (
          <div className="space-y-4">
            <div className="text-center py-4">
              <CloudUploadIcon className="text-5xl text-blue-500 mb-2" />
              <div className="text-lg font-semibold">上传产品材料</div>
              <div className="text-sm text-gray-500 mt-1">请上传产品文档、接口说明、使用指南等材料</div>
            </div>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer">
              <CloudUploadIcon className="text-4xl text-gray-400 mb-2" />
              <div className="text-sm text-gray-500">点击或拖拽文件到此区域上传</div>
            </div>
          </div>
        );
      case 3:
        return (
          <Descriptions title="产品信息确认" bordered column={2}>
            <Descriptions.Item label="产品名称">{newProduct.name || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="类型">{PRODUCT_TYPE_MAP[newProduct.type].label}</Descriptions.Item>
            <Descriptions.Item label="价格"><span className="text-orange-600">¥{newProduct.price || 0}/月</span></Descriptions.Item>
            <Descriptions.Item label="标签">{newProduct.tags || '无'}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{newProduct.description || '未填写'}</Descriptions.Item>
          </Descriptions>
        );
      default:
        return null;
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title="数据产品管理"
        subtitle="数据产品全生命周期管理：创建、开发、审核、上架、订阅"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '创建产品', icon: <AddIcon />, onClick: () => { setCreateStep(0); setNewProduct({ name: '', type: 'api', description: '', price: '', tags: '' }); setCreateOpen(true); }, variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="产品总数" value={stats.total} icon={<ServerIcon />} gradient="blue" />
        <StatCard title="已上架" value={stats.published} icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="开发/审核中" value={stats.developing} icon={<TimeIcon />} gradient="orange" />
        <StatCard title="总订阅数" value={stats.totalSubscribers} icon={<UserIcon />} gradient="purple" />
      </StatGrid>

      {/* 主内容 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="list" label="产品列表">
          {/* 筛选栏 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索产品名称"
                style={{ width: 220 }}
                clearable
              />
              <Select
                value={typeFilter}
                onChange={setTypeFilter}
                options={[{ value: '', label: '全部类型' }, ...Object.entries(PRODUCT_TYPE_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                options={[{ value: '', label: '全部状态' }, ...Object.entries(PRODUCT_STATUS_MAP).map(([k, v]) => ({ value: k, label: v.label }))]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setTypeFilter(''); setStatusFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 产品表格 */}
          <PageSection className="mt-4">
            <Table data={filteredProducts} columns={productColumns} rowKey="id" bordered hover />
          </PageSection>

          {/* 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="产品类型分布" option={typeChartOption} height={300} />
            <ChartCard title="产品状态统计" option={statusChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="subscriptions" label="订阅管理">
          <PageSection className="mt-4">
            <Table data={MOCK_PRODUCT_SUBS} columns={subColumns} rowKey="id" bordered hover />
          </PageSection>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="订阅趋势" option={subscriberChartOption} height={300} />
            <ChartCard title="收入趋势" option={revenueChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="review" label="上架审核">
          <PageSection title="待审核产品" titleIcon={<TimeIcon />} className="mt-4">
            <div className="space-y-3">
              {MOCK_PRODUCTS.filter(p => ['pending_review', 'reviewing'].includes(p.status)).map(product => (
                <div key={product.id} className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 bg-white hover:shadow-sm transition-shadow">
                  <div className="text-3xl">{PRODUCT_TYPE_MAP[product.type].icon}</div>
                  <div className="flex-1">
                    <div className="font-semibold">{product.name}</div>
                    <div className="text-sm text-gray-500 mt-1">{product.description}</div>
                    <div className="flex gap-2 mt-1">
                      <Tag variant="outline">{PRODUCT_TYPE_MAP[product.type].label}</Tag>
                      <Tag variant="outline">{product.version}</Tag>
                      <span className="text-xs text-gray-400">审核周期：{product.review_cycle}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="small" variant="contained" theme="success" onClick={() => MessagePlugin.success('审核通过')}>通过</Button>
                    <Button size="small" variant="contained" theme="danger" onClick={() => MessagePlugin.warning('已驳回')}>驳回</Button>
                  </div>
                </div>
              ))}
              {MOCK_PRODUCTS.filter(p => ['pending_review', 'reviewing'].includes(p.status)).length === 0 && (
                <div className="text-center py-8 text-gray-400">暂无待审核产品</div>
              )}
            </div>
          </PageSection>

          {/* 审核周期说明 */}
          <PageSection title="差异化审核周期" titleIcon={<ChartIcon />} className="mt-4">
            <div className="grid grid-cols-5 gap-3">
              {[
                { type: 'api', cycle: '3个工作日', desc: 'API接口文档审核+安全测试' },
                { type: 'report', cycle: '5个工作日', desc: '内容合规性审核+数据脱敏检查' },
                { type: 'application', cycle: '5个工作日', desc: '功能测试+安全评估+合规审查' },
                { type: 'model', cycle: '7个工作日', desc: '模型评估+安全测试+隐私合规' },
                { type: 'dataset', cycle: '5个工作日', desc: '数据质量检查+脱敏验证+合规审查' },
              ].map(item => (
                <div key={item.type} className="p-3 rounded-lg border border-gray-200 bg-white text-center">
                  <div className="text-2xl mb-1">{PRODUCT_TYPE_MAP[item.type].icon}</div>
                  <div className="font-semibold text-sm">{PRODUCT_TYPE_MAP[item.type].label}</div>
                  <div className="text-blue-600 font-semibold mt-1">{item.cycle}</div>
                  <div className="text-xs text-gray-500 mt-1">{item.desc}</div>
                </div>
              ))}
            </div>
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 创建产品弹窗 */}
      <Dialog header="创建数据产品" visible={createOpen} onClose={() => setCreateOpen(false)} width={700}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setCreateOpen(false)}>取消</Button>
            {createStep > 0 && <Button onClick={() => setCreateStep(createStep - 1)}>上一步</Button>}
            {createStep < 3 ? (
              <Button variant="contained" onClick={handleCreateNext}>下一步</Button>
            ) : (
              <Button variant="contained" theme="success" onClick={handleCreateSubmit}>提交</Button>
            )}
          </div>
        }
      >
        <Steps current={createStep} style={{ marginBottom: 24 }}>
          <Steps.StepItem title="选择类型" />
          <Steps.StepItem title="填写信息" />
          <Steps.StepItem title="上传材料" />
          <Steps.StepItem title="确认提交" />
        </Steps>
        {renderCreateStepContent()}
      </Dialog>

      {/* 产品详情弹窗 */}
      <Dialog header="产品详情" visible={detailOpen} onClose={() => setDetailOpen(false)} width={800}>
        {detailProduct && (
          <div className="space-y-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="产品名称">{detailProduct.name}</Descriptions.Item>
              <Descriptions.Item label="类型"><div className="flex items-center gap-1"><span>{PRODUCT_TYPE_MAP[detailProduct.type].icon}</span><span>{PRODUCT_TYPE_MAP[detailProduct.type].label}</span></div></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag theme={PRODUCT_STATUS_MAP[detailProduct.status].theme}>{PRODUCT_STATUS_MAP[detailProduct.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="版本">{detailProduct.version}</Descriptions.Item>
              <Descriptions.Item label="发布方">{detailProduct.publisher}</Descriptions.Item>
              <Descriptions.Item label="价格"><span className="text-orange-600 font-semibold">¥{detailProduct.price}/月</span></Descriptions.Item>
              <Descriptions.Item label="订阅数">{detailProduct.subscribers}</Descriptions.Item>
              <Descriptions.Item label="评分">{detailProduct.rating > 0 ? <span className="text-yellow-500">{detailProduct.rating}</span> : '暂无评分'}</Descriptions.Item>
              <Descriptions.Item label="审核周期">{detailProduct.review_cycle}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{detailProduct.updated_at}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{detailProduct.description}</Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                <div className="flex flex-wrap gap-1">
                  {detailProduct.tags.map(tag => <Tag key={tag} variant="outline">{tag}</Tag>)}
                </div>
              </Descriptions.Item>
              {detailProduct.review_comment && <Descriptions.Item label="审核意见" span={2}><span className="text-red-500">{detailProduct.review_comment}</span></Descriptions.Item>}
            </Descriptions>

            {/* 版本历史 */}
            <PageSection title="版本历史" titleIcon={<TimeIcon />}>
              <Timeline>
                <Timeline.Item dotColor="green">
                  <div className="font-medium">{detailProduct.version}</div>
                  <div className="text-xs text-gray-500">{detailProduct.updated_at} - 当前版本</div>
                </Timeline.Item>
                {detailProduct.version !== 'v1.0.0' && (
                  <Timeline.Item dotColor="blue">
                    <div className="font-medium">v1.0.0</div>
                    <div className="text-xs text-gray-500">2025-01-15 - 首次发布</div>
                  </Timeline.Item>
                )}
              </Timeline>
            </PageSection>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default ProductManagePage;
