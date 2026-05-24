/**
 * 认证 API
 * 登录 / DID登录 / 证书登录 / MFA验证 / 登出 / 刷新Token / 会话查询
 * MFA 设置/启用/禁用 / SSO 授权/Token/用户信息
 */
import request from './request';
import type {
  ApiResponse, LoginRequest, LoginResponse, DIDLoginRequest,
  CertificateLoginRequest, MfaVerifyRequest, SessionInfo,
} from '@/types/api';

// ===== MFA 相关类型 =====
export interface MfaSetupResponse {
  secret: string;
  qr_code_url: string;
  backup_codes: string[];
  method: string;
  created_at: string;
}

export interface MfaStatusResponse {
  user_id: string;
  enabled: boolean;
  method: string | null;
  backup_codes_remaining: number;
  last_verified_at: string | null;
}

export interface MfaVerifyResponse {
  verified: boolean;
  session_id: string | null;
  message: string;
}

export interface MfaBackupCodesResponse {
  backup_codes: string[];
  regenerated_at: string;
}

// ===== SSO 相关类型 =====
export interface SSOProvider {
  provider_id: string;
  name: string;
  protocol: string;
  client_id?: string;
  authorize_url?: string;
  redirect_uri?: string;
  scopes: string[];
  enabled: boolean;
}

export interface SSOAuthorizeResponse {
  authorize_url: string;
  state: string;
}

export interface SSOTokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  id_token?: string;
  user_info?: Record<string, any>;
}

export interface SSOUserInfo {
  provider_id: string;
  sub: string;
  name?: string;
  email?: string;
  picture?: string;
  raw_claims: Record<string, any>;
}

export interface SSOSessionInfo {
  session_id: string;
  user_id: string;
  provider_id: string;
  created_at: string;
  expires_at: string;
  ip_address?: string;
  user_agent?: string;
}

/** 用户名密码登录 */
export function login(data: LoginRequest) {
  return request.post<any, ApiResponse<LoginResponse>>('/auth/login', data);
}

/** DID 签名登录 */
export function loginWithDID(data: DIDLoginRequest) {
  return request.post<any, ApiResponse<LoginResponse>>('/auth/login/did', data);
}

/** 证书登录 */
export function loginWithCertificate(data: CertificateLoginRequest) {
  return request.post<any, ApiResponse<LoginResponse>>('/auth/login/certificate', data);
}

/** MFA 二次验证 */
export function mfaVerify(data: MfaVerifyRequest) {
  return request.post<any, ApiResponse<LoginResponse>>('/auth/mfa/verify', data);
}

/** 登出 */
export function logout() {
  return request.post<any, ApiResponse<null>>('/auth/logout');
}

/** 刷新 Token */
export function refreshToken(refresh_token: string) {
  return request.post<any, ApiResponse<LoginResponse>>('/auth/refresh', { refresh_token });
}

/** 获取当前会话 */
export function getSession() {
  return request.get<any, ApiResponse<SessionInfo>>('/auth/session');
}

/** 修改密码 */
export function changePassword(oldPassword: string, newPassword: string) {
  return request.post<any, ApiResponse<null>>('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

// ===== MFA API =====

/** MFA 设置（生成密钥和备份码） */
export function mfaSetup(userId: string, method: string = 'totp') {
  return request.post<any, ApiResponse<MfaSetupResponse>>('/auth/mfa/setup', {
    user_id: userId,
    method,
  });
}

/** MFA 启用 */
export function mfaEnable(userId: string, code: string) {
  return request.post<any, ApiResponse<{ success: boolean; message: string }>>('/auth/mfa/enable', {
    user_id: userId,
    code,
  });
}

/** MFA 禁用 */
export function mfaDisable(userId: string, password: string, code?: string) {
  return request.post<any, ApiResponse<{ success: boolean; message: string }>>('/auth/mfa/disable', {
    user_id: userId,
    password,
    code,
  });
}

/** 获取 MFA 状态 */
export function getMfaStatus(userId: string) {
  return request.get<any, ApiResponse<MfaStatusResponse>>(`/auth/mfa/status/${userId}`);
}

/** 备份码验证 */
export function verifyBackupCode(userId: string, backupCode: string) {
  return request.post<any, ApiResponse<MfaVerifyResponse>>('/auth/mfa/backup-codes/verify', {
    user_id: userId,
    backup_code: backupCode,
  });
}

/** 重新生成备份码 */
export function regenerateBackupCodes(userId: string) {
  return request.post<any, ApiResponse<MfaBackupCodesResponse>>('/auth/mfa/backup-codes/regenerate', null, {
    params: { user_id: userId },
  });
}

// ===== SSO API =====

/** 列出 SSO 提供者 */
export function listSSOProviders() {
  return request.get<any, ApiResponse<{ providers: SSOProvider[] }>>('/auth/sso/providers');
}

/** 获取 SSO 提供者 */
export function getSSOProvider(providerId: string) {
  return request.get<any, ApiResponse<SSOProvider>>(`/auth/sso/providers/${providerId}`);
}

/** SSO 授权 */
export function ssoAuthorize(providerId: string, redirectUri?: string, state?: string) {
  return request.post<any, ApiResponse<SSOAuthorizeResponse>>('/auth/sso/authorize', {
    provider_id: providerId,
    redirect_uri: redirectUri,
    state,
  });
}

/** SSO Token 交换 */
export function ssoExchangeToken(providerId: string, code: string, state?: string, redirectUri?: string) {
  return request.post<any, ApiResponse<SSOTokenResponse>>('/auth/sso/token', {
    provider_id: providerId,
    code,
    state,
    redirect_uri: redirectUri,
  });
}

/** 获取 SSO 用户信息 */
export function getSSOUserInfo(accessToken: string) {
  return request.get<any, ApiResponse<SSOUserInfo>>('/auth/sso/userinfo', {
    params: { access_token: accessToken },
  });
}

/** 列出 SSO 会话 */
export function listSSOSessions(userId?: string) {
  return request.get<any, ApiResponse<{ sessions: SSOSessionInfo[] }>>('/auth/sso/sessions', {
    params: userId ? { user_id: userId } : {},
  });
}

/** 删除 SSO 会话 */
export function invalidateSSOSession(sessionId: string) {
  return request.delete<any, ApiResponse<{ success: boolean }>>(`/auth/sso/sessions/${sessionId}`);
}
