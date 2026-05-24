/**
 * 数据目录管理 API
 * /api/v1/catalog-manage - 数据目录注册、管控模板、访问范围
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  CatalogRegistration, ControlTemplate, AccessScopeRule,
} from '@/types/api';

// ==================== 数据目录注册 ====================

export function registerCatalog(data: {
  name: string;
  description: string;
  category: string;
  sensitivity_level: string;
  tags?: string[];
}) {
  return request.post<any, ApiResponse<CatalogRegistration>>('/catalog-manage', data);
}

export function listCatalogs(params?: PaginatedRequest & {
  status?: string;
  category?: string;
  sensitivity_level?: string;
  organization_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<CatalogRegistration>>>('/catalog-manage', { params });
}

export function getCatalog(id: string) {
  return request.get<any, ApiResponse<CatalogRegistration>>(`/catalog-manage/${id}`);
}

export function updateCatalog(id: string, data: {
  name?: string;
  description?: string;
  category?: string;
  sensitivity_level?: string;
  tags?: string[];
  status?: string;
}) {
  return request.put<any, ApiResponse<CatalogRegistration>>(`/catalog-manage/${id}`, data);
}

export function deleteCatalog(id: string) {
  return request.delete<any, ApiResponse<null>>(`/catalog-manage/${id}`);
}

export function publishCatalog(id: string) {
  return request.post<any, ApiResponse<null>>(`/catalog-manage/${id}/publish`);
}

export function unpublishCatalog(id: string) {
  return request.post<any, ApiResponse<null>>(`/catalog-manage/${id}/unpublish`);
}

// ==================== 管控模板 ====================

export function createControlTemplate(catalogId: string, data: {
  template_type: string;
  rules: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ControlTemplate>>(`/catalog-manage/${catalogId}/control-templates`, data);
}

export function listControlTemplates(catalogId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ControlTemplate>>>(`/catalog-manage/${catalogId}/control-templates`, { params });
}

export function getControlTemplate(catalogId: string, templateId: string) {
  return request.get<any, ApiResponse<ControlTemplate>>(`/catalog-manage/${catalogId}/control-templates/${templateId}`);
}

export function updateControlTemplate(catalogId: string, templateId: string, data: {
  rules?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<ControlTemplate>>(`/catalog-manage/${catalogId}/control-templates/${templateId}`, data);
}

export function deleteControlTemplate(catalogId: string, templateId: string) {
  return request.delete<any, ApiResponse<null>>(`/catalog-manage/${catalogId}/control-templates/${templateId}`);
}

// ==================== 访问范围规则 ====================

export function createAccessScopeRule(catalogId: string, data: {
  rule_type: string;
  target_id: string;
  permissions: string[];
  conditions?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<AccessScopeRule>>(`/catalog-manage/${catalogId}/access-rules`, data);
}

export function listAccessScopeRules(catalogId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<AccessScopeRule>>>(`/catalog-manage/${catalogId}/access-rules`, { params });
}

export function updateAccessScopeRule(catalogId: string, ruleId: string, data: {
  permissions?: string[];
  conditions?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<AccessScopeRule>>(`/catalog-manage/${catalogId}/access-rules/${ruleId}`, data);
}

export function deleteAccessScopeRule(catalogId: string, ruleId: string) {
  return request.delete<any, ApiResponse<null>>(`/catalog-manage/${catalogId}/access-rules/${ruleId}`);
}
