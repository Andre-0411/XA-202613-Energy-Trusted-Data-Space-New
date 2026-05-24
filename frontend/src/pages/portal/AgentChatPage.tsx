/**
 * AI Agent 聊天页面
 * 支持自然语言查询、四大Agent切换（查询/交易/安全/调度）
 * Markdown回复、工具调用结果展示
 */
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Select } from 'tdesign-react';
import {
  SendIcon, SearchIcon, LinkIcon, LockOnIcon, TrendingUpIcon,
  RefreshIcon, ClearIcon, ChatIcon, Robot1Icon, UserIcon,
  CopyIcon, CheckIcon,
} from 'tdesign-icons-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import { PageContainer, PageSection } from '@/components/common';

/* ========== 类型定义 ========== */
interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agentType?: string;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

interface AgentInfo {
  key: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  welcomeMessage: string;
  placeholder: string;
}

/* ========== Agent 配置 ========== */
const AGENTS: AgentInfo[] = [
  {
    key: 'query',
    label: '查询代理',
    description: '数据查询与检索',
    icon: <SearchIcon />,
    color: '#2196f3',
    welcomeMessage: '你好！我是查询代理，可以帮你检索数据目录、查询数据资源、分析数据统计信息。请问你想查询什么？',
    placeholder: '输入查询需求，例如：查询最近一周新增的能源数据...',
  },
  {
    key: 'trade',
    label: '交易代理',
    description: '数据交易与结算',
    icon: <LinkIcon />,
    color: '#4caf50',
    welcomeMessage: '你好！我是交易代理，可以帮你进行数据产品浏览、下单购买、合约管理和交易结算。请问有什么需要？',
    placeholder: '输入交易需求，例如：查看可用的数据产品...',
  },
  {
    key: 'security',
    label: '安全代理',
    description: '安全审计与合规',
    icon: <LockOnIcon />,
    color: '#f44336',
    welcomeMessage: '你好！我是安全代理，可以帮你进行安全策略检查、合规审计、威胁检测和隐私评估。请问需要什么帮助？',
    placeholder: '输入安全需求，例如：检查当前系统的安全状态...',
  },
  {
    key: 'dispatch',
    label: '调度代理',
    description: '资源调度与优化',
    icon: <TrendingUpIcon />,
    color: '#ff9800',
    welcomeMessage: '你好！我是调度代理，可以帮你进行计算任务调度、资源分配、性能优化和负载均衡。请问需要调度什么？',
    placeholder: '输入调度需求，例如：查看当前计算资源使用情况...',
  },
];

/* ========== 模拟回复数据 ========== */
const MOCK_RESPONSES: Record<string, { content: string; toolCalls?: ToolCall[] }[]> = {
  query: [
    {
      content: '根据你的查询，我找到了以下相关数据资源：\n\n## 查询结果\n\n| 数据名称 | 类型 | 更新时间 | 安全等级 |\n|---------|------|---------|----------|\n| 电网负荷数据 | 实时流 | 2026-05-25 | L3 |\n| 新能源发电量 | 日报 | 2026-05-24 | L2 |\n| 气象环境数据 | API | 2026-05-25 | L2 |\n\n共找到 **12** 条匹配记录。',
      toolCalls: [
        { id: 'tc-1', name: 'search_catalog', args: { keyword: '能源数据', time_range: '7d' }, result: '返回12条记录' },
      ],
    },
  ],
  trade: [
    {
      content: '## 可用数据产品\n\n当前市场上有以下热门数据产品：\n\n1. **电力负荷预测数据集** - 价格：500元/月\n2. **新能源出力预测** - 价格：800元/月\n3. **电价走势分析** - 价格：300元/月\n\n需要我帮你下单购买或查看更多详情吗？',
      toolCalls: [
        { id: 'tc-2', name: 'list_products', args: { category: 'energy', sort: 'popular' }, result: '返回3个产品' },
      ],
    },
  ],
  security: [
    {
      content: '## 安全状态报告\n\n当前系统安全状态：**良好** ✅\n\n- 已认证机构：45个\n- 活跃连接器：23个\n- 今日威胁告警：0条\n- 合规状态：等保三级 ✅\n\n所有安全指标均在正常范围内。',
      toolCalls: [
        { id: 'tc-3', name: 'security_scan', args: { scope: 'full' }, result: '扫描完成，无威胁' },
      ],
    },
  ],
  dispatch: [
    {
      content: '## 资源使用情况\n\n当前计算集群状态：\n\n- **CPU使用率**：67%\n- **内存使用率**：54%\n- **GPU使用率**：82%\n- **运行任务**：12个\n- **排队任务**：3个\n\n建议：GPU资源较紧张，可考虑扩容或错峰调度。',
      toolCalls: [
        { id: 'tc-4', name: 'check_resources', args: { cluster: 'main' }, result: '资源状态正常' },
      ],
    },
  ],
};

/* ========== Markdown 简易渲染 ========== */
const SimpleMarkdown: React.FC<{ content: string }> = ({ content }) => {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inTable = false;
  let tableRows: string[][] = [];

  const flushTable = () => {
    if (tableRows.length > 0) {
      const header = tableRows[0];
      const body = tableRows.slice(2); // skip separator
      elements.push(
        <table key={`table-${elements.length}`} className="w-full text-sm border-collapse my-3">
          <thead>
            <tr className="bg-gray-50">
              {header.map((h, i) => (
                <th key={i} className="border border-gray-200 px-3 py-2 text-left font-semibold">{h.trim()}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri} className="hover:bg-gray-50">
                {row.map((cell, ci) => (
                  <td key={ci} className="border border-gray-200 px-3 py-2">{cell.trim()}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>,
      );
      tableRows = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Table detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const cells = trimmed.split('|').filter(c => c.trim() !== '');
      if (cells.length > 0 && !cells.every(c => /^[-:]+$/.test(c.trim()))) {
        if (!inTable) inTable = true;
        tableRows.push(cells);
        return;
      } else if (inTable) {
        tableRows.push(cells);
        return;
      }
    } else if (inTable) {
      flushTable();
      inTable = false;
    }

    // Headers
    if (trimmed.startsWith('## ')) {
      elements.push(<h3 key={idx} className="text-base font-bold mt-4 mb-2 text-gray-800">{trimmed.slice(3)}</h3>);
    } else if (trimmed.startsWith('### ')) {
      elements.push(<h4 key={idx} className="text-sm font-bold mt-3 mb-1 text-gray-700">{trimmed.slice(4)}</h4>);
    } else if (trimmed.startsWith('- **') || trimmed.startsWith('* **')) {
      // Bold list items
      const match = trimmed.match(/^[-*]\s+\*\*(.+?)\*\*\s*[-–]?\s*(.*)$/);
      if (match) {
        elements.push(
          <div key={idx} className="flex gap-2 my-1">
            <span className="text-gray-400">-</span>
            <span><strong className="text-gray-800">{match[1]}</strong>{match[2] && <span className="text-gray-600"> - {match[2]}</span>}</span>
          </div>,
        );
      } else {
        elements.push(<div key={idx} className="ml-4 my-0.5">{renderInline(trimmed.slice(2))}</div>);
      }
    } else if (/^\d+\.\s/.test(trimmed)) {
      // Ordered list
      const match = trimmed.match(/^(\d+)\.\s+\*\*(.+?)\*\*\s*[-–]?\s*(.*)$/);
      if (match) {
        elements.push(
          <div key={idx} className="flex gap-2 my-1">
            <span className="text-gray-500 font-medium">{match[1]}.</span>
            <span><strong className="text-gray-800">{match[2]}</strong>{match[3] && <span className="text-gray-600"> - {match[3]}</span>}</span>
          </div>,
        );
      } else {
        elements.push(<div key={idx} className="ml-4 my-0.5">{renderInline(trimmed)}</div>);
      }
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(<div key={idx} className="flex gap-2 my-0.5"><span className="text-gray-400">-</span><span>{renderInline(trimmed.slice(2))}</span></div>);
    } else if (trimmed === '') {
      elements.push(<div key={idx} className="h-2" />);
    } else {
      elements.push(<p key={idx} className="my-1 leading-relaxed">{renderInline(trimmed)}</p>);
    }
  });

  flushTable();
  return <>{elements}</>;
};

const renderInline = (text: string): React.ReactNode => {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*|`(.+?)`|(.+?)/g;
  let match;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match[1]) parts.push(<strong key={key++} className="text-gray-800">{match[1]}</strong>);
    else if (match[2]) parts.push(<code key={key++} className="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono text-blue-600">{match[2]}</code>);
    else if (match[3]) parts.push(<span key={key++}>{match[3]}</span>);
  }
  return parts.length > 0 ? parts : text;
};

/* ========== 工具调用展示组件 ========== */
const ToolCallDisplay: React.FC<{ toolCall: ToolCall }> = ({ toolCall }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden my-2">
      <button
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-blue-100 flex items-center justify-center">
            <SearchIcon className="text-blue-600" style={{ fontSize: '12px' }} />
          </div>
          <span className="font-medium text-gray-700">{toolCall.name}</span>
          {toolCall.result && <Tag variant="light" size="small" theme="success">完成</Tag>}
        </div>
        <span className="text-gray-400 text-xs">{expanded ? '收起' : '展开'}</span>
      </button>
      {expanded && (
        <div className="px-3 py-2 border-t border-gray-100 text-xs">
          <div className="mb-2">
            <span className="text-gray-500 font-medium">参数：</span>
            <pre className="mt-1 p-2 bg-gray-50 rounded text-gray-600 overflow-x-auto">{JSON.stringify(toolCall.args, null, 2)}</pre>
          </div>
          {toolCall.result && (
            <div>
              <span className="text-gray-500 font-medium">结果：</span>
              <span className="ml-1 text-gray-600">{toolCall.result}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* ========== AgentChatPage 主组件 ========== */
const AgentChatPage: React.FC = () => {
  const [activeAgent, setActiveAgent] = useState<string>('query');
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({
    query: [{
      id: 'welcome-query',
      role: 'assistant',
      content: AGENTS[0].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'query',
    }],
    trade: [{
      id: 'welcome-trade',
      role: 'assistant',
      content: AGENTS[1].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'trade',
    }],
    security: [{
      id: 'welcome-security',
      role: 'assistant',
      content: AGENTS[2].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'security',
    }],
    dispatch: [{
      id: 'welcome-dispatch',
      role: 'assistant',
      content: AGENTS[3].welcomeMessage,
      timestamp: new Date().toISOString(),
      agentType: 'dispatch',
    }],
  });
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const currentAgent = useMemo(() => AGENTS.find(a => a.key === activeAgent)!, [activeAgent]);
  const currentMessages = messages[activeAgent] || [];

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessages]);

  // Copy message content
  const handleCopy = useCallback((id: string, content: string) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  }, []);

  // Send message
  const handleSend = useCallback(() => {
    if (!inputValue.trim() || isTyping) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
      agentType: activeAgent,
    };

    setMessages(prev => ({
      ...prev,
      [activeAgent]: [...(prev[activeAgent] || []), userMsg],
    }));
    setInputValue('');
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = MOCK_RESPONSES[activeAgent] || MOCK_RESPONSES.query;
      const response = responses[Math.floor(Math.random() * responses.length)];

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        agentType: activeAgent,
        toolCalls: response.toolCalls,
      };

      setMessages(prev => ({
        ...prev,
        [activeAgent]: [...(prev[activeAgent] || []), assistantMsg],
      }));
      setIsTyping(false);
    }, 1200);
  }, [inputValue, isTyping, activeAgent]);

  // Clear conversation
  const handleClear = useCallback(() => {
    setMessages(prev => ({
      ...prev,
      [activeAgent]: [{
        id: `welcome-${activeAgent}`,
        role: 'assistant',
        content: currentAgent.welcomeMessage,
        timestamp: new Date().toISOString(),
        agentType: activeAgent,
      }],
    }));
  }, [activeAgent, currentAgent]);

  // Breadcrumbs
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: 'AI 助手' }],
    [],
  );

  return (
    <PageContainer padding="none" bgColor="#f0f2f5">
      <div className="flex flex-col h-[calc(100vh-64px)]">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 sm:px-6 py-3">
          <PageHeader
            title="AI 智能助手"
            subtitle="基于大模型的能源数据空间智能问答服务"
            breadcrumbs={breadcrumbs}
            iconActions={[
              { icon: <RefreshIcon />, onClick: handleClear, tooltip: '清空对话' },
            ]}
          />
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* 左侧 Agent 切换面板 */}
          <div className="w-64 bg-white border-r border-gray-200 flex-shrink-0 hidden md:flex flex-col">
            <div className="p-3 border-b border-gray-100">
              <h4 className="text-sm font-semibold text-gray-700">选择 Agent</h4>
            </div>
            <div className="flex-1 overflow-auto p-2 flex flex-col gap-1">
              {AGENTS.map(agent => (
                <button
                  key={agent.key}
                  className={`flex items-center gap-3 px-3 py-3 rounded-lg transition-all text-left ${
                    activeAgent === agent.key
                      ? 'bg-blue-50 border border-blue-200'
                      : 'hover:bg-gray-50 border border-transparent'
                  }`}
                  onClick={() => setActiveAgent(agent.key)}
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${agent.color}15`, color: agent.color }}
                  >
                    {agent.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={`text-sm font-medium truncate ${activeAgent === agent.key ? 'text-blue-700' : 'text-gray-800'}`}>
                      {agent.label}
                    </div>
                    <div className="text-xs text-gray-500 truncate">{agent.description}</div>
                  </div>
                  {activeAgent === agent.key && (
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>

            {/* Agent 信息 */}
            <div className="p-3 border-t border-gray-100 bg-gray-50">
              <div className="flex items-center gap-2 mb-2">
                <Robot1Icon className="text-gray-400" />
                <span className="text-xs text-gray-500">Agent 信息</span>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div className="flex justify-between">
                  <span>当前Agent</span>
                  <span className="font-medium">{currentAgent.label}</span>
                </div>
                <div className="flex justify-between">
                  <span>对话轮次</span>
                  <span className="font-medium">{Math.floor(currentMessages.length / 2)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* 移动端 Agent 选择 */}
          <div className="md:hidden bg-white border-b border-gray-200 px-3 py-2">
            <Select
              value={activeAgent}
              onChange={(val) => setActiveAgent(val as string)}
              options={AGENTS.map(a => ({ value: a.key, label: a.label }))}
              style={{ width: '100%' }}
            />
          </div>

          {/* 右侧聊天区域 */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* 消息列表 */}
            <div className="flex-1 overflow-auto px-4 sm:px-6 py-4 space-y-4">
              {currentMessages.map((msg) => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-1"
                      style={{ backgroundColor: `${currentAgent.color}15`, color: currentAgent.color }}
                    >
                      {currentAgent.icon}
                    </div>
                  )}

                  <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white rounded-tr-sm'
                          : 'bg-white border border-gray-200 text-gray-700 rounded-tl-sm shadow-sm'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <span>{msg.content}</span>
                      ) : (
                        <SimpleMarkdown content={msg.content} />
                      )}
                    </div>

                    {/* 工具调用 */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="mt-2">
                        {msg.toolCalls.map(tc => (
                          <ToolCallDisplay key={tc.id} toolCall={tc} />
                        ))}
                      </div>
                    )}

                    {/* 消息操作 */}
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-1 mt-1.5 ml-1">
                        <span className="text-xs text-gray-400">
                          {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <Tooltip content={copiedId === msg.id ? '已复制' : '复制'}>
                          <button
                            className="p-1 hover:bg-gray-100 rounded transition-colors"
                            onClick={() => handleCopy(msg.id, msg.content)}
                          >
                            {copiedId === msg.id
                              ? <CheckIcon className="text-green-500" style={{ fontSize: '14px' }} />
                              : <CopyIcon className="text-gray-400" style={{ fontSize: '14px' }} />
                            }
                          </button>
                        </Tooltip>
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
                      <UserIcon className="text-white" style={{ fontSize: '16px' }} />
                    </div>
                  )}
                </div>
              ))}

              {/* Typing indicator */}
              {isTyping && (
                <div className="flex gap-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${currentAgent.color}15`, color: currentAgent.color }}
                  >
                    {currentAgent.icon}
                  </div>
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className="bg-white border-t border-gray-200 px-4 sm:px-6 py-4">
              <div className="flex gap-3 items-end max-w-4xl mx-auto">
                <div className="flex-1 relative">
                  <Input
                    ref={inputRef}
                    value={inputValue}
                    onChange={setInputValue}
                    placeholder={currentAgent.placeholder}
                    onEnter={handleSend}
                    disabled={isTyping}
                    size="large"
                    className="!rounded-xl"
                  />
                </div>
                <Button
                  theme="primary"
                  icon={<SendIcon />}
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isTyping}
                  size="large"
                  className="!rounded-xl !px-5"
                >
                  发送
                </Button>
              </div>
              <div className="text-center mt-2">
                <span className="text-xs text-gray-400">AI 回复仅供参考，重要决策请以官方数据为准</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  );
};

export default AgentChatPage;
