/**
 * SLA 管理 API
 * SLA 配置、指标、报告、仪表盘
 */
import request from './request';
import type { ApiResponse } from '@/types/api';

// ===== 类型定义 =====
export interface SLATarget {
  metric_name: string;
  target_value: number;
  unit: string;
  operator: string;
  description?: string;
}

export interface SLAConfig {
  sla_id: string;
  name: string;
  service_id: string;
  service_name?: string;
  targets: SLATarget[];
  enabled: boolean;
  created_at: string;
  updated_at?: string;
}

export interface SLAMetricData {
  metric_name: string;
  current_value: number;
  target_value: number;
  unit: string;
  status: 'met' | 'at_risk' | 'breached';
  compliance_percent: number;
  trend?: string;
  last_measured_at: string;
}

export interface SLAReport {
  report_id: string;
  sla_id: string;
  service_id: string;
  period_start: string;
  period_end: string;
  overall_compliance: number;
  metrics: SLAMetricData[];
  breaches: Array<Record<string, any>>;
  generated_at: string;
}

export interface SLADashboard {
  total_slas: number;
  met_count: number;
  at_risk_count: number;
  breached_count: number;
  overall_compliance: number;
  metrics: SLAMetricData[];
  recent_breaches: Array<Record<string, any>>;
  period: string;
}

export interface SLAAlertConfig {
  alert_id: string;
  sla_id: string;
  metric_name: string;
  threshold_percent: number;
  notify_channels: string[];
  enabled: boolean;
}

// ===== API 函数 =====

/** 列出 SLA 配置 */
export function getSlaConfigs() {
  return request.get<any, ApiResponse<{ configs: SLAConfig[] }>>('/ops/sla/configs');
}

/** 获取 SLA 配置 */
export function getSlaConfig(slaId: string) {
  return request.get<any, ApiResponse<SLAConfig>>(`/ops/sla/configs/${slaId}`);
}

/** 创建 SLA 配置 */
export function createSlaConfig(config: Omit<SLAConfig, 'sla_id' | 'created_at'>) {
  return request.post<any, ApiResponse<SLAConfig>>('/ops/sla/configs', config);
}

/** 更新 SLA 配置 */
export function updateSlaConfig(slaId: string, config: Partial<SLAConfig>) {
  return request.put<any, ApiResponse<SLAConfig>>(`/ops/sla/configs/${slaId}`, config);
}

/** 删除 SLA 配置 */
export function deleteSlaConfig(slaId: string) {
  return request.delete<any, ApiResponse<{ success: boolean }>>(`/ops/sla/configs/${slaId}`);
}

/** 采集 SLA 指标 */
export function collectSlaMetrics(slaId: string) {
  return request.get<any, ApiResponse<{ sla_id: string; metrics: SLAMetricData[] }>>(`/ops/sla/metrics/${slaId}`);
}

/** 生成 SLA 报告 */
export function generateSlaReport(slaId: string, periodStart: string, periodEnd: string) {
  return request.post<any, ApiResponse<SLAReport>>('/ops/sla/reports', null, {
    params: {
      sla_id: slaId,
      period_start: periodStart,
      period_end: periodEnd,
    },
  });
}

/** 获取 SLA 仪表盘 */
export function getSlaDashboard(period?: string) {
  return request.get<any, ApiResponse<SLADashboard>>('/ops/sla/dashboard', {
    params: { period: period || '30d' },
  });
}

/** 获取指标历史 */
export function getMetricHistory(slaId: string, metricName: string) {
  return request.get<any, ApiResponse<{ history: Array<{ timestamp: string; value: number }> }>>(
    `/ops/sla/metrics/${slaId}/history`,
    { params: { metric_name: metricName } },
  );
}

/** 创建 SLA 告警配置 */
export function createSlaAlertConfig(config: Omit<SLAAlertConfig, 'alert_id'>) {
  return request.post<any, ApiResponse<SLAAlertConfig>>('/ops/sla/alerts', config);
}

/** 列出 SLA 告警配置 */
export function listSlaAlertConfigs(slaId?: string) {
  return request.get<any, ApiResponse<{ configs: SLAAlertConfig[] }>>('/ops/sla/alerts', {
    params: slaId ? { sla_id: slaId } : {},
  });
}
