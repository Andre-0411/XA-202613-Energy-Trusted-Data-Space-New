/**
 * AI Agent 智能助手页面
 * 左右分栏：Agent列表 + 对话区域
 * 支持技能学习和自动调用
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button, Input, Tag, Avatar, Divider, MessagePlugin, Tooltip, Loading } from 'tdesign-react';
import { SendIcon, AddIcon, SearchIcon, ChatIcon, BookIcon } from 'tdesign-icons-react';
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
  skillUsed?: string;
  intentType?: string;
}

interface SkillMatch {
  id: string;
  name: string;
  description: string;
  score: number;
  category: string;
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
  const [matchedSkills, setMatchedSkills] = useState<SkillMatch[]>([]);
  const [learningMode, setLearningMode] = useState(false);
  const [skillStats, setSkillStats] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchAgents(); fetchSkillStats(); }, []);

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
    } catch (error) {
      console.error('Failed to fetch agents:', error);
      setAgents([]);
    }
  };

  const fetchSkillStats = async () => {
    try {
      const res: any = await request.get('/agent-skills/statistics');
      const data = res?.data || res;
      setSkillStats(data);
    } catch (error) {
      console.error('Failed to fetch skill stats:', error);
    }
  };

  // 分析用户意图并匹配技能
  const analyzeIntent = async (message: string) => {
    try {
      const res: any = await request.post('/agent-skills/process', { message });
      const data = res?.data || res;
      
      if (data.matched_skills && data.matched_skills.length > 0) {
        setMatchedSkills(data.matched_skills);
        return data.matched_skills[0]; // 返回最佳匹配
      }
    } catch (error) {
      console.error('Intent analysis failed:', error);
    }
    return null;
  };

  // 学习新技能
  const learnFromInteraction = async (userInput: string, assistantResponse: string) => {
    if (!learningMode) return;
    
    try {
      const res: any = await request.post('/agent-skills/learn', {
        user_input: userInput,
        assistant_response: assistantResponse,
      });
      const data = res?.data || res;
      
      if (data.learned) {
        MessagePlugin.success(`已学习新技能：${data.skill?.skill_name || '未知'}`);
        fetchSkillStats(); // 刷新统计
      }
    } catch (error) {
      console.error('Learning failed:', error);
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || !selectedAgent || sending) return;
    
    const userMsg: ChatMessage = { 
      id: Date.now().toString(), 
      role: 'user', 
      content: content.trim(), 
      timestamp: new Date().toLocaleTimeString('zh-CN') 
    };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setSending(true);
    
    try {
      // 1. 先分析意图，查找匹配技能
      const matchedSkill = await analyzeIntent(content.trim());
      
      let responseContent = '';
      let skillUsed = '';
      let intentType = '';
      
      // 2. 如果有匹配的高置信度技能，尝试执行
      if (matchedSkill && matchedSkill.score > 0.6) {
        try {
          const execRes: any = await request.post('/agent-skills/execute', {
            skill_id: matchedSkill.id,
            user_input: content.trim(),
          });
          const execData = execRes?.data || execRes;
          
          if (execData.success) {
            responseContent = execData.output || '技能执行完成';
            skillUsed = matchedSkill.name;
            intentType = matchedSkill.category;
          }
        } catch {
          // 技能执行失败，回退到普通对话
        }
      }
      
      // 3. 如果没有技能执行结果，调用Agent对话
      if (!responseContent) {
        const res: any = await request.post(`/agent/agents/${selectedAgent.id}/chat`, { 
          message: content.trim(),
          context: {
            matched_skills: matchedSkills.map(s => s.name),
            learning_mode: learningMode,
          }
        });
        const data = res?.data || res;
        responseContent = data?.reply || data?.message || data?.content || '收到您的请求，正在处理中...';
        intentType = 'general';
      }
      
      const aiMsg: ChatMessage = { 
        id: (Date.now() + 1).toString(), 
        role: 'assistant', 
        content: responseContent,
        timestamp: new Date().toLocaleTimeString('zh-CN'),
        skillUsed,
        intentType,
      };
      setMessages(prev => [...prev, aiMsg]);
      
      // 4. 如果开启学习模式，从交互中学习
      await learnFromInteraction(content.trim(), responseContent);
      
    } catch (error: any) {
      const errorMsg = error?.message || '网络错误，请稍后重试';
      const aiMsg: ChatMessage = { 
        id: (Date.now() + 1).toString(), 
        role: 'assistant', 
        content: `抱歉，消息发送失败：${errorMsg}`, 
        timestamp: new Date().toLocaleTimeString('zh-CN') 
      };
      setMessages(prev => [...prev, aiMsg]);
    } finally {
      setSending(false);
      setMatchedSkills([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
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
          
          {/* 技能统计 */}
          {skillStats && (
            <div className="p-3 border-t border-gray-200 bg-blue-50">
              <div className="text-xs font-medium text-blue-700 mb-2">📚 技能库</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>总技能: {skillStats.total_skills || 0}</div>
                <div>学习中: {skillStats.by_source?.learned || 0}</div>
              </div>
            </div>
          )}
          
          <div className="p-2 border-t border-gray-200">
            <Button 
              block 
              icon={learningMode ? '🧠' : <BookIcon />}
              variant={learningMode ? 'base' : 'outline'} 
              size="small"
              theme={learningMode ? 'primary' : 'default'}
              onClick={() => setLearningMode(!learningMode)}
            >
              {learningMode ? '学习模式: 开启' : '学习模式: 关闭'}
            </Button>
          </div>
        </div>

        {/* 右侧 对话区域 */}
        <div className="flex-1 flex flex-col">
          {/* Agent 信息栏 */}
          {selectedAgent && (
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{selectedAgent.avatar_emoji || '🤖'}</span>
                <div>
                  <div className="font-semibold">{selectedAgent.name}</div>
                  <div className="text-xs text-gray-500">{selectedAgent.description}</div>
                </div>
                {selectedAgent.model && <Tag size="small" variant="outline">{selectedAgent.model}</Tag>}
              </div>
              <div className="flex items-center gap-2">
                {learningMode && (
                  <Tag size="small" theme="warning" variant="light">
                    🧠 学习模式
                  </Tag>
                )}
                <Tag size="small" theme="success" variant="light">在线</Tag>
              </div>
            </div>
          )}

          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <ChatIcon size="48px" className="mb-4" />
                <p className="text-lg font-medium">开始对话</p>
                <p className="text-sm mt-2">选择一个 Agent 开始交流，或使用快捷指令</p>
                <div className="flex gap-2 mt-4">
                  {QUICK_COMMANDS.map(cmd => (
                    <Button key={cmd.label} variant="outline" size="small" onClick={() => sendMessage(cmd.prompt)}>
                      {cmd.icon} {cmd.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-800'}`}>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  <div className={`text-xs mt-1 ${msg.role === 'user' ? 'text-blue-100' : 'text-gray-400'}`}>
                    {msg.timestamp}
                    {msg.skillUsed && (
                      <span className="ml-2">🔧 使用技能: {msg.skillUsed}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl px-4 py-3">
                  <Loading size="small" />
                  <span className="ml-2 text-gray-500">思考中...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 匹配的技能提示 */}
          {matchedSkills.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-100 bg-blue-50">
              <div className="text-xs text-blue-600 mb-1">🎯 匹配到 {matchedSkills.length} 个技能:</div>
              <div className="flex gap-2">
                {matchedSkills.slice(0, 3).map(skill => (
                  <Tag key={skill.id} size="small" theme="primary" variant="light">
                    {skill.name} ({Math.round(skill.score * 100)}%)
                  </Tag>
                ))}
              </div>
            </div>
          )}

          {/* 输入框 */}
          <div className="p-4 border-t border-gray-200 bg-white">
            <div className="flex items-end gap-2">
              <Input
                value={inputValue}
                onChange={setInputValue}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... (Enter 发送)"
                disabled={sending}
                className="flex-1"
              />
              <Button 
                theme="primary" 
                icon={<SendIcon />} 
                onClick={() => sendMessage(inputValue)} 
                loading={sending}
                disabled={!inputValue.trim()}
              >
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
