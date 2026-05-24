/**
 * 系统管理 API
 * 包含通知公告、系统配置、操作日志等功能
 */
import request from './request';

// ===== 类型定义 =====

export interface Notification {
  id: string;
  title: string;
  content: string;
  type: 'info' | 'warning' | 'error' | 'success';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  category: 'system' | 'task' | 'security' | 'billing';
  target_users: string[] | null;
  created_at: string;
  updated_at: string;
  is_read: boolean;
  read_at: string | null;
  sender: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export interface ConfigItem {
  key: string;
  value: any;
  description: string;
  category: string;
  is_sensitive: boolean;
}

export interface ConfigCategory {
  key: string;
  name: string;
  description: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string;
  username: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  resource_name: string | null;
  details: string | null;
  ip_address: string;
  user_agent: string | null;
  status: string;
  module: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogStatistics {
  total_logs: number;
  today_count: number;
  action_stats: Record<string, number>;
  module_stats: Record<string, number>;
  status_stats: Record<string, number>;
}

// ===== 通知公告 API =====

/** 获取通知列表 */
export const getNotifications = (params?: {
  page?: number;
  page_size?: number;
  type?: string;
  category?: string;
  is_read?: boolean;
  priority?: string;
}) => request.get<{ code: number; data: NotificationListResponse }>('/notifications', { params });

/** 获取未读通知数量 */
export const getUnreadCount = () =>
  request.get<{ code: number; data: { unread_count: number } }>('/notifications/unread-count');

/** 获取通知详情 */
export const getNotificationDetail = (id: string) =>
  request.get<{ code: number; data: Notification }>(`/notifications/${id}`);

/** 创建通知 */
export const createNotification = (data: {
  title: string;
  content: string;
  type?: string;
  priority?: string;
  category?: string;
  target_users?: string[];
}) => request.post<{ code: number; data: Notification }>('/notifications', data);

/** 更新通知 */
export const updateNotification = (id: string, data: {
  title?: string;
  content?: string;
  type?: string;
  priority?: string;
  category?: string;
}) => request.put<{ code: number; data: Notification }>(`/notifications/${id}`, data);

/** 删除通知 */
export const deleteNotification = (id: string) =>
  request.delete<{ code: number }>(`/notifications/${id}`);

/** 标记通知为已读 */
export const markAsRead = (id: string) =>
  request.post<{ code: number }>(`/notifications/${id}/read`);

/** 标记所有通知为已读 */
export const markAllAsRead = () =>
  request.post<{ code: number }>('/notifications/read-all');

/** 批量删除通知 */
export const batchDeleteNotifications = (ids: string[]) =>
  request.post<{ code: number }>('/notifications/batch-delete', ids);

/** 批量标记已读 */
export const batchMarkAsRead = (ids: string[]) =>
  request.post<{ code: number }>('/notifications/batch-read', ids);

// ===== 系统配置 API =====

/** 获取配置分类列表 */
export const getConfigCategories = () =>
  request.get<{ code: number; data: ConfigCategory[] }>('/system/config/categories');

/** 获取分类下的配置 */
export const getConfigsByCategory = (category: string) =>
  request.get<{ code: number; data: ConfigItem[] }>(`/system/config/${category}`);

/** 更新配置项 */
export const updateConfig = (category: string, key: string, value: any) =>
  request.put<{ code: number }>(`/system/config/${category}/${key}`, { value });

/** 批量更新配置 */
export const batchUpdateConfigs = (configs: ConfigItem[]) =>
  request.post<{ code: number }>('/system/config/batch-update', { configs });

/** 重置分类配置 */
export const resetCategoryConfig = (category: string) =>
  request.post<{ code: number }>(`/system/config/reset/${category}`);

/** 导出所有配置 */
export const exportAllConfigs = () =>
  request.get<{ code: number; data: Record<string, any> }>('/system/config/export/all');

// ===== 操作日志 API =====

/** 获取操作日志列表 */
export const getAuditLogs = (params?: {
  page?: number;
  page_size?: number;
  user_id?: string;
  action?: string;
  resource_type?: string;
  module?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  keyword?: string;
}) => request.get<{ code: number; data: AuditLogListResponse }>('/audit-logs', { params });

/** 获取操作类型列表 */
export const getActionTypes = () =>
  request.get<{ code: number; data: { value: string; label: string }[] }>('/audit-logs/actions');

/** 获取资源类型列表 */
export const getResourceTypes = () =>
  request.get<{ code: number; data: { value: string; label: string }[] }>('/audit-logs/resource-types');

/** 获取模块列表 */
export const getModules = () =>
  request.get<{ code: number; data: { value: string; label: string }[] }>('/audit-logs/modules');

/** 获取日志统计 */
export const getAuditLogStatistics = () =>
  request.get<{ code: number; data: AuditLogStatistics }>('/audit-logs/statistics');

/** 获取日志详情 */
export const getAuditLogDetail = (id: string) =>
  request.get<{ code: number; data: AuditLog }>(`/audit-logs/${id}`);

/** 导出操作日志 */
export const exportAuditLogs = (params: {
  format?: string;
  user_id?: string;
  action?: string;
  module?: string;
  start_date?: string;
  end_date?: string;
}) => request.post<{ code: number; data: { format: string; count: number; download_url: string } }>('/audit-logs/export', null, { params });
