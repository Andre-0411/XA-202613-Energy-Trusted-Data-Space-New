"""
计算沙箱 Schema
沙箱创建/响应、算法扫描、出口审核
"""
from typing import Optional
from pydantic import BaseModel, Field


class SandboxCreate(BaseModel):
    """创建沙箱请求"""
    name: str = Field(max_length=200, description="沙箱名称")
    algorithm_code: str = Field(description="算法代码（Python 脚本）")
    input_asset_ids: list[str] = Field(description="输入资产 ID 列表")
    cpu_limit: str = Field(default="2", description="CPU 限制")
    memory_limit: str = Field(default="4Gi", description="内存限制")
    timeout_seconds: int = Field(default=3600, ge=10, le=86400, description="超时秒数")
    network_enabled: bool = Field(default=False, description="是否启用网络")


class SandboxRuntimeConfig(BaseModel):
    """沙箱运行时配置"""
    cpu_limit: str = Field(default="2", description="CPU 限制")
    memory_limit: str = Field(default="4Gi", description="内存限制")
    timeout_seconds: int = Field(default=3600, description="超时秒数")
    network_enabled: bool = Field(default=False, description="是否启用网络")


class SandboxResponse(BaseModel):
    """沙箱响应"""
    sandbox_id: str = Field(description="沙箱 ID")
    task_id: Optional[str] = Field(default=None, description="关联任务 ID")
    name: Optional[str] = Field(default=None, description="沙箱名称")
    status: str = Field(description="沙箱状态: created/active/scanning/running/exporting/destroyed")
    algorithm_hash: Optional[str] = Field(default=None, description="算法哈希")
    input_asset_ids: list[str] = Field(default_factory=list, description="输入资产 ID 列表")
    runtime_config: Optional[SandboxRuntimeConfig] = Field(default=None, description="运行时配置")
    created_by: Optional[str] = Field(default=None, description="创建者")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    scan_result: Optional[dict] = Field(default=None, description="扫描结果")
    export_result: Optional[dict] = Field(default=None, description="出口审核结果")


class BlacklistHit(BaseModel):
    """黑名单命中"""
    pattern: str = Field(description="匹配的正则模式")
    matches: list[str] = Field(description="匹配内容")
    severity: str = Field(description="严重级别: critical/warning")


class ScanCodeStats(BaseModel):
    """代码统计"""
    lines: int = Field(description="代码行数")
    characters: int = Field(description="字符数")
    complexity_warning: bool = Field(description="是否过于复杂")


class AlgorithmScanResult(BaseModel):
    """算法准入扫描结果"""
    sandbox_id: str = Field(description="沙箱 ID")
    is_approved: bool = Field(description="是否通过")
    blacklist_hits: list[BlacklistHit] = Field(default_factory=list, description="黑名单命中")
    code_stats: ScanCodeStats = Field(description="代码统计")
    resource_warnings: list[str] = Field(default_factory=list, description="资源警告")
    scanned_at: str = Field(description="扫描时间")


class ComplianceChecks(BaseModel):
    """合规性检查"""
    has_scan_approval: bool = Field(description="是否有扫描批准")
    no_sensitive_data: bool = Field(description="是否无敏感数据")
    data_volume_within_limit: bool = Field(description="数据量是否在限制内")
    algorithm_hash_verified: bool = Field(description="算法哈希是否验证通过")


class ExportAuditResult(BaseModel):
    """出口审核结果"""
    sandbox_id: str = Field(description="沙箱 ID")
    is_approved: bool = Field(description="是否通过")
    sensitive_findings: list[dict] = Field(default_factory=list, description="敏感数据发现")
    compliance_checks: ComplianceChecks = Field(description="合规性检查")
    data_volume_bytes: int = Field(description="数据量（字节）")
    volume_limit_bytes: int = Field(description="数据量限制（字节）")
    volume_ok: bool = Field(description="数据量是否合格")
    audited_at: str = Field(description="审核时间")
