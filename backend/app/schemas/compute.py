"""
计算任务 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class ComputeTaskCreate(BaseModel):
    """创建计算任务"""
    name: str = Field(max_length=200, description="任务名称")
    task_type: str = Field(description="类型: FL/MPC/TEE/HE/DP")
    scenario: Optional[str] = Field(default=None, description="业务场景路由")
    dag_id: Optional[str] = Field(default=None, description="关联 DAG ID")
    config: dict = Field(description="任务配置")
    input_asset_ids: list[str] = Field(description="输入资产 ID 列表")


class ComputeTaskResponse(BaseModel):
    """计算任务响应"""
    id: str
    name: str
    task_type: str
    scenario: Optional[str] = None
    dag_id: Optional[str] = None
    config: Optional[dict] = None
    input_asset_ids: Optional[list[str]] = None
    status: str
    progress: int = 0
    result_ref: Optional[str] = None
    result_hash: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DagCreate(BaseModel):
    """创建 DAG"""
    name: str = Field(max_length=200, description="DAG 名称")
    description: Optional[str] = Field(default=None, description="描述")
    nodes: dict = Field(description="节点定义")
    edges: dict = Field(description="边定义")


class DagResponse(BaseModel):
    """DAG 响应"""
    id: str
    name: str
    description: Optional[str] = None
    nodes: dict
    edges: dict
    version: int
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskSignatureRequest(BaseModel):
    """任务签名请求"""
    signer_did: str = Field(description="签名方 DID")
    signature: str = Field(description="SM2 签名值")


# ==================== 计算集群节点管理 ====================


class NodeCapabilities(BaseModel):
    """节点能力描述"""
    cpu_cores: int = Field(default=0, description="CPU 核数")
    memory_mb: int = Field(default=0, description="内存大小(MB)")
    gpu_count: int = Field(default=0, description="GPU 数量")
    gpu_memory_mb: int = Field(default=0, description="GPU 显存(MB)")
    supported_types: list[str] = Field(default_factory=list, description="支持的计算类型: FL/MPC/TEE/HE/DP")
    max_concurrent_tasks: int = Field(default=1, description="最大并发任务数")


class ClusterNodeCreate(BaseModel):
    """注册集群节点"""
    name: str = Field(max_length=200, description="节点名称")
    node_type: str = Field(description="节点类型: FATE/MPC/TEE/HE/通用")
    endpoint: str = Field(description="节点通信地址 (host:port)")
    region: Optional[str] = Field(default=None, description="部署区域")
    organization_id: Optional[str] = Field(default=None, description="所属组织 ID")
    capabilities: NodeCapabilities = Field(default_factory=NodeCapabilities, description="节点能力")
    metadata: dict = Field(default_factory=dict, description="扩展元数据")


class ClusterNodeUpdate(BaseModel):
    """更新集群节点"""
    name: Optional[str] = Field(default=None, max_length=200, description="节点名称")
    node_type: Optional[str] = Field(default=None, description="节点类型")
    endpoint: Optional[str] = Field(default=None, description="节点通信地址")
    region: Optional[str] = Field(default=None, description="部署区域")
    capabilities: Optional[NodeCapabilities] = Field(default=None, description="节点能力")
    metadata: Optional[dict] = Field(default=None, description="扩展元数据")


class ClusterNodeResponse(BaseModel):
    """集群节点响应"""
    node_id: str = Field(description="节点 ID")
    name: str = Field(description="节点名称")
    node_type: str = Field(description="节点类型")
    endpoint: str = Field(description="节点通信地址")
    region: Optional[str] = None
    organization_id: Optional[str] = None
    status: str = Field(description="节点状态: online/offline/disabled")
    capabilities: NodeCapabilities = Field(description="节点能力")
    active_tasks: int = Field(default=0, description="当前活跃任务数")
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime = Field(description="注册时间")
    metadata: dict = Field(default_factory=dict)


class NodeHeartbeat(BaseModel):
    """节点心跳"""
    status: str = Field(default="online", description="节点状态")
    active_tasks: int = Field(default=0, description="当前活跃任务数")
    cpu_usage: float = Field(default=0.0, description="CPU 使用率 (0-1)")
    memory_usage: float = Field(default=0.0, description="内存使用率 (0-1)")
    gpu_usage: float = Field(default=0.0, description="GPU 使用率 (0-1)")


class ClusterStatus(BaseModel):
    """集群整体状态"""
    total_nodes: int = Field(description="节点总数")
    online_nodes: int = Field(description="在线节点数")
    offline_nodes: int = Field(description="离线节点数")
    disabled_nodes: int = Field(description="禁用节点数")
    total_active_tasks: int = Field(description="集群活跃任务总数")
    available_capacity: dict = Field(description="可用容量汇总")
    nodes: list[ClusterNodeResponse] = Field(default_factory=list)


class ClusterDispatchRequest(BaseModel):
    """任务派发请求"""
    task_id: str = Field(description="计算任务 ID")
    task_type: str = Field(description="任务类型: FL/MPC/TEE/HE/DP")
    preferred_node_id: Optional[str] = Field(default=None, description="首选节点 ID (可选)")
    required_capabilities: Optional[NodeCapabilities] = Field(default=None, description="所需节点能力")
    priority: int = Field(default=0, description="优先级 (越大越高)")


class ClusterDispatchResponse(BaseModel):
    """任务派发响应"""
    dispatch_id: str = Field(description="派发 ID")
    task_id: str = Field(description="计算任务 ID")
    node_id: str = Field(description="被派发的节点 ID")
    node_endpoint: str = Field(description="节点通信地址")
    status: str = Field(description="派发状态: dispatched/queued/failed")
    dispatched_at: datetime = Field(description="派发时间")


# ==================== AI Agent 请求 Schema ====================


class AgentQueryRequest(BaseModel):
    """查询代理请求"""
    query: str = Field(description="自然语言查询")
    context: Optional[dict] = Field(default=None, description="上下文信息")


class AgentTradeRequest(BaseModel):
    """交易代理请求"""
    request: str = Field(description="交易相关查询")
    context: Optional[dict] = Field(default=None, description="上下文信息")


class AgentSecurityRequest(BaseModel):
    """安全代理请求"""
    query: str = Field(description="安全相关查询")
    context: Optional[dict] = Field(default=None, description="上下文信息")


class AgentDispatchRequest(BaseModel):
    """调度代理请求"""
    task: str = Field(description="调度相关查询")
    context: Optional[dict] = Field(default=None, description="上下文信息")
