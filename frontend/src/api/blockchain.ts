/**
 * 区块链 API
 * NFT / 存证 / 智能合约 / 结算 / 链状态 / 证据链
 */
import request from './request';
import type {
  ApiResponse, PaginatedResponse, PaginatedRequest,
  NftAsset, Evidence, SmartContract, Settlement,
} from '@/types/api';

// ==================== NFT ====================

export function mintNft(data: { asset_id: string; metadata_uri?: string }) {
  return request.post<any, ApiResponse<NftAsset>>('/blockchain/nft/mint', data);
}

export function getNftDetail(tokenId: string) {
  return request.get<any, ApiResponse<NftAsset>>(`/blockchain/nft/${tokenId}`);
}

export function listNfts(params?: PaginatedRequest & { owner?: string; asset_id?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<NftAsset>>>('/blockchain/nft/', { params });
}

export function transferNft(tokenId: string, to: string) {
  return request.post<any, ApiResponse<null>>(`/blockchain/nft/${tokenId}/transfer`, { to });
}

// ==================== 存证 ====================

export function submitEvidence(data: { evidence_hash: string; evidence_type: string; description?: string }) {
  return request.post<any, ApiResponse<Evidence>>('/blockchain/evidence/', data);
}

export function getEvidenceDetail(id: string) {
  return request.get<any, ApiResponse<Evidence>>(`/blockchain/evidence/${id}`);
}

export function traceEvidence(hash: string) {
  return request.get<any, ApiResponse<Evidence[]>>('/blockchain/evidence/trace', { params: { hash } });
}

export function queryEvidenceRange(params?: PaginatedRequest & { evidence_type?: string }) {
  return request.get<any, ApiResponse<PaginatedResponse<Evidence>>>('/blockchain/evidence/', { params });
}

// ==================== 智能合约 ====================

/** 获取合约列表 — 后端返回数组（非分页） */
export function listContracts() {
  return request.get<any, ApiResponse<SmartContract[]>>('/blockchain/contracts/');
}

export function getContractDetail(id: string) {
  return request.get<any, ApiResponse<SmartContract>>(`/blockchain/contracts/${id}`);
}

export function invokeContract(id: string, method: string, args: Record<string, unknown>) {
  return request.post<any, ApiResponse<Record<string, unknown>>>(`/blockchain/contracts/${id}/invoke`, { method, args });
}

export function getContractTransactions(id: string, params?: PaginatedRequest) {
  return request.get<any, ApiResponse<PaginatedResponse<Record<string, unknown>>>>(`/blockchain/contracts/${id}/transactions`, { params });
}

// ==================== 结算 ====================

export function triggerSettlement(data: { from_org: string; to_org: string; amount: number; asset_id: string }) {
  return request.post<any, ApiResponse<Settlement>>('/blockchain/settlement', data);
}

export function getSettlementDetail(id: string) {
  return request.get<any, ApiResponse<Settlement>>(`/blockchain/settlement/${id}`);
}

export function disputeSettlement(id: string, reason: string) {
  return request.post<any, ApiResponse<null>>(`/blockchain/settlement/${id}/dispute`, { reason });
}

// ==================== 链状态 ====================

/** 获取链状态 — 公开端点 */
export function getChainStatus() {
  return request.get<any, ApiResponse<{
    connected: boolean;
    block_number: number;
    peer_count: number;
    chain_id: number;
    latest_block_time: number;
  }>>('/blockchain/contracts/chain/status');
}

// ==================== 合约部署 ====================

/** 部署单个合约 — 需要 admin 权限 */
export function deployContract(contractName: string, account?: string) {
  return request.post<any, ApiResponse<{
    name: string;
    address: string;
    deploy_tx_hash: string;
    version: string;
    status: string;
  }>>('/blockchain/contracts/deploy', { contract_name: contractName, account });
}

/** 一键部署全部合约 — 需要 admin 权限 */
export function deployAllContracts() {
  return request.post<any, ApiResponse<{
    results: Record<string, {
      name: string;
      address: string;
      deploy_tx_hash: string;
      version: string;
      status: string;
    }>;
  }>>('/blockchain/contracts/deploy-all');
}

// ==================== 证据链 ====================

/** 获取存证链 */
export function getEvidenceChain(resourceId: string) {
  return request.get<any, ApiResponse<{
    resource_id: string;
    resource_type: string;
    total_records: number;
    chain_valid: boolean;
    records: Record<string, unknown>[];
    first_hash: string;
    last_hash: string;
  }>>(`/blockchain/evidence/chain/${resourceId}`);
}

/** 验证存证链完整性 */
export function verifyEvidenceChain(resourceId: string) {
  return request.post<any, ApiResponse<{
    evidence_id: string;
    hash_valid: boolean;
    chain_valid: boolean;
    on_chain: boolean;
    errors: string[];
  }>>(`/blockchain/evidence/chain/${resourceId}/verify`);
}

/** 获取区块详情 */
export function getBlockDetail(blockNumber: number) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/blockchain/contracts/block/${blockNumber}`);
}

/** 获取交易详情 */
export function getTransactionDetail(txHash: string) {
  return request.get<any, ApiResponse<Record<string, unknown>>>(`/blockchain/contracts/transaction/${txHash}`);
}

// ==================== FISCO BCOS Channel ====================

/** 获取 FISCO BCOS 连接状态 */
export function getFiscoConnectionStatus() {
  return request.get<any, ApiResponse<{
    connected: boolean;
    current_node: string;
    block_number: number;
    peer_count: number;
    chain_id: string;
    group_id: number;
    stats: Record<string, unknown>;
  }>>('/blockchain/contracts/fisco/status');
}

/** 获取共识状态 */
export function getConsensusStatus() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/blockchain/contracts/fisco/consensus');
}

/** 获取同步状态 */
export function getSyncStatus() {
  return request.get<any, ApiResponse<Record<string, unknown>>>('/blockchain/contracts/fisco/sync');
}
