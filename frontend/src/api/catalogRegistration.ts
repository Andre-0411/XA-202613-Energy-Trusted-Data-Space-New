/**
 * 数据目录注册 API
 * /api/v1/catalog-registrations - 目录注册 CRUD、上下架、管控模板、访问规则
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  CatalogRegistration, ControlTemplate, AccessScopeRule,
} from '@/types/api';

// ==================== 目录注册 CRUD ====================

export function createCatalogRegistration(data: {
  name: string;
  description: string;
  category: string;
  sensitivity_level?: string;
  tags?: string[];
}) {
  return request.post<any, ApiResponse<CatalogRegistration>>('/catalog-registrations', data);
}

export function listCatalogRegistrations(params?: PaginatedRequest & {
  status?: string;
  category?: string;
  sensitivity_level?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<CatalogRegistration>>>('/catalog-registrations', { params });
}

export function getCatalogRegistration(id: string) {
  return request.get<any, ApiResponse<CatalogRegistration>>(`/catalog-registrations/${id}`);
}

export function updateCatalogRegistration(id: string, data: {
  name?: string;
  description?: string;
  category?: string;
  sensitivity_level?: string;
  tags?: string[];
}) {
  return request.put<any, ApiResponse<CatalogRegistration>>(`/catalog-registrations/${id}`, data);
}

export function deleteCatalogRegistration(id: string) {
  return request.delete<any, ApiResponse<null>>(`/catalog-registrations/${id}`);
}

export function publishCatalogRegistration(id: string) {
  return request.post<any, ApiResponse<CatalogRegistration>>(`/catalog-registrations/${id}/publish`);
}

export function unpublishCatalogRegistration(id: string) {
  return request.post<any, ApiResponse<CatalogRegistration>>(`/catalog-registrations/${id}/unpublish`);
}

// ==================== 管控模板 ====================

export function createControlTemplate(catalogId: string, data: {
  template_type: string;
  rules: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ControlTemplate>>(`/catalog-registrations/${catalogId}/control-templates`, data);
}

export function listControlTemplates(catalogId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<ControlTemplate>>>(`/catalog-registrations/${catalogId}/control-templates`, { params });
}

export function updateControlTemplate(catalogId: string, templateId: string, data: {
  template_type?: string;
  rules?: Record<string, unknown>;
}) {
  return request.put<any, ApiResponse<ControlTemplate>>(`/catalog-registrations/${catalogId}/control-templates/${templateId}`, data);
}

export function deleteControlTemplate(catalogId: string, templateId: string) {
  return request.delete<any, ApiResponse<null>>(`/catalog-registrations/${catalogId}/control-templates/${templateId}`);
}

// ==================== 访问规则 ====================

export function createAccessRule(catalogId: string, data: {
  rule_type: string;
  target_id: string;
  permissions: string[];
  conditions?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<AccessScopeRule>>(`/catalog-registrations/${catalogId}/access-rules`, data);
}

export function listAccessRules(catalogId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<AccessScopeRule>>>(`/catalog-registrations/${catalogId}/access-rules`, { params });
}

export function deleteAccessRule(catalogId: string, ruleId: string) {
  return request.delete<any, ApiResponse<null>>(`/catalog-registrations/${catalogId}/access-rules/${ruleId}`);
}
