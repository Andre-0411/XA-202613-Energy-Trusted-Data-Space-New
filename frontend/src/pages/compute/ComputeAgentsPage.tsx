/**
 * 计算代理页面
 * 4 个 Agent 卡片：查询/交易/安全/调度代理
 * 对话式交互界面（Chat UI） + 历史记录列表
 */
import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { Button, Input, Tag, Divider } from 'tdesign-react';
import {
  SendIcon, RefreshIcon, SearchIcon, SwapIcon, ShieldErrorIcon,
  TimeIcon, HistoryIcon, Screen4KIcon, UserIcon, CheckCircleFilledIcon,
  TrendingUpIcon, TimeFilledIcon,
} from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  queryAgent, tradeAgent, securityAgent, dispatchAgent, getAgentHistory,
  queryAgentStream, tradeAgentStream, securityAgentStream, dispatchAgentStream,
} from '@/api/compute';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import type { ApiResponse } from '@/types/api';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

/** Agent 类型定义 */
interface AgentDef {
  type: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  mutationFn: (data: { query: string; context?: Record<string, unknown> }) => Promise<ApiResponse<Record<string, unknown>>>;
  streamFn: (data: { query: string; context?: Record<string, unknown> }) => AsyncGenerator<{ type: string; content?: string; conversation_id?: string; agent_type?: string; agent_name?: string }, void, unknown>;
}

/** 聊天消息 */
interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
}

/** Agent 定义列表 */
const AGENTS: AgentDef[] = [
  {
    type: 'query', label: '查询代理', description: '智能数据查询，支持自然语言转 SQL',
    icon: <SearchIcon />, color: '#2196f3',
    mutationFn: queryAgent as unknown as AgentDef['mutationFn'],
    streamFn: queryAgentStream as unknown as AgentDef['streamFn'],
  },
  {
    type: 'trade', label: '交易代理', description: '数据交易撮合与定价建议',
    icon: <SwapIcon />, color: '#4caf50',
    mutationFn: tradeAgent as unknown as AgentDef['mutationFn'],
    streamFn: tradeAgentStream as unknown as AgentDef['streamFn'],
  },
  {
    type: 'security', label: '安全代理', description: '安全策略审查与风险预警',
    icon: <ShieldErrorIcon />, color: '#f44336',
    mutationFn: securityAgent as unknown as AgentDef['mutationFn'],
    streamFn: securityAgentStream as unknown as AgentDef['streamFn'],
  },
  {
    type: 'dispatch', label: '调度代理', description: '任务调度优化与资源分配',
    icon: <TimeIcon />, color: '#ff9800',
    mutationFn: dispatchAgent as unknown as AgentDef['mutationFn'],
    streamFn: dispatchAgentStream as unknown as AgentDef['streamFn'],
  },
];

/** Agent 卡片组件 */
const AgentCard: React.FC<{ agent: AgentDef; isSelected: boolean; onClick: () => void }> = ({ agent, isSelected, onClick }) => (
  <div
    onClick={onClick}
    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${isSelected ? 'bg-opacity-10' : 'border-gray-200 hover:border-gray-300'}`}
    style={{ borderColor: isSelected ? agent.color : undefined, backgroundColor: isSelected ? `${agent.color}10` : undefined }}
  >
    <div className="flex items-center gap-3">
      <div className="flex items-center justify-center w-10 h-10 rounded-full text-white" style={{ backgroundColor: agent.color }}>
        {agent.icon}
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-800">{agent.label}</p>
        <p className="text-xs text-gray-500">{agent.description}</p>
      </div>
    </div>
  </div>
);

let msgIdCounter = 0;
const getNextMsgId = () => `msg-${++msgIdCounter}`;

const ComputeAgentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const chatEndRef = useRef<HTMLDivElement>(null);

  // ===== ECharts 配置 =====
  const agentUsageOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['查询代理', '交易代理', '安全代理', '调度代理'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '调用次数' },
    series: [
      { name: '查询代理', type: 'bar', data: [800, 950, 1100, 1250, 1400, 1550, 1700], itemStyle: { color: '#2196f3' } },
      { name: '交易代理', type: 'bar', data: [400, 480, 550, 620, 700, 780, 850], itemStyle: { color: '#4caf50' } },
      { name: '安全代理', type: 'bar', data: [300, 350, 400, 450, 500, 550, 600], itemStyle: { color: '#f44336' } },
      { name: '调度代理', type: 'bar', data: [200, 240, 280, 320, 360, 400, 450], itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  const agentTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [{
      name: '代理类型', type: 'pie', radius: ['40%', '70%'], center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: [
        { value: 5200, name: '查询代理', itemStyle: { color: '#2196f3' } },
        { value: 3800, name: '交易代理', itemStyle: { color: '#4caf50' } },
        { value: 2100, name: '安全代理', itemStyle: { color: '#f44336' } },
        { value: 1400, name: '调度代理', itemStyle: { color: '#ff9800' } },
      ],
    }],
  }), []);

  // ===== 状态 =====
  const [selectedAgent, setSelectedAgent] = useState<string>('query');
  const [chatHistories, setChatHistories] = useState<Record<string, ChatMessage[]>>({
    query: [], trade: [], security: [], dispatch: [],
  });
  const [inputText, setInputText] = useState<string>('');
  const [activeTab, setActiveTab] = useState<number>(0);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingContent, setStreamingContent] = useState<string>('');

  // ===== 当前 Agent =====
  const currentAgent = useMemo(
    () => AGENTS.find((a) => a.type === selectedAgent) ?? AGENTS[0],
    [selectedAgent],
  );

  const currentMessages = useMemo(
    () => chatHistories[selectedAgent] ?? [],
    [selectedAgent, chatHistories],
  );

  // ===== 历史记录查询 =====
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['agentHistory', selectedAgent],
    queryFn: () => getAgentHistory(selectedAgent, { page: 1, page_size: 20 }),
    enabled: activeTab === 1,
  });

  const historyItems = historyData?.data?.items ?? [];

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalQueries: historyItems.length,
    activeAgents: 4,
    successRate: 98.5,
    todayQueries: historyItems.filter((item: Record<string, unknown>) => {
      const today = new Date().toDateString();
      return new Date(item.created_at as string).toDateString() === today;
    }).length,
  }), [historyItems]);

  // ===== 发送消息（SSE 流式） =====
  const handleSend = useCallback(async () => {
    if (!inputText.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: getNextMsgId(), role: 'user', content: inputText, timestamp: new Date().toISOString(),
    };
    setChatHistories((prev) => ({
      ...prev,
      [selectedAgent]: [...(prev[selectedAgent] ?? []), userMsg],
    }));

    const queryText = inputText;
    setInputText('');
    setIsStreaming(true);
    setStreamingContent('');

    const placeholderMsg: ChatMessage = {
      id: getNextMsgId(), role: 'agent', content: '', timestamp: new Date().toISOString(),
    };
    setChatHistories((prev) => ({
      ...prev,
      [selectedAgent]: [...(prev[selectedAgent] ?? []), placeholderMsg],
    }));

    try {
      let fullContent = '';
      const stream = currentAgent.streamFn({ query: queryText });

      for await (const chunk of stream) {
        if (chunk.type === 'chunk' && chunk.content) {
          fullContent += chunk.content;
          setStreamingContent(fullContent);
          setChatHistories((prev) => {
            const messages = prev[selectedAgent] ?? [];
            const lastIdx = messages.length - 1;
            if (lastIdx >= 0 && messages[lastIdx].id === placeholderMsg.id) {
              const updated = [...messages];
              updated[lastIdx] = { ...updated[lastIdx], content: fullContent };
              return { ...prev, [selectedAgent]: updated };
            }
            return prev;
          });
        } else if (chunk.type === 'done') {
          break;
        }
      }
    } catch (error) {
      console.error('SSE 流式请求失败:', error);
      setChatHistories((prev) => {
        const messages = prev[selectedAgent] ?? [];
        const lastIdx = messages.length - 1;
        if (lastIdx >= 0 && messages[lastIdx].id === placeholderMsg.id) {
          const updated = [...messages];
          updated[lastIdx] = { ...updated[lastIdx], content: '抱歉，请求处理失败，请稍后重试。' };
          return { ...prev, [selectedAgent]: updated };
        }
        return prev;
      });
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
    }
  }, [inputText, selectedAgent, currentAgent, isStreaming]);

  // ===== 自动滚动到底部 =====
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessages]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '计算代理' }],
    [],
  );

  return (
    <div className="flex flex-col gap-4 h-full">
      <style>{`@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }`}</style>
      <PageHeader
        title="计算代理"
        subtitle="AI 代理辅助数据查询、交易撮合、安全审查和任务调度"
        breadcrumbs={breadcrumbs}
        iconActions={[{
          icon: <RefreshIcon />,
          onClick: () => queryClient.invalidateQueries({ queryKey: ['agentHistory'] }),
          tooltip: '刷新',
        }]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: <Screen4KIcon size="28px" />, value: stats.totalQueries, label: '总查询数', color: '#667eea' },
          { icon: <CheckCircleFilledIcon size="28px" />, value: stats.activeAgents, label: '活跃代理', color: '#43e97b' },
          { icon: <TrendingUpIcon size="28px" />, value: `${stats.successRate}%`, label: '成功率', color: '#4facfe' },
          { icon: <TimeFilledIcon size="28px" />, value: stats.todayQueries, label: '今日查询', color: '#fa709a' },
        ].map((card) => (
          <div key={card.label} className="rounded-xl text-white p-4 shadow-sm" style={{ background: `linear-gradient(135deg, ${card.color} 0%, ${card.color}88 100%)` }}>
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-white/20">{card.icon}</div>
              <div><p className="text-2xl font-bold">{card.value}</p><p className="text-sm opacity-80">{card.label}</p></div>
            </div>
          </div>
        ))}
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-xl bg-white border border-gray-200 p-4">
          <h3 className="text-base font-semibold text-gray-800 mb-2">代理使用趋势</h3>
          <ReactECharts option={agentUsageOption} style={{ height: 300 }} />
        </div>
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <h3 className="text-base font-semibold text-gray-800 mb-2">代理类型分布</h3>
          <ReactECharts option={agentTypeOption} style={{ height: 300 }} />
        </div>
      </div>

      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* 左侧 Agent 卡片列表 */}
        <div className="w-[280px] flex-shrink-0 rounded-xl bg-white border border-gray-200 p-4 overflow-auto">
          <h3 className="text-sm font-bold text-gray-700 mb-2">可用代理</h3>
          <Divider />
          <div className="flex flex-col gap-3 mt-3">
            {AGENTS.map((agent) => (
              <AgentCard key={agent.type} agent={agent} isSelected={selectedAgent === agent.type} onClick={() => setSelectedAgent(agent.type)} />
            ))}
          </div>
        </div>

        {/* 右侧交互区 */}
        <div className="flex-1 rounded-xl bg-white border border-gray-200 flex flex-col overflow-hidden">
          {/* 标签切换 */}
          <div className="flex border-b border-gray-200 px-4">
            {[
              { label: '对话', icon: <Screen4KIcon size="16px" /> },
              { label: '历史记录', icon: <HistoryIcon size="16px" /> },
            ].map((tab, idx) => (
              <button
                key={tab.label}
                onClick={() => setActiveTab(idx)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === idx ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
              >
                {tab.icon}{tab.label}
              </button>
            ))}
          </div>

          {/* 对话 Tab */}
          {activeTab === 0 && (
            <>
              <div className="flex-1 overflow-auto p-4">
                {currentMessages.length === 0 ? (
                  <div className="flex flex-col items-center gap-3 pt-12">
                    <div className="w-16 h-16 rounded-full flex items-center justify-center text-white" style={{ backgroundColor: currentAgent.color }}>
                      {currentAgent.icon}
                    </div>
                    <h3 className="text-lg font-semibold">{currentAgent.label}</h3>
                    <p className="text-sm text-gray-500 text-center max-w-[400px]">
                      {currentAgent.description}。请在下方输入框输入您的问题或指令。
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    {currentMessages.map((msg) => (
                      <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'agent' && (
                          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white flex-shrink-0" style={{ backgroundColor: currentAgent.color }}>
                            {currentAgent.icon}
                          </div>
                        )}
                        <div className={`p-3 rounded-xl max-w-[70%] ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-800'}`}>
                          <p className={`text-sm whitespace-pre-wrap ${msg.role === 'agent' ? 'font-mono text-xs' : ''}`}>
                            {msg.content}
                            {isStreaming && msg.id === currentMessages[currentMessages.length - 1]?.id && (
                              <span style={{ animation: 'blink 1s infinite' }}>▌</span>
                            )}
                          </p>
                          <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-blue-100' : 'text-gray-400'}`}>
                            {new Date(msg.timestamp).toLocaleTimeString('zh-CN')}
                          </p>
                        </div>
                        {msg.role === 'user' && (
                          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-300 text-white flex-shrink-0">
                            <UserIcon size="16px" />
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={chatEndRef} />
                  </div>
                )}
              </div>

              {/* 输入区 */}
              <div className="p-4 border-t border-gray-200">
                <div className="flex gap-2">
                  <Input
                    value={inputText}
                    onChange={setInputText}
                    placeholder={`向${currentAgent.label}发送消息...`}
                    disabled={isStreaming}
                    onKeydown={(_val, { e }) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    style={{ flex: 1 }}
                  />
                  <Button theme="primary" onClick={handleSend} disabled={!inputText.trim() || isStreaming} icon={<SendIcon />} />
                </div>
              </div>
            </>
          )}

          {/* 历史记录 Tab */}
          {activeTab === 1 && (
            <div className="flex-1 overflow-auto p-4">
              {historyLoading ? (
                <p className="text-gray-400 text-center pt-12">加载中...</p>
              ) : historyItems.length === 0 ? (
                <p className="text-gray-400 text-center pt-12">暂无历史记录</p>
              ) : (
                <div className="flex flex-col gap-3">
                  {historyItems.map((item: Record<string, unknown>, idx: number) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <Tag>{String(item.type ?? 'query')}</Tag>
                        <span className="text-xs text-gray-400">
                          {item.timestamp ? new Date(String(item.timestamp)).toLocaleString('zh-CN') : ''}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-700">
                        {String(item.query ?? item.request ?? item.task ?? '')}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <LoadingOverlay open={isStreaming} message="AI 代理正在思考..." />
    </div>
  );
};

export default ComputeAgentsPage;
