/**
 * HTTP 请求封装
 * 基于 axios，请求/响应拦截器，Bearer token 自动注入，CSRF token 自动注入，统一错误处理
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const TOKEN_KEY = 'eds_token';
const REFRESH_TOKEN_KEY = 'eds_refresh_token';
const CSRF_COOKIE_NAME = 'csrftoken';
const CSRF_HEADER_NAME = 'X-CSRFToken';

// 防止 token 刷新期间重复发起刷新请求
let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

/**
 * 从 Cookie 中读取指定名称的值
 */
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

/** axios 实例 */
const request = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==================== 请求拦截器 ====================

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Bearer token 注入
    const token = localStorage.getItem(TOKEN_KEY);
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // CSRF token 注入（非安全方法需要）
    const method = (config.method || 'get').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
      const csrfToken = getCookie(CSRF_COOKIE_NAME);
      if (csrfToken && config.headers) {
        config.headers[CSRF_HEADER_NAME] = csrfToken;
      }
    }

    return config;
  },
  (error: AxiosError) => {
    console.error('[Request Error]', error);
    return Promise.reject(error);
  },
);

// ==================== 响应拦截器 ====================

request.interceptors.response.use(
  (response) => {
    // 如果后端返回 { code, message, data, timestamp }，直接返回 data
    const body = response.data;
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) {
        return body;
      }
      // 业务错误
      console.error(`[Business Error] code=${body.code}, message=${body.message}`);
      return Promise.reject(new Error(body.message || '业务错误'));
    }
    return response.data;
  },
  async (error: AxiosError) => {
    if (!error.response) {
      console.error('[Network Error]', error.message);
      return Promise.reject(new Error('网络连接失败，请检查网络设置'));
    }

    const { status, data } = error.response;
    const detail = (data as Record<string, unknown>)?.detail;
    const errorMsg = typeof detail === 'string' ? detail : (data as Record<string, unknown>)?.message || '请求失败';

    switch (status) {
      case 401: {
        // 认证相关接口（login/refresh/mfa）的 401 是"凭据错误"，直接返回错误，不做刷新/跳转
        const requestUrl = error.config?.url || '';
        const isAuthEndpoint = /\/auth\/(login|refresh|mfa|register)/.test(requestUrl);

        if (isAuthEndpoint) {
          // 登录失败 / 刷新失败 / MFA 失败 → 直接抛出，让调用方处理
          return Promise.reject(new Error(errorMsg as string || '认证失败，请检查凭据'));
        }

        // 非认证接口的 401 → Token 过期，尝试刷新（防止并发重复刷新）
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        if (!refreshToken) {
          localStorage.removeItem(TOKEN_KEY);
          window.location.href = '/login';
          return Promise.reject(new Error('登录已过期，请重新登录'));
        }

        if (isRefreshing) {
          // 等待刷新完成后重试
          return new Promise((resolve, reject) => {
            pendingRequests.push((newToken: string) => {
              if (error.config) {
                error.config.headers.Authorization = `Bearer ${newToken}`;
                resolve(request(error.config));
              } else {
                reject(new Error('请求配置缺失'));
              }
            });
          });
        }

        isRefreshing = true;
        try {
          const res = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newToken = res.data?.data?.access_token || res.data?.access_token;
          const newRefreshToken = res.data?.data?.refresh_token || res.data?.refresh_token;
          if (newToken) {
            localStorage.setItem(TOKEN_KEY, newToken);
            if (newRefreshToken) {
              localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
            }
            // 释放等待队列
            pendingRequests.forEach((cb) => cb(newToken));
            pendingRequests = [];
            // 重试原请求
            if (error.config) {
              error.config.headers.Authorization = `Bearer ${newToken}`;
              return request(error.config);
            }
          }
        } catch {
          // 刷新失败，清除 token 并跳转登录
          pendingRequests = [];
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(REFRESH_TOKEN_KEY);
          window.location.href = '/login';
        } finally {
          isRefreshing = false;
        }
        return Promise.reject(new Error('登录已过期，请重新登录'));
      }
      case 403:
        console.error('[Forbidden]', errorMsg);
        return Promise.reject(new Error('权限不足'));
      case 404:
        console.error('[Not Found]', errorMsg);
        return Promise.reject(new Error('资源不存在'));
      case 422:
        console.error('[Validation Error]', errorMsg);
        return Promise.reject(new Error('请求参数验证失败'));
      case 429:
        console.error('[Rate Limited]');
        return Promise.reject(new Error('请求过于频繁，请稍后再试'));
      case 500:
        console.error('[Server Error]', errorMsg);
        return Promise.reject(new Error('服务器内部错误'));
      default:
        console.error(`[HTTP ${status}]`, errorMsg);
        return Promise.reject(new Error(errorMsg as string));
    }
  },
);

// ==================== 工具方法 ====================

/** 设置 token */
export function setTokens(accessToken: string, refreshToken?: string): void {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

/** 清除 token */
export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/** 获取当前 access token */
export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export default request;
