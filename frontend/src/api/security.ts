/**
 * 安全管控 API
 * 策略 / DID / VC / 密钥 / 威胁 / 国密 / ZKP / ABAC / 凭证链
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  SecurityPolicy, DidDocument, VcRecord, KeyInfo,
  ThreatEvent, CryptoResult, ZkpProof,
} from '@/types/api';

// ==================== 安全策略 ====================

export function listPolicies(params?: PaginatedRequest & { policy_type?: string; status?: string }) {
  return request.get<any, ApiResponse<SecurityPolicy[]>>('/security/policies', { params });
}

export function createPolicy(data: Partial<SecurityPolicy>) {
  return request.post<any, ApiResponse<SecurityPolicy>>('/security/policies', data);
}

export function getPolicy(id: string) {
  return request.get<any, ApiResponse<SecurityPolicy>>(`/security/policies/${id}`);
}

export function updatePolicy(id: string, data: Partial<SecurityPolicy>) {
  return request.put<any, ApiResponse<SecurityPolicy>>(`/security/policies/${id}`, data);
}

export function deletePolicy(id: string) {
  return request.delete<any, ApiResponse<null>>(`/security/policies/${id}`);
}

export function evaluatePermission(data: { subject_did: string; resource_type: string; resource_id: string; action: string; context?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<{ allowed: boolean; deny_reason?: string }>>('/security/policies/evaluate', data);
}

// ==================== DID ====================

export function createDid(data: { method?: string; public_key: string; controller?: string }) {
  return request.post<any, ApiResponse<DidDocument>>('/security/did/create', data);
}

export function createFiscoDid(data: { public_key: string; controller?: string; chain_id?: string; node_url?: string }) {
  return request.post<any, ApiResponse<DidDocument>>('/security/did/create-fisco', data);
}

export function resolveDid(did: string) {
  return request.get<any, ApiResponse<DidDocument>>(`/security/did/${did}`);
}

export function updateDidDocument(did: string, data: { service_endpoints?: Record<string, unknown>[]; add_authentication?: Record<string, unknown>[]; remove_authentication?: string[] }) {
  return request.put<any, ApiResponse<DidDocument>>(`/security/did/${did}`, data);
}

export function deactivateDid(did: string) {
  return request.post<any, ApiResponse<{ did: string; status: string }>>(`/security/did/${did}/deactivate`);
}

// ==================== ABAC 动态授权 ====================

export function createTemporaryAuth(data: { subject_did: string; resource_type: string; resource_id: string; action: string; expires_in_seconds?: number; reason?: string }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/security/abac/temp-auth', data);
}

export function listTemporaryAuths(params?: { subject_did?: string; status?: string }) {
  return request.get<any, ApiResponse<Record<string, unknown>[]>>('/security/abac/temp-auth', { params });
}

export function revokeTemporaryAuth(authId: string) {
  return request.delete<any, ApiResponse<null>>(`/security/abac/temp-auth/${authId}`);
}

export function createConditionalAuth(data: { subject_did: string; resource_type: string; resource_id: string; action: string; conditions: Record<string, unknown>; reason?: string }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/security/abac/cond-auth', data);
}

export function listConditionalAuths(params?: { subject_did?: string; status?: string }) {
  return request.get<any, ApiResponse<Record<string, unknown>[]>>('/security/abac/cond-auth', { params });
}

export function revokeConditionalAuth(authId: string) {
  return request.delete<any, ApiResponse<null>>(`/security/abac/cond-auth/${authId}`);
}

// ==================== VC ====================

export function issueVc(data: { issuer_did: string; subject_did: string; vc_type: string; claims: Record<string, unknown>; expires_at?: string }) {
  return request.post<any, ApiResponse<Record<string, unknown>>>('/security/vc/issue', data);
}

export function verifyVc(data: { vc_id: string; vc_data?: Record<string, unknown> }) {
  return request.post<any, ApiResponse<{ overall_valid: boolean; errors: string[] }>>('/security/vc/verify', data);
}

export function revokeVc(vcId: string) {
  return request.post<any, ApiResponse<{ vc_id: string; status: string }>>(`/security/vc/${vcId}/revoke`);
}

export function listVcs(params?: PaginatedRequest & { issuer_did?: string; subject_did?: string; status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<VcRecord>>>('/security/vc/list', { params });
}

// ==================== 密钥管理 ====================

export function listKeys(params?: PaginatedRequest & { algorithm?: string; status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<KeyInfo>>>('/security/keys', { params });
}

export function generateKey(data: { algorithm: string; hierarchy_level: string; purpose: string; parent_key_id?: string }) {
  return request.post<any, ApiResponse<KeyInfo>>('/security/keys/generate', data);
}

export function getKey(keyId: string) {
  return request.get<any, ApiResponse<KeyInfo>>(`/security/keys/${keyId}`);
}

export function rotateKey(keyId: string) {
  return request.post<any, ApiResponse<{ old_key_id: string; new_key_id: string }>>(`/security/keys/${keyId}/rotate`);
}

export function getKeyAuditLog(keyId: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<Record<string, unknown>>>>(`/security/keys/${keyId}/audit`, { params });
}

export function shamirSplit(data: { secret: string; n: number; k: number }) {
  return request.post<any, ApiResponse<{ shares: Record<string, unknown>[] }>>('/security/keys/shamir/split', data);
}

export function shamirCombine(data: { shares: Record<string, unknown>[] }) {
  return request.post<any, ApiResponse<{ recovered: boolean }>>('/security/keys/shamir/combine', data);
}

// ==================== 威胁检测 ====================

export function listThreats(params?: PaginatedRequest & { threat_type?: string; severity?: string; status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ThreatEvent>>>('/security/threats', { params });
}

export function detectThreats() {
  return request.post<any, ApiResponse<{ threats_detected: number }>>('/security/threats/detect');
}

export function getThreat(id: string) {
  return request.get<any, ApiResponse<ThreatEvent>>(`/security/threats/${id}`);
}

export function resolveThreat(id: string, data: { resolution: string; description?: string }) {
  return request.put<any, ApiResponse<null>>(`/security/threats/${id}/resolve`, data);
}

export function getSecurityDashboard() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/security/threats/dashboard');
}

// ==================== 国密算法 ====================

export function sm2Sign(data: { private_key: string; public_key: string; data: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm2/sign', data);
}

export function sm2Verify(data: { public_key: string; data: string; signature: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm2/verify', data);
}

export function sm2Encrypt(data: { public_key: string; plaintext: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm2/encrypt', data);
}

export function sm2Decrypt(data: { private_key: string; public_key: string; ciphertext: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm2/decrypt', data);
}

export function sm3Hash(data: { data: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm3/hash', data);
}

export function sm4Encrypt(data: { key: string; plaintext: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm4/encrypt', data);
}

export function sm4Decrypt(data: { key: string; ciphertext: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm4/decrypt', data);
}

export function sm9Sign(data: { master_private_key: string; data: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm9/sign', data);
}

export function sm9Verify(data: { master_public_key: string; data: string; signature: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/sm9/verify', data);
}

export function zucEncrypt(data: { key: string; iv: string; plaintext: string; key_id?: string }) {
  return request.post<any, ApiResponse<CryptoResult>>('/security/gmssl/zuc/encrypt', data);
}

// ==================== ZKP ====================

export function groth16Prove(data: { circuit_id: string; private_input: Record<string, unknown>; public_input: Record<string, unknown> }) {
  return request.post<any, ApiResponse<ZkpProof>>('/security/zkp/groth16/prove', data);
}

export function groth16Verify(data: { proof: Record<string, unknown>; public_signals: string[] }) {
  return request.post<any, ApiResponse<{ is_valid: boolean }>>('/security/zkp/groth16/verify', data);
}

export function bbsSign(data: { private_key: string; messages: string[] }) {
  return request.post<any, ApiResponse<ZkpProof>>('/security/zkp/bbs/sign', data);
}

export function bbsVerify(data: { public_key: string; messages: string[]; signature: Record<string, unknown> }) {
  return request.post<any, ApiResponse<{ is_valid: boolean }>>('/security/zkp/bbs/verify', data);
}

export function bulletproofsProve(data: { value: number; min_val?: number; max_val?: number }) {
  return request.post<any, ApiResponse<ZkpProof>>('/security/zkp/bulletproofs/prove', data);
}

export function bulletproofsVerify(data: { proof: Record<string, unknown>; min_val?: number; max_val?: number }) {
  return request.post<any, ApiResponse<{ is_valid: boolean }>>('/security/zkp/bulletproofs/verify', data);
}

// ==================== ABAC 属性访问控制 ====================

/** 获取 ABAC 属性定义列表 */
export function listAbacAttributes() {
  return request.get<any, ApiResponse<Record<string, unknown>[]>>('/security/policies/abac/attributes');
}

/** 创建 ABAC 策略（支持 AND/OR/NOT 逻辑） */
export function createAbacPolicy(data: {
  name: string;
  rules: Record<string, unknown>[];
  priority?: number;
  target?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<SecurityPolicy>>('/security/policies/abac', data);
}

/** 评估 ABAC 访问请求 */
export function evaluateAbacAccess(data: {
  subject_did: string;
  subject_attributes: Record<string, unknown>;
  resource_type: string;
  resource_id: string;
  resource_attributes: Record<string, unknown>;
  action: string;
  environment?: Record<string, unknown>;
  context?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<{
    allowed: boolean;
    matched_policies: string[];
    evaluation_details: Record<string, unknown>[];
    deny_reason?: string;
    conflicts: Record<string, unknown>[];
  }>>('/security/policies/abac/evaluate', data);
}

/** 模拟 ABAC 策略评估 */
export function simulateAbacEvaluation(data: {
  subject_did: string;
  subject_attributes: Record<string, unknown>;
  resource_type: string;
  resource_id: string;
  resource_attributes: Record<string, unknown>;
  action: string;
  context?: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<{
    simulation: boolean;
    result: Record<string, unknown>;
    recommendation: string;
  }>>('/security/policies/abac/simulate', data);
}

// ==================== 凭证链验证 ====================

/** 验证凭证链 */
export function verifyCredentialChain(vcIds: string[]) {
  return request.post<any, ApiResponse<{
    chain_valid: boolean;
    total_credentials: number;
    verified_credentials: number;
    results: Record<string, unknown>[];
    errors: string[];
  }>>('/security/vc/chain/verify', { vc_ids: vcIds });
}

/** 获取凭证签发者链 */
export function getIssuerChain(vcId: string) {
  return request.get<any, ApiResponse<{
    vc_id: string;
    chain_length: number;
    chain: Record<string, unknown>[];
    root_issuer: string;
  }>>(`/security/vc/${vcId}/issuer-chain`);
}
