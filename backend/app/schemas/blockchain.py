"""
区块链 Schema
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== NFT 相关 Schema ====================


class NftMintRequest(BaseModel):
    """铸造 NFT 请求"""
    asset_id: str = Field(description="关联数据资产 ID")
    category: str = Field(description="资产大类")
    classification_level: int = Field(ge=1, le=4, description="敏感级别")
    evidence_hash: str = Field(description="确权证据 SM3 哈希")
    certificate_url: Optional[str] = Field(default=None, description="确权证书 URL")


class NftResponse(BaseModel):
    """NFT 响应"""
    id: str
    token_id: str
    asset_id: str
    owner_did: str
    creator_did: str
    token_uri: Optional[str] = None
    evidence_hash: str
    certificate_url: Optional[str] = None
    tx_hash: str
    block_number: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NftTransferRequest(BaseModel):
    """NFT 转移请求"""
    to_did: str = Field(description="接收方 DID")
    signature: str = Field(description="所有者 SM2 签名")


class NftAuthorizeRequest(BaseModel):
    """NFT 授权请求"""
    authorized_did: str = Field(description="被授权方 DID")
    permission_type: str = Field(default="use", description="权限类型: use/view/transfer")
    duration_seconds: Optional[int] = Field(default=None, ge=0, description="授权时长（秒），None 为永久")


class NftRevokeRequest(BaseModel):
    """NFT 撤销授权请求"""
    authorized_did: str = Field(description="被授权方 DID")


class NftAuthorization(BaseModel):
    """NFT 授权记录"""
    auth_id: str = Field(description="授权 ID")
    token_id: str = Field(description="NFT Token ID")
    owner_did: str = Field(description="授权方 DID")
    authorized_did: str = Field(description="被授权方 DID")
    permission_type: str = Field(description="权限类型")
    duration_seconds: Optional[int] = Field(default=None, description="授权时长")
    created_at: str = Field(description="授权时间")
    expires_at: Optional[str] = Field(default=None, description="过期时间")
    is_active: bool = Field(default=True, description="是否有效")
    tx_hash: str = Field(default="", description="链上交易哈希")


class NftCategoryStats(BaseModel):
    """NFT 分类统计"""
    category: str = Field(description="分类名称")
    count: int = Field(description="数量")


class NftStatsResponse(BaseModel):
    """NFT 统计响应"""
    total_nfts: int = Field(description="NFT 总量")
    minted_today: int = Field(description="今日铸造量")
    active_authorizations: int = Field(description="活跃授权数")
    category_stats: list[NftCategoryStats] = Field(default_factory=list, description="分类统计")
    owner_filter: Optional[str] = Field(default=None, description="所有者筛选条件")


# ==================== 存证相关 Schema ====================


class EvidenceCreate(BaseModel):
    """提交存证请求"""
    node_type: str = Field(description="存证节点类型")
    resource_id: str = Field(description="关联资源 ID")
    resource_type: str = Field(description="资源类型")
    data_hash: str = Field(description="数据 SM3 哈希")
    evidence_data: dict = Field(description="存证数据")
    operator_did: Optional[str] = Field(default=None, description="操作主体 DID")
    operator_signature: Optional[str] = Field(default=None, description="操作者签名")


class EvidenceResponse(BaseModel):
    """存证响应"""
    id: str
    node_type: str
    resource_id: str
    resource_type: str
    data_hash: str
    schema_version: str
    evidence_data: dict
    tx_hash: str
    block_number: Optional[int] = None
    timestamp: int
    prev_hash: Optional[str] = None
    chain_hash: Optional[str] = None
    operator_did: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceBatchSubmit(BaseModel):
    """批量存证请求"""
    items: list[EvidenceCreate] = Field(description="存证条目列表", min_length=1, max_length=100)


class ChainVerificationResponse(BaseModel):
    """链式哈希验证响应"""
    resource_id: str = Field(description="资源 ID")
    chain_length: int = Field(description="链长度")
    is_valid: bool = Field(description="链是否完整有效")
    invalid_nodes: list[dict] = Field(default_factory=list, description="无效节点列表")
    chain_records: list[EvidenceResponse] = Field(default_factory=list, description="链记录")


class EvidenceBatchResult(BaseModel):
    """批量存证结果"""
    total: int = Field(description="总条数")
    success_count: int = Field(description="成功条数")
    failure_count: int = Field(description="失败条数")
    results: list[dict] = Field(description="每条存证的处理结果")


class TimestampResponse(BaseModel):
    """存证时间戳响应（RFC3161 风格）"""
    evidence_id: str = Field(description="存证 ID")
    tx_hash: str = Field(description="链上交易哈希")
    block_number: Optional[int] = Field(default=None, description="区块高度")
    evidence_timestamp: int = Field(description="存证时间戳")
    chain_timestamp: Optional[str] = Field(default=None, description="链上区块时间")
    tsa_hash: str = Field(description="TSA 时间戳哈希")
    tsa_version: str = Field(default="v1.0", description="TSA 版本")
    is_valid: bool = Field(description="存证是否有效")
    chain_confirmed: bool = Field(description="链上是否确认")
    hash_match: bool = Field(description="哈希是否匹配")


# ==================== 结算相关 Schema ====================


class SettlementRequest(BaseModel):
    """结算请求"""
    subscription_id: str = Field(description="订阅 ID")
    amount: float = Field(gt=0, description="结算金额")
    billing_period: str = Field(description="计费周期")


class SettlementBatchRequest(BaseModel):
    """批量结算请求"""
    items: list[SettlementRequest] = Field(description="结算条目列表", min_length=1, max_length=100)


class SettlementBatchResult(BaseModel):
    """批量结算结果"""
    total: int = Field(description="总条数")
    success_count: int = Field(description="成功条数")
    failure_count: int = Field(description="失败条数")
    total_amount: float = Field(description="总金额")
    results: list[dict] = Field(description="每条结算的处理结果")


class SettlementReconciliationItem(BaseModel):
    """对账明细项"""
    billing_id: str = Field(default="", description="数据库结算 ID")
    tx_hash: str = Field(default="", description="链上交易哈希")
    db_amount: float = Field(description="数据库金额")
    chain_amount: float = Field(description="链上金额")
    amount_match: bool = Field(description="金额是否一致")
    subscription_id: str = Field(default="", description="订阅 ID")
    payment_status: str = Field(default="", description="支付状态")


class SettlementReconciliation(BaseModel):
    """对账结果"""
    billing_period: str = Field(description="计费周期")
    subscription_id_filter: Optional[str] = Field(default=None, description="订阅 ID 筛选")
    total_db_records: int = Field(description="数据库记录数")
    total_chain_records: int = Field(description="链上记录数")
    match_count: int = Field(description="一致记录数")
    discrepancy_count: int = Field(description="差异记录数")
    is_consistent: bool = Field(description="是否完全一致")
    reconciled: list[SettlementReconciliationItem] = Field(default_factory=list, description="一致记录")
    discrepancies: list[SettlementReconciliationItem] = Field(default_factory=list, description="金额不一致")
    db_only: list[SettlementReconciliationItem] = Field(default_factory=list, description="仅数据库有")
    chain_only: list[SettlementReconciliationItem] = Field(default_factory=list, description="仅链上有")


class SettlementReportRequest(BaseModel):
    """结算报告请求"""
    billing_period: Optional[str] = Field(default=None, description="计费周期")
    subscription_id: Optional[str] = Field(default=None, description="订阅 ID")
    start_date: Optional[datetime] = Field(default=None, description="开始日期")
    end_date: Optional[datetime] = Field(default=None, description="结束日期")


class SettlementReportResponse(BaseModel):
    """结算报告响应"""
    billing_period: Optional[str] = Field(default=None, description="计费周期")
    subscription_id: Optional[str] = Field(default=None, description="订阅 ID")
    total_count: int = Field(description="总结算笔数")
    total_amount: float = Field(description="总结算金额")
    success_rate: float = Field(description="成功率 (%)")
    status_breakdown: dict[str, dict] = Field(description="按状态分组统计")
    period_breakdown: list[dict] = Field(description="按计费周期统计")
    chain_tx_count: int = Field(description="链上交易数")
    generated_at: datetime = Field(description="报告生成时间")
    summary: str = Field(description="报告摘要")


# ==================== 合约 / 区块链通用 Schema ====================


class ContractCallRequest(BaseModel):
    """合约调用请求"""
    method: str = Field(description="调用方法")
    params: Optional[dict] = Field(default=None, description="调用参数")
    from_address: Optional[str] = Field(default=None, description="发起地址")


class Transaction(BaseModel):
    """交易信息"""
    tx_hash: str = Field(description="交易哈希")
    block_number: int = Field(description="区块高度")
    from_address: str = Field(description="发送者地址")
    to_address: Optional[str] = Field(default=None, description="接收者地址")
    value: str = Field(default="0", description="交易金额")
    input_data: Optional[str] = Field(default=None, description="输入数据")
    status: str = Field(description="交易状态")
    gas_used: Optional[int] = Field(default=None, description="Gas 消耗")
    timestamp: Optional[datetime] = Field(default=None, description="交易时间")

    model_config = {"from_attributes": True}


class Block(BaseModel):
    """区块信息"""
    block_number: int = Field(description="区块高度")
    block_hash: str = Field(description="区块哈希")
    parent_hash: str = Field(description="父区块哈希")
    timestamp: datetime = Field(description="区块时间")
    transactions_count: int = Field(default=0, description="交易数量")
    transactions: list[Transaction] = Field(default_factory=list, description="交易列表")
    gas_used: Optional[int] = Field(default=None, description="Gas 消耗")
    gas_limit: Optional[int] = Field(default=None, description="Gas 限制")

    model_config = {"from_attributes": True}


class ContractInfo(BaseModel):
    """合约信息"""
    name: str = Field(description="合约名称")
    address: str = Field(description="合约地址")
    abi: Optional[list] = Field(default=None, description="合约 ABI")
    bytecode: Optional[str] = Field(default=None, description="合约字节码")
    deploy_tx_hash: Optional[str] = Field(default=None, description="部署交易哈希")
    deploy_block_number: Optional[int] = Field(default=None, description="部署区块高度")
    version: str = Field(default="1.0.0", description="合约版本")
    status: str = Field(default="active", description="合约状态")

    model_config = {"from_attributes": True}


class DeployResult(BaseModel):
    """部署结果"""
    contract_name: str = Field(description="合约名称")
    contract_address: str = Field(description="合约地址")
    tx_hash: str = Field(description="部署交易哈希")
    block_number: Optional[int] = Field(default=None, description="部署区块高度")
    abi: Optional[list] = Field(default=None, description="合约 ABI")
    gas_used: Optional[int] = Field(default=None, description="Gas 消耗")
    deployer: str = Field(description="部署者地址")
    timestamp: datetime = Field(description="部署时间")

    model_config = {"from_attributes": True}


class ChainStatus(BaseModel):
    """链状态"""
    connected: bool = Field(description="是否连接")
    chain_id: str = Field(description="链 ID")
    block_number: int = Field(default=0, description="最新区块高度")
    peer_count: int = Field(default=0, description="节点数量")
    consensus_status: Optional[str] = Field(default=None, description="共识状态")
    group_id: int = Field(default=1, description="群组 ID")
    node_version: Optional[str] = Field(default=None, description="节点版本")

    model_config = {"from_attributes": True}
