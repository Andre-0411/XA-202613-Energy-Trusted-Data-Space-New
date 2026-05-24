/**
 * 注册认证 API
 * /api/v1/registration - 邀请码、组织认证、加入申请、自定义角色、用户角色分配
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  InviteCode, OrganizationCertification, OrganizationJoinRequest,
  CustomRole, UserRoleAssignment,
} from '@/types/api';

// ==================== 邀请码 ====================

export function createInviteCode(data: {
  max_uses?: number;
  expires_at?: string;
}) {
  return request.post<any, ApiResponse<InviteCode>>('/registration/invite-codes', data);
}

export function listInviteCodes(params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<InviteCode>>>('/registration/invite-codes', { params });
}

export function verifyInviteCode(code: string) {
  return request.post<any, ApiResponse<InviteCode>>('/registration/invite-codes/verify', { code });
}

// ==================== 组织认证 ====================

export function createCertification(data: {
  certification_type: string;
  certification_data: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<OrganizationCertification>>('/registration/certifications', data);
}

export function listCertifications(params?: PaginatedRequest & { status?: string; certification_type?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<OrganizationCertification>>>('/registration/certifications', { params });
}

export function getCertification(id: string) {
  return request.get<any, ApiResponse<OrganizationCertification>>(`/registration/certifications/${id}`);
}

export function reviewCertification(id: string, data: { status: string; review_comment?: string }) {
  return request.post<any, ApiResponse<OrganizationCertification>>(`/registration/certifications/${id}/review`, data);
}

// ==================== 加入申请 ====================

export function createJoinRequest(data: {
  organization_id: string;
  reason: string;
}) {
  return request.post<any, ApiResponse<OrganizationJoinRequest>>('/registration/join-requests', data);
}

export function listJoinRequests(params?: PaginatedRequest & { status?: string; organization_id?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<OrganizationJoinRequest>>>('/registration/join-requests', { params });
}

export function reviewJoinRequest(id: string, data: { status: string; review_comment?: string }) {
  return request.post<any, ApiResponse<OrganizationJoinRequest>>(`/registration/join-requests/${id}/review`, data);
}

// ==================== 自定义角色 ====================

export function createRole(data: {
  name: string;
  description?: string;
  permissions: string[];
}) {
  return request.post<any, ApiResponse<CustomRole>>('/registration/roles', data);
}

export function listRoles(params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<CustomRole>>>('/registration/roles', { params });
}

export function updateRole(id: string, data: {
  name?: string;
  description?: string;
  permissions?: string[];
}) {
  return request.put<any, ApiResponse<CustomRole>>(`/registration/roles/${id}`, data);
}

export function deleteRole(id: string) {
  return request.delete<any, ApiResponse<null>>(`/registration/roles/${id}`);
}

// ==================== 用户角色分配 ====================

export function assignUserRole(data: {
  user_id: string;
  role_id: string;
}) {
  return request.post<any, ApiResponse<UserRoleAssignment>>('/registration/user-roles', data);
}

export function listUserRoles(params?: PaginatedRequest & { user_id?: string; role_id?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<UserRoleAssignment>>>('/registration/user-roles', { params });
}

export function removeUserRole(userId: string, roleId: string) {
  return request.delete<any, ApiResponse<null>>(`/registration/user-roles/${userId}/${roleId}`);
}
