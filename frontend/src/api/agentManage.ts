/**
 * AI Agent 管理 API
 * 知识库管理、模型配置、Agent 参数调节
 */
import request from './request';
import type { ApiResponse } from '@/types/api';

// ==================== 类型定义 ====================

/** 知识库 */
export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  category: string;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  document_count: number;
  total_tokens: number;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

/** 创建知识库请求 */
export interface KnowledgeBaseCreate {
  name: string;
  description?: string;
  category?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  metadata?: Record<string, unknown>;
}

/** 更新知识库请求 */
export interface KnowledgeBaseUpdate {
  name?: string;
  description?: string;
  category?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  metadata?: Record<string, unknown>;
}

/** 文档 */
export interface Document {
  id: string;
  knowledge_base_id: string;
  title: string;
  content_type: string;
  chunk_count: number;
  token_count: number;
  status: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

/** 上传文档请求 */
export interface DocumentUpload {
  title: string;
  content: string;
  content_type?: string;
  metadata?: Record<string, unknown>;
}

/** 模型配置 */
export interface ModelConfig {
  provider: string;
  model_name: string;
  api_key_set: boolean;
  base_url: string;
  max_tokens: number;
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  metadata: Record<string, unknown>;
}

/** 模型配置更新请求 */
export interface ModelConfigUpdate {
  provider?: string;
  model_name?: string;
  api_key?: string;
  base_url?: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  metadata?: Record<string, unknown>;
}

/** Agent 配置 */
export interface AgentConfig {
  agent_type: string;
  name: string;
  description: string;
  system_prompt: string;
  knowledge_base_ids: string[];
  knowledge_base_names: string[];
  model_config: ModelConfig;
  enabled: boolean;
  total_queries: number;
  avg_response_time: number;
  last_used_at: string | null;
  metadata: Record<string, unknown>;
}

/** Agent 配置更新请求 */
export interface AgentConfigUpdate {
  agent_type: string;
  name?: string;
  description?: string;
  system_prompt?: string;
  knowledge_base_ids?: string[];
  model_config?: ModelConfigUpdate;
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}

/** Agent 统计数据 */
export interface AgentStats {
  total_agents: number;
  active_agents: number;
  total_knowledge_bases: number;
  total_documents: number;
  total_queries_today: number;
  avg_response_time: number;
  model_provider: string;
  model_name: string;
}

/** 分页响应 */
interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ==================== API 函数 ====================

// ---------- 统计数据 ----------

/** 获取 Agent 统计数据 */
export function getAgentStats() {
  return request.get<any, ApiResponse<AgentStats>>('/agents/stats');
}

// ---------- Agent 配置 ----------

/** 获取所有 Agent 配置 */
export function listAgentConfigs() {
  return request.get<any, ApiResponse<AgentConfig[]>>('/agents/configs');
}

/** 获取指定 Agent 配置 */
export function getAgentConfig(agentType: string) {
  return request.get<any, ApiResponse<AgentConfig>>(`/agents/configs/${agentType}`);
}

/** 更新 Agent 配置 */
export function updateAgentConfig(agentType: string, data: AgentConfigUpdate) {
  return request.put<any, ApiResponse<AgentConfig>>(`/agents/configs/${agentType}`, data);
}

// ---------- 模型配置 ----------

/** 获取模型配置 */
export function getModelConfig() {
  return request.get<any, ApiResponse<ModelConfig>>('/agents/model-config');
}

/** 更新模型配置 */
export function updateModelConfig(data: ModelConfigUpdate) {
  return request.put<any, ApiResponse<ModelConfig>>('/agents/model-config', data);
}

// ---------- 知识库管理 ----------

/** 获取知识库列表 */
export function listKnowledgeBases(params?: { category?: string; page?: number; page_size?: number }) {
  return request.get<any, ApiResponse<PaginatedData<KnowledgeBase>>>('/agents/knowledge-bases', { params });
}

/** 创建知识库 */
export function createKnowledgeBase(data: KnowledgeBaseCreate) {
  return request.post<any, ApiResponse<KnowledgeBase>>('/agents/knowledge-bases', data);
}

/** 获取知识库详情 */
export function getKnowledgeBase(kbId: string) {
  return request.get<any, ApiResponse<KnowledgeBase>>(`/agents/knowledge-bases/${kbId}`);
}

/** 更新知识库 */
export function updateKnowledgeBase(kbId: string, data: KnowledgeBaseUpdate) {
  return request.put<any, ApiResponse<KnowledgeBase>>(`/agents/knowledge-bases/${kbId}`, data);
}

/** 删除知识库 */
export function deleteKnowledgeBase(kbId: string) {
  return request.delete<any, ApiResponse<null>>(`/agents/knowledge-bases/${kbId}`);
}

// ---------- 文档管理 ----------

/** 获取知识库文档列表 */
export function listDocuments(kbId: string, params?: { page?: number; page_size?: number }) {
  return request.get<any, ApiResponse<PaginatedData<Document>>>(`/agents/knowledge-bases/${kbId}/documents`, { params });
}

/** 添加文档到知识库 */
export function addDocument(kbId: string, data: DocumentUpload) {
  return request.post<any, ApiResponse<Document>>(`/agents/knowledge-bases/${kbId}/documents`, data);
}

/** 删除文档 */
export function deleteDocument(kbId: string, docId: string) {
  return request.delete<any, ApiResponse<null>>(`/agents/knowledge-bases/${kbId}/documents/${docId}`);
}
