/**
 * 统一门户 API
 * 仪表盘、快速入口、通知、布局配置
 */
import request from './request';
import type { ApiResponse } from '@/types/api';

// ===== 类型定义 =====
export interface PortalDashboard {
  user_id: string;
  role: string;
  data_assets_count: number;
  compute_tasks_count: number;
  active_alerts_count: number;
  blockchain_transactions: number;
  recent_activities: Array<{
    action: string;
    resource_type: string;
    timestamp: string;
  }>;
  quick_links: Array<{
    id: string;
    title: string;
    icon: string;
    url: string;
    description?: string;
    category: string;
  }>;
  system_status: string;
  last_updated: string;
}

export interface QuickLink {
  id: string;
  title: string;
  icon: string;
  url: string;
  description?: string;
  category: string;
  order: number;
}

export interface DataOverview {
  metric_name: string;
  metric_value: number;
  unit: string;
  change_percent?: number;
  trend?: string;
}

export interface PortalNotification {
  id: string;
  title: string;
  content: string;
  type: string;
  read: boolean;
  created_at: string;
  link?: string;
}

export interface WidgetConfig {
  widget_id: string;
  widget_type: string;
  title: string;
  position: { x: number; y: number; w: number; h: number };
  config: Record<string, any>;
  visible: boolean;
}

export interface LayoutConfig {
  user_id: string;
  layout_name: string;
  widgets: WidgetConfig[];
  updated_at: string;
}

// ===== API 函数 =====

/** 获取门户仪表盘数据 */
export function getPortalDashboard(userId: string, role?: string, timeRange?: string) {
  return request.get<any, ApiResponse<PortalDashboard>>('/portal/dashboard', {
    params: {
      user_id: userId,
      role,
      time_range: timeRange || '7d',
    },
  });
}

/** 获取快速链接 */
export function getQuickLinks() {
  return request.get<any, ApiResponse<{ links: QuickLink[] }>>('/portal/quick-links');
}

/** 添加快速链接 */
export function addQuickLink(link: Omit<QuickLink, 'id'>) {
  return request.post<any, ApiResponse<QuickLink>>('/portal/quick-links', link);
}

/** 删除快速链接 */
export function removeQuickLink(linkId: string) {
  return request.delete<any, ApiResponse<{ success: boolean }>>(`/portal/quick-links/${linkId}`);
}

/** 获取数据概览 */
export function getDataOverview(timeRange?: string) {
  return request.get<any, ApiResponse<{ overview: DataOverview[] }>>('/portal/overview', {
    params: { time_range: timeRange || '7d' },
  });
}

/** 获取通知 */
export function getPortalNotifications(userId: string, unreadOnly?: boolean, limit?: number) {
  return request.get<any, ApiResponse<{ notifications: PortalNotification[] }>>('/portal/notifications', {
    params: {
      user_id: userId,
      unread_only: unreadOnly || false,
      limit: limit || 20,
    },
  });
}

/** 标记通知已读 */
export function markNotificationRead(notificationId: string) {
  return request.put<any, ApiResponse<{ success: boolean }>>(`/portal/notifications/${notificationId}/read`);
}

/** 获取布局配置 */
export function getLayoutConfig(userId: string) {
  return request.get<any, ApiResponse<LayoutConfig>>('/portal/layout', {
    params: { user_id: userId },
  });
}

/** 保存布局配置 */
export function saveLayoutConfig(config: LayoutConfig) {
  return request.put<any, ApiResponse<LayoutConfig>>('/portal/layout', config);
}

/** 获取活动日志 */
export function getActivityLogs(userId?: string, resourceType?: string, limit?: number) {
  return request.get<any, ApiResponse<{ activities: Array<{
    id: string;
    user_id: string;
    action: string;
    resource_type: string;
    resource_id?: string;
    details?: string;
    timestamp: string;
  }> }>>('/portal/activities', {
    params: {
      user_id: userId,
      resource_type: resourceType,
      limit: limit || 50,
    },
  });
}
