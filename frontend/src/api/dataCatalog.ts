/**
 * 数据目录 API
 * 数据分类、搜索、血缘关系
 */
import request from './request';
import type { ApiResponse, PaginatedResponse } from '@/types/api';

// ==================== 类型定义 ====================

export interface CatalogItem {
  id: string;
  name: string;
  description?: string;
  category: string;
  subcategory?: string;
  classification_level: number;
  sensitivity_label: string;
  owner_name?: string;
  organization_name?: string;
  record_count: number;
  size_bytes: number;
  storage_format: string;
  tags: string[];
  avg_rating: number;
  rating_count: number;
  published_at?: string;
  status: string;
}

export interface SearchResult {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: CatalogItem[];
  facets: SearchFacets;
  query_time_ms: number;
}

export interface SearchFacets {
  categories: Record<string, number>;
  classification_levels: Record<string, number>;
  organizations: Record<string, number>;
  tags: Record<string, number>;
}

export interface SearchSuggestion {
  keyword: string;
  category?: string;
  count: number;
}

export interface DataClassification {
  category: string;
  classification_level: number;
  sensitivity_label: string;
  sm3_hash?: string;
  confidence: number;
  matched_rules: Array<{
    rule_id: string;
    rule_name: string;
    score: number;
  }>;
  classified_at: string;
  classified_by: string;
}

export interface DataLineageNode {
  id: string;
  name: string;
  type: string;
  metadata?: Record<string, any>;
}

export interface DataLineageEdge {
  source: string;
  target: string;
  label?: string;
  metadata?: Record<string, any>;
}

export interface DataLineageGraph {
  nodes: DataLineageNode[];
  edges: DataLineageEdge[];
  center_node_id?: string;
}

export interface QualityDimension {
  dimension: string;
  score: number;
  weight: number;
  details?: Record<string, any>;
  check_items: Array<{
    name: string;
    status: string;
    score: number;
  }>;
}

export interface QualityAssessment {
  id: string;
  asset_id: string;
  asset_name?: string;
  total_score: number;
  grade: string;
  dimensions: QualityDimension[];
  assessed_at: string;
  assessed_by: string;
  status: string;
}

// ==================== 数据搜索 ====================

/**
 * 搜索数据目录
 */
export function searchCatalog(params: {
  keyword?: string;
  category?: string;
  classification_level?: number;
  min_level?: number;
  max_level?: number;
  organization_id?: string;
  tags?: string[];
  status?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}) {
  return request.get<any, ApiResponse<SearchResult>>('/data/catalog/search', { params });
}

/**
 * 获取搜索建议
 */
export function getSearchSuggestions(keyword: string, limit: number = 10) {
  return request.get<any, ApiResponse<SearchSuggestion[]>>('/data/catalog/suggestions', {
    params: { keyword, limit },
  });
}

/**
 * 浏览数据目录
 */
export function browseCatalog(params?: {
  category?: string;
  classification_level?: number;
  organization_id?: string;
  page?: number;
  page_size?: number;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<CatalogItem>>>('/data/catalog', { params });
}

/**
 * 预览数据
 */
export function previewCatalogItem(id: string) {
  return request.get<any, ApiResponse<{
    asset_id: string;
    total_records: number;
    preview_records: Record<string, any>[];
    fields: Array<{ name: string; type: string }>;
    masked: boolean;
  }>>(`/data/catalog/${id}/preview`);
}

/**
 * 申请使用数据
 */
export function applyForAccess(id: string, purpose: string, durationDays: number = 30) {
  return request.post<any, ApiResponse<{ success: boolean; message: string }>>(
    `/data/catalog/${id}/apply`,
    null,
    { params: { purpose, duration_days: durationDays } }
  );
}

/**
 * 提交评价反馈
 */
export function submitFeedback(id: string, rating: number, comment: string) {
  return request.post<any, ApiResponse<{ success: boolean; message: string }>>(
    `/data/catalog/${id}/feedback`,
    null,
    { params: { rating, comment } }
  );
}

// ==================== 数据分类 ====================

/**
 * 自动分类数据
 */
export function classifyData(params: {
  data_name: string;
  data_description?: string;
  data_fields?: string[];
  category_hint?: string;
}) {
  return request.post<any, ApiResponse<DataClassification>>('/data/classify', params);
}

/**
 * 批量分类
 */
export function classifyBatch(items: Array<{
  name: string;
  description?: string;
  fields?: string[];
  category_hint?: string;
}>) {
  return request.post<any, ApiResponse<DataClassification[]>>('/data/classify/batch', { items });
}

/**
 * 获取分类规则
 */
export function getClassificationRules() {
  return request.get<any, ApiResponse<Array<{
    rule_id: string;
    name: string;
    category: string;
    keywords: string[];
    sensitivity_level: number;
    auto_classify: boolean;
    priority: number;
  }>>>('/data/classification-rules');
}

/**
 * 验证数据完整性
 */
export function verifyIntegrity(params: {
  data_name: string;
  data_fields: string[];
  expected_hash: string;
}) {
  return request.post<any, ApiResponse<{ valid: boolean }>>('/data/classify/verify', params);
}

// ==================== 数据质量 ====================

/**
 * 评估数据质量
 */
export function assessQuality(params: {
  asset_id: string;
  asset_name?: string;
  dimensions?: string[];
  sample_size?: number;
}) {
  return request.post<any, ApiResponse<QualityAssessment>>('/data/quality/check', params);
}

/**
 * 获取质量报告
 */
export function getQualityReport(reportId: string) {
  return request.get<any, ApiResponse<QualityAssessment>>(`/data/quality/reports/${reportId}`);
}

/**
 * 获取资产最新质量报告
 */
export function getLatestQualityReport(assetId: string) {
  return request.get<any, ApiResponse<QualityAssessment>>(`/data/quality/latest/${assetId}`);
}

/**
 * 列出质量报告
 */
export function listQualityReports(params?: {
  asset_id?: string;
  min_score?: number;
  page?: number;
  page_size?: number;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<QualityAssessment>>>('/data/quality/reports', { params });
}

/**
 * 获取质量统计
 */
export function getQualityStatistics() {
  return request.get<any, ApiResponse<{
    total_assets: number;
    checked_assets: number;
    avg_score: number;
    grade_distribution: Record<string, number>;
    dimension_averages: Record<string, number>;
    trend: Array<{
      date: string;
      total_score: number;
      completeness: number;
      accuracy: number;
      consistency: number;
      timeliness: number;
      uniqueness: number;
    }>;
  }>>('/data/quality/statistics');
}

// ==================== 数据血缘 ====================

/**
 * 获取数据血缘图
 */
export function getDataLineage(assetId: string) {
  return request.get<any, ApiResponse<DataLineageGraph>>(`/data/lineage/${assetId}`);
}

/**
 * 获取元数据版本历史
 */
export function getMetadataVersions(metadataId: string) {
  return request.get<any, ApiResponse<Array<{
    id: string;
    version: number;
    content: Record<string, any>;
    created_at: string;
    created_by?: string;
  }>>>(`/data/metadata/${metadataId}/versions`);
}
