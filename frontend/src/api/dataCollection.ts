/**
 * 数据采集 API
 * MQTT 数据流、设备管理、采集统计
 */
import request from './request';
import type { ApiResponse } from '@/types/api';

// ==================== 类型定义 ====================

export interface DeviceInfo {
  did: string;
  name: string;
  type: string;
  enterprise: string;
  location: string;
  capacity_kw: number;
  status: string;
  last_heartbeat?: string;
  registered_at?: string;
}

export interface DeviceDataRecord {
  device_did: string;
  data_type: string;
  values: Record<string, any>;
  timestamp: string;
  signature: string;
  stored_at?: string;
}

export interface CollectStatistics {
  device_count: number;
  online_device_count: number;
  total_messages: number;
  total_records: number;
  total_alarms: number;
  recent_alarms: number;
  missing_rate: number;
  start_time?: string;
  last_message_time?: string;
}

export interface AlarmRecord {
  device_did: string;
  alarm_type: string;
  message: string;
  severity: string;
  values?: Record<string, any>;
  timestamp: string;
  acknowledged: boolean;
}

export interface SimulatorStatus {
  running: boolean;
  connected: boolean;
  mode: string;
  device_count: number;
  offline_buffer_size: number;
  reconnect_count: number;
}

export interface EnterpriseInfo {
  name: string;
  device_count: number;
  online_count: number;
  total_capacity_kw: number;
  device_types: Record<string, number>;
}

// ==================== 采集控制 ====================

/**
 * 启动 MQTT 数据采集
 */
export function startCollection() {
  return request.post<any, ApiResponse<{ status: string; device_count: number; enterprises: string[] }>>('/mqtt/stream/start');
}

/**
 * 停止 MQTT 数据采集
 */
export function stopCollection() {
  return request.post<any, ApiResponse<{ status: string }>>('/mqtt/stream/stop');
}

/**
 * 获取采集状态
 */
export function getCollectionStatus() {
  return request.get<any, ApiResponse<SimulatorStatus & { collector: any; simulator: any }>>('/mqtt/stream/status');
}

// ==================== 设备管理 ====================

/**
 * 获取设备列表
 */
export function listDevices(params?: { enterprise?: string; device_type?: string }) {
  return request.get<any, ApiResponse<{ devices: DeviceInfo[]; total: number; enterprises: string[] }>>('/mqtt/stream/devices', { params });
}

/**
 * 获取设备详情
 */
export function getDeviceInfo(deviceDid: string) {
  return request.get<any, ApiResponse<{ device: DeviceInfo; latest_data: Record<string, DeviceDataRecord> }>>(`/mqtt/stream/devices/${deviceDid}`);
}

/**
 * 获取设备历史数据
 */
export function getDeviceData(
  deviceDid: string,
  params?: {
    data_type?: string;
    start_time?: string;
    end_time?: string;
    limit?: number;
  }
) {
  return request.get<any, ApiResponse<{ device_did: string; records: DeviceDataRecord[]; total: number }>>(
    `/mqtt/stream/devices/${deviceDid}/data`,
    { params }
  );
}

/**
 * 获取设备数据统计
 */
export function getDeviceStatistics(
  deviceDid: string,
  dataType: string,
  params?: { start_time?: string; end_time?: string }
) {
  return request.get<any, ApiResponse<{
    count: number;
    mean: Record<string, number>;
    max: Record<string, number>;
    min: Record<string, number>;
    missing_rate: number;
  }>>(`/mqtt/stream/devices/${deviceDid}/statistics`, { params: { data_type: dataType, ...params } });
}

// ==================== 统计查询 ====================

/**
 * 获取采集统计信息
 */
export function getCollectionStatistics() {
  return request.get<any, ApiResponse<{ data_store: CollectStatistics; enterprises: Record<string, any> }>>('/mqtt/stream/statistics');
}

/**
 * 获取实时数据快照
 */
export function getRealtimeData(limitPerDevice: number = 10) {
  return request.get<any, ApiResponse<Record<string, { device_info: DeviceInfo; latest_data: Record<string, DeviceDataRecord> }>>>(
    '/mqtt/stream/realtime',
    { params: { limit_per_device: limitPerDevice } }
  );
}

// ==================== 告警管理 ====================

/**
 * 获取告警列表
 */
export function listAlarms(params?: { device_did?: string; alarm_type?: string; limit?: number }) {
  return request.get<any, ApiResponse<{ alarms: AlarmRecord[]; total: number }>>('/mqtt/stream/alarms', { params });
}

/**
 * 手动注入告警
 */
export function injectAlarm(params: {
  device_did: string;
  alarm_type: string;
  message: string;
  severity?: string;
}) {
  return request.post<any, ApiResponse<{ success: boolean; message: string }>>('/mqtt/stream/alarms/inject', null, { params });
}

// ==================== 企业统计 ====================

/**
 * 获取企业列表及统计
 */
export function listEnterprises() {
  return request.get<any, ApiResponse<{ enterprises: EnterpriseInfo[]; total: number }>>('/mqtt/stream/enterprises');
}

/**
 * 获取采集概览
 */
export function getCollectionOverview() {
  return request.get<any, ApiResponse<{
    devices: DeviceInfo[];
    statistics: CollectStatistics;
    recent_data: DeviceDataRecord[];
    alarms: AlarmRecord[];
  }>>('/mqtt/stream/overview');
}
