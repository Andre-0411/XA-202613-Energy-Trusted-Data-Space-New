/**
 * 连接器文件库 API
 * /api/v1/connector-files - 文件集、文件、API代理管理
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  ConnectorFile, FileSet, ApiProxy,
} from '@/types/api';

// ==================== 文件集管理 ====================

export function createFileSet(data: {
  name: string;
  description?: string;
}) {
  return request.post<any, ApiResponse<FileSet>>('/connector-files/sets', data);
}

export function listFileSets(params?: PaginatedRequest & {
  status?: string;
  organization_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<FileSet>>>('/connector-files/sets', { params });
}

export function getFileSet(id: string) {
  return request.get<any, ApiResponse<FileSet>>(`/connector-files/sets/${id}`);
}

export function updateFileSet(id: string, data: {
  name?: string;
  description?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<FileSet>>(`/connector-files/sets/${id}`, data);
}

export function deleteFileSet(id: string) {
  return request.delete<any, ApiResponse<null>>(`/connector-files/sets/${id}`);
}

// ==================== 文件管理 ====================

export function uploadFile(data: {
  connector_id: string;
  file_set_id?: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  content_hash?: string;
  row_count?: number;
  column_schema?: Record<string, unknown>[];
  metadata?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ConnectorFile>>('/connector-files', data);
}

export function listFiles(params?: PaginatedRequest & {
  status?: string;
  connector_id?: string;
  file_set_id?: string;
  file_type?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ConnectorFile>>>('/connector-files', { params });
}

export function getFile(id: string) {
  return request.get<any, ApiResponse<ConnectorFile>>(`/connector-files/${id}`);
}

export function updateFile(id: string, data: {
  file_name?: string;
  file_set_id?: string;
  column_schema?: Record<string, unknown>[];
  metadata?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<ConnectorFile>>(`/connector-files/${id}`, data);
}

export function deleteFile(id: string) {
  return request.delete<any, ApiResponse<null>>(`/connector-files/${id}`);
}

export function getFileDownloadUrl(id: string) {
  return request.get<any, ApiResponse<{
    download_url: string;
    expires_at: string;
  }>>(`/connector-files/${id}/download-url`);
}

// ==================== API 代理管理 ====================

export function createApiProxy(data: {
  connector_id: string;
  name: string;
  description?: string;
  target_url: string;
  http_method?: string;
  request_headers?: Record<string, unknown>;
  request_params?: Record<string, unknown>;
  request_body_template?: string;
  response_mapping?: Record<string, unknown>;
  auth_config?: Record<string, unknown>;
  rate_limit?: number;
  timeout_ms?: number;
  retry_count?: number;
}) {
  return request.post<any, ApiResponse<ApiProxy>>('/connector-files/proxies', data);
}

export function listApiProxies(params?: PaginatedRequest & {
  status?: string;
  connector_id?: string;
  is_enabled?: boolean;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ApiProxy>>>('/connector-files/proxies', { params });
}

export function getApiProxy(id: string) {
  return request.get<any, ApiResponse<ApiProxy>>(`/connector-files/proxies/${id}`);
}

export function updateApiProxy(id: string, data: {
  name?: string;
  description?: string;
  target_url?: string;
  http_method?: string;
  request_headers?: Record<string, unknown>;
  request_params?: Record<string, unknown>;
  request_body_template?: string;
  response_mapping?: Record<string, unknown>;
  auth_config?: Record<string, unknown>;
  rate_limit?: number;
  timeout_ms?: number;
  retry_count?: number;
  is_enabled?: boolean;
  status?: string;
}) {
  return request.put<any, ApiResponse<ApiProxy>>(`/connector-files/proxies/${id}`, data);
}

export function deleteApiProxy(id: string) {
  return request.delete<any, ApiResponse<null>>(`/connector-files/proxies/${id}`);
}

export function testApiProxy(id: string) {
  return request.post<any, ApiResponse<{
    success: boolean;
    response_time_ms: number;
    status_code: number;
    error?: string;
  }>>(`/connector-files/proxies/${id}/test`);
}
