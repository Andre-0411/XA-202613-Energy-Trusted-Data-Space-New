"""
性能基准 Schema
基准测试配置、结果、对比报告
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BenchmarkRequest(BaseModel):
    """基准测试请求"""
    algorithms: list[str] = Field(description="要测试的算法列表")
    iterations: int = Field(default=10, ge=1, le=1000, description="测试迭代次数")
    data_size: int = Field(default=1000, ge=1, description="测试数据规模")
    participants: int = Field(default=2, ge=2, description="参与方数量")
    config_override: Optional[dict] = Field(default=None, description="覆盖配置")


class AlgorithmBenchmark(BaseModel):
    """单算法基准结果"""
    algorithm: str = Field(description="算法名称")
    algorithm_name: str = Field(description="算法显示名称")
    avg_time_ms: float = Field(description="平均执行时间(ms)")
    min_time_ms: float = Field(description="最小执行时间(ms)")
    max_time_ms: float = Field(description="最大执行时间(ms)")
    p50_time_ms: float = Field(default=0.0, description="P50执行时间(ms)")
    p95_time_ms: float = Field(default=0.0, description="P95执行时间(ms)")
    p99_time_ms: float = Field(default=0.0, description="P99执行时间(ms)")
    throughput: float = Field(description="吞吐量(ops/s)")
    cpu_usage_percent: float = Field(description="CPU 使用率(%)")
    memory_usage_mb: float = Field(description="内存使用(MB)")
    task_count: int = Field(default=0, description="任务数")
    success_rate: float = Field(default=1.0, description="成功率(0-1)")
    iterations: int = Field(default=0, description="测试迭代次数")


class BenchmarkResponse(BaseModel):
    """基准测试响应"""
    benchmark_id: str = Field(description="基准测试 ID")
    status: str = Field(description="状态: pending/running/completed/failed")
    algorithms: list[str] = Field(description="测试算法列表")
    iterations: int = Field(description="迭代次数")
    data_size: int = Field(description="数据规模")
    participants: int = Field(description="参与方数量")
    results: list[AlgorithmBenchmark] = Field(default_factory=list, description="测试结果")
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    total_time_ms: Optional[float] = Field(default=None, description="总耗时(ms)")


class BenchmarkSummary(BaseModel):
    """基准摘要"""
    total_benchmarks: int = Field(description="基准测试总数")
    algorithms_tested: list[str] = Field(description="已测试算法")
    latest_benchmark_id: Optional[str] = Field(default=None, description="最新基准 ID")
    latest_results: list[AlgorithmBenchmark] = Field(default_factory=list, description="最新结果")


class TrendDataPoint(BaseModel):
    """趋势数据点"""
    timestamp: str = Field(description="时间戳")
    algorithm: str = Field(description="算法名称")
    avg_time_ms: float = Field(description="平均执行时间(ms)")
    throughput: float = Field(description="吞吐量")
    cpu_usage_percent: float = Field(description="CPU 使用率")
    memory_usage_mb: float = Field(description="内存使用")


class BenchmarkExportRequest(BaseModel):
    """基准报告导出请求"""
    benchmark_ids: list[str] = Field(description="基准测试 ID 列表")
    format: str = Field(default="json", description="导出格式: json/csv/pdf")
    include_charts: bool = Field(default=True, description="是否包含图表")
