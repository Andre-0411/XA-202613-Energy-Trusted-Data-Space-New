from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class EvidenceResponse(BaseModel):
    """存证响应"""
    id: int
    asset_id: Optional[int] = None
    action: str
    operator_id: int
    data_hash: str
    block_height: int
    prev_hash: str
    block_hash: str
    timestamp: datetime
    extra_data: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class EvidenceWithDetail(EvidenceResponse):
    """存证详情"""
    operator_name: Optional[str] = None
    asset_name: Optional[str] = None


class ChainBlock(BaseModel):
    """区块信息"""
    block_height: int
    block_hash: str
    prev_hash: str
    evidence_count: int
    timestamp: datetime
    evidences: List[EvidenceResponse] = []


class TraceEvent(BaseModel):
    """追踪事件"""
    evidence_id: int
    action: str
    operator_name: str
    data_hash: str
    block_height: int
    timestamp: datetime
    extra_data: Optional[Dict[str, Any]] = None


class TraceTimeline(BaseModel):
    """追踪时间线"""
    asset_id: int
    asset_name: str
    total_events: int
    events: List[TraceEvent] = []


class ChainVerifyResult(BaseModel):
    """链验证结果"""
    is_valid: bool
    total_blocks: int
    checked_blocks: int
    invalid_blocks: List[Dict[str, Any]] = []


class EvidenceRecord(BaseModel):
    """存证记录"""
    id: str = Field(description="存证 ID")
    node_type: str = Field(description="存证节点类型（collect/preprocess/classify/publish/apply/compute/result/settle）")
    resource_id: str = Field(description="关联资源 ID")
    resource_type: str = Field(description="资源类型")
    data_hash: str = Field(description="数据 SM3 哈希")
    previous_hash: str = Field(default="", description="前一条存证哈希（链式结构）")
    evidence_data: Dict[str, Any] = Field(description="存证数据")
    tx_hash: Optional[str] = Field(default=None, description="链上交易哈希")
    block_number: Optional[int] = Field(default=None, description="区块高度")
    operator_did: Optional[str] = Field(default=None, description="操作者 DID")
    schema_version: str = Field(default="1.0", description="数据模式版本")
    timestamp: datetime = Field(description="存证时间")

    model_config = {"from_attributes": True}


class EvidenceChain(BaseModel):
    """存证链"""
    resource_id: str = Field(description="资源 ID")
    resource_type: str = Field(description="资源类型")
    total_records: int = Field(description="存证记录总数")
    chain_valid: bool = Field(description="链完整性是否有效")
    records: List[EvidenceRecord] = Field(default_factory=list, description="存证记录列表")
    first_hash: Optional[str] = Field(default=None, description="链首哈希")
    last_hash: Optional[str] = Field(default=None, description="链尾哈希")

    model_config = {"from_attributes": True}


class EvidenceVerify(BaseModel):
    """存证验证结果"""
    evidence_id: str = Field(description="存证 ID")
    hash_valid: bool = Field(description="哈希验证是否通过")
    chain_valid: bool = Field(description="链完整性验证是否通过")
    on_chain: bool = Field(description="是否已上链")
    tx_hash: Optional[str] = Field(default=None, description="链上交易哈希")
    block_number: Optional[int] = Field(default=None, description="区块高度")
    verification_time: datetime = Field(description="验证时间")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")

    model_config = {"from_attributes": True}
