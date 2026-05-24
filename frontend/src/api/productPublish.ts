/**
 * 产品上架 API
 * /api/v1/product-publish - 产品上架申请、审核、下架
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  ProductPublishRequest, ProductUnpublishRequest,
} from '@/types/api';

// ==================== 上架申请 ====================

export function createPublishRequest(data: {
  product_id: string;
  review_deadline?: string;
  control_protocol?: Record<string, unknown>;
  compliance_docs?: Record<string, unknown>;
  pricing_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ProductPublishRequest>>('/product-publish/requests', data);
}

export function listPublishRequests(params?: PaginatedRequest & {
  status?: string;
  product_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductPublishRequest>>>('/product-publish/requests', { params });
}

export function getPublishRequest(id: string) {
  return request.get<any, ApiResponse<ProductPublishRequest>>(`/product-publish/requests/${id}`);
}

// ==================== 上架审核 ====================

export function approvePublishRequest(id: string, data?: {
  review_comment?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/product-publish/requests/${id}/approve`, data);
}

export function rejectPublishRequest(id: string, data: {
  review_comment: string;
}) {
  return request.post<any, ApiResponse<null>>(`/product-publish/requests/${id}/reject`, data);
}

// ==================== 下架申请 ====================

export function createUnpublishRequest(data: {
  product_id: string;
  reason: string;
}) {
  return request.post<any, ApiResponse<ProductUnpublishRequest>>('/product-publish/unpublish-requests', data);
}

export function listUnpublishRequests(params?: PaginatedRequest & {
  status?: string;
  product_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductUnpublishRequest>>>('/product-publish/unpublish-requests', { params });
}

export function getUnpublishRequest(id: string) {
  return request.get<any, ApiResponse<ProductUnpublishRequest>>(`/product-publish/unpublish-requests/${id}`);
}

export function approveUnpublishRequest(id: string, data?: {
  review_comment?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/product-publish/unpublish-requests/${id}/approve`, data);
}

export function rejectUnpublishRequest(id: string, data: {
  review_comment: string;
}) {
  return request.post<any, ApiResponse<null>>(`/product-publish/unpublish-requests/${id}/reject`, data);
}
