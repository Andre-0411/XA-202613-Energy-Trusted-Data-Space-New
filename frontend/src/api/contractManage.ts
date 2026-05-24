/**
 * 合约管理 API
 * /api/v1/contracts - 合约 CRUD、修订、区块链存证
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  Contract, ContractAmendment,
} from '@/types/api';

// ==================== 合约 CRUD ====================

export function createContract(data: {
  title: string;
  contract_type: string;
  party_a_org_id: string;
  party_b_org_id: string;
  party_b_user_id?: string;
  related_subscription_id?: string;
  related_product_id?: string;
  content: string;
  terms?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  effective_date?: string;
  expiration_date?: string;
}) {
  return request.post<any, ApiResponse<Contract>>('/contracts', data);
}

export function listContracts(params?: PaginatedRequest & {
  status?: string;
  contract_type?: string;
  party_a_org_id?: string;
  party_b_org_id?: string;
}) {
  return request.get<any, ApiResponse<PaginatedResponse<Contract>>>('/contracts', { params });
}

export function getContract(id: string) {
  return request.get<any, ApiResponse<Contract>>(`/contracts/${id}`);
}

export function updateContract(id: string, data: {
  title?: string;
  content?: string;
  terms?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  effective_date?: string;
  expiration_date?: string;
  status?: string;
}) {
  return request.put<any, ApiResponse<Contract>>(`/contracts/${id}`, data);
}

export function deleteContract(id: string) {
  return request.delete<any, ApiResponse<null>>(`/contracts/${id}`);
}

// ==================== 合约状态流转 ====================

export function submitContractForReview(id: string) {
  return request.post<any, ApiResponse<null>>(`/contracts/${id}/submit`);
}

export function activateContract(id: string) {
  return request.post<any, ApiResponse<null>>(`/contracts/${id}/activate`);
}

export function terminateContract(id: string, data?: {
  reason?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/contracts/${id}/terminate`, data);
}

// ==================== 合约修订 ====================

export function createAmendment(contractId: string, data: {
  reason: string;
  changes: Record<string, unknown>;
  previous_terms: Record<string, unknown>;
  new_terms: Record<string, unknown>;
}) {
  return request.post<any, ApiResponse<ContractAmendment>>(`/contracts/${contractId}/amendments`, data);
}

export function listAmendments(contractId: string, params?: PaginatedRequest & { status?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<ContractAmendment>>>(`/contracts/${contractId}/amendments`, { params });
}

export function getAmendment(contractId: string, amendmentId: string) {
  return request.get<any, ApiResponse<ContractAmendment>>(`/contracts/${contractId}/amendments/${amendmentId}`);
}

export function approveAmendment(contractId: string, amendmentId: string) {
  return request.post<any, ApiResponse<null>>(`/contracts/${contractId}/amendments/${amendmentId}/approve`);
}

export function rejectAmendment(contractId: string, amendmentId: string, data?: {
  reason?: string;
}) {
  return request.post<any, ApiResponse<null>>(`/contracts/${contractId}/amendments/${amendmentId}/reject`, data);
}

// ==================== 区块链存证 ====================

export function anchorContractOnChain(id: string) {
  return request.post<any, ApiResponse<{
    tx_hash: string;
    contract_address: string;
    block_number: number;
  }>>(`/contracts/${id}/anchor`);
}

export function verifyContractOnChain(id: string) {
  return request.get<any, ApiResponse<{
    verified: boolean;
    tx_hash: string;
    block_number: number;
    chain_data: Record<string, unknown>;
  }>>(`/contracts/${id}/verify`);
}
