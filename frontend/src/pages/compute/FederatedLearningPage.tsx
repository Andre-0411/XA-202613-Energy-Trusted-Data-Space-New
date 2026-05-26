/**
 * 联邦学习管理页面
 * 概览/训练任务/节点管理/模型仓库
 */
import React, { useState, useEffect } from 'react';
import { Button, Table, Tag, Dialog, Input, Select, Tabs, Progress, MessagePlugin, Row, Col, Card } from 'tdesign-react';
import { AddIcon, ServerIcon, RefreshIcon } from 'tdesign-icons-react';
import request from '@/api/request';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';

const ALGORITHMS = [{ label: 'FedAvg', value: 'fedavg' }, { label: 'FedProx', value: 'fedprox' }, { label: 'SCAFFOLD', value: 'scaffold' }];
const STATUS_MAP: Record<string, { label: string; theme: string }> = {
  running: { label: '训练中', theme: 'warning' }, completed: { label: '已完成', theme: 'success' },
  failed: { label: '失败', theme: 'danger' }, pending: { label: '等待中', theme: 'default' },
  active: { label: '在线', theme: 'success' }, inactive: { label: '离线', theme: 'default' },
};

const FederatedLearningPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [homeBreadcrumb, { label: '计算中心' }, { label: '联邦学习' }];
  const [tab, setTab] = useState('overview');
  const [tasks, setTasks] = useState<any[]>([]);
  const [nodes, setNodes] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', algorithm: 'fedavg', rounds: 10, learning_rate: 0.01, dataset: '' });
  const [stats] = useState({ total_tasks: 28, active_nodes: 12, avg_accuracy: 94.7, total_rounds: 1560 });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res: any = await request.get('/compute/tasks', { params: { page: 1, page_size: 20 } });
      const data = res?.data || res;
      setTasks(data?.items || data?.list || data || []);
    } catch {
      setTasks([
        { id: '1', name: '电网负荷预测联合训练', algorithm: 'fedavg', participants: 6, status: 'running', current_round: 7, total_rounds: 10, accuracy: 92.3 },
        { id: '2', name: '新能源出力预测模型', algorithm: 'fedprox', participants: 4, status: 'completed', current_round: 10, total_rounds: 10, accuracy: 95.1 },
        { id: '3', name: '设备故障诊断模型', algorithm: 'scaffold', participants: 8, status: 'pending', current_round: 0, total_rounds: 15, accuracy: 0 },
        { id: '4', name: '电力价格预测联合模型', algorithm: 'fedavg', participants: 5, status: 'running', current_round: 3, total_rounds: 8, accuracy: 87.6 },
      ]);
    }
    setNodes([
      { id: '1', name: '国网山东节点', type: '数据提供方', status: 'active', cpu: '85%', memory: '16GB', last_heartbeat: '2分钟前' },
      { id: '2', name: '华能集团节点', type: '数据提供方', status: 'active', cpu: '62%', memory: '32GB', last_heartbeat: '1分钟前' },
      { id: '3', name: '清华大学节点', type: '计算节点', status: 'active', cpu: '45%', memory: '64GB', last_heartbeat: '30秒前' },
      { id: '4', name: '南方电网节点', type: '数据提供方', status: 'inactive', cpu: '0%', memory: '8GB', last_heartbeat: '2小时前' },
    ]);
    setModels([
      { id: '1', name: '负荷预测v3.2', algorithm: 'fedavg', accuracy: 95.1, version: '3.2', created_at: '2026-05-20' },
      { id: '2', name: '故障诊断v2.0', algorithm: 'scaffold', accuracy: 92.3, version: '2.0', created_at: '2026-05-18' },
      { id: '3', name: '价格预测v1.5', algorithm: 'fedprox', accuracy: 89.7, version: '1.5', created_at: '2026-05-15' },
    ]);
  };

  const taskColumns = [
    { title: '任务名称', colKey: 'name', width: 200 },
    { title: '算法', colKey: 'algorithm', width: 100, cell: ({ row }: any) => <Tag variant="light">{row.algorithm?.toUpperCase()}</Tag> },
    { title: '参与方', colKey: 'participants', width: 80 },
    { title: '状态', colKey: 'status', width: 100, cell: ({ row }: any) => { const s = STATUS_MAP[row.status] || { label: row.status, theme: 'default' }; return <Tag theme={s.theme as any} variant="light">{s.label}</Tag>; } },
    { title: '训练进度', colKey: 'current_round', width: 180, cell: ({ row }: any) => <Progress theme="line" percentage={Math.round((row.current_round / row.total_rounds) * 100)} label={`${row.current_round}/${row.total_rounds}`} /> },
    { title: '精度', colKey: 'accuracy', width: 100, cell: ({ row }: any) => <span className="font-semibold text-blue-600">{row.accuracy}%</span> },
    { title: '操作', colKey: 'action', width: 120, cell: ({ row }: any) => (
      <div className="flex gap-1">
        {row.status === 'running' && <Button size="small" variant="text">暂停</Button>}
        <Button size="small" variant="text">详情</Button>
      </div>
    )},
  ];

  const nodeColumns = [
    { title: '节点名称', colKey: 'name', width: 180 },
    { title: '类型', colKey: 'type', width: 120, cell: ({ row }: any) => <Tag variant="light">{row.type}</Tag> },
    { title: '状态', colKey: 'status', width: 100, cell: ({ row }: any) => <Tag theme={row.status === 'active' ? 'success' : 'default'} variant="light">{STATUS_MAP[row.status]?.label || row.status}</Tag> },
    { title: 'CPU', colKey: 'cpu', width: 80 },
    { title: '内存', colKey: 'memory', width: 80 },
    { title: '最后心跳', colKey: 'last_heartbeat', width: 120 },
  ];

  const modelColumns = [
    { title: '模型名称', colKey: 'name', width: 180 },
    { title: '算法', colKey: 'algorithm', width: 100, cell: ({ row }: any) => <Tag variant="light">{row.algorithm?.toUpperCase()}</Tag> },
    { title: '精度', colKey: 'accuracy', width: 100, cell: ({ row }: any) => <span className="font-semibold text-green-600">{row.accuracy}%</span> },
    { title: '版本', colKey: 'version', width: 80 },
    { title: '创建时间', colKey: 'created_at', width: 150 },
    { title: '操作', colKey: 'action', width: 150, cell: () => (
      <div className="flex gap-1">
        <Button size="small" variant="text">部署</Button>
        <Button size="small" variant="text" theme="danger">删除</Button>
      </div>
    )},
  ];

  return (
    <PageContainer>
      <PageHeader title="联邦学习管理" breadcrumbs={breadcrumbs} />
      <Tabs value={tab} onChange={(v) => setTab(v as string)}>
        <Tabs.TabPanel value="overview" label="概览">
          <Row gutter={16} className="mb-4">
            {[
              { label: '训练任务', value: stats.total_tasks, color: '#165DFF', icon: '📊' },
              { label: '参与节点', value: stats.active_nodes, color: '#0FC6C2', icon: '🖥️' },
              { label: '平均精度', value: `${stats.avg_accuracy}%`, color: '#00B42A', icon: '🎯' },
              { label: '累计轮次', value: stats.total_rounds, color: '#FF7D00', icon: '🔄' },
            ].map((item, i) => (
              <Col key={i} span={3}>
                <Card className="text-center py-4">
                  <div className="text-2xl mb-1">{item.icon}</div>
                  <div className="text-2xl font-bold" style={{ color: item.color }}>{item.value}</div>
                  <div className="text-sm text-gray-500">{item.label}</div>
                </Card>
              </Col>
            ))}
          </Row>
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-semibold">联邦学习任务</h3>
            <Button theme="primary" icon={<AddIcon />} onClick={() => setShowCreate(true)}>创建任务</Button>
          </div>
          <Table data={tasks} columns={taskColumns} rowKey="id" bordered />
        </Tabs.TabPanel>

        <Tabs.TabPanel value="tasks" label="训练任务">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-semibold">训练任务列表</h3>
            <Button theme="primary" icon={<AddIcon />} onClick={() => setShowCreate(true)}>创建任务</Button>
          </div>
          <Table data={tasks} columns={taskColumns} rowKey="id" bordered />
        </Tabs.TabPanel>

        <Tabs.TabPanel value="nodes" label="节点管理">
          <h3 className="text-lg font-semibold mb-3">参与节点</h3>
          <Table data={nodes} columns={nodeColumns} rowKey="id" bordered />
        </Tabs.TabPanel>

        <Tabs.TabPanel value="models" label="模型仓库">
          <h3 className="text-lg font-semibold mb-3">已训练模型</h3>
          <Table data={models} columns={modelColumns} rowKey="id" bordered />
        </Tabs.TabPanel>
      </Tabs>

      <Dialog header="创建联邦学习任务" visible={showCreate} onClose={() => setShowCreate(false)}
        onConfirm={async () => {
          try { await request.post('/compute/tasks', { ...form, type: 'federated_learning' }); MessagePlugin.success('任务创建成功'); } catch { MessagePlugin.info('演示模式'); }
          setShowCreate(false); fetchData();
        }}>
        <div className="space-y-4">
          <div><label className="block text-sm mb-1">任务名称</label><Input value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="输入任务名称" /></div>
          <div><label className="block text-sm mb-1">算法类型</label><Select options={ALGORITHMS} value={form.algorithm} onChange={(v) => setForm({ ...form, algorithm: v as string })} /></div>
          <div><label className="block text-sm mb-1">训练轮次</label><Input type="number" value={String(form.rounds)} onChange={(v) => setForm({ ...form, rounds: Number(v) })} /></div>
          <div><label className="block text-sm mb-1">学习率</label><Input value={String(form.learning_rate)} onChange={(v) => setForm({ ...form, learning_rate: Number(v) })} /></div>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default FederatedLearningPage;
