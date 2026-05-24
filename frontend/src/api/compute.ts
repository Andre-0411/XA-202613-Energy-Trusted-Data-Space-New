/**
 * 可信计算 API
 * 任务 / DAG / 联邦学习 / MPC / TEE / 同态加密 / 差分隐私 / 沙箱 / AI Agent
 */
import request from './request';
import { getAccessToken } from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  ComputeTask, TaskSignature, DagDefinition, FlModel, Sandbox, CryptoResult,
  ClusterNode, ClusterStatus, RegisterNodeRequest, DispatchTaskRequest,
  BenchmarkResult, BenchmarkSummary, BenchmarkTrendPoint,
  PrivacyRouteResult, PrivacyTechnology, PrivacyScenario,
} from '@/types/api';

// ==================== 计算任务 ====================

export function listTasks(params?: PaginatedRequest & { task_type?: string; status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ComputeTask>>>('/compute/tasks', { params });
}

export function createTask(data: Partial<ComputeTask>) {
  return request.post<any, ApiResponse<ComputeTask>>('/compute/tasks', data);
}

export function getTask(id: string) {
  return request.get<any, ApiResponse<ComputeTask>>(`/compute/tasks/${id}`);
}

export function updateTask(id: string, data: Partial<ComputeTask>) {
  return request.put<any, ApiResponse<ComputeTask>>(`/compute/tasks/${id}`, data);
}

export function startTask(id: string) {
  return request.post<any, ApiResponse<null>>(`/compute/tasks/${id}/start`);
}

export function stopTask(id: string) {
  return request.post<any, ApiResponse<null>>(`/compute/tasks/${id}/stop`);
}

export function getTaskResult(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/compute/tasks/${id}/result`);
}

export function signTask(id: string, data: { signer_did: string; signature: string }) {
  return request.post<any, ApiResponse<null>>(`/compute/tasks/${id}/sign`, data);
}

export function getTaskSignatures(id: string) {
  return request.get<any, ApiResponse<TaskSignature[]>>(`/compute/tasks/${id}/signatures`);
}

// ==================== DAG ====================

export function listDags(params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<DagDefinition>>>('/compute/dag', { params });
}

export function createDag(data: Partial<DagDefinition>) {
  return request.post<any, ApiResponse<DagDefinition>>('/compute/dag', data);
}

export function getDag(id: string) {
  return request.get<any, ApiResponse<DagDefinition>>(`/compute/dag/${id}`);
}

export function updateDag(id: string, data: Partial<DagDefinition>) {
  return request.put<any, ApiResponse<DagDefinition>>(`/compute/dag/${id}`, data);
}

export function executeDag(id: string) {
  return request.post<any, ApiResponse<Record<string, unknown>>>(`/compute/dag/${id}/execute`);
}

// ==================== 联邦学习 ====================

export function submitFlTraining(data: { algorithm: string; dataset_ids: string[]; params?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<ComputeTask>>('/compute/fl/train', data);
}

export function listFlModels(params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<FlModel>>>('/compute/fl/models', { params });
}

export function getFlModel(id: string) {
  return request.get<any, ApiResponse<FlModel>>(`/compute/fl/models/${id}`);
}

export function evaluateFlModel(id: string) {
  return request.post<any, ApiResponse<Record<string, number>>>(`/compute/fl/models/${id}/evaluate`);
}

// ==================== MPC ====================

export function submitMpcComputation(data: { protocol: string; parties: string[]; config: Record<string, unknown> }) {
  return request.post<any, ApiResponse<ComputeTask>>('/compute/mpc/compute', data);
}

export function listMpcProtocols() {
  return request.get<any, ApiResponse<string[]>>('/compute/mpc/protocols');
}

// ==================== TEE ====================

export function executeInTee(data: { runtime: string; algorithm: string; config: Record<string, unknown> }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/tee/execute', data);
}

export function getTeeStatus(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/compute/tee/status/${id}`);
}

// ==================== 同态加密 ====================

export function heEncrypt(data: { scheme: string; public_key: string; plaintext: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/compute/he/encrypt', data);
}

export function heCompute(data: { scheme: string; operation: string; ciphertexts: string[] }) {
  return request.post<any, ApiResponse<CryptoResult>>('/compute/he/compute', data);
}

// ==================== 差分隐私 ====================

export function applyDp(data: { mechanism: string; config: Record<string, unknown> }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/dp/apply', data);
}

export function listDpConfigs() {
  return request.get<any, ApiResponse<Record<string, unknown>[]>>('/compute/dp/configs');
}

// ==================== 沙箱 ====================

export function listSandboxes(params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<Sandbox>>>('/compute/sandbox', { params });
}

export function createSandbox(data: Partial<Sandbox>) {
  return request.post<any, ApiResponse<Sandbox>>('/compute/sandbox', data);
}

export function getSandbox(id: string) {
  return request.get<any, ApiResponse<Sandbox>>(`/compute/sandbox/${id}`);
}

export function deleteSandbox(id: string) {
  return request.delete<any, ApiResponse<null>>(`/compute/sandbox/${id}`);
}

export function scanSandboxAlgorithm(id: string) {
  return request.post<any, ApiResponse<Record<string, unknown>>>(`/compute/sandbox/${id}/scan`);
}

export function exportSandboxAudit(id: string) {
  return request.post<any, ApiResponse<Record<string, unknown>>>(`/compute/sandbox/${id}/export`);
}

// ==================== AI Agent ====================

export function queryAgent(data: { query: string; context?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/agents/query', data);
}

export function tradeAgent(data: { request: string; context?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/agents/trade', data);
}

export function securityAgent(data: { query: string; context?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/agents/security', data);
}

export function dispatchAgent(data: { task: string; context?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/agents/dispatch', data);
}

export function getAgentHistory(agentType: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<Record<string, unknown>>>>(`/compute/agents/history`, { params: { agent_type: agentType, ...params } });
}

// ==================== AI Agent SSE 流式 ====================

const SSE_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/** SSE 流式请求通用函数 */
async function* streamAgentResponse(
  endpoint: string,
  data: Record<string, unknown>,
): AsyncGenerator<{ type: string; content?: string; conversation_id?: string; agent_type?: string; agent_name?: string }, void, unknown> {
  const token = getAccessToken();
  const response = await fetch(`${SSE_BASE_URL}/compute/agents/${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`SSE 请求失败: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法获取响应流');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6).trim();
            if (jsonStr) {
              const parsed = JSON.parse(jsonStr);
              yield parsed;
            }
          } catch (e) {
            console.warn('SSE JSON 解析失败:', line, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/** QueryAgent SSE 流式 */
export function queryAgentStream(data: { query: string; context?: Record<string, unknown> }) {
  return streamAgentResponse('query/stream', data);
}

/** TradeAgent SSE 流式 */
export function tradeAgentStream(data: { request: string; context?: Record<string, unknown> }) {
  return streamAgentResponse('trade/stream', data);
}

/** SecurityAgent SSE 流式 */
export function securityAgentStream(data: { query: string; context?: Record<string, unknown> }) {
  return streamAgentResponse('security/stream', data);
}

/** DispatchAgent SSE 流式 */
export function dispatchAgentStream(data: { task: string; context?: Record<string, unknown> }) {
  return streamAgentResponse('dispatch/stream', data);
}

// ==================== 计算集群 ====================

export function getClusterNodes(params?: PaginatedRequest & { status?: string; node_type?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ClusterNode>>>('/compute/cluster/nodes', { params });
}

export function getClusterNode(id: string) {
  return request.get<any, ApiResponse<ClusterNode>>(`/compute/cluster/nodes/${id}`);
}

export function registerNode(data: RegisterNodeRequest) {
  return request.post<any, ApiResponse<ClusterNode>>('/compute/cluster/nodes', data);
}

export function updateNode(id: string, data: Partial<ClusterNode>) {
  return request.put<any, ApiResponse<ClusterNode>>(`/compute/cluster/nodes/${id}`, data);
}

export function deleteNode(id: string) {
  return request.delete<any, ApiResponse<null>>(`/compute/cluster/nodes/${id}`);
}

export function getClusterStatus() {
  return request.get<any, ApiResponse<ClusterStatus>>('/compute/cluster/status');
}

export function dispatchTask(data: DispatchTaskRequest) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/cluster/dispatch', data);
}

export function getNodeHeartbeat(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/compute/cluster/nodes/${id}/heartbeat`);
}

// ==================== 性能基准测试 ====================

export function runBenchmark(data: {
  algorithms: string[];
  iterations?: number;
  data_size?: number;
  participants?: number;
  config_override?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<BenchmarkResult>>('/compute/benchmarks', data);
}

export function listBenchmarks(params?: { limit?: number; offset?: number }) {
  return request.get<any, ApiResponse<{ items: BenchmarkResult[]; total: number }>>('/compute/benchmarks', { params });
}

export function getBenchmark(id: string) {
  return request.get<any, ApiResponse<BenchmarkResult>>(`/compute/benchmarks/${id}`);
}

export function getBenchmarkSummary() {
  return request.get<any, ApiResponse<BenchmarkSummary>>('/compute/benchmarks/summary');
}

export function getBenchmarkTrends(params?: { algorithm?: string; limit?: number }) {
  return request.get<any, ApiResponse<BenchmarkTrendPoint[]>>('/compute/benchmarks/trends', { params });
}

export function exportBenchmarkReport(data: { benchmark_ids: string[]; format_type?: string }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/compute/benchmarks/export', data);
}

// ==================== 隐私计算路由 ====================

export function routePrivacyTask(data: {
  task_description: string;
  data_sensitivity?: string;
  participants?: number;
  scenario?: string;
  requirements?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<PrivacyRouteResult>>('/compute/enhanced/privacy/route', data);
}

export function listPrivacyTechnologies() {
  return request.get<any, ApiResponse<{ technologies: PrivacyTechnology[] }>>('/compute/enhanced/privacy/technologies');
}

export function listPrivacyScenarios() {
  return request.get<any, ApiResponse<{ scenarios: PrivacyScenario[] }>>('/compute/enhanced/privacy/scenarios');
}

export function getPrivacyEngineStatus() {
  return request.get<any, ApiResponse<{ engines: Record<string, { available: boolean; name: string }> }>>('/compute/enhanced/privacy/status');
}
