/**
 * 机构管理 API
 * /api/v1/organizations - 机构 CRUD、认证、成员管理
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  Organization, OrganizationCertification, OrganizationJoinRequest,
  CustomRole, UserRoleAssignment,
} from '@/types/api';

// ==================== 机构 CRUD ====================

export function createOrganization(data: {
  name: string;
  code: string;
  did?: string;
  parent_id?: string;
  level?: number;
}) {
  return request.post<any, ApiResponse<Organization>>('/organizations', data);
}

export function listOrganizations(params?: PaginatedRequest & { status?: string; level?: number }) {
  return request.get<any, ApiResponse<PaginatedResponse<Organization>>>('/organizations', { params });
}

export function getOrganization(id: string) {
  return request.get<any, ApiResponse<Organization>>(`/organizations/${id}`);
}

export function updateOrganization(id: string, data: {
  name?: string;
  code?: string;
  did?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<Organization>>(`/organizations/${id}`, data);
}

export function deleteOrganization(id: string) {
  return request.delete<any, ApiResponse<null>>(`/organizations/${id}`);
}

// ==================== 机构认证 ====================

export function submitCertification(orgId: string, data: {
  certification_type: string;
  certification_data: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<OrganizationCertification>>(`/organizations/${orgId}/certifications`, data);
}

export function listCertifications(orgId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<OrganizationCertification>>>(`/organizations/${orgId}/certifications`, { params });
}

export function getCertification(orgId: string, certId: string) {
  return request.get<any, ApiResponse<OrganizationCertification>>(`/organizations/${orgId}/certifications/${certId}`);
}

export function reviewCertification(orgId: string, certId: string, data: {
  status: 'approved' | 'rejected';
  review_comment?: string;
}) {
  return request.put<any, ApiResponse<OrganizationCertification>>(`/organizations/${orgId}/certifications/${certId}/review`, data);
}

// ==================== 加入申请 ====================

export function submitJoinRequest(orgId: string, data: {
  reason: string;
}) {
  return request.post<any, ApiResponse<OrganizationJoinRequest>>(`/organizations/${orgId}/join-requests`, data);
}

export function listJoinRequests(orgId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<OrganizationJoinRequest>>>(`/organizations/${orgId}/join-requests`, { params });
}

export function reviewJoinRequest(orgId: string, requestId: string, data: {
  status: 'approved' | 'rejected';
  review_comment?: string;
}) {
  return request.put<any, ApiResponse<OrganizationJoinRequest>>(`/organizations/${orgId}/join-requests/${requestId}/review`, data);
}

// ==================== 自定义角色 ====================

export function createCustomRole(orgId: string, data: {
  name: string;
  description?: string;
  permissions: string[];
}) {
  return request.post<any, ApiResponse<CustomRole>>(`/organizations/${orgId}/roles`, data);
}

export function listCustomRoles(orgId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<CustomRole>>>(`/organizations/${orgId}/roles`, { params });
}

export function updateCustomRole(orgId: string, roleId: string, data: {
  name?: string;
  description?: string;
  permissions?: string[];
  status?: string;
}) {
  return request.put<any, ApiResponse<CustomRole>>(`/organizations/${orgId}/roles/${roleId}`, data);
}

export function deleteCustomRole(orgId: string, roleId: string) {
  return request.delete<any, ApiResponse<null>>(`/organizations/${orgId}/roles/${roleId}`);
}

// ==================== 用户角色分配 ====================

export function assignUserRole(orgId: string, data: {
  user_id: string;
  role_id: string;
}) {
  return request.post<any, ApiResponse<UserRoleAssignment>>(`/organizations/${orgId}/user-roles`, data);
}

export function listUserRoles(orgId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<UserRoleAssignment>>>(`/organizations/${orgId}/user-roles`, { params });
}

export function removeUserRole(orgId: string, assignmentId: string) {
  return request.delete<any, ApiResponse<null>>(`/organizations/${orgId}/user-roles/${assignmentId}`);
}
