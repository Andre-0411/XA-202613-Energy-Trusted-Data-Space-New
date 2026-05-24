/**
 * 数据服务市场 API
 * /api/v1/data/market - 可申请数据资产列表 / 资产详情 / 数据分类 / 市场统计
 */
import request from './request';
import type { ApiResponse, PaginatedResponse, PaginatedRequest, DataAsset } from '@/types/api';

// ==================== 市场资产类型 ====================

/** 市场统计数据 */
export interface MarketStats {
  total_assets: number;
  available_assets: number;
  monthly_new: number;
  hot_category: string;
}

/** 数据分类统计 */
export interface CategoryStat {
  category: string;
  label: string;
  count: number;
}

// ==================== API 函数 ====================

/**
 * 获取可申请的数据资产列表
 */
export function getMarketAssets(params?: PaginatedRequest & {
  keyword?: string;
  category?: string;
  sensitivity_level?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<DataAsset>>>('/data/market/assets', { params });
}

/**
 * 获取市场资产详情
 */
export function getMarketAssetDetail(id: string) {
  return request.get<any, ApiResponse<DataAsset>>(`/data/market/assets/${id}`);
}

/**
 * 获取数据分类列表（含各分类资产数量）
 */
export function getMarketCategories() {
  return request.get<any, ApiResponse<CategoryStat[]>>('/data/market/categories');
}

/**
 * 获取市场统计数据
 */
export function getMarketStats() {
  return request.get<any, ApiResponse<MarketStats>>('/data/market/stats');
}
