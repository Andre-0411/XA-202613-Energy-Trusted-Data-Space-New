/**
 * AI Agent 管理页面（管理员端）
 * 知识库管理、模型配置、Agent 参数调节、统计概览
 */
import React, { useState, useMemo, useCallback } from 'react';
import { Button, Dialog, Input, Tag, Tooltip, Select, Tabs, Slider, Textarea, MessagePlugin } from 'tdesign-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import LoadingOverlay from '@/components/LoadingOverlay';
import {
  getAgentStats, listAgentConfigs, updateAgentConfig,
  getModelConfig, updateModelConfig,
  listKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase,
  addDocument, listDocuments, deleteDocument,
} from '@/api/agentManage';
import type {
  AgentConfig, AgentConfigUpdate, AgentStats,
  KnowledgeBase, KnowledgeBaseCreate, ModelConfig, ModelConfigUpdate,
  Document, DocumentUpload,
} from '@/api/agentManage';
import { AddIcon, ChevronDownIcon, CloudIcon, ComponentSwitchIcon, DeleteIcon, EditIcon, ErrorCircleFilledIcon, LinkIcon, MemberIcon, Ai1Icon, RefreshIcon, SaveIcon, SearchIcon, ServerIcon, SettingIcon, Robot1Icon, TrendingUpIcon, ViewListIcon } from 'tdesign-icons-react';

/** Agent 类型配置 */
const AGENT_TYPES: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  query: { label: '查询代理', color: '#2196f3', icon: <SearchIcon /> },
  trade: { label: '交易代理', color: '#4caf50', icon: <LinkIcon /> },
  security: { label: '安全代理', color: '#f44336', icon: <SearchIcon /> },
  dispatch: { label: '调度代理', color: '#ff9800', icon: <TrendingUpIcon /> },
};

const AgentManagePage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 状态 =====
  const [activeTab, setActiveTab] = useState<number>(0);
  const [expandedAgent, setExpandedAgent] = useState<string | null>('query');

  // 知识库对话框
  const [kbDialogOpen, setKbDialogOpen] = useState(false);
  const [kbDialogMode, setKbDialogMode] = useState<'create' | 'edit'>('create');
  const [kbFormData, setKbFormData] = useState<KnowledgeBaseCreate>({
    name: '', description: '', category: 'general', embedding_model: 'text-embedding-v2',
    chunk_size: 512, chunk_overlap: 50,
  });
  const [editingKbId, setEditingKbId] = useState<string | null>(null);

  // 文档对话框
  const [docDialogOpen, setDocDialogOpen] = useState(false);
  const [docDialogKbId, setDocDialogKbId] = useState<string>('');
  const [docFormData, setDocFormData] = useState<DocumentUpload>({
    title: '', content: '', content_type: 'text/plain',
  });

  // 文档列表对话框
  const [docListOpen, setDocListOpen] = useState(false);
  const [docListKbId, setDocListKbId] = useState<string>('');
  const [docListKbName, setDocListKbName] = useState<string>('');

  // Agent 配置编辑
  const [editingAgent, setEditingAgent] = useState<string | null>(null);
  const [agentEditData, setAgentEditData] = useState<Partial<AgentConfigUpdate>>({});

  // 模型配置编辑
  const [modelEditData, setModelEditData] = useState<ModelConfigUpdate>({});
  const [modelEditing, setModelEditing] = useState(false);

  // ===== 数据获取 =====
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['agentStats'],
    queryFn: () => getAgentStats(),
  });

  const { data: agentsData, isLoading: agentsLoading } = useQuery({
    queryKey: ['agentConfigs'],
    queryFn: () => listAgentConfigs(),
  });

  const { data: modelData, isLoading: modelLoading } = useQuery({
    queryKey: ['modelConfig'],
    queryFn: () => getModelConfig(),
  });

  const { data: kbData, isLoading: kbLoading } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: () => listKnowledgeBases(),
  });

  const { data: docData } = useQuery({
    queryKey: ['kbDocuments', docListKbId],
    queryFn: () => listDocuments(docListKbId),
    enabled: !!docListKbId && docListOpen,
  });

  const stats = statsData?.data;
  const agents = agentsData?.data ?? [];
  const modelConfig = modelData?.data;
  const knowledgeBases = kbData?.data?.items ?? [];
  const documents = docData?.data?.items ?? [];

  // ===== ECharts 配置 =====
  const agentUsageChart = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: agents.map(a => a.name), top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: { type: 'value', name: '查询次数' },
    series: agents.map((a) => ({
      name: a.name,
      type: 'line',
      smooth: true,
      data: [
        Math.floor(a.total_queries * 0.1),
        Math.floor(a.total_queries * 0.15),
        Math.floor(a.total_queries * 0.12),
        Math.floor(a.total_queries * 0.18),
        Math.floor(a.total_queries * 0.2),
        Math.floor(a.total_queries * 0.13),
        Math.floor(a.total_queries * 0.12),
      ],
      areaStyle: { opacity: 0.1 },
      itemStyle: { color: AGENT_TYPES[a.agent_type]?.color || '#999' },
    })),
  }), [agents]);

  const knowledgeBaseChart = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [{
      name: '知识库文档',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      data: knowledgeBases.map((kb, i) => ({
        value: kb.document_count,
        name: kb.name,
        itemStyle: { color: ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4'][i % 6] },
      })),
    }],
  }), [knowledgeBases]);

  // ===== Mutations =====
  const updateAgentMutation = useMutation({
    mutationFn: ({ agentType, data }: { agentType: string; data: AgentConfigUpdate }) =>
      updateAgentConfig(agentType, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agentConfigs'] });
      queryClient.invalidateQueries({ queryKey: ['agentStats'] });
      MessagePlugin.success('Agent 配置已更新');
      setEditingAgent(null);
    },
    onError: () => {
      MessagePlugin.error('更新失败，请重试');
    },
  });

  const updateModelMutation = useMutation({
    mutationFn: (data: ModelConfigUpdate) => updateModelConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modelConfig'] });
      MessagePlugin.success('模型配置已更新');
      setModelEditing(false);
    },
    onError: () => {
      MessagePlugin.error('更新失败，请重试');
    },
  });

  const createKbMutation = useMutation({
    mutationFn: (data: KnowledgeBaseCreate) => createKnowledgeBase(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
      queryClient.invalidateQueries({ queryKey: ['agentStats'] });
      MessagePlugin.success('知识库创建成功');
      setKbDialogOpen(false);
    },
    onError: () => {
      MessagePlugin.error('创建失败，请重试');
    },
  });

  const updateKbMutation = useMutation({
    mutationFn: ({ kbId, data }: { kbId: string; data: Partial<KnowledgeBaseCreate> }) =>
      updateKnowledgeBase(kbId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
      MessagePlugin.success('知识库已更新');
      setKbDialogOpen(false);
    },
    onError: () => {
      MessagePlugin.error('更新失败，请重试');
    },
  });

  const deleteKbMutation = useMutation({
    mutationFn: (kbId: string) => deleteKnowledgeBase(kbId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
      queryClient.invalidateQueries({ queryKey: ['agentStats'] });
      MessagePlugin.success('知识库已删除');
    },
    onError: () => {
      MessagePlugin.error('删除失败，请检查是否有关联的 Agent');
    },
  });

  const addDocMutation = useMutation({
    mutationFn: ({ kbId, data }: { kbId: string; data: DocumentUpload }) => addDocument(kbId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
      queryClient.invalidateQueries({ queryKey: ['kbDocuments'] });
      queryClient.invalidateQueries({ queryKey: ['agentStats'] });
      MessagePlugin.success('文档添加成功');
      setDocDialogOpen(false);
    },
    onError: () => {
      MessagePlugin.error('添加失败，请重试');
    },
  });

  const deleteDocMutation = useMutation({
    mutationFn: ({ kbId, docId }: { kbId: string; docId: string }) => deleteDocument(kbId, docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
      queryClient.invalidateQueries({ queryKey: ['kbDocuments'] });
      queryClient.invalidateQueries({ queryKey: ['agentStats'] });
      MessagePlugin.success('文档已删除');
    },
    onError: () => {
      MessagePlugin.error('删除失败，请重试');
    },
  });

  // ===== 事件处理 =====
  const handleOpenCreateKb = useCallback(() => {
    setKbDialogMode('create');
    setKbFormData({ name: '', description: '', category: 'general', embedding_model: 'text-embedding-v2', chunk_size: 512, chunk_overlap: 50 });
    setKbDialogOpen(true);
  }, []);

  const handleOpenEditKb = useCallback((kb: KnowledgeBase) => {
    setKbDialogMode('edit');
    setEditingKbId(kb.id);
    setKbFormData({
      name: kb.name,
      description: kb.description,
      category: kb.category,
      embedding_model: kb.embedding_model,
      chunk_size: kb.chunk_size,
      chunk_overlap: kb.chunk_overlap,
    });
    setKbDialogOpen(true);
  }, []);

  const handleSaveKb = useCallback(() => {
    if (!kbFormData.name.trim()) {
      MessagePlugin.error('请输入知识库名称');
      return;
    }
    if (kbDialogMode === 'create') {
      createKbMutation.mutate(kbFormData);
    } else if (editingKbId) {
      updateKbMutation.mutate({ kbId: editingKbId, data: kbFormData });
    }
  }, [kbFormData, kbDialogMode, editingKbId, createKbMutation, updateKbMutation]);

  const handleDeleteKb = useCallback((kbId: string) => {
    if (window.confirm('确定要删除此知识库吗？此操作不可恢复。')) {
      deleteKbMutation.mutate(kbId);
    }
  }, [deleteKbMutation]);

  const handleOpenAddDoc = useCallback((kbId: string) => {
    setDocDialogKbId(kbId);
    setDocFormData({ title: '', content: '', content_type: 'text/plain' });
    setDocDialogOpen(true);
  }, []);

  const handleSaveDoc = useCallback(() => {
    if (!docFormData.title.trim() || !docFormData.content.trim()) {
      MessagePlugin.error('请输入文档标题和内容');
      return;
    }
    addDocMutation.mutate({ kbId: docDialogKbId, data: docFormData });
  }, [docFormData, docDialogKbId, addDocMutation]);

  const handleOpenDocList = useCallback((kb: KnowledgeBase) => {
    setDocListKbId(kb.id);
    setDocListKbName(kb.name);
    setDocListOpen(true);
  }, []);

  const handleStartEditAgent = useCallback((agent: AgentConfig) => {
    setEditingAgent(agent.agent_type);
    setAgentEditData({
      agent_type: agent.agent_type,
      name: agent.name,
      description: agent.description,
      system_prompt: agent.system_prompt,
      knowledge_base_ids: [...agent.knowledge_base_ids],
      enabled: agent.enabled,
    });
  }, []);

  const handleSaveAgent = useCallback(() => {
    if (!editingAgent) return;
    updateAgentMutation.mutate({ agentType: editingAgent, data: agentEditData as AgentConfigUpdate });
  }, [editingAgent, agentEditData, updateAgentMutation]);

  const handleToggleAgent = useCallback((agent: AgentConfig) => {
    updateAgentMutation.mutate({
      agentType: agent.agent_type,
      data: { agent_type: agent.agent_type, enabled: !agent.enabled },
    });
  }, [updateAgentMutation]);

  const handleSaveModelConfig = useCallback(() => {
    updateModelMutation.mutate(modelEditData);
  }, [modelEditData, updateModelMutation]);

  const handleStartEditModel = useCallback(() => {
    if (modelConfig) {
      setModelEditData({
        provider: modelConfig.provider,
        model_name: modelConfig.model_name,
        base_url: modelConfig.base_url,
        max_tokens: modelConfig.max_tokens,
        temperature: modelConfig.temperature,
        top_p: modelConfig.top_p,
        frequency_penalty: modelConfig.frequency_penalty,
        presence_penalty: modelConfig.presence_penalty,
      });
    }
    setModelEditing(true);
  }, [modelConfig]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: 'AI Agent 管理' }],
    [],
  );

  return (
    <PageContainer>
      <PageHeader
        title="AI Agent 管理"
        subtitle="管理 AI 代理配置、知识库、模型参数，打造智能数据服务能力"
        breadcrumbs={breadcrumbs}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => {
              queryClient.invalidateQueries({ queryKey: ['agentStats'] });
              queryClient.invalidateQueries({ queryKey: ['agentConfigs'] });
              queryClient.invalidateQueries({ queryKey: ['modelConfig'] });
              queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
            },
            tooltip: '刷新数据',
          },
        ]}
      />

      {/* ========== 统计卡片 ========== */}
      <StatGrid columns={4} className="mb-4">
        <MetricsCard title="Agent 总数" value={stats?.total_agents ?? 0} icon={<Robot1Icon />} color="primary" />
        <MetricsCard title="知识库" value={stats?.total_knowledge_bases ?? 0} icon={<ServerIcon />} color="info" />
        <MetricsCard title="文档数" value={stats?.total_documents ?? 0} icon={<ViewListIcon />} color="success" />
        <MetricsCard title="今日查询" value={stats?.total_queries_today ?? 0} icon={<TrendingUpIcon />} color="warning" />
      </StatGrid>

      {/* ========== 图表 ========== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="md:col-span-2"><ChartCard title="Agent 使用趋势" option={agentUsageChart} height={300} /></div>
        <ChartCard title="知识库文档分布" option={knowledgeBaseChart} height={300} loading={knowledgeBases.length === 0} />
      </div>

      {/* ========== Tab 切换 ========== */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm">
        <Tabs
          value={activeTab}
          onChange={(v) => setActiveTab(v as number)}
        >
          {/* ========== Tab 1: Agent 配置 ========== */}
          <Tabs.TabPanel value={0} label="Agent 配置">
            <div className="p-4">
              {agentsLoading ? (
                <LoadingOverlay open />
              ) : (
                <div className="flex flex-col gap-3">
                  {agents.map((agent) => {
                    const agentType = AGENT_TYPES[agent.agent_type] || { label: agent.agent_type, color: '#999', icon: <Robot1Icon /> };
                    const isEditing = editingAgent === agent.agent_type;
                    const isExpanded = expandedAgent === agent.agent_type;

                    return (
                      <div key={agent.agent_type} className="rounded-xl border border-gray-200 shadow-sm">
                        {/* Agent 头部 - 可点击展开/收起 */}
                        <div
                          className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50"
                          onClick={() => setExpandedAgent(isExpanded ? null : agent.agent_type)}
                        >
                          <div className="w-10 h-10 rounded-full flex items-center justify-center text-white" style={{ backgroundColor: agentType.color }}>
                            {agentType.icon}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-base font-semibold">{agent.name}</span>
                              <Tag
                                content={agent.enabled ? '已启用' : '已禁用'}
                                theme={agent.enabled ? 'success' : 'default'}
                                size="small"
                              />
                            </div>
                            <span className="text-xs text-gray-600">{agent.description}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <Tooltip content={agent.enabled ? '点击禁用' : '点击启用'}>
                              <span
                                className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"
                                onClick={(e) => { e.stopPropagation(); handleToggleAgent(agent); }}
                              >
                                {agent.enabled ? <ComponentSwitchIcon style={{ color: '#4caf50' }} /> : <ComponentSwitchIcon style={{ color: '#999' }} />}
                              </span>
                            </Tooltip>
                            <span className="text-xs text-gray-500">{agent.total_queries} 次查询</span>
                            <span className="text-xs text-gray-500">{agent.avg_response_time.toFixed(0)}ms</span>
                            <ChevronDownIcon className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                          </div>
                        </div>

                        {/* Agent 详情 - 展开内容 */}
                        {isExpanded && (
                          <div className="px-4 pb-4 border-t border-gray-100">
                            {isEditing ? (
                              <div className="flex flex-col gap-4 pt-4">
                                <div>
                                  <span className="text-sm text-gray-500 mb-1 block">Agent 名称</span>
                                  <Input
                                    value={agentEditData.name || ''}
                                    onChange={(val) => setAgentEditData(prev => ({ ...prev, name: val }))}
                                  />
                                </div>
                                <div>
                                  <span className="text-sm text-gray-500 mb-1 block">描述</span>
                                  <Input
                                    value={agentEditData.description || ''}
                                    onChange={(val) => setAgentEditData(prev => ({ ...prev, description: val }))}
                                  />
                                </div>
                                <div>
                                  <span className="text-sm text-gray-500 mb-1 block">系统提示词</span>
                                  <Textarea
                                    value={agentEditData.system_prompt || ''}
                                    onChange={(val) => setAgentEditData(prev => ({ ...prev, system_prompt: val }))}
                                    rows={6}
                                    placeholder="定义 Agent 的行为和能力..."
                                  />
                                </div>
                                <div>
                                  <span className="text-sm text-gray-500 mb-1 block">关联知识库</span>
                                  <Select
                                    multiple
                                    value={agentEditData.knowledge_base_ids || []}
                                    onChange={(val) => setAgentEditData(prev => ({
                                      ...prev,
                                      knowledge_base_ids: val as string[],
                                    }))}
                                    options={knowledgeBases.map(kb => ({
                                      label: `${kb.name} (${kb.document_count} 文档)`,
                                      value: kb.id,
                                    }))}
                                    style={{ width: '100%' }}
                                  />
                                </div>
                                <div className="flex items-center gap-2">
                                  <Button
                                    theme="primary"
                                    icon={<SaveIcon />}
                                    onClick={handleSaveAgent}
                                  >
                                    保存
                                  </Button>
                                  <Button
                                    variant="outline"
                                    onClick={() => setEditingAgent(null)}
                                  >
                                    取消
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <div className="flex flex-col gap-4 pt-4">
                                <div>
                                  <span className="text-sm text-gray-500 mb-1 block">系统提示词</span>
                                  <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
                                    <span className="text-xs text-gray-700 whitespace-pre-wrap">
                                      {agent.system_prompt}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex flex-wrap gap-6">
                                  <div>
                                    <span className="text-sm text-gray-500 mb-1 block">关联知识库</span>
                                    {agent.knowledge_base_names.length > 0 ? (
                                      <div className="flex flex-wrap gap-1">
                                        {agent.knowledge_base_names.map(name => (
                                          <Tag key={name} content={name} variant="outline" />
                                        ))}
                                      </div>
                                    ) : (
                                      <span className="text-xs text-gray-600">未关联</span>
                                    )}
                                  </div>
                                  <div>
                                    <span className="text-sm text-gray-500 mb-1 block">模型</span>
                                    <span className="text-xs text-gray-700">{agent.model_config.model_name}</span>
                                  </div>
                                  <div>
                                    <span className="text-sm text-gray-500 mb-1 block">温度</span>
                                    <span className="text-xs text-gray-700">{agent.model_config.temperature}</span>
                                  </div>
                                  <div>
                                    <span className="text-sm text-gray-500 mb-1 block">最大 Token</span>
                                    <span className="text-xs text-gray-700">{agent.model_config.max_tokens}</span>
                                  </div>
                                </div>
                                <Button
                                  variant="outline"
                                  icon={<EditIcon />}
                                  onClick={() => handleStartEditAgent(agent)}
                                >
                                  编辑配置
                                </Button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </Tabs.TabPanel>

          {/* ========== Tab 2: 模型设置 ========== */}
          <Tabs.TabPanel value={1} label="模型设置">
            <div className="p-4">
              {modelLoading ? (
                <LoadingOverlay open />
              ) : modelConfig ? (
                <div className="flex flex-col gap-4">
                  {/* 模型信息卡片 */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="rounded-xl bg-white border border-gray-200 p-4 flex flex-col items-center gap-2">
                      <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                        <Ai1Icon style={{ fontSize: '1.5rem', color: '#2196f3' }} />
                      </div>
                      <h3 className="text-base font-semibold text-gray-800">{modelConfig.provider.toUpperCase()}</h3>
                      <span className="text-xs text-gray-600">{modelConfig.model_name}</span>
                      <Tag
                        content={modelConfig.api_key_set ? 'API Key 已配置' : 'API Key 未配置'}
                        theme={modelConfig.api_key_set ? 'success' : 'warning'}
                      />
                    </div>
                    <div className="md:col-span-2 rounded-xl bg-white border border-gray-200 p-4">
                      <span className="text-base font-semibold mb-3 block">运行状态</span>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <span className="text-xs text-gray-500">平均响应时间</span>
                          <h2 className="text-xl font-semibold text-gray-800">{stats?.avg_response_time?.toFixed(0) ?? '-'}ms</h2>
                        </div>
                        <div>
                          <span className="text-xs text-gray-500">今日查询总数</span>
                          <h2 className="text-xl font-semibold text-gray-800">{stats?.total_queries_today ?? '-'}</h2>
                        </div>
                        <div>
                          <span className="text-xs text-gray-500">活跃 Agent</span>
                          <h2 className="text-xl font-semibold text-gray-800">{stats?.active_agents ?? '-'}</h2>
                        </div>
                        <div>
                          <span className="text-xs text-gray-500">API Base URL</span>
                          <span className="text-xs text-gray-700 break-all">{modelConfig.base_url}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 参数调节 */}
                  <div className="rounded-xl bg-white border border-gray-200 p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-base font-semibold text-gray-800">模型参数调节</h3>
                      {!modelEditing ? (
                        <Button variant="outline" icon={<EditIcon />} onClick={handleStartEditModel}>
                          编辑参数
                        </Button>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Button
                            theme="primary"
                            icon={<SaveIcon />}
                            onClick={handleSaveModelConfig}
                          >
                            保存
                          </Button>
                          <Button variant="outline" onClick={() => setModelEditing(false)}>取消</Button>
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                      <div>
                        <span className="text-sm text-gray-700 mb-2 block">Temperature: {modelEditing ? modelEditData.temperature : modelConfig.temperature}</span>
                        <Slider
                          value={modelEditing ? (modelEditData.temperature ?? 0.7) : modelConfig.temperature}
                          onChange={(v) => modelEditing && setModelEditData(prev => ({ ...prev, temperature: v as number }))}
                          min={0}
                          max={2}
                          step={0.1}
                          marks={{ 0: '0', 1: '1', 2: '2' }}
                          disabled={!modelEditing}
                        />
                        <span className="text-xs text-gray-400 mt-1 block">值越高回答越随机多样，值越低回答越确定精确</span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-700 mb-2 block">Top P: {modelEditing ? modelEditData.top_p : modelConfig.top_p}</span>
                        <Slider
                          value={modelEditing ? (modelEditData.top_p ?? 0.9) : modelConfig.top_p}
                          onChange={(v) => modelEditing && setModelEditData(prev => ({ ...prev, top_p: v as number }))}
                          min={0}
                          max={1}
                          step={0.05}
                          marks={{ 0: '0', 0.5: '0.5', 1: '1' }}
                          disabled={!modelEditing}
                        />
                        <span className="text-xs text-gray-400 mt-1 block">核采样阈值，控制输出多样性</span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-500 mb-1 block">Max Tokens</span>
                        <Input
                          type="number"
                          value={String(modelEditing ? (modelEditData.max_tokens ?? 2048) : modelConfig.max_tokens)}
                          onChange={(val) => modelEditing && setModelEditData(prev => ({ ...prev, max_tokens: Number(val) }))}
                          disabled={!modelEditing}
                        />
                        <span className="text-xs text-gray-400 mt-1 block">最大输出 Token 数 (256-32768)</span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-500 mb-1 block">Frequency Penalty</span>
                        <Input
                          type="number"
                          value={String(modelEditing ? (modelEditData.frequency_penalty ?? 0) : modelConfig.frequency_penalty)}
                          onChange={(val) => modelEditing && setModelEditData(prev => ({ ...prev, frequency_penalty: Number(val) }))}
                          disabled={!modelEditing}
                        />
                        <span className="text-xs text-gray-400 mt-1 block">频率惩罚 (-2.0 ~ 2.0)</span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-500 mb-1 block">Presence Penalty</span>
                        <Input
                          type="number"
                          value={String(modelEditing ? (modelEditData.presence_penalty ?? 0) : modelConfig.presence_penalty)}
                          onChange={(val) => modelEditing && setModelEditData(prev => ({ ...prev, presence_penalty: Number(val) }))}
                          disabled={!modelEditing}
                        />
                        <span className="text-xs text-gray-400 mt-1 block">存在惩罚 (-2.0 ~ 2.0)</span>
                      </div>
                      {modelEditing && (
                        <>
                          <div>
                            <span className="text-sm text-gray-500 mb-1 block">模型提供商</span>
                            <Select
                              value={modelEditData.provider || 'deepseek'}
                              onChange={(val) => setModelEditData(prev => ({ ...prev, provider: val as string }))}
                              options={[
                                { label: 'DeepSeek', value: 'deepseek' },
                                { label: 'OpenAI', value: 'openai' },
                                { label: '智谱 AI', value: 'zhipu' },
                                { label: '通义千问', value: 'qwen' },
                              ]}
                            />
                          </div>
                          <div>
                            <span className="text-sm text-gray-500 mb-1 block">模型名称</span>
                            <Input
                              value={modelEditData.model_name || ''}
                              onChange={(val) => setModelEditData(prev => ({ ...prev, model_name: val }))}
                            />
                          </div>
                          <div>
                            <span className="text-sm text-gray-500 mb-1 block">API Base URL</span>
                            <Input
                              value={modelEditData.base_url || ''}
                              onChange={(val) => setModelEditData(prev => ({ ...prev, base_url: val }))}
                            />
                          </div>
                          <div>
                            <span className="text-sm text-gray-500 mb-1 block">API Key</span>
                            <Input
                              type="password"
                              value={(modelEditData as Record<string, unknown>).api_key as string || ''}
                              onChange={(val) => setModelEditData(prev => ({ ...prev, api_key: val }))}
                              placeholder="留空则不修改"
                            />
                            <span className="text-xs text-gray-400 mt-1 block">注意：API Key 更新后需重启服务生效</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-4 text-center text-orange-500">无法加载模型配置</div>
              )}
            </div>
          </Tabs.TabPanel>

          {/* ========== Tab 3: 知识库 ========== */}
          <Tabs.TabPanel value={2} label="知识库">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-gray-800">知识库管理</h3>
                <Button
                  theme="primary"
                  icon={<AddIcon />}
                  onClick={handleOpenCreateKb}
                >
                  创建知识库
                </Button>
              </div>

              {kbLoading ? (
                <LoadingOverlay open />
              ) : knowledgeBases.length === 0 ? (
                <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-8 text-center">
                  <ServerIcon style={{ fontSize: '3rem', color: '#ccc' }} />
                  <h3 className="text-base font-semibold text-gray-800 mt-3">暂无知识库</h3>
                  <span className="text-xs text-gray-600 block mt-1 mb-4">
                    创建知识库后可以向其中添加文档，AI Agent 将利用知识库提供更精准的回答
                  </span>
                  <Button variant="outline" icon={<AddIcon />} onClick={handleOpenCreateKb}>
                    创建第一个知识库
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {knowledgeBases.map((kb) => (
                    <div key={kb.id} className="rounded-xl bg-white border border-gray-200 shadow-sm">
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-base font-semibold">{kb.name}</span>
                            <Tag content={kb.category} variant="outline" size="small" />
                          </div>
                          <Tag
                            content={kb.status === 'active' ? '活跃' : kb.status}
                            theme={kb.status === 'active' ? 'success' : 'default'}
                            size="small"
                          />
                        </div>
                        <span className="text-xs text-gray-600 block mb-3">
                          {kb.description || '暂无描述'}
                        </span>
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <span className="text-xs text-gray-500 block">文档数</span>
                            <span className="text-sm font-medium">{kb.document_count}</span>
                          </div>
                          <div>
                            <span className="text-xs text-gray-500 block">Token 数</span>
                            <span className="text-sm font-medium">{kb.total_tokens.toLocaleString()}</span>
                          </div>
                          <div>
                            <span className="text-xs text-gray-500 block">分块大小</span>
                            <span className="text-sm font-medium">{kb.chunk_size}</span>
                          </div>
                        </div>
                      </div>
                      <hr className="border-gray-200" />
                      <div className="flex items-center gap-1 p-3">
                        <Button size="small" icon={<ViewListIcon />} onClick={() => handleOpenDocList(kb)}>
                          文档
                        </Button>
                        <Button size="small" icon={<AddIcon />} onClick={() => handleOpenAddDoc(kb.id)}>
                          添加
                        </Button>
                        <Button size="small" icon={<EditIcon />} onClick={() => handleOpenEditKb(kb)}>
                          编辑
                        </Button>
                        <Button size="small" theme="danger" icon={<DeleteIcon />} onClick={() => handleDeleteKb(kb.id)}>
                          删除
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Tabs.TabPanel>
        </Tabs>
      </div>

      {/* ========== 知识库创建/编辑对话框 ========== */}
      <Dialog visible={kbDialogOpen} onClose={() => setKbDialogOpen(false)} header={kbDialogMode === 'create' ? '创建知识库' : '编辑知识库'} width="560px">
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-sm text-gray-500 mb-1 block">知识库名称 <span className="text-red-500">*</span></span>
            <Input
              value={kbFormData.name}
              onChange={(val) => setKbFormData(prev => ({ ...prev, name: val }))}
            />
          </div>
          <div>
            <span className="text-sm text-gray-500 mb-1 block">描述</span>
            <Textarea
              value={kbFormData.description || ''}
              onChange={(val) => setKbFormData(prev => ({ ...prev, description: val }))}
              rows={2}
            />
          </div>
          <div>
            <span className="text-sm text-gray-500 mb-1 block">分类</span>
            <Select
              value={kbFormData.category || 'general'}
              onChange={(val) => setKbFormData(prev => ({ ...prev, category: val as string }))}
              options={[
                { label: '通用', value: 'general' },
                { label: '能源', value: 'energy' },
                { label: '交易', value: 'trade' },
                { label: '安全', value: 'security' },
                { label: '调度', value: 'dispatch' },
              ]}
            />
          </div>
          <div>
            <span className="text-sm text-gray-500 mb-1 block">向量化模型</span>
            <Input
              value={kbFormData.embedding_model || 'text-embedding-v2'}
              onChange={(val) => setKbFormData(prev => ({ ...prev, embedding_model: val }))}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-500 mb-1 block">分块大小</span>
              <Input
                type="number"
                value={String(kbFormData.chunk_size || 512)}
                onChange={(val) => setKbFormData(prev => ({ ...prev, chunk_size: Number(val) }))}
              />
              <span className="text-xs text-gray-400 mt-1 block">64-2048</span>
            </div>
            <div>
              <span className="text-sm text-gray-500 mb-1 block">分块重叠</span>
              <Input
                type="number"
                value={String(kbFormData.chunk_overlap || 50)}
                onChange={(val) => setKbFormData(prev => ({ ...prev, chunk_overlap: Number(val) }))}
              />
              <span className="text-xs text-gray-400 mt-1 block">0-500</span>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button onClick={() => setKbDialogOpen(false)}>取消</Button>
          <Button theme="primary" onClick={handleSaveKb}>
            {kbDialogMode === 'create' ? '创建' : '保存'}
          </Button>
        </div>
      </Dialog>

      {/* ========== 添加文档对话框 ========== */}
      <Dialog visible={docDialogOpen} onClose={() => setDocDialogOpen(false)} header="添加文档" width="560px">
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-sm text-gray-500 mb-1 block">文档标题 <span className="text-red-500">*</span></span>
            <Input
              value={docFormData.title}
              onChange={(val) => setDocFormData(prev => ({ ...prev, title: val }))}
            />
          </div>
          <div>
            <span className="text-sm text-gray-500 mb-1 block">内容类型</span>
            <Select
              value={docFormData.content_type || 'text/plain'}
              onChange={(val) => setDocFormData(prev => ({ ...prev, content_type: val as string }))}
              options={[
                { label: '纯文本', value: 'text/plain' },
                { label: 'Markdown', value: 'text/markdown' },
                { label: 'JSON', value: 'application/json' },
              ]}
            />
          </div>
          <div>
            <span className="text-sm text-gray-500 mb-1 block">文档内容 <span className="text-red-500">*</span></span>
            <Textarea
              value={docFormData.content}
              onChange={(val) => setDocFormData(prev => ({ ...prev, content: val }))}
              rows={10}
              placeholder="粘贴文档内容..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button onClick={() => setDocDialogOpen(false)}>取消</Button>
          <Button theme="primary" onClick={handleSaveDoc}>添加</Button>
        </div>
      </Dialog>

      {/* ========== 文档列表对话框 ========== */}
      <Dialog visible={docListOpen} onClose={() => setDocListOpen(false)} header={`${docListKbName} - 文档列表`} width="800px">
        <div className="flex justify-end mb-3">
          <Button
            theme="primary"
            icon={<AddIcon />}
            size="small"
            onClick={() => { setDocListOpen(false); handleOpenAddDoc(docListKbId); }}
          >
            添加文档
          </Button>
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-8">
            <ViewListIcon style={{ fontSize: '2rem', color: '#ccc' }} />
            <span className="text-gray-500 block mt-2">暂无文档</span>
          </div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-bold">标题</th>
                  <th className="px-4 py-3 text-left font-bold">类型</th>
                  <th className="px-4 py-3 text-right font-bold">分块数</th>
                  <th className="px-4 py-3 text-right font-bold">Token 数</th>
                  <th className="px-4 py-3 text-left font-bold">状态</th>
                  <th className="px-4 py-3 text-right font-bold">操作</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">{doc.title}</td>
                    <td className="px-4 py-3">{doc.content_type}</td>
                    <td className="px-4 py-3 text-right">{doc.chunk_count}</td>
                    <td className="px-4 py-3 text-right">{doc.token_count.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <Tag
                        content={doc.status === 'indexed' ? '已索引' : doc.status}
                        theme={doc.status === 'indexed' ? 'success' : 'warning'}
                        size="small"
                      />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-red-500"
                        onClick={() => deleteDocMutation.mutate({ kbId: docListKbId, docId: doc.id })}
                      >
                        <DeleteIcon />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={() => setDocListOpen(false)}>关闭</Button>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default AgentManagePage;
