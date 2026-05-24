/**
 * 服务申请审批 API
 * /api/v1/data/applications - 提交申请 / 申请列表 / 申请详情 / 审批操作 / 申请统计
 */
import request from './request';
import type { ApiResponse, PaginatedResponse, PaginatedRequest } from '@/types/api';

// ==================== 类型定义 ====================

/** 数据使用申请 */
export interface DataApplication {
  id: string;
  application_no: string;
  asset_id: string;
  asset_name: string;
  applicant_id: string;
  applicant_name: string;
  purpose: string;
  status: 'pending' | 'approved' | 'rejected';
  duration_days: number;
  validity_start: string | null;
  validity_end: string | null;
  reviewer_id: string | null;
  reviewer_name: string | null;
  review_comment: string | null;
  reject_reason: string | null;
  created_at: string;
  updated_at: string;
}

/** 提交申请请求 */
export interface ApplicationCreateRequest {
  asset_id: string;
  purpose: string;
  duration_days?: number;
  validity_start?: string;
  validity_end?: string;
}

/** 审批通过请求 */
export interface ApplicationApproveRequest {
  comment?: string;
}

/** 审批拒绝请求 */
export interface ApplicationRejectRequest {
  reason: string;
  comment?: string;
}

/** 申请统计数据 */
export interface ApplicationStats {
  total_applications: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
}

/** 申请列表查询范围 */
export type ApplicationScope = 'mine' | 'pending_approval' | 'all';

// ==================== API 函数 ====================

/**
 * 提交数据使用申请
 */
export function createApplication(data: ApplicationCreateRequest) {
  return request.post<any, ApiResponse<DataApplication>>('/data/applications', data);
}

/**
 * 获取申请列表
 */
export function getApplications(params?: PaginatedRequest & {
  scope?: ApplicationScope;
  status?: string;
  keyword?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataApplication>>>('/data/applications', { params });
}

/**
 * 获取申请统计数据
 */
export function getApplicationStats() {
  return request.get<any, ApiResponse<ApplicationStats>>('/data/applications/stats');
}

/**
 * 获取申请详情
 */
export function getApplicationDetail(id: string) {
  return request.get<any, ApiResponse<DataApplication>>(`/data/applications/${id}`);
}

/**
 * 审批通过
 */
export function approveApplication(id: string, data?: ApplicationApproveRequest) {
  return request.put<any, ApiResponse<DataApplication>>(`/data/applications/${id}/approve`, data ?? {});
}

/**
 * 审批拒绝
 */
export function rejectApplication(id: string, data: ApplicationRejectRequest) {
  return request.put<any, ApiResponse<DataApplication>>(`/data/applications/${id}/reject`, data);
}
