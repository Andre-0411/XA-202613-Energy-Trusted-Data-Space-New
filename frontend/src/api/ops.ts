// Operations API - 运营管理 API

import request from './request';
import type {
  ApiResponse,
  PaginatedResponse,
  PaginatedRequest,
  User,
  Organization,
  ServiceCatalog,
  Subscription,
  BillingRecord,
  BillingSummary,
  AlertInfo,
  ComplianceReport,
  KpiDashboard,
} from '@/types/api';

// ==================== 用户管理 ====================

export function listUsers(params?: PaginatedRequest & { role?: string; status?: string; organization_id?: string; keyword?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<User>>>('/ops/users', { params });
}

export function createUser(data: Partial<User> & { password: string }) {
  return request.post<any, ApiResponse<User>>('/ops/users', data);
}

export function getUser(id: string) {
  return request.get<any, ApiResponse<User>>(`/ops/users/${id}`);
}

export function updateUser(id: string, data: Partial<User>) {
  return request.put<any, ApiResponse<User>>(`/ops/users/${id}`, data);
}

export function deleteUser(id: string) {
  return request.delete<any, ApiResponse<null>>(`/ops/users/${id}`);
}

export function importUsers(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return request.post<any, ApiResponse<{ success_count: number; fail_count: number }>>('/ops/users/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function resetPassword(id: string, newPassword?: string) {
  return request.post<any, ApiResponse<null>>(`/ops/users/${id}/reset-password`, { new_password: newPassword });
}

// ==================== 组织管理 ====================

export function listOrganizations(params?: PaginatedRequest & { status?: string; parent_id?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<Organization>>>('/ops/organizations', { params });
}

export function createOrganization(data: Partial<Organization>) {
  return request.post<any, ApiResponse<Organization>>('/ops/organizations', data);
}

export function getOrganization(id: string) {
  return request.get<any, ApiResponse<Organization>>(`/ops/organizations/${id}`);
}

export function updateOrganization(id: string, data: Partial<Organization>) {
  return request.put<any, ApiResponse<Organization>>(`/ops/organizations/${id}`, data);
}

export function getOrganizationTree(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/ops/organizations/${id}/tree`);
}

export function deleteOrganization(id: string) {
  return request.delete<any, ApiResponse<null>>(`/ops/organizations/${id}`);
}

export function getOrganizationMembers(orgId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<User>>>(`/ops/organizations/${orgId}/members`, { params });
}

export function getOrganizationStats(orgId: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/ops/organizations/${orgId}/stats`);
}

// ==================== 服务管理 ====================

export function listServices(params?: PaginatedRequest & { category?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ServiceCatalog>>>('/ops/services', { params });
}

export function createService(data: Partial<ServiceCatalog>) {
  return request.post<any, ApiResponse<ServiceCatalog>>('/ops/services', data);
}

export function getService(id: string) {
  return request.get<any, ApiResponse<ServiceCatalog>>(`/ops/services/${id}`);
}

export function updateService(id: string, data: Partial<ServiceCatalog>) {
  return request.put<any, ApiResponse<ServiceCatalog>>(`/ops/services/${id}`, data);
}

export function getSubscriptions(serviceId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<Subscription>>>(`/ops/services/${serviceId}/subscriptions`, { params });
}

export function subscribeService(serviceId: string, data: { start_date: string; end_date?: string }) {
  return request.post<any, ApiResponse<Subscription>>(`/ops/services/${serviceId}/subscribe`, data);
}

export function approveSubscription(subId: string, approved: boolean) {
  return request.put<any, ApiResponse<Subscription>>(`/ops/services/subscriptions/${subId}/approve`, { approved });
}

// ==================== 计费 ====================

export function getBillingRecords(params?: PaginatedRequest & { payment_status?: string; billing_period?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<BillingRecord>>>('/ops/billing/records', { params });
}

export function getMonthlyInvoice(period: string, organizationId?: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/ops/billing/invoice/${period}`, { params: { organization_id: organizationId } });
}

export function getBillingSummary(organizationId?: string) {
  return request.get<any, ApiResponse<BillingSummary>>('/ops/billing/summary', { params: { organization_id: organizationId } });
}

// ==================== 监控 ====================

export function getMetrics() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/ops/monitoring/metrics');
}

export function getAlerts(params?: { status?: string; severity?: string; limit?: number; offset?: number }) {
  return request.get<any, ApiResponse<PaginatedResponse<AlertInfo>>>('/ops/monitoring/alerts', { params });
}

export function acknowledgeAlert(alertId: string) {
  return request.post<any, ApiResponse<AlertInfo>>(`/ops/monitoring/alerts/${alertId}/ack`);
}

export function getHealthCheck() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/ops/monitoring/health');
}

// ==================== 门户公开接口（无需认证） ====================

export function getPublicDashboard() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/ops/monitoring/dashboard');
}

// ==================== 合规 ====================

export function listComplianceReports(params?: PaginatedRequest & { report_type?: string; status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ComplianceReport>>>('/ops/compliance/reports', { params });
}

export function generateComplianceReport(data: { organization_id: string; report_type: string; period: string }) {
  return request.post<any, ApiResponse<ComplianceReport>>('/ops/compliance/reports/generate', data);
}

export function getComplianceReport(id: string) {
  return request.get<any, ApiResponse<ComplianceReport>>(`/ops/compliance/reports/${id}`);
}

export function getComplianceChecklist(reportType?: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/ops/compliance/checklist', { params: { report_type: reportType } });
}

// ==================== KPI ====================

export function getKpiDashboard() {
  return request.get<any, ApiResponse<KpiDashboard>>('/ops/kpi/dashboard');
}

export function getSlaMetrics() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/ops/kpi/sla');
}

export function getPerformanceMetrics() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/ops/kpi/performance');
}

// ==================== 收益分配 ====================

export interface RevenueDistribution {
  period: string;
  total_revenue: number;
  distributions: Array<{
    organization_id: string;
    organization_name: string;
    total_revenue: number;
    quality_score: number;
    usage_score: number;
    composite_score: number;
    provider_share: number;
    platform_fee: number;
    algorithm_contribution: number;
    governance_reward: number;
    data_asset_count: number;
    total_usage_count: number;
  }>;
  summary: {
    platform_fee: number;
    algorithm_contribution: number;
    data_governance_reward: number;
    data_provider_total: number;
  };
}

export interface RevenueSummary {
  total_revenue: number;
  total_platform_fee: number;
  total_algorithm_contribution: number;
  total_governance_reward: number;
  total_provider_share: number;
  periods: Array<{
    period: string;
    total_revenue: number;
    record_count: number;
    platform_fee: number;
    provider_share: number;
  }>;
}

export function calculateRevenue(period: string, organizationId?: string) {
  return request.get<any, ApiResponse<RevenueDistribution>>('/ops/revenue/calculate', {
    params: { period, organization_id: organizationId },
  });
}

export function getRevenueSummary(params?: { start_period?: string; end_period?: string; organization_id?: string }) {
  return request.get<any, ApiResponse<RevenueSummary>>('/ops/revenue/summary', { params });
}

export function createSettlement(period: string, organizationId: string) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/ops/revenue/settlements', null, {
    params: { period, organization_id: organizationId },
  });
}

export function listSettlements(params?: { period?: string; organization_id?: string; status?: string }) {
  return request.get<any, ApiResponse<Record<string, unknown>[]>>('/ops/revenue/settlements', { params });
}

export function confirmSettlement(settlementId: string) {
  return request.post<any, ApiResponse<Record<string, unknown>>>(`/ops/revenue/settlements/${settlementId}/confirm`);
}

// ==================== 告警通知渠道 ====================

export function listNotificationChannels() {
  return request.get<any, ApiResponse<Record<string, unknown>[]>>('/ops/alerts/notification-channels');
}

export function updateNotificationChannel(channelId: string, config: Record<string, unknown>) {
  return request.put<any, ApiResponse<Record<string, unknown>>>(`/ops/alerts/notification-channels/${channelId}`, config);
}

export function testNotificationChannel(channelId: string) {
  return request.post<any, ApiResponse<null>>(`/ops/alerts/notification-channels/${channelId}/test`);
}
