/**
 * 数据资源订阅 API
 * /api/v1/subscriptions - 订阅 CRUD、审核、取消、数据交付管理
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  DataSubscription, DataDelivery,
} from '@/types/api';

// ==================== 订阅 CRUD ====================

export function createDataSubscription(data: {
  catalog_id: string;
  reason?: string;
  subscription_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<DataSubscription>>('/subscriptions', data);
}

export function listDataSubscriptions(params?: PaginatedRequest & {
  status?: string;
  catalog_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataSubscription>>>('/subscriptions', { params });
}

export function getDataSubscription(id: string) {
  return request.get<any, ApiResponse<DataSubscription>>(`/subscriptions/${id}`);
}

export function updateDataSubscription(id: string, data: {
  reason?: string;
  subscription_config?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<DataSubscription>>(`/subscriptions/${id}`, data);
}

export function reviewDataSubscription(id: string, data: {
  status: string;
  expires_at?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/subscriptions/${id}/review`, data);
}

export function cancelDataSubscription(id: string) {
  return request.post<any, ApiResponse<null>>(`/subscriptions/${id}/cancel`);
}

// ==================== 数据交付 ====================

export function createDelivery(subscriptionId: string, data: {
  delivery_type: string;
  delivery_config: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<DataDelivery>>(`/subscriptions/${subscriptionId}/deliveries`, data);
}

export function listDeliveries(subscriptionId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<DataDelivery>>>(`/subscriptions/${subscriptionId}/deliveries`, { params });
}

export function recordDownload(subscriptionId: string, deliveryId: string) {
  return request.post<any, ApiResponse<null>>(`/subscriptions/${subscriptionId}/deliveries/${deliveryId}/download`);
}

export function revokeDelivery(subscriptionId: string, deliveryId: string) {
  return request.post<any, ApiResponse<null>>(`/subscriptions/${subscriptionId}/deliveries/${deliveryId}/revoke`);
}
