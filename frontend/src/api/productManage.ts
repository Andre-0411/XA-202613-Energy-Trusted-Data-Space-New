/**
 * 数据产品管理 API
 * /api/v1/product-manage - 产品项目、产品开发、验收
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  ProductProject, ProjectMember, DataProduct, ProductAcceptance,
} from '@/types/api';

// ==================== 产品项目 ====================

export function createProductProject(data: {
  name: string;
  project_type: string;
  description?: string;
  data_sources?: string[];
}) {
  return request.post<any, ApiResponse<ProductProject>>('/product-manage/projects', data);
}

export function listProductProjects(params?: PaginatedRequest & {
  status?: string;
  project_type?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductProject>>>('/product-manage/projects', { params });
}

export function getProductProject(id: string) {
  return request.get<any, ApiResponse<ProductProject>>(`/product-manage/projects/${id}`);
}

export function updateProductProject(id: string, data: {
  name?: string;
  description?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<ProductProject>>(`/product-manage/projects/${id}`, data);
}

export function deleteProductProject(id: string) {
  return request.delete<any, ApiResponse<null>>(`/product-manage/projects/${id}`);
}

// ==================== 项目成员 ====================

export function addProjectMember(projectId: string, data: {
  user_id: string;
  role: string;
}) {
  return request.post<any, ApiResponse<ProjectMember>>(`/product-manage/projects/${projectId}/members`, data);
}

export function listProjectMembers(projectId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<ProjectMember>>>(`/product-manage/projects/${projectId}/members`, { params });
}

export function updateProjectMember(projectId: string, memberId: string, data: {
  role: string;
}) {
  return request.put<any, ApiResponse<ProjectMember>>(`/product-manage/projects/${projectId}/members/${memberId}`, data);
}

export function removeProjectMember(projectId: string, memberId: string) {
  return request.delete<any, ApiResponse<null>>(`/product-manage/projects/${projectId}/members/${memberId}`);
}

// ==================== 数据产品 ====================

export function createDataProduct(data: {
  name: string;
  product_type: string;
  project_id?: string;
  description?: string;
  compute_engine?: string;
  technical_spec?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  delivery_config?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<DataProduct>>('/product-manage/products', data);
}

export function listDataProducts(params?: PaginatedRequest & {
  status?: string;
  product_type?: string;
  project_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataProduct>>>('/product-manage/products', { params });
}

export function getDataProduct(id: string) {
  return request.get<any, ApiResponse<DataProduct>>(`/product-manage/products/${id}`);
}

export function updateDataProduct(id: string, data: {
  name?: string;
  description?: string;
  technical_spec?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  delivery_config?: Record<string, unknown>;
  compliance_docs?: Record<string, unknown>;
  control_protocol?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<DataProduct>>(`/product-manage/products/${id}`, data);
}

export function deleteDataProduct(id: string) {
  return request.delete<any, ApiResponse<null>>(`/product-manage/products/${id}`);
}

export function submitDataProduct(id: string) {
  return request.post<any, ApiResponse<null>>(`/product-manage/products/${id}/submit`);
}

// ==================== 产品验收 ====================

export function createProductAcceptance(productId: string, data: {
  test_result: Record<string, unknown>;
  comment?: string;
}) {
  return request.post<any, ApiResponse<ProductAcceptance>>(`/product-manage/products/${productId}/acceptances`, data);
}

export function listProductAcceptances(productId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ProductAcceptance>>>(`/product-manage/products/${productId}/acceptances`, { params });
}

export function reviewProductAcceptance(productId: string, acceptanceId: string, data: {
  status: 'approved' | 'rejected';
  comment?: string;
}) {
  return request.put<any, ApiResponse<ProductAcceptance>>(`/product-manage/products/${productId}/acceptances/${acceptanceId}`, data);
}
