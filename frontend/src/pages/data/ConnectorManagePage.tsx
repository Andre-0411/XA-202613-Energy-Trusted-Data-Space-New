/**
 * 连接器管理页面（增强版）
 * 连接器列表、创建连接器（5步骤）、文件库管理、API代理配置、连接器监控
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Button, Dialog, Input, Select, Tag, Tabs, Steps, Form, Textarea,
  Table, Tooltip, MessagePlugin, Switch, Progress, Descriptions, Timeline,
} from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, DeleteIcon, EditIcon,
  SearchIcon, CloudUploadIcon, LinkIcon, ChartIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TimeIcon,
  ServerIcon, DataBaseIcon, FileIcon, SettingIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid } from '@/components/common';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/* ========== 模拟连接器数据 ========== */
interface ConnectorItem {
  id: string;
  name: string;
  type: 'light' | 'standard' | 'custom';
  status: 'online' | 'offline' | 'connecting' | 'maintenance';
  created_at: string;
  data_sources: number;
  api_count: number;
  file_count: number;
  uptime: number;
  calls_today: number;
  error_rate: number;
  description: string;
}

const MOCK_CONNECTORS: ConnectorItem[] = [
  { id: 'conn-001', name: '电力调度数据连接器', type: 'standard', status: 'online', created_at: '2025-03-15', data_sources: 5, api_count: 12, file_count: 28, uptime: 99.8, calls_today: 15420, error_rate: 0.02, description: '接入省调、地调调度数据' },
  { id: 'conn-002', name: '光伏电站监控连接器', type: 'light', status: 'online', created_at: '2025-04-02', data_sources: 3, api_count: 8, file_count: 15, uptime: 99.5, calls_today: 8930, error_rate: 0.05, description: '光伏逆变器、汇流箱数据采集' },
  { id: 'conn-003', name: '用户用电采集连接器', type: 'standard', status: 'online', created_at: '2025-02-20', data_sources: 8, api_count: 20, file_count: 45, uptime: 99.9, calls_today: 32100, error_rate: 0.01, description: '智能电表用电数据采集与清洗' },
  { id: 'conn-004', name: '碳排放监测连接器', type: 'custom', status: 'maintenance', created_at: '2025-01-10', data_sources: 4, api_count: 6, file_count: 12, uptime: 95.2, calls_today: 0, error_rate: 0, description: '碳排放因子与监测数据对接' },
  { id: 'conn-005', name: '储能系统连接器', type: 'standard', status: 'online', created_at: '2025-05-01', data_sources: 2, api_count: 10, file_count: 8, uptime: 98.7, calls_today: 5600, error_rate: 0.08, description: 'BMS、PCS数据实时采集' },
  { id: 'conn-006', name: '气象数据连接器', type: 'light', status: 'connecting', created_at: '2025-05-10', data_sources: 1, api_count: 4, file_count: 6, uptime: 0, calls_today: 0, error_rate: 0, description: '气象局API对接中' },
  { id: 'conn-007', name: '配电物联网连接器', type: 'custom', status: 'offline', created_at: '2025-03-28', data_sources: 6, api_count: 15, file_count: 22, uptime: 88.5, calls_today: 0, error_rate: 2.1, description: '配电终端物联网数据接入' },
  { id: 'conn-008', name: '交易结算数据连接器', type: 'standard', status: 'online', created_at: '2025-04-15', data_sources: 3, api_count: 9, file_count: 18, uptime: 99.6, calls_today: 12300, error_rate: 0.03, description: '电力交易中心结算数据对接' },
];

/* ========== 模拟文件库数据 ========== */
interface FileItem {
  id: string;
  name: string;
  connector_id: string;
  connector_name: string;
  size: string;
  type: string;
  upload_time: string;
  status: 'active' | 'processing' | 'error';
}

const MOCK_FILES: FileItem[] = [
  { id: 'f-001', name: '调度日报_20250523.csv', connector_id: 'conn-001', connector_name: '电力调度数据连接器', size: '2.4MB', type: 'CSV', upload_time: '2025-05-23 10:30', status: 'active' },
  { id: 'f-002', name: '光伏出力实时数据.json', connector_id: 'conn-002', connector_name: '光伏电站监控连接器', size: '1.8MB', type: 'JSON', upload_time: '2025-05-23 09:15', status: 'active' },
  { id: 'f-003', name: '用户电量统计_05月.xlsx', connector_id: 'conn-003', connector_name: '用户用电采集连接器', size: '15.6MB', type: 'Excel', upload_time: '2025-05-22 16:45', status: 'active' },
  { id: 'f-004', name: '碳排放月报_202504.pdf', connector_id: 'conn-004', connector_name: '碳排放监测连接器', size: '3.2MB', type: 'PDF', upload_time: '2025-05-20 14:00', status: 'processing' },
  { id: 'f-005', name: '储能充放电记录.csv', connector_id: 'conn-005', connector_name: '储能系统连接器', size: '890KB', type: 'CSV', upload_time: '2025-05-23 11:20', status: 'active' },
  { id: 'f-006', name: '配电终端状态_异常.csv', connector_id: 'conn-007', connector_name: '配电物联网连接器', size: '456KB', type: 'CSV', upload_time: '2025-05-22 08:30', status: 'error' },
];

/* ========== 模拟API代理配置 ========== */
interface ApiProxyItem {
  id: string;
  name: string;
  endpoint: string;
  method: string;
  connector_id: string;
  status: 'active' | 'inactive';
  rate_limit: number;
  calls_today: number;
  avg_latency: number;
}

const MOCK_API_PROXIES: ApiProxyItem[] = [
  { id: 'api-001', name: '获取调度计划', endpoint: '/api/v1/dispatch/plans', method: 'GET', connector_id: 'conn-001', status: 'active', rate_limit: 1000, calls_today: 5420, avg_latency: 120 },
  { id: 'api-002', name: '光伏实时出力', endpoint: '/api/v1/pv/realtime', method: 'GET', connector_id: 'conn-002', status: 'active', rate_limit: 500, calls_today: 3200, avg_latency: 85 },
  { id: 'api-003', name: '用户电量查询', endpoint: '/api/v1/user/consumption', method: 'POST', connector_id: 'conn-003', status: 'active', rate_limit: 2000, calls_today: 12800, avg_latency: 200 },
  { id: 'api-004', name: '碳排放数据上报', endpoint: '/api/v1/carbon/report', method: 'POST', connector_id: 'conn-004', status: 'inactive', rate_limit: 100, calls_today: 0, avg_latency: 0 },
  { id: 'api-005', name: '储能状态查询', endpoint: '/api/v1/ess/status', method: 'GET', connector_id: 'conn-005', status: 'active', rate_limit: 800, calls_today: 2100, avg_latency: 95 },
  { id: 'api-006', name: '交易结算查询', endpoint: '/api/v1/trading/settlement', method: 'GET', connector_id: 'conn-008', status: 'active', rate_limit: 300, calls_today: 4500, avg_latency: 150 },
];

const CONNECTOR_TYPE_MAP: Record<string, { label: string; color: string }> = {
  light: { label: '轻量连接器', color: '#52c41a' },
  standard: { label: '标准连接器', color: '#1890ff' },
  custom: { label: '定制连接器', color: '#722ed1' },
};

const STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' }> = {
  online: { label: '在线', theme: 'success' },
  offline: { label: '离线', theme: 'danger' },
  connecting: { label: '连接中', theme: 'warning' },
  maintenance: { label: '维护中', theme: 'default' },
};

const FILE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'danger' | 'default' }> = {
  active: { label: '正常', theme: 'success' },
  processing: { label: '处理中', theme: 'warning' },
  error: { label: '异常', theme: 'danger' },
};

const ConnectorManagePage: React.FC = () => {
  // ===== Tab状态 =====
  const [activeTab, setActiveTab] = useState<string>('list');

  // ===== 列表筛选 =====
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // ===== 创建连接器 =====
  const [createOpen, setCreateOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [newConnector, setNewConnector] = useState({
    name: '', type: 'standard', description: '',
    host: '', port: '', username: '', password: '',
    protocol: 'https', timeout: 30,
  });

  // ===== 文件管理 =====
  const [fileKeyword, setFileKeyword] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);

  // ===== API代理 =====
  const [apiDialogOpen, setApiDialogOpen] = useState(false);
  const [newApi, setNewApi] = useState({ name: '', endpoint: '', method: 'GET', rate_limit: 100 });

  // ===== 详情 =====
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<ConnectorItem | null>(null);

  // ===== 过滤数据 =====
  const filteredConnectors = useMemo(() => {
    return MOCK_CONNECTORS.filter(c => {
      if (keyword && !c.name.includes(keyword)) return false;
      if (typeFilter && c.type !== typeFilter) return false;
      if (statusFilter && c.status !== statusFilter) return false;
      return true;
    });
  }, [keyword, typeFilter, statusFilter]);

  const filteredFiles = useMemo(() => {
    if (!fileKeyword) return MOCK_FILES;
    return MOCK_FILES.filter(f => f.name.includes(fileKeyword) || f.connector_name.includes(fileKeyword));
  }, [fileKeyword]);

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    total: MOCK_CONNECTORS.length,
    online: MOCK_CONNECTORS.filter(c => c.status === 'online').length,
    totalCalls: MOCK_CONNECTORS.reduce((s, c) => s + c.calls_today, 0),
    avgUptime: parseFloat((MOCK_CONNECTORS.filter(c => c.uptime > 0).reduce((s, c) => s + c.uptime, 0) / MOCK_CONNECTORS.filter(c => c.uptime > 0).length).toFixed(1)),
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '连接器管理' }],
    [],
  );

  // ===== ECharts 配置 =====
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#ff9800', '#9c27b0'];

  const callsChartOption = useMemo(() => {
    const items = MOCK_CONNECTORS.filter(c => c.status === 'online');
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: items.map(c => c.name.substring(0, 6)), axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '调用次数' },
      series: [{
        type: 'bar',
        data: items.map((c, i) => ({ value: c.calls_today, itemStyle: { color: COLORS[i % COLORS.length] } })),
        barWidth: '40%',
      }],
    };
  }, []);

  const typeChartOption = useMemo(() => {
    const typeCount = { light: 0, standard: 0, custom: 0 };
    MOCK_CONNECTORS.forEach(c => typeCount[c.type]++);
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 20 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: [
          { value: typeCount.light, name: '轻量连接器', itemStyle: { color: '#52c41a' } },
          { value: typeCount.standard, name: '标准连接器', itemStyle: { color: '#1890ff' } },
          { value: typeCount.custom, name: '定制连接器', itemStyle: { color: '#722ed1' } },
        ],
      }],
    };
  }, []);

  const uptimeChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['可用率', '错误率'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
    },
    yAxis: [
      { type: 'value', name: '可用率(%)', min: 95, max: 100 },
      { type: 'value', name: '错误率(%)', min: 0, max: 1 },
    ],
    series: [
      { name: '可用率', type: 'line', data: [99.8, 99.7, 99.9, 99.6, 99.8, 99.5, 99.7], smooth: true, lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '错误率', type: 'line', yAxisIndex: 1, data: [0.02, 0.03, 0.01, 0.04, 0.02, 0.05, 0.03], smooth: true, lineStyle: { color: '#f44336' }, itemStyle: { color: '#f44336' } },
    ],
  }), []);

  const latencyChartOption = useMemo(() => {
    const items = MOCK_API_PROXIES.filter(a => a.status === 'active');
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: items.map(a => a.name.substring(0, 6)), axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '延迟(ms)' },
      series: [{
        type: 'bar',
        data: items.map((a, i) => ({ value: a.avg_latency, itemStyle: { color: a.avg_latency > 150 ? '#ff9800' : '#52c41a' } })),
        barWidth: '40%',
      }],
    };
  }, []);

  // ===== 操作处理 =====
  const handleViewDetail = useCallback((item: ConnectorItem) => {
    setDetailItem(item);
    setDetailOpen(true);
  }, []);

  const handleCreateNext = useCallback(() => {
    if (currentStep < 4) setCurrentStep(currentStep + 1);
  }, [currentStep]);

  const handleCreatePrev = useCallback(() => {
    if (currentStep > 0) setCurrentStep(currentStep - 1);
  }, [currentStep]);

  const handleCreateSubmit = useCallback(() => {
    MessagePlugin.success('连接器创建成功！');
    setCreateOpen(false);
    setCurrentStep(0);
    setNewConnector({ name: '', type: 'standard', description: '', host: '', port: '', username: '', password: '', protocol: 'https', timeout: 30 });
  }, []);

  const handleCreateCancel = useCallback(() => {
    setCreateOpen(false);
    setCurrentStep(0);
  }, []);

  // ===== 连接器列表列定义 =====
  const connectorColumns = [
    {
      title: '连接器名称', colKey: 'name', width: 200,
      cell: ({ row }: { row: ConnectorItem }) => (
        <span className="text-blue-600 cursor-pointer hover:underline font-medium" onClick={() => handleViewDetail(row)}>
          {row.name}
        </span>
      ),
    },
    {
      title: '类型', colKey: 'type', width: 120,
      cell: ({ row }: { row: ConnectorItem }) => (
        <Tag color={CONNECTOR_TYPE_MAP[row.type].color} variant="light">
          {CONNECTOR_TYPE_MAP[row.type].label}
        </Tag>
      ),
    },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: ConnectorItem }) => (
        <Tag theme={STATUS_MAP[row.status].theme} variant="light">
          {STATUS_MAP[row.status].label}
        </Tag>
      ),
    },
    { title: '数据源数', colKey: 'data_sources', width: 100 },
    { title: 'API数', colKey: 'api_count', width: 80 },
    { title: '文件数', colKey: 'file_count', width: 80 },
    {
      title: '今日调用', colKey: 'calls_today', width: 120,
      cell: ({ row }: { row: ConnectorItem }) => (
        <span className="font-mono">{row.calls_today.toLocaleString()}</span>
      ),
    },
    {
      title: '可用率', colKey: 'uptime', width: 100,
      cell: ({ row }: { row: ConnectorItem }) => (
        <span className={row.uptime >= 99 ? 'text-green-600' : row.uptime >= 95 ? 'text-yellow-600' : 'text-red-600'}>
          {row.uptime > 0 ? `${row.uptime}%` : '-'}
        </span>
      ),
    },
    { title: '创建时间', colKey: 'created_at', width: 120 },
    {
      title: '操作', colKey: 'action', width: 150, fixed: 'right' as const,
      cell: ({ row }: { row: ConnectorItem }) => (
        <div className="flex gap-2">
          <Tooltip content="查看详情"><Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => handleViewDetail(row)} /></Tooltip>
          <Tooltip content="编辑"><Button size="small" variant="text" icon={<EditIcon />} /></Tooltip>
          <Tooltip content="删除"><Button size="small" variant="text" theme="danger" icon={<DeleteIcon />} /></Tooltip>
        </div>
      ),
    },
  ];

  // ===== 文件列表列定义 =====
  const fileColumns = [
    { title: '文件名', colKey: 'name', width: 250 },
    { title: '连接器', colKey: 'connector_name', width: 180 },
    { title: '类型', colKey: 'type', width: 80 },
    { title: '大小', colKey: 'size', width: 100 },
    { title: '上传时间', colKey: 'upload_time', width: 160 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: FileItem }) => (
        <Tag theme={FILE_STATUS_MAP[row.status].theme} variant="light">
          {FILE_STATUS_MAP[row.status].label}
        </Tag>
      ),
    },
    {
      title: '操作', colKey: 'action', width: 120,
      cell: () => (
        <div className="flex gap-2">
          <Button size="small" variant="text">下载</Button>
          <Button size="small" variant="text" theme="danger">删除</Button>
        </div>
      ),
    },
  ];

  // ===== API代理列定义 =====
  const apiColumns = [
    { title: 'API名称', colKey: 'name', width: 160 },
    { title: '端点', colKey: 'endpoint', width: 250, cell: ({ row }: { row: ApiProxyItem }) => <span className="font-mono text-sm">{row.endpoint}</span> },
    { title: '方法', colKey: 'method', width: 80, cell: ({ row }: { row: ApiProxyItem }) => <Tag variant="outline">{row.method}</Tag> },
    {
      title: '状态', colKey: 'status', width: 80,
      cell: ({ row }: { row: ApiProxyItem }) => (
        <Tag theme={row.status === 'active' ? 'success' : 'default'} variant="light">
          {row.status === 'active' ? '启用' : '禁用'}
        </Tag>
      ),
    },
    { title: '限流(次/分)', colKey: 'rate_limit', width: 110 },
    { title: '今日调用', colKey: 'calls_today', width: 100, cell: ({ row }: { row: ApiProxyItem }) => <span className="font-mono">{row.calls_today.toLocaleString()}</span> },
    { title: '平均延迟', colKey: 'avg_latency', width: 100, cell: ({ row }: { row: ApiProxyItem }) => <span>{row.avg_latency > 0 ? `${row.avg_latency}ms` : '-'}</span> },
    {
      title: '操作', colKey: 'action', width: 120,
      cell: () => (
        <div className="flex gap-2">
          <Button size="small" variant="text">编辑</Button>
          <Button size="small" variant="text" theme="danger">禁用</Button>
        </div>
      ),
    },
  ];

  // ===== 创建步骤内容 =====
  const renderCreateStepContent = () => {
    switch (currentStep) {
      case 0: // 选择类型
        return (
          <div className="space-y-4">
            <div className="text-sm text-gray-500 mb-4">选择连接器类型，不同类型适用于不同的数据接入场景</div>
            <div className="grid grid-cols-3 gap-4">
              {[
                { type: 'light', title: '轻量连接器', desc: '适用于简单API对接、文件传输等轻量场景，部署快速', icon: <CloudUploadIcon className="text-3xl text-green-500" /> },
                { type: 'standard', title: '标准连接器', desc: '适用于数据库对接、MQTT消息等标准场景，功能完整', icon: <ServerIcon className="text-3xl text-blue-500" /> },
                { type: 'custom', title: '定制连接器', desc: '适用于复杂业务逻辑、私有协议等定制场景，灵活扩展', icon: <SettingIcon className="text-3xl text-purple-500" /> },
              ].map(item => (
                <div
                  key={item.type}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${newConnector.type === item.type ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                  onClick={() => setNewConnector({ ...newConnector, type: item.type })}
                >
                  <div className="flex flex-col items-center text-center">
                    {item.icon}
                    <div className="mt-2 font-semibold">{item.title}</div>
                    <div className="mt-1 text-xs text-gray-500">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 1: // 配置参数
        return (
          <div className="space-y-4">
            <Form labelWidth={100}>
              <Form.FormItem label="连接器名称" required>
                <Input value={newConnector.name} onChange={(v) => setNewConnector({ ...newConnector, name: v })} placeholder="请输入连接器名称" />
              </Form.FormItem>
              <Form.FormItem label="描述">
                <Textarea value={newConnector.description} onChange={(v) => setNewConnector({ ...newConnector, description: v })} placeholder="请输入连接器描述" />
              </Form.FormItem>
              <Form.FormItem label="主机地址" required>
                <Input value={newConnector.host} onChange={(v) => setNewConnector({ ...newConnector, host: v })} placeholder="请输入主机地址" />
              </Form.FormItem>
              <Form.FormItem label="端口" required>
                <Input value={newConnector.port} onChange={(v) => setNewConnector({ ...newConnector, port: v })} placeholder="请输入端口号" />
              </Form.FormItem>
              <Form.FormItem label="协议">
                <Select value={newConnector.protocol} onChange={(v) => setNewConnector({ ...newConnector, protocol: v })} options={[{ value: 'https', label: 'HTTPS' }, { value: 'http', label: 'HTTP' }, { value: 'mqtt', label: 'MQTT' }]} />
              </Form.FormItem>
              <Form.FormItem label="用户名">
                <Input value={newConnector.username} onChange={(v) => setNewConnector({ ...newConnector, username: v })} placeholder="请输入用户名" />
              </Form.FormItem>
              <Form.FormItem label="密码">
                <Input type="password" value={newConnector.password} onChange={(v) => setNewConnector({ ...newConnector, password: v })} placeholder="请输入密码" />
              </Form.FormItem>
              <Form.FormItem label="超时(秒)">
                <Input type="number" value={String(newConnector.timeout)} onChange={(v) => setNewConnector({ ...newConnector, timeout: Number(v) })} />
              </Form.FormItem>
            </Form>
          </div>
        );
      case 2: // 部署
        return (
          <div className="space-y-4 text-center py-8">
            <ServerIcon className="text-6xl text-blue-500 mb-4" />
            <div className="text-lg font-semibold">正在部署连接器...</div>
            <Progress percentage={100} theme="success" />
            <div className="text-sm text-gray-500 mt-2">连接器已成功部署到运行环境</div>
          </div>
        );
      case 3: // 验证
        return (
          <div className="space-y-4">
            <div className="text-center py-4">
              <CheckCircleFilledIcon className="text-5xl text-green-500 mb-2" />
              <div className="text-lg font-semibold text-green-600">连接验证通过</div>
            </div>
            <Timeline>
              <Timeline.Item dotColor="green">网络连通性检查 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">认证信息验证 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">数据源可用性测试 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">数据格式解析测试 - 通过</Timeline.Item>
              <Timeline.Item dotColor="green">性能基准测试 - 达标</Timeline.Item>
            </Timeline>
          </div>
        );
      case 4: // 激活
        return (
          <div className="space-y-4">
            <Descriptions title="连接器信息确认" bordered column={2}>
              <Descriptions.Item label="名称">{newConnector.name || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="类型">{CONNECTOR_TYPE_MAP[newConnector.type].label}</Descriptions.Item>
              <Descriptions.Item label="主机">{newConnector.host || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="端口">{newConnector.port || '未填写'}</Descriptions.Item>
              <Descriptions.Item label="协议">{newConnector.protocol}</Descriptions.Item>
              <Descriptions.Item label="超时">{newConnector.timeout}秒</Descriptions.Item>
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
        title="连接器管理"
        subtitle="管理数据连接器、文件库、API代理配置及运行监控"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '创建连接器', icon: <AddIcon />, onClick: () => setCreateOpen(true), variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="连接器总数" value={stats.total} icon={<LinkIcon />} gradient="blue" />
        <StatCard title="在线连接器" value={stats.online} icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="今日总调用" value={stats.totalCalls} icon={<ChartIcon />} gradient="purple" unit="次" />
        <StatCard title="平均可用率" value={stats.avgUptime} icon={<TrendingUpIcon />} gradient="orange" unit="%" />
      </StatGrid>

      {/* 主内容 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="list" label="连接器列表">
          {/* 筛选栏 */}
          <PageSection className="mt-4">
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                prefixIcon={<SearchIcon />}
                value={keyword}
                onChange={setKeyword}
                placeholder="搜索连接器名称"
                style={{ width: 220 }}
                clearable
              />
              <Select
                value={typeFilter}
                onChange={setTypeFilter}
                options={[{ value: '', label: '全部类型' }, { value: 'light', label: '轻量连接器' }, { value: 'standard', label: '标准连接器' }, { value: 'custom', label: '定制连接器' }]}
                style={{ width: 150 }}
                clearable
              />
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                options={[{ value: '', label: '全部状态' }, { value: 'online', label: '在线' }, { value: 'offline', label: '离线' }, { value: 'connecting', label: '连接中' }, { value: 'maintenance', label: '维护中' }]}
                style={{ width: 150 }}
                clearable
              />
              <Button icon={<RefreshIcon />} onClick={() => { setKeyword(''); setTypeFilter(''); setStatusFilter(''); }}>重置</Button>
            </div>
          </PageSection>

          {/* 连接器表格 */}
          <PageSection className="mt-4">
            <Table
              data={filteredConnectors}
              columns={connectorColumns}
              rowKey="id"
              bordered
              hover
              pagination={{ current: 1, pageSize: 10, total: filteredConnectors.length }}
            />
          </PageSection>

          {/* 图表区域 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="今日调用统计" option={callsChartOption} height={300} />
            <ChartCard title="连接器类型分布" option={typeChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="files" label="文件库管理">
          <PageSection className="mt-4">
            <div className="flex justify-between items-center mb-4">
              <Input
                prefixIcon={<SearchIcon />}
                value={fileKeyword}
                onChange={setFileKeyword}
                placeholder="搜索文件名或连接器"
                style={{ width: 280 }}
                clearable
              />
              <Button icon={<CloudUploadIcon />} variant="contained" onClick={() => setUploadOpen(true)}>上传文件</Button>
            </div>
            <Table data={filteredFiles} columns={fileColumns} rowKey="id" bordered hover />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="api" label="API代理配置">
          <PageSection className="mt-4">
            <div className="flex justify-end mb-4">
              <Button icon={<AddIcon />} variant="contained" onClick={() => setApiDialogOpen(true)}>注册API</Button>
            </div>
            <Table data={MOCK_API_PROXIES} columns={apiColumns} rowKey="id" bordered hover />
          </PageSection>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="API延迟分布" option={latencyChartOption} height={300} />
            <ChartCard title="可用率与错误率趋势" option={uptimeChartOption} height={300} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="monitor" label="连接器监控">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="今日调用统计" option={callsChartOption} height={300} />
            <ChartCard title="连接器类型分布" option={typeChartOption} height={300} />
            <ChartCard title="可用率与错误率趋势" option={uptimeChartOption} height={300} />
            <ChartCard title="API延迟分布" option={latencyChartOption} height={300} />
          </div>

          {/* 告警信息 */}
          <PageSection title="异常告警" titleIcon={<ErrorCircleFilledIcon />} className="mt-4">
            <div className="space-y-3">
              {[
                { time: '2025-05-23 11:30', connector: '配电物联网连接器', level: '严重', message: '连接超时，已持续15分钟未响应' },
                { time: '2025-05-23 10:45', connector: '储能系统连接器', level: '警告', message: '错误率升至0.08%，超过阈值0.05%' },
                { time: '2025-05-23 09:20', connector: '气象数据连接器', level: '提示', message: '连接建立中，预计5分钟内完成' },
              ].map((alert, i) => (
                <div key={i} className="flex items-center gap-4 p-3 rounded-lg border border-gray-200 bg-white">
                  <Tag theme={alert.level === '严重' ? 'danger' : alert.level === '警告' ? 'warning' : 'primary'} variant="light">{alert.level}</Tag>
                  <div className="flex-1">
                    <div className="font-medium text-sm">{alert.connector}</div>
                    <div className="text-xs text-gray-500">{alert.message}</div>
                  </div>
                  <div className="text-xs text-gray-400">{alert.time}</div>
                </div>
              ))}
            </div>
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 创建连接器弹窗 */}
      <Dialog
        header="创建连接器"
        visible={createOpen}
        onClose={handleCreateCancel}
        width={720}
        footer={
          <div className="flex justify-between">
            <Button onClick={handleCreateCancel}>取消</Button>
            <div className="flex gap-2">
              {currentStep > 0 && <Button onClick={handleCreatePrev}>上一步</Button>}
              {currentStep < 4 ? (
                <Button variant="contained" onClick={handleCreateNext}>下一步</Button>
              ) : (
                <Button variant="contained" theme="success" onClick={handleCreateSubmit}>完成创建</Button>
              )}
            </div>
          </div>
        }
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Steps.StepItem title="选择类型" />
          <Steps.StepItem title="配置参数" />
          <Steps.StepItem title="部署" />
          <Steps.StepItem title="验证" />
          <Steps.StepItem title="激活" />
        </Steps>
        {renderCreateStepContent()}
      </Dialog>

      {/* 上传文件弹窗 */}
      <Dialog header="上传文件" visible={uploadOpen} onClose={() => setUploadOpen(false)} width={500}>
        <div className="space-y-4">
          <Form.FormItem label="选择连接器">
            <Select options={MOCK_CONNECTORS.filter(c => c.status === 'online').map(c => ({ value: c.id, label: c.name }))} placeholder="请选择连接器" />
          </Form.FormItem>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer">
            <CloudUploadIcon className="text-4xl text-gray-400 mb-2" />
            <div className="text-sm text-gray-500">点击或拖拽文件到此区域上传</div>
            <div className="text-xs text-gray-400 mt-1">支持 CSV、JSON、Excel、PDF 格式</div>
          </div>
        </div>
      </Dialog>

      {/* 注册API弹窗 */}
      <Dialog header="注册API" visible={apiDialogOpen} onClose={() => setApiDialogOpen(false)} width={500}>
        <Form labelWidth={100}>
          <Form.FormItem label="API名称" required>
            <Input value={newApi.name} onChange={(v) => setNewApi({ ...newApi, name: v })} placeholder="请输入API名称" />
          </Form.FormItem>
          <Form.FormItem label="端点" required>
            <Input value={newApi.endpoint} onChange={(v) => setNewApi({ ...newApi, endpoint: v })} placeholder="/api/v1/xxx" />
          </Form.FormItem>
          <Form.FormItem label="请求方法">
            <Select value={newApi.method} onChange={(v) => setNewApi({ ...newApi, method: v })} options={[{ value: 'GET', label: 'GET' }, { value: 'POST', label: 'POST' }, { value: 'PUT', label: 'PUT' }, { value: 'DELETE', label: 'DELETE' }]} />
          </Form.FormItem>
          <Form.FormItem label="限流(次/分)">
            <Input type="number" value={String(newApi.rate_limit)} onChange={(v) => setNewApi({ ...newApi, rate_limit: Number(v) })} />
          </Form.FormItem>
        </Form>
        <div className="flex justify-end mt-4">
          <Button variant="contained" onClick={() => { MessagePlugin.success('API注册成功'); setApiDialogOpen(false); }}>注册</Button>
        </div>
      </Dialog>

      {/* 连接器详情弹窗 */}
      <Dialog header="连接器详情" visible={detailOpen} onClose={() => setDetailOpen(false)} width={700}>
        {detailItem && (
          <div className="space-y-4">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="名称">{detailItem.name}</Descriptions.Item>
              <Descriptions.Item label="类型"><Tag color={CONNECTOR_TYPE_MAP[detailItem.type].color}>{CONNECTOR_TYPE_MAP[detailItem.type].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag theme={STATUS_MAP[detailItem.status].theme}>{STATUS_MAP[detailItem.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="创建时间">{detailItem.created_at}</Descriptions.Item>
              <Descriptions.Item label="数据源数">{detailItem.data_sources}</Descriptions.Item>
              <Descriptions.Item label="API数">{detailItem.api_count}</Descriptions.Item>
              <Descriptions.Item label="文件数">{detailItem.file_count}</Descriptions.Item>
              <Descriptions.Item label="可用率">{detailItem.uptime}%</Descriptions.Item>
              <Descriptions.Item label="今日调用">{detailItem.calls_today.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="错误率">{detailItem.error_rate}%</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{detailItem.description}</Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default ConnectorManagePage;
