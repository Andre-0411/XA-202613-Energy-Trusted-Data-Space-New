/**
 * 需求管理 API
 * /api/v1/demands - 需求 CRUD、发布、关闭、认领管理
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
  return request.post<any, ApiResponse<Demand>>('/demands', data);
}

export function listDemands(params?: PaginatedRequest & {
  status?: string;
  demand_type?: string;
  publisher_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<Demand>>>('/demands', { params });
}

export function getDemand(id: string) {
  return request.get<any, ApiResponse<Demand>>(`/demands/${id}`);
}

export function updateDemand(id: string, data: {
  title?: string;
  demand_type?: string;
  description?: string;
  technical_requirements?: Record<string, unknown>;
  budget_range?: string;
  deadline?: string;
  security_risk_assessment?: Record<string, unknown>;
  status?: string;
}) {
  return request.put<any, ApiResponse<Demand>>(`/demands/${id}`, data);
}

export function deleteDemand(id: string) {
  return request.delete<any, ApiResponse<null>>(`/demands/${id}`);
}

export function publishDemand(id: string) {
  return request.post<any, ApiResponse<Demand>>(`/demands/${id}/publish`);
}

export function closeDemand(id: string) {
  return request.post<any, ApiResponse<Demand>>(`/demands/${id}/close`);
}

// ==================== 需求认领 ====================

export function createClaim(demandId: string, data: {
  proposal: string;
}) {
  return request.post<any, ApiResponse<DemandClaim>>(`/demands/${demandId}/claims`, data);
}

export function listClaims(demandId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DemandClaim>>>(`/demands/${demandId}/claims`, { params });
}

export function reviewClaim(claimId: string, data: {
  status: string;
}) {
  return request.post<any, ApiResponse<DemandClaim>>(`/demands/claims/${claimId}/review`, data);
}
