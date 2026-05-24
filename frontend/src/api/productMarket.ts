/**
 * 产品市场 API
 * /api/v1/product-market - 产品浏览、订阅、交付
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  DataProduct, ProductSubscription, ProductDelivery,
} from '@/types/api';

// ==================== 产品浏览 ====================

export function listMarketProducts(params?: PaginatedRequest & {
  product_type?: string;
  category?: string;
  keyword?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataProduct>>>('/product-market/products', { params });
}

export function getMarketProduct(id: string) {
  return request.get<any, ApiResponse<DataProduct>>(`/product-market/products/${id}`);
}

export function getProductDetail(id: string) {
  return request.get<any, ApiResponse<DataProduct>>(`/product-market/products/${id}/detail`);
}

// ==================== 产品订阅 ====================

export function subscribeProduct(data: {
  product_id: string;
  reason?: string;
  subscription_config?: Record<string, unknown>;
  delivery_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ProductSubscription>>('/product-market/subscriptions', data);
}

export function listMySubscriptions(params?: PaginatedRequest & {
  status?: string;
  product_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductSubscription>>>('/product-market/subscriptions', { params });
}

export function getSubscription(id: string) {
  return request.get<any, ApiResponse<ProductSubscription>>(`/product-market/subscriptions/${id}`);
}

export function cancelSubscription(id: string) {
  return request.post<any, ApiResponse<null>>(`/product-market/subscriptions/${id}/cancel`);
}

// ==================== 订阅审批 (供产品方使用) ====================

export function approveSubscription(id: string, data?: {
  review_comment?: string;
  expires_at?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/product-market/subscriptions/${id}/approve`, data);
}

export function rejectSubscription(id: string, data: {
  review_comment: string;
}) {
  return request.post<any, ApiResponse<null>>(`/product-market/subscriptions/${id}/reject`, data);
}

// ==================== 产品交付 ====================

export function createProductDelivery(subscriptionId: string, data: {
  delivery_type: string;
  delivery_config: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ProductDelivery>>(`/product-market/subscriptions/${subscriptionId}/deliveries`, data);
}

export function listProductDeliveries(subscriptionId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductDelivery>>>(`/product-market/subscriptions/${subscriptionId}/deliveries`, { params });
}

export function revokeProductDelivery(subscriptionId: string, deliveryId: string) {
  return request.post<any, ApiResponse<null>>(`/product-market/subscriptions/${subscriptionId}/deliveries/${deliveryId}/revoke`);
}
