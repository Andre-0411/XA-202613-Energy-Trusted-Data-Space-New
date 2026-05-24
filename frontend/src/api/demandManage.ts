/**
 * 需求管理 API
 * /api/v1/demand-manage - 需求发布、认领、管理
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  Demand, DemandClaim,
} from '@/types/api';

// ==================== 需求 CRUD ====================

export function createDemand(data: {
  title: string;
  demand_type: string;
  description: string;
  technical_requirements?: Record<string, unknown>;
  budget_range?: string;
  deadline?: string;
  security_risk_assessment?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<Demand>>('/demand-manage', data);
}

export function listDemands(params?: PaginatedRequest & {
  status?: string;
  demand_type?: string;
  organization_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<Demand>>>('/demand-manage', { params });
}

export function getDemand(id: string) {
  return request.get<any, ApiResponse<Demand>>(`/demand-manage/${id}`);
}

export function updateDemand(id: string, data: {
  title?: string;
  description?: string;
  technical_requirements?: Record<string, unknown>;
  budget_range?: string;
  deadline?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<Demand>>(`/demand-manage/${id}`, data);
}

export function deleteDemand(id: string) {
  return request.delete<any, ApiResponse<null>>(`/demand-manage/${id}`);
}

export function closeDemand(id: string) {
  return request.post<any, ApiResponse<null>>(`/demand-manage/${id}/close`);
}

// ==================== 需求认领 ====================

export function claimDemand(demandId: string, data: {
  proposal: string;
}) {
  return request.post<any, ApiResponse<DemandClaim>>(`/demand-manage/${demandId}/claims`, data);
}

export function listDemandClaims(demandId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DemandClaim>>>(`/demand-manage/${demandId}/claims`, { params });
}

export function reviewDemandClaim(demandId: string, claimId: string, data: {
  status: 'approved' | 'rejected';
  review_comment?: string;
}) {
  return request.put<any, ApiResponse<DemandClaim>>(`/demand-manage/${demandId}/claims/${claimId}/review`, data);
}

// ==================== 我的需求 ====================

export function listMyDemands(params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<Demand>>>('/demand-manage/my', { params });
}

export function listMyClaims(params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DemandClaim>>>('/demand-manage/my-claims', { params });
}
