/**
 * 数据资源 API
 * 数据源 / 数据资产 / 数据目录 / 元数据 / 标签 / 质量检查
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  DataSource, DataAsset, DataCatalogItem, MetadataRecord, Tag, QualityReport,
} from '@/types/api';

// ==================== 数据源 ====================

export function listDataSources(params?: PaginatedRequest & { source_type?: string; status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DataSource>>>('/data/sources', { params });
}

export function getDataSource(id: string) {
  return request.get<any, ApiResponse<DataSource>>(`/data/sources/${id}`);
}

export function createDataSource(data: Partial<DataSource>) {
  return request.post<any, ApiResponse<DataSource>>('/data/sources', data);
}

export function updateDataSource(id: string, data: Partial<DataSource>) {
  return request.put<any, ApiResponse<DataSource>>(`/data/sources/${id}`, data);
}

export function deleteDataSource(id: string) {
  return request.delete<any, ApiResponse<null>>(`/data/sources/${id}`);
}

export function startDataSource(id: string) {
  return request.post<any, ApiResponse<null>>(`/data/sources/${id}/start`);
}

export function stopDataSource(id: string) {
  return request.post<any, ApiResponse<null>>(`/data/sources/${id}/stop`);
}

export function getDataSourceMetrics(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/data/sources/${id}/metrics`);
}

// ==================== 数据资产 ====================

export function listDataAssets(params?: PaginatedRequest & { asset_type?: string; category?: string; sensitivity_level?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DataAsset>>>('/data/assets', { params });
}

export function getDataAsset(id: string) {
  return request.get<any, ApiResponse<DataAsset>>(`/data/assets/${id}`);
}

export function createDataAsset(data: Partial<DataAsset>) {
  return request.post<any, ApiResponse<DataAsset>>('/data/assets', data);
}

export function updateDataAsset(id: string, data: Partial<DataAsset>) {
  return request.put<any, ApiResponse<DataAsset>>(`/data/assets/${id}`, data);
}

export function classifyAsset(id: string) {
  return request.post<any, ApiResponse<DataAsset>>(`/data/assets/${id}/classify`);
}

export function publishAsset(id: string) {
  return request.post<any, ApiResponse<null>>(`/data/assets/${id}/publish`);
}

// ==================== 数据目录 ====================

export function browseCatalog(params?: PaginatedRequest & { category?: string; keyword?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<DataCatalogItem>>>('/data/catalog', { params });
}

export function searchCatalog(keyword: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<DataCatalogItem>>>('/data/catalog/search', { params: { keyword, ...params } });
}

export function previewCatalogItem(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/data/catalog/${id}/preview`);
}

export function applyForAccess(id: string, reason: string) {
  return request.post<any, ApiResponse<null>>(`/data/catalog/${id}/apply`, { reason });
}

export function submitFeedback(id: string, rating: number, comment: string) {
  return request.post<any, ApiResponse<null>>(`/data/catalog/${id}/feedback`, { rating, comment });
}

// ==================== 元数据 ====================

export function listMetadata(params?: PaginatedRequest & { asset_id?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<MetadataRecord>>>('/data/metadata', { params });
}

export function createMetadata(data: Partial<MetadataRecord>) {
  return request.post<any, ApiResponse<MetadataRecord>>('/data/metadata', data);
}

export function getMetadata(id: string) {
  return request.get<any, ApiResponse<MetadataRecord>>(`/data/metadata/${id}`);
}

export function updateMetadata(id: string, data: Partial<MetadataRecord>) {
  return request.put<any, ApiResponse<MetadataRecord>>(`/data/metadata/${id}`, data);
}

export function getLineage(id: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/data/metadata/${id}/lineage`);
}

export function getVersions(id: string) {
  return request.get<any, ApiResponse<MetadataRecord[]>>(`/data/metadata/${id}/versions`);
}

// ==================== 标签 ====================

export function listTags(params?: PaginatedRequest & { dimension?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<Tag>>>('/data/tags', { params });
}

export function createTag(data: Partial<Tag>) {
  return request.post<any, ApiResponse<Tag>>('/data/tags', data);
}

export function deleteTag(id: string) {
  return request.delete<any, ApiResponse<null>>(`/data/tags/${id}`);
}

export function assignTag(assetId: string, tagId: string) {
  return request.post<any, ApiResponse<null>>(`/data/tags/assign`, { asset_id: assetId, tag_id: tagId });
}

export function removeTag(assetId: string, tagId: string) {
  return request.post<any, ApiResponse<null>>(`/data/tags/remove`, { asset_id: assetId, tag_id: tagId });
}

export function getDimensions() {
  return request.get<any, ApiResponse<Record<string, string[]>>>('/data/tags/dimensions');
}

// ==================== 质量 ====================

export function listQualityReports(params?: PaginatedRequest & { asset_id?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<QualityReport>>>('/data/quality', { params });
}

export function getQualityReport(id: string) {
  return request.get<any, ApiResponse<QualityReport>>(`/data/quality/${id}`);
}

export function runQualityCheck(assetId: string) {
  return request.post<any, ApiResponse<QualityReport>>('/data/quality/check', { asset_id: assetId });
}

export function getLatestQualityReport(assetId: string) {
  return request.get<any, ApiResponse<QualityReport>>(`/data/quality/latest`, { params: { asset_id: assetId } });
}
