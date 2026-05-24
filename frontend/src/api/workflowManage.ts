/**
 * 审批工作流 API
 * /api/v1/workflows - 工作流模板、审批记录管理
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  ApprovalWorkflow, ApprovalRecord,
} from '@/types/api';

// ==================== 工作流模板 ====================

export function createWorkflow(data: {
  name: string;
  description?: string;
  workflow_type: string;
  organization_id?: string;
  steps: Record<string, unknown>[];
}) {
  return request.post<any, ApiResponse<ApprovalWorkflow>>('/workflows', data);
}

export function listWorkflows(params?: PaginatedRequest & {
  status?: string;
  workflow_type?: string;
  organization_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ApprovalWorkflow>>>('/workflows', { params });
}

export function getWorkflow(id: string) {
  return request.get<any, ApiResponse<ApprovalWorkflow>>(`/workflows/${id}`);
}

export function updateWorkflow(id: string, data: {
  name?: string;
  description?: string;
  steps?: Record<string, unknown>[];
  status?: string;
}) {
  return request.put<any, ApiResponse<ApprovalWorkflow>>(`/workflows/${id}`, data);
}

export function deleteWorkflow(id: string) {
  return request.delete<any, ApiResponse<null>>(`/workflows/${id}`);
}

// ==================== 审批记录 ====================

export function createApprovalRecord(data: {
  workflow_id: string;
  business_type: string;
  business_id: string;
  approval_data?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ApprovalRecord>>('/workflows/records', data);
}

export function listApprovalRecords(params?: PaginatedRequest & {
  status?: string;
  workflow_id?: string;
  business_type?: string;
  business_id?: string;
  applicant_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<ApprovalRecord>>>('/workflows/records', { params });
}

export function getApprovalRecord(id: string) {
  return request.get<any, ApiResponse<ApprovalRecord>>(`/workflows/records/${id}`);
}

// ==================== 审批操作 ====================

export function approveRecord(id: string, data?: {
  comment?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/workflows/records/${id}/approve`, data);
}

export function rejectRecord(id: string, data: {
  reject_reason: string;
}) {
  return request.post<any, ApiResponse<null>>(`/workflows/records/${id}/reject`, data);
}

export function cancelRecord(id: string) {
  return request.post<any, ApiResponse<null>>(`/workflows/records/${id}/cancel`);
}

// ==================== 我的审批 ====================

export function listMyPendingApprovals(params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<ApprovalRecord>>>('/workflows/records/my-pending', { params });
}

export function listMyApplications(params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ApprovalRecord>>>('/workflows/records/my-applications', { params });
}
