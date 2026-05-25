/**
 * 计算任务管理页面
 * 任务列表、创建任务、任务详情、任务监控
 */
import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { Button, Input, Tooltip, MessagePlugin, Tag, Progress, Select, Textarea } from 'tdesign-react';
import {
  AddIcon, PlayIcon, StopIcon, RefreshIcon, ViewModuleIcon,
  AssignmentIcon, PlayCircleIcon, CheckCircleIcon, TrendingUpIcon,
  TimeIcon, InfoCircleIcon, DeleteIcon, EditIcon,
} from 'tdesign-icons-react';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import ResponsiveFilterBar from '@/components/responsive/ResponsiveFilterBar';

// ==================== 类型 ====================

interface MockTask {
  id: string;
  name: string;
  task_type: string;
  status: string;
  progress: number;
  creator: string;
  created_at: string;
  duration: string;
  participants: number;
  description: string;
  logs: string[];
}

// ==================== 模拟数据 ====================

const MOCK_TASKS: MockTask[] = [
  {
    id: 'task-001', name: '电力负荷联合预测', task_type: 'FL', status: 'running', progress: 68,
    creator: '张工', created_at: '2026-05-25 09:30:00', duration: '2h 15m', participants: 4,
    description: '基于联邦学习的多区域电力负荷联合预测任务，参与方包括国网北京、上海、广州、深圳',
    logs: [
      '[09:30] 任务创建，配置聚合算法: FedAvg',
      '[09:31] 参与方连接检查: 4/4 在线',
      '[09:32] 开始第 1 轮训练...',
      '[09:35] 第 1 轮完成, loss=1.234, acc=0.456',
      '[11:45] 第 68 轮完成, loss=0.089, acc=0.923',
    ],
  },
  {
    id: 'task-002', name: '安全电价协商', task_type: 'MPC', status: 'completed', progress: 100,
    creator: '李工', created_at: '2026-05-25 08:00:00', duration: '45m', participants: 3,
    description: '基于 MPC 秘密分享的安全电价协商计算，确保各方电价数据不泄露',
    logs: [
      '[08:00] MPC 任务创建，协议: 秘密分享',
      '[08:02] 3 方密钥交换完成',
      '[08:15] 秘密分享生成完成',
      '[08:40] 安全计算完成',
      '[08:45] 结果聚合，验证通过',
    ],
  },
  {
    id: 'task-003', name: '碳排放加密审计', task_type: 'HE', status: 'pending', progress: 0,
    creator: '王工', created_at: '2026-05-25 10:15:00', duration: '-', participants: 5,
    description: '使用同态加密对多家企业的碳排放数据进行加密审计，保护企业敏感数据',
    logs: ['[10:15] 任务创建，等待启动'],
  },
  {
    id: 'task-004', name: '敏感数据分析', task_type: 'TEE', status: 'completed', progress: 100,
    creator: '赵工', created_at: '2026-05-24 14:00:00', duration: '1h 20m', participants: 2,
    description: '在 Intel SGX 安全飞地中处理敏感电力交易数据',
    logs: [
      '[14:00] TEE 环境初始化: Intel SGX',
      '[14:05] 远程证明验证通过',
      '[14:10] 数据安全传入 TEE',
      '[15:15] 计算完成，结果加密输出',
      '[15:20] 完整性验证通过',
    ],
  },
  {
    id: 'task-005', name: '分布式差分隐私统计', task_type: 'DP', status: 'running', progress: 42,
    creator: '孙工', created_at: '2026-05-25 11:00:00', duration: '1h 5m', participants: 6,
    description: '对用户用电行为数据应用差分隐私保护后进行统计分析',
    logs: [
      '[11:00] 差分隐私参数: ε=1.0, δ=1e-5',
      '[11:05] 噪声机制: Laplace',
      '[12:05] 已处理 42% 数据',
    ],
  },
  {
    id: 'task-006', name: '能源数据沙箱分析', task_type: 'SANDBOX', status: 'failed', progress: 75,
    creator: '周工', created_at: '2026-05-24 16:00:00', duration: '2h', participants: 1,
    description: '在安全沙箱环境中对能源数据进行探索性分析',
    logs: [
      '[16:00] 沙箱环境创建',
      '[16:05] 数据导入完成',
      '[18:00] 错误: 内存溢出，任务中止',
    ],
  },
  {
    id: 'task-007', name: '新能源发电预测', task_type: 'FL', status: 'completed', progress: 100,
    creator: '张工', created_at: '2026-05-23 09:00:00', duration: '4h 30m', participants: 8,
    description: '基于联邦学习的多风电场、光伏电站发电功率预测',
    logs: [
      '[09:00] 联邦学习任务启动，8 参与方',
      '[13:30] 训练完成，准确率 94.2%',
    ],
  },
  {
    id: 'task-008', name: '跨域数据安全查询', task_type: 'MPC', status: 'running', progress: 30,
    creator: '李工', created_at: '2026-05-25 13:00:00', duration: '1h 30m', participants: 4,
    description: '基于混淆电路的安全多方查询，跨机构数据联合查询',
    logs: [
      '[13:00] 混淆电路构建',
      '[13:30] 电路混淆完成，开始求值',
      '[14:30] 求值进行中... 30%',
    ],
  },
];

const TASK_TYPE_OPTIONS = [
  { value: 'MPC', label: 'MPC 安全多方计算' },
  { value: 'FL', label: '联邦学习' },
  { value: 'TEE', label: 'TEE 可信执行' },
  { value: 'HE', label: '同态加密' },
  { value: 'DP', label: '差分隐私' },
  { value: 'SANDBOX', label: '沙箱计算' },
];

const STATUS_OPTIONS = [
  { value: 'created', label: '已创建' },
  { value: 'pending', label: '待处理' },
  { value: 'running', label: '运行中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'stopped', label: '已停止' },
];

const typeColorMap: Record<string, string> = {
  MPC: '#2196f3', FL: '#9c27b0', TEE: '#4caf50', HE: '#ff9800', DP: '#00bcd4', SANDBOX: '#f44336',
};

const typeLabelMap: Record<string, string> = {
  MPC: 'MPC', FL: '联邦学习', TEE: 'TEE', HE: '同态加密', DP: '差分隐私', SANDBOX: '沙箱',
};

// ==================== 主组件 ====================

const ComputeTasksPage: React.FC = () => {
  const navigate = useNavigate();

  // 筛选状态
  const [keyword, setKeyword] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  // 任务状态（本地模拟）
  const [tasks, setTasks] = useState<MockTask[]>(MOCK_TASKS);
  const [selectedTask, setSelectedTask] = useState<MockTask | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  // 创建任务表单
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('FL');
  const [newDesc, setNewDesc] = useState('');
  const [newParticipants, setNewParticipants] = useState('3');

  // 模拟进度更新
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setTasks((prev) =>
        prev.map((t) => {
          if (t.status !== 'running') return t;
          const newProgress = Math.min(100, t.progress + Math.random() * 3);
          if (newProgress >= 100) {
            return { ...t, status: 'completed', progress: 100 };
          }
          return { ...t, progress: Math.round(newProgress) };
        })
      );
    }, 5000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  // 统计
  const stats = useMemo(() => ({
    total: tasks.length,
    running: tasks.filter((t) => t.status === 'running').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
  }), [tasks]);

  // 过滤
  const filtered = useMemo(() => {
    let result = tasks;
    if (keyword.trim()) {
      const kw = keyword.toLowerCase();
      result = result.filter((t) => t.name.toLowerCase().includes(kw) || t.id.toLowerCase().includes(kw));
    }
    if (filterType) result = result.filter((t) => t.task_type === filterType);
    if (filterStatus) result = result.filter((t) => t.status === filterStatus);
    return result;
  }, [tasks, keyword, filterType, filterStatus]);

  const paged = useMemo(() => {
    const start = page * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, page, pageSize]);

  // 图表
  const trendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['任务创建', '任务完成'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category' as const, data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: { type: 'value' as const },
    series: [
      { name: '任务创建', type: 'bar', data: [8, 12, 6, 15, 10, 4, 3], itemStyle: { color: '#667eea', borderRadius: [4, 4, 0, 0] } },
      { name: '任务完成', type: 'bar', data: [6, 10, 5, 12, 8, 3, 2], itemStyle: { color: '#764ba2', borderRadius: [4, 4, 0, 0] } },
    ],
  }), []);

  const typeOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 11 },
      data: [
        { value: 2, name: '联邦学习', itemStyle: { color: '#9c27b0' } },
        { value: 2, name: 'MPC', itemStyle: { color: '#2196f3' } },
        { value: 1, name: 'TEE', itemStyle: { color: '#4caf50' } },
        { value: 1, name: '同态加密', itemStyle: { color: '#ff9800' } },
        { value: 1, name: '差分隐私', itemStyle: { color: '#00bcd4' } },
        { value: 1, name: '沙箱', itemStyle: { color: '#f44336' } },
      ],
    }],
  }), []);

  // 操作
  const handleStart = useCallback((id: string) => {
    setTasks((prev) => prev.map((t) => t.id === id ? { ...t, status: 'running', progress: 0 } : t));
    MessagePlugin.success('任务已启动');
  }, []);

  const handleStop = useCallback((id: string) => {
    setTasks((prev) => prev.map((t) => t.id === id ? { ...t, status: 'stopped' } : t));
    MessagePlugin.success('任务已停止');
  }, []);

  const handleCreate = useCallback(() => {
    if (!newName.trim()) {
      MessagePlugin.warning('请输入任务名称');
      return;
    }
    const newTask: MockTask = {
      id: `task-${Date.now()}`,
      name: newName,
      task_type: newType,
      status: 'created',
      progress: 0,
      creator: '当前用户',
      created_at: new Date().toLocaleString('zh-CN'),
      duration: '-',
      participants: parseInt(newParticipants) || 3,
      description: newDesc,
      logs: [`[${new Date().toLocaleTimeString('zh-CN')}] 任务创建`],
    };
    setTasks((prev) => [newTask, ...prev]);
    setCreateOpen(false);
    setNewName('');
    setNewDesc('');
    MessagePlugin.success('任务创建成功');
  }, [newName, newType, newDesc, newParticipants]);

  const handleViewDetail = useCallback((task: MockTask) => {
    setSelectedTask(task);
    setDetailOpen(true);
  }, []);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '计算任务' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '创建任务', icon: <AddIcon />, onClick: () => setCreateOpen(true), variant: 'contained' },
    ],
    [],
  );

  const getProgressColor = (status: string) => {
    if (status === 'failed') return '#f44336';
    if (status === 'completed') return '#4caf50';
    return '#667eea';
  };

  return (
    <PageContainer>
      <PageHeader
        title="计算任务"
        subtitle="管理可信计算任务的创建、执行与监控"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.info('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <StatCard title="总任务数" value={stats.total} unit="个" icon={<AssignmentIcon size="20px" />} gradient="purple" />
        <StatCard title="运行中" value={stats.running} unit="个" icon={<PlayCircleIcon size="20px" />} gradient="red" />
        <StatCard title="已完成" value={stats.completed} unit="个" icon={<CheckCircleIcon size="20px" />} gradient="green" />
        <StatCard title="失败任务" value={stats.failed} unit="个" icon={<InfoCircleIcon size="20px" />} gradient="orange" />
      </div>

      {/* 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <div className="md:col-span-2"><ChartCard title="本周任务趋势" option={trendOption} height={280} /></div>
        <ChartCard title="任务类型分布" option={typeOption} height={280} />
      </div>

      {/* 筛选栏 */}
      <ResponsiveFilterBar
        showClear={!!keyword || !!filterType || !!filterStatus}
        onClear={() => { setKeyword(''); setFilterType(''); setFilterStatus(''); setPage(0); }}
      >
        <Input value={keyword} onChange={setKeyword} placeholder="搜索任务名称/ID" style={{ minWidth: 200 }} />
        <Select value={filterType} onChange={(v) => { setFilterType(v as string); setPage(0); }} options={[{ label: '全部类型', value: '' }, ...TASK_TYPE_OPTIONS]} style={{ minWidth: 160 }} clearable />
        <Select value={filterStatus} onChange={(v) => { setFilterStatus(v as string); setPage(0); }} options={[{ label: '全部状态', value: '' }, ...STATUS_OPTIONS]} style={{ minWidth: 140 }} clearable />
      </ResponsiveFilterBar>

      {/* 任务列表 */}
      <div className="rounded-xl bg-white border border-gray-200 overflow-hidden">
        {/* 桌面端表格 */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-bold text-xs">任务名</th>
                <th className="px-4 py-3 text-left font-bold text-xs">类型</th>
                <th className="px-4 py-3 text-left font-bold text-xs">状态</th>
                <th className="px-4 py-3 text-left font-bold text-xs">进度</th>
                <th className="px-4 py-3 text-left font-bold text-xs">参与方</th>
                <th className="px-4 py-3 text-left font-bold text-xs">耗时</th>
                <th className="px-4 py-3 text-left font-bold text-xs">创建时间</th>
                <th className="px-4 py-3 text-center font-bold text-xs w-[160px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((task) => (
                <tr key={task.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-sm">{task.name}</p>
                    <p className="text-xs text-gray-400 truncate max-w-[200px]">{task.description}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Tag variant="outline" size="small" style={{ borderColor: typeColorMap[task.task_type], color: typeColorMap[task.task_type] }}>
                      {typeLabelMap[task.task_type] ?? task.task_type}
                    </Tag>
                  </td>
                  <td className="px-4 py-3">
                    <StatusTag status={task.status} />
                  </td>
                  <td className="px-4 py-3 min-w-[120px]">
                    <div className="flex items-center gap-2">
                      <Progress
                        theme="line"
                        percentage={task.progress}
                        style={{ flex: 1 }}
                        color={getProgressColor(task.status)}
                        size="small"
                      />
                      <span className="text-xs text-gray-400 w-8 text-right">{task.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{task.participants} 方</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{task.duration}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{task.created_at}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex gap-1 justify-center">
                      <Tooltip content="查看详情">
                        <Button variant="text" theme="primary" icon={<ViewModuleIcon />} onClick={() => handleViewDetail(task)} />
                      </Tooltip>
                      {(task.status === 'created' || task.status === 'stopped' || task.status === 'pending') && (
                        <Tooltip content="启动">
                          <Button variant="text" theme="success" icon={<PlayIcon />} onClick={() => handleStart(task.id)} />
                        </Tooltip>
                      )}
                      {task.status === 'running' && (
                        <Tooltip content="停止">
                          <Button variant="text" theme="warning" icon={<StopIcon />} onClick={() => handleStop(task.id)} />
                        </Tooltip>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {paged.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">暂无数据</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* 移动端卡片 */}
        <div className="md:hidden p-3">
          {paged.length === 0 ? (
            <div className="py-12 text-center text-gray-400">暂无数据</div>
          ) : (
            <div className="flex flex-col gap-3">
              {paged.map((task) => (
                <div key={task.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm font-semibold">{task.name}</p>
                    <StatusTag status={task.status} />
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <Tag variant="outline" size="small" style={{ borderColor: typeColorMap[task.task_type], color: typeColorMap[task.task_type] }}>
                      {typeLabelMap[task.task_type] ?? task.task_type}
                    </Tag>
                    <span className="text-xs text-gray-400">{task.participants} 方 | {task.duration}</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <Progress theme="line" percentage={task.progress} style={{ flex: 1 }} color={getProgressColor(task.status)} size="small" />
                    <span className="text-xs text-gray-400">{task.progress}%</span>
                  </div>
                  <p className="text-xs text-gray-400 mb-2">{task.created_at}</p>
                  <div className="flex gap-2 justify-end">
                    <Button size="small" variant="outline" icon={<ViewModuleIcon />} onClick={() => handleViewDetail(task)}>详情</Button>
                    {(task.status === 'created' || task.status === 'stopped') && (
                      <Button size="small" icon={<PlayIcon />} onClick={() => handleStart(task.id)}>启动</Button>
                    )}
                    {task.status === 'running' && (
                      <Button size="small" theme="warning" icon={<StopIcon />} onClick={() => handleStop(task.id)}>停止</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 分页 */}
        <div className="px-4 py-3 border-t border-gray-100 flex flex-wrap justify-end items-center gap-3">
          <span className="text-xs text-gray-400">每页</span>
          <Select value={pageSize} onChange={(v) => { setPageSize(v as number); setPage(0); }} options={[10, 20, 50].map((n) => ({ label: `${n} 行`, value: n }))} style={{ width: 80 }} />
          <span className="text-xs text-gray-400">{page * pageSize + 1}-{Math.min((page + 1) * pageSize, filtered.length)} / {filtered.length}</span>
          <Button variant="outline" size="small" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>上一页</Button>
          <Button variant="outline" size="small" disabled={(page + 1) * pageSize >= filtered.length} onClick={() => setPage((p) => p + 1)}>下一页</Button>
        </div>
      </div>

      {/* 任务详情弹窗 */}
      {detailOpen && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setDetailOpen(false)} />
          <div className="relative w-full max-w-2xl mx-4 bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[85vh]">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-base font-semibold">任务详情</h3>
              <Tag variant="outline" style={{ borderColor: typeColorMap[selectedTask.task_type], color: typeColorMap[selectedTask.task_type] }}>
                {typeLabelMap[selectedTask.task_type]}
              </Tag>
            </div>
            <div className="px-6 py-4 overflow-auto flex-1">
              {/* 基本信息 */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500">任务名称</p>
                  <p className="text-sm font-medium">{selectedTask.name}</p>
                </div>
                <div className="p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500">状态</p>
                  <StatusTag status={selectedTask.status} />
                </div>
                <div className="p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500">创建者</p>
                  <p className="text-sm">{selectedTask.creator}</p>
                </div>
                <div className="p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500">参与方</p>
                  <p className="text-sm">{selectedTask.participants} 方</p>
                </div>
                <div className="p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500">创建时间</p>
                  <p className="text-sm">{selectedTask.created_at}</p>
                </div>
                <div className="p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500">耗时</p>
                  <p className="text-sm">{selectedTask.duration}</p>
                </div>
              </div>

              {/* 进度 */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-1">执行进度</p>
                <Progress
                  theme="line"
                  percentage={selectedTask.progress}
                  color={getProgressColor(selectedTask.status)}
                />
              </div>

              {/* 描述 */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-1">任务描述</p>
                <p className="text-sm text-gray-700 p-3 bg-gray-50 rounded-lg">{selectedTask.description}</p>
              </div>

              {/* 执行日志 */}
              <div>
                <p className="text-xs text-gray-500 mb-1">执行日志</p>
                <div className="p-3 rounded-lg bg-gray-900 text-green-400 text-xs font-mono" style={{ maxHeight: 200, overflow: 'auto' }}>
                  {selectedTask.logs.map((log, i) => (
                    <div key={i} className="py-0.5">{log}</div>
                  ))}
                </div>
              </div>
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2">
              {(selectedTask.status === 'created' || selectedTask.status === 'stopped') && (
                <Button theme="primary" icon={<PlayIcon />} onClick={() => { handleStart(selectedTask.id); setDetailOpen(false); }}>启动</Button>
              )}
              {selectedTask.status === 'running' && (
                <Button theme="warning" icon={<StopIcon />} onClick={() => { handleStop(selectedTask.id); setDetailOpen(false); }}>停止</Button>
              )}
              <Button variant="outline" onClick={() => setDetailOpen(false)}>关闭</Button>
            </div>
          </div>
        </div>
      )}

      {/* 创建任务弹窗 */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setCreateOpen(false)} />
          <div className="relative w-full max-w-lg mx-4 bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold">创建计算任务</h3>
            </div>
            <div className="px-6 py-4 flex flex-col gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">任务名称 *</p>
                <Input value={newName} onChange={setNewName} placeholder="输入任务名称" />
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">计算类型</p>
                <Select value={newType} onChange={(v) => setNewType(v as string)} options={TASK_TYPE_OPTIONS} />
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">参与方数量</p>
                <Input value={newParticipants} onChange={setNewParticipants} type="number" placeholder="3" />
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">任务描述</p>
                <Textarea value={newDesc} onChange={setNewDesc} rows={3} placeholder="描述计算任务的目标和要求..." />
              </div>
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
              <Button theme="primary" onClick={handleCreate}>创建</Button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default ComputeTasksPage;
