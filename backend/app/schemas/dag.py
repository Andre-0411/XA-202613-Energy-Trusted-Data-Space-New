"""
DAG 编排 Schema
DAG 节点/边定义、验证请求/响应、执行计划
"""
from typing import Optional
from pydantic import BaseModel, Field


class DagNode(BaseModel):
    """DAG 节点"""
    id: str = Field(description="节点 ID")
    type: str = Field(description="节点类型: FL/MPC/TEE/HE/DP/Sandbox/Input/Output")
    config: dict = Field(default_factory=dict, description="节点配置")
    input_asset_ids: list[str] = Field(default_factory=list, description="输入资产 ID 列表")


class DagEdge(BaseModel):
    """DAG 边"""
    source: str = Field(description="源节点 ID", alias="from")
    target: str = Field(description="目标节点 ID", alias="to")

    model_config = {"populate_by_name": True}


class DagValidationResult(BaseModel):
    """DAG 验证结果"""
    is_valid: bool = Field(description="是否有效")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")
    node_count: int = Field(default=0, description="节点数量")
    edge_count: int = Field(default=0, description="边数量")
    execution_plan: Optional[list[list[str]]] = Field(default=None, description="并行执行计划")


class DagNodeStatus(BaseModel):
    """DAG 节点执行状态"""
    status: str = Field(description="节点状态: pending/running/completed/failed/skipped")
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    error: Optional[str] = Field(default=None, description="错误信息")


class DagExecutionResponse(BaseModel):
    """DAG 执行响应"""
    dag_id: str = Field(description="DAG ID")
    execution_id: str = Field(description="执行 ID")
    status: str = Field(description="执行状态")
    execution_plan: list[list[str]] = Field(description="并行执行计划")
    parallel_layers: int = Field(description="并行层数")
    tasks_created: int = Field(description="创建的任务数")
    task_details: list[dict] = Field(default_factory=list, description="任务详情")
    node_statuses: dict[str, DagNodeStatus] = Field(default_factory=dict, description="节点状态映射")
    started_at: str = Field(description="开始时间")


class DagExecutionStatus(BaseModel):
    """DAG 执行状态查询响应"""
    dag_id: str = Field(description="DAG ID")
    execution_id: Optional[str] = Field(default=None, description="执行 ID")
    status: str = Field(description="执行状态")
    total_tasks: int = Field(description="任务总数")
    status_summary: dict[str, int] = Field(default_factory=dict, description="状态统计")
    progress: float = Field(default=0.0, description="进度百分比")
    task_details: list[dict] = Field(default_factory=list, description="任务详情")
    execution_plan: Optional[list[list[str]]] = Field(default=None, description="执行计划")
    started_at: Optional[str] = Field(default=None, description="开始时间")


class DagExecutionHistory(BaseModel):
    """DAG 执行历史"""
    execution_id: str = Field(description="执行 ID")
    dag_id: str = Field(description="DAG ID")
    dag_name: str = Field(description="DAG 名称")
    status: str = Field(description="执行状态")
    started_at: str = Field(description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    tasks_created: int = Field(default=0, description="创建的任务数")
