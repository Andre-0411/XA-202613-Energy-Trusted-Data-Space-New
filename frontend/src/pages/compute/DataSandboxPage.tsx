/**
 * 数据沙箱监控页面
 * 沙箱任务列表、资源使用监控（CPU/内存/存储）、算法准入审核、出口审核面板、计算结果导出
 */
import React, { useState, useMemo } from 'react';
import { Button, Tag, Progress, MessagePlugin, Select, Input } from 'tdesign-react';
import {
  RefreshIcon, SearchIcon, PlayIcon, PauseIcon,
  ServerIcon, CheckCircleIcon, TrendingUpIcon,
  DownloadIcon, SecuredIcon, AddIcon,
} from 'tdesign-icons-react';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/** 沙箱任务 */
interface SandboxTask {
  id: string;
  name: string;
  algorithm: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'reviewing';
  cpu: number;
  memory: number;
  storage: number;
  startTime: string;
  progress: number;
  resultReady: boolean;
}

/** 算法审核 */
interface AlgorithmReview {
  id: string;
  name: string;
  submitter: string;
  submitTime: string;
  riskLevel: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'rejected';
  scanResult: string;
}

/** 出口审核 */
interface ExportReview {
  id: string;
  taskId: string;
  taskName: string;
  requestTime: string;
  dataType: string;
  dataSize: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewer: string;
}

/** 模拟沙箱任务 */
const MOCK_TASKS: SandboxTask[] = [
  { id: 'SB-001', name: '负荷预测模型训练', algorithm: 'xgboost_v3.py', status: 'running', cpu: 72, memory: 65, storage: 45, startTime: '2026-05-25 08:30', progress: 68, resultReady: false },
  { id: 'SB-002', name: '新能源出力预测', algorithm: 'lstm_forecast.py', status: 'completed', cpu: 0, memory: 20, storage: 60, startTime: '2026-05-25 06:00', progress: 100, resultReady: true },
  { id: 'SB-003', name: '电价波动分析', algorithm: 'arima_analysis.py', status: 'running', cpu: 45, memory: 38, storage: 25, startTime: '2026-05-25 09:15', progress: 42, resultReady: false },
  { id: 'SB-004', name: '用户用电行为聚类', algorithm: 'kmeans_cluster.py', status: 'pending', cpu: 0, memory: 0, storage: 10, startTime: '-', progress: 0, resultReady: false },
  { id: 'SB-005', name: '设备故障诊断模型', algorithm: 'random_forest.py', status: 'failed', cpu: 0, memory: 0, storage: 30, startTime: '2026-05-25 07:00', progress: 35, resultReady: false },
  { id: 'SB-006', name: '配电网络拓扑优化', algorithm: 'graph_optimize.py', status: 'reviewing', cpu: 0, memory: 0, storage: 15, startTime: '-', progress: 0, resultReady: false },
];

/** 模拟算法审核 */
const MOCK_ALGORITHM_REVIEWS: AlgorithmReview[] = [
  { id: 'AR-001', name: 'graph_optimize.py', submitter: '张工', submitTime: '2026-05-25 09:00', riskLevel: 'low', status: 'pending', scanResult: '无恶意代码，依赖安全' },
  { id: 'AR-002', name: 'deep_learning_v2.py', submitter: '李工', submitTime: '2026-05-25 08:30', riskLevel: 'medium', status: 'pending', scanResult: '检测到网络请求，需人工审核' },
  { id: 'AR-003', name: 'data_extract.py', submitter: '王工', submitTime: '2026-05-25 07:45', riskLevel: 'high', status: 'rejected', scanResult: '包含敏感数据访问模式' },
];

/** 模拟出口审核 */
const MOCK_EXPORT_REVIEWS: ExportReview[] = [
  { id: 'ER-001', taskId: 'SB-002', taskName: '新能源出力预测', requestTime: '2026-05-25 10:00', dataType: '统计结果', dataSize: '2.5MB', status: 'pending', reviewer: '待分配' },
  { id: 'ER-002', taskId: 'SB-001', taskName: '负荷预测模型训练', requestTime: '2026-05-25 09:30', dataType: '模型参数', dataSize: '15MB', status: 'approved', reviewer: '赵主任' },
  { id: 'ER-003', taskId: 'SB-003', taskName: '电价波动分析', requestTime: '2026-05-25 11:00', dataType: '分析报告', dataSize: '1.2MB', status: 'pending', reviewer: '待分配' },
];

const DataSandboxPage: React.FC = () => {
  const [taskFilter, setTaskFilter] = useState<string>('all');
  const [searchText, setSearchText] = useState<string>('');

  // ===== ECharts 配置 =====
  const resourceUsageOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['CPU使用率', '内存使用率', '存储使用率'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00'],
    },
    yAxis: { type: 'value', name: '%', max: 100 },
    series: [
      { name: 'CPU使用率', type: 'line', smooth: true, data: [20, 18, 15, 25, 65, 72, 68], itemStyle: { color: '#1976d2' }, areaStyle: { color: 'rgba(25, 118, 210, 0.1)' } },
      { name: '内存使用率', type: 'line', smooth: true, data: [35, 32, 30, 40, 58, 65, 62], itemStyle: { color: '#4caf50' }, areaStyle: { color: 'rgba(76, 175, 80, 0.1)' } },
      { name: '存储使用率', type: 'line', smooth: true, data: [40, 40, 40, 42, 45, 48, 50], itemStyle: { color: '#ff9800' }, areaStyle: { color: 'rgba(255, 152, 0, 0.1)' } },
    ],
  }), []);

  const taskTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['提交', '完成', '失败'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: { type: 'value', name: '个数' },
    series: [
      { name: '提交', type: 'bar', data: [12, 15, 10, 18, 14, 8, 6], itemStyle: { color: 'rgba(33, 150, 243, 0.6)' } },
      { name: '完成', type: 'bar', data: [10, 13, 9, 15, 12, 7, 5], itemStyle: { color: '#4caf50' } },
      { name: '失败', type: 'bar', data: [1, 1, 0, 2, 1, 0, 0], itemStyle: { color: '#f44336' } },
    ],
  }), []);

  // ===== 过滤任务 =====
  const filteredTasks = useMemo(() => {
    let tasks = MOCK_TASKS;
    if (taskFilter !== 'all') {
      tasks = tasks.filter(t => t.status === taskFilter);
    }
    if (searchText) {
      tasks = tasks.filter(t => t.name.includes(searchText) || t.algorithm.includes(searchText));
    }
    return tasks;
  }, [taskFilter, searchText]);

  // ===== 状态映射 =====
  type TagTheme = 'default' | 'primary' | 'warning' | 'danger' | 'success';
  const taskStatusMap: Record<string, { color: TagTheme; label: string }> = {
    pending: { color: 'default', label: '待运行' },
    running: { color: 'primary', label: '运行中' },
    completed: { color: 'success', label: '已完成' },
    failed: { color: 'danger', label: '失败' },
    reviewing: { color: 'warning', label: '审核中' },
  };

  const reviewStatusMap: Record<string, { color: TagTheme; label: string }> = {
    pending: { color: 'warning', label: '待审核' },
    approved: { color: 'success', label: '已通过' },
    rejected: { color: 'danger', label: '已拒绝' },
  };

  const riskMap: Record<string, { color: TagTheme; label: string }> = {
    low: { color: 'success', label: '低风险' },
    medium: { color: 'warning', label: '中风险' },
    high: { color: 'danger', label: '高风险' },
  };

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '数据沙箱' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{ label: '创建沙箱任务', icon: <AddIcon />, onClick: () => MessagePlugin.info('创建沙箱任务'), variant: 'contained' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="数据沙箱"
        subtitle="安全隔离的数据计算环境，支持算法准入审核与结果安全导出"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => MessagePlugin.success('数据已刷新'),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <StatCard title="总沙箱任务" value={48} unit="个" icon={<ServerIcon size="20px" />} gradient="blue" />
        <StatCard title="运行中" value={2} unit="个" icon={<PlayIcon size="20px" />} gradient="green" />
        <StatCard title="待审核算法" value={2} unit="个" icon={<SecuredIcon size="20px" />} gradient="orange" />
        <StatCard title="今日完成" value={12} unit="个" icon={<CheckCircleIcon size="20px" />} gradient="purple" trend={8.3} />
      </div>

      {/* 资源监控 + 任务趋势 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard title="资源使用监控" subtitle="CPU/内存/存储实时使用率" option={resourceUsageOption} height={320} />
        <ChartCard title="任务执行趋势" subtitle="本周任务提交/完成/失败统计" option={taskTrendOption} height={320} />
      </div>

      {/* 沙箱任务列表 */}
      <div className="rounded-xl bg-white p-5 mb-4" style={{ border: '1px solid #e5e7eb' }}>
        <div className="flex items-center justify-between mb-4">
          <h6 className="text-base font-semibold text-gray-900 m-0">沙箱任务列表</h6>
          <div className="flex items-center gap-2">
            <Input
              value={searchText}
              onChange={setSearchText}
              placeholder="搜索任务名称/算法"
              prefixIcon={<SearchIcon />}
              style={{ width: 200 }}
              size="small"
            />
            <Select
              value={taskFilter}
              onChange={(val) => setTaskFilter(val as string)}
              options={[
                { label: '全部', value: 'all' },
                { label: '待运行', value: 'pending' },
                { label: '运行中', value: 'running' },
                { label: '已完成', value: 'completed' },
                { label: '失败', value: 'failed' },
                { label: '审核中', value: 'reviewing' },
              ]}
              style={{ width: 120 }}
              size="small"
            />
          </div>
        </div>
        <div className="flex flex-col gap-3">
          {filteredTasks.map((task) => (
            <div key={task.id} className="p-4 rounded-lg" style={{ backgroundColor: '#f8fafc', border: '1px solid #e8e8e8' }}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Tag variant="outline" size="small">{task.id}</Tag>
                  <Tag theme={taskStatusMap[task.status].color}>{taskStatusMap[task.status].label}</Tag>
                </div>
                <span className="text-xs text-gray-400">{task.startTime}</span>
              </div>
              <div className="flex items-center gap-6 mb-3">
                <div>
                  <p className="text-sm font-medium text-gray-900 m-0">{task.name}</p>
                  <p className="text-xs text-gray-500 m-0">算法: {task.algorithm}</p>
                </div>
              </div>
              {/* 资源使用条 */}
              {task.status === 'running' && (
                <div className="grid grid-cols-3 gap-4 mb-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500">CPU</span>
                      <span className="font-medium">{task.cpu}%</span>
                    </div>
                    <Progress percentage={task.cpu} size="small" color={task.cpu > 80 ? '#f44336' : '#1976d2'} />
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500">内存</span>
                      <span className="font-medium">{task.memory}%</span>
                    </div>
                    <Progress percentage={task.memory} size="small" color={task.memory > 80 ? '#f44336' : '#4caf50'} />
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500">存储</span>
                      <span className="font-medium">{task.storage}%</span>
                    </div>
                    <Progress percentage={task.storage} size="small" color={task.storage > 80 ? '#f44336' : '#ff9800'} />
                  </div>
                </div>
              )}
              {/* 进度条 */}
              {task.status === 'running' && (
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">执行进度</span>
                    <span className="font-medium">{task.progress}%</span>
                  </div>
                  <Progress percentage={task.progress} size="small" color="#1976d2" />
                </div>
              )}
              {/* 操作按钮 */}
              <div className="flex gap-2">
                {task.status === 'pending' && (
                  <Button size="small" theme="primary" icon={<PlayIcon />}>启动</Button>
                )}
                {task.status === 'running' && (
                  <Button size="small" variant="outline" icon={<PauseIcon />}>暂停</Button>
                )}
                {task.resultReady && (
                  <Button size="small" theme="success" variant="outline" icon={<DownloadIcon />}>导出结果</Button>
                )}
                {task.status === 'completed' && (
                  <Button size="small" variant="outline" icon={<DownloadIcon />}>导出审计日志</Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 算法准入审核 + 出口审核 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 算法准入审核 */}
        <div className="rounded-xl bg-white p-5" style={{ border: '1px solid #e5e7eb' }}>
          <h6 className="text-base font-semibold text-gray-900 m-0 mb-4">算法准入审核</h6>
          <div className="flex flex-col gap-3">
            {MOCK_ALGORITHM_REVIEWS.map((review) => (
              <div key={review.id} className="p-3 rounded-lg" style={{ backgroundColor: '#f8fafc', border: '1px solid #f0f0f0' }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Tag variant="outline" size="small">{review.name}</Tag>
                    <Tag theme={riskMap[review.riskLevel].color} size="small">{riskMap[review.riskLevel].label}</Tag>
                  </div>
                  <Tag theme={reviewStatusMap[review.status].color} size="small">{reviewStatusMap[review.status].label}</Tag>
                </div>
                <p className="text-xs text-gray-500 m-0">提交人: {review.submitter} | {review.submitTime}</p>
                <p className="text-xs text-gray-600 m-0 mt-1">扫描结果: {review.scanResult}</p>
                {review.status === 'pending' && (
                  <div className="flex gap-2 mt-2">
                    <Button size="small" theme="success" variant="outline" onClick={() => MessagePlugin.success('已通过')}>通过</Button>
                    <Button size="small" theme="danger" variant="outline" onClick={() => MessagePlugin.warning('已拒绝')}>拒绝</Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 出口审核面板 */}
        <div className="rounded-xl bg-white p-5" style={{ border: '1px solid #e5e7eb' }}>
          <h6 className="text-base font-semibold text-gray-900 m-0 mb-4">出口审核面板</h6>
          <div className="flex flex-col gap-3">
            {MOCK_EXPORT_REVIEWS.map((review) => (
              <div key={review.id} className="p-3 rounded-lg" style={{ backgroundColor: '#f8fafc', border: '1px solid #f0f0f0' }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Tag variant="outline" size="small">{review.taskId}</Tag>
                    <Tag theme={reviewStatusMap[review.status].color} size="small">{reviewStatusMap[review.status].label}</Tag>
                  </div>
                  <span className="text-xs text-gray-400">{review.requestTime}</span>
                </div>
                <p className="text-sm font-medium text-gray-900 m-0">{review.taskName}</p>
                <div className="flex gap-4 mt-1">
                  <span className="text-xs text-gray-500">类型: {review.dataType}</span>
                  <span className="text-xs text-gray-500">大小: {review.dataSize}</span>
                  <span className="text-xs text-gray-500">审核人: {review.reviewer}</span>
                </div>
                {review.status === 'pending' && (
                  <div className="flex gap-2 mt-2">
                    <Button size="small" theme="success" variant="outline" onClick={() => MessagePlugin.success('已批准导出')}>批准导出</Button>
                    <Button size="small" theme="danger" variant="outline" onClick={() => MessagePlugin.warning('已拒绝导出')}>拒绝</Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageContainer>
  );
};

export default DataSandboxPage;
