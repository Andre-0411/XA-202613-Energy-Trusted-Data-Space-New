/**
 * 连接器管理 API (新)
 * /api/v1/connector-manage - 连接器注册、心跳、状态管理
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  Connector, ConnectorDataSource,
} from '@/types/api';

// ==================== 连接器注册与管理 ====================

export function registerConnector(data: {
  name: string;
  connector_type: string;
  version?: string;
  deployment_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<Connector>>('/connector-manage', data);
}

export function listManagedConnectors(params?: PaginatedRequest & {
  status?: string;
  connector_type?: string;
  organization_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<Connector>>>('/connector-manage', { params });
}

export function getManagedConnector(id: string) {
  return request.get<any, ApiResponse<Connector>>(`/connector-manage/${id}`);
}

export function updateManagedConnector(id: string, data: {
  name?: string;
  version?: string;
  deployment_config?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<Connector>>(`/connector-manage/${id}`, data);
}

export function deregisterConnector(id: string) {
  return request.delete<any, ApiResponse<null>>(`/connector-manage/${id}`);
}

// ==================== 心跳与状态 ====================

export function sendHeartbeat(id: string, data: {
  system_status?: Record<string, unknown>;
  resource_usage?: Record<string, unknown>;
  network_info?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<null>>(`/connector-manage/${id}/heartbeat`, data);
}

export function getConnectorStatus(id: string) {
  return request.get<any, ApiResponse<Connector>>(`/connector-manage/${id}/status`);
}

export function getConnectorHealth(id: string) {
  return request.get<any, ApiResponse<{
    status: string;
    last_heartbeat: string | null;
    uptime_seconds: number;
    error_count: number;
  }>>(`/connector-manage/${id}/health`);
}

// ==================== 数据源管理 ====================

export function addDataSource(connectorId: string, data: {
  name: string;
  source_type: string;
  connection_config: Record<string, unknown>;
  refresh_schedule?: string;
}) {
  return request.post<any, ApiResponse<ConnectorDataSource>>(`/connector-manage/${connectorId}/data-sources`, data);
}

export function listDataSources(connectorId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ConnectorDataSource>>>(`/connector-manage/${connectorId}/data-sources`, { params });
}

export function updateDataSource(connectorId: string, sourceId: string, data: {
  name?: string;
  connection_config?: Record<string, unknown>;
  refresh_schedule?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<ConnectorDataSource>>(`/connector-manage/${connectorId}/data-sources/${sourceId}`, data);
}

export function removeDataSource(connectorId: string, sourceId: string) {
  return request.delete<any, ApiResponse<null>>(`/connector-manage/${connectorId}/data-sources/${sourceId}`);
}

// ==================== 元数据发现 ====================

export function triggerDiscovery(connectorId: string, data: {
  data_source_id: string;
  discovery_scope?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<{
    id: string;
    status: string;
    message: string;
  }>>(`/connector-manage/${connectorId}/discover`, data);
}

export function listDiscoveries(connectorId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<{
    id: string;
    data_source_id: string;
    status: string;
    result_summary: Record<string, unknown> | null;
    created_at: string;
  }>>>(`/connector-manage/${connectorId}/discoveries`, { params });
}
