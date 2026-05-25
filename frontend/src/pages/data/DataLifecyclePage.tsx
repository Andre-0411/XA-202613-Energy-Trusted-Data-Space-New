/**
 * 数据资源生命周期管理页面
 * 基于可信数据空间标准体系，实现数据全生命周期管理
 * 包含：接入登记、处理加工、发布发现、服务交付、价值评估、退出注销
 */
import React, { useState, useMemo } from 'react';
import { Button, Tag, Tabs, Dialog, Input, Select, Tooltip, MessagePlugin } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, EditIcon, DeleteIcon,
  CheckCircleFilledIcon, TimeIcon, TrendingUpIcon, DataBaseIcon,
  CloudUploadIcon, FileIcon, ChartIcon, LinkIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import StatusTag from '@/components/StatusTag';

/* ========== 类型定义 ========== */
interface LifecycleRecord {
  id: string;
  name: string;
  source: string;
  stage: string;
  status: string;
  security_level: string;
  owner: string;
  created_at: string;
  updated_at: string;
  description: string;
}

/* ========== 模拟数据 ========== */
const MOCK_LIFECYCLE_DATA: LifecycleRecord[] = [
  { id: 'lc-001', name: '电网负荷数据', source: '国网数据中台', stage: '接入登记', status: 'active', security_level: 'L3', owner: '数据中心', created_at: '2025-01-15T08:00:00Z', updated_at: '2025-05-20T10:30:00Z', description: '覆盖全省电网实时负荷监测数据' },
  { id: 'lc-002', name: '光伏发电出力数据', source: '新能源管理平台', stage: '处理加工', status: 'processing', security_level: 'L2', owner: '新能源部', created_at: '2025-02-10T09:00:00Z', updated_at: '2025-05-22T14:15:00Z', description: '分布式光伏电站实时出力监测' },
  { id: 'lc-003', name: '用户用电量统计', source: '营销系统', stage: '发布发现', status: 'published', security_level: 'L2', owner: '营销部', created_at: '2025-03-05T10:00:00Z', updated_at: '2025-05-18T16:45:00Z', description: '工商业用户用电量月度统计数据' },
  { id: 'lc-004', name: '充电桩运营数据', source: '充电服务平台', stage: '服务交付', status: 'delivering', security_level: 'L2', owner: '电动汽车部', created_at: '2025-01-20T11:00:00Z', updated_at: '2025-05-23T09:20:00Z', description: '公共充电桩使用率与运营状态' },
  { id: 'lc-005', name: '碳排放监测数据', source: '碳管理平台', stage: '价值评估', status: 'evaluating', security_level: 'L4', owner: '双碳办', created_at: '2025-04-01T08:30:00Z', updated_at: '2025-05-21T11:00:00Z', description: '重点企业碳排放实时监测数据' },
  { id: 'lc-006', name: '气象历史数据集', source: '气象局接口', stage: '退出注销', status: 'archived', security_level: 'L1', owner: '数据中心', created_at: '2024-06-01T08:00:00Z', updated_at: '2025-05-10T15:30:00Z', description: '2020-2024年历史气象数据（已到期）' },
  { id: 'lc-007', name: '风电场运行数据', source: '风电监控系统', stage: '接入登记', status: 'pending', security_level: 'L2', owner: '新能源部', created_at: '2025-05-01T09:00:00Z', updated_at: '2025-05-24T08:00:00Z', description: '沿海风电场设备运行状态数据' },
  { id: 'lc-008', name: '电价预测模型数据', source: '交易中心', stage: '处理加工', status: 'processing', security_level: 'L3', owner: '交易中心', created_at: '2025-04-15T10:00:00Z', updated_at: '2025-05-23T17:00:00Z', description: '电力市场日前电价预测所需特征数据' },
  { id: 'lc-009', name: '储能电站调度数据', source: '调度中心', stage: '发布发现', status: 'published', security_level: 'L3', owner: '调度中心', created_at: '2025-03-20T08:00:00Z', updated_at: '2025-05-19T13:45:00Z', description: '电化学储能电站充放电调度指令' },
  { id: 'lc-010', name: '综合能源服务数据', source: '综能服务平台', stage: '服务交付', status: 'delivering', security_level: 'L2', owner: '综能服务部', created_at: '2025-02-28T09:30:00Z', updated_at: '2025-05-22T10:10:00Z', description: '园区综合能源管理与优化数据' },
  { id: 'lc-011', name: '配电设备状态数据', source: '设备管理平台', stage: '价值评估', status: 'evaluating', security_level: 'L2', owner: '运检部', created_at: '2025-03-10T08:00:00Z', updated_at: '2025-05-20T14:30:00Z', description: '配变及开关设备在线监测数据' },
  { id: 'lc-012', name: '电力交易结算数据', source: '交易平台', stage: '退出注销', status: 'destroyed', security_level: 'L3', owner: '交易中心', created_at: '2024-01-01T00:00:00Z', updated_at: '2025-04-30T23:59:00Z', description: '2024年Q1交易结算明细（已按合约销毁）' },
];

const STAGE_OPTIONS = [
  { value: '', label: '全部阶段' },
  { value: '接入登记', label: '接入登记' },
  { value: '处理加工', label: '处理加工' },
  { value: '发布发现', label: '发布发现' },
  { value: '服务交付', label: '服务交付' },
  { value: '价值评估', label: '价值评估' },
  { value: '退出注销', label: '退出注销' },
];

const STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  active: { label: '已接入', theme: 'success' },
  processing: { label: '处理中', theme: 'primary' },
  published: { label: '已发布', theme: 'success' },
  delivering: { label: '交付中', theme: 'primary' },
  evaluating: { label: '评估中', theme: 'warning' },
  archived: { label: '已归档', theme: 'default' },
  pending: { label: '待接入', theme: 'warning' },
  destroyed: { label: '已销毁', theme: 'danger' },
};

const STAGE_ICONS: Record<string, React.ReactNode> = {
  '接入登记': <CloudUploadIcon />,
  '处理加工': <DataBaseIcon />,
  '发布发现': <FileIcon />,
  '服务交付': <LinkIcon />,
  '价值评估': <ChartIcon />,
  '退出注销': <DeleteIcon />,
};

const DataLifecyclePage: React.FC = () => {
  // ===== 状态 =====
  const [filterStage, setFilterStage] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedRecord, setSelectedRecord] = useState<LifecycleRecord | null>(null);

  // ===== 过滤数据 =====
  const filteredData = useMemo(() => {
    if (!filterStage) return MOCK_LIFECYCLE_DATA;
    return MOCK_LIFECYCLE_DATA.filter(r => r.stage === filterStage);
  }, [filterStage]);

  // ===== 统计数据 =====
  const stats = useMemo(() => {
    const total = MOCK_LIFECYCLE_DATA.length;
    const stageCounts: Record<string, number> = {};
    MOCK_LIFECYCLE_DATA.forEach(r => {
      stageCounts[r.stage] = (stageCounts[r.stage] || 0) + 1;
    });
    const activeCount = MOCK_LIFECYCLE_DATA.filter(r => ['active', 'processing', 'published', 'delivering'].includes(r.status)).length;
    const evaluatingCount = MOCK_LIFECYCLE_DATA.filter(r => r.status === 'evaluating').length;
    const archivedCount = MOCK_LIFECYCLE_DATA.filter(r => ['archived', 'destroyed'].includes(r.status)).length;
    return { total, activeCount, evaluatingCount, archivedCount, stageCounts };
  }, []);

  // ===== ECharts - 生命周期分布 =====
  const stageDistributionOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [{
      name: '生命周期阶段',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: [
        { value: stats.stageCounts['接入登记'] || 0, name: '接入登记', itemStyle: { color: '#2196f3' } },
        { value: stats.stageCounts['处理加工'] || 0, name: '处理加工', itemStyle: { color: '#4caf50' } },
        { value: stats.stageCounts['发布发现'] || 0, name: '发布发现', itemStyle: { color: '#ff9800' } },
        { value: stats.stageCounts['服务交付'] || 0, name: '服务交付', itemStyle: { color: '#9c27b0' } },
        { value: stats.stageCounts['价值评估'] || 0, name: '价值评估', itemStyle: { color: '#00bcd4' } },
        { value: stats.stageCounts['退出注销'] || 0, name: '退出注销', itemStyle: { color: '#e91e63' } },
      ],
    }],
  }), [stats]);

  // ===== ECharts - 安全等级分布 =====
  const securityDistOption = useMemo(() => {
    const levels: Record<string, number> = {};
    MOCK_LIFECYCLE_DATA.forEach(r => {
      levels[r.security_level] = (levels[r.security_level] || 0) + 1;
    });
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: Object.keys(levels) },
      yAxis: { type: 'value', name: '数量' },
      series: [{
        type: 'bar',
        data: Object.entries(levels).map(([k, v]) => ({
          value: v,
          itemStyle: {
            color: k === 'L4' ? '#f44336' : k === 'L3' ? '#ff9800' : k === 'L2' ? '#2196f3' : '#4caf50',
          },
        })),
        barWidth: '40%',
      }],
    };
  }, []);

  // ===== ECharts - 月度趋势 =====
  const trendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增接入', '完成处理', '退出注销'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '新增接入', type: 'line', smooth: true, data: [3, 5, 4, 6, 8], areaStyle: { opacity: 0.15 }, itemStyle: { color: '#2196f3' } },
      { name: '完成处理', type: 'line', smooth: true, data: [2, 3, 5, 4, 6], areaStyle: { opacity: 0.15 }, itemStyle: { color: '#4caf50' } },
      { name: '退出注销', type: 'line', smooth: true, data: [1, 0, 1, 2, 1], areaStyle: { opacity: 0.15 }, itemStyle: { color: '#f44336' } },
    ],
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '数据中心' }, { label: '数据生命周期' }],
    [],
  );

  // ===== 表格列定义 =====
  const columns: Column<LifecycleRecord>[] = useMemo(() => [
    {
      id: 'name', label: '数据名称', minWidth: 160,
      render: (row) => <span className="text-sm font-medium text-gray-900">{row.name}</span>,
    },
    { id: 'source', label: '数据来源', minWidth: 130 },
    {
      id: 'stage', label: '生命周期阶段', minWidth: 120,
      render: (row) => (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">{STAGE_ICONS[row.stage]}</span>
          <Tag variant="outline" size="small">{row.stage}</Tag>
        </div>
      ),
    },
    {
      id: 'status', label: '状态', minWidth: 90,
      render: (row) => {
        const s = STATUS_MAP[row.status];
        return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>;
      },
    },
    {
      id: 'security_level', label: '安全等级', minWidth: 90,
      render: (row) => {
        const colorMap: Record<string, string> = { L1: 'green', L2: 'blue', L3: 'orange', L4: 'red' };
        return <Tag theme={colorMap[row.security_level] as any || 'default'} size="small">{row.security_level}</Tag>;
      },
    },
    { id: 'owner', label: '责任方', minWidth: 100 },
    {
      id: 'updated_at', label: '更新时间', minWidth: 150,
      render: (row) => new Date(row.updated_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions', label: '操作', minWidth: 100, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span
              className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500"
              onClick={() => { setSelectedRecord(row); setDetailOpen(true); }}
            >
              <BrowseIcon />
            </span>
          </Tooltip>
          <Tooltip content="编辑">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500">
              <EditIcon />
            </span>
          </Tooltip>
        </div>
      ),
    },
  ], []);

  // ===== 生命周期流转视图 =====
  const stageFlowItems = [
    { key: '接入登记', label: '接入登记', desc: '数据源连接、元数据发现、安全定级', count: stats.stageCounts['接入登记'] || 0, color: '#2196f3' },
    { key: '处理加工', label: '处理加工', desc: '数据清洗、分类分级、质量评估', count: stats.stageCounts['处理加工'] || 0, color: '#4caf50' },
    { key: '发布发现', label: '发布发现', desc: '目录注册、供需匹配', count: stats.stageCounts['发布发现'] || 0, color: '#ff9800' },
    { key: '服务交付', label: '服务交付', desc: '接口封装、交付记录、质量监控', count: stats.stageCounts['服务交付'] || 0, color: '#9c27b0' },
    { key: '价值评估', label: '价值评估', desc: '资产评估、使用统计、收益分配', count: stats.stageCounts['价值评估'] || 0, color: '#00bcd4' },
    { key: '退出注销', label: '退出注销', desc: '数据销毁、合约终止', count: stats.stageCounts['退出注销'] || 0, color: '#e91e63' },
  ];

  return (
    <PageContainer>
      <PageHeader
        title="数据资源生命周期"
        subtitle="基于可信数据空间标准体系，管理数据从接入到退出的全生命周期"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '新增数据接入', icon: <AddIcon />, onClick: () => MessagePlugin.info('新增数据接入功能'), variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('数据已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="数据资源总数" value={stats.total} icon={<DataBaseIcon />} gradient="blue" unit="个" />
        <StatCard title="活跃资源" value={stats.activeCount} icon={<CheckCircleFilledIcon />} gradient="green" unit="个" />
        <StatCard title="评估中" value={stats.evaluatingCount} icon={<ChartIcon />} gradient="orange" unit="个" />
        <StatCard title="已归档/销毁" value={stats.archivedCount} icon={<TimeIcon />} gradient="purple" unit="个" />
      </StatGrid>

      {/* 生命周期流转视图 */}
      <PageSection title="生命周期流转" titleIcon={<TrendingUpIcon />}>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {stageFlowItems.map((item, idx) => (
            <div
              key={item.key}
              className="relative flex flex-col items-center p-4 rounded-lg border border-gray-200 bg-white hover:shadow-md transition-all cursor-pointer"
              onClick={() => setFilterStage(filterStage === item.key ? '' : item.key)}
              style={filterStage === item.key ? { borderColor: item.color, backgroundColor: `${item.color}08` } : {}}
            >
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-white mb-2"
                style={{ backgroundColor: item.color }}
              >
                {STAGE_ICONS[item.key]}
              </div>
              <span className="text-sm font-semibold text-gray-800">{item.label}</span>
              <span className="text-xs text-gray-500 mt-1 text-center">{item.desc}</span>
              <span className="text-lg font-bold mt-2" style={{ color: item.color }}>{item.count}</span>
              {idx < stageFlowItems.length - 1 && (
                <div className="hidden lg:block absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2 text-gray-300 z-10">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M6 4l8 6-8 6V4z" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </PageSection>

      {/* Tabs 切换 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="overview" label="概览图表">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="生命周期阶段分布" option={stageDistributionOption} className="lg:col-span-1" />
            <ChartCard title="月度生命周期趋势" option={trendOption} className="lg:col-span-2" />
          </div>
          <div className="mt-4">
            <ChartCard title="安全等级分布" option={securityDistOption} height={240} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="list" label="数据列表">
          {/* 过滤栏 */}
          <div className="mt-4 mb-4 flex items-center gap-3">
            <Select
              value={filterStage}
              options={STAGE_OPTIONS}
              onChange={(val) => setFilterStage(String(val))}
              style={{ width: 180 }}
              placeholder="筛选阶段"
            />
            <span className="text-sm text-gray-500">共 {filteredData.length} 条记录</span>
          </div>

          {/* 数据表格 */}
          <PageSection padding="none">
            <DataTable
              columns={columns}
              rows={filteredData}
              page={0}
              pageSize={20}
              total={filteredData.length}
            />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="stages" label="阶段详情">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
            {stageFlowItems.map((stage) => {
              const stageRecords = MOCK_LIFECYCLE_DATA.filter(r => r.stage === stage.key);
              return (
                <PageSection key={stage.key} title={stage.label} titleIcon={STAGE_ICONS[stage.key]}>
                  <p className="text-sm text-gray-500 mb-3">{stage.desc}</p>
                  <div className="space-y-2">
                    {stageRecords.length === 0 && (
                      <p className="text-sm text-gray-400 text-center py-4">暂无数据</p>
                    )}
                    {stageRecords.map((r) => (
                      <div key={r.id} className="flex items-center justify-between p-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer" onClick={() => { setSelectedRecord(r); setDetailOpen(true); }}>
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: stage.color }} />
                          <span className="text-sm text-gray-800 truncate">{r.name}</span>
                        </div>
                        <Tag theme={STATUS_MAP[r.status]?.theme || 'default'} size="small">{STATUS_MAP[r.status]?.label || r.status}</Tag>
                      </div>
                    ))}
                  </div>
                </PageSection>
              );
            })}
          </div>
        </Tabs.TabPanel>
      </Tabs>

      {/* 详情弹窗 */}
      <Dialog
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        header="数据资源详情"
        width={640}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}
      >
        {selectedRecord && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-gray-500">数据名称</span>
                <p className="text-sm font-semibold text-gray-800">{selectedRecord.name}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">数据来源</span>
                <p className="text-sm text-gray-800">{selectedRecord.source}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">生命周期阶段</span>
                <div className="flex items-center gap-1 mt-1">
                  {STAGE_ICONS[selectedRecord.stage]}
                  <Tag variant="outline" size="small">{selectedRecord.stage}</Tag>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">状态</span>
                <div className="mt-1">
                  <StatusTag status={STATUS_MAP[selectedRecord.status]?.label || selectedRecord.status} color={STATUS_MAP[selectedRecord.status]?.theme || 'default'} />
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">安全等级</span>
                <p className="text-sm text-gray-800">{selectedRecord.security_level}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">责任方</span>
                <p className="text-sm text-gray-800">{selectedRecord.owner}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">创建时间</span>
                <p className="text-sm text-gray-800">{new Date(selectedRecord.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">更新时间</span>
                <p className="text-sm text-gray-800">{new Date(selectedRecord.updated_at).toLocaleString('zh-CN')}</p>
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500">描述</span>
              <p className="text-sm text-gray-700 mt-1 p-3 bg-gray-50 rounded-lg">{selectedRecord.description}</p>
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default DataLifecyclePage;
