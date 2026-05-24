/**
 * 数据产品 API
 * /api/v1/products - 产品项目、数据产品、验收、上下架、产品订阅、产品交付
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  ProductProject, ProjectMember, DataProduct, ProductAcceptance,
  ProductPublishRequest, ProductUnpublishRequest,
  ProductSubscription, ProductDelivery,
} from '@/types/api';

// ==================== 产品项目 ====================

export function createProject(data: {
  name: string;
  project_type: string;
  description?: string;
  data_sources?: string[];
}) {
  return request.post<any, ApiResponse<ProductProject>>('/products/projects', data);
}

export function listProjects(params?: PaginatedRequest & {
  status?: string;
  project_type?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductProject>>>('/products/projects', { params });
}

export function getProject(id: string) {
  return request.get<any, ApiResponse<ProductProject>>(`/products/projects/${id}`);
}

export function updateProject(id: string, data: {
  name?: string;
  description?: string;
  project_type?: string;
  data_sources?: string[];
  status?: string;
}) {
  return request.put<any, ApiResponse<ProductProject>>(`/products/projects/${id}`, data);
}

export function deleteProject(id: string) {
  return request.delete<any, ApiResponse<null>>(`/products/projects/${id}`);
}

export function addProjectMember(projectId: string, data: {
  user_id: string;
  role?: string;
}) {
  return request.post<any, ApiResponse<ProjectMember>>(`/products/projects/${projectId}/members`, data);
}

export function removeProjectMember(projectId: string, memberUserId: string) {
  return request.delete<any, ApiResponse<null>>(`/products/projects/${projectId}/members/${memberUserId}`);
}

// ==================== 数据产品 CRUD ====================

export function createProduct(data: {
  name: string;
  product_type: string;
  project_id?: string;
  description?: string;
  compute_engine?: string;
  version?: string;
  technical_spec?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  delivery_config?: Record<string, unknown>;
  compliance_docs?: Record<string, unknown>;
  control_protocol?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<DataProduct>>('/products', data);
}

export function listProducts(params?: PaginatedRequest & {
  status?: string;
  product_type?: string;
  project_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataProduct>>>('/products', { params });
}

export function getProduct(id: string) {
  return request.get<any, ApiResponse<DataProduct>>(`/products/${id}`);
}

export function updateProduct(id: string, data: {
  name?: string;
  description?: string;
  product_type?: string;
  compute_engine?: string;
  version?: string;
  technical_spec?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  delivery_config?: Record<string, unknown>;
  compliance_docs?: Record<string, unknown>;
  control_protocol?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<DataProduct>>(`/products/${id}`, data);
}

export function deleteProduct(id: string) {
  return request.delete<any, ApiResponse<null>>(`/products/${id}`);
}

// ==================== 产品验收 ====================

export function createAcceptance(productId: string, data: {
  acceptor_id: string;
  test_result: Record<string, unknown>;
  comment?: string;
}) {
  return request.post<any, ApiResponse<ProductAcceptance>>(`/products/${productId}/acceptances`, data);
}

export function listAcceptances(productId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductAcceptance>>>(`/products/${productId}/acceptances`, { params });
}

export function reviewAcceptance(acceptanceId: string, status: string, comment?: string) {
  return request.post<any, ApiResponse<null>>(`/products/acceptances/${acceptanceId}/review`, null, {
    params: { status, comment },
  });
}

// ==================== 产品上下架 ====================

export function createPublishRequest(productId: string, data: {
  review_deadline?: string;
  control_protocol?: Record<string, unknown>;
  compliance_docs?: Record<string, unknown>;
  pricing_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ProductPublishRequest>>(`/products/${productId}/publish`, data);
}

export function listPublishRequests(params?: PaginatedRequest & {
  status?: string;
  product_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductPublishRequest>>>('/products/publish-requests', { params });
}

export function reviewPublishRequest(requestId: string, data: {
  status: string;
  review_comment?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/products/publish-requests/${requestId}/review`, data);
}

export function createUnpublishRequest(productId: string, reason: string) {
  return request.post<any, ApiResponse<ProductUnpublishRequest>>(`/products/${productId}/unpublish`, { reason });
}

export function reviewUnpublishRequest(requestId: string, data: {
  status: string;
  review_comment?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/products/unpublish-requests/${requestId}/review`, data);
}

// ==================== 产品订阅 ====================

export function createProductSubscription(productId: string, data: {
  reason?: string;
  subscription_config?: Record<string, unknown>;
  delivery_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ProductSubscription>>(`/products/${productId}/subscriptions`, data);
}

export function listProductSubscriptions(productId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductSubscription>>>(`/products/${productId}/subscriptions`, { params });
}

export function reviewProductSubscription(subscriptionId: string, data: {
  status: string;
  expires_at?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/products/subscriptions/${subscriptionId}/review`, data);
}

// ==================== 产品交付 ====================

export function createProductDelivery(subscriptionId: string, data: {
  delivery_type: string;
  delivery_config: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ProductDelivery>>(`/products/subscriptions/${subscriptionId}/deliveries`, data);
}

export function recordProductDownload(deliveryId: string) {
  return request.post<any, ApiResponse<null>>(`/products/deliveries/${deliveryId}/download`);
}
