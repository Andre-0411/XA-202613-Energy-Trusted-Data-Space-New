/**
 * AI Agent 智能助手页面
 * 左右分栏：Agent列表 + 对话区域
 */
import React, { useState, useEffect, useRef } from 'react';
import { Button, Input, Tag, Avatar, Divider, MessagePlugin } from 'tdesign-react';
import { SendIcon, AddIcon, SearchIcon, ChatIcon } from 'tdesign-icons-react';
import request from '@/api/request';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';

interface Agent {
  id: string;
  name: string;
  description: string;
  avatar_emoji?: string;
  status: string;
  model?: string;
  capabilities?: string[];
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

const QUICK_COMMANDS = [
  { label: '数据查询', icon: '🔍', prompt: '请帮我查询数据资产信息' },
  { label: '安全分析', icon: '🛡️', prompt: '请对当前系统进行安全分析' },
  { label: '合规检查', icon: '✅', prompt: '请执行合规性检查' },
  { label: '性能报告', icon: '📊', prompt: '请生成系统性能报告' },
];

const AgentChatPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [homeBreadcrumb, { label: 'AI 智能助手' }];
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [searchText, setSearchText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchAgents(); }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchAgents = async () => {
    try {
      const res: any = await request.get('/agent/agents', { params: { page: 1, page_size: 50 } });
      const data = res?.data || res;
      const list = data?.items || data?.agents || data || [];
      setAgents(Array.isArray(list) ? list : []);
      if (list.length > 0) setSelectedAgent(list[0]);
    } catch {
      // Demo agents
      const demoAgents: Agent[] = [
        { id: '1', name: '数据管家', description: '智能数据查询与分析助手', avatar_emoji: '📊', status: 'active', model: 'GPT-4', capabilities: ['数据查询', '报表生成'] },
        { id: '2', name: '安全卫士', description: '系统安全监控与威胁检测', avatar_emoji: '🛡️', status: 'active', model: 'Security-LLM', capabilities: ['安全分析', '威胁检测'] },
        { id: '3', name: '合规官', description: '数据合规性审查与隐私保护', avatar_emoji: '✅', status: 'active', model: 'Compliance-LLM', capabilities: ['合规检查', '隐私评估'] },
        { id: '4', name: '运维助手', description: '系统运维与故障诊断', avatar_emoji: '🔧', status: 'idle', model: 'Ops-LLM', capabilities: ['故障诊断', '性能优化'] },
      ];
      setAgents(demoAgents);
      setSelectedAgent(demoAgents[0]);
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || !selectedAgent || sending) return;
    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: content.trim(), timestamp: new Date().toLocaleTimeString('zh-CN') };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setSending(true);
    try {
      const res: any = await request.post(`/agent/agents/${selectedAgent.id}/chat`, { message: content.trim() });
      const data = res?.data || res;
      const aiMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'assistant', content: data?.reply || data?.message || data?.content || '收到您的请求，正在处理中...', timestamp: new Date().toLocaleTimeString('zh-CN') };
      setMessages(prev => [...prev, aiMsg]);
    } catch (error: any) {
      const errorMsg = error?.message || '网络错误，请稍后重试';
      const aiMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'assistant', content: `抱歉，消息发送失败：${errorMsg}`, timestamp: new Date().toLocaleTimeString('zh-CN') };
      setMessages(prev => [...prev, aiMsg]);
    } finally {
      setSending(false);
    }
  };

  const filteredAgents = agents.filter(a => !searchText || a.name.includes(searchText) || a.description.includes(searchText));

  return (
    <PageContainer>
      <PageHeader title="AI 智能助手" breadcrumbs={breadcrumbs} />
      <div className="flex gap-0 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" style={{ height: 'calc(100vh - 180px)' }}>
        {/* 左侧 Agent 列表 */}
        <div className="w-72 border-r border-gray-200 flex flex-col bg-gray-50">
          <div className="p-3 border-b border-gray-200">
            <Input prefixIcon={<SearchIcon />} placeholder="搜索 Agent..." value={searchText} onChange={setSearchText} size="small" />
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {filteredAgents.map(agent => (
              <div key={agent.id} onClick={() => { setSelectedAgent(agent); setMessages([]); }}
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${selectedAgent?.id === agent.id ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-100'}`}>
                <span className="text-2xl">{agent.avatar_emoji || '🤖'}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{agent.name}</div>
                  <div className="text-xs text-gray-400 truncate">{agent.description}</div>
                </div>
                <Tag size="small" theme={agent.status === 'active' ? 'success' : 'default'} variant="light">{agent.status === 'active' ? '在线' : '离线'}</Tag>
              </div>
            ))}
          </div>
          <div className="p-2 border-t border-gray-200">
            <Button block icon={<AddIcon />} variant="outline" size="small">新建 Agent</Button>
          </div>
        </div>

        {/* 右侧 对话区域 */}
        <div className="flex-1 flex flex-col">
          {/* Agent 信息栏 */}
          {selectedAgent && (
            <div className="flex items-center gap-3 px-5 py-3 border-b border-gray-200 bg-white">
              <span className="text-2xl">{selectedAgent.avatar_emoji || '🤖'}</span>
              <div className="flex-1">
                <div className="font-semibold">{selectedAgent.name}</div>
                <div className="text-xs text-gray-400">{selectedAgent.description} · 模型: {selectedAgent.model || 'default'}</div>
              </div>
              <div className="flex gap-1">
                {(selectedAgent.capabilities || []).map((cap, i) => <Tag key={i} size="small" variant="light">{cap}</Tag>)}
              </div>
            </div>
          )}

          {/* 消息区域 */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <ChatIcon size="48px" className="mb-4" />
                <p className="text-lg font-medium mb-2">开始与 {selectedAgent?.name || 'Agent'} 对话</p>
                <p className="text-sm mb-6">选择下方快捷指令或直接输入问题</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {QUICK_COMMANDS.map(cmd => (
                    <Button key={cmd.label} size="small" variant="outline" onClick={() => sendMessage(cmd.prompt)}>
                      {cmd.icon} {cmd.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex items-end gap-2 max-w-[70%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <span className="text-xl">{msg.role === 'user' ? '👤' : (selectedAgent?.avatar_emoji || '🤖')}</span>
                  <div className={`px-4 py-2.5 ${msg.role === 'user' ? 'bg-[#165DFF] text-white' : 'bg-white text-gray-800 border border-gray-200'}`} style={{ borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px' }}>
                    <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                    <div className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>{msg.timestamp}</div>
                  </div>
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="flex items-end gap-2">
                  <span className="text-xl">{selectedAgent?.avatar_emoji || '🤖'}</span>
                  <div className="px-4 py-3 bg-white border border-gray-200 rounded-2xl">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 快捷指令 + 输入框 */}
          <div className="border-t border-gray-200 bg-white">
            <div className="flex gap-2 px-4 py-2 border-b border-gray-100">
              {QUICK_COMMANDS.map(cmd => (
                <Button key={cmd.label} size="small" variant="text" onClick={() => sendMessage(cmd.prompt)}>
                  {cmd.icon} {cmd.label}
                </Button>
              ))}
            </div>
            <div className="flex items-center gap-2 p-3">
              <Input value={inputValue} onChange={setInputValue} placeholder={`向 ${selectedAgent?.name || 'Agent'} 提问...`}
                onPressEnter={() => sendMessage(inputValue)} size="large" className="flex-1" />
              <Button theme="primary" icon={<SendIcon />} loading={sending} disabled={!inputValue.trim()} onClick={() => sendMessage(inputValue)} size="large">
                发送
              </Button>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  );
};

export default AgentChatPage;
