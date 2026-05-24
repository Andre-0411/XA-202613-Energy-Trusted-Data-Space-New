/**
 * 连接器管理 API
 * /api/v1/connectors - 连接器 CRUD、心跳、数据源管理、元数据发现
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  Connector, ConnectorDataSource, MetadataDiscovery,
} from '@/types/api';

// ==================== 连接器 CRUD ====================

export function createConnector(data: {
  name: string;
  connector_type: string;
  version?: string;
  deployment_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<Connector>>('/connectors', data);
}

export function listConnectors(params?: PaginatedRequest & { status?: string; connector_type?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<Connector>>>('/connectors', { params });
}

export function getConnector(id: string) {
  return request.get<any, ApiResponse<Connector>>(`/connectors/${id}`);
}

export function updateConnector(id: string, data: {
  name?: string;
  version?: string;
  deployment_config?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<Connector>>(`/connectors/${id}`, data);
}

export function deleteConnector(id: string) {
  return request.delete<any, ApiResponse<null>>(`/connectors/${id}`);
}

export function connectorHeartbeat(id: string, data: {
  system_status?: Record<string, unknown>;
  resource_usage?: Record<string, unknown>;
  network_info?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<null>>(`/connectors/${id}/heartbeat`, data);
}

// ==================== 数据源管理 ====================

export function createConnectorDataSource(connectorId: string, data: {
  name: string;
  source_type: string;
  connection_config: Record<string, unknown>;
  refresh_schedule?: string;
}) {
  return request.post<any, ApiResponse<ConnectorDataSource>>(`/connectors/${connectorId}/data-sources`, data);
}

export function listConnectorDataSources(connectorId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ConnectorDataSource>>>(`/connectors/${connectorId}/data-sources`, { params });
}

export function getConnectorDataSource(connectorId: string, sourceId: string) {
  return request.get<any, ApiResponse<ConnectorDataSource>>(`/connectors/${connectorId}/data-sources/${sourceId}`);
}

export function updateConnectorDataSource(connectorId: string, sourceId: string, data: {
  name?: string;
  connection_config?: Record<string, unknown>;
  refresh_schedule?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<ConnectorDataSource>>(`/connectors/${connectorId}/data-sources/${sourceId}`, data);
}

export function deleteConnectorDataSource(connectorId: string, sourceId: string) {
  return request.delete<any, ApiResponse<null>>(`/connectors/${connectorId}/data-sources/${sourceId}`);
}

// ==================== 元数据发现 ====================

export function triggerMetadataDiscovery(connectorId: string, data: {
  data_source_id: string;
  discovery_scope?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<MetadataDiscovery>>(`/connectors/${connectorId}/discover`, data);
}

export function listDiscoveries(connectorId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<MetadataDiscovery>>>(`/connectors/${connectorId}/discoveries`, { params });
}

export function getDiscovery(connectorId: string, discoveryId: string) {
  return request.get<any, ApiResponse<MetadataDiscovery>>(`/connectors/${connectorId}/discoveries/${discoveryId}`);
}

export function approveDiscovery(connectorId: string, discoveryId: string) {
  return request.post<any, ApiResponse<null>>(`/connectors/${connectorId}/discoveries/${discoveryId}/approve`);
}
