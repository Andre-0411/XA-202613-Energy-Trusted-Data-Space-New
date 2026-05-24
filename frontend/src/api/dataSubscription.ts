/**
 * 数据资源订阅 API
 * /api/v1/data-subscriptions - 数据订阅申请、审批、交付
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  DataSubscription, DataDelivery,
} from '@/types/api';

// ==================== 数据订阅 ====================

export function createDataSubscription(data: {
  catalog_id: string;
  reason?: string;
  subscription_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<DataSubscription>>('/data-subscriptions', data);
}

export function listDataSubscriptions(params?: PaginatedRequest & {
  status?: string;
  catalog_id?: string;
  subscriber_org_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataSubscription>>>('/data-subscriptions', { params });
}

export function getDataSubscription(id: string) {
  return request.get<any, ApiResponse<DataSubscription>>(`/data-subscriptions/${id}`);
}

export function updateDataSubscription(id: string, data: {
  subscription_config?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<DataSubscription>>(`/data-subscriptions/${id}`, data);
}

export function cancelDataSubscription(id: string) {
  return request.post<any, ApiResponse<null>>(`/data-subscriptions/${id}/cancel`);
}

// ==================== 订阅审批 ====================

export function approveDataSubscription(id: string, data?: {
  review_comment?: string;
  expires_at?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/data-subscriptions/${id}/approve`, data);
}

export function rejectDataSubscription(id: string, data: {
  review_comment: string;
}) {
  return request.post<any, ApiResponse<null>>(`/data-subscriptions/${id}/reject`, data);
}

// ==================== 数据交付 ====================

export function createDelivery(subscriptionId: string, data: {
  delivery_type: string;
  delivery_config: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<DataDelivery>>(`/data-subscriptions/${subscriptionId}/deliveries`, data);
}

export function listDeliveries(subscriptionId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DataDelivery>>>(`/data-subscriptions/${subscriptionId}/deliveries`, { params });
}

export function getDelivery(subscriptionId: string, deliveryId: string) {
  return request.get<any, ApiResponse<DataDelivery>>(`/data-subscriptions/${subscriptionId}/deliveries/${deliveryId}`);
}

export function revokeDelivery(subscriptionId: string, deliveryId: string) {
  return request.post<any, ApiResponse<null>>(`/data-subscriptions/${subscriptionId}/deliveries/${deliveryId}/revoke`);
}
